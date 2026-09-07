@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  call INSTALAR_Y_ABRIR.bat
  exit /b
)
".venv\Scripts\python.exe" app.py
pause
