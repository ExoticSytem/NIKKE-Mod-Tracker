from __future__ import annotations
from PIL import Image

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



def _atlas_page_names(text: str) -> list[str]:
    pages: list[str] = []
    lines = [ln.strip() for ln in (text or '').splitlines()]
    for i, ln in enumerate(lines):
        if not ln or ':' in ln:
            continue
        low = ln.lower()
        if low.endswith(('.png', '.jpg', '.jpeg', '.webp')):
            pages.append(Path(ln).name)
            continue
        # Spine pages are normally followed by size/format/filter/repeat lines.
        look = '\n'.join(lines[i+1:i+5]).lower()
        if ('size:' in look or 'filter:' in look or 'format:' in look) and not any(c.isspace() for c in ln):
            pages.append(Path(ln).name)
    out: list[str] = []
    for p in pages:
        if p and p not in out:
            out.append(p)
    return out


def _atlas_needed_canvas(text: str) -> tuple[int, int]:
    """Return the minimum canvas the atlas needs.

    NIKKE atlases sometimes reference an original/padded texture area larger than
    the decoded PNG returned by UnityPy. Padding the image avoids Pixi's
    'frame does not fit inside base Texture dimensions' error.
    """
    max_w = 0
    max_h = 0
    for m in re.finditer(r'(?mi)^\s*size:\s*(\d+)\s*,\s*(\d+)\s*$', text or ''):
        try:
            w, h = int(m.group(1)), int(m.group(2))
            if 0 < w <= 16384 and 0 < h <= 16384:
                max_w = max(max_w, w)
                max_h = max(max_h, h)
        except Exception:
            pass
    lines = (text or '').splitlines()
    for i, line in enumerate(lines):
        mxy = re.match(r'\s*xy:\s*(-?\d+)\s*,\s*(-?\d+)\s*$', line)
        if not mxy:
            continue
        x, y = int(mxy.group(1)), int(mxy.group(2))
        for j in range(i + 1, min(i + 8, len(lines))):
            ms = re.match(r'\s*size:\s*(\d+)\s*,\s*(\d+)\s*$', lines[j])
            if ms:
                w, h = int(ms.group(1)), int(ms.group(2))
                max_w = max(max_w, x + w)
                max_h = max(max_h, y + h)
                break
    return max_w, max_h


def _pad_image_to(img, width: int, height: int):
    if width <= img.width and height <= img.height:
        return img
    width = max(width, img.width)
    height = max(height, img.height)
    canvas = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    canvas.paste(img, (0, 0))
    return canvas


_ATLAS_ATTR_LINE_RE = re.compile(r'^\s*[A-Za-z_]+\s*:')
_ATLAS_BOUNDS_RE = re.compile(r'^\s*bounds\s*:\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*$', re.IGNORECASE)
_ATLAS_PAGE_SIZE_RE = re.compile(r'^\s*size\s*:\s*(\d+)\s*,\s*(\d+)\s*$', re.IGNORECASE)
_ATLAS_JUNK_PREFIX_RE = re.compile(r'(?i)^(tmwalls|wmtpn|wmtpg)')
_ATLAS_JUNK_REPEAT_RE = re.compile(r'^(.)\1{5,}')
_ATLAS_UPPERCASE_RE = re.compile(r'[A-Z]')


def _looks_like_junk_region_name(name: str) -> bool:
    """Flag atlas region names that are almost certainly not real Spine
    attachments, based on patterns observed in actual NIKKE swap-mod atlases:
    every legitimate slot/attachment name we've seen (arm_t_l, calf_r,
    hair_10, eye_l3, mouth_ex_01, ...) is plain lowercase + digits +
    underscores. Entries with a mixed-case/random-looking name (and, in
    practice, a couple of recurring prefixes) that also blow far past the
    texture bounds are injected data - not geometry - and safe to drop.
    """
    if _ATLAS_JUNK_PREFIX_RE.match(name):
        return True
    if _ATLAS_JUNK_REPEAT_RE.match(name):
        return True
    if _ATLAS_UPPERCASE_RE.search(name):
        return True
    return False


def _sanitize_atlas(text: str, tex_w: int, tex_h: int) -> tuple[str, int, int, list[str]]:
    """Validate and clean a NIKKE-style Spine atlas.

    NIKKE bundles use per-region ``bounds:x,y,w,h`` lines (not the classic
    libGDX ``xy:``/``size:`` pair), so the previous canvas-sizing code never
    matched a single real region and effectively did nothing. Real NIKKE
    swap-mod atlases we've seen also occasionally carry a handful of regions
    whose frame goes far outside the exported texture - garbage/injected
    entries with nonsense names, not real Spine attachments - which is what
    actually triggers the runtime's "frame does not fit inside the base
    Texture dimensions" error.

    This walks the atlas region-by-region against the *real* exported
    texture size and:
      - keeps regions that fit,
      - grows the canvas a bounded amount for regions that overflow only
        slightly (a legitimate trim/rounding difference from the packer),
      - drops regions that overflow far past that tolerance instead of
        blowing the canvas up to fit obvious junk data.

    Returns ``(clean_atlas_text, canvas_width, canvas_height, dropped_names)``.
    """
    if not text:
        return text, tex_w, tex_h, []
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    if not lines:
        return text, tex_w, tex_h, []

    # Header = page filename (line 0) plus any immediately-following
    # attribute lines (size:, filter:, pma:, repeat:, format:) that precede
    # the first region name.
    header: list[str] = [lines[0]]
    idx = 1
    page_w, page_h = tex_w, tex_h
    while idx < len(lines):
        ln = lines[idx]
        if ln.strip() == '':
            header.append(ln)
            idx += 1
            continue
        if _ATLAS_ATTR_LINE_RE.match(ln):
            m = _ATLAS_PAGE_SIZE_RE.match(ln.strip())
            if m:
                page_w, page_h = int(m.group(1)), int(m.group(2))
            header.append(ln)
            idx += 1
            continue
        break

    # Group the rest into per-region blocks: a non-attribute line starts a
    # new region, every attribute line right after it belongs to that region.
    blocks: list[list[str]] = []
    while idx < len(lines):
        ln = lines[idx]
        if ln.strip() == '':
            idx += 1
            continue
        block = [ln]
        idx += 1
        while idx < len(lines) and (lines[idx].strip() == '' or _ATLAS_ATTR_LINE_RE.match(lines[idx])):
            if lines[idx].strip() != '':
                block.append(lines[idx])
            idx += 1
        blocks.append(block)

    needed_w, needed_h = page_w, page_h
    dropped: list[str] = []
    kept_blocks: list[list[str]] = []

    for block in blocks:
        name = block[0].strip()
        bounds = None
        for ln in block[1:]:
            m = _ATLAS_BOUNDS_RE.match(ln)
            if m:
                bounds = tuple(int(g) for g in m.groups())
                break
        if bounds is None:
            # Couldn't validate (unexpected shape) - keep untouched rather
            # than risk dropping a legitimate attachment.
            kept_blocks.append(block)
            continue
        x, y, w, h = bounds
        if x < 0 or y < 0:
            dropped.append(name)
            continue
        over_x = max(0, x + w - page_w)
        over_y = max(0, y + h - page_h)
        if over_x == 0 and over_y == 0:
            kept_blocks.append(block)
            continue
        # A region that overflows: keep + pad the canvas for a plausible
        # packer-rounding difference (a legitimately-named region that
        # overflows by less than half the page dimension); drop anything
        # that looks like injected data, or that overflows so far it can
        # only be garbage (>= the full page dimension again).
        extreme = over_x >= page_w or over_y >= page_h
        moderate = over_x > page_w * 0.5 or over_y > page_h * 0.5
        if extreme or moderate or _looks_like_junk_region_name(name):
            dropped.append(name)
            continue
        needed_w = max(needed_w, x + w)
        needed_h = max(needed_h, y + h)
        kept_blocks.append(block)

    if needed_w != page_w or needed_h != page_h:
        new_header = []
        replaced = False
        for ln in header:
            if not replaced and _ATLAS_PAGE_SIZE_RE.match(ln.strip()):
                new_header.append(f'size:{needed_w},{needed_h}')
                replaced = True
            else:
                new_header.append(ln)
        header = new_header

    out_lines = header + [ln for block in kept_blocks for ln in block]
    return '\n'.join(out_lines), needed_w, needed_h, dropped


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
        h.update(b'classic-v0-14-atlas-sanitize-001')
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
                if isinstance(meta, dict) and meta.get('preview_version') == 'classic_v0_14_integrated_viewer':
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
                # Pick the atlas first, then pick the texture that actually
                # matches its declared page name. Falling back to "largest
                # Texture2D in the bundle" (the old behaviour) can silently
                # grab the wrong page when a bundle carries more than one
                # texture, which then makes every region coordinate wrong.
                atlas_name = ''
                atlas_text = ''
                if atlases:
                    atlas_name, atlas_payload = sorted(atlases, key=lambda x: _score_asset(x[0], action), reverse=True)[0]
                    atlas_text = _decode_atlas(atlas_payload)
                primary = textures[0]
                if atlas_text:
                    probe_pages = _atlas_page_names(atlas_text)
                    if probe_pages:
                        target = Path(probe_pages[0]).stem.lower()
                        for cand in textures:
                            cand_name = str(cand['name']).lower()
                            if cand_name == target or target in cand_name or cand_name in target:
                                primary = cand
                                break
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
                # Save a cropped-looking fallback for the UI, but validate the
                # atlas against the *real* texture size for Spine: keep
                # regions that fit, pad a bounded amount for regions that
                # overflow slightly (packer rounding), and drop regions that
                # overflow far past that (garbage/injected data) instead of
                # inflating the canvas to fit them.
                spine_image = full_image
                dropped_regions: list[str] = []
                if atlas_text:
                    atlas_text, need_w, need_h, dropped_regions = _sanitize_atlas(
                        atlas_text, int(primary['width']), int(primary['height'])
                    )
                    spine_image = _pad_image_to(full_image, need_w, need_h)
                page_names = _atlas_page_names(atlas_text) if atlas_text else []
                if page_names:
                    texture_file = _clean_filename(page_names[0], texture_file)
                    if not texture_file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                        texture_file += '.png'
                full_texture_path = asset_dir / texture_file
                spine_image.save(full_texture_path, format='PNG', optimize=True)
                # Also save aliases for all atlas page names so the viewer-style Pixi loader can resolve them.
                for page in page_names:
                    alias = asset_dir / _clean_filename(Path(page).name, full_texture_path.name)
                    if alias.name != full_texture_path.name and alias.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'}:
                        try:
                            spine_image.save(alias, format='PNG', optimize=True)
                        except Exception:
                            pass
                fallback_image = full_image.copy()
                bbox = fallback_image.getbbox()
                if bbox:
                    fallback_image = fallback_image.crop(bbox)
                fallback_image.save(image_path, format='PNG', optimize=True)
                if atlas_text:
                    (asset_dir / 'model.atlas').write_text(atlas_text, encoding='utf-8', errors='replace')
                skel_name = ''
                skel_payload = b''
                if skels:
                    skel_name, skel_payload = sorted(skels, key=lambda x: _score_asset(x[0], action), reverse=True)[0]
                    (asset_dir / 'model.skel').write_bytes(skel_payload)
                warning_parts: list[str] = []
                if atlas_text and skel_payload:
                    warning_parts.append(
                        'Classic v0.14: visor integrado (runtime low-level + JS del NIKKE Spine Viewer) '
                        'con atlas saneado dentro del Preview Alpha.'
                    )
                else:
                    warning_parts.append('Fallback: este bundle no trae atlas + skel normal suficientes para armar el modelo.')
                if dropped_regions:
                    shown = ', '.join(dropped_regions[:8])
                    more = f' (+{len(dropped_regions) - 8} más)' if len(dropped_regions) > 8 else ''
                    warning_parts.append(
                        f'Se ignoraron {len(dropped_regions)} región(es) del atlas que excedían la textura real '
                        f'(datos inválidos o inyectados, no son geometría del modelo): {shown}{more}.'
                    )
                result: dict[str, Any] = {
                    'ok': True,
                    'preview_version': 'classic_v0_14_integrated_viewer',
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
                    'preview_kind': 'classic_v0_14_integrated_viewer' if atlas_text and skel_payload else 'texture_fallback',
                    'spine_ready': bool(atlas_text and skel_payload),
                    'spine_canvas': bool(atlas_text and skel_payload),
                    'spine_texture_url': f'assets/previews/{asset_dir.name}/{full_texture_path.name}',
                    'spine_atlas_url': f'assets/previews/{asset_dir.name}/model.atlas' if atlas_text else '',
                    'spine_skel_url': f'assets/previews/{asset_dir.name}/model.skel' if skel_payload else '',
                    'spine_atlas_text': atlas_text,
                    'spine_skel_b64': base64.b64encode(skel_payload).decode('ascii') if skel_payload else '',
                    'spine_canvas_width': int(spine_image.width) if atlas_text else int(full_image.width),
                    'spine_canvas_height': int(spine_image.height) if atlas_text else int(full_image.height),
                    'spine_atlas_pages': page_names,
                    'spine_atlas_name': atlas_name,
                    'spine_skel_name': skel_name,
                    'spine_dropped_regions': dropped_regions,
                    'action_hint': action,
                    'warning': ' '.join(warning_parts),
                }
                meta_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
                return result
            except Exception as exc:
                last_error = exc
                continue
        detail = str(last_error) if last_error else 'ningun archivo candidato pudo abrirse'
        raise PreviewError(f'No pude extraer datos compatibles de este mod. Ultimo error: {detail}')

# --- NMM v0.14.3 Atlas PreserveFix -----------------------------------------
# Do not delete atlas regions by suspicious names: the .skel may still need them.
# Preserve the original atlas and expand the transparent Spine canvas instead.
try:
    _nmm_v0143_original_sanitize_atlas = _sanitize_atlas
except NameError:
    _nmm_v0143_original_sanitize_atlas = None
import re as _nmm_v0143_re

def _nmm_v0143_needed_canvas(atlas_text, base_w=0, base_h=0, hard_limit=8192):
    text = atlas_text or ''
    bw = int(base_w or 0)
    bh = int(base_h or 0)
    m = _nmm_v0143_re.search(r'(?im)^\s*size\s*:\s*(-?\d+)\s*,\s*(-?\d+)\s*$', text)
    if (bw <= 0 or bh <= 0) and m:
        bw, bh = int(m.group(1)), int(m.group(2))
    need_w, need_h = max(1, bw), max(1, bh)
    for m in _nmm_v0143_re.finditer(r'(?im)^\s*bounds\s*:\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*$', text):
        x, y, w, h = map(int, m.groups())
        if w > 0 and h > 0:
            need_w = max(need_w, x + w)
            need_h = max(need_h, y + h)
    last_xy = None
    for line in text.splitlines():
        mxy = _nmm_v0143_re.match(r'\s*xy\s*:\s*(-?\d+)\s*,\s*(-?\d+)\s*$', line)
        if mxy:
            last_xy = (int(mxy.group(1)), int(mxy.group(2)))
            continue
        ms = _nmm_v0143_re.match(r'\s*size\s*:\s*(-?\d+)\s*,\s*(-?\d+)\s*$', line)
        if ms and last_xy:
            x, y = last_xy
            w, h = int(ms.group(1)), int(ms.group(2))
            if w > 0 and h > 0:
                need_w = max(need_w, x + w)
                need_h = max(need_h, y + h)
            last_xy = None
    return max(1, min(int(need_w), hard_limit)), max(1, min(int(need_h), hard_limit))

def _nmm_v0143_base_size(args, kwargs, atlas_text):
    for wk, hk in (('texture_width','texture_height'), ('tex_width','tex_height'), ('width','height'), ('base_width','base_height'), ('image_width','image_height')):
        if isinstance(kwargs.get(wk), int) and isinstance(kwargs.get(hk), int):
            return int(kwargs[wk]), int(kwargs[hk])
    for a in args[1:]:
        if isinstance(a, (tuple, list)) and len(a) >= 2 and isinstance(a[0], int) and isinstance(a[1], int):
            return int(a[0]), int(a[1])
    ints = [int(a) for a in args[1:] if isinstance(a, int)]
    if len(ints) >= 2:
        return ints[0], ints[1]
    return _nmm_v0143_needed_canvas(atlas_text, 0, 0)

def _nmm_v0143_shape(result, atlas_text, need_w, need_h):
    if isinstance(result, dict):
        out = dict(result)
        for k in ('atlas_text', 'atlas', 'sanitized_atlas', 'spine_atlas_text'):
            if k in out: out[k] = atlas_text
        for k in ('width', 'atlas_width', 'canvas_width', 'needed_width', 'spine_width'):
            if isinstance(out.get(k), int): out[k] = need_w
        for k in ('height', 'atlas_height', 'canvas_height', 'needed_height', 'spine_height'):
            if isinstance(out.get(k), int): out[k] = need_h
        return out
    if isinstance(result, str):
        return atlas_text
    if not isinstance(result, (tuple, list)):
        return result
    seq = list(result)
    ret = tuple if isinstance(result, tuple) else list
    atlas_i = next((i for i,v in enumerate(seq) if isinstance(v, str) and ('bounds:' in v or '\nsize:' in v or '.png' in v)), None)
    if atlas_i is None:
        atlas_i = next((i for i,v in enumerate(seq) if isinstance(v, str)), None)
    if atlas_i is not None:
        seq[atlas_i] = atlas_text
    for i,v in enumerate(seq):
        if isinstance(v, tuple) and len(v) >= 2 and isinstance(v[0], int) and isinstance(v[1], int):
            seq[i] = (need_w, need_h) + tuple(v[2:])
        elif isinstance(v, list) and len(v) >= 2 and isinstance(v[0], int) and isinstance(v[1], int):
            v[0], v[1] = need_w, need_h
    start = (atlas_i + 1) if atlas_i is not None else 0
    for i in range(start, len(seq)-1):
        if isinstance(seq[i], int) and isinstance(seq[i+1], int):
            seq[i], seq[i+1] = need_w, need_h
            break
    return ret(seq)

def _sanitize_atlas(*args, **kwargs):
    atlas_text = args[0] if args and isinstance(args[0], str) else ''
    if not atlas_text:
        for k in ('atlas_text', 'atlas', 'raw_atlas'):
            if isinstance(kwargs.get(k), str):
                atlas_text = kwargs[k]
                break
    bw, bh = _nmm_v0143_base_size(args, kwargs, atlas_text)
    need_w, need_h = _nmm_v0143_needed_canvas(atlas_text, bw, bh)
    if _nmm_v0143_original_sanitize_atlas is None:
        return atlas_text, need_w, need_h, ['AtlasPreserveFix activo']
    try:
        old = _nmm_v0143_original_sanitize_atlas(*args, **kwargs)
    except Exception:
        return atlas_text, need_w, need_h, ['AtlasPreserveFix: sanitizer antiguo omitido']
    return _nmm_v0143_shape(old, atlas_text, need_w, need_h)
# --- end NMM v0.14.3 Atlas PreserveFix -------------------------------------

