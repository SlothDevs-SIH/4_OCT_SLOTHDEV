"""Order-based metrics (pure Python), written once and used on every order list: Box Box's own sheet,
the synthetic tenant, and the public Online Retail II validation file.

Definitions
- An order = one order id with a date, an optional customer id and a revenue amount (>= 0).
- Repeat customer share = customers with at least 2 orders / customers with at least 1 order.
- Days between orders = gap between a customer's consecutive orders (median and 90th percentile).
- Concentration = share of revenue from the top k customers; and the share of customers that make up 80% of revenue.
  (An alert rule from the brief family: "one client brings more than 30% of revenue".)
- Orders without a customer id are counted in totals but cannot be linked, and are reported separately.
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Iterable, Optional


@dataclass
class Order:
    order_id: str
    day: date
    customer: Optional[str]
    revenue: float


def _p90(values: list) -> Optional[float]:
    if not values:
        return None
    v = sorted(values)
    i = 0.9 * (len(v) - 1)
    lo = int(i)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (i - lo) * (v[hi] - v[lo])


def summarize(orders: Iterable[Order], top_ks: tuple = (1, 10)) -> dict:
    orders = list(orders)
    total_revenue = sum(o.revenue for o in orders)
    linked = [o for o in orders if o.customer]
    by_customer = defaultdict(list)
    for o in linked:
        by_customer[o.customer].append(o)
    n_cust = len(by_customer)
    repeat = sum(1 for v in by_customer.values() if len(v) >= 2)
    gaps = []
    for v in by_customer.values():
        days = sorted(o.day for o in v)
        gaps += [(b - a).days for a, b in zip(days, days[1:])]
    rev_by_customer = sorted((sum(o.revenue for o in v) for v in by_customer.values()), reverse=True)
    linked_revenue = sum(rev_by_customer)
    top_share = {f"top_{k}": (round(sum(rev_by_customer[:k]) / linked_revenue, 4) if linked_revenue else None) for k in top_ks}
    pareto = None
    if linked_revenue:
        running, n = 0.0, 0
        for r in rev_by_customer:
            running += r
            n += 1
            if running >= 0.8 * linked_revenue:
                break
        pareto = round(n / n_cust, 4)
    days_sorted = sorted(o.day for o in orders)
    return {
        "orders": len(orders), "orders_without_customer": len(orders) - len(linked), "customers": n_cust,
        "repeat_customers": repeat, "repeat_customer_share": round(repeat / n_cust, 4) if n_cust else None,
        "revenue_total": round(total_revenue, 2), "average_order_value": round(total_revenue / len(orders), 2) if orders else None,
        "days_between_orders_median": statistics.median(gaps) if gaps else None, "days_between_orders_p90": _p90(gaps),
        "concentration": {**top_share, "customer_share_for_80pct_of_revenue": pareto,
                          "single_customer_over_30pct": bool(top_share.get("top_1") and top_share["top_1"] > 0.30)},
        "first_order": days_sorted[0].isoformat() if days_sorted else None,
        "last_order": days_sorted[-1].isoformat() if days_sorted else None,
    }


def monthly(orders: Iterable[Order]) -> list:
    agg = defaultdict(lambda: [0, 0.0])
    for o in orders:
        key = o.day.strftime("%Y-%m")
        agg[key][0] += 1
        agg[key][1] += o.revenue
    return [{"month": k, "orders": v[0], "revenue": round(v[1], 2)} for k, v in sorted(agg.items())]
