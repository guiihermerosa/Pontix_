"""
Dependencies reutilizáveis para validação de acesso.
"""
import logging
from typing import Dict, Any, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.permissions import get_current_user
from app.database.database import get_db
from app.database.models_cloud import Company, CompanyUser

logger = logging.getLogger("dependencies")


async def validate_company_access(
    company_id: UUID,
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Company:
    """
    Valida se usuário autenticado tem acesso à empresa.
    
    Verifica:
    1. Empresa existe
    2. Usuário é accountant_id responsável OU está em company_users
    
    Retorna: Objeto Company se autorizado
    Raises: HTTPException 404 ou 403
    """
    try:
        # Obtém empresa
        company = db.query(Company).filter(Company.id == company_id).first()
        
        if not company:
            logger.warning(f"Empresa {company_id} não encontrada (user: {user['id']})")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa não encontrada"
            )
        
        # ✅ VERIFICAÇÃO 1: É o contador responsável?
        if company.accountant_id and company.accountant_id == user["id"]:
            logger.info(f"Acesso concedido: {user['id']} é accountant de {company_id}")
            return company
        
        # ✅ VERIFICAÇÃO 2: Está em company_users com acesso aceito?
        company_user = db.query(CompanyUser).filter(
            CompanyUser.company_id == company_id,
            CompanyUser.user_id == user["id"],
            CompanyUser.invitation_status == "accepted"
        ).first()
        
        if company_user:
            logger.info(f"Acesso concedido: {user['id']} em company_users de {company_id} (role: {company_user.role})")
            return company
        
        # ❌ Acesso negado
        logger.warning(f"Acesso negado: {user['id']} tentou acessar {company_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar esta empresa"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao validar acesso à empresa: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao validar acesso"
        )


async def get_user_companies(
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> list[UUID]:
    """
    Obtém lista de UUIDs das empresas às quais o usuário tem acesso.
    
    Inclui:
    - Empresas onde user é accountant_id
    - Empresas onde user está em company_users com status accepted
    """
    try:
        from sqlalchemy import or_
        
        # Empresas como accountant
        accountant_companies = db.query(Company.id).filter(
            Company.accountant_id == user["id"]
        ).all()
        
        # Empresas em company_users
        company_user_companies = db.query(CompanyUser.company_id).filter(
            CompanyUser.user_id == user["id"],
            CompanyUser.invitation_status == "accepted"
        ).all()
        
        # Combina e retorna UUIDs únicos
        company_ids = set()
        for row in accountant_companies:
            company_ids.add(row[0])
        for row in company_user_companies:
            company_ids.add(row[0])
        
        logger.debug(f"User {user['id']} tem acesso a {len(company_ids)} empresas")
        return list(company_ids)
        
    except Exception as e:
        logger.error(f"Erro ao obter empresas do usuário: {str(e)}")
        return []


async def get_user_role_in_company(
    company_id: UUID,
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Optional[str]:
    """
    Obtém role do usuário na empresa.
    
    Retorna:
    - "accountant" se user.id == company.accountant_id
    - role de company_users se existir
    - None se não tem acesso
    """
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        
        if not company:
            return None
        
        if company.accountant_id == user["id"]:
            return "accountant"
        
        company_user = db.query(CompanyUser).filter(
            CompanyUser.company_id == company_id,
            CompanyUser.user_id == user["id"],
            CompanyUser.invitation_status == "accepted"
        ).first()
        
        return company_user.role if company_user else None
        
    except Exception as e:
        logger.error(f"Erro ao obter role do usuário: {str(e)}")
        return None