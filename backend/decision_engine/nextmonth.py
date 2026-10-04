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
    unique = {(w["name"], w["from"]): w for w in out}  # race weekends also appear as events
    return sorted(unique.values(), key=lambda w: w["from"])


def build(projection: Optional[dict], diagnosis: dict, business: dict, context: Optional[dict]) -> dict:
    base = {"business_id": business["business_id"], "week": diagnosis["week"], "estimate": True,
            "synthetic": business.get("synthetic", False)}
    if not projection or not projection.get("orders"):
        return dict(base, status="no_projection",
                    message="There is not enough history to project the next weeks yet; the projection appears after a few more weeks.")
    month = projection["month"]
    o, demand = projection["orders"], projection.get("demand") or projection["orders"]
    cap = projection.get("capacity") or {}
    if not cap and business.get("capacity_orders_per_week"):
        days = (date.fromisoformat(month["to"]) - date.fromisoformat(month["from"])).days + 1
        per_month = round(business["capacity_orders_per_week"] * days / 7)
        cap = {"orders_per_week": business["capacity_orders_per_week"], "orders_per_month": per_month,
               "demand_exceeds_capacity": demand["expected"] > per_month}
    limited = bool(cap.get("demand_exceeds_capacity"))
    limiting = "capacity" if limited else diagnosis.get("primary")
    windows = windows_in(context, month)
    parts = [f"For {month['from']} to {month['to']} we project {o['low']} to {o['high']} orders, most likely about "
             f"{o['expected']}. This is an estimate from your recent weeks, not a forecast."]
    b = projection.get("basis", {})
    if b.get("weeks_used") is not None:
        parts.append(f"It uses your last {b['weeks_used']} weeks (trend {b.get('trend_per_week', 0):+g} a week) and a "
                     f"context factor of {b.get('context_factor', 1):g} from {b.get('context_source') or 'no calendar'}.")
    if windows:
        parts.append("Demand windows in that period: " + ", ".join(f"{w['name']} ({w['from']} to {w['to']})" for w in windows) + ".")
    if limited:
        parts.append(f"Demand is about {demand['expected']} orders ({demand['low']} to {demand['high']}), more than the "
                     f"{cap.get('orders_per_month')} you can make at {cap.get('orders_per_week')} a week. "
                     + (cap.get("message") or "") + " Capacity is what limits these weeks: plan batches or pre-orders now.")
    elif limiting:
        parts.append(f"The bottleneck that most limits it is {limiting.replace('_', ' ')}; this week's actions target it.")
    else:
        parts.append("No single bottleneck limits it right now; keep doing what works.")
    return dict(base, status="ok", month=month, orders=o, demand=demand, basis=b,
                weekly_expected_demand=projection.get("weekly_expected_demand"),
                confidence=projection.get("confidence", "estimate"), capacity=cap, limited_by_capacity=limited,
                limiting_bottleneck=limiting, primary_bottleneck=diagnosis.get("primary"), demand_windows=windows,
                note=projection.get("note"), text=" ".join(parts))
