# -*- coding: utf-8 -*-

import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "relatorios", "auditoria")
LOG_PATH = os.path.join(LOG_DIR, "auditoria.jsonl")


def registrar_evento(tipo, detalhe, origem="web"):
    if not os.path.isdir(LOG_DIR):
        os.makedirs(LOG_DIR)
    item = {
        "quando": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "tipo": tipo,
        "origem": origem,
        "detalhe": detalhe,
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")
    return item


def ler_eventos(limite=100):
    if not os.path.isfile(LOG_PATH):
        return []
    eventos = []
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha:
                continue
            try:
                eventos.append(json.loads(linha))
            except ValueError:
                continue
    if limite is not None and limite > 0:
        eventos = eventos[-limite:]
    return eventos
