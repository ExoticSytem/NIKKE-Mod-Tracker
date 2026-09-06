@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title NIKKE Mod Manager v0.12 Preview Beta

echo ===============================================
echo    NIKKE MOD MANAGER v0.12 PREVIEW BETA
echo ===============================================
echo.

set "PY="
if exist ".venv\Scripts\python.exe" set "PY=%CD%\.venv\Scripts\python.exe"
if defined PY goto deps

where py >nul 2>&1
if not errorlevel 1 (
  py -3.12 -c "import sys" >nul 2>&1
  if not errorlevel 1 (
    echo Creando entorno Python local...
    py -3.12 -m venv .venv
    set "PY=%CD%\.venv\Scripts\python.exe"
    goto deps
  )
  py -3 -c "import sys" >nul 2>&1
  if not errorlevel 1 (
    echo Creando entorno Python local...
    py -3 -m venv .venv
    set "PY=%CD%\.venv\Scripts\python.exe"
    goto deps
  )
)

where python >nul 2>&1
if not errorlevel 1 (
  echo Creando entorno Python local...
  python -m venv .venv
  if exist ".venv\Scripts\python.exe" set "PY=%CD%\.venv\Scripts\python.exe"
)

if not defined PY (
  echo.
  echo No se encontro Python 3 en este PC.
  echo Instala Python 3.11 o 3.12 desde python.org y vuelve a ejecutar este archivo.
  echo Marca "Add Python to PATH" durante la instalacion.
  pause
  exit /b 1
)

:deps
echo Verificando dependencias del visualizador...
"%PY%" -c "import UnityPy, PIL, cryptography" >nul 2>&1
if errorlevel 1 (
  echo Instalando UnityPy, Pillow y cryptography...
  "%PY%" -m pip install --disable-pip-version-check --upgrade pip >nul
  "%PY%" -m pip install --disable-pip-version-check UnityPy Pillow cryptography
  if errorlevel 1 (
    echo.
    echo No se pudieron instalar las dependencias.
    pause
    exit /b 1
  )
)

if not exist "tools\preview_beta_server.py" (
  echo Falta tools\preview_beta_server.py. Vuelve a extraer el ZIP completo.
  pause
  exit /b 1
)

if not exist "manager_server.py" (
  echo Falta manager_server.py. Vuelve a extraer el ZIP completo.
  pause
  exit /b 1
)

REM Cierra instancias antiguas solo de nuestros puertos mediante los endpoints, sin matar Python global.
powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 http://127.0.0.1:8137/health | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 start "NIKKE Preview Beta" /min "%PY%" "%CD%\tools\preview_beta_server.py" --root "%CD%" --port 8137

powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 http://127.0.0.1:8136/api/health | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
  start "NIKKE Mod Manager" /min "%PY%" "%CD%\manager_server.py" --port 8136
  timeout /t 2 /nobreak >nul
)

start "" "http://127.0.0.1:8136/"
exit /b 0
