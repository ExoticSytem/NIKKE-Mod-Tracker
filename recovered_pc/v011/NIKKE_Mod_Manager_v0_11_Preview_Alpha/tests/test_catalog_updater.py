from pathlib import Path
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.catalog import Catalog
from src.catalog_updater import merge_online_catalog


def test_online_merge_never_overwrites_and_skips_legacy_duplicates():
    base = Catalog(ROOT / 'data' / 'characters.json')
    remote = [
        {'name': 'Rapi Classic Vacation', 'id': 'c010_03'},  # duplicate name, shifted legacy numbering
        {'name': 'Rapi_old', 'id': 'c010_01'},               # legacy
        {'name': 'c122', 'id': 'c122'},                      # placeholder
        {'name': 'Future Test Nikke', 'id': 'c777'},          # valid new base
        {'name': 'Future Test Skin', 'id': 'c777_01'},        # valid new version
    ]
    with tempfile.TemporaryDirectory() as td:
        overlay = Path(td) / 'catalog_online.json'
        result = merge_online_catalog(base.characters, overlay, remote)
        assert result['added_count'] == 2
        merged = Catalog(ROOT / 'data' / 'characters.json', overlay)
        assert merged.by_key['010_02']['name'] == 'Rapi - Classic Vacation'
        assert '010_03' not in merged.by_key
        assert merged.by_key['777_00']['name'] == 'Future Test Nikke'
        assert merged.by_key['777_01']['name'] == 'Future Test Skin'


def test_future_skin_uses_official_version_sequence_despite_legacy_remote_entry():
    base = Catalog(ROOT / 'data' / 'characters.json')
    remote = [
        {'name': 'Rapi', 'id': 'c010'},
        {'name': 'Rapi_old', 'id': 'c010_01'},
        {'name': 'Rapi White Promise', 'id': 'c010_02'},
        {'name': 'Rapi Classic Vacation', 'id': 'c010_03'},
        {'name': 'Rapi Future Costume', 'id': 'c010_04'},
    ]
    with tempfile.TemporaryDirectory() as td:
        overlay = Path(td) / 'catalog_online.json'
        result = merge_online_catalog(base.characters, overlay, remote)
        assert result['added_count'] == 1
        merged = Catalog(ROOT / 'data' / 'characters.json', overlay)
        assert merged.by_key['010_03']['name'] == 'Rapi Future Costume'
