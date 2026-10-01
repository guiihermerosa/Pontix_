#!/usr/bin/env python
"""
Pontix Cloud - Entry point para produção
Roda o backend FastAPI
"""
import os
import sys
from pathlib import Path

# Adiciona o diretório backend ao path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

# Importa e roda o app
from app.main import app
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8001)),
        log_level="info"
    )
