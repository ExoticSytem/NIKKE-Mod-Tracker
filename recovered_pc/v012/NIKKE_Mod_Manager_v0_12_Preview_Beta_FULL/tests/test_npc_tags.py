from pathlib import Path
import shutil
import time

from src.api import AppAPI
from src.scanner import parse_target_name


def make_api(tmp_path: Path) -> AppAPI:
    project = tmp_path / 'app'
    (project / 'data').mkdir(parents=True)
    (project / 'web' / 'assets' / 'characters').mkdir(parents=True)
    source = Path(__file__).resolve().parents[1] / 'data'
    shutil.copy2(source / 'characters.json', project / 'data' / 'characters.json')
    shutil.copy2(source / 'prydwen_playable.json', project / 'data' / 'prydwen_playable.json')
    api = AppAPI(project)
    api._project_classification_checked_at = time.time()
    api._project_manifest_checked_at = time.time()
    return api


def test_npc_extra_exposes_only_standing_until_project_override(tmp_path):
    api = make_api(tmp_path)
    names = [
        'c9004_00_aim_Test_Aim',
        'c9004_00_cover_Test_Cover',
        'c9004_00_standing_Test_One',
        'c9004_00_standing_Test_Two',
    ]
    api.items = [
        parse_target_name(name, api.catalog, tmp_path / name, 'file')
        for name in names
    ]
    api.items = [x for x in api.items if x]

    state = api._state()
    assert {x['action'] for x in state['items']} == {'standing'}
    assert len(state['items']) == 2
    assert len(state['conflicts']) == 1
    assert state['conflicts'][0]['action'] == 'standing'
    char = next(c for c in state['characters'] if c['key'] == '9004_00')
    assert char['is_npc_extra'] is True
    assert char['counts']['aim'] == 0
    assert char['counts']['cover'] == 0
    assert char['counts']['standing'] == 2
    assert char['mod_count'] == 2

    api._project_npc_overrides['9004_00'] = False
    state = api._state()
    assert {x['action'] for x in state['items']} == {'aim', 'cover', 'standing'}
    char = next(c for c in state['characters'] if c['key'] == '9004_00')
    assert char['is_npc_extra'] is False
    assert char['mod_count'] == 4


def test_tags_persist_and_are_case_insensitive(tmp_path):
    api = make_api(tmp_path)
    state = api.update_character_tags(['010_00', '011_00'], 'Favoritas', 'add')
    assert state['tag_update_result']['changed'] == 2
    assert 'Favoritas' in state['available_tags']

    state = api.update_character_tags(['010_00'], 'favoritas', 'add')
    assert state['tag_update_result']['changed'] == 0

    reloaded = AppAPI(api.root)
    assert reloaded.character_tags['010_00'] == ['Favoritas']
    assert reloaded.character_tags['011_00'] == ['Favoritas']

    state = reloaded.update_character_tags(['010_00', '011_00'], 'FAVORITAS', 'remove')
    assert state['tag_update_result']['changed'] == 2
    assert 'Favoritas' not in state['available_tags']


def test_old_npc_can_try_current_prydwen_art(tmp_path):
    api = make_api(tmp_path)
    candidates = api._remote_image_candidates('9008_00')
    assert candidates[0][0] == 'prydwen_full'
    assert candidates[0][1].endswith('/nayuta_full.webp')
    assert api._find_playable_alias_key('9008_00', 'Nayuta (NPC)') == '223_00'
