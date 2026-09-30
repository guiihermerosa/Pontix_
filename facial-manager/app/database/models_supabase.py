"""
Models SQLAlchemy para integração com Supabase PostgreSQL.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer,
    String, Text, UniqueConstraint, JSON, DECIMAL
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.database.database import Base


# ---------------------------------------------------------------------------
# Empresas
# ---------------------------------------------------------------------------
class Company(Base):
    __tablename__ = "companies"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    cnpj = Column(String(18), unique=True)
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(2))
    zip_code = Column(String(9))
    phone = Column(String(20))
    email = Column(String(254))
    logo_url = Column(Text)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    
    # Configurações específicas da empresa
    timezone = Column(String(50), default="America/Sao_Paulo")
    work_hours = Column(JSON, default=lambda: {
        "start": "08:00", 
        "end": "18:00", 
        "break_start": "12:00", 
        "break_end": "13:00"
    })
    sync_settings = Column(JSON, default=lambda: {
        "frequency": 5, 
        "max_retries": 3
    })
    
    # Relacionamentos
    users = relationship("CompanyUser", back_populates="company")
    employees = relationship("EmployeeSupabase", back_populates="company")
    time_records = relationship("TimeRecord", back_populates="company")
    work_periods = relationship("WorkPeriod", back_populates="company")
    occurrences = relationship("Occurrence", back_populates="company")
    justifications = relationship("Justification", back_populates="company")
    audit_logs = relationship("AuditLog", back_populates="company")
    sync_logs = relationship("SyncLog", back_populates="company")
    reports = relationship("Report", back_populates="company")
    email_templates = relationship("EmailTemplate", back_populates="company")


# ---------------------------------------------------------------------------
# Usuários do Sistema (relacionamento com Supabase Auth)
# ---------------------------------------------------------------------------
class CompanyUser(Base):
    __tablename__ = "company_users"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, index=True)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), nullable=False)  # ID do usuário no Supabase Auth
    role = Column(String(50), nullable=False, default="employee")  # owner, accountant, manager, employee
    permissions = Column(JSON)
    invitation_token = Column(Text)
    invitation_status = Column(String(20), default="pending")  # pending, accepted, declined
    invited_by = Column(String(36))  # ID do usuário que convidou
    invited_at = Column(DateTime(timezone=True))
    accepted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    
    # Relacionamentos
    company = relationship("Company", back_populates="users")
    
    __table_args__ = (
        UniqueConstraint("company_id", "user_id", name="uq_company_user"),
    )


# ---------------------------------------------------------------------------
# Funcionários (Cloud)
# ---------------------------------------------------------------------------
class EmployeeSupabase(Base):
    __tablename__ = "employees"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, index=True)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    local_id = Column(String(100))  # ID do sistema local
    user_id = Column(String(50), nullable=False)  # userid do dispositivo
    full_name = Column(String(200), nullable=False)
    department = Column(String(100))
    role = Column(String(100))
    registration_number = Column(String(100))  # Matrícula
    cpf = Column(String(14))
    admission_date = Column(DateTime)
    email = Column(String(254))
    phone = Column(String(20))
    work_schedule = Column(JSON)  # Horário de trabalho padrão
    biometric_data = Column(JSON)  # Dados de biometria (criptografados)
    is_active = Column(Boolean, default=True)
    sync_status = Column(String(20), default="synced")  # synced, pending, conflict
    last_synced_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    
    # Relacionamentos
    company = relationship("Company", back_populates="employees")
    time_records = relationship("TimeRecord", back_populates="employee")
    occurrences = relationship("Occurrence", back_populates="employee")
    justifications = relationship("Justification", back_populates="employee")


# ---------------------------------------------------------------------------
# Registros de Ponto (Cloud)
# ---------------------------------------------------------------------------
class TimeRecord(Base):
    __tablename__ = "time_records"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, index=True)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    employee_id = Column(PG_UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    local_record_id = Column(String(100))  # ID do registro local
    user_id = Column(String(50), nullable=False)  # userid do dispositivo
    employee_name = Column(String(200))
    record_date = Column(DateTime, nullable=False)  # DATE
    record_time = Column(String(8), nullable=False)  # TIME como string HH:MM:SS
    record_type = Column(String(20), nullable=False)  # entry, exit, break_start, break_end
    source = Column(String(20), default="device")  # device, manual, adjusted
    device_id = Column(String(100))
    latitude = Column(DECIMAL(10, 8))
    longitude = Column(DECIMAL(11, 8))
    original_data = Column(JSON)  # Dados originais do dispositivo
    is_adjusted = Column(Boolean, default=False)
    adjustment_reason = Column(Text)
    adjusted_by = Column(String(36))  # ID do usuário
    adjusted_at = Column(DateTime(timezone=True))
    sync_status = Column(String(20), default="synced")
    deduplication_key = Column(String(100), unique=True)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    
    # Relacionamentos
    company = relationship("Company", back_populates="time_records")
    employee = relationship("EmployeeSupabase", back_populates="time_records")


# ---------------------------------------------------------------------------
# Períodos de Trabalho
# ---------------------------------------------------------------------------
class WorkPeriod(Base):
    __tablename__ = "work_periods"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, index=True)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)  # 1-12
    status = Column(String(20), default="open")  # open, reviewing, closed, reopened
    closed_by = Column(String(36))  # ID do usuário
    closed_at = Column(DateTime(timezone=True))
    reopened_by = Column(String(36))  # ID do usuário
    reopened_at = Column(DateTime(timezone=True))
    closing_notes = Column(Text)
    statistics = Column(JSON)  # Estatísticas calculadas
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    
    # Relacionamentos
    company = relationship("Company", back_populates="work_periods")
    
    __table_args__ = (
        UniqueConstraint("company_id", "year", "month", name="uq_company_year_month"),
    )


# ---------------------------------------------------------------------------
# Ocorrências
# ---------------------------------------------------------------------------
class Occurrence(Base):
    __tablename__ = "occurrences"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, index=True)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    employee_id = Column(PG_UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    occurrence_date = Column(DateTime, nullable=False)  # DATE
    occurrence_type = Column(String(50), nullable=False)  # late, absence, early_exit, etc.
    severity = Column(String(20), default="medium")  # low, medium, high, critical
    status = Column(String(20), default="pending")  # pending, reviewed, resolved, dismissed
    description = Column(Text)
    details = Column(JSON)  # Detalhes específicos do tipo
    assigned_to = Column(String(36))  # ID do usuário
    resolved_by = Column(String(36))  # ID do usuário
    resolved_at = Column(DateTime(timezone=True))
    resolution_notes = Column(Text)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    
    # Relacionamentos
    company = relationship("Company", back_populates="occurrences")
    employee = relationship("EmployeeSupabase", back_populates="occurrences")
    justification = relationship("Justification", back_populates="occurrence", uselist=False)


# ---------------------------------------------------------------------------
# Justificativas
# ---------------------------------------------------------------------------
class Justification(Base):
    __tablename__ = "justifications"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, index=True)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    occurrence_id = Column(PG_UUID(as_uuid=True), ForeignKey("occurrences.id", ondelete="CASCADE"))
    employee_id = Column(PG_UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    justification_type = Column(String(50), nullable=False)  # medical, personal, etc.
    start_date = Column(DateTime, nullable=False)  # DATE
    end_date = Column(DateTime, nullable=False)  # DATE
    description = Column(Text, nullable=False)
    supporting_document_url = Column(Text)
    submitted_by = Column(String(36))  # ID do usuário
    approved_by = Column(String(36))  # ID do usuário
    approved_at = Column(DateTime(timezone=True))
    status = Column(String(20), default="pending")  # pending, approved, rejected
    rejection_reason = Column(Text)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    
    # Relacionamentos
    company = relationship("Company", back_populates="justifications")
    employee = relationship("EmployeeSupabase", back_populates="justifications")
    occurrence = relationship("Occurrence", back_populates="justification")


# ---------------------------------------------------------------------------
# Logs de Auditoria
# ---------------------------------------------------------------------------
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, index=True)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36))  # ID do usuário no Supabase Auth
    action_type = Column(String(50), nullable=False)  # login, logout, create, update, delete, etc.
    entity_type = Column(String(50), nullable=False)  # employee, time_record, etc.
    entity_id = Column(String(100))
    old_values = Column(JSON)
    new_values = Column(JSON)
    ip_address = Column(String(45))  # IPv4 ou IPv6
    user_agent = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True))
    
    # Relacionamentos
    company = relationship("Company", back_populates="audit_logs")


# ---------------------------------------------------------------------------
# Logs de Sincronização
# ---------------------------------------------------------------------------
class SyncLog(Base):
    __tablename__ = "sync_logs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, index=True)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    sync_type = Column(String(50), nullable=False)  # full, incremental, employees, time_records
    status = Column(String(20), nullable=False)  # started, completed, failed, partial
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    records_processed = Column(Integer, default=0)
    records_succeeded = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    errors = Column(JSON)  # Lista de erros
    details = Column(Text)
    created_at = Column(DateTime(timezone=True))
    
    # Relacionamentos
    company = relationship("Company", back_populates="sync_logs")


# ---------------------------------------------------------------------------
# Relatórios
# ---------------------------------------------------------------------------
class Report(Base):
    __tablename__ = "reports"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, index=True)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    report_type = Column(String(50), nullable=False)  # monthly, employee, overtime, absences
    period_year = Column(Integer)
    period_month = Column(Integer)
    employee_id = Column(PG_UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"))
    format = Column(String(20), default="pdf")  # pdf, excel, csv
    status = Column(String(20), default="generating")  # generating, ready, sent, expired
    file_url = Column(Text)
    file_size = Column(Integer)
    access_token = Column(String(100), unique=True)  # Token para acesso seguro
    expires_at = Column(DateTime(timezone=True))
    generated_by = Column(String(36))  # ID do usuário
    sent_to_email = Column(String(254))
    sent_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True))
    
    # Relacionamentos
    company = relationship("Company", back_populates="reports")
    employee = relationship("EmployeeSupabase")


# ---------------------------------------------------------------------------
# Modelos de E-mail
# ---------------------------------------------------------------------------
class EmailTemplate(Base):
    __tablename__ = "email_templates"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, index=True)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    template_type = Column(String(50), nullable=False)  # monthly_report, occurrence_notice, invitation
    subject_template = Column(Text, nullable=False)
    body_template = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    variables = Column(JSON)  # Variáveis disponíveis no template
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    
    # Relacionamentos
    company = relationship("Company", back_populates="email_templates")
    
    __table_args__ = (
        UniqueConstraint("company_id", "template_type", name="uq_company_template_type"),
    )