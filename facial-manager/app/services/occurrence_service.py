"""
OccurrenceService — Serviço de detecção e gerenciamento de ocorrências.

Responsabilidades:
1. Detectar ocorrências automáticamente comparando registros vs. horário de trabalho
2. Criar registros de Occurrence no Supabase
3. CRUD operations para ocorrências
4. Atribuição de ocorrências a gerentes
5. Resolução/dismissão de ocorrências

Tipos de Ocorrências Detectadas:
- late: Entrada atrasada
- early_exit: Saída antecipada
- absence: Falta (sem registros no dia)
- incomplete_day: Dia incompleto (faltou entrada ou saída)
- missing_break: Não registrou intervalo (se configurado)
- excessive_hours: Horas além do permitido
"""

import logging
from datetime import datetime, timedelta, time, date
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.database.models_cloud import (
    Occurrence,
    TimeRecord,
    EmployeeSupabase,
    Company,
    WorkPeriod,
)

logger = logging.getLogger("occurrence_service")


class OccurrenceService:
    """Serviço de gerenciamento de ocorrências."""

    # Mapeamento de tipos de ocorrência para severidade padrão
    SEVERITY_MAP = {
        "late": "low",
        "early_exit": "low",
        "absence": "high",
        "incomplete_day": "medium",
        "missing_break": "low",
        "excessive_hours": "medium",
    }

    # Configuração de tolerância por tipo (em minutos)
    TOLERANCE_MINUTES = {
        "late": 5,  # Até 5 minutos é tolerado
        "early_exit": 5,
        "absence": 0,  # Sem tolerância
    }

    @staticmethod
    def parse_time_from_string(time_str: str) -> Optional[time]:
        """Converte string HH:MM:SS ou HH:MM para objeto time."""
        if not time_str:
            return None
        try:
            parts = time_str.split(":")
            if len(parts) >= 2:
                return time(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            pass
        return None

    @staticmethod
    def get_work_hours_for_employee(
        db: Session,
        employee_id: UUID,
        company_id: UUID
    ) -> Optional[Dict[str, str]]:
        """
        Obtém horário de trabalho do funcionário.
        
        Ordem de precedência:
        1. Horário específico do funcionário (employee.work_schedule)
        2. Horário padrão da empresa (company.work_hours)
        
        Retorna: {"start": "HH:MM", "end": "HH:MM", "break_start": "HH:MM", "break_end": "HH:MM"}
        """
        try:
            employee = db.query(EmployeeSupabase).filter(
                EmployeeSupabase.id == employee_id,
                EmployeeSupabase.company_id == company_id
            ).first()

            if not employee:
                logger.warning(f"Funcionário {employee_id} não encontrado")
                return None

            # Se funcionário tem horário específico, usa ele
            if employee.work_schedule:
                return employee.work_schedule

            # Caso contrário, usa horário padrão da empresa
            company = db.query(Company).filter(Company.id == company_id).first()
            if company and company.work_hours:
                return company.work_hours

            # Horário padrão fallback
            return {
                "start": "08:00",
                "end": "18:00",
                "break_start": "12:00",
                "break_end": "13:00",
            }

        except Exception as e:
            logger.error(f"Erro ao obter horário do funcionário: {str(e)}")
            return None

    @classmethod
    def detect_occurrences(
        cls,
        db: Session,
        company_id: UUID,
        employee_id: UUID,
        occurrence_date: date,
    ) -> List[Dict[str, Any]]:
        """
        Detecta ocorrências para um funcionário em uma data específica.
        
        Retorna lista de ocorrências detectadas (não as cria automaticamente).
        """
        occurrences_detected = []

        try:
            # Obtém registros do dia
            records = db.query(TimeRecord).filter(
                and_(
                    TimeRecord.company_id == company_id,
                    TimeRecord.employee_id == employee_id,
                    TimeRecord.record_date == datetime.combine(occurrence_date, time.min),
                )
            ).order_by(TimeRecord.record_time).all()

            # Obtém horário de trabalho
            work_hours = cls.get_work_hours_for_employee(db, employee_id, company_id)
            if not work_hours:
                logger.warning(
                    f"Não foi possível obter horário para {employee_id} em {company_id}"
                )
                return occurrences_detected

            start_time = cls.parse_time_from_string(work_hours.get("start", "08:00"))
            end_time = cls.parse_time_from_string(work_hours.get("end", "18:00"))
            break_start = cls.parse_time_from_string(work_hours.get("break_start", "12:00"))
            break_end = cls.parse_time_from_string(work_hours.get("break_end", "13:00"))

            # DETECÇÃO 1: Falta — nenhum registro no dia
            if not records:
                occurrences_detected.append({
                    "type": "absence",
                    "severity": "high",
                    "description": "Funcionário não registrou entrada",
                    "details": {
                        "expected_start": work_hours.get("start"),
                    },
                })
                return occurrences_detected  # Se faltou, não há mais o que detectar

            # Agrupa registros por tipo
            entries = [r for r in records if r.record_type == "entry"]
            exits = [r for r in records if r.record_type == "exit"]

            # DETECÇÃO 2: Entrada atrasada
            if entries:
                first_entry_time = cls.parse_time_from_string(entries[0].record_time)
                if first_entry_time and start_time:
                    tolerance = timedelta(minutes=cls.TOLERANCE_MINUTES.get("late", 5))
                    if first_entry_time > (datetime.combine(date.today(), start_time) + tolerance).time():
                        minutes_late = int(
                            (
                                datetime.combine(date.today(), first_entry_time)
                                - datetime.combine(date.today(), start_time)
                            ).total_seconds() / 60
                        )
                        occurrences_detected.append({
                            "type": "late",
                            "severity": "low",
                            "description": f"Entrada atrasada ({minutes_late} minutos)",
                            "details": {
                                "expected_time": work_hours.get("start"),
                                "actual_time": entries[0].record_time,
                                "minutes_late": minutes_late,
                            },
                        })

            # DETECÇÃO 3: Saída antecipada
            if exits:
                last_exit_time = cls.parse_time_from_string(exits[-1].record_time)
                if last_exit_time and end_time:
                    tolerance = timedelta(minutes=cls.TOLERANCE_MINUTES.get("early_exit", 5))
                    if last_exit_time < (datetime.combine(date.today(), end_time) - tolerance).time():
                        minutes_early = int(
                            (
                                datetime.combine(date.today(), end_time)
                                - datetime.combine(date.today(), last_exit_time)
                            ).total_seconds() / 60
                        )
                        occurrences_detected.append({
                            "type": "early_exit",
                            "severity": "low",
                            "description": f"Saída antecipada ({minutes_early} minutos)",
                            "details": {
                                "expected_time": work_hours.get("end"),
                                "actual_time": exits[-1].record_time,
                                "minutes_early": minutes_early,
                            },
                        })

            # DETECÇÃO 4: Dia incompleto (sem entrada ou saída)
            if not entries:
                occurrences_detected.append({
                    "type": "incomplete_day",
                    "severity": "medium",
                    "description": "Sem registro de entrada",
                    "details": {},
                })
            elif not exits:
                occurrences_detected.append({
                    "type": "incomplete_day",
                    "severity": "medium",
                    "description": "Sem registro de saída",
                    "details": {},
                })

            logger.info(
                f"Detectadas {len(occurrences_detected)} ocorrências para {employee_id} em {occurrence_date}"
            )
            return occurrences_detected

        except Exception as e:
            logger.error(f"Erro ao detectar ocorrências: {str(e)}")
            return occurrences_detected

    @classmethod
    def create_occurrence(
        cls,
        db: Session,
        company_id: UUID,
        employee_id: UUID,
        occurrence_date: date,
        occurrence_type: str,
        description: str = "",
        details: Optional[Dict[str, Any]] = None,
        severity: Optional[str] = None,
        assigned_to: Optional[str] = None,
    ) -> Optional[Occurrence]:
        """
        Cria um novo registro de ocorrência.
        
        Args:
            db: Sessão do banco
            company_id: ID da empresa
            employee_id: ID do funcionário
            occurrence_date: Data da ocorrência
            occurrence_type: Tipo (late, absence, early_exit, etc.)
            description: Descrição textual
            details: Detalhes adicionais (JSON)
            severity: Severidade (low, medium, high, critical) — default baseado em type
            assigned_to: ID do usuário responsável (gerente/RH)
        
        Returns: Objeto Occurrence criado ou None em caso de erro
        """
        try:
            from uuid import uuid4
            
            # Define severidade se não informada
            if not severity:
                severity = cls.SEVERITY_MAP.get(occurrence_type, "medium")

            occurrence = Occurrence(
                id=uuid4(),  # Gera UUID explicitamente
                company_id=company_id,
                employee_id=employee_id,
                occurrence_date=datetime.combine(occurrence_date, time.min),
                occurrence_type=occurrence_type,
                description=description,
                details=details or {},
                severity=severity,
                status="pending",
                assigned_to=assigned_to,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            db.add(occurrence)
            db.commit()
            db.refresh(occurrence)

            logger.info(
                f"Ocorrência criada: {occurrence.id} (empresa: {company_id}, "
                f"funcionário: {employee_id}, tipo: {occurrence_type})"
            )
            return occurrence

        except Exception as e:
            logger.error(f"Erro ao criar ocorrência: {str(e)}")
            db.rollback()
            return None

    @classmethod
    def create_occurrences_from_detection(
        cls,
        db: Session,
        company_id: UUID,
        employee_id: UUID,
        occurrence_date: date,
        assigned_to: Optional[str] = None,
    ) -> List[Occurrence]:
        """
        Detecta ocorrências e as cria no banco em uma operação.
        
        Retorna lista de ocorrências criadas.
        """
        created_occurrences = []

        try:
            # Detecta ocorrências
            detected = cls.detect_occurrences(db, company_id, employee_id, occurrence_date)

            # Cria cada uma
            for occ_data in detected:
                occurrence = cls.create_occurrence(
                    db=db,
                    company_id=company_id,
                    employee_id=employee_id,
                    occurrence_date=occurrence_date,
                    occurrence_type=occ_data["type"],
                    description=occ_data["description"],
                    details=occ_data.get("details", {}),
                    severity=occ_data.get("severity"),
                    assigned_to=assigned_to,
                )
                if occurrence:
                    created_occurrences.append(occurrence)

            return created_occurrences

        except Exception as e:
            logger.error(f"Erro ao criar ocorrências em lote: {str(e)}")
            return created_occurrences

    @classmethod
    def get_occurrence(
        cls,
        db: Session,
        company_id: UUID,
        occurrence_id: UUID,
    ) -> Optional[Occurrence]:
        """Obtém uma ocorrência por ID com validação de empresa."""
        try:
            occurrence = db.query(Occurrence).filter(
                and_(
                    Occurrence.id == occurrence_id,
                    Occurrence.company_id == company_id,
                )
            ).first()

            if not occurrence:
                logger.warning(f"Ocorrência {occurrence_id} não encontrada para empresa {company_id}")

            return occurrence

        except Exception as e:
            logger.error(f"Erro ao obter ocorrência: {str(e)}")
            return None

    @classmethod
    def list_occurrences(
        cls,
        db: Session,
        company_id: UUID,
        filters: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[List[Occurrence], int]:
        """
        Lista ocorrências com filtros opcionais.
        
        Filtros suportados:
        - status: pending, reviewed, resolved, dismissed
        - occurrence_type: late, absence, early_exit, etc.
        - severity: low, medium, high, critical
        - employee_id: UUID do funcionário
        - start_date: Data inicial (YYYY-MM-DD)
        - end_date: Data final (YYYY-MM-DD)
        
        Retorna: (lista de ocorrências, total de registros)
        """
        try:
            query = db.query(Occurrence).filter(Occurrence.company_id == company_id)

            if filters:
                if filters.get("status"):
                    query = query.filter(Occurrence.status == filters["status"])

                if filters.get("occurrence_type"):
                    query = query.filter(Occurrence.occurrence_type == filters["occurrence_type"])

                if filters.get("severity"):
                    query = query.filter(Occurrence.severity == filters["severity"])

                if filters.get("employee_id"):
                    query = query.filter(Occurrence.employee_id == filters["employee_id"])

                if filters.get("start_date"):
                    try:
                        start_date = datetime.fromisoformat(filters["start_date"])
                        query = query.filter(Occurrence.occurrence_date >= start_date)
                    except (ValueError, TypeError):
                        pass

                if filters.get("end_date"):
                    try:
                        end_date = datetime.fromisoformat(filters["end_date"])
                        # Adiciona 1 dia para incluir todo o dia final
                        end_date = end_date + timedelta(days=1)
                        query = query.filter(Occurrence.occurrence_date < end_date)
                    except (ValueError, TypeError):
                        pass

            # Conta total
            total = query.count()

            # Aplica paginação
            occurrences = query.order_by(Occurrence.occurrence_date.desc()).offset(skip).limit(limit).all()

            return occurrences, total

        except Exception as e:
            logger.error(f"Erro ao listar ocorrências: {str(e)}")
            return [], 0

    @classmethod
    def update_occurrence_status(
        cls,
        db: Session,
        company_id: UUID,
        occurrence_id: UUID,
        new_status: str,
        resolved_by: Optional[str] = None,
        resolution_notes: Optional[str] = None,
    ) -> Optional[Occurrence]:
        """
        Atualiza status de uma ocorrência.
        
        Status válidos: pending, reviewed, resolved, dismissed
        
        Se novo_status é "resolved" ou "dismissed", registra resolved_by e resolution_notes.
        """
        try:
            occurrence = cls.get_occurrence(db, company_id, occurrence_id)
            if not occurrence:
                return None

            # Valida transição de status
            valid_statuses = ["pending", "reviewed", "resolved", "dismissed"]
            if new_status not in valid_statuses:
                logger.warning(f"Status inválido: {new_status}")
                return None

            occurrence.status = new_status
            occurrence.updated_at = datetime.now()

            if new_status in ["resolved", "dismissed"]:
                occurrence.resolved_by = resolved_by
                occurrence.resolved_at = datetime.now()
                occurrence.resolution_notes = resolution_notes

            db.commit()
            db.refresh(occurrence)

            logger.info(
                f"Status da ocorrência {occurrence_id} atualizado para {new_status}"
            )
            return occurrence

        except Exception as e:
            logger.error(f"Erro ao atualizar status da ocorrência: {str(e)}")
            db.rollback()
            return None

    @classmethod
    def assign_occurrence(
        cls,
        db: Session,
        company_id: UUID,
        occurrence_id: UUID,
        assigned_to: str,
    ) -> Optional[Occurrence]:
        """Atribui uma ocorrência a um usuário (gerente/RH)."""
        try:
            occurrence = cls.get_occurrence(db, company_id, occurrence_id)
            if not occurrence:
                return None

            occurrence.assigned_to = assigned_to
            occurrence.updated_at = datetime.now()

            db.commit()
            db.refresh(occurrence)

            logger.info(f"Ocorrência {occurrence_id} atribuída a {assigned_to}")
            return occurrence

        except Exception as e:
            logger.error(f"Erro ao atribuir ocorrência: {str(e)}")
            db.rollback()
            return None

    @classmethod
    def delete_occurrence(
        cls,
        db: Session,
        company_id: UUID,
        occurrence_id: UUID,
    ) -> bool:
        """
        Remove uma ocorrência (soft delete via status, não remove do banco).
        
        Retorna True se sucesso, False caso contrário.
        """
        try:
            occurrence = cls.get_occurrence(db, company_id, occurrence_id)
            if not occurrence:
                return False

            # Soft delete: marca como dismissed
            occurrence.status = "dismissed"
            occurrence.updated_at = datetime.now()

            db.commit()

            logger.info(f"Ocorrência {occurrence_id} removida (soft delete)")
            return True

        except Exception as e:
            logger.error(f"Erro ao remover ocorrência: {str(e)}")
            db.rollback()
            return False

    @classmethod
    def get_occurrences_by_employee_and_period(
        cls,
        db: Session,
        company_id: UUID,
        employee_id: UUID,
        start_date: date,
        end_date: date,
    ) -> List[Occurrence]:
        """Obtém todas as ocorrências de um funcionário em um período."""
        try:
            start_dt = datetime.combine(start_date, time.min)
            end_dt = datetime.combine(end_date, time.max)

            occurrences = db.query(Occurrence).filter(
                and_(
                    Occurrence.company_id == company_id,
                    Occurrence.employee_id == employee_id,
                    Occurrence.occurrence_date >= start_dt,
                    Occurrence.occurrence_date <= end_dt,
                )
            ).order_by(Occurrence.occurrence_date).all()

            return occurrences

        except Exception as e:
            logger.error(f"Erro ao obter ocorrências do período: {str(e)}")
            return []

    @classmethod
    def get_statistics(
        cls,
        db: Session,
        company_id: UUID,
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        """Obtém estatísticas de ocorrências para um período."""
        try:
            start_dt = datetime.combine(start_date, time.min)
            end_dt = datetime.combine(end_date, time.max)

            query = db.query(Occurrence).filter(
                and_(
                    Occurrence.company_id == company_id,
                    Occurrence.occurrence_date >= start_dt,
                    Occurrence.occurrence_date <= end_dt,
                )
            )

            total = query.count()
            by_status = {}
            by_type = {}
            by_severity = {}

            for status in ["pending", "reviewed", "resolved", "dismissed"]:
                by_status[status] = query.filter(Occurrence.status == status).count()

            for occ_type in ["late", "absence", "early_exit", "incomplete_day", "missing_break", "excessive_hours"]:
                by_type[occ_type] = query.filter(Occurrence.occurrence_type == occ_type).count()

            for severity in ["low", "medium", "high", "critical"]:
                by_severity[severity] = query.filter(Occurrence.severity == severity).count()

            return {
                "total": total,
                "by_status": by_status,
                "by_type": by_type,
                "by_severity": by_severity,
            }

        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {str(e)}")
            return {
                "total": 0,
                "by_status": {},
                "by_type": {},
                "by_severity": {},
            }
