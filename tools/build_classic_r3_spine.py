from __future__ import annotations

import os
import shutil
import subprocess
import textwrap
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'recovered_pc' / 'v011' / 'NIKKE_Mod_Manager_v0_11_Preview_Alpha'
DIST = ROOT / 'dist'
OUT = DIST / 'NIKKE_Mod_Manager_v0_13_CLASSIC_R3_SPINE_FULL'
ZIP = DIST / 'NIKKE_Mod_Manager_v0_13_CLASSIC_R3_SPINE_FULL.zip'

PREVIEW_PY = r'''
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import struct
import zipfile
from pathlib import Path
from typing import Any, Iterable

class PreviewError(RuntimeError):
    pass

def _decrypt_aes_cbc(key: bytes, iv: bytes, payload: bytes) -> bytes:
    try:
        from Crypto.Cipher import AES
    except Exception as exc:
        raise PreviewError('Falta pycryptodome. Ejecuta INSTALAR_Y_ABRIR.bat para actualizar dependencias.') from exc
    if len(iv) != 16:
        raise PreviewError(f'IV NKAB no compatible ({len(iv)} bytes).')
    if len(payload) % 16:
        raise PreviewError('El bloque cifrado NKAB no es multiplo de 16 bytes.')
    return AES.new(key, AES.MODE_CBC, iv=iv).decrypt(payload)

def decrypt_nkab(raw: bytes) -> tuple[bytes, int | None]:
    if len(raw) < 8 or raw[:4] != b'NKAB':
        return raw, None
    version = struct.unpack_from('<I', raw, 4)[0]
    if version == 1:
        if len(raw) < 16:
            raise PreviewError('Cabecera NKAB v1 incompleta.')
        pos = 8
        header_size_raw, mode_raw, key_len_raw, encrypted_len_raw = struct.unpack_from('<hhhh', raw, pos)
        pos += 8
        _header_size = header_size_raw + 100
        _mode = mode_raw + 100
        key_len = key_len_raw + 100
        encrypted_len = encrypted_len_raw + 100
        if key_len <= 0 or key_len > 64:
            raise PreviewError(f'Longitud de clave NKAB v1 no valida: {key_len}.')
        if encrypted_len <= 0 or encrypted_len > len(raw):
            raise PreviewError(f'Longitud cifrada NKAB v1 no valida: {encrypted_len}.')
        if pos + key_len * 2 + encrypted_len > len(raw):
            raise PreviewError('NKAB v1 truncado.')
        key = raw[pos:pos + key_len]
        pos += key_len
        iv = raw[pos:pos + key_len]
        pos += key_len
        encrypted = raw[pos:pos + encrypted_len]
        pos += encrypted_len
        import hashlib as _hashlib
        aes_key = _hashlib.sha256(key).digest()
        decrypted = _decrypt_aes_cbc(aes_key, iv, encrypted)
        return decrypted + raw[pos:], version
    if version == 2:
        if len(raw) < 56:
            raise PreviewError('Cabecera NKAB v2 incompleta.')
        key = raw[-32:]
        obf_number = struct.unpack_from('<h', key, 0)[0]
        pos = 8
        header_size_raw, mode_raw, key_len_raw, encrypted_len_raw = struct.unpack_from('<hhhh', raw, pos)
        pos += 8
        _header_size = header_size_raw + obf_number
        _mode = mode_raw + obf_number
        _key_len = key_len_raw + obf_number
        encrypted_len = encrypted_len_raw + obf_number
        iv = raw[pos:pos + 16]
        pos += 16
        if encrypted_len <= 0 or pos + encrypted_len > len(raw) - 32:
            raise PreviewError(f'Longitud cifrada NKAB v2 no valida: {encrypted_len}.')
        encrypted = raw[pos:pos + encrypted_len]
        pos += encrypted_len
        decrypted = _decrypt_aes_cbc(key, iv, encrypted)
        return decrypted + raw[pos:-32], version
    raise PreviewError(f'Version NKAB no compatible: {version}.')

def _object_data(obj):
    if hasattr(obj, 'parse_as_object'):
        return obj.parse_as_object()
    if hasattr(obj, 'read'):
        return obj.read()
    raise PreviewError('La version instalada de UnityPy no puede leer objetos.')

def _text_asset_bytes(data) -> bytes:
    value = getattr(data, 'm_Script', None)
    if value is None:
        value = getattr(data, 'script', b'')
    if isinstance(value, str):
        return value.encode('utf-8', errors='replace')
    try:
        return bytes(value)
    except Exception:
        return b''

def _text_asset_name(data) -> str:
    return str(getattr(data, 'm_Name', None) or getattr(data, 'name', '') or '')

def _texture_name(data) -> str:
    return str(getattr(data, 'm_Name', None) or getattr(data, 'name', '') or 'Texture2D')

def _safe_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except Exception:
        return 0

def _folder_candidates(folder: Path) -> list[Path]:
    files: list[Path] = []
    try:
        for current, dirs, names in os.walk(folder):
            dirs[:] = [d for d in dirs if d.lower() not in {'.git', '.svn', '__pycache__'}]
            for name in names:
                p = Path(current) / name
                if p.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.txt', '.md', '.json'}:
                    continue
                files.append(p)
                if len(files) >= 400:
                    break
            if len(files) >= 400:
                break
    except Exception:
        pass
    files.sort(key=lambda p: (_safe_size(p), str(p).lower()), reverse=True)
    return files

def _zip_candidates(path: Path) -> Iterable[tuple[str, bytes]]:
    try:
        with zipfile.ZipFile(path, 'r') as zf:
            members = [m for m in zf.infolist() if not m.is_dir()]
            members.sort(key=lambda m: m.file_size, reverse=True)
            for member in members[:250]:
                suffix = Path(member.filename).suffix.lower()
                if suffix in {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.txt', '.md', '.json'}:
                    continue
                try:
                    yield member.filename, zf.read(member)
                except Exception:
                    continue
    except zipfile.BadZipFile as exc:
        raise PreviewError('El archivo .zip no es valido o esta danado.') from exc

def _raw_candidates(target: Path) -> Iterable[tuple[str, bytes]]:
    if target.is_dir():
        files = _folder_candidates(target)
        if not files:
            raise PreviewError('No encontre archivos de bundle dentro de esta carpeta de mod.')
        for p in files:
            try:
                yield str(p), p.read_bytes()
            except Exception:
                continue
        return
    if not target.exists():
        raise PreviewError('El mod ya no existe en la ruta escaneada.')
    if target.suffix.lower() == '.zip':
        yield from _zip_candidates(target)
        return
    if target.suffix.lower() in {'.rar', '.7z'}:
        raise PreviewError('Preview Alpha todavia no abre RAR/7Z. Descomprime ese mod primero.')
    try:
        yield str(target), target.read_bytes()
    except Exception as exc:
        raise PreviewError(f'No pude leer el archivo: {exc}') from exc

def _clean_filename(name: str, fallback: str) -> str:
    value = re.sub(r'[^0-9A-Za-z._-]+', '_', name or '').strip('._-')
    return value or fallback

def _decode_atlas(raw: bytes) -> str:
    for enc in ('utf-8', 'utf-8-sig', 'latin-1'):
        try:
            text = raw.decode(enc)
            if 'size:' in text or 'xy:' in text or 'rotate:' in text:
                return text
        except Exception:
            pass
    return raw.decode('utf-8', errors='replace')

def _looks_like_atlas(name: str, payload: bytes) -> bool:
    lname = name.lower()
    if '.atlas' in lname or lname.endswith('_atlas'):
        return True
    head = payload[:5000]
    return b'size:' in head and (b'filter:' in head or b'xy:' in head or b'rotate:' in head)

def _looks_like_skel(name: str, payload: bytes) -> bool:
    lname = name.lower()
    if '.skel' in lname or lname.endswith('_skel') or 'skeleton' in lname:
        return True
    return payload[:128].lower().find(b'spine') >= 0 and b'\x00' in payload[:256]

def _score_asset(name: str, action: str) -> int:
    lname = name.lower()
    score = 0
    if action and action.lower() in lname:
        score += 200
    for hint in ('aim', 'cover', 'standing', 'idle'):
        if hint in lname:
            score += 10
    if '.atlas' in lname or '.skel' in lname:
        score += 5
    return score

class ModPreviewEngine:
    ATLAS_NAME_RE = re.compile(r'^([0-9a-z]+)_(?:([a-z]+)_)?([0-9]+)\.atlas$', re.IGNORECASE)

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _fingerprint(path: Path, item_id: str, action: str = '') -> str:
        h = hashlib.sha1()
        h.update(b'classic-r3-spine-003')
        h.update(str(path.resolve()).encode('utf-8', errors='replace'))
        h.update(str(item_id).encode('utf-8', errors='replace'))
        h.update(str(action).encode('utf-8', errors='replace'))
        try:
            if path.is_file():
                st = path.stat()
                h.update(f'{st.st_size}:{st.st_mtime_ns}'.encode())
            elif path.is_dir():
                latest = 0
                total = 0
                count = 0
                for p in _folder_candidates(path)[:60]:
                    try:
                        st = p.stat()
                        latest = max(latest, st.st_mtime_ns)
                        total += st.st_size
                        count += 1
                    except Exception:
                        pass
                h.update(f'{count}:{total}:{latest}'.encode())
        except Exception:
            pass
        return h.hexdigest()[:20]

    def generate(self, target: Path, item_id: str, action: str = '') -> dict[str, Any]:
        cache_key = self._fingerprint(target, item_id, action)
        image_path = self.output_dir / f'{cache_key}.png'
        meta_path = self.output_dir / f'{cache_key}.json'
        if image_path.exists() and meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding='utf-8'))
                if isinstance(meta, dict) and meta.get('preview_version') == 'classic_r3_spine_canvas':
                    meta['cached'] = True
                    meta['preview_url'] = f'assets/previews/{image_path.name}'
                    return meta
            except Exception:
                pass
        try:
            import UnityPy
        except Exception as exc:
            raise PreviewError('Falta UnityPy. Cierra la app y ejecuta INSTALAR_Y_ABRIR.bat para instalar dependencias.') from exc
        attempts: list[str] = []
        last_error: Exception | None = None
        for source_name, raw in _raw_candidates(target):
            if not raw:
                continue
            attempts.append(source_name)
            try:
                plain, nkab_version = decrypt_nkab(raw)
                env = UnityPy.load(plain)
                textures: list[dict[str, Any]] = []
                atlases: list[tuple[str, bytes]] = []
                skels: list[tuple[str, bytes]] = []
                character_id = ''
                pose = ''
                skin_key: int | None = None
                for obj in env.objects:
                    type_name = getattr(getattr(obj, 'type', None), 'name', '')
                    if type_name == 'Texture2D':
                        try:
                            data = _object_data(obj)
                            width = int(getattr(data, 'm_Width', 0) or getattr(data, 'width', 0) or 0)
                            height = int(getattr(data, 'm_Height', 0) or getattr(data, 'height', 0) or 0)
                            image = data.image
                            if image is None:
                                continue
                            textures.append({'area': max(1, width) * max(1, height), 'data': data, 'name': _texture_name(data), 'width': width, 'height': height, 'image': image})
                        except Exception:
                            continue
                    elif type_name == 'TextAsset':
                        try:
                            data = _object_data(obj)
                            name = _text_asset_name(data)
                            payload = _text_asset_bytes(data)
                            if not payload:
                                continue
                            if _looks_like_atlas(name, payload):
                                atlases.append((name or f'atlas_{len(atlases)}.atlas', payload))
                                m = self.ATLAS_NAME_RE.match(name or '')
                                if m:
                                    character_id = m.group(1)
                                    pose = m.group(2) or 'idle'
                                    try:
                                        skin_key = int(m.group(3))
                                    except Exception:
                                        skin_key = None
                            elif _looks_like_skel(name, payload):
                                skels.append((name or f'skeleton_{len(skels)}.skel', payload))
                        except Exception:
                            continue
                if not textures:
                    raise PreviewError('El bundle se abrio, pero no contiene Texture2D que pueda mostrar.')
                textures.sort(key=lambda x: int(x['area']), reverse=True)
                primary = textures[0]
                full_image = primary['image']
                if full_image.mode != 'RGBA':
                    full_image = full_image.convert('RGBA')
                asset_dir = self.output_dir / f'{cache_key}_spine'
                if asset_dir.exists():
                    shutil.rmtree(asset_dir, ignore_errors=True)
                asset_dir.mkdir(parents=True, exist_ok=True)
                texture_file = _clean_filename(str(primary['name']), 'texture')
                if not texture_file.lower().endswith('.png'):
                    texture_file += '.png'
                full_texture_path = asset_dir / texture_file
                full_image.save(full_texture_path, format='PNG', optimize=True)
                fallback_image = full_image.copy()
                bbox = fallback_image.getbbox()
                if bbox:
                    fallback_image = fallback_image.crop(bbox)
                fallback_image.save(image_path, format='PNG', optimize=True)
                atlas_name = ''
                atlas_text = ''
                if atlases:
                    atlas_name, atlas_payload = sorted(atlases, key=lambda x: _score_asset(x[0], action), reverse=True)[0]
                    atlas_text = _decode_atlas(atlas_payload)
                    (asset_dir / 'model.atlas').write_text(atlas_text, encoding='utf-8', errors='replace')
                skel_name = ''
                skel_payload = b''
                if skels:
                    skel_name, skel_payload = sorted(skels, key=lambda x: _score_asset(x[0], action), reverse=True)[0]
                    (asset_dir / 'model.skel').write_bytes(skel_payload)
                result: dict[str, Any] = {
                    'ok': True,
                    'preview_version': 'classic_r3_spine_canvas',
                    'preview_url': f'assets/previews/{image_path.name}',
                    'cached': False,
                    'source_file': source_name,
                    'nkab_version': nkab_version,
                    'texture_name': str(primary['name']),
                    'texture_width': int(primary['width']),
                    'texture_height': int(primary['height']),
                    'texture_count': len(textures),
                    'atlas_names': [x[0] for x in atlases[:12]],
                    'skeleton_names': [x[0] for x in skels[:12]],
                    'character_id_detected': character_id,
                    'pose_detected': pose,
                    'skin_key_detected': skin_key,
                    'attempted_files': len(attempts),
                    'preview_kind': 'classic_r3_spine_canvas' if atlas_text and skel_payload else 'texture_fallback',
                    'spine_ready': bool(atlas_text and skel_payload),
                    'spine_canvas': bool(atlas_text and skel_payload),
                    'spine_texture_url': f'assets/previews/{asset_dir.name}/{full_texture_path.name}',
                    'spine_atlas_text': atlas_text,
                    'spine_skel_b64': base64.b64encode(skel_payload).decode('ascii') if skel_payload else '',
                    'spine_atlas_name': atlas_name,
                    'spine_skel_name': skel_name,
                    'action_hint': action,
                    'warning': ('Classic R3: intentando mostrar el modelo armado con atlas + skel dentro del Preview Alpha.' if atlas_text and skel_payload else 'Fallback: este bundle no trae atlas + skel normal suficientes para armar el modelo.'),
                }
                meta_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
                return result
            except Exception as exc:
                last_error = exc
                continue
        detail = str(last_error) if last_error else 'ningun archivo candidato pudo abrirse'
        raise PreviewError(f'No pude extraer datos compatibles de este mod. Ultimo error: {detail}')
'''

APP_JS_OVERRIDE = r'''

/* Classic R3 Spine preview override. Keeps the original v0.11 interface/modal; replaces only the content renderer. */
(function(){
  let r3PixiApp = null;
  let r3SpineObj = null;
  let r3BaseScale = 1;
  let r3Zoom = 1;
  function r3Cleanup(){ try { if (r3PixiApp) r3PixiApp.destroy(true, {children:true, texture:false, baseTexture:false}); } catch(e) {} r3PixiApp = null; r3SpineObj = null; r3BaseScale = 1; r3Zoom = 1; }
  function r3BytesFromB64(b64){ const bin = atob(String(b64 || '')); const out = new Uint8Array(bin.length); for(let i=0;i<bin.length;i++) out[i]=bin.charCodeAt(i); return out; }
  function r3WaitBaseTexture(bt){ return new Promise((resolve,reject)=>{ if(bt.valid){ resolve(); return; } let done=false; const ok=()=>{ if(!done){ done=true; resolve(); } }; const bad=(e)=>{ if(!done){ done=true; reject(e || new Error('No se pudo cargar la textura.')); } }; bt.once('loaded', ok); bt.once('error', bad); setTimeout(()=>{ if(!done && bt.valid) ok(); }, 3000); setTimeout(()=>{ if(!done) bad(new Error('Timeout cargando textura.')); }, 9000); }); }
  function r3PickAnimation(names, action){ const low = names.map(n=>String(n).toLowerCase()); const wanted=[]; const a=String(action||'').toLowerCase(); if(a==='aim') wanted.push('aim','idle','stand'); else if(a==='cover') wanted.push('cover','idle','stand'); else if(a==='standing') wanted.push('idle','stand','wait','default'); else wanted.push('idle','stand','aim','cover','default'); for(const w of wanted){ const exact=low.indexOf(w); if(exact>=0) return names[exact]; const partial=low.findIndex(n=>n.includes(w)); if(partial>=0) return names[partial]; } return names[0] || ''; }
  function r3FitSpine(){ if(!r3PixiApp || !r3SpineObj) return; const w=r3PixiApp.renderer.width||900; const h=r3PixiApp.renderer.height||560; try{ r3SpineObj.update(0.016); }catch(e){} const b=r3SpineObj.getLocalBounds(); const bw=Math.max(1,b.width||1); const bh=Math.max(1,b.height||1); r3BaseScale=Math.min((w*.82)/bw,(h*.86)/bh); if(!isFinite(r3BaseScale)||r3BaseScale<=0) r3BaseScale=1; r3SpineObj.scale.set(r3BaseScale*r3Zoom); r3SpineObj.x=(w/2)-((b.x+bw/2)*r3SpineObj.scale.x); r3SpineObj.y=(h/2)-((b.y+bh/2)*r3SpineObj.scale.y); }
  async function r3RenderSpine(r){ const host=document.getElementById('r3SpineHost'); const fallback=document.getElementById('r3TextureFallback'); const status=document.getElementById('r3SpineStatus'); const controls=document.getElementById('r3SpineControls'); if(!host||!r) return; try{ if(!window.PIXI||!PIXI.spine) throw new Error('No se cargó Pixi/Spine local.'); const core=PIXI.spine.core||PIXI.spine; if(!core.TextureAtlas||!core.AtlasAttachmentLoader||!core.SkeletonBinary||!PIXI.spine.Spine) throw new Error('Runtime Spine incompleto o incompatible.'); r3Cleanup(); const width=Math.max(640,host.clientWidth||900); const height=Math.max(420,host.clientHeight||560); r3PixiApp=new PIXI.Application({width,height,backgroundAlpha:0,antialias:true,autoDensity:true,resolution:window.devicePixelRatio||1}); host.innerHTML=''; host.appendChild(r3PixiApp.view); const baseTexture=PIXI.BaseTexture.from(r.spine_texture_url); await r3WaitBaseTexture(baseTexture); const atlas=new core.TextureAtlas(String(r.spine_atlas_text||''), function(_line, callback){ callback(baseTexture); }); const atlasLoader=new core.AtlasAttachmentLoader(atlas); const binary=new core.SkeletonBinary(atlasLoader); const skeletonData=binary.readSkeletonData(r3BytesFromB64(r.spine_skel_b64)); r3SpineObj=new PIXI.spine.Spine(skeletonData); r3PixiApp.stage.addChild(r3SpineObj); const animations=(skeletonData.animations||[]).map(a=>a.name||String(a)); const chosen=r3PickAnimation(animations,r.action_hint||r.action||''); if(chosen&&r3SpineObj.state) r3SpineObj.state.setAnimation(0,chosen,true); r3FitSpine(); if(fallback) fallback.style.display='none'; host.style.display='block'; if(status) status.textContent=chosen?`Modelo Spine armado · animación: ${chosen}`:'Modelo Spine armado'; if(controls){ controls.innerHTML='<button id="r3PauseBtn">Pausa</button><select id="r3AnimSelect"></select><button id="r3FitBtn">Ajustar</button><button id="r3ZoomOut">−</button><button id="r3ZoomIn">+</button><button id="r3ToggleTexture">Ver textura</button>'; const sel=document.getElementById('r3AnimSelect'); if(sel){ sel.innerHTML=animations.map(n=>`<option value="${esc(n)}">${esc(n)}</option>`).join(''); if(chosen) sel.value=chosen; sel.onchange=()=>{ try{ r3SpineObj.state.setAnimation(0,sel.value,true); if(status) status.textContent=`Modelo Spine armado · animación: ${sel.value}`; }catch(e){} }; } const pause=document.getElementById('r3PauseBtn'); if(pause) pause.onclick=()=>{ if(!r3PixiApp) return; const stopped=!r3PixiApp.ticker.started; if(stopped){ r3PixiApp.ticker.start(); pause.textContent='Pausa'; } else { r3PixiApp.ticker.stop(); pause.textContent='Reanudar'; } }; const fit=document.getElementById('r3FitBtn'); if(fit) fit.onclick=()=>{ r3Zoom=1; r3FitSpine(); }; const zout=document.getElementById('r3ZoomOut'); if(zout) zout.onclick=()=>{ r3Zoom=Math.max(.25,r3Zoom-.1); r3FitSpine(); }; const zin=document.getElementById('r3ZoomIn'); if(zin) zin.onclick=()=>{ r3Zoom=Math.min(3,r3Zoom+.1); r3FitSpine(); }; const tog=document.getElementById('r3ToggleTexture'); if(tog) tog.onclick=()=>{ const showingTex=fallback&&fallback.style.display!=='none'; if(showingTex){ fallback.style.display='none'; host.style.display='block'; tog.textContent='Ver textura'; } else { if(fallback) fallback.style.display='block'; host.style.display='none'; tog.textContent='Ver armado'; } }; } }catch(err){ console.error('Classic R3 Spine render failed',err); r3Cleanup(); if(host) host.style.display='none'; if(fallback) fallback.style.display='block'; if(status) status.textContent='No se pudo armar con Spine: '+(err&&err.message?err.message:err); if(controls) controls.innerHTML='<button id="r3OnlyTexture">Mostrando textura fallback</button>'; } }
  window.closePreview=function(){ r3Cleanup(); const modal=document.getElementById('previewModal'); if(modal) modal.classList.add('hidden'); };
  window.openPreview=async function(itemId){ const m=state?.items?.find(x=>x.item_id===itemId); const pc=document.getElementById('previewContent'); const pm=document.getElementById('previewModal'); if(!pc||!pm) return; r3Cleanup(); pc.innerHTML=`<div class="preview-loading"><div class="preview-spinner">↻</div><h2>${esc(t('preview_title'))}</h2><p>Montando modelo Spine del mod normal...</p>${m?`<div class="preview-mod-label">${esc(m.mod_title||m.name)}</div>`:''}</div>`; pm.classList.remove('hidden'); try{ const r=await apiCall('preview_item',itemId); if(!r?.ok){ pc.innerHTML=`<div class="preview-error"><div class="preview-error-icon">⚠</div><h2>${esc(t('preview_title'))}</h2><p>${esc(t('preview_failed',{error:r?.error||'—'}))}</p><div class="detail-path">${esc(r?.path||m?.path||'')}</div></div>`; return; } const canSpine=!!(r.spine_ready&&r.spine_canvas&&r.spine_skel_b64&&r.spine_atlas_text&&r.spine_texture_url); pc.innerHTML=`<div class="preview-head"><div><div class="preview-kicker">Preview Alpha · Classic R3</div><h2>${esc(r.mod_name||m?.mod_title||'Mod')}</h2><p>${esc(r.character_name||'')} · ID ${esc(r.id||'')} · Ver ${esc(r.version||'')} · ${esc((r.action||m?.action||'').toString())}</p></div><span class="preview-chip">${canSpine?'SPINE':'TEXTURA'}</span></div><div style="background:#05080d;border-top:1px solid rgba(255,255,255,.08);border-bottom:1px solid rgba(255,255,255,.08);min-height:560px;display:flex;align-items:center;justify-content:center;position:relative;overflow:hidden;"><div id="r3SpineHost" style="width:100%;height:560px;display:${canSpine?'block':'none'};"></div><img id="r3TextureFallback" src="${esc(r.preview_url)}" style="display:${canSpine?'none':'block'};max-width:100%;max-height:560px;object-fit:contain;" /></div><div id="r3SpineControls" style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:10px 14px;background:#0f1928;border-bottom:1px solid rgba(255,255,255,.08);"></div><div class="preview-warning" id="r3SpineStatus">${canSpine?'Preparando modelo armado...':esc(r.warning||'Fallback de textura.')}</div><div class="preview-grid"><div><span>${esc(t('preview_texture'))}</span><b>${esc(r.texture_name||'—')} · ${esc(r.texture_width||'')}×${esc(r.texture_height||'')}</b></div><div><span>SPINE</span><b>${canSpine?`${esc(r.spine_skel_name||'skel')} + ${esc(r.spine_atlas_name||'atlas')}`:'No detectado'}</b></div><div><span>${esc(t('preview_source'))}</span><b>${esc(r.source_file||'Unity bundle')}</b></div><div><span>${esc(t('preview_detected'))}</span><b>ID ${esc(r.character_id_detected||r.id||'—')} · ${esc(r.pose_detected||r.action_hint||'—')}</b></div></div>`; if(canSpine) setTimeout(()=>r3RenderSpine(r),40); }catch(err){ pc.innerHTML=`<div class="preview-error"><div class="preview-error-icon">⚠</div><h2>${esc(t('preview_title'))}</h2><p>${esc(err?.message||err)}</p></div>`; } };
})();
'''

def run(cmd: list[str], cwd: Path | None = None) -> None:
    print('+', ' '.join(cmd))
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)

def replace_visible_text(root: Path) -> None:
    repls = {
        'NIKKE Mod Library':'NIKKE Mod Manager',
        'NIKKE MOD LIBRARY':'NIKKE MOD MANAGER',
        'BIBLIOTECA DE MODS':'MOD MANAGER',
        '0.11 Preview Alpha':'0.13 Classic R3 Spine',
        'v0.11 Preview Alpha':'v0.13 Classic R3 Spine',
        'Extrayendo textura real del mod...':'Montando modelo Spine del mod normal...',
        'Extracting the real mod texture...':'Mounting normal mod Spine model...',
        'Esta primera versión muestra la textura real extraída del bundle. Todavía no reconstruye la animación Spine.':'Classic R3 intenta mostrar el modelo armado usando atlas + skel dentro del mismo Preview Alpha.',
        'This first version displays the real texture extracted from the bundle. It does not reconstruct the Spine animation yet.':'Classic R3 tries to render the assembled model from atlas + skel inside the same Preview Alpha.',
    }
    for rel in ['app.py','README.md','PREVIEW_NOTES.md','INSTALAR_Y_ABRIR.bat','ABRIR.bat','web/app.js','web/index.html']:
        p = root / rel
        if p.exists():
            s = p.read_text(encoding='utf-8', errors='ignore')
            for a,b in repls.items():
                s = s.replace(a,b)
            p.write_text(s, encoding='utf-8')

def patch_index(root: Path) -> None:
    p = root / 'web' / 'index.html'
    s = p.read_text(encoding='utf-8', errors='ignore')
    block = '  <script src="assets/vendor/pixi.min.js"></script>\n  <script src="assets/vendor/pixi-spine.umd.js"></script>\n  <script src="app.js"></script>'
    if 'assets/vendor/pixi.min.js' not in s:
        if '  <script src="app.js"></script>' in s:
            s = s.replace('  <script src="app.js"></script>', block)
        elif '<script src="app.js"></script>' in s:
            s = s.replace('<script src="app.js"></script>', block)
        else:
            s = s.replace('</body>', block + '\n</body>')
    p.write_text(s, encoding='utf-8')

def patch_api(root: Path) -> None:
    p = root / 'src' / 'api.py'
    s = p.read_text(encoding='utf-8', errors='ignore')
    s = s.replace('result = self.preview_engine.generate(path, item_id)', "result = self.preview_engine.generate(path, item_id, item.get('action', ''))")
    p.write_text(s, encoding='utf-8')

def copy_vendor(root: Path) -> None:
    vendor = root / 'web' / 'assets' / 'vendor'
    vendor.mkdir(parents=True, exist_ok=True)
    run(['npm','init','-y'], ROOT)
    run(['npm','install','pixi.js@6.5.10','pixi-spine@3.1.0','--no-audit','--no-fund'], ROOT)
    shutil.copy2(ROOT / 'node_modules' / 'pixi.js' / 'dist' / 'browser' / 'pixi.min.js', vendor / 'pixi.min.js')
    candidates = list((ROOT / 'node_modules' / 'pixi-spine').rglob('*umd*.js')) + list((ROOT / 'node_modules' / 'pixi-spine').rglob('pixi-spine.js')) + list((ROOT / 'node_modules' / 'pixi-spine').rglob('*.min.js'))
    if not candidates:
        raise RuntimeError('No encontre el runtime JS de pixi-spine dentro de node_modules.')
    shutil.copy2(candidates[0], vendor / 'pixi-spine.umd.js')

def write_zip() -> None:
    if ZIP.exists():
        ZIP.unlink()
    with zipfile.ZipFile(ZIP, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for p in OUT.rglob('*'):
            z.write(p, p.relative_to(DIST))

def main() -> None:
    if not SRC.exists():
        raise SystemExit(f'No existe base v0.11: {SRC}')
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    shutil.copytree(SRC, OUT)
    replace_visible_text(OUT)
    patch_index(OUT)
    patch_api(OUT)
    copy_vendor(OUT)
    (OUT / 'src' / 'preview.py').write_text(PREVIEW_PY.lstrip(), encoding='utf-8')
    (OUT / 'web' / 'app.js').write_text((OUT / 'web' / 'app.js').read_text(encoding='utf-8', errors='ignore') + APP_JS_OVERRIDE, encoding='utf-8')
    (OUT / 'VERSION.txt').write_text('NIKKE Mod Manager v0.13 Classic R3 Spine FULL\nBase real: v0.11 Preview Alpha\nInstalacion: descomprimir y ejecutar INSTALAR_Y_ABRIR.bat\nCambio principal: intenta mostrar mods normales como modelo Spine armado dentro del mismo Preview Alpha; no usa visor HTML externo.\n', encoding='utf-8')
    (OUT / 'LEEME_PRIMERO.txt').write_text('NIKKE Mod Manager v0.13 Classic R3 Spine FULL\n\nDescomprime esta carpeta en un lugar nuevo y ejecuta INSTALAR_Y_ABRIR.bat.\nMantiene la interfaz clasica de v0.11. El Preview Alpha primero intenta armar el modelo normal con atlas + skel; si falla, muestra la textura como fallback.\nLos 3DMigoto quedan para una revision posterior.\n', encoding='utf-8')
    run(['python3','-m','py_compile', str(OUT/'app.py'), str(OUT/'src/api.py'), str(OUT/'src/preview.py'), str(OUT/'src/scanner.py'), str(OUT/'src/classifier.py')], ROOT)
    assert 'spine_skel_b64' in (OUT/'src/preview.py').read_text(encoding='utf-8')
    assert 'Classic R3 Spine preview override' in (OUT/'web/app.js').read_text(encoding='utf-8')
    assert 'assets/vendor/pixi.min.js' in (OUT/'web/index.html').read_text(encoding='utf-8')
    assert (OUT/'web/assets/vendor/pixi.min.js').stat().st_size > 1000
    assert (OUT/'web/assets/vendor/pixi-spine.umd.js').stat().st_size > 1000
    write_zip()
    with zipfile.ZipFile(ZIP) as z:
        bad = z.testzip()
        if bad:
            raise RuntimeError(f'Zip corrupto en {bad}')
    print(f'OK {ZIP} {ZIP.stat().st_size} bytes')

if __name__ == '__main__':
    main()
