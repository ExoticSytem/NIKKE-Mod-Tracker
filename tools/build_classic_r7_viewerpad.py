from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R61_PATH = ROOT / 'tools' / 'build_classic_r6_1_startupfix.py'
spec = importlib.util.spec_from_file_location('classic_r61_builder', R61_PATH)
r61 = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(r61)
base = r61.base

base.OUT = base.DIST / 'NIKKE_Mod_Manager_v0_13_CLASSIC_R7_VIEWERPAD_FULL'
base.ZIP = base.DIST / 'NIKKE_Mod_Manager_v0_13_CLASSIC_R7_VIEWERPAD_FULL.zip'

base.PREVIEW_PY = base.PREVIEW_PY.replace('classic-r6-1-startupfix-001', 'classic-r7-viewerpad-001')
base.PREVIEW_PY = base.PREVIEW_PY.replace('classic_r6_1_spine_startupfix', 'classic_r7_viewerpad')
base.PREVIEW_PY = base.PREVIEW_PY.replace('Classic R6.1:', 'Classic R7:')
base.PREVIEW_PY = base.PREVIEW_PY.replace('Classic R6.1', 'Classic R7')
base.PREVIEW_PY = base.PREVIEW_PY.replace('Classic R6', 'Classic R7')

# The R6/R6.1 runtime reaches atlas parsing, but NIKKE atlases can reference
# regions that slightly exceed the decoded UnityPy image dimensions. Some viewers
# tolerate/pad this. Do the same: calculate atlas bounds and pad the PNG used by
# Spine, while keeping the normal fallback image untouched.
atlas_helper = r'''

def _atlas_required_size(text: str) -> tuple[int, int]:
    """Return minimum texture size needed by regions in a Spine .atlas file.

    Supports common Spine atlas keys: xy/size and bounds. Page-level size is
    also honored as a lower bound. If the atlas has trimmed or oversized packed
    regions, padding avoids PIXI's "frame does not fit inside base Texture" crash.
    """
    max_w = 0
    max_h = 0
    current_xy: tuple[int, int] | None = None
    seen_page_size = False
    for raw_line in (text or '').splitlines():
        line = raw_line.strip()
        if not line:
            current_xy = None
            seen_page_size = False
            continue
        lower = line.lower()
        nums = [int(x) for x in re.findall(r'-?\d+', line)]
        if lower.startswith('size:') and len(nums) >= 2:
            if current_xy is None and not seen_page_size:
                # page header size
                max_w = max(max_w, nums[0])
                max_h = max(max_h, nums[1])
                seen_page_size = True
            elif current_xy is not None:
                x, y = current_xy
                max_w = max(max_w, x + abs(nums[0]))
                max_h = max(max_h, y + abs(nums[1]))
            continue
        if lower.startswith('xy:') and len(nums) >= 2:
            current_xy = (max(0, nums[0]), max(0, nums[1]))
            continue
        if lower.startswith('bounds:') and len(nums) >= 4:
            x, y, w, h = nums[:4]
            max_w = max(max_w, max(0, x) + abs(w))
            max_h = max(max_h, max(0, y) + abs(h))
            current_xy = (max(0, x), max(0, y))
            continue
    return max_w, max_h
'''
marker = "def _score_asset(name: str, action: str) -> int:\n"
if atlas_helper not in base.PREVIEW_PY:
    if marker not in base.PREVIEW_PY:
        raise SystemExit('No encontre marcador para insertar _atlas_required_size')
    base.PREVIEW_PY = base.PREVIEW_PY.replace(marker, atlas_helper + '\n' + marker)

old = "atlas_text = _decode_atlas(atlas_payload)\n                    (asset_dir / 'model.atlas').write_text(atlas_text, encoding='utf-8', errors='replace')"
new = "atlas_text = _decode_atlas(atlas_payload)\n                    req_w, req_h = _atlas_required_size(atlas_text)\n                    if req_w > full_image.width or req_h > full_image.height:\n                        try:\n                            from PIL import Image as _PILImage\n                            padded_w = max(full_image.width, req_w)\n                            padded_h = max(full_image.height, req_h)\n                            padded = _PILImage.new('RGBA', (padded_w, padded_h), (0, 0, 0, 0))\n                            padded.paste(full_image, (0, 0))\n                            full_image = padded\n                            full_image.save(full_texture_path, format='PNG', optimize=True)\n                        except Exception:\n                            pass\n                    (asset_dir / 'model.atlas').write_text(atlas_text, encoding='utf-8', errors='replace')"
if old not in base.PREVIEW_PY:
    raise SystemExit('No encontre bloque atlas para aplicar padding R7')
base.PREVIEW_PY = base.PREVIEW_PY.replace(old, new)

# Add useful metadata if the web view prints debug info.
base.PREVIEW_PY = base.PREVIEW_PY.replace(
    "'texture_height': int(primary['height']),",
    "'texture_height': int(primary['height']),\n                    'spine_texture_padded_width': int(full_image.width),\n                    'spine_texture_padded_height': int(full_image.height),",
)

js = base.APP_JS_OVERRIDE
for a in ['Preview Alpha · Classic R6.1', 'Preview Alpha · Classic R6']:
    js = js.replace(a, 'Preview Alpha · Classic R7')
for a in ['Classic R6.1 Spine render failed', 'Classic R6 Spine render failed']:
    js = js.replace(a, 'Classic R7 Spine render failed')
js = js.replace('Classic R6.1', 'Classic R7').replace('Classic R6', 'Classic R7')
js = js.replace('DEBUG R6', 'DEBUG R7')
js = js.replace('Debug runtime R6.1', 'Debug runtime R7').replace('Debug runtime R6', 'Debug runtime R7')
base.APP_JS_OVERRIDE = js + '\n/* Classic R7 viewerpad atlas texture padding */\n'


def write_zip_r7() -> None:
    base.OUT.joinpath('VERSION.txt').write_text(
        'NIKKE Mod Manager v0.13 Classic R7 ViewerPad FULL\n'
        'Base real: v0.11 Preview Alpha\n'
        'Instalacion: descomprimir y ejecutar INSTALAR_Y_ABRIR.bat\n'
        'Cambio principal: aplica enfoque tipo viewer: rellena la textura usada por Spine cuando el atlas referencia regiones fuera del PNG exportado, evitando el error frame does not fit.\n',
        encoding='utf-8',
    )
    base.OUT.joinpath('LEEME_PRIMERO.txt').write_text(
        'NIKKE Mod Manager v0.13 Classic R7 ViewerPad FULL\n\n'
        'Descomprime esta carpeta en un lugar nuevo y ejecuta INSTALAR_Y_ABRIR.bat.\n'
        'Mantiene la interfaz clasica de v0.11. Esta revision conserva el runtime Spine low-level y agrega padding de textura basado en atlas, como hacen viewers que toleran regiones fuera del tamano PNG.\n'
        'Si falla, manda la linea DEBUG R7 completa.\n'
        'Los 3DMigoto quedan para una revision posterior.\n',
        encoding='utf-8',
    )
    for rel in ['app.py', 'README.md', 'PREVIEW_NOTES.md', 'INSTALAR_Y_ABRIR.bat', 'ABRIR.bat', 'web/app.js', 'web/index.html', 'src/preview.py']:
        p = base.OUT / rel
        if p.exists():
            s = p.read_text(encoding='utf-8', errors='ignore')
            s = s.replace('0.13 Classic R6.1 Spine StartupFix', '0.13 Classic R7 ViewerPad')
            s = s.replace('0.13 Classic R6 Spine LowLevel', '0.13 Classic R7 ViewerPad')
            s = s.replace('Classic R6.1', 'Classic R7').replace('Classic R6', 'Classic R7')
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

base.write_zip = write_zip_r7

if __name__ == '__main__':
    base.main()
