"""
Configuração do banco de dados SQLite com SQLAlchemy.
"""
import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Caminho absoluto para o banco de dados
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "data" / "facial.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    echo=False,
)

# Habilitar WAL mode, busy_timeout e foreign keys no SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")   # espera até 5s antes de SQLITE_BUSY
    cursor.execute("PRAGMA synchronous=NORMAL")  # melhor performance com WAL
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA cache_size=-32000")   # 32 MB de cache
    cursor.close()


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,   # evita lazy-load após commit em requests concorrentes
    bind=engine,
)


class Base(DeclarativeBase):
    pass


def get_db():
    """Dependency para injeção do banco nas rotas FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Cria todas as tabelas e popula configurações padrão."""
    from app.database.models import Base as ModelBase  # evita import circular
    ModelBase.metadata.create_all(bind=engine)
    _seed_default_settings()


def _seed_default_settings():
    """Insere configurações padrão se ainda não existirem."""
    from app.database.models import Setting
    db = SessionLocal()
    try:
        defaults = {
            "device_host":         "192.168.0.24",
            "device_port":         "80",
            "device_password":     "",          # preenchido pelo usuário
            "device_timeout":      "10",
            "sync_interval":       "30",
            "sync_auto_enabled":   "true",
            "sync_employees":      "true",
            "sync_attendance":     "true",
            "log_level":           "INFO",
            "log_retention_days":  "30",
            "app_name":            "Pontix",
        }
        for key, value in defaults.items():
            exists = db.query(Setting).filter(Setting.key == key).first()
            if not exists:
                db.add(Setting(key=key, value=value))
        db.commit()
    finally:
        db.close()
