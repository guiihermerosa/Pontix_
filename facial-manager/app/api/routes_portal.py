"""
Rotas do Portal do Contador para React frontend.
"""
import logging
from datetime import datetime
from typing import Dict, Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.auth.permissions import (
    get_current_user, check_permission, Permissions, Role
)
from app.database.database import get_db
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/portal", tags=["Portal do Contador"])
logger = logging.getLogger("portal_routes")


@router.get("/dashboard/overview")
async def get_accountant_overview(
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retorna visão geral para o contador (todas as empresas).
    
    Requer permissão de contador ou superior.
    """
    try:
        dashboard_service = DashboardService(db)
        
        # Verifica se é contador
        from app.database.models_supabase import CompanyUser
        
        is_accountant = db.query(CompanyUser).filter(
            CompanyUser.user_id == user["id"],
            CompanyUser.role == Role.ACCOUNTANT.value,
            CompanyUser.invitation_status == "accepted"
        ).first() is not None
        
        if not is_accountant:
            # Pode ser owner também
            is_owner = db.query(CompanyUser).filter(
                CompanyUser.user_id == user["id"],
                CompanyUser.role == Role.OWNER.value,
                CompanyUser.invitation_status == "accepted"
            ).first() is not None
            
            if not is_owner:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Acesso restrito a contadores e proprietários"
                )
        
        overview = dashboard_service.get_companies_overview(user["id"])
        
        return {
            "success": True,
            "data": overview,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter overview do contador: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter dados do portal"
        )


@router.get("/dashboard/company/{company_id}")
async def get_company_dashboard(
    company_id: UUID,
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
    # Verifica permissão específica
    _ = Depends(check_permission(Permissions.COMPANY_VIEW, company_id=company_id))
):
    """
    Retorna dashboard específico de uma empresa.
    
    Requer permissão COMPANY_VIEW para a empresa.
    """
    try:
        # Obtém role do usuário na empresa
        from app.database.models_supabase import CompanyUser
        
        company_user = db.query(CompanyUser).filter(
            CompanyUser.user_id == user["id"],
            CompanyUser.company_id == company_id,
            CompanyUser.invitation_status == "accepted"
        ).first()
        
        if not company_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuário não tem acesso a esta empresa"
            )
        
        dashboard_service = DashboardService(db)
        dashboard_data = dashboard_service.get_accountant_dashboard(
            company_id, company_user.role
        )
        
        return {
            "success": True,
            "data": dashboard_data,
            "user_role": company_user.role,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter dashboard da empresa: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter dados do dashboard"
        )


@router.get("/companies/search")
async def search_companies(
    search: str = Query(..., min_length=2, max_length=100, description="Termo de busca"),
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Busca empresas por nome ou CNPJ.
    
    Retorna apenas empresas às quais o usuário tem acesso.
    """
    try:
        dashboard_service = DashboardService(db)
        results = dashboard_service.search_companies(user["id"], search)
        
        return {
            "success": True,
            "data": results,
            "count": len(results),
            "search_term": search
        }
        
    except Exception as e:
        logger.error(f"Erro na busca de empresas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro na busca de empresas"
        )


@router.get("/companies/filter")
async def filter_companies(
    status: str = Query(None, description="Status do período: open, closed, all"),
    role: str = Query(None, description="Role do usuário na empresa"),
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Filtra empresas por status do período ou role.
    """
    try:
        from app.database.models_supabase import CompanyUser, WorkPeriod
        
        # Base query para empresas do usuário
        query = db.query(CompanyUser).filter(
            CompanyUser.user_id == user["id"],
            CompanyUser.invitation_status == "accepted"
        )
        
        # Filtro por role
        if role and role in Role.get_all_roles():
            query = query.filter(CompanyUser.role == role)
        
        company_users = query.all()
        
        filtered_companies = []
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        
        for cu in company_users:
            if not cu.company:
                continue
            
            # Obtém período atual da empresa
            period = db.query(WorkPeriod).filter(
                WorkPeriod.company_id == cu.company_id,
                WorkPeriod.year == current_year,
                WorkPeriod.month == current_month
            ).first()
            
            period_status = period.status if period else "open"
            
            # Aplica filtro de status
            if status and status != "all":
                if status != period_status:
                    continue
            
            company_data = {
                "id": str(cu.company_id),
                "name": cu.company.name,
                "cnpj": cu.company.cnpj,
                "role": cu.role,
                "period_status": period_status,
                "period_month": current_month,
                "period_year": current_year
            }
            
            filtered_companies.append(company_data)
        
        # Ordena por nome
        filtered_companies.sort(key=lambda x: x["name"])
        
        return {
            "success": True,
            "data": filtered_companies,
            "count": len(filtered_companies),
            "filters": {
                "status": status,
                "role": role
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao filtrar empresas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao filtrar empresas"
        )


@router.get("/companies/{company_id}/quick-stats")
async def get_company_quick_stats(
    company_id: UUID,
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
    _ = Depends(check_permission(Permissions.COMPANY_VIEW, company_id=company_id))
):
    """
    Retorna estatísticas rápidas de uma empresa.
    
    Para uso em cards e visão geral.
    """
    try:
        from app.database.models_supabase import (
            EmployeeSupabase, TimeRecord, Occurrence, WorkPeriod
        )
        
        current_date = datetime.now()
        start_of_month = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Conta funcionários ativos
        employees_count = db.query(EmployeeSupabase).filter(
            EmployeeSupabase.company_id == company_id,
            EmployeeSupabase.is_active == True
        ).count()
        
        # Conta registros deste mês
        time_records_count = db.query(TimeRecord).filter(
            TimeRecord.company_id == company_id,
            TimeRecord.record_date >= start_of_month
        ).count()
        
        # Conta ocorrências pendentes
        pending_occurrences = db.query(Occurrence).filter(
            Occurrence.company_id == company_id,
            Occurrence.status == "pending"
        ).count()
        
        # Status do período atual
        period = db.query(WorkPeriod).filter(
            WorkPeriod.company_id == company_id,
            WorkPeriod.year == current_date.year,
            WorkPeriod.month == current_date.month
        ).first()
        
        period_status = period.status if period else "open"
        
        # Última sincronização
        from app.database.models_supabase import SyncLog
        last_sync = db.query(SyncLog).filter(
            SyncLog.company_id == company_id
        ).order_by(SyncLog.started_at.desc()).first()
        
        last_sync_time = last_sync.started_at.isoformat() if last_sync and last_sync.started_at else None
        
        return {
            "success": True,
            "data": {
                "employees": employees_count,
                "time_records_month": time_records_count,
                "pending_occurrences": pending_occurrences,
                "period_status": period_status,
                "last_sync": last_sync_time,
                "calculated_at": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter quick stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter estatísticas rápidas"
        )


@router.get("/recent-activity")
async def get_recent_activity(
    company_id: UUID = Query(None, description="ID da empresa (opcional)"),
    limit: int = Query(10, ge=1, le=50, description="Limite de atividades"),
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retorna atividade recente (audit logs).
    
    Se company_id for fornecido, retorna apenas daquela empresa.
    """
    try:
        from app.database.models_supabase import AuditLog, CompanyUser
        
        # Se company_id fornecido, verifica permissão
        if company_id:
            # Verifica acesso à empresa
            company_user = db.query(CompanyUser).filter(
                CompanyUser.user_id == user["id"],
                CompanyUser.company_id == company_id,
                CompanyUser.invitation_status == "accepted"
            ).first()
            
            if not company_user:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Usuário não tem acesso a esta empresa"
                )
            
            # Filtra por empresa
            query = db.query(AuditLog).filter(
                AuditLog.company_id == company_id
            )
        else:
            # Obtém todas as empresas do usuário
            user_companies = db.query(CompanyUser.company_id).filter(
                CompanyUser.user_id == user["id"],
                CompanyUser.invitation_status == "accepted"
            ).subquery()
            
            # Filtra por empresas do usuário
            query = db.query(AuditLog).filter(
                AuditLog.company_id.in_(user_companies)
            )
        
        # Obtém atividades recentes
        activities = query.order_by(
            AuditLog.created_at.desc()
        ).limit(limit).all()
        
        formatted_activities = []
        for activity in activities:
            # Formata a ação
            action_descriptions = {
                "login": "Login realizado",
                "logout": "Logout realizado",
                "create": "Criado",
                "update": "Atualizado",
                "delete": "Excluído",
                "adjust": "Ajustado",
                "close_period": "Período fechado",
                "reopen_period": "Período reaberto",
                "approve_justification": "Justificativa aprovada",
                "reject_justification": "Justificativa rejeitada"
            }
            
            action_desc = action_descriptions.get(activity.action_type, activity.action_type)
            
            formatted_activities.append({
                "id": str(activity.id),
                "action": action_desc,
                "entity_type": activity.entity_type,
                "entity_id": activity.entity_id,
                "user_id": activity.user_id,
                "timestamp": activity.created_at.isoformat(),
                "notes": activity.notes,
                "company_id": str(activity.company_id)
            })
        
        return {
            "success": True,
            "data": formatted_activities,
            "count": len(formatted_activities),
            "company_filter": str(company_id) if company_id else "all"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter atividade recente: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter atividade recente"
        )


@router.get("/sync-status")
async def get_sync_status(
    company_id: UUID = Query(None, description="ID da empresa (opcional)"),
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retorna status da sincronização.
    
    Se company_id não for fornecido, retorna status de todas as empresas do usuário.
    """
    try:
        from app.database.models_supabase import SyncLog, CompanyUser
        
        if company_id:
            # Verifica acesso à empresa
            company_user = db.query(CompanyUser).filter(
                CompanyUser.user_id == user["id"],
                CompanyUser.company_id == company_id,
                CompanyUser.invitation_status == "accepted"
            ).first()
            
            if not company_user:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Usuário não tem acesso a esta empresa"
                )
            
            # Última sincronização da empresa
            last_sync = db.query(SyncLog).filter(
                SyncLog.company_id == company_id
            ).order_by(SyncLog.started_at.desc()).first()
            
            sync_data = []
            if last_sync:
                sync_data.append({
                    "company_id": str(company_id),
                    "company_name": company_user.company.name if company_user.company else "Empresa",
                    "last_sync": last_sync.started_at.isoformat() if last_sync.started_at else None,
                    "status": last_sync.status,
                    "records_processed": last_sync.records_processed,
                    "records_succeeded": last_sync.records_succeeded,
                    "records_failed": last_sync.records_failed,
                    "details": last_sync.details
                })
        else:
            # Todas as empresas do usuário
            user_companies = db.query(CompanyUser).filter(
                CompanyUser.user_id == user["id"],
                CompanyUser.invitation_status == "accepted"
            ).all()
            
            sync_data = []
            for cu in user_companies:
                if not cu.company:
                    continue
                
                last_sync = db.query(SyncLog).filter(
                    SyncLog.company_id == cu.company_id
                ).order_by(SyncLog.started_at.desc()).first()
                
                sync_data.append({
                    "company_id": str(cu.company_id),
                    "company_name": cu.company.name,
                    "last_sync": last_sync.started_at.isoformat() if last_sync and last_sync.started_at else None,
                    "status": last_sync.status if last_sync else "never",
                    "records_processed": last_sync.records_processed if last_sync else 0,
                    "records_succeeded": last_sync.records_succeeded if last_sync else 0,
                    "records_failed": last_sync.records_failed if last_sync else 0,
                    "details": last_sync.details if last_sync else "Nenhuma sincronização"
                })
        
        # Calcula status geral
        all_success = all(s["status"] == "completed" for s in sync_data if s["status"] != "never")
        any_failed = any(s["status"] == "failed" for s in sync_data)
        
        overall_status = "success"
        if any_failed:
            overall_status = "error"
        elif not all_success:
            overall_status = "warning"
        
        return {
            "success": True,
            "data": sync_data,
            "overall_status": overall_status,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter status de sincronização: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter status de sincronização"
        )


@router.get("/health")
async def portal_health():
    """
    Health check do módulo do portal.
    """
    return {
        "status": "ok",
        "service": "portal",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }