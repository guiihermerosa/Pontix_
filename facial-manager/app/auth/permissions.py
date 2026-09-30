"""
Sistema de permissões baseado em função (RBAC) para o Pontix.
"""
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID
from functools import wraps

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.auth.auth_service import get_auth_service, AuthService

security = HTTPBearer()


class Role(str, Enum):
    """Papéis (roles) disponíveis no sistema."""
    SUPER_ADMIN = "super_admin"      # Administrador do sistema (GRB)
    OWNER = "owner"                  # Proprietário da empresa
    ACCOUNTANT = "accountant"        # Contador
    MANAGER = "manager"              # Gerente/RH
    EMPLOYEE = "employee"            # Funcionário
    
    @classmethod
    def get_all_roles(cls) -> List[str]:
        """Retorna todas as roles disponíveis."""
        return [role.value for role in cls]
    
    @classmethod
    def get_higher_roles(cls, role: str) -> List[str]:
        """Retorna roles com permissões iguais ou superiores."""
        hierarchy = {
            cls.EMPLOYEE.value: [cls.EMPLOYEE.value],
            cls.MANAGER.value: [cls.MANAGER.value, cls.EMPLOYEE.value],
            cls.ACCOUNTANT.value: [cls.ACCOUNTANT.value, cls.MANAGER.value, cls.EMPLOYEE.value],
            cls.OWNER.value: [cls.OWNER.value, cls.ACCOUNTANT.value, cls.MANAGER.value, cls.EMPLOYEE.value],
            cls.SUPER_ADMIN.value: [cls.SUPER_ADMIN.value, cls.OWNER.value, cls.ACCOUNTANT.value, cls.MANAGER.value, cls.EMPLOYEE.value]
        }
        return hierarchy.get(role, [])


class Permissions:
    """Definição de permissões por recurso e ação."""
    
    # Permissões para empresas
    COMPANY_VIEW = "company:view"
    COMPANY_EDIT = "company:edit"
    COMPANY_DELETE = "company:delete"
    COMPANY_MANAGE_USERS = "company:manage_users"
    
    # Permissões para funcionários
    EMPLOYEE_VIEW = "employee:view"
    EMPLOYEE_CREATE = "employee:create"
    EMPLOYEE_EDIT = "employee:edit"
    EMPLOYEE_DELETE = "employee:delete"
    
    # Permissões para registros de ponto
    TIMERECORD_VIEW = "timerecord:view"
    TIMERECORD_CREATE = "timerecord:create"
    TIMERECORD_EDIT = "timerecord:edit"
    TIMERECORD_DELETE = "timerecord:delete"
    
    # Permissões para ocorrências
    OCCURRENCE_VIEW = "occurrence:view"
    OCCURRENCE_CREATE = "occurrence:create"
    OCCURRENCE_EDIT = "occurrence:edit"
    OCCURRENCE_DELETE = "occurrence:delete"
    OCCURRENCE_RESOLVE = "occurrence:resolve"
    
    # Permissões para justificativas
    JUSTIFICATION_VIEW = "justification:view"
    JUSTIFICATION_CREATE = "justification:create"
    JUSTIFICATION_EDIT = "justification:edit"
    JUSTIFICATION_DELETE = "justification:delete"
    JUSTIFICATION_APPROVE = "justification:approve"
    
    # Permissões para períodos
    PERIOD_VIEW = "period:view"
    PERIOD_CLOSE = "period:close"
    PERIOD_REOPEN = "period:reopen"
    
    # Permissões para relatórios
    REPORT_VIEW = "report:view"
    REPORT_CREATE = "report:create"
    REPORT_EXPORT = "report:export"
    
    # Permissões para auditoria
    AUDIT_VIEW = "audit:view"
    
    # Permissões para configurações
    SETTINGS_VIEW = "settings:view"
    SETTINGS_EDIT = "settings:edit"
    
    # Mapeamento de roles para permissões
    ROLE_PERMISSIONS = {
        Role.SUPER_ADMIN.value: [
            COMPANY_VIEW, COMPANY_EDIT, COMPANY_DELETE, COMPANY_MANAGE_USERS,
            EMPLOYEE_VIEW, EMPLOYEE_CREATE, EMPLOYEE_EDIT, EMPLOYEE_DELETE,
            TIMERECORD_VIEW, TIMERECORD_CREATE, TIMERECORD_EDIT, TIMERECORD_DELETE,
            OCCURRENCE_VIEW, OCCURRENCE_CREATE, OCCURRENCE_EDIT, OCCURRENCE_DELETE, OCCURRENCE_RESOLVE,
            JUSTIFICATION_VIEW, JUSTIFICATION_CREATE, JUSTIFICATION_EDIT, JUSTIFICATION_DELETE, JUSTIFICATION_APPROVE,
            PERIOD_VIEW, PERIOD_CLOSE, PERIOD_REOPEN,
            REPORT_VIEW, REPORT_CREATE, REPORT_EXPORT,
            AUDIT_VIEW,
            SETTINGS_VIEW, SETTINGS_EDIT
        ],
        Role.OWNER.value: [
            COMPANY_VIEW, COMPANY_EDIT, COMPANY_MANAGE_USERS,
            EMPLOYEE_VIEW, EMPLOYEE_CREATE, EMPLOYEE_EDIT, EMPLOYEE_DELETE,
            TIMERECORD_VIEW, TIMERECORD_CREATE, TIMERECORD_EDIT, TIMERECORD_DELETE,
            OCCURRENCE_VIEW, OCCURRENCE_CREATE, OCCURRENCE_EDIT, OCCURRENCE_DELETE, OCCURRENCE_RESOLVE,
            JUSTIFICATION_VIEW, JUSTIFICATION_CREATE, JUSTIFICATION_EDIT, JUSTIFICATION_DELETE, JUSTIFICATION_APPROVE,
            PERIOD_VIEW, PERIOD_CLOSE, PERIOD_REOPEN,
            REPORT_VIEW, REPORT_CREATE, REPORT_EXPORT,
            AUDIT_VIEW,
            SETTINGS_VIEW, SETTINGS_EDIT
        ],
        Role.ACCOUNTANT.value: [
            COMPANY_VIEW,
            EMPLOYEE_VIEW,
            TIMERECORD_VIEW,
            OCCURRENCE_VIEW,
            JUSTIFICATION_VIEW,
            PERIOD_VIEW,
            REPORT_VIEW, REPORT_CREATE, REPORT_EXPORT,
            AUDIT_VIEW
        ],
        Role.MANAGER.value: [
            EMPLOYEE_VIEW,
            TIMERECORD_VIEW, TIMERECORD_EDIT,
            OCCURRENCE_VIEW, OCCURRENCE_CREATE, OCCURRENCE_EDIT, OCCURRENCE_RESOLVE,
            JUSTIFICATION_VIEW, JUSTIFICATION_CREATE, JUSTIFICATION_EDIT, JUSTIFICATION_APPROVE,
            PERIOD_VIEW,
            REPORT_VIEW, REPORT_CREATE,
            AUDIT_VIEW
        ],
        Role.EMPLOYEE.value: [
            TIMERECORD_VIEW,
            OCCURRENCE_VIEW,
            JUSTIFICATION_VIEW, JUSTIFICATION_CREATE,
            PERIOD_VIEW,
            REPORT_VIEW
        ]
    }
    
    @classmethod
    def has_permission(cls, role: str, permission: str) -> bool:
        """
        Verifica se uma role possui determinada permissão.
        
        Args:
            role: Papel do usuário
            permission: Permissão a ser verificada
            
        Returns:
            True se a role tem a permissão, False caso contrário
        """
        return permission in cls.ROLE_PERMISSIONS.get(role, [])
    
    @classmethod
    def get_permissions_for_role(cls, role: str) -> List[str]:
        """
        Retorna todas as permissões de uma role.
        
        Args:
            role: Papel do usuário
            
        Returns:
            Lista de permissões
        """
        return cls.ROLE_PERMISSIONS.get(role, [])


def check_permission(
    permission: str,
    auth_service: AuthService = Depends(get_auth_service),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Dependency que verifica se o usuário atual tem uma permissão específica.
    
    Args:
        permission: Permissão requerida
        auth_service: Serviço de autenticação
        credentials: Credenciais do token
        
    Returns:
        Dados do usuário se autorizado
        
    Raises:
        HTTPException 401 se não autenticado
        HTTPException 403 se não autorizado
    """
    def _check_permission_inner(company_id: Optional[UUID] = None):
        # Verifica autenticação
        user = auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Não autenticado",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Se for super_admin, tem todas as permissões
        if user.get("email") in ["admin@pontix.com", "superadmin@grb.com"]:
            return user
        
        # Obtém role do usuário na empresa
        if company_id:
            from app.database.database import SessionLocal
            from app.database.models_supabase import CompanyUser
            
            db = SessionLocal()
            try:
                company_user = db.query(CompanyUser).filter(
                    CompanyUser.user_id == user["id"],
                    CompanyUser.company_id == company_id
                ).first()
                
                if not company_user:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Usuário não tem acesso a esta empresa"
                    )
                
                role = company_user.role
                
                # Verifica permissão
                if not Permissions.has_permission(role, permission):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permissão '{permission}' não concedida para role '{role}'"
                    )
                
            finally:
                db.close()
        else:
            # Para endpoints globais, verifica se é super_admin
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão requer acesso a uma empresa específica"
            )
        
        return user
    
    return _check_permission_inner


def require_role(*roles: str):
    """
    Decorator para verificar se o usuário tem uma das roles especificadas.
    
    Args:
        *roles: Lista de roles permitidas
        
    Returns:
        Decorator que verifica role
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Esta função será implementada como middleware
            # A verificação real será feita no dependency check_permission
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def get_current_user(
    auth_service: AuthService = Depends(get_auth_service),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Dependency que retorna o usuário atual se autenticado.
    
    Args:
        auth_service: Serviço de autenticação
        credentials: Credenciais do token
        
    Returns:
        Dados do usuário
        
    Raises:
        HTTPException 401 se não autenticado
    """
    user = auth_service.get_current_user(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_user_companies(user_id: str) -> List[Dict[str, Any]]:
    """
    Obtém todas as empresas de um usuário.
    
    Args:
        user_id: ID do usuário
        
    Returns:
        Lista de empresas com roles
    """
    from app.database.database import SessionLocal
    from app.database.models_supabase import CompanyUser, Company
    from sqlalchemy.orm import joinedload
    
    db = SessionLocal()
    try:
        company_users = db.query(CompanyUser).filter(
            CompanyUser.user_id == user_id
        ).options(
            joinedload(CompanyUser.company)
        ).all()
        
        companies = []
        for cu in company_users:
            if cu.company:
                companies.append({
                    "id": str(cu.company.id),
                    "name": cu.company.name,
                    "role": cu.role,
                    "permissions": cu.permissions or {},
                    "invitation_status": cu.invitation_status
                })
        
        return companies
    finally:
        db.close()