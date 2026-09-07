@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title NIKKE Mod Manager v0.13 Restored Native Preview

echo =====================================================
echo    NIKKE MOD MANAGER v0.13 - PREVIEW NATIVO
ECHO =====================================================
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
echo Verificando dependencias...
"%PY%" -c "import UnityPy, PIL, cryptography, send2trash" >nul 2>&1
if errorlevel 1 (
  echo Instalando UnityPy, Pillow, cryptography y send2trash...
  "%PY%" -m pip install --disable-pip-version-check --upgrade pip >nul
  "%PY%" -m pip install --disable-pip-version-check UnityPy Pillow cryptography send2trash
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
if not exist "manager.py" (
  echo Falta manager.py. Vuelve a extraer el ZIP completo.
  pause
  exit /b 1
)
if not exist "manager_native.py" (
  echo Falta manager_native.py. Vuelve a extraer el ZIP completo.
  pause
  exit /b 1
)
if not exist "native_preview.py" (
  echo Falta native_preview.py. Vuelve a extraer el ZIP completo.
  pause
  exit /b 1
)

REM El gestor y la vista previa se abren como ventanas nativas de Windows.
REM No se abre navegador ni localhost para previsualizar mods.
set "PYW=%CD%\.venv\Scripts\pythonw.exe"
if exist "%PYW%" (
  start "NIKKE Mod Manager" "%PYW%" "%CD%\manager_native.py"
) else (
  start "NIKKE Mod Manager" "%PY%" "%CD%\manager_native.py"
)
exit /b 0
