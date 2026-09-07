@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title NIKKE Mod Manager v0.13 Classic

echo ===============================================
echo   NIKKE MOD MANAGER v0.13 CLASSIC
echo   Base: v0.11 Preview Alpha sin redisenar UI
echo ===============================================
echo.

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" update_from_v011.py
  goto end
)
where py >nul 2>&1
if not errorlevel 1 (
  py -3 update_from_v011.py
  goto end
)
where python >nul 2>&1
if not errorlevel 1 (
  python update_from_v011.py
  goto end
)

echo No encontre Python instalado.
echo Ejecuta primero INSTALAR_Y_ABRIR.bat de tu v0.11 y luego vuelve a probar.
pause

:end
endlocal
