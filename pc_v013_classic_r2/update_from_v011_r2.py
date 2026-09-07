from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

MARKER = 'NMM_CLASSIC_R2'
LAUNCH_MARKER = 'NMM_CLASSIC_LAUNCHER_R2'
PORT = 8138
LOCAL_FILES = (
    'nmm_pixi_v6.min.js',
    'nmm_pixi_spine_v4.js',
    'nmm_classic_r2.js',
)


def ask_folder(initial: Path) -> Path:
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
        selected = filedialog.askdirectory(
            title='Selecciona NIKKE Mod Manager v0.11 Preview Alpha',
            initialdir=str(initial),
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


def restore_best_base(html: Path) -> str:
    # Si ya se instaló una prueba anterior, recuperamos primero el HTML original
    # de v0.11. Así R2 no se monta encima del panel grande de la v0.13 anterior.
    candidates = [
        html.with_suffix(html.suffix + '.v011_classic_backup'),
        html.with_suffix(html.suffix + '.v011.bak'),
    ]
    for p in candidates:
        if p.exists():
            try:
                return p.read_text(encoding='utf-8')
            except Exception:
                pass
    try:
        return html.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return html.read_text(encoding='utf-8-sig')


def clean_our_injections(text: str) -> str:
    # Preview Beta v0.12 externo.
    text = re.sub(
        r'\s*<script[^>]+src=["\']http://127\.0\.0\.1:8137/inject\.js["\'][^>]*></script>\s*<!--\s*NMT_PREVIEW_BETA_V012\s*-->\s*',
        '\n', text, flags=re.I,
    )
    # Classic v0.13 inline anterior.
    text = re.sub(
        r'\s*<script[^>]*data-nmm-classic-v013[^>]*>.*?</script>\s*<!--\s*NMM_CLASSIC_V013\s*-->\s*',
        '\n', text, flags=re.I | re.S,
    )
    # R2 anterior, para poder reinstalar limpiamente.
    text = re.sub(
        r'\s*<!--\s*NMM_CLASSIC_R2_BEGIN\s*-->.*?<!--\s*NMM_CLASSIC_R2_END\s*-->\s*',
        '\n', text, flags=re.I | re.S,
    )
    return text


def add_tokens(value: str, *tokens: str) -> str:
    parts = value.split()
    existing = set(parts)
    for token in tokens:
        if token not in existing:
            parts.append(token); existing.add(token)
    return ' '.join(parts)


def patch_csp_content(content: str) -> str:
    directives = []
    by_name = {}
    for raw in content.split(';'):
        raw = raw.strip()
        if not raw:
            continue
        parts = raw.split()
        name = parts[0].lower()
        item = [parts[0], parts[1:]]
        directives.append(item)
        by_name[name] = item

    def ensure(name: str, *tokens: str):
        item = by_name.get(name)
        if item is None:
            item = [name, []]
            directives.append(item); by_name[name] = item
        current = item[1]
        for token in tokens:
            if token not in current:
                current.append(token)

    local = f'http://127.0.0.1:{PORT}'
    ensure('script-src', "'self'")
    ensure('connect-src', "'self'", local)
    ensure('img-src', "'self'", 'data:', 'blob:', local)
    ensure('style-src', "'self'", "'unsafe-inline'")
    return '; '.join(' '.join([name] + vals) for name, vals in directives) + ';'


def patch_csp(text: str) -> str:
    meta_re = re.compile(r'<meta\b[^>]*http-equiv\s*=\s*(["\'])Content-Security-Policy\1[^>]*>', re.I)

    def repl(match):
        tag = match.group(0)
        cm = re.search(r'content\s*=\s*(["\'])(.*?)\1', tag, re.I | re.S)
        if not cm:
            return tag
        quote = cm.group(1)
        new_content = patch_csp_content(cm.group(2))
        return tag[:cm.start()] + f'content={quote}{new_content}{quote}' + tag[cm.end():]

    return meta_re.sub(repl, text)


def inject_html(root: Path, package: Path) -> int:
    changed = 0
    js_src = package / 'inject_classic_r2.js'
    vendor = package / 'vendor'

    for html in root.rglob('*.html'):
        if any(part.lower() in {
            'node_modules', '.git', '.nikke_preview_beta_cache', '.nikke_preview_native_cache'
        } for part in html.parts):
            continue
        try:
            text = restore_best_base(html)
        except Exception:
            continue
        if '</body>' not in text.lower():
            continue

        pristine = html.with_suffix(html.suffix + '.v011_classic_backup')
        if not pristine.exists():
            try:
                shutil.copy2(html, pristine)
            except Exception:
                pass

        text = clean_our_injections(text)
        text = patch_csp(text)

        target_dir = html.parent
        shutil.copy2(vendor / 'pixi.min.js', target_dir / 'nmm_pixi_v6.min.js')
        shutil.copy2(vendor / 'pixi-spine.umd.js', target_dir / 'nmm_pixi_spine_v4.js')
        shutil.copy2(js_src, target_dir / 'nmm_classic_r2.js')

        block = (
            '\n<!-- NMM_CLASSIC_R2_BEGIN -->\n'
            '<script src="nmm_pixi_v6.min.js"></script>\n'
            '<script src="nmm_pixi_spine_v4.js"></script>\n'
            '<script src="nmm_classic_r2.js"></script>\n'
            '<!-- NMM_CLASSIC_R2_END -->\n'
        )
        idx = text.lower().rfind('</body>')
        new_text = text[:idx] + block + text[idx:]
        old_text = html.read_text(encoding='utf-8', errors='ignore')
        if new_text != old_text:
            html.write_text(new_text, encoding='utf-8')
            changed += 1
    return changed


def copy_engine(package: Path, root: Path) -> None:
    tools = root / 'tools'; tools.mkdir(parents=True, exist_ok=True)
    shutil.copy2(package / 'tools' / 'preview_classic_r2_server.py', tools / 'preview_classic_r2_server.py')


def write_starter(root: Path) -> None:
    tools = root / 'tools'; tools.mkdir(parents=True, exist_ok=True)
    (tools / 'START_PREVIEW_CLASSIC_R2.bat').write_text(r'''@echo off
setlocal
cd /d "%~dp0.."

powershell -NoProfile -Command "try { $r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 http://127.0.0.1:8138/health; if($r.StatusCode -eq 200){exit 0}else{exit 1} } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 exit /b 0

if exist ".venv\Scripts\pythonw.exe" (
  start "" /min ".venv\Scripts\pythonw.exe" "tools\preview_classic_r2_server.py" --root "%CD%" --port 8138
  exit /b 0
)
if exist ".venv\Scripts\python.exe" (
  start "" /min ".venv\Scripts\python.exe" "tools\preview_classic_r2_server.py" --root "%CD%" --port 8138
  exit /b 0
)
if exist "venv\Scripts\pythonw.exe" (
  start "" /min "venv\Scripts\pythonw.exe" "tools\preview_classic_r2_server.py" --root "%CD%" --port 8138
  exit /b 0
)
if exist "venv\Scripts\python.exe" (
  start "" /min "venv\Scripts\python.exe" "tools\preview_classic_r2_server.py" --root "%CD%" --port 8138
  exit /b 0
)
where pythonw >nul 2>&1 && (start "" /min pythonw "%CD%\tools\preview_classic_r2_server.py" --root "%CD%" --port 8138 & exit /b 0)
where python >nul 2>&1 && (start "" /min python "%CD%\tools\preview_classic_r2_server.py" --root "%CD%" --port 8138 & exit /b 0)
where py >nul 2>&1 && (start "" /min py -3 "%CD%\tools\preview_classic_r2_server.py" --root "%CD%" --port 8138 & exit /b 0)
exit /b 1
''', encoding='utf-8')


def wrap_launcher(root: Path) -> None:
    launcher = root / 'INSTALAR_Y_ABRIR.bat'
    original = root / 'INSTALAR_Y_ABRIR_v011_ORIGINAL.bat'
    if not launcher.exists():
        raise FileNotFoundError('Falta INSTALAR_Y_ABRIR.bat')

    current = launcher.read_text(encoding='utf-8', errors='ignore')
    if original.exists():
        # Ya hubo una actualización anterior: esa copia es nuestra mejor base v0.11.
        base = original.read_text(encoding='utf-8', errors='ignore')
    else:
        base = current
        shutil.copy2(launcher, original)

    # Si por cualquier motivo la copia quedó siendo un wrapper nuestro, intenta
    # recuperar el launcher más antiguo disponible.
    if 'NMM_CLASSIC_LAUNCHER_V013' in base or LAUNCH_MARKER in base:
        for candidate in root.glob('INSTALAR_Y_ABRIR*.bak'):
            try:
                txt = candidate.read_text(encoding='utf-8', errors='ignore')
                if 'NMM_CLASSIC_' not in txt:
                    base = txt; original.write_text(base, encoding='utf-8'); break
            except Exception:
                pass

    launcher.write_text(r'''@echo off
REM NMM_CLASSIC_LAUNCHER_R2
setlocal
cd /d "%~dp0"
call "%~dp0tools\START_PREVIEW_CLASSIC_R2.bat"
call "%~dp0INSTALAR_Y_ABRIR_v011_ORIGINAL.bat"
''', encoding='utf-8')


def check_deps(root: Path) -> None:
    candidates = [
        root / '.venv' / 'Scripts' / 'python.exe',
        root / 'venv' / 'Scripts' / 'python.exe',
    ]
    py = next((p for p in candidates if p.exists()), Path(sys.executable))
    try:
        probe = subprocess.run([str(py), '-c', 'import UnityPy, PIL, cryptography'], capture_output=True, timeout=25)
        if probe.returncode == 0:
            return
        print('Instalando dependencias del preview Spine...')
        subprocess.run([
            str(py), '-m', 'pip', 'install', '--disable-pip-version-check',
            'UnityPy', 'Pillow', 'cryptography'
        ], timeout=300, check=False)
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

    copy_engine(package, root)
    write_starter(root)
    count = inject_html(root, package)
    wrap_launcher(root)
    check_deps(root)

    (root / 'VERSION_v0_13_CLASSIC_R2.txt').write_text(
        'NIKKE Mod Manager v0.13 Classic R2\n'
        '- Conserva la interfaz original v0.11.\n'
        '- Los mods normales intentan reconstruirse como Spine dentro del MISMO Preview Alpha.\n'
        '- No abre iframe, viewer ni pagina HTML separada.\n'
        '- La textura Alpha original sigue disponible como respaldo.\n'
        '- 3DMigoto se deja sin cambios en esta revisión; se trabajara después.\n'
        '- El motor auxiliar se auto-cierra al desaparecer el Manager.\n',
        encoding='utf-8',
    )

    print('\n================================================')
    print(' NIKKE Mod Manager v0.13 Classic R2 instalado')
    print('================================================')
    print('Carpeta:', root)
    print('HTML actualizados:', count)
    print('\nAbre INSTALAR_Y_ABRIR.bat como siempre.')
    print('Prueba primero un mod NORMAL como Summer Anis.')
    input('\nEnter para cerrar...')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
