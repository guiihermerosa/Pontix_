# -*- coding: utf-8 -*-

import time
import threading
from datetime import date, datetime, timedelta
import hashlib
import os
import shutil
import subprocess
import tempfile

import config_store
import ponto_core
import requests

try:
    from win10toast import ToastNotifier
    _TOAST_DISPONIVEL = True
except ImportError:
    _TOAST_DISPONIVEL = False

_TOAST = ToastNotifier() if _TOAST_DISPONIVEL else None

_MONITOR_INICIADO = False
_MONITOR_LOCK = threading.Lock()
_PASTA_ICONE_TEMP = os.path.join(tempfile.gettempdir(), "ponto_web_notificacoes")


def notificar(titulo, mensagem, icon_path=None):
    """Notificacoes do Windows foram canceladas. Mantemos apenas o log em console."""
    print("[NOTIFICACAO] {} - {}".format(titulo, mensagem))


def _eh_reconhecimento_facial(log):
    try:
        return int(log.get("mode", 0) or 0) == 8
    except (TypeError, ValueError):
        return str(log.get("mode", "")).strip() == "8"


def _assinatura_log(log):
    return ponto_core._assinatura_log_bruto(log)


def _converter_horario(log):
    horario_completo = str(log.get("hora") or log.get("time", ""))
    if len(horario_completo) >= 8:
        return horario_completo[-8:]
    return horario_completo


def _descricao_inout(valor):
    try:
        valor_int = int(valor)
    except (TypeError, ValueError):
        return ""
    if valor_int == 1:
        return "Entrada"
    if valor_int == 0:
        return "Saida"
    return ""


def _descricao_evento(item):
    tipo = str(item.get("acao", "") or "").strip()
    if tipo in ("Entrada", "Saida"):
        return tipo
    tipo = _descricao_inout(item.get("inout", ""))
    if tipo:
        return tipo

    try:
        event = int(item.get("event", 0) or 0)
    except (TypeError, ValueError):
        event = None
    if event == 1:
        return "Entrada"
    if event == 2:
        return "Saida"
    return "Registro"


def _montar_mensagem_notificacao(item):
    nome = item.get("name", "") or "Funcionario {}".format(item.get("enrollid", ""))
    horario = _converter_horario(item)
    matricula = str(item.get("enrollid", "") or "").strip()
    departamento = str(item.get("department", "") or "").strip()
    tipo = _descricao_evento(item)
    partes = []
    if horario:
        partes.append(horario)
    if matricula:
        partes.append("Matrícula {}".format(matricula))
    if departamento:
        partes.append(departamento)
    if not partes:
        partes.append("Registro capturado")
    return tipo, nome, "\n".join(partes)


def _url_absoluta(config, caminho):
    caminho = str(caminho or "").strip()
    if not caminho:
        return ""
    if caminho.startswith("http://") or caminho.startswith("https://"):
        return caminho
    if not caminho.startswith("/"):
        caminho = "/" + caminho
    return "http://{}:{}{}".format(config.get("device_ip", ""), config.get("device_port", 80), caminho)


def _garantir_pasta_temp():
    if not os.path.isdir(_PASTA_ICONE_TEMP):
        os.makedirs(_PASTA_ICONE_TEMP)


def _converter_imagem_para_icone(caminho_imagem, caminho_icone):
    comando = u"""
Add-Type -AssemblyName System.Drawing
$src = '{src}'
$dst = '{dst}'
$bmp = [System.Drawing.Bitmap]::FromFile($src)
try {{
    $icon = [System.Drawing.Icon]::FromHandle($bmp.GetHicon())
    try {{
        $fs = New-Object System.IO.FileStream($dst, [System.IO.FileMode]::Create)
        try {{
            $icon.Save($fs)
        }} finally {{
            $fs.Close()
        }}
    }} finally {{
        if ($icon -and $icon.Dispose) {{ $icon.Dispose() }}
    }}
}} finally {{
    $bmp.Dispose()
}}
""".format(src=caminho_imagem.replace("'", "''"), dst=caminho_icone.replace("'", "''"))
    subprocess.check_call([
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        comando,
    ])


def _baixar_icone_do_log(config, item):
    photourl = str(item.get("photourl", "") or "").strip()
    if not photourl:
        return None

    url = _url_absoluta(config, photourl)
    if not url:
        return None

    _garantir_pasta_temp()
    assinatura = hashlib.md5(_assinatura_log(item).encode("utf-8")).hexdigest()
    caminho_img = os.path.join(_PASTA_ICONE_TEMP, assinatura + ".img")
    caminho_ico = os.path.join(_PASTA_ICONE_TEMP, assinatura + ".ico")

    if os.path.isfile(caminho_ico):
        return caminho_ico

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        with open(caminho_img, "wb") as f_img:
            f_img.write(resp.content)
        _converter_imagem_para_icone(caminho_img, caminho_ico)
        return caminho_ico if os.path.isfile(caminho_ico) else None
    except Exception:
        return None


def _carregar_estado_notificacao(config):
    estado = ponto_core.ler_estado_coletor(config)
    vistos = estado.get("notified_signatures", []) or []
    if not isinstance(vistos, list):
        vistos = []
    vistos_limpos = [str(item) for item in vistos if item]
    return estado, vistos_limpos, set(vistos_limpos)


def _salvar_estado_notificacao(config, estado, vistos_lista):
    estado = dict(estado or {})
    estado["notified_signatures"] = list(vistos_lista)[-500:]
    ponto_core.salvar_estado_coletor(config, estado)


def _registrar_lote(config, logs, origem, exibir_notificacao=False, dia=None):
    registros_novos = []
    estado_notificacao, vistos_lista_notificacao, vistos_notificacao = _carregar_estado_notificacao(config)
    alterou_notificacao = False

    def _chave_ordenacao(log):
        item_ordenacao = ponto_core._normalizar_log_bruto(log, origem)
        return (
            str(item_ordenacao.get("data", "")),
            str(item_ordenacao.get("hora", "")),
            str(item_ordenacao.get("enrollid", "")),
            str(item_ordenacao.get("time", "")),
        )

    for log in sorted(logs or [], key=_chave_ordenacao):
        item_base = ponto_core._normalizar_log_bruto(log, origem)
        assinatura = _assinatura_log(item_base)
        if ponto_core.log_local_ja_existe(config, assinatura):
            continue

        acao, estado_tentativo = ponto_core.determinar_acao_marcacao(config, item_base, estado_notificacao)
        item_base["acao"] = acao
        item_base["acao_origem"] = "alternancia"

        try:
            item = ponto_core.registrar_log_local(config, item_base, source=origem)
        except Exception:
            continue
        if not item.get("gravado"):
            continue
        estado_notificacao = estado_tentativo
        registros_novos.append(item)
        if not exibir_notificacao or not _eh_reconhecimento_facial(item):
            continue

        assinatura = _assinatura_log(item)
        if assinatura in vistos_notificacao:
            continue
        vistos_lista_notificacao.append(assinatura)
        vistos_notificacao.add(assinatura)
        alterou_notificacao = True

        enrollid = item.get("enrollid", "")
        horario = _converter_horario(item)
        nome = item.get("name", "") or "Funcionario {}".format(enrollid)

        try:
            info_usuario = ponto_core.get_user_info(config, enrollid) or {}
        except Exception:
            info_usuario = {}

        try:
            turnos = ponto_core.get_shifts(config)
        except Exception:
            turnos = []

        shiftid = info_usuario.get("shiftid", item.get("shiftid", 0))
        turno = info_usuario.get("shift_name", "") or ponto_core._nome_turno(turnos, shiftid)

        notificacao_item = {
            "name": info_usuario.get("name", "") or nome,
            "enrollid": enrollid,
            "department": info_usuario.get("department", "") or item.get("department", ""),
            "acao": item.get("acao", ""),
            "inout": item.get("inout", ""),
            "event": item.get("event", ""),
            "hora": horario,
        }
        tipo, nome_titulo, mensagem = _montar_mensagem_notificacao(notificacao_item)
        icon_path = _baixar_icone_do_log(config, item)
        notificar("{} - {}".format(tipo, nome_titulo), mensagem, icon_path=icon_path)

        try:
            ponto_core.registrar_marcacao_local(config, {
                "data": (dia or date.today()).isoformat(),
                "hora": horario,
                "enrollid": enrollid,
                "name": info_usuario.get("name", "") or nome,
                "department": info_usuario.get("department", ""),
                "shiftid": shiftid,
                "shift_name": turno,
                "source": origem,
                "mode": item.get("mode", ""),
                "acao": item.get("acao", ""),
                "inout": item.get("inout", ""),
                "event": item.get("event", ""),
                "note": item.get("note", ""),
                "photourl": item.get("photourl", ""),
            })
        except Exception:
            pass
    if alterou_notificacao:
        _salvar_estado_notificacao(config, estado_notificacao, vistos_lista_notificacao)
    return registros_novos


def _sincronizar_getlog(config, ultima_data=None):
    hoje = date.today()
    if ultima_data is None:
        dias_retrospectivos = config.get("coleta_retrospectiva_dias", 7)
        try:
            dias_retrospectivos = max(1, int(dias_retrospectivos))
        except (TypeError, ValueError):
            dias_retrospectivos = 7
        inicio = hoje - timedelta(days=dias_retrospectivos)
    else:
        try:
            texto_data = str(ultima_data or "").strip()
            if len(texto_data) >= 10:
                texto_data = texto_data[:10]
            inicio = datetime.strptime(texto_data, "%Y-%m-%d").date()
        except Exception:
            inicio = hoje
    try:
        logs = ponto_core.listar_getlogs(config, inicio=inicio, fim=hoje, limite=5000)
    except ponto_core.DeviceError:
        return None
    except Exception:
        return None

    return _registrar_lote(config, logs, "getlog", exibir_notificacao=False, dia=hoje)


def monitorar_loop():
    """Roda pra sempre em segundo plano enquanto o servidor estiver ligado."""
    while True:
        config = config_store.carregar()

        if not config_store.esta_configurado(config):
            time.sleep(10)
            continue

        intervalo = config.get("intervalo_notificacao_segundos", 60)
        try:
            intervalo = max(15, int(intervalo))
        except (TypeError, ValueError):
            intervalo = 60

        estado = ponto_core.ler_estado_coletor(config)
        ultima_sincronizacao = estado.get("ultima_sincronizacao")
        novos_getlog = _sincronizar_getlog(config, ultima_sincronizacao)
        if novos_getlog is not None:
            estado["status_leitor"] = "online"
            estado["ultima_sincronizacao"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            estado["ultima_coleta_em"] = estado["ultima_sincronizacao"]
            ponto_core.salvar_estado_coletor(config, estado)

        hoje = date.today()
        try:
            logs_atuais = ponto_core.listar_rtlogs(config, limite=200)
        except ponto_core.DeviceError:
            estado = ponto_core.ler_estado_coletor(config)
            estado["status_leitor"] = "offline"
            ponto_core.salvar_estado_coletor(config, estado)
            time.sleep(intervalo)
            continue
        except Exception:
            estado = ponto_core.ler_estado_coletor(config)
            estado["status_leitor"] = "offline"
            ponto_core.salvar_estado_coletor(config, estado)
            time.sleep(intervalo)
            continue

        if logs_atuais:
            _registrar_lote(config, logs_atuais, "rtlog", exibir_notificacao=False, dia=hoje)
            estado = ponto_core.ler_estado_coletor(config)
            estado["status_leitor"] = "online"
            estado["ultima_coleta_em"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            ponto_core.salvar_estado_coletor(config, estado)

        time.sleep(intervalo)


def iniciar_em_segundo_plano():
    global _MONITOR_INICIADO
    with _MONITOR_LOCK:
        if _MONITOR_INICIADO:
            return
        _MONITOR_INICIADO = True
    threading.Thread(target=monitorar_loop, daemon=True).start()
