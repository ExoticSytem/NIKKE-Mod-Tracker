from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path


def normalize_name(value: str) -> str:
    s = unicodedata.normalize('NFKD', value or '').encode('ascii', 'ignore').decode('ascii')
    s = s.lower().strip()
    s = re.sub(r'\bnew\b$', '', s).strip()
    s = re.sub(r'\bb3\b$', '', s).strip()
    s = s.replace('&', ' and ')
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


OFFICIAL_TO_PRYDWEN = {
    'Ada': 'Ada Wong',
    'Jill': 'Jill Valentine',
    'Claire': 'Claire Redfield',
    'EVE': 'Eve',
    'Asuka': 'Asuka Shikinami Langley',
    'Asuka: WILLE': 'Asuka Shikinami Langley: Wille',
    'Mari': 'Mari Makinami Illustrious',
    'Misato': 'Misato Katsuragi',
    'Chisato': 'Chisato Nishikigi',
    'Takina': 'Takina Inoue',
    'Queen (Makoto)': 'Queen (Makoto Niijima)',
    'Product 08': 'Product-08',
    'Product 12': 'Product-12',
    'Product 23': 'Product-23',
}


class CharacterClassifier:
    def __init__(self, catalog, data_path: Path, online_path: Path | None = None):
        payload = json.loads(data_path.read_text(encoding='utf-8'))
        self.source = payload.get('source', '')
        self.last_updated = payload.get('last_updated', '')
        names = list(payload.get('names', []))
        self.online_reference_count = 0
        self.online_reference_checked = ''
        if online_path and online_path.exists():
            try:
                online = json.loads(online_path.read_text(encoding='utf-8'))
                online_names = online.get('names', []) if isinstance(online, dict) else []
                names.extend(online_names)
                self.online_reference_count = len(online_names)
                self.online_reference_checked = online.get('last_checked', '')
            except Exception:
                pass

        self.prydwen_names = names
        self._playable_norm = {normalize_name(n) for n in names}
        self._base_playable_ids: set[str] = set()

        for char in catalog.characters:
            if char.get('is_placeholder') or char.get('version') != '00':
                continue
            if self._is_exact_playable_name(char.get('name', '')):
                self._base_playable_ids.add(char['id'])

    def _is_exact_playable_name(self, official_name: str) -> bool:
        compare_name = OFFICIAL_TO_PRYDWEN.get(official_name, official_name)
        return normalize_name(compare_name) in self._playable_norm

    def is_playable_name(self, name: str) -> bool:
        """Return True when a display name matches the refreshed playable references.

        This is also used by the image resolver so legacy NPC entries that later
        became playable (for example `Velvet (NPC)`) can reuse a current HQ art
        source after stripping the explicit NPC suffix.
        """
        return self._is_exact_playable_name(name)

    def classify(self, char: dict) -> str:
        if char.get('is_placeholder'):
            return 'placeholder'
        cid = str(char.get('id', ''))
        ver = str(char.get('version', ''))
        if ver == '00' and self._is_exact_playable_name(char.get('name', '')):
            return 'nikke'
        if ver != '00' and cid in self._base_playable_ids:
            return 'skin'

        # Online additions are deliberately conservative. A freshly released
        # playable may appear in Nikke-DB before our cached playable references.
        # Do not falsely stamp it as NPC; it will be picked up by the online
        # Prydwen/Enikk refresh or can be manually overridden.
        if char.get('catalog_source') == 'nikke_db_online':
            name = str(char.get('name', ''))
            if '(npc)' in name.lower() or ' npc' in name.lower():
                return 'npc_extra'
            if cid.isdigit() and int(cid) >= 900:
                return 'npc_extra'
            return 'unknown'

        return 'npc_extra'

    def annotate(self, char: dict) -> dict:
        out = dict(char)
        out['category'] = self.classify(char)
        out['prydwen_match'] = out['category'] == 'nikke'
        return out

    @property
    def base_playable_ids(self) -> set[str]:
        return set(self._base_playable_ids)
