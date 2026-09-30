"""
Rotas de Configurações — sistema local e configurações do device.
"""
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import Setting
from app.schemas.settings import AppSettingsUpdate, StatusResponse
from app.services.sync_service import _build_client, test_connection

logger = logging.getLogger("routes_settings")
router = APIRouter()
from app.templates_config import templates


# ---------------------------------------------------------------------------
# Página HTML
# ---------------------------------------------------------------------------

@router.get("/configuracoes")
async def settings_page(request: Request, db: Session = Depends(get_db)):
    app_settings = _load_app_settings(db)
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "settings": app_settings,
        "active_page": "settings",
    })


# ---------------------------------------------------------------------------
# Configurações da aplicação
# ---------------------------------------------------------------------------

@router.get("/api/settings")
async def get_settings(db: Session = Depends(get_db)):
    return _load_app_settings(db)


@router.put("/api/settings")
async def update_settings(data: AppSettingsUpdate, db: Session = Depends(get_db)):
    update_map = data.model_dump(exclude_unset=True, exclude_none=True)

    for key, value in update_map.items():
        if key == "device_password" and not value:
            continue  # não apaga senha com string vazia
        row = db.query(Setting).filter(Setting.key == key).first()
        if row:
            row.value = str(value)
        else:
            db.add(Setting(key=key, value=str(value)))

    db.commit()
    return {"success": True, "message": "Configurações salvas"}


@router.get("/api/settings/company-logo")
async def get_company_logo(db: Session = Depends(get_db)):
    """Retorna o logo da empresa em base64 (separado para não pesar no GET /api/settings)."""
    row = db.query(Setting).filter(Setting.key == "company_logo_b64").first()
    logo = row.value if row and row.value else ""
    return {"company_logo_b64": logo}


@router.delete("/api/settings/company-logo")
async def delete_company_logo(db: Session = Depends(get_db)):
    """Remove o logo da empresa."""
    row = db.query(Setting).filter(Setting.key == "company_logo_b64").first()
    if row:
        row.value = ""
        db.commit()
    return {"success": True}


# ---------------------------------------------------------------------------
# Teste de conexão
# ---------------------------------------------------------------------------

@router.post("/api/settings/test-connection")
async def test_conn(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Testa conexão com o device.
    Aceita body JSON opcional com {host, port, password, timeout} para testar
    antes de salvar — se omitido, usa as configs do banco.
    """
    from app.services.facial_client import (
        FacialApiError, FacialAuthenticationError,
        FacialOfflineError, FacialTimeoutError,
    )
    import time

    body = {}
    try:
        body = await request.json()
    except Exception:
        pass

    # Prioriza body; cai para banco se não vier no body
    def _get_setting_local(key: str, default: str = "") -> str:
        row = db.query(Setting).filter(Setting.key == key).first()
        return row.value if row and row.value else default

    host     = body.get("device_host")     or _get_setting_local("device_host")
    port     = int(body.get("device_port") or _get_setting_local("device_port", "80"))
    password = body.get("device_password") or _get_setting_local("device_password")
    timeout  = float(body.get("device_timeout") or _get_setting_local("device_timeout", "10"))

    if not host:
        return {"connected": False, "error": "IP do dispositivo não configurado."}
    if not password:
        return {"connected": False, "error": "Senha do dispositivo não configurada. Salve as configurações primeiro."}

    from app.services.facial_client import FacialClient
    from app.services.sync_service import _update_device_status, _log_comm
    client = FacialClient(host=host, password=password, port=port, timeout=timeout)

    start = time.monotonic()
    try:
        result = client.get_device_auth()
        elapsed = (time.monotonic() - start) * 1000
        _update_device_status(db, online=True, response_time=elapsed)
        _log_comm(db, endpoint="/getDevAuth", status_code=200, duration_ms=elapsed, success=True)
        return {
            "connected": True,
            "host": host,
            "response_time_ms": round(elapsed, 1),
            "device_info": result,
        }
    except FacialOfflineError as exc:
        elapsed = (time.monotonic() - start) * 1000
        _update_device_status(db, online=False, error=str(exc))
        return {"connected": False, "host": host, "error": str(exc)}
    except FacialTimeoutError as exc:
        elapsed = (time.monotonic() - start) * 1000
        _update_device_status(db, online=False, error=str(exc))
        return {"connected": False, "host": host, "error": f"Timeout ({timeout}s): verifique o IP e se o device está acessível."}
    except FacialAuthenticationError as exc:
        elapsed = (time.monotonic() - start) * 1000
        _update_device_status(db, online=False, error=str(exc))
        return {"connected": False, "host": host, "error": "Senha incorreta."}
    except FacialApiError as exc:
        elapsed = (time.monotonic() - start) * 1000
        _update_device_status(db, online=False, error=str(exc))
        return {"connected": False, "host": host, "error": str(exc)}
    except Exception as exc:
        elapsed = (time.monotonic() - start) * 1000
        _update_device_status(db, online=False, error=str(exc))
        return {"connected": False, "host": host, "error": f"Erro inesperado: {exc}"}


# ---------------------------------------------------------------------------
# Configurações do dispositivo — leitura e escrita via FacialClient
# ---------------------------------------------------------------------------

@router.get("/api/device/local-settings")
async def get_local_settings(db: Session = Depends(get_db)):
    client = _get_client_or_error(db)
    return _safe_call(client.get_local_settings)


@router.put("/api/device/local-settings")
async def set_local_settings(data: dict, db: Session = Depends(get_db)):
    client = _get_client_or_error(db)
    return _safe_call(client.set_local_settings, data)


@router.get("/api/device/advanced-settings")
async def get_advanced_settings(db: Session = Depends(get_db)):
    client = _get_client_or_error(db)
    return _safe_call(client.get_advanced_settings)


@router.put("/api/device/advanced-settings")
async def set_advanced_settings(data: dict, db: Session = Depends(get_db)):
    client = _get_client_or_error(db)
    return _safe_call(client.set_advanced_settings, data)


@router.get("/api/device/identify-settings")
async def get_identify_settings(db: Session = Depends(get_db)):
    client = _get_client_or_error(db)
    return _safe_call(client.get_identify_settings)


@router.put("/api/device/identify-settings")
async def set_identify_settings(data: dict, db: Session = Depends(get_db)):
    client = _get_client_or_error(db)
    return _safe_call(client.set_identify_settings, data)


@router.get("/api/device/access-control")
async def get_access_control(db: Session = Depends(get_db)):
    client = _get_client_or_error(db)
    return _safe_call(client.get_access_control_settings)


@router.put("/api/device/access-control")
async def set_access_control(data: dict, db: Session = Depends(get_db)):
    client = _get_client_or_error(db)
    return _safe_call(client.set_access_control_settings, data)


@router.get("/api/device/shifts")
async def get_shifts(db: Session = Depends(get_db)):
    """
    Retorna todos os turnos cadastrados no device.
    Resposta bruta de /getShiftManagement.
    """
    client = _get_client_or_error(db)
    return _safe_call(client.get_shift_management)


@router.put("/api/device/shifts/{shift_no}")
async def set_shift_by_no(shift_no: int, data: dict, db: Session = Depends(get_db)):
    """
    Salva (cria ou atualiza) um turno específico no device.

    shift_no: número do turno (1..N) — extraído da URL.

    Body JSON com os campos do turno (shift_no no body é sobrescrito pelo path):
      {
        "shift_name":      "Manhã",
        "shift_t1":        "08:00",
        "shift_t2":        "12:00",
        "shift_t3":        "13:00",
        "shift_t4":        "17:00",
        "shift_t5":        "00:00",
        "shift_t6":        "00:00",
        "shift_across_t":  "00:00",
        "shift_ot_select1": 0,
        "shift_ot_select2": 0,
        "shift_ot_select3": 0
      }

    Campos omitidos recebem defaults seguros (horários "00:00", OT = 0).
    """
    from app.services.facial_client import FacialApiError as _FacialApiError
    client = _get_client_or_error(db)
    # shift_no da URL sempre prevalece
    payload = dict(data)
    payload["shift_no"] = shift_no
    return _safe_call(client.set_shift_management, payload)


@router.put("/api/device/shifts")
async def set_shift(data: dict, db: Session = Depends(get_db)):
    """
    Salva um turno pelo shift_no presente no body (mantido por compatibilidade).
    Prefira PUT /api/device/shifts/{shift_no}.
    """
    client = _get_client_or_error(db)
    return _safe_call(client.set_shift_management, data)


@router.get("/api/device/law-rules")
async def get_law_rules(db: Session = Depends(get_db)):
    client = _get_client_or_error(db)
    return _safe_call(client.get_law_rules)


@router.put("/api/device/law-rules")
async def set_law_rules(data: dict, db: Session = Depends(get_db)):
    client = _get_client_or_error(db)
    return _safe_call(client.set_law_rules, data)


@router.get("/api/device/holidays")
async def get_holidays(db: Session = Depends(get_db)):
    client = _get_client_or_error(db)
    return _safe_call(client.get_holidays)


@router.put("/api/device/holidays")
async def set_holidays(data: list, db: Session = Depends(get_db)):
    client = _get_client_or_error(db)
    return _safe_call(client.set_holidays, data)


@router.get("/api/device/open-day")
async def get_open_day(db: Session = Depends(get_db)):
    client = _get_client_or_error(db)
    return _safe_call(client.get_open_day)


@router.put("/api/device/open-day")
async def set_open_day(data: list, db: Session = Depends(get_db)):
    client = _get_client_or_error(db)
    return _safe_call(client.set_open_day, data)


@router.get("/api/device/open-week")
async def get_open_week(db: Session = Depends(get_db)):
    client = _get_client_or_error(db)
    return _safe_call(client.get_open_week)


@router.put("/api/device/open-week")
async def set_open_week(data: list, db: Session = Depends(get_db)):
    client = _get_client_or_error(db)
    return _safe_call(client.set_open_week, data)


@router.get("/api/device/open-go")
async def get_open_go(db: Session = Depends(get_db)):
    client = _get_client_or_error(db)
    return _safe_call(client.get_open_go)


@router.put("/api/device/open-go")
async def set_open_go(data: dict, db: Session = Depends(get_db)):
    client = _get_client_or_error(db)
    return _safe_call(client.set_open_go, data)


@router.get("/api/device/open-door")
async def get_open_door(db: Session = Depends(get_db)):
    client = _get_client_or_error(db)
    return _safe_call(client.get_open_door)


# ---------------------------------------------------------------------------
# Rede
# ---------------------------------------------------------------------------

@router.get("/api/device/network/ip")
async def get_ip(db: Session = Depends(get_db)):
    client = _get_client_or_error(db)
    return _safe_call(client.get_ip_settings)


@router.get("/api/device/network/wifi")
async def get_wifi(db: Session = Depends(get_db)):
    client = _get_client_or_error(db)
    return _safe_call(client.get_wifi_state)


@router.get("/api/device/network/wifi-scan")
async def scan_wifi(db: Session = Depends(get_db)):
    client = _get_client_or_error(db)
    return _safe_call(client.get_wifi_networks)


@router.get("/api/device/server-settings")
async def get_server_settings(db: Session = Depends(get_db)):
    client = _get_client_or_error(db)
    return _safe_call(client.get_server_setting)


@router.get("/api/device/mqtt")
async def get_mqtt(db: Session = Depends(get_db)):
    """
    Retorna configurações MQTT com credenciais mascaradas.
    mqtt_password e mqtt_username nunca são expostos ao frontend.
    """
    client = _get_client_or_error(db)
    result = _safe_call(client.get_mqtt_settings)
    if isinstance(result, dict):
        result.pop("mqtt_password", None)
        result.pop("mqtt_username", None)
    return result


@router.get("/api/device/usb")
async def get_usb(db: Session = Depends(get_db)):
    client = _get_client_or_error(db)
    return _safe_call(client.get_usb_switch)


@router.put("/api/device/usb")
async def set_usb(usbset: int, db: Session = Depends(get_db)):
    client = _get_client_or_error(db)
    return _safe_call(client.set_usb_switch, usbset)


@router.get("/api/device/note")
async def get_note(db: Session = Depends(get_db)):
    client = _get_client_or_error(db)
    return _safe_call(client.get_note)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_app_settings(db: Session) -> dict:
    rows = db.query(Setting).all()
    settings = {r.key: r.value for r in rows}
    # Nunca retorna a senha — apenas indica se está definida
    password_set = bool(settings.get("device_password", ""))
    settings.pop("device_password", None)
    settings["device_password_set"] = password_set
    # Logo é grande demais para o GET geral — use /api/settings/company-logo
    logo_set = bool(settings.get("company_logo_b64", ""))
    settings.pop("company_logo_b64", None)
    settings["company_logo_set"] = logo_set
    return settings


def _get_client_or_error(db: Session):
    client = _build_client(db)
    if not client:
        raise HTTPException(
            status_code=503,
            detail="Device não configurado. Configure o IP e senha nas Configurações.",
        )
    return client


def _safe_call(fn, *args) -> Any:
    """Chama método do FacialClient e converte exceções em HTTP errors legíveis."""
    from app.services.facial_client import (
        FacialApiError,
        FacialAuthenticationError,
        FacialOfflineError,
        FacialTimeoutError,
    )
    try:
        return fn(*args)
    except FacialOfflineError as exc:
        raise HTTPException(status_code=503, detail=f"Device offline: {exc}")
    except FacialTimeoutError as exc:
        raise HTTPException(status_code=504, detail=f"Timeout: {exc}")
    except FacialAuthenticationError as exc:
        raise HTTPException(status_code=401, detail=f"Autenticação falhou: {exc}")
    except FacialApiError as exc:
        raise HTTPException(status_code=502, detail=f"Erro do device: {exc}")
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
