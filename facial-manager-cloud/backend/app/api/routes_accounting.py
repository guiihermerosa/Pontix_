"""
Rotas do painel do contador (accountant dashboard).

Endpoints:
- GET /api/accounting/dashboard - Dashboard principal
- GET /api/accounting/employees - Listagem de funcionários
- GET /api/accounting/time-records - Registros de ponto
- GET /api/accounting/occurrences - Ocorrências
- GET /api/accounting/justifications - Justificativas
- POST /api/accounting/occurrences - Criar ocorrência
- PUT /api/accounting/occurrences/{id} - Atualizar ocorrência
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.database.models import (
    Company, Employee, TimeRecord, Occurrence, Justification
)
from app.schemas import (
    EmployeeResponse, TimeRecordResponse, OccurrenceResponse,
    OccurrenceCreate, OccurrenceUpdate, SuccessResponse,
    PaginatedResponse
)
from app.auth import get_current_company_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/accounting", tags=["accounting"])


# ---------------------------------------------------------------------------
# Dashboard Principal
# ---------------------------------------------------------------------------

@router.get("/dashboard")
async def get_accounting_dashboard(
    company_id: str = Depends(get_current_company_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna dashboard do contador com estatísticas principais.
    """
    try:
        company_uuid = UUID(company_id)
        
        # Total de funcionários ativos
        employees_result = await db.execute(
            select(func.count(Employee.id)).where(
                and_(
                    Employee.company_id == company_uuid,
                    Employee.is_active == True
                )
            )
        )
        total_employees = employees_result.scalar() or 0
        
        # Registros de ponto hoje
        today = datetime.now(timezone.utc).date()
        today_start = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
        today_end = datetime.combine(today, datetime.max.time(), tzinfo=timezone.utc)
        
        today_records_result = await db.execute(
            select(func.count(TimeRecord.id)).where(
                and_(
                    TimeRecord.company_id == company_uuid,
                    TimeRecord.record_date >= today_start,
                    TimeRecord.record_date <= today_end,
                )
            )
        )
        today_records = today_records_result.scalar() or 0
        
        # Ocorrências pendentes
        pending_occurrences_result = await db.execute(
            select(func.count(Occurrence.id)).where(
                and_(
                    Occurrence.company_id == company_uuid,
                    Occurrence.status == "pending"
                )
            )
        )
        pending_occurrences = pending_occurrences_result.scalar() or 0
        
        # Justificativas pendentes
        pending_justifications_result = await db.execute(
            select(func.count(Justification.id)).where(
                and_(
                    Justification.company_id == company_uuid,
                    Justification.status == "pending"
                )
            )
        )
        pending_justifications = pending_justifications_result.scalar() or 0
        
        # Última sincronização
        last_sync_result = await db.execute(
            select(func.max(TimeRecord.updated_at)).where(
                TimeRecord.company_id == company_uuid
            )
        )
        last_sync = last_sync_result.scalar()
        
        return {
            "statistics": {
                "total_employees": total_employees,
                "today_records": today_records,
                "pending_occurrences": pending_occurrences,
                "pending_justifications": pending_justifications,
                "last_sync": last_sync.isoformat() if last_sync else None,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="ID da empresa inválido")
    except Exception as e:
        logger.error(f"Erro ao buscar dashboard: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar dashboard")


# ---------------------------------------------------------------------------
# Funcionários
# ---------------------------------------------------------------------------

@router.get("/employees", response_model=PaginatedResponse)
async def list_employees(
    company_id: str = Depends(get_current_company_id),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista funcionários da empresa com paginação.
    """
    try:
        company_uuid = UUID(company_id)
        
        # Query base
        query = select(Employee).where(
            and_(
                Employee.company_id == company_uuid,
                Employee.is_active == True
            )
        )
        
        # Filtro de busca
        if search:
            query = query.where(
                Employee.full_name.ilike(f"%{search}%") |
                Employee.cpf.ilike(f"%{search}%")
            )
        
        # Contar total
        count_result = await db.execute(
            select(func.count(Employee.id)).where(
                and_(
                    Employee.company_id == company_uuid,
                    Employee.is_active == True
                )
            )
        )
        total = count_result.scalar() or 0
        
        # Paginar
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        result = await db.execute(query)
        employees = result.scalars().all()
        
        pages = (total + page_size - 1) // page_size
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "items": [
                EmployeeResponse.model_validate(emp) for emp in employees
            ],
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="ID da empresa inválido")
    except Exception as e:
        logger.error(f"Erro ao listar funcionários: {e}")
        raise HTTPException(status_code=500, detail="Erro ao listar funcionários")


# ---------------------------------------------------------------------------
# Registros de Ponto
# ---------------------------------------------------------------------------

@router.get("/time-records", response_model=PaginatedResponse)
async def list_time_records(
    company_id: str = Depends(get_current_company_id),
    employee_id: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista registros de ponto com filtros opcionais.
    """
    try:
        company_uuid = UUID(company_id)
        
        # Query base
        query = select(TimeRecord).where(TimeRecord.company_id == company_uuid)
        
        # Filtros
        if employee_id:
            employee_uuid = UUID(employee_id)
            query = query.where(TimeRecord.employee_id == employee_uuid)
        
        if start_date:
            query = query.where(TimeRecord.record_date >= start_date)
        
        if end_date:
            query = query.where(TimeRecord.record_date <= end_date)
        
        # Contar total
        count_result = await db.execute(
            select(func.count(TimeRecord.id)).where(
                TimeRecord.company_id == company_uuid
            )
        )
        total = count_result.scalar() or 0
        
        # Paginar
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(TimeRecord.record_date.desc())
        
        result = await db.execute(query)
        records = result.scalars().all()
        
        pages = (total + page_size - 1) // page_size
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "items": [
                TimeRecordResponse.model_validate(rec) for rec in records
            ],
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")
    except Exception as e:
        logger.error(f"Erro ao listar registros de ponto: {e}")
        raise HTTPException(status_code=500, detail="Erro ao listar registros")


# ---------------------------------------------------------------------------
# Ocorrências
# ---------------------------------------------------------------------------

@router.get("/occurrences", response_model=PaginatedResponse)
async def list_occurrences(
    company_id: str = Depends(get_current_company_id),
    status: Optional[str] = Query(None),
    employee_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista ocorrências com filtros opcionais.
    """
    try:
        company_uuid = UUID(company_id)
        
        # Query base
        query = select(Occurrence).where(Occurrence.company_id == company_uuid)
        
        # Filtros
        if status:
            query = query.where(Occurrence.status == status)
        
        if employee_id:
            employee_uuid = UUID(employee_id)
            query = query.where(Occurrence.employee_id == employee_uuid)
        
        # Contar total
        count_result = await db.execute(
            select(func.count(Occurrence.id)).where(
                Occurrence.company_id == company_uuid
            )
        )
        total = count_result.scalar() or 0
        
        # Paginar
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(Occurrence.created_at.desc())
        
        result = await db.execute(query)
        occurrences = result.scalars().all()
        
        pages = (total + page_size - 1) // page_size
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "items": [
                OccurrenceResponse.model_validate(occ) for occ in occurrences
            ],
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")
    except Exception as e:
        logger.error(f"Erro ao listar ocorrências: {e}")
        raise HTTPException(status_code=500, detail="Erro ao listar ocorrências")


@router.post("/occurrences", response_model=OccurrenceResponse, status_code=status.HTTP_201_CREATED)
async def create_occurrence(
    company_id: str = Depends(get_current_company_id),
    payload: OccurrenceCreate = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Cria uma nova ocorrência.
    """
    try:
        company_uuid = UUID(company_id)
        
        # Valida que a empresa está correta
        if str(payload.company_id) != company_id:
            raise HTTPException(status_code=403, detail="Acesso negado")
        
        occurrence = Occurrence(
            company_id=company_uuid,
            employee_id=payload.employee_id,
            occurrence_date=payload.occurrence_date,
            occurrence_type=payload.occurrence_type,
            severity=payload.severity,
            description=payload.description,
            status="pending",
        )
        
        db.add(occurrence)
        await db.commit()
        await db.refresh(occurrence)
        
        logger.info(f"Ocorrência criada: {occurrence.id}")
        return OccurrenceResponse.model_validate(occurrence)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")
    except Exception as e:
        await db.rollback()
        logger.error(f"Erro ao criar ocorrência: {e}")
        raise HTTPException(status_code=500, detail="Erro ao criar ocorrência")


@router.put("/occurrences/{occurrence_id}", response_model=OccurrenceResponse)
async def update_occurrence(
    occurrence_id: str,
    company_id: str = Depends(get_current_company_id),
    payload: OccurrenceUpdate = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Atualiza uma ocorrência existente.
    """
    try:
        company_uuid = UUID(company_id)
        occurrence_uuid = UUID(occurrence_id)
        
        # Busca ocorrência
        result = await db.execute(
            select(Occurrence).where(
                and_(
                    Occurrence.id == occurrence_uuid,
                    Occurrence.company_id == company_uuid
                )
            )
        )
        occurrence = result.scalar_one_or_none()
        
        if not occurrence:
            raise HTTPException(status_code=404, detail="Ocorrência não encontrada")
        
        # Atualiza campos
        if payload.status:
            occurrence.status = payload.status
        
        if payload.resolution_notes:
            occurrence.resolution_notes = payload.resolution_notes
            if payload.status == "resolved":
                occurrence.resolved_at = datetime.now(timezone.utc)
        
        await db.commit()
        await db.refresh(occurrence)
        
        return OccurrenceResponse.model_validate(occurrence)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")
    except Exception as e:
        await db.rollback()
        logger.error(f"Erro ao atualizar ocorrência: {e}")
        raise HTTPException(status_code=500, detail="Erro ao atualizar ocorrência")


# ---------------------------------------------------------------------------
# Justificativas
# ---------------------------------------------------------------------------

@router.get("/justifications", response_model=PaginatedResponse)
async def list_justifications(
    company_id: str = Depends(get_current_company_id),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista justificativas com filtros opcionais.
    """
    try:
        company_uuid = UUID(company_id)
        
        # Query base
        query = select(Justification).where(Justification.company_id == company_uuid)
        
        # Filtro de status
        if status:
            query = query.where(Justification.status == status)
        
        # Contar total
        count_result = await db.execute(
            select(func.count(Justification.id)).where(
                Justification.company_id == company_uuid
            )
        )
        total = count_result.scalar() or 0
        
        # Paginar
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(Justification.created_at.desc())
        
        result = await db.execute(query)
        justifications = result.scalars().all()
        
        pages = (total + page_size - 1) // page_size
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "items": justifications,
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")
    except Exception as e:
        logger.error(f"Erro ao listar justificativas: {e}")
        raise HTTPException(status_code=500, detail="Erro ao listar justificativas")
