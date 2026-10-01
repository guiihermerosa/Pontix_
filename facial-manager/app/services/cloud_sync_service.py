"""
Serviço de sincronização com sistema cloud (Supabase/API remota).
Responsável por enviar dados do sistema local para a cloud.
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import requests
from sqlalchemy.orm import Session

from app.database.models import Setting, Employee, AttendanceRecord
from app.database.database import SessionLocal

logger = logging.getLogger("cloud_sync_service")


def get_cloud_sync_config(db: Session) -> Dict[str, Any]:
    """
    Obtém configuração de sincronização cloud do banco de dados.
    
    Returns:
        {
            "enabled": bool,
            "url": str,
            "api_key": str
        }
    """
    def _get_setting(key: str, default: str = "") -> str:
        row = db.query(Setting).filter(Setting.key == key).first()
        return row.value if row and row.value else default
    
    return {
        "enabled": _get_setting("cloud_sync_enabled", "false").lower() == "true",
        "url": _get_setting("cloud_sync_url", "").rstrip("/"),
        "api_key": _get_setting("cloud_sync_api_key", ""),
    }


def sync_employees_to_cloud(db: Session) -> Dict[str, Any]:
    """
    Sincroniza funcionários locais com sistema cloud.
    
    Returns:
        {
            "success": bool,
            "synced_count": int,
            "error": str (se houver)
        }
    """
    config = get_cloud_sync_config(db)
    
    if not config["enabled"]:
        return {
            "success": False,
            "synced_count": 0,
            "error": "Sincronização cloud desativada"
        }
    
    if not config["url"]:
        return {
            "success": False,
            "synced_count": 0,
            "error": "URL do sistema cloud não configurada"
        }
    
    try:
        # Obtém todos os funcionários do sistema local
        employees = db.query(Employee).all()
        
        if not employees:
            logger.info("Nenhum funcionário para sincronizar")
            return {
                "success": True,
                "synced_count": 0,
                "message": "Nenhum funcionário para sincronizar"
            }
        
        # Prepara dados para sincronização
        employees_data = []
        for emp in employees:
            employees_data.append({
                "userid": emp.userid,
                "name": emp.name,
                "department": emp.department,
                "schedule": emp.schedule,
                "role": emp.role,
                "access_card_number": emp.access_card_number,
                "id_number": emp.id_number,
                "has_face": emp.has_face,
                "has_fingerprint": emp.has_fingerprint,
                "has_palm": emp.has_palm,
            })
        
        # Envia para cloud
        headers = {
            "Content-Type": "application/json",
        }
        if config["api_key"]:
            headers["Authorization"] = f"Bearer {config['api_key']}"
        
        response = requests.post(
            f"{config['url']}/api/sync/employees",
            json={"employees": employees_data},
            headers=headers,
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            logger.info(f"✓ Sincronizados {len(employees)} funcionários com cloud")
            return {
                "success": True,
                "synced_count": len(employees),
                "message": f"Sincronizados {len(employees)} funcionários"
            }
        else:
            error_msg = f"Cloud retornou status {response.status_code}"
            logger.error(f"✕ Erro na sincronização de funcionários: {error_msg}")
            return {
                "success": False,
                "synced_count": 0,
                "error": error_msg
            }
    
    except requests.exceptions.ConnectionError as e:
        error_msg = "Não foi possível conectar ao sistema cloud"
        logger.error(f"✕ Erro de conexão: {error_msg}")
        return {
            "success": False,
            "synced_count": 0,
            "error": error_msg
        }
    
    except requests.exceptions.Timeout:
        error_msg = "Timeout ao conectar com sistema cloud"
        logger.error(f"✕ {error_msg}")
        return {
            "success": False,
            "synced_count": 0,
            "error": error_msg
        }
    
    except Exception as e:
        error_msg = f"Erro na sincronização: {str(e)}"
        logger.error(f"✕ {error_msg}")
        return {
            "success": False,
            "synced_count": 0,
            "error": error_msg
        }


def sync_attendance_to_cloud(db: Session, limit: int = 100) -> Dict[str, Any]:
    """
    Sincroniza registros de presença não sincronizados com sistema cloud.
    
    Args:
        limit: Máximo de registros a sincronizar por chamada
    
    Returns:
        {
            "success": bool,
            "synced_count": int,
            "error": str (se houver)
        }
    """
    config = get_cloud_sync_config(db)
    
    if not config["enabled"]:
        return {
            "success": False,
            "synced_count": 0,
            "error": "Sincronização cloud desativada"
        }
    
    if not config["url"]:
        return {
            "success": False,
            "synced_count": 0,
            "error": "URL do sistema cloud não configurada"
        }
    
    try:
        # Obtém registros de presença (implementar lógica de marcação se necessário)
        records = db.query(AttendanceRecord).limit(limit).all()
        
        if not records:
            logger.info("Nenhum registro de presença para sincronizar")
            return {
                "success": True,
                "synced_count": 0,
                "message": "Nenhum registro para sincronizar"
            }
        
        # Prepara dados para sincronização
        records_data = []
        for rec in records:
            records_data.append({
                "userid": rec.userid,
                "employee_name": rec.employee_name,
                "attendance_date": rec.attendance_date,
                "attendance_time": rec.attendance_time,
                "record_type": rec.record_type,
                "source": rec.source,
            })
        
        # Envia para cloud
        headers = {
            "Content-Type": "application/json",
        }
        if config["api_key"]:
            headers["Authorization"] = f"Bearer {config['api_key']}"
        
        response = requests.post(
            f"{config['url']}/api/sync/attendance",
            json={"records": records_data},
            headers=headers,
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            logger.info(f"✓ Sincronizados {len(records)} registros com cloud")
            return {
                "success": True,
                "synced_count": len(records),
                "message": f"Sincronizados {len(records)} registros"
            }
        else:
            error_msg = f"Cloud retornou status {response.status_code}"
            logger.error(f"✕ Erro na sincronização de registros: {error_msg}")
            return {
                "success": False,
                "synced_count": 0,
                "error": error_msg
            }
    
    except requests.exceptions.ConnectionError:
        error_msg = "Não foi possível conectar ao sistema cloud"
        logger.error(f"✕ Erro de conexão: {error_msg}")
        return {
            "success": False,
            "synced_count": 0,
            "error": error_msg
        }
    
    except requests.exceptions.Timeout:
        error_msg = "Timeout ao conectar com sistema cloud"
        logger.error(f"✕ {error_msg}")
        return {
            "success": False,
            "synced_count": 0,
            "error": error_msg
        }
    
    except Exception as e:
        error_msg = f"Erro na sincronização: {str(e)}"
        logger.error(f"✕ {error_msg}")
        return {
            "success": False,
            "synced_count": 0,
            "error": error_msg
        }


def run_full_cloud_sync() -> Dict[str, Any]:
    """
    Executa sincronização completa (funcionários + presença).
    """
    db = SessionLocal()
    try:
        result_employees = sync_employees_to_cloud(db)
        result_attendance = sync_attendance_to_cloud(db)
        
        return {
            "success": result_employees["success"] and result_attendance["success"],
            "employees": result_employees,
            "attendance": result_attendance,
            "timestamp": datetime.now().isoformat()
        }
    finally:
        db.close()
