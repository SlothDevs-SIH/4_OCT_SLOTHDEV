"""In-process registry of the home businesses (demo and created). State is in memory: demo businesses are regenerated
deterministically on load; created businesses live only for the life of the process (persistence to Supabase is a later step).
"""
from __future__ import annotations

import copy
import re
from datetime import date, timedelta
from typing import Optional

from pydantic import BaseModel, Field

from .. import importer
from . import config as C
from . import generate, intake
from .model import BusinessData, as_of_for, d, max_week

_data: dict = {}      # business_id -> BusinessData
_week: dict = {}      # business_id -> current snapshot week


# ------------------------------------------------------------------ create from the intake form
class ProductIn(BaseModel):
    name: str = Field(min_length=1)
    category: Optional[str] = None
    price: float = Field(ge=0)
    unit_cost: Optional[float] = Field(None, ge=0)


class ProfileIn(BaseModel):
    name: str = Field(min_length=2)
    kind: str = "home business"
    products: list[ProductIn] = Field(min_length=1)
    channels: list[str] = ["instagram", "whatsapp"]
    team_size: int = Field(1, ge=1, le=20)
    weekly_hours: float = Field(10, gt=0, le=100)
    capacity_orders_per_week: Optional[int] = Field(None, gt=0)
    ad_budget_inr: float = Field(0, ge=0)
    goal: str = Field("More orders from new people next month", min_length=3)
    serves_cities: list[str] = []
    serves_sizes: list[str] = []
    context_feed: Optional[str] = Field(None, pattern="^(f1_calendar|india_festivals)$")
    city: Optional[str] = None
    ships_to: Optional[str] = None
    topics: list[str] = []
    growth_minutes_per_week: Optional[int] = Field(None, ge=0, le=6000)
    order_link: Optional[str] = None
    payment: Optional[str] = None
    reach_candidates: list[dict] = []


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "business"


def create(p: ProfileIn) -> BusinessData:
    bid = f"biz_{slug(p.name)}"
    if bid in _data:
        raise ValueError(f"{bid} already exists")
    costs = {x.name: {"material": x.unit_cost or 0, "making": 0, "packaging": 0, "courier": 0, "full": x.unit_cost or 0, "source": "estimate"}
             for x in p.products if x.unit_cost is not None}
    fields = {k: {"value": v, "source": "estimate"} for k, v in [("weekly_hours", p.weekly_hours), ("capacity_orders_per_week", p.capacity_orders_per_week),
                                                                   ("team_size", p.team_size), ("ad_budget_inr", p.ad_budget_inr), ("goal", p.goal)] if v is not None}
    profile = {"business_id": bid, "name": p.name, "case_study": None, "synthetic": False, "kind": p.kind,
               "products": [{"name": x.name, "category": x.category, "price": x.price, "unit_cost": x.unit_cost} for x in p.products],
               "channels": p.channels, "team_size": p.team_size, "weekly_hours": p.weekly_hours, "ad_budget_inr": p.ad_budget_inr,
               "capacity_orders_per_week": p.capacity_orders_per_week, "goal": {"statement": p.goal, "horizon_days": 30},
               "constraints": {"forbidden_actions": ["paid_ads"] if p.ad_budget_inr == 0 else [], "approval_required_for": ["customer_outreach"], "notes": []},
               "context_feeds": [p.context_feed] if p.context_feed else [], "serves": {"cities": p.serves_cities, "sizes": p.serves_sizes},
               "city": p.city, "ships_to": p.ships_to, "topics": p.topics,
               "growth_minutes_per_week": p.growth_minutes_per_week if p.growth_minutes_per_week is not None else round(p.weekly_hours * 60 * 0.25),
               "order_link": p.order_link, "payment": p.payment, "reach_candidates": p.reach_candidates,
               "history_weeks": 0, "fields": fields}
    data = BusinessData(key=bid, profile=profile, costs=costs, meta={"max_week": 1, "created": True})
    _data[bid] = data
    _week[bid] = 1
    return data


# ------------------------------------------------------------------ demo businesses
def load_demo(key: str, week: int) -> BusinessData:
    if not 1 <= week <= C.ADVISORY_WEEKS:
        raise ValueError(f"week must be between 1 and {C.ADVISORY_WEEKS}")
    data = copy.deepcopy(generate.build(key))          # a fresh copy: edits (tags, outcomes) never touch the cached original
    data.meta["context_effect"] = C.SCENARIOS[key]["context_order_factor"] - 1
    bid = data.profile["business_id"]
    _data[bid] = data
    _week[bid] = week
    return data


def contract_view(data: BusinessData, week: int) -> dict:
    """The business as contract v2 section 2.1 describes it: one flat object, with where each estimate came from."""
    p = data.profile
    out = {k: v for k, v in p.items() if k not in ("fields", "kind", "history_weeks")}
    out["category"] = p.get("kind")
    out["week"] = f"week_{week}"
    prov = {k: v["source"] for k, v in p.get("fields", {}).items() if k in ("weekly_hours", "capacity_orders_per_week", "ad_budget_inr", "team_size")}
    prov["growth_minutes_per_week"] = "estimate"
    prov["unit_cost"] = "estimate" if any(c.get("source") == "estimate" for c in data.costs.values()) or not data.costs else "exact"
    out["provenance"] = prov
    return out


def get(business_id: str) -> Optional[BusinessData]:
    return _data.get(business_id)


def is_v2(business_id: str) -> bool:
    return business_id in _data


def current_week(business_id: str) -> int:
    return _week.get(business_id, 1)


def set_week(business_id: str, week: int) -> None:
    data = _data[business_id]
    as_of_for(week, data)                               # validates
    _week[business_id] = week


def find_lead(lead_id: str):
    for data in _data.values():
        for lead in data.leads:
            if lead["lead_id"] == lead_id:
                return data, lead
    return None, None


def counts(data: BusinessData) -> dict:
    return {"orders": len(data.orders), "posts": len(data.posts), "leads": len(data.leads), "products": len(data.profile["products"]),
            "turned_away": len(data.turned_away), "stockouts": len(data.stockouts)}


# ------------------------------------------------------------------ an import applied to a business
def _timeline(data: BusinessData) -> None:
    """For a created business: the history starts on the Monday of its first order; week 1 starts on the Monday after its last."""
    if not data.orders:
        return
    days = sorted(d(o["date"]) for o in data.orders)
    first, last = days[0], days[-1]
    data.meta["history_start"] = (first - timedelta(days=first.weekday())).isoformat()
    data.meta["advisory_start"] = (last + timedelta(days=7 - last.weekday())).isoformat()
    data.meta["max_week"] = 1
    data.profile["history_weeks"] = ((d(data.meta["advisory_start"]) - d(data.meta["history_start"])).days) // 7


def attach_import(job: dict) -> Optional[str]:
    """Add a loaded import's clean rows to the business's data. Returns what was attached, or None."""
    data = _data.get(job["business_id"])
    if data is None or job.get("status") != "loaded" or not data.meta.get("created"):
        return None                                      # demo businesses are generated; their import only shows the intake
    clean = job["run"]["clean"]
    if job["kind"] == "orders":
        new = intake.orders_from_clean(clean, data.costs)
        have = {o["order_id"] for o in data.orders}
        data.orders += [o for o in new if o["order_id"] not in have]
        data.orders.sort(key=lambda o: o["date"])
        seen = set()
        for o in data.orders:
            o["is_first_order"] = o["buyer_ref"] not in seen
            seen.add(o["buyer_ref"])
        _timeline(data)
    elif job["kind"] == "costs":
        data.costs.update(intake.costs_from_clean(clean))
        for p in data.profile["products"]:
            if p["name"] in data.costs:
                p["unit_cost"] = data.costs[p["name"]]["full"]
    elif job["kind"] == "insights":
        have = {p["post_id"] for p in data.posts}
        data.posts += [p for p in intake.posts_from_clean(clean) if p["post_id"] not in have]
    else:
        return None
    return job["kind"]
