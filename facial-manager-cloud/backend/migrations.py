"""
Migration script for Pontix Cloud database.

Este script cria todas as tabelas no Supabase PostgreSQL.

Uso:
    python migrations.py create      # Cria todas as tabelas
    python migrations.py drop        # Remove todas as tabelas (⚠️)
    python migrations.py reset       # Remove e recria todas as tabelas (⚠️)
"""
import asyncio
import sys
import logging
from pathlib import Path

# Adiciona o diretório do projeto ao path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import init_db, drop_all_tables, check_db_connection
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create():
    """Cria todas as tabelas."""
    logger.info("Criando tabelas no banco de dados...")
    
    # Verifica conexão
    connected = await check_db_connection()
    if not connected:
        logger.error("Não foi possível conectar ao banco de dados")
        return False
    
    # Inicializa banco de dados
    try:
        await init_db()
        logger.info("✓ Banco de dados criado com sucesso!")
        return True
    except Exception as e:
        logger.error(f"✗ Erro ao criar banco de dados: {e}")
        return False


async def drop():
    """Remove todas as tabelas."""
    logger.warning("⚠️ AVISO: Esta ação removerá TODOS os dados do banco de dados!")
    response = input("Digite 'sim' para confirmar: ").strip().lower()
    
    if response != "sim":
        logger.info("Operação cancelada.")
        return False
    
    try:
        await drop_all_tables()
        logger.info("✓ Todas as tabelas foram removidas")
        return True
    except Exception as e:
        logger.error(f"✗ Erro ao remover tabelas: {e}")
        return False


async def reset():
    """Remove e recria todas as tabelas."""
    logger.warning("⚠️ AVISO: Esta ação removerá TODOS os dados do banco de dados!")
    response = input("Digite 'sim' para confirmar: ").strip().lower()
    
    if response != "sim":
        logger.info("Operação cancelada.")
        return False
    
    try:
        await drop_all_tables()
        logger.info("✓ Tabelas removidas")
        
        await init_db()
        logger.info("✓ Banco de dados recriado com sucesso!")
        return True
    except Exception as e:
        logger.error(f"✗ Erro ao resetar banco de dados: {e}")
        return False


async def seed():
    """Popula o banco de dados com dados de teste."""
    from sqlalchemy import insert
    from app.database import SyncSessionLocal
    from app.database.models import Company, Employee
    from datetime import datetime
    from uuid import uuid4
    
    logger.info("Adicionando dados de teste...")
    
    try:
        with SyncSessionLocal() as session:
            # Cria empresa de teste
            company = Company(
                id=uuid4(),
                name="Empresa Teste",
                cnpj="12.345.678/0001-00",
                email="contato@empresa.com",
                owner_id="test-owner-001",
                timezone="America/Sao_Paulo",
            )
            
            session.add(company)
            session.commit()
            
            logger.info(f"✓ Empresa criada: {company.name}")
            
            # Cria funcionários de teste
            for i in range(5):
                employee = Employee(
                    id=uuid4(),
                    company_id=company.id,
                    user_id=f"user-{i+1:03d}",
                    full_name=f"Funcionário {i+1}",
                    email=f"employee{i+1}@empresa.com",
                    cpf=f"{111*(i+1):014d}",
                    department="TI",
                    admission_date=datetime.now(),
                )
                session.add(employee)
            
            session.commit()
            logger.info("✓ 5 funcionários de teste adicionados")
        
        return True
    except Exception as e:
        logger.error(f"✗ Erro ao adicionar dados de teste: {e}")
        return False


def main():
    """Entry point."""
    if len(sys.argv) < 2:
        print("Uso: python migrations.py [create|drop|reset|seed]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "create":
        result = asyncio.run(create())
    elif command == "drop":
        result = asyncio.run(drop())
    elif command == "reset":
        result = asyncio.run(reset())
    elif command == "seed":
        result = asyncio.run(seed())
    else:
        logger.error(f"Comando desconhecido: {command}")
        print("Comandos válidos: create, drop, reset, seed")
        result = False
    
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
