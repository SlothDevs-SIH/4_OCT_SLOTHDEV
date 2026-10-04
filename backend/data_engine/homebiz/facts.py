"""Facts for the five bottlenecks and the main measure (orders from strangers). Deterministic, pure Python, never an LLM.

Definitions (v2)
- A fact is computed over a window of the 4 complete Monday-to-Sunday weeks before the snapshot day (as_of).
  Cumulative facts (repeat customer share, days between orders) are computed as of the window's end.
- The BASELINE is the business's OWN BEST window in its history (the highest value when higher is better, the lowest when
  lower is better). `gap_to_best` = how far the current window is from that best, as a share of the best (0 when current is best).
- A snapshot only sees events dated before its as_of day (point in time): week 1 never sees week 2.
- Every fact carries its sample size. Under the minimum sample the fact is an `estimate` and flagged `partial`.
- `source`: `exact` (counted straight from the order sheet), `derived` (computed from self-reported tags such as friend or
  stranger, or from leads), `estimate` (rests on numbers the owner stated, such as unit costs and capacity).
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import date, timedelta
from typing import Callable, Optional

from . import config as C
from .model import BusinessData, as_of_for, d, history_start, week_label, window_weeks

VERSION = "v2"
MIN_ORDERS, MIN_POSTS, MIN_LEADS = 30, 8, 20
RELATIONSHIPS = ("friend", "friend_of_friend", "stranger", "unknown")


class Ctx:
    """Everything the facts may look at, filtered to what had happened before `as_of`."""

    def __init__(self, data: BusinessData, as_of: date):
        self.data, self.as_of = data, as_of
        self.orders = [o for o in data.orders if d(o["date"]) < as_of]
        self.posts = [p for p in data.posts if d(p["date"]) < as_of]
        self.leads = [l for l in data.leads if d(l["created"]) < as_of]
        self.turned_away = [t for t in data.turned_away if d(t["date"]) < as_of]
        self.stockouts = [t for t in data.stockouts if d(t["date"]) < as_of]
        self.capacity = data.profile.get("capacity_orders_per_week")
        self.costs_source = next(iter(data.costs.values()), {}).get("source", "estimate") if data.costs else "estimate"
        self.attributed = {o["post_id"] for o in self.orders if o.get("post_id")}

    def orders_in(self, a: date, b: date) -> list:
        return [o for o in self.orders if a <= d(o["date"]) <= b]

    def posts_in(self, a: date, b: date) -> list:
        return [p for p in self.posts if a <= d(p["date"]) <= b]

    def dispatched(self, o: dict) -> Optional[int]:
        if o.get("dispatched_at") and d(o["dispatched_at"]) < self.as_of:
            return (d(o["dispatched_at"]) - d(o["date"])).days
        return None


def _ratio(n, den):
    return n / den if den else None


# Each calc returns (value, numerator, denominator, sample_size, sample_kind) or None when there is nothing to measure.
def _by_source(rel):
    def calc(c: Ctx, a: date, b: date, weeks: int):
        os_ = c.orders_in(a, b)
        n = sum(1 for o in os_ if o["relationship"] == rel)
        if not os_:
            return None
        return n / weeks, n, weeks, len(os_), "orders"
    return calc


def _stranger_week(c, a, b, weeks):
    os_ = c.orders_in(a, b)
    n = sum(1 for o in os_ if o["relationship"] == "stranger")
    return (n / weeks, n, weeks, len(os_), "orders") if os_ else None


def _stranger_share(c, a, b, weeks):
    os_ = c.orders_in(a, b)
    n = sum(1 for o in os_ if o["relationship"] == "stranger")
    return (n / len(os_), n, len(os_), len(os_), "orders") if os_ else None


def _reach_per_post(c, a, b, weeks):
    ps = c.posts_in(a, b)
    return (sum(p["reach"] for p in ps) / len(ps), sum(p["reach"] for p in ps), len(ps), len(ps), "posts") if ps else None


def _posts_with_orders(c, a, b, weeks):
    ps = c.posts_in(a, b)
    n = sum(1 for p in ps if p["post_id"] in c.attributed)
    return (n / len(ps), n, len(ps), len(ps), "posts") if ps else None


def _visit_rate(c, a, b, weeks):
    ps = c.posts_in(a, b)
    reach = sum(p["reach"] for p in ps)
    return (sum(p["profile_visits"] for p in ps) / reach, sum(p["profile_visits"] for p in ps), reach, len(ps), "posts") if reach else None


def _follow_rate(c, a, b, weeks):
    ps = c.posts_in(a, b)
    visits = sum(p["profile_visits"] for p in ps)
    return (sum(p["follows"] for p in ps) / visits, sum(p["follows"] for p in ps), visits, len(ps), "posts") if visits else None


def _per_1000_reach(c, a, b, weeks):
    ps, os_ = c.posts_in(a, b), c.orders_in(a, b)
    reach = sum(p["reach"] for p in ps)
    return (1000 * len(os_) / reach, len(os_), reach, len(os_), "orders") if reach else None


def _lead_to_order(c, a, b, weeks):
    ls = [l for l in c.leads if a <= d(l["created"]) <= b and l["outcome"] in ("ordered", "not_ordered") and l["outcome_date"] and d(l["outcome_date"]) < c.as_of]
    n = sum(1 for l in ls if l["outcome"] == "ordered")
    return (n / len(ls), n, len(ls), len(ls), "leads") if ls else None


def _item_cost(o: dict) -> float:
    return sum(i["qty"] * i["unit_cost"] for i in o["items"])


def _unit_cost(c, a, b, weeks):
    os_ = c.orders_in(a, b)
    qty = sum(i["qty"] for o in os_ for i in o["items"])
    cost = sum(_item_cost(o) for o in os_)
    return (cost / qty, cost, qty, len(os_), "orders") if qty else None


def _margin_order(c, a, b, weeks):
    os_ = c.orders_in(a, b)
    if not os_:
        return None
    margin = sum(o["total"] - _item_cost(o) for o in os_)
    return margin / len(os_), margin, len(os_), len(os_), "orders"


def _margin_pct(c, a, b, weeks):
    os_ = c.orders_in(a, b)
    rev = sum(o["total"] for o in os_)
    if not rev:
        return None
    margin = sum(o["total"] - _item_cost(o) for o in os_)
    return margin / rev, margin, rev, len(os_), "orders"


def _discount_share(c, a, b, weeks):
    os_ = c.orders_in(a, b)
    gross = sum(o["gross"] for o in os_)
    return (sum(o["discount"] for o in os_) / gross, sum(o["discount"] for o in os_), gross, len(os_), "orders") if gross else None


def _repeat_share(c, a, b, weeks):
    per = defaultdict(int)
    for o in c.orders:
        if d(o["date"]) <= b:
            per[o["buyer_ref"]] += 1
    if not per:
        return None
    rep = sum(1 for v in per.values() if v >= 2)
    return rep / len(per), rep, len(per), len(per), "customers"


def _days_between(c, a, b, weeks):
    by = defaultdict(list)
    for o in c.orders:
        if d(o["date"]) <= b:
            by[o["buyer_ref"]].append(d(o["date"]))
    gaps = [(sorted(v)[i + 1] - sorted(v)[i]).days for v in by.values() if len(v) > 1 for i in range(len(v) - 1)]
    return (statistics.median(gaps), sum(gaps), len(gaps), len(gaps), "repeat gaps") if gaps else None


def _orders_week(c, a, b, weeks):
    os_ = c.orders_in(a, b)
    return (len(os_) / weeks, len(os_), weeks, len(os_), "orders") if os_ else None


def _dispatch_delay(c, a, b, weeks):
    vals = [c.dispatched(o) for o in c.orders_in(a, b)]
    vals = [v for v in vals if v is not None]
    return (statistics.median(vals), sum(vals), len(vals), len(vals), "dispatched orders") if vals else None


def _stockouts(c, a, b, weeks):
    n = sum(1 for t in c.stockouts if a <= d(t["date"]) <= b)
    return n, n, weeks, max(1, len(c.orders_in(a, b))), "orders"


def _turned_away(c, a, b, weeks):
    n = sum(1 for t in c.turned_away if a <= d(t["date"]) <= b)
    return n, n, weeks, max(1, len(c.orders_in(a, b))), "orders"


def _utilisation(c, a, b, weeks):
    os_ = c.orders_in(a, b)
    if not c.capacity or not os_:
        return None
    return len(os_) / weeks / c.capacity, len(os_), weeks * c.capacity, len(os_), "orders"


# fact_id, kpi, bottleneck, unit, better (higher|lower|info), source_rule (exact|derived|estimate), dimension, calc
SPECS: list = []
for _rel in RELATIONSHIPS[:3]:
    SPECS.append((f"f_orders_by_source_{_rel}", "orders_by_source", "reach", "orders/week", "info", "derived", {"relationship": _rel}, _by_source(_rel)))
SPECS += [
    ("f_stranger_orders_week", "stranger_orders_per_week", "reach", "orders/week", "higher", "derived", {}, _stranger_week),
    ("f_stranger_share", "stranger_share", "reach", "ratio", "higher", "derived", {}, _stranger_share),
    ("f_reach_per_post", "reach_per_post", "reach", "people", "higher", "exact", {}, _reach_per_post),
    ("f_posts_with_orders", "posts_with_orders", "reach", "ratio", "higher", "exact", {}, _posts_with_orders),
    ("f_profile_visit_rate", "profile_visit_rate", "conversion", "ratio", "higher", "exact", {}, _visit_rate),
    ("f_follow_rate", "follow_rate", "conversion", "ratio", "higher", "exact", {}, _follow_rate),
    ("f_orders_per_1000_reach", "orders_per_1000_reach", "conversion", "orders", "higher", "exact", {}, _per_1000_reach),
    ("f_lead_to_order_rate", "lead_to_order_rate", "conversion", "ratio", "higher", "derived", {}, _lead_to_order),
    ("f_unit_cost_full", "unit_cost_full", "margin", "INR", "info", "estimate", {}, _unit_cost),
    ("f_margin_per_order", "margin_per_order", "margin", "INR", "higher", "estimate", {}, _margin_order),
    ("f_margin_pct", "margin_pct", "margin", "ratio", "higher", "estimate", {}, _margin_pct),
    ("f_discount_share", "discount_share", "margin", "ratio", "lower", "exact", {}, _discount_share),
    ("f_repeat_customer_share", "repeat_customer_share", "repeat_orders", "ratio", "higher", "exact", {}, _repeat_share),
    ("f_days_between_orders", "days_between_orders", "repeat_orders", "days", "info", "exact", {}, _days_between),
    ("f_orders_per_week", "orders_per_week", "capacity", "orders/week", "info", "exact", {}, _orders_week),
    ("f_dispatch_delay_days", "dispatch_delay_days", "capacity", "days", "lower", "exact", {}, _dispatch_delay),
    ("f_stockouts", "stockouts", "capacity", "count", "lower", "exact", {}, _stockouts),
    ("f_orders_turned_away", "orders_turned_away", "capacity", "count", "lower", "exact", {}, _turned_away),
    ("f_capacity_utilisation", "capacity_utilisation", "capacity", "ratio", "info", "estimate", {}, _utilisation),
]
SPEC_BY_ID = {s[0]: s for s in SPECS}
_MIN = {"orders": MIN_ORDERS, "posts": MIN_POSTS, "leads": MIN_LEADS, "customers": 20, "repeat gaps": 5, "dispatched orders": 20}


def _round(v: float, unit: str) -> float:
    return round(v, 4) if unit in ("ratio",) else round(v, 2)


def _value_at(spec, c: Ctx, week_windows: list):
    calc = spec[7]
    a, b = week_windows[0][0], week_windows[-1][1]
    return calc(c, a, b, len(week_windows))


def compute(data: BusinessData, week: int, window: int = 4) -> list:
    """All facts for the snapshot `week_k` (as_of = start of advisory week k)."""
    as_of = as_of_for(week, data)
    if not any(d(o["date"]) < as_of for o in data.orders):
        raise ValueError("no orders imported yet")
    c = Ctx(data, as_of)
    origin = history_start(data)
    cur_w = window_weeks(as_of, window, origin)
    if len(cur_w) < window:
        raise ValueError("not enough history for a 4-week window")
    # all complete windows in the history seen by this snapshot, ending at each week boundary
    ends = []
    k = 0
    while True:
        w = window_weeks(as_of - timedelta(weeks=k), window, origin)
        if len(w) < window:
            break
        ends.append(w)
        k += 1
    out = []
    for spec in SPECS:
        fid, kpi, bott, unit, better, srule, dim, calc = spec
        cur = _value_at(spec, c, cur_w)
        if cur is None:
            continue
        value, num, den, n, kind = cur
        best_val, best_w = None, None
        if better in ("higher", "lower"):
            for w in ends:
                r = _value_at(spec, c, w)
                if r is None:
                    continue
                if best_val is None or (r[0] > best_val if better == "higher" else r[0] < best_val):
                    best_val, best_w = r[0], w
        small = n < _MIN.get(kind, MIN_ORDERS)
        source = "estimate" if small else srule
        if srule == "estimate" and fid.startswith("f_unit") or fid in ("f_margin_per_order", "f_margin_pct"):
            source = "estimate"                                     # rests on the owner's own cost figures
        gap = None
        if best_val not in (None, 0):
            gap = (best_val - value) / best_val if better == "higher" else (value - best_val) / best_val
            gap = max(0.0, round(gap, 4))
        elif best_val == 0 and better == "lower":
            gap = 1.0 if value > 0 else 0.0            # best was none at all: any occurrence is the full gap
        delta = round((value - best_val) / best_val * 100, 1) if best_val not in (None, 0) else None
        out.append({
            "fact_id": fid, "kpi": kpi, "bottleneck": bott, "dimension": dim,
            "period": {"from": cur_w[0][0].isoformat(), "to": cur_w[-1][1].isoformat()}, "value": _round(value, unit), "unit": unit,
            "baseline": _round(best_val, unit) if best_val is not None else None,
            "best_period": {"from": best_w[0][0].isoformat(), "to": best_w[-1][1].isoformat()} if best_w else None,
            "delta_pct": delta, "gap_to_best": gap, "better": better,
            "numerator": _round(num, "") if isinstance(num, float) else num, "denominator": _round(den, "") if isinstance(den, float) else den,
            "definition_version": VERSION, "quality_flag": "partial" if small else "ok", "source": source, "sample_size": n,
            "sample_kind": kind, "snapshot": week_label(week), "synthetic": bool(data.profile.get("synthetic"))})
    return out


def weekly_series(data: BusinessData, fact_id: str, week: int) -> dict:
    """One fact, week by week (1-week windows), up to the snapshot."""
    if fact_id not in SPEC_BY_ID:
        raise KeyError(fact_id)
    spec = SPEC_BY_ID[fact_id]
    as_of = as_of_for(week, data)
    c = Ctx(data, as_of)
    points = []
    start = history_start(data)
    while start + timedelta(days=6) < as_of:
        end = start + timedelta(days=6)
        r = spec[7](c, start, end, 1)
        points.append({"from": start.isoformat(), "to": end.isoformat(), "value": _round(r[0], spec[3]) if r else None,
                       "sample_size": r[3] if r else 0})
        start += timedelta(days=7)
    return {"fact_id": fact_id, "kpi": spec[1], "unit": spec[3], "snapshot": week_label(week), "points": points}
