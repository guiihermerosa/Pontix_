"""
Pontix — ponto de entrada da aplicação FastAPI.

Inicialização:
  1. Cria banco de dados e tabelas
  2. Carrega configurações padrão
  3. Registra rotas
  4. Inicia serviço de sincronização em background
  5. Configura logging
"""
import logging
import logging.handlers
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes_attendance import router as attendance_router
from app.api.routes_dashboard import router as dashboard_router
from app.api.routes_employees import router as employees_router
from app.api.routes_settings import router as settings_router
from app.api.routes_sync import router as sync_router
from app.api.routes_email import router as email_router
from app.api.routes_certificates import router as certificates_router
from app.api.routes_auth import router as auth_router
from app.api.routes_portal import router as portal_router
from app.api.routes_time_view import router as time_view_router
from app.api.routes_accountant import router as accountant_router
from app.api.routes_occurrences import router as occurrences_router
from app.api.routes_justifications import router as justifications_router
from app.database.database import init_db
from app.services.sync_service import start_sync_service, stop_sync_service

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

    # Arquivo rotativo — 5 MB × 5 arquivos
    file_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / "pontix.log",
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

    # Silencia loggers muito verbosos
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


setup_logging()
logger = logging.getLogger("main")

# ---------------------------------------------------------------------------
# Scheduler global — usado pelo email_service para re-agendar jobs
# ---------------------------------------------------------------------------
scheduler = AsyncIOScheduler(timezone="America/Sao_Paulo")


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("  Pontix iniciando…")
    logger.info("=" * 60)

    # 1. Inicializa banco
    logger.info("Inicializando banco de dados…")
    init_db()
    logger.info("Banco pronto.")

    # 2. Inicia sincronizador
    logger.info("Iniciando serviço de sincronização…")
    start_sync_service()

    # 3. Inicia scheduler e agenda job mensal de email
    logger.info("Iniciando scheduler de tarefas…")
    from app.database.database import SessionLocal
    from app.services.email_service import schedule_monthly_email
    _db = SessionLocal()
    try:
        from app.database.models import Setting
        row = _db.query(Setting).filter(Setting.key == "email_send_day").first()
        send_day = int(row.value) if row and row.value else 1
    finally:
        _db.close()
    schedule_monthly_email(scheduler, day=send_day)
    scheduler.start()
    logger.info("Scheduler iniciado. Job mensal agendado para o dia %d.", send_day)

    yield  # aplicação rodando

    # Shutdown
    logger.info("Encerrando scheduler…")
    scheduler.shutdown(wait=False)
    logger.info("Encerrando serviço de sincronização…")
    stop_sync_service()
    logger.info("Pontix encerrado.")


# ---------------------------------------------------------------------------
# Aplicação
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Pontix",
    description="Sistema de gerenciamento do dispositivo ALTEK ALPHA-1111",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware de autenticação - OBRIGATÓRIO em todos endpoints
from app.auth.middleware import auth_middleware
app.middleware("http")(auth_middleware(app, require_auth=True))  # ✅ ATIVADO: Autentica todos os requests

# Arquivos estáticos
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Templates — usa a instância centralizada com filtros e globals já registrados
from app.templates_config import templates  # noqa: E402

# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------

app.include_router(dashboard_router,      tags=["Dashboard"])
app.include_router(employees_router,      tags=["Funcionários"])
app.include_router(attendance_router,     tags=["Presença"])
app.include_router(settings_router,       tags=["Configurações"])
app.include_router(sync_router,           tags=["Sincronização"])
app.include_router(email_router,          tags=["Email"])
app.include_router(certificates_router,   tags=["Atestados"])
app.include_router(auth_router,           tags=["Autenticação"])
app.include_router(portal_router,         tags=["Portal do Contador"])
app.include_router(time_view_router,      tags=["Visualização de Batidas"])
app.include_router(accountant_router,     tags=["Portal Contador v1"])
app.include_router(occurrences_router,    tags=["Ocorrências"])
app.include_router(justifications_router, tags=["Justificativas"])


# Rota de relatórios (página HTML)
from fastapi import Depends
from sqlalchemy.orm import Session
from app.database.database import get_db


@app.get("/relatorios", tags=["Relatórios"])
async def reports_page(request: Request, db: Session = Depends(get_db)):
    from app.database.models import Employee
    employees = db.query(Employee).order_by(Employee.name).all()
    return templates.TemplateResponse("reports.html", {
        "request": request,
        "employees": employees,
        "active_page": "reports",
    })


# ---------------------------------------------------------------------------
# Handlers globais de erro
# ---------------------------------------------------------------------------

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"detail": "Recurso não encontrado"})
    return templates.TemplateResponse(
        "errors/404.html", {"request": request}, status_code=404
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    logger.exception("Erro interno: %s %s", request.method, request.url)
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=500,
            content={"detail": "Erro interno do servidor"},
        )
    return templates.TemplateResponse(
        "errors/500.html", {"request": request}, status_code=500
    )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Sistema"])
async def health():
    return {"status": "ok", "service": "pontix"}
