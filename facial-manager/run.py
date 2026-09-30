"""
Ponto de entrada da aplicação Pontix.

Execução padrão (porta 8000):
    python run.py

Execução na porta 80 (acesso via http://pontix.local):
    python run.py --port 80
    Requer permissão de administrador no Windows para usar porta < 1024.

Execução em produção (sem reload):
    python run.py --prod
"""
import argparse
import uvicorn

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pontix — servidor web")
    parser.add_argument("--host", default="0.0.0.0", help="Interface de rede (padrão: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Porta (padrão: 8000)")
    parser.add_argument("--prod", action="store_true", help="Modo produção (sem reload automático)")
    args = parser.parse_args()

    print(f"\n  Pontix iniciando em http://{args.host}:{args.port}")
    if args.port == 80:
        print("  Acesse via: http://pontix.local")
    else:
        print(f"  Acesse via: http://pontix.local:{args.port}  ou  http://localhost:{args.port}")
    print()

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=not args.prod,
        reload_dirs=["app", "static"],   # monitora todos os arquivos, inclusive novos
        log_level="info",
    )
