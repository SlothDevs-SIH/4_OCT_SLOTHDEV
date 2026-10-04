"""Advice: one to three actions for this week, from an approved library, filtered by the owner's constraints.

Eligibility gate (an action is blocked, with the reason shown, when):
  - it needs paid ads or money beyond the ad budget (the user has no ad budget)
  - it needs more minutes than the owner has for growth this week
  - it needs data that is missing (no partner list, no demand window, no past buyers, no unit costs)
Brand and IP risk is a flag, not a block: protected names in product names raise a warning, more
strongly when the action makes those products more visible.

Ranking (shown to the owner):
  score = 100 x (0.5 x impact + 0.3 x fit + 0.2 x timing) x (1 - 0.5 x effort / weekly growth minutes)
ties go to the action with less effort. Actions are picked best-first while their total effort fits the week.
"""
from __future__ import annotations

import copy
import json
import re
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Optional

import jsonschema

LIBRARY_DIR = Path(__file__).resolve().parent / "library"
MAX_ACTIONS = 3
WINDOW_DAYS = 21  # a demand window must start within 3 weeks to plan for it

ACTION_SCHEMA = {
    "type": "object",
    "required": ["action_key", "bottleneck", "title", "what", "kind", "effort_min", "impact", "cost_inr",
                 "timing_sensitive", "raises_visibility", "requires", "requires_approval", "target", "base_fit"],
    "properties": {
        "bottleneck": {"enum": ["reach", "conversion", "margin", "repeat_orders", "capacity"]},
        "effort_min": {"type": "integer", "minimum": 1},
        "impact": {"type": "number", "minimum": 0, "maximum": 1},
        "base_fit": {"type": "number", "minimum": 0, "maximum": 1},
        "requires": {"type": "array", "items": {"enum": ["reach_candidates", "demand_window", "past_buyers", "unit_cost"]}},
        "target": {"type": "object", "required": ["fact_id", "rule"],
                   "properties": {"rule": {"enum": ["add", "relative", "to_best", "to_zero"]}}},
    },
}


@lru_cache(maxsize=1)
def _library() -> tuple:
    data = json.loads((LIBRARY_DIR / "actions.json").read_text(encoding="utf-8"))
    keys = set()
    for a in data["actions"]:
        jsonschema.validate(a, ACTION_SCHEMA)
        if a["action_key"] in keys:
            raise ValueError(f"duplicate action_key {a['action_key']}")
        keys.add(a["action_key"])
    return data["version"], data["ranking"], tuple(data["actions"])


def library() -> dict:
    version, ranking, actions = _library()
    return {"version": version, "ranking": ranking, "actions": copy.deepcopy(list(actions))}


def for_bottleneck(b: str) -> list[dict]:
    return [a for a in library()["actions"] if a["bottleneck"] == b]


@lru_cache(maxsize=1)
def _terms() -> dict:
    return json.loads((LIBRARY_DIR / "protected_terms.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- brand / IP risk


def protected_terms_in(names: list[str]) -> list[str]:
    found = []
    for term in (t for group in _terms()["terms"].values() for t in group):
        if any(re.search(rf"(?<![\w]){re.escape(term)}(?![\w])", n, re.I) for n in names) and term not in found:
            found.append(term)
    return found


def brand_risk(business: dict, raises_visibility: bool = False) -> Optional[dict]:
    names = [p["name"] for p in business.get("products", [])]
    terms = protected_terms_in(names)
    if not terms:
        return None
    t = _terms()
    text = t["warning"].format(terms=", ".join(terms))
    if raises_visibility:
        text += " " + t["visibility_warning"]
    products = [n for n in names if protected_terms_in([n])]
    return {"flag": "brand_ip", "level": "high" if raises_visibility else "medium", "terms": terms,
            "products": products, "text": text, "not_legal_advice": True}


# ---------------------------------------------------------------- reach partners


def _engagement(c: dict) -> float:
    rate = (c.get("avg_comments_per_post", 0) + c.get("avg_shares_per_post", 0)) / max(1, c.get("followers", 1))
    return round(min(1.0, rate / 0.02), 3)  # 2% comments+shares per follower per post counts as strong


def rank_partners(business: dict, results: Optional[dict] = None) -> dict:
    """Rank the owner's candidate partners: audience match, location, engagement (not followers), past
    results and cost. results = {partner_id: [stranger leads per collab, ...]} from earlier follow-ups."""
    results = results or {}
    topics, city = set(business.get("topics", [])), business.get("city")
    budget = business.get("ad_budget_inr", 0) or 0
    ranked, blocked = [], []
    for c in business.get("reach_candidates", []):
        audience = 1.0 if topics & set(c.get("topics", [])) else 0.4
        location = 1.0 if c.get("city") == city else (0.5 if c.get("city") is None else 0.6)
        engagement = _engagement(c)
        history = results.get(c["partner_id"], [])
        past = round(min(1.0, sum(history) / len(history) / 5), 3) if history else 0.5
        parts = {"audience_match": audience, "location_match": location, "engagement": engagement,
                 "past_results": past}
        score = round(100 * (0.35 * audience + 0.20 * location + 0.25 * engagement + 0.20 * past), 1)
        row = dict(c, score=score, score_parts=parts, past_stranger_leads=history or None,
                   engagement_rate=round((c.get("avg_comments_per_post", 0) + c.get("avg_shares_per_post", 0))
                                         / max(1, c.get("followers", 1)), 4))
        if c.get("cost_inr", 0) > budget:
            row["blocked_reason"] = (f"Asks for INR {c['cost_inr']:,} (a paid shoutout); your ad budget is "
                                     f"INR {budget:,}.")
            blocked.append(row)
        else:
            ranked.append(row)
    ranked.sort(key=lambda r: -r["score"])
    for i, r in enumerate(ranked, 1):
        r["rank"] = i
    return {"business_id": business["business_id"], "synthetic": business.get("synthetic", False),
            "formula": "score = 100 x (0.35 audience match + 0.20 location match + 0.25 engagement + 0.20 past results); "
                       "engagement = comments and shares per follower per post, 2% or more counts as full",
            "recommended": [r["partner_id"] for r in ranked[:3]], "partners": ranked, "blocked": blocked}


# ---------------------------------------------------------------- demand windows


def demand_windows(context: Optional[dict], as_of: str, days: int = WINDOW_DAYS) -> list[dict]:
    """Race weekends or festival windows starting after `as_of` and within `days`."""
    if not context:
        return []
    start = date.fromisoformat(as_of)
    end = start + timedelta(days=days)
    out = []
    for r in context.get("race_weekends", []):
        s = date.fromisoformat(r["weekend_start"])
        if start < s <= end:
            out.append({"name": r["name"], "from": r["weekend_start"], "to": r["weekend_end"], "kind": "race_weekend"})
    for e in context.get("events", []):
        s = date.fromisoformat(e.get("window_start") or e["date"])
        if start < s <= end:
            out.append({"name": e["name"], "from": e.get("window_start") or e["date"],
                        "to": e.get("window_end") or e["date"], "kind": e.get("kind", "event")})
    uplift = (context.get("interest_uplift") or {}).get("overall", {}).get("uplift") if context.get("interest_uplift") else None
    unique = {}
    for w in out:  # data_engine lists race weekends both as race_weekends and as events
        unique.setdefault((w["name"], w["from"]), dict(w, interest_uplift=uplift))
    return sorted(unique.values(), key=lambda w: w["from"])


# ---------------------------------------------------------------- gate


def gate(action: dict, business: dict, data: dict) -> dict:
    checks = []

    def check(name, ok, detail):
        checks.append({"check": name, "passed": bool(ok), "detail": detail})

    budget = business.get("ad_budget_inr", 0) or 0
    forbidden = set(business.get("constraints", {}).get("forbidden_actions", []))
    paid = action["kind"] == "paid_ads" or action["kind"] in forbidden
    check("no_paid_ads", not paid and action["cost_inr"] <= budget,
          f"Needs INR {action['cost_inr']:,} for ads; your ad budget is INR {budget:,}, so paid ads are not an option."
          if (paid or action["cost_inr"] > budget) else "No money needed.")
    minutes = business.get("growth_minutes_per_week") or (business.get("weekly_hours", 0) * 60) // 4
    check("hours", action["effort_min"] <= minutes,
          f"Needs {action['effort_min']} minutes; you have {minutes} minutes a week for growth."
          if action["effort_min"] > minutes else f"Fits your {minutes} minutes a week.")
    missing = []
    for need in action["requires"]:
        if need == "reach_candidates" and not data["partners"]["partners"]:
            missing.append("no reach partners are listed (add a few fan pages, creators or communities)")
        if need == "demand_window" and not data["windows"]:
            missing.append("no demand window in the next 3 weeks" if data["context"] else
                           "no event calendar for this business yet")
        if need == "past_buyers" and (data["customers"] or 0) < 5:
            missing.append("fewer than 5 past buyers")
        if need == "unit_cost" and any(p.get("unit_cost") is None for p in business.get("products", [])):
            missing.append("unit costs are missing for some products")
    check("data", not missing, "; ".join(missing).capitalize() + "." if missing else "Data available.")
    failed = [c for c in checks if not c["passed"]]
    return {"eligible": not failed, "blocked_reason": failed[0]["detail"] if failed else None, "checks": checks}


# ---------------------------------------------------------------- instantiate, score, select


def _fill(action: dict, business: dict, data: dict) -> tuple[dict, float, Optional[str]]:
    """Fill the placeholders; returns (values, fit, partner_id)."""
    values, fit, partner = {}, action["base_fit"], None
    partners = data["partners"]["partners"]
    if action["action_key"] == "reach_partner_collab" and partners:
        top = partners[0]
        values["partner_name"], fit, partner = top["name"], top["score"] / 100, top["partner_id"]
    if action["action_key"] == "reach_community_share":
        # a different community from the top partner, so two actions never ask the same people
        top_id = partners[0]["partner_id"] if partners else None
        comm = next((p for p in partners if p["type"] == "community" and p["partner_id"] != top_id), None)
        values["community_name"] = comm["name"] if comm else "a college or local community you belong to"
        if comm:
            fit, partner = max(fit, comm["score"] / 100), comm["partner_id"]
    if action["action_key"] == "reach_demand_window_drop" and data["windows"]:
        w = data["windows"][0]
        values["event_name"], values["event_dates"] = w["name"], f"{w['from']} to {w['to']}"
        fit = 1.0 if (date.fromisoformat(w["from"]) - date.fromisoformat(data["as_of"])).days <= 7 else 0.7
    products = sorted(business.get("products", []),
                      key=lambda p: ((p["price"] - (p.get("unit_cost") or 0)) / p["price"]) if p.get("price") else 1)
    asked = data.get("asked_products") or []
    if products:
        # re-pricing: the lowest-margin product; a pre-order drop: the product people ask for most
        values["product_name"] = asked[0] if (asked and action["bottleneck"] == "capacity") else products[0]["name"]
        values["product_a"] = products[0]["name"]
        values["product_b"] = products[1]["name"] if len(products) > 1 else products[0]["name"]
    return values, round(fit, 3), partner


def _timing(action: dict, data: dict) -> float:
    if not action["timing_sensitive"]:
        return 0.5
    if not data["windows"]:
        return 0.0
    days = (date.fromisoformat(data["windows"][0]["from"]) - date.fromisoformat(data["as_of"])).days
    return 1.0 if days <= 7 else 0.5


def score(action: dict, fit: float, timing: float, minutes: int) -> dict:
    share = min(1.0, action["effort_min"] / max(1, minutes))
    value = 100 * (0.5 * action["impact"] + 0.3 * fit + 0.2 * timing) * (1 - 0.5 * share)
    return {"score": round(value, 1), "parts": {"impact": action["impact"], "fit": fit, "timing": timing,
                                                "effort_share": round(share, 3)}}


TARGET_LABELS = {"stranger_orders_per_week": "orders from strangers a week (4-week average)",
                 "stranger_orders_week": "orders from strangers a week", "lead_to_order_rate": "of interested people ordering",
                 "margin_pct": "margin after full costs", "repeat_customer_share": "of customers ordering again",
                 "dispatch_delay_days": "days to dispatch", "orders_turned_away": "orders turned away"}


def target_for(action: dict, facts: dict) -> dict:
    t = action["target"]
    f = facts.get(t["fact_id"])
    if not f or f["value"] is None:
        return {"fact_id": t["fact_id"], "value": None, "text": "no current value to measure against"}
    v, unit = f["value"], f["unit"]
    label = TARGET_LABELS.get(f["kpi"], f["kpi"].replace("_", " "))
    if t["rule"] == "add":
        goal = v + t["amount"]
        text = f"at least {goal:g} {label} (now {v:g} a week)"
    elif t["rule"] == "relative":
        goal = round(v * (1 + t["amount"]), 3)
        shown = (lambda x: f"{round(x * 100, 1):g}%") if unit == "ratio" else (lambda x: f"{x:g}")
        text = f"{shown(goal)} {label} or better within 4 weeks (now {shown(v)})"
    elif t["rule"] == "to_best":
        goal = round(f["baseline"], 2)
        text = f"{goal:g} {label} or fewer, as in your best weeks (now {v:g})" if f.get("better") == "lower" \
            else f"back to {goal:g} {label}, as in your best weeks (now {v:g})"
    else:
        goal = 0
        text = f"no orders turned away (now {v:g} in the last 4 weeks)"
    return {"fact_id": f["fact_id"], "kpi": f["kpi"], "current": v, "value": goal, "unit": unit, "text": text}


def candidates(bottleneck: str, business: dict, data: dict) -> list[dict]:
    """Every library action for the bottleneck, filled, gated and scored."""
    minutes = business.get("growth_minutes_per_week") or (business.get("weekly_hours", 0) * 60) // 4
    out = []
    for a in for_bottleneck(bottleneck):
        values, fit, partner = _fill(a, business, data)
        try:
            title = a["title"].format(**values)
        except KeyError:  # a placeholder could not be filled; the gate says why
            title = re.sub(r"\s*\(?\{[^}]+\}\)?", "", a["title"]).strip()
            title = {"Plan a drop or post for": "Plan a drop or post for an upcoming event"}.get(title, title)
        g = gate(a, business, data)
        s = score(a, fit, _timing(a, data), minutes)
        out.append(dict(a, title=title, gate=g, partner_id=partner,
                        product_name=values.get("product_name") if "{product_name}" in a["title"] else None, **s))
    out.sort(key=lambda c: (not c["gate"]["eligible"], -c["score"], c["effort_min"]))
    return out


def actionable(bottleneck: str, business: dict, data: dict) -> tuple[bool, Optional[int], Optional[str]]:
    cands = candidates(bottleneck, business, data)
    eligible = [c for c in cands if c["gate"]["eligible"]]
    if eligible:
        return True, min(c["effort_min"] for c in eligible), None
    reasons = sorted({c["gate"]["blocked_reason"] for c in cands})
    return False, None, "every action for it is blocked: " + " ".join(reasons) if reasons else "no actions in the library"


def select(cands: list[dict], minutes: int) -> list[dict]:
    chosen, used = [], 0
    for c in cands:
        if c["gate"]["eligible"] and used + c["effort_min"] <= minutes and len(chosen) < MAX_ACTIONS:
            chosen.append(c)
            used += c["effort_min"]
    return chosen
