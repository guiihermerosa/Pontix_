"""
Configuração de conexão com Supabase PostgreSQL para Pontix Cloud.
"""
import logging
import os
import sys
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)

# ⚠️ IMPORTANTE: Ler DATABASE_URL ANTES de qualquer outro import
DATABASE_URL = os.getenv("DATABASE_URL")

# Debug detalhado
print(f"\n{'='*60}", file=sys.stderr)
print(f"[DB] Inicializando configuração de banco de dados", file=sys.stderr)
print(f"[DB] DATABASE_URL presente: {DATABASE_URL is not None}", file=sys.stderr)
if DATABASE_URL:
    # Mostra URL sem senha
    parts = DATABASE_URL.split('@')
    print(f"[DB] URL sem senha: {parts[0]}@[REDACTED]", file=sys.stderr)
    print(f"[DB] Host: {parts[1] if len(parts) > 1 else 'N/A'}", file=sys.stderr)
print(f"{'='*60}\n", file=sys.stderr)

if not DATABASE_URL:
    error_msg = (
        "❌ ERRO CRÍTICO: DATABASE_URL não está configurado!\n"
        "Configure a variável de ambiente DATABASE_URL no Render:\n"
        "postgresql+asyncpg://user:password@host:port/database"
    )
    print(f"[DB] {error_msg}", file=sys.stderr)
    raise RuntimeError(error_msg)

if "asyncpg" not in DATABASE_URL:
    error_msg = (
        f"❌ ERRO: DATABASE_URL deve usar +asyncpg!\n"
        f"Recebido: {DATABASE_URL.split('@')[0]}@[REDACTED]\n"
        f"Esperado: postgresql+asyncpg://user:password@host:port/database"
    )
    print(f"[DB] {error_msg}", file=sys.stderr)
    raise RuntimeError(error_msg)

print(f"[DB] ✓ DATABASE_URL configurado corretamente com asyncpg", file=sys.stderr)

from app.database.models import Base

# ---------------------------------------------------------------------------
# Engine assíncrono
# ---------------------------------------------------------------------------

print(f"[DB] Criando engine assíncrono...", file=sys.stderr)

try:
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=10,
        max_overflow=20,
    )
    print(f"[DB] ✓ Engine assíncrono criado com sucesso", file=sys.stderr)
except Exception as e:
    error_msg = f"❌ Erro ao criar engine: {type(e).__name__}: {e}"
    print(f"[DB] {error_msg}", file=sys.stderr)
    raise

logger.info(f"✓ Engine assíncrono criado com sucesso")

# Session factory assíncrona
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
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
        print(f"[DB] Testando conexão e criando tabelas...", file=sys.stderr)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✓ Banco de dados inicializado com sucesso")
        print(f"[DB] ✓ Banco de dados inicializado", file=sys.stderr)
    except Exception as e:
        error_msg = f"✗ Erro ao inicializar banco de dados: {e}"
        logger.error(error_msg)
        print(f"[DB] {error_msg}", file=sys.stderr)
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
        print(f"[DB] Verificando conexão...", file=sys.stderr)
        async with engine.begin() as conn:
            result = await conn.exec_driver_sql("SELECT 1")
            logger.info("✓ Conexão com banco de dados OK")
            print(f"[DB] ✓ Conexão com banco de dados OK", file=sys.stderr)
            return True
    except Exception as e:
        error_msg = f"✗ Erro de conexão com banco de dados: {e}"
        logger.error(error_msg)
        print(f"[DB] {error_msg}", file=sys.stderr)
        return False
