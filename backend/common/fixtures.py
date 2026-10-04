"""Load the shared contract fixtures in `contracts/fixtures/`."""
import copy
import json
from functools import lru_cache
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "contracts" / "fixtures"


@lru_cache(maxsize=None)
def _read(name: str):
    path = FIXTURES_DIR / (name if name.endswith(".json") else f"{name}.json")
    if not path.is_file():
        raise FileNotFoundError(f"fixture not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_fixture(name: str):
    """Return a fresh copy of a fixture, e.g. `load_fixture("kpi_facts")`.

    Callers may mutate the result; the cached original is never changed.
    """
    return copy.deepcopy(_read(name))
