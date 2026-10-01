"""
Script de inicialização do Pontix Cloud Backend.
"""
import uvicorn

if __name__ == "__main__":
    print("=" * 60)
    print("  Pontix Cloud iniciando em http://0.0.0.0:8001")
    print("  Acesse via: http://localhost:8001")
    print("=" * 60)
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
