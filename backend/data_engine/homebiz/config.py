"""Scenarios and calibration for the generated demo businesses (Box Box and a home baker).

Everything generated from here is SYNTHETIC and labelled `synthetic: True`. Two kinds of numbers live here, kept apart on purpose:

CALIBRATION: numbers read from the committed profiles of PUBLIC datasets (see docs/DATASET.md), so the generated data behaves
like real data in these respects. `CALIBRATION` records, for each one, the dataset it came from.

SCENARIO ASSUMPTIONS: numbers chosen by us to tell the story of each case (how many orders come from strangers, unit costs,
Instagram reach, the capacity limit, how demand reacts to events). No public data has them, so they are listed in
`ASSUMPTIONS` and shown in the data card, never presented as measured facts.
"""
from __future__ import annotations

import json
import math
from datetime import date, timedelta
from pathlib import Path

SNAP = Path(__file__).resolve().parents[1] / "external" / "snapshots"
Z90 = 1.2816     # standard-normal quantile for the 90th percentile


def _profile(name: str) -> dict:
    p = SNAP / f"{name}_profile.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _calibration() -> dict:
    olist, retail, shoppers = _profile("olist"), _profile("retail_ii"), _profile("shoppers")
    repeat_floor = olist.get("repeat_buying", {}).get("customers_of_small_sellers", {}).get("repeat_customer_share", 0.0211)
    late = olist.get("delivery", {}).get("small_sellers", {}).get("late_share", 0.0801)
    om = retail.get("order_metrics", {})
    gap_med, gap_p90 = om.get("days_between_orders_median") or 25.0, om.get("days_between_orders_p90") or 136.0
    nv = shoppers.get("by_visitor_type", {})
    new_c = nv.get("New_Visitor", {}).get("conversion", 0.2491)
    ret_c = nv.get("Returning_Visitor", {}).get("conversion", 0.1393)
    return {
        "repeat_share_floor": {"value": repeat_floor, "from": "Olist: repeat customers of sellers with 50-500 orders"},
        "late_delivery_share": {"value": late, "from": "Olist: late-delivery share of small sellers"},
        "repeat_gap_days_median": {"value": gap_med, "from": "UCI Online Retail II: median days between a customer's orders"},
        "repeat_gap_days_p90": {"value": gap_p90, "from": "UCI Online Retail II: 90th percentile"},
        "repeat_gap_lognormal_sigma": {"value": round(math.log(gap_p90 / gap_med) / Z90, 4), "from": "derived from the median and p90 above"},
        "new_vs_returning_conversion_ratio": {"value": round(new_c / ret_c, 3), "from": "UCI Online Shoppers: new vs returning visitors"},
        "intent_vs_interest_lift": {"value": shoppers.get("reading", {}).get("page_value_lift", 14.6), "from": "UCI Online Shoppers: sessions with page value vs without"},
        "context_interest_uplift": {"value": 2.027, "from": "Wikipedia page views: F1 race weekends vs other days (interest, not sales)"},
    }


CALIBRATION = _calibration()
GAP_MU = math.log(CALIBRATION["repeat_gap_days_median"]["value"])
GAP_SIGMA = CALIBRATION["repeat_gap_lognormal_sigma"]["value"]
# dispatch delay: lognormal with median 2 days whose share above 5 days equals the late-delivery share measured on Olist
LATE_Z = {0.08: 1.405}.get(round(CALIBRATION["late_delivery_share"]["value"], 2), 1.405)
DISPATCH_SIGMA = round(math.log(5 / 2.0) / LATE_Z, 4)

# Advisory timeline: the owner gets the diagnosis on Monday of week 1. Ten weeks of history come before it.
ADVISORY_START = date(2026, 10, 5)
HISTORY_WEEKS = 10
ADVISORY_WEEKS = 4
HISTORY_START = ADVISORY_START - timedelta(weeks=HISTORY_WEEKS)      # 2026-07-27
END = ADVISORY_START + timedelta(weeks=ADVISORY_WEEKS)               # 2026-11-02 (exclusive)

# Explicit scenario assumptions shared by both businesses
SHARED_ASSUMPTIONS = {
    "payment_upi_share": "85% UPI, 15% cash on delivery",
    "basket": "1 item 80%, 2 items 15%, 3 items 5%",
    "discount": "5% of orders carry a 10% discount",
    "weekday_pattern": "weekends 15% busier than weekdays",
    "lead_outcome_by_group": "Hot 45% order, Warm 15%, Cold 3% (direction supported by public data; the values are assumptions)",
    "min_sample_orders": "30 orders in a 4-week window; below that a fact is an estimate",
}

SCENARIOS = {
    "boxbox": {
        "business_id": "biz_boxbox", "name": "Box Box", "case_study": "Box Box", "kind": "F1 merchandise",
        "story": "Reach: most orders come from friends and friends of friends; very few from strangers.",
        "products": [   # protected terms are on purpose: they exercise the brand-and-IP risk rule
            {"name": "Ferrari F1 Tee", "category": "t-shirt", "price": 799, "material": 260, "making": 110, "packaging": 25, "courier": 70},
            {"name": "Verstappen Fan Tee", "category": "t-shirt", "price": 799, "material": 260, "making": 110, "packaging": 25, "courier": 70},
            {"name": "McLaren Papaya Hoodie", "category": "hoodie", "price": 1499, "material": 520, "making": 150, "packaging": 30, "courier": 90},
            {"name": "Box Box Racing Cap", "category": "cap", "price": 499, "material": 150, "making": 60, "packaging": 20, "courier": 60},
        ],
        "product_weights": [0.34, 0.30, 0.18, 0.18],
        "channels": ["instagram", "whatsapp"], "team_size": 1, "weekly_hours": 14, "capacity_orders_per_week": 30,
        "serves": {"cities": ["Pune", "Mumbai", "Bangalore", "Delhi", "Hyderabad", "Chennai"], "sizes": ["S", "M", "L", "XL"]},
        "context_feed": "f1_calendar",
        "base_orders_per_week": 15.0, "context_order_factor": 1.4,
        # share of NEW customers by relationship: history, then advisory weeks 1..4 (the scripted replay after the advice)
        "shares": {"history": (0.55, 0.33, 0.12), "week_1": (0.54, 0.33, 0.13), "week_2": (0.48, 0.34, 0.18),
                   "week_3": (0.42, 0.33, 0.25), "week_4": (0.36, 0.32, 0.32)},
        "week_order_multiplier": {"history": 1.0, "week_1": 1.0, "week_2": 1.05, "week_3": 1.12, "week_4": 1.22},
        "repeat_customer_target": 0.09, "posts_per_week": 3, "reach_median": 320, "reach_sigma": 0.85,
        "reach_multiplier": {"history": 1.0, "week_1": 1.0, "week_2": 1.25, "week_3": 1.6, "week_4": 2.0},
        "profile_visit_rate": 0.06, "follow_rate": 0.12, "post_to_order_share": 0.35,
        "leads_per_week": 11, "lead_stranger_share_boost": 0.0,
        "interview": {"goal": "More orders from people outside my circle next month", "tried": "Posting designs on Instagram stories",
                      "constraints": ["no paid ads", "one person", "14 hours a week"]},
    },
    "homebaker": {
        "business_id": "biz_homebaker", "name": "Meera's Kitchen", "case_study": "Home baker", "kind": "home-baked goods",
        "story": "Capacity: demand is steady and rises before festivals, but she can only bake so much; orders get turned away and dispatch slips.",
        "products": [
            {"name": "Eggless Brownie Box (6)", "category": "brownies", "price": 450, "material": 150, "making": 70, "packaging": 30, "courier": 50},
            {"name": "Choco Chip Cookies (12)", "category": "cookies", "price": 380, "material": 110, "making": 60, "packaging": 25, "courier": 50},
            {"name": "Custom Birthday Cake (1 kg)", "category": "cakes", "price": 1400, "material": 480, "making": 260, "packaging": 60, "courier": 120},
            {"name": "Festive Gift Hamper", "category": "hampers", "price": 1800, "material": 650, "making": 220, "packaging": 90, "courier": 120},
        ],
        "product_weights": [0.34, 0.30, 0.20, 0.16],
        "channels": ["instagram", "whatsapp"], "team_size": 1, "weekly_hours": 20, "capacity_orders_per_week": 14,
        "serves": {"cities": ["Pune"], "sizes": []},
        "context_feed": "india_festivals",
        "base_orders_per_week": 14.5, "context_order_factor": 1.3,
        "shares": {"history": (0.58, 0.24, 0.18), "week_1": (0.57, 0.25, 0.18), "week_2": (0.56, 0.25, 0.19),
                   "week_3": (0.55, 0.25, 0.20), "week_4": (0.54, 0.25, 0.21)},
        "week_order_multiplier": {"history": 1.0, "week_1": 1.05, "week_2": 1.10, "week_3": 1.15, "week_4": 1.2},
        "repeat_customer_target": 0.14, "posts_per_week": 4, "reach_median": 520, "reach_sigma": 0.8,
        "reach_multiplier": {"history": 1.0, "week_1": 1.0, "week_2": 1.0, "week_3": 1.05, "week_4": 1.1},
        "profile_visit_rate": 0.07, "follow_rate": 0.13, "post_to_order_share": 0.30,
        "leads_per_week": 10, "lead_stranger_share_boost": 0.0,
        "interview": {"goal": "Handle Diwali demand without disappointing customers", "tried": "Taking orders by WhatsApp only",
                      "constraints": ["no paid ads", "one person", "20 hours a week", "single oven"]},
    },
}

ASSUMPTIONS = {
    key: {
        "relationship_shares_of_new_customers": {k: dict(zip(("friend", "friend_of_friend", "stranger"), v)) for k, v in s["shares"].items()},
        "base_orders_per_week": s["base_orders_per_week"], "capacity_orders_per_week": s["capacity_orders_per_week"],
        "unit_costs": {p["name"]: p["material"] + p["making"] + p["packaging"] + p["courier"] for p in s["products"]},
        "prices": {p["name"]: p["price"] for p in s["products"]},
        "context_order_factor": s["context_order_factor"], "context_feed": s["context_feed"],
        "repeat_customer_target": s["repeat_customer_target"], "reach_median_per_post": s["reach_median"],
        "profile_visit_rate": s["profile_visit_rate"], "follow_rate": s["follow_rate"],
        "weekly_order_multiplier_after_advice": s["week_order_multiplier"],
    } for key, s in SCENARIOS.items()
}


def data_card(key: str) -> dict:
    s = SCENARIOS[key]
    return {
        "business_id": s["business_id"], "name": s["name"], "synthetic": True, "story": s["story"],
        "what_is_calibrated_on_public_data": CALIBRATION,
        "what_is_a_scenario_assumption": {**SHARED_ASSUMPTIONS, **ASSUMPTIONS[key]},
        "note": "Generated, deterministic, always labelled synthetic. Weeks 2 to 4 of the demo are a scripted replay of what could happen after the advice.",
        "public_datasets": ["Olist", "UCI Online Retail II", "UCI Online Shoppers", "UCI Bank Marketing", "F1 calendar and page views / India festival calendar"],
    }
