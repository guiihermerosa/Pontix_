"""
Middleware de autenticação para FastAPI.
"""
import logging
from typing import Callable, Optional
from uuid import UUID

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth.auth_service import get_auth_service

logger = logging.getLogger("auth_middleware")


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware que valida autenticação e adiciona usuário ao request.
    
    Para rotas que não requerem autenticação, use o prefixo /public/ ou
    adicione a rota à lista de exceções.
    """
    
    def __init__(self, app, require_auth: bool = True):
        super().__init__(app)
        self.require_auth = require_auth
        self.auth_service = get_auth_service()
        
        # Rotas que não requerem autenticação
        self.public_routes = {
            "/public/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/auth/login",
            "/auth/register",
            "/auth/refresh",
            "/auth/password-reset",
            "/auth/password-reset/confirm",
        }
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Verifica se é uma rota pública
        if self._is_public_route(request.url.path):
            return await call_next(request)
        
        # Obtém token do header
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            if self.require_auth:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Token de autenticação não fornecido"},
                    headers={"WWW-Authenticate": "Bearer"},
                )
            # Se não requer autenticação, continua sem usuário
            request.state.user = None
            return await call_next(request)
        
        # Extrai token (Bearer <token>)
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                raise ValueError("Esquema de autenticação inválido")
        except ValueError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Formato de token inválido. Use: Bearer <token>"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Valida token
        user = self.auth_service.get_current_user(token)
        
        if not user:
            if self.require_auth:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Token inválido ou expirado"},
                    headers={"WWW-Authenticate": "Bearer"},
                )
            # Se não requer autenticação, continua sem usuário
            request.state.user = None
            return await call_next(request)
        
        # Adiciona usuário ao request
        request.state.user = user
        
        # Adiciona informações de auditoria
        request.state.audit_info = {
            "user_id": user["id"],
            "ip_address": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent"),
        }
        
        # Registra acesso no log
        logger.info(f"Acesso autorizado: {user['email']} - {request.method} {request.url.path}")
        
        response = await call_next(request)
        return response
    
    def _is_public_route(self, path: str) -> bool:
        """Verifica se a rota é pública."""
        return any(path.startswith(route) for route in self.public_routes)
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Obtém IP do cliente."""
        # Tenta obter do header X-Forwarded-For primeiro (para proxies)
        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        
        # Fallback para client host
        return request.client.host if request.client else None


def auth_middleware(app, require_auth: bool = True):
    """
    Factory para criar middleware de autenticação.
    
    Args:
        app: Aplicação FastAPI
        require_auth: Se True, requer autenticação para todas as rotas não públicas
        
    Returns:
        Instância do middleware
    """
    return AuthMiddleware(app, require_auth)


# Dependency para obter usuário atual
async def get_current_user(request: Request):
    """
    Dependency que obtém o usuário atual do request.
    
    Args:
        request: Request atual
        
    Returns:
        Dados do usuário ou None
        
    Raises:
        HTTPException se usuário não encontrado (quando require_auth=True)
    """
    user = getattr(request.state, "user", None)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


# Dependency para obter empresa atual
async def get_current_company(request: Request, company_id: Optional[UUID] = None):
    """
    Dependency que valida se o usuário tem acesso à empresa.
    
    Args:
        request: Request atual
        company_id: ID da empresa (opcional, pode vir da rota)
        
    Returns:
        Dados da empresa e role do usuário
        
    Raises:
        HTTPException se não autorizado
    """
    user = await get_current_user(request)
    
    # Se não há company_id, retorna apenas o usuário
    if not company_id:
        return {"user": user, "company": None, "role": None}
    
    # Obtém acesso do usuário à empresa
    from app.database.database import SessionLocal
    from app.database.models_supabase import CompanyUser
    
    db = SessionLocal()
    try:
        company_user = db.query(CompanyUser).filter(
            CompanyUser.user_id == user["id"],
            CompanyUser.company_id == company_id,
            CompanyUser.invitation_status == "accepted"
        ).first()
        
        if not company_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuário não tem acesso a esta empresa"
            )
        
        return {
            "user": user,
            "company": {"id": company_id},
            "role": company_user.role,
            "permissions": company_user.permissions or {}
        }
        
    finally:
        db.close()