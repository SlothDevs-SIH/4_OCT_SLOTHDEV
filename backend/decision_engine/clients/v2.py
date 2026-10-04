"""DataClientV2: reads data_engine's contract v2 output (Catalyst AI) from fixtures, HTTP or in-process calls.

Same `DATA_SOURCE` switch as `DataClient` (which it extends, so the earlier methods still work):

- `fixture`: JSON files, by default `contracts/fixtures/v2_engine/` (data_engine's real output for both demo businesses, weeks 1 to 4).
  Set `V2_FIXTURE_DIR` (or `fixture_dir=`) to use another folder, e.g. `contracts/fixtures/v2/` (the stand-ins).
- `http`: data_engine's REST API (`DATA_ENGINE_URL`), contract section 3.
- `local`: in-process calls to `backend.data_engine.public`.

`week` is 1 to 4 (or `"week_2"`). For `http` and `local` the demo business must be loaded first (`load_demo`); `fixture` needs no loading.
Every method returns the contract shape whatever the source (a list of facts, a list of leads, one projection object).
"""
from __future__ import annotations

import copy
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional, Union
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from backend.common.fixtures import FIXTURES_DIR

from .data_client import DataClient, DataNotFound, DataSourceUnavailable

Week = Optional[Union[int, str]]
GROUPS = ("hot", "warm", "cold", "disqualified")
DEMO_BUSINESSES = ("boxbox", "homebaker")


def _week(week: Week) -> Optional[int]:
    if week is None:
        return None
    n = int(str(week).replace("week_", ""))
    if not 1 <= n <= 4:
        raise ValueError(f"week must be 1 to 4, got {week!r}")
    return n


class DataClientV2(DataClient):
    def __init__(self, *args, fixture_dir: Optional[Union[str, Path]] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fixture_dir = Path(fixture_dir or os.getenv("V2_FIXTURE_DIR") or FIXTURES_DIR / "v2_engine")

    # ------------------------------------------------------------------ demo loading (http and local only)
    def load_demo(self, business: str, week: int = 1) -> dict:
        """Load a generated demo business at a weekly snapshot in data_engine. Not needed for `fixture`."""
        if business not in DEMO_BUSINESSES:
            raise ValueError(f"business must be one of {DEMO_BUSINESSES}, got {business!r}")
        week = _week(week)
        if self.source == "fixture":
            return {"business_id": f"biz_{business}", "week": week, "synthetic": True}
        if self.source == "http":
            return self._post(f"/demo/load?business={business}&week={week}")
        try:
            from backend.data_engine.homebiz import store as hb
            data = hb.load_demo(business, week)
        except ImportError as e:
            raise DataSourceUnavailable("DATA_SOURCE=local needs backend/data_engine (merge backend-1)") from e
        return {"business_id": data.profile["business_id"], "week": week, "synthetic": True}

    # ------------------------------------------------------------------ the contract v2 reads
    def get_business(self, business_id: str, week: Week = None) -> dict:
        """The business (contract 2.1): one flat object with `provenance`."""
        week = _week(week)
        if self.source == "fixture":
            b = self._fx(business_id, "business.json")
            if week:
                b["week"] = f"week_{week}"
            return b
        if self.source == "http":
            return self._get(f"/businesses/{quote(business_id)}")
        return self._local("get_business", business_id)

    def get_facts(self, business_id: str, week: Week = None, bottleneck: Optional[str] = None) -> list:
        """The facts (contract 2.2) at the weekly snapshot, optionally for one bottleneck (data_engine's `bottleneck` tag)."""
        week = _week(week)
        if self.source == "fixture":
            facts = self._fx(business_id, f"facts_week_{week or 1}.json")["facts"]
        elif self.source == "http":
            facts = self._get(f"/businesses/{quote(business_id)}/facts", {"week": week})["facts"]
        else:
            facts = self._local("get_facts", business_id, week)
        return [f for f in facts if bottleneck is None or f.get("bottleneck") == bottleneck]

    def get_leads(self, business_id: str, group: Optional[str] = None, week: Week = None) -> list:
        """Scored open leads (contract 2.4), hot first; `group` = hot, warm, cold or disqualified."""
        if group is not None and group not in GROUPS:
            raise ValueError(f"group must be one of {GROUPS}, got {group!r}")
        week = _week(week)
        if self.source == "fixture":
            leads = self._fx(business_id, f"leads_week_{week or 1}.json")["leads"]
        elif self.source == "http":
            leads = self._get(f"/businesses/{quote(business_id)}/leads", {"week": week})["leads"]
        else:
            leads = self._local("get_leads", business_id, None, week)
        return [lead for lead in leads if group is None or lead["group"] == group]

    def get_projection(self, business_id: str, week: Week = None) -> dict:
        """Next month's orders with a range (contract 2.7)."""
        week = _week(week)
        if self.source == "fixture":
            return self._fx(business_id, f"projection_week_{week or 1}.json")
        if self.source == "http":
            return self._get(f"/businesses/{quote(business_id)}/projection", {"week": week})
        return self._local("get_projection", business_id, week)

    def get_data_quality(self, business_id: str) -> dict:
        if self.source == "fixture":
            return self._fx(business_id, "data_quality.json")
        return super().get_data_quality(business_id)

    def get_market_context(self, from_date: Optional[str] = None, to_date: Optional[str] = None, feed: str = "f1_calendar") -> dict:
        """Event windows for a date range (contract 2.9). `fixture` returns the stored file as it is (2026-10-05 to 2026-12-31)."""
        if feed not in ("f1_calendar", "india_festivals"):
            raise ValueError(f"feed must be f1_calendar or india_festivals, got {feed!r}")
        if self.source == "fixture":
            path = self.fixture_dir / "market_context" / f"{feed}.json"
            if not path.is_file():
                raise DataSourceUnavailable(f"fixture not found: {path}")
            return json.loads(path.read_text(encoding="utf-8"))
        if self.source == "http":
            return self._get("/market-context", {"from": from_date, "to": to_date, "feed": feed})
        return self._local("get_market_context", from_date, to_date, feed)

    # ------------------------------------------------------------------ internals
    def _folder(self, business_id: str) -> Optional[Path]:
        if not self.fixture_dir.is_dir():
            return None
        for d in sorted(self.fixture_dir.iterdir()):
            f = d / "business.json"
            if d.is_dir() and f.is_file() and json.loads(f.read_text(encoding="utf-8")).get("business_id") == business_id:
                return d
        return None

    def _fx(self, business_id: str, name: str) -> dict:
        folder = self._folder(business_id)
        if folder is None:
            raise DataNotFound(f"business {business_id!r} not found in {self.fixture_dir}")
        path = folder / name
        if not path.is_file():
            raise DataNotFound(f"{name} not found for {business_id!r}")
        return copy.deepcopy(json.loads(path.read_text(encoding="utf-8")))

    def _post(self, path: str) -> dict:
        url = f"{self.base_url}{self.api_prefix}{path}"
        try:
            with urlopen(Request(url, data=b"", method="POST", headers={"Accept": "application/json"}), timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            raise DataSourceUnavailable(f"POST {url} returned {e.code}") from e
        except (URLError, TimeoutError, ValueError) as e:
            raise DataSourceUnavailable(f"POST {url} failed: {e}") from e


@lru_cache(maxsize=1)
def get_data_client_v2() -> DataClientV2:
    """Shared v2 client configured from the environment (use as a FastAPI dependency)."""
    return DataClientV2()
