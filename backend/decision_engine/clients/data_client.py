"""DataClient: the only way decision_engine reads data_engine's output (contract v2).

`DATA_SOURCE` picks where the data comes from:

- `fixture` (default): `contracts/fixtures/v2/` (stand-in Box Box and home baker). Works with no data_engine.
- `http`: data_engine's REST API at `DATA_ENGINE_URL` (contract v2 section 3).
- `local`: in-process calls to `backend.data_engine.public` (used on backend-integration).

Every method returns the contract shape, whatever the source.
"""
from __future__ import annotations

import importlib
import inspect
import json
import os
from datetime import date
from functools import lru_cache
from typing import Any, Optional, Union
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from backend.common.fixtures import load_fixture

SOURCES = ("fixture", "http", "local")
WEEKS = ("week_1", "week_2", "week_3", "week_4")
FIXTURE_BUSINESSES = {"biz_boxbox": "boxbox", "biz_homebaker": "homebaker"}
DateLike = Optional[Union[str, date]]


class DataClientError(Exception):
    """Base error for DataClient."""


class DataNotFound(DataClientError):
    """The business (or resource) does not exist in the data source."""


class DataSourceUnavailable(DataClientError):
    """The data source could not be reached or does not support the call."""


def _iso(d: DateLike) -> Optional[str]:
    if d is None:
        return None
    return d.isoformat() if isinstance(d, date) else str(d)


def check_week(week: str) -> str:
    if week not in WEEKS:
        raise ValueError(f"week must be one of {WEEKS}, got {week!r}")
    return week


class DataClient:
    def __init__(self, source: Optional[str] = None, base_url: Optional[str] = None,
                 api_prefix: str = "/api/v1", timeout: float = 10.0):
        self.source = (source or os.getenv("DATA_SOURCE") or "fixture").strip().lower()
        if self.source not in SOURCES:
            raise ValueError(f"DATA_SOURCE must be one of {SOURCES}, got {self.source!r}")
        self.base_url = (base_url or os.getenv("DATA_ENGINE_URL") or "http://localhost:8001").rstrip("/")
        self.api_prefix = api_prefix.rstrip("/")
        self.timeout = timeout
        self._public = None

    # ------------------------------------------------------------------ API

    def get_context(self, business_id: str) -> dict:
        """Business profile (contract 2.1)."""
        if self.source == "fixture":
            return self._fixture(business_id, "business")
        if self.source == "http":
            return self._get(f"/businesses/{quote(business_id)}")
        return self._local("get_context", business_id)

    def get_facts(self, business_id: str, week: str = "week_1") -> dict:
        """`{business_id, week, as_of, facts: [Fact 2.2]}` as of the end of `week` (point in time)."""
        check_week(week)
        if self.source == "fixture":
            return self._fixture(business_id, f"facts_{week}")
        if self.source == "http":
            body = self._get(f"/businesses/{quote(business_id)}/facts", {"week": week})
        else:
            body = self._local("get_facts", business_id, week)
        return body if isinstance(body, dict) else {"business_id": business_id, "week": week, "facts": body}

    def get_leads(self, business_id: str, week: str = "week_1", group: Optional[str] = None) -> dict:
        """`{business_id, week, leads: [Lead 2.4]}`, optionally one group."""
        check_week(week)
        if self.source == "fixture":
            body = self._fixture(business_id, f"leads_{week}")
        elif self.source == "http":
            body = self._get(f"/businesses/{quote(business_id)}/leads", {"week": week, "group": group})
        else:
            body = self._local("get_leads", business_id, week)
        if not isinstance(body, dict):
            body = {"business_id": business_id, "week": week, "leads": body}
        if group:
            body["leads"] = [l for l in body["leads"] if l["group"] == group]
        return body

    def get_projection(self, business_id: str, week: str = "week_1") -> dict:
        """Next month's orders with a range (contract 2.7)."""
        check_week(week)
        if self.source == "fixture":
            return self._fixture(business_id, f"projection_{week}")
        if self.source == "http":
            return self._get(f"/businesses/{quote(business_id)}/projection", {"week": week})
        return self._local("get_projection", business_id, week)

    def get_data_quality(self, business_id: str) -> dict:
        if self.source == "fixture":
            return self._fixture(business_id, "data_quality")
        if self.source == "http":
            return self._get(f"/businesses/{quote(business_id)}/data-quality")
        return self._local("get_data_quality", business_id)

    def get_market_context(self, feed: str, from_date: DateLike = None, to_date: DateLike = None) -> dict:
        """Demand windows from one calendar feed (`f1_calendar`, `india_festivals`, ...), contract 2.9."""
        from_date, to_date = _iso(from_date), _iso(to_date)
        if self.source == "fixture":
            try:
                return load_fixture(f"v2/market_context/{feed}")
            except FileNotFoundError:
                raise DataSourceUnavailable(f"no market context for feed {feed!r}") from None
        if self.source == "http":
            return self._get("/market-context", {"from": from_date, "to": to_date, "feed": feed})
        func = getattr(self._public_module(), "get_market_context", None)
        if func is None:
            raise DataSourceUnavailable("data_engine.public has no get_market_context()")
        if "feed" in inspect.signature(func).parameters:
            return func(from_date, to_date, feed=feed)
        if feed != "f1_calendar":  # the built module only knows the F1 calendar
            raise DataSourceUnavailable(f"market context feed {feed!r} is not built yet")
        return func(from_date, to_date)

    # ------------------------------------------------------------ internals

    def _fixture(self, business_id: str, name: str) -> Any:
        slug = FIXTURE_BUSINESSES.get(business_id)
        if slug is None:
            raise DataNotFound(f"business {business_id!r} not found in fixtures")
        return load_fixture(f"v2/{slug}/{name}")

    def _get(self, path: str, params: Optional[dict] = None) -> Any:
        query = urlencode({k: v for k, v in (params or {}).items() if v is not None})
        url = f"{self.base_url}{self.api_prefix}{path}" + (f"?{query}" if query else "")
        req = Request(url, headers={"Accept": "application/json"})
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            if e.code == 404:
                raise DataNotFound(f"GET {url} returned 404") from e
            raise DataSourceUnavailable(f"GET {url} returned {e.code}") from e
        except (URLError, TimeoutError, ValueError) as e:
            raise DataSourceUnavailable(f"GET {url} failed: {e}") from e

    def _public_module(self):
        if self._public is None:
            try:
                self._public = importlib.import_module("backend.data_engine.public")
            except ImportError as e:
                raise DataSourceUnavailable(
                    "DATA_SOURCE=local needs backend/data_engine/public.py (merge backend-1)") from e
        return self._public

    def _local(self, func_name: str, *args) -> Any:
        func = getattr(self._public_module(), func_name, None)
        if func is None:
            raise DataSourceUnavailable(f"data_engine.public has no {func_name}() yet (contract v2)")
        result = func(*args)
        if result is None:
            raise DataNotFound(f"data_engine.public.{func_name} returned nothing for {args[0]!r}")
        return result


@lru_cache(maxsize=1)
def get_data_client() -> DataClient:
    """Shared client configured from the environment (use as a FastAPI dependency)."""
    return DataClient()
