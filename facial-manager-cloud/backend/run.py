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
    
    # Detecta ambiente (Render usa variável RENDER)
    is_production = os.getenv("RENDER") is not None
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=not is_production,  # Disable reload em produção
        log_level="info"
    )
