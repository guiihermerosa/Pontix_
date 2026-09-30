"""
Rotas de Sincronização — controle manual do SyncService e fila.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import SyncLog, SyncQueue
from app.services.sync_service import get_sync_status, run_sync_now

router = APIRouter()
from app.templates_config import templates


@router.get("/api/sync")
async def sync_status(db: Session = Depends(get_db)):
    return get_sync_status(db)


@router.post("/api/sync/run")
async def sync_now():
    """Dispara um ciclo completo de sincronização imediatamente."""
    result = await run_sync_now()
    return result


@router.get("/api/sync/queue")
async def get_queue(
    page: int = 1,
    page_size: int = 50,
    status: str = None,
    db: Session = Depends(get_db),
):
    query = db.query(SyncQueue)
    if status:
        query = query.filter(SyncQueue.status == status.upper())
    total = query.count()
    items = (
        query.order_by(SyncQueue.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    pages = max(1, (total + page_size - 1) // page_size)
    return {
        "items": [
            {
                "id": i.id,
                "entity_type": i.entity_type,
                "entity_id": i.entity_id,
                "operation": i.operation,
                "status": i.status,
                "attempts": i.attempts,
                "last_error": i.last_error,
                "created_at": i.created_at.isoformat() if i.created_at else None,
                "synced_at": i.synced_at.isoformat() if i.synced_at else None,
            }
            for i in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.get("/api/sync/logs")
async def get_sync_logs(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    total = db.query(SyncLog).count()
    items = (
        db.query(SyncLog)
        .order_by(SyncLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    pages = max(1, (total + page_size - 1) // page_size)
    return {
        "items": [
            {
                "id": log.id,
                "started_at": log.started_at.isoformat() if log.started_at else None,
                "finished_at": log.finished_at.isoformat() if log.finished_at else None,
                "success": log.success,
                "employees_synced": log.employees_synced,
                "attendance_synced": log.attendance_synced,
                "errors_count": log.errors_count,
                "summary": log.summary,
            }
            for log in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }
