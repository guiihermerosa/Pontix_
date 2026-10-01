"""
Rotas de sincronização com o sistema local.

Endpoints:
- POST /api/sync/employees - Recebe funcionários do sistema local
- POST /api/sync/time-records - Recebe registros de ponto
- POST /api/sync/occurrences - Recebe ocorrências
- GET /api/sync/status - Status da última sincronização
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.database.models import (
    Company, Employee, TimeRecord, Occurrence, AuditLog
)
from app.schemas import SuccessResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sync", tags=["sync"])


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

async def get_or_create_company(
    db: AsyncSession,
    local_id: str,
    company_data: dict
) -> Company:
    """
    Obtém ou cria uma empresa baseada em dados do sistema local.
    """
    # Busca por local_id
    result = await db.execute(
        select(Company).where(Company.id == UUID(local_id) if len(local_id) == 36 else None)
    )
    company = result.scalar_one_or_none()
    
    if not company:
        # Cria nova empresa
        company = Company(
            id=uuid4(),
            name=company_data.get("name", "Empresa Importada"),
            cnpj=company_data.get("cnpj", "00.000.000/0000-00"),
            owner_id=company_data.get("owner_id", "local-owner"),
            email=company_data.get("email"),
            phone=company_data.get("phone"),
            is_active=True,
        )
        db.add(company)
        await db.flush()  # Garante que tem ID
    
    return company


# ---------------------------------------------------------------------------
# Sincronização de Funcionários
# ---------------------------------------------------------------------------

@router.post("/employees", response_model=SuccessResponse)
async def sync_employees(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Recebe lista de funcionários do sistema local e sincroniza.
    
    Body:
        {
            "company_id": "uuid",
            "company_data": {...},
            "employees": [
                {
                    "local_id": "id",
                    "user_id": "user_id",
                    "full_name": "Name",
                    "email": "email@example.com",
                    "cpf": "000.000.000-00",
                    "department": "TI",
                    "role": "Developer",
                    ...
                }
            ]
        }
    """
    try:
        company_id = payload.get("company_id")
        company_data = payload.get("company_data", {})
        employees_data = payload.get("employees", [])
        
        # Obtém ou cria a empresa
        company = await get_or_create_company(db, company_id, company_data)
        
        synced_count = 0
        errors = []
        
        for emp_data in employees_data:
            try:
                local_id = emp_data.get("local_id")
                user_id = emp_data.get("user_id")
                
                # Busca funcionário existente
                result = await db.execute(
                    select(Employee).where(
                        and_(
                            Employee.company_id == company.id,
                            Employee.user_id == user_id
                        )
                    )
                )
                employee = result.scalar_one_or_none()
                
                if employee:
                    # Atualiza funcionário existente
                    employee.full_name = emp_data.get("full_name", employee.full_name)
                    employee.email = emp_data.get("email", employee.email)
                    employee.cpf = emp_data.get("cpf", employee.cpf)
                    employee.department = emp_data.get("department", employee.department)
                    employee.role = emp_data.get("role", employee.role)
                    employee.registration_number = emp_data.get("registration_number", employee.registration_number)
                    employee.sync_status = "synced"
                    employee.last_synced_at = datetime.now(timezone.utc)
                else:
                    # Cria novo funcionário
                    employee = Employee(
                        id=uuid4(),
                        company_id=company.id,
                        local_id=local_id,
                        user_id=user_id,
                        full_name=emp_data.get("full_name", "Sem nome"),
                        email=emp_data.get("email"),
                        cpf=emp_data.get("cpf"),
                        department=emp_data.get("department"),
                        role=emp_data.get("role"),
                        registration_number=emp_data.get("registration_number"),
                        sync_status="synced",
                        last_synced_at=datetime.now(timezone.utc),
                    )
                    db.add(employee)
                
                synced_count += 1
            except Exception as e:
                logger.error(f"Erro ao sincronizar funcionário {emp_data.get('user_id')}: {e}")
                errors.append(f"Erro em {emp_data.get('user_id')}: {str(e)}")
        
        await db.commit()
        
        message = f"{synced_count} funcionários sincronizados"
        if errors:
            message += f" ({len(errors)} erros)"
        
        return SuccessResponse(
            message=message,
            data={
                "synced": synced_count,
                "errors": errors,
                "company_id": str(company.id),
            }
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Erro ao sincronizar funcionários: {e}")
        raise HTTPException(status_code=500, detail="Erro ao sincronizar funcionários")


# ---------------------------------------------------------------------------
# Sincronização de Registros de Ponto
# ---------------------------------------------------------------------------

@router.post("/time-records", response_model=SuccessResponse)
async def sync_time_records(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Recebe registros de ponto do sistema local e sincroniza.
    
    Body:
        {
            "company_id": "uuid",
            "time_records": [
                {
                    "local_id": "id",
                    "user_id": "user_id",
                    "employee_name": "Name",
                    "record_date": "2024-01-15",
                    "record_time": "08:30:00",
                    "record_type": "entry",
                    ...
                }
            ]
        }
    """
    try:
        company_id = payload.get("company_id")
        records_data = payload.get("time_records", [])
        
        try:
            company_uuid = UUID(company_id)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Company ID inválido")
        
        synced_count = 0
        errors = []
        
        for record_data in records_data:
            try:
                local_id = record_data.get("local_id")
                user_id = record_data.get("user_id")
                
                # Busca funcionário
                result = await db.execute(
                    select(Employee).where(
                        and_(
                            Employee.company_id == company_uuid,
                            Employee.user_id == user_id
                        )
                    )
                )
                employee = result.scalar_one_or_none()
                
                if not employee:
                    logger.warning(f"Funcionário {user_id} não encontrado")
                    errors.append(f"Funcionário {user_id} não encontrado")
                    continue
                
                # Cria deduplication key
                dedup_key = f"{employee.id}_{record_data.get('record_date')}_{record_data.get('record_time')}_{record_data.get('record_type')}"
                
                # Verifica se já existe
                result = await db.execute(
                    select(TimeRecord).where(TimeRecord.deduplication_key == dedup_key)
                )
                if result.scalar_one_or_none():
                    logger.info(f"Registro duplicado ignorado: {dedup_key}")
                    continue
                
                # Cria novo registro
                record = TimeRecord(
                    id=uuid4(),
                    company_id=company_uuid,
                    employee_id=employee.id,
                    local_record_id=local_id,
                    user_id=user_id,
                    employee_name=record_data.get("employee_name"),
                    record_date=record_data.get("record_date"),
                    record_time=record_data.get("record_time"),
                    record_type=record_data.get("record_type"),
                    source=record_data.get("source", "device"),
                    sync_status="synced",
                    deduplication_key=dedup_key,
                )
                
                db.add(record)
                synced_count += 1
            except Exception as e:
                logger.error(f"Erro ao sincronizar registro: {e}")
                errors.append(f"Erro em registro: {str(e)}")
        
        await db.commit()
        
        message = f"{synced_count} registros de ponto sincronizados"
        if errors:
            message += f" ({len(errors)} erros)"
        
        return SuccessResponse(
            message=message,
            data={
                "synced": synced_count,
                "errors": errors,
                "company_id": company_id,
            }
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Erro ao sincronizar registros de ponto: {e}")
        raise HTTPException(status_code=500, detail="Erro ao sincronizar registros")


# ---------------------------------------------------------------------------
# Sincronização de Ocorrências
# ---------------------------------------------------------------------------

@router.post("/occurrences", response_model=SuccessResponse)
async def sync_occurrences(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Recebe ocorrências do sistema local e sincroniza.
    """
    try:
        company_id = payload.get("company_id")
        occurrences_data = payload.get("occurrences", [])
        
        try:
            company_uuid = UUID(company_id)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Company ID inválido")
        
        synced_count = 0
        errors = []
        
        for occ_data in occurrences_data:
            try:
                user_id = occ_data.get("user_id")
                
                # Busca funcionário
                result = await db.execute(
                    select(Employee).where(
                        and_(
                            Employee.company_id == company_uuid,
                            Employee.user_id == user_id
                        )
                    )
                )
                employee = result.scalar_one_or_none()
                
                if not employee:
                    errors.append(f"Funcionário {user_id} não encontrado")
                    continue
                
                # Cria ocorrência
                occurrence = Occurrence(
                    id=uuid4(),
                    company_id=company_uuid,
                    employee_id=employee.id,
                    occurrence_date=occ_data.get("occurrence_date"),
                    occurrence_type=occ_data.get("occurrence_type", "other"),
                    severity=occ_data.get("severity", "medium"),
                    description=occ_data.get("description"),
                    status="pending",
                )
                
                db.add(occurrence)
                synced_count += 1
            except Exception as e:
                logger.error(f"Erro ao sincronizar ocorrência: {e}")
                errors.append(f"Erro em ocorrência: {str(e)}")
        
        await db.commit()
        
        message = f"{synced_count} ocorrências sincronizadas"
        if errors:
            message += f" ({len(errors)} erros)"
        
        return SuccessResponse(
            message=message,
            data={
                "synced": synced_count,
                "errors": errors,
                "company_id": company_id,
            }
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Erro ao sincronizar ocorrências: {e}")
        raise HTTPException(status_code=500, detail="Erro ao sincronizar ocorrências")


# ---------------------------------------------------------------------------
# Status de Sincronização
# ---------------------------------------------------------------------------

@router.get("/status/{company_id}")
async def get_sync_status(
    company_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna status da última sincronização de uma empresa.
    """
    try:
        company_uuid = UUID(company_id)
        
        # Obtém última sincronização
        result = await db.execute(
            select(TimeRecord.updated_at).where(
                TimeRecord.company_id == company_uuid
            ).order_by(TimeRecord.updated_at.desc()).limit(1)
        )
        last_sync = result.scalar()
        
        # Conta registros pendentes
        pending_result = await db.execute(
            select(func.count(TimeRecord.id)).where(
                and_(
                    TimeRecord.company_id == company_uuid,
                    TimeRecord.sync_status == "pending"
                )
            )
        )
        pending_records = pending_result.scalar() or 0
        
        return {
            "company_id": company_id,
            "last_sync": last_sync.isoformat() if last_sync else None,
            "pending_records": pending_records,
            "status": "synced" if pending_records == 0 else "pending",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Company ID inválido")
    except Exception as e:
        logger.error(f"Erro ao buscar status de sincronização: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar status")
