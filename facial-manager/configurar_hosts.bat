@echo off
:: ============================================================
::  Pontix — Configurar domínio local (pontix.local)
::  Execute como Administrador
:: ============================================================

cd /d "%~dp0"
setlocal

set HOSTS_FILE=C:\Windows\System32\drivers\etc\hosts
set ENTRY=127.0.0.1 pontix.local
set MARKER=# pontix

echo.
echo  =========================================
echo    Pontix — Configurar dominio local
echo  =========================================
echo.

:: Verifica privilégios de administrador
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERRO] Este script precisa ser executado como Administrador.
    echo.
    echo  Como fazer:
    echo  1. Clique com o botao direito neste arquivo
    echo  2. Selecione "Executar como administrador"
    echo.
    pause
    exit /b 1
)

:: Verifica se a entrada já existe
findstr /C:"pontix.local" "%HOSTS_FILE%" >nul 2>&1
if %errorlevel% == 0 (
    echo  [OK] pontix.local ja esta configurado no hosts.
    echo.
    echo  Entrada encontrada:
    findstr /C:"pontix.local" "%HOSTS_FILE%"
    echo.
    goto :test
)

:: Adiciona a entrada
echo. >> "%HOSTS_FILE%"
echo %ENTRY%   %MARKER% >> "%HOSTS_FILE%"

if %errorlevel% == 0 (
    echo  [OK] Entrada adicionada com sucesso!
    echo      %ENTRY%
) else (
    echo  [ERRO] Nao foi possivel editar o arquivo hosts.
    echo  Verifique se o arquivo nao esta bloqueado por antivirus.
    pause
    exit /b 1
)

echo.

:test
:: Testa resolucao do nome
echo  Testando resolucao de pontix.local...
ping -n 1 pontix.local >nul 2>&1
if %errorlevel% == 0 (
    echo  [OK] pontix.local resolve corretamente para 127.0.0.1
) else (
    echo  [AVISO] Nao foi possivel resolver pontix.local ainda.
    echo  Tente abrir um novo terminal e pingar novamente.
)

echo.
echo  =========================================
echo    Como acessar o Pontix:
echo.
echo    Porta 8000 (sem admin):
echo    http://pontix.local:8000
echo.
echo    Porta 80 (com admin):
echo    http://pontix.local
echo    (use iniciar_pontix.bat como admin)
echo  =========================================
echo.

pause
endlocal
