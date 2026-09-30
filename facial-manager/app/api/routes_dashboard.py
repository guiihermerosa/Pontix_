"""
Rotas do Dashboard — dados para a tela principal.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import ApplicationLog, SyncLog
from app.services.attendance_service import count_today, get_recent_records, get_today_status
from app.services.sync_service import get_sync_status

router = APIRouter()
from app.templates_config import templates


@router.get("/")
async def dashboard_page(request: Request, db: Session = Depends(get_db)):
    status = get_sync_status(db)
    today_status = get_today_status(db)
    recent = get_recent_records(db, limit=20)
    today_count = count_today(db)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "status": status,
        "today_status": today_status,
        "recent_records": recent,
        "today_count": today_count,
        "active_page": "dashboard",
    })


@router.get("/api/dashboard")
async def dashboard_api(db: Session = Depends(get_db)):
    status = get_sync_status(db)
    today_status = get_today_status(db)
    recent = get_recent_records(db, limit=20)
    today_count = count_today(db)

    return {
        "sync_status": status,
        "today_count": today_count,
        "today_status": today_status,
        "recent_records": [
            {
                "userid": r.userid,
                "employee_name": r.employee_name,
                "attendance_date": r.attendance_date,
                "attendance_time": r.attendance_time,
                "record_type": r.record_type,
            }
            for r in recent
        ],
    }


@router.get("/api/device/status")
async def device_status(db: Session = Depends(get_db)):
    return get_sync_status(db)


@router.get("/api/logs")
async def get_logs(
    page: int = 1,
    page_size: int = 50,
    level: str = None,
    db: Session = Depends(get_db),
):
    query = db.query(ApplicationLog)
    if level:
        query = query.filter(ApplicationLog.level == level.upper())
    total = query.count()
    items = (
        query.order_by(ApplicationLog.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    pages = max(1, (total + page_size - 1) // page_size)
    return {
        "items": [
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "level": log.level,
                "endpoint": log.endpoint,
                "status_code": log.status_code,
                "duration_ms": log.duration_ms,
                "success": log.success,
                "error": log.error,
                "message": log.message,
            }
            for log in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }
