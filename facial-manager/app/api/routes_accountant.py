"""
API do Portal do Contador - Endpoints principais.

Fluxo de Acesso:
1. get_current_user (autenticação JWT)
2. validate_company_access (autorização company_id)
3. Lógica de negócio + filtro de dados
4. Resposta JSON
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.auth.permissions import get_current_user, Permissions
from app.database.database import get_db
from app.database.models_supabase import (
    Company, CompanyUser, EmployeeSupabase, TimeRecord, 
    WorkPeriod, Occurrence, Justification
)
from app.dependencies import validate_company_access, get_user_companies, get_user_role_in_company

router = APIRouter(prefix="/api/v1/accountant", tags=["Portal do Contador"])
logger = logging.getLogger("accountant_routes")


# ============================================================================
# PERFIL DO CONTADOR
# ============================================================================

@router.get("/me")
async def get_my_profile(
    user: Dict[str, Any] = Depends(get_current_user),
    companies: List[UUID] = Depends(get_user_companies),
    db: Session = Depends(get_db)
):
    """Retorna perfil do contador autenticado."""
    try:
        # Obtém dados das empresas
        company_list = db.query(Company).filter(
            Company.id.in_(companies)
        ).all()
        
        companies_data = [
            {
                "id": str(c.id),
                "name": c.name,
                "cnpj": c.cnpj,
                "role": "accountant" if c.accountant_id == user["id"] else "user"
            }
            for c in company_list
        ]
        
        return {
            "success": True,
            "data": {
                "user_id": user["id"],
                "email": user["email"],
                "companies": companies_data,
                "total_companies": len(companies_data)
            }
        }
    except Exception as e:
        logger.error(f"Erro ao obter perfil: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter perfil"
        )


# ============================================================================
# EMPRESAS DO CONTADOR
# ============================================================================

@router.get("/companies")
async def list_companies(
    user: Dict[str, Any] = Depends(get_current_user),
    companies: List[UUID] = Depends(get_user_companies),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, max_length=100),
):
    """
    Lista empresas do contador.
    
    Filtros:
    - search: busca por nome ou CNPJ
    - page/page_size: paginação
    """
    try:
        query = db.query(Company).filter(Company.id.in_(companies))
        
        # Filtro por busca
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (Company.name.ilike(search_term)) |
                (Company.cnpj.ilike(search_term))
            )
        
        # Total para paginação
        total = query.count()
        
        # Pagina
        skip = (page - 1) * page_size
        companies_list = query.offset(skip).limit(page_size).all()
        
        # Enriquece com stats
        companies_data = []
        for company in companies_list:
            # Conta funcionários
            employees_count = db.query(EmployeeSupabase).filter(
                EmployeeSupabase.company_id == company.id,
                EmployeeSupabase.is_active == True
            ).count()
            
            # Obtém período atual
            current_date = datetime.now()
            period = db.query(WorkPeriod).filter(
                WorkPeriod.company_id == company.id,
                WorkPeriod.year == current_date.year,
                WorkPeriod.month == current_date.month
            ).first()
            
            companies_data.append({
                "id": str(company.id),
                "name": company.name,
                "cnpj": company.cnpj,
                "city": company.city,
                "state": company.state,
                "employees_count": employees_count,
                "period_status": period.status if period else "not_created",
                "accountant_id": str(company.accountant_id) if company.accountant_id else None
            })
        
        return {
            "success": True,
            "data": companies_data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size
            }
        }
    except Exception as e:
        logger.error(f"Erro ao listar empresas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao listar empresas"
        )


@router.get("/companies/{company_id}")
async def get_company(
    company_id: UUID,
    user: Dict[str, Any] = Depends(get_current_user),
    company: Company = Depends(validate_company_access),
    db: Session = Depends(get_db)
):
    """Retorna detalhes de uma empresa (com validação de acesso)."""
    try:
        employees_count = db.query(EmployeeSupabase).filter(
            EmployeeSupabase.company_id == company.id,
            EmployeeSupabase.is_active == True
        ).count()
        
        time_records_count = db.query(TimeRecord).filter(
            TimeRecord.company_id == company.id
        ).count()
        
        occurrences_count = db.query(Occurrence).filter(
            Occurrence.company_id == company.id,
            Occurrence.status == "pending"
        ).count()
        
        return {
            "success": True,
            "data": {
                "id": str(company.id),
                "name": company.name,
                "cnpj": company.cnpj,
                "address": company.address,
                "city": company.city,
                "state": company.state,
                "timezone": company.timezone,
                "work_hours": company.work_hours,
                "accountant_id": str(company.accountant_id) if company.accountant_id else None,
                "statistics": {
                    "employees": employees_count,
                    "time_records": time_records_count,
                    "pending_occurrences": occurrences_count
                }
            }
        }
    except Exception as e:
        logger.error(f"Erro ao obter empresa: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter empresa"
        )


# ============================================================================
# FUNCIONÁRIOS
# ============================================================================

@router.get("/companies/{company_id}/employees")
async def get_employees(
    company_id: UUID,
    user: Dict[str, Any] = Depends(get_current_user),
    company: Company = Depends(validate_company_access),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None, max_length=100)
):
    """Lista funcionários da empresa (com filtro de company_id)."""
    try:
        query = db.query(EmployeeSupabase).filter(
            EmployeeSupabase.company_id == company.id,
            EmployeeSupabase.is_active == True
        )
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(EmployeeSupabase.full_name.ilike(search_term))
        
        total = query.count()
        skip = (page - 1) * page_size
        
        employees = query.order_by(EmployeeSupabase.full_name).offset(skip).limit(page_size).all()
        
        employees_data = [
            {
                "id": str(emp.id),
                "name": emp.full_name,
                "department": emp.department,
                "registration_number": emp.registration_number,
                "email": emp.email,
                "is_active": emp.is_active
            }
            for emp in employees
        ]
        
        return {
            "success": True,
            "data": employees_data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size
            }
        }
    except Exception as e:
        logger.error(f"Erro ao listar funcionários: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao listar funcionários"
        )


# ============================================================================
# REGISTROS DE PONTO (ESPELHO)
# ============================================================================

@router.get("/companies/{company_id}/time-records")
async def get_time_records(
    company_id: UUID,
    user: Dict[str, Any] = Depends(get_current_user),
    company: Company = Depends(validate_company_access),
    db: Session = Depends(get_db),
    employee_id: Optional[UUID] = Query(None),
    year: int = Query(datetime.now().year, ge=2020, le=2100),
    month: int = Query(datetime.now().month, ge=1, le=12),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500)
):
    """Lista registros de ponto do mês (com filtro de company_id)."""
    try:
        query = db.query(TimeRecord).filter(
            TimeRecord.company_id == company.id
        )
        
        if employee_id:
            query = query.filter(TimeRecord.employee_id == employee_id)
        
        # Filtra por período
        from datetime import date
        from dateutil.relativedelta import relativedelta
        
        start_date = date(year, month, 1)
        end_date = start_date + relativedelta(months=1) - relativedelta(days=1)
        
        query = query.filter(
            TimeRecord.record_date >= start_date,
            TimeRecord.record_date <= end_date
        )
        
        total = query.count()
        skip = (page - 1) * page_size
        
        records = query.order_by(
            TimeRecord.record_date.desc(),
            TimeRecord.record_time.desc()
        ).offset(skip).limit(page_size).all()
        
        records_data = [
            {
                "id": str(record.id),
                "employee_id": str(record.employee_id),
                "employee_name": record.employee_name,
                "date": record.record_date.isoformat(),
                "time": record.record_time,
                "type": record.record_type,
                "source": record.source,
                "is_adjusted": record.is_adjusted
            }
            for record in records
        ]
        
        return {
            "success": True,
            "data": records_data,
            "period": {"year": year, "month": month},
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size
            }
        }
    except Exception as e:
        logger.error(f"Erro ao listar registros de ponto: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao listar registros de ponto"
        )


# ============================================================================
# OCORRÊNCIAS
# ============================================================================

@router.get("/companies/{company_id}/occurrences")
async def get_occurrences(
    company_id: UUID,
    user: Dict[str, Any] = Depends(get_current_user),
    company: Company = Depends(validate_company_access),
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200)
):
    """Lista ocorrências da empresa (com filtro de company_id)."""
    try:
        query = db.query(Occurrence).filter(
            Occurrence.company_id == company.id
        )
        
        if status:
            query = query.filter(Occurrence.status == status)
        
        total = query.count()
        skip = (page - 1) * page_size
        
        occurrences = query.order_by(
            Occurrence.occurrence_date.desc()
        ).offset(skip).limit(page_size).all()
        
        occurrences_data = [
            {
                "id": str(occ.id),
                "employee_id": str(occ.employee_id),
                "employee_name": occ.employee.full_name if occ.employee else "Desconhecido",
                "date": occ.occurrence_date.isoformat(),
                "type": occ.occurrence_type,
                "severity": occ.severity,
                "status": occ.status,
                "description": occ.description
            }
            for occ in occurrences
        ]
        
        return {
            "success": True,
            "data": occurrences_data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size
            }
        }
    except Exception as e:
        logger.error(f"Erro ao listar ocorrências: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao listar ocorrências"
        )


# ============================================================================
# PERÍODOS
# ============================================================================

@router.get("/companies/{company_id}/periods")
async def get_periods(
    company_id: UUID,
    user: Dict[str, Any] = Depends(get_current_user),
    company: Company = Depends(validate_company_access),
    db: Session = Depends(get_db),
    year: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100)
):
    """Lista períodos da empresa (com filtro de company_id)."""
    try:
        query = db.query(WorkPeriod).filter(
            WorkPeriod.company_id == company.id
        )
        
        if year:
            query = query.filter(WorkPeriod.year == year)
        
        total = query.count()
        skip = (page - 1) * page_size
        
        periods = query.order_by(
            WorkPeriod.year.desc(),
            WorkPeriod.month.desc()
        ).offset(skip).limit(page_size).all()
        
        periods_data = [
            {
                "id": str(period.id),
                "year": period.year,
                "month": period.month,
                "label": f"{period.month:02d}/{period.year}",
                "status": period.status,
                "closed_at": period.closed_at.isoformat() if period.closed_at else None,
                "closed_by": period.closed_by,
                "statistics": period.statistics
            }
            for period in periods
        ]
        
        return {
            "success": True,
            "data": periods_data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size
            }
        }
    except Exception as e:
        logger.error(f"Erro ao listar períodos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao listar períodos"
        )


# ============================================================================
# DASHBOARD AGREGADO
# ============================================================================

@router.get("/dashboard")
async def get_dashboard(
    user: Dict[str, Any] = Depends(get_current_user),
    companies: List[UUID] = Depends(get_user_companies),
    db: Session = Depends(get_db)
):
    """
    Dashboard agregado de todas as empresas do contador.
    
    Retorna estatísticas consolidadas.
    """
    try:
        stats = {
            "companies": len(companies),
            "total_employees": 0,
            "total_time_records": 0,
            "pending_occurrences": 0,
            "open_periods": 0,
            "closed_periods": 0,
            "pending_justifications": 0
        }
        
        for company_id in companies:
            # Funcionários
            stats["total_employees"] += db.query(EmployeeSupabase).filter(
                EmployeeSupabase.company_id == company_id,
                EmployeeSupabase.is_active == True
            ).count()
            
            # Registros de ponto
            stats["total_time_records"] += db.query(TimeRecord).filter(
                TimeRecord.company_id == company_id
            ).count()
            
            # Ocorrências pendentes
            stats["pending_occurrences"] += db.query(Occurrence).filter(
                Occurrence.company_id == company_id,
                Occurrence.status == "pending"
            ).count()
            
            # Períodos
            open_p = db.query(WorkPeriod).filter(
                WorkPeriod.company_id == company_id,
                WorkPeriod.status.in_(["open", "reviewing"])
            ).count()
            stats["open_periods"] += open_p
            
            closed_p = db.query(WorkPeriod).filter(
                WorkPeriod.company_id == company_id,
                WorkPeriod.status == "closed"
            ).count()
            stats["closed_periods"] += closed_p
            
            # Justificativas pendentes
            stats["pending_justifications"] += db.query(Justification).filter(
                Justification.company_id == company_id,
                Justification.status == "pending"
            ).count()
        
        return {
            "success": True,
            "data": {
                "user_id": user["id"],
                "companies_count": len(companies),
                "statistics": stats,
                "generated_at": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Erro ao gerar dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao gerar dashboard"
        )


# ============================================================================
# JUSTIFICATIVAS
# ============================================================================

@router.get("/companies/{company_id}/justifications")
async def get_justifications(
    company_id: UUID,
    user: Dict[str, Any] = Depends(get_current_user),
    company: Company = Depends(validate_company_access),
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None, description="Filtrar por status: pending, approved, rejected"),
    justification_type: Optional[str] = Query(None, description="Filtrar por tipo: medical, personal, work_related, court_order, other"),
    employee_id: Optional[UUID] = Query(None, description="Filtrar por funcionário"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200)
):
    """
    Lista justificativas da empresa (com filtro de company_id).
    
    Filtros:
    - status: pending, approved, rejected
    - justification_type: medical, personal, work_related, court_order, other
    - employee_id: UUID do funcionário
    """
    try:
        query = db.query(Justification).filter(
            Justification.company_id == company.id
        )
        
        if status:
            query = query.filter(Justification.status == status)
        
        if justification_type:
            query = query.filter(Justification.justification_type == justification_type)
        
        if employee_id:
            query = query.filter(Justification.employee_id == employee_id)
        
        total = query.count()
        skip = (page - 1) * page_size
        
        justifications = query.order_by(
            Justification.start_date.desc()
        ).offset(skip).limit(page_size).all()
        
        justifications_data = [
            {
                "id": str(j.id),
                "employee_id": str(j.employee_id),
                "employee_name": j.employee.full_name if j.employee else "Desconhecido",
                "occurrence_id": str(j.occurrence_id) if j.occurrence_id else None,
                "type": j.justification_type,
                "start_date": j.start_date.isoformat(),
                "end_date": j.end_date.isoformat(),
                "description": j.description,
                "status": j.status,
                "submitted_by": j.submitted_by,
                "approved_by": j.approved_by,
                "approved_at": j.approved_at.isoformat() if j.approved_at else None,
                "rejection_reason": j.rejection_reason,
            }
            for j in justifications
        ]
        
        return {
            "success": True,
            "data": justifications_data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size
            }
        }
    except Exception as e:
        logger.error(f"Erro ao listar justificativas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao listar justificativas"
        )


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def health():
    """Health check do portal do contador."""
    return {
        "status": "ok",
        "service": "accountant-portal",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }