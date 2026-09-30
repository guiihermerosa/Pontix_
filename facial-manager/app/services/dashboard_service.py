"""
Serviço para o Dashboard do Portal do Contador.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, extract

from app.database.models_supabase import (
    Company, EmployeeSupabase, TimeRecord, WorkPeriod, 
    Occurrence, Justification, SyncLog
)
from app.auth.permissions import Role

logger = logging.getLogger("dashboard_service")


class DashboardService:
    """Serviço para dados do dashboard."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_accountant_dashboard(self, company_id: UUID, user_role: str) -> Dict[str, Any]:
        """
        Retorna dados para o dashboard do contador.
        
        Args:
            company_id: ID da empresa
            user_role: Papel do usuário
            
        Returns:
            Dados do dashboard
        """
        try:
            # Dados básicos da empresa
            company = self.db.query(Company).filter(
                Company.id == company_id,
                Company.is_active == True
            ).first()
            
            if not company:
                raise ValueError(f"Empresa {company_id} não encontrada")
            
            # Estatísticas gerais
            stats = self._get_company_stats(company_id)
            
            # Períodos atuais
            current_date = datetime.now()
            current_period = self._get_current_period(company_id, current_date)
            
            # Ocorrências pendentes
            pending_occurrences = self._get_pending_occurrences(company_id)
            
            # Sincronização status
            sync_status = self._get_sync_status(company_id)
            
            # Gráficos
            charts = self._get_dashboard_charts(company_id)
            
            # Dados para cards
            cards = self._prepare_dashboard_cards(stats, pending_occurrences, sync_status)
            
            return {
                "company": {
                    "id": str(company.id),
                    "name": company.name,
                    "cnpj": company.cnpj,
                    "active": company.is_active
                },
                "stats": stats,
                "current_period": current_period,
                "pending_occurrences": pending_occurrences,
                "sync_status": sync_status,
                "charts": charts,
                "cards": cards,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter dashboard: {str(e)}")
            raise
    
    def get_companies_overview(self, user_id: str) -> Dict[str, Any]:
        """
        Retorna visão geral de todas as empresas do contador.
        
        Args:
            user_id: ID do usuário (contador)
            
        Returns:
            Visão geral das empresas
        """
        try:
            # Obtém empresas do usuário
            from app.database.models_supabase import CompanyUser
            
            company_users = self.db.query(CompanyUser).filter(
                CompanyUser.user_id == user_id,
                CompanyUser.invitation_status == "accepted",
                CompanyUser.role.in_([Role.ACCOUNTANT.value, Role.OWNER.value])
            ).all()
            
            companies_data = []
            total_stats = {
                "companies": 0,
                "employees": 0,
                "pending_periods": 0,
                "closed_periods": 0,
                "pending_occurrences": 0
            }
            
            for cu in company_users:
                company_stats = self._get_company_stats(cu.company_id)
                current_period = self._get_current_period(cu.company_id, datetime.now())
                
                company_data = {
                    "id": str(cu.company_id),
                    "name": cu.company.name if cu.company else "Empresa",
                    "role": cu.role,
                    "stats": company_stats,
                    "current_period": current_period,
                    "pending_occurrences": self._get_pending_occurrences_count(cu.company_id)
                }
                
                companies_data.append(company_data)
                
                # Acumula totais
                total_stats["companies"] += 1
                total_stats["employees"] += company_stats.get("employees", 0)
                total_stats["pending_periods"] += 1 if current_period and current_period.get("status") == "open" else 0
                total_stats["closed_periods"] += 1 if current_period and current_period.get("status") == "closed" else 0
                total_stats["pending_occurrences"] += company_data["pending_occurrences"]
            
            # Ordena empresas por nome
            companies_data.sort(key=lambda x: x["name"])
            
            return {
                "companies": companies_data,
                "total_stats": total_stats,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter overview de empresas: {str(e)}")
            raise
    
    def search_companies(self, user_id: str, search_term: str) -> List[Dict[str, Any]]:
        """
        Busca empresas por nome ou CNPJ.
        
        Args:
            user_id: ID do usuário
            search_term: Termo de busca
            
        Returns:
            Lista de empresas encontradas
        """
        try:
            from app.database.models_supabase import CompanyUser
            
            # Obtém IDs das empresas do usuário
            user_companies = self.db.query(CompanyUser.company_id).filter(
                CompanyUser.user_id == user_id,
                CompanyUser.invitation_status == "accepted"
            ).subquery()
            
            # Busca empresas
            query = self.db.query(Company).filter(
                Company.id.in_(user_companies),
                Company.is_active == True,
                or_(
                    Company.name.ilike(f"%{search_term}%"),
                    Company.cnpj.ilike(f"%{search_term}%")
                )
            ).order_by(Company.name)
            
            companies = query.limit(20).all()
            
            results = []
            for company in companies:
                # Obtém role do usuário na empresa
                company_user = self.db.query(CompanyUser).filter(
                    CompanyUser.user_id == user_id,
                    CompanyUser.company_id == company.id
                ).first()
                
                results.append({
                    "id": str(company.id),
                    "name": company.name,
                    "cnpj": company.cnpj,
                    "role": company_user.role if company_user else None,
                    "city": company.city,
                    "state": company.state
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Erro na busca de empresas: {str(e)}")
            return []
    
    def _get_company_stats(self, company_id: UUID) -> Dict[str, Any]:
        """Calcula estatísticas da empresa."""
        # Total de funcionários ativos
        employees_count = self.db.query(EmployeeSupabase).filter(
            EmployeeSupabase.company_id == company_id,
            EmployeeSupabase.is_active == True
        ).count()
        
        # Total de registros deste mês
        current_date = datetime.now()
        start_of_month = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        time_records_count = self.db.query(TimeRecord).filter(
            TimeRecord.company_id == company_id,
            TimeRecord.record_date >= start_of_month
        ).count()
        
        # Períodos fechados
        closed_periods = self.db.query(WorkPeriod).filter(
            WorkPeriod.company_id == company_id,
            WorkPeriod.status == "closed"
        ).count()
        
        # Períodos abertos
        open_periods = self.db.query(WorkPeriod).filter(
            WorkPeriod.company_id == company_id,
            WorkPeriod.status == "open"
        ).count()
        
        # Ocorrências
        occurrences_count = self.db.query(Occurrence).filter(
            Occurrence.company_id == company_id,
            Occurrence.status == "pending"
        ).count()
        
        # Horas extras (estimativa simples)
        # Esta é uma estimativa básica - pode ser melhorada
        extra_hours_estimate = self._estimate_extra_hours(company_id)
        
        return {
            "employees": employees_count,
            "time_records": time_records_count,
            "closed_periods": closed_periods,
            "open_periods": open_periods,
            "pending_occurrences": occurrences_count,
            "extra_hours": extra_hours_estimate,
            "last_calculated": datetime.now().isoformat()
        }
    
    def _get_current_period(self, company_id: UUID, current_date: datetime) -> Optional[Dict[str, Any]]:
        """Obtém período atual da empresa."""
        year = current_date.year
        month = current_date.month
        
        period = self.db.query(WorkPeriod).filter(
            WorkPeriod.company_id == company_id,
            WorkPeriod.year == year,
            WorkPeriod.month == month
        ).first()
        
        if period:
            return {
                "id": str(period.id),
                "year": period.year,
                "month": period.month,
                "status": period.status,
                "closed_at": period.closed_at.isoformat() if period.closed_at else None,
                "closed_by": period.closed_by,
                "statistics": period.statistics or {}
            }
        
        return None
    
    def _get_pending_occurrences(self, company_id: UUID, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtém ocorrências pendentes."""
        occurrences = self.db.query(Occurrence).filter(
            Occurrence.company_id == company_id,
            Occurrence.status == "pending"
        ).order_by(Occurrence.occurrence_date.desc()).limit(limit).all()
        
        result = []
        for occ in occurrences:
            result.append({
                "id": str(occ.id),
                "employee_name": occ.employee.full_name if occ.employee else "Desconhecido",
                "date": occ.occurrence_date.strftime("%d/%m/%Y"),
                "type": occ.occurrence_type,
                "severity": occ.severity,
                "description": occ.description
            })
        
        return result
    
    def _get_pending_occurrences_count(self, company_id: UUID) -> int:
        """Conta ocorrências pendentes."""
        return self.db.query(Occurrence).filter(
            Occurrence.company_id == company_id,
            Occurrence.status == "pending"
        ).count()
    
    def _get_sync_status(self, company_id: UUID) -> Dict[str, Any]:
        """Obtém status da sincronização."""
        last_sync = self.db.query(SyncLog).filter(
            SyncLog.company_id == company_id
        ).order_by(SyncLog.started_at.desc()).first()
        
        if last_sync:
            status = "success" if last_sync.status == "completed" else "warning"
            if last_sync.status == "failed":
                status = "error"
            
            return {
                "last_sync": last_sync.started_at.isoformat() if last_sync.started_at else None,
                "status": status,
                "records_processed": last_sync.records_processed,
                "records_succeeded": last_sync.records_succeeded,
                "records_failed": last_sync.records_failed,
                "details": last_sync.details
            }
        
        return {
            "last_sync": None,
            "status": "unknown",
            "records_processed": 0,
            "records_succeeded": 0,
            "records_failed": 0,
            "details": "Nenhuma sincronização registrada"
        }
    
    def _get_dashboard_charts(self, company_id: UUID) -> Dict[str, Any]:
        """Gera dados para gráficos do dashboard."""
        # Gráfico de horas extras por mês (últimos 6 meses)
        extra_hours_by_month = self._get_extra_hours_chart(company_id, months=6)
        
        # Gráfico de ocorrências por tipo
        occurrences_by_type = self._get_occurrences_by_type_chart(company_id)
        
        # Gráfico de evolução de funcionários
        employees_evolution = self._get_employees_evolution_chart(company_id, months=12)
        
        # Gráfico de períodos pendentes
        pending_periods_chart = self._get_pending_periods_chart(company_id)
        
        return {
            "extra_hours_by_month": extra_hours_by_month,
            "occurrences_by_type": occurrences_by_type,
            "employees_evolution": employees_evolution,
            "pending_periods": pending_periods_chart
        }
    
    def _estimate_extra_hours(self, company_id: UUID) -> float:
        """Estima horas extras da empresa (em horas)."""
        # Implementação básica - pode ser aprimorada
        # Aqui estimamos baseado em registros fora do horário comercial
        
        try:
            company = self.db.query(Company).filter(Company.id == company_id).first()
            if not company or not company.work_hours:
                return 0.0
            
            work_hours = company.work_hours
            normal_start = datetime.strptime(work_hours.get("start", "08:00"), "%H:%M").time()
            normal_end = datetime.strptime(work_hours.get("end", "18:00"), "%H:%M").time()
            
            # Este é um placeholder - implementação real requer lógica complexa
            # que analisa cada registro de ponto
            return 0.0
            
        except Exception:
            return 0.0
    
    def _get_extra_hours_chart(self, company_id: UUID, months: int = 6) -> Dict[str, Any]:
        """Gera dados para gráfico de horas extras por mês."""
        # Placeholder - implementação real requer cálculo complexo
        current_date = datetime.now()
        
        labels = []
        data = []
        
        for i in range(months - 1, -1, -1):
            month_date = current_date - timedelta(days=30 * i)
            month_label = month_date.strftime("%b/%y")
            
            # Valor aleatório para demonstração
            import random
            hours = random.uniform(0, 50)
            
            labels.append(month_label)
            data.append(round(hours, 1))
        
        return {
            "labels": labels,
            "datasets": [
                {
                    "label": "Horas Extras",
                    "data": data,
                    "backgroundColor": "rgba(59, 130, 246, 0.5)",
                    "borderColor": "rgb(59, 130, 246)",
                    "borderWidth": 1
                }
            ]
        }
    
    def _get_occurrences_by_type_chart(self, company_id: UUID) -> Dict[str, Any]:
        """Gera dados para gráfico de ocorrências por tipo."""
        # Agrupa ocorrências por tipo
        occurrences = self.db.query(
            Occurrence.occurrence_type,
            func.count(Occurrence.id).label('count')
        ).filter(
            Occurrence.company_id == company_id,
            Occurrence.created_at >= datetime.now() - timedelta(days=30)
        ).group_by(Occurrence.occurrence_type).all()
        
        labels = []
        data = []
        background_colors = [
            'rgba(239, 68, 68, 0.5)',    # Vermelho - atraso
            'rgba(245, 158, 11, 0.5)',   # Laranja - falta
            'rgba(59, 130, 246, 0.5)',   # Azul - saída antecipada
            'rgba(16, 185, 129, 0.5)',   # Verde - hora extra
            'rgba(139, 92, 246, 0.5)',   # Roxo - intervalo irregular
        ]
        
        for i, (occ_type, count) in enumerate(occurrences):
            labels.append(occ_type.replace('_', ' ').title())
            data.append(count)
        
        return {
            "labels": labels,
            "datasets": [
                {
                    "label": "Ocorrências",
                    "data": data,
                    "backgroundColor": background_colors[:len(data)],
                    "borderColor": [c.replace('0.5', '1') for c in background_colors[:len(data)]],
                    "borderWidth": 1
                }
            ]
        }
    
    def _get_employees_evolution_chart(self, company_id: UUID, months: int = 12) -> Dict[str, Any]:
        """Gera dados para gráfico de evolução de funcionários."""
        # Placeholder - implementação real requer histórico de admissões/demissões
        current_date = datetime.now()
        
        labels = []
        data = []
        
        # Conta funcionários ativos
        active_employees = self.db.query(EmployeeSupabase).filter(
            EmployeeSupabase.company_id == company_id,
            EmployeeSupabase.is_active == True
        ).count()
        
        for i in range(months - 1, -1, -1):
            month_date = current_date - timedelta(days=30 * i)
            month_label = month_date.strftime("%b/%y")
            
            # Para simplificar, usamos o mesmo valor
            labels.append(month_label)
            data.append(active_employees)
        
        return {
            "labels": labels,
            "datasets": [
                {
                    "label": "Funcionários Ativos",
                    "data": data,
                    "backgroundColor": "rgba(16, 185, 129, 0.5)",
                    "borderColor": "rgb(16, 185, 129)",
                    "borderWidth": 1,
                    "fill": True
                }
            ]
        }
    
    def _get_pending_periods_chart(self, company_id: UUID) -> Dict[str, Any]:
        """Gera dados para gráfico de períodos pendentes."""
        # Obtém períodos dos últimos 12 meses
        current_date = datetime.now()
        
        periods = self.db.query(WorkPeriod).filter(
            WorkPeriod.company_id == company_id,
            WorkPeriod.year >= current_date.year - 1
        ).order_by(WorkPeriod.year, WorkPeriod.month).all()
        
        labels = []
        closed_data = []
        open_data = []
        
        for period in periods:
            label = f"{period.month:02d}/{str(period.year)[2:]}"
            labels.append(label)
            
            if period.status == "closed":
                closed_data.append(1)
                open_data.append(0)
            else:
                closed_data.append(0)
                open_data.append(1)
        
        return {
            "labels": labels,
            "datasets": [
                {
                    "label": "Fechados",
                    "data": closed_data,
                    "backgroundColor": "rgba(16, 185, 129, 0.5)",
                    "borderColor": "rgb(16, 185, 129)",
                    "borderWidth": 1
                },
                {
                    "label": "Pendentes",
                    "data": open_data,
                    "backgroundColor": "rgba(245, 158, 11, 0.5)",
                    "borderColor": "rgb(245, 158, 11)",
                    "borderWidth": 1
                }
            ]
        }
    
    def _prepare_dashboard_cards(self, stats: Dict[str, Any], 
                                pending_occurrences: List[Dict[str, Any]],
                                sync_status: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prepara dados para cards do dashboard."""
        cards = [
            {
                "title": "Empresas",
                "value": "1",  # Para dashboard de empresa específica
                "subtitle": "Ativa",
                "icon": "🏢",
                "color": "blue",
                "trend": None
            },
            {
                "title": "Funcionários",
                "value": str(stats.get("employees", 0)),
                "subtitle": "Ativos",
                "icon": "👥",
                "color": "green",
                "trend": "+2"  # Placeholder
            },
            {
                "title": "Registros",
                "value": str(stats.get("time_records", 0)),
                "subtitle": "Este mês",
                "icon": "📊",
                "color": "purple",
                "trend": "+15%"
            },
            {
                "title": "Pendências",
                "value": str(stats.get("pending_occurrences", 0)),
                "subtitle": "Ocorrências",
                "icon": "⚠️",
                "color": "orange",
                "trend": None
            },
            {
                "title": "Períodos",
                "value": str(stats.get("closed_periods", 0)),
                "subtitle": "Fechados",
                "icon": "✅",
                "color": "green",
                "trend": None
            },
            {
                "title": "Horas Extras",
                "value": f"{stats.get('extra_hours', 0):.1f}h",
                "subtitle": "Estimado",
                "icon": "⏰",
                "color": "red",
                "trend": "-5%"
            }
        ]
        
        return cards