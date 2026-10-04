"""Next month's sales: a transparent projection with a range. An ESTIMATE, never a machine-learning forecast.

Method (all shown to the owner as the `basis`)
1. Weekly order counts for the last up to 8 complete weeks before the snapshot.
2. A straight-line trend through them, DAMPED to half its slope (small samples exaggerate trends).
3. A market-context factor: how much of the next 4 weeks sits inside demand windows (race weekends, festivals) compared with the
   recent past, times an ASSUMED demand effect of those windows (a scenario assumption: no public data measures it for orders).
4. A range of about 8 in 10 outcomes if the recent pattern holds: expected plus or minus 1.28 times the weekly scatter, scaled to 4 weeks.
5. If the owner's capacity is known, demand above it is shown separately: you cannot sell what you cannot make.
If there are fewer than 6 weeks of history the projection says so instead of guessing.
"""
from __future__ import annotations

import math
import statistics
from datetime import date, timedelta
from typing import Optional

from ..external import f1_calendar, india_festivals
from . import config as C
from .model import BusinessData, as_of_for, d, history_start, window_weeks

MIN_WEEKS = 6
DAMPING = 0.5
Z80 = 1.2816


def _context_days(feed: str, start: date, end: date) -> set:
    out = set()
    if feed == "f1_calendar":
        wins = [(w["weekend_start"], w["weekend_end"]) for y in range(start.year, end.year + 1)
                for w in _safe(lambda: f1_calendar.race_weekends(y, start.isoformat(), end.isoformat()))]
    elif feed == "india_festivals":
        wins = [(w["window_start"], w["window_end"]) for w in india_festivals.demand_events(start.isoformat(), end.isoformat())]
    else:
        wins = []
    for a, b in wins:
        day = date.fromisoformat(a)
        while day <= date.fromisoformat(b):
            if start <= day <= end:
                out.add(day)
            day += timedelta(days=1)
    return out


def _safe(fn):
    try:
        return fn()
    except FileNotFoundError:
        return []


def project(data: BusinessData, week: int) -> dict:
    as_of = as_of_for(week, data)
    origin = history_start(data)
    wks = window_weeks(as_of, 8, origin)
    base = {"business_id": data.profile["business_id"], "snapshot": f"week_{week}", "week": f"week_{week}", "estimate": True,
            "month": {"from": as_of.isoformat(), "to": (as_of + timedelta(days=27)).isoformat()},
            "synthetic": bool(data.profile.get("synthetic"))}
    if len(wks) < MIN_WEEKS:
        return {**base, "orders": None, "confidence": "none",
                "message": f"Only {len(wks)} weeks of history; at least {MIN_WEEKS} are needed to project. Not projecting."}
    orders_w = [sum(1 for o in data.orders if a <= d(o["date"]) <= b) for a, b in wks]
    away_w = [sum(1 for t in data.turned_away if a <= d(t["date"]) <= b) for a, b in wks]
    counts = [o + t for o, t in zip(orders_w, away_w)]               # DEMAND: orders taken plus requests turned away
    n = len(counts)
    xs = list(range(n))
    mx, my = sum(xs) / n, sum(counts) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, counts)) / sxx if sxx else 0.0
    intercept = my - slope * mx
    resid = [y - (intercept + slope * x) for x, y in zip(xs, counts)]
    sd = math.sqrt(sum(r * r for r in resid) / max(1, n - 2))
    feed = (data.profile.get("context_feeds") or [None])[0]
    nxt_start, nxt_end = as_of, as_of + timedelta(days=27)
    hist_start, hist_end = wks[0][0], wks[-1][1]
    f_next = len(_context_days(feed, nxt_start, nxt_end)) / 28
    f_hist = len(_context_days(feed, hist_start, hist_end)) / ((hist_end - hist_start).days + 1)
    effect = float(data.meta.get("context_effect", 0.3))
    factor = (1 + effect * f_next) / (1 + effect * f_hist)
    # damped trend: the level at the last week plus half the slope per week ahead
    level = intercept + slope * (n - 1)
    weekly = [max(0.0, (level + DAMPING * slope * k) * factor) for k in range(1, 5)]
    expected = sum(weekly)
    half = Z80 * sd * math.sqrt(4)
    cap = data.profile.get("capacity_orders_per_week")
    low, high = max(0.0, expected - half), expected + half
    rng = lambda v: round(v)   # noqa: E731
    out = {**base,
           "demand": {"low": rng(low), "expected": rng(expected), "high": rng(high)},
           "weekly_expected_demand": [round(x, 1) for x in weekly],
           "basis": {"weeks_used": n, "weekly_demand": counts, "weekly_orders": orders_w, "weekly_turned_away": away_w,
                     "trend_per_week": round(slope, 2), "damping": DAMPING, "weekly_scatter_sd": round(sd, 2),
                     "context_factor": round(factor, 3), "context_source": feed, "context_share_next_4_weeks": round(f_next, 3),
                     "context_share_recent_weeks": round(f_hist, 3), "assumed_context_effect": effect,
                     "method": "damped straight-line trend of weekly demand (orders plus turned away), times a market-context factor; range = 1.28 x weekly scatter x 2"},
           "confidence": "low" if n < 8 or (my and sd / my > 0.35) else "medium",
           "note": "An estimate from recent weeks, not a forecast. The market-context effect is an assumption, not a measured fact."}
    if cap:
        limit = cap * 4
        capped = {k: rng(min(v, limit)) for k, v in (("low", low), ("expected", expected), ("high", high))}
        out["orders"] = capped
        out["capacity"] = {"orders_per_week": cap, "orders_per_month": limit, "demand_exceeds_capacity": expected > limit,
                           "orders_lost_to_capacity_expected": max(0, rng(expected) - limit),
                           "message": ("Demand is expected to exceed what you can make: about %d orders would be turned away." % max(0, rng(expected) - limit))
                           if expected > limit else "Demand is expected to fit within your capacity."}
    else:
        out["orders"] = out["demand"]
    return out
