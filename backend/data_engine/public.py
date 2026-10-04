"""In-process interface used by decision_engine when DATA_SOURCE=local.

Stages 1a-2a: get_context, get_data_quality, get_kpi_facts and get_kpi_series are real. get_lead_scores is replaced in
Stage 2b; signatures stay the same. Each function returns exactly the contract fixture shape, or None
when the business is unknown.
"""
from typing import Optional

from backend.common.fixtures import load_fixture
from backend.data_engine import kpis, quality, store
from backend.data_engine.synth import config as C


def _for(business_id: str, name: str):
    data = load_fixture(name)
    return data if data.get("business_id") == business_id else None


def get_context(business_id: str) -> Optional[dict]:
    """Real (Stage 1a): the demo tenant's context or a business created through onboarding."""
    return store.get_context(business_id)


def get_kpi_facts(business_id: str, from_date: Optional[str] = None, to_date: Optional[str] = None,
                  snapshot: str = "baseline") -> Optional[list]:
    """Real (Stage 2a): computed by the KPI engine. `snapshot` 'baseline' = current week, 'day7' = follow-up week.
    `from_date`/`to_date` (ISO) compute a custom period. Raises ValueError for a bad period or snapshot."""
    if store.get_context(business_id) is None:
        return None
    if business_id != C.BUSINESS_ID:
        return []                       # a business with no data loaded has no facts
    return kpis.compute_facts(snapshot, from_date, to_date)


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
    """Real (Stage 2a): daily per-channel series (instagram, google) + injected-incident ground truth."""
    if store.get_context(business_id) is None:
        return None
    if business_id != C.BUSINESS_ID:
        return {"business_id": business_id, "synthetic": False, "series": [], "injected_incidents": []}
    return kpis.daily_series(from_date, to_date, channel)
