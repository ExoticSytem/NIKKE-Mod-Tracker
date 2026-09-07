@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  call INSTALAR_Y_ABRIR.bat
  exit /b
)
start "Preview Beta v0.12" ".venv\Scripts\python.exe" "tools\preview_beta_server.py" --root "%~dp0"
".venv\Scripts\python.exe" app.py
pause
