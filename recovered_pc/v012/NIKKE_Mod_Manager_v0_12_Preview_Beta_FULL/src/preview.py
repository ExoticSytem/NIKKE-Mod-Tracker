from __future__ import annotations

import hashlib
import io
import json
import os
import re
import struct
import zipfile
from pathlib import Path
from typing import Any, Iterable


class PreviewError(RuntimeError):
    pass


def _decrypt_aes_cbc(key: bytes, iv: bytes, payload: bytes) -> bytes:
    try:
        from Crypto.Cipher import AES
    except Exception as exc:  # pragma: no cover - dependency error is reported to UI
        raise PreviewError(
            'Falta la dependencia pycryptodome. Ejecuta INSTALAR_Y_ABRIR.bat para actualizar las dependencias.'
        ) from exc
    if len(iv) != 16:
        raise PreviewError(f'IV NKAB no compatible ({len(iv)} bytes).')
    if len(payload) % 16:
        raise PreviewError('El bloque cifrado NKAB no es multiplo de 16 bytes.')
    return AES.new(key, AES.MODE_CBC, iv=iv).decrypt(payload)


def decrypt_nkab(raw: bytes) -> tuple[bytes, int | None]:
    """Return a plain Unity bundle plus the detected NKAB version.

    NIKKE mod bundles commonly use the NKAB wrapper. Files without that wrapper
    are returned unchanged so this preview can also inspect already-unwrapped
    Unity bundles. This implementation was written independently from the file
    format behavior and does not require the token used by third-party managers.
    """
    if len(raw) < 8 or raw[:4] != b'NKAB':
        return raw, None

    version = struct.unpack_from('<I', raw, 4)[0]
    if version == 1:
        if len(raw) < 16:
            raise PreviewError('Cabecera NKAB v1 incompleta.')
        pos = 8
        header_size_raw, mode_raw, key_len_raw, encrypted_len_raw = struct.unpack_from('<hhhh', raw, pos)
        pos += 8
        header_size = header_size_raw + 100
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
    # UnityPy changed this name between versions. Support both public APIs.
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
            # Hidden VCS/cache folders are never mod payloads.
            dirs[:] = [d for d in dirs if d.lower() not in {'.git', '.svn', '__pycache__'}]
            for name in names:
                p = Path(current) / name
                # Images/readmes are useful sidecars, not the animated bundle itself.
                if p.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.txt', '.md', '.json'}:
                    continue
                files.append(p)
                if len(files) >= 300:
                    break
            if len(files) >= 300:
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
            for member in members[:200]:
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
        raise PreviewError(
            'Preview Alpha todavia no abre mods comprimidos en RAR/7Z. '
            'Descomprime ese mod o prueba uno que sea carpeta/archivo de bundle.'
        )

    try:
        yield str(target), target.read_bytes()
    except Exception as exc:
        raise PreviewError(f'No pude leer el archivo: {exc}') from exc


class ModPreviewEngine:
    """Experimental static preview for NIKKE mod bundles.

    v0.11 intentionally renders the real Texture2D atlas extracted from the
    selected mod. It does not yet reconstruct the Spine skeleton/animation.
    The goal of this alpha is to verify bundle compatibility safely before
    implementing the animated renderer.
    """

    ATLAS_NAME_RE = re.compile(r'^([0-9a-z]+)_(?:([a-z]+)_)?([0-9]+)\.atlas$', re.IGNORECASE)

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _fingerprint(path: Path, item_id: str) -> str:
        h = hashlib.sha1()
        h.update(str(path.resolve()).encode('utf-8', errors='replace'))
        h.update(str(item_id).encode('utf-8', errors='replace'))
        try:
            if path.is_file():
                st = path.stat()
                h.update(f'{st.st_size}:{st.st_mtime_ns}'.encode())
            elif path.is_dir():
                latest = 0
                total = 0
                count = 0
                for p in _folder_candidates(path)[:40]:
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

    def generate(self, target: Path, item_id: str) -> dict[str, Any]:
        cache_key = self._fingerprint(target, item_id)
        image_path = self.output_dir / f'{cache_key}.png'
        meta_path = self.output_dir / f'{cache_key}.json'
        if image_path.exists() and meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding='utf-8'))
                if isinstance(meta, dict):
                    meta['cached'] = True
                    meta['preview_url'] = f'assets/previews/{image_path.name}'
                    return meta
            except Exception:
                pass

        try:
            import UnityPy
        except Exception as exc:  # pragma: no cover
            raise PreviewError(
                'Falta UnityPy. Cierra la app y ejecuta INSTALAR_Y_ABRIR.bat para instalar las nuevas dependencias.'
            ) from exc

        attempts: list[str] = []
        last_error: Exception | None = None
        for source_name, raw in _raw_candidates(target):
            if not raw:
                continue
            attempts.append(source_name)
            try:
                plain, nkab_version = decrypt_nkab(raw)
                env = UnityPy.load(plain)

                textures: list[tuple[int, Any, str, int, int]] = []
                atlas_names: list[str] = []
                skel_names: list[str] = []
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
                            textures.append((max(1, width) * max(1, height), data, _texture_name(data), width, height))
                        except Exception:
                            continue
                    elif type_name == 'TextAsset':
                        try:
                            data = _object_data(obj)
                            name = _text_asset_name(data)
                            lname = name.lower()
                            if '.atlas' in lname:
                                atlas_names.append(name)
                                m = self.ATLAS_NAME_RE.match(name)
                                if m:
                                    character_id = m.group(1)
                                    pose = m.group(2) or 'idle'
                                    try:
                                        skin_key = int(m.group(3))
                                    except Exception:
                                        skin_key = None
                            elif '.skel' in lname:
                                skel_names.append(name)
                        except Exception:
                            continue

                if not textures:
                    raise PreviewError('El bundle se abrio, pero no contiene Texture2D que pueda mostrar.')

                textures.sort(key=lambda x: x[0], reverse=True)
                _, texture, texture_name, width, height = textures[0]
                image = texture.image
                if image is None:
                    raise PreviewError('UnityPy encontro la textura pero no pudo convertirla a imagen.')
                # Normalize to a PNG-compatible mode without altering the atlas layout.
                if image.mode not in {'RGB', 'RGBA'}:
                    image = image.convert('RGBA')
                image.save(image_path, format='PNG', optimize=True)

                result: dict[str, Any] = {
                    'ok': True,
                    'preview_url': f'assets/previews/{image_path.name}',
                    'cached': False,
                    'source_file': source_name,
                    'nkab_version': nkab_version,
                    'texture_name': texture_name,
                    'texture_width': width,
                    'texture_height': height,
                    'texture_count': len(textures),
                    'atlas_names': atlas_names[:12],
                    'skeleton_names': skel_names[:12],
                    'character_id_detected': character_id,
                    'pose_detected': pose,
                    'skin_key_detected': skin_key,
                    'attempted_files': len(attempts),
                    'preview_kind': 'texture_atlas_alpha',
                    'warning': (
                        'Vista previa experimental: esta primera version muestra la textura real del mod. '
                        'Todavia no reconstruye el esqueleto/animacion Spine.'
                    ),
                }
                meta_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
                return result
            except Exception as exc:
                last_error = exc
                continue

        detail = str(last_error) if last_error else 'ningun archivo candidato pudo abrirse'
        raise PreviewError(
            f'No pude extraer una textura compatible de este mod. Ultimo error: {detail}'
        )
