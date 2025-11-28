
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

collect_ignore = ["generator_tests"]

def pytest_addoption(parser):
    parser.addoption("--update-fixtures", action="store_true", help="Update test fixtures")

def load_fixture(name):
    path = Path(__file__).parent / "fixtures" / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None

def save_fixture(name, data):
    path = Path(__file__).parent / "fixtures" / f"{name}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
