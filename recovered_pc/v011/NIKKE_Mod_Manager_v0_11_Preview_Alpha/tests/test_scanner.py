from pathlib import Path
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.catalog import Catalog
from src.scanner import build_conflicts, parse_target_name, scan_folder


catalog = Catalog(ROOT / 'data' / 'characters.json')

names = (ROOT / 'tests' / 'sample_mod_names.txt').read_text(encoding='utf-8').splitlines()
parsed = [parse_target_name(n, catalog, Path('/sample') / n) for n in names]
assert all(parsed)
assert parsed[0]['character_name'] == 'Rapi: Red Hood - Cherished Red'
assert parsed[3]['character_name'] == 'Anis: Sparkling Summer'
conflicts = build_conflicts(parsed)
assert len(conflicts) == 1
assert conflicts[0]['target_key'] == '017_00|standing'
assert conflicts[0]['count'] == 2
print('OK: 12 ejemplos, 1 conflicto real detectado en 017/00/standing')
