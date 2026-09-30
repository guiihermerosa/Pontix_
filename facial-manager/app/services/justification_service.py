"""
JustificationService — Serviço de gerenciamento de justificativas.

Responsabilidades:
1. Criar justificativas para ocorrências
2. Gerenciar workflow: submitted → reviewed → approved/rejected
3. Validação de justificativas
4. Auditoria de aprovações/rejeições
5. Linking entre justificativas e ocorrências

Tipos de Justificativa:
- medical: Atestado médico
- personal: Motivo pessoal (com descrição)
- work_related: Assunto de trabalho
- court_order: Ordem judicial
- other: Outro (requer descrição)
"""

import logging
from datetime import datetime, date, time, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.database.models_supabase import (
    Justification,
    Occurrence,
    EmployeeSupabase,
    Company,
)

logger = logging.getLogger("justification_service")


class JustificationService:
    """Serviço de gerenciamento de justificativas."""

    # Tipos de justificativa suportados
    VALID_TYPES = [
        "medical",
        "personal",
        "work_related",
        "court_order",
        "other",
    ]

    # Status válidos
    VALID_STATUSES = ["pending", "approved", "rejected"]

    @classmethod
    def create_justification(
        cls,
        db: Session,
        company_id: UUID,
        employee_id: UUID,
        justification_type: str,
        start_date: date,
        end_date: date,
        description: str,
        occurrence_id: Optional[UUID] = None,
        supporting_document_url: Optional[str] = None,
        submitted_by: Optional[str] = None,
    ) -> Optional[Justification]:
        """
        Cria uma nova justificativa.
        
        Args:
            db: Sessão do banco
            company_id: ID da empresa
            employee_id: ID do funcionário
            justification_type: Tipo (medical, personal, work_related, court_order, other)
            start_date: Data inicial da justificativa
            end_date: Data final da justificativa
            description: Descrição detalhada
            occurrence_id: ID da ocorrência (opcional, pode estar relacionada)
            supporting_document_url: URL do documento comprobatório
            submitted_by: ID do usuário que submeteu (employee_id ou manager)
        
        Returns: Objeto Justification criado ou None em caso de erro
        """
        try:
            from uuid import uuid4
            
            # Valida tipo
            if justification_type not in cls.VALID_TYPES:
                logger.warning(f"Tipo de justificativa inválido: {justification_type}")
                return None

            # Valida datas
            if start_date > end_date:
                logger.warning(f"Data inicial após data final: {start_date} > {end_date}")
                return None

            # Se há occurrence_id, valida que pertence à mesma empresa/funcionário
            if occurrence_id:
                occurrence = db.query(Occurrence).filter(
                    and_(
                        Occurrence.id == occurrence_id,
                        Occurrence.company_id == company_id,
                        Occurrence.employee_id == employee_id,
                    )
                ).first()

                if not occurrence:
                    logger.warning(
                        f"Ocorrência {occurrence_id} não encontrada para "
                        f"empresa {company_id} e funcionário {employee_id}"
                    )
                    return None

            # Cria justificativa
            justification = Justification(
                id=uuid4(),  # Gera UUID explicitamente
                company_id=company_id,
                employee_id=employee_id,
                occurrence_id=occurrence_id,
                justification_type=justification_type,
                start_date=datetime.combine(start_date, time.min),
                end_date=datetime.combine(end_date, time.max),
                description=description,
                supporting_document_url=supporting_document_url,
                submitted_by=submitted_by,
                status="pending",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            db.add(justification)
            db.commit()
            db.refresh(justification)

            logger.info(
                f"Justificativa criada: {justification.id} "
                f"(empresa: {company_id}, funcionário: {employee_id}, tipo: {justification_type})"
            )

            # Se há occurrence_id, atualiza status da ocorrência para "reviewed"
            if occurrence_id:
                occurrence = db.query(Occurrence).filter(
                    Occurrence.id == occurrence_id
                ).first()
                if occurrence:
                    occurrence.status = "reviewed"
                    occurrence.updated_at = datetime.now()
                    db.commit()

            return justification

        except Exception as e:
            logger.error(f"Erro ao criar justificativa: {str(e)}")
            db.rollback()
            return None

    @classmethod
    def get_justification(
        cls,
        db: Session,
        company_id: UUID,
        justification_id: UUID,
    ) -> Optional[Justification]:
        """Obtém uma justificativa por ID com validação de empresa."""
        try:
            justification = db.query(Justification).filter(
                and_(
                    Justification.id == justification_id,
                    Justification.company_id == company_id,
                )
            ).first()

            if not justification:
                logger.warning(
                    f"Justificativa {justification_id} não encontrada para empresa {company_id}"
                )

            return justification

        except Exception as e:
            logger.error(f"Erro ao obter justificativa: {str(e)}")
            return None

    @classmethod
    def list_justifications(
        cls,
        db: Session,
        company_id: UUID,
        filters: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[List[Justification], int]:
        """
        Lista justificativas com filtros opcionais.
        
        Filtros suportados:
        - status: pending, approved, rejected
        - justification_type: medical, personal, work_related, court_order, other
        - employee_id: UUID do funcionário
        - start_date: Data inicial (YYYY-MM-DD)
        - end_date: Data final (YYYY-MM-DD)
        - submitted_by: ID do usuário que submeteu
        
        Retorna: (lista de justificativas, total de registros)
        """
        try:
            query = db.query(Justification).filter(Justification.company_id == company_id)

            if filters:
                if filters.get("status"):
                    query = query.filter(Justification.status == filters["status"])

                if filters.get("justification_type"):
                    query = query.filter(Justification.justification_type == filters["justification_type"])

                if filters.get("employee_id"):
                    query = query.filter(Justification.employee_id == filters["employee_id"])

                if filters.get("start_date"):
                    try:
                        start_date = datetime.fromisoformat(filters["start_date"])
                        query = query.filter(Justification.start_date >= start_date)
                    except (ValueError, TypeError):
                        pass

                if filters.get("end_date"):
                    try:
                        end_date = datetime.fromisoformat(filters["end_date"])
                        # Adiciona 1 dia para incluir todo o dia final
                        end_date = end_date + timedelta(days=1)
                        query = query.filter(Justification.start_date < end_date)
                    except (ValueError, TypeError):
                        pass

                if filters.get("submitted_by"):
                    query = query.filter(Justification.submitted_by == filters["submitted_by"])

            # Conta total
            total = query.count()

            # Aplica paginação
            justifications = query.order_by(Justification.start_date.desc()).offset(skip).limit(limit).all()

            return justifications, total

        except Exception as e:
            logger.error(f"Erro ao listar justificativas: {str(e)}")
            return [], 0

    @classmethod
    def approve_justification(
        cls,
        db: Session,
        company_id: UUID,
        justification_id: UUID,
        approved_by: str,
    ) -> Optional[Justification]:
        """
        Aprova uma justificativa.
        
        Transição: pending → approved
        """
        try:
            justification = cls.get_justification(db, company_id, justification_id)
            if not justification:
                return None

            if justification.status != "pending":
                logger.warning(
                    f"Justificativa {justification_id} não está em status 'pending' "
                    f"(atual: {justification.status})"
                )
                return None

            justification.status = "approved"
            justification.approved_by = approved_by
            justification.approved_at = datetime.now()
            justification.updated_at = datetime.now()

            db.commit()
            db.refresh(justification)

            logger.info(
                f"Justificativa {justification_id} aprovada por {approved_by}"
            )

            # Se há occurrence_id, atualiza status da ocorrência para "resolved"
            if justification.occurrence_id:
                occurrence = db.query(Occurrence).filter(
                    Occurrence.id == justification.occurrence_id
                ).first()
                if occurrence:
                    occurrence.status = "resolved"
                    occurrence.resolved_by = approved_by
                    occurrence.resolved_at = datetime.now()
                    occurrence.resolution_notes = f"Justificativa aprovada: {justification.description}"
                    db.commit()
                    logger.info(
                        f"Ocorrência {justification.occurrence_id} resolvida pela justificativa aprovada"
                    )

            return justification

        except Exception as e:
            logger.error(f"Erro ao aprovar justificativa: {str(e)}")
            db.rollback()
            return None

    @classmethod
    def reject_justification(
        cls,
        db: Session,
        company_id: UUID,
        justification_id: UUID,
        rejected_by: str,
        rejection_reason: str,
    ) -> Optional[Justification]:
        """
        Rejeita uma justificativa.
        
        Transição: pending → rejected
        
        Args:
            db: Sessão do banco
            company_id: ID da empresa
            justification_id: ID da justificativa
            rejected_by: ID do usuário que rejeitou
            rejection_reason: Motivo da rejeição
        
        Returns: Justificativa atualizada ou None em caso de erro
        """
        try:
            justification = cls.get_justification(db, company_id, justification_id)
            if not justification:
                return None

            if justification.status != "pending":
                logger.warning(
                    f"Justificativa {justification_id} não está em status 'pending' "
                    f"(atual: {justification.status})"
                )
                return None

            justification.status = "rejected"
            justification.approved_by = rejected_by  # Reutiliza campo para rastrear quem rejeitou
            justification.approved_at = datetime.now()
            justification.rejection_reason = rejection_reason
            justification.updated_at = datetime.now()

            db.commit()
            db.refresh(justification)

            logger.info(
                f"Justificativa {justification_id} rejeitada por {rejected_by}. "
                f"Motivo: {rejection_reason}"
            )

            # Se há occurrence_id, mantém status "reviewed" (pode reenviar justificativa)
            # Não muda status da ocorrência automaticamente

            return justification

        except Exception as e:
            logger.error(f"Erro ao rejeitar justificativa: {str(e)}")
            db.rollback()
            return None

    @classmethod
    def get_justifications_by_employee_and_period(
        cls,
        db: Session,
        company_id: UUID,
        employee_id: UUID,
        start_date: date,
        end_date: date,
    ) -> List[Justification]:
        """Obtém todas as justificativas de um funcionário em um período."""
        try:
            start_dt = datetime.combine(start_date, time.min)
            end_dt = datetime.combine(end_date, time.max)

            justifications = db.query(Justification).filter(
                and_(
                    Justification.company_id == company_id,
                    Justification.employee_id == employee_id,
                    Justification.start_date >= start_dt,
                    Justification.start_date <= end_dt,
                )
            ).order_by(Justification.start_date).all()

            return justifications

        except Exception as e:
            logger.error(f"Erro ao obter justificativas do período: {str(e)}")
            return []

    @classmethod
    def get_justification_by_occurrence(
        cls,
        db: Session,
        company_id: UUID,
        occurrence_id: UUID,
    ) -> Optional[Justification]:
        """Obtém a justificativa associada a uma ocorrência."""
        try:
            justification = db.query(Justification).filter(
                and_(
                    Justification.company_id == company_id,
                    Justification.occurrence_id == occurrence_id,
                )
            ).first()

            return justification

        except Exception as e:
            logger.error(f"Erro ao obter justificativa da ocorrência: {str(e)}")
            return None

    @classmethod
    def get_statistics(
        cls,
        db: Session,
        company_id: UUID,
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        """Obtém estatísticas de justificativas para um período."""
        try:
            start_dt = datetime.combine(start_date, time.min)
            end_dt = datetime.combine(end_date, time.max)

            query = db.query(Justification).filter(
                and_(
                    Justification.company_id == company_id,
                    Justification.start_date >= start_dt,
                    Justification.start_date <= end_dt,
                )
            )

            total = query.count()
            by_status = {}
            by_type = {}

            for status in ["pending", "approved", "rejected"]:
                by_status[status] = query.filter(Justification.status == status).count()

            for jtype in cls.VALID_TYPES:
                by_type[jtype] = query.filter(Justification.justification_type == jtype).count()

            return {
                "total": total,
                "by_status": by_status,
                "by_type": by_type,
            }

        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {str(e)}")
            return {
                "total": 0,
                "by_status": {},
                "by_type": {},
            }

    @classmethod
    def validate_justification_for_dates(
        cls,
        db: Session,
        company_id: UUID,
        employee_id: UUID,
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        """
        Valida se há justificativas adequadas para um período.
        
        Retorna informação sobre cobertura e gaps.
        """
        try:
            current_date = start_date
            covered_dates = set()
            gap_dates = []

            while current_date <= end_date:
                # Procura justificativa que cubra este dia
                justifications = db.query(Justification).filter(
                    and_(
                        Justification.company_id == company_id,
                        Justification.employee_id == employee_id,
                        Justification.start_date <= datetime.combine(current_date, time.max),
                        Justification.end_date >= datetime.combine(current_date, time.min),
                        Justification.status == "approved",
                    )
                ).all()

                if justifications:
                    covered_dates.add(current_date)
                else:
                    gap_dates.append(current_date)

                current_date += timedelta(days=1)

            return {
                "total_days": (end_date - start_date).days + 1,
                "covered_days": len(covered_dates),
                "gap_days": len(gap_dates),
                "coverage_percentage": (
                    100 * len(covered_dates) / ((end_date - start_date).days + 1)
                    if (end_date - start_date).days > 0
                    else 0
                ),
                "gap_dates": gap_dates,
            }

        except Exception as e:
            logger.error(f"Erro ao validar justificativas: {str(e)}")
            return {
                "total_days": 0,
                "covered_days": 0,
                "gap_days": 0,
                "coverage_percentage": 0,
                "gap_dates": [],
            }
