#!/usr/bin/env python
"""
Script para testar conexão com banco de dados Supabase
"""
import asyncio
import os
import sys

async def test_connection():
    print("[TEST] Testando conexão com banco de dados...")
    print(f"[TEST] DATABASE_URL: {os.getenv('DATABASE_URL', 'NOT SET')[:50]}...")
    
    try:
        # Testa se tem asyncpg
        import asyncpg
        print("[OK] asyncpg importado com sucesso")
    except ImportError as e:
        print(f"[ERROR] Erro ao importar asyncpg: {e}")
        return False
    
    try:
        # Testa SQLAlchemy
        from sqlalchemy.ext.asyncio import create_async_engine
        print("[OK] SQLAlchemy async importado com sucesso")
    except ImportError as e:
        print(f"[ERROR] Erro ao importar SQLAlchemy async: {e}")
        return False
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("[ERROR] DATABASE_URL não está configurado!")
        return False
    
    print(f"[TEST] Usando: {database_url.split('@')[0]}@...")
    
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        
        engine = create_async_engine(
            database_url,
            echo=True,
            pool_pre_ping=True,
        )
        
        print("[TEST] Engine criado com sucesso")
        
        # Tenta fazer uma query simples
        async with engine.connect() as conn:
            result = await conn.exec_driver_sql("SELECT 1")
            print(f"[OK] Conexão bem-sucedida! Query retornou: {result.scalar()}")
            await engine.dispose()
            return True
            
    except Exception as e:
        print(f"[ERROR] Erro ao conectar: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)
