@echo off
setlocal
cd /d "%~dp0"

rem ---- Configuracao ----
set "HOST=127.0.0.1"
set "PORT=8000"
set "VENV=%~dp0.venv"

rem ---- 1. Localizar Python (python ou py -3) ----
set "PYTHON_CMD="
where python >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
    where py >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD (
    echo [ERRO] Python nao encontrado no PATH. Instale Python 3.10 ou superior.
    pause
    exit /b 1
)

rem ---- 2. Verificar versao do Python (>= 3.10) ----
%PYTHON_CMD% -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
if errorlevel 1 (
    echo [ERRO] Requer Python 3.10 ou superior.
    pause
    exit /b 1
)

rem ---- 3. Criar ambiente virtual, se necessario ----
if not exist "%VENV%\Scripts\python.exe" (
    echo Criando ambiente virtual .venv ...
    %PYTHON_CMD% -m venv "%VENV%"
    if errorlevel 1 (
        echo [ERRO] Falha ao criar o ambiente virtual.
        pause
        exit /b 1
    )
)

set "PYV=%VENV%\Scripts\python.exe"

rem ---- 4. Instalar dependencias, se necessario ----
"%PYV%" -c "import fastapi, uvicorn, bcrypt, multipart" >nul 2>nul
if errorlevel 1 (
    echo Instalando dependencias ...
    "%PYV%" -m pip install --upgrade pip >nul 2>nul
    "%PYV%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERRO] Falha ao instalar dependencias.
        pause
        exit /b 1
    )
)

rem ---- 5. Avisar se a porta estiver em uso ----
netstat -ano | findstr ":%PORT% " >nul 2>nul
if not errorlevel 1 (
    echo [AVISO] A porta %PORT% parece estar em uso.
)

rem ---- 6. Abrir navegador e iniciar o servidor ----
echo Iniciando servidor em http://%HOST%:%PORT% ...
start "" cmd /c "timeout /t 3 >nul & start http://%HOST%:%PORT%"
"%PYV%" -m uvicorn app.main:app --host %HOST% --port %PORT% --reload

pause
