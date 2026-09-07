@echo off
setlocal
cd /d "%~dp0"
title NIKKE Mod Manager v0.12 Preview Beta - Instalador

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py"
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        set "PY=python"
    ) else (
        echo.
        echo [ERROR] No se encontro Python.
        echo Instala Python 3.11 o superior desde https://www.python.org/downloads/
        echo Durante la instalacion marca "Add Python to PATH".
        echo.
        pause
        exit /b 1
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno local...
    %PY% -m venv .venv || goto :error
)

echo Instalando/actualizando dependencias...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt || goto :error

echo Iniciando Preview Beta v0.12...
call "%~dp0tools\START_PREVIEW_BETA.bat"

echo Abriendo NIKKE Mod Manager...
start "" ".venv\Scripts\pythonw.exe" app.py
exit /b 0

:error
echo.
echo [ERROR] No se pudo preparar la aplicacion.
echo Revisa el mensaje anterior y vuelve a ejecutar este archivo.
pause
exit /b 1
