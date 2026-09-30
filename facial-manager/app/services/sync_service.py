"""
SyncService — orquestrador de sincronização contínua com o ALPHA-1111.

Fluxo por ciclo:
  1. Testar conexão com o device
  2. Processar fila de pendências (sync_queue)
  3. Importar funcionários do device → SQLite
  4. Fazer polling de presença
  5. Atualizar device_status
  6. Registrar sync_log
  7. Aguardar intervalo configurável
"""
import asyncio
import json
import logging
import time
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.database.models import ApplicationLog, DeviceStatus, SyncLog, SyncQueue
from app.services.attendance_service import (
    format_date_for_device,
    poll_attendance,
    poll_work_note,
)
from app.services.employee_service import import_from_device
from app.services.facial_client import (
    FacialApiError,
    FacialAuthenticationError,
    FacialClient,
    FacialOfflineError,
    FacialTimeoutError,
)

logger = logging.getLogger("sync_service")

# Instância global mantida pelo main.py
_sync_task: asyncio.Task | None = None
_running = False


# ---------------------------------------------------------------------------
# Fábrica de cliente — lê configurações do banco a cada ciclo
# ---------------------------------------------------------------------------

def _build_client(db: Session) -> FacialClient | None:
    from app.database.models import Setting

    def _get(key: str, default: str = "") -> str:
        row = db.query(Setting).filter(Setting.key == key).first()
        return row.value if row and row.value else default

    host = _get("device_host")
    password = _get("device_password")
    port = int(_get("device_port", "80"))
    timeout = float(_get("device_timeout", "10"))

    if not host or not password:
        logger.warning("Configurações do device incompletas (host/password). Sincronização pausada.")
        return None

    return FacialClient(host=host, password=password, port=port, timeout=timeout)


def _get_setting(db: Session, key: str, default: str = "") -> str:
    from app.database.models import Setting
    row = db.query(Setting).filter(Setting.key == key).first()
    return row.value if row and row.value else default


# ---------------------------------------------------------------------------
# Teste de conexão
# ---------------------------------------------------------------------------

def test_connection(db: Session) -> dict:
    """Executa /getDevAuth e retorna status de conexão."""
    client = _build_client(db)
    if not client:
        return {"connected": False, "error": "Configurações incompletas (host ou senha)."}

    start = time.monotonic()
    try:
        result = client.get_device_auth()
        elapsed = (time.monotonic() - start) * 1000

        _update_device_status(db, online=True, response_time=elapsed)
        _log_comm(db, endpoint="/getDevAuth", status_code=200,
                  duration_ms=elapsed, success=True)

        return {
            "connected": True,
            "host": client.host,
            "response_time_ms": round(elapsed, 1),
            "device_info": result,
        }

    except FacialOfflineError as exc:
        elapsed = (time.monotonic() - start) * 1000
        _update_device_status(db, online=False, error=str(exc))
        _log_comm(db, endpoint="/getDevAuth", duration_ms=elapsed,
                  success=False, error=str(exc))
        return {"connected": False, "host": client.host, "error": str(exc)}

    except FacialTimeoutError as exc:
        elapsed = (time.monotonic() - start) * 1000
        _update_device_status(db, online=False, error=str(exc))
        _log_comm(db, endpoint="/getDevAuth", duration_ms=elapsed,
                  success=False, error=str(exc))
        return {"connected": False, "host": client.host, "error": f"Timeout: {exc}"}

    except FacialAuthenticationError as exc:
        elapsed = (time.monotonic() - start) * 1000
        _update_device_status(db, online=False, error=str(exc))
        return {"connected": False, "host": client.host, "error": f"Autenticação: {exc}"}

    except Exception as exc:
        elapsed = (time.monotonic() - start) * 1000
        _update_device_status(db, online=False, error=str(exc))
        return {"connected": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Processar fila de sincronização
# ---------------------------------------------------------------------------

def process_sync_queue(db: Session, client: FacialClient) -> dict:
    """
    Processa entradas PENDING/ERROR da sync_queue.
    Retorna {"processed": int, "success": int, "errors": int}.
    """
    processed = success = errors = 0

    pending = (
        db.query(SyncQueue)
        .filter(SyncQueue.status.in_(["PENDING", "ERROR"]))
        .filter(SyncQueue.attempts < 5)       # desiste após 5 tentativas
        .order_by(SyncQueue.created_at.asc())
        .limit(50)
        .all()
    )

    for item in pending:
        processed += 1
        item.status = "PROCESSING"
        item.attempts += 1
        db.commit()

        try:
            payload = json.loads(item.payload) if item.payload else {}
            result = _dispatch_queue_item(client, item.entity_type, item.operation, payload)

            # Verifica código de sucesso do device
            if isinstance(result, dict):
                code = result.get("code", 200)
                res_result = result.get("result", 0)
                if code not in (0, 200) and res_result != 0:
                    raise FacialApiError(result.get("message", "Erro desconhecido"), body=result)

            item.status = "SUCCESS"
            item.synced_at = datetime.now(timezone.utc)
            item.last_error = None

            # Atualiza status do funcionário se for operação de employee
            if item.entity_type == "employee" and item.entity_id:
                _mark_employee_synced(db, item.entity_id)

            success += 1
            logger.info("Queue processada: %s %s %s → SUCCESS", item.entity_type, item.operation, item.entity_id)

        except NotImplementedError as exc:
            item.status = "ERROR"
            item.last_error = f"Rota não validada: {exc}"
            errors += 1
            logger.warning("Operação não suportada na fila: %s", exc)

        except (FacialOfflineError, FacialTimeoutError) as exc:
            item.status = "ERROR"
            item.last_error = str(exc)
            errors += 1
            logger.warning("Device offline ao processar fila: %s", exc)
            break   # não adianta continuar se está offline

        except FacialApiError as exc:
            item.status = "ERROR"
            item.last_error = str(exc)
            errors += 1
            logger.error("Erro da API ao processar fila: %s", exc)

        except Exception as exc:
            item.status = "ERROR"
            item.last_error = str(exc)
            errors += 1
            logger.exception("Erro inesperado ao processar fila item id=%s", item.id)

        db.commit()

    return {"processed": processed, "success": success, "errors": errors}


def _dispatch_queue_item(client: FacialClient, entity_type: str, operation: str, payload: dict) -> dict:
    if entity_type == "employee":
        if operation == "INSERT":
            return client.insert_employee(payload)
        if operation == "UPDATE":
            return client.update_employee(payload)
    raise FacialApiError(f"Operação desconhecida na fila: {entity_type}/{operation}")


def _mark_employee_synced(db: Session, userid: str):
    from app.database.models import Employee
    emp = db.query(Employee).filter(Employee.userid == userid).first()
    if emp:
        emp.device_synced = True
        emp.sync_status = "SUCCESS"
        emp.last_synced_at = datetime.now(timezone.utc)
        db.commit()


# ---------------------------------------------------------------------------
# Ciclo principal de sincronização
# ---------------------------------------------------------------------------

async def _sync_cycle():
    """Executa um ciclo completo de sincronização."""
    db = SessionLocal()
    started = datetime.now(timezone.utc)
    sync_log = SyncLog(started_at=started)
    db.add(sync_log)
    db.commit()

    emp_synced = att_synced = err_count = 0

    try:
        client = _build_client(db)
        if not client:
            sync_log.success = False
            sync_log.summary = "Configurações incompletas"
            db.commit()
            return

        # 1. Testar conexão
        start = time.monotonic()
        try:
            client.get_device_auth()
            elapsed = (time.monotonic() - start) * 1000
            _update_device_status(db, online=True, response_time=elapsed)
        except (FacialOfflineError, FacialTimeoutError, FacialAuthenticationError) as exc:
            _update_device_status(db, online=False, error=str(exc))
            sync_log.success = False
            sync_log.summary = f"Device offline: {exc}"
            sync_log.finished_at = datetime.now(timezone.utc)
            db.commit()
            logger.warning("Ciclo abortado — device offline: %s", exc)
            return

        # 2. Processar fila de pendências
        sync_employees = _get_setting(db, "sync_employees", "true") == "true"
        if sync_employees:
            queue_result = process_sync_queue(db, client)
            emp_synced += queue_result["success"]
            err_count += queue_result["errors"]

            # 3. Importar funcionários do device
            import_result = import_from_device(db, client)
            emp_synced += import_result["updated"]

        # 4. Polling de presença
        # Usa getWorkNoteList (type=2) como fonte principal — retorna passagens individuais
        # com checkin_time completo. Se retornar vazio, tenta getAttendTable como fallback.
        sync_attendance = _get_setting(db, "sync_attendance", "true") == "true"
        if sync_attendance:
            today   = date.today()
            start_d = format_date_for_device(today.replace(day=1))
            end_d   = format_date_for_device(today)

            # Fonte primária: /getWorkNoteList
            att_result = poll_work_note(db, client, start_d, end_d, record_type=2)
            att_synced += att_result["new_records"]
            err_count  += len(att_result["errors"])

            # Fallback: /getAttendTable (para devices que usam estrutura de turno)
            if att_result["new_records"] == 0 and not att_result["errors"]:
                att_result2 = poll_attendance(db, client, start_d, end_d)
                att_synced += att_result2["new_records"]
                err_count  += len(att_result2["errors"])

        sync_log.success = err_count == 0
        sync_log.employees_synced = emp_synced
        sync_log.attendance_synced = att_synced
        sync_log.errors_count = err_count
        sync_log.summary = (
            f"Funcionários: {emp_synced} | Marcações: {att_synced} | Erros: {err_count}"
        )

    except Exception as exc:
        sync_log.success = False
        sync_log.summary = f"Erro inesperado: {exc}"
        logger.exception("Erro inesperado no ciclo de sincronização")

    finally:
        sync_log.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.close()


# ---------------------------------------------------------------------------
# Controle do loop assíncrono
# ---------------------------------------------------------------------------

async def _sync_loop():
    global _running
    logger.info("Serviço de sincronização iniciado.")
    while _running:
        db = SessionLocal()
        try:
            interval = int(_get_setting(db, "sync_interval", "30"))
            auto = _get_setting(db, "sync_auto_enabled", "true") == "true"
        finally:
            db.close()

        if auto:
            try:
                await _sync_cycle()
            except Exception as exc:
                logger.exception("Falha crítica no ciclo de sincronização: %s", exc)
        else:
            logger.debug("Sincronização automática desativada.")

        await asyncio.sleep(interval)

    logger.info("Serviço de sincronização encerrado.")


def start_sync_service():
    """Inicia o loop de sincronização em background (chama do lifespan do FastAPI)."""
    global _sync_task, _running
    if _running:
        return
    _running = True
    loop = asyncio.get_event_loop()
    _sync_task = loop.create_task(_sync_loop())
    logger.info("Task de sincronização criada.")


def stop_sync_service():
    """Para o loop de sincronização (chama do shutdown do FastAPI)."""
    global _sync_task, _running
    _running = False
    if _sync_task and not _sync_task.done():
        _sync_task.cancel()
    logger.info("Task de sincronização cancelada.")


async def run_sync_now() -> dict:
    """Dispara um ciclo único imediatamente (usado pelo botão 'Sincronizar agora')."""
    await _sync_cycle()
    db = SessionLocal()
    try:
        last = db.query(SyncLog).order_by(SyncLog.id.desc()).first()
        if last:
            return {
                "success": last.success,
                "employees_synced": last.employees_synced,
                "attendance_synced": last.attendance_synced,
                "errors_count": last.errors_count,
                "summary": last.summary,
            }
        return {"success": False, "summary": "Sem log disponível"}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Helpers de status / log
# ---------------------------------------------------------------------------

def _update_device_status(
    db: Session,
    online: bool,
    response_time: float | None = None,
    error: str | None = None,
):
    status = db.query(DeviceStatus).first()
    if not status:
        status = DeviceStatus()
        db.add(status)

    status.online = online
    status.last_check = datetime.now(timezone.utc)
    if online:
        status.last_success = datetime.now(timezone.utc)
        status.response_time = response_time
        status.last_error = None
    else:
        status.last_error = error

    db.commit()


def _log_comm(
    db: Session,
    endpoint: str,
    status_code: int | None = None,
    duration_ms: float | None = None,
    success: bool = True,
    error: str | None = None,
    request_summary: str | None = None,
    response_summary: str | None = None,
):
    entry = ApplicationLog(
        level="INFO" if success else "ERROR",
        endpoint=endpoint,
        method="POST",
        status_code=status_code,
        duration_ms=duration_ms,
        success=success,
        error=error,
        request_summary=request_summary,
        response_summary=response_summary,
    )
    db.add(entry)
    db.commit()


def get_sync_status(db: Session) -> dict:
    """Retorna um resumo rápido do estado de sincronização para o dashboard."""
    from app.database.models import Employee

    device_status = db.query(DeviceStatus).first()
    last_log = db.query(SyncLog).order_by(SyncLog.id.desc()).first()
    pending_count = db.query(SyncQueue).filter(SyncQueue.status.in_(["PENDING", "ERROR"])).count()
    total_employees = db.query(Employee).count()
    synced_employees = db.query(Employee).filter(Employee.device_synced == True).count()

    return {
        "device_online": device_status.online if device_status else False,
        "device_response_time": device_status.response_time if device_status else None,
        "last_check": device_status.last_check.isoformat() if device_status and device_status.last_check else None,
        "last_success": device_status.last_success.isoformat() if device_status and device_status.last_success else None,
        "last_error": device_status.last_error if device_status else None,
        "pending_sync": pending_count,
        "total_employees": total_employees,
        "synced_employees": synced_employees,
        "last_sync_summary": last_log.summary if last_log else None,
        "last_sync_at": last_log.finished_at.isoformat() if last_log and last_log.finished_at else None,
        "sync_running": _running,
    }
