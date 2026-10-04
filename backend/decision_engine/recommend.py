"""Recommendation pipeline: signals -> candidates -> eligibility -> priority -> LLM explanation."""
from __future__ import annotations

import math
from typing import Optional

from backend.decision_engine import eligibility, factors, scoring, templates
from backend.decision_engine.llm.synthesize import Synthesizer
from backend.decision_engine.llm.validator import validate_recommendation
from backend.decision_engine.signals import Facts

KPI_LABELS = {"lead_wins": "lead wins", "repeat_rate": "repeat rate", "contribution_roas": "contribution ROAS",
              "conversion_rate": "conversion rate", "new_customers": "new customers", "cac": "CAC"}


def kpi_label(kpi: str) -> str:
    return KPI_LABELS.get(kpi, kpi.replace("_", " "))


# ---------------------------------------------------------------- building blocks


def group_candidates(signal_list: list[dict]) -> list[tuple[dict, list[dict]]]:
    """One candidate per template, with every signal that triggered it (first-seen order)."""
    by_id = templates.templates_by_id()
    groups: dict[str, list] = {}
    for s in signal_list:
        for tid in s["candidate_template_ids"]:
            groups.setdefault(tid, []).append(s)
    return [(by_id[tid], sigs) for tid, sigs in groups.items()]


def resolve_fact(facts: Facts, kpi: str, signal_list: list[dict]) -> Optional[dict]:
    for s in signal_list:
        f = facts.get(kpi, **s["dimension"])
        if f:
            return f
    return facts.get(kpi)


def targets(template: dict, signal_list: list[dict], lead_index: dict) -> dict:
    channel = next((s["dimension"]["channel"] for s in signal_list if "channel" in s["dimension"]), None)
    lead_ids = []
    if "lead_scores" in template["requires_data"]:
        for s in signal_list:
            lead_ids += [e for e in s["evidence_ids"] if e in lead_index and e not in lead_ids]
    segment = next((s["dimension"]["segment"] for s in signal_list if "segment" in s["dimension"]), None)
    return {"channel": channel, "segment": segment, "lead_ids": lead_ids}


def _round_like(fact: dict, x: float):
    if fact["unit"] == "count":
        return int(round(x))
    if fact["unit"] == "ratio":
        return round(x, 3)
    return round(x, 1)


def expected_range(template: dict, fact: Optional[dict], tgt: dict, lead_index: dict) -> dict:
    exp = {"kpi": template["kpi"], "fact_id": fact["fact_id"] if fact else None,
           "direction": template["expected_direction"], "low": None, "high": None,
           "unit": fact["unit"] if fact else None, "window_days": template["measurement_window_days"]}
    if not fact:
        return exp
    rule = template["expected_change"]
    if rule["method"] == "lead_probability_sum":
        total = sum(lead_index[l]["probability"] for l in tgt["lead_ids"] if lead_index[l]["probability"])
        exp["low"], exp["high"] = max(0, round(total - rule["band"])), round(total + rule["band"])
        exp["basis"] = f"sum of calibrated probabilities of the targeted leads ({round(total, 2)}) +/- {rule['band']}"
    else:
        sign = 1 if template["expected_direction"] == "up" else -1
        lo = fact["value"] * (1 + sign * rule["low_pct"] / 100)
        hi = fact["value"] * (1 + sign * rule["high_pct"] / 100)
        exp["low"], exp["high"] = _round_like(fact, min(lo, hi)), _round_like(fact, max(lo, hi))
        exp["basis"] = f"{rule['low_pct']}% to {rule['high_pct']}% change from the current value"
    return exp


def confidence(q: float, quality: str, expected: dict) -> str:
    if expected["fact_id"] is None:
        return "low"  # no measurable KPI -> low confidence, not dressed up
    if q >= 0.85 and quality == "ok":
        return "high"
    return "medium" if q >= 0.6 else "low"


def assumptions(template: dict, signal_list: list[dict], inputs: dict, quality: str) -> list[str]:
    out = []
    if "lead_scores" in template["requires_data"]:
        caveats = (inputs["lead_scores"].get("model_card") or {}).get("caveats") or []
        out.append(caveats[0] if caveats else "Lead probabilities come from the lead-conversion model")
    if quality != "ok":
        out.append(f"Data quality for {kpi_label(template['kpi'])} is {quality}: "
                   f"{inputs['data_quality']['overall'].get('summary', '')}".strip())
    if any(s["type"] == "opportunity" for s in signal_list):
        out.append("The cohort comparison is observational, not proof of cause")
    out += template.get("confounders", [])
    return out


def format_text(text: str, ctx: dict, tgt: dict) -> str:
    leads = tgt.get("lead_ids") or []
    half = math.ceil(len(leads) / 2)
    values = {"leads_a": ", ".join(leads[:half]), "leads_b": ", ".join(leads[half:]),
              "sla_hours": f"{ctx['constraints'].get('lead_response_sla_hours', 24):g}",
              "channel_title": (tgt.get("channel") or "ad").title()}
    return text.format(**values)


# ---------------------------------------------------------------- LLM packet + fallback


def evidence_packet(rec: dict, template: dict, signal_list: list[dict], facts: Facts, lead_index: dict,
                    ctx: dict) -> dict:
    fact_ids = []
    for s in signal_list:
        fact_ids += [e for e in s["evidence_ids"] if e in facts.by_id and e not in fact_ids]
    if rec["expected"]["fact_id"] and rec["expected"]["fact_id"] not in fact_ids:
        fact_ids.append(rec["expected"]["fact_id"])
    keep = ("fact_id", "kpi", "dimension", "value", "unit", "baseline", "delta_pct", "quality_flag")
    return {
        "task": "explain_recommendation",
        "business": {"name": ctx.get("name"), "goal": (ctx.get("goal") or {}).get("statement"),
                     "constraints": ctx["constraints"]},
        "recommendation": {k: rec[k] for k in ("recommendation_id", "template_id", "title", "status",
                                               "blocked_reason", "priority", "confidence", "expected")},
        "template": {"template_id": template["template_id"], "title": template["title"],
                     "kpi": template["kpi"], "expected_direction": template["expected_direction"],
                     "steps": [format_text(t["title"], ctx, rec["targets"]) for t in template["tasks"]]},
        "allowed_template_ids": [template["template_id"]],
        "signals": [{"signal_id": s["signal_id"], "type": s["type"], "title": s["title"]} for s in signal_list],
        "facts": [{k: facts.by_id[f][k] for k in keep} for f in fact_ids],
        "leads": [{k: lead_index[l].get(k) for k in ("lead_id", "label", "probability", "expected_value_inr",
                                                     "hours_since_inquiry", "rank")}
                  for l in rec["targets"]["lead_ids"]],
    }


def fallback_explanation(rec: dict, signal_list: list[dict], default_evidence: list[str]) -> dict:
    if rec["status"] == "blocked":
        text = rec["blocked_reason"]
    else:
        e = rec["expected"]
        text = ". ".join(s["title"] for s in signal_list) + f". Recommended action: {rec['title'].lower()}."
        if e["low"] is not None:
            text += (f" Success means {kpi_label(e['kpi'])} between {e['low']:g} and {e['high']:g} "
                     f"within {e['window_days']} days.")
    return {"template_id": rec["template_id"], "rationale": text, "evidence_ids": default_evidence}


# ---------------------------------------------------------------- pipeline


def build(inputs: dict, signals_doc: dict, synthesizer: Synthesizer, now: str) -> list[dict]:
    ctx = inputs["context"]
    facts = Facts(inputs["facts"])
    lead_index = {l["lead_id"]: l for l in inputs["lead_scores"].get("leads", [])}
    recs = []
    for template, sigs in group_candidates(signals_doc["signals"]):
        evidence_facts = []
        for s in sigs:
            evidence_facts += [facts.by_id[e] for e in s["evidence_ids"]
                               if e in facts.by_id and facts.by_id[e] not in evidence_facts]
        gate = eligibility.gate(template, sigs, inputs)
        f, q_parts = factors.assemble(template, sigs, evidence_facts, ctx, inputs["data_quality"],
                                      inputs["lead_scores"])
        quality = factors.kpi_quality(template, evidence_facts, inputs["data_quality"])
        tgt = targets(template, sigs, lead_index)
        expected = expected_range(template, resolve_fact(facts, template["kpi"], sigs), tgt, lead_index)
        rec = {
            "recommendation_id": f"rec_{template['recommendation_slug']}",
            "business_id": ctx["business_id"], "template_id": template["template_id"],
            "signal_ids": [s["signal_id"] for s in sigs], "title": template["title"],
            "rationale": None, "evidence_ids": [], "factors": f, "q_breakdown": q_parts,
            "benefit": None, "cost_penalty": None, "priority": None, "rank": None,
            "status": "proposed" if gate["eligible"] else "blocked",
            "blocked_reason": gate["blocked_reason"], "eligibility": gate["checks"],
            "expected": expected, "confidence": confidence(f["Q"], quality, expected),
            "assumptions": assumptions(template, sigs, inputs, quality),
            "requires_approval": template["requires_approval"], "approval_reason": template["approval_reason"],
            "risks": template["risks"], "targets": tgt, "synthetic": ctx.get("synthetic", False),
            "created_at": now, "updated_at": now, "decision": None, "ledger": None,
        }
        if gate["eligible"]:
            rec.update(scoring.score(f))  # blocked actions are never scored
        default_evidence = [x["fact_id"] for x in evidence_facts] + tgt["lead_ids"][:2]
        if rec["status"] == "blocked":
            # no LLM call for blocked actions: the gate's reason is the explanation
            out = fallback_explanation(rec, sigs, [x["fact_id"] for x in evidence_facts][:3])
            meta = {"used": False, "cached": False, "provider": None, "model": None, "fallback": True,
                    "validator": {"passed": True, "retries": 0, "errors": []}, "prompt_version": None}
        else:
            packet = evidence_packet(rec, template, sigs, facts, lead_index, ctx)
            out, meta = synthesizer.run("explain_recommendation", packet, validate_recommendation,
                                        lambda: fallback_explanation(rec, sigs, default_evidence))
        rec["rationale"], rec["evidence_ids"] = out["rationale"], out["evidence_ids"]
        rec["assumptions"] += [a for a in out.get("assumptions", []) if a not in rec["assumptions"]]
        rec["llm"] = meta
        recs.append(rec)
    return recs


def rank(recs: list[dict]) -> list[dict]:
    scored = sorted((r for r in recs if r["priority"] is not None), key=lambda r: -r["priority"])
    for i, r in enumerate(scored, 1):
        r["rank"] = i
    blocked = [r for r in recs if r["priority"] is None]
    for r in blocked:
        r["rank"] = None
    return scored + blocked
