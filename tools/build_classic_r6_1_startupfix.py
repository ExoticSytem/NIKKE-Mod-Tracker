from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R6_PATH = ROOT / 'tools' / 'build_classic_r6_lowlevel.py'
spec = importlib.util.spec_from_file_location('classic_r6_builder', R6_PATH)
r6 = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(r6)
base = r6.base

base.OUT = base.DIST / 'NIKKE_Mod_Manager_v0_13_CLASSIC_R6_1_SPINE_STARTUPFIX_FULL'
base.ZIP = base.DIST / 'NIKKE_Mod_Manager_v0_13_CLASSIC_R6_1_SPINE_STARTUPFIX_FULL.zip'
base.PREVIEW_PY = base.PREVIEW_PY.replace('classic-r6-lowlevel-002', 'classic-r6-1-startupfix-001')
base.PREVIEW_PY = base.PREVIEW_PY.replace('classic_r6_spine_lowlevel', 'classic_r6_1_spine_startupfix')
base.PREVIEW_PY = base.PREVIEW_PY.replace('Classic R6:', 'Classic R6.1:')
base.PREVIEW_PY = base.PREVIEW_PY.replace('Classic R6', 'Classic R6.1')

js = base.APP_JS_OVERRIDE
js = js.replace('Preview Alpha · Classic R6', 'Preview Alpha · Classic R6.1')
js = js.replace('Classic R6 Spine render failed', 'Classic R6.1 Spine render failed')
js = js.replace('Classic R6', 'Classic R6.1')

# R6 broke the whole app because the generated web/app.js had this inside a
# single-quoted JS string: typeof r6RuntimeInfo==='function'. Escape those two
# inner quotes so the catalog can load before any preview is opened.
js = js.replace(
    "onclick=\"alert((typeof r6RuntimeInfo==='function'?r6RuntimeInfo():r5RuntimeInfo()).summary)\"",
    "onclick=\"alert((typeof r6RuntimeInfo===\\'function\\'?r6RuntimeInfo():r5RuntimeInfo()).summary)\"",
)

base.APP_JS_OVERRIDE = js + '\n/* Classic R6.1 startup syntax guard */\n'


def write_zip_r61() -> None:
    base.OUT.joinpath('VERSION.txt').write_text(
        'NIKKE Mod Manager v0.13 Classic R6.1 Spine StartupFix FULL\n'
        'Base real: v0.11 Preview Alpha\n'
        'Instalacion: descomprimir y ejecutar INSTALAR_Y_ABRIR.bat\n'
        'Cambio principal: corrige el JS que impedia cargar personajes al inicio y conserva el runtime Spine low-level de R6.\n',
        encoding='utf-8',
    )
    base.OUT.joinpath('LEEME_PRIMERO.txt').write_text(
        'NIKKE Mod Manager v0.13 Classic R6.1 Spine StartupFix FULL\n\n'
        'Descomprime esta carpeta en un lugar nuevo y ejecuta INSTALAR_Y_ABRIR.bat.\n'
        'Mantiene la interfaz clasica de v0.11. Esta revision corrige el error de sintaxis de R6 que hacia que no cargaran los personajes al abrir.\n'
        'El Preview Alpha sigue intentando armar mods normales con Spine low-level; textura queda como fallback.\n'
        'Los 3DMigoto quedan para una revision posterior.\n',
        encoding='utf-8',
    )
    for rel in ['app.py', 'README.md', 'PREVIEW_NOTES.md', 'INSTALAR_Y_ABRIR.bat', 'ABRIR.bat', 'web/app.js', 'web/index.html', 'src/preview.py']:
        p = base.OUT / rel
        if p.exists():
            s = p.read_text(encoding='utf-8', errors='ignore')
            s = s.replace('0.13 Classic R6 Spine LowLevel', '0.13 Classic R6.1 Spine StartupFix')
            s = s.replace('Classic R6', 'Classic R6.1')
            p.write_text(s, encoding='utf-8')
    if base.ZIP.exists():
        base.ZIP.unlink()
    with zipfile.ZipFile(base.ZIP, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for p in base.OUT.rglob('*'):
            z.write(p, p.relative_to(base.DIST))
    with zipfile.ZipFile(base.ZIP) as z:
        bad = z.testzip()
        if bad:
            raise RuntimeError(f'Zip corrupto en {bad}')
    print(f'OK {base.ZIP} {base.ZIP.stat().st_size} bytes')

base.write_zip = write_zip_r61

if __name__ == '__main__':
    base.main()
