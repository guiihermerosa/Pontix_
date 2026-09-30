"""
FacialClient — única classe que conhece os endpoints do ALTEK ALPHA-1111.

IMPORTANTE:
  - Somente este módulo faz chamadas HTTP ao dispositivo.
  - Nenhuma outra parte da aplicação deve importar httpx ou construir
    URLs para o facial diretamente.
  - Rotas não validadas no HAR estão marcadas explicitamente.
"""

import json
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger("facial_client")

# ---------------------------------------------------------------------------
# Exceções específicas
# ---------------------------------------------------------------------------

class FacialOfflineError(Exception):
    """Dispositivo não acessível na rede."""

class FacialTimeoutError(Exception):
    """Requisição excedeu o tempo limite."""

class FacialAuthenticationError(Exception):
    """Senha rejeitada pelo dispositivo."""

class FacialApiError(Exception):
    """Dispositivo retornou um erro de API (ex.: result != 0, code != 200)."""
    def __init__(self, message: str, status_code: int | None = None, body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


# ---------------------------------------------------------------------------
# Cliente principal
# ---------------------------------------------------------------------------

class FacialClient:
    """
    Centraliza toda comunicação HTTP com o ALTEK ALPHA-1111.

    Uso:
        client = FacialClient(host="192.168.0.24", password="...", timeout=10)
        data   = client.get_local_settings()
    """

    def __init__(self, host: str, password: str, port: int = 80, timeout: float = 10.0):
        self.host = host
        self.port = port
        self._password = password   # nunca exposto em logs ou respostas
        self.timeout = timeout
        self._base_url = f"http://{host}:{port}"

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _post(self, endpoint: str, payload: dict) -> dict:
        """
        Executa POST no dispositivo.
        Injeta automaticamente a senha e trata todos os erros de rede.

        Retorna o JSON decodificado ou levanta uma exceção específica.
        """
        url = f"{self._base_url}{endpoint}"

        # Garante que a senha esteja no payload raiz
        payload = dict(payload)
        payload["password"] = self._password

        # Sanitiza payload para log — remove senha e dados biométricos
        safe_payload = {
            k: "<REDACTED>" if k in ("password", "featureFile", "fingerFile",
                                      "palm1File", "palm2File", "pic_large")
            else v
            for k, v in payload.items()
        }

        start = time.monotonic()
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload)
            duration_ms = (time.monotonic() - start) * 1000

            logger.debug(
                "POST %s → HTTP %s (%.0f ms) | req=%s",
                endpoint, resp.status_code, duration_ms,
                json.dumps(safe_payload, ensure_ascii=False)[:300],
            )

            if resp.status_code == 401:
                raise FacialAuthenticationError(
                    f"Senha rejeitada pelo dispositivo em {endpoint}"
                )
            if resp.status_code == 404:
                raise FacialApiError(
                    f"Rota não encontrada: {endpoint}",
                    status_code=404,
                )
            if resp.status_code >= 500:
                raise FacialApiError(
                    f"Erro interno do dispositivo em {endpoint} (HTTP {resp.status_code})",
                    status_code=resp.status_code,
                    body=resp.text[:500],
                )

            # Alguns endpoints retornam corpo vazio "{}" como sucesso
            if not resp.text.strip():
                return {}

            try:
                body = resp.json()
            except Exception:
                # Fallback: tenta parsear manualmente se Content-Type não for JSON
                # (o ALTEK devolve text/plain com corpo JSON em alguns endpoints)
                import json as _json
                try:
                    body = _json.loads(resp.text)
                except Exception:
                    body = resp.text

            # Sanitiza valores binários/inválidos em campos de texto
            # (alguns campos como border_color podem conter bytes não-UTF-8)
            if isinstance(body, dict):
                body = _sanitize_response(body)

            return body

        except httpx.ConnectError as exc:
            raise FacialOfflineError(
                f"Não foi possível conectar ao facial em {self._base_url}: {exc}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise FacialTimeoutError(
                f"Timeout ao chamar {endpoint} (limite: {self.timeout}s)"
            ) from exc
        except (FacialOfflineError, FacialTimeoutError,
                FacialAuthenticationError, FacialApiError):
            raise
        except Exception as exc:
            raise FacialApiError(f"Erro inesperado em {endpoint}: {exc}") from exc

    def _post_nested(self, endpoint: str, data: dict) -> dict:
        """
        Variante para endpoints que esperam {"data": {...}, "password": "..."}.
        """
        return self._post(endpoint, {"data": data})

    # ------------------------------------------------------------------
    # Autenticação / Status
    # ------------------------------------------------------------------

    def get_device_auth(self) -> dict:
        """POST /getDevAuth — valida conexão e retorna permissões."""
        return self._post("/getDevAuth", {})

    # ------------------------------------------------------------------
    # Configurações locais
    # ------------------------------------------------------------------

    def get_local_settings(self) -> dict:
        """POST /getLocalSettingParameter"""
        return self._post("/getLocalSettingParameter", {"set": 0})

    def set_local_settings(self, data: dict) -> dict:
        """POST /setLocalSettingParameter"""
        payload = dict(data)
        payload["set"] = 1
        return self._post_nested("/setLocalSettingParameter", payload)

    # ------------------------------------------------------------------
    # Configurações avançadas
    # ------------------------------------------------------------------

    def get_advanced_settings(self) -> dict:
        """POST /getAdvancedSettingParameter"""
        return self._post("/getAdvancedSettingParameter", {"set": 0})

    def set_advanced_settings(self, data: dict) -> dict:
        """POST /setAdvancedSettingParameter"""
        payload = dict(data)
        payload["set"] = 1
        return self._post_nested("/setAdvancedSettingParameter", payload)

    # ------------------------------------------------------------------
    # USB
    # ------------------------------------------------------------------

    def get_usb_switch(self) -> dict:
        """POST /getUSBswitch"""
        return self._post("/getUSBswitch", {"set": 0})

    def set_usb_switch(self, usbset: int) -> dict:
        """POST /USBswitch"""
        return self._post("/USBswitch", {"data": {"usbset": usbset, "set": 1}})

    # ------------------------------------------------------------------
    # Configurações de identificação facial
    # ------------------------------------------------------------------

    def get_identify_settings(self) -> dict:
        """POST /getIdentifySettingParameter"""
        return self._post_nested("/getIdentifySettingParameter", {"set": 0})

    def set_identify_settings(self, data: dict) -> dict:
        """POST /setIdentifySettingParameter"""
        payload = dict(data)
        payload["set"] = 1
        return self._post_nested("/setIdentifySettingParameter", payload)

    # ------------------------------------------------------------------
    # Controle de acesso
    # ------------------------------------------------------------------

    def get_access_control_settings(self) -> dict:
        """POST /getAccessControlSettingParameter"""
        return self._post("/getAccessControlSettingParameter", {"set": 0})

    def set_access_control_settings(self, data: dict) -> dict:
        """POST /setAccessControlSettingParameter"""
        payload = dict(data)
        payload["set"] = 1
        return self._post_nested("/setAccessControlSettingParameter", payload)

    # ------------------------------------------------------------------
    # Períodos diários de acesso
    # ------------------------------------------------------------------

    def get_open_day(self) -> dict:
        """POST /getOpenDay"""
        return self._post_nested("/getOpenDay", {"set": 0})

    def set_open_day(self, data: list) -> dict:
        """POST /setOpenDay"""
        return self._post("/setOpenDay", {"data": data})

    # ------------------------------------------------------------------
    # Períodos semanais de acesso
    # ------------------------------------------------------------------

    def get_open_week(self) -> dict:
        """POST /getOpenWeek"""
        return self._post_nested("/getOpenWeek", {"set": 0})

    def set_open_week(self, data: list) -> dict:
        """POST /setOpenWeek"""
        return self._post("/setOpenWeek", {"data": data})

    # ------------------------------------------------------------------
    # Regras de acesso por dia da semana
    # ------------------------------------------------------------------

    def get_open_go(self) -> dict:
        """POST /getOpenGo"""
        return self._post_nested("/getOpenGo", {"set": 0})

    def set_open_go(self, data: dict) -> dict:
        """POST /setOpenGo"""
        return self._post("/setOpenGo", {"data": data})

    def get_open_door(self) -> dict:
        """POST /getOpenDoor"""
        return self._post_nested("/getOpenDoor", {"set": 0})

    # ------------------------------------------------------------------
    # Regras trabalhistas
    # ------------------------------------------------------------------

    def get_law_rules(self) -> dict:
        """POST /getLawRule"""
        return self._post_nested("/getLawRule", {"set": 0})

    def set_law_rules(self, data: dict) -> dict:
        """POST /setLawRule"""
        payload = dict(data)
        payload["set"] = 1
        return self._post_nested("/setLawRule", payload)

    # ------------------------------------------------------------------
    # Feriados
    # ------------------------------------------------------------------

    def get_holidays(self) -> dict:
        """POST /getOpenHoliday"""
        return self._post_nested("/getOpenHoliday", {"set": 0})

    def set_holidays(self, data: list) -> dict:
        """POST /setOpenHoliday"""
        return self._post("/setOpenHoliday", {"data": data})

    # ------------------------------------------------------------------
    # Jornadas/turnos
    # ------------------------------------------------------------------

    def get_shift_management(self) -> dict:
        """
        POST /getShiftManagement
        Retorna todos os turnos cadastrados no device.
        """
        return self._post("/getShiftManagement", {})

    def set_shift_management(self, data: dict) -> dict:
        """
        POST /setShiftManagement — envia um turno por vez.

        Campos validados no HAR (obrigatórios):
          shift_no        int   — número do turno (1..N)
          shift_name      str   — nome livre, ex: "shift1"
          shift_t1..t6    str   — horários HH:MM (entrada/saída de até 3 períodos)
          shift_across_t  str   — horário de cruzamento de virada de dia HH:MM
          shift_ot_select1..3 int — seleção de hora extra (0/1) por período

        Exemplo:
          {
            "shift_no": 1, "shift_name": "Manhã",
            "shift_t1": "08:00", "shift_t2": "12:00",
            "shift_t3": "13:00", "shift_t4": "17:00",
            "shift_t5": "00:00", "shift_t6": "00:00",
            "shift_across_t": "00:00",
            "shift_ot_select1": 0, "shift_ot_select2": 0, "shift_ot_select3": 0
          }
        """
        # Garante campos obrigatórios com defaults seguros
        shift = _build_shift_payload(data)
        return self._post("/setShiftManagement", {"data": shift})

    # ------------------------------------------------------------------
    # Registros de passagem (log bruto do device)
    # ------------------------------------------------------------------

    def get_work_note_list(
        self,
        record_type: int = 2,
        start_time: str | None = None,
        end_time: str | None = None,
        userid: str | None = None,
    ) -> dict:
        """
        POST /getWorkNoteList — log bruto de passagens do device.

        Parâmetros validados no HAR:
          type        int   — 1 = desconhecidos/estranhos, 2 = funcionários cadastrados
          start_time  str   — "YYYY/MM/DD" (opcional; omitir = todos disponíveis)
          end_time    str   — "YYYY/MM/DD" (opcional)
          userid      str   — filtra por funcionário (opcional)

        Resposta:
          { "data": [{
              "userid": "1", "name": "...", "ispass": 1,
              "passway": "0", "cardnum": "", "score": 89,
              "checkin_time": "2026-09-23 21:41:41", "temp": ""
            }],
            "page_sum": 1, "total": 2, "index": 0, "count": 16, "code": 200
          }

        Campos de passway:
          0=facial  1=cartão  2=QR  3=senha  4=ID  5=health  6=botão/remoto
          7=digital  8=palma  10=face+cartão  11=face+senha  12=face+cartão/senha
          13=face+digital  14=face+palma  ... (ver HAR employee_note.js)
        """
        payload: dict = {"type": record_type}
        if start_time:
            payload["start_time"] = start_time
            payload["startTime"] = start_time
        if end_time:
            payload["end_time"] = end_time
            payload["endTime"] = end_time
        if userid is not None:
            payload["userid"] = userid
        return self._post("/getWorkNoteList", payload)

    def export_checkin_record(
        self,
        record_type: int = 2,
        start_time: str | None = None,
        end_time: str | None = None,
        start_index: int = 1,
        end_index: int = 100,
        current_call: int = 1,
        total_call: int = 1,
    ) -> dict:
        """
        POST /exportCheckinRecord — exporta lote paginado de registros do device.

        Usado para exportação em massa: divide o total em chamadas de até 100
        registros (startIndex/endIndex), repetindo com currentCall/totalCall.

        Parâmetros validados no HAR:
          type        int  — 1=desconhecidos, 2=funcionários
          start_time  str  — "YYYY/MM/DD"
          end_time    str  — "YYYY/MM/DD"
          startIndex  int  — início da página (1-based)
          endIndex    int  — fim da página
          currentCall int  — número desta chamada
          totalCall   int  — total de chamadas previsto

        Resposta:
          { "code": 200, "data": [{
              "userid": "1", "name": "...", "ispass": 1,
              "passway": "0", "score": 48, "cardnum": "",
              "checkin_time": "2026-09-23 21:41:41", "temp": ""
            }]
          }
        """
        payload: dict = {
            "type": record_type,
            "startIndex": start_index,
            "endIndex": end_index,
            "currentCall": current_call,
            "totalCall": total_call,
        }
        if start_time:
            payload["start_time"] = start_time
            payload["startTime"] = start_time
        if end_time:
            payload["end_time"] = end_time
            payload["endTime"] = end_time
        return self._post("/exportCheckinRecord", payload)

    # ------------------------------------------------------------------
    # Upload de nota
    # ------------------------------------------------------------------

    def get_note(self) -> dict:
        """POST /getNote"""
        return self._post("/getNote", {})

    def get_ip_settings(self) -> dict:
        """POST /IpSetting (set=0 = consultar)."""
        return self._post("/IpSetting", {
            "is_dhcp": 0, "ip": "0.0.0.0", "mask": "0.0.0.0",
            "gate": "0.0.0.0", "dns": "0.0.0.0", "set": 0,
        })

    def get_wifi_state(self) -> dict:
        """POST /getWifiState"""
        return self._post("/getWifiState", {})

    def get_wifi_networks(self) -> list:
        """POST /getScanWifiResults"""
        result = self._post("/getScanWifiResults", {
            "sort": "ssid", "sortOrder": "desc",
        })
        if isinstance(result, list):
            return result
        return result.get("data", [])

    def get_server_setting(self) -> dict:
        """POST /serverSetting (set=0 = consultar)."""
        return self._post("/serverSetting", {"set": 0})

    def get_mqtt_settings(self) -> dict:
        """
        POST /getMqttSet
        ATENÇÃO: a resposta contém credenciais MQTT — nunca repassar
        diretamente ao frontend sem sanitizar mqtt_password e mqtt_username.
        """
        return self._post_nested("/getMqttSet", {"set": 0})

    # ------------------------------------------------------------------
    # Funcionários
    # ------------------------------------------------------------------

    def get_employee_list(self, index: int = 1, count: int = 100) -> dict:
        """POST /getEmployeeList — paginado."""
        return self._post("/getEmployeeList", {"index": index, "count": count})

    def insert_employee(self, data: dict) -> dict:
        """POST /insertEmployee."""
        # Garante que campos sensíveis sejam strings vazias, nunca None
        clean = _clean_employee_payload(data)
        return self._post("/insertEmployee", {"data": clean})

    def update_employee(self, data: dict) -> dict:
        """POST /updateEmployee."""
        clean = _clean_employee_payload(data)
        return self._post("/updateEmployee", {"data": clean})

    # ------------------------------------------------------------------
    # Presença
    # ------------------------------------------------------------------

    def get_attendance(
        self,
        start_date: str,
        end_date: str,
        start_index: int = 1,
        end_index: int = 999999,
    ) -> dict:
        """
        POST /getAttendTable
        Datas no formato YYYY/MM/DD conforme observado no HAR.
        """
        return self._post("/getAttendTable", {
            "type": 0,
            "start_time":  start_date,
            "end_time":    end_date,
            "startTime":   start_date,
            "endTime":     end_date,
            "startIndex":  start_index,
            "endIndex":    end_index,
            "currentCall": 1,
            "totalCall":   1,
        })

    def get_attendance_summary(
        self,
        start_date: str,
        end_date: str,
    ) -> dict:
        """POST /getSummaryTable"""
        return self._post("/getSummaryTable", {
            "type": 0,
            "start_time":  start_date,
            "end_time":    end_date,
            "startTime":   start_date,
            "endTime":     end_date,
            "startIndex":  1,
            "endIndex":    999999,
            "currentCall": 1,
            "totalCall":   1,
        })

    # ------------------------------------------------------------------
    # Rotas referenciadas no JS do device — NÃO VALIDADAS no HAR
    # ------------------------------------------------------------------

    def delete_employee(self, userids: list[str]) -> dict:
        """
        POST /deleteEmployee — VALIDADO NO HAR.

        Payload validado:
          {"password": "...", "userid": ["1"]}
        Resposta:
          {"code": 200, "message": "OK"}

        Aceita lista de userids para exclusão em lote.
        """
        return self._post("/deleteEmployee", {"userid": userids})

    def delete_all_employees(self) -> dict:
        """POST /deleteAllemployee — ROTA NÃO VALIDADA."""
        raise NotImplementedError(
            "delete_all_employees: rota /deleteAllemployee não foi validada no HAR."
        )

    def get_success_data(self) -> dict:
        """POST /getSuccessData — ROTA NÃO VALIDADA."""
        raise NotImplementedError(
            "get_success_data: rota /getSuccessData não foi validada no HAR."
        )

    def get_device_log(self) -> dict:
        """POST /getDeviceLog — ROTA NÃO VALIDADA."""
        raise NotImplementedError(
            "get_device_log: rota /getDeviceLog não foi validada no HAR."
        )

    # Rotas que retornaram 404 no HAR — não implementar
    # /getDeviceTimeAccessGroups  → HTTP 404
    # /getDeviceTimeKeepOpenGroups → HTTP 404


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sanitize_response(data: Any) -> Any:
    """
    Recursivamente sanitiza um dict/list retornado pelo device.

    Problemas conhecidos no ALPHA-1111:
      - border_color: contém bytes binários (cor em formato nativo)
        → convertido para string hexadecimal legível
      - Strings com caracteres não-UTF-8 → substituídos por '?'
    """
    if isinstance(data, dict):
        return {k: _sanitize_response(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_sanitize_response(v) for v in data]
    if isinstance(data, bytes):
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.hex()
    if isinstance(data, str):
        # Tenta re-encodar para garantir UTF-8 válido; substitui caracteres inválidos
        try:
            data.encode("utf-8")
            return data
        except (UnicodeEncodeError, UnicodeDecodeError):
            return data.encode("utf-8", errors="replace").decode("utf-8")
    return data


def _clean_employee_payload(data: dict) -> dict:
    """Garante que campos biométricos sejam string vazia quando não fornecidos."""
    bio_fields = ("featureFile", "fingerFile", "palm1File", "palm2File", "pic_large")
    result = dict(data)
    for field in bio_fields:
        if result.get(field) is None:
            result[field] = ""
    return result


def _build_shift_payload(data: dict) -> dict:
    """
    Garante que todos os campos obrigatórios de um turno estejam presentes
    e com tipos corretos, conforme validado no HAR (/setShiftManagement).

    Campos obrigatórios e defaults:
      shift_no        int   — sem default; levanta ValueError se ausente
      shift_name      str   — default: "shift{shift_no}"
      shift_t1..t6    str   — default: "00:00"
      shift_across_t  str   — default: "00:00"
      shift_ot_select1..3 int — default: 0
    """
    result = dict(data)

    if "shift_no" not in result:
        raise ValueError("shift_no é obrigatório para setShiftManagement")

    shift_no = int(result["shift_no"])
    result["shift_no"] = shift_no
    result.setdefault("shift_name", f"shift{shift_no}")

    for i in range(1, 7):
        key = f"shift_t{i}"
        val = result.get(key, "00:00") or "00:00"
        # Normaliza para HH:MM
        result[key] = str(val).strip()

    result.setdefault("shift_across_t", "00:00")
    result["shift_across_t"] = result["shift_across_t"] or "00:00"

    for i in range(1, 4):
        key = f"shift_ot_select{i}"
        result[key] = int(result.get(key, 0))

    return result
    bio_fields = ("featureFile", "fingerFile", "palm1File", "palm2File", "pic_large")
    result = dict(data)
    for field in bio_fields:
        if result.get(field) is None:
            result[field] = ""
    return result
