"""Plain-language explanations. The LLM may only use numbers the engine produced (evidence packet + validator);
without a key, or when its answer fails the validator, the deterministic text below is used."""
from __future__ import annotations

from backend.decision_engine.llm.synthesize import Synthesizer
from backend.decision_engine.llm.validator import validate_explanation


def _fact_rows(findings: list[dict], facts: dict) -> list[dict]:
    """Every fact a card cites (its headline fact and the supporting ones), so any cited id is in the packet."""
    rows, seen = [], set()
    for f in findings:
        for c in f["cards"]:
            for fid in c["evidence_ids"]:
                if fid in seen or fid not in facts:
                    continue
                seen.add(fid)
                x = facts[fid]
                rows.append({"fact_id": fid, "kpi": x["kpi"], "dimension": x.get("dimension"), "value": x["value"],
                             "unit": x["unit"], "best_weeks": x["baseline"], "source": x.get("source"),
                             "sample_size": x.get("sample_size"),
                             "claim": c["claim"] if fid == c["source"]["fact_id"] else None})
    return rows


def diagnosis_packet(diag: dict, business: dict, facts: dict) -> dict:
    keep = [f for f in diag["bottlenecks"] if f["bottleneck"] == diag["primary"] or f["bottleneck"] in diag["runners_up"]]
    return {
        "task": "explain_diagnosis",
        "business": {"name": business["name"], "category": business.get("category"),
                     "forbidden_actions": business.get("constraints", {}).get("forbidden_actions", [])},
        "primary": diag["primary"], "runners_up": diag["runners_up"],
        "findings": [{"bottleneck": f["bottleneck"], "gap_to_best": f["gap_to_best"], "where": f.get("where"),
                      "impact": f.get("impact"), "passed": f["passed"]} for f in keep],
        "facts": _fact_rows(keep, facts),
        "main_measure": diag.get("main_measure"),
    }


def diagnosis_fallback(diag: dict) -> dict:
    if diag["primary"] is None:
        return {"summary": diag.get("message") or "No clear bottleneck this week.",
                "evidence_ids": [f["key_fact"] for f in diag["bottlenecks"] if f.get("key_fact")][:1] or ["none"]}
    p = next(f for f in diag["bottlenecks"] if f["bottleneck"] == diag["primary"])
    text = f"{p['label']} is what holds the business back most this week. {p['cards'][0]['claim']}"
    if p.get("where"):
        text += f" {p['where'][0].upper()}{p['where'][1:]}."
    others = [f for f in diag["bottlenecks"] if f["bottleneck"] in diag["runners_up"]]
    if others:
        text += " Next in line: " + ", ".join(
            f"{f['label'].lower()} ({round(f['gap_to_best'] * 100, 1):g}% from your best)" for f in others) + "."
    return {"summary": text, "evidence_ids": p["evidence_ids"][:4]}


def explain_diagnosis(diag: dict, business: dict, facts: dict, synthesizer: Synthesizer) -> dict:
    if diag["primary"] is None:
        out = diagnosis_fallback(diag)
        return {"text": out["summary"], "evidence_ids": [], "llm": {"used": False, "cached": False, "fallback": True}}
    packet = diagnosis_packet(diag, business, facts)
    out, meta = synthesizer.run("explain_diagnosis", packet, validate_explanation, lambda: diagnosis_fallback(diag))
    return {"text": out["summary"], "evidence_ids": out["evidence_ids"], "llm": meta}


def next_month_packet(nm: dict, business: dict, diag: dict, facts: dict) -> dict:
    primary = next((f for f in diag["bottlenecks"] if f["bottleneck"] == diag["primary"]), None)
    return {"task": "explain_next_month",
            "business": {"name": business["name"], "capacity_orders_per_week": business.get("capacity_orders_per_week"),
                         "forbidden_actions": business.get("constraints", {}).get("forbidden_actions", [])},
            "projection": {"month": nm["month"], "orders": nm["orders"], "basis": nm["basis"],
                           "capacity_month": nm["capacity_month"], "limited_by_capacity": nm["limited_by_capacity"],
                           "limiting_bottleneck": nm["limiting_bottleneck"], "demand_windows": nm["demand_windows"]},
            "facts": _fact_rows([primary], facts) if primary else [], "engine_text": nm["text"]}


def explain_next_month(nm: dict, business: dict, diag: dict, facts: dict, synthesizer: Synthesizer) -> dict:
    if nm.get("status") != "ok":
        return {"text": nm["message"], "evidence_ids": [], "llm": {"used": False, "cached": False, "fallback": True}}
    packet = next_month_packet(nm, business, diag, facts)
    ids = [f["fact_id"] for f in packet["facts"]][:2]
    out, meta = synthesizer.run("explain_next_month", packet, validate_explanation,
                                lambda: {"summary": nm["text"], "evidence_ids": ids or ["projection"]})
    return {"text": out["summary"], "evidence_ids": out["evidence_ids"], "llm": meta}
