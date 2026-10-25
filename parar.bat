@echo off
setlocal
rem Para o servidor do app (uvicorn) que estiver escutando na porta.
rem Uso: parar.bat            -> porta 8000 (padrao)
rem      parar.bat 8010       -> outra porta
set PORT=8000
if not "%~1"=="" set PORT=%~1

echo Procurando servidor na porta %PORT% ...
set FOUND=0
for /f "tokens=5" %%p in ('netstat -ano ^| findstr :%PORT% ^| findstr LISTENING') do (
    echo  - encerrando PID %%p
    taskkill /PID %%p /F >nul 2>&1
    set FOUND=1
)

if "%FOUND%"=="0" (
    echo Nenhum servidor escutando na porta %PORT%.
) else (
    echo Servidor encerrado. Rode iniciar.bat e de Ctrl+F5 no navegador.
)
endlocal
