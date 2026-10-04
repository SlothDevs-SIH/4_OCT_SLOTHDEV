"""In-process interface used by decision_engine when DATA_SOURCE=local.

Stages 1a/1b: get_context and get_data_quality are real. The other functions are still fixture-backed and are replaced in
Stage 2 (KPI engine, lead model); signatures stay the same. Each function returns exactly the contract fixture shape, or None
when the business is unknown.
"""
from typing import Optional

from backend.common.fixtures import load_fixture
from backend.data_engine import quality, store


def _for(business_id: str, name: str):
    data = load_fixture(name)
    return data if data.get("business_id") == business_id else None


def get_context(business_id: str) -> Optional[dict]:
    """Real (Stage 1a): the demo tenant's context or a business created through onboarding."""
    return store.get_context(business_id)


def get_kpi_facts(business_id: str, from_date: Optional[str] = None, to_date: Optional[str] = None,
                  snapshot: str = "baseline") -> Optional[list]:
    if _for(business_id, "business_context") is None:
        return None
    facts = load_fixture("kpi_facts" if snapshot == "baseline" else "kpi_facts_day7")
    return [f for f in facts
            if (from_date is None or f["period"]["from"] >= from_date)
            and (to_date is None or f["period"]["to"] <= to_date)]


def get_lead_scores(business_id: str, limit: Optional[int] = None) -> Optional[dict]:
    data = _for(business_id, "lead_scores")
    if data is not None and limit is not None:
        data["leads"] = data["leads"][:limit]
    return data


def get_data_quality(business_id: str) -> Optional[dict]:
    """Real (Stage 1b): computed from the import jobs (the demo business imports its messy orders export)."""
    return quality.data_quality(business_id)


def get_kpi_series(business_id: str, from_date: Optional[str] = None, to_date: Optional[str] = None,
                   channel: Optional[str] = None) -> Optional[dict]:
    data = _for(business_id, "kpi_daily")
    if data is not None:
        data["series"] = [r for r in data["series"]
                          if (from_date is None or r["date"] >= from_date)
                          and (to_date is None or r["date"] <= to_date)
                          and (channel is None or r["channel"] == channel)]
    return data
