"""Diagnosis: name the ONE bottleneck among reach, conversion, margin, repeat orders and capacity.

The calculations decide; the LLM only explains later. Facts are grouped by data_engine's `bottleneck` tag.
Within a group a few DECISIVE facts may decide the bottleneck; every other fact with the tag is supporting
evidence (shown on the cards, used to localise). For each bottleneck:

  gap_to_best   data_engine's gap of its decisive fact, clipped to 0..1 (0 = at its best, 1 = 100% or more worse)
  four tests    materiality  - 20+ orders in the window, and the gap is worth at least 2 orders (or leads,
                               customers), INR 500, or half a day of dispatch
                deviation    - the gap is at least 20%
                localisation - we can say where: which source, stage, cause or step
                actionability- an eligible action exists in the library (checked by the caller)

The primary bottleneck is the largest gap among those passing all four tests; ties go to the one the owner
can act on with less effort. Every finding carries an evidence card: claim, number, source and confidence.
"""
from __future__ import annotations

from typing import Callable, Optional

BOTTLENECKS = ("reach", "conversion", "margin", "repeat_orders", "capacity")
MIN_ORDERS = 20          # below this: no verdict
SOLID_ORDERS = 40        # below this: findings are shown as estimates
DEVIATION = 0.20
LABELS = {"reach": "Reach", "conversion": "Conversion", "margin": "Margin", "repeat_orders": "Repeat orders",
          "capacity": "Capacity"}

# Facts that may decide each bottleneck. Others with the same tag are supporting evidence. Orders per 1,000
# people reached is supporting only: most orders of a home business come from people who do not depend on
# Instagram reach (friends), so its gap mixes audience with conversion.
DECISIVE = {
    "reach": ("f_stranger_orders_week", "f_stranger_share"),
    "conversion": ("f_lead_to_order_rate",),
    "margin": ("f_margin_pct", "f_margin_per_order"),
    "repeat_orders": ("f_repeat_customer_share",),
    "capacity": ("f_orders_turned_away", "f_dispatch_delay_days", "f_stockouts"),
}
MONEY_RATIOS = {"margin_pct", "discount_share"}  # ratios whose denominator is money (INR), not a count


def fmt(value, unit: str) -> str:
    if value is None:
        return "n/a"
    if unit == "ratio":
        return f"{round(value * 100, 1):g}%"
    if unit == "INR":
        return f"INR {round(value):,}"
    if unit == "days":
        return f"{round(value, 1):g} days"
    if unit == "orders/week":
        return f"{round(value, 2):g} a week"
    return f"{round(value, 2):g}"


def gap(fact: Optional[dict]) -> Optional[float]:
    """data_engine's gap_to_best, clipped to 0..1 (computed from value and baseline if missing)."""
    if not fact or fact.get("better") not in ("higher", "lower") or fact.get("value") is None or fact.get("baseline") is None:
        return None
    g = fact.get("gap_to_best")
    if g is None:
        b, v = fact["baseline"], fact["value"]
        if not b:
            return None
        g = (b - v) / b if fact["better"] == "higher" else (v - b) / b
    return round(min(1.0, max(0.0, g)), 4)


def shortfall(fact: dict, window_weeks: int) -> tuple[float, str, float]:
    """What the gap costs in the window: (amount, what, threshold to matter)."""
    v, b = fact["value"], fact["baseline"]
    diff = max(0.0, (b - v) if fact["better"] == "higher" else (v - b))
    unit = fact["unit"]
    if unit == "orders/week":
        return diff * window_weeks, "orders", 2
    if unit == "ratio":
        if fact["kpi"] in MONEY_RATIOS:
            return diff * (fact.get("denominator") or 0), "INR", 500
        return diff * (fact.get("denominator") or 0), fact.get("sample_kind") or "items", 2
    if unit == "INR":
        return diff * (fact.get("sample_size") or 0), "INR", 500
    if unit == "days":
        return diff, "days", 0.5
    return diff, fact.get("sample_kind") or "count", 2


def confidence(fact: dict, orders: int) -> str:
    if orders < SOLID_ORDERS or fact.get("quality_flag") in ("partial", "low"):
        return "estimate"
    return fact.get("source") or "derived"


CLAIMS = {
    "stranger_share": "{v} of your orders in the last 4 weeks came from strangers, against {b} in your best weeks.",
    "stranger_orders_per_week": "Orders from strangers: {v} on average over the last 4 weeks (best weeks: {b}).",
    "lead_to_order_rate": "{v} of people who showed interest ordered, against {b} in your best weeks.",
    "orders_per_1000_reach": "{v} orders per 1,000 people reached (best weeks: {b}).",
    "profile_visit_rate": "{v} of people reached visited your profile (best weeks: {b}).",
    "follow_rate": "{v} of profile visitors followed you (best weeks: {b}).",
    "posts_with_orders": "{v} of your posts led to an order (best weeks: {b}).",
    "reach_per_post": "Each post reached {v} people on average (best weeks: {b}).",
    "margin_pct": "You keep {v} of each order after full costs, against {b} in your best weeks.",
    "margin_per_order": "Margin per order: {v} (best weeks: {b}).",
    "discount_share": "Discounts are {v} of sales (best weeks: {b}).",
    "repeat_customer_share": "{v} of your customers have ordered more than once (best: {b}).",
    "orders_turned_away": "{v} orders were turned away in the last 4 weeks, against {b} in your best weeks.",
    "dispatch_delay_days": "Orders take {v} to go out, against {b} in your best weeks.",
    "stockouts": "{v} stock-outs in the last 4 weeks (best weeks: {b}).",
}


def card(fact: dict, orders: int, extra_ids=()) -> dict:
    unit = fact["unit"]
    v, b = fmt(fact["value"], unit), fmt(fact.get("baseline"), unit)
    if unit == "count" or fact["kpi"] in ("orders_turned_away", "stockouts"):
        v, b = f"{fact['value']:g}", (f"{fact['baseline']:g}" if fact.get("baseline") is not None else "n/a")
    tmpl = CLAIMS.get(fact["kpi"], fact["kpi"].replace("_", " ").capitalize() + " is {v} (best weeks: {b}).")
    claim = tmpl.format(v=v, b=b)
    return {"claim": claim[0].upper() + claim[1:],
            "number": {"value": fact["value"], "unit": unit, "display": v},
            "best_weeks": {"value": fact.get("baseline"), "display": b, "period": fact.get("best_period")},
            "source": {"fact_id": fact["fact_id"], "origin": fact.get("origin"), "provenance": fact.get("source"),
                       "period": fact.get("period")},
            "confidence": confidence(fact, orders), "sample_size": fact.get("sample_size"),
            "evidence_ids": [fact["fact_id"], *extra_ids]}


def _where(b: str, key: dict, group: dict) -> Optional[str]:
    """Localisation, generic over the facts that carry the bottleneck's tag."""
    if b == "reach":
        src = {fid.removeprefix("f_orders_by_source_"): f for fid, f in group.items() if f["kpi"] == "orders_by_source"}
        if "stranger" not in src:
            return None
        total = key.get("sample_size") or sum((f.get("numerator") or 0) for f in src.values())
        circle = sum((src[s].get("numerator") or 0) for s in ("friend", "friend_of_friend") if s in src)
        return (f"the gap is in orders from strangers: {circle:g} of {total:g} orders in the last 4 weeks came from "
                f"friends and friends of friends")
    if b == "conversion":
        stages = [(f, gap(f)) for f in group.values() if gap(f) is not None]
        if not stages:
            return None
        worst = max(stages, key=lambda x: x[1])[0]
        return f"the biggest drop is in {worst['kpi'].replace('_', ' ')}"
    if b == "margin":
        causes = [f["kpi"].replace("_", " ") for f in group.values()
                  if f["fact_id"] != key["fact_id"] and gap(f) is not None and gap(f) >= DEVIATION
                  and shortfall(f, 4)[0] >= shortfall(f, 4)[2]]
        return ("it comes from " + " and ".join(causes)) if causes else "price is low for the full unit cost"
    if b == "repeat_orders":
        return "first-time buyers are not coming back" if any(f["kpi"] == "days_between_orders" for f in group.values()) else None
    if b == "capacity":
        step = {"orders_turned_away": "demand above what you can make", "dispatch_delay_days": "dispatch",
                "stockouts": "making (stock-outs)"}.get(key["kpi"], key["kpi"].replace("_", " "))
        return f"the limit is {step}"
    return None


def _reason(tests: dict, why_not: Optional[str]) -> str:
    words = {"materiality": "too small to matter yet", "deviation": "within 20% of your best weeks",
             "localisation": "cannot say where the problem is", "actionability": why_not or "no eligible action this week"}
    return "; ".join(words[k] for k, ok in tests.items() if not ok)


def score_bottleneck(b: str, group: dict, orders: int, window_weeks: int) -> Optional[dict]:
    decisive = [group[fid] for fid in DECISIVE[b] if fid in group and gap(group[fid]) is not None]
    if not decisive:
        return None
    rated = []
    for f in decisive:
        amount, what, threshold = shortfall(f, window_weeks)
        rated.append({"fact": f, "gap": gap(f), "amount": amount, "what": what, "material": amount >= threshold})
    material = [r for r in rated if r["material"]]
    key = max(material or rated, key=lambda r: r["gap"])
    f = key["fact"]
    supporting = [x for fid, x in group.items() if fid != f["fact_id"]]
    extra = [x["fact_id"] for x in supporting if x["kpi"] == "orders_by_source"] if b == "reach" else []
    cards = [card(f, orders, extra)] + [card(o, orders) for o in decisive if o["fact_id"] != f["fact_id"]]
    if key["what"] == "INR":
        impact = f"about INR {round(key['amount']):,} in the last 4 weeks"
    elif key["what"] == "days":
        impact = f"about {round(key['amount'], 1):g} days slower"
    else:
        impact = f"about {round(key['amount'], 1):g} {key['what']} in the last 4 weeks"
    return {"gap": key["gap"], "material": key["material"], "key_fact": f["fact_id"], "impact": impact,
            "where": _where(b, f, group), "cards": cards, "supporting_ids": [x["fact_id"] for x in supporting]}


def diagnose(facts_doc: dict, actionable: Callable[[str], tuple[bool, Optional[int], Optional[str]]]) -> dict:
    """`actionable(bottleneck) -> (has_eligible_action, min_effort_minutes, reason_if_not)`."""
    facts = facts_doc["facts"]
    window = facts_doc.get("window_weeks") or 4
    groups = {b: {f["fact_id"]: f for f in facts if f.get("bottleneck") == b} for b in BOTTLENECKS}
    orders = max([f.get("sample_size") or 0 for f in facts if f.get("sample_kind") == "orders"] or [0])
    findings = []
    for b in BOTTLENECKS:
        s = score_bottleneck(b, groups[b], orders, window)
        if s is None:
            findings.append({"bottleneck": b, "label": LABELS[b], "gap_to_best": None, "passed": False, "tests": None,
                             "reason": "the facts for this bottleneck are missing", "cards": [], "evidence_ids": [],
                             "confidence": None, "key_fact": None})
            continue
        ok, effort, why_not = actionable(b)
        tests = {"materiality": orders >= MIN_ORDERS and s["material"], "deviation": s["gap"] >= DEVIATION,
                 "localisation": s["where"] is not None, "actionability": ok}
        evidence = []
        for c in s["cards"]:
            evidence += [e for e in c["evidence_ids"] if e not in evidence]
        findings.append({
            "bottleneck": b, "label": LABELS[b], "gap_to_best": s["gap"], "tests": tests, "passed": all(tests.values()),
            "where": s["where"], "impact": s["impact"], "key_fact": s["key_fact"], "min_action_effort": effort,
            "cards": s["cards"], "evidence_ids": evidence, "supporting_fact_ids": s["supporting_ids"],
            "confidence": s["cards"][0]["confidence"], "reason": None if all(tests.values()) else _reason(tests, why_not),
        })
    passing = sorted((f for f in findings if f["passed"]), key=lambda f: (-f["gap_to_best"], f["min_action_effort"] or 10 ** 6))
    status, message, primary = "ok", None, None
    if orders < MIN_ORDERS:
        status = "not_enough_data"
        message = (f"Only {orders} orders in the last 4 weeks. At least {MIN_ORDERS} are needed before naming a "
                   f"bottleneck; the numbers below are estimates.")
        for f in findings:
            for c in f["cards"]:
                c["confidence"] = "estimate"
            f["confidence"] = "estimate" if f["cards"] else None
    elif not passing:
        status = "no_clear_bottleneck"
        message = "Nothing is clearly holding the business back compared with its own best weeks. Keep doing what works."
    else:
        primary = passing[0]["bottleneck"]
    others = sorted((f for f in findings if f["gap_to_best"] is not None and f["bottleneck"] != primary),
                    key=lambda f: (not (f["tests"] or {}).get("materiality"), -f["gap_to_best"]))
    week_fact = next((f for f in facts if f["fact_id"] == "f_stranger_orders_week"), None)
    return {
        "business_id": facts_doc["business_id"], "week": facts_doc["week"], "as_of": facts_doc.get("as_of"),
        "synthetic": facts_doc.get("synthetic", False), "status": status, "message": message,
        "orders_in_window": orders, "primary": primary, "runners_up": [f["bottleneck"] for f in others[:2]],
        "rejected": [{"bottleneck": f["bottleneck"], "reason": f["reason"]}
                     for f in findings if not f["passed"] and f["bottleneck"] != primary],
        "main_measure": ({"fact_id": week_fact["fact_id"], "stranger_orders_per_week": week_fact["value"],
                          "best_weeks": week_fact.get("baseline"), "unit": week_fact["unit"]} if week_fact else None),
        "bottlenecks": findings,
        "rule": "largest gap to your own best weeks among bottlenecks passing all four tests",
        "decisive_facts": {b: list(v) for b, v in DECISIVE.items()},
    }
