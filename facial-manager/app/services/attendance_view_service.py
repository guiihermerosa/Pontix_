"""
Serviço para visualização organizada de batidas (espelho de ponto).
"""
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.database.models_supabase import (
    EmployeeSupabase, TimeRecord, Company
)

logger = logging.getLogger("attendance_view_service")


class AttendanceViewService:
    """Serviço para visualização de batidas de ponto."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_monthly_view(
        self,
        company_id: UUID,
        employee_id: Optional[UUID] = None,
        year: Optional[int] = None,
        month: Optional[int] = None,
        include_statistics: bool = True
    ) -> Dict[str, Any]:
        """
        Retorna visualização mensal (espelho de ponto).
        
        Args:
            company_id: ID da empresa
            employee_id: ID do funcionário (opcional, se None, retorna todos)
            year: Ano (opcional, padrão: atual)
            month: Mês 1-12 (opcional, padrão: atual)
            include_statistics: Incluir estatísticas calculadas
            
        Returns:
            Dados do espelho mensal
        """
        try:
            # Define período
            current_date = datetime.now()
            target_year = year or current_date.year
            target_month = month or current_date.month
            
            # Valida mês
            if not 1 <= target_month <= 12:
                raise ValueError(f"Mês inválido: {target_month}")
            
            # Obtém dados da empresa
            company = self.db.query(Company).filter(Company.id == company_id).first()
            if not company:
                raise ValueError(f"Empresa {company_id} não encontrada")
            
            # Configurações da empresa
            work_hours = company.work_hours or {}
            work_start = datetime.strptime(work_hours.get("start", "08:00"), "%H:%M").time()
            work_end = datetime.strptime(work_hours.get("end", "18:00"), "%H:%M").time()
            break_start = datetime.strptime(work_hours.get("break_start", "12:00"), "%H:%M").time()
            break_end = datetime.strptime(work_hours.get("break_end", "13:00"), "%H:%M").time()
            
            # Obtém funcionários
            if employee_id:
                employees = self.db.query(EmployeeSupabase).filter(
                    EmployeeSupabase.id == employee_id,
                    EmployeeSupabase.company_id == company_id,
                    EmployeeSupabase.is_active == True
                ).all()
            else:
                employees = self.db.query(EmployeeSupabase).filter(
                    EmployeeSupabase.company_id == company_id,
                    EmployeeSupabase.is_active == True
                ).order_by(EmployeeSupabase.full_name).all()
            
            # Processa cada funcionário
            monthly_data = []
            total_stats = {
                "employees": 0,
                "work_days": 0,
                "total_hours": 0.0,
                "extra_hours": 0.0,
                "delays": 0,
                "early_exits": 0,
                "incomplete_records": 0,
                "absences": 0
            }
            
            for employee in employees:
                employee_view = self._get_employee_monthly_view(
                    employee, target_year, target_month,
                    work_start, work_end, break_start, break_end,
                    include_statistics
                )
                
                if employee_view["days"]:  # Só inclui se tiver dados
                    monthly_data.append(employee_view)
                    
                    # Acumula estatísticas
                    if include_statistics and employee_view.get("statistics"):
                        stats = employee_view["statistics"]
                        total_stats["employees"] += 1
                        total_stats["work_days"] += stats.get("work_days", 0)
                        total_stats["total_hours"] += stats.get("total_hours", 0)
                        total_stats["extra_hours"] += stats.get("extra_hours", 0)
                        total_stats["delays"] += stats.get("delays", 0)
                        total_stats["early_exits"] += stats.get("early_exits", 0)
                        total_stats["incomplete_records"] += stats.get("incomplete_records", 0)
                        total_stats["absences"] += stats.get("absences", 0)
            
            # Formata período
            period_label = f"{target_month:02d}/{target_year}"
            
            return {
                "company": {
                    "id": str(company.id),
                    "name": company.name,
                    "work_hours": work_hours
                },
                "period": {
                    "year": target_year,
                    "month": target_month,
                    "label": period_label,
                    "start_date": f"{target_year}-{target_month:02d}-01",
                    "end_date": self._get_month_end_date(target_year, target_month)
                },
                "employees": monthly_data,
                "total_statistics": total_stats if include_statistics else None,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar visualização mensal: {str(e)}")
            raise
    
    def get_daily_view(
        self,
        company_id: UUID,
        target_date: Optional[date] = None,
        employee_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Retorna visualização detalhada de um dia específico.
        
        Args:
            company_id: ID da empresa
            target_date: Data (opcional, padrão: hoje)
            employee_id: ID do funcionário (opcional, se None, retorna todos)
            
        Returns:
            Dados do dia
        """
        try:
            # Define data
            view_date = target_date or date.today()
            
            # Obtém dados da empresa
            company = self.db.query(Company).filter(Company.id == company_id).first()
            if not company:
                raise ValueError(f"Empresa {company_id} não encontrada")
            
            # Configurações da empresa
            work_hours = company.work_hours or {}
            
            # Obtém funcionários
            if employee_id:
                employees = self.db.query(EmployeeSupabase).filter(
                    EmployeeSupabase.id == employee_id,
                    EmployeeSupabase.company_id == company_id,
                    EmployeeSupabase.is_active == True
                ).all()
            else:
                employees = self.db.query(EmployeeSupabase).filter(
                    EmployeeSupabase.company_id == company_id,
                    EmployeeSupabase.is_active == True
                ).order_by(EmployeeSupabase.full_name).all()
            
            # Processa cada funcionário
            daily_data = []
            date_stats = {
                "total_employees": len(employees),
                "employees_present": 0,
                "employees_absent": 0,
                "total_records": 0,
                "incomplete_records": 0,
                "delays": 0,
                "early_exits": 0
            }
            
            for employee in employees:
                employee_day = self._get_employee_daily_view(
                    employee, view_date, work_hours
                )
                
                daily_data.append(employee_day)
                
                # Acumula estatísticas
                date_stats["total_records"] += len(employee_day["records"])
                
                if employee_day["status"] == "present":
                    date_stats["employees_present"] += 1
                elif employee_day["status"] == "absent":
                    date_stats["employees_absent"] += 1
                
                if employee_day.get("has_incomplete_records"):
                    date_stats["incomplete_records"] += 1
                
                if employee_day.get("has_delay"):
                    date_stats["delays"] += 1
                
                if employee_day.get("has_early_exit"):
                    date_stats["early_exits"] += 1
            
            # Verifica se é dia útil
            is_work_day = view_date.weekday() < 5  # Segunda a sexta
            
            return {
                "company": {
                    "id": str(company.id),
                    "name": company.name
                },
                "date": {
                    "iso": view_date.isoformat(),
                    "formatted": view_date.strftime("%d/%m/%Y"),
                    "weekday": view_date.strftime("%A"),
                    "is_work_day": is_work_day
                },
                "employees": daily_data,
                "statistics": date_stats,
                "work_hours": work_hours,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar visualização diária: {str(e)}")
            raise
    
    def get_employee_timeline(
        self,
        employee_id: UUID,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """
        Retorna timeline de registros de um funcionário.
        
        Args:
            employee_id: ID do funcionário
            start_date: Data inicial
            end_date: Data final
            
        Returns:
            Timeline de registros
        """
        try:
            employee = self.db.query(EmployeeSupabase).filter(
                EmployeeSupabase.id == employee_id
            ).first()
            
            if not employee:
                raise ValueError(f"Funcionário {employee_id} não encontrado")
            
            # Obtém registros no período
            records = self.db.query(TimeRecord).filter(
                TimeRecord.employee_id == employee_id,
                TimeRecord.record_date >= start_date,
                TimeRecord.record_date <= end_date
            ).order_by(
                TimeRecord.record_date,
                TimeRecord.record_time
            ).all()
            
            # Agrupa por dia
            timeline_by_day = defaultdict(list)
            for record in records:
                day_key = record.record_date.strftime("%Y-%m-%d")
                timeline_by_day[day_key].append({
                    "id": str(record.id),
                    "time": record.record_time,
                    "type": record.record_type,
                    "source": record.source,
                    "is_adjusted": record.is_adjusted,
                    "adjusted_reason": record.adjustment_reason
                })
            
            # Formata timeline
            timeline = []
            current_date = start_date
            while current_date <= end_date:
                day_key = current_date.strftime("%Y-%m-%d")
                day_records = timeline_by_day.get(day_key, [])
                
                # Ordena registros por horário
                day_records.sort(key=lambda x: x["time"])
                
                # Detecta ocorrências do dia
                occurrences = self._detect_day_occurrences(day_records, current_date)
                
                timeline.append({
                    "date": current_date.isoformat(),
                    "formatted_date": current_date.strftime("%d/%m/%Y"),
                    "weekday": current_date.strftime("%A"),
                    "is_work_day": current_date.weekday() < 5,
                    "records": day_records,
                    "occurrences": occurrences,
                    "has_records": len(day_records) > 0
                })
                
                current_date += timedelta(days=1)
            
            return timeline
            
        except Exception as e:
            logger.error(f"Erro ao gerar timeline: {str(e)}")
            raise
    
    def _get_employee_monthly_view(
        self,
        employee: EmployeeSupabase,
        year: int,
        month: int,
        work_start: datetime.time,
        work_end: datetime.time,
        break_start: datetime.time,
        break_end: datetime.time,
        include_statistics: bool
    ) -> Dict[str, Any]:
        """Gera visualização mensal para um funcionário."""
        # Calcula dias do mês
        start_date = date(year, month, 1)
        end_date = self._get_month_end_date(year, month)
        
        # Obtém registros do mês
        records = self.db.query(TimeRecord).filter(
            TimeRecord.employee_id == employee.id,
            TimeRecord.record_date >= start_date,
            TimeRecord.record_date <= end_date
        ).order_by(
            TimeRecord.record_date,
            TimeRecord.record_time
        ).all()
        
        # Agrupa registros por dia
        records_by_day = defaultdict(list)
        for record in records:
            day_key = record.record_date.strftime("%Y-%m-%d")
            records_by_day[day_key].append(record)
        
        # Processa cada dia do mês
        days_data = []
        current_date = start_date
        monthly_stats = {
            "work_days": 0,
            "present_days": 0,
            "absent_days": 0,
            "total_hours": 0.0,
            "extra_hours": 0.0,
            "delays": 0,
            "early_exits": 0,
            "incomplete_records": 0,
            "justified_absences": 0
        }
        
        while current_date <= end_date:
            day_key = current_date.strftime("%Y-%m-%d")
            day_records = records_by_day.get(day_key, [])
            
            # Processa dia
            day_view = self._process_day_records(
                current_date, day_records,
                work_start, work_end, break_start, break_end
            )
            
            days_data.append(day_view)
            
            # Atualiza estatísticas
            if current_date.weekday() < 5:  # Dia útil
                monthly_stats["work_days"] += 1
                
                if day_view["status"] == "present":
                    monthly_stats["present_days"] += 1
                elif day_view["status"] == "absent":
                    monthly_stats["absent_days"] += 1
                
                monthly_stats["total_hours"] += day_view.get("worked_hours", 0)
                monthly_stats["extra_hours"] += day_view.get("extra_hours", 0)
                
                if day_view.get("has_delay"):
                    monthly_stats["delays"] += 1
                
                if day_view.get("has_early_exit"):
                    monthly_stats["early_exits"] += 1
                
                if day_view.get("has_incomplete_records"):
                    monthly_stats["incomplete_records"] += 1
            
            current_date += timedelta(days=1)
        
        # Calcula horas formatadas
        total_hours_str = self._format_hours(monthly_stats["total_hours"])
        extra_hours_str = self._format_hours(monthly_stats["extra_hours"])
        
        return {
            "employee": {
                "id": str(employee.id),
                "name": employee.full_name,
                "department": employee.department,
                "registration_number": employee.registration_number
            },
            "days": days_data,
            "statistics": monthly_stats if include_statistics else None,
            "summary": {
                "total_hours": total_hours_str,
                "extra_hours": extra_hours_str,
                "attendance_rate": self._calculate_attendance_rate(
                    monthly_stats["present_days"], monthly_stats["work_days"]
                )
            } if include_statistics else None
        }
    
    def _get_employee_daily_view(
        self,
        employee: EmployeeSupabase,
        target_date: date,
        work_hours: Dict[str, str]
    ) -> Dict[str, Any]:
        """Gera visualização diária para um funcionário."""
        # Obtém registros do dia
        records = self.db.query(TimeRecord).filter(
            TimeRecord.employee_id == employee.id,
            TimeRecord.record_date == target_date
        ).order_by(TimeRecord.record_time).all()
        
        # Parse work hours
        work_start = datetime.strptime(work_hours.get("start", "08:00"), "%H:%M").time()
        work_end = datetime.strptime(work_hours.get("end", "18:00"), "%H:%M").time()
        break_start = datetime.strptime(work_hours.get("break_start", "12:00"), "%H:%M").time()
        break_end = datetime.strptime(work_hours.get("break_end", "13:00"), "%H:%M").time()
        
        # Processa registros
        day_view = self._process_day_records(
            target_date, records,
            work_start, work_end, break_start, break_end
        )
        
        # Adiciona informações do funcionário
        day_view.update({
            "employee": {
                "id": str(employee.id),
                "name": employee.full_name,
                "department": employee.department,
                "photo_url": None  # Placeholder
            }
        })
        
        return day_view
    
    def _process_day_records(
        self,
        day_date: date,
        records: List[TimeRecord],
        work_start: datetime.time,
        work_end: datetime.time,
        break_start: datetime.time,
        break_end: datetime.time
    ) -> Dict[str, Any]:
        """Processa registros de um dia."""
        # Verifica se é dia útil
        is_work_day = day_date.weekday() < 5
        
        # Se não for dia útil ou não há registros
        if not is_work_day or not records:
            return {
                "date": day_date.isoformat(),
                "formatted_date": day_date.strftime("%d/%m/%Y"),
                "weekday": day_date.strftime("%A"),
                "is_work_day": is_work_day,
                "status": "not_work_day" if not is_work_day else "absent",
                "records": [],
                "has_records": False,
                "worked_hours": 0.0,
                "extra_hours": 0.0,
                "has_delay": False,
                "has_early_exit": False,
                "has_incomplete_records": False,
                "occurrences": []
            }
        
        # Agrupa registros por tipo
        entries = []
        exits = []
        break_starts = []
        break_ends = []
        
        for record in records:
            if record.record_type == "entry":
                entries.append(record)
            elif record.record_type == "exit":
                exits.append(record)
            elif record.record_type == "break_start":
                break_starts.append(record)
            elif record.record_type == "break_end":
                break_ends.append(record)
        
        # Ordena por horário
        entries.sort(key=lambda x: x.record_time)
        exits.sort(key=lambda x: x.record_time)
        break_starts.sort(key=lambda x: x.record_time)
        break_ends.sort(key=lambda x: x.record_time)
        
        # Calcula horas trabalhadas
        worked_hours = 0.0
        extra_hours = 0.0
        has_delay = False
        has_early_exit = False
        has_incomplete_records = False
        
        # Verifica se tem entrada e saída
        if entries and exits:
            # Usa primeira entrada e última saída
            first_entry = entries[0]
            last_exit = exits[-1]
            
            # Calcula horas entre entrada e saída
            entry_time = datetime.strptime(first_entry.record_time, "%H:%M:%S")
            exit_time = datetime.strptime(last_exit.record_time, "%H:%M:%S")
            
            total_hours = (exit_time - entry_time).total_seconds() / 3600
            
            # Subtrai intervalo de almoço se existir
            if break_starts and break_ends:
                break_start_time = datetime.strptime(break_starts[0].record_time, "%H:%M:%S")
                break_end_time = datetime.strptime(break_ends[0].record_time, "%H:%M:%S")
                break_hours = (break_end_time - break_start_time).total_seconds() / 3600
                total_hours -= break_hours
            
            worked_hours = max(0, total_hours)
            
            # Calcula horas extras (acima de 8 horas)
            normal_hours = 8.0  # Jornada padrão
            if worked_hours > normal_hours:
                extra_hours = worked_hours - normal_hours
            
            # Verifica atraso
            expected_start = datetime.combine(day_date, work_start)
            actual_start = datetime.combine(day_date, entry_time.time())
            
            if actual_start > expected_start + timedelta(minutes=10):  # Tolerância 10min
                has_delay = True
            
            # Verifica saída antecipada
            expected_end = datetime.combine(day_date, work_end)
            actual_end = datetime.combine(day_date, exit_time.time())
            
            if actual_end < expected_end - timedelta(minutes=10):  # Tolerância 10min
                has_early_exit = True
        
        # Verifica registros incompletos
        expected_record_count = 4  # entrada, saída almoço, retorno, saída
        if len(records) < expected_record_count:
            has_incomplete_records = True
        
        # Detecta ocorrências
        occurrences = self._detect_day_occurrences_from_records(records, day_date)
        
        # Formata registros para visualização
        formatted_records = []
        for record in records:
            formatted_records.append({
                "id": str(record.id),
                "time": record.record_time,
                "type": record.record_type,
                "type_label": self._get_record_type_label(record.record_type),
                "source": record.source,
                "is_adjusted": record.is_adjusted,
                "adjusted_reason": record.adjustment_reason
            })
        
        return {
            "date": day_date.isoformat(),
            "formatted_date": day_date.strftime("%d/%m/%Y"),
            "weekday": day_date.strftime("%A"),
            "is_work_day": is_work_day,
            "status": "present" if records else "absent",
            "records": formatted_records,
            "has_records": len(records) > 0,
            "worked_hours": round(worked_hours, 2),
            "extra_hours": round(extra_hours, 2),
            "has_delay": has_delay,
            "has_early_exit": has_early_exit,
            "has_incomplete_records": has_incomplete_records,
            "occurrences": occurrences,
            "summary": {
                "first_entry": entries[0].record_time if entries else None,
                "last_exit": exits[-1].record_time if exits else None,
                "break_start": break_starts[0].record_time if break_starts else None,
                "break_end": break_ends[0].record_time if break_ends else None,
                "record_count": len(records)
            }
        }
    
    def _detect_day_occurrences(
        self,
        records: List[Dict[str, Any]],
        day_date: date
    ) -> List[Dict[str, Any]]:
        """Detecta ocorrências em registros formatados."""
        occurrences = []
        
        # Verifica se é dia útil
        if day_date.weekday() >= 5:
            return occurrences
        
        # Conta registros por tipo
        type_counts = defaultdict(int)
        for record in records:
            type_counts[record["type"]] += 1
        
        # Verifica registros incompletos
        expected_types = {"entry", "exit"}
        if not all(t in type_counts for t in expected_types):
            occurrences.append({
                "type": "incomplete_record",
                "severity": "medium",
                "description": "Registros incompletos"
            })
        
        # Verifica múltiplas entradas/saídas
        if type_counts.get("entry", 0) > 1:
            occurrences.append({
                "type": "multiple_entries",
                "severity": "low",
                "description": f"Múltiplas entradas ({type_counts['entry']})"
            })
        
        if type_counts.get("exit", 0) > 1:
            occurrences.append({
                "type": "multiple_exits",
                "severity": "low",
                "description": f"Múltiplas saídas ({type_counts['exit']})"
            })
        
        return occurrences
    
    def _detect_day_occurrences_from_records(
        self,
        records: List[TimeRecord],
        day_date: date
    ) -> List[Dict[str, Any]]:
        """Detecta ocorrências em registros do banco."""
        # Implementação similar à anterior, mas com TimeRecord
        occurrences = []
        
        if day_date.weekday() >= 5:
            return occurrences
        
        type_counts = defaultdict(int)
        for record in records:
            type_counts[record.record_type] += 1
        
        expected_types = {"entry", "exit"}
        if not all(t in type_counts for t in expected_types):
            occurrences.append({
                "type": "incomplete_record",
                "severity": "medium",
                "description": "Registros incompletos"
            })
        
        if type_counts.get("entry", 0) > 1:
            occurrences.append({
                "type": "multiple_entries",
                "severity": "low",
                "description": f"Múltiplas entradas ({type_counts['entry']})"
            })
        
        if type_counts.get("exit", 0) > 1:
            occurrences.append({
                "type": "multiple_exits",
                "severity": "low",
                "description": f"Múltiplas saídas ({type_counts['exit']})"
            })
        
        return occurrences
    
    def _get_record_type_label(self, record_type: str) -> str:
        """Retorna label humanizado para tipo de registro."""
        labels = {
            "entry": "Entrada",
            "exit": "Saída",
            "break_start": "Saída Almoço",
            "break_end": "Retorno Almoço",
            "unknown": "Desconhecido"
        }
        return labels.get(record_type, record_type)
    
    def _get_month_end_date(self, year: int, month: int) -> date:
        """Retorna última data do mês."""
        if month == 12:
            return date(year, month, 31)
        else:
            next_month = date(year, month + 1, 1)
            return next_month - timedelta(days=1)
    
    def _format_hours(self, hours: float) -> str:
        """Formata horas para string HHhMM."""
        total_minutes = int(hours * 60)
        hours_part = total_minutes // 60
        minutes_part = total_minutes % 60
        
        if minutes_part == 0:
            return f"{hours_part}h"
        else:
            return f"{hours_part}h{minutes_part:02d}"
    
    def _calculate_attendance_rate(self, present_days: int, work_days: int) -> float:
        """Calcula taxa de presença."""
        if work_days == 0:
            return 0.0
        return round((present_days / work_days) * 100, 1)