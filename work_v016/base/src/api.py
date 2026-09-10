from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import re
import unicodedata
import time
import threading
import secrets
import socket
from urllib.parse import quote
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps
from send2trash import send2trash
import qrcode

from .catalog import Catalog
from .catalog_updater import is_stale, read_overlay
from .classifier import CharacterClassifier, OFFICIAL_TO_PRYDWEN, normalize_name
from .playable_updater import refresh_playable_reference
from .scanner import build_conflicts, character_summary, scan_folder
from .sync_server import MobileSyncServer
from .preview import ModPreviewEngine, PreviewError


NIKKE_DB_SPRITE_BASE = (
    'https://raw.githubusercontent.com/Nikke-db/Nikke-db.github.io/'
    'main/images/sprite'
)
NIKKE_DB_FB_BASE = (
    'https://raw.githubusercontent.com/Nikke-db/Nikke-db.github.io/'
    'main/images/FB'
)
PRYDWEN_IMAGE_BASE = 'https://cdn.prydwen.gg/images/nikke/characters'
PROJECT_RAW_ROOT = 'https://raw.githubusercontent.com/ExoticSytem/NIKKE-Mod-Tracker/main'
PROJECT_IMAGE_MANIFEST = f'{PROJECT_RAW_ROOT}/assets/characters/manifest.json'
PROJECT_CLASSIFICATION_OVERRIDES = f'{PROJECT_RAW_ROOT}/admin/catalog_overrides.json'
PROJECT_DISCOVERED_CATALOG = f'{PROJECT_RAW_ROOT}/catalog/discovered.json'


class AppAPI:
    def __init__(self, root: Path):
        self.root = root
        self.window = None
        self.base_catalog_path = root / 'data' / 'characters.json'
        self.online_catalog_path = root / 'data' / 'catalog_online.json'
        self.prydwen_path = root / 'data' / 'prydwen_playable.json'
        self.playable_online_path = root / 'data' / 'playable_online.json'
        self.manual_images_path = root / 'data' / 'manual_images.json'
        self.tags_path = root / 'data' / 'character_tags.json'
        self.tag_sync_meta_path = root / 'data' / 'tag_sync_meta.json'
        self.settings_path = root / 'data' / 'settings.json'
        self.images_dir = root / 'web' / 'assets' / 'characters'
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.previews_dir = root / 'web' / 'assets' / 'previews'
        self.previews_dir.mkdir(parents=True, exist_ok=True)
        self.preview_engine = ModPreviewEngine(self.previews_dir)

        self._lock = threading.RLock()
        self.settings = self._load_settings()
        self.manual_image_keys = set(self._load_json_list(self.manual_images_path))
        self.character_tags = self._load_tags()
        self.tag_sync_meta = self._load_tag_sync_meta()
        self._ensure_tag_meta_for_existing_tags()
        self.catalog_update_status: dict[str, Any] = {}
        self._auto_update_attempted = False
        self._project_images: dict[str, list[str]] = {}
        self._project_manifest_checked_at = 0.0
        self._project_npc_overrides: dict[str, bool] = {}
        self._project_character_status: dict[str, str] = {}
        self._project_classification_checked_at = 0.0
        self.items: list[dict] = []
        self._reload_catalog()
        if self.settings.get('mods_folder'):
            self._scan()
        self.sync_server = MobileSyncServer(
            self.settings['mobile_sync_token'],
            self._mobile_snapshot,
            self._merge_mobile_tags,
            self._record_mobile_sync,
        )
        try:
            self.sync_server.start(int(self.settings.get('mobile_sync_port', 8765) or 8765))
            self.settings['mobile_sync_port'] = self.sync_server.port
            self._save_settings()
            self._write_pair_qr()
        except Exception as exc:
            self.settings['mobile_sync_error'] = str(exc)
            self._save_settings()

    def attach_window(self, window) -> None:
        self.window = window

    # --- persistence ---
    def _load_settings(self) -> dict:
        defaults = {
            'settings_version': 6,
            'mods_folder': '',
            'onboarding_complete': False,
            'default_character_filter': 'all',
            'language': 'es',
            'character_sort': 'id_asc',
            'auto_catalog_updates': True,
            'mobile_sync_token': secrets.token_urlsafe(24),
            'mobile_sync_port': 8765,
            'mobile_sync_last': '',
            'mobile_sync_error': '',
        }
        loaded: dict = {}
        if self.settings_path.exists():
            try:
                loaded = json.loads(self.settings_path.read_text(encoding='utf-8'))
            except Exception:
                loaded = {}
        old_version = int(loaded.get('settings_version', 0) or 0)
        defaults.update(loaded)
        # v0.4 changed the first screen to show the whole catalog by default.
        if old_version < 4:
            defaults['default_character_filter'] = 'all'
        if old_version < 6:
            defaults['settings_version'] = 6
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings_path.write_text(json.dumps(defaults, ensure_ascii=False, indent=2), encoding='utf-8')
        return defaults

    def _save_settings(self) -> None:
        self.settings_path.write_text(json.dumps(self.settings, ensure_ascii=False, indent=2), encoding='utf-8')

    @staticmethod
    def _load_json_object(path: Path) -> dict:
        try:
            payload = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def _load_json_list(path: Path) -> list:
        try:
            payload = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
            return payload if isinstance(payload, list) else []
        except Exception:
            return []

    def _save_manual_images(self) -> None:
        self.manual_images_path.write_text(
            json.dumps(sorted(self.manual_image_keys), ensure_ascii=False, indent=2), encoding='utf-8'
        )

    def _load_tags(self) -> dict[str, list[str]]:
        raw = self._load_json_object(self.tags_path)
        clean: dict[str, list[str]] = {}
        for key, values in raw.items():
            if not isinstance(key, str) or not isinstance(values, list):
                continue
            tags = []
            seen = set()
            for value in values:
                tag = str(value).strip()[:40]
                norm = tag.casefold()
                if tag and norm not in seen:
                    tags.append(tag)
                    seen.add(norm)
            if tags:
                clean[key] = sorted(tags, key=str.casefold)
        return clean

    def _save_tags(self) -> None:
        self.tags_path.write_text(
            json.dumps(self.character_tags, ensure_ascii=False, indent=2), encoding='utf-8'
        )

    def _load_tag_sync_meta(self) -> dict[str, dict[str, dict[str, Any]]]:
        raw = self._load_json_object(self.tag_sync_meta_path)
        clean: dict[str, dict[str, dict[str, Any]]] = {}
        for key, tag_map in raw.items():
            if not isinstance(key, str) or not isinstance(tag_map, dict):
                continue
            out: dict[str, dict[str, Any]] = {}
            for norm, meta in tag_map.items():
                if not isinstance(norm, str) or not isinstance(meta, dict):
                    continue
                tag = re.sub(r'\s+', ' ', str(meta.get('tag', '')).strip())[:40]
                try:
                    updated = int(meta.get('updated_at', 0) or 0)
                except Exception:
                    updated = 0
                if tag:
                    out[norm.casefold()] = {
                        'tag': tag,
                        'present': bool(meta.get('present', False)),
                        'updated_at': updated,
                    }
            if out:
                clean[key] = out
        return clean

    def _save_tag_sync_meta(self) -> None:
        self.tag_sync_meta_path.write_text(
            json.dumps(self.tag_sync_meta, ensure_ascii=False, indent=2), encoding='utf-8'
        )

    def _ensure_tag_meta_for_existing_tags(self) -> None:
        changed = False
        now = int(time.time() * 1000)
        for key, values in self.character_tags.items():
            bucket = self.tag_sync_meta.setdefault(key, {})
            for tag in values:
                norm = tag.casefold()
                if norm not in bucket:
                    bucket[norm] = {'tag': tag, 'present': True, 'updated_at': now}
                    changed = True
        if changed:
            self._save_tag_sync_meta()

    def _rebuild_tags_from_meta(self) -> None:
        result: dict[str, list[str]] = {}
        for key, bucket in self.tag_sync_meta.items():
            values = [
                str(meta.get('tag', '')).strip()
                for meta in bucket.values()
                if isinstance(meta, dict) and bool(meta.get('present')) and str(meta.get('tag', '')).strip()
            ]
            if values:
                result[key] = sorted(dict.fromkeys(values), key=str.casefold)
        self.character_tags = result
        self._save_tags()

    @staticmethod
    def _lan_ip() -> str:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(('8.8.8.8', 80))
            ip = sock.getsockname()[0]
            if ip and not ip.startswith('127.'):
                return ip
        except Exception:
            pass
        finally:
            sock.close()
        try:
            ip = socket.gethostbyname(socket.gethostname())
            if ip and not ip.startswith('127.'):
                return ip
        except Exception:
            pass
        return '127.0.0.1'

    def _mobile_sync_info(self) -> dict[str, Any]:
        port = getattr(getattr(self, 'sync_server', None), 'port', 0) or int(self.settings.get('mobile_sync_port', 8765) or 8765)
        ip = self._lan_ip()
        host = f'http://{ip}:{port}'
        token = self.settings.get('mobile_sync_token', '')
        pair_uri = f'nikkemodtracker://pair?host={quote(host, safe="")}&token={quote(token, safe="")}&name={quote("NIKKE Mod Library PC", safe="")}'
        qr = self.root / 'web' / 'assets' / 'mobile_pair_qr.png'
        return {
            'enabled': bool(getattr(getattr(self, 'sync_server', None), 'port', 0)),
            'host': host,
            'port': port,
            'pair_uri': pair_uri,
            'qr_url': f'assets/mobile_pair_qr.png?v={int(qr.stat().st_mtime)}' if qr.exists() else '',
            'last_sync': self.settings.get('mobile_sync_last', ''),
            'error': self.settings.get('mobile_sync_error', ''),
        }

    def _write_pair_qr(self) -> None:
        info = self._mobile_sync_info()
        if not info.get('pair_uri'):
            return
        target = self.root / 'web' / 'assets' / 'mobile_pair_qr.png'
        img = qrcode.make(info['pair_uri'])
        img.save(target)

    def _record_mobile_sync(self) -> None:
        with self._lock:
            self.settings['mobile_sync_last'] = time.strftime('%Y-%m-%d %H:%M:%S')
            self._save_settings()
        if self.window is not None:
            try:
                self.window.evaluate_js("window.dispatchEvent(new Event('nikke-mobile-sync'))")
            except Exception:
                pass

    def _mobile_inventory(self) -> dict[str, Any]:
        state = self._state()
        by_key: dict[str, dict[str, Any]] = {}
        chars = {c['key']: c for c in state.get('characters', [])}
        for key, char in chars.items():
            by_key[key] = {
                'name': char.get('name', ''),
                'id': char.get('id', ''),
                'version': char.get('version', ''),
                'is_npc_extra': bool(char.get('is_npc_extra')),
                'mods': [],
                'counts': {'aim': 0, 'cover': 0, 'standing': 0},
                'conflicts': [],
            }
        for item in state.get('items', []):
            key = item.get('character_key', '')
            entry = by_key.setdefault(key, {
                'name': item.get('character_name', key), 'id': '', 'version': '',
                'is_npc_extra': bool(item.get('is_npc_extra')), 'mods': [],
                'counts': {'aim': 0, 'cover': 0, 'standing': 0}, 'conflicts': [],
            })
            action = item.get('action', '')
            if action in entry['counts']:
                entry['counts'][action] += 1
            name = item.get('mod_title') or item.get('name') or Path(str(item.get('path', ''))).name
            entry['mods'].append({
                'name': str(name or ''),
                'action': action,
                'author': str(item.get('author_guess', '') or item.get('author', '') or ''),
                'file_name': Path(str(item.get('path', '') or '')).name,
                'conflict': bool(item.get('conflict')),
            })
        for conflict in state.get('conflicts', []):
            target = str(conflict.get('target_key', ''))
            if '|' in target:
                parts = target.split('|')
                key = parts[0]
                action = parts[-1]
            else:
                key = str(conflict.get('character_key', ''))
                action = str(conflict.get('action', ''))
            if key in by_key and action and action not in by_key[key]['conflicts']:
                by_key[key]['conflicts'].append(action)
        # Send only entries with mods; Android already carries the public catalog.
        return {k: v for k, v in by_key.items() if sum(v['counts'].values()) > 0}

    def _mobile_snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                'ok': True,
                'protocol': 1,
                'generated_at': int(time.time() * 1000),
                'catalog_version': self.catalog.version,
                'inventory': self._mobile_inventory(),
                'tags': self.tag_sync_meta,
            }

    def _merge_mobile_tags(self, incoming: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            changed = 0
            for key, tag_map in incoming.items():
                if not isinstance(key, str) or not isinstance(tag_map, dict):
                    continue
                bucket = self.tag_sync_meta.setdefault(key, {})
                for norm, meta in tag_map.items():
                    if not isinstance(meta, dict):
                        continue
                    tag = re.sub(r'\s+', ' ', str(meta.get('tag', '')).strip())[:40]
                    if not tag:
                        continue
                    try:
                        updated = int(meta.get('updated_at', 0) or 0)
                    except Exception:
                        updated = 0
                    normalized = str(norm or tag).casefold()
                    current = bucket.get(normalized)
                    current_updated = int(current.get('updated_at', 0) or 0) if isinstance(current, dict) else -1
                    if updated > current_updated:
                        bucket[normalized] = {'tag': tag, 'present': bool(meta.get('present', False)), 'updated_at': updated}
                        changed += 1
            if changed:
                self._save_tag_sync_meta()
                self._rebuild_tags_from_meta()
            return {'changed': changed}

    def _reload_catalog(self) -> None:
        self.catalog = Catalog(self.base_catalog_path, self.online_catalog_path)
        self.classifier = CharacterClassifier(self.catalog, self.prydwen_path, self.playable_online_path)
        self.prydwen_meta = json.loads(self.prydwen_path.read_text(encoding='utf-8'))

    # --- catalog updates ---
    def _refresh_project_catalog_additions(self, force: bool = False) -> dict:
        """Download only owner-approved additions from the public project catalog.

        Upstream discovery is performed centrally by GitHub Actions. Entries marked
        needs_review stay invisible to player clients until the project owner assigns
        a global Playable or NPC/Extra classification, which creates an override.
        The protected bundled catalog is never renamed or overwritten.
        """
        if not force and not is_stale(self.online_catalog_path, hours=24):
            overlay = read_overlay(self.online_catalog_path)
            return {
                'ok': True, 'automatic': True, 'skipped': True,
                'added_count': len(overlay.get('characters', [])),
                'online_total': len(overlay.get('characters', [])),
                'source_entries': int(overlay.get('source_entries', 0) or 0),
                'last_checked': overlay.get('last_checked', ''),
            }

        self._refresh_project_classification_overrides(force=force)
        now = time.time()
        req = urllib.request.Request(
            f'{PROJECT_DISCOVERED_CATALOG}?v={int(now)}',
            headers={'User-Agent': 'NIKKE-Mod-Library/0.11-preview-alpha'},
        )
        with urllib.request.urlopen(req, timeout=8 if force else 4) as response:
            if getattr(response, 'status', 200) != 200:
                raise RuntimeError(f'Project catalog HTTP {getattr(response, "status", 0)}')
            remote = json.loads(response.read().decode('utf-8'))
        raw_chars = remote.get('characters', []) if isinstance(remote, dict) else []
        if not isinstance(raw_chars, list):
            raw_chars = []

        base_keys = {c.get('key') for c in self.catalog.base_characters}
        approved: list[dict] = []
        seen: set[str] = set()
        for raw in raw_chars:
            if not isinstance(raw, dict):
                continue
            cid = str(raw.get('id', '')).strip()
            ver = str(raw.get('version', '00')).zfill(2)
            key = str(raw.get('key') or f'{cid}_{ver}')
            name = str(raw.get('name', '')).strip()
            if not cid or not name or key in base_keys or key in seen:
                continue
            status = self._project_character_status.get(key, '')
            if status == 'discarded':
                continue
            reviewed = (
                not bool(raw.get('needs_review', False))
                or status == 'approved'
                or key in self._project_npc_overrides
            )
            if not reviewed:
                continue
            item = dict(raw)
            item.update({
                'id': cid, 'version': ver, 'key': key, 'name': name,
                'is_placeholder': False, 'catalog_source': 'project_online',
            })
            approved.append(item)
            seen.add(key)

        from datetime import datetime, timezone
        payload = {
            'source': PROJECT_DISCOVERED_CATALOG,
            'last_checked': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'source_entries': len(raw_chars),
            'pending_review': sum(
                1 for x in raw_chars if isinstance(x, dict) and bool(x.get('needs_review', False))
                and self._project_character_status.get(str(x.get('key') or f"{x.get('id','')}_{str(x.get('version','00')).zfill(2)}"), '') not in {'approved', 'discarded'}
                and str(x.get('key') or f"{x.get('id','')}_{str(x.get('version','00')).zfill(2)}") not in self._project_npc_overrides
            ),
            'characters': approved,
        }
        before = self.online_catalog_path.read_text(encoding='utf-8') if self.online_catalog_path.exists() else ''
        rendered = json.dumps(payload, ensure_ascii=False, indent=2)
        self.online_catalog_path.parent.mkdir(parents=True, exist_ok=True)
        self.online_catalog_path.write_text(rendered, encoding='utf-8')
        changed = before != rendered
        return {
            'ok': True, 'automatic': not force, 'added_count': len(approved),
            'online_total': len(approved), 'source_entries': len(raw_chars),
            'pending_review': payload['pending_review'], 'last_checked': payload['last_checked'],
            'changed': changed,
        }

    def _maybe_auto_update_catalog(self) -> None:
        if self._auto_update_attempted:
            return
        self._auto_update_attempted = True
        if not self.settings.get('auto_catalog_updates', True):
            return
        try:
            result = self._refresh_project_catalog_additions(force=False)
            self.catalog_update_status = result
            if result.get('changed'):
                self._reload_catalog()
            playable_result = refresh_playable_reference(
                self.catalog.characters, self.playable_online_path, timeout=4
            )
            result['playable_refresh'] = playable_result
            if playable_result.get('ok'):
                self._reload_catalog()
            if result.get('changed') or playable_result.get('ok'):
                self._scan()
        except Exception as exc:
            # Auto-update must never prevent the app from opening offline.
            self.catalog_update_status = {'ok': False, 'automatic': True, 'error': str(exc)}

    # --- character identity / classification ---
    def _refresh_project_classification_overrides(self, force: bool = False) -> None:
        now = time.time()
        if not force and self._project_classification_checked_at and now - self._project_classification_checked_at < 300:
            return
        self._project_classification_checked_at = now
        req = urllib.request.Request(
            f'{PROJECT_CLASSIFICATION_OVERRIDES}?v={int(now)}',
            headers={'User-Agent': 'NIKKE-Mod-Library/0.11-preview-alpha'},
        )
        try:
            with urllib.request.urlopen(req, timeout=4) as response:
                if getattr(response, 'status', 200) != 200:
                    return
                payload = json.loads(response.read().decode('utf-8'))
            chars = payload.get('characters', {}) if isinstance(payload, dict) else {}
            if not isinstance(chars, dict):
                return
            parsed: dict[str, bool] = {}
            statuses: dict[str, str] = {}
            for key, meta in chars.items():
                if not isinstance(meta, dict):
                    continue
                skey = str(key)
                if isinstance(meta.get('npc_extra'), bool):
                    parsed[skey] = bool(meta['npc_extra'])
                status = str(meta.get('status', '')).strip().lower()
                if status in {'approved', 'discarded'}:
                    statuses[skey] = status
            self._project_npc_overrides = parsed
            self._project_character_status = statuses
        except Exception:
            # Offline keeps the built-in automatic classification.
            return

    def _effective_npc_extra(self, key: str, auto_category: str) -> tuple[bool, str]:
        self._refresh_project_classification_overrides()
        if key in self._project_npc_overrides:
            return self._project_npc_overrides[key], 'project'
        return auto_category == 'npc_extra', 'auto'

    @staticmethod
    def _split_character_key(key: str) -> tuple[str, str] | None:
        if '_' not in key:
            return None
        cid, ver = key.rsplit('_', 1)
        if not cid.isdigit() or len(cid) not in (3, 4) or not ver.isdigit() or len(ver) != 2:
            return None
        return cid, ver

    # --- images ---

    def _refresh_project_image_manifest(self, force: bool = False) -> None:
        now = time.time()
        if not force and self._project_manifest_checked_at and now - self._project_manifest_checked_at < 300:
            return
        self._project_manifest_checked_at = now
        req = urllib.request.Request(
            f'{PROJECT_IMAGE_MANIFEST}?v={int(now)}',
            headers={'User-Agent': 'NIKKE-Mod-Library/0.11-preview-alpha'},
        )
        try:
            with urllib.request.urlopen(req, timeout=4) as response:
                if getattr(response, 'status', 200) != 200:
                    return
                payload = json.loads(response.read().decode('utf-8'))
            images = payload.get('images', {}) if isinstance(payload, dict) else {}
            if isinstance(images, dict):
                self._project_images = {
                    str(k): [str(x) for x in v if isinstance(x, str)]
                    for k, v in images.items() if isinstance(v, list)
                }
        except Exception:
            # The repository can still be private. In that case external fallbacks continue normally.
            return

    def _project_image_candidates(self, key: str) -> list[tuple[str, str]]:
        self._refresh_project_image_manifest()
        result: list[tuple[str, str]] = []
        for path in self._project_images.get(key, []):
            clean = path.lstrip('/')
            source = 'project_manual' if '/manual/' in f'/{clean}' else 'project_library'
            result.append((source, f'{PROJECT_RAW_ROOT}/{clean}'))
        return result

    def _remote_sprite_url(self, key: str) -> str:
        parts = self._split_character_key(key)
        if not parts:
            return ''
        cid, ver = parts
        filename = f'si_c{cid}_00_s.png' if ver == '00' else f'si_c{cid}_{ver}_00_s.png'
        return f'{NIKKE_DB_SPRITE_BASE}/{filename}'

    def _remote_fullbody_url(self, key: str) -> str:
        parts = self._split_character_key(key)
        if not parts:
            return ''
        cid, ver = parts
        if ver != '00':
            return ''
        return f'{NIKKE_DB_FB_BASE}/c{cid}_00.png'

    @staticmethod
    def _strip_npc_suffix(name: str) -> str:
        value = (name or '').strip()
        value = re.sub(r'\s*\(NPC\)\s*$', '', value, flags=re.I)
        value = re.sub(r'\s+NPC\s*$', '', value, flags=re.I)
        return value.strip()

    @staticmethod
    def _slugify_prydwen(value: str) -> str:
        value = unicodedata.normalize('NFKD', value or '').encode('ascii', 'ignore').decode('ascii')
        value = value.lower().replace('&', ' and ')
        value = re.sub(r'[^a-z0-9]+', '-', value).strip('-')
        return re.sub(r'-+', '-', value)

    def _prydwen_image_url(self, name: str, allow_speculative: bool = False) -> str:
        canonical = self._strip_npc_suffix(name)
        if not canonical:
            return ''
        if not allow_speculative and not self.classifier.is_playable_name(canonical):
            return ''
        compare = OFFICIAL_TO_PRYDWEN.get(canonical, canonical)
        # Prydwen uses a couple of shorter slugs than their display names.
        special = {
            'Queen (Makoto)': 'queen-makoto',
            'Queen (Makoto Niijima)': 'queen-makoto',
        }
        slug = special.get(canonical) or special.get(compare) or self._slugify_prydwen(compare)
        return f'{PRYDWEN_IMAGE_BASE}/{slug}_full.webp' if slug else ''

    def _find_playable_alias_key(self, key: str, name: str) -> str:
        """Find a current playable/base entry that represents an older NPC record."""
        canonical = self._strip_npc_suffix(name)
        if canonical == name or not canonical:
            return ''
        wanted = normalize_name(OFFICIAL_TO_PRYDWEN.get(canonical, canonical))
        for char in self.catalog.characters:
            if char.get('key') == key or char.get('version') != '00' or char.get('is_placeholder'):
                continue
            candidate = self._strip_npc_suffix(str(char.get('name', '')))
            candidate = OFFICIAL_TO_PRYDWEN.get(candidate, candidate)
            if normalize_name(candidate) == wanted and self.classifier.is_playable_name(candidate):
                return str(char.get('key', ''))
        return ''

    def _remote_image_candidates(self, key: str) -> list[tuple[str, str]]:
        char = self.catalog.by_key.get(key) or {}
        name = str(char.get('name', ''))
        result: list[tuple[str, str]] = []
        seen: set[str] = set()

        def add(source: str, url: str) -> None:
            if url and url not in seen:
                result.append((source, url))
                seen.add(url)

        # Project-hosted images are the canonical first choice when available.
        # A small manifest prevents wasting time probing missing raw GitHub paths.
        for project_source, project_url in self._project_image_candidates(key):
            add(project_source, project_url)

        # Prydwen provides clean, high-resolution full art for current playable
        # characters.  The name matching also lets older NPC records reuse that
        # art after the same character later becomes playable.
        explicit_old_npc = self._strip_npc_suffix(name) != name
        add('prydwen_full', self._prydwen_image_url(name, allow_speculative=explicit_old_npc))

        # If an old NPC record maps to a current playable key and that playable art
        # was already cached locally, use it before dropping to a tiny thumbnail.
        alias_key = self._find_playable_alias_key(key, name)
        if alias_key:
            alias_local = self._local_image_path(alias_key)
            if alias_local:
                add('playable_alias_local', f'assets/characters/{alias_local.name}?v={int(alias_local.stat().st_mtime)}')
            alias_char = self.catalog.by_key.get(alias_key) or {}
            add('prydwen_alias', self._prydwen_image_url(str(alias_char.get('name', ''))))
            add('nikke_db_alias_fullbody', self._remote_fullbody_url(alias_key))

        add('nikke_db_fullbody', self._remote_fullbody_url(key))
        add('nikke_db_sprite', self._remote_sprite_url(key))
        return result

    def _local_image_path(self, key: str) -> Path | None:
        for ext in ('.webp', '.png', '.jpg', '.jpeg'):
            p = self.images_dir / f'{key}{ext}'
            if p.exists():
                return p
        return None

    def _image_info(self, key: str) -> dict:
        p = self._local_image_path(key)
        if p:
            return {
                'image_url': f'assets/characters/{p.name}?v={int(p.stat().st_mtime)}',
                'image_fallback_urls': [],
                'image_local': True,
                'image_source': 'manual' if key in self.manual_image_keys else 'local_cache',
                'image_fit': 'contain',
            }

        candidates = self._remote_image_candidates(key)
        if not candidates:
            return {
                'image_url': '', 'image_fallback_urls': [], 'image_local': False,
                'image_source': 'none', 'image_fit': 'cover'
            }
        primary_source, primary_url = candidates[0]
        fallbacks = [url for _source, url in candidates[1:]]
        return {
            'image_url': primary_url,
            'image_fallback_urls': fallbacks,
            'image_local': False,
            'image_source': primary_source,
            'image_fit': 'contain' if 'full' in primary_source or 'prydwen' in primary_source else 'cover',
        }

    # --- scanning / state ---
    def _scan(self) -> None:
        folder = self.settings.get('mods_folder', '')
        self.items = scan_folder(Path(folder), self.catalog) if folder else []

    def _state(self) -> dict:
        # NPC / Extra entries only expose Standing. Shared admin overrides are read
        # from the public project repository; players cannot edit classification locally.
        classified_items: list[tuple[dict, str, bool, str]] = []
        visible_raw_items: list[dict] = []
        for item in self.items:
            char = self.catalog.by_key.get(item['character_key'])
            auto_category = self.classifier.classify(char) if char else 'npc_extra'
            is_npc, override_mode = self._effective_npc_extra(item['character_key'], auto_category)
            classified_items.append((item, auto_category, is_npc, override_mode))
            if not is_npc or item.get('action') == 'standing':
                visible_raw_items.append(item)

        conflicts = build_conflicts(visible_raw_items)
        conflict_targets = {c['target_key'] for c in conflicts}
        items = []
        for item, auto_category, is_npc, override_mode in classified_items:
            if is_npc and item.get('action') != 'standing':
                continue
            row = dict(item)
            row['conflict'] = item['target_key'] in conflict_targets
            row['category_auto'] = auto_category
            row['is_npc_extra'] = is_npc
            row['classification_override'] = override_mode
            items.append(row)

        characters = character_summary(
            self.catalog,
            visible_raw_items,
            self._image_info,
            classifier=self.classifier,
        )
        for char in characters:
            auto_category = char.get('category', 'npc_extra')
            is_npc, override_mode = self._effective_npc_extra(char['key'], auto_category)
            char['category_auto'] = auto_category
            char['is_npc_extra'] = is_npc
            char['classification_override'] = override_mode
            char['classification_manual'] = False
            char['classification_source'] = 'project' if override_mode == 'project' else 'automatic'
            char['tags'] = list(self.character_tags.get(char['key'], []))

        visible_chars = [c for c in characters if not c.get('is_placeholder')]
        all_tags = sorted({tag for tags in self.character_tags.values() for tag in tags}, key=str.casefold)
        npc_count = sum(1 for c in visible_chars if c.get('is_npc_extra'))
        cached_images = sum(1 for c in self.catalog.characters if self._local_image_path(c['key']))
        overlay = read_overlay(self.online_catalog_path)

        return {
            'settings': self.settings,
            'mobile_sync': self._mobile_sync_info(),
            'catalog_version': self.catalog.version,
            'catalog_count': len(self.catalog.characters),
            'base_catalog_count': len(self.catalog.base_characters),
            'online_catalog_count': len(self.catalog.online_characters),
            'characters': characters,
            'items': items,
            'conflicts': conflicts,
            'available_tags': all_tags,
            'playable_reference': {
                'source': self.classifier.source,
                'secondary_source': self.prydwen_meta.get('secondary_source', 'https://enikk.app/characters'),
                'last_updated': self.classifier.last_updated,
                'prydwen_site_count': self.prydwen_meta.get('site_count', 221),
                'unique_playable_names': self.prydwen_meta.get('secondary_count', self.prydwen_meta.get('unique_base_names_used', 200)),
                'catalog_base_matches': sum(
                    1 for c in visible_chars if c.get('category_auto') == 'nikke'
                ),
                'online_reference_names': self.classifier.online_reference_count,
                'online_reference_checked': self.classifier.online_reference_checked,
            },
            # Kept for v0.3 frontend compatibility.
            'prydwen': {
                'source': self.classifier.source,
                'last_updated': self.classifier.last_updated,
                'site_count': self.prydwen_meta.get('site_count', 221),
                'catalog_playable_matches': sum(
                    1 for c in visible_chars if c.get('category_auto') == 'nikke'
                ),
            },
            'catalog_updates': {
                'source': overlay.get('source', ''),
                'last_checked': overlay.get('last_checked', ''),
                'source_entries': overlay.get('source_entries', 0),
                'online_total': len(self.catalog.online_characters),
                'last_result': self.catalog_update_status,
            },
            'image_provider': {
                'name': 'Prydwen HQ + Nikke-DB',
                'prydwen_base_url': PRYDWEN_IMAGE_BASE,
                'fullbody_base_url': NIKKE_DB_FB_BASE,
                'sprite_base_url': NIKKE_DB_SPRITE_BASE,
                'cached': cached_images,
                'eligible': sum(1 for c in self.catalog.characters if self._remote_sprite_url(c['key'])),
            },
            'stats': {
                'mods': len(items),
                'variants_with_mods': sum(1 for c in characters if c['mod_count'] > 0),
                'conflicts': len(conflicts),
                'catalog': len(self.catalog.characters),
                'base_catalog': len(self.catalog.base_characters),
                'online_catalog': len(self.catalog.online_characters),
                'npc_extra': npc_count,
                'cached_images': cached_images,
                'tags': len(all_tags),
            },
        }

    # --- JS API ---
    def get_state(self) -> dict:
        self._maybe_auto_update_catalog()
        self._refresh_project_classification_overrides()
        self._refresh_project_image_manifest()
        return self._state()

    def refresh(self) -> dict:
        self._refresh_project_classification_overrides(force=True)
        self._refresh_project_image_manifest(force=True)
        try:
            result = self._refresh_project_catalog_additions(force=True)
            self.catalog_update_status = result
            self._reload_catalog()
        except Exception:
            pass
        self._scan()
        return self._state()

    def set_language(self, language: str) -> dict:
        if language in {'es', 'en'}:
            self.settings['language'] = language
            self._save_settings()
        return self._state()

    def set_character_sort(self, sort_key: str) -> dict:
        allowed = {'id_asc', 'id_desc', 'name_asc', 'name_desc', 'mods_desc', 'conflicts_first'}
        if sort_key in allowed:
            self.settings['character_sort'] = sort_key
            self._save_settings()
        return self._state()

    def set_auto_catalog_updates(self, enabled: bool) -> dict:
        self.settings['auto_catalog_updates'] = bool(enabled)
        self._save_settings()
        return self._state()


    def update_character_tags(self, character_keys: list[str], tag: str, operation: str = 'add') -> dict:
        clean_tag = re.sub(r'\s+', ' ', str(tag or '').strip())[:40]
        if not clean_tag or operation not in {'add', 'remove'}:
            return self._state()
        valid_keys = {c['key'] for c in self.catalog.characters}
        valid_keys.update(i['character_key'] for i in self.items)
        changed = 0
        now = int(time.time() * 1000)
        norm = clean_tag.casefold()
        with self._lock:
            for key in dict.fromkeys(character_keys or []):
                if key not in valid_keys:
                    continue
                bucket = self.tag_sync_meta.setdefault(key, {})
                current = bucket.get(norm, {})
                desired = operation == 'add'
                current_present = bool(current.get('present', False))
                current_tag = str(current.get('tag', '')).strip()
                same_label = bool(current_tag) and current_tag.casefold() == norm
                if current_present != desired or (desired and not same_label):
                    bucket[norm] = {'tag': clean_tag, 'present': desired, 'updated_at': now}
                    changed += 1
            if changed:
                self._save_tag_sync_meta()
                self._rebuild_tags_from_meta()
        state = self._state()
        state['tag_update_result'] = {'changed': changed, 'tag': clean_tag, 'operation': operation}
        return state

    def regenerate_mobile_pairing_token(self) -> dict:
        with self._lock:
            self.settings['mobile_sync_token'] = secrets.token_urlsafe(24)
            self._save_settings()
            if getattr(self, 'sync_server', None):
                self.sync_server.token = self.settings['mobile_sync_token']
            self._write_pair_qr()
        return self._state()

    def check_catalog_updates(self) -> dict:
        try:
            self._refresh_project_classification_overrides(force=True)
            self._refresh_project_image_manifest(force=True)
            result = self._refresh_project_catalog_additions(force=True)
            result['automatic'] = False
            self.catalog_update_status = result
            self._reload_catalog()
            playable_result = refresh_playable_reference(
                self.catalog.characters, self.playable_online_path, timeout=8
            )
            result['playable_refresh'] = playable_result
            if playable_result.get('ok'):
                self._reload_catalog()
            self._scan()
            state = self._state()
            state['catalog_update_result'] = result
            return state
        except Exception as exc:
            result = {'ok': False, 'automatic': False, 'error': str(exc), 'added_count': 0}
            self.catalog_update_status = result
            state = self._state()
            state['catalog_update_result'] = result
            return state

    def choose_mods_folder(self) -> dict:
        if self.window is None:
            return self._state()
        try:
            import webview
            result = self.window.create_file_dialog(webview.FOLDER_DIALOG)
            if result:
                chosen = result[0] if isinstance(result, (tuple, list)) else result
                self.settings['mods_folder'] = str(chosen)
                self._save_settings()
                self._scan()
        except Exception as exc:
            return {'error': str(exc), **self._state()}
        return self._state()

    def set_mods_folder(self, folder: str) -> dict:
        p = Path(folder).expanduser()
        if p.exists() and p.is_dir():
            self.settings['mods_folder'] = str(p.resolve())
            self._save_settings()
            self._scan()
        return self._state()

    def open_mods_folder(self) -> dict:
        folder = self.settings.get('mods_folder', '')
        if folder and Path(folder).exists():
            self._open_path(Path(folder))
        return {'ok': True}

    def open_item(self, item_id: str) -> dict:
        item = next((x for x in self.items if x['item_id'] == item_id), None)
        if item:
            self._reveal_path(Path(item['path']))
        return {'ok': bool(item)}

    def preview_item(self, item_id: str) -> dict:
        """Generate an experimental preview from the real selected mod bundle.

        v0.11 Preview Alpha extracts and displays the largest Texture2D atlas.
        It deliberately does not copy/use a third-party preview renderer and it
        never executes content from the mod.
        """
        item = next((x for x in self.items if x['item_id'] == item_id), None)
        if not item:
            return {'ok': False, 'error': 'Mod no encontrado. Vuelve a escanear la carpeta.'}
        path = Path(item['path'])
        try:
            result = self.preview_engine.generate(path, item_id, item.get('action', ''))
            result.update({
                'item_id': item_id,
                'mod_name': item.get('mod_title') or item.get('name') or path.name,
                'character_name': item.get('character_name', ''),
                'id': item.get('id', ''),
                'version': item.get('version', ''),
                'action': item.get('action', ''),
                'path': str(path),
            })
            return result
        except PreviewError as exc:
            return {
                'ok': False,
                'error': str(exc),
                'item_id': item_id,
                'mod_name': item.get('mod_title') or item.get('name') or path.name,
                'path': str(path),
            }
        except Exception as exc:
            return {
                'ok': False,
                'error': f'Error inesperado de Preview Alpha: {exc}',
                'item_id': item_id,
                'mod_name': item.get('mod_title') or item.get('name') or path.name,
                'path': str(path),
            }

    def delete_items(self, item_ids: list[str]) -> dict:
        wanted = set(item_ids or [])
        targets = [x for x in self.items if x['item_id'] in wanted]
        deleted = []
        errors = []
        targets.sort(key=lambda x: len(Path(x['path']).parts))
        deleted_paths: list[Path] = []
        for item in targets:
            p = Path(item['path'])
            if any(parent in p.parents for parent in deleted_paths):
                continue
            try:
                if p.exists():
                    send2trash(str(p))
                    deleted.append(str(p))
                    deleted_paths.append(p)
            except Exception as exc:
                errors.append(f'{p}: {exc}')
        self._scan()
        state = self._state()
        state['delete_result'] = {'deleted': deleted, 'errors': errors}
        return state

    def choose_character_image(self, character_key: str) -> dict:
        if character_key not in self.catalog.by_key and not any(i['character_key'] == character_key for i in self.items):
            return self._state()
        if self.window is None:
            return self._state()
        try:
            import webview
            result = self.window.create_file_dialog(
                webview.OPEN_DIALOG,
                allow_multiple=False,
                file_types=('Images (*.png;*.jpg;*.jpeg;*.webp)', 'All files (*.*)'),
            )
            if result:
                selected = result[0] if isinstance(result, (tuple, list)) else result
                self._store_character_image(character_key, Path(selected))
                self.manual_image_keys.add(character_key)
                self._save_manual_images()
        except Exception as exc:
            state = self._state()
            state['error'] = str(exc)
            return state
        return self._state()

    def remove_character_image(self, character_key: str) -> dict:
        for ext in ('.webp', '.png', '.jpg', '.jpeg'):
            p = self.images_dir / f'{character_key}{ext}'
            if p.exists():
                p.unlink()
        self.manual_image_keys.discard(character_key)
        self._save_manual_images()
        return self._state()

    def cache_character_images(self) -> dict:
        """Download missing images from Prydwen and Nikke-DB, preferring HQ art."""
        targets = []
        already_cached = 0
        for char in self.catalog.characters:
            key = char['key']
            candidates = self._remote_image_candidates(key)
            if not candidates:
                continue
            local = self._local_image_path(key)
            # v0.5 can upgrade older Nikke-DB thumbnail caches to Prydwen HQ art.
            # Never overwrite a picture explicitly chosen by the user.
            force_upgrade = bool(
                local
                and key not in self.manual_image_keys
                and candidates
                and candidates[0][0] in {'prydwen_full', 'prydwen_alias'}
            )
            if local and not force_upgrade:
                already_cached += 1
                continue
            targets.append((key, candidates, force_upgrade))

        downloaded: list[str] = []
        failed: list[str] = []
        high_quality = 0
        with ThreadPoolExecutor(max_workers=8) as pool:
            future_map = {
                pool.submit(self._download_character_image, key, candidates, force): key
                for key, candidates, force in targets
            }
            for future in as_completed(future_map):
                key = future_map[future]
                try:
                    ok, source = future.result()
                    if ok:
                        downloaded.append(key)
                        if source in {'project_manual', 'project_library', 'prydwen_full', 'prydwen_alias', 'playable_alias_local', 'nikke_db_fullbody', 'nikke_db_alias_fullbody'}:
                            high_quality += 1
                    else:
                        failed.append(key)
                except Exception:
                    failed.append(key)

        state = self._state()
        state['image_cache_result'] = {
            'downloaded': len(downloaded),
            'high_quality': high_quality,
            'already_cached': already_cached,
            'failed': len(failed),
            'failed_keys': sorted(failed)[:60],
        }
        return state

    def open_images_folder(self) -> dict:
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self._open_path(self.images_dir)
        return {'ok': True}

    # --- image helpers ---
    def _download_character_image(self, key: str, candidates: list[tuple[str, str]], force: bool = False) -> tuple[bool, str]:
        dest = self.images_dir / f'{key}.webp'
        if dest.exists() and not force:
            return True, 'existing'

        for source_name, url in candidates:
            if not url.startswith(('http://', 'https://')):
                continue
            req = urllib.request.Request(url, headers={'User-Agent': 'NIKKE-Mod-Library/0.11-preview-alpha'})
            try:
                with urllib.request.urlopen(req, timeout=12) as response:
                    if getattr(response, 'status', 200) != 200:
                        continue
                    raw = response.read()
                with Image.open(io.BytesIO(raw)) as im:
                    im = ImageOps.exif_transpose(im)
                    if 'A' in im.getbands():
                        im = im.convert('RGBA')
                    else:
                        im = im.convert('RGB')
                    # Preserve the source resolution unless it is exceptionally large.
                    # Prydwen full art is much sharper than the old 128 px sprite fallback.
                    im.thumbnail((2400, 3000), Image.Resampling.LANCZOS)
                    im.save(dest, 'WEBP', quality=96, method=6)
                return True, source_name
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError):
                continue
        return False, ''

    def _store_character_image(self, key: str, source: Path) -> None:
        if not source.exists() or not source.is_file():
            return
        with Image.open(source) as im:
            im = ImageOps.exif_transpose(im)
            if 'A' in im.getbands():
                im = im.convert('RGBA')
            else:
                im = im.convert('RGB')
            im.thumbnail((2400, 3000), Image.Resampling.LANCZOS)
            dest = self.images_dir / f'{key}.webp'
            im.save(dest, 'WEBP', quality=96, method=6)
        for ext in ('.png', '.jpg', '.jpeg'):
            old = self.images_dir / f'{key}{ext}'
            if old.exists():
                old.unlink()

    # --- filesystem helpers ---
    @staticmethod
    def _open_path(path: Path) -> None:
        if os.name == 'nt':
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', str(path)])
        else:
            subprocess.Popen(['xdg-open', str(path)])

    @staticmethod
    def _reveal_path(path: Path) -> None:
        if os.name == 'nt':
            if path.is_file():
                subprocess.Popen(['explorer', '/select,', str(path)])
            else:
                os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', '-R', str(path)])
        else:
            target = path.parent if path.is_file() else path
            subprocess.Popen(['xdg-open', str(target)])
