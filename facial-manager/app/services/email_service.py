"""
EmailService — envio de relatórios via Resend.

Lógica de envio por tipo de destinatário:
  owner      → recebe 1 email com XLSX geral (todas as marcações + resumo + atestados)
  accounting → recebe 1 email POR FUNCIONÁRIO com o XLSX individual daquele funcionário
  other      → recebe o XLSX geral (mesmo que owner)

Agendamento mensal: gerenciado pelo APScheduler inicializado no main.py.
"""
import base64
import logging
from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Optional

import resend
from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.database.models import ApplicationLog, AttendanceRecord, EmailRecipient, Employee, Setting
from app.services.export_service import export_attendance_xlsx, export_employee_xlsx

logger = logging.getLogger("email_service")


# ---------------------------------------------------------------------------
# Helpers de configuração
# ---------------------------------------------------------------------------

def _get(db: Session, key: str, default: str = "") -> str:
    row = db.query(Setting).filter(Setting.key == key).first()
    return row.value if row and row.value else default


def _load_email_config(db: Session) -> dict:
    return {
        "api_key":      _get(db, "resend_api_key"),
        "from_email":   _get(db, "resend_from_email", "onboarding@resend.dev"),
        "from_name":    _get(db, "resend_from_name",  "Pontix"),
        "send_day":     int(_get(db, "email_send_day", "1")),
        "send_enabled": _get(db, "email_send_enabled", "true") == "true",
    }


def _load_company(db: Session) -> dict:
    return {
        "name":    _get(db, "company_name",    "Empresa"),
        "cnpj":    _get(db, "company_cnpj",    ""),
        "address": _get(db, "company_address", ""),
        "logo":    _get(db, "company_logo_b64", ""),
    }


def _from_addr(config: dict) -> str:
    name = config.get("from_name", "").strip()
    email = config.get("from_email", "onboarding@resend.dev").strip()
    return f"{name} <{email}>" if name else email


def _logo_attachment(company: dict, cid: str = "logo@pontix") -> tuple[dict | None, str]:
    """
    Prepara o logo como attachment inline CID.
    Retorna (attachment_dict | None, cid_para_html).
    """
    raw_logo = company.get("logo", "")
    if not raw_logo:
        return None, ""
    logo_b64_raw = ""
    logo_mime    = "image/png"
    if raw_logo.startswith("data:"):
        header, logo_b64_raw = raw_logo.split(",", 1)
        logo_mime = header.split(";")[0].replace("data:", "") or "image/png"
    else:
        logo_b64_raw = raw_logo
    if not logo_b64_raw:
        return None, ""
    attachment = {
        "filename":     f"logo.{logo_mime.split('/')[-1]}",
        "content":      logo_b64_raw,
        "content_id":   cid,
        "content_type": logo_mime,
    }
    return attachment, cid


# ---------------------------------------------------------------------------
# Template HTML — geral (para owner / other)
# ---------------------------------------------------------------------------

def _html_general(company: dict, period_label: str, recipients: list,
                  stats: dict, logo_cid: str = "") -> str:
    logo_html = (
        f'<img src="cid:{logo_cid}" alt="{company["name"]}" '
        f'style="max-height:60px;max-width:200px;object-fit:contain;"/>'
        if logo_cid else
        f'<span style="font-size:22px;font-weight:700;color:#fff;">{company["name"]}</span>'
    )
    greeting = ", ".join(r.name.split()[0] for r in recipients if r.name) or "prezado(a)"
    gen_time = datetime.now().strftime("%d/%m/%Y às %H:%M")

    def _card(bg, val, label):
        return f"""
        <td align="center" style="padding:0 8px;">
          <div style="background:{bg};border-radius:10px;padding:14px 10px;min-width:80px;">
            <div style="font-size:26px;font-weight:700;color:#1e3a6e;">{val}</div>
            <div style="font-size:10px;color:#6b7280;margin-top:4px;text-transform:uppercase;
                        letter-spacing:.5px;">{label}</div>
          </div>
        </td>"""

    cards = (
        _card("#EFF6FF", stats.get("employees", 0), "Funcionários") +
        _card("#ECFDF5", stats.get("entries",   0), "Entradas") +
        _card("#FFF7ED", stats.get("exits",     0), "Saídas") +
        _card("#F5F3FF", stats.get("total",     0), "Marcações") +
        _card("#F0FDF4", stats.get("certs",     0), "Atestados")
    )

    cnpj_line = f'<div style="color:#6b7280;font-size:12px;">CNPJ: {company["cnpj"]}</div>' if company.get("cnpj") else ""
    addr_line = f'<div style="color:#6b7280;font-size:12px;">{company["address"]}</div>' if company.get("address") else ""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Relatório de Ponto — {period_label}</title></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:'Segoe UI',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:32px 0;">
<tr><td align="center">
<table width="620" cellpadding="0" cellspacing="0"
       style="background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.09);">

  <!-- Header -->
  <tr><td style="background:linear-gradient(135deg,#0d2137 0%,#1a56db 100%);padding:28px 36px;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td>{logo_html}</td>
      <td align="right"><span style="background:rgba(255,255,255,.18);color:#fff;font-size:11px;
          padding:4px 12px;border-radius:20px;font-weight:600;">Relatório de Ponto</span></td>
    </tr></table>
  </td></tr>

  <!-- Período -->
  <tr><td style="background:#1a56db;padding:8px 36px;">
    <span style="color:#bfdbfe;font-size:12px;">Período:&nbsp;</span>
    <span style="color:#fff;font-size:13px;font-weight:600;">{period_label}</span>
    <span style="color:#bfdbfe;font-size:11px;float:right;margin-top:1px;">Gerado em {gen_time}</span>
  </td></tr>

  <!-- Corpo -->
  <tr><td style="padding:32px 36px;">
    <p style="margin:0 0 4px;font-size:15px;color:#111827;font-weight:600;">Olá, {greeting}!</p>
    <p style="margin:0 0 22px;font-size:13px;color:#4b5563;line-height:1.65;">
      Segue em anexo o <strong>relatório geral de controle de ponto</strong> referente ao período
      <strong>{period_label}</strong> de <strong>{company["name"]}</strong>.
      O arquivo <code style="background:#f3f4f6;padding:1px 5px;border-radius:3px;font-size:12px;">.xlsx</code>
      contém a capa executiva, resumo consolidado, todas as marcações e os atestados cadastrados.
    </p>
    <!-- Cards -->
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
      <tr>{cards}</tr>
    </table>
    <hr style="border:none;border-top:1px solid #e5e7eb;margin:0 0 18px;"/>
    <p style="margin:0;font-size:12px;color:#6b7280;line-height:1.6;">
      Em caso de dúvidas, entre em contato com o responsável pelo sistema.
    </p>
  </td></tr>

  <!-- Footer -->
  <tr><td style="background:#f9fafb;padding:18px 36px;border-top:1px solid #e5e7eb;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td>
        <div style="font-size:12px;font-weight:600;color:#374151;">{company["name"]}</div>
        {cnpj_line}{addr_line}
      </td>
      <td align="right" style="vertical-align:bottom;">
        <span style="font-size:10px;color:#9ca3af;">
          Enviado por <strong style="color:#6b7280;">Pontix</strong><br/>Feito por GRB Tecnologia
        </span>
      </td>
    </tr></table>
  </td></tr>

</table>
</td></tr></table>
</body></html>"""


# ---------------------------------------------------------------------------
# Template HTML — individual (para accounting, por funcionário)
# ---------------------------------------------------------------------------

def _html_individual(company: dict, period_label: str, recipient,
                     employee_name: str, stats_emp: dict,
                     logo_cid: str = "") -> str:
    logo_html = (
        f'<img src="cid:{logo_cid}" alt="{company["name"]}" '
        f'style="max-height:60px;max-width:200px;object-fit:contain;"/>'
        if logo_cid else
        f'<span style="font-size:22px;font-weight:700;color:#fff;">{company["name"]}</span>'
    )
    greeting = recipient.name.split()[0] if recipient.name else "prezado(a)"
    gen_time = datetime.now().strftime("%d/%m/%Y às %H:%M")

    def _kv(label, val, color="#EFF6FF", txt_color="#1e3a6e"):
        return f"""
        <tr>
          <td style="padding:8px 12px;font-size:12px;color:#6b7280;border-bottom:1px solid #f3f4f6;
                     background:#fff;font-weight:500;">{label}</td>
          <td style="padding:8px 12px;font-size:13px;color:{txt_color};font-weight:700;
                     background:{color};border-bottom:1px solid #f3f4f6;">{val}</td>
        </tr>"""

    sit_color = "#FEF2F2" if stats_emp.get("absences", 0) > stats_emp.get("justified", 0) else "#F0FDF4"
    sit_txt   = "#C81E1E"  if stats_emp.get("absences", 0) > stats_emp.get("justified", 0) else "#057A55"
    falta_val = (f"{stats_emp.get('absences', 0)} "
                 f"({stats_emp.get('justified', 0)} justif.)")

    cnpj_line = f'<div style="color:#6b7280;font-size:12px;">CNPJ: {company["cnpj"]}</div>' if company.get("cnpj") else ""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Ponto — {employee_name} — {period_label}</title></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:'Segoe UI',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:32px 0;">
<tr><td align="center">
<table width="580" cellpadding="0" cellspacing="0"
       style="background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.09);">

  <!-- Header -->
  <tr><td style="background:linear-gradient(135deg,#0d2137 0%,#0694a2 100%);padding:24px 32px;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td>{logo_html}</td>
      <td align="right"><span style="background:rgba(255,255,255,.18);color:#fff;font-size:11px;
          padding:4px 12px;border-radius:20px;font-weight:600;">Relatório Individual</span></td>
    </tr></table>
  </td></tr>

  <!-- Período -->
  <tr><td style="background:#0694a2;padding:7px 32px;">
    <span style="color:#a5f3fc;font-size:12px;">Funcionário:&nbsp;</span>
    <span style="color:#fff;font-size:13px;font-weight:700;">{employee_name}</span>
    <span style="color:#a5f3fc;font-size:11px;float:right;margin-top:1px;">{period_label}</span>
  </td></tr>

  <!-- Corpo -->
  <tr><td style="padding:28px 32px;">
    <p style="margin:0 0 4px;font-size:15px;color:#111827;font-weight:600;">Olá, {greeting}!</p>
    <p style="margin:0 0 20px;font-size:13px;color:#4b5563;line-height:1.65;">
      Segue o relatório de ponto de <strong>{employee_name}</strong> referente ao período
      <strong>{period_label}</strong>.
    </p>
    <!-- Tabela de resumo -->
    <table width="100%" cellpadding="0" cellspacing="0"
           style="border-radius:10px;overflow:hidden;border:1px solid #e5e7eb;margin-bottom:24px;">
      {_kv("Dias úteis no período", stats_emp.get("work_days", "—"))}
      {_kv("Dias presentes",        stats_emp.get("present", "—"),    "#ECFDF5", "#057A55")}
      {_kv("Faltas",                falta_val,                         sit_color, sit_txt)}
      {_kv("Entradas registradas",  stats_emp.get("entries", "—"))}
      {_kv("Saídas registradas",    stats_emp.get("exits", "—"))}
      {_kv("Horas trabalhadas (est.)", stats_emp.get("hours_str", "—"))}
      {_kv("Atestados médicos",     stats_emp.get("certs", "—"),       "#F0FDFA", "#0694a2")}
    </table>
    <p style="margin:0;font-size:12px;color:#6b7280;line-height:1.6;">
      O arquivo <code style="background:#f3f4f6;padding:1px 5px;border-radius:3px;">.xlsx</code>
      em anexo contém o detalhamento completo das marcações e os atestados cadastrados.
    </p>
  </td></tr>

  <!-- Footer -->
  <tr><td style="background:#f9fafb;padding:16px 32px;border-top:1px solid #e5e7eb;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td>
        <div style="font-size:12px;font-weight:600;color:#374151;">{company["name"]}</div>
        {cnpj_line}
      </td>
      <td align="right" style="vertical-align:bottom;">
        <span style="font-size:10px;color:#9ca3af;">
          Gerado em {gen_time}<br/>Pontix · GRB Tecnologia
        </span>
      </td>
    </tr></table>
  </td></tr>

</table>
</td></tr></table>
</body></html>"""


# ---------------------------------------------------------------------------
# Envio principal
# ---------------------------------------------------------------------------

def send_monthly_report(
    db: Session,
    year: Optional[int] = None,
    month: Optional[int] = None,
    force_recipients: Optional[list[str]] = None,
) -> dict:
    """
    Gera e envia relatórios mensais via Resend.

    Lógica por tipo de destinatário:
      owner / other → 1 email com XLSX geral (Capa + Resumo + Marcações + Atestados)
      accounting    → 1 email POR FUNCIONÁRIO com XLSX individual daquele funcionário

    Retorna:
      {"success": bool, "sent_to": [...], "errors": [...], "message": str}
    """
    config = _load_email_config(db)
    if not config["api_key"]:
        return {"success": False, "sent_to": [], "errors": ["API key do Resend não configurada."]}

    # Período
    today = date.today()
    if not year or not month:
        last_month = today.replace(day=1) - timedelta(days=1)
        year, month = last_month.year, last_month.month

    _, last_day   = monthrange(year, month)
    start_date    = f"{year}-{month:02d}-01"
    end_date      = f"{year}-{month:02d}-{last_day:02d}"
    period_label  = f"{month:02d}/{year}"

    # Destinatários
    if force_recipients:
        recipients = [
            type("R", (), {"name": e.split("@")[0], "email": e, "role": "owner"})()
            for e in force_recipients
        ]
    else:
        recipients = (
            db.query(EmailRecipient)
            .filter(EmailRecipient.active == True)
            .order_by(EmailRecipient.name)
            .all()
        )

    if not recipients:
        return {"success": False, "sent_to": [], "errors": ["Nenhum destinatário ativo."]}

    # Separa por role
    owners       = [r for r in recipients if r.role in ("owner", "other")]
    accountings  = [r for r in recipients if r.role == "accounting"]

    resend.api_key = config["api_key"]
    from_addr      = _from_addr(config)
    company        = _load_company(db)
    logo_att, logo_cid = _logo_attachment(company)

    sent_to: list[str] = []
    errors:  list[str] = []

    # ── Envio para OWNERS: XLSX geral ─────────────────────────────────────
    if owners:
        try:
            xlsx_geral = export_attendance_xlsx(db, start_date=start_date, end_date=end_date)
        except Exception as exc:
            logger.exception("Erro ao gerar XLSX geral")
            errors.append(f"Erro ao gerar XLSX geral: {exc}")
            xlsx_geral = None

        if xlsx_geral:
            stats = _calc_stats_general(db, start_date, end_date)
            xlsx_b64 = base64.b64encode(xlsx_geral).decode()
            filename = f"relatorio_ponto_{year}_{month:02d}.xlsx"

            for recipient in owners:
                html_body = _html_general(company, period_label,
                                          [recipient], stats, logo_cid)
                attachments = []
                if logo_att: attachments.append(logo_att)
                attachments.append({"filename": filename, "content": xlsx_b64})

                try:
                    result = resend.Emails.send({
                        "from":        from_addr,
                        "to":          [recipient.email],
                        "subject":     f"Relatório de Ponto — {company['name']} — {period_label}",
                        "html":        html_body,
                        "attachments": attachments,
                    })
                    sent_to.append(recipient.email)
                    logger.info("Email geral → %s (id=%s)", recipient.email, result.get("id"))
                except Exception as exc:
                    err = _translate_resend_error(str(exc))
                    errors.append(f"{recipient.email}: {err}")
                    logger.error("Falha email geral → %s: %s", recipient.email, exc)

    # ── Envio para ACCOUNTING: XLSX individual por funcionário ────────────
    if accountings:
        employees = db.query(Employee).order_by(Employee.name).all()

        for emp in employees:
            try:
                xlsx_emp = export_employee_xlsx(
                    db, emp.userid,
                    start_date=start_date,
                    end_date=end_date,
                )
            except Exception as exc:
                logger.error("Erro XLSX individual %s: %s", emp.userid, exc)
                errors.append(f"XLSX de {emp.name or emp.userid}: {exc}")
                continue

            stats_emp  = _calc_stats_employee(db, emp.userid, start_date, end_date)
            xlsx_b64   = base64.b64encode(xlsx_emp).decode()
            safe_name  = (emp.name or emp.userid).replace(" ", "_")
            filename   = f"ponto_{safe_name}_{year}_{month:02d}.xlsx"

            for recipient in accountings:
                html_body = _html_individual(
                    company, period_label,
                    recipient, emp.name or emp.userid,
                    stats_emp, logo_cid,
                )
                attachments = []
                if logo_att: attachments.append(logo_att)
                attachments.append({"filename": filename, "content": xlsx_b64})

                try:
                    result = resend.Emails.send({
                        "from":        from_addr,
                        "to":          [recipient.email],
                        "subject":     (f"Ponto — {emp.name or emp.userid} — "
                                        f"{company['name']} — {period_label}"),
                        "html":        html_body,
                        "attachments": attachments,
                    })
                    key = f"{recipient.email}→{emp.userid}"
                    sent_to.append(key)
                    logger.info("Email individual %s → %s (id=%s)",
                                emp.userid, recipient.email, result.get("id"))
                except Exception as exc:
                    err = _translate_resend_error(str(exc))
                    errors.append(f"{recipient.email} / {emp.name}: {err}")
                    logger.error("Falha email individual %s → %s: %s",
                                 emp.userid, recipient.email, exc)

    _log_email(db, sent_to, errors, period_label)

    success = len(sent_to) > 0 and len(errors) == 0
    nb_emails = len(sent_to)
    return {
        "success":  success,
        "sent_to":  sent_to,
        "errors":   errors,
        "message":  (
            f"{nb_emails} email(s) enviado(s)." if nb_emails
            else "Nenhum email enviado."
        ),
    }


# ---------------------------------------------------------------------------
# Email de teste
# ---------------------------------------------------------------------------

def send_test_email(db: Session, test_email: str) -> dict:
    config  = _load_email_config(db)
    company = _load_company(db)

    if not config["api_key"]:
        return {"success": False, "error": "API key do Resend não configurada."}

    resend.api_key = config["api_key"]
    logo_att, logo_cid = _logo_attachment(company)

    stats_mock = {"employees": "—", "entries": "—", "exits": "—",
                  "total": "—", "certs": "—"}
    period     = f"TESTE — {datetime.now().strftime('%m/%Y')}"
    mock_r     = type("R", (), {"name": test_email.split("@")[0], "role": "owner"})()
    html_body  = _html_general(company, period, [mock_r], stats_mock, logo_cid)

    attachments = []
    if logo_att:
        attachments.append(logo_att)

    try:
        result = resend.Emails.send({
            "from":        _from_addr(config),
            "to":          [test_email],
            "subject":     f"[TESTE] Relatório de Ponto — {company['name']}",
            "html":        html_body,
            "attachments": attachments,
        })
        logger.info("Email de teste → %s (id=%s)", test_email, result.get("id"))
        return {"success": True,
                "message": f"Email de teste enviado para {test_email}.",
                "id": result.get("id")}
    except Exception as exc:
        error_msg = _translate_resend_error(str(exc))
        logger.error("Falha email teste → %s: %s", test_email, exc)
        return {"success": False, "error": error_msg}


# ---------------------------------------------------------------------------
# Agendador mensal
# ---------------------------------------------------------------------------

def schedule_monthly_email(scheduler, day: int = 1):
    job_id = "monthly_email_report"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    scheduler.add_job(
        _run_monthly_job,
        trigger="cron",
        day=day,
        hour=7,
        minute=0,
        id=job_id,
        name="Relatório mensal por email",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    logger.info("Job mensal de email agendado para o dia %d de cada mês às 07:00.", day)


def _run_monthly_job():
    db = SessionLocal()
    try:
        config = _load_email_config(db)
        if not config["send_enabled"]:
            logger.info("Envio automático desativado — pulando.")
            return
        result = send_monthly_report(db)
        logger.info("Job mensal: %s", result["message"])
    except Exception as exc:
        logger.exception("Erro no job mensal de email: %s", exc)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Helpers de estatísticas
# ---------------------------------------------------------------------------

def _calc_stats_general(db: Session, start_date: str, end_date: str) -> dict:
    from app.database.models import MedicalCertificate

    total   = db.query(AttendanceRecord).filter(
        AttendanceRecord.attendance_date >= start_date,
        AttendanceRecord.attendance_date <= end_date,
    ).count()
    entries = db.query(AttendanceRecord).filter(
        AttendanceRecord.attendance_date >= start_date,
        AttendanceRecord.attendance_date <= end_date,
        AttendanceRecord.record_type == "ENTRY",
    ).count()
    exits   = db.query(AttendanceRecord).filter(
        AttendanceRecord.attendance_date >= start_date,
        AttendanceRecord.attendance_date <= end_date,
        AttendanceRecord.record_type == "EXIT",
    ).count()
    emp_count = db.query(Employee).count()
    cert_count = db.query(MedicalCertificate).filter(
        MedicalCertificate.cert_date >= start_date,
        MedicalCertificate.cert_date <= end_date,
    ).count()
    return {"total": total, "entries": entries, "exits": exits,
            "employees": emp_count, "certs": cert_count}


def _calc_stats_employee(db: Session, userid: str, start_date: str, end_date: str) -> dict:
    from app.database.models import MedicalCertificate
    from datetime import datetime as _dt, timedelta as _td

    records = db.query(AttendanceRecord).filter(
        AttendanceRecord.userid == userid,
        AttendanceRecord.attendance_date >= start_date,
        AttendanceRecord.attendance_date <= end_date,
    ).all()

    certs = db.query(MedicalCertificate).filter(
        MedicalCertificate.userid == userid,
        MedicalCertificate.cert_date >= start_date,
        MedicalCertificate.cert_date <= end_date,
    ).all()

    # Dias úteis no período
    try:
        d0 = _dt.strptime(start_date, "%Y-%m-%d").date()
        d1 = _dt.strptime(end_date,   "%Y-%m-%d").date()
        work_days = sum(
            1 for i in range((d1 - d0).days + 1)
            if (d0 + _td(days=i)).weekday() < 5
        )
    except Exception:
        work_days = 0

    days_pres = len({r.attendance_date for r in records})
    entries   = sum(1 for r in records if r.record_type == "ENTRY")
    exits_    = sum(1 for r in records if r.record_type == "EXIT")

    # Horas estimadas
    from collections import defaultdict
    by_day: dict = defaultdict(list)
    for r in records:
        by_day[r.attendance_date].append(r)
    total_h = 0.0
    for day_recs in by_day.values():
        entr = sorted([r for r in day_recs if r.record_type == "ENTRY"], key=lambda x: x.attendance_time)
        exts = sorted([r for r in day_recs if r.record_type == "EXIT"],  key=lambda x: x.attendance_time)
        for i in range(min(len(entr), len(exts))):
            try:
                fmt = "%H:%M:%S"
                h = (_dt.strptime(exts[i].attendance_time, fmt) -
                     _dt.strptime(entr[i].attendance_time, fmt)).total_seconds() / 3600
                if h > 0:
                    total_h += h
            except Exception:
                pass

    # Faltas justificadas
    cert_dates: set[str] = set()
    for cert in certs:
        cd = _dt.strptime(cert.cert_date, "%Y-%m-%d").date()
        for i in range(cert.days_off):
            cert_dates.add((cd + _td(days=i)).isoformat())
    justified = len([d for d in cert_dates
                     if _dt.strptime(d, "%Y-%m-%d").weekday() < 5])
    absences  = max(0, work_days - days_pres)

    return {
        "work_days": work_days,
        "present":   days_pres,
        "absences":  absences,
        "justified": justified,
        "entries":   entries,
        "exits":     exits_,
        "hours_str": f"{total_h:.1f}h",
        "certs":     len(certs),
    }


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _translate_resend_error(msg: str) -> str:
    if "only send testing emails to your own email" in msg:
        return ("Remetente com domínio não verificado. "
                "Configure um email do seu domínio em Configurações → Integrações.")
    if "API key is invalid" in msg or "Unauthorized" in msg:
        return "API key inválida. Verifique em resend.com/api-keys."
    if "from address" in msg.lower():
        return "Email remetente inválido. Use um email do seu domínio verificado."
    return msg


def _log_email(db: Session, sent_to: list, errors: list, period: str):
    entry = ApplicationLog(
        level    = "INFO" if not errors else "ERROR",
        endpoint = "/email/send-report",
        method   = "POST",
        success  = len(sent_to) > 0,
        message  = f"Email relatório {period} → {sent_to} | erros: {errors}",
    )
    db.add(entry)
    db.commit()
