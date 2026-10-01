"""
Script de inicialização do Pontix Cloud Backend.
"""
import os
import sys
import uvicorn

# Debug: mostra variáveis de ambiente críticas
print("[STARTUP] Variáveis de ambiente críticas:", file=sys.stderr)
print(f"[STARTUP] RENDER: {os.getenv('RENDER')}", file=sys.stderr)
print(f"[STARTUP] DATABASE_URL: {os.getenv('DATABASE_URL', 'NOT SET')[:60] if os.getenv('DATABASE_URL') else 'NOT SET'}...", file=sys.stderr)
print(f"[STARTUP] DEBUG: {os.getenv('DEBUG')}", file=sys.stderr)

if __name__ == "__main__":
    print("=" * 60)
    print("  Pontix Cloud iniciando em http://0.0.0.0:8001")
    print("  Acesse via: http://localhost:8001")
    print("=" * 60)
    
    # Detecta ambiente
    is_production = any([
        os.getenv("RENDER") is not None,
        os.getenv("HEROKU") is not None,
        os.getenv("VERCEL") is not None,
        os.getenv("ENVIRONMENT") == "production",
    ])
    
    print(f"[DEBUG] is_production={is_production}, RENDER={os.getenv('RENDER')}", file=sys.stderr)
    
    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8001,
            reload=False,
            log_level="info"
        )
    except Exception as e:
        print(f"[ERROR] Erro ao iniciar aplicação: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
