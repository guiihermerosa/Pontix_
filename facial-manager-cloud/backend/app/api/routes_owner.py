"""
Rotas do painel do proprietário (owner dashboard).

Endpoints:
- GET /api/owner/dashboard - Dashboard principal
- GET /api/owner/companies - Listagem de empresas
- GET /api/owner/companies/{id} - Detalhes da empresa
- PUT /api/owner/companies/{id} - Atualizar empresa
- GET /api/owner/users - Usuários da empresa
- POST /api/owner/users - Convidar usuário
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.database.models import (
    Company, Employee, TimeRecord, CompanyUser, Occurrence
)
from app.schemas import (
    CompanyResponse, CompanyUpdate, EmployeeResponse,
    SuccessResponse, PaginatedResponse
)
from app.auth import get_current_user, get_current_company_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/owner", tags=["owner"])


# ---------------------------------------------------------------------------
# Dashboard Principal
# ---------------------------------------------------------------------------

@router.get("/dashboard")
async def get_owner_dashboard(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna dashboard do proprietário com visão geral.
    """
    try:
        # Busca empresas do proprietário
        result = await db.execute(
            select(Company).where(Company.owner_id == user_id)
        )
        companies = result.scalars().all()
        
        if not companies:
            return {
                "statistics": {
                    "total_companies": 0,
                    "total_employees": 0,
                    "total_time_records": 0,
                    "pending_occurrences": 0,
                },
                "companies": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        
        company_ids = [c.id for c in companies]
        
        # Total de funcionários
        employees_result = await db.execute(
            select(func.count(Employee.id)).where(
                and_(
                    Employee.company_id.in_(company_ids),
                    Employee.is_active == True
                )
            )
        )
        total_employees = employees_result.scalar() or 0
        
        # Total de registros de ponto
        records_result = await db.execute(
            select(func.count(TimeRecord.id)).where(
                TimeRecord.company_id.in_(company_ids)
            )
        )
        total_records = records_result.scalar() or 0
        
        # Ocorrências pendentes
        pending_result = await db.execute(
            select(func.count(Occurrence.id)).where(
                and_(
                    Occurrence.company_id.in_(company_ids),
                    Occurrence.status == "pending"
                )
            )
        )
        pending_occurrences = pending_result.scalar() or 0
        
        return {
            "statistics": {
                "total_companies": len(companies),
                "total_employees": total_employees,
                "total_time_records": total_records,
                "pending_occurrences": pending_occurrences,
            },
            "companies": [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "cnpj": c.cnpj,
                    "is_active": c.is_active,
                    "created_at": c.created_at.isoformat(),
                }
                for c in companies
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Erro ao buscar dashboard do proprietário: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar dashboard")


# ---------------------------------------------------------------------------
# Empresas
# ---------------------------------------------------------------------------

@router.get("/companies", response_model=PaginatedResponse)
async def list_companies(
    user_id: str = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista empresas do proprietário com paginação.
    """
    try:
        # Query base
        query = select(Company).where(Company.owner_id == user_id)
        
        # Filtro de busca
        if search:
            query = query.where(
                Company.name.ilike(f"%{search}%") |
                Company.cnpj.ilike(f"%{search}%")
            )
        
        # Contar total
        count_result = await db.execute(
            select(func.count(Company.id)).where(Company.owner_id == user_id)
        )
        total = count_result.scalar() or 0
        
        # Paginar
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        result = await db.execute(query)
        companies = result.scalars().all()
        
        pages = (total + page_size - 1) // page_size
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "items": [
                CompanyResponse.model_validate(c) for c in companies
            ],
        }
    except Exception as e:
        logger.error(f"Erro ao listar empresas: {e}")
        raise HTTPException(status_code=500, detail="Erro ao listar empresas")


@router.get("/companies/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Obtém detalhes de uma empresa específica.
    """
    try:
        company_uuid = UUID(company_id)
        
        result = await db.execute(
            select(Company).where(
                and_(
                    Company.id == company_uuid,
                    Company.owner_id == user_id
                )
            )
        )
        company = result.scalar_one_or_none()
        
        if not company:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        
        return CompanyResponse.model_validate(company)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")
    except Exception as e:
        logger.error(f"Erro ao buscar empresa: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar empresa")


@router.put("/companies/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: str,
    user_id: str = Depends(get_current_user),
    payload: CompanyUpdate = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Atualiza informações de uma empresa.
    """
    try:
        company_uuid = UUID(company_id)
        
        result = await db.execute(
            select(Company).where(
                and_(
                    Company.id == company_uuid,
                    Company.owner_id == user_id
                )
            )
        )
        company = result.scalar_one_or_none()
        
        if not company:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        
        # Atualiza campos
        if payload.name:
            company.name = payload.name
        if payload.phone:
            company.phone = payload.phone
        if payload.address:
            company.address = payload.address
        if payload.city:
            company.city = payload.city
        if payload.state:
            company.state = payload.state
        if payload.zip_code:
            company.zip_code = payload.zip_code
        
        company.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        await db.refresh(company)
        
        return CompanyResponse.model_validate(company)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")
    except Exception as e:
        await db.rollback()
        logger.error(f"Erro ao atualizar empresa: {e}")
        raise HTTPException(status_code=500, detail="Erro ao atualizar empresa")


# ---------------------------------------------------------------------------
# Usuários da Empresa
# ---------------------------------------------------------------------------

@router.get("/companies/{company_id}/users", response_model=PaginatedResponse)
async def list_company_users(
    company_id: str,
    user_id: str = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista usuários de uma empresa.
    """
    try:
        company_uuid = UUID(company_id)
        
        # Verifica se o usuário é dono da empresa
        result = await db.execute(
            select(Company).where(
                and_(
                    Company.id == company_uuid,
                    Company.owner_id == user_id
                )
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Acesso negado")
        
        # Query de usuários
        query = select(CompanyUser).where(CompanyUser.company_id == company_uuid)
        
        # Contar total
        count_result = await db.execute(
            select(func.count(CompanyUser.id)).where(
                CompanyUser.company_id == company_uuid
            )
        )
        total = count_result.scalar() or 0
        
        # Paginar
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        result = await db.execute(query)
        users = result.scalars().all()
        
        pages = (total + page_size - 1) // page_size
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "items": [
                {
                    "id": str(u.id),
                    "user_id": u.user_id,
                    "role": u.role,
                    "invitation_status": u.invitation_status,
                    "created_at": u.created_at.isoformat(),
                }
                for u in users
            ],
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")
    except Exception as e:
        logger.error(f"Erro ao listar usuários da empresa: {e}")
        raise HTTPException(status_code=500, detail="Erro ao listar usuários")


@router.post("/companies/{company_id}/users/invite", response_model=SuccessResponse)
async def invite_user_to_company(
    company_id: str,
    user_id: str = Depends(get_current_user),
    payload: dict = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Convida um usuário para uma empresa.
    
    Body:
        {
            "email": "email@example.com",
            "role": "accountant"  # owner, accountant, manager
        }
    """
    try:
        company_uuid = UUID(company_id)
        
        # Verifica se o usuário é dono da empresa
        result = await db.execute(
            select(Company).where(
                and_(
                    Company.id == company_uuid,
                    Company.owner_id == user_id
                )
            )
        )
        company = result.scalar_one_or_none()
        
        if not company:
            raise HTTPException(status_code=403, detail="Acesso negado")
        
        # Cria convite
        email = payload.get("email")
        role = payload.get("role", "accountant")
        
        if not email:
            raise HTTPException(status_code=400, detail="Email obrigatório")
        
        company_user = CompanyUser(
            company_id=company_uuid,
            user_id=email,  # Usa email como user_id para agora
            role=role,
            invitation_status="pending",
        )
        
        db.add(company_user)
        await db.commit()
        
        # TODO: Enviar email de convite
        
        return SuccessResponse(
            message=f"Convite enviado para {email}",
            data={"user_email": email, "role": role}
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")
    except Exception as e:
        await db.rollback()
        logger.error(f"Erro ao convidar usuário: {e}")
        raise HTTPException(status_code=500, detail="Erro ao convidar usuário")


# ---------------------------------------------------------------------------
# Estatísticas por Empresa
# ---------------------------------------------------------------------------

@router.get("/companies/{company_id}/statistics")
async def get_company_statistics(
    company_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna estatísticas de uma empresa específica.
    """
    try:
        company_uuid = UUID(company_id)
        
        # Verifica se o usuário é dono
        result = await db.execute(
            select(Company).where(
                and_(
                    Company.id == company_uuid,
                    Company.owner_id == user_id
                )
            )
        )
        company = result.scalar_one_or_none()
        
        if not company:
            raise HTTPException(status_code=403, detail="Acesso negado")
        
        # Calcula estatísticas
        employees_result = await db.execute(
            select(func.count(Employee.id)).where(
                and_(
                    Employee.company_id == company_uuid,
                    Employee.is_active == True
                )
            )
        )
        total_employees = employees_result.scalar() or 0
        
        records_result = await db.execute(
            select(func.count(TimeRecord.id)).where(
                TimeRecord.company_id == company_uuid
            )
        )
        total_records = records_result.scalar() or 0
        
        occurrences_result = await db.execute(
            select(func.count(Occurrence.id)).where(
                Occurrence.company_id == company_uuid
            )
        )
        total_occurrences = occurrences_result.scalar() or 0
        
        return {
            "company_id": str(company.id),
            "company_name": company.name,
            "statistics": {
                "total_employees": total_employees,
                "total_records": total_records,
                "total_occurrences": total_occurrences,
                "created_at": company.created_at.isoformat(),
                "updated_at": company.updated_at.isoformat(),
            }
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")
    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar estatísticas")
