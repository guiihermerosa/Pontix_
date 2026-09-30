"""
Serviço de autenticação integrado com Supabase Auth.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import HTTPException, status
from supabase import create_client, Client
from jose import JWTError, jwt

from app.auth.schemas import UserCreate, UserLogin, TokenResponse, UserProfile
from app.auth.permissions import Role
from app.config import settings

logger = logging.getLogger("auth_service")


class AuthService:
    """Serviço de autenticação com Supabase."""
    
    def __init__(self):
        self.supabase: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY
        )
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    
    def register(self, user_data: UserCreate, company_id: UUID = None) -> Dict[str, Any]:
        """
        Registra um novo usuário no Supabase Auth.
        
        Args:
            user_data: Dados do usuário
            company_id: ID da empresa se for convite
            
        Returns:
            Dados do usuário registrado
        """
        try:
            # Cria usuário no Supabase Auth
            auth_response = self.supabase.auth.sign_up({
                "email": user_data.email,
                "password": user_data.password,
                "options": {
                    "data": {
                        "full_name": user_data.full_name,
                        "phone": user_data.phone,
                    }
                }
            })
            
            user = auth_response.user
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Falha ao criar usuário"
                )
            
            # Se for convite para empresa, cria relacionamento
            if company_id:
                from app.database.database import SessionLocal
                from app.database.models_supabase import CompanyUser
                
                db = SessionLocal()
                try:
                    company_user = CompanyUser(
                        company_id=company_id,
                        user_id=user.id,
                        role=user_data.role or Role.EMPLOYEE.value,
                        invitation_status="accepted"
                    )
                    db.add(company_user)
                    db.commit()
                finally:
                    db.close()
            
            logger.info(f"Usuário registrado: {user.email}")
            
            return {
                "id": user.id,
                "email": user.email,
                "full_name": user_data.full_name,
                "email_confirmed": user.email_confirmed_at is not None,
                "created_at": user.created_at,
            }
            
        except Exception as e:
            logger.error(f"Erro ao registrar usuário: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Erro ao registrar usuário: {str(e)}"
            )
    
    def login(self, login_data: UserLogin) -> TokenResponse:
        """
        Autentica usuário e retorna tokens.
        
        Args:
            login_data: Credenciais de login
            
        Returns:
            Tokens de acesso e refresh
        """
        try:
            auth_response = self.supabase.auth.sign_in_with_password({
                "email": login_data.email,
                "password": login_data.password
            })
            
            user = auth_response.user
            session = auth_response.session
            
            if not user or not session:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Credenciais inválidas"
                )
            
            # Cria JWT adicional para uso interno
            access_token_expires = timedelta(minutes=self.access_token_expire_minutes)
            access_token = self.create_access_token(
                data={"sub": user.id, "email": user.email},
                expires_delta=access_token_expires
            )
            
            # Registra login no audit log
            self._log_login(user.id)
            
            logger.info(f"Login realizado: {user.email}")
            
            return TokenResponse(
                access_token=access_token,
                refresh_token=session.refresh_token,
                token_type="bearer",
                expires_in=self.access_token_expire_minutes * 60,
                user_id=user.id,
                email=user.email
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro no login: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais inválidas"
            )
    
    def logout(self, user_id: str) -> None:
        """
        Realiza logout do usuário.
        
        Args:
            user_id: ID do usuário
        """
        try:
            self.supabase.auth.sign_out()
            logger.info(f"Logout realizado: {user_id}")
        except Exception as e:
            logger.error(f"Erro no logout: {str(e)}")
    
    def get_current_user(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Valida token JWT e retorna usuário atual.
        
        Args:
            token: Token JWT
            
        Returns:
            Dados do usuário ou None se inválido
        """
        try:
            payload = jwt.decode(
                token, self.secret_key, algorithms=[self.algorithm]
            )
            user_id: str = payload.get("sub")
            email: str = payload.get("email")
            
            if user_id is None or email is None:
                return None
            
            # Obtém dados do usuário do Supabase
            user_response = self.supabase.auth.get_user(token)
            user = user_response.user
            
            if not user:
                return None
            
            return {
                "id": user.id,
                "email": user.email,
                "user_metadata": user.user_metadata or {},
                "email_confirmed": user.email_confirmed_at is not None,
            }
            
        except JWTError:
            return None
        except Exception as e:
            logger.error(f"Erro ao obter usuário: {str(e)}")
            return None
    
    def refresh_token(self, refresh_token: str) -> TokenResponse:
        """
        Renova token de acesso usando refresh token.
        
        Args:
            refresh_token: Token de refresh
            
        Returns:
            Novos tokens
        """
        try:
            # Usa o método de refresh do Supabase
            auth_response = self.supabase.auth.refresh_session(refresh_token)
            session = auth_response.session
            
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token inválido"
                )
            
            # Cria novo JWT
            access_token_expires = timedelta(minutes=self.access_token_expire_minutes)
            access_token = self.create_access_token(
                data={"sub": session.user.id, "email": session.user.email},
                expires_delta=access_token_expires
            )
            
            return TokenResponse(
                access_token=access_token,
                refresh_token=session.refresh_token,
                token_type="bearer",
                expires_in=self.access_token_expire_minutes * 60,
                user_id=session.user.id,
                email=session.user.email
            )
            
        except Exception as e:
            logger.error(f"Erro ao refresh token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Não foi possível renovar o token"
            )
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Cria token JWT.
        
        Args:
            data: Dados a serem incluídos no token
            expires_delta: Tempo de expiração
            
        Returns:
            Token JWT
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def get_user_profile(self, user_id: str) -> UserProfile:
        """
        Obtém perfil completo do usuário.
        
        Args:
            user_id: ID do usuário
            
        Returns:
            Perfil do usuário
        """
        try:
            # Obtém usuário do Supabase
            user_response = self.supabase.auth.admin.get_user_by_id(user_id)
            user = user_response.user
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Usuário não encontrado"
                )
            
            # Obtém empresas do usuário
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
                            "permissions": cu.permissions or {}
                        })
                
                return UserProfile(
                    id=user.id,
                    email=user.email,
                    full_name=user.user_metadata.get("full_name", "") if user.user_metadata else "",
                    phone=user.user_metadata.get("phone", "") if user.user_metadata else "",
                    email_confirmed=user.email_confirmed_at is not None,
                    created_at=user.created_at,
                    last_login=self._get_last_login(user_id),
                    companies=companies
                )
                
            finally:
                db.close()
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro ao obter perfil: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao obter perfil do usuário"
            )
    
    def _log_login(self, user_id: str) -> None:
        """Registra login no audit log."""
        try:
            from app.database.database import SessionLocal
            from app.database.models_supabase import AuditLog
            
            db = SessionLocal()
            try:
                audit_log = AuditLog(
                    user_id=user_id,
                    action_type="login",
                    entity_type="user",
                    entity_id=user_id,
                    ip_address=None,  # Será preenchido pelo middleware
                    user_agent=None,  # Será preenchido pelo middleware
                    notes="Login realizado"
                )
                db.add(audit_log)
                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Erro ao registrar login no audit: {str(e)}")
    
    def _get_last_login(self, user_id: str) -> Optional[datetime]:
        """Obtém último login do usuário."""
        try:
            from app.database.database import SessionLocal
            from app.database.models_supabase import AuditLog
            
            db = SessionLocal()
            try:
                last_login = db.query(AuditLog).filter(
                    AuditLog.user_id == user_id,
                    AuditLog.action_type == "login"
                ).order_by(AuditLog.created_at.desc()).first()
                
                return last_login.created_at if last_login else None
            finally:
                db.close()
        except Exception:
            return None


# Instância global do serviço de autenticação
_auth_service = None

def get_auth_service() -> AuthService:
    """Retorna instância do serviço de autenticação."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service