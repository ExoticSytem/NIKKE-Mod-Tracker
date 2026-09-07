from __future__ import annotations

import hashlib
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from .catalog import Catalog

# NIKKE mod targets observed in the user's collection:
# c016_02_standing_...
# c015_00_aim_...
# c015_00_cover_...
TARGET_RE = re.compile(
    r'^c(?P<id>\d{3,4})_(?P<ver>\d{2})_(?P<action>aim|cover|standing)(?:_(?P<label>.+))?$',
    re.IGNORECASE,
)

ARCHIVE_EXTS = {'.zip', '.rar', '.7z'}


def _stable_id(path: Path) -> str:
    return hashlib.sha1(str(path.resolve()).encode('utf-8', errors='replace')).hexdigest()[:16]


def _pretty_label(label: str) -> str:
    if not label:
        return 'Mod sin nombre'
    # Keep underscores meaningful as separators, but do not rewrite the source filename.
    return re.sub(r'[-_]+', ' ', label).strip()


def _guess_author(label: str) -> tuple[str, str]:
    """Small non-authoritative helper for display only.

    The identity of a mod never depends on this guess. ID/Ver/Action do.
    """
    if not label:
        return '', 'Mod sin nombre'
    parts = label.split('_', 1)
    if len(parts) == 2 and 1 <= len(parts[0]) <= 32:
        author = parts[0].strip()
        title = _pretty_label(parts[1])
        return author, title
    return '', _pretty_label(label)


def parse_target_name(name: str, catalog: Catalog, full_path: Path | None = None, source_kind: str = 'file') -> dict | None:
    m = TARGET_RE.match(name)
    if not m:
        return None

    cid = m.group('id')
    ver = m.group('ver')
    action = m.group('action').lower()
    label = (m.group('label') or '').strip()
    key = f'{cid}_{ver}'
    char = catalog.by_key.get(key)
    author, mod_title = _guess_author(label)

    if full_path is None:
        full_path = Path(name)

    return {
        'item_id': _stable_id(full_path),
        'path': str(full_path),
        'name': name,
        'source_kind': source_kind,
        'id': cid,
        'version': ver,
        'character_key': key,
        'character_name': char['name'] if char else f'Desconocido ({cid}/{ver})',
        'catalog_match': bool(char),
        'action': action,
        'label': label,
        'author_guess': author,
        'mod_title': mod_title,
        'target_key': f'{key}|{action}',
    }


def scan_folder(root: Path, catalog: Catalog) -> list[dict]:
    root = root.expanduser().resolve()
    if not root.exists() or not root.is_dir():
        return []

    results: list[dict] = []

    for current, dirs, files in os.walk(root):
        current_path = Path(current)

        # A mod may itself be a folder named cXXX_YY_action_...
        # If so, classify the folder as one mod item and do not scan its children,
        # preventing false duplicates from files contained inside it.
        kept_dirs = []
        for d in dirs:
            parsed = parse_target_name(d, catalog, current_path / d, 'folder')
            if parsed:
                results.append(parsed)
            else:
                kept_dirs.append(d)
        dirs[:] = kept_dirs

        for filename in files:
            parsed = parse_target_name(filename, catalog, current_path / filename, 'file')
            if parsed:
                results.append(parsed)

    # Stable sorting: character, version, action, name
    results.sort(key=lambda x: (x['id'], x['version'], x['action'], x['name'].lower()))
    return results


def build_conflicts(items: Iterable[dict]) -> list[dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        groups[item['target_key']].append(item)

    conflicts = []
    for target_key, group in groups.items():
        if len(group) < 2:
            continue
        first = group[0]
        conflicts.append({
            'target_key': target_key,
            'character_key': first['character_key'],
            'character_name': first['character_name'],
            'id': first['id'],
            'version': first['version'],
            'action': first['action'],
            'count': len(group),
            'items': group,
        })

    conflicts.sort(key=lambda x: (x['character_name'].lower(), x['version'], x['action']))
    return conflicts


def character_summary(catalog: Catalog, items: list[dict], image_resolver, classifier=None) -> list[dict]:
    by_char: dict[str, list[dict]] = defaultdict(list)
    conflicts_by_target = {c['target_key']: c for c in build_conflicts(items)}
    for item in items:
        by_char[item['character_key']].append(item)

    summaries = []
    for char in catalog.characters:
        key = char['key']
        char_items = by_char.get(key, [])
        counts = {'aim': 0, 'cover': 0, 'standing': 0}
        action_conflicts = {'aim': False, 'cover': False, 'standing': False}
        for item in char_items:
            counts[item['action']] = counts.get(item['action'], 0) + 1
        for action in ('aim', 'cover', 'standing'):
            action_conflicts[action] = f'{key}|{action}' in conflicts_by_target

        image_info = image_resolver(key)
        if isinstance(image_info, str):
            image_info = {'image_url': image_info, 'image_local': bool(image_info), 'image_source': 'local' if image_info else 'none'}
        classification = classifier.annotate(char) if classifier else dict(char)
        summaries.append({
            **classification,
            'mod_count': len(char_items),
            'counts': counts,
            'action_conflicts': action_conflicts,
            'has_conflict': any(action_conflicts.values()),
            **image_info,
        })

    # Unknown catalog targets should still remain visible instead of disappearing.
    known = set(catalog.by_key)
    for key, char_items in by_char.items():
        if key in known:
            continue
        first = char_items[0]
        counts = {'aim': 0, 'cover': 0, 'standing': 0}
        action_conflicts = {'aim': False, 'cover': False, 'standing': False}
        for item in char_items:
            counts[item['action']] += 1
        for action in counts:
            action_conflicts[action] = f'{key}|{action}' in conflicts_by_target
        image_info = image_resolver(key)
        if isinstance(image_info, str):
            image_info = {'image_url': image_info, 'image_local': bool(image_info), 'image_source': 'local' if image_info else 'none'}
        summaries.append({
            'id': first['id'],
            'version': first['version'],
            'key': key,
            'name': first['character_name'],
            'is_placeholder': False,
            'category': 'npc_extra',
            'prydwen_match': False,
            'mod_count': len(char_items),
            'counts': counts,
            'action_conflicts': action_conflicts,
            'has_conflict': any(action_conflicts.values()),
            **image_info,
            'unknown_catalog': True,
        })

    return summaries
