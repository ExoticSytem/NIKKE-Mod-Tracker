@echo off
setlocal
cd /d "%~dp0"
title NIKKE Mod Library - Instalador

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

echo Abriendo NIKKE Mod Library...
start "" ".venv\Scripts\pythonw.exe" app.py
exit /b 0

:error
echo.
echo [ERROR] No se pudo preparar la aplicacion.
echo Revisa el mensaje anterior y vuelve a ejecutar este archivo.
pause
exit /b 1
