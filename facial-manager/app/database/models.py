"""
Modelos SQLAlchemy — todas as tabelas do sistema.
"""
from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, Float, Integer,
    String, Text, func,
)
from app.database.database import Base


# ---------------------------------------------------------------------------
# Configurações do sistema
# ---------------------------------------------------------------------------
class Setting(Base):
    __tablename__ = "settings"

    id    = Column(Integer, primary_key=True, index=True)
    key   = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


# ---------------------------------------------------------------------------
# Funcionários
# ---------------------------------------------------------------------------
class Employee(Base):
    __tablename__ = "employees"

    id                 = Column(Integer, primary_key=True, index=True)
    userid             = Column(String(50), unique=True, nullable=False, index=True)
    name               = Column(String(200), nullable=False, default="")
    department         = Column(Integer, default=0)
    schedule           = Column(Integer, default=0)
    role               = Column(Integer, default=0)
    access_card_number = Column(String(100), default="")
    id_number          = Column(String(100), default="")
    # senha não é armazenada aqui — trafega só no momento do envio ao device
    person_period      = Column(Integer, default=0)
    pass_times         = Column(Integer, default=-1)
    pass_date          = Column(String(20), default="0")

    # Biometria / foto — apenas flag local, o arquivo fica no device
    has_face           = Column(Boolean, default=False)
    has_fingerprint    = Column(Boolean, default=False)
    has_palm           = Column(Boolean, default=False)

    # Sincronização
    device_synced      = Column(Boolean, default=False)
    sync_status        = Column(String(20), default="PENDING")   # PENDING | SUCCESS | ERROR
    last_synced_at     = Column(DateTime, nullable=True)

    created_at         = Column(DateTime, default=func.now())
    updated_at         = Column(DateTime, default=func.now(), onupdate=func.now())


# ---------------------------------------------------------------------------
# Registros de presença
# ---------------------------------------------------------------------------
class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id              = Column(Integer, primary_key=True, index=True)
    userid          = Column(String(50), nullable=False, index=True)
    employee_name   = Column(String(200), default="")
    attendance_date = Column(String(10), nullable=False, index=True)   # YYYY-MM-DD
    attendance_time = Column(String(8), nullable=False)                # HH:MM:SS
    record_type     = Column(String(20), default="UNKNOWN")            # ENTRY | EXIT | UNKNOWN
    raw_data        = Column(Text, nullable=True)                      # JSON original do device
    source          = Column(String(20), default="DEVICE")             # DEVICE | MANUAL
    created_at      = Column(DateTime, default=func.now())

    # Chave de deduplicação: userid + date + time
    dedup_key       = Column(String(80), unique=True, nullable=False, index=True)


# ---------------------------------------------------------------------------
# Fila de sincronização
# ---------------------------------------------------------------------------
class SyncQueue(Base):
    __tablename__ = "sync_queue"

    id           = Column(Integer, primary_key=True, index=True)
    entity_type  = Column(String(50), nullable=False)   # employee | settings | ...
    entity_id    = Column(String(50), nullable=True)
    operation    = Column(String(20), nullable=False)   # INSERT | UPDATE | DELETE
    payload      = Column(Text, nullable=True)          # JSON com dados
    status       = Column(String(20), default="PENDING") # PENDING | PROCESSING | SUCCESS | ERROR
    attempts     = Column(Integer, default=0)
    last_error   = Column(Text, nullable=True)
    created_at   = Column(DateTime, default=func.now())
    updated_at   = Column(DateTime, default=func.now(), onupdate=func.now())
    synced_at    = Column(DateTime, nullable=True)


# ---------------------------------------------------------------------------
# Logs de sincronização
# ---------------------------------------------------------------------------
class SyncLog(Base):
    __tablename__ = "sync_logs"

    id           = Column(Integer, primary_key=True, index=True)
    started_at   = Column(DateTime, default=func.now())
    finished_at  = Column(DateTime, nullable=True)
    success      = Column(Boolean, default=False)
    employees_synced   = Column(Integer, default=0)
    attendance_synced  = Column(Integer, default=0)
    errors_count       = Column(Integer, default=0)
    summary      = Column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Logs de comunicação com o dispositivo
# ---------------------------------------------------------------------------
class ApplicationLog(Base):
    __tablename__ = "application_logs"

    id               = Column(Integer, primary_key=True, index=True)
    timestamp        = Column(DateTime, default=func.now(), index=True)
    level            = Column(String(10), default="INFO")   # INFO | WARNING | ERROR | DEBUG
    endpoint         = Column(String(200), nullable=True)
    method           = Column(String(10), nullable=True)
    status_code      = Column(Integer, nullable=True)
    duration_ms      = Column(Float, nullable=True)
    success          = Column(Boolean, nullable=True)
    error            = Column(Text, nullable=True)
    request_summary  = Column(Text, nullable=True)
    response_summary = Column(Text, nullable=True)
    message          = Column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Status do dispositivo
# ---------------------------------------------------------------------------
class DeviceStatus(Base):
    __tablename__ = "device_status"

    id            = Column(Integer, primary_key=True, index=True)
    online        = Column(Boolean, default=False)
    response_time = Column(Float, nullable=True)   # ms
    last_check    = Column(DateTime, nullable=True)
    last_success  = Column(DateTime, nullable=True)
    last_error    = Column(Text, nullable=True)
    firmware_info = Column(Text, nullable=True)    # JSON extra quando disponível


# ---------------------------------------------------------------------------
# Destinatários de email
# ---------------------------------------------------------------------------
class EmailRecipient(Base):
    __tablename__ = "email_recipients"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(200), nullable=False, default="")
    email      = Column(String(254), nullable=False, unique=True, index=True)
    # "owner" = dono da empresa | "accounting" = escritório de contabilidade | "other"
    role       = Column(String(30), nullable=False, default="other")
    active     = Column(Boolean, default=True)   # checkbox ativo/inativo
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


# ---------------------------------------------------------------------------
# Atestados médicos
# ---------------------------------------------------------------------------
class MedicalCertificate(Base):
    __tablename__ = "medical_certificates"

    id           = Column(Integer, primary_key=True, index=True)
    userid       = Column(String(50), nullable=False, index=True)
    cert_date    = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD — data do atestado
    days_off     = Column(Integer, nullable=False, default=1)       # dias de afastamento
    description  = Column(Text, nullable=True)                      # observação / diagnóstico
    file_b64     = Column(Text, nullable=True)                      # imagem/PDF em base64
    file_mime    = Column(String(50), nullable=True)                # ex: image/jpeg, application/pdf
    file_name    = Column(String(200), nullable=True)               # nome original do arquivo
    created_at   = Column(DateTime, default=func.now())
    updated_at   = Column(DateTime, default=func.now(), onupdate=func.now())
