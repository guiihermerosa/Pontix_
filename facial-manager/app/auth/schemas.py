"""
Schemas Pydantic para autenticação e usuários.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, validator, constr


class UserBase(BaseModel):
    """Base para usuários."""
    email: EmailStr
    full_name: str
    phone: Optional[str] = None


class UserCreate(UserBase):
    """Schema para criação de usuário."""
    password: constr(min_length=8, max_length=100)
    confirm_password: str
    role: Optional[str] = "employee"  # owner, accountant, manager, employee
    company_id: Optional[UUID] = None  # Para convites
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('As senhas não conferem')
        return v
    
    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('A senha deve ter pelo menos 8 caracteres')
        # Pode adicionar mais validações de força aqui
        return v


class UserLogin(BaseModel):
    """Schema para login."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Resposta com tokens de autenticação."""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int  # segundos
    user_id: str
    email: str


class UserProfile(BaseModel):
    """Perfil completo do usuário."""
    id: str
    email: str
    full_name: str
    phone: Optional[str]
    email_confirmed: bool
    created_at: datetime
    last_login: Optional[datetime]
    companies: List[Dict[str, Any]] = []


class CompanyInvite(BaseModel):
    """Schema para convite de usuário para empresa."""
    email: EmailStr
    role: str  # owner, accountant, manager, employee
    permissions: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


class PasswordResetRequest(BaseModel):
    """Solicitação de reset de senha."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Confirmação de reset de senha."""
    token: str
    new_password: str
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('As senhas não conferem')
        return v
    
    @validator('new_password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('A senha deve ter pelo menos 8 caracteres')
        return v


class ChangePassword(BaseModel):
    """Alteração de senha pelo usuário."""
    current_password: str
    new_password: str
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('As senhas não conferem')
        return v
    
    @validator('new_password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('A senha deve ter pelo menos 8 caracteres')
        return v


class UpdateProfile(BaseModel):
    """Atualização de perfil do usuário."""
    full_name: Optional[str] = None
    phone: Optional[str] = None


class AuthResponse(BaseModel):
    """Resposta genérica de autenticação."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


# Schemas para validação de tokens
class TokenData(BaseModel):
    """Dados extraídos do token JWT."""
    sub: Optional[str] = None
    email: Optional[str] = None
    exp: Optional[int] = None


# Schemas para auditoria
class AuditLogEntry(BaseModel):
    """Entrada de log de auditoria."""
    id: UUID
    user_id: Optional[str]
    action_type: str
    entity_type: str
    entity_id: Optional[str]
    old_values: Optional[Dict[str, Any]]
    new_values: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    user_agent: Optional[str]
    notes: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True