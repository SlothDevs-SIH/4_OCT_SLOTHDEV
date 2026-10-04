"""In-process interface used by decision_engine when DATA_SOURCE=local.

Stages 1a-2b: every function is real (context, data quality, KPI facts, daily series, lead scores).
Signatures stay the same. Each function returns exactly the contract fixture shape, or None
when the business is unknown.
"""
from typing import Optional

from backend.common.fixtures import load_fixture
from backend.data_engine import kpis, leads, quality, store
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


def get_lead_scores(business_id: str, limit: Optional[int] = None, snapshot: str = "baseline") -> Optional[dict]:
    """Real (Stage 2b): the trained model scores the open leads of the snapshot's period.
    `limit` keeps the top-ranked leads; abstentions come after them. Default snapshot is the baseline week."""
    if store.get_context(business_id) is None:
        return None
    if business_id != C.BUSINESS_ID:
        return {"business_id": business_id, "synthetic": False, "scored_at": None,
                "high_value_threshold_inr": C.HIGH_VALUE_THRESHOLD_INR, "ranking": "probability x expected_value_inr",
                "model_card": leads.model_card(), "leads": []}
    return leads.lead_scores(business_id, limit, snapshot)


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
