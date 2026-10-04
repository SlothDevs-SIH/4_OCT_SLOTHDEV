"""DataClient: the only way decision_engine reads data_engine's output.

`DATA_SOURCE` picks where the data comes from:

- `fixture` (default): the JSON files in `contracts/fixtures/`. Works with no data_engine.
- `http`: data_engine's REST API at `DATA_ENGINE_URL` (contract section 3).
- `local`: in-process calls to `backend.data_engine.public` (used on backend-integration).

Every method returns the contract shape, whatever the source.
"""
from __future__ import annotations

import inspect
import importlib
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
SNAPSHOTS = ("baseline", "day7")
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


class DataClient:
    def __init__(
        self,
        source: Optional[str] = None,
        base_url: Optional[str] = None,
        api_prefix: str = "/api/v1",
        timeout: float = 10.0,
    ):
        self.source = (source or os.getenv("DATA_SOURCE") or "fixture").strip().lower()
        if self.source not in SOURCES:
            raise ValueError(f"DATA_SOURCE must be one of {SOURCES}, got {self.source!r}")
        self.base_url = (base_url or os.getenv("DATA_ENGINE_URL") or "http://localhost:8001").rstrip("/")
        self.api_prefix = api_prefix.rstrip("/")
        self.timeout = timeout
        self._public = None

    # ------------------------------------------------------------------ API

    def get_context(self, business_id: str) -> dict:
        """Business profile, goal, constraints and capacity (`business_context.json`)."""
        if self.source == "fixture":
            return self._fixture_for(business_id, "business_context")
        if self.source == "http":
            return self._get(f"/businesses/{quote(business_id)}")
        return self._local("get_context", business_id)

    def get_kpi_facts(
        self,
        business_id: str,
        from_date: DateLike = None,
        to_date: DateLike = None,
        snapshot: str = "baseline",
    ) -> list[dict]:
        """KPI facts (`kpi_facts.json`); `snapshot="day7"` returns the day-7 follow-up week."""
        if snapshot not in SNAPSHOTS:
            raise ValueError(f"snapshot must be one of {SNAPSHOTS}, got {snapshot!r}")
        from_date, to_date = _iso(from_date), _iso(to_date)
        if self.source == "fixture":
            self._fixture_for(business_id, "business_context")
            name = "kpi_facts" if snapshot == "baseline" else "kpi_facts_day7"
            facts = load_fixture(name)
            return [
                f for f in facts
                if (from_date is None or f["period"]["from"] >= from_date)
                and (to_date is None or f["period"]["to"] <= to_date)
            ]
        if self.source == "http":
            body = self._get(
                f"/businesses/{quote(business_id)}/kpis",
                {"from": from_date, "to": to_date, "snapshot": snapshot},
            )
            return body["facts"] if isinstance(body, dict) and "facts" in body else body
        kwargs = {"snapshot": snapshot} if self._accepts("get_kpi_facts", "snapshot") else {}
        if snapshot != "baseline" and not kwargs:
            raise DataSourceUnavailable("data_engine.public.get_kpi_facts does not support snapshot")
        return self._local("get_kpi_facts", business_id, from_date, to_date, **kwargs)

    def get_lead_scores(self, business_id: str, limit: Optional[int] = None) -> dict:
        """Ranked lead scores plus `model_card` (`lead_scores.json`).

        `limit` keeps the top-ranked leads; abstentions (rank null) are kept after them.
        """
        if self.source == "fixture":
            data = self._fixture_for(business_id, "lead_scores")
            if limit is not None:
                ranked = sorted((l for l in data["leads"] if l["rank"] is not None), key=lambda l: l["rank"])
                abstained = [l for l in data["leads"] if l["rank"] is None]
                data["leads"] = (ranked + abstained)[:limit]
            return data
        if self.source == "http":
            return self._get(f"/businesses/{quote(business_id)}/leads/queue", {"limit": limit})
        return self._local("get_lead_scores", business_id, limit)

    def get_data_quality(self, business_id: str) -> dict:
        """Data confidence badge and import reports (`data_quality.json`)."""
        if self.source == "fixture":
            return self._fixture_for(business_id, "data_quality")
        if self.source == "http":
            return self._get(f"/businesses/{quote(business_id)}/data-quality")
        return self._local("get_data_quality", business_id)

    def get_kpi_series(
        self,
        business_id: str,
        from_date: DateLike = None,
        to_date: DateLike = None,
        channel: Optional[str] = None,
    ) -> dict:
        """Daily per-channel series for anomaly detection (`kpi_daily.json`).

        Proposed contract addition: `GET /businesses/{id}/kpis/daily` and
        `data_engine.public.get_kpi_series`.
        """
        from_date, to_date = _iso(from_date), _iso(to_date)
        if self.source == "fixture":
            data = self._fixture_for(business_id, "kpi_daily")
            data["series"] = [
                r for r in data["series"]
                if (from_date is None or r["date"] >= from_date)
                and (to_date is None or r["date"] <= to_date)
                and (channel is None or r["channel"] == channel)
            ]
            return data
        if self.source == "http":
            return self._get(
                f"/businesses/{quote(business_id)}/kpis/daily",
                {"from": from_date, "to": to_date, "channel": channel},
            )
        return self._local("get_kpi_series", business_id, from_date, to_date, channel)

    # ------------------------------------------------------------ internals

    def _fixture_for(self, business_id: str, name: str) -> Any:
        data = load_fixture(name)
        if data.get("business_id") != business_id:
            raise DataNotFound(f"business {business_id!r} not found in fixtures")
        return data

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
                    "DATA_SOURCE=local needs backend/data_engine/public.py (merge backend-1)"
                ) from e
        return self._public

    def _accepts(self, func_name: str, param: str) -> bool:
        func = getattr(self._public_module(), func_name, None)
        return func is not None and param in inspect.signature(func).parameters

    def _local(self, func_name: str, *args, **kwargs) -> Any:
        func = getattr(self._public_module(), func_name, None)
        if func is None:
            raise DataSourceUnavailable(f"data_engine.public has no {func_name}()")
        result = func(*args, **kwargs)
        if result is None:
            raise DataNotFound(f"data_engine.public.{func_name} returned nothing for {args[0]!r}")
        return result


@lru_cache(maxsize=1)
def get_data_client() -> DataClient:
    """Shared client configured from the environment (use as a FastAPI dependency)."""
    return DataClient()
