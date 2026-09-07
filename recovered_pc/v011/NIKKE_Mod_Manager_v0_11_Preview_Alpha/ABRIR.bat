@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  call INSTALAR_Y_ABRIR.bat
  exit /b
)

rem v0.11 Preview Alpha adds UnityPy + pycryptodome. If this is an upgrade
rem over an older extracted folder, make sure the new dependencies exist.
".venv\Scripts\python.exe" -c "import UnityPy, Crypto" >nul 2>nul
if errorlevel 1 (
  call INSTALAR_Y_ABRIR.bat
  exit /b
)

start "" ".venv\Scripts\pythonw.exe" app.py
