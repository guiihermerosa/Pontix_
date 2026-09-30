"""
API Routes — Gerenciamento de Ocorrências

Endpoints:
- GET /api/v1/occurrences/{company_id} — Listar ocorrências com filtros
- GET /api/v1/occurrences/{company_id}/{occurrence_id} — Detalhe de ocorrência
- PUT /api/v1/occurrences/{company_id}/{occurrence_id}/status — Atualizar status
- PUT /api/v1/occurrences/{company_id}/{occurrence_id}/assign — Atribuir a usuário
- DELETE /api/v1/occurrences/{company_id}/{occurrence_id} — Remover (soft delete)
- GET /api/v1/occurrences/{company_id}/statistics — Estatísticas
- POST /api/v1/occurrences/{company_id}/detect — Detectar ocorrências para um dia

Segurança:
- Todas as rotas exigem Bearer token JWT
- validate_company_access garante que usuário tem acesso à empresa
- Queries filtram por company_id em todas as operações (data isolation)
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
from app.database.models_supabase import Company, Occurrence, EmployeeSupabase
from app.services.occurrence_service import OccurrenceService

logger = logging.getLogger("routes_occurrences")

router = APIRouter(prefix="/api/v1/occurrences", tags=["occurrences"])


# ============================================================================
# Schemas (Pydantic)
# ============================================================================

from pydantic import BaseModel, Field


class OccurrenceBase(BaseModel):
    """Dados base de uma ocorrência."""
    occurrence_type: str = Field(..., description="Tipo: late, absence, early_exit, etc.")
    severity: Optional[str] = Field(None, description="Severidade: low, medium, high, critical")
    description: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class OccurrenceStatusUpdate(BaseModel):
    """Atualizar status de uma ocorrência."""
    new_status: str = Field(..., description="Novo status: pending, reviewed, resolved, dismissed")
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None


class OccurrenceAssign(BaseModel):
    """Atribuir ocorrência a um usuário."""
    assigned_to: str = Field(..., description="ID do usuário responsável")


class OccurrenceDetect(BaseModel):
    """Detectar ocorrências para uma data."""
    employee_id: UUID = Field(..., description="ID do funcionário")
    occurrence_date: str = Field(..., description="Data em formato YYYY-MM-DD")
    assign_to: Optional[str] = Field(None, description="Atribuir a este usuário")


class OccurrenceResponse(BaseModel):
    """Resposta com dados de ocorrência."""
    id: UUID
    company_id: UUID
    employee_id: UUID
    occurrence_date: datetime
    occurrence_type: str
    severity: str
    status: str
    description: Optional[str]
    details: Optional[Dict[str, Any]]
    assigned_to: Optional[str]
    resolved_by: Optional[str]
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]
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
async def list_occurrences(
    company_id: UUID,
    user: Dict[str, Any] = Depends(get_current_user),
    company: Company = Depends(validate_company_access),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Página (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página"),
    status: Optional[str] = Query(None, description="Filtrar por status"),
    occurrence_type: Optional[str] = Query(None, description="Filtrar por tipo"),
    severity: Optional[str] = Query(None, description="Filtrar por severidade"),
    employee_id: Optional[UUID] = Query(None, description="Filtrar por funcionário"),
    start_date: Optional[str] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Data final (YYYY-MM-DD)"),
):
    """
    Lista ocorrências da empresa com filtros e paginação.
    
    Filtros suportados:
    - status: pending, reviewed, resolved, dismissed
    - occurrence_type: late, absence, early_exit, incomplete_day, missing_break, excessive_hours
    - severity: low, medium, high, critical
    - employee_id: UUID do funcionário
    - start_date, end_date: Intervalo de datas
    """
    try:
        # Monta filtros
        filters = {}
        if status:
            filters["status"] = status
        if occurrence_type:
            filters["occurrence_type"] = occurrence_type
        if severity:
            filters["severity"] = severity
        if employee_id:
            filters["employee_id"] = employee_id
        if start_date:
            filters["start_date"] = start_date
        if end_date:
            filters["end_date"] = end_date

        # Calcula skip/limit
        skip = (page - 1) * page_size

        # Lista ocorrências
        occurrences, total = OccurrenceService.list_occurrences(
            db=db,
            company_id=company_id,
            filters=filters,
            skip=skip,
            limit=page_size,
        )

        # Monta resposta com paginação
        return ListResponse(
            success=True,
            data=[OccurrenceResponse.from_orm(occ).dict() for occ in occurrences],
            pagination={
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size,
            },
            error=None,
        )

    except Exception as e:
        logger.error(f"Erro ao listar ocorrências: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao listar ocorrências",
        )


@router.get("/{company_id}/{occurrence_id}", response_model=DetailResponse)
async def get_occurrence(
    company_id: UUID,
    occurrence_id: UUID,
    user: Dict[str, Any] = Depends(get_current_user),
    company: Company = Depends(validate_company_access),
    db: Session = Depends(get_db),
):
    """
    Obtém detalhes de uma ocorrência específica.
    
    Validação de acesso: Usuário deve ter acesso à empresa.
    """
    try:
        occurrence = OccurrenceService.get_occurrence(
            db=db,
            company_id=company_id,
            occurrence_id=occurrence_id,
        )

        if not occurrence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ocorrência não encontrada",
            )

        return DetailResponse(
            success=True,
            data=OccurrenceResponse.from_orm(occurrence).dict(),
            error=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter ocorrência: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter ocorrência",
        )


@router.put("/{company_id}/{occurrence_id}/status", response_model=DetailResponse)
async def update_occurrence_status(
    company_id: UUID,
    occurrence_id: UUID,
    payload: OccurrenceStatusUpdate,
    user: Dict[str, Any] = Depends(get_current_user),
    company: Company = Depends(validate_company_access),
    db: Session = Depends(get_db),
):
    """
    Atualiza o status de uma ocorrência.
    
    Transições de status válidas:
    - pending → reviewed, resolved, dismissed
    - reviewed → resolved, dismissed
    - resolved → (terminal)
    - dismissed → (terminal)
    
    Requer permissão de gerente/RH.
    """
    try:
        # Valida novo status
        valid_statuses = ["pending", "reviewed", "resolved", "dismissed"]
        if payload.new_status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Status inválido. Válidos: {', '.join(valid_statuses)}",
            )

        # Obtém ocorrência atual
        occurrence = OccurrenceService.get_occurrence(
            db=db,
            company_id=company_id,
            occurrence_id=occurrence_id,
        )

        if not occurrence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ocorrência não encontrada",
            )

        # Atualiza status
        updated = OccurrenceService.update_occurrence_status(
            db=db,
            company_id=company_id,
            occurrence_id=occurrence_id,
            new_status=payload.new_status,
            resolved_by=payload.resolved_by or user["id"],
            resolution_notes=payload.resolution_notes,
        )

        if not updated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Falha ao atualizar status da ocorrência",
            )

        return DetailResponse(
            success=True,
            data=OccurrenceResponse.from_orm(updated).dict(),
            error=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao atualizar status",
        )


@router.put("/{company_id}/{occurrence_id}/assign", response_model=DetailResponse)
async def assign_occurrence(
    company_id: UUID,
    occurrence_id: UUID,
    payload: OccurrenceAssign,
    user: Dict[str, Any] = Depends(get_current_user),
    company: Company = Depends(validate_company_access),
    db: Session = Depends(get_db),
):
    """
    Atribui uma ocorrência a um usuário (gerente/RH).
    
    Requer permissão de gerente/RH ou contador.
    """
    try:
        occurrence = OccurrenceService.get_occurrence(
            db=db,
            company_id=company_id,
            occurrence_id=occurrence_id,
        )

        if not occurrence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ocorrência não encontrada",
            )

        updated = OccurrenceService.assign_occurrence(
            db=db,
            company_id=company_id,
            occurrence_id=occurrence_id,
            assigned_to=payload.assigned_to,
        )

        if not updated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Falha ao atribuir ocorrência",
            )

        return DetailResponse(
            success=True,
            data=OccurrenceResponse.from_orm(updated).dict(),
            error=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atribuir ocorrência: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao atribuir ocorrência",
        )


@router.delete("/{company_id}/{occurrence_id}", response_model=DetailResponse)
async def delete_occurrence(
    company_id: UUID,
    occurrence_id: UUID,
    user: Dict[str, Any] = Depends(get_current_user),
    company: Company = Depends(validate_company_access),
    db: Session = Depends(get_db),
):
    """
    Remove uma ocorrência (soft delete).
    
    Na verdade marca como 'dismissed' em vez de deletar fisicamente.
    
    Requer permissão de gerente/RH ou contador.
    """
    try:
        occurrence = OccurrenceService.get_occurrence(
            db=db,
            company_id=company_id,
            occurrence_id=occurrence_id,
        )

        if not occurrence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ocorrência não encontrada",
            )

        success = OccurrenceService.delete_occurrence(
            db=db,
            company_id=company_id,
            occurrence_id=occurrence_id,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Falha ao remover ocorrência",
            )

        return DetailResponse(
            success=True,
            data={"id": occurrence_id, "status": "dismissed"},
            error=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao remover ocorrência: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao remover ocorrência",
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
    Retorna estatísticas de ocorrências para um período.
    
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

        stats = OccurrenceService.get_statistics(
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


@router.post("/{company_id}/detect", response_model=ListResponse)
async def detect_occurrences(
    company_id: UUID,
    payload: OccurrenceDetect,
    user: Dict[str, Any] = Depends(get_current_user),
    company: Company = Depends(validate_company_access),
    db: Session = Depends(get_db),
):
    """
    Detecta ocorrências para um funcionário em uma data específica.
    
    Cria registros de Occurrence para cada incidente detectado.
    
    Payload:
    - employee_id: UUID do funcionário
    - occurrence_date: Data em formato YYYY-MM-DD
    - assign_to: Atribuir a este usuário (opcional)
    
    Retorna lista de ocorrências criadas.
    """
    try:
        # Converte data
        try:
            occurrence_date = datetime.fromisoformat(payload.occurrence_date).date()
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Data inválida. Use formato YYYY-MM-DD",
            )

        # Valida se funcionário existe e pertence à empresa
        employee = db.query(EmployeeSupabase).filter(
            EmployeeSupabase.id == payload.employee_id,
            EmployeeSupabase.company_id == company_id,
        ).first()

        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Funcionário não encontrado nesta empresa",
            )

        # Detecta e cria ocorrências
        created_occurrences = OccurrenceService.create_occurrences_from_detection(
            db=db,
            company_id=company_id,
            employee_id=payload.employee_id,
            occurrence_date=occurrence_date,
            assigned_to=payload.assign_to or user["id"],
        )

        return ListResponse(
            success=True,
            data=[OccurrenceResponse.from_orm(occ).dict() for occ in created_occurrences],
            pagination=None,
            error=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao detectar ocorrências: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao detectar ocorrências",
        )
