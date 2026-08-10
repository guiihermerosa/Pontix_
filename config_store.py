# -*- coding: utf-8 -*-
"""Le e grava as configuracoes (IP, senha, empresa, logo) num config.json,
pra ninguem precisar mais editar codigo Python pra mudar isso."""

import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def _padrao_turnos_config():
    return [
        {
            "sections": [
                {"active": True},
                {"active": True},
                {"active": True},
            ]
        }
        for _ in range(8)
    ]


PADRAO = {
    "device_ip": "192.168.0.24",
    "device_port": 80,
    "device_password": "",
    "company_name": "Minha Empresa",
    "vendor_name": "GRB Tecnologia",
    "logo_path": "",
    "output_dir": "relatorios",
    "turnos_config": _padrao_turnos_config(),
    "notificacoes_ativas": False,
    "intervalo_notificacao_segundos": 60,
    "coleta_retrospectiva_dias": 7,
    "regras_ponto": {
        "banco_horas": {
            "ativo": True,
            "limite_minutos": 480,
            "validade_dias": 30,
            "compensacao_minutos": 0,
        },
        "horas_extras": {
            "ativo": True,
            "percentual_50": 50,
            "percentual_70": 70,
            "percentual_100": 100,
            "domingos_percentual": 100,
            "feriados_percentual": 100,
            "noturnas_percentual": 70,
        },
        "adicional_noturno": {
            "ativo": True,
            "inicio": "22:00",
            "fim": "05:00",
            "percentual": 20,
        },
        "tolerancias": {
            "entrada_minutos": 5,
            "saida_minutos": 10,
        },
        "intervalo": {
            "minimo_minutos": 30,
            "maximo_minutos": 120,
            "avisar": True,
        },
        "feriados": [
            {"data": "01-01", "nome": "Confraternizacao Universal", "tipo": "nacional", "ativo": True},
        ],
        "escalas": [
            {"nome": "Escala A", "descricao": "", "funcionarios": []},
            {"nome": "Escala B", "descricao": "", "funcionarios": []},
            {"nome": "Escala C", "descricao": "", "funcionarios": []},
        ],
    },
}


def _mesclar_padrao(base, dados):
    if isinstance(base, dict):
        resultado = dict(base)
        for chave, valor in (dados or {}).items():
            if chave in resultado:
                resultado[chave] = _mesclar_padrao(resultado[chave], valor)
            else:
                resultado[chave] = valor
        return resultado
    if isinstance(base, list):
        if isinstance(dados, list):
            return dados
        return list(base)
    return dados if dados is not None else base


def carregar():
    if not os.path.isfile(CONFIG_PATH):
        salvar(PADRAO)
        return dict(PADRAO)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        dados = json.load(f)
    return _mesclar_padrao(PADRAO, dados)


def salvar(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def esta_configurado(config):
    return bool(config.get("device_password"))
