"""
AttendanceService — lógica de negócio para presença.

Obtém registros do ALPHA-1111 via /getAttendTable (relatório estruturado)
ou via /getWorkNoteList + /exportCheckinRecord (log bruto de passagens),
deduplica, salva no SQLite e os serve para o dashboard/relatórios.
"""
import json
import logging
import re
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.database.models import AttendanceRecord, Employee
from app.services.facial_client import (
    FacialClient,
    FacialOfflineError,
    FacialTimeoutError,
    FacialApiError,
)

logger = logging.getLogger("attendance_service")

# Horários nos campos shift_t1..shift_t6 que indicam presença real
_TIME_RE = re.compile(r"^\d{1,2}:\d{2}$")

# Mapeamento de passway → descrição legível (validado no HAR employee_note.js)
PASSWAY_LABELS = {
    "0": "Facial",
    "1": "Cartão",
    "2": "QR Code",
    "3": "Senha",
    "4": "ID",
    "5": "Health Code",
    "6": "Botão/Remoto",
    "7": "Digital",
    "8": "Palma",
    "10": "Facial+Cartão",
    "11": "Facial+Senha",
    "12": "Facial+Cartão/Senha",
    "13": "Facial+Digital",
    "14": "Facial+Palma",
    "15": "Cartão+Palma",
    "16": "Cartão+Senha",
    "17": "Cartão+Digital",
    "18": "Palma+Senha",
    "19": "Palma+Digital",
    "20": "Digital+Senha",
}


# ---------------------------------------------------------------------------
# Polling de presença do device → SQLite
# ---------------------------------------------------------------------------

def poll_attendance(
    db: Session,
    client: FacialClient,
    start_date: str,
    end_date: str,
) -> dict:
    """
    Consulta /getAttendTable e salva registros novos no banco.
    Formato de data esperado pela API: YYYY/MM/DD.

    Retorna: {"new_records": int, "errors": list[str]}
    """
    new_records = 0
    errors: list[str] = []

    try:
        result = client.get_attendance(start_date, end_date)
        employees_data = result.get("data", [])

        for emp_record in employees_data:
            userid = str(emp_record.get("userid", ""))
            emp_name = emp_record.get("employeeName", "")

            # Tenta preencher nome pelo banco local se vier vazio
            if not emp_name:
                local = db.query(Employee).filter(Employee.userid == userid).first()
                if local:
                    emp_name = local.name

            for day in emp_record.get("attendan", []):
                att_date_raw = day.get("attDate", "")  # ex: "09-22"
                if not att_date_raw:
                    continue

                # Extrai ano do range da resposta quando disponível
                year = _extract_year(emp_record, start_date)
                full_date = f"{year}-{att_date_raw}"  # YYYY-MM-DD

                # Coleta horários registrados (shift_t1..shift_t6)
                times = []
                for i in range(1, 7):
                    t = day.get(f"shift_t{i}", "").strip()
                    if t and _TIME_RE.match(t):
                        times.append(t)

                for idx, t in enumerate(times):
                    # Tipo alternado: índice par = ENTRADA, ímpar = SAÍDA
                    record_type = "ENTRY" if idx % 2 == 0 else "EXIT"
                    time_str = f"{t}:00"  # HH:MM → HH:MM:SS
                    dedup = f"{userid}_{full_date}_{t}"

                    exists = db.query(AttendanceRecord).filter(
                        AttendanceRecord.dedup_key == dedup
                    ).first()

                    if not exists:
                        rec = AttendanceRecord(
                            userid=userid,
                            employee_name=emp_name,
                            attendance_date=full_date,
                            attendance_time=time_str,
                            record_type=record_type,
                            raw_data=json.dumps(day, ensure_ascii=False),
                            source="DEVICE",
                            dedup_key=dedup,
                        )
                        db.add(rec)
                        new_records += 1

        db.commit()
        logger.info("Poll de presença: %d novos registros (%s → %s)", new_records, start_date, end_date)

    except (FacialOfflineError, FacialTimeoutError) as exc:
        errors.append(f"Device offline: {exc}")
        logger.warning("Device offline durante poll de presença: %s", exc)
    except FacialApiError as exc:
        errors.append(f"API error: {exc}")
        logger.error("Erro da API no poll de presença: %s", exc)
    except Exception as exc:
        errors.append(f"Erro inesperado: {exc}")
        logger.exception("Erro inesperado no poll de presença")

    return {"new_records": new_records, "errors": errors}


# ---------------------------------------------------------------------------
# Coleta via log bruto — /getWorkNoteList (mais simples, sem estrutura de turno)
# ---------------------------------------------------------------------------

def poll_work_note(
    db: Session,
    client: FacialClient,
    start_date: str | None = None,
    end_date: str | None = None,
    record_type: int = 2,
) -> dict:
    """
    Coleta registros brutos via /getWorkNoteList e persiste no banco.

    Diferença em relação a poll_attendance (/getAttendTable):
      - Retorna registros individuais com checkin_time completo (YYYY-MM-DD HH:MM:SS)
      - Não tem estrutura de turno — cada linha é uma passagem
      - type=2 = funcionários cadastrados; type=1 = desconhecidos

    Campos do device:
      userid, name, ispass, passway, cardnum, score, checkin_time, temp

    Parâmetros:
      start_date  — "YYYY/MM/DD" (None = sem filtro)
      end_date    — "YYYY/MM/DD" (None = sem filtro)
      record_type — 1=desconhecidos, 2=funcionários (default)
    """
    new_records = 0
    errors: list[str] = []

    try:
        result = client.get_work_note_list(
            record_type=record_type,
            start_time=start_date,
            end_time=end_date,
        )

        if result.get("code") != 200:
            errors.append(f"getWorkNoteList retornou code={result.get('code')}: {result.get('message', '')}")
            return {"new_records": 0, "errors": errors}

        records = result.get("data", [])
        saved = _persist_work_note_records(db, records, fallback_start=start_date)
        new_records = saved

        logger.info(
            "poll_work_note (type=%d): %d registros do device, %d novos salvos",
            record_type, len(records), new_records,
        )

    except (FacialOfflineError, FacialTimeoutError) as exc:
        errors.append(f"Device offline: {exc}")
        logger.warning("Device offline durante poll_work_note: %s", exc)
    except FacialApiError as exc:
        errors.append(f"API error: {exc}")
        logger.error("Erro da API em poll_work_note: %s", exc)
    except Exception as exc:
        errors.append(f"Erro inesperado: {exc}")
        logger.exception("Erro inesperado em poll_work_note")

    return {"new_records": new_records, "errors": errors}


def bulk_export_checkin(
    db: Session,
    client: FacialClient,
    start_date: str | None = None,
    end_date: str | None = None,
    record_type: int = 2,
    page_size: int = 100,
) -> dict:
    """
    Exporta todos os registros brutos via /exportCheckinRecord em páginas.

    Fluxo:
      1. Chama getWorkNoteList para descobrir o total
      2. Divide em lotes de page_size (máx 100 recomendado pelo JS do device)
      3. Chama exportCheckinRecord para cada lote
      4. Persiste registros novos no banco

    Parâmetros:
      start_date  — "YYYY/MM/DD"
      end_date    — "YYYY/MM/DD"
      record_type — 1=desconhecidos, 2=funcionários
      page_size   — registros por chamada (default 100)
    """
    new_records = 0
    errors: list[str] = []
    total_fetched = 0

    try:
        # 1. Descobre o total
        count_result = client.get_work_note_list(
            record_type=record_type,
            start_time=start_date,
            end_time=end_date,
        )
        if count_result.get("code") != 200:
            errors.append(f"Falha ao obter total: code={count_result.get('code')}")
            return {"new_records": 0, "total_fetched": 0, "errors": errors}

        total = count_result.get("total", 0)
        if total == 0:
            logger.info("bulk_export_checkin: sem registros no período")
            return {"new_records": 0, "total_fetched": 0, "errors": errors}

        import math
        total_calls = math.ceil(total / page_size)

        logger.info(
            "bulk_export_checkin: %d registros em %d chamadas (type=%d, %s→%s)",
            total, total_calls, record_type, start_date, end_date,
        )

        # 2. Pagina via exportCheckinRecord
        for page in range(1, total_calls + 1):
            start_idx = (page - 1) * page_size + 1
            end_idx   = min(page * page_size, total)

            try:
                batch = client.export_checkin_record(
                    record_type=record_type,
                    start_time=start_date,
                    end_time=end_date,
                    start_index=start_idx,
                    end_index=end_idx,
                    current_call=page,
                    total_call=total_calls,
                )
                if batch.get("code") != 200:
                    errors.append(
                        f"exportCheckinRecord página {page}: code={batch.get('code')}"
                    )
                    continue

                records = batch.get("data", [])
                total_fetched += len(records)
                saved = _persist_work_note_records(db, records, fallback_start=start_date)
                new_records += saved

            except (FacialOfflineError, FacialTimeoutError) as exc:
                errors.append(f"Página {page}: device offline — {exc}")
                logger.warning("bulk_export_checkin página %d: device offline", page)
                break   # não tem sentido continuar
            except FacialApiError as exc:
                errors.append(f"Página {page}: API error — {exc}")
                logger.error("bulk_export_checkin página %d: API error: %s", page, exc)

        logger.info(
            "bulk_export_checkin concluído: %d buscados, %d novos, %d erros",
            total_fetched, new_records, len(errors),
        )

    except (FacialOfflineError, FacialTimeoutError) as exc:
        errors.append(f"Device offline ao buscar total: {exc}")
        logger.warning("bulk_export_checkin: device offline: %s", exc)
    except FacialApiError as exc:
        errors.append(f"API error ao buscar total: {exc}")
        logger.error("bulk_export_checkin: API error: %s", exc)
    except Exception as exc:
        errors.append(f"Erro inesperado: {exc}")
        logger.exception("Erro inesperado em bulk_export_checkin")

    return {"new_records": new_records, "total_fetched": total_fetched, "errors": errors}


def _persist_work_note_records(
    db: Session,
    records: list[dict],
    fallback_start: str | None = None,
) -> int:
    """
    Persiste lista de registros do formato /getWorkNoteList ou /exportCheckinRecord.

    Formato esperado por registro:
      {
        "userid":       "1",
        "name":         "João",
        "ispass":       1,
        "passway":      "0",
        "cardnum":      "",
        "score":        89,
        "checkin_time": "2026-09-23 21:41:41",
        "temp":         ""
      }
    """
    new_count = 0

    for rec in records:
        checkin_time_raw = rec.get("checkin_time", "")
        if not checkin_time_raw:
            continue

        # Parseia "YYYY-MM-DD HH:MM:SS"
        try:
            dt = datetime.strptime(checkin_time_raw.strip(), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            logger.debug("checkin_time inválido ignorado: %r", checkin_time_raw)
            continue

        att_date = dt.strftime("%Y-%m-%d")
        att_time = dt.strftime("%H:%M:%S")

        userid = str(rec.get("userid", "")).strip()
        if not userid:
            continue

        # Tenta preencher nome pelo banco local se vier vazio
        emp_name = rec.get("name", "").strip()
        if not emp_name and userid != "-1":
            local = db.query(Employee).filter(Employee.userid == userid).first()
            if local:
                emp_name = local.name

        # Dedup por userid + data + hora exata
        dedup = f"wn_{userid}_{att_date}_{att_time}"

        exists = db.query(AttendanceRecord).filter(
            AttendanceRecord.dedup_key == dedup
        ).first()

        if not exists:
            # Lógica de alternância ENTRADA/SAÍDA por paridade:
            # conta quantas batidas o funcionário já tem neste dia.
            # 0 batidas anteriores → esta é ENTRADA (índice 0, par)
            # 1 batida anterior    → esta é SAÍDA   (índice 1, ímpar)
            # 2 batidas anteriores → esta é ENTRADA (índice 2, par)  etc.
            count_today = db.query(AttendanceRecord).filter(
                AttendanceRecord.userid      == userid,
                AttendanceRecord.attendance_date == att_date,
            ).count()

            if str(rec.get("ispass")) == "1":
                record_type = "ENTRY" if count_today % 2 == 0 else "EXIT"
            else:
                # ispass=0 → batida não autorizada (desconhecido, acesso negado)
                record_type = "UNKNOWN"

            db.add(AttendanceRecord(
                userid=userid,
                employee_name=emp_name,
                attendance_date=att_date,
                attendance_time=att_time,
                record_type=record_type,
                raw_data=json.dumps(rec, ensure_ascii=False),
                source="DEVICE",
                dedup_key=dedup,
            ))
            new_count += 1

    db.commit()
    return new_count


# ---------------------------------------------------------------------------
# Recalcula ENTRY/EXIT dos registros já salvos (corrige importações antigas)
# ---------------------------------------------------------------------------

def recalculate_record_types(db: Session) -> dict:
    """
    Recalcula o tipo (ENTRY/EXIT) de todos os registros existentes no banco
    que vieram do device (source=DEVICE) e têm ispass=1.

    Lógica: por funcionário × dia, ordena por horário e aplica alternância:
      1ª batida = ENTRY, 2ª = EXIT, 3ª = ENTRY ...

    Retorna: {"updated": int, "skipped": int}
    """
    updated = 0
    skipped = 0

    # Agrupa por userid + attendance_date
    from sqlalchemy import func as sqlfunc
    pairs = (
        db.query(
            AttendanceRecord.userid,
            AttendanceRecord.attendance_date,
        )
        .filter(AttendanceRecord.source == "DEVICE")
        .distinct()
        .all()
    )

    for userid, att_date in pairs:
        records = (
            db.query(AttendanceRecord)
            .filter(
                AttendanceRecord.userid == userid,
                AttendanceRecord.attendance_date == att_date,
                AttendanceRecord.source == "DEVICE",
            )
            .order_by(AttendanceRecord.attendance_time.asc())
            .all()
        )

        for idx, rec in enumerate(records):
            if rec.record_type == "UNKNOWN":
                skipped += 1
                continue
            expected = "ENTRY" if idx % 2 == 0 else "EXIT"
            if rec.record_type != expected:
                rec.record_type = expected
                updated += 1

    db.commit()
    logger.info("recalculate_record_types: %d atualizados, %d ignorados", updated, skipped)
    return {"updated": updated, "skipped": skipped}

def list_attendance(
    db: Session,
    page: int = 1,
    page_size: int = 50,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    userid: Optional[str] = None,
    record_type: Optional[str] = None,
) -> dict:
    query = db.query(AttendanceRecord)

    if start_date:
        query = query.filter(AttendanceRecord.attendance_date >= start_date)
    if end_date:
        query = query.filter(AttendanceRecord.attendance_date <= end_date)
    if userid:
        query = query.filter(AttendanceRecord.userid == userid)
    if record_type:
        query = query.filter(AttendanceRecord.record_type == record_type)

    total = query.count()
    items = (
        query.order_by(
            AttendanceRecord.attendance_date.desc(),
            AttendanceRecord.attendance_time.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    pages = max(1, (total + page_size - 1) // page_size)

    return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": pages}


def get_today_records(db: Session) -> list[AttendanceRecord]:
    today = date.today().isoformat()
    return (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.attendance_date == today)
        .order_by(AttendanceRecord.attendance_time.asc())
        .all()
    )


def get_today_status(db: Session) -> list[dict]:
    """
    Retorna quem passou pelo facial hoje, cruzado com a lista local.
    Não inventa presença — baseia-se apenas nos registros persistidos.
    """
    today = date.today().isoformat()

    # Registros de hoje agrupados por userid
    records = get_today_records(db)
    passed: dict[str, str] = {}
    for r in records:
        # Mantém o horário mais recente
        if r.userid not in passed or r.attendance_time > passed[r.userid]:
            passed[r.userid] = r.attendance_time

    # Todos os funcionários locais
    employees = db.query(Employee).order_by(Employee.name).all()

    status_list = []
    for emp in employees:
        uid = emp.userid
        if uid in passed:
            status_list.append({
                "userid": uid,
                "name": emp.name or uid,
                "passed": True,
                "last_time": passed[uid][:5],  # HH:MM
            })
        else:
            status_list.append({
                "userid": uid,
                "name": emp.name or uid,
                "passed": False,
                "last_time": None,
            })

    # Ordena: quem passou primeiro, depois quem não passou
    status_list.sort(key=lambda x: (not x["passed"], x["last_time"] or "99:99"))
    return status_list


def get_recent_records(db: Session, limit: int = 20) -> list[AttendanceRecord]:
    return (
        db.query(AttendanceRecord)
        .order_by(
            AttendanceRecord.attendance_date.desc(),
            AttendanceRecord.attendance_time.desc(),
        )
        .limit(limit)
        .all()
    )


def count_today(db: Session) -> int:
    today = date.today().isoformat()
    return db.query(AttendanceRecord).filter(
        AttendanceRecord.attendance_date == today
    ).count()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_year(emp_record: dict, fallback_start: str) -> str:
    """Tenta extrair o ano do campo dateRange ou da data de início do filtro."""
    date_range = emp_record.get("dateRange", {})
    start = date_range.get("start", "")
    if start and len(start) >= 4:
        return start[:4]
    # fallback_start está em formato YYYY/MM/DD ou YYYY-MM-DD
    if fallback_start and len(fallback_start) >= 4:
        return fallback_start[:4]
    return str(date.today().year)


def format_date_for_device(d: date) -> str:
    """Converte date Python para o formato YYYY/MM/DD esperado pela API."""
    return d.strftime("%Y/%m/%d")
