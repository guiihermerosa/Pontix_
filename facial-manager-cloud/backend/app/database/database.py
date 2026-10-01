"""
Configuração de conexão com Supabase PostgreSQL para Pontix Cloud.
"""
import logging
from typing import AsyncGenerator

from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database.models import Base

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Engine assíncrono para Supabase
# ---------------------------------------------------------------------------

# URL de conexão assíncrona com PostgreSQL
DATABASE_URL = f"postgresql+asyncpg://{settings.SUPABASE_URL.split('://')[1].split(':')[0]}:{settings.SUPABASE_KEY}@{settings.SUPABASE_URL.split('://')[1]}/postgres"

# Fallback se SUPABASE_URL não estiver configurado
if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
    logger.warning("SUPABASE_URL ou SUPABASE_KEY não configurados. Usando SQLite de fallback.")
    DATABASE_URL = "sqlite+aiosqlite:///./data/pontix_cloud.db"

# Engine assíncrono
engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=10,
    max_overflow=20,
)

# Session factory assíncrona
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ---------------------------------------------------------------------------
# Engine síncrono para migrações e tarefas administrativas
# ---------------------------------------------------------------------------

# Fallback para URL síncrona se precisar
SYNC_DATABASE_URL = settings.SUPABASE_URL or "sqlite:///./data/pontix_cloud.db"

if SYNC_DATABASE_URL.startswith("postgresql://"):
    SYNC_DATABASE_URL = SYNC_DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://")
elif SYNC_DATABASE_URL.startswith("postgresql+asyncpg://"):
    SYNC_DATABASE_URL = SYNC_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")

sync_engine = create_engine(
    SYNC_DATABASE_URL,
    echo=settings.DEBUG,
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
