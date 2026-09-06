from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

MARKER = "NMT_PREVIEW_BETA_V012"
SCRIPT_TAG = '<script src="http://127.0.0.1:8137/inject.js"></script><!-- NMT_PREVIEW_BETA_V012 -->'


def ask_folder(initial: Path) -> Path:
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
        selected = filedialog.askdirectory(title="Selecciona la carpeta de NIKKE Mod Manager v0.11", initialdir=str(initial))
        root.destroy()
        if selected:
            return Path(selected)
    except Exception:
        pass
    raw = input("Ruta de la carpeta de NIKKE Mod Manager v0.11: ").strip().strip('"')
    return Path(raw)


def looks_like_manager(root: Path) -> bool:
    if not root.is_dir():
        return False
    if (root / "INSTALAR_Y_ABRIR.bat").exists():
        return True
    names = {p.name.lower() for p in root.iterdir() if p.is_file()}
    return any("nikke" in n and n.endswith(".bat") for n in names)


def locate_manager() -> Path:
    here = Path(__file__).resolve().parent
    candidates = [here, here.parent, Path.cwd(), Path.cwd().parent]
    for c in candidates:
        try:
            if looks_like_manager(c):
                return c
        except Exception:
            pass
    return ask_folder(Path.cwd())


def inject_html(root: Path) -> int:
    count = 0
    for p in root.rglob("*.html"):
        if any(part.lower() in {"node_modules", ".git", ".nikke_preview_beta_cache"} for part in p.parts):
            continue
        try:
            txt = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                txt = p.read_text(encoding="utf-8-sig")
            except Exception:
                continue
        except Exception:
            continue
        if MARKER in txt:
            continue
        if "</body>" not in txt.lower():
            continue
        backup = p.with_suffix(p.suffix + ".v011.bak")
        if not backup.exists():
            shutil.copy2(p, backup)
        idx = txt.lower().rfind("</body>")
        txt = txt[:idx] + "\n" + SCRIPT_TAG + "\n" + txt[idx:]
        p.write_text(txt, encoding="utf-8")
        count += 1
    return count


def write_start_bat(root: Path) -> None:
    tools = root / "tools"
    tools.mkdir(parents=True, exist_ok=True)
    start = tools / "START_PREVIEW_BETA.bat"
    start.write_text(r'''@echo off
setlocal
cd /d "%~dp0.."
set "PREVIEW=%~dp0preview_beta_server.py"

REM Evita abrir dos servidores si ya está activo.
powershell -NoProfile -Command "try { $r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 http://127.0.0.1:8137/health; if($r.StatusCode -eq 200){exit 0}else{exit 1} } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 exit /b 0

if exist "%~dp0..\.venv\Scripts\pythonw.exe" (
  start "" /min "%~dp0..\.venv\Scripts\pythonw.exe" "%PREVIEW%" --root "%~dp0.."
  exit /b 0
)
if exist "%~dp0..\venv\Scripts\pythonw.exe" (
  start "" /min "%~dp0..\venv\Scripts\pythonw.exe" "%PREVIEW%" --root "%~dp0.."
  exit /b 0
)
if exist "%~dp0..\.venv\Scripts\python.exe" (
  start "" /min "%~dp0..\.venv\Scripts\python.exe" "%PREVIEW%" --root "%~dp0.."
  exit /b 0
)
if exist "%~dp0..\venv\Scripts\python.exe" (
  start "" /min "%~dp0..\venv\Scripts\python.exe" "%PREVIEW%" --root "%~dp0.."
  exit /b 0
)
where pythonw >nul 2>&1 && (start "" /min pythonw "%PREVIEW%" --root "%~dp0.." & exit /b 0)
where python >nul 2>&1 && (start "" /min python "%PREVIEW%" --root "%~dp0.." & exit /b 0)

echo No se encontro Python para iniciar Preview Beta.
exit /b 1
''', encoding="utf-8")

    launcher = root / "ABRIR_NIKKE_MOD_MANAGER_v0_12.bat"
    original = root / "INSTALAR_Y_ABRIR.bat"
    if original.exists():
        body = r'''@echo off
cd /d "%~dp0"
call "%~dp0tools\START_PREVIEW_BETA.bat"
timeout /t 1 /nobreak >nul
call "%~dp0INSTALAR_Y_ABRIR.bat"
'''
    else:
        bats = [p for p in root.glob("*.bat") if p.name.lower() != launcher.name.lower()]
        target = bats[0].name if bats else ""
        body = '@echo off\ncd /d "%~dp0"\ncall "%~dp0tools\\START_PREVIEW_BETA.bat"\ntimeout /t 1 /nobreak >nul\n'
        if target:
            body += f'call "%~dp0{target}"\n'
        else:
            body += 'echo Abre tu launcher habitual de NIKKE Mod Manager.\npause\n'
    launcher.write_text(body, encoding="utf-8")


def copy_payload(package_dir: Path, root: Path) -> None:
    src = package_dir / "preview_beta_server.py"
    if not src.exists():
        raise FileNotFoundError(f"Falta {src}")
    tools = root / "tools"
    tools.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, tools / "preview_beta_server.py")


def check_deps(root: Path) -> None:
    # No fuerza una instalación si v0.11 ya trae todo. Solo intenta completar dependencias
    # con el mismo Python que esté disponible.
    candidates = [
        root / ".venv" / "Scripts" / "python.exe",
        root / "venv" / "Scripts" / "python.exe",
    ]
    py = next((p for p in candidates if p.exists()), None)
    if py is None:
        py = Path(sys.executable)
    try:
        proc = subprocess.run([str(py), "-c", "import UnityPy, PIL, cryptography"], capture_output=True, timeout=20)
        if proc.returncode == 0:
            return
        print("Completando dependencias del preview (UnityPy, Pillow, cryptography)...")
        subprocess.run([str(py), "-m", "pip", "install", "--disable-pip-version-check", "UnityPy", "Pillow", "cryptography"], timeout=240)
    except Exception as exc:
        print("Aviso: no pude verificar/instalar dependencias automáticamente:", exc)
        print("Si el preview lo pide, vuelve a ejecutar INSTALAR_Y_ABRIR.bat de v0.11.")


def main() -> int:
    package_dir = Path(__file__).resolve().parent
    root = locate_manager().resolve()
    if not looks_like_manager(root):
        print("\nNo parece ser la carpeta de NIKKE Mod Manager v0.11:", root)
        print("Ejecuta de nuevo y selecciona la carpeta donde está INSTALAR_Y_ABRIR.bat.")
        input("Enter para salir...")
        return 2

    print("\nNIKKE Mod Manager v0.12 Preview Beta")
    print("Actualizando:", root)
    copy_payload(package_dir, root)
    html_count = inject_html(root)
    write_start_bat(root)
    check_deps(root)

    note = root / "PREVIEW_BETA_v0_12_INSTALADO.txt"
    note.write_text(
        "NIKKE Mod Manager v0.12 Preview Beta instalado.\n"
        "Usa ABRIR_NIKKE_MOD_MANAGER_v0_12.bat para iniciar el manager.\n"
        "El preview Alpha original se conserva como respaldo.\n"
        "En su ventana aparecerá el botón ▶ Preview Beta.\n",
        encoding="utf-8",
    )
    print(f"\nListo. HTML modificados: {html_count}")
    if html_count == 0:
        print("Aviso: no encontré HTML para inyectar automáticamente. El servidor Beta quedó instalado, pero puede que no aparezca el botón dentro de la interfaz.")
    print("A partir de ahora abre: ABRIR_NIKKE_MOD_MANAGER_v0_12.bat")
    try:
        subprocess.Popen([str(root / "tools" / "START_PREVIEW_BETA.bat")], cwd=str(root), shell=True)
    except Exception:
        pass
    input("\nEnter para cerrar este actualizador...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
