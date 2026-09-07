from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'pc_preview_v012' / 'preview_beta_server.py'
PKG = ROOT / 'dist' / 'NIKKE_Mod_Manager_v0_13_CLASSIC_UPDATE'


def one(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f'No se encontró marcador: {label}')
    return text.replace(old, new, 1)


REPAIR_HELPERS = r'''

def repair_unity_version(payload: bytes) -> Tuple[bytes, bool, str]:
    """Repara en memoria la cadena de versión UnityFS dañada en algunos 3DMigoto.
    Nunca escribe sobre el mod del usuario.
    """
    if not payload.startswith((b"UnityFS\x00", b"UnityRaw\x00", b"UnityWeb\x00")):
        return payload, False, ""
    sig_end = payload.find(b"\x00", 0, 16)
    if sig_end < 0:
        return payload, False, ""
    pos = sig_end + 1 + 4
    if pos >= len(payload):
        return payload, False, ""
    end = payload.find(b"\x00", pos, min(len(payload), pos + 64))
    if end < 0:
        return payload, False, ""
    raw = payload[pos:end]
    try:
        version = raw.decode("ascii")
    except Exception:
        version = ""
    if re.fullmatch(r"\d{4}\.\d+\.\d+[abfp]\d+", version or ""):
        return payload, False, version
    for candidate in (b"2021.3.36f1", b"2021.3.48f1", b"2020.3.48f1"):
        if len(candidate) == len(raw):
            fixed = bytearray(payload)
            fixed[pos:end] = candidate
            return bytes(fixed), True, raw.hex()
    return payload, False, raw.hex()


def extract_unity_textures(path: Path, outdir: Path) -> Dict[str, Any]:
    """Extrae Texture2D embebidas cuando no existe un set Spine completo."""
    try:
        import UnityPy
    except Exception as exc:
        raise RuntimeError("Falta UnityPy para leer este 3DMigoto.") from exc

    info = parse_mod_name(path)
    temp_root = outdir / "_work_unity_textures"
    temp_root.mkdir(parents=True, exist_ok=True)
    errors: List[str] = []

    for candidate in _candidate_files(path, temp_root):
        try:
            if candidate.stat().st_size < 256:
                continue
            raw = candidate.read_bytes()
            payload, bundle_kind = decrypt_nkab(raw)
            payload, repaired, original_version = repair_unity_version(payload)
            env = UnityPy.load(io.BytesIO(payload))
            found: List[Tuple[str, Any, int]] = []
            for idx, obj in enumerate(env.objects):
                typ = getattr(getattr(obj, "type", None), "name", str(getattr(obj, "type", "")))
                if typ != "Texture2D":
                    continue
                try:
                    data = obj.read()
                    image = data.image
                    if image is None:
                        continue
                    name = _asset_name(data, f"texture_{idx}")
                    area = int(getattr(image, "width", 0) * getattr(image, "height", 0))
                    if area > 0:
                        found.append((name, image.copy(), area))
                except Exception:
                    continue
            if not found:
                raise ValueError("Bundle leído, pero no contiene Texture2D utilizables")
            found.sort(key=lambda x: x[2], reverse=True)
            images: List[Dict[str, Any]] = []
            for idx, (source_name, image, area) in enumerate(found[:16]):
                if getattr(image, "mode", "") not in ("RGBA", "RGB"):
                    image = image.convert("RGBA")
                name = f"unity_texture_{idx:02d}.png"
                image.save(outdir / name, "PNG")
                images.append({"name": name, "sourceName": source_name, "width": image.width, "height": image.height, "area": area})
            return {
                "type": "3dmigoto",
                "source": str(path),
                "id": info.get("id", ""),
                "ver": info.get("ver", ""),
                "action": info.get("action", "").lower(),
                "rest": info.get("rest", ""),
                "images": images,
                "metadataFiles": [],
                "bundleKind": bundle_kind,
                "unityVersionRepaired": repaired,
                "unityVersionOriginal": original_version,
                "technicalFallback": True,
                "note": "No había un set Spine completo; se muestra la mejor textura embebida como respaldo estático.",
            }
        except Exception as exc:
            errors.append(f"{candidate.name}: {exc}")
    raise RuntimeError("No pude extraer Texture2D del 3DMigoto. " + " | ".join(errors[-5:]))

'''


def patch_server(src: str) -> str:
    src = src.replace('v0.12', 'v0.13 Classic')
    src = src.replace('"version": "0.12"', '"version": "0.13-classic"')
    src = one(src, '\ndef extract_spine(path: Path, outdir: Path) -> Dict[str, Any]:\n', REPAIR_HELPERS + '\ndef extract_spine(path: Path, outdir: Path) -> Dict[str, Any]:\n', 'repair helpers')
    src = one(src,
        '            env = UnityPy.load(io.BytesIO(payload))',
        '            payload, unity_repaired, unity_original_version = repair_unity_version(payload)\n            env = UnityPy.load(io.BytesIO(payload))',
        'UnityPy repaired load')
    src = one(src,
        '                "textures": saved_textures,\n            }',
        '                "textures": saved_textures,\n                "unityVersionRepaired": unity_repaired,\n                "unityVersionOriginal": unity_original_version,\n            }',
        'repair metadata')

    old_prepare = '''    if is_3dmigoto(path):\n        data = extract_3dmigoto(path, outdir)\n    else:\n        data = extract_spine(path, outdir)'''
    new_prepare = '''    if is_3dmigoto(path):\n        spine_error = ""\n        try:\n            data = extract_spine(path, outdir)\n            data["sourceType"] = "3dmigoto-spine"\n        except Exception as exc:\n            spine_error = str(exc)\n            try:\n                data = extract_unity_textures(path, outdir)\n            except Exception as unity_exc:\n                data = extract_3dmigoto(path, outdir)\n                data["unityFallbackError"] = str(unity_exc)\n                data["technicalFallback"] = True\n                data["note"] = "No se pudo reconstruir el personaje. Se muestra una sola textura legible como respaldo, no un mosaico de assets."\n            data["spineError"] = spine_error\n    else:\n        data = extract_spine(path, outdir)'''
    src = one(src, old_prepare, new_prepare, '3DMigoto routing')

    # Cache fuera de la carpeta de la app: evita que un proceso residual impida borrarla.
    src = src.replace('CACHE_ROOT = APP_ROOT / ".nikke_preview_beta_cache"', 'CACHE_ROOT = Path(tempfile.gettempdir()) / "NIKKE_Mod_Manager_v013_preview_cache"')

    old_handler_head = 'class Handler(BaseHTTPRequestHandler):'
    src = one(src, old_handler_head, 'LAST_HEARTBEAT = time.time()\nHAD_HEARTBEAT = False\nHTTPD_REF = None\n\n\n' + old_handler_head, 'heartbeat globals')

    health = '''            if u.path == "/health":\n                self._send(_json_bytes({"ok": True, "version": "0.13-classic"}), "application/json; charset=utf-8")\n                return'''
    if health not in src:
        # version replacement may leave another exact literal; normalize the block.
        src = re.sub(r'            if u\.path == "/health":\n                self\._send\(_json_bytes\(\{"ok": True, "version": "[^"]+"\}\), "application/json; charset=utf-8"\)\n                return', health, src, count=1)

    heartbeat_block = '''            if u.path == "/api/heartbeat":\n                global LAST_HEARTBEAT, HAD_HEARTBEAT\n                LAST_HEARTBEAT = time.time()\n                HAD_HEARTBEAT = True\n                self._send(_json_bytes({"ok": True}), "application/json; charset=utf-8")\n                return\n'''
    src = one(src, '            if u.path == "/inject.js":\n', heartbeat_block + '            if u.path == "/inject.js":\n', 'heartbeat endpoint')

    old_main = '''    APP_ROOT = Path(ns.root).resolve()\n    CACHE_ROOT = APP_ROOT / ".nikke_preview_beta_cache"\n    CACHE_ROOT.mkdir(parents=True, exist_ok=True)\n    PORT = ns.port\n    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)\n    print(f"NIKKE Preview Beta v0.13 Classic: http://127.0.0.1:{PORT}")\n    httpd.serve_forever()'''
    if old_main not in src:
        old_main = '''    APP_ROOT = Path(ns.root).resolve()\n    CACHE_ROOT = Path(tempfile.gettempdir()) / "NIKKE_Mod_Manager_v013_preview_cache"\n    CACHE_ROOT.mkdir(parents=True, exist_ok=True)\n    PORT = ns.port\n    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)\n    print(f"NIKKE Preview Beta v0.13 Classic: http://127.0.0.1:{PORT}")\n    httpd.serve_forever()'''
    new_main = '''    global HTTPD_REF\n    APP_ROOT = Path(ns.root).resolve()\n    CACHE_ROOT = Path(tempfile.gettempdir()) / "NIKKE_Mod_Manager_v013_preview_cache"\n    CACHE_ROOT.mkdir(parents=True, exist_ok=True)\n    try:\n        os.chdir(tempfile.gettempdir())\n    except Exception:\n        pass\n    PORT = ns.port\n    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)\n    HTTPD_REF = httpd\n\n    def watchdog():\n        started = time.time()\n        while True:\n            time.sleep(1.0)\n            if HAD_HEARTBEAT and time.time() - LAST_HEARTBEAT > 4.0:\n                try:\n                    httpd.shutdown()\n                except Exception:\n                    pass\n                return\n            if not HAD_HEARTBEAT and time.time() - started > 45.0:\n                try:\n                    httpd.shutdown()\n                except Exception:\n                    pass\n                return\n    threading.Thread(target=watchdog, daemon=True).start()\n    print(f"NIKKE Preview Classic v0.13: http://127.0.0.1:{PORT}")\n    httpd.serve_forever()'''
    if old_main not in src:
        raise RuntimeError('No se encontró main del servidor')
    src = src.replace(old_main, new_main, 1)
    return src


def build():
    if PKG.exists():
        shutil.rmtree(PKG)
    (PKG / 'tools').mkdir(parents=True, exist_ok=True)
    server = patch_server(SRC.read_text(encoding='utf-8'))
    (PKG / 'tools' / 'preview_classic_server.py').write_text(server, encoding='utf-8')
    shutil.copy2(ROOT / 'pc_v013_classic' / 'inject_classic_v013.js', PKG / 'inject_classic_v013.js')
    shutil.copy2(ROOT / 'pc_v013_classic' / 'update_from_v011.py', PKG / 'update_from_v011.py')
    shutil.copy2(ROOT / 'pc_v013_classic' / 'INSTALAR_ACTUALIZACION_v0_13.bat', PKG / 'INSTALAR_ACTUALIZACION_v0_13.bat')
    shutil.copy2(ROOT / 'pc_v013_classic' / 'README.txt', PKG / 'README.txt')


if __name__ == '__main__':
    build()
