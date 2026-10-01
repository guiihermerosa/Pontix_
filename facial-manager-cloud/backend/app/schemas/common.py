"""
Schemas comuns para Pontix Cloud API.
"""
from datetime import datetime
from typing import Optional, Generic, TypeVar, List
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr

T = TypeVar('T')


# ---------------------------------------------------------------------------
# Resposta paginada genérica
# ---------------------------------------------------------------------------

class PaginatedResponse(BaseModel, Generic[T]):
    """Resposta paginada genérica."""
    
    total: int = Field(description="Total de itens")
    page: int = Field(description="Página atual (começa em 1)")
    page_size: int = Field(description="Itens por página")
    pages: int = Field(description="Total de páginas")
    items: List[T] = Field(description="Itens da página")


# ---------------------------------------------------------------------------
# Resposta padrão
# ---------------------------------------------------------------------------

class SuccessResponse(BaseModel):
    """Resposta padrão de sucesso."""
    success: bool = True
    message: str
    data: Optional[dict] = None


class ErrorResponse(BaseModel):
    """Resposta padrão de erro."""
    success: bool = False
    message: str
    error_code: Optional[str] = None


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------

class TokenResponse(BaseModel):
    """Resposta com token de acesso."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Request para refresh de token."""
    refresh_token: str


# ---------------------------------------------------------------------------
# Usuário
# ---------------------------------------------------------------------------

class UserBase(BaseModel):
    """Base do usuário."""
    email: EmailStr
    full_name: str


class UserCreate(UserBase):
    """Criar usuário."""
    password: str


class UserResponse(UserBase):
    """Resposta de usuário."""
    id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Empresa
# ---------------------------------------------------------------------------

class CompanyBase(BaseModel):
    """Base de empresa."""
    name: str = Field(max_length=200)
    cnpj: str = Field(max_length=18)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None


class CompanyCreate(CompanyBase):
    """Criar empresa."""
    owner_id: str


class CompanyUpdate(BaseModel):
    """Atualizar empresa."""
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None


class CompanyResponse(CompanyBase):
    """Resposta de empresa."""
    id: UUID
    owner_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Funcionário
# ---------------------------------------------------------------------------

class EmployeeBase(BaseModel):
    """Base de funcionário."""
    full_name: str = Field(max_length=200)
    user_id: str = Field(max_length=50)
    email: Optional[EmailStr] = None
    cpf: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None
    registration_number: Optional[str] = None


class EmployeeCreate(EmployeeBase):
    """Criar funcionário."""
    company_id: UUID


class EmployeeUpdate(BaseModel):
    """Atualizar funcionário."""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    department: Optional[str] = None
    role: Optional[str] = None
    registration_number: Optional[str] = None


class EmployeeResponse(EmployeeBase):
    """Resposta de funcionário."""
    id: UUID
    company_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Registro de Ponto
# ---------------------------------------------------------------------------

class TimeRecordBase(BaseModel):
    """Base de registro de ponto."""
    employee_id: UUID
    record_date: datetime
    record_time: str = Field(pattern=r"^\d{2}:\d{2}:\d{2}$")
    record_type: str = Field(pattern="^(entry|exit|break_start|break_end)$")


class TimeRecordCreate(TimeRecordBase):
    """Criar registro de ponto."""
    company_id: UUID
    source: str = "device"


class TimeRecordUpdate(BaseModel):
    """Atualizar registro de ponto."""
    record_time: Optional[str] = None
    adjustment_reason: Optional[str] = None


class TimeRecordResponse(TimeRecordBase):
    """Resposta de registro de ponto."""
    id: UUID
    company_id: UUID
    user_id: str
    employee_name: str
    source: str
    is_adjusted: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Ocorrência
# ---------------------------------------------------------------------------

class OccurrenceBase(BaseModel):
    """Base de ocorrência."""
    employee_id: UUID
    occurrence_date: datetime
    occurrence_type: str = Field(max_length=50)
    severity: str = "medium"
    description: Optional[str] = None


class OccurrenceCreate(OccurrenceBase):
    """Criar ocorrência."""
    company_id: UUID


class OccurrenceUpdate(BaseModel):
    """Atualizar ocorrência."""
    status: Optional[str] = None
    resolution_notes: Optional[str] = None


class OccurrenceResponse(OccurrenceBase):
    """Resposta de ocorrência."""
    id: UUID
    company_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Justificativa
# ---------------------------------------------------------------------------

class JustificationBase(BaseModel):
    """Base de justificativa."""
    employee_id: UUID
    justification_type: str = Field(max_length=50)
    start_date: datetime
    end_date: datetime
    description: str


class JustificationCreate(JustificationBase):
    """Criar justificativa."""
    company_id: UUID
    submitted_by: str


class JustificationUpdate(BaseModel):
    """Atualizar justificativa."""
    status: Optional[str] = None
    approved_by: Optional[str] = None


class JustificationResponse(JustificationBase):
    """Resposta de justificativa."""
    id: UUID
    company_id: UUID
    status: str
    submitted_by: str
    created_at: datetime
    
    class Config:
        from_attributes = True
