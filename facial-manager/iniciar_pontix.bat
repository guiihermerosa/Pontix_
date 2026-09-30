@echo off
:: Pontix — Inicializador
:: Sobe o servidor na porta 80 para acesso via http://pontix.local
:: Requer execução como Administrador.

cd /d "%~dp0"

echo.
echo  =========================================
echo    Pontix — Gerenciador de Ponto
echo  =========================================
echo.

:: Verifica se está rodando como admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  [AVISO] Execute este arquivo como Administrador
    echo  para usar a porta 80 (http://pontix.local^).
    echo.
    echo  Subindo na porta 8000 em vez disso...
    echo  Acesse: http://pontix.local:8000
    echo.
    python run.py --port 8000
) else (
    echo  Subindo na porta 80...
    echo  Acesse: http://pontix.local
    echo.
    python run.py --port 80
)

pause
