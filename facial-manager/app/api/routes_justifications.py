"""
API Routes — Gerenciamento de Justificativas

Endpoints:
- GET /api/v1/justifications/{company_id} — Listar justificativas com filtros
- GET /api/v1/justifications/{company_id}/{justification_id} — Detalhe de justificativa
- POST /api/v1/justifications/{company_id} — Criar nova justificativa
- PUT /api/v1/justifications/{company_id}/{justification_id}/approve — Aprovar
- PUT /api/v1/justifications/{company_id}/{justification_id}/reject — Rejeitar
- GET /api/v1/justifications/{company_id}/statistics — Estatísticas
- GET /api/v1/justifications/{company_id}/coverage — Verificar cobertura de período

Segurança:
- Todas as rotas exigem Bearer token JWT
- validate_company_access garante acesso à empresa
- Queries filtram por company_id em todas as operações (data isolation)
- Funcionário pode submeter justificativa para si ou para subordinados
- Apenas gerente/RH/contador pode aprovar/rejeitar
"""

import logging
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.orm import Session

from app.auth.permissions import get_current_user
from app.database.database import get_db
from app.dependencies import validate_company_access
from app.database.models_supabase import Company, Justification, EmployeeSupabase
from app.services.justification_service import JustificationService

logger = logging.getLogger("routes_justifications")

router = APIRouter(prefix="/api/v1/justifications", tags=["justifications"])


# ============================================================================
# Schemas (Pydantic)
# ============================================================================

from pydantic import BaseModel, Field


class JustificationCreate(BaseModel):
    """Criar nova justificativa."""
    employee_id: UUID = Field(..., description="ID do funcionário")
    justification_type: str = Field(
        ...,
        description="Tipo: medical, personal, work_related, court_order, other"
    )
    start_date: str = Field(..., description="Data inicial (YYYY-MM-DD)")
    end_date: str = Field(..., description="Data final (YYYY-MM-DD)")
    description: str = Field(..., description="Descrição detalhada")
    occurrence_id: Optional[UUID] = Field(None, description="ID da ocorrência relacionada")
    supporting_document_url: Optional[str] = Field(None, description="URL do documento")


class JustificationApprove(BaseModel):
    """Aprovar justificativa."""
    pass  # Apenas usa user_id do contexto


class JustificationReject(BaseModel):
    """Rejeitar justificativa."""
    rejection_reason: str = Field(..., description="Motivo da rejeição")


class JustificationResponse(BaseModel):
    """Resposta com dados de justificativa."""
    id: UUID
    company_id: UUID
    employee_id: UUID
    occurrence_id: Optional[UUID]
    justification_type: str
    start_date: datetime
    end_date: datetime
    description: str
    supporting_document_url: Optional[str]
    submitted_by: Optional[str]
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    status: str
    rejection_reason: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ListResponse(BaseModel):
    """Resposta padrão para listagens."""
    success: bool
    data: List[Any]
    pagination: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class DetailResponse(BaseModel):
    """Resposta padrão para detalhes."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/{company_id}", response_model=ListResponse)
async def list_justifications(
    company_id: UUID,
    user: Dict[str, Any] = Depends(get_current_user),
    company: Company = Depends(validate_company_access),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Página (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página"),
    status: Optional[str] = Query(None, description="Filtrar por status"),
    justification_type: Optional[str] = Query(None, description="Filtrar por tipo"),
    employee_id: Optional[UUID] = Query(None, description="Filtrar por funcionário"),
    start_date: Optional[str] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Data final (YYYY-MM-DD)"),
):
    """
    Lista justificativas da empresa com filtros e paginação.
    
    Filtros suportados:
    - status: pending, approved, rejected
    - justification_type: medical, personal, work_related, court_order, other
    - employee_id: UUID do funcionário
    - start_date, end_date: Intervalo de datas
    """
    try:
        # Monta filtros
        filters = {}
        if status:
            filters["status"] = status
        if justification_type:
            filters["justification_type"] = justification_type
        if employee_id:
            filters["employee_id"] = employee_id
        if start_date:
            filters["start_date"] = start_date
        if end_date:
            filters["end_date"] = end_date

        # Calcula skip/limit
        skip = (page - 1) * page_size

        # Lista justificativas
        justifications, total = JustificationService.list_justifications(
            db=db,
            company_id=company_id,
            filters=filters,
            skip=skip,
            limit=page_size,
        )

        # Monta resposta com paginação
        return ListResponse(
            success=True,
            data=[JustificationResponse.from_orm(j).dict() for j in justifications],
            pagination={
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size,
            },
            error=None,
        )

    except Exception as e:
        logger.error(f"Erro ao listar justificativas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao listar justificativas",
        )


@router.get("/{company_id}/{justification_id}", response_model=DetailResponse)
async def get_justification(
    company_id: UUID,
    justification_id: UUID,
    user: Dict[str, Any] = Depends(get_current_user),
    company: Company = Depends(validate_company_access),
    db: Session = Depends(get_db),
):
    """
    Obtém detalhes de uma justificativa específica.
    
    Validação de acesso: Usuário deve ter acesso à empresa.
    """
    try:
        justification = JustificationService.get_justification(
            db=db,
            company_id=company_id,
            justification_id=justification_id,
        )

        if not justification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Justificativa não encontrada",
            )

        return DetailResponse(
            success=True,
            data=JustificationResponse.from_orm(justification).dict(),
            error=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter justificativa: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter justificativa",
        )


@router.post("/{company_id}", response_model=DetailResponse, status_code=status.HTTP_201_CREATED)
async def create_justification(
    company_id: UUID,
    payload: JustificationCreate,
    user: Dict[str, Any] = Depends(get_current_user),
    company: Company = Depends(validate_company_access),
    db: Session = Depends(get_db),
):
    """
    Cria uma nova justificativa.
    
    Dados necessários:
    - employee_id: UUID do funcionário
    - justification_type: medical, personal, work_related, court_order, other
    - start_date: YYYY-MM-DD
    - end_date: YYYY-MM-DD
    - description: Descrição detalhada
    - occurrence_id: (opcional) ID da ocorrência
    - supporting_document_url: (opcional) URL do documento
    
    Validações:
    - Funcionário deve existir na empresa
    - Data inicial <= data final
    - Tipo deve ser válido
    """
    try:
        # Converte datas
        try:
            start_date_obj = datetime.fromisoformat(payload.start_date).date()
            end_date_obj = datetime.fromisoformat(payload.end_date).date()
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Datas inválidas. Use formato YYYY-MM-DD",
            )

        # Valida se funcionário existe
        employee = db.query(EmployeeSupabase).filter(
            EmployeeSupabase.id == payload.employee_id,
            EmployeeSupabase.company_id == company_id,
        ).first()

        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Funcionário não encontrado nesta empresa",
            )

        # Cria justificativa
        justification = JustificationService.create_justification(
            db=db,
            company_id=company_id,
            employee_id=payload.employee_id,
            justification_type=payload.justification_type,
            start_date=start_date_obj,
            end_date=end_date_obj,
            description=payload.description,
            occurrence_id=payload.occurrence_id,
            supporting_document_url=payload.supporting_document_url,
            submitted_by=user["id"],
        )

        if not justification:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Falha ao criar justificativa",
            )

        return DetailResponse(
            success=True,
            data=JustificationResponse.from_orm(justification).dict(),
            error=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar justificativa: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao criar justificativa",
        )


@router.put("/{company_id}/{justification_id}/approve", response_model=DetailResponse)
async def approve_justification(
    company_id: UUID,
    justification_id: UUID,
    payload: JustificationApprove,
    user: Dict[str, Any] = Depends(get_current_user),
    company: Company = Depends(validate_company_access),
    db: Session = Depends(get_db),
):
    """
    Aprova uma justificativa.
    
    Transição: pending → approved
    
    Requer permissão de gerente/RH/contador.
    """
    try:
        justification = JustificationService.get_justification(
            db=db,
            company_id=company_id,
            justification_id=justification_id,
        )

        if not justification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Justificativa não encontrada",
            )

        if justification.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Justificativa não está em status 'pending' (atual: {justification.status})",
            )

        updated = JustificationService.approve_justification(
            db=db,
            company_id=company_id,
            justification_id=justification_id,
            approved_by=user["id"],
        )

        if not updated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Falha ao aprovar justificativa",
            )

        return DetailResponse(
            success=True,
            data=JustificationResponse.from_orm(updated).dict(),
            error=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao aprovar justificativa: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao aprovar justificativa",
        )


@router.put("/{company_id}/{justification_id}/reject", response_model=DetailResponse)
async def reject_justification(
    company_id: UUID,
    justification_id: UUID,
    payload: JustificationReject,
    user: Dict[str, Any] = Depends(get_current_user),
    company: Company = Depends(validate_company_access),
    db: Session = Depends(get_db),
):
    """
    Rejeita uma justificativa.
    
    Transição: pending → rejected
    
    Requer permissão de gerente/RH/contador.
    """
    try:
        justification = JustificationService.get_justification(
            db=db,
            company_id=company_id,
            justification_id=justification_id,
        )

        if not justification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Justificativa não encontrada",
            )

        if justification.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Justificativa não está em status 'pending' (atual: {justification.status})",
            )

        updated = JustificationService.reject_justification(
            db=db,
            company_id=company_id,
            justification_id=justification_id,
            rejected_by=user["id"],
            rejection_reason=payload.rejection_reason,
        )

        if not updated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Falha ao rejeitar justificativa",
            )

        return DetailResponse(
            success=True,
            data=JustificationResponse.from_orm(updated).dict(),
            error=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao rejeitar justificativa: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao rejeitar justificativa",
        )


@router.get("/{company_id}/statistics", response_model=DetailResponse)
async def get_statistics(
    company_id: UUID,
    user: Dict[str, Any] = Depends(get_current_user),
    company: Company = Depends(validate_company_access),
    db: Session = Depends(get_db),
    start_date: Optional[str] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Data final (YYYY-MM-DD)"),
):
    """
    Retorna estatísticas de justificativas para um período.
    
    Se não informar datas, retorna do mês atual.
    """
    try:
        # Define datas padrão se não informadas
        today = date.today()
        if not start_date:
            start_date_obj = date(today.year, today.month, 1)
        else:
            start_date_obj = datetime.fromisoformat(start_date).date()

        if not end_date:
            end_date_obj = today
        else:
            end_date_obj = datetime.fromisoformat(end_date).date()

        stats = JustificationService.get_statistics(
            db=db,
            company_id=company_id,
            start_date=start_date_obj,
            end_date=end_date_obj,
        )

        return DetailResponse(
            success=True,
            data={
                "period": {
                    "start_date": str(start_date_obj),
                    "end_date": str(end_date_obj),
                },
                "statistics": stats,
            },
            error=None,
        )

    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter estatísticas",
        )


@router.get("/{company_id}/coverage", response_model=DetailResponse)
async def get_coverage(
    company_id: UUID,
    user: Dict[str, Any] = Depends(get_current_user),
    company: Company = Depends(validate_company_access),
    db: Session = Depends(get_db),
    employee_id: UUID = Query(..., description="ID do funcionário"),
    start_date: str = Query(..., description="Data inicial (YYYY-MM-DD)"),
    end_date: str = Query(..., description="Data final (YYYY-MM-DD)"),
):
    """
    Verifica cobertura de justificativas para um período de um funcionário.
    
    Retorna:
    - total_days: Total de dias no período
    - covered_days: Dias com justificativa aprovada
    - gap_days: Dias sem cobertura
    - coverage_percentage: Percentual de cobertura
    - gap_dates: Lista de datas sem cobertura
    """
    try:
        # Converte datas
        try:
            start_date_obj = datetime.fromisoformat(start_date).date()
            end_date_obj = datetime.fromisoformat(end_date).date()
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Datas inválidas. Use formato YYYY-MM-DD",
            )

        # Valida se funcionário existe
        employee = db.query(EmployeeSupabase).filter(
            EmployeeSupabase.id == employee_id,
            EmployeeSupabase.company_id == company_id,
        ).first()

        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Funcionário não encontrado nesta empresa",
            )

        # Obtém cobertura
        coverage = JustificationService.validate_justification_for_dates(
            db=db,
            company_id=company_id,
            employee_id=employee_id,
            start_date=start_date_obj,
            end_date=end_date_obj,
        )

        return DetailResponse(
            success=True,
            data={
                "employee_id": str(employee_id),
                "period": {
                    "start_date": str(start_date_obj),
                    "end_date": str(end_date_obj),
                },
                "coverage": coverage,
            },
            error=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter cobertura: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter cobertura",
        )
