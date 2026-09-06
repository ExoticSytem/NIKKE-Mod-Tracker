from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist" / "NIKKE_Mod_Manager_v0_13_FULL"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"No se encontró marcador para {label}")
    return text.replace(old, new, 1)


def patch_manager(src: str) -> str:
    src = src.replace('APP_VERSION = "0.12 Preview Beta FULL"', 'APP_VERSION = "0.13 Repair + Animated Demo"')
    src = src.replace('Preview Beta · v0.12', 'Preview animado · v0.13')
    # El gestor de usuario solo consume las imágenes del catálogo. La edición/subida
    # de imágenes queda reservada para la aplicación Admin independiente.
    return src


def patch_manager_server(src: str) -> str:
    src = src.replace('NIKKE-Mod-Manager/0.12', 'NIKKE-Mod-Manager/0.13')
    src = src.replace('NIKKE Mod Manager v0.12', 'NIKKE Mod Manager v0.13')
    src = src.replace('MOD MANAGER · v0.12 PREVIEW BETA', 'MOD MANAGER · v0.13 REPAIR + DEMO')
    src = src.replace('"version": "0.12"', '"version": "0.13"')
    # No se añade ningún endpoint para cambiar imágenes: son solo lectura en el
    # Mod Manager y se administrarán desde NIKKE Admin Manager.
    return src


def patch_preview(src: str) -> str:
    src = src.replace('v0.12', 'v0.13')
    src = src.replace('NIKKEPreviewBeta/0.12', 'NIKKEPreviewBeta/0.13')
    src = src.replace('"version": "0.12"', '"version": "0.13"')

    # Fuerza cache nueva: evita reutilizar manifests de v0.12 donde 3DMigoto
    # quedó clasificado como una simple textura/atlas.
    src = replace_once(
        src,
        'raw = f"{path.resolve()}|{st.st_size}|{st.st_mtime_ns}".encode("utf-8", "ignore")',
        'raw = f"v013|{path.resolve()}|{st.st_size}|{st.st_mtime_ns}".encode("utf-8", "ignore")',
        'salt de cache v0.13',
    )

    repair_helpers = r'''

def repair_unity_version(payload: bytes) -> Tuple[bytes, bool, str]:
    """Repara solo en memoria cabeceras UnityFS con version corrupta.

    Algunos mods 3DMigoto de la colección conservan un Unity bundle válido pero
    tienen dañados los 11 bytes de la cadena de versión del header. UnityPy corta
    antes de leer los assets con "Invalid version string". No tocamos el mod del
    usuario: se crea una copia de bytes únicamente para el parser.
    """
    if not payload.startswith((b"UnityFS\x00", b"UnityRaw\x00", b"UnityWeb\x00")):
        return payload, False, ""
    sig_end = payload.find(b"\x00", 0, 16)
    if sig_end < 0:
        return payload, False, ""
    pos = sig_end + 1 + 4  # uint32 format tras la firma
    if pos >= len(payload):
        return payload, False, ""
    end = payload.find(b"\x00", pos, min(len(payload), pos + 64))
    if end < 0:
        return payload, False, ""
    raw_version = payload[pos:end]
    try:
        version = raw_version.decode("ascii")
    except Exception:
        version = ""
    if re.fullmatch(r"\d{4}\.\d+\.\d+[abfp]\d+", version or ""):
        return payload, False, version

    # Los casos defectuosos reportados usan exactamente el hueco de 11 bytes que
    # en los bundles sanos contiene 2021.3.36f1. Mantener el largo evita desplazar
    # el resto de la cabecera UnityFS.
    replacements = [b"2021.3.36f1", b"2021.3.48f1", b"2020.3.48f1"]
    replacement = next((x for x in replacements if len(x) == len(raw_version)), None)
    if replacement is None:
        return payload, False, raw_version.hex()
    fixed = bytearray(payload)
    fixed[pos:end] = replacement
    return bytes(fixed), True, raw_version.hex()


def extract_3dmigoto_unity(path: Path, outdir: Path) -> Dict[str, Any]:
    """Fallback para 3DMigoto que realmente es un Unity bundle.

    Primero v0.13 intenta reconstruir Spine. Si no hay .skel/.atlas suficientes,
    esta ruta al menos extrae Texture2D embebidas (incluyendo bundles cuyo header
    debió repararse) y las marca explícitamente como vista técnica.
    """
    try:
        import UnityPy
    except Exception as exc:
        raise RuntimeError("Falta UnityPy para leer el bundle 3DMigoto.") from exc

    info = parse_mod_name(path)
    temp_root = outdir / "_work_3dmigoto"
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
                raise ValueError("Unity bundle leído, pero no contiene Texture2D utilizables")
            found.sort(key=lambda x: x[2], reverse=True)
            images: List[Dict[str, Any]] = []
            for idx, (source_name, image, area) in enumerate(found[:16]):
                if getattr(image, "mode", "") not in ("RGBA", "RGB"):
                    image = image.convert("RGBA")
                name = f"unity_texture_{idx:02d}.png"
                image.save(outdir / name, "PNG")
                images.append({
                    "name": name,
                    "sourceName": source_name,
                    "width": image.width,
                    "height": image.height,
                    "area": area,
                })
            return {
                "type": "3dmigoto",
                "source": str(path),
                "id": info.get("id", ""),
                "ver": info.get("ver", ""),
                "action": info.get("action", "").lower(),
                "rest": info.get("rest", ""),
                "images": images,
                "metadataFiles": [],
                "unityVersionRepaired": repaired,
                "unityVersionOriginal": original_version,
                "bundleKind": bundle_kind,
                "technicalFallback": True,
                "note": "No se pudo ensamblar el personaje con Spine. Se muestran Texture2D embebidas como respaldo técnico; no se consideran una vista previa final.",
            }
        except Exception as exc:
            errors.append(f"{candidate.name}: {exc}")

    raise RuntimeError("No pude extraer Texture2D del 3DMigoto. " + " | ".join(errors[-5:]))

'''
    src = replace_once(src, '\ndef extract_spine(path: Path, outdir: Path) -> Dict[str, Any]:\n', repair_helpers + '\ndef extract_spine(path: Path, outdir: Path) -> Dict[str, Any]:\n', 'helpers de reparación')

    src = replace_once(
        src,
        '            env = UnityPy.load(io.BytesIO(payload))',
        '            payload, repaired, original_version = repair_unity_version(payload)\n            env = UnityPy.load(io.BytesIO(payload))',
        'carga Unity reparada',
    )
    src = replace_once(
        src,
        '                "textures": saved_textures,\n            }',
        '                "textures": saved_textures,\n                "unityVersionRepaired": repaired,\n                "unityVersionOriginal": original_version,\n            }',
        'metadatos reparación Spine',
    )

    old_prepare = '''    if is_3dmigoto(path):\n        data = extract_3dmigoto(path, outdir)\n    else:\n        data = extract_spine(path, outdir)'''
    new_prepare = '''    if is_3dmigoto(path):\n        spine_error = ""\n        try:\n            data = extract_spine(path, outdir)\n            data["sourceType"] = "3dmigoto-unity-spine"\n            data["note"] = "3DMigoto reconstruido como Spine/Unity por v0.13."\n        except Exception as exc:\n            spine_error = str(exc)\n            try:\n                data = extract_3dmigoto_unity(path, outdir)\n            except Exception as unity_exc:\n                data = extract_3dmigoto(path, outdir)\n                data["unityFallbackError"] = str(unity_exc)\n            data["spineError"] = spine_error\n    else:\n        data = extract_spine(path, outdir)'''
    src = replace_once(src, old_prepare, new_prepare, 'routing 3DMigoto')

    src = src.replace(
        '"note": "3DMigoto detectado. Esta beta ya evita tratarlo como Unity bundle y muestra sus texturas; el ensamblado 3D queda para una siguiente iteración.",',
        '"technicalFallback": True,\n        "note": "Vista técnica de respaldo: no fue posible reconstruir Spine/Unity. Se muestran solo archivos de textura directamente legibles.",',
    )

    old_footer = '<footer><button id="play">⏸ Pausa</button><select id="anim"></select><label class="pill"><input id="loop" type="checkbox" checked> Loop</label><button id="reset">↺ Reset</button><button id="minus">−</button><button id="plus">+</button><span class="pill" id="meta">—</span>'
    new_footer = '<footer><button id="play">⏸ Pausa</button><select id="anim"></select><label class="pill"><input id="loop" type="checkbox" checked> Loop</label><button id="demoIdle">🎬 Demo Idle</button><button id="demoAction">🎬 Demo Acción</button><button id="demoAuto">🎬 Demo Auto</button><button id="reset">↺ Reset</button><button id="minus">−</button><button id="plus">+</button><span class="pill" id="meta">—</span>'
    src = replace_once(src, old_footer, new_footer, 'controles demo')
    src = replace_once(src, 'let app=null,model=null,baseScale=1,paused=false;', 'let app=null,model=null,baseScale=1,paused=false,demoTimer=null,demoIndex=0;', 'estado demo')

    demo_js = r'''
function stopDemo(){if(demoTimer){clearInterval(demoTimer);demoTimer=null;}const b=$('#demoAuto');if(b)b.textContent='🎬 Demo Auto';}
function animationNames(){return [...$('#anim').options].map(o=>o.value).filter(Boolean);}
function playHint(hints){if(!model)return;stopDemo();const names=animationNames();let chosen='';for(const h of hints){chosen=names.find(n=>n.toLowerCase()===h)||names.find(n=>n.toLowerCase().includes(h));if(chosen)break;}chosen=chosen||names[0]||'';if(!chosen)return;$('#anim').value=chosen;$('#loop').checked=true;model.state.setAnimation(0,chosen,true);}
function demoStep(){if(!model)return;const names=animationNames();if(!names.length)return;const n=names[demoIndex%names.length];demoIndex++;$('#anim').value=n;model.state.setAnimation(0,n,false);}
function toggleAutoDemo(){if(!model)return;if(demoTimer){stopDemo();return;}demoIndex=0;demoStep();demoTimer=setInterval(demoStep,4200);$('#demoAuto').textContent='■ Detener Demo';}
$('#demoIdle').onclick=()=>playHint(['idle','normal_idle','standing','wait']);
$('#demoAction').onclick=()=>playHint(['burst','skill','attack','shoot','aim','cover']);
$('#demoAuto').onclick=toggleAutoDemo;
'''
    src = replace_once(src, '(async()=>{{try{{const r=await fetch(', demo_js + '\n(async()=>{{try{{const r=await fetch(', 'javascript demos')

    src = src.replace(
        "$('#play').disabled=true;$('#anim').disabled=true;",
        "$('#play').disabled=true;$('#anim').disabled=true;$('#demoIdle').disabled=true;$('#demoAction').disabled=true;$('#demoAuto').disabled=true;",
    )
    src = src.replace(
        "sel.onchange=()=>model.state.setAnimation(0,sel.value,$('#loop').checked);",
        "sel.onchange=()=>{stopDemo();model.state.setAnimation(0,sel.value,$('#loop').checked);};",
    )
    src = src.replace(
        "$('#meta').textContent='Spine '+m.spineVersion+' · '+(m.action||'')+' · '+m.bundleKind;",
        "$('#meta').textContent='Spine '+m.spineVersion+' · '+(m.action||'')+' · '+m.bundleKind+(m.unityVersionRepaired?' · Unity reparado':'');",
    )

    return src


def build() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "tools").mkdir(parents=True, exist_ok=True)
    (OUT / "catalog").mkdir(parents=True, exist_ok=True)

    manager = (ROOT / "pc_full_v012" / "manager.py").read_text(encoding="utf-8")
    (OUT / "manager.py").write_text(patch_manager(manager), encoding="utf-8")

    server = (ROOT / "pc_full_v012" / "manager_server.py").read_text(encoding="utf-8")
    (OUT / "manager_server.py").write_text(patch_manager_server(server), encoding="utf-8")

    preview = (ROOT / "pc_preview_v012" / "preview_beta_server.py").read_text(encoding="utf-8")
    (OUT / "tools" / "preview_beta_server.py").write_text(patch_preview(preview), encoding="utf-8")

    catalog = ROOT / "catalog" / "base_catalog.json"
    if catalog.exists():
        shutil.copy2(catalog, OUT / "catalog" / "base_catalog.json")

    installer = r'''@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title NIKKE Mod Manager v0.13

echo ===============================================
echo        NIKKE MOD MANAGER v0.13
echo        3DMigoto Repair + Animated Demo
echo ===============================================
echo.

set "PY="
if exist ".venv\Scripts\python.exe" set "PY=%CD%\.venv\Scripts\python.exe"
if defined PY goto deps
where py >nul 2>&1
if not errorlevel 1 (
  py -3.12 -c "import sys" >nul 2>&1
  if not errorlevel 1 (py -3.12 -m venv .venv & set "PY=%CD%\.venv\Scripts\python.exe" & goto deps)
  py -3 -c "import sys" >nul 2>&1
  if not errorlevel 1 (py -3 -m venv .venv & set "PY=%CD%\.venv\Scripts\python.exe" & goto deps)
)
where python >nul 2>&1
if not errorlevel 1 (python -m venv .venv & if exist ".venv\Scripts\python.exe" set "PY=%CD%\.venv\Scripts\python.exe")
if not defined PY (
  echo No se encontro Python 3. Instala Python 3.11 o 3.12 y marca Add Python to PATH.
  pause
  exit /b 1
)
:deps
echo Verificando dependencias...
"%PY%" -c "import UnityPy, PIL, cryptography, send2trash" >nul 2>&1
if errorlevel 1 (
  "%PY%" -m pip install --disable-pip-version-check --upgrade pip >nul
  "%PY%" -m pip install --disable-pip-version-check UnityPy Pillow cryptography send2trash
  if errorlevel 1 (echo No se pudieron instalar las dependencias. & pause & exit /b 1)
)
if not exist "tools\preview_beta_server.py" (echo Falta tools\preview_beta_server.py & pause & exit /b 1)
if not exist "manager.py" (echo Falta manager.py & pause & exit /b 1)
set "PYW=%CD%\.venv\Scripts\pythonw.exe"
if exist "%PYW%" (start "NIKKE Mod Manager" "%PYW%" "%CD%\manager.py") else (start "NIKKE Mod Manager" "%PY%" "%CD%\manager.py")
exit /b 0
'''
    (OUT / "INSTALAR_Y_ABRIR.bat").write_text(installer, encoding="utf-8", newline="\r\n")

    readme = '''NIKKE MOD MANAGER v0.13 - FULL\n\nNovedades principales\n--------------------\n- Nuevo intento de reconstrucción animada para mods 3DMigoto que internamente son Unity/Spine.\n- Reparación EN MEMORIA de la cadena UnityFS dañada que provoca "Invalid version string"; nunca modifica el mod original.\n- Si no existe un set Spine utilizable, intenta extraer Texture2D embebidas antes de caer al respaldo técnico.\n- El mosaico de assets queda marcado como respaldo técnico y ya no se presenta como preview final.\n- Demos animados: Demo Idle, Demo Acción y Demo Auto para recorrer animaciones del personaje.\n- Cache v0.13 independiente para no reutilizar previews defectuosos de v0.12.\n- Nombre unificado: NIKKE Mod Manager.\n- La gestión/subida de imágenes de personajes se elimina del Mod Manager. Las imágenes del catálogo son de solo lectura y se administrarán desde la app Admin separada.\n\nPrueba recomendada\n------------------\n1. Descomprime el ZIP en una carpeta nueva.\n2. Ejecuta INSTALAR_Y_ABRIR.bat.\n3. Prueba primero Crown Glorious Flower, D: Killer Wife y Milk Blooming Bunny 3DMigoto.\n4. Si el mod contiene Spine compatible, el preview intentará mostrar el personaje montado y animado.\n5. Usa Demo Idle / Demo Acción / Demo Auto para probar sus animaciones.\n\nNota\n----\nEl reparador trabaja sobre una copia de bytes en memoria. No reescribe ni altera tus archivos de mods.\n'''
    (OUT / "README.txt").write_text(readme, encoding="utf-8")

    # Validación sintáctica rápida sin importar dependencias opcionales.
    compile((OUT / "manager.py").read_text(encoding="utf-8"), "manager.py", "exec")
    compile((OUT / "manager_server.py").read_text(encoding="utf-8"), "manager_server.py", "exec")
    compile((OUT / "tools" / "preview_beta_server.py").read_text(encoding="utf-8"), "preview_beta_server.py", "exec")
    print(f"Built: {OUT}")


if __name__ == "__main__":
    build()
