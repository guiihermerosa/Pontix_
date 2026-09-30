"""
Schemas Pydantic para configurações do sistema e do dispositivo.
"""
from typing import Optional, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Configurações da aplicação (armazenadas no SQLite)
# ---------------------------------------------------------------------------
class AppSettingsRead(BaseModel):
    device_host: str
    device_port: str
    device_timeout: str
    sync_interval: str
    sync_auto_enabled: str
    sync_employees: str
    sync_attendance: str
    log_level: str
    log_retention_days: str
    app_name: str
    # Senha nunca é retornada ao frontend
    device_password_set: bool = False   # apenas indica se está preenchida


class AppSettingsUpdate(BaseModel):
    device_host: Optional[str] = None
    device_port: Optional[str] = None
    device_password: Optional[str] = None   # só enviado se o usuário quiser alterar
    device_timeout: Optional[str] = None
    sync_interval: Optional[str] = None
    sync_auto_enabled: Optional[str] = None
    sync_employees: Optional[str] = None
    sync_attendance: Optional[str] = None
    log_level: Optional[str] = None
    log_retention_days: Optional[str] = None
    app_name: Optional[str] = None
    # Identidade da empresa
    company_name: Optional[str] = None
    company_cnpj: Optional[str] = None
    company_address: Optional[str] = None
    company_logo_b64: Optional[str] = None  # PNG/JPEG em base64 (data-URL ou raw)


# ---------------------------------------------------------------------------
# Configurações do dispositivo — espelham os payloads do ALPHA-1111
# ---------------------------------------------------------------------------

class LocalSettingsDevice(BaseModel):
    """Espelho de /getLocalSettingParameter — /setLocalSettingParameter."""
    time_zone: Optional[int] = None
    brightness: Optional[int] = None
    volume: Optional[int] = None
    device_lang: Optional[int] = None
    magazine_creensaver: Optional[int] = None
    return_home_enable: Optional[int] = None
    auto_screen_off: Optional[int] = None
    auto_screen_saver_off: Optional[int] = None
    auto_screen_off_timeout: Optional[int] = None
    auto_screen_saver_timeout: Optional[int] = None
    reboot_interval: Optional[int] = None
    reboot_time: Optional[str] = None
    human_induction: Optional[int] = None
    ip_display: Optional[int] = None
    company_name: Optional[str] = None
    input_set: Optional[int] = None


class AdvancedSettingsDevice(BaseModel):
    """Espelho de /getAdvancedSettingParameter — /setAdvancedSettingParameter."""
    admin_number: Optional[int] = None
    forbid_face: Optional[int] = None
    verification_mode: Optional[int] = None
    validate_login: Optional[int] = None
    developer_mode: Optional[int] = None
    usbset: Optional[int] = None
    tack_icon: Optional[int] = None


class IdentifySettingsDevice(BaseModel):
    """Espelho de /getIdentifySettingParameter — /setIdentifySettingParameter."""
    live_testing: Optional[int] = None
    live_threshold: Optional[int] = None
    identification_interval: Optional[int] = None
    identification_distance: Optional[int] = None
    identification_level: Optional[int] = None
    infrared_image: Optional[int] = None
    lighting_settings: Optional[int] = None
    auto_light_time: Optional[int] = None
    play_name: Optional[int] = None
    play_greetings: Optional[int] = None
    show_image: Optional[int] = None
    show_name: Optional[int] = None
    stranger_voice: Optional[int] = None
    show_id: Optional[int] = None
    stranger_verification: Optional[int] = None
    attendance_mode: Optional[int] = None
    continuous_recognition: Optional[int] = None


class AccessControlSettingsDevice(BaseModel):
    """Espelho de /getAccessControlSettingParameter — /setAccessControlSettingParameter."""
    auth_success_open_door: Optional[int] = None
    strangers_open_door: Optional[int] = None
    io_type: Optional[int] = None
    wigan_mode: Optional[int] = None
    wigan_format: Optional[int] = None
    wigan_output: Optional[int] = None
    door_opening_delay: Optional[int] = None
    door_magnetic_alarm: Optional[int] = None
    door_magnetic_time: Optional[int] = None
    button_door_switch: Optional[int] = None
    wigan_reverse: Optional[int] = None
    card_format: Optional[int] = None
    card_reverse: Optional[int] = None
    local_doorbell: Optional[int] = None
    out_doorbell: Optional[int] = None
    self_password_open: Optional[int] = None


class ShiftData(BaseModel):
    """Um turno — usado em /getShiftManagement e /setShiftManagement."""
    shift_no: int
    shift_name: str = ""
    shift_t1: str = "00:00"
    shift_t2: str = "00:00"
    shift_t3: str = "00:00"
    shift_t4: str = "00:00"
    shift_t5: str = "00:00"
    shift_t6: str = "00:00"
    shift_across_t: str = "00:00"
    shift_ot_select1: int = 0
    shift_ot_select2: int = 0
    shift_ot_select3: int = 0


class LawRuleDevice(BaseModel):
    """Espelho de /getLawRule — /setLawRule."""
    record_warning: Optional[int] = None
    allow_tardiness: Optional[int] = None
    allow_early: Optional[int] = None
    weekend: Optional[int] = None
    default_shift: Optional[int] = None
    no_sign: Optional[int] = None


class HolidayItem(BaseModel):
    openHolidayNum: int
    openHolidayName: str = ""
    gregorian_calendar: int = 0
    openHolidayStart: str = ""
    openHolidayEnd: str = ""


# ---------------------------------------------------------------------------
# Resposta genérica de status
# ---------------------------------------------------------------------------
class StatusResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None


class ConnectionTestResponse(BaseModel):
    connected: bool
    host: str
    response_time_ms: Optional[float] = None
    error: Optional[str] = None
    device_info: Optional[dict] = None
