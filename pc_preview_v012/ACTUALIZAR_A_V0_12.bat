@echo off
setlocal
cd /d "%~dp0"
title NIKKE Mod Manager v0.12 Preview Beta - Actualizador

echo =======================================================
echo   NIKKE Mod Manager v0.12 - Preview Beta
echo =======================================================
echo.
echo Este actualizador se aplica sobre tu carpeta v0.11.
echo Conserva el Preview Alpha como respaldo y agrega Preview Beta.
echo.

where py >nul 2>&1 && (py -3 "%~dp0update_to_v012.py" & goto :end)
where python >nul 2>&1 && (python "%~dp0update_to_v012.py" & goto :end)

echo No encontre Python en PATH.
echo Primero ejecuta INSTALAR_Y_ABRIR.bat de NIKKE Mod Manager v0.11.
pause

:end
endlocal
