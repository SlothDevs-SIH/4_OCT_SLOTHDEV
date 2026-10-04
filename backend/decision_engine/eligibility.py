"""Eligibility / safety gate. Runs before scoring: a blocked action is never scored.

Blocks an action that is forbidden by the business's constraints, needs spend or time the
business does not have, needs data that is missing, or skips a required human approval.
"""
from __future__ import annotations

OUTREACH_OR_SPEND = {"outreach", "spend_increase", "experiment"}
CAMPAIGN_ID_MAX_QUARANTINE = 0.10


def _data_checks(inputs: dict) -> dict:
    ctx, quality, facts = inputs["context"], inputs["data_quality"], inputs["facts"]
    leads = inputs["lead_scores"].get("leads", [])
    channels = set(ctx.get("channels", []))

    def campaign_ids_ok():
        for imp in quality.get("imports", []):
            missing = sum(i["count"] for i in imp.get("issues", []) if i["code"] == "missing_campaign_id")
            if imp.get("rows_total") and missing / imp["rows_total"] > CAMPAIGN_ID_MAX_QUARANTINE:
                return False
        return True

    return {
        "lead_scores": lambda: any(not l["abstain"] for l in leads),
        "email_consent": lambda: "email" in channels,
        "whatsapp_consent": lambda: "whatsapp" in channels,
        "campaign_ids": campaign_ids_ok,
        "sessions": lambda: any(f["kpi"] == "funnel_sessions" for f in facts),
    }


def _channel_context(signals: list[dict], facts_by_id: dict) -> str:
    """'Instagram CAC is up 49.3% and contribution ROAS is 0.694, ...' from the cited facts."""
    for s in signals:
        ch = s["dimension"].get("channel")
        if not ch:
            continue
        cac = facts_by_id.get(f"f_cac_{ch}")
        croas = facts_by_id.get(f"f_croas_{ch}")
        if cac and croas and croas["value"] < 1:
            return (f" {ch.title()} CAC is up {cac['delta_pct']:g}% and contribution ROAS is "
                    f"{croas['value']:g}, so more spend buys customers below break-even.")
    return ""


def _phrase(action: str) -> str:
    """increase_total_ad_spend -> 'increase in total ad spend'"""
    for verb in ("increase", "decrease", "reduce", "change"):
        if action.startswith(verb + "_"):
            return f"{verb} in {action[len(verb) + 1:].replace('_', ' ')}"
    return action.replace("_", " ")


def gate(template: dict, signals: list[dict], inputs: dict) -> dict:
    ctx = inputs["context"]
    cons, cap = ctx["constraints"], ctx["capacity"]
    facts_by_id = {f["fact_id"]: f for f in inputs["facts"]}
    checks = []

    def check(name, passed, detail):
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    forbidden = set(cons.get("forbidden_actions", []))
    hit = sorted(forbidden & {template["spend_change"], template["action_type"]})
    check("forbidden_action", not hit,
          f"Violates the constraint 'no {_phrase(hit[0])}' (forbidden action: {hit[0]})."
          if hit else "Not a forbidden action.")

    extra = cons.get("extra_spend_allowed_inr", 0) or 0
    check("budget", template["cost_inr"] <= extra,
          f"Needs INR {template['cost_inr']:g} of extra spend; INR {extra:g} is allowed."
          if template["cost_inr"] > extra else "Fits the budget.")

    weekly = cap.get("weekly_minutes") or cap.get("weekly_hours", 0) * 60
    check("capacity", template["effort_min"] <= weekly,
          f"Needs {template['effort_min']} minutes; the team has {weekly} a week."
          if template["effort_min"] > weekly else "Fits weekly capacity.")

    available = _data_checks(inputs)
    missing = [d for d in template["requires_data"] if d not in available or not available[d]()]
    check("data", not missing, f"Needs data that is missing: {', '.join(missing)}." if missing else "Required data present.")

    unsafe = template["action_type"] in OUTREACH_OR_SPEND and not template["requires_approval"]
    check("approval", not unsafe, "Spend or outreach without human approval is not allowed."
          if unsafe else "Human approval required." if template["requires_approval"] else "No approval needed.")

    failed = [c for c in checks if not c["passed"]]
    reason = None
    if failed:
        reason = failed[0]["detail"]
        if failed[0]["check"] in ("forbidden_action", "budget"):
            reason += _channel_context(signals, facts_by_id)
    return {"eligible": not failed, "blocked_reason": reason, "checks": checks}
