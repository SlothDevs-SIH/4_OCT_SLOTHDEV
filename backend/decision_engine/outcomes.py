"""Outcome ledger: freeze the baseline at approval, evaluate the day-7 snapshot later.

Fidelity (was the plan executed?) is reported separately from effectiveness (did the KPI
move as expected?). Without a control group every result is labelled observational.
"""
from __future__ import annotations

from typing import Optional

from backend.decision_engine.signals import Facts


def _guardrail_fact(facts: Facts, kpi: str, dimension: dict) -> Optional[dict]:
    return facts.get(kpi, **dimension) or facts.get(kpi)


def freeze(rec: dict, template: dict, kpi_facts: list[dict], now: str) -> dict:
    """Ledger entry stored on the recommendation when it is approved."""
    facts = Facts(kpi_facts)
    exp = rec["expected"]
    fact = facts.by_id.get(exp["fact_id"]) if exp["fact_id"] else None
    dimension = fact["dimension"] if fact else {}
    guardrails = []
    for g in template.get("guardrails", []):
        gf = _guardrail_fact(facts, g["kpi"], dimension)
        if not gf:
            continue
        threshold = gf["value"] if g["max"] == "baseline_value" else g["max"]
        guardrails.append({"kpi": g["kpi"], "fact_id": gf["fact_id"], "max": threshold,
                           "baseline": gf["value"]})
    return {
        "frozen_at": now, "kpi": exp["kpi"], "fact_id": exp["fact_id"],
        "baseline": fact["value"] if fact else None,
        "baseline_period": fact["period"] if fact else None,
        "unit": exp["unit"], "expected": {"low": exp["low"], "high": exp["high"], "direction": exp["direction"]},
        "window_days": exp["window_days"], "guardrails": guardrails,
        "confounders": list(template.get("confounders", [])),
    }
