@echo off
cd /d "%~dp0"
REM Inicia servidor em nova janela, ativando .venv se existir
if exist ".venv\Scripts\Activate.bat" (
  start "SILGON Server" cmd /k "cd /d "%~dp0" && .venv\Scripts\Activate.bat && python app.py"
) else (
  start "SILGON Server" cmd /k "cd /d "%~dp0" && python app.py"
)
REM Pequena espera para permitir que o servidor suba, depois abre o navegador
timeout /t 2 >nul
start "" "http://127.0.0.1:5000/"
