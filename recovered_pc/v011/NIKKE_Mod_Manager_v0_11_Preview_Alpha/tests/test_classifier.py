from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.catalog import Catalog
from src.classifier import CharacterClassifier
from src.api import AppAPI


def build():
    cat = Catalog(ROOT / 'data' / 'characters.json')
    clf = CharacterClassifier(cat, ROOT / 'data' / 'prydwen_playable.json')
    return cat, clf


def test_classification_examples():
    cat, clf = build()
    assert clf.classify(cat.by_key['010_00']) == 'nikke'  # Rapi
    assert clf.classify(cat.by_key['010_01']) == 'skin'   # White Promise
    assert clf.classify(cat.by_key['016_00']) == 'nikke'  # Rapi: Red Hood
    assert clf.classify(cat.by_key['016_03']) == 'skin'
    assert clf.classify(cat.by_key['472_00']) == 'npc_extra'
    assert clf.classify(cat.by_key['840_00']) == 'nikke'  # Ada -> Ada Wong alias
    assert clf.classify(cat.by_key['840_02']) == 'skin'


def test_sprite_url_pattern():
    api = AppAPI(ROOT)
    assert api._remote_sprite_url('010_00').endswith('/si_c010_00_s.png')
    assert api._remote_sprite_url('010_01').endswith('/si_c010_01_00_s.png')
    assert api._remote_sprite_url('016_03').endswith('/si_c016_03_00_s.png')
    assert api._remote_sprite_url('dummy_00') == ''


def test_v08_image_sources_and_project_npc_override_helpers():
    api = AppAPI(ROOT)
    assert api._remote_fullbody_url('010_00').endswith('/images/FB/c010_00.png')
    assert api._remote_fullbody_url('010_01') == ''
    assert api._remote_image_candidates('010_00')[0][0] == 'prydwen_full'
    assert api._prydwen_image_url('Rapi').endswith('/rapi_full.webp')
    assert api._prydwen_image_url('Nayuta (NPC)').endswith('/nayuta_full.webp')
    assert api._find_playable_alias_key('9008_00', 'Nayuta (NPC)') == '223_00'
    assert api._effective_npc_extra('472_00', 'npc_extra')[0] is True
    api._project_npc_overrides['472_00'] = False
    api._project_classification_checked_at = __import__('time').time()
    assert api._effective_npc_extra('472_00', 'npc_extra')[0] is False
