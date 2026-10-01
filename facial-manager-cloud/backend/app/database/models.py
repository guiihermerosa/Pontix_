"""
Modelos SQLAlchemy para Supabase PostgreSQL - Pontix Cloud
"""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer,
    String, Text, UniqueConstraint, JSON, DECIMAL, Index,
    func
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


# ---------------------------------------------------------------------------
# Empresas
# ---------------------------------------------------------------------------
class Company(Base):
    __tablename__ = "companies"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(200), nullable=False)
    cnpj = Column(String(18), unique=True, nullable=False, index=True)
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(2))
    zip_code = Column(String(9))
    phone = Column(String(20))
    email = Column(String(254), index=True)
    logo_url = Column(Text)
    
    # Responsável pela empresa
    owner_id = Column(String(36), nullable=False)  # Supabase Auth ID
    accountant_id = Column(String(36))  # Contador responsável
    
    # Configurações
    timezone = Column(String(50), default="America/Sao_Paulo")
    work_hours = Column(JSON, default=lambda: {
        "start": "08:00", 
        "end": "18:00", 
        "break_start": "12:00", 
        "break_end": "13:00"
    })
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    users = relationship("CompanyUser", back_populates="company")
    employees = relationship("Employee", back_populates="company")
    time_records = relationship("TimeRecord", back_populates="company")
    occurrences = relationship("Occurrence", back_populates="company")
    justifications = relationship("Justification", back_populates="company")
    audit_logs = relationship("AuditLog", back_populates="company")
    
    __table_args__ = (
        Index('idx_company_owner', 'owner_id'),
        Index('idx_company_active', 'is_active'),
    )


# ---------------------------------------------------------------------------
# Usuários do Sistema
# ---------------------------------------------------------------------------
class CompanyUser(Base):
    __tablename__ = "company_users"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), nullable=False)  # Supabase Auth ID
    
    # Role na empresa
    role = Column(String(50), nullable=False)  # owner, accountant, manager, employee
    permissions = Column(JSON)
    
    # Status
    invitation_status = Column(String(20), default="pending")  # pending, accepted, declined
    invitation_token = Column(Text)
    invited_by = Column(String(36))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    accepted_at = Column(DateTime(timezone=True))
    
    # Relacionamentos
    company = relationship("Company", back_populates="users")
    
    __table_args__ = (
        UniqueConstraint("company_id", "user_id", name="uq_company_user"),
        Index('idx_company_user_status', 'company_id', 'invitation_status'),
    )


# ---------------------------------------------------------------------------
# Funcionários
# ---------------------------------------------------------------------------
class Employee(Base):
    __tablename__ = "employees"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    
    # Identificação
    local_id = Column(String(100))  # ID do sistema local
    user_id = Column(String(50), nullable=False)  # ID do dispositivo facial
    full_name = Column(String(200), nullable=False)
    email = Column(String(254))
    cpf = Column(String(14))
    
    # Cargo
    department = Column(String(100))
    role = Column(String(100))
    registration_number = Column(String(100))
    
    # Datas
    admission_date = Column(DateTime)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Sincronização
    sync_status = Column(String(20), default="pending")  # pending, synced, conflict
    last_synced_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    company = relationship("Company", back_populates="employees")
    time_records = relationship("TimeRecord", back_populates="employee")
    occurrences = relationship("Occurrence", back_populates="employee")
    justifications = relationship("Justification", back_populates="employee")
    
    __table_args__ = (
        Index('idx_employee_company', 'company_id'),
        Index('idx_employee_active', 'company_id', 'is_active'),
        Index('idx_employee_userid', 'user_id'),
    )


# ---------------------------------------------------------------------------
# Registros de Ponto
# ---------------------------------------------------------------------------
class TimeRecord(Base):
    __tablename__ = "time_records"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    employee_id = Column(PG_UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    
    # Informações do registro
    local_record_id = Column(String(100))  # ID do registro local
    user_id = Column(String(50), nullable=False)
    employee_name = Column(String(200))
    
    # Data/Hora
    record_date = Column(DateTime, nullable=False, index=True)
    record_time = Column(String(8), nullable=False)
    record_type = Column(String(20), nullable=False)  # entry, exit, break_start, break_end
    
    # Fonte
    source = Column(String(20), default="device")  # device, manual, adjusted
    device_id = Column(String(100))
    
    # Localização
    latitude = Column(DECIMAL(10, 8))
    longitude = Column(DECIMAL(11, 8))
    
    # Ajuste
    is_adjusted = Column(Boolean, default=False)
    adjustment_reason = Column(Text)
    adjusted_by = Column(String(36))
    adjusted_at = Column(DateTime(timezone=True))
    
    # Sincronização
    sync_status = Column(String(20), default="pending")
    deduplication_key = Column(String(100), unique=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    company = relationship("Company", back_populates="time_records")
    employee = relationship("Employee", back_populates="time_records")
    
    __table_args__ = (
        Index('idx_timerecord_company_date', 'company_id', 'record_date'),
        Index('idx_timerecord_employee_date', 'employee_id', 'record_date'),
    )


# ---------------------------------------------------------------------------
# Ocorrências
# ---------------------------------------------------------------------------
class Occurrence(Base):
    __tablename__ = "occurrences"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    employee_id = Column(PG_UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    
    # Informações
    occurrence_date = Column(DateTime, nullable=False, index=True)
    occurrence_type = Column(String(50), nullable=False)  # late, absence, early_exit, extra_hours, etc
    severity = Column(String(20), default="medium")  # low, medium, high, critical
    
    # Status
    status = Column(String(20), default="pending")  # pending, reviewed, resolved, dismissed
    
    # Detalhes
    description = Column(Text)
    details = Column(JSON)
    
    # Resolução
    assigned_to = Column(String(36))
    resolved_by = Column(String(36))
    resolved_at = Column(DateTime(timezone=True))
    resolution_notes = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    company = relationship("Company", back_populates="occurrences")
    employee = relationship("Employee", back_populates="occurrences")
    justification = relationship("Justification", back_populates="occurrence", uselist=False)
    
    __table_args__ = (
        Index('idx_occurrence_company_date', 'company_id', 'occurrence_date'),
        Index('idx_occurrence_employee', 'employee_id'),
        Index('idx_occurrence_status', 'status'),
    )


# ---------------------------------------------------------------------------
# Justificativas
# ---------------------------------------------------------------------------
class Justification(Base):
    __tablename__ = "justifications"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    occurrence_id = Column(PG_UUID(as_uuid=True), ForeignKey("occurrences.id", ondelete="CASCADE"))
    employee_id = Column(PG_UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    
    # Tipo e período
    justification_type = Column(String(50), nullable=False)  # medical, personal, business, etc
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    
    # Descrição
    description = Column(Text, nullable=False)
    supporting_document_url = Column(Text)
    
    # Status
    status = Column(String(20), default="pending")  # pending, approved, rejected
    submitted_by = Column(String(36), nullable=False)
    approved_by = Column(String(36))
    approved_at = Column(DateTime(timezone=True))
    rejection_reason = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    company = relationship("Company", back_populates="justifications")
    employee = relationship("Employee", back_populates="justifications")
    occurrence = relationship("Occurrence", back_populates="justification")
    
    __table_args__ = (
        Index('idx_justification_company', 'company_id'),
        Index('idx_justification_employee', 'employee_id'),
        Index('idx_justification_status', 'status'),
    )


# ---------------------------------------------------------------------------
# Logs de Auditoria
# ---------------------------------------------------------------------------
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    
    # Ator
    user_id = Column(String(36))
    
    # Ação
    action_type = Column(String(50), nullable=False)  # create, update, delete, view, etc
    entity_type = Column(String(50), nullable=False)  # employee, timerecord, occurrence, etc
    entity_id = Column(String(100))
    
    # Dados
    old_values = Column(JSON)
    new_values = Column(JSON)
    
    # Metadados
    ip_address = Column(String(45))
    user_agent = Column(Text)
    notes = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relacionamentos
    company = relationship("Company", back_populates="audit_logs")
    
    __table_args__ = (
        Index('idx_auditlog_company', 'company_id'),
        Index('idx_auditlog_user', 'user_id'),
        Index('idx_auditlog_date', 'created_at'),
    )
