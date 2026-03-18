@echo off
setlocal

REM Builds a portable folder (EXE + templates) using the active venv.
REM Output: dist\SILGON\

cd /d %~dp0\..

if exist .venv\Scripts\activate.bat (
  call .venv\Scripts\activate.bat
)

python -m pip install --upgrade pip
python -m pip install pyinstaller

pyinstaller --noconfirm --clean --onedir --name SILGON ^
  --add-data "SILGON\templates;templates" ^
  --add-data "SILGON\static;static" ^
  SILGON\portable_server.py

REM Ensure dist folder does not ship a DB
if exist dist\SILGON\silgon.db del /f /q dist\SILGON\silgon.db

REM Create run helpers inside dist
(
  echo @echo off
  echo setlocal
  echo.
  echo REM Starts SILGON server and opens browser
  echo start "" "http://127.0.0.1:5000/"
  echo "%%~dp0SILGON.exe" --host 127.0.0.1 --port 5000
) > dist\SILGON\run_silgon.bat

(
  echo @echo off
  echo setlocal
  echo.
  echo REM Resets the local DB ^(silgon.db^) and starts the server
  echo start "" "http://127.0.0.1:5000/"
  echo "%%~dp0SILGON.exe" --host 127.0.0.1 --port 5000 --reset-db
) > dist\SILGON\run_silgon_reset_db.bat

echo.
echo Build OK. Send the folder: dist\SILGON\
echo.
pause
