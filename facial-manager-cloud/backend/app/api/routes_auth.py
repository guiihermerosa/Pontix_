"""
Rotas de autenticação para Pontix Cloud.

Endpoints:
- POST /api/auth/register - Registrar novo usuário
- POST /api/auth/login - Fazer login
- POST /api/auth/refresh - Renovar token de acesso
- GET /api/auth/me - Obter dados do usuário atual
- POST /api/auth/logout - Logout (client-side only)
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.database.models import Company, CompanyUser
from app.auth import create_access_token, verify_token, get_current_user
from app.schemas import TokenResponse, SuccessResponse, UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    """Request para registrar novo usuário."""
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=200)
    password: str = Field(min_length=8, max_length=255)
    company_name: Optional[str] = Field(None, max_length=200)
    cnpj: Optional[str] = None


class LoginRequest(BaseModel):
    """Request para login."""
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    """Request para renovar token."""
    refresh_token: str


class UserMe(BaseModel):
    """Dados do usuário atual."""
    user_id: str
    email: str
    full_name: Optional[str] = None
    companies: list = []


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

async def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verifica se a senha corresponde ao hash.
    TODO: Implementar com bcrypt quando houver tabela de usuários
    """
    # Por enquanto, apenas comparação simples para desenvolvimento
    return password == hashed_password


async def hash_password(password: str) -> str:
    """
    Faz hash da senha.
    TODO: Implementar com bcrypt quando houver tabela de usuários
    """
    # Por enquanto, apenas retorna a senha para desenvolvimento
    return password


# ---------------------------------------------------------------------------
# Endpoints de Autenticação
# ---------------------------------------------------------------------------

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Registra um novo usuário e cria uma empresa (se fornecida).
    
    Retorna token de acesso JWT para login automático.
    """
    try:
        # TODO: Integrar com Supabase Auth para registro real
        # Por enquanto, simula criação de usuário
        
        user_id = payload.email.split("@")[0]  # Usa parte do email como ID
        
        # Se forneceu dados de empresa, cria empresa
        if payload.company_name and payload.cnpj:
            company = Company(
                name=payload.company_name,
                cnpj=payload.cnpj,
                owner_id=user_id,
                email=payload.email,
                is_active=True,
            )
            db.add(company)
            await db.flush()
            
            # Cria usuário na empresa
            company_user = CompanyUser(
                company_id=company.id,
                user_id=user_id,
                role="owner",
                invitation_status="accepted",
                accepted_at=datetime.now(timezone.utc),
            )
            db.add(company_user)
        
        await db.commit()
        
        logger.info(f"Novo usuário registrado: {payload.email}")
        
        # Cria token de acesso
        access_token = create_access_token(
            data={
                "sub": user_id,
                "email": payload.email,
                "full_name": payload.full_name,
            },
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Erro ao registrar usuário: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erro ao registrar usuário",
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Autentica o usuário e retorna token de acesso JWT.
    
    Em produção, seria integrado com Supabase Auth.
    Para desenvolvimento, aceita qualquer email com senha genérica.
    """
    try:
        # TODO: Integrar com Supabase Auth para verificação real
        # Por enquanto, simula autenticação
        
        email = payload.email
        user_id = email.split("@")[0]
        
        # Em desenvolvimento, qualquer senha funciona
        if not payload.password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha inválido",
            )
        
        logger.info(f"Usuário autenticado: {email}")
        
        # Busca empresas do usuário
        result = await db.execute(
            select(Company).where(Company.owner_id == user_id)
        )
        companies = result.scalars().all()
        
        # Se não tem empresa, cria uma padrão
        company_id = None
        if companies:
            company_id = str(companies[0].id)
        
        # Cria token de acesso
        access_token = create_access_token(
            data={
                "sub": user_id,
                "email": email,
                "company_id": company_id,
            },
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao fazer login: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erro ao fazer login",
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    payload: RefreshTokenRequest,
):
    """
    Renova o token de acesso usando um refresh token.
    
    TODO: Implementar refresh tokens com storage
    """
    try:
        # Verifica o token fornecido
        token_data = verify_token(payload.refresh_token)
        
        # Cria novo token de acesso
        access_token = create_access_token(
            data={
                "sub": token_data.user_id,
                "company_id": token_data.company_id,
                "role": token_data.role,
            },
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao renovar token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )


@router.get("/me", response_model=UserMe)
async def get_current_user_info(
    request: Request,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna informações do usuário atual.
    """
    try:
        # Busca empresas do usuário
        result = await db.execute(
            select(Company).where(Company.owner_id == user_id)
        )
        companies = result.scalars().all()
        
        return UserMe(
            user_id=user_id,
            email=getattr(request.state, "email", f"{user_id}@local"),
            full_name=getattr(request.state, "full_name", user_id),
            companies=[
                {
                    "id": str(c.id),
                    "name": c.name,
                    "cnpj": c.cnpj,
                }
                for c in companies
            ],
        )
    except Exception as e:
        logger.error(f"Erro ao buscar dados do usuário: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erro ao buscar dados do usuário",
        )


@router.post("/logout", response_model=SuccessResponse)
async def logout(
    user_id: str = Depends(get_current_user),
):
    """
    Logout do usuário.
    
    Em um aplicativo real com refresh tokens, invalidaria o token.
    Por enquanto, apenas retorna sucesso (logout é client-side).
    """
    logger.info(f"Usuário desconectado: {user_id}")
    return SuccessResponse(
        success=True,
        message="Logout realizado com sucesso",
    )
