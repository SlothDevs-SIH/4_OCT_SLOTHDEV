"""Diagnosis: name the ONE bottleneck among reach, conversion, margin, repeat orders and capacity.

The calculations decide; the LLM only explains later. For each bottleneck:

  gap_to_best   how far the key fact is from the business's own best weeks (0 = at its best, 1 = 100% worse)
  four tests    materiality  - enough orders, and the gap is worth at least a couple of orders (or INR 500)
                deviation    - the gap is at least 20%
                localisation - we can say where: which source, stage, cause or step
                actionability- an eligible action exists in the library (checked by the caller)

The primary bottleneck is the largest gap among those passing all four tests; ties go to the one
the owner can act on with less effort. Every finding carries an evidence card: claim, number,
source and confidence. Under MIN_ORDERS orders the engine gives no verdict, only estimates.
"""
from __future__ import annotations

from typing import Callable, Optional

BOTTLENECKS = ("reach", "conversion", "margin", "repeat_orders", "capacity")
MIN_ORDERS = 20          # below this: no verdict
SOLID_ORDERS = 40        # below this: every finding is shown as an estimate
DEVIATION = 0.20
LABELS = {"reach": "Reach", "conversion": "Conversion", "margin": "Margin", "repeat_orders": "Repeat orders",
          "capacity": "Capacity"}


# ---------------------------------------------------------------- formatting


def fmt(value, unit: str) -> str:
    if value is None:
        return "n/a"
    if unit == "ratio":
        return f"{round(value * 100, 1):g}%"
    if unit == "INR":
        return f"INR {value:,.10g}"
    if unit == "days":
        return f"{value:g} days"
    return f"{round(value, 1):g}"


def gap(fact: Optional[dict]) -> Optional[float]:
    """Relative shortfall against the own-best baseline, clipped to 0..1."""
    if not fact or fact["value"] is None or not fact["baseline"]:
        return None
    v, b = fact["value"], fact["baseline"]
    raw = (b - v) / b if fact.get("direction") == "up" else (v - b) / b
    return round(min(1.0, max(0.0, raw)), 3)


class Facts:
    def __init__(self, facts: list[dict]):
        self.by_id = {f["fact_id"]: f for f in facts}

    def __getitem__(self, fid):
        return self.by_id.get(fid)

    def ids(self, *fids):
        return [f for f in fids if f in self.by_id]


def confidence(fact: dict, sample: int) -> str:
    """exact | estimate | derived, downgraded to estimate when the sample is small."""
    if sample < SOLID_ORDERS or fact.get("quality_flag") in ("partial", "low"):
        return "estimate"
    return fact.get("source") or "derived"


def card(claim: str, fact: dict, sample: int, extra_ids=()) -> dict:
    return {"claim": claim,
            "number": {"value": fact["value"], "unit": fact["unit"], "display": fmt(fact["value"], fact["unit"])},
            "best_weeks": {"value": fact["baseline"], "display": fmt(fact["baseline"], fact["unit"])},
            "source": {"fact_id": fact["fact_id"], "origin": fact.get("origin"), "provenance": fact.get("source"),
                       "period": fact.get("period")},
            "confidence": confidence(fact, sample), "sample_size": fact.get("sample_size"),
            "evidence_ids": [fact["fact_id"], *extra_ids]}


# ---------------------------------------------------------------- the five scorers
# each returns dict(gap, material, localised, where, cards, evidence_ids) or None when the facts are missing


def score_reach(F: Facts, n: int) -> Optional[dict]:
    share, week = F["f_stranger_share"], F["f_stranger_orders_week"]
    g = gap(share)
    if g is None:
        return None
    lost = (share["baseline"] - share["value"]) * (share["denominator"] or 0)
    src = {s: F[f"f_orders_by_source_{s}"] for s in ("friend", "friend_of_friend", "stranger", "unknown")}
    circle = sum(f["value"] for k, f in src.items() if f and k in ("friend", "friend_of_friend"))
    localised = src["stranger"] is not None
    where = (f"the gap is in orders from strangers: {circle} of {n} orders in the last 4 weeks came from "
             f"friends and friends of friends" if localised else None)
    cards = [card(f"Only {fmt(share['value'], 'ratio')} of your orders in the last 4 weeks came from strangers, "
                  f"against {fmt(share['baseline'], 'ratio')} in your best weeks.", share, n,
                  F.ids("f_orders_by_source_stranger", "f_orders_by_source_friend", "f_orders_by_source_friend_of_friend"))]
    if week:
        cards.append(card(f"Orders from strangers this week: {fmt(week['value'], 'count')} "
                          f"(best weeks: {fmt(week['baseline'], 'count')}).", week, n))
    return {"gap": g, "material": lost >= 2, "impact": f"about {round(lost)} more orders from strangers in 4 weeks "
            f"at your best share", "localised": localised, "where": where, "cards": cards,
            "key_fact": share["fact_id"]}


def score_conversion(F: Facts, n: int) -> Optional[dict]:
    rate = F["f_lead_to_order_rate"]
    g = gap(rate)
    if g is None:
        return None
    lost = (rate["baseline"] - rate["value"]) * (rate["denominator"] or 0)
    stages = {"reach to profile visit": F["f_profile_visit_rate"], "visit to follow": F["f_follow_rate"],
              "interest to order": rate}
    worst = max(((k, gap(f)) for k, f in stages.items() if gap(f) is not None), key=lambda kv: kv[1], default=None)
    cards = [card(f"{fmt(rate['value'], 'ratio')} of people who showed interest ordered, against "
                  f"{fmt(rate['baseline'], 'ratio')} in your best weeks.", rate, n)]
    if F["f_orders_per_1000_reach"]:
        o = F["f_orders_per_1000_reach"]
        cards.append(card(f"{fmt(o['value'], 'count')} orders per 1,000 people reached "
                          f"(best weeks: {fmt(o['baseline'], 'count')}).", o, n))
    return {"gap": g, "material": lost >= 2, "impact": f"about {round(lost)} more orders in 4 weeks from the same interest",
            "localised": worst is not None, "where": f"the biggest drop is at {worst[0]}" if worst else None,
            "cards": cards, "key_fact": rate["fact_id"]}


def score_margin(F: Facts, n: int) -> Optional[dict]:
    pct = F["f_margin_pct"]
    g = gap(pct)
    if g is None:
        return None
    lost = (pct["baseline"] - pct["value"]) * (pct["denominator"] or 0)
    cost, disc = F["f_unit_cost_full"], F["f_discount_share"]
    causes = []
    if cost and (gap(cost) or 0) >= 0.05:
        causes.append("full unit cost has risen")
    if disc and (gap(disc) or 0) >= 0.2:
        causes.append("more orders are discounted")
    where = " and ".join(causes) if causes else "price is low for the full unit cost"
    cards = [card(f"You keep {fmt(pct['value'], 'ratio')} of each order after full costs, against "
                  f"{fmt(pct['baseline'], 'ratio')} in your best weeks.", pct, n, F.ids("f_unit_cost_full"))]
    if F["f_margin_per_order"]:
        m = F["f_margin_per_order"]
        cards.append(card(f"Margin per order: {fmt(m['value'], 'INR')}.", m, n))
    return {"gap": g, "material": lost >= 500, "impact": f"about INR {round(lost):,} more margin in 4 weeks",
            "localised": cost is not None, "where": where, "cards": cards, "key_fact": pct["fact_id"]}


def score_repeat(F: Facts, n: int) -> Optional[dict]:
    share = F["f_repeat_customer_share"]
    g = gap(share)
    if g is None:
        return None
    lost = (share["baseline"] - share["value"]) * (share["denominator"] or 0)
    days = F["f_days_between_orders"]
    cards = [card(f"{fmt(share['value'], 'ratio')} of your customers have ordered more than once, against "
                  f"{fmt(share['baseline'], 'ratio')} at your best.", share, n)]
    if days and days["value"] is not None:
        cards.append(card(f"Returning buyers come back after {fmt(days['value'], 'days')} (median).", days, n))
    return {"gap": g, "material": lost >= 2, "impact": f"about {round(lost)} more returning customers",
            "localised": bool(days and days["value"] is not None),
            "where": "first-time buyers are not coming back" if days else None, "cards": cards,
            "key_fact": share["fact_id"]}


def score_capacity(F: Facts, n: int) -> Optional[dict]:
    delay, away, stock = F["f_dispatch_delay_days"], F["f_orders_turned_away"], F["f_stockouts"]
    parts = []
    if gap(delay) is not None:
        parts.append(("dispatch", gap(delay)))
    if away and away["value"]:
        parts.append(("demand above your limit", round(away["value"] / max(1, away["denominator"] or 1), 3)))
    if not parts:
        return None if delay is None else {"gap": 0.0, "material": False, "impact": None, "localised": False,
                                           "where": None, "cards": [], "key_fact": delay["fact_id"]}
    step, g = max(parts, key=lambda p: p[1])
    turned = away["value"] if away else 0
    slower = (delay["value"] - delay["baseline"]) if (delay and delay["baseline"]) else 0
    cards = []
    if delay:
        cards.append(card(f"Orders take {fmt(delay['value'], 'days')} to go out, against "
                          f"{fmt(delay['baseline'], 'days')} in your best weeks.", delay, n))
    if away and away["value"]:
        cards.append(card(f"{fmt(turned, 'count')} orders were turned away in the last 4 weeks.", away, n))
    if stock and stock["value"]:
        cards.append(card(f"{fmt(stock['value'], 'count')} stock-outs in the last 4 weeks.", stock, n))
    if stock and stock["value"] and step == "dispatch":
        step = "making (stock-outs) and dispatch"
    return {"gap": g, "material": turned >= 2 or slower >= 0.5,
            "impact": f"{turned} orders turned away, orders {round(slower, 1)} days slower", "localised": True,
            "where": f"the limit is at {step}", "cards": cards,
            "key_fact": delay["fact_id"] if "dispatch" in step or not away else away["fact_id"]}


SCORERS = {"reach": score_reach, "conversion": score_conversion, "margin": score_margin,
           "repeat_orders": score_repeat, "capacity": score_capacity}


# ---------------------------------------------------------------- the diagnosis


def _reason(tests: dict, scored: dict) -> str:
    words = {"materiality": "too small to matter yet", "deviation": "within 20% of your best weeks",
             "localisation": "cannot say where the problem is", "actionability": scored.get("no_action_reason")
             or "no eligible action this week"}
    return "; ".join(words[k] for k, ok in tests.items() if not ok)


def diagnose(facts_doc: dict, actionable: Callable[[str], tuple[bool, Optional[int], Optional[str]]]) -> dict:
    """`actionable(bottleneck) -> (has_eligible_action, min_effort_minutes, reason_if_not)`."""
    F = Facts(facts_doc["facts"])
    orders_fact = F["f_stranger_share"] or F["f_orders_per_week"]
    n = (orders_fact or {}).get("sample_size") or 0
    findings = []
    for b in BOTTLENECKS:
        s = SCORERS[b](F, n)
        if s is None:
            findings.append({"bottleneck": b, "label": LABELS[b], "gap_to_best": None, "passed": False,
                             "tests": None, "reason": "the facts for this bottleneck are missing",
                             "cards": [], "evidence_ids": [], "confidence": None})
            continue
        ok, effort, why_not = actionable(b)
        s["no_action_reason"] = why_not
        tests = {"materiality": n >= MIN_ORDERS and s["material"], "deviation": s["gap"] >= DEVIATION,
                 "localisation": s["localised"], "actionability": ok}
        evidence = []
        for c in s["cards"]:
            evidence += [e for e in c["evidence_ids"] if e not in evidence]
        findings.append({
            "bottleneck": b, "label": LABELS[b], "gap_to_best": s["gap"], "tests": tests,
            "passed": all(tests.values()), "where": s["where"], "impact": s["impact"], "key_fact": s["key_fact"],
            "min_action_effort": effort, "cards": s["cards"], "evidence_ids": evidence,
            "confidence": s["cards"][0]["confidence"] if s["cards"] else None,
            "reason": None if all(tests.values()) else _reason(tests, s),
        })
    ranked = sorted((f for f in findings if f["gap_to_best"] is not None), key=lambda f: -f["gap_to_best"])
    passing = sorted((f for f in findings if f["passed"]),
                     key=lambda f: (-f["gap_to_best"], f["min_action_effort"] or 10 ** 6))
    status, message = "ok", None
    if n < MIN_ORDERS:
        status = "not_enough_data"
        message = (f"Only {n} orders in the last 4 weeks. At least {MIN_ORDERS} are needed before naming a bottleneck; "
                   f"the numbers below are estimates.")
        for f in findings:
            f["confidence"] = "estimate" if f["cards"] else None
            for c in f["cards"]:
                c["confidence"] = "estimate"
        primary = None
    elif not passing:
        status = "no_clear_bottleneck"
        message = "Nothing is clearly holding the business back compared with its own best weeks."
        primary = None
    else:
        primary = passing[0]["bottleneck"]
    runners_up = [f["bottleneck"] for f in ranked if f["bottleneck"] != primary][:2]
    rejected = [{"bottleneck": f["bottleneck"], "reason": f["reason"]}
                for f in findings if not f["passed"] and f["bottleneck"] != primary]
    week_fact = F["f_stranger_orders_week"]
    return {
        "business_id": facts_doc["business_id"], "week": facts_doc["week"], "as_of": facts_doc.get("as_of"),
        "synthetic": facts_doc.get("synthetic", False), "status": status, "message": message,
        "orders_in_window": n, "primary": primary, "runners_up": runners_up, "rejected": rejected,
        "main_measure": ({"fact_id": week_fact["fact_id"], "stranger_orders_this_week": week_fact["value"],
                          "best_weeks": week_fact["baseline"]} if week_fact else None),
        "bottlenecks": findings,
        "rule": "largest gap to your own best weeks among bottlenecks passing all four tests",
    }
