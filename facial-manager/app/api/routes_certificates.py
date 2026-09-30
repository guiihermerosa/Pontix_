"""
Rotas de Atestados Médicos — CRUD completo com upload de arquivo.
"""
import base64
import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import Employee, MedicalCertificate

logger = logging.getLogger("routes_certificates")
router = APIRouter()

_MAX_FILE_BYTES = 5 * 1024 * 1024   # 5 MB


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CertUpdate(BaseModel):
    cert_date:   Optional[str] = None   # YYYY-MM-DD
    days_off:    Optional[int] = None
    description: Optional[str] = None


# ---------------------------------------------------------------------------
# Listar atestados (por funcionário ou todos)
# ---------------------------------------------------------------------------

@router.get("/api/certificates")
async def list_certificates(
    userid: Optional[str] = None,
    year:   Optional[int] = None,
    month:  Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    Lista atestados ordenados por data descendente.
    Filtros: userid, year, month (todos opcionais).
    """
    q = db.query(MedicalCertificate)
    if userid:
        q = q.filter(MedicalCertificate.userid == userid)
    if year:
        q = q.filter(MedicalCertificate.cert_date.like(f"{year}-%"))
    if month:
        prefix = f"%-{month:02d}-%"
        q = q.filter(MedicalCertificate.cert_date.like(prefix))
    rows = q.order_by(MedicalCertificate.cert_date.desc()).all()
    return [_serialize(r, include_file=False) for r in rows]


@router.get("/api/certificates/{cert_id}")
async def get_certificate(cert_id: int, db: Session = Depends(get_db)):
    cert = _get_or_404(db, cert_id)
    return _serialize(cert, include_file=True)


# ---------------------------------------------------------------------------
# Download do arquivo
# ---------------------------------------------------------------------------

@router.get("/api/certificates/{cert_id}/file")
async def download_file(cert_id: int, db: Session = Depends(get_db)):
    """Retorna o arquivo do atestado como download direto."""
    cert = _get_or_404(db, cert_id)
    if not cert.file_b64:
        raise HTTPException(status_code=404, detail="Nenhum arquivo anexado a este atestado.")
    raw = base64.b64decode(cert.file_b64)
    filename = cert.file_name or f"atestado_{cert_id}"
    mime     = cert.file_mime or "application/octet-stream"
    return Response(
        content=raw,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Criar atestado (multipart/form-data — aceita arquivo opcional)
# ---------------------------------------------------------------------------

@router.post("/api/certificates", status_code=201)
async def create_certificate(
    userid:      str = Form(...),
    cert_date:   str = Form(...),           # YYYY-MM-DD
    days_off:    int = Form(1),
    description: str = Form(""),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """
    Cadastra um atestado médico.
    O arquivo (imagem ou PDF) é opcional — pode ser adicionado depois via PATCH.
    """
    # Valida funcionário
    emp = db.query(Employee).filter(Employee.userid == userid).first()
    if not emp:
        raise HTTPException(status_code=404, detail=f"Funcionário '{userid}' não encontrado.")

    # Processa arquivo se enviado
    file_b64 = file_mime = file_name = None
    if file and file.filename:
        raw = await file.read()
        if len(raw) > _MAX_FILE_BYTES:
            raise HTTPException(status_code=413, detail="Arquivo muito grande (máx 5 MB).")
        file_b64  = base64.b64encode(raw).decode()
        file_mime = file.content_type or "application/octet-stream"
        file_name = file.filename

    cert = MedicalCertificate(
        userid=userid,
        cert_date=cert_date,
        days_off=max(1, days_off),
        description=description.strip() or None,
        file_b64=file_b64,
        file_mime=file_mime,
        file_name=file_name,
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)

    logger.info("Atestado criado: id=%d userid=%s data=%s dias=%d",
                cert.id, userid, cert_date, days_off)
    return {"success": True, "certificate": _serialize(cert, include_file=False)}


# ---------------------------------------------------------------------------
# Atualizar dados (sem substituir arquivo)
# ---------------------------------------------------------------------------

@router.put("/api/certificates/{cert_id}")
async def update_certificate(
    cert_id: int,
    data: CertUpdate,
    db: Session = Depends(get_db),
):
    cert = _get_or_404(db, cert_id)
    if data.cert_date   is not None: cert.cert_date   = data.cert_date
    if data.days_off    is not None: cert.days_off    = max(1, data.days_off)
    if data.description is not None: cert.description = data.description.strip() or None
    db.commit()
    db.refresh(cert)
    return {"success": True, "certificate": _serialize(cert, include_file=False)}


# ---------------------------------------------------------------------------
# Substituir / adicionar arquivo
# ---------------------------------------------------------------------------

@router.patch("/api/certificates/{cert_id}/file")
async def upload_file(
    cert_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Substitui ou adiciona o arquivo de um atestado existente."""
    cert = _get_or_404(db, cert_id)
    raw = await file.read()
    if len(raw) > _MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo muito grande (máx 5 MB).")
    cert.file_b64  = base64.b64encode(raw).decode()
    cert.file_mime = file.content_type or "application/octet-stream"
    cert.file_name = file.filename
    db.commit()
    return {"success": True, "file_name": cert.file_name}


# ---------------------------------------------------------------------------
# Remover arquivo (mantém o registro)
# ---------------------------------------------------------------------------

@router.delete("/api/certificates/{cert_id}/file")
async def remove_file(cert_id: int, db: Session = Depends(get_db)):
    cert = _get_or_404(db, cert_id)
    cert.file_b64 = cert.file_mime = cert.file_name = None
    db.commit()
    return {"success": True}


# ---------------------------------------------------------------------------
# Excluir atestado
# ---------------------------------------------------------------------------

@router.delete("/api/certificates/{cert_id}")
async def delete_certificate(cert_id: int, db: Session = Depends(get_db)):
    cert = _get_or_404(db, cert_id)
    db.delete(cert)
    db.commit()
    logger.info("Atestado removido: id=%d", cert_id)
    return {"success": True}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_404(db: Session, cert_id: int) -> MedicalCertificate:
    cert = db.query(MedicalCertificate).filter(MedicalCertificate.id == cert_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Atestado não encontrado.")
    return cert


def _serialize(cert: MedicalCertificate, include_file: bool = False) -> dict:
    d = {
        "id":          cert.id,
        "userid":      cert.userid,
        "cert_date":   cert.cert_date,
        "days_off":    cert.days_off,
        "description": cert.description or "",
        "has_file":    bool(cert.file_b64),
        "file_name":   cert.file_name or "",
        "file_mime":   cert.file_mime or "",
        "created_at":  cert.created_at.isoformat() if cert.created_at else None,
    }
    if include_file and cert.file_b64:
        d["file_b64"] = cert.file_b64
    return d
