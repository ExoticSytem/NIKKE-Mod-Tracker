@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  call INSTALAR_Y_ABRIR.bat
  exit /b
)

".venv\Scripts\python.exe" -c "import UnityPy, Crypto, cryptography, PIL" >nul 2>nul
if errorlevel 1 (
  call INSTALAR_Y_ABRIR.bat
  exit /b
)

call "%~dp0tools\START_PREVIEW_BETA.bat"
start "" ".venv\Scripts\pythonw.exe" app.py
