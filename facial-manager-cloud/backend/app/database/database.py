"""
Configuração de conexão com Supabase PostgreSQL para Pontix Cloud.
"""
import logging
import os
import sys
from typing import AsyncGenerator

from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# ⚠️ IMPORTANTE: Ler DATABASE_URL ANTES de qualquer outro import
DATABASE_URL = os.getenv("DATABASE_URL")

print(f"[STARTUP] DATABASE_URL={DATABASE_URL[:50] if DATABASE_URL else 'NOT SET'}...", file=sys.stderr)

if not DATABASE_URL:
    raise RuntimeError(
        "❌ ERRO CRÍTICO: DATABASE_URL não está configurado!\n"
        "Configure a variável de ambiente DATABASE_URL no Render:\n"
        "postgresql+asyncpg://user:password@host:port/database"
    )

if "asyncpg" not in DATABASE_URL:
    raise RuntimeError(
        f"❌ ERRO: DATABASE_URL deve usar +asyncpg!\n"
        f"Recebido: {DATABASE_URL.split('@')[0]}@...\n"
        f"Esperado: postgresql+asyncpg://user:password@host:port/database"
    )

print(f"[STARTUP] ✓ DATABASE_URL configurado corretamente", file=sys.stderr)

from app.database.models import Base

# ---------------------------------------------------------------------------
# Engine assíncrono
# ---------------------------------------------------------------------------

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=10,
    max_overflow=20,
)

logger.info(f"✓ Engine assíncrono criado: {DATABASE_URL.split('@')[0]}@...")

# Session factory assíncrona
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ---------------------------------------------------------------------------
# Engine síncrono para migrações
# ---------------------------------------------------------------------------

SYNC_DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")

sync_engine = create_engine(
    SYNC_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=3600,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)


# ---------------------------------------------------------------------------
# Dependency para FastAPI (async)
# ---------------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency para injetar sessão do banco de dados em endpoints.
    
    Uso:
        @app.get("/api/employees")
        async def get_employees(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Employee))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Inicialização do banco de dados
# ---------------------------------------------------------------------------

async def init_db():
    """
    Cria todas as tabelas no banco de dados.
    Execute uma única vez na inicialização da aplicação.
    """
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✓ Banco de dados inicializado com sucesso")
    except Exception as e:
        logger.error(f"✗ Erro ao inicializar banco de dados: {e}")
        raise


async def drop_all_tables():
    """
    Remove todas as tabelas do banco de dados.
    ⚠️ USE COM CUIDADO - DELETA TODOS OS DADOS!
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.warning("⚠️ Todas as tabelas foram removidas do banco de dados")


async def check_db_connection():
    """
    Verifica a conexão com o banco de dados.
    """
    try:
        async with engine.begin() as conn:
            result = await conn.execute("SELECT 1")
            logger.info("✓ Conexão com banco de dados OK")
            return True
    except Exception as e:
        logger.error(f"✗ Erro de conexão com banco de dados: {e}")
        return False


# ---------------------------------------------------------------------------
# Migrations (alembic compatible)
# ---------------------------------------------------------------------------

def get_migration_context():
    """
    Retorna contexto para Alembic (se usar)
    """
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from alembic.runtime.migration import MigrationContext
    
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)
    mc = MigrationContext.configure(sync_engine)
    
    return config, script, mc
