"""
Middleware de autenticação JWT para Pontix Cloud.
"""
import logging
from typing import Optional, Callable
from datetime import datetime, timedelta, timezone

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from jose import JWTError, jwt

from app.config import settings

logger = logging.getLogger(__name__)

security = HTTPBearer()


class TokenData:
    """Dados extraídos do token JWT."""
    
    def __init__(self, user_id: str, company_id: Optional[str] = None, role: Optional[str] = None):
        self.user_id = user_id
        self.company_id = company_id
        self.role = role


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Cria um token JWT.
    
    Args:
        data: Dados a serem incluídos no token
        expires_delta: Tempo de expiração (padrão: 30 minutos)
    
    Returns:
        Token JWT codificado
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    """
    Verifica e decodifica um token JWT.
    
    Args:
        token: Token JWT a ser verificado
    
    Returns:
        TokenData com informações do usuário
    
    Raises:
        HTTPException: Se o token for inválido ou expirado
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        
        company_id: Optional[str] = payload.get("company_id")
        role: Optional[str] = payload.get("role")
        
        token_data = TokenData(user_id=user_id, company_id=company_id, role=role)
    except JWTError:
        raise credentials_exception
    
    return token_data


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware de autenticação que verifica tokens JWT.
    """
    
    def __init__(self, app, require_auth: bool = True):
        super().__init__(app)
        self.require_auth = require_auth
    
    async def dispatch(self, request: Request, call_next: Callable) -> any:
        """
        Intercepta requisições e valida autenticação.
        """
        # Rotas públicas (não requerem autenticação)
        public_routes = [
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/refresh",
        ]
        
        # Se for rota pública, continua sem validar
        if request.url.path in public_routes or request.url.path.startswith("/static"):
            return await call_next(request)
        
        # Se autenticação não é obrigatória, continua
        if not self.require_auth:
            return await call_next(request)
        
        # Extrai token do header Authorization
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de autenticação não fornecido",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Tipo de autenticação inválido",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Formato de autenticação inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Valida o token
        try:
            token_data = verify_token(token)
            request.state.user_id = token_data.user_id
            request.state.company_id = token_data.company_id
            request.state.role = token_data.role
            request.state.token = token
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Erro ao validar token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Continua processando a requisição
        response = await call_next(request)
        return response


def get_current_user(request: Request) -> str:
    """
    Extrai o ID do usuário atual da requisição.
    
    Uso em endpoints:
        @app.get("/api/users/me")
        async def get_current_user_info(user_id: str = Depends(get_current_user)):
            return {"user_id": user_id}
    """
    if not hasattr(request.state, "user_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não autenticado",
        )
    return request.state.user_id


def get_current_company_id(request: Request) -> str:
    """
    Extrai o ID da empresa atual da requisição.
    """
    if not hasattr(request.state, "company_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nenhuma empresa associada",
        )
    return request.state.company_id


def get_current_role(request: Request) -> str:
    """
    Extrai o role do usuário atual da requisição.
    """
    if not hasattr(request.state, "role"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Role não definido",
        )
    return request.state.role
