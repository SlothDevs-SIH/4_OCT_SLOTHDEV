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


FIDELITY_MIN = 0.8  # below this the plan was not really executed, so the KPI says little

METHOD = ("Baseline and expected range were frozen at approval; the actual value comes from the "
          "day-7 snapshot. Fidelity (was it executed?) is judged separately from effectiveness "
          "(did the KPI move as expected?). There is no control group, so results are observational.")


def _days(period: dict) -> int:
    from datetime import date
    return (date.fromisoformat(period["to"]) - date.fromisoformat(period["from"])).days + 1


def fidelity(plan: dict, rec_id: str) -> dict:
    tasks = [t for t in plan["tasks"] if t["recommendation_id"] == rec_id]
    done = sum(t["status"] == "done" for t in tasks)
    doing = sum(t["status"] == "doing" for t in tasks)
    rate = round(done / len(tasks), 2) if tasks else 0.0
    return {"tasks_total": len(tasks), "tasks_done": done, "tasks_doing": doing, "rate": rate,
            "executed": rate >= FIDELITY_MIN}


def judge(led: dict, actual, fid: dict, elapsed_days: int) -> tuple[str, list[str]]:
    """promising | inconclusive | not_effective, with the reasons."""
    low, high, up = led["expected"]["low"], led["expected"]["high"], led["expected"]["direction"] == "up"
    if actual is None or led["baseline"] is None or low is None:
        return "inconclusive", ["no measurable day-7 value for this KPI"]
    reasons = []
    if not fid["executed"]:
        reasons.append(f"only {fid['tasks_done']} of {fid['tasks_total']} tasks done")
    if led["window_days"] > elapsed_days:
        reasons.append(f"measurement window is {led['window_days']} days; {elapsed_days} have passed")
    reached = actual >= low if up else actual <= high
    better = actual > led["baseline"] if up else actual < led["baseline"]
    if reasons:
        if reached:
            reasons.append("the KPI already reached the expected range")
        return "inconclusive", reasons
    if reached:
        return "promising", ["executed and the KPI reached the expected range"]
    if not better:
        return "not_effective", ["executed for the full window but the KPI did not improve"]
    return "inconclusive", ["the KPI improved but stayed below the expected range"]


def evaluate(plan: dict, recs: dict, day7_facts: list[dict], now: str) -> dict:
    facts = {f["fact_id"]: f for f in day7_facts}
    periods = [f["period"] for f in day7_facts]
    period = max(periods, key=lambda p: periods.count(p)) if periods else None
    elapsed = _days(period) if period else 0
    results = []
    for rid in plan["recommendation_ids"]:
        rec = recs[rid]
        led = rec.get("ledger")
        if not led:
            continue
        fact = facts.get(led["fact_id"]) if led["fact_id"] else None
        actual = fact["value"] if fact else None
        fid = fidelity(plan, rid)
        effect, reasons = judge(led, actual, fid, elapsed)
        guardrails = []
        for g in led["guardrails"]:
            gf = facts.get(g["fact_id"])
            value = gf["value"] if gf else None
            guardrails.append({**g, "value": value, "breached": value is not None and value > g["max"]})
        if any(g["breached"] for g in guardrails):
            reasons.append("a guardrail was breached; review before repeating this action")
        delta = (round((actual - led["baseline"]) / led["baseline"] * 100, 1)
                 if actual is not None and led["baseline"] else None)
        results.append({
            "recommendation_id": rid, "kpi": led["kpi"], "fact_id": led["fact_id"], "unit": led["unit"],
            "baseline": led["baseline"], "expected": {"low": led["expected"]["low"], "high": led["expected"]["high"]},
            "actual": actual, "delta_vs_baseline_pct": delta, "fidelity": fid, "effectiveness": effect,
            "reasons": reasons, "observational": True, "guardrails": guardrails,
            "confounders": led["confounders"],
        })
    return {"plan_id": plan["plan_id"], "business_id": plan["business_id"], "synthetic": plan.get("synthetic", False),
            "evaluated_at": now, "snapshot": {"phase": "day7", "period": period}, "observational": True,
            "method": METHOD, "outcomes": results}
