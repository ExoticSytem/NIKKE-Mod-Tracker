from __future__ import annotations

import json
import re
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

NIKKE_DB_L2D_URL = (
    'https://raw.githubusercontent.com/Nikke-db/Nikke-db.github.io/'
    'main/js/json/l2d.json'
)
ID_RE = re.compile(r'^c(?P<id>\d{3,4})(?:_(?P<ver>\d{2}))?$')
PLACEHOLDER_NAME_RE = re.compile(r'^c\d{3,4}(?:_\d{2})?$', re.IGNORECASE)


def _norm(value: str) -> str:
    s = unicodedata.normalize('NFKD', value or '').encode('ascii', 'ignore').decode('ascii')
    s = s.lower().replace('_', ' ').strip()
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def _looks_usable_name(name: str) -> bool:
    n = (name or '').strip()
    if not n or PLACEHOLDER_NAME_RE.fullmatch(n):
        return False
    lower = n.lower()
    if lower.endswith('_old') or lower.endswith(' old') or '_old_' in lower:
        return False
    return True


def read_overlay(path: Path) -> dict:
    if not path.exists():
        return {
            'source': NIKKE_DB_L2D_URL,
            'last_checked': '',
            'source_entries': 0,
            'characters': [],
        }
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(payload, dict):
            raise ValueError('overlay must be an object')
        payload.setdefault('source', NIKKE_DB_L2D_URL)
        payload.setdefault('last_checked', '')
        payload.setdefault('source_entries', 0)
        payload.setdefault('characters', [])
        return payload
    except Exception:
        return {
            'source': NIKKE_DB_L2D_URL,
            'last_checked': '',
            'source_entries': 0,
            'characters': [],
        }


def is_stale(path: Path, hours: int = 24) -> bool:
    payload = read_overlay(path)
    stamp = payload.get('last_checked') or ''
    if not stamp:
        return True
    try:
        checked = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
        if checked.tzinfo is None:
            checked = checked.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - checked.astimezone(timezone.utc)
        return age.total_seconds() >= hours * 3600
    except Exception:
        return True


def fetch_entries(timeout: int = 10) -> list[dict]:
    req = urllib.request.Request(
        NIKKE_DB_L2D_URL,
        headers={'User-Agent': 'NIKKE-Mod-Library/0.5'},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode('utf-8')
    payload = json.loads(raw)
    if not isinstance(payload, list):
        raise ValueError('Nikke-DB catalog response is not a list')
    return payload


def _project_version(cid: str, remote_ver: str, name: str, current_characters: list[dict], remote_entries: list[dict]) -> str:
    """Project a Nikke-DB L2D suffix onto the user's official Ver numbering.

    Nikke-DB preserves some legacy entries (for example Rapi_old) which can shift
    cosmetic suffixes. We use exact-name matches already present in the official
    catalog as anchors, then continue the numbering from the newest known anchor.
    This keeps future additions aligned with the user's ID + Ver convention.
    """
    if not remote_ver.isdigit():
        return remote_ver
    rv = int(remote_ver)
    same_id = [c for c in current_characters if str(c.get('id')) == cid]
    if not same_id:
        return f'{rv:02d}'

    # If this exact name already exists, return its official version immediately.
    target_norm = _norm(name)
    for c in same_id:
        if _norm(str(c.get('name', ''))) == target_norm:
            return str(c.get('version', remote_ver)).zfill(2)

    anchors: list[tuple[int, int]] = []
    official_by_name = {
        _norm(str(c.get('name', ''))): int(str(c.get('version', '0')))
        for c in same_id
        if str(c.get('version', '')).isdigit() and c.get('name')
    }
    for entry in remote_entries:
        if not isinstance(entry, dict):
            continue
        m = ID_RE.fullmatch(str(entry.get('id', '')).strip())
        if not m or m.group('id') != cid:
            continue
        rver = int(m.group('ver') or '00')
        off = official_by_name.get(_norm(str(entry.get('name', ''))))
        if off is not None:
            anchors.append((rver, off))

    if anchors:
        # Use the newest matching asset at/before the new remote suffix. This
        # naturally skips legacy insertions such as c010_01 Rapi_old.
        eligible = [a for a in anchors if a[0] <= rv]
        anchor = max(eligible or anchors, key=lambda x: x[0])
        projected = anchor[1] + (rv - anchor[0])
        if projected >= 0:
            return f'{projected:02d}'
    return f'{rv:02d}'


def merge_online_catalog(base_characters: list[dict], overlay_path: Path, remote_entries: list[dict]) -> dict:
    """Add only new, plausible entries; never overwrite baseline or prior additions.

    The user's catalog remains authoritative. Nikke-DB is used as a discovery
    feed, and its cosmetic suffixes are projected onto the official numbering
    using exact-name anchors so legacy L2D entries do not shift future skins.
    """
    overlay = read_overlay(overlay_path)
    existing_online = [dict(c) for c in overlay.get('characters', [])]
    current = [dict(c) for c in base_characters]
    current.extend(existing_online)

    known_keys = {c.get('key') for c in current}
    known_names = {_norm(c.get('name', '')) for c in current if c.get('name')}

    added: list[dict] = []
    for entry in remote_entries:
        if not isinstance(entry, dict):
            continue
        remote_id = str(entry.get('id', '')).strip()
        match = ID_RE.fullmatch(remote_id)
        if not match:
            continue
        cid = match.group('id')
        remote_ver = match.group('ver') or '00'
        name = str(entry.get('name', '')).strip()
        if not _looks_usable_name(name):
            continue
        norm_name = _norm(name)
        if not norm_name or norm_name in known_names:
            continue

        ver = _project_version(cid, remote_ver, name, current, remote_entries)
        key = f'{cid}_{ver}'
        if key in known_keys:
            # Do not invent another key when projection collides. A later source
            # refresh or the user's manual catalog can resolve ambiguous legacy data.
            continue

        char = {
            'id': cid,
            'version': ver,
            'key': key,
            'name': name,
            'is_placeholder': False,
            'catalog_source': 'nikke_db_online',
            'source_id': remote_id,
            'source_version': remote_ver,
        }
        existing_online.append(char)
        current.append(char)
        added.append(char)
        known_keys.add(key)
        known_names.add(norm_name)

    overlay.update({
        'source': NIKKE_DB_L2D_URL,
        'last_checked': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'source_entries': len(remote_entries),
        'characters': existing_online,
    })
    overlay_path.parent.mkdir(parents=True, exist_ok=True)
    overlay_path.write_text(json.dumps(overlay, ensure_ascii=False, indent=2), encoding='utf-8')
    return {
        'added': added,
        'added_count': len(added),
        'online_total': len(existing_online),
        'source_entries': len(remote_entries),
        'last_checked': overlay['last_checked'],
    }

