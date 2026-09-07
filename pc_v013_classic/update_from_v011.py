from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

MARKER = 'NMM_CLASSIC_V013'
LAUNCH_MARKER = 'NMM_CLASSIC_LAUNCHER_V013'


def ask_folder(initial: Path) -> Path:
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
        selected = filedialog.askdirectory(
            title='Selecciona la carpeta LIMPIA de NIKKE Mod Manager v0.11 Preview Alpha',
            initialdir=str(initial)
        )
        root.destroy()
        if selected:
            return Path(selected)
    except Exception:
        pass
    return Path(input('Ruta de NIKKE Mod Manager v0.11: ').strip().strip('"'))


def looks_like_v011(root: Path) -> bool:
    if not root.is_dir():
        return False
    return (root / 'INSTALAR_Y_ABRIR.bat').exists() and any(root.rglob('*.html'))


def locate_manager() -> Path:
    here = Path(__file__).resolve().parent
    for c in (here, here.parent, Path.cwd(), Path.cwd().parent):
        try:
            if looks_like_v011(c):
                return c
        except Exception:
            pass
    return ask_folder(Path.cwd())


def clean_old_preview_injection(text: str) -> str:
    # Quita únicamente las inyecciones nuestras de Preview Beta/v0.13 anteriores.
    text = re.sub(
        r'\s*<script[^>]+src=["\']http://127\.0\.0\.1:8137/inject\.js["\'][^>]*></script>\s*<!--\s*NMT_PREVIEW_BETA_V012\s*-->\s*',
        '\n', text, flags=re.I
    )
    text = re.sub(
        r'\s*<script[^>]*data-nmm-classic-v013[^>]*>.*?</script>\s*<!--\s*NMM_CLASSIC_V013\s*-->\s*',
        '\n', text, flags=re.I | re.S
    )
    return text


def inject_html(root: Path, inject_js: str) -> int:
    changed = 0
    for p in root.rglob('*.html'):
        if any(part.lower() in {'node_modules','.git','.nikke_preview_beta_cache','.nikke_preview_native_cache'} for part in p.parts):
            continue
        try:
            text = p.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            try:
                text = p.read_text(encoding='utf-8-sig')
            except Exception:
                continue
        except Exception:
            continue

        # Si v0.12 había guardado el Alpha original, preferimos esa copia para no
        # heredar el iframe/Preview Beta antiguo.
        old_backup = p.with_suffix(p.suffix + '.v011.bak')
        if 'NMT_PREVIEW_BETA_V012' in text and old_backup.exists():
            try:
                text = old_backup.read_text(encoding='utf-8')
            except Exception:
                text = clean_old_preview_injection(text)
        else:
            text = clean_old_preview_injection(text)

        if '</body>' not in text.lower():
            continue
        pristine = p.with_suffix(p.suffix + '.v011_classic_backup')
        if not pristine.exists():
            try:
                shutil.copy2(p, pristine)
            except Exception:
                pass

        block = f'\n<script data-nmm-classic-v013>\n{inject_js}\n</script><!-- {MARKER} -->\n'
        idx = text.lower().rfind('</body>')
        new_text = text[:idx] + block + text[idx:]
        if new_text != p.read_text(encoding='utf-8', errors='ignore'):
            p.write_text(new_text, encoding='utf-8')
            changed += 1
    return changed


def copy_engine(package: Path, root: Path) -> None:
    tools = root / 'tools'
    tools.mkdir(parents=True, exist_ok=True)
    shutil.copy2(package / 'tools' / 'preview_classic_server.py', tools / 'preview_classic_server.py')


def write_preview_starter(root: Path) -> None:
    tools = root / 'tools'; tools.mkdir(parents=True, exist_ok=True)
    (tools / 'START_PREVIEW_CLASSIC_v013.bat').write_text(r'''@echo off
setlocal
cd /d "%~dp0.."

REM Si ya responde el motor, no abre otro.
powershell -NoProfile -Command "try { $r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 http://127.0.0.1:8137/health; if($r.StatusCode -eq 200){exit 0}else{exit 1} } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 exit /b 0

if exist ".venv\Scripts\pythonw.exe" (
  start "" /min ".venv\Scripts\pythonw.exe" "tools\preview_classic_server.py" --root "%CD%" --port 8137
  exit /b 0
)
if exist ".venv\Scripts\python.exe" (
  start "" /min ".venv\Scripts\python.exe" "tools\preview_classic_server.py" --root "%CD%" --port 8137
  exit /b 0
)
if exist "venv\Scripts\pythonw.exe" (
  start "" /min "venv\Scripts\pythonw.exe" "tools\preview_classic_server.py" --root "%CD%" --port 8137
  exit /b 0
)
if exist "venv\Scripts\python.exe" (
  start "" /min "venv\Scripts\python.exe" "tools\preview_classic_server.py" --root "%CD%" --port 8137
  exit /b 0
)
where pythonw >nul 2>&1 && (start "" /min pythonw "tools\preview_classic_server.py" --root "%CD%" --port 8137 & exit /b 0)
where python >nul 2>&1 && (start "" /min python "tools\preview_classic_server.py" --root "%CD%" --port 8137 & exit /b 0)
where py >nul 2>&1 && (start "" /min py -3 "tools\preview_classic_server.py" --root "%CD%" --port 8137 & exit /b 0)
exit /b 1
''', encoding='utf-8')


def wrap_launcher(root: Path) -> None:
    launcher = root / 'INSTALAR_Y_ABRIR.bat'
    original = root / 'INSTALAR_Y_ABRIR_v011_ORIGINAL.bat'
    if not launcher.exists():
        raise FileNotFoundError('Falta INSTALAR_Y_ABRIR.bat de v0.11')
    current = launcher.read_text(encoding='utf-8', errors='ignore')
    if LAUNCH_MARKER not in current:
        if not original.exists():
            shutil.copy2(launcher, original)
        launcher.write_text(r'''@echo off
REM NMM_CLASSIC_LAUNCHER_V013
setlocal
cd /d "%~dp0"
call "%~dp0tools\START_PREVIEW_CLASSIC_v013.bat"
call "%~dp0INSTALAR_Y_ABRIR_v011_ORIGINAL.bat"
''', encoding='utf-8')


def check_deps(root: Path) -> None:
    candidates = [root / '.venv' / 'Scripts' / 'python.exe', root / 'venv' / 'Scripts' / 'python.exe']
    py = next((p for p in candidates if p.exists()), Path(sys.executable))
    try:
        probe = subprocess.run([str(py), '-c', 'import UnityPy, PIL, cryptography'], capture_output=True, timeout=25)
        if probe.returncode == 0:
            return
        print('Instalando dependencias de preview...')
        subprocess.run([str(py), '-m', 'pip', 'install', '--disable-pip-version-check', 'UnityPy', 'Pillow', 'cryptography'], timeout=300, check=False)
    except Exception as exc:
        print('Aviso: no pude verificar dependencias:', exc)


def main() -> int:
    package = Path(__file__).resolve().parent
    root = locate_manager().resolve()
    if not looks_like_v011(root):
        print('\nLa carpeta seleccionada no parece ser NIKKE Mod Manager v0.11 Preview Alpha.')
        print(root)
        input('\nEnter para salir...')
        return 2

    inject_js = (package / 'inject_classic_v013.js').read_text(encoding='utf-8')
    copy_engine(package, root)
    write_preview_starter(root)
    html_count = inject_html(root, inject_js)
    wrap_launcher(root)
    check_deps(root)

    (root / 'VERSION_v0_13_CLASSIC.txt').write_text(
        'NIKKE Mod Manager v0.13 Classic\n'
        '- Interfaz v0.11 conservada.\n'
        '- Preview mejorado dentro del mismo modal Alpha: sin iframe ni ventana HTML separada.\n'
        '- Reparación en memoria de cabeceras Unity de 3DMigoto.\n'
        '- Demos de animación cuando existe Spine compatible.\n'
        '- Administración de imágenes oculta del Manager; queda para la app Admin.\n'
        '- Motor de preview usa cache temporal y se auto-cierra al cerrar el Manager.\n',
        encoding='utf-8'
    )
    print('\n===============================================')
    print(' NIKKE Mod Manager v0.13 Classic instalado')
    print('===============================================')
    print('Carpeta:', root)
    print('HTML actualizados:', html_count)
    print('\nSigue usando INSTALAR_Y_ABRIR.bat como siempre.')
    print('La interfaz exterior sigue siendo la de v0.11.')
    input('\nEnter para cerrar...')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
