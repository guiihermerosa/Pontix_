# -*- coding: utf-8 -*-
"""Persistencia local de dados extras dos funcionarios.

O leitor facial continua sendo a fonte da matricula, nome, departamento e turno.
Este modulo guarda os dados que o equipamento nao suporta de forma nativa:
CPF, atestados e anexos administrativos.
"""

import copy
import json
import os
import threading
import uuid
from datetime import datetime

from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "dados")
ATESTADOS_DIR = os.path.join(DATA_DIR, "atestados")
STORE_PATH = os.path.join(DATA_DIR, "funcionarios_extras.json")

_LOCK = threading.Lock()
_EXTENSOES_PERMITIDAS = {".pdf", ".png", ".jpg", ".jpeg", ".doc", ".docx"}


def _garantir_estrutura():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(ATESTADOS_DIR, exist_ok=True)


def _carregar():
    _garantir_estrutura()
    if not os.path.isfile(STORE_PATH):
        return {}
    with open(STORE_PATH, "r", encoding="utf-8") as f:
        try:
            dados = json.load(f)
        except ValueError:
            return {}
    return dados if isinstance(dados, dict) else {}


def _salvar(dados):
    _garantir_estrutura()
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def _chave(enrollid):
    return str(int(enrollid))


def _registro(dados, enrollid):
    chave = _chave(enrollid)
    registro = dados.setdefault(chave, {
        "cpf": "",
        "pis": "",
        "ctps": "",
        "data_admissao": "",
        "atestados": [],
        "afastamentos": [],
    })
    registro.setdefault("cpf", "")
    registro.setdefault("pis", "")
    registro.setdefault("ctps", "")
    registro.setdefault("data_admissao", "")
    registro.setdefault("atestados", [])
    registro.setdefault("afastamentos", [])
    return registro


def normalizar_cpf(cpf):
    texto = "".join(ch for ch in (cpf or "") if ch.isdigit())
    if not texto:
        return ""
    if len(texto) != 11:
        raise ValueError("CPF invalido. Use 11 digitos.")
    if texto == texto[0] * 11:
        raise ValueError("CPF invalido.")
    return "{}.{}.{}-{}".format(texto[:3], texto[3:6], texto[6:9], texto[9:])


def obter_resumo(enrollid):
    with _LOCK:
        dados = _carregar()
        registro = copy.deepcopy(_registro(dados, enrollid))
    return {
        "cpf": registro.get("cpf", ""),
        "pis": registro.get("pis", ""),
        "ctps": registro.get("ctps", ""),
        "data_admissao": registro.get("data_admissao", ""),
        "qtd_atestados": len(registro.get("atestados", []) or []),
        "qtd_afastamentos": len(registro.get("afastamentos", []) or []),
    }


def obter_funcionario(enrollid):
    with _LOCK:
        dados = _carregar()
        registro = copy.deepcopy(_registro(dados, enrollid))
    registro["atestados"] = sorted(
        registro.get("atestados", []) or [],
        key=lambda item: item.get("criado_em", ""),
        reverse=True,
    )
    return registro


def salvar_cpf(enrollid, cpf):
    cpf = normalizar_cpf(cpf)
    with _LOCK:
        dados = _carregar()
        registro = _registro(dados, enrollid)
        registro["cpf"] = cpf
        _salvar(dados)
    return cpf


def salvar_dados_profissionais(enrollid, pis="", ctps="", data_admissao=""):
    pis = "".join(ch for ch in (pis or "") if ch.isdigit())
    ctps = "".join(ch for ch in (ctps or "") if ch.isdigit())
    data_admissao = (data_admissao or "").strip()
    if data_admissao:
        try:
            data_admissao = datetime.strptime(data_admissao, "%Y-%m-%d").date().isoformat()
        except ValueError:
            raise ValueError("Data de admissao invalida. Use o formato YYYY-MM-DD.")
    with _LOCK:
        dados = _carregar()
        registro = _registro(dados, enrollid)
        registro["pis"] = pis
        registro["ctps"] = ctps
        registro["data_admissao"] = data_admissao
        _salvar(dados)
    return {"pis": pis, "ctps": ctps, "data_admissao": data_admissao}


def _extensao_permitida(nome_arquivo):
    _, extensao = os.path.splitext(nome_arquivo.lower())
    return extensao in _EXTENSOES_PERMITIDAS


def adicionar_atestado(enrollid, arquivo, data_emissao="", validade_ate="", observacoes=""):
    if arquivo is None or not getattr(arquivo, "filename", ""):
        raise ValueError("Selecione um arquivo para anexar.")

    nome_original = secure_filename(arquivo.filename)
    if not nome_original:
        raise ValueError("Nome de arquivo invalido.")
    if not _extensao_permitida(nome_original):
        raise ValueError("Formato nao permitido. Use PDF, JPG, JPEG, PNG, DOC ou DOCX.")

    identificador = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + uuid.uuid4().hex[:10]
    extensao = os.path.splitext(nome_original)[1].lower()
    pasta_funcionario = os.path.join(ATESTADOS_DIR, _chave(enrollid))
    os.makedirs(pasta_funcionario, exist_ok=True)
    nome_armazenado = "{}{}".format(identificador, extensao)
    caminho = os.path.join(pasta_funcionario, nome_armazenado)
    arquivo.save(caminho)

    item = {
        "id": identificador,
        "nome_original": nome_original,
        "arquivo": nome_armazenado,
        "data_emissao": (data_emissao or "").strip(),
        "validade_ate": (validade_ate or "").strip(),
        "observacoes": (observacoes or "").strip(),
        "criado_em": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }

    with _LOCK:
        dados = _carregar()
        registro = _registro(dados, enrollid)
        registro.setdefault("atestados", []).append(item)
        _salvar(dados)
    return item


def _normalizar_data_iso(valor):
    valor = (valor or "").strip()
    if not valor:
        return ""
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date().isoformat()
    except ValueError:
        raise ValueError("Data invalida. Use o formato YYYY-MM-DD.")


def adicionar_afastamento(enrollid, tipo, data_inicio, data_fim="", observacoes=""):
    tipo = (tipo or "").strip()
    if not tipo:
        raise ValueError("Informe o tipo do afastamento ou licenca.")
    data_inicio = _normalizar_data_iso(data_inicio)
    data_fim = _normalizar_data_iso(data_fim)
    if data_fim and data_fim < data_inicio:
        raise ValueError("A data final nao pode ser menor que a inicial.")

    item = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S") + "_" + uuid.uuid4().hex[:10],
        "tipo": tipo,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "observacoes": (observacoes or "").strip(),
        "criado_em": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }

    with _LOCK:
        dados = _carregar()
        registro = _registro(dados, enrollid)
        registro.setdefault("afastamentos", []).append(item)
        _salvar(dados)
    return item


def listar_atestados(enrollid):
    registro = obter_funcionario(enrollid)
    return registro.get("atestados", []) or []


def listar_afastamentos(enrollid):
    registro = obter_funcionario(enrollid)
    itens = registro.get("afastamentos", []) or []
    return sorted(itens, key=lambda item: item.get("criado_em", ""), reverse=True)


def obter_atestado(enrollid, atestado_id):
    for item in listar_atestados(enrollid):
        if item.get("id") == atestado_id:
            return item
    return None


def caminho_atestado(enrollid, atestado_id):
    atestado = obter_atestado(enrollid, atestado_id)
    if not atestado:
        return None
    caminho = os.path.join(ATESTADOS_DIR, _chave(enrollid), atestado.get("arquivo", ""))
    return caminho if os.path.isfile(caminho) else None


def excluir_atestado(enrollid, atestado_id):
    with _LOCK:
        dados = _carregar()
        registro = _registro(dados, enrollid)
        itens = registro.get("atestados", []) or []
        removido = None
        novos = []
        for item in itens:
            if item.get("id") == atestado_id:
                removido = item
            else:
                novos.append(item)
        if not removido:
            return None
        registro["atestados"] = novos
        _salvar(dados)

    caminho = os.path.join(ATESTADOS_DIR, _chave(enrollid), removido.get("arquivo", ""))
    if os.path.isfile(caminho):
        os.remove(caminho)
    return removido


def excluir_afastamento(enrollid, afastamento_id):
    with _LOCK:
        dados = _carregar()
        registro = _registro(dados, enrollid)
        itens = registro.get("afastamentos", []) or []
        removido = None
        novos = []
        for item in itens:
            if item.get("id") == afastamento_id:
                removido = item
            else:
                novos.append(item)
        if not removido:
            return None
        registro["afastamentos"] = novos
        _salvar(dados)
    return removido
