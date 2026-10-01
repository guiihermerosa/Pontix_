"""
Pontix Cloud — Painel para Contador e Proprietário
Ponto de entrada da aplicação FastAPI.

Funcionalidades:
  1. Autenticação JWT com Supabase
  2. Painel do Contador (contabilidade)
  3. Painel do Proprietário (visão geral)
  4. Sincronização com sistema local
  5. Relatórios e estatísticas
"""
import logging
import logging.handlers
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db, check_db_connection
from app.auth import AuthMiddleware
from app.api import routes_auth, routes_accounting, routes_owner, routes_sync

# ---------------------------------------------------------------------------
# Diretórios base
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging():
    fmt = logging.Formatter(
        fmt="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)

    # Arquivo rotativo
    file_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / "pontix-cloud.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(console)
    root.addHandler(file_handler)

    # Silencia loggers verbosos
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


setup_logging()
logger = logging.getLogger("main")


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("  Pontix Cloud iniciando…")
    logger.info("=" * 60)
    
    # Inicializa banco de dados
    try:
        await init_db()
        await check_db_connection()
    except Exception as e:
        logger.error(f"Erro ao inicializar banco de dados: {e}")
    
    yield  # Aplicação rodando
    
    logger.info("Pontix Cloud encerrado.")


# ---------------------------------------------------------------------------
# Aplicação
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Pontix Cloud",
    description="Painel de Contador e Proprietário - Sistema Cloud",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication Middleware
app.add_middleware(AuthMiddleware, require_auth=settings.REQUIRE_AUTH)

# Include Routers
app.include_router(routes_auth.router)
app.include_router(routes_accounting.router)
app.include_router(routes_owner.router)
app.include_router(routes_sync.router)

# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------

# Placeholder para rotas futuras
@app.get("/")
async def root():
    return {
        "name": "Pontix Cloud",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "pontix-cloud"
    }


@app.get("/api/accountant")
async def accountant_dashboard():
    """
    Painel do Contador.
    Retorna: Resumo de funcionários, presença, ocorrências, justificativas.
    """
    return {
        "message": "Painel do Contador - em desenvolvimento",
        "features": [
            "Listagem de funcionários",
            "Registros de presença",
            "Ocorrências e justificativas",
            "Relatórios mensais",
            "Exportação de dados"
        ]
    }


@app.get("/api/owner")
async def owner_dashboard():
    """
    Painel do Proprietário.
    Retorna: Visão geral, estatísticas, integrações.
    """
    return {
        "message": "Painel do Proprietário - em desenvolvimento",
        "features": [
            "Visão geral da empresa",
            "Estatísticas de presença",
            "Configurações de integração",
            "Gerenciamento de usuários",
            "Faturamento e planos"
        ]
    }


# ---------------------------------------------------------------------------
# Error Handlers
# ---------------------------------------------------------------------------

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Recurso não encontrado"}
    )


@app.exception_handler(500)
async def server_error_handler(request, exc):
    logger.exception("Erro interno: %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor"}
    )
