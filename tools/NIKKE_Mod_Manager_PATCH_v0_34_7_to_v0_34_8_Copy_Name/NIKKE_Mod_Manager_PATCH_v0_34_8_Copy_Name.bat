@echo off
setlocal
set "PATCHPY=%TEMP%\NIKKE_Mod_Manager_v0_34_8_patch.py"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -UseBasicParsing 'https://raw.githubusercontent.com/ExoticSytem/NIKKE-Mod-Tracker/manager-v0-34-8-copy-name/tools/NIKKE_Mod_Manager_PATCH_v0_34_7_to_v0_34_8_Copy_Name/patch.py' -OutFile '%PATCHPY%'"
if errorlevel 1 (
  echo ERROR: no se pudo descargar el parche.
  pause
  exit /b 1
)
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "%PATCHPY%"
) else (
  python "%PATCHPY%"
)
del /q "%PATCHPY%" >nul 2>nul
endlocal
