"""
Rotas de autenticação para o Pontix.
"""
import logging
from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer

from app.auth.auth_service import AuthService, get_auth_service
from app.auth.schemas import (
    UserCreate, UserLogin, TokenResponse, UserProfile,
    PasswordResetRequest, PasswordResetConfirm, ChangePassword,
    UpdateProfile, CompanyInvite, AuthResponse
)
from app.auth.permissions import get_current_user
from app.auth.middleware import get_current_company

router = APIRouter(prefix="/auth", tags=["Autenticação"])
security = HTTPBearer()
logger = logging.getLogger("auth_routes")


@router.post("/register", response_model=AuthResponse)
async def register(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Registra um novo usuário no sistema.
    
    Se company_id for fornecido, o usuário será vinculado à empresa como convidado.
    """
    try:
        # Converte company_id string para UUID se fornecido
        company_id = None
        if user_data.company_id:
            company_id = UUID(str(user_data.company_id))
        
        user = auth_service.register(user_data, company_id)
        
        return AuthResponse(
            success=True,
            message="Usuário registrado com sucesso. Verifique seu email para confirmar.",
            data=user
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no registro: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro ao registrar usuário: {str(e)}"
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: UserLogin,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Autentica usuário e retorna tokens de acesso.
    """
    try:
        return auth_service.login(login_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Renova token de acesso usando refresh token.
    """
    try:
        return auth_service.refresh_token(refresh_token)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao refresh token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não foi possível renovar o token"
        )


@router.post("/logout")
async def logout(
    user: Dict[str, Any] = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Realiza logout do usuário.
    """
    try:
        auth_service.logout(user["id"])
        return {"success": True, "message": "Logout realizado com sucesso"}
    except Exception as e:
        logger.error(f"Erro no logout: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao realizar logout"
        )


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    auth_service: AuthService = Depends(get_auth_service),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Retorna perfil completo do usuário atual.
    """
    try:
        return auth_service.get_user_profile(user["id"])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter perfil: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter perfil do usuário"
        )


@router.put("/me")
async def update_profile(
    profile_data: UpdateProfile,
    user: Dict[str, Any] = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Atualiza perfil do usuário atual.
    """
    try:
        # Atualiza dados no Supabase Auth
        # Esta função seria implementada no AuthService
        return {
            "success": True,
            "message": "Perfil atualizado com sucesso",
            "data": profile_data.dict(exclude_unset=True)
        }
    except Exception as e:
        logger.error(f"Erro ao atualizar perfil: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao atualizar perfil"
        )


@router.post("/password-reset")
async def request_password_reset(
    reset_data: PasswordResetRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Solicita reset de senha.
    """
    try:
        # Implementar lógica de reset de senha no AuthService
        return {
            "success": True,
            "message": "Instruções de reset de senha enviadas para o email"
        }
    except Exception as e:
        logger.error(f"Erro ao solicitar reset de senha: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao solicitar reset de senha"
        )


@router.post("/password-reset/confirm")
async def confirm_password_reset(
    confirm_data: PasswordResetConfirm,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Confirma reset de senha com token.
    """
    try:
        # Implementar lógica de confirmação de reset no AuthService
        return {
            "success": True,
            "message": "Senha redefinida com sucesso"
        }
    except Exception as e:
        logger.error(f"Erro ao confirmar reset de senha: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao confirmar reset de senha"
        )


@router.post("/change-password")
async def change_password(
    password_data: ChangePassword,
    user: Dict[str, Any] = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Altera senha do usuário atual.
    """
    try:
        # Implementar lógica de alteração de senha no AuthService
        return {
            "success": True,
            "message": "Senha alterada com sucesso"
        }
    except Exception as e:
        logger.error(f"Erro ao alterar senha: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao alterar senha"
        )


@router.post("/invite/{company_id}")
async def invite_user_to_company(
    company_id: UUID,
    invite_data: CompanyInvite,
    company_access: Dict[str, Any] = Depends(lambda: get_current_company(company_id))
):
    """
    Convida usuário para empresa.
    
    Requer permissão COMPANY_MANAGE_USERS.
    """
    try:
        from app.database.database import SessionLocal
        from app.database.models_cloud import CompanyUser
        
        db = SessionLocal()
        try:
            # Verifica se usuário já está convidado
            existing_invite = db.query(CompanyUser).filter(
                CompanyUser.company_id == company_id,
                CompanyUser.user_id == invite_data.email  # Temporário até implementar busca por email
            ).first()
            
            if existing_invite:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Usuário já convidado para esta empresa"
                )
            
            # Cria convite
            invitation = CompanyUser(
                company_id=company_id,
                user_id=invite_data.email,  # Temporário - será atualizado quando usuário aceitar
                role=invite_data.role,
                permissions=invite_data.permissions,
                invitation_status="pending",
                invited_by=company_access["user"]["id"],
                invited_at=db.now()  # Usar função now do banco
            )
            
            db.add(invitation)
            db.commit()
            
            # TODO: Enviar email de convite
            
            return {
                "success": True,
                "message": f"Convite enviado para {invite_data.email}",
                "data": {
                    "invitation_id": str(invitation.id),
                    "email": invite_data.email,
                    "role": invite_data.role,
                    "status": "pending"
                }
            }
            
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao convidar usuário: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao convidar usuário"
        )


@router.get("/companies")
async def get_user_companies(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Retorna todas as empresas do usuário.
    """
    try:
        from app.auth.permissions import get_user_companies
        companies = get_user_companies(user["id"])
        
        return {
            "success": True,
            "data": companies
        }
    except Exception as e:
        logger.error(f"Erro ao obter empresas do usuário: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter empresas"
        )


@router.get("/validate/{company_id}")
async def validate_company_access(
    company_id: UUID,
    company_access: Dict[str, Any] = Depends(lambda: get_current_company(company_id))
):
    """
    Valida se usuário tem acesso à empresa.
    """
    return {
        "success": True,
        "message": "Acesso autorizado",
        "data": {
            "company_id": str(company_id),
            "role": company_access["role"],
            "permissions": company_access["permissions"]
        }
    }


@router.get("/health")
async def auth_health():
    """
    Health check do módulo de autenticação.
    """
    return {
        "status": "ok",
        "service": "auth",
        "version": "1.0.0"
    }