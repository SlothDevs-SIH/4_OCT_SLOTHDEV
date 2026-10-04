"""Next month's sales: backend 1's projection, explained and tied to the one bottleneck.

The projection is always an estimate. If it is above what the owner can make, capacity is what
limits next month, whatever the main bottleneck is today.
"""
from __future__ import annotations

from datetime import date
from typing import Optional


def windows_in(context: Optional[dict], month: dict) -> list[dict]:
    if not context:
        return []
    out = []
    for r in context.get("race_weekends", []):
        if month["from"] <= r["weekend_end"] and r["weekend_start"] <= month["to"]:
            out.append({"name": r["name"], "from": r["weekend_start"], "to": r["weekend_end"]})
    for e in context.get("events", []):
        s, t = e.get("window_start") or e["date"], e.get("window_end") or e["date"]
        if month["from"] <= t and s <= month["to"]:
            out.append({"name": e["name"], "from": s, "to": t})
    return out


def build(projection: Optional[dict], diagnosis: dict, business: dict, context: Optional[dict]) -> dict:
    base = {"business_id": business["business_id"], "week": diagnosis["week"], "estimate": True,
            "synthetic": business.get("synthetic", False)}
    if not projection or not projection.get("orders"):
        return dict(base, status="no_projection",
                    message="There is not enough history to project next month yet; the projection is shown after a few more weeks.")
    month = projection["month"]
    days = (date.fromisoformat(month["to"]) - date.fromisoformat(month["from"])).days + 1
    cap_week = business.get("capacity_orders_per_week")
    cap_month = round(cap_week * days / 7) if cap_week else None
    o = projection["orders"]
    limited_by_capacity = cap_month is not None and o["expected"] > cap_month
    limiting = "capacity" if limited_by_capacity else diagnosis.get("primary")
    windows = windows_in(context, month)
    parts = [f"Next month ({month['from']} to {month['to']}) is projected at {o['low']} to {o['high']} orders, "
             f"most likely about {o['expected']}. This is an estimate."]
    b = projection.get("basis", {})
    if b:
        parts.append(f"It uses your last {b.get('weeks_used')} weeks (trend {b.get('trend_per_week'):+g} orders a week) "
                     f"and a context factor of {b.get('context_factor'):g}.")
    if windows:
        parts.append("Demand windows that month: " + ", ".join(f"{w['name']} ({w['from']} to {w['to']})" for w in windows) + ".")
    if limited_by_capacity:
        parts.append(f"That is more than you can make: about {cap_month} orders at {cap_week} a week. "
                     f"Capacity is what limits next month, so plan batches or pre-orders now.")
    elif limiting:
        parts.append(f"The bottleneck that most limits it is {limiting.replace('_', ' ')}; this week's actions target it.")
    return dict(base, status="ok", month=month, orders=o, basis=b, confidence=projection.get("confidence", "estimate"),
                capacity_month=cap_month, limited_by_capacity=limited_by_capacity, limiting_bottleneck=limiting,
                primary_bottleneck=diagnosis.get("primary"), demand_windows=windows, text=" ".join(parts),
                standin=projection.get("standin", False))
