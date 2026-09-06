from __future__ import annotations

import argparse
import io
import re
from pathlib import Path
from typing import Any, List

import preview_beta_server_core as core

# v0.13 mantiene el servidor v0.12 como núcleo y añade:
# - reparación conservadora EN MEMORIA de cadenas Unity dañadas;
# - intento Spine/Unity también para 3DMigoto antes del fallback de texturas;
# - demos rápidos sobre las animaciones reales encontradas;
# - caché separada para no reutilizar previews antiguos.

try:
    import UnityPy
except Exception:
    UnityPy = None

_ORIGINAL_UNITY_LOAD = getattr(UnityPy, "load", None) if UnityPy else None
_ORIGINAL_SPINE = core.extract_spine
_ORIGINAL_3DMIGOTO = core.extract_3dmigoto
_ORIGINAL_VIEWER = core.viewer_html
_ORIGINAL_INJECT = core.inject_js
_REPAIR_COUNT = 0

UNITY_RE = re.compile(rb"20\d{2}\.\d{1,2}\.\d{1,3}[abfp]\d+")


def _valid_versions_for_length(length: int) -> List[bytes]:
    out: List[bytes] = []
    for major in (2021, 2020, 2022, 2019, 2023, 2018):
        for minor in (3, 4, 2, 1, 0):
            for patch in (36, 35, 48, 18, 16, 12, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0):
                for suffix in ("f1", "f2", "p1", "b1", "a1"):
                    value = f"{major}.{minor}.{patch}{suffix}".encode("ascii")
                    if len(value) == length and value not in out:
                        out.append(value)
    return out


def _read_source_bytes(source: Any) -> bytes | None:
    try:
        if isinstance(source, (bytes, bytearray)):
            return bytes(source)
        if hasattr(source, "read") and hasattr(source, "seek"):
            try:
                pos = source.tell()
            except Exception:
                pos = 0
            source.seek(0)
            data = source.read()
            try:
                source.seek(pos)
            except Exception:
                pass
            return bytes(data)
        p = Path(source)
        if p.is_file():
            return p.read_bytes()
    except Exception:
        return None
    return None


def _repair_variants(raw: bytes, error_text: str) -> List[bytes]:
    variants: List[bytes] = []

    # 1) Si UnityPy nos entrega literalmente la cadena inválida, sustituimos
    # SOLO esa secuencia y SOLO por otra versión válida de igual longitud.
    m = re.search(r"Invalid version string:\s*([^\r\n]+)", error_text, re.I)
    if m:
        bad_text = m.group(1).strip().strip("'\"")
        for enc in ("utf-8", "latin1"):
            try:
                bad = bad_text.encode(enc)
            except Exception:
                continue
            if not bad or bad not in raw:
                continue
            candidates = _valid_versions_for_length(len(bad))
            if candidates:
                variants.append(raw.replace(bad, candidates[0], 1))
                break

    # 2) Reparación del campo unityVersion del encabezado UnityFS/Raw/Web.
    # No se cambia el largo del archivo: es deliberadamente conservadora.
    if raw.startswith((b"UnityFS\x00", b"UnityRaw\x00", b"UnityWeb\x00")):
        try:
            sig_end = raw.index(b"\x00", 0, 16)
            v_start = sig_end + 1 + 4
            v_end = raw.index(b"\x00", v_start, min(len(raw), v_start + 96))
            current = raw[v_start:v_end]
            if not UNITY_RE.fullmatch(current):
                revision_start = v_end + 1
                revision_end = raw.index(b"\x00", revision_start, min(len(raw), revision_start + 96))
                revision = raw[revision_start:revision_end]
                candidate = revision if UNITY_RE.fullmatch(revision) and len(revision) == len(current) else None
                if candidate is None:
                    choices = _valid_versions_for_length(len(current))
                    candidate = choices[0] if choices else None
                if candidate:
                    patched = raw[:v_start] + candidate + raw[v_end:]
                    if patched not in variants:
                        variants.append(patched)
        except Exception:
            pass

    return variants


def _safe_unity_load(source: Any, *args: Any, **kwargs: Any):
    global _REPAIR_COUNT
    if _ORIGINAL_UNITY_LOAD is None:
        raise RuntimeError("UnityPy no está disponible")
    try:
        return _ORIGINAL_UNITY_LOAD(source, *args, **kwargs)
    except Exception as first:
        if "invalid version string" not in str(first).lower():
            raise
        raw = _read_source_bytes(source)
        if not raw:
            raise
        last = first
        for patched in _repair_variants(raw, str(first)):
            try:
                env = _ORIGINAL_UNITY_LOAD(io.BytesIO(patched), *args, **kwargs)
                _REPAIR_COUNT += 1
                print("[Preview v0.13] Se reparó en memoria una cadena Unity inválida; el mod original no fue modificado.")
                return env
            except Exception as exc:
                last = exc
        raise last


if UnityPy is not None and _ORIGINAL_UNITY_LOAD is not None:
    UnityPy.load = _safe_unity_load


def extract_3dmigoto_v013(path: Path, outdir: Path):
    """Intenta reconstrucción Spine real antes de recurrir a la vista técnica."""
    global _REPAIR_COUNT
    before = _REPAIR_COUNT
    spine_error = ""
    try:
        data = _ORIGINAL_SPINE(path, outdir)
        data = dict(data)
        data["previewMode"] = "3dmigoto-spine"
        data["repairApplied"] = _REPAIR_COUNT > before
        data["note"] = (
            "3DMigoto reconstruido como Spine/Unity. "
            + ("Se corrigió una cadena Unity dañada únicamente en memoria." if data["repairApplied"] else "")
        ).strip()
        return data
    except Exception as exc:
        spine_error = str(exc)

    # Fallback: conservar la extracción de imágenes de v0.12, pero dejar claro
    # que es una vista técnica y no un personaje reconstruido.
    data = dict(_ORIGINAL_3DMIGOTO(path, outdir))
    data["previewMode"] = "3dmigoto-texture-fallback"
    data["repairApplied"] = _REPAIR_COUNT > before
    short_error = spine_error[-260:] if spine_error else "No se encontró un set Spine utilizable."
    data["note"] = (
        "Vista técnica de respaldo: no se pudo reconstruir todavía el personaje animado. "
        "Las imágenes de abajo son texturas/assets del mod, no una preview final. "
        f"Detalle: {short_error}"
    )
    return data


core.extract_3dmigoto = extract_3dmigoto_v013


def inject_js_v013() -> str:
    return (
        _ORIGINAL_INJECT()
        .replace("▶ Preview Beta", "▶ Preview & Demo")
        .replace("PreviewBeta", "PreviewDemo")
    )


core.inject_js = inject_js_v013

_DEMO_JS = r'''
let demoTimer=null,demoPos=0;
function stopDemo(){if(demoTimer){clearInterval(demoTimer);demoTimer=null;}}
function animationNames(){return [...document.querySelectorAll('#anim option')].map(o=>o.value).filter(Boolean);}
function playNamed(name){
  if(!model||!name)return false;
  stopDemo();
  const sel=$('#anim'); sel.value=name;
  model.state.setAnimation(0,name,$('#loop').checked);
  return true;
}
function pickByKeywords(keys){
  const names=animationNames();
  for(const key of keys){const exact=names.find(n=>n.toLowerCase()===key);if(exact)return exact;}
  for(const key of keys){const part=names.find(n=>n.toLowerCase().includes(key));if(part)return part;}
  return names[0]||'';
}
function demoIdle(){playNamed(pickByKeywords(['idle','normal_idle','standing','wait','loop','normal']));}
function demoAction(){playNamed(pickByKeywords(['attack','skill','burst','fire','shot','action','aim','cover']));}
function demoAuto(){
  stopDemo(); const names=animationNames(); if(!model||!names.length)return;
  const preferred=names.filter(n=>/(idle|stand|wait|attack|skill|burst|fire|shot|action|aim|cover)/i.test(n));
  const list=preferred.length?preferred:names; demoPos=0;
  const next=()=>{const name=list[demoPos++%list.length];$('#anim').value=name;model.state.setAnimation(0,name,true);};
  next(); demoTimer=setInterval(next,2800);
}
$('#demoIdle').onclick=demoIdle;
$('#demoAction').onclick=demoAction;
$('#demoAuto').onclick=demoAuto;
'''


def viewer_html_v013(path_text: str) -> str:
    html = _ORIGINAL_VIEWER(path_text)
    html = html.replace("NIKKE Preview Beta · v0.12", "NIKKE Preview & Demo · v0.13")
    html = html.replace("<title>NIKKE Preview Beta</title>", "<title>NIKKE Preview & Demo v0.13</title>")
    html = html.replace(
        '<button id="reset">↺ Reset</button>',
        '<button id="reset">↺ Reset</button><button id="demoIdle" title="Busca una animación Idle/Standing">Demo Idle</button><button id="demoAction" title="Busca Attack/Skill/Burst">Demo Acción</button><button id="demoAuto" title="Recorre automáticamente animaciones detectadas">Demo Auto</button>',
        1,
    )
    html = html.replace("(async()=>{try{", _DEMO_JS + "\n(async()=>{try{", 1)
    html = html.replace(
        "sel.onchange=()=>model.state.setAnimation(0,sel.value,$('#loop').checked);",
        "sel.onchange=()=>{stopDemo();model.state.setAnimation(0,sel.value,$('#loop').checked);};",
    )
    html = html.replace("NIKKE Preview Beta", "NIKKE Preview & Demo")
    return html


core.viewer_html = viewer_html_v013


class HandlerV013(core.Handler):
    server_version = "NIKKEPreviewDemo/0.13"

    def do_GET(self) -> None:
        u = core.urllib.parse.urlsplit(self.path)
        if u.path == "/health":
            self._send(core._json_bytes({"ok": True, "version": "0.13", "preview": "Preview & Demo"}), "application/json; charset=utf-8")
            return
        return super().do_GET()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path.cwd()))
    ap.add_argument("--port", type=int, default=core.PORT)
    ns = ap.parse_args()
    core.APP_ROOT = Path(ns.root).resolve()
    core.CACHE_ROOT = core.APP_ROOT / ".nikke_preview_v013_cache"
    core.CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    core.PORT = ns.port
    httpd = core.ThreadingHTTPServer(("127.0.0.1", core.PORT), HandlerV013)
    print(f"NIKKE Preview & Demo v0.13: http://127.0.0.1:{core.PORT}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
