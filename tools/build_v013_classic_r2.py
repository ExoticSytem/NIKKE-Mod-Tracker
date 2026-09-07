from __future__ import annotations

import shutil
from pathlib import Path

import build_v013_classic as old

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'pc_preview_v012' / 'preview_beta_server.py'
PKG = ROOT / 'dist' / 'NIKKE_Mod_Manager_v0_13_CLASSIC_R2_UPDATE'
R2 = ROOT / 'pc_v013_classic_r2'
VENDOR = R2 / 'vendor'


def patch_server_r2(src: str) -> str:
    text = old.patch_server(src)
    text = text.replace('v0.13 Classic', 'v0.13 Classic R2')
    text = text.replace('"version": "0.13-classic"', '"version": "0.13-classic-r2"')
    text = text.replace('NIKKE_Mod_Manager_v013_preview_cache', 'NIKKE_Mod_Manager_v013_r2_preview_cache')

    old_route = '''    if is_3dmigoto(path):\n        spine_error = ""\n        try:\n            data = extract_spine(path, outdir)\n            data["sourceType"] = "3dmigoto-spine"\n        except Exception as exc:\n            spine_error = str(exc)\n            try:\n                data = extract_unity_textures(path, outdir)\n            except Exception as unity_exc:\n                data = extract_3dmigoto(path, outdir)\n                data["unityFallbackError"] = str(unity_exc)\n                data["technicalFallback"] = True\n                data["note"] = "No se pudo reconstruir el personaje. Se muestra una sola textura legible como respaldo, no un mosaico de assets."\n            data["spineError"] = spine_error\n    else:\n        data = extract_spine(path, outdir)'''
    new_route = '''    if is_3dmigoto(path):\n        raise RuntimeError("Classic R2 se concentra en mods normales. 3DMigoto se trabajará después.")\n    data = extract_spine(path, outdir)'''
    if old_route not in text:
        raise RuntimeError('No se encontró routing Classic anterior')
    text = text.replace(old_route, new_route, 1)

    # La R2 no usa ni expone una interfaz viewer. Mantiene únicamente API/asset.
    old_inject = '''            if u.path == "/inject.js":\n                self._send(inject_js().encode("utf-8"), "application/javascript; charset=utf-8")\n                return\n            if u.path == "/viewer":\n                p = q.get("path", [""])[0]\n                self._send(viewer_html(p).encode("utf-8"), "text/html; charset=utf-8")\n                return\n'''
    if old_inject in text:
        text = text.replace(old_inject, '', 1)

    return text


def build() -> None:
    if PKG.exists():
        shutil.rmtree(PKG)
    (PKG / 'tools').mkdir(parents=True, exist_ok=True)
    (PKG / 'vendor').mkdir(parents=True, exist_ok=True)

    server = patch_server_r2(SRC.read_text(encoding='utf-8'))
    (PKG / 'tools' / 'preview_classic_r2_server.py').write_text(server, encoding='utf-8')

    shutil.copy2(R2 / 'inject_classic_r2.js', PKG / 'inject_classic_r2.js')
    shutil.copy2(R2 / 'update_from_v011_r2.py', PKG / 'update_from_v011_r2.py')
    shutil.copy2(R2 / 'INSTALAR_ACTUALIZACION_v0_13_R2.bat', PKG / 'INSTALAR_ACTUALIZACION_v0_13_R2.bat')
    shutil.copy2(R2 / 'README.txt', PKG / 'README.txt')

    for name in ('pixi.min.js', 'pixi-spine.umd.js'):
        src = VENDOR / name
        if not src.exists() or src.stat().st_size < 10000:
            raise RuntimeError(f'Falta runtime vendor válido: {src}')
        shutil.copy2(src, PKG / 'vendor' / name)


if __name__ == '__main__':
    build()
