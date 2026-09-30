"""
Rotas de Funcionários — CRUD local + sincronização com o device.
"""
import base64
import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.services import employee_service
from app.services.export_service import export_employees_csv, export_employees_xlsx
from app.services.sync_service import _build_client

logger = logging.getLogger("routes_employees")
router = APIRouter()
from app.templates_config import templates


# ---------------------------------------------------------------------------
# Página HTML
# ---------------------------------------------------------------------------

@router.get("/funcionarios")
async def employees_page(request: Request, db: Session = Depends(get_db)):
    result = employee_service.list_employees(db, page=1, page_size=50)
    return templates.TemplateResponse("employees.html", {
        "request": request,
        "employees": result["items"],
        "pagination": result,
        "active_page": "employees",
    })


# ---------------------------------------------------------------------------
# API JSON
# ---------------------------------------------------------------------------

@router.get("/api/employees")
async def list_employees(
    page: int = 1,
    page_size: int = 50,
    search: Optional[str] = None,
    department: Optional[int] = None,
    sync_status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    result = employee_service.list_employees(
        db, page=page, page_size=page_size,
        search=search, department=department, sync_status=sync_status,
    )
    return {
        "items": [_serialize(e) for e in result["items"]],
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
        "pages": result["pages"],
    }


@router.get("/api/employees/{employee_id}")
async def get_employee(employee_id: int, db: Session = Depends(get_db)):
    emp = employee_service.get_employee(db, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")
    return _serialize(emp)


@router.post("/api/employees", status_code=201)
async def create_employee(data: EmployeeCreate, db: Session = Depends(get_db)):
    try:
        emp = employee_service.create_employee(db, data)
        # Tenta sincronizar imediatamente
        _try_sync_now(db, emp.id)
        db.refresh(emp)
        return {"success": True, "employee": _serialize(emp)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/api/employees/{employee_id}")
async def update_employee(
    employee_id: int,
    data: EmployeeUpdate,
    db: Session = Depends(get_db),
):
    try:
        emp = employee_service.update_employee(db, employee_id, data)
        # Tenta sincronizar imediatamente
        _try_sync_now(db, emp.id)
        db.refresh(emp)
        return {"success": True, "employee": _serialize(emp)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ---------------------------------------------------------------------------
# Upload de foto + cadastro via multipart
# ---------------------------------------------------------------------------

@router.post("/api/employees/with-photo", status_code=201)
async def create_employee_with_photo(
    userid: str = Form(...),
    name: str = Form(""),
    department: int = Form(0),
    schedule: int = Form(0),
    role: int = Form(0),
    access_card_number: str = Form(""),
    person_period: int = Form(0),
    pass_times: int = Form(-1),
    pass_date: str = Form("0"),
    userpassword: str = Form(""),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """
    Cria funcionário com foto facial.
    A foto é convertida para base64 e enviada ao device como pic_large.
    featureFile, fingerFile e palmFiles nunca são fabricados.
    """
    pic_large_b64 = ""
    if photo and photo.filename:
        raw = await photo.read()
        pic_large_b64 = base64.b64encode(raw).decode("utf-8")

    data = EmployeeCreate(
        userid=userid,
        name=name,
        department=department,
        schedule=schedule,
        role=role,
        access_card_number=access_card_number,
        person_period=person_period,
        pass_times=pass_times,
        pass_date=pass_date,
        userpassword=userpassword,
    )

    try:
        emp = employee_service.create_employee(db, data)
        # Sincroniza imediatamente, passando a foto se houver
        sync_result = _try_sync_now(db, emp.id, pic_large_b64)
        db.refresh(emp)
        return {
            "success": True,
            "employee": _serialize(emp),
            "synced": sync_result.get("synced", False),
            "sync_detail": sync_result.get("reason", ""),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ---------------------------------------------------------------------------
# Sincronização
# ---------------------------------------------------------------------------

@router.post("/api/employees/{employee_id}/sync")
async def sync_employee(employee_id: int, db: Session = Depends(get_db)):
    client = _build_client(db)
    if not client:
        raise HTTPException(status_code=503, detail="Device não configurado (host/senha ausentes)")
    try:
        result = employee_service.sync_employee_now(db, employee_id, client)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ---------------------------------------------------------------------------
# Exclusão de funcionário
# ---------------------------------------------------------------------------

@router.delete("/api/employees/{employee_id}")
async def delete_employee(
    employee_id: int,
    sync_device: bool = True,
    db: Session = Depends(get_db),
):
    """
    Remove um funcionário do banco local e, opcionalmente, do device.

    Parâmetros:
      employee_id — id interno (PK) do funcionário
      sync_device — True (default): tenta remover do device também via /deleteEmployee

    Se sync_device=True e o device estiver offline, o funcionário é removido
    do banco local mesmo assim e o erro do device é relatado no retorno.
    """
    from app.services.facial_client import (
        FacialApiError, FacialAuthenticationError,
        FacialOfflineError, FacialTimeoutError,
    )

    emp = employee_service.get_employee(db, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")

    userid = emp.userid
    device_result: dict = {}

    if sync_device:
        client = _build_client(db)
        if client:
            try:
                device_result = client.delete_employee([userid])
                code = device_result.get("code", 200) if isinstance(device_result, dict) else 200
                if code not in (0, 200):
                    device_result["warning"] = f"Device retornou code={code}"
            except (FacialOfflineError, FacialTimeoutError) as exc:
                device_result = {"warning": f"Device offline — removido apenas do banco: {exc}"}
                logger.warning("delete_employee: device offline para userid=%s: %s", userid, exc)
            except FacialAuthenticationError as exc:
                device_result = {"warning": f"Autenticação falhou: {exc}"}
            except FacialApiError as exc:
                device_result = {"warning": f"Erro do device: {exc}"}
        else:
            device_result = {"warning": "Device não configurado — removido apenas do banco"}

    # Remove do banco local
    db.delete(emp)
    db.commit()
    logger.info("Funcionário userid=%s removido do banco local.", userid)

    return {
        "success": True,
        "userid": userid,
        "device": device_result,
    }


@router.post("/api/employees/sync-all")
async def sync_all_employees(db: Session = Depends(get_db)):
    client = _build_client(db)
    if not client:
        raise HTTPException(status_code=503, detail="Device não configurado (host/senha ausentes)")

    result = employee_service.import_from_device(db, client)
    return {"success": True, **result}


# ---------------------------------------------------------------------------
# Exportação
# ---------------------------------------------------------------------------

@router.get("/api/reports/employees.xlsx")
async def export_xlsx(db: Session = Depends(get_db)):
    content = export_employees_xlsx(db)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=funcionarios.xlsx"},
    )


@router.get("/api/reports/employees.csv")
async def export_csv(db: Session = Depends(get_db)):
    content = export_employees_csv(db)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=funcionarios.csv"},
    )


# ---------------------------------------------------------------------------
# Helper de serialização
# ---------------------------------------------------------------------------

def _serialize(emp) -> dict:
    return {
        "id": emp.id,
        "userid": emp.userid,
        "name": emp.name,
        "department": emp.department,
        "schedule": emp.schedule,
        "role": emp.role,
        "access_card_number": emp.access_card_number or "",
        "id_number": emp.id_number or "",
        "person_period": emp.person_period,
        "pass_times": emp.pass_times,
        "pass_date": emp.pass_date,
        "has_face": emp.has_face,
        "has_fingerprint": emp.has_fingerprint,
        "has_palm": emp.has_palm,
        "device_synced": emp.device_synced,
        "sync_status": emp.sync_status,
        "last_synced_at": emp.last_synced_at.isoformat() if emp.last_synced_at else None,
        "created_at": emp.created_at.isoformat() if emp.created_at else None,
        "updated_at": emp.updated_at.isoformat() if emp.updated_at else None,
    }


# ---------------------------------------------------------------------------
# Helper: tenta sincronizar com o device imediatamente após criar/editar
# ---------------------------------------------------------------------------

def _try_sync_now(db: Session, employee_id: int, pic_large_b64: str = "") -> dict:
    """
    Tenta enviar o funcionário ao device logo após criar/editar.
    Não levanta exceção — falhas ficam registradas na sync_queue como PENDING.
    """
    from datetime import datetime, timezone
    client = _build_client(db)
    if not client:
        logger.info("Device não configurado, funcionário ficará como PENDING na fila.")
        return {"synced": False, "reason": "device_not_configured"}

    emp = employee_service.get_employee(db, employee_id)
    if not emp:
        return {"synced": False, "reason": "not_found"}

    payload = employee_service._employee_payload_from_model(emp)
    if pic_large_b64:
        payload["pic_large"] = pic_large_b64

    try:
        if emp.device_synced:
            result = client.update_employee(payload)
        else:
            result = client.insert_employee(payload)

        code = result.get("code", 200) if isinstance(result, dict) else 200
        ok   = result.get("result", 0)  if isinstance(result, dict) else 0

        if code in (0, 200) or ok == 0:
            emp.device_synced = True
            emp.sync_status   = "SUCCESS"
            emp.has_face      = emp.has_face or bool(pic_large_b64)
            emp.last_synced_at = datetime.now(timezone.utc)
            # Marca itens da fila deste funcionário como SUCCESS
            from app.database.models import SyncQueue
            db.query(SyncQueue).filter(
                SyncQueue.entity_id == emp.userid,
                SyncQueue.status.in_(["PENDING", "PROCESSING"]),
            ).update({"status": "SUCCESS", "synced_at": datetime.now(timezone.utc)})
            db.commit()
            logger.info("Funcionário %s sincronizado imediatamente com o device.", emp.userid)
            return {"synced": True}
        else:
            msg = result.get("message", "Erro desconhecido") if isinstance(result, dict) else str(result)
            emp.sync_status = "ERROR"
            db.commit()
            logger.warning("Device recusou funcionário %s: %s", emp.userid, msg)
            return {"synced": False, "reason": msg}

    except Exception as exc:
        # Não propaga — ficará como PENDING na fila para retry automático
        emp.sync_status = "ERROR"
        db.commit()
        logger.warning("Sync imediato falhou para %s, entrará no próximo ciclo: %s", emp.userid, exc)
        return {"synced": False, "reason": str(exc)}
