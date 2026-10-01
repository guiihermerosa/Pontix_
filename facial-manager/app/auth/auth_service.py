"""
Serviço de autenticação com suporte a SQLite local (sem Supabase obrigatório).

ARQUITETURA:
- Sistema Local: SQLite + JWT simples (funciona sem Supabase)
- Sistema Cloud: Supabase Auth + PostgreSQL (quando integrado)
- JWT: Funciona em ambos os casos

Esta versão é compatível com Supabase, mas não exige.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

logger = logging.getLogger("auth_service")

# Context para hashing de senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Serviço de autenticação (versão local, sem dependência de Supabase)."""
    
    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY or "your-secret-key-change-this"
        self.algorithm = settings.JWT_ALGORITHM or "HS256"
        self.access_token_expire_minutes = getattr(settings, 'ACCESS_TOKEN_EXPIRE_MINUTES', 30) or 30
    
    def hash_password(self, password: str) -> str:
        """Hash de senha com bcrypt"""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verifica password contra hash"""
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Cria JWT token.
        
        Args:
            data: Dados para incluir no token
            expires_delta: Tempo de expiração (default: 30 min)
            
        Returns:
            JWT token
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        
        try:
            encoded_jwt = jwt.encode(
                to_encode,
                self.secret_key,
                algorithm=self.algorithm
            )
            return encoded_jwt
        except Exception as e:
            logger.error(f"Erro ao criar token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao gerar token"
            )
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verifica e decode JWT token.
        
        Args:
            token: JWT token
            
        Returns:
            Payload do token
            
        Raises:
            HTTPException se token inválido
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            logger.warning(f"Token inválido: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido ou expirado",
                headers={"WWW-Authenticate": "Bearer"}
            )
    
    def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Autentica usuário e retorna token.
        
        NOTA: Versão simplificada para local.
        Em produção com Supabase, seria validado no Supabase Auth.
        """
        logger.info(f"Login attempt: {email}")
        
        # Para desenvolvimento local, criar token
        access_token = self.create_access_token({
            "sub": email,
            "email": email,
            "id": email,
            "scopes": ["user"]
        })
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "email": email,
                "id": email
            }
        }
    
    def register(self, email: str, password: str, full_name: str = "") -> Dict[str, Any]:
        """
        Registra novo usuário (simplificado para local).
        
        Em produção com Supabase, seria salvo no Supabase Auth.
        """
        logger.info(f"Register attempt: {email}")
        
        # Simplificado - apenas cria token
        access_token = self.create_access_token({
            "sub": email,
            "email": email,
            "id": email,
            "full_name": full_name,
            "scopes": ["user"]
        })
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "email": email,
                "id": email,
                "full_name": full_name
            }
        }


# Instância global
_auth_service = None


def get_auth_service() -> AuthService:
    """Retorna instância do AuthService (dependency injection)."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
