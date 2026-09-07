@echo off
setlocal
cd /d "%~dp0.."
set "PREVIEW=%~dp0preview_beta_server.py"

REM Si el servidor Beta ya responde, no abre otra copia.
powershell -NoProfile -Command "try { $r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 http://127.0.0.1:8137/health; if($r.StatusCode -eq 200){exit 0}else{exit 1} } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 exit /b 0

if exist "%~dp0..\.venv\Scripts\pythonw.exe" (
  start "" /min "%~dp0..\.venv\Scripts\pythonw.exe" "%PREVIEW%" --root "%~dp0.."
  exit /b 0
)
if exist "%~dp0..\.venv\Scripts\python.exe" (
  start "" /min "%~dp0..\.venv\Scripts\python.exe" "%PREVIEW%" --root "%~dp0.."
  exit /b 0
)
where pythonw >nul 2>&1 && (start "" /min pythonw "%PREVIEW%" --root "%~dp0.." & exit /b 0)
where python >nul 2>&1 && (start "" /min python "%PREVIEW%" --root "%~dp0.." & exit /b 0)

echo No se encontro Python para iniciar Preview Beta.
exit /b 1
