"""
Rotas para visualização organizada de batidas (espelho de ponto).
"""
import logging
from datetime import date, datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.auth.permissions import (
    get_current_user, Permissions
)
from app.database.database import get_db
from app.dependencies import validate_company_access
from app.services.attendance_view_service import AttendanceViewService

router = APIRouter(prefix="/time-view", tags=["Visualização de Batidas"])
logger = logging.getLogger("time_view_routes")


@router.get("/monthly")
async def get_monthly_time_view(
    company_id: UUID,
    employee_id: Optional[UUID] = Query(None, description="ID do funcionário (opcional)"),
    year: Optional[int] = Query(None, ge=2020, le=2100, description="Ano (opcional)"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Mês 1-12 (opcional)"),
    include_stats: bool = Query(True, description="Incluir estatísticas"),
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: Any = Depends(validate_company_access)
):
    """
    Retorna visualização mensal (espelho de ponto).
    
    Requer permissão TIMERECORD_VIEW para a empresa.
    """
    try:
        service = AttendanceViewService(db)
        
        monthly_view = service.get_monthly_view(
            company_id=company_id,
            employee_id=employee_id,
            year=year,
            month=month,
            include_statistics=include_stats
        )
        
        return {
            "success": True,
            "data": monthly_view,
            "filters": {
                "company_id": str(company_id),
                "employee_id": str(employee_id) if employee_id else "all",
                "year": year or datetime.now().year,
                "month": month or datetime.now().month,
                "include_stats": include_stats
            },
            "generated_at": datetime.now().isoformat()
        }
        
    except ValueError as e:
        logger.error(f"Erro de validação na visualização mensal: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Erro ao gerar visualização mensal: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao gerar visualização mensal"
        )


@router.get("/daily")
async def get_daily_time_view(
    company_id: UUID,
    target_date: Optional[date] = Query(None, description="Data (opcional, padrão: hoje)"),
    employee_id: Optional[UUID] = Query(None, description="ID do funcionário (opcional)"),
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: Any = Depends(validate_company_access)
):
    """
    Retorna visualização detalhada de um dia específico.
    
    Requer permissão TIMERECORD_VIEW para a empresa.
    """
    try:
        service = AttendanceViewService(db)
        
        daily_view = service.get_daily_view(
            company_id=company_id,
            target_date=target_date,
            employee_id=employee_id
        )
        
        return {
            "success": True,
            "data": daily_view,
            "filters": {
                "company_id": str(company_id),
                "employee_id": str(employee_id) if employee_id else "all",
                "date": target_date.isoformat() if target_date else date.today().isoformat()
            },
            "generated_at": datetime.now().isoformat()
        }
        
    except ValueError as e:
        logger.error(f"Erro de validação na visualização diária: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Erro ao gerar visualização diária: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao gerar visualização diária"
        )


@router.get("/employee/{employee_id}/timeline")
async def get_employee_timeline(
    employee_id: UUID,
    start_date: date = Query(..., description="Data inicial"),
    end_date: date = Query(..., description="Data final"),
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retorna timeline de registros de um funcionário.
    
    Verifica se o usuário tem acesso à empresa do funcionário.
    """
    try:
        from app.database.models_cloud import EmployeeSupabase, CompanyUser
        
        # Obtém funcionário e verifica acesso
        employee = db.query(EmployeeSupabase).filter(
            EmployeeSupabase.id == employee_id
        ).first()
        
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Funcionário não encontrado"
            )
        
        # Verifica se usuário tem acesso à empresa do funcionário
        has_access = db.query(CompanyUser).filter(
            CompanyUser.user_id == user["id"],
            CompanyUser.company_id == employee.company_id,
            CompanyUser.invitation_status == "accepted"
        ).first()
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuário não tem acesso a este funcionário"
            )
        
        service = AttendanceViewService(db)
        
        timeline = service.get_employee_timeline(
            employee_id=employee_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return {
            "success": True,
            "data": {
                "employee": {
                    "id": str(employee.id),
                    "name": employee.full_name,
                    "department": employee.department
                },
                "timeline": timeline,
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": (end_date - start_date).days + 1
                }
            },
            "filters": {
                "employee_id": str(employee_id),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "generated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao gerar timeline: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao gerar timeline do funcionário"
        )


@router.get("/employee/{employee_id}/summary")
async def get_employee_summary(
    employee_id: UUID,
    year: Optional[int] = Query(None, ge=2020, le=2100, description="Ano (opcional)"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Mês 1-12 (opcional)"),
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retorna resumo mensal de um funcionário.
    """
    try:
        from app.database.models_cloud import EmployeeSupabase, CompanyUser
        
        # Obtém funcionário e verifica acesso
        employee = db.query(EmployeeSupabase).filter(
            EmployeeSupabase.id == employee_id
        ).first()
        
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Funcionário não encontrado"
            )
        
        # Verifica acesso
        has_access = db.query(CompanyUser).filter(
            CompanyUser.user_id == user["id"],
            CompanyUser.company_id == employee.company_id,
            CompanyUser.invitation_status == "accepted"
        ).first()
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuário não tem acesso a este funcionário"
            )
        
        service = AttendanceViewService(db)
        
        # Usa ano/mês atual se não especificado
        current_date = datetime.now()
        target_year = year or current_date.year
        target_month = month or current_date.month
        
        monthly_view = service.get_monthly_view(
            company_id=employee.company_id,
            employee_id=employee_id,
            year=target_year,
            month=target_month,
            include_statistics=True
        )
        
        # Extrai dados do funcionário
        employee_data = None
        if monthly_view.get("employees"):
            employee_data = monthly_view["employees"][0]
        
        return {
            "success": True,
            "data": {
                "employee": {
                    "id": str(employee.id),
                    "name": employee.full_name,
                    "department": employee.department,
                    "registration_number": employee.registration_number
                },
                "period": monthly_view["period"],
                "summary": employee_data.get("summary") if employee_data else None,
                "statistics": employee_data.get("statistics") if employee_data else None,
                "days_count": len(employee_data.get("days", [])) if employee_data else 0
            },
            "period": {
                "year": target_year,
                "month": target_month,
                "label": f"{target_month:02d}/{target_year}"
            },
            "generated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao gerar resumo do funcionário: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao gerar resumo do funcionário"
        )


@router.get("/company/{company_id}/daily-summary")
async def get_company_daily_summary(
    company_id: UUID,
    target_date: Optional[date] = Query(None, description="Data (opcional, padrão: hoje)"),
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: Any = Depends(validate_company_access)
):
    """
    Retorna resumo diário de toda a empresa.
    
    Requer permissão TIMERECORD_VIEW para a empresa.
    """
    try:
        service = AttendanceViewService(db)
        
        daily_view = service.get_daily_view(
            company_id=company_id,
            target_date=target_date,
            employee_id=None  # Todos os funcionários
        )
        
        # Agrupa por status
        status_groups = {
            "present": [],
            "absent": [],
            "incomplete": [],
            "delayed": [],
            "early_exit": []
        }
        
        for employee in daily_view["employees"]:
            if employee["status"] == "present":
                status_groups["present"].append(employee["employee"]["name"])
            
            if employee["status"] == "absent":
                status_groups["absent"].append(employee["employee"]["name"])
            
            if employee.get("has_incomplete_records"):
                status_groups["incomplete"].append(employee["employee"]["name"])
            
            if employee.get("has_delay"):
                status_groups["delayed"].append(employee["employee"]["name"])
            
            if employee.get("has_early_exit"):
                status_groups["early_exit"].append(employee["employee"]["name"])
        
        return {
            "success": True,
            "data": {
                "date": daily_view["date"],
                "statistics": daily_view["statistics"],
                "status_groups": status_groups,
                "total_employees": daily_view["statistics"]["total_employees"],
                "work_hours": daily_view["work_hours"]
            },
            "filters": {
                "company_id": str(company_id),
                "date": target_date.isoformat() if target_date else date.today().isoformat()
            },
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao gerar resumo diário da empresa: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao gerar resumo diário da empresa"
        )


@router.get("/filters")
async def get_time_view_filters(
    company_id: UUID,
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: Any = Depends(validate_company_access)
):
    """
    Retorna opções de filtro para visualização de batidas.
    """
    try:
        from app.database.models_cloud import EmployeeSupabase
        
        # Obtém funcionários ativos
        employees = db.query(EmployeeSupabase).filter(
            EmployeeSupabase.company_id == company_id,
            EmployeeSupabase.is_active == True
        ).order_by(EmployeeSupabase.full_name).all()
        
        # Obtém anos/meses com registros
        from sqlalchemy import extract
        from app.database.models_cloud import TimeRecord
        
        years_with_data = db.query(
            extract('year', TimeRecord.record_date).label('year')
        ).filter(
            TimeRecord.company_id == company_id
        ).distinct().order_by('year desc').all()
        
        # Formata opções
        employee_options = [
            {
                "value": str(emp.id),
                "label": emp.full_name,
                "department": emp.department
            }
            for emp in employees
        ]
        
        year_options = sorted(set([int(y.year) for y in years_with_data]), reverse=True)
        
        # Adiciona ano atual se não existir
        current_year = datetime.now().year
        if current_year not in year_options:
            year_options.insert(0, current_year)
        
        month_options = [
            {"value": 1, "label": "Janeiro"},
            {"value": 2, "label": "Fevereiro"},
            {"value": 3, "label": "Março"},
            {"value": 4, "label": "Abril"},
            {"value": 5, "label": "Maio"},
            {"value": 6, "label": "Junho"},
            {"value": 7, "label": "Julho"},
            {"value": 8, "label": "Agosto"},
            {"value": 9, "label": "Setembro"},
            {"value": 10, "label": "Outubro"},
            {"value": 11, "label": "Novembro"},
            {"value": 12, "label": "Dezembro"}
        ]
        
        return {
            "success": True,
            "data": {
                "employees": employee_options,
                "years": year_options,
                "months": month_options,
                "status_options": [
                    {"value": "present", "label": "Presente"},
                    {"value": "absent", "label": "Ausente"},
                    {"value": "incomplete", "label": "Registro Incompleto"},
                    {"value": "delayed", "label": "Atrasado"},
                    {"value": "early_exit", "label": "Saída Antecipada"}
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter filtros: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter opções de filtro"
        )


@router.get("/export/monthly")
async def export_monthly_view(
    company_id: UUID,
    year: int = Query(..., ge=2020, le=2100, description="Ano"),
    month: int = Query(..., ge=1, le=12, description="Mês 1-12"),
    format: str = Query("json", description="Formato: json, csv, excel"),
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: Any = Depends(validate_company_access)
):
    """
    Exporta visualização mensal em diferentes formatos.
    
    Requer permissão REPORT_EXPORT para a empresa.
    """
    try:
        service = AttendanceViewService(db)
        
        monthly_view = service.get_monthly_view(
            company_id=company_id,
            employee_id=None,  # Todos funcionários
            year=year,
            month=month,
            include_statistics=True
        )
        
        # Placeholder para implementação de exportação
        # A implementação real seria em um serviço de exportação separado
        
        return {
            "success": True,
            "message": f"Exportação do período {month:02d}/{year} gerada",
            "data": {
                "period": monthly_view["period"],
                "employee_count": len(monthly_view["employees"]),
                "total_statistics": monthly_view["total_statistics"],
                "format": format,
                "download_url": None  # URL seria gerada por um serviço de exportação
            },
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao exportar visualização mensal: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao exportar visualização mensal"
        )


@router.get("/health")
async def time_view_health():
    """
    Health check do módulo de visualização de batidas.
    """
    return {
        "status": "ok",
        "service": "time-view",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }