"""
EmployeeService — lógica de negócio para funcionários.

Orquestra operações entre o banco local (SQLite) e o FacialClient.
Nunca chama httpx diretamente.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.database.models import Employee, SyncQueue
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.services.facial_client import (
    FacialClient,
    FacialOfflineError,
    FacialTimeoutError,
    FacialApiError,
)

logger = logging.getLogger("employee_service")


# ---------------------------------------------------------------------------
# Leitura
# ---------------------------------------------------------------------------

def list_employees(
    db: Session,
    page: int = 1,
    page_size: int = 50,
    search: Optional[str] = None,
    department: Optional[int] = None,
    sync_status: Optional[str] = None,
) -> dict:
    query = db.query(Employee)

    if search:
        term = f"%{search}%"
        query = query.filter(
            Employee.name.ilike(term) | Employee.userid.ilike(term)
        )
    if department is not None:
        query = query.filter(Employee.department == department)
    if sync_status:
        query = query.filter(Employee.sync_status == sync_status)

    total = query.count()
    items = query.order_by(Employee.name).offset((page - 1) * page_size).limit(page_size).all()
    pages = max(1, (total + page_size - 1) // page_size)

    return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": pages}


def get_employee(db: Session, employee_id: int) -> Optional[Employee]:
    return db.query(Employee).filter(Employee.id == employee_id).first()


def get_employee_by_userid(db: Session, userid: str) -> Optional[Employee]:
    return db.query(Employee).filter(Employee.userid == userid).first()


# ---------------------------------------------------------------------------
# Criação local + enfileiramento
# ---------------------------------------------------------------------------

def create_employee(db: Session, data: EmployeeCreate) -> Employee:
    """Cria funcionário localmente e enfileira sincronização com o device."""
    existing = get_employee_by_userid(db, data.userid)
    if existing:
        raise ValueError(f"Funcionário com userid '{data.userid}' já existe.")

    emp = Employee(
        userid=data.userid,
        name=data.name,
        department=data.department,
        schedule=data.schedule,
        role=data.role,
        access_card_number=data.access_card_number,
        id_number=data.id_number,
        person_period=data.person_period,
        pass_times=data.pass_times,
        pass_date=data.pass_date,
        sync_status="PENDING",
        device_synced=False,
    )
    db.add(emp)
    db.flush()

    # Enfileira operação para enviar ao device
    _enqueue(db, "employee", str(emp.userid), "INSERT", _employee_payload(data))

    db.commit()
    db.refresh(emp)
    logger.info("Funcionário criado localmente: userid=%s name=%s", emp.userid, emp.name)
    return emp


# ---------------------------------------------------------------------------
# Atualização local + enfileiramento
# ---------------------------------------------------------------------------

def update_employee(db: Session, employee_id: int, data: EmployeeUpdate) -> Employee:
    emp = get_employee(db, employee_id)
    if not emp:
        raise ValueError(f"Funcionário id={employee_id} não encontrado.")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field != "userpassword":   # senha não persiste localmente
            setattr(emp, field, value)

    emp.sync_status = "PENDING"
    emp.device_synced = False

    payload = _employee_payload_from_model(emp)
    if "userpassword" in update_data:
        payload["userpassword"] = update_data["userpassword"]

    _enqueue(db, "employee", str(emp.userid), "UPDATE", payload)

    db.commit()
    db.refresh(emp)
    logger.info("Funcionário atualizado localmente: userid=%s", emp.userid)
    return emp


# ---------------------------------------------------------------------------
# Sincronização imediata de um funcionário
# ---------------------------------------------------------------------------

def sync_employee_now(db: Session, employee_id: int, client: FacialClient) -> dict:
    """Tenta sincronizar um funcionário específico imediatamente."""
    emp = get_employee(db, employee_id)
    if not emp:
        raise ValueError(f"Funcionário id={employee_id} não encontrado.")

    payload = _employee_payload_from_model(emp)
    try:
        if emp.device_synced:
            result = client.update_employee(payload)
        else:
            result = client.insert_employee(payload)

        # Verifica código de sucesso
        if isinstance(result, dict):
            code = result.get("code", 200)
            if code not in (0, 200):
                raise FacialApiError(result.get("message", "Erro desconhecido"), body=result)

        emp.device_synced = True
        emp.sync_status = "SUCCESS"
        emp.last_synced_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("Funcionário sincronizado: userid=%s", emp.userid)
        return {"success": True, "message": "Sincronizado com sucesso"}

    except (FacialOfflineError, FacialTimeoutError) as exc:
        emp.sync_status = "ERROR"
        db.commit()
        logger.warning("Dispositivo offline ao sincronizar userid=%s: %s", emp.userid, exc)
        return {"success": False, "message": str(exc)}

    except FacialApiError as exc:
        emp.sync_status = "ERROR"
        db.commit()
        logger.error("Erro da API ao sincronizar userid=%s: %s", emp.userid, exc)
        return {"success": False, "message": str(exc)}


# ---------------------------------------------------------------------------
# Importar funcionários do device → SQLite
# ---------------------------------------------------------------------------

def import_from_device(db: Session, client: FacialClient) -> dict:
    """
    Busca todos os funcionários do ALPHA-1111 e atualiza o banco local.
    Não sobrescreve funcionários locais que ainda têm sync_status=PENDING.
    """
    imported = 0
    updated = 0
    errors = []

    try:
        index = 1
        page_size = 100
        while True:
            result = client.get_employee_list(index=index, count=page_size)
            employees = result.get("data", [])
            if not employees:
                break

            for item in employees:
                uid = str(item.get("userid", ""))
                if not uid:
                    continue

                existing = get_employee_by_userid(db, uid)
                if existing:
                    if existing.sync_status == "PENDING":
                        continue  # não sobrescreve pendência local
                    existing.name = item.get("name", existing.name)
                    existing.department = item.get("department", existing.department)
                    existing.schedule = item.get("schedule", existing.schedule)
                    existing.role = item.get("role", existing.role)
                    existing.access_card_number = item.get("access_card_number", existing.access_card_number)
                    existing.has_face = item.get("face_norm", 0) > 0
                    existing.has_fingerprint = item.get("fingerprintid", 0) > 0
                    existing.has_palm = (item.get("palmleftid", 0) > 0 or item.get("palmrightid", 0) > 0)
                    existing.device_synced = True
                    existing.sync_status = "SUCCESS"
                    existing.last_synced_at = datetime.now(timezone.utc)
                    updated += 1
                else:
                    emp = Employee(
                        userid=uid,
                        name=item.get("name", ""),
                        department=item.get("department", 0),
                        schedule=item.get("schedule", 0),
                        role=item.get("role", 0),
                        access_card_number=item.get("access_card_number", ""),
                        pass_times=item.get("pass_times", -1),
                        has_face=item.get("face_norm", 0) > 0,
                        has_fingerprint=item.get("fingerprintid", 0) > 0,
                        has_palm=(item.get("palmleftid", 0) > 0 or item.get("palmrightid", 0) > 0),
                        device_synced=True,
                        sync_status="SUCCESS",
                        last_synced_at=datetime.now(timezone.utc),
                    )
                    db.add(emp)
                    imported += 1

            db.commit()

            total = result.get("total", 0)
            if index * page_size >= total:
                break
            index += 1

    except (FacialOfflineError, FacialTimeoutError, FacialApiError) as exc:
        errors.append(str(exc))
        logger.warning("Erro ao importar funcionários do device: %s", exc)

    return {"imported": imported, "updated": updated, "errors": errors}


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _employee_payload(data: EmployeeCreate) -> dict:
    return {
        "userid": data.userid,
        "name": data.name,
        "access_card_number": data.access_card_number,
        "userpassword": data.userpassword,
        "department": data.department,
        "schedule": data.schedule,
        "role": data.role,
        "person_period": data.person_period,
        "pass_times": data.pass_times,
        "pass_date": data.pass_date,
        "pass_time": "[null,null,null]",
        "pic_large": "",
        "featureFile": "",
        "fingerFile": "",
        "palm1File": "",
        "palm2File": "",
    }


def _employee_payload_from_model(emp: Employee) -> dict:
    return {
        "userid": emp.userid,
        "name": emp.name,
        "access_card_number": emp.access_card_number or "",
        "userpassword": "",
        "department": emp.department,
        "schedule": emp.schedule,
        "role": emp.role,
        "person_period": emp.person_period,
        "pass_times": emp.pass_times,
        "pass_date": emp.pass_date or "0",
        "pass_time": "[null,null,null]",
        "new_userid": emp.userid,
        "pic_large": "",
        "featureFile": "",
        "fingerFile": "",
        "palm1File": "",
        "palm2File": "",
    }


def _enqueue(db: Session, entity_type: str, entity_id: str, operation: str, payload: dict):
    entry = SyncQueue(
        entity_type=entity_type,
        entity_id=entity_id,
        operation=operation,
        payload=json.dumps(payload, ensure_ascii=False),
        status="PENDING",
    )
    db.add(entry)
