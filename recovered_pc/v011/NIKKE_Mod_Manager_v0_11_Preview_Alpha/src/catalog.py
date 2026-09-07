from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


def _sort_key(char: dict):
    cid = str(char.get('id', ''))
    ver = str(char.get('version', ''))
    return (
        0 if cid.isdigit() else 1,
        int(cid) if cid.isdigit() else cid,
        int(ver) if ver.isdigit() else 999,
        ver,
        str(char.get('name', '')).lower(),
    )


class Catalog:
    """Catalog with a protected local baseline plus optional online additions.

    data/characters.json stays authoritative for every key it contains.  The online
    overlay can only add missing ID+Ver combinations; it never overwrites the
    user's baseline names.
    """

    def __init__(self, path: Path, online_path: Path | None = None):
        self.path = path
        self.online_path = online_path
        payload = json.loads(path.read_text(encoding='utf-8'))
        self.base_version = payload.get('catalog_version', '')
        self.base_characters: List[dict] = [dict(c, catalog_source='official') for c in payload['characters']]

        merged: Dict[str, dict] = {c['key']: c for c in self.base_characters}
        self.online_meta: dict = {}
        self.online_characters: List[dict] = []

        if online_path and online_path.exists():
            try:
                online = json.loads(online_path.read_text(encoding='utf-8'))
                self.online_meta = {k: v for k, v in online.items() if k != 'characters'}
                for raw in online.get('characters', []):
                    c = dict(raw)
                    key = c.get('key')
                    if not key or key in merged:
                        continue
                    c.setdefault('catalog_source', 'nikke_db_online')
                    c.setdefault('is_placeholder', False)
                    self.online_characters.append(c)
                    merged[key] = c
            except Exception:
                self.online_meta = {}
                self.online_characters = []

        self.characters = sorted(merged.values(), key=_sort_key)
        self.by_key = {c['key']: c for c in self.characters}
        self.version = self.base_version
        if self.online_characters:
            self.version = f"{self.base_version}+online.{len(self.online_characters)}"

    def get(self, character_id: str, version: str) -> dict | None:
        return self.by_key.get(f'{character_id}_{version}')
