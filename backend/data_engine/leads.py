"""Lead queue: score the demo leads with the trained model, rank by probability x expected value, abstain on
incomplete leads. Output has the shape of contracts/fixtures/lead_scores.json.

Point in time: a snapshot only sees what had happened by its `as_of` time (responses and wins that happen later
are invisible). The queue for a snapshot is the OPEN leads (not won or lost) created in that snapshot's period.
"""
from __future__ import annotations

from typing import Optional

from . import kpis
from .ml import features as F
from .ml.lead_model import LeadModel
from .synth import config as C


def model_card() -> dict:
    return LeadModel.load().card


def lead_scores(business_id: str, limit: Optional[int] = None, snapshot: str = "baseline") -> Optional[dict]:
    if business_id != C.BUSINESS_ID:
        return None
    if snapshot not in ("baseline", "day7"):
        raise ValueError("snapshot must be 'baseline' or 'day7'")
    a, b, _ = kpis.period_for(snapshot)
    ix = kpis.indexed("day7" if snapshot == "day7" else "baseline")
    model = LeadModel.load()
    baseline = round(model.prevalence, 3)
    ranked, abstained = [], []
    for created, lead in ix.leads_in(a, b):
        if ix.stage(lead) in ("won", "lost"):
            continue
        responded = ix.seen(lead["first_response_at"])
        base = {
            "lead_id": lead["lead_id"], "label": lead["label"], "channel": lead["channel"], "high_value": lead["high_value"],
            "attended": responded is not None, "hours_since_inquiry": round((ix.as_of - created).total_seconds() / 3600, 1),
            "expected_value_inr": lead["expected_value_inr"], "baseline": baseline, "synthetic": True,
        }
        missing = F.missing_fields(lead["attributes"], lead["channel"])
        if missing:
            abstained.append({**base, "probability": None, "score_value_inr": None, "abstain": True,
                              "abstain_reason": "Missing key fields: " + ", ".join(missing), "factors": [], "rank": None})
            continue
        s = model.score(lead["attributes"])
        ev = lead["expected_value_inr"]
        ranked.append({**base, "probability": s["probability"],
                       "score_value_inr": round(s["probability"] * ev, 2) if ev is not None else None,
                       "abstain": False, "abstain_reason": None, "factors": s["factors"], "rank": None})
    ranked.sort(key=lambda r: (-(r["score_value_inr"] or 0), r["lead_id"]))
    for i, r in enumerate(ranked, 1):
        r["rank"] = i
    abstained.sort(key=lambda r: r["lead_id"])
    leads = ranked + abstained
    if limit is not None:
        leads = leads[:limit]
    return {"business_id": business_id, "synthetic": True, "scored_at": kpis_as_of(ix),
            "high_value_threshold_inr": C.HIGH_VALUE_THRESHOLD_INR, "ranking": "probability x expected_value_inr",
            "model_card": model.card, "leads": leads}


def kpis_as_of(ix) -> str:
    return ix.as_of.strftime("%Y-%m-%dT%H:%M:%SZ")
