"""
Rotas de Presença — consultas, polling manual e exportação.
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.services.attendance_service import (
    PASSWAY_LABELS,
    bulk_export_checkin,
    count_today,
    format_date_for_device,
    get_recent_records,
    get_today_records,
    get_today_status,
    list_attendance,
    poll_attendance,
    poll_work_note,
    recalculate_record_types,
)
from app.services.export_service import (
    export_attendance_csv,
    export_attendance_xlsx,
    export_employee_xlsx,
)
from app.services.sync_service import _build_client

router = APIRouter()
from app.templates_config import templates


# ---------------------------------------------------------------------------
# Página HTML
# ---------------------------------------------------------------------------

@router.get("/presenca")
async def attendance_page(request: Request, db: Session = Depends(get_db)):
    today = date.today().isoformat()
    result = list_attendance(db, page=1, page_size=50, start_date=today, end_date=today)
    today_status = get_today_status(db)
    return templates.TemplateResponse("attendance.html", {
        "request": request,
        "attendance": result["items"],
        "pagination": result,
        "today_status": today_status,
        "today": today,
        "active_page": "attendance",
    })


# ---------------------------------------------------------------------------
# API JSON
# ---------------------------------------------------------------------------

@router.get("/api/attendance")
async def list_attendance_api(
    page: int = 1,
    page_size: int = 50,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    userid: Optional[str] = None,
    record_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    result = list_attendance(
        db,
        page=page,
        page_size=page_size,
        start_date=start_date,
        end_date=end_date,
        userid=userid,
        record_type=record_type,
    )
    return {
        "items": [_serialize(r) for r in result["items"]],
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
        "pages": result["pages"],
    }


@router.get("/api/attendance/today")
async def today_attendance(db: Session = Depends(get_db)):
    records = get_today_records(db)
    today_status = get_today_status(db)
    return {
        "date": date.today().isoformat(),
        "total": len(records),
        "records": [_serialize(r) for r in records],
        "status": today_status,
    }


@router.post("/api/attendance/poll")
async def manual_poll(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Dispara polling manual de presença para o período informado.
    Útil para buscar registros históricos sem aguardar o ciclo automático.
    """
    client = _build_client(db)
    if not client:
        return {"success": False, "error": "Device não configurado (host/senha ausentes)"}

    today = date.today()
    start = start_date or format_date_for_device(today.replace(day=1))
    end = end_date or format_date_for_device(today)

    # Usa getWorkNoteList como fonte principal (mais confiável neste device)
    result = poll_work_note(db, client, start, end, record_type=2)
    # Fallback para getAttendTable se não trouxer registros
    if result["new_records"] == 0 and not result["errors"]:
        result = poll_attendance(db, client, start, end)
    return {"success": len(result["errors"]) == 0, **result}
# ---------------------------------------------------------------------------

@router.post("/api/attendance/poll-work-note")
async def manual_poll_work_note(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    record_type: int = 2,
    db: Session = Depends(get_db),
):
    """
    Coleta registros brutos via /getWorkNoteList e persiste no banco.

    Parâmetros:
      start_date  — "YYYY/MM/DD" (None = sem filtro)
      end_date    — "YYYY/MM/DD" (None = sem filtro)
      record_type — 2=funcionários cadastrados (default), 1=desconhecidos/estranhos

    Diferença em relação a /api/attendance/poll:
      - Usa /getWorkNoteList em vez de /getAttendTable
      - Retorna passagens individuais com checkin_time, passway, score, ispass
      - Não requer estrutura de turno no device
    """
    client = _build_client(db)
    if not client:
        return {"success": False, "error": "Device não configurado (host/senha ausentes)"}

    today = date.today()
    start = start_date or format_date_for_device(today.replace(day=1))
    end   = end_date   or format_date_for_device(today)

    result = poll_work_note(db, client, start, end, record_type=record_type)
    return {"success": len(result["errors"]) == 0, **result}


@router.post("/api/attendance/bulk-export")
async def bulk_export(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    record_type: int = 2,
    page_size: int = 100,
    db: Session = Depends(get_db),
):
    """
    Exporta todos os registros do device via /exportCheckinRecord com paginação automática.

    Ideal para importações históricas grandes. O device é consultado em lotes
    de até `page_size` registros (máximo recomendado: 100).

    Parâmetros:
      start_date  — "YYYY/MM/DD"
      end_date    — "YYYY/MM/DD"
      record_type — 2=funcionários (default), 1=desconhecidos
      page_size   — registros por chamada ao device (default 100, máx recomendado)

    Retorna:
      { "success": bool, "new_records": int, "total_fetched": int, "errors": [...] }
    """
    client = _build_client(db)
    if not client:
        return {"success": False, "error": "Device não configurado (host/senha ausentes)"}

    today = date.today()
    start = start_date or format_date_for_device(today.replace(day=1))
    end   = end_date   or format_date_for_device(today)

    result = bulk_export_checkin(
        db, client, start, end,
        record_type=record_type,
        page_size=min(page_size, 100),  # protege contra valores acima do limite
    )
    return {"success": len(result["errors"]) == 0, **result}


@router.get("/api/attendance/passway-labels")
async def get_passway_labels():
    """
    Retorna o mapeamento de passway → descrição legível.
    Útil para o frontend exibir o tipo de passagem em português.
    """
    return PASSWAY_LABELS


@router.post("/api/attendance/recalculate-types")
async def recalculate_types(db: Session = Depends(get_db)):
    """
    Recalcula ENTRY/EXIT de todos os registros existentes no banco.

    Necessário quando registros antigos foram importados todos como ENTRY.
    Aplica a lógica de alternância: 1ª batida do dia = ENTRY, 2ª = EXIT, etc.
    """
    result = recalculate_record_types(db)
    return {"success": True, **result}


# ---------------------------------------------------------------------------
# Exportação
# ---------------------------------------------------------------------------

@router.get("/api/reports/attendance.xlsx")
async def export_xlsx(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    userid: Optional[str] = None,
    record_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    content = export_attendance_xlsx(db, start_date, end_date, userid, record_type)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=presenca.xlsx"},
    )


@router.get("/api/reports/attendance.csv")
async def export_csv(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    userid: Optional[str] = None,
    record_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    content = export_attendance_csv(db, start_date, end_date, userid, record_type)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=presenca.csv"},
    )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _serialize(r) -> dict:
    return {
        "id": r.id,
        "userid": r.userid,
        "employee_name": r.employee_name or "",
        "attendance_date": r.attendance_date,
        "attendance_time": r.attendance_time,
        "record_type": r.record_type,
        "source": r.source,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


@router.get("/api/reports/attendance/{userid}.xlsx")
async def export_employee_xlsx_route(
    userid: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Exporta XLSX individual de um funcionário (para contabilidade)."""
    content = export_employee_xlsx(db, userid, start_date, end_date)
    safe = userid.replace("/", "_").replace("\\", "_")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=ponto_{safe}.xlsx"},
    )
