@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title NIKKE Mod Manager v0.13 Classic R2

echo ================================================
echo      NIKKE MOD MANAGER v0.13 CLASSIC R2
echo      Reconstruccion Spine dentro de Alpha
echo ================================================
echo.

where py >nul 2>&1
if not errorlevel 1 (
  py -3 "%~dp0update_from_v011_r2.py"
  goto end
)
where python >nul 2>&1
if not errorlevel 1 (
  python "%~dp0update_from_v011_r2.py"
  goto end
)

echo No se encontro Python.
echo Ejecuta primero INSTALAR_Y_ABRIR.bat de tu v0.11 para instalar sus dependencias.
pause

:end
endlocal
