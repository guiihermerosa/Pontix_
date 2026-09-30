# ALTEK ALPHA-1111 — Documentação da API

**Fonte:** Análise do arquivo HAR `192.168.0.24_Facial_pontix.har`  
**Protocolo:** HTTP/1.1  
**Método:** Todos os endpoints utilizam `POST`  
**Content-Type:** `application/json` (exceto upload multipart)  
**Autenticação:** Campo `password` no corpo JSON de cada requisição

---

## Regras de integração

- **Nunca hardcode** o campo `password`. Leia sempre do banco de configurações.
- Endpoints com `set=0` no payload são consultas. `set=1` são gravações.
- Muitos endpoints aceitam a estrutura `{"data": {...}, "password": "..."}`.
- Resposta de sucesso padrão: `{"result": 0, "message": "..."}` ou `{"code": 200}`.
- O sistema deve tolerar o device offline sem travar.

---

## Status de validação

| Símbolo | Significado |
|---------|-------------|
| ✅ | Validado — resposta capturada no HAR |
| ⚠️ | Descoberto no JS do device, sem resposta no HAR |
| ❌ | Retornou HTTP 404 no HAR |

---

## Endpoints validados

### Autenticação / Status

#### `POST /getDevAuth` ✅

Valida a conexão e retorna o perfil de permissões do dispositivo.  
Usado como health check pelo `SyncService`.

**Requisição:**
```json
{"password": "<REDACTED>"}
```

**Resposta:**
```json
{
  "data": {"autho_type": "0000000000011001"},
  "message": "Get autho success",
  "result": 0
}
```

---

### Configurações locais

#### `POST /getLocalSettingParameter` ✅

**Requisição:**
```json
{"set": 0, "password": "<REDACTED>"}
```

**Resposta (campos relevantes):**
```json
{
  "data": {
    "time_zone": 26,
    "brightness": 5,
    "volume": 90,
    "device_lang": 6,
    "return_home_enable": 1,
    "auto_screen_off": 1,
    "auto_screen_off_timeout": 300,
    "reboot_interval": 2,
    "reboot_time": "03:00",
    "human_induction": 1,
    "ip_display": 1,
    "company_name": ""
  },
  "message": "Get params success",
  "result": 0
}
```

#### `POST /setLocalSettingParameter` ✅

**Requisição:**
```json
{
  "data": {
    "volume": 90,
    "return_home_enable": 1,
    "auto_screen_off": 1,
    "auto_screen_off_timeout": 300,
    "reboot_interval": 2,
    "reboot_time": "03:00",
    "ip_display": 1,
    "company_name": "",
    "set": 1,
    "password": "<REDACTED>"
  },
  "password": "<REDACTED>"
}
```

**Resposta:** `{"message": "Set param success", "result": 0}`

---

### Configurações avançadas

#### `POST /getAdvancedSettingParameter` ✅

**Requisição:** `{"set": 0, "password": "<REDACTED>"}`

**Resposta:**
```json
{
  "data": {
    "admin_number": 10,
    "forbid_face": 1,
    "verification_mode": 0,
    "validate_login": 0,
    "developer_mode": 0,
    "usbset": 0,
    "tack_icon": 1
  },
  "message": "Get params success",
  "result": 0
}
```

#### `POST /setAdvancedSettingParameter` ✅

**Requisição:** `{"data": {..., "set": 1, "password": "<REDACTED>"}, "password": "<REDACTED>"}`

**Resposta:** `{"message": "Set param success", "result": 0}`

---

### USB

#### `POST /getUSBswitch` ✅

**Requisição:** `{"set": 0, "password": "<REDACTED>"}`

**Resposta:** `{"data": {"usbset": 0}, "message": "Get params success", "result": 0}`

#### `POST /USBswitch` ✅

**Requisição:** `{"data": {"usbset": 0, "set": 1, "password": "<REDACTED>"}, "password": "<REDACTED>"}`

**Resposta:** `{}`

---

### Identificação facial

#### `POST /getIdentifySettingParameter` ✅

**Requisição:** `{"data": {"set": 0, "password": "<REDACTED>"}, "password": "<REDACTED>"}`

**Resposta (campos relevantes):**
```json
{
  "data": {
    "live_testing": 1,
    "live_threshold": 54,
    "identification_interval": 1,
    "identification_distance": 150,
    "identification_level": 1,
    "infrared_image": 0,
    "lighting_settings": 2,
    "auto_light_time": 10,
    "play_name": 1,
    "play_greetings": 1,
    "show_image": 0,
    "show_name": 1,
    "stranger_voice": 1,
    "stranger_verification": 1,
    "attendance_mode": 1,
    "continuous_recognition": 0
  }
}
```

#### `POST /setIdentifySettingParameter` ✅

**Requisição:** `{"data": {..., "set": 1, "password": "<REDACTED>"}, "password": "<REDACTED>"}`

---

### Controle de acesso

#### `POST /getAccessControlSettingParameter` ✅

**Resposta (campos relevantes):**
```json
{
  "data": {
    "auth_success_open_door": 1,
    "strangers_open_door": 0,
    "door_opening_delay": 5,
    "button_door_switch": 1,
    "self_password_open": 1,
    "local_doorbell": 1,
    "out_doorbell": 1
  }
}
```

#### `POST /setAccessControlSettingParameter` ✅

---

### Períodos de acesso

#### `POST /getOpenDay` ✅ / `POST /setOpenDay` ✅

Até 8 períodos diários, cada um com até 5 faixas de horário.

```json
{
  "data": [
    {
      "openDayNum": 1,
      "openDayName": "天时段1",
      "startTime1": "00:00", "endTime1": "00:00",
      "startTime2": "00:00", "endTime2": "00:00",
      "startTime3": "00:00", "endTime3": "00:00",
      "startTime4": "00:00", "endTime4": "00:00",
      "startTime5": "00:00", "endTime5": "00:00"
    }
  ]
}
```

#### `POST /getOpenWeek` ✅ / `POST /setOpenWeek` ✅

Até 8 períodos semanais. Campos `week1`..`week7` referenciam IDs de períodos diários.

#### `POST /getOpenGo` ✅ / `POST /setOpenGo` ✅

Regras de acesso por dia da semana. Valores: `"否"` (negar) / `"是"` (permitir).

#### `POST /getOpenDoor` ✅

Consulta configuração de abertura de porta (somente leitura observada no HAR).

#### `POST /getOpenHoliday` ✅ / `POST /setOpenHoliday` ✅

Até 30 feriados. Campo `gregorian_calendar`: `0` = lunar, `1` = gregoriano.

---

### Regras trabalhistas

#### `POST /getLawRule` ✅

```json
{
  "data": {
    "record_warning": 1000,
    "allow_tardiness": 0,
    "allow_early": 0,
    "weekend": 1,
    "default_shift": 0,
    "no_sign": 0
  }
}
```

#### `POST /setLawRule` ✅

---

### Jornadas / Turnos

#### `POST /getShiftManagement` ✅

Retorna até 8 turnos. Campos de tempo em `HH:MM`.

```json
{
  "data": [
    {
      "shift_no": 1,
      "shift_name": "shift1",
      "shift_t1": "08:30", "shift_t2": "12:00",
      "shift_t3": "13:00", "shift_t4": "17:30",
      "shift_t5": "19:00", "shift_t6": "22:00",
      "shift_across_t": "00:00",
      "shift_start_min": 12600,
      "shift_end_min": 16200
    }
  ]
}
```

#### `POST /setShiftManagement` ✅

Envia **um turno por vez** no campo `data`.

---

### Funcionários

#### `POST /getEmployeeList` ✅

Paginado com `index` e `count`.

**Requisição:**
```json
{"index": 1, "count": 100, "password": "<REDACTED>"}
```

**Resposta:**
```json
{
  "data": [
    {
      "userid": "1",
      "name": "",
      "access_card_number": "",
      "role": 0,
      "department": 0,
      "schedule": 1,
      "face_norm": 308.69,
      "fingerprintid": 0,
      "palmleftid": 0,
      "palmrightid": 0,
      "pass_times": -1
    }
  ],
  "total": 1,
  "code": 200
}
```

> `face_norm > 0` indica que existe template facial cadastrado.

#### `POST /insertEmployee` ✅

```json
{
  "data": {
    "userid": "45",
    "name": "Nome",
    "access_card_number": "",
    "userpassword": "",
    "department": 0,
    "schedule": 0,
    "role": 0,
    "person_period": 0,
    "pass_times": -1,
    "pass_date": "0",
    "pass_time": "[null,null,null]",
    "pic_large": "",
    "featureFile": "",
    "fingerFile": "",
    "palm1File": "",
    "palm2File": ""
  },
  "password": "<REDACTED>"
}
```

**Resposta de sucesso:** `{"code": 200, "message": "OK"}`  
**Resposta de erro:** `{"code": -1, "message": "At least one of photo, card number, or password is required"}`

> O device exige pelo menos um de: foto (`pic_large`), cartão (`access_card_number`) ou senha (`userpassword`).

#### `POST /updateEmployee` ✅

Mesmo payload do `insertEmployee`, acrescido de `new_userid`.

---

### Upload multipart

#### `POST /html/employee_add.html` ✅ (HTTP 0 no HAR — status não capturado)

Interface original do equipamento. Aceita `multipart/form-data` com os mesmos campos de `insertEmployee` mais arquivos biométricos.

> O sistema utiliza `/insertEmployee` (JSON) com `pic_large` em base64 quando há foto.

---

### Presença

#### `POST /getAttendTable` ✅

Retorna registros de presença por período.

**Requisição:**
```json
{
  "type": 0,
  "start_time": "2026/09/01",
  "end_time":   "2026/09/25",
  "startTime":  "2026/09/01",
  "endTime":    "2026/09/25",
  "startIndex": 1,
  "endIndex":   999999,
  "currentCall": 1,
  "totalCall":   1,
  "password": "<REDACTED>"
}
```

**Resposta (estrutura por funcionário):**
```json
{
  "data": [
    {
      "userid": "1",
      "employeeName": "",
      "department": "dept1",
      "shift": "shift1",
      "dateRange": {"start": "2026-09-01", "end": "2026-09-25"},
      "attendan": [
        {
          "attDate": "09-22",
          "attWeek": "Ter",
          "shift_t1": "08:30",
          "shift_t2": "12:00",
          "shift_t3": "13:00",
          "shift_t4": "17:30",
          "shift_t5": "",
          "shift_t6": "",
          "attStandard": "11.0",
          "attActual": "8.5",
          "attOver": "0.0",
          "attLate": "0",
          "attEarly": "0"
        }
      ]
    }
  ]
}
```

> Campos `shift_t1`..`shift_t6` com valor `HH:MM` indicam batidas registradas.  
> Interpretação padrão: índice par = Entrada, ímpar = Saída.  
> **Não existe push/webhook** — o sistema usa polling.

#### `POST /getSummaryTable` ✅

Mesmo payload do `getAttendTable`. Retorna resumo consolidado por funcionário.

---

### Rede

#### `POST /IpSetting` ✅

```json
{"is_dhcp": 0, "ip": "0.0.0.0", "mask": "0.0.0.0", "gate": "0.0.0.0", "dns": "0.0.0.0", "set": 0, "password": "<REDACTED>"}
```

**Resposta:** `{"ip": "192.168.0.146", "mask": "255.255.255.0", "gate": "192.168.0.1", "is_dhcp": 1}`

#### `POST /getWifiState` ✅

**Resposta:** `{"enable_wifi": 1, "connected_ssid": "Infoseg", "enable_hotspot": 0}`

#### `POST /getScanWifiResults` ✅

**Requisição:** `{"sort": "ssid", "sortOrder": "desc", "password": "<REDACTED>"}`

**Resposta:** `[{"ssid": "Infoseg", "strength": -46, "encryption": "WPA2", "channel": 1}]`

> Retorna array direto, sem envelope `data`.

#### `POST /serverSetting` ✅

**Resposta:** `{"cloudserver_address": "...", "cloudserver_pollingtime": 10, "protocol_type": 1, ...}`

#### `POST /getMqttSet` ✅

> ⚠️ A resposta contém `mqtt_password` e `mqtt_username`. Esses campos **nunca** devem ser repassados ao frontend.

---

### Nota / Upload

#### `POST /getNote` ✅

**Resposta:** `{"data": {"note": 1}, "message": "Get record upload note success", "result": 0}`

---

## Endpoints com erro 404

| Endpoint | Status |
|----------|--------|
| `POST /getDeviceTimeAccessGroups` | ❌ HTTP 404 |
| `POST /getDeviceTimeKeepOpenGroups` | ❌ HTTP 404 |

Não implementar. Podem estar ausentes no firmware instalado.

---

## Rotas descobertas no JS — não validadas

| Endpoint | Função presumida |
|----------|-----------------|
| `POST /deleteEmployee` ⚠️ | Excluir funcionário (`{password, userid:[...]}`) |
| `POST /deleteAllemployee` ⚠️ | Excluir todos |
| `POST /getSuccessData` ⚠️ | Resultado de importação |
| `POST /getDeviceLog` ⚠️ | Logo em base64 |
| `POST /passwordEdit` ⚠️ | Alterar senha |
| `POST /setLangCustom` ⚠️ | Idioma customizado |
| `POST /screensaverRecover` ⚠️ | Reset screensaver |
| `POST /setSyncLang` ⚠️ | Sincronizar idioma |
| `POST /setDeviceLogo` ⚠️ | Definir logo |
| `POST /setLogo` ⚠️ | Definir logo (variante) |

No código do sistema, todas essas rotas levantam `NotImplementedError` no `FacialClient` até serem validadas em ambiente real.

---

## Comportamento esperado das respostas

| Campo | Significado |
|-------|-------------|
| `result: 0` | Operação bem-sucedida |
| `result: -1` | Erro genérico |
| `code: 200` | Sucesso (endpoints de funcionários) |
| `code: -1` | Erro (endpoints de funcionários) |
| Corpo `{}` | Sucesso implícito (ex: USBswitch) |

---

## Limitações conhecidas

1. **Não há push/webhook** — o sistema opera exclusivamente por polling via `getAttendTable`.
2. **Biometria não fabricada** — `featureFile`, `fingerFile`, `palm1File`, `palm2File` só são enviados se fornecidos pelo usuário.
3. **Encoding** — respostas com nomes em chinês vêm codificados como UTF-8; o sistema trata como string opaca.
4. **Rotas 404** — duas rotas retornaram 404 no HAR e não foram implementadas.
