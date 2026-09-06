from __future__ import annotations

import argparse
import base64
import hashlib
import html
import io
import json
import mimetypes
import os
import re
import shutil
import struct
import sys
import tempfile
import threading
import time
import traceback
import urllib.parse
import zipfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

PORT = 8137
APP_ROOT = Path.cwd()
CACHE_ROOT = APP_ROOT / ".nikke_preview_beta_cache"
CACHE_ROOT.mkdir(parents=True, exist_ok=True)

MOD_RE = re.compile(r"c(?P<id>\d{3,4})_(?P<ver>\d{2})_(?P<action>standing|aim|cover)(?:_(?P<rest>.*))?$", re.I)
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tga", ".dds", ".webp"}
SKIP_BINARY_EXTS = IMAGE_EXTS | {".ini", ".txt", ".json", ".log", ".cfg", ".md", ".py", ".dll", ".exe", ".bat", ".ps1", ".url"}


def _safe_name(name: str, fallback: str) -> str:
    name = name.replace("\\", "_").replace("/", "_").strip()
    name = re.sub(r"[^0-9A-Za-z._()\- ]+", "_", name)
    return name[:180] or fallback


def _json_bytes(data: Any) -> bytes:
    return json.dumps(data, ensure_ascii=False).encode("utf-8")


def _file_signature(path: Path) -> str:
    try:
        st = path.stat()
        raw = f"{path.resolve()}|{st.st_size}|{st.st_mtime_ns}".encode("utf-8", "ignore")
    except Exception:
        raw = str(path).encode("utf-8", "ignore")
    return hashlib.sha1(raw).hexdigest()[:18]


def parse_mod_name(path: Path) -> Dict[str, str]:
    m = MOD_RE.search(path.name)
    if not m:
        return {"id": "", "ver": "", "action": "", "rest": ""}
    return {k: (v or "") for k, v in m.groupdict().items()}


def find_related(path: Path) -> Dict[str, str]:
    info = parse_mod_name(path)
    if not info["id"] or not info["ver"]:
        return {}
    parent = path.parent
    try:
        entries = list(parent.iterdir())
    except Exception:
        return {}
    desired_rest = info.get("rest", "").lower()
    buckets: Dict[str, List[Tuple[int, Path]]] = {"standing": [], "aim": [], "cover": []}
    for p in entries:
        mi = parse_mod_name(p)
        act = mi.get("action", "").lower()
        if mi.get("id") != info["id"] or mi.get("ver") != info["ver"] or act not in buckets:
            continue
        score = 0
        rest = mi.get("rest", "").lower()
        if desired_rest and rest == desired_rest:
            score += 100
        if p.name.lower() == path.name.lower():
            score += 200
        buckets[act].append((score, p))
    out: Dict[str, str] = {}
    for act, values in buckets.items():
        if values:
            values.sort(key=lambda x: (-x[0], x[1].name.lower()))
            out[act] = str(values[0][1])
    return out


def is_3dmigoto(path: Path) -> bool:
    if "3dmigoto" in path.name.lower():
        return True
    targets: Iterable[Path]
    if path.is_dir():
        try:
            targets = path.rglob("*")
        except Exception:
            targets = []
    else:
        targets = [path]
    checked = 0
    for p in targets:
        if checked > 600:
            break
        checked += 1
        if not p.is_file():
            continue
        s = p.suffix.lower()
        n = p.name.lower()
        if s == ".ini":
            try:
                txt = p.read_text(encoding="utf-8", errors="ignore")[:20000].lower()
            except Exception:
                txt = ""
            if any(x in txt for x in ("[textureoverride", "[shaderoverride", "vb0", "ib =", "drawindexed")):
                return True
        if s in {".buf", ".ib", ".vb"} or n.endswith(".buf"):
            return True
    return False


def decrypt_nkab(raw: bytes) -> Tuple[bytes, str]:
    if raw[:4] != b"NKAB":
        return raw, "Unity bundle"
    if len(raw) < 24:
        raise ValueError("NKAB demasiado corto")
    version = struct.unpack_from("<I", raw, 4)[0]
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    except Exception as exc:
        raise RuntimeError("Falta 'cryptography'. Ejecuta INSTALAR_Y_ABRIR.bat de v0.11 primero.") from exc

    def aes_cbc(data: bytes, key: bytes, iv: bytes) -> bytes:
        dec = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
        return dec.update(data) + dec.finalize()

    if version == 1:
        pos = 8
        header_size, enc_mode, key_len, enc_len = struct.unpack_from("<hhhh", raw, pos)
        pos += 8
        header_size += 100
        enc_mode += 100
        key_len += 100
        enc_len += 100
        if key_len <= 0 or enc_len <= 0 or pos + key_len * 2 + enc_len > len(raw):
            raise ValueError("Cabecera NKAB v1 inválida")
        key = raw[pos:pos + key_len]
        pos += key_len
        iv = raw[pos:pos + key_len]
        pos += key_len
        import hashlib as _hashlib
        key_hash = _hashlib.sha256(key).digest()
        encrypted = raw[pos:pos + enc_len]
        pos += enc_len
        return aes_cbc(encrypted, key_hash, iv) + raw[pos:], "NKAB v1"

    if version == 2:
        if len(raw) < 48:
            raise ValueError("NKAB v2 demasiado corto")
        key = raw[-32:]
        obf = struct.unpack_from("<h", key, 0)[0]
        pos = 8
        header_size, enc_mode, key_len, enc_len = struct.unpack_from("<hhhh", raw, pos)
        pos += 8
        header_size += obf
        enc_mode += obf
        key_len += obf
        enc_len += obf
        iv = raw[pos:pos + 16]
        pos += 16
        if enc_len <= 0 or pos + enc_len > len(raw) - 32:
            raise ValueError("Cabecera NKAB v2 inválida")
        encrypted = raw[pos:pos + enc_len]
        pos += enc_len
        remainder = raw[pos:-32]
        return aes_cbc(encrypted, key, iv) + remainder, "NKAB v2"

    raise ValueError(f"Versión NKAB no soportada: {version}")


def _read_varint(data: bytes, pos: int) -> Tuple[int, int]:
    value = 0
    shift = 0
    for _ in range(5):
        if pos >= len(data):
            raise ValueError("EOF")
        b = data[pos]
        pos += 1
        value |= (b & 0x7F) << shift
        if (b & 0x80) == 0:
            return value, pos
        shift += 7
    raise ValueError("varint inválido")


def _read_spine_string(data: bytes, pos: int) -> Tuple[str, int]:
    ln, pos = _read_varint(data, pos)
    if ln == 0:
        return "", pos
    if ln == 1:
        return "", pos
    ln -= 1
    if pos + ln > len(data):
        raise ValueError("string fuera de rango")
    return data[pos:pos + ln].decode("utf-8", errors="ignore"), pos + ln


def detect_spine_version(data: bytes) -> str:
    # Spine 4.x binary places two int32 hashes before the version string.
    for mode in ("new", "old"):
        try:
            pos = 8 if mode == "new" else 0
            if mode == "old":
                _, pos = _read_spine_string(data, pos)
            version, _ = _read_spine_string(data, pos)
            m = re.search(r"(?:^|[^0-9])(3\.\d+(?:\.\d+)?|4\.\d+(?:\.\d+)?)", version)
            if m:
                return m.group(1)
        except Exception:
            pass
    # Fallback: versions are often visible as ASCII near the beginning.
    head = data[:256].decode("latin1", errors="ignore")
    m = re.search(r"(4\.[01](?:\.\d+)?|3\.8(?:\.\d+)?)", head)
    return m.group(1) if m else "desconocida"


def _textasset_bytes(asset: Any) -> bytes:
    for attr in ("m_Script", "script"):
        if hasattr(asset, attr):
            val = getattr(asset, attr)
            if isinstance(val, bytes):
                return val
            if isinstance(val, bytearray):
                return bytes(val)
            if isinstance(val, str):
                return val.encode("utf-8")
    return b""


def _asset_name(asset: Any, fallback: str = "asset") -> str:
    for attr in ("m_Name", "name"):
        val = getattr(asset, attr, None)
        if val:
            return str(val)
    return fallback


def _score_named(name: str, wanted_action: str, wanted_id: str, kind: str) -> int:
    low = name.lower()
    score = 0
    if wanted_action and wanted_action in low:
        score += 30
    if wanted_id and f"c{wanted_id}" in low:
        score += 20
    if kind in low:
        score += 10
    return score


def _atlas_page_names(text: str) -> List[str]:
    out: List[str] = []
    for raw in text.replace("\r", "").split("\n"):
        line = raw.strip()
        if re.search(r"\.(?:png|jpg|jpeg|webp|tga|bmp)$", line, re.I):
            if line not in out:
                out.append(line)
    return out


def _candidate_files(path: Path, temp_root: Path) -> List[Path]:
    if path.is_dir():
        result = []
        for p in path.rglob("*"):
            if p.is_file() and p.suffix.lower() not in SKIP_BINARY_EXTS:
                result.append(p)
        return sorted(result, key=lambda p: p.stat().st_size if p.exists() else 0, reverse=True)
    if path.suffix.lower() == ".zip":
        target = temp_root / "zip"
        target.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path) as z:
            for member in z.infolist():
                dest = (target / member.filename).resolve()
                if not str(dest).startswith(str(target.resolve())):
                    continue
                if member.is_dir():
                    dest.mkdir(parents=True, exist_ok=True)
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(member) as src, open(dest, "wb") as dst:
                        shutil.copyfileobj(src, dst)
        return _candidate_files(target, temp_root)
    return [path]


def extract_spine(path: Path, outdir: Path) -> Dict[str, Any]:
    try:
        import UnityPy
    except Exception as exc:
        raise RuntimeError("Falta UnityPy. Ejecuta INSTALAR_Y_ABRIR.bat de v0.11 primero.") from exc

    info = parse_mod_name(path)
    temp_root = outdir / "_work"
    temp_root.mkdir(parents=True, exist_ok=True)
    errors: List[str] = []

    for candidate in _candidate_files(path, temp_root):
        try:
            if candidate.stat().st_size < 256:
                continue
            raw = candidate.read_bytes()
            payload, bundle_kind = decrypt_nkab(raw)
            if not (payload.startswith(b"UnityFS") or payload.startswith(b"UnityRaw") or payload.startswith(b"UnityWeb")):
                # UnityPy may still support a few nonstandard bundles, so try anyway.
                pass
            env = UnityPy.load(io.BytesIO(payload))
            text_assets: List[Tuple[str, bytes]] = []
            textures: List[Tuple[str, Any, int]] = []
            for idx, obj in enumerate(env.objects):
                typ = getattr(getattr(obj, "type", None), "name", str(getattr(obj, "type", "")))
                try:
                    data = obj.read()
                except Exception:
                    continue
                if typ == "TextAsset":
                    name = _asset_name(data, f"text_{idx}")
                    script = _textasset_bytes(data)
                    if script:
                        text_assets.append((name, script))
                elif typ == "Texture2D":
                    try:
                        image = data.image
                        if image is None:
                            continue
                        name = _asset_name(data, f"texture_{idx}")
                        area = int(getattr(image, "width", 0) * getattr(image, "height", 0))
                        textures.append((name, image.copy(), area))
                    except Exception:
                        continue

            atlases = [(n, b) for n, b in text_assets if ".atlas" in n.lower() or b"format:" in b[:3000].lower()]
            skels = [(n, b) for n, b in text_assets if ".skel" in n.lower()]
            if not atlases or not skels or not textures:
                raise ValueError(f"Bundle leído, pero faltan assets Spine (atlas={len(atlases)}, skel={len(skels)}, texturas={len(textures)})")

            atlases.sort(key=lambda x: _score_named(x[0], info.get("action", ""), info.get("id", ""), "atlas"), reverse=True)
            skels.sort(key=lambda x: _score_named(x[0], info.get("action", ""), info.get("id", ""), "skel"), reverse=True)
            atlas_name, atlas_bytes = atlases[0]
            skel_name, skel_bytes = skels[0]
            try:
                atlas_text = atlas_bytes.decode("utf-8")
            except UnicodeDecodeError:
                atlas_text = atlas_bytes.decode("utf-8-sig", errors="replace")

            # Save canonical files so the browser loader has predictable URLs.
            (outdir / "model.atlas").write_text(atlas_text, encoding="utf-8")
            (outdir / "model.skel").write_bytes(skel_bytes)

            saved_textures: List[Dict[str, Any]] = []
            by_name: Dict[str, Tuple[str, Any, int]] = {}
            for item in textures:
                by_name[item[0].lower()] = item
                by_name[Path(item[0]).stem.lower()] = item

            page_names = _atlas_page_names(atlas_text)
            used = set()
            textures_sorted = sorted(textures, key=lambda x: x[2], reverse=True)
            for idx, page in enumerate(page_names):
                page_path = Path(page)
                lookup = page.lower()
                lookup_stem = page_path.stem.lower()
                item = by_name.get(lookup) or by_name.get(lookup_stem)
                if item is None:
                    remaining = [t for t in textures_sorted if t[0] not in used]
                    item = remaining[0] if remaining else textures_sorted[min(idx, len(textures_sorted) - 1)]
                used.add(item[0])
                safe_page = _safe_name(page_path.name, f"page_{idx}.png")
                if not Path(safe_page).suffix:
                    safe_page += ".png"
                target = outdir / safe_page
                img = item[1]
                if getattr(img, "mode", "") not in ("RGBA", "RGB"):
                    img = img.convert("RGBA")
                img.save(target, "PNG")
                if safe_page != page_path.name:
                    atlas_text = atlas_text.replace(page, safe_page)
                saved_textures.append({"name": safe_page, "width": img.width, "height": img.height, "area": img.width * img.height})

            # If atlas parser found no explicit page name, expose the largest texture and rewrite a best-effort first line.
            if not saved_textures:
                item = textures_sorted[0]
                img = item[1].convert("RGBA") if getattr(item[1], "mode", "") not in ("RGBA", "RGB") else item[1]
                target = outdir / "model.png"
                img.save(target, "PNG")
                saved_textures.append({"name": "model.png", "width": img.width, "height": img.height, "area": img.width * img.height})

            (outdir / "model.atlas").write_text(atlas_text, encoding="utf-8")

            return {
                "type": "spine",
                "source": str(path),
                "bundleFile": str(candidate),
                "bundleKind": bundle_kind,
                "spineVersion": detect_spine_version(skel_bytes),
                "id": info.get("id", ""),
                "ver": info.get("ver", ""),
                "action": info.get("action", "").lower(),
                "rest": info.get("rest", ""),
                "atlasAsset": atlas_name,
                "skelAsset": skel_name,
                "atlas": "model.atlas",
                "skel": "model.skel",
                "textures": saved_textures,
            }
        except Exception as exc:
            errors.append(f"{candidate.name}: {exc}")
            continue

    detail = " | ".join(errors[-5:]) if errors else "no se encontraron bundles candidatos"
    raise RuntimeError(f"No pude extraer un set Spine compatible. {detail}")


def extract_3dmigoto(path: Path, outdir: Path) -> Dict[str, Any]:
    try:
        from PIL import Image
    except Exception as exc:
        raise RuntimeError("Falta Pillow/PIL para previsualizar texturas 3DMigoto.") from exc

    files: List[Path] = []
    if path.is_dir():
        files = [p for p in path.rglob("*") if p.is_file()]
    else:
        files = [path]
    images: List[Dict[str, Any]] = []
    metadata_files: List[str] = []
    for p in files:
        if p.suffix.lower() == ".ini" or p.suffix.lower() in {".buf", ".ib", ".vb"}:
            metadata_files.append(p.name)
        if p.suffix.lower() not in IMAGE_EXTS:
            continue
        try:
            with Image.open(p) as im:
                rgba = im.convert("RGBA")
                name = f"texture_{len(images):02d}.png"
                rgba.save(outdir / name, "PNG")
                images.append({"name": name, "sourceName": p.name, "width": rgba.width, "height": rgba.height, "area": rgba.width * rgba.height})
        except Exception:
            continue
    images.sort(key=lambda x: x["area"], reverse=True)
    info = parse_mod_name(path)
    return {
        "type": "3dmigoto",
        "source": str(path),
        "id": info.get("id", ""),
        "ver": info.get("ver", ""),
        "action": info.get("action", "").lower(),
        "rest": info.get("rest", ""),
        "images": images[:12],
        "metadataFiles": metadata_files[:60],
        "note": "3DMigoto detectado. Esta beta ya evita tratarlo como Unity bundle y muestra sus texturas; el ensamblado 3D queda para una siguiente iteración.",
    }


def prepare(path_text: str) -> Tuple[str, Dict[str, Any]]:
    path = Path(path_text.strip().strip('"'))
    if not path.exists():
        raise FileNotFoundError(f"No existe: {path}")
    token = _file_signature(path)
    outdir = CACHE_ROOT / token
    manifest_file = outdir / "manifest.json"
    if manifest_file.exists():
        try:
            data = json.loads(manifest_file.read_text(encoding="utf-8"))
            data["related"] = find_related(path)
            return token, data
        except Exception:
            shutil.rmtree(outdir, ignore_errors=True)
    outdir.mkdir(parents=True, exist_ok=True)
    if is_3dmigoto(path):
        data = extract_3dmigoto(path, outdir)
    else:
        data = extract_spine(path, outdir)
    data["token"] = token
    data["related"] = find_related(path)
    manifest_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return token, data


def inject_js() -> str:
    return r'''(() => {
  if (window.__NMT_PREVIEW_BETA_INJECTED__) return;
  window.__NMT_PREVIEW_BETA_INJECTED__ = true;
  const BETA = 'http://127.0.0.1:8137';
  const findPath = (txt) => {
    const m = String(txt || '').match(/[A-Za-z]:\\[^\r\n]+/g);
    if (!m || !m.length) return null;
    return m.sort((a,b)=>b.length-a.length)[0].trim();
  };
  function openBeta(path) {
    document.getElementById('nmt-preview-beta-overlay')?.remove();
    const ov = document.createElement('div');
    ov.id = 'nmt-preview-beta-overlay';
    Object.assign(ov.style,{position:'fixed',inset:'0',zIndex:'2147483646',background:'rgba(2,7,14,.86)',backdropFilter:'blur(8px)',display:'flex',alignItems:'center',justifyContent:'center',padding:'18px'});
    const box = document.createElement('div');
    Object.assign(box.style,{width:'min(1400px,96vw)',height:'min(920px,94vh)',background:'#0b1220',border:'1px solid #334155',borderRadius:'16px',overflow:'hidden',boxShadow:'0 24px 80px rgba(0,0,0,.55)',position:'relative'});
    const close = document.createElement('button');
    close.textContent='×'; close.title='Cerrar';
    Object.assign(close.style,{position:'absolute',right:'12px',top:'10px',zIndex:'4',width:'38px',height:'38px',borderRadius:'999px',border:'1px solid #475569',background:'#243247',color:'#fff',fontSize:'25px',cursor:'pointer'});
    close.onclick=()=>ov.remove();
    const frame=document.createElement('iframe');
    frame.src=BETA+'/viewer?path='+encodeURIComponent(path);
    Object.assign(frame.style,{width:'100%',height:'100%',border:'0',background:'#080d16'});
    box.append(frame,close); ov.append(box); document.body.append(ov);
    ov.addEventListener('click',e=>{if(e.target===ov)ov.remove();});
  }
  function attach() {
    const nodes=[...document.querySelectorAll('div,section,dialog')].filter(el=>{
      const t=el.innerText||'';
      return t.includes('Preview Alpha') && (t.includes('ARCHIVO DEL BUNDLE')||t.includes('BUNDLE FILE')||/C:\\/.test(t));
    });
    nodes.sort((a,b)=>(a.innerText||'').length-(b.innerText||'').length);
    const modal=nodes[0]; if(!modal || modal.dataset.nmtBeta==='1') return;
    const path=findPath(modal.innerText); if(!path) return;
    modal.dataset.nmtBeta='1';
    const btn=document.createElement('button');
    btn.type='button'; btn.textContent='▶ Preview Beta';
    Object.assign(btn.style,{position:'absolute',right:'68px',top:'18px',zIndex:'9999',padding:'9px 13px',borderRadius:'999px',border:'1px solid #fbbf24',background:'#3a2d08',color:'#fde68a',fontWeight:'800',cursor:'pointer',boxShadow:'0 6px 18px rgba(0,0,0,.3)'});
    btn.onclick=(e)=>{e.preventDefault();e.stopPropagation();openBeta(path);};
    const cs=getComputedStyle(modal); if(cs.position==='static') modal.style.position='relative';
    modal.appendChild(btn);
  }
  new MutationObserver(()=>attach()).observe(document.documentElement,{subtree:true,childList:true,characterData:true});
  setInterval(attach,700); attach();
})();'''


def viewer_html(path_text: str) -> str:
    q = urllib.parse.quote(path_text, safe="")
    return f'''<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NIKKE Preview Beta</title>
<style>
*{{box-sizing:border-box}}html,body{{margin:0;height:100%;background:#070c14;color:#e5e7eb;font-family:Inter,Segoe UI,Arial,sans-serif;overflow:hidden}}
#app{{height:100%;display:grid;grid-template-rows:auto 1fr auto}}header{{background:#101a2a;border-bottom:1px solid #2d3b50;padding:14px 20px;display:flex;gap:16px;align-items:center;min-height:76px}}.brand{{font-size:12px;font-weight:900;color:#facc15;text-transform:uppercase;letter-spacing:.08em}}h1{{font-size:20px;margin:2px 0 0}}.sub{{color:#94a3b8;font-size:12px;margin-top:4px}}#tabs{{margin-left:auto;display:flex;gap:7px}}#tabs a{{text-decoration:none;color:#cbd5e1;border:1px solid #334155;background:#172033;padding:7px 11px;border-radius:9px;font-size:12px;font-weight:700}}#tabs a.active{{border-color:#fbbf24;color:#fde68a;background:#3a2d08}}main{{position:relative;min-height:0}}#stage{{position:absolute;inset:0;overflow:hidden;background:radial-gradient(circle at 50% 42%,#172033 0,#080d16 58%,#05080d 100%)}}#stage canvas{{display:block;width:100%;height:100%}}#loading,#error{{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;text-align:center;padding:30px;color:#cbd5e1;z-index:3}}#error{{color:#fecaca;display:none}}footer{{min-height:78px;background:#101a2a;border-top:1px solid #2d3b50;padding:10px 18px;display:flex;align-items:center;gap:10px;flex-wrap:wrap}}button,select,input{{font:inherit}}button,select{{background:#172033;color:#e5e7eb;border:1px solid #334155;border-radius:8px;padding:7px 10px}}button{{cursor:pointer}}button:hover{{border-color:#64748b}}select{{min-width:210px}}.pill{{border:1px solid #334155;border-radius:999px;padding:6px 10px;color:#94a3b8;font-size:11px}}#three{{display:none;position:absolute;inset:0;overflow:auto;padding:22px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}}.card{{background:#0f1725;border:1px solid #28364b;border-radius:12px;padding:10px}}.card img{{width:100%;height:260px;object-fit:contain;background:#05080d;border-radius:8px}}.warn{{background:#30250a;border:1px solid #705513;color:#fde68a;border-radius:10px;padding:10px 12px;margin-bottom:14px}}.spacer{{flex:1}}#status{{max-width:45vw;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/pixi.js/6.5.10/browser/pixi.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/pixi-spine@4.0.4/dist/pixi-spine.umd.js"></script>
</head><body><div id="app"><header><div><div class="brand">NIKKE Preview Beta · v0.12</div><h1 id="title">Cargando…</h1><div class="sub" id="subtitle"></div></div><div id="tabs"></div></header><main><div id="stage"></div><div id="three"></div><div id="loading">Preparando el mod…</div><div id="error"></div></main><footer><button id="play">⏸ Pausa</button><select id="anim"></select><label class="pill"><input id="loop" type="checkbox" checked> Loop</label><button id="reset">↺ Reset</button><button id="minus">−</button><button id="plus">+</button><span class="pill" id="meta">—</span><span class="spacer"></span><span class="pill" id="status">{html.escape(path_text)}</span></footer></div>
<script>
const SOURCE=decodeURIComponent('{q}');
const $=s=>document.querySelector(s);let app=null,model=null,baseScale=1,paused=false;
function fail(msg){{$('#loading').style.display='none';$('#error').style.display='flex';$('#error').innerHTML='<div><b>No se pudo montar el preview.</b><br><br>'+String(msg).replaceAll('<','&lt;')+'</div>';}}
function setTabs(rel,current){{const box=$('#tabs');box.innerHTML='';for(const a of ['standing','aim','cover']){{if(!rel||!rel[a])continue;const el=document.createElement('a');el.href='/viewer?path='+encodeURIComponent(rel[a]);el.textContent=a[0].toUpperCase()+a.slice(1);if(a===current)el.className='active';box.appendChild(el);}}}}
function chooseAnim(names,action){{const prefs=action==='aim'?['aim_idle','aim']:action==='cover'?['cover_idle','cover']:['idle','normal_idle','standing'];for(const p of prefs){{const exact=names.find(n=>n.toLowerCase()===p);if(exact)return exact;const part=names.find(n=>n.toLowerCase().includes(p));if(part)return part;}}return names[0]||'';}}
function fit(){{if(!model||!app)return;const w=$('#stage').clientWidth,h=$('#stage').clientHeight;app.renderer.resize(w,h);let b;try{{b=model.getLocalBounds();}}catch(e){{b=model.getBounds();}}const bw=Math.max(1,b.width),bh=Math.max(1,b.height);baseScale=Math.min(w/bw,h/bh)*.82;model.scale.set(baseScale);model.x=w/2-(b.x+b.width/2)*baseScale;model.y=h/2-(b.y+b.height/2)*baseScale;}}
async function show3d(m){{$('#loading').style.display='none';$('#stage').style.display='none';$('#three').style.display='block';$('#play').disabled=true;$('#anim').disabled=true;$('#meta').textContent='3DMigoto · '+(m.action||'');const c=$('#three');c.innerHTML='<div class="warn">'+m.note+'</div><div class="grid"></div>';const g=c.querySelector('.grid');for(const im of (m.images||[])){{const d=document.createElement('div');d.className='card';d.innerHTML='<img src="/asset/'+m.token+'/'+encodeURIComponent(im.name)+'"><div style="margin-top:8px;font-size:12px;color:#cbd5e1">'+im.sourceName+' · '+im.width+'×'+im.height+'</div>';g.appendChild(d);}}if(!(m.images||[]).length)c.innerHTML+='<p>No encontré una textura DDS/PNG que Pillow pudiera abrir en esta carpeta.</p>';}}
async function showSpine(m){{$('#loading').style.display='none';$('#three').style.display='none';$('#stage').style.display='block';if(!window.PIXI||!PIXI.spine)throw new Error('No cargó el runtime web de Pixi/Spine. Comprueba tu conexión a Internet.');const stage=$('#stage');stage.innerHTML='';app=new PIXI.Application({{width:stage.clientWidth,height:stage.clientHeight,transparent:true,antialias:true,autoDensity:true,resolution:Math.min(devicePixelRatio||1,2)}});stage.appendChild(app.view);const loader=new PIXI.Loader();const base='/asset/'+m.token+'/';loader.add('nikke',base+m.skel,{{metadata:{{spineAtlasFile:base+m.atlas}}}});await new Promise((resolve,reject)=>{{loader.onError.add((e)=>reject(e));loader.load((ldr,res)=>{{try{{if(!res.nikke||!res.nikke.spineData)throw new Error('Pixi no obtuvo spineData');model=new PIXI.spine.Spine(res.nikke.spineData);app.stage.addChild(model);resolve();}}catch(e){{reject(e);}}}});}});const names=(model.spineData?.animations||[]).map(x=>x.name);const sel=$('#anim');sel.innerHTML='';for(const n of names){{const o=document.createElement('option');o.value=n;o.textContent=n;sel.appendChild(o);}}const initial=chooseAnim(names,m.action);if(initial){{sel.value=initial;model.state.setAnimation(0,initial,$('#loop').checked);}}fit();$('#meta').textContent='Spine '+m.spineVersion+' · '+(m.action||'')+' · '+m.bundleKind;sel.onchange=()=>model.state.setAnimation(0,sel.value,$('#loop').checked);$('#loop').onchange=()=>{{if(sel.value)model.state.setAnimation(0,sel.value,$('#loop').checked);}};$('#play').onclick=()=>{{paused=!paused;model.state.timeScale=paused?0:1;$('#play').textContent=paused?'▶ Reanudar':'⏸ Pausa';}};$('#reset').onclick=fit;$('#plus').onclick=()=>model.scale.set(model.scale.x*1.12);$('#minus').onclick=()=>model.scale.set(model.scale.x/1.12);let drag=false,lx=0,ly=0;app.view.addEventListener('pointerdown',e=>{{drag=true;lx=e.clientX;ly=e.clientY;app.view.setPointerCapture?.(e.pointerId);}});app.view.addEventListener('pointermove',e=>{{if(!drag)return;model.x+=e.clientX-lx;model.y+=e.clientY-ly;lx=e.clientX;ly=e.clientY;}});app.view.addEventListener('pointerup',()=>drag=false);app.view.addEventListener('wheel',e=>{{e.preventDefault();const f=e.deltaY<0?1.08:.92;model.scale.set(model.scale.x*f);}},{{passive:false}});window.addEventListener('resize',fit);}}
(async()=>{{try{{const r=await fetch('/api/prepare?path='+encodeURIComponent(SOURCE));const m=await r.json();if(!r.ok||m.error)throw new Error(m.error||'Error preparando mod');$('#title').textContent=(m.rest||'Mod')+(m.action?' · '+m.action.toUpperCase():'');$('#subtitle').textContent=(m.id?'ID '+m.id+' · Ver '+m.ver+' · ':'')+m.source;setTabs(m.related,m.action);if(m.type==='3dmigoto')await show3d(m);else await showSpine(m);}}catch(e){{fail(e.stack||e.message||e);}}}})();
</script></body></html>'''


class Handler(BaseHTTPRequestHandler):
    server_version = "NIKKEPreviewBeta/0.12"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("[PreviewBeta] " + (fmt % args) + "\n")

    def _send(self, body: bytes, content_type: str = "text/plain; charset=utf-8", status: int = 200, extra: Optional[Dict[str, str]] = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        if extra:
            for k, v in extra.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self._send(b"", status=204, extra={"Access-Control-Allow-Methods": "GET, OPTIONS", "Access-Control-Allow-Headers": "*"})

    def do_GET(self) -> None:
        u = urllib.parse.urlsplit(self.path)
        q = urllib.parse.parse_qs(u.query)
        try:
            if u.path == "/health":
                self._send(_json_bytes({"ok": True, "version": "0.12"}), "application/json; charset=utf-8")
                return
            if u.path == "/inject.js":
                self._send(inject_js().encode("utf-8"), "application/javascript; charset=utf-8")
                return
            if u.path == "/viewer":
                p = q.get("path", [""])[0]
                self._send(viewer_html(p).encode("utf-8"), "text/html; charset=utf-8")
                return
            if u.path == "/api/prepare":
                p = q.get("path", [""])[0]
                try:
                    token, data = prepare(p)
                    data = dict(data)
                    data["token"] = token
                    self._send(_json_bytes(data), "application/json; charset=utf-8")
                except Exception as exc:
                    traceback.print_exc()
                    self._send(_json_bytes({"error": str(exc)}), "application/json; charset=utf-8", 500)
                return
            m = re.fullmatch(r"/asset/([0-9a-f]{8,40})/(.+)", u.path)
            if m:
                token = m.group(1)
                name = urllib.parse.unquote(m.group(2))
                base = (CACHE_ROOT / token).resolve()
                target = (base / name).resolve()
                if not str(target).startswith(str(base)) or not target.is_file():
                    self._send(b"Not found", status=404)
                    return
                ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
                self._send(target.read_bytes(), ctype)
                return
            self._send(b"NIKKE Preview Beta v0.12", status=404)
        except BrokenPipeError:
            pass
        except Exception as exc:
            traceback.print_exc()
            self._send(str(exc).encode("utf-8", errors="replace"), status=500)


def main() -> None:
    global APP_ROOT, CACHE_ROOT, PORT
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path.cwd()))
    ap.add_argument("--port", type=int, default=PORT)
    ns = ap.parse_args()
    APP_ROOT = Path(ns.root).resolve()
    CACHE_ROOT = APP_ROOT / ".nikke_preview_beta_cache"
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    PORT = ns.port
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"NIKKE Preview Beta v0.12: http://127.0.0.1:{PORT}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
