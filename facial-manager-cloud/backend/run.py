"""
Script de inicialização do Pontix Cloud Backend.
"""
import os
import uvicorn

if __name__ == "__main__":
    print("=" * 60)
    print("  Pontix Cloud iniciando em http://0.0.0.0:8001")
    print("  Acesse via: http://localhost:8001")
    print("=" * 60)
    
    # Detecta ambiente (Render, Heroku, ou outro PaaS)
    is_production = any([
        os.getenv("RENDER") is not None,
        os.getenv("HEROKU") is not None,
        os.getenv("VERCEL") is not None,
        os.getenv("ENVIRONMENT") == "production",
    ])
    
    print(f"[DEBUG] is_production={is_production}, RENDER={os.getenv('RENDER')}")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,  # Sempre desabilita reload em produção
        log_level="info"
    )
