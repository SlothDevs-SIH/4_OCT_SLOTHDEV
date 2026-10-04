"""Factor assembly for the priority score.

I, F, R, T  from the template
U           from the linked signals (highest urgency)
Q           data quality (overall confidence x KPI quality), model calibration (only when
            the action relies on lead scores) and rule strength, weighted 0.5 / 0.25 / 0.25
E, C, D     from the template, raised when the action is large for this business's
            capacity (E) or budget (C)
"""
QUALITY_MULTIPLIER = {"ok": 1.0, "partial": 0.75, "low": 0.5}
RULE_STRENGTH = {"rule": 1.0, "seasonal_median_mad_robust_z": 0.9, "isolation_forest": 0.8}
OPPORTUNITY_STRENGTH = 0.8  # cohort comparisons are observational
Q_WEIGHTS = {"data": 0.5, "model": 0.25, "rule": 0.25}


def worst_quality(flags) -> str:
    flags = [f for f in flags if f]
    return min(flags, key=lambda f: QUALITY_MULTIPLIER[f]) if flags else "ok"


def kpi_quality(template: dict, evidence_facts: list[dict], data_quality: dict) -> str:
    flags = [f["quality_flag"] for f in evidence_facts]
    flags.append(data_quality.get("kpi_quality", {}).get(template["kpi"]))
    return worst_quality(flags)


def rule_strength(signals: list[dict]) -> float:
    def one(s):
        base = RULE_STRENGTH.get(s["method"], 0.8)
        return min(base, OPPORTUNITY_STRENGTH) if s["type"] == "opportunity" else base
    return max((one(s) for s in signals), default=0.5)


def model_quality(lead_scores: dict) -> float:
    ece = (lead_scores.get("model_card") or {}).get("metrics", {}).get("calibration_error")
    return max(0.0, 1 - 10 * ece) if ece is not None else 0.5


def q_factor(template: dict, signals: list[dict], evidence_facts: list[dict], data_quality: dict,
             lead_scores: dict) -> tuple[float, dict]:
    parts = {
        "data": data_quality["overall"]["confidence"]
                * QUALITY_MULTIPLIER[kpi_quality(template, evidence_facts, data_quality)],
        "rule": rule_strength(signals),
    }
    if "lead_scores" in template["requires_data"]:
        parts["model"] = model_quality(lead_scores)
    total_w = sum(Q_WEIGHTS[k] for k in parts)
    q = sum(Q_WEIGHTS[k] * v for k, v in parts.items()) / total_w
    return round(q, 2), {k: round(v, 3) for k, v in parts.items()}


def assemble(template: dict, signals: list[dict], evidence_facts: list[dict], ctx: dict,
             data_quality: dict, lead_scores: dict) -> tuple[dict, dict]:
    """Return (factors, q_breakdown)."""
    t = template["factors"]
    weekly_min = ctx["capacity"].get("weekly_minutes") or 480
    budget = ctx["constraints"].get("weekly_ad_budget_inr") or 0
    q, q_parts = q_factor(template, signals, evidence_facts, data_quality, lead_scores)
    factors = {
        "I": t["I"],
        "U": max((s["urgency"] for s in signals), default=0.0),
        "F": t["F"], "R": t["R"], "T": t["T"],
        "Q": q,
        "E": round(max(t["E"], min(1.0, template["effort_min"] / weekly_min / 2)), 2),
        "C": round(max(t["C"], min(1.0, template["cost_inr"] / budget)) if budget else t["C"], 2),
        "D": t["D"],
    }
    return factors, q_parts
