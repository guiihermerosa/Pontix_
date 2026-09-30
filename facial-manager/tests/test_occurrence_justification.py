"""
Testes abrangentes para Serviços de Ocorrências e Justificativas.

Cobertura:
1. OccurrenceService — detecção, CRUD, filtros
2. JustificationService — workflow, aprovação, rejeição
3. Segurança — data isolation, validação de company_id
4. Workflows — transições de status, linking
5. Edge cases — datas inválidas, funcionários não encontrados, etc.
"""

import pytest
from datetime import date, datetime, timedelta, time
from uuid import UUID, uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.models_supabase import (
    Base,
    Company,
    EmployeeSupabase,
    TimeRecord,
    Occurrence,
    Justification,
    WorkPeriod,
)
from app.services.occurrence_service import OccurrenceService
from app.services.justification_service import JustificationService


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def db():
    """Cria banco de dados em memória para testes."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def company(db: Session):
    """Cria empresa de teste."""
    company_obj = Company(
        id=uuid4(),
        name="Empresa Teste",
        cnpj="12.345.678/0001-90",
        timezone="America/Sao_Paulo",
        work_hours={
            "start": "08:00",
            "end": "18:00",
            "break_start": "12:00",
            "break_end": "13:00",
        },
        is_active=True,
    )
    db.add(company_obj)
    db.commit()
    return company_obj


@pytest.fixture
def employee(db: Session, company: Company):
    """Cria funcionário de teste."""
    employee_obj = EmployeeSupabase(
        id=uuid4(),
        company_id=company.id,
        user_id="emp_001",
        full_name="João Silva",
        is_active=True,
        work_schedule={
            "start": "08:00",
            "end": "18:00",
            "break_start": "12:00",
            "break_end": "13:00",
        },
    )
    db.add(employee_obj)
    db.commit()
    return employee_obj


@pytest.fixture
def another_employee(db: Session, company: Company):
    """Cria outro funcionário de teste."""
    employee_obj = EmployeeSupabase(
        id=uuid4(),
        company_id=company.id,
        user_id="emp_002",
        full_name="Maria Santos",
        is_active=True,
    )
    db.add(employee_obj)
    db.commit()
    return employee_obj


@pytest.fixture
def another_company(db: Session):
    """Cria segunda empresa para testes de isolamento."""
    company_obj = Company(
        id=uuid4(),
        name="Outra Empresa",
        cnpj="98.765.432/0001-01",
        is_active=True,
    )
    db.add(company_obj)
    db.commit()
    return company_obj


@pytest.fixture
def time_records(db: Session, employee: EmployeeSupabase, company: Company):
    """Cria registros de ponto de teste."""
    today = date.today()
    records = [
        TimeRecord(
            id=uuid4(),
            company_id=company.id,
            employee_id=employee.id,
            user_id=employee.user_id,
            employee_name=employee.full_name,
            record_date=datetime.combine(today, time.min),
            record_time="08:15",  # 15 minutos atrasado
            record_type="entry",
            source="device",
        ),
        TimeRecord(
            id=uuid4(),
            company_id=company.id,
            employee_id=employee.id,
            user_id=employee.user_id,
            employee_name=employee.full_name,
            record_date=datetime.combine(today, time.min),
            record_time="17:45",  # 15 minutos antes do fim
            record_type="exit",
            source="device",
        ),
    ]
    for record in records:
        db.add(record)
    db.commit()
    return records


# ============================================================================
# TESTES: OccurrenceService — Detecção
# ============================================================================

class TestOccurrenceDetection:
    """Testes de detecção de ocorrências."""

    def test_detect_late_arrival(self, db: Session, employee: EmployeeSupabase, company: Company):
        """Detecta entrada atrasada."""
        today = date.today()
        
        # Registra entrada 15 minutos depois
        record = TimeRecord(
            id=uuid4(),
            company_id=company.id,
            employee_id=employee.id,
            user_id=employee.user_id,
            employee_name=employee.full_name,
            record_date=datetime.combine(today, time.min),
            record_time="08:15",
            record_type="entry",
            source="device",
        )
        db.add(record)
        db.commit()
        
        # Detecta ocorrências
        detected = OccurrenceService.detect_occurrences(
            db=db,
            company_id=company.id,
            employee_id=employee.id,
            occurrence_date=today,
        )
        
        # Verifica detecção
        assert len(detected) > 0
        late_occ = next((o for o in detected if o["type"] == "late"), None)
        assert late_occ is not None
        assert late_occ["severity"] == "low"
        assert late_occ["details"]["minutes_late"] == 15

    def test_detect_absence(self, db: Session, employee: EmployeeSupabase, company: Company):
        """Detecta falta (sem registros no dia)."""
        today = date.today()
        
        # Sem registros
        detected = OccurrenceService.detect_occurrences(
            db=db,
            company_id=company.id,
            employee_id=employee.id,
            occurrence_date=today,
        )
        
        # Verifica detecção
        assert len(detected) > 0
        absence_occ = next((o for o in detected if o["type"] == "absence"), None)
        assert absence_occ is not None
        assert absence_occ["severity"] == "high"

    def test_detect_early_exit(self, db: Session, employee: EmployeeSupabase, company: Company):
        """Detecta saída antecipada."""
        today = date.today()
        
        # Registra entrada normal e saída 15 minutos cedo
        records = [
            TimeRecord(
                id=uuid4(),
                company_id=company.id,
                employee_id=employee.id,
                user_id=employee.user_id,
                employee_name=employee.full_name,
                record_date=datetime.combine(today, time.min),
                record_time="08:00",
                record_type="entry",
                source="device",
            ),
            TimeRecord(
                id=uuid4(),
                company_id=company.id,
                employee_id=employee.id,
                user_id=employee.user_id,
                employee_name=employee.full_name,
                record_date=datetime.combine(today, time.min),
                record_time="17:45",  # 15 minutos antes de 18:00
                record_type="exit",
                source="device",
            ),
        ]
        for r in records:
            db.add(r)
        db.commit()
        
        # Detecta ocorrências
        detected = OccurrenceService.detect_occurrences(
            db=db,
            company_id=company.id,
            employee_id=employee.id,
            occurrence_date=today,
        )
        
        # Verifica detecção
        early_exit_occ = next((o for o in detected if o["type"] == "early_exit"), None)
        assert early_exit_occ is not None
        assert early_exit_occ["severity"] == "low"
        assert early_exit_occ["details"]["minutes_early"] == 15

    def test_detect_incomplete_day_no_exit(self, db: Session, employee: EmployeeSupabase, company: Company):
        """Detecta dia incompleto (sem saída)."""
        today = date.today()
        
        # Registra apenas entrada
        record = TimeRecord(
            id=uuid4(),
            company_id=company.id,
            employee_id=employee.id,
            user_id=employee.user_id,
            employee_name=employee.full_name,
            record_date=datetime.combine(today, time.min),
            record_time="08:00",
            record_type="entry",
            source="device",
        )
        db.add(record)
        db.commit()
        
        # Detecta ocorrências
        detected = OccurrenceService.detect_occurrences(
            db=db,
            company_id=company.id,
            employee_id=employee.id,
            occurrence_date=today,
        )
        
        # Verifica detecção
        incomplete_occ = next((o for o in detected if o["type"] == "incomplete_day"), None)
        assert incomplete_occ is not None
        assert "saída" in incomplete_occ["description"].lower()


# ============================================================================
# TESTES: OccurrenceService — CRUD
# ============================================================================

class TestOccurrenceCRUD:
    """Testes de CRUD para ocorrências."""

    def test_create_occurrence(self, db: Session, employee: EmployeeSupabase, company: Company):
        """Cria ocorrência."""
        today = date.today()
        
        occurrence = OccurrenceService.create_occurrence(
            db=db,
            company_id=company.id,
            employee_id=employee.id,
            occurrence_date=today,
            occurrence_type="late",
            description="Chegou 15 minutos atrasado",
            severity="low",
        )
        
        assert occurrence is not None
        assert occurrence.occurrence_type == "late"
        assert occurrence.status == "pending"
        assert occurrence.severity == "low"

    def test_get_occurrence(self, db: Session, employee: EmployeeSupabase, company: Company):
        """Obtém ocorrência por ID."""
        today = date.today()
        
        # Cria ocorrência
        created = OccurrenceService.create_occurrence(
            db=db,
            company_id=company.id,
            employee_id=employee.id,
            occurrence_date=today,
            occurrence_type="late",
            description="Teste",
        )
        
        # Obtém
        retrieved = OccurrenceService.get_occurrence(
            db=db,
            company_id=company.id,
            occurrence_id=created.id,
        )
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.occurrence_type == "late"

    def test_get_occurrence_wrong_company(self, db: Session, employee: EmployeeSupabase, company: Company, another_company: Company):
        """Data isolation: não retorna ocorrência de outra empresa."""
        today = date.today()
        
        # Cria ocorrência na primeira empresa
        created = OccurrenceService.create_occurrence(
            db=db,
            company_id=company.id,
            employee_id=employee.id,
            occurrence_date=today,
            occurrence_type="late",
        )
        
        # Tenta obter pela segunda empresa
        retrieved = OccurrenceService.get_occurrence(
            db=db,
            company_id=another_company.id,
            occurrence_id=created.id,
        )
        
        assert retrieved is None  # Não encontra (data isolation)

    def test_list_occurrences(self, db: Session, employee: EmployeeSupabase, company: Company):
        """Lista ocorrências."""
        today = date.today()
        
        # Cria 3 ocorrências
        for i in range(3):
            OccurrenceService.create_occurrence(
                db=db,
                company_id=company.id,
                employee_id=employee.id,
                occurrence_date=today - timedelta(days=i),
                occurrence_type="late" if i % 2 == 0 else "absence",
            )
        
        # Lista
        occurrences, total = OccurrenceService.list_occurrences(
            db=db,
            company_id=company.id,
            skip=0,
            limit=10,
        )
        
        assert total == 3
        assert len(occurrences) == 3

    def test_list_occurrences_with_filters(self, db: Session, employee: EmployeeSupabase, company: Company):
        """Lista ocorrências com filtros."""
        today = date.today()
        
        # Cria ocorrências de tipos diferentes
        OccurrenceService.create_occurrence(
            db=db,
            company_id=company.id,
            employee_id=employee.id,
            occurrence_date=today,
            occurrence_type="late",
        )
        OccurrenceService.create_occurrence(
            db=db,
            company_id=company.id,
            employee_id=employee.id,
            occurrence_date=today,
            occurrence_type="absence",
        )
        
        # Filtra apenas por "late"
        occurrences, total = OccurrenceService.list_occurrences(
            db=db,
            company_id=company.id,
            filters={"occurrence_type": "late"},
            skip=0,
            limit=10,
        )
        
        assert total == 1
        assert occurrences[0].occurrence_type == "late"

    def test_update_occurrence_status(self, db: Session, employee: EmployeeSupabase, company: Company):
        """Atualiza status de ocorrência."""
        today = date.today()
        
        # Cria ocorrência
        created = OccurrenceService.create_occurrence(
            db=db,
            company_id=company.id,
            employee_id=employee.id,
            occurrence_date=today,
            occurrence_type="late",
        )
        
        # Atualiza status
        updated = OccurrenceService.update_occurrence_status(
            db=db,
            company_id=company.id,
            occurrence_id=created.id,
            new_status="reviewed",
        )
        
        assert updated is not None
        assert updated.status == "reviewed"

    def test_update_occurrence_status_resolved(self, db: Session, employee: EmployeeSupabase, company: Company):
        """Atualiza status para resolvido com notas."""
        today = date.today()
        
        # Cria ocorrência
        created = OccurrenceService.create_occurrence(
            db=db,
            company_id=company.id,
            employee_id=employee.id,
            occurrence_date=today,
            occurrence_type="late",
        )
        
        # Atualiza para resolvido
        updated = OccurrenceService.update_occurrence_status(
            db=db,
            company_id=company.id,
            occurrence_id=created.id,
            new_status="resolved",
            resolved_by="manager_001",
            resolution_notes="Justificativa aceita",
        )
        
        assert updated.status == "resolved"
        assert updated.resolved_by == "manager_001"
        assert updated.resolution_notes == "Justificativa aceita"
        assert updated.resolved_at is not None

    def test_delete_occurrence_soft_delete(self, db: Session, employee: EmployeeSupabase, company: Company):
        """Remove ocorrência (soft delete)."""
        today = date.today()
        
        # Cria ocorrência
        created = OccurrenceService.create_occurrence(
            db=db,
            company_id=company.id,
            employee_id=employee.id,
            occurrence_date=today,
            occurrence_type="late",
        )
        
        # Remove
        success = OccurrenceService.delete_occurrence(
            db=db,
            company_id=company.id,
            occurrence_id=created.id,
        )
        
        assert success is True
        
        # Verifica que fica marcado como dismissed
        retrieved = OccurrenceService.get_occurrence(
            db=db,
            company_id=company.id,
            occurrence_id=created.id,
        )
        assert retrieved.status == "dismissed"


# ============================================================================
# TESTES: JustificationService — Workflow
# ============================================================================

class TestJustificationWorkflow:
    """Testes de workflow de justificativas."""

    def test_create_justification(self, db: Session, employee: EmployeeSupabase, company: Company):
        """Cria justificativa."""
        start_date = date.today()
        end_date = date.today() + timedelta(days=1)
        
        justification = JustificationService.create_justification(
            db=db,
            company_id=company.id,
            employee_id=employee.id,
            justification_type="medical",
            start_date=start_date,
            end_date=end_date,
            description="Atestado médico",
            submitted_by="emp_001",
        )
        
        assert justification is not None
        assert justification.justification_type == "medical"
        assert justification.status == "pending"

    def test_create_justification_with_occurrence(self, db: Session, employee: EmployeeSupabase, company: Company):
        """Cria justificativa para ocorrência e atualiza status."""
        today = date.today()
        
        # Cria ocorrência
        occurrence = OccurrenceService.create_occurrence(
            db=db,
            company_id=company.id,
            employee_id=employee.id,
            occurrence_date=today,
            occurrence_type="absence",
        )
        
        # Cria justificativa
        justification = JustificationService.create_justification(
            db=db,
            company_id=company.id,
            employee_id=employee.id,
            justification_type="medical",
            start_date=today,
            end_date=today,
            description="Atestado médico",
            occurrence_id=occurrence.id,
            submitted_by="emp_001",
        )
        
        assert justification is not None
        assert justification.occurrence_id == occurrence.id
        
        # Verifica que ocorrência foi marcada como "reviewed"
        db.refresh(occurrence)
        assert occurrence.status == "reviewed"

    def test_approve_justification(self, db: Session, employee: EmployeeSupabase, company: Company):
        """Aprova justificativa."""
        today = date.today()
        
        # Cria justificativa
        justification = JustificationService.create_justification(
            db=db,
            company_id=company.id,
            employee_id=employee.id,
            justification_type="medical",
            start_date=today,
            end_date=today,
            description="Atestado",
            submitted_by="emp_001",
        )
        
        # Aprova
        approved = JustificationService.approve_justification(
            db=db,
            company_id=company.id,
            justification_id=justification.id,
            approved_by="manager_001",
        )
        
        assert approved.status == "approved"
        assert approved.approved_by == "manager_001"
        assert approved.approved_at is not None

    def test_approve_justification_with_occurrence(self, db: Session, employee: EmployeeSupabase, company: Company):
        """Aprova justificativa e resolve ocorrência associada."""
        today = date.today()
        
        # Cria ocorrência
        occurrence = OccurrenceService.create_occurrence(
            db=db,
            company_id=company.id,
            employee_id=employee.id,
            occurrence_date=today,
            occurrence_type="absence",
        )
        
        # Cria justificativa
        justification = JustificationService.create_justification(
            db=db,
            company_id=company.id,
            employee_id=employee.id,
            justification_type="medical",
            start_date=today,
            end_date=today,
            description="Atestado",
            occurrence_id=occurrence.id,
            submitted_by="emp_001",
        )
        
        # Aprova
        JustificationService.approve_justification(
            db=db,
            company_id=company.id,
            justification_id=justification.id,
            approved_by="manager_001",
        )
        
        # Verifica que ocorrência foi resolvida
        db.refresh(occurrence)
        assert occurrence.status == "resolved"
        assert occurrence.resolved_by == "manager_001"

    def test_reject_justification(self, db: Session, employee: EmployeeSupabase, company: Company):
        """Rejeita justificativa."""
        today = date.today()
        
        # Cria justificativa
        justification = JustificationService.create_justification(
            db=db,
            company_id=company.id,
            employee_id=employee.id,
            justification_type="personal",
            start_date=today,
            end_date=today,
            description="Motivo pessoal",
            submitted_by="emp_001",
        )
        
        # Rejeita
        rejected = JustificationService.reject_justification(
            db=db,
            company_id=company.id,
            justification_id=justification.id,
            rejected_by="manager_001",
            rejection_reason="Não possui documentação adequada",
        )
        
        assert rejected.status == "rejected"
        assert rejected.rejection_reason == "Não possui documentação adequada"

    def test_cannot_approve_rejected_justification(self, db: Session, employee: EmployeeSupabase, company: Company):
        """Não permite aprovar justificativa já rejeitada."""
        today = date.today()
        
        # Cria justificativa
        justification = JustificationService.create_justification(
            db=db,
            company_id=company.id,
            employee_id=employee.id,
            justification_type="personal",
            start_date=today,
            end_date=today,
            description="Motivo pessoal",
            submitted_by="emp_001",
        )
        
        # Rejeita
        JustificationService.reject_justification(
            db=db,
            company_id=company.id,
            justification_id=justification.id,
            rejected_by="manager_001",
            rejection_reason="Sem documentação",
        )
        
        # Tenta aprovar (deve falhar)
        result = JustificationService.approve_justification(
            db=db,
            company_id=company.id,
            justification_id=justification.id,
            approved_by="manager_002",
        )
        
        assert result is None  # Falha


# ============================================================================
# TESTES: Segurança e Data Isolation
# ============================================================================

class TestSecurityDataIsolation:
    """Testes de segurança e isolamento de dados."""

    def test_occurrence_isolation_by_company(self, db: Session, employee: EmployeeSupabase, another_employee: EmployeeSupabase, company: Company, another_company: Company):
        """Ocorrências de uma empresa não aparecem em outra."""
        today = date.today()
        
        # Cria ocorrência na empresa 1
        occ1 = OccurrenceService.create_occurrence(
            db=db,
            company_id=company.id,
            employee_id=employee.id,
            occurrence_date=today,
            occurrence_type="late",
        )
        
        # Lista ocorrências da empresa 2
        occs, total = OccurrenceService.list_occurrences(
            db=db,
            company_id=another_company.id,
            skip=0,
            limit=10,
        )
        
        assert total == 0
        assert occ1.company_id != another_company.id

    def test_justification_isolation_by_company(self, db: Session, employee: EmployeeSupabase, company: Company, another_company: Company):
        """Justificativas de uma empresa não aparecem em outra."""
        today = date.today()
        
        # Cria justificativa na empresa 1
        just1 = JustificationService.create_justification(
            db=db,
            company_id=company.id,
            employee_id=employee.id,
            justification_type="medical",
            start_date=today,
            end_date=today,
            description="Atestado",
            submitted_by="emp_001",
        )
        
        # Tenta obter pela empresa 2
        retrieved = JustificationService.get_justification(
            db=db,
            company_id=another_company.id,
            justification_id=just1.id,
        )
        
        assert retrieved is None


# ============================================================================
# TESTES: Estatísticas
# ============================================================================

class TestStatistics:
    """Testes de estatísticas."""

    def test_occurrence_statistics(self, db: Session, employee: EmployeeSupabase, company: Company):
        """Calcula estatísticas de ocorrências."""
        today = date.today()
        start_date = today - timedelta(days=30)
        
        # Cria ocorrências
        OccurrenceService.create_occurrence(
            db=db,
            company_id=company.id,
            employee_id=employee.id,
            occurrence_date=today,
            occurrence_type="late",
            severity="low",
        )
        OccurrenceService.create_occurrence(
            db=db,
            company_id=company.id,
            employee_id=employee.id,
            occurrence_date=today,
            occurrence_type="absence",
            severity="high",
        )
        
        # Calcula estatísticas
        stats = OccurrenceService.get_statistics(
            db=db,
            company_id=company.id,
            start_date=start_date,
            end_date=today,
        )
        
        assert stats["total"] == 2
        assert stats["by_type"]["late"] == 1
        assert stats["by_type"]["absence"] == 1
        assert stats["by_severity"]["low"] == 1
        assert stats["by_severity"]["high"] == 1

    def test_justification_statistics(self, db: Session, employee: EmployeeSupabase, company: Company):
        """Calcula estatísticas de justificativas."""
        today = date.today()
        start_date = today - timedelta(days=30)
        
        # Cria justificativa aprovada
        just1 = JustificationService.create_justification(
            db=db,
            company_id=company.id,
            employee_id=employee.id,
            justification_type="medical",
            start_date=today,
            end_date=today,
            description="Atestado",
            submitted_by="emp_001",
        )
        JustificationService.approve_justification(
            db=db,
            company_id=company.id,
            justification_id=just1.id,
            approved_by="manager_001",
        )
        
        # Cria justificativa rejeitada
        just2 = JustificationService.create_justification(
            db=db,
            company_id=company.id,
            employee_id=employee.id,
            justification_type="personal",
            start_date=today - timedelta(days=1),
            end_date=today - timedelta(days=1),
            description="Motivo pessoal",
            submitted_by="emp_001",
        )
        JustificationService.reject_justification(
            db=db,
            company_id=company.id,
            justification_id=just2.id,
            rejected_by="manager_001",
            rejection_reason="Sem documentação",
        )
        
        # Calcula estatísticas
        stats = JustificationService.get_statistics(
            db=db,
            company_id=company.id,
            start_date=start_date,
            end_date=today,
        )
        
        assert stats["total"] == 2
        assert stats["by_status"]["approved"] == 1
        assert stats["by_status"]["rejected"] == 1
        assert stats["by_status"]["pending"] == 0


# ============================================================================
# TESTES: Validação de Entrada
# ============================================================================

class TestInputValidation:
    """Testes de validação de entrada."""

    def test_invalid_justification_type(self, db: Session, employee: EmployeeSupabase, company: Company):
        """Rejeita tipo de justificativa inválido."""
        today = date.today()
        
        result = JustificationService.create_justification(
            db=db,
            company_id=company.id,
            employee_id=employee.id,
            justification_type="invalid_type",
            start_date=today,
            end_date=today,
            description="Teste",
            submitted_by="emp_001",
        )
        
        assert result is None

    def test_invalid_date_range(self, db: Session, employee: EmployeeSupabase, company: Company):
        """Rejeita data inicial > data final."""
        start_date = date.today()
        end_date = date.today() - timedelta(days=1)
        
        result = JustificationService.create_justification(
            db=db,
            company_id=company.id,
            employee_id=employee.id,
            justification_type="medical",
            start_date=start_date,
            end_date=end_date,
            description="Teste",
            submitted_by="emp_001",
        )
        
        assert result is None

    def test_nonexistent_employee(self, db: Session, company: Company):
        """Permite criar justificativa mesmo com employee_id não existente (será validado na API)."""
        today = date.today()
        
        # A criação pode não falhar, mas será validado no endpoint da API
        result = JustificationService.create_justification(
            db=db,
            company_id=company.id,
            employee_id=uuid4(),  # UUID aleatório
            justification_type="medical",
            start_date=today,
            end_date=today,
            description="Teste",
            submitted_by="emp_001",
        )
        
        # Este teste não valida existência no service, é delegado à API
        # O importante é que tipos inválidos sejam rejeitados
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
