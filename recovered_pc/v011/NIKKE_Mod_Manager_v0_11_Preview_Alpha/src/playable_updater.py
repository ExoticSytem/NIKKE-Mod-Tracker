from __future__ import annotations

import html as html_module
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .classifier import normalize_name

PRYDWEN_URL = 'https://www.prydwen.gg/nikke/characters'
ENIKK_URL = 'https://enikk.app/characters'

# We intentionally use several conservative string extractors instead of relying
# on one site's private API/schema. The result is intersected with our catalog,
# so random page labels cannot create new characters or IDs.
STRING_PATTERNS = [
    re.compile(r'"(?:name|characterName|displayName)"\s*:\s*"([^"\\]{2,100})"', re.I),
    re.compile(r'(?:alt|title)=["\']([^"\']{2,100})["\']', re.I),
]


def _fetch_text(url: str, timeout: int) -> str:
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 NIKKE-Mod-Library/0.5',
            'Accept-Language': 'en-US,en;q=0.9',
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode('utf-8', errors='replace')


def _extract_catalog_matches(page: str, catalog_characters: list[dict]) -> list[str]:
    strings: set[str] = set()
    for pattern in STRING_PATTERNS:
        for value in pattern.findall(page):
            cleaned = html_module.unescape(value).strip()
            if 2 <= len(cleaned) <= 100:
                strings.add(normalize_name(cleaned))

    # Some SSR sites render visible character text directly rather than JSON.
    # Use exact escaped-name containment only for sufficiently specific names.
    lower_page = html_module.unescape(page).lower()
    matches: list[str] = []
    for char in catalog_characters:
        name = str(char.get('name', '')).strip()
        if not name:
            continue
        n = normalize_name(name)
        if n in strings:
            matches.append(name)
            continue
        if len(n) >= 5 and name.lower() in lower_page:
            matches.append(name)
    return sorted(set(matches), key=str.lower)


def refresh_playable_reference(catalog_characters: list[dict], output_path: Path, timeout: int = 8) -> dict:
    sources = []
    all_matches: set[str] = set()
    errors: list[str] = []
    for label, url in [('Prydwen', PRYDWEN_URL), ('Enikk', ENIKK_URL)]:
        try:
            page = _fetch_text(url, timeout)
            matches = _extract_catalog_matches(page, catalog_characters)
            # Reject clearly broken/blocked pages instead of poisoning the cache.
            if len(matches) < 40:
                raise ValueError(f'only {len(matches)} catalog names recognized')
            all_matches.update(matches)
            sources.append({'name': label, 'url': url, 'matches': len(matches)})
        except Exception as exc:
            errors.append(f'{label}: {exc}')

    if all_matches:
        payload = {
            'last_checked': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'sources': sources,
            'names': sorted(all_matches, key=str.lower),
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    else:
        payload = {}

    return {
        'ok': bool(all_matches),
        'names': len(all_matches),
        'sources': sources,
        'errors': errors,
        'last_checked': payload.get('last_checked', ''),
    }
