"""
Sistema de autenticação e autorização do Pontix.

Integração com Supabase Auth e controle de permissões baseado em função.
"""

from .auth_service import AuthService, get_auth_service
from .permissions import Permissions, Role, check_permission
from .middleware import auth_middleware
from .schemas import UserCreate, UserLogin, TokenResponse, UserProfile

__all__ = [
    "AuthService",
    "get_auth_service",
    "Permissions",
    "Role",
    "check_permission",
    "auth_middleware",
    "UserCreate",
    "UserLogin",
    "TokenResponse",
    "UserProfile",
]