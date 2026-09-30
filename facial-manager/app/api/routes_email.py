"""
Rotas de Email — CRUD de destinatários, configurações Resend,
teste de envio e disparo manual do relatório mensal.
"""
import logging
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import EmailRecipient, Setting
from app.services.email_service import send_monthly_report, send_test_email

logger = logging.getLogger("routes_email")
router = APIRouter()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class RecipientCreate(BaseModel):
    name:   str
    email:  str
    role:   str = "other"   # owner | accounting | other
    active: bool = True

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not _EMAIL_RE.match(v):
            raise ValueError("Email inválido")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("owner", "accounting", "other"):
            raise ValueError("role deve ser owner, accounting ou other")
        return v


class RecipientUpdate(BaseModel):
    name:   Optional[str]  = None
    role:   Optional[str]  = None
    active: Optional[bool] = None


class IntegrationSettings(BaseModel):
    resend_api_key:   Optional[str] = None
    resend_from_email: Optional[str] = None
    resend_from_name:  Optional[str] = None


class EmailScheduleSettings(BaseModel):
    email_send_day:     Optional[int]  = None   # 1-28
    email_send_enabled: Optional[bool] = None


class SendReportRequest(BaseModel):
    year:  Optional[int] = None
    month: Optional[int] = None   # 1-12


class TestEmailRequest(BaseModel):
    email: str


# ---------------------------------------------------------------------------
# Destinatários
# ---------------------------------------------------------------------------

@router.get("/api/email/recipients")
async def list_recipients(db: Session = Depends(get_db)):
    try:
        rows = db.query(EmailRecipient).order_by(EmailRecipient.name).all()
        return [_serialize(r) for r in rows]
    except Exception as exc:
        logger.error("Erro em list_recipients: %s", exc)
        raise HTTPException(status_code=500, detail=f"Erro ao listar destinatários: {exc}")


@router.post("/api/email/recipients", status_code=201)
async def create_recipient(data: RecipientCreate, db: Session = Depends(get_db)):
    exists = db.query(EmailRecipient).filter(
        EmailRecipient.email == data.email
    ).first()
    if exists:
        raise HTTPException(status_code=409, detail="Email já cadastrado.")

    rec = EmailRecipient(
        name=data.name.strip(),
        email=data.email,
        role=data.role,
        active=data.active,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    logger.info("Destinatário criado: %s (%s)", rec.email, rec.role)
    return {"success": True, "recipient": _serialize(rec)}


@router.put("/api/email/recipients/{recipient_id}")
async def update_recipient(
    recipient_id: int,
    data: RecipientUpdate,
    db: Session = Depends(get_db),
):
    rec = db.query(EmailRecipient).filter(EmailRecipient.id == recipient_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Destinatário não encontrado.")

    if data.name  is not None: rec.name   = data.name.strip()
    if data.role  is not None: rec.role   = data.role
    if data.active is not None: rec.active = data.active

    db.commit()
    db.refresh(rec)
    return {"success": True, "recipient": _serialize(rec)}


@router.patch("/api/email/recipients/{recipient_id}/toggle")
async def toggle_recipient(recipient_id: int, db: Session = Depends(get_db)):
    """Ativa ou desativa um destinatário sem alterar outros campos."""
    rec = db.query(EmailRecipient).filter(EmailRecipient.id == recipient_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Destinatário não encontrado.")
    rec.active = not rec.active
    db.commit()
    return {"success": True, "active": rec.active, "id": rec.id}


@router.delete("/api/email/recipients/{recipient_id}")
async def delete_recipient(recipient_id: int, db: Session = Depends(get_db)):
    rec = db.query(EmailRecipient).filter(EmailRecipient.id == recipient_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Destinatário não encontrado.")
    db.delete(rec)
    db.commit()
    logger.info("Destinatário removido: id=%d", recipient_id)
    return {"success": True}


# ---------------------------------------------------------------------------
# Configurações de integração (API key Resend)
# ---------------------------------------------------------------------------

@router.get("/api/email/integration")
async def get_integration(db: Session = Depends(get_db)):
    """Retorna configs de integração — API key mascarada."""
    try:
        keys = ["resend_api_key", "resend_from_email", "resend_from_name"]
        rows = db.query(Setting).filter(Setting.key.in_(keys)).all()
        cfg = {r.key: r.value for r in rows}

        api_key     = cfg.get("resend_api_key", "")
        from_email  = cfg.get("resend_from_email", "onboarding@resend.dev")
        from_name   = cfg.get("resend_from_name", "Pontix")

        return {
            "resend_api_key_set":  bool(api_key),
            "resend_api_key_hint": f"re_...{api_key[-6:]}" if len(api_key) > 6 else ("definida" if api_key else ""),
            "resend_from_email":   from_email or "onboarding@resend.dev",
            "resend_from_name":    from_name  or "Pontix",
        }
    except Exception as exc:
        logger.error("Erro em get_integration: %s", exc)
        raise HTTPException(status_code=500, detail=f"Erro ao ler configurações: {exc}")


@router.put("/api/email/integration")
async def save_integration(data: IntegrationSettings, db: Session = Depends(get_db)):
    update = data.model_dump(exclude_unset=True, exclude_none=True)
    for key, value in update.items():
        if key == "resend_api_key" and not str(value).strip():
            continue   # não apaga chave com string vazia
        row = db.query(Setting).filter(Setting.key == key).first()
        if row:
            row.value = str(value).strip()
        else:
            db.add(Setting(key=key, value=str(value).strip()))
    db.commit()
    return {"success": True, "message": "Integração salva."}


# ---------------------------------------------------------------------------
# Configurações de agendamento
# ---------------------------------------------------------------------------

@router.get("/api/email/schedule")
async def get_schedule(db: Session = Depends(get_db)):
    try:
        keys = ["email_send_day", "email_send_enabled"]
        rows = db.query(Setting).filter(Setting.key.in_(keys)).all()
        cfg  = {r.key: r.value for r in rows}
        return {
            "email_send_day":     int(cfg.get("email_send_day", "1")),
            "email_send_enabled": cfg.get("email_send_enabled", "true") == "true",
        }
    except Exception as exc:
        logger.error("Erro em get_schedule: %s", exc)
        raise HTTPException(status_code=500, detail=f"Erro ao ler agendamento: {exc}")


@router.put("/api/email/schedule")
async def save_schedule(data: EmailScheduleSettings, db: Session = Depends(get_db)):
    if data.email_send_day is not None:
        if not (1 <= data.email_send_day <= 28):
            raise HTTPException(status_code=422, detail="Dia de envio deve ser entre 1 e 28.")
        _upsert(db, "email_send_day", str(data.email_send_day))

    if data.email_send_enabled is not None:
        _upsert(db, "email_send_enabled", "true" if data.email_send_enabled else "false")

    db.commit()

    # Re-agenda o job com o novo dia
    try:
        from app.main import scheduler as _scheduler
        from app.services.email_service import schedule_monthly_email
        day = int(_get_setting(db, "email_send_day", "1"))
        schedule_monthly_email(_scheduler, day=day)
    except Exception as exc:
        logger.warning("Não foi possível re-agendar job: %s", exc)

    return {"success": True, "message": "Agendamento salvo."}


# ---------------------------------------------------------------------------
# Envio
# ---------------------------------------------------------------------------

@router.post("/api/email/send-report")
async def send_report_now(
    data: SendReportRequest,
    db: Session = Depends(get_db),
):
    """
    Dispara o envio do relatório imediatamente para todos os destinatários ativos.
    Aceita year/month opcionais (default = mês anterior).
    """
    result = send_monthly_report(db, year=data.year, month=data.month)
    status = 200 if result["success"] else 502
    return result


@router.post("/api/email/test")
async def test_email(data: TestEmailRequest, db: Session = Depends(get_db)):
    """Envia email de teste (sem XLSX) para o endereço informado."""
    if not _EMAIL_RE.match(data.email.strip()):
        raise HTTPException(status_code=422, detail="Email inválido.")
    result = send_test_email(db, data.email.strip())
    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialize(r: EmailRecipient) -> dict:
    return {
        "id":         r.id,
        "name":       r.name,
        "email":      r.email,
        "role":       r.role,
        "role_label": {"owner": "Proprietário", "accounting": "Contabilidade", "other": "Outro"}.get(r.role, r.role),
        "active":     r.active,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _upsert(db: Session, key: str, value: str):
    row = db.query(Setting).filter(Setting.key == key).first()
    if row:
        row.value = value
    else:
        db.add(Setting(key=key, value=value))


def _get_setting(db: Session, key: str, default: str = "") -> str:
    row = db.query(Setting).filter(Setting.key == key).first()
    return row.value if row and row.value else default
