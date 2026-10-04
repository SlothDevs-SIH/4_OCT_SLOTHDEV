"""Stand-in v2 input fixtures for Box Box and the home baker (contract v2 shapes).

Backend 1 owns the real generator (docs/DATASET.md section 4). Until it lands, decision_engine
is built against these stand-ins. Everything here is synthetic and labelled so.

    python -m backend.decision_engine.devtools.standin_fixtures   # writes contracts/fixtures/v2/

Weekly scenario numbers are explicit below (they are scenario assumptions, not measurements).
Facts are computed from them with the definitions in `FACT_DEFS`; lead scores use the points
in backend/BACKEND_1_DATA_ENGINE.md section 5. Same input, same output.
"""
from __future__ import annotations

import json
import statistics
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parents[3] / "contracts" / "fixtures" / "v2"
FIRST_MONDAY = date(2026, 6, 29)          # history week h1 = 2026-06-29..2026-07-05
SNAPSHOT_WEEK = {"week_1": 14, "week_2": 15, "week_3": 16, "week_4": 17}
WINDOW = 4                                # facts use the last 4 weeks (tiny volumes)
BEST_N = 3                                # baseline = mean of the 3 best weeks/windows so far
MIN_ORDERS = 20                           # under this the data is too thin for a verdict
POINTS = {"asked_price_size_stock_delivery": 40, "bought_before": 30, "replied_to_story": 20,
          "saved_or_shared": 15, "commented": 10, "stranger": 10, "followed_or_liked_once": 5,
          "inactive_30_days": -20}


def week_range(h: int) -> tuple[str, str]:
    start = FIRST_MONDAY + timedelta(weeks=h - 1)
    return start.isoformat(), (start + timedelta(days=6)).isoformat()


# ---------------------------------------------------------------- scenarios (assumptions)

BOXBOX = {
    "slug": "boxbox",
    "business": {
        "business_id": "biz_boxbox", "name": "Box Box", "case_study": "Box Box", "synthetic": True,
        "category": "F1 merchandise", "city": "Pune", "ships_to": "India",
        "topics": ["f1", "motorsport"],
        "products": [
            {"name": "Monza Tee", "category": "t-shirt", "price": 799, "unit_cost": 430, "sizes": ["S", "M", "L", "XL"]},
            {"name": "Pit Wall Cap", "category": "cap", "price": 599, "unit_cost": 310},
            {"name": "Lights Out Poster", "category": "poster", "price": 299, "unit_cost": 120},
            {"name": "Ferrari Red Tribute Tee", "category": "t-shirt", "price": 849, "unit_cost": 445, "sizes": ["S", "M", "L", "XL"]},
            {"name": "Hamilton 44 Keychain", "category": "accessory", "price": 199, "unit_cost": 70},
        ],
        "channels": ["instagram", "whatsapp"], "payment": "UPI", "order_link": "link in bio",
        "team_size": 1, "weekly_hours": 12, "growth_minutes_per_week": 180, "ad_budget_inr": 0,
        "capacity_orders_per_week": 25,
        "goal": {"statement": "Get more orders from people outside my circle", "horizon_days": 30},
        "constraints": {"forbidden_actions": ["paid_ads"],
                        "approval_required_for": ["customer_outreach", "public_post", "price_change", "partner_collab"]},
        "context_feeds": ["f1_calendar"],
        "reach_candidates": [
            {"partner_id": "rp_bb_1", "name": "Pune F1 Fans (fan page)", "type": "fan_page", "topics": ["f1"],
             "city": "Pune", "followers": 8200, "avg_comments_per_post": 46, "avg_shares_per_post": 30, "cost_inr": 0},
            {"partner_id": "rp_bb_2", "name": "Grid Sketches (F1 illustrator)", "type": "creator", "topics": ["f1", "art"],
             "city": "Mumbai", "followers": 12000, "avg_comments_per_post": 80, "avg_shares_per_post": 40, "cost_inr": 0},
            {"partner_id": "rp_bb_3", "name": "Campus Motorsport Club (college community)", "type": "community",
             "topics": ["motorsport"], "city": "Pune", "followers": 1900, "avg_comments_per_post": 22,
             "avg_shares_per_post": 18, "cost_inr": 0},
            {"partner_id": "rp_bb_4", "name": "Lights Out India (national fan page)", "type": "fan_page", "topics": ["f1"],
             "city": None, "followers": 41000, "avg_comments_per_post": 35, "avg_shares_per_post": 12, "cost_inr": 1500},
            {"partner_id": "rp_bb_5", "name": "Pune Streetwear Collective (community)", "type": "community",
             "topics": ["streetwear"], "city": "Pune", "followers": 5000, "avg_comments_per_post": 10,
             "avg_shares_per_post": 5, "cost_inr": 0},
        ],
        "provenance": {"weekly_hours": "estimate", "growth_minutes_per_week": "estimate",
                       "capacity_orders_per_week": "estimate", "unit_cost": "exact", "ad_budget_inr": "exact"},
    },
    "unit_cost_source": "exact", "insights_source": "exact",
    "weeks": {  # h1..h17; h14 = week_1 (as of 2026-10-04); h15-h17 = scripted replay weeks 2-4
        "stranger":  [1, 2, 7, 5, 4, 3, 2, 2, 2, 2, 1, 2, 2, 1, 3, 4, 6],
        "friend":    [7, 7, 8, 7, 6, 6, 8, 8, 7, 8, 8, 8, 8, 9, 8, 8, 9],
        "fof":       [3, 4, 6, 6, 5, 5, 6, 7, 6, 6, 6, 7, 6, 6, 6, 6, 7],
        "unknown":   [1] * 17,
        "posts":     [3, 3, 4, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 5],
        "reach":     [1800, 1900, 7600, 3200, 2400, 2100, 2000, 2000, 1900, 1950, 1850, 1900, 1900, 1850, 3300, 3600, 4800],
        "visit_rate": 0.065, "follow_rate": 0.20,
        "posts_with_orders": [1, 1, 3, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 3],
        "leads":     [15, 17, 30, 25, 20, 19, 21, 22, 20, 21, 20, 22, 21, 21, 24, 26, 32],
        "aov": 720, "cost_per_order": 405, "discount_share": 0.12,
        "repeat_order_share": 0.16,
        "days_between": [None, None, None, None, 31, 32, 33, 33, 34, 34, 34, 35, 34, 34, 34, 34, 33],
        "dispatch_delay": [2.0, 2.1, 3.4, 2.6, 2.2, 2.0, 2.1, 2.0, 1.9, 2.0, 2.1, 2.0, 2.1, 2.2, 2.2, 2.3, 2.6],
        "stockouts":  [0, 0, 2, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        "turned_away": [0, 0, 3, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    },
}

BAKER = {
    "slug": "homebaker",
    "business": {
        "business_id": "biz_homebaker", "name": "Butter Lane Bakes", "case_study": "Home baker (sample)",
        "synthetic": True, "category": "home bakery", "city": "Pune",
        "ships_to": "Pune, within 8 km of Kothrud", "topics": ["baking", "desserts", "gifting"],
        "products": [
            {"name": "Brownie Box", "category": "dessert", "price": 450, "unit_cost": 210},
            {"name": "Celebration Cake", "category": "cake", "price": 1200, "unit_cost": 620},
            {"name": "Cookie Jar", "category": "cookies", "price": 350, "unit_cost": 150},
            {"name": "Diwali Hamper", "category": "gifting", "price": 899, "unit_cost": 520},
            {"name": "Nutella Brownie Tub", "category": "dessert", "price": 520, "unit_cost": 260},
        ],
        "channels": ["whatsapp", "instagram"], "payment": "UPI", "order_link": "WhatsApp order form",
        "team_size": 2, "weekly_hours": 30, "growth_minutes_per_week": 120, "ad_budget_inr": 0,
        "capacity_orders_per_week": 20,
        "goal": {"statement": "Reach new customers beyond my society and get ready for Diwali", "horizon_days": 30},
        "constraints": {"forbidden_actions": ["paid_ads"],
                        "approval_required_for": ["customer_outreach", "public_post", "price_change", "partner_collab"]},
        "context_feeds": ["india_festivals"],
        "reach_candidates": [
            {"partner_id": "rp_hb_1", "name": "Neighbourhood parents group (WhatsApp community)", "type": "community",
             "topics": ["parenting", "gifting"], "city": "Pune", "followers": 900, "avg_comments_per_post": 25,
             "avg_shares_per_post": 12, "cost_inr": 0},
            {"partner_id": "rp_hb_2", "name": "Pune dessert reviewer (creator)", "type": "creator",
             "topics": ["desserts", "baking"], "city": "Pune", "followers": 15000, "avg_comments_per_post": 60,
             "avg_shares_per_post": 25, "cost_inr": 0},
            {"partner_id": "rp_hb_3", "name": "Office foodies group (community)", "type": "community",
             "topics": ["food"], "city": "Pune", "followers": 3000, "avg_comments_per_post": 15,
             "avg_shares_per_post": 6, "cost_inr": 0},
            {"partner_id": "rp_hb_4", "name": "Food influencer with paid shoutouts", "type": "creator",
             "topics": ["desserts"], "city": "Mumbai", "followers": 90000, "avg_comments_per_post": 120,
             "avg_shares_per_post": 40, "cost_inr": 3000},
        ],
        "provenance": {"weekly_hours": "estimate", "growth_minutes_per_week": "estimate",
                       "capacity_orders_per_week": "estimate", "unit_cost": "estimate", "ad_budget_inr": "exact"},
    },
    "unit_cost_source": "estimate", "insights_source": "estimate",
    "weeks": {
        "stranger":  [2, 2, 3, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 3, 4],
        "friend":    [7, 7, 7, 8, 9, 8, 9, 9, 9, 9, 9, 10, 9, 9, 9, 11, 12],
        "fof":       [4, 5, 5, 6, 6, 6, 6, 7, 6, 5, 7, 7, 7, 6, 7, 9, 11],
        "unknown":   [1] * 17,
        "posts":     [2] * 17,
        "reach":     [900, 950, 1000, 900, 950, 900, 880, 900, 870, 860, 900, 880, 870, 860, 1100, 1300, 1500],
        "visit_rate": 0.08, "follow_rate": 0.15,
        "posts_with_orders": [1] * 17,
        "leads":     [18, 19, 20, 21, 22, 20, 21, 22, 21, 20, 22, 23, 22, 21, 24, 31, 37],
        "aov": 620, "cost_per_order": 350, "discount_share": 0.05,
        "repeat_order_share": 0.30,
        "days_between": [None, None, None, None, 21, 21, 20, 20, 21, 21, 20, 20, 21, 21, 20, 19, 18],
        "dispatch_delay": [1.0, 1.1, 1.0, 1.0, 1.1, 1.0, 1.1, 1.0, 1.1, 1.1, 1.0, 1.1, 1.1, 1.1, 1.3, 2.0, 2.6],
        "stockouts":  [0] * 15 + [1, 2],
        "turned_away": [0] * 14 + [1, 5, 9],
    },
}


# ---------------------------------------------------------------- weekly aggregates


def weekly_table(sc: dict) -> list[dict]:
    w = sc["weeks"]
    rows, customers, repeat_customers = [], 0, 0
    for i in range(17):
        orders = w["stranger"][i] + w["friend"][i] + w["fof"][i] + w["unknown"][i]
        repeat_orders = round(orders * w["repeat_order_share"])
        customers += orders - repeat_orders
        # a returning buyer becomes a repeat customer the first time they come back (about 80% of repeat orders)
        repeat_customers += round(repeat_orders * 0.8)
        reach = w["reach"][i]
        visits = round(reach * w["visit_rate"])
        revenue = orders * sc["weeks"]["aov"]
        rows.append({
            "h": i + 1, "orders": orders, "stranger": w["stranger"][i], "friend": w["friend"][i],
            "friend_of_friend": w["fof"][i], "unknown": w["unknown"][i], "posts": w["posts"][i],
            "reach": reach, "visits": visits, "follows": round(visits * w["follow_rate"]),
            "posts_with_orders": w["posts_with_orders"][i], "leads": w["leads"][i],
            "leads_ordered": round(orders * 0.7), "revenue": revenue,
            "cost": orders * sc["weeks"]["cost_per_order"],
            "discount_orders": round(orders * w["discount_share"]),
            "customers": customers, "repeat_customers": repeat_customers,
            "days_between": w["days_between"][i], "dispatch_delay": w["dispatch_delay"][i],
            "stockouts": w["stockouts"][i], "turned_away": w["turned_away"][i],
        })
    return rows


def window(rows, t, n=WINDOW):
    return rows[max(0, t - n):t]


def total(rows, key):
    return sum(r[key] for r in rows)


# ---------------------------------------------------------------- facts

# fact_id: (kpi, dimension, unit, direction, scope, value_fn) ; scope 'week' = last week, 'window' = last 4 weeks,
# 'cumulative' = all history up to the snapshot. value_fn(rows_in_scope, sc) -> (value, numerator, denominator)
def _rate(num_key, den_key, scale=1.0, digits=3):
    def fn(rs, sc):
        n, d = total(rs, num_key), total(rs, den_key)
        return (round(n / d * scale, digits) if d else None), n, d
    return fn


def _weighted_delay(rs, sc):
    o = total(rs, "orders")
    return round(sum(r["dispatch_delay"] * r["orders"] for r in rs) / o, 2), None, o


FACT_DEFS = {
    "f_orders_by_source_friend": ("orders_by_source", {"source": "friend"}, "count", None, "window",
                                  lambda rs, sc: (total(rs, "friend"), total(rs, "friend"), total(rs, "orders"))),
    "f_orders_by_source_friend_of_friend": ("orders_by_source", {"source": "friend_of_friend"}, "count", None, "window",
                                            lambda rs, sc: (total(rs, "friend_of_friend"), total(rs, "friend_of_friend"), total(rs, "orders"))),
    "f_orders_by_source_stranger": ("orders_by_source", {"source": "stranger"}, "count", None, "window",
                                    lambda rs, sc: (total(rs, "stranger"), total(rs, "stranger"), total(rs, "orders"))),
    "f_orders_by_source_unknown": ("orders_by_source", {"source": "unknown"}, "count", None, "window",
                                   lambda rs, sc: (total(rs, "unknown"), total(rs, "unknown"), total(rs, "orders"))),
    "f_stranger_orders_week": ("stranger_orders_week", {}, "count", "up", "week",
                               lambda rs, sc: (total(rs, "stranger"), total(rs, "stranger"), total(rs, "orders"))),
    "f_stranger_share": ("stranger_share", {}, "ratio", "up", "window", _rate("stranger", "orders")),
    "f_reach_per_post": ("reach_per_post", {}, "people", "up", "window", _rate("reach", "posts", digits=0)),
    "f_posts_with_orders": ("posts_with_orders", {}, "ratio", "up", "window", _rate("posts_with_orders", "posts")),
    "f_profile_visit_rate": ("profile_visit_rate", {}, "ratio", "up", "window", _rate("visits", "reach")),
    "f_follow_rate": ("follow_rate", {}, "ratio", "up", "window", _rate("follows", "visits")),
    "f_orders_per_1000_reach": ("orders_per_1000_reach", {}, "orders", "up", "window", _rate("orders", "reach", 1000, 2)),
    "f_lead_to_order_rate": ("lead_to_order_rate", {}, "ratio", "up", "window", _rate("leads_ordered", "leads")),
    "f_unit_cost_full": ("unit_cost_full", {}, "INR", "down", "window", _rate("cost", "orders", digits=1)),
    "f_margin_per_order": ("margin_per_order", {}, "INR", "up", "window",
                           lambda rs, sc: (round((total(rs, "revenue") - total(rs, "cost")) / total(rs, "orders"), 1),
                                           total(rs, "revenue") - total(rs, "cost"), total(rs, "orders"))),
    "f_margin_pct": ("margin_pct", {}, "ratio", "up", "window",
                     lambda rs, sc: (round((total(rs, "revenue") - total(rs, "cost")) / total(rs, "revenue"), 3),
                                     total(rs, "revenue") - total(rs, "cost"), total(rs, "revenue"))),
    "f_discount_share": ("discount_share", {}, "ratio", "down", "window", _rate("discount_orders", "orders")),
    "f_repeat_customer_share": ("repeat_customer_share", {}, "ratio", "up", "cumulative",
                                lambda rs, sc: (round(rs[-1]["repeat_customers"] / rs[-1]["customers"], 3),
                                                rs[-1]["repeat_customers"], rs[-1]["customers"])),
    "f_days_between_orders": ("days_between_orders", {}, "days", "down", "week",
                              lambda rs, sc: (rs[-1]["days_between"], None, rs[-1]["repeat_customers"])),
    "f_orders_per_week": ("orders_per_week", {}, "count", "up", "week", lambda rs, sc: (total(rs, "orders"), None, None)),
    "f_dispatch_delay_days": ("dispatch_delay_days", {}, "days", "down", "window", _weighted_delay),
    "f_stockouts": ("stockouts", {}, "count", "down", "window", lambda rs, sc: (total(rs, "stockouts"), None, None)),
    "f_orders_turned_away": ("orders_turned_away", {}, "count", "down", "window",
                             lambda rs, sc: (total(rs, "turned_away"), total(rs, "turned_away"),
                                             total(rs, "orders") + total(rs, "turned_away"))),
    "f_capacity_utilisation": ("capacity_utilisation", {}, "ratio", "up_to_limit", "window",
                               lambda rs, sc: (round(total(rs, "orders") / len(rs) / sc["business"]["capacity_orders_per_week"], 3),
                                               total(rs, "orders"), len(rs) * sc["business"]["capacity_orders_per_week"])),
}

ORIGIN = {"orders_by_source": "orders.csv + owner's friend/stranger tags", "stranger_orders_week": "orders.csv + tags",
          "stranger_share": "orders.csv + tags", "reach_per_post": "instagram insights", "posts_with_orders": "instagram insights + orders.csv",
          "profile_visit_rate": "instagram insights", "follow_rate": "instagram insights",
          "orders_per_1000_reach": "orders.csv + instagram insights", "lead_to_order_rate": "pasted chats + orders.csv",
          "unit_cost_full": "costs", "margin_per_order": "orders.csv + costs", "margin_pct": "orders.csv + costs",
          "discount_share": "orders.csv", "repeat_customer_share": "orders.csv", "days_between_orders": "orders.csv",
          "orders_per_week": "orders.csv", "dispatch_delay_days": "orders.csv (dispatched_at)", "stockouts": "interview",
          "orders_turned_away": "interview", "capacity_utilisation": "orders.csv + interview"}


def scope_rows(rows, t, scope):
    if scope == "week":
        return rows[t - 1:t]
    if scope == "cumulative":
        return rows[:t]
    return window(rows, t)


def fact_value(fid, rows, t, sc):
    kpi, dim, unit, direction, scope, fn = FACT_DEFS[fid]
    return fn(scope_rows(rows, t, scope), sc)


def baseline(fid, rows, t, sc):
    """Mean of the 3 best values the business reached in its own history up to week t."""
    kpi, dim, unit, direction, scope, fn = FACT_DEFS[fid]
    if direction is None or direction == "up_to_limit":
        return None
    first = WINDOW if scope == "window" else (5 if scope == "cumulative" else 1)
    vals = []
    for k in range(first, t + 1):
        rs = scope_rows(rows, k, scope)
        if scope == "cumulative" and rs[-1]["customers"] < 50:
            continue
        v = fn(rs, sc)[0]
        if v is not None:
            vals.append(v)
    if not vals:
        return None
    best = sorted(vals, reverse=(direction == "up"))[:BEST_N]
    return round(statistics.mean(best), 3)


def source_of(kpi, sc):
    if kpi in ("unit_cost_full", "margin_per_order", "margin_pct"):
        return sc["unit_cost_source"]
    if kpi in ("reach_per_post", "profile_visit_rate", "follow_rate"):
        return sc["insights_source"]
    if kpi in ("stockouts", "orders_turned_away"):
        return "estimate"
    if kpi == "orders_per_week":
        return "exact"
    return "derived"


def facts_for(sc, rows, week):
    t = SNAPSHOT_WEEK[week]
    win_from, _ = week_range(max(1, t - WINDOW + 1))
    _, to = week_range(t)
    out = []
    for fid, (kpi, dim, unit, direction, scope, fn) in FACT_DEFS.items():
        value, num, den = fact_value(fid, rows, t, sc)
        base = baseline(fid, rows, t, sc)
        frm = week_range(t)[0] if scope == "week" else (week_range(1)[0] if scope == "cumulative" else win_from)
        sample = total(scope_rows(rows, t, scope), "orders")
        quality = "ok" if sample >= MIN_ORDERS else ("partial" if sample >= 10 else "low")
        out.append({
            "fact_id": fid, "kpi": kpi, "dimension": dim, "period": {"from": frm, "to": to},
            "value": value, "unit": unit, "baseline": base,
            "delta_pct": round((value - base) / base * 100, 1) if (base and value is not None) else None,
            "numerator": num, "denominator": den, "definition_version": "v2", "quality_flag": quality,
            "snapshot": week, "source": source_of(kpi, sc), "sample_size": sample, "direction": direction,
            "origin": ORIGIN[kpi], "synthetic": True,
        })
    return {"business_id": sc["business"]["business_id"], "week": week, "as_of": to, "synthetic": True,
            "window_weeks": WINDOW, "baseline_rule": f"mean of the {BEST_N} best weeks (or 4-week windows) so far",
            "facts": out}


# ---------------------------------------------------------------- leads


def lead(lid, handle, source, relationship, signals, asked_for, last_message, intents, last_activity,
         deliverable=True, disqualified_reason=None, outcome="open"):
    reasons = [{"signal": s, "points": POINTS[s]} for s in signals]
    if relationship == "stranger" and "stranger" not in signals:
        reasons.append({"signal": "stranger", "points": POINTS["stranger"]})
    score = sum(r["points"] for r in reasons)
    group = "disqualified" if not deliverable else "hot" if score >= 50 else "warm" if score >= 20 else "cold"
    return {"lead_id": lid, "handle_ref": handle, "source": source, "relationship": relationship,
            "signals": [{"type": r["signal"], "date": last_activity} for r in reasons],
            "asked_for": asked_for, "last_message": last_message, "deliverable": deliverable,
            "intents": intents, "score": score, "group": group, "reasons": reasons,
            "disqualified_reason": disqualified_reason, "outcome": outcome, "last_activity": last_activity,
            "synthetic": True}


def rank(leads):
    """Group, then score; at equal score a stranger ranks above a friend; then the newest activity."""
    order = {"hot": 0, "warm": 1, "cold": 2, "disqualified": 3}
    ranked = sorted(leads, key=lambda l: (order[l["group"]], -l["score"], l["relationship"] != "stranger",
                                          -date.fromisoformat(l["last_activity"]).toordinal()))
    for i, l in enumerate(ranked, 1):
        l["rank"] = i
    return ranked


A = "asked_price_size_stock_delivery"


def boxbox_leads(week):
    base = {
        "week_1": [
            lead("lead_bb_01", "ig_user_7f3a", "dm", "stranger", [A, "saved_or_shared", "commented"],
                 {"product": "Monza Tee", "size": "L", "design": None, "city": "Pune"},
                 "Is the Monza tee available in L? How much with delivery to Pune?", ["buying_question"], "2026-10-04"),
            lead("lead_bb_02", "ig_user_1c22", "story", "friend", ["bought_before", "replied_to_story"],
                 {"product": "Pit Wall Cap", "size": None, "design": None, "city": "Pune"},
                 "When is the cap back in stock?", ["product_interest"], "2026-10-03"),
            lead("lead_bb_03", "ig_user_9b10", "comment", "stranger", ["commented", "saved_or_shared"],
                 {"product": "Lights Out Poster", "size": None, "design": None, "city": None},
                 "This poster is fire", ["product_interest"], "2026-10-02"),
            lead("lead_bb_04", "ig_user_44d0", "dm", "stranger", [A],
                 {"product": "Monza Tee", "size": "M", "design": None, "city": "Dubai"},
                 "Price for the Monza tee with shipping to Dubai?", ["buying_question"], "2026-10-03",
                 deliverable=False, disqualified_reason="city: Dubai (ships within India only)"),
            lead("lead_bb_05", "wa_ref_0815", "whatsapp", "friend_of_friend", [A, "commented"],
                 {"product": "Lights Out Poster", "size": None, "design": None, "city": "Mumbai"},
                 "How much is the poster with delivery to Mumbai?", ["buying_question"], "2026-10-02"),
            lead("lead_bb_06", "ig_user_5e61", "story", "stranger", ["replied_to_story"],
                 {"product": "Ferrari Red Tribute Tee", "size": None, "design": None, "city": None},
                 "Need this one", ["product_interest"], "2026-10-01"),
            lead("lead_bb_07", "ig_user_2a90", "comment", "friend", ["followed_or_liked_once"],
                 {"product": None, "size": None, "design": None, "city": None}, "Love the page",
                 ["general_praise"], "2026-09-30"),
            lead("lead_bb_08", "ig_user_8d3c", "comment", "stranger", ["followed_or_liked_once"],
                 {"product": None, "size": None, "design": None, "city": None}, "Nice", ["general_praise"], "2026-09-29"),
            lead("lead_bb_09", "ig_user_6f02", "dm", "stranger", [A],
                 {"product": "Monza Tee", "size": "XXL", "design": None, "city": "Bengaluru"},
                 "Do you have the Monza tee in XXL?", ["buying_question"], "2026-10-03",
                 deliverable=False, disqualified_reason="size: XXL (not made)"),
            lead("lead_bb_10", "ig_user_3b77", "comment", "friend_of_friend", ["saved_or_shared", "commented"],
                 {"product": "Hamilton 44 Keychain", "size": None, "design": None, "city": None},
                 "Saving this for later", ["product_interest"], "2026-10-01"),
            lead("lead_bb_11", "ig_user_0a4e", "dm", "stranger", [A],
                 {"product": "Monza Tee", "size": "M", "design": "name on the back", "city": "Pune"},
                 "Can you print my name on the back? What would it cost?", ["custom_request", "buying_question"],
                 "2026-10-04"),
            lead("lead_bb_12", "ig_user_c1d9", "comment", "friend", ["commented", "saved_or_shared", "inactive_30_days"],
                 {"product": "Pit Wall Cap", "size": None, "design": None, "city": None}, "Want this",
                 ["product_interest"], "2026-09-01"),
        ],
    }
    if week == "week_1":
        return base["week_1"]
    extra = {
        "week_2": [
            lead("lead_bb_13", "ig_user_d4e1", "dm", "stranger", [A, "saved_or_shared"],
                 {"product": "Monza Tee", "size": "M", "design": None, "city": "Pune"},
                 "Saw you on Pune F1 Fans. Monza tee in M, price?", ["buying_question"], "2026-10-10"),
            lead("lead_bb_14", "ig_user_77aa", "comment", "stranger", ["commented", "saved_or_shared"],
                 {"product": "Lights Out Poster", "size": None, "design": None, "city": None},
                 "Need this for my room", ["product_interest"], "2026-10-09"),
        ],
        "week_3": [
            lead("lead_bb_15", "ig_user_e0b3", "dm", "stranger", [A],
                 {"product": "Pit Wall Cap", "size": None, "design": None, "city": "Nashik"},
                 "Cap price with delivery to Nashik?", ["buying_question"], "2026-10-17"),
            lead("lead_bb_16", "ig_user_19f4", "story", "stranger", ["replied_to_story", "saved_or_shared"],
                 {"product": "Monza Tee", "size": None, "design": None, "city": None}, "Drop when?",
                 ["product_interest"], "2026-10-16"),
        ],
        "week_4": [
            lead("lead_bb_17", "ig_user_aa02", "dm", "stranger", [A, "commented"],
                 {"product": "Monza Tee", "size": "L", "design": None, "city": "Pune"},
                 "Race-weekend drop: is L still there?", ["buying_question"], "2026-10-24"),
            lead("lead_bb_18", "ig_user_5c5c", "dm", "stranger", [A],
                 {"product": "Lights Out Poster", "size": None, "design": None, "city": "Hyderabad"},
                 "Poster to Hyderabad, how much?", ["buying_question"], "2026-10-24"),
        ],
    }
    closed = {"week_2": {"lead_bb_01": "ordered", "lead_bb_02": "ordered", "lead_bb_04": "not_ordered", "lead_bb_09": "not_ordered"},
              "week_3": {"lead_bb_05": "ordered", "lead_bb_11": "ordered", "lead_bb_13": "ordered"},
              "week_4": {"lead_bb_03": "ordered", "lead_bb_15": "ordered", "lead_bb_06": "not_ordered"}}
    leads = list(base["week_1"])
    for wk in ("week_2", "week_3", "week_4"):
        leads += extra[wk]
        for l in leads:
            if l["lead_id"] in closed[wk]:
                l["outcome"] = closed[wk][l["lead_id"]]
        if wk == week:
            break
    return [l for l in leads if l["outcome"] == "open"] + [l for l in leads if l["outcome"] != "open"]


def baker_leads(week):
    w1 = [
        lead("lead_hb_01", "wa_ref_2201", "whatsapp", "stranger", [A],
             {"product": "Celebration Cake", "size": "1 kg", "design": "eggless", "city": "Pune"},
             "Eggless celebration cake, 1 kg, for Saturday? Price?", ["buying_question"], "2026-10-04"),
        lead("lead_hb_02", "wa_ref_1180", "whatsapp", "friend", ["bought_before", "replied_to_story"],
             {"product": "Brownie Box", "size": None, "design": None, "city": "Pune"},
             "Brownies again this week?", ["product_interest"], "2026-10-03"),
        lead("lead_hb_03", "wa_ref_3302", "whatsapp", "friend_of_friend", [A],
             {"product": "Diwali Hamper", "size": "10 boxes", "design": None, "city": "Pune"},
             "Price for 10 Diwali hampers for my office?", ["buying_question"], "2026-10-02"),
        lead("lead_hb_04", "ig_user_b7c1", "comment", "stranger", ["commented", "saved_or_shared"],
             {"product": "Cookie Jar", "size": None, "design": None, "city": None}, "These look so good",
             ["product_interest"], "2026-10-01"),
        lead("lead_hb_05", "wa_ref_9001", "whatsapp", "stranger", [A],
             {"product": "Celebration Cake", "size": None, "design": None, "city": "Hinjewadi"},
             "Do you deliver a cake to Hinjewadi?", ["buying_question"], "2026-10-03",
             deliverable=False, disqualified_reason="city: Hinjewadi (outside the 8 km delivery area)"),
        lead("lead_hb_06", "ig_user_0d0d", "comment", "friend", ["followed_or_liked_once"],
             {"product": None, "size": None, "design": None, "city": None}, "Yum", ["general_praise"], "2026-09-30"),
    ]
    extra = {"week_2": [lead("lead_hb_07", "wa_ref_4410", "whatsapp", "stranger", [A, "saved_or_shared"],
                             {"product": "Diwali Hamper", "size": "4 boxes", "design": None, "city": "Pune"},
                             "Saw you in the parents group. 4 hampers, price?", ["buying_question"], "2026-10-10")],
             "week_3": [lead("lead_hb_08", "wa_ref_5120", "whatsapp", "stranger", [A],
                             {"product": "Diwali Hamper", "size": "20 boxes", "design": None, "city": "Pune"},
                             "Can you do 20 hampers by 5 Nov?", ["buying_question"], "2026-10-17")],
             "week_4": [lead("lead_hb_09", "wa_ref_6011", "whatsapp", "friend_of_friend", [A],
                             {"product": "Brownie Box", "size": None, "design": None, "city": "Pune"},
                             "Brownie box for Sunday?", ["buying_question"], "2026-10-24")]}
    closed = {"week_2": {"lead_hb_01": "ordered", "lead_hb_05": "not_ordered"},
              "week_3": {"lead_hb_02": "ordered", "lead_hb_03": "ordered", "lead_hb_07": "ordered"},
              "week_4": {"lead_hb_04": "ordered"}}
    leads = list(w1)
    for wk in ("week_2", "week_3", "week_4"):
        if week == "week_1":
            break
        leads += extra[wk]
        for l in leads:
            if l["lead_id"] in closed[wk]:
                l["outcome"] = closed[wk][l["lead_id"]]
        if wk == week:
            break
    return leads


def leads_doc(sc, week):
    import copy
    raw = copy.deepcopy((boxbox_leads if sc["slug"] == "boxbox" else baker_leads)(week))
    open_leads = rank([l for l in raw if l["outcome"] == "open"])
    closed = [dict(l, rank=None) for l in raw if l["outcome"] != "open"]
    return {"business_id": sc["business"]["business_id"], "week": week,
            "as_of": week_range(SNAPSHOT_WEEK[week])[1], "synthetic": True, "points_version": "v1",
            "groups": {"hot": "50+", "warm": "20-49", "cold": "under 20", "disqualified": "cannot deliver"},
            "leads": open_leads + closed}


# ---------------------------------------------------------------- projection, context, quality


CONTEXT_FACTOR = {"boxbox": (1.10, "f1_calendar: 4 race weekends touch November; page views show 2.0x interest "
                                   "on race weekends (interest, not sales); a +10% sales effect is a stand-in assumption"),
                  "homebaker": (1.35, "india_festivals: Diwali on 2026-11-08; a +35% gifting effect is a stand-in assumption")}


def projection(sc, rows, week):
    t = SNAPSHOT_WEEK[week]
    hist = [r["orders"] for r in rows[t - 8:t]]
    xs = list(range(len(hist)))
    mx, my = statistics.mean(xs), statistics.mean(hist)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, hist)) / sum((x - mx) ** 2 for x in xs)
    weeks_in_month = 30 / 7
    factor, note = CONTEXT_FACTOR[sc["slug"]]
    base = (my + slope * (len(hist) - mx + 2)) * weeks_in_month
    expected = base * factor
    # week-to-week variation, but never narrower than +/-15%: a few weeks of a tiny business are not precise
    spread = max(statistics.stdev(hist) * weeks_in_month ** 0.5 * 1.5, 0.15 * expected)
    return {"business_id": sc["business"]["business_id"], "week": week, "synthetic": True,
            "month": {"from": "2026-11-01", "to": "2026-11-30"},
            "orders": {"low": round(expected - spread), "expected": round(expected), "high": round(expected + spread)},
            "basis": {"weeks_used": len(hist), "weekly_orders": hist, "trend_per_week": round(slope, 2),
                      "context_factor": factor, "context_source": note,
                      "method": "recent weekly average plus trend, times a context factor; range from week-to-week variation, at least +/-15%"},
            "confidence": "estimate", "estimate": True, "standin": True}


FESTIVALS = {
    "source": {"calendar": "stand-in: India festival calendar is planned in backend 1 (verify dates before use)"},
    "feed": "india_festivals", "from": "2026-09-28", "to": "2026-11-30",
    "events": [{"name": "Diwali", "date": "2026-11-08", "window_start": "2026-11-01", "window_end": "2026-11-08",
                "kind": "festival", "note": "gifting week before Diwali"}],
    "interest_uplift": None,
    "note": "Festival weeks are demand windows for gifting and food. No measured uplift yet.",
    "standin": True,
}


def data_quality(sc):
    orders = 234 if sc["slug"] == "boxbox" else 236
    return {"business_id": sc["business"]["business_id"], "synthetic": True,
            "overall": {"confidence": 0.84 if sc["slug"] == "boxbox" else 0.72,
                        "badge": "medium",
                        "summary": ("Orders load cleanly after repairs; 1 in 17 orders has no friend/stranger tag."
                                    if sc["slug"] == "boxbox" else
                                    "Orders load cleanly; unit costs and reach are the owner's estimates.")},
            "imports": [{"import_id": f"imp_{sc['slug']}_orders", "kind": "orders", "rows_total": orders + 9,
                         "rows_loaded": orders, "rows_repaired": 21, "rows_quarantined": 6, "duplicates_merged": 3}]}


# ---------------------------------------------------------------- write


def write(path: Path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    for sc in (BOXBOX, BAKER):
        rows = weekly_table(sc)
        d = OUT / sc["slug"]
        write(d / "business.json", dict(sc["business"], week="week_1"))
        write(d / "data_quality.json", data_quality(sc))
        write(d / "weekly_history.json", {"business_id": sc["business"]["business_id"], "synthetic": True,
                                          "note": "scenario input for the stand-in facts; h14 = week_1",
                                          "weeks": [dict(r, period=dict(zip(("from", "to"), week_range(r["h"]))))
                                                    for r in rows]})
        for week in SNAPSHOT_WEEK:
            write(d / f"facts_{week}.json", facts_for(sc, rows, week))
            write(d / f"leads_{week}.json", leads_doc(sc, week))
            write(d / f"projection_{week}.json", projection(sc, rows, week))
    write(OUT / "market_context" / "india_festivals.json", FESTIVALS)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
