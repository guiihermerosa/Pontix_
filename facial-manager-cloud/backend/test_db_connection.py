#!/usr/bin/env python
"""
Script para testar conexão com banco de dados Supabase
Uso: python test_db_connection.py
"""
import asyncio
import os
import sys

async def test_connection():
    print("[TEST] Testando conexão com banco de dados Supabase...")
    print(f"[TEST] DATABASE_URL: {os.getenv('DATABASE_URL', 'NOT SET')[:80]}...")
    
    # Parse da URL manual
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        try:
            # Remove protocolo
            url_parts = db_url.replace("postgresql+asyncpg://", "")
            # Parse user:pass@host:port/database
            auth_part, host_part = url_parts.split("@")
            user, password = auth_part.split(":")
            host_port, database = host_part.rsplit("/", 1)
            host, port = host_port.rsplit(":", 1)
            
            print(f"[TEST] Parsed:")
            print(f"  - Host: {host}")
            print(f"  - Port: {port}")
            print(f"  - Database: {database}")
            print(f"  - User: {user}")
        except Exception as e:
            print(f"[ERROR] Erro ao fazer parse da URL: {e}")
    
    try:
        # Testa se tem asyncpg
        import asyncpg
        print("[OK] asyncpg importado")
    except ImportError as e:
        print(f"[ERROR] asyncpg não está instalado: {e}")
        return False
    
    try:
        # Testa SQLAlchemy
        from sqlalchemy.ext.asyncio import create_async_engine
        print("[OK] SQLAlchemy async importado")
    except ImportError as e:
        print(f"[ERROR] SQLAlchemy não está instalado: {e}")
        return False
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("[ERROR] DATABASE_URL não está configurado!")
        return False
    
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        
        print("[TEST] Criando engine...")
        engine = create_async_engine(
            database_url,
            echo=False,
            pool_pre_ping=True,
        )
        
        print("[TEST] Testando conexão simples...")
        async with engine.connect() as conn:
            result = await conn.exec_driver_sql("SELECT 1")
            val = result.scalar()
            print(f"[OK] ✓ Conexão bem-sucedida! Query retornou: {val}")
            await engine.dispose()
            return True
            
    except Exception as e:
        print(f"[ERROR] Erro: {type(e).__name__}")
        print(f"[ERROR] Mensagem: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Se não tem DATABASE_URL, usa default para teste local
    if not os.getenv("DATABASE_URL"):
        print("[INFO] DATABASE_URL não configurada, usando default local...")
        os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/pontix"
    
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)
