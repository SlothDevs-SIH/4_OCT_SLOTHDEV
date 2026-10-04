"""Business context for the demo tenant and for businesses created through onboarding.

The demo context has the same shape as contracts/fixtures/business_context.json, plus additive fields:
`business_model` (d2c | hybrid | b2c_retail), `segments`, `data_phase`.
"""
from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, Field

from .synth import config as C

BUSINESS_MODELS = ("d2c", "hybrid", "b2c_retail")

# Channel set per business-model profile (b2c_retail is a profile only: no own-site funnel)
PROFILE_CHANNELS = {
    "d2c": ["instagram", "google", "email", "whatsapp", "website"],
    "hybrid": ["instagram", "google", "email", "whatsapp", "website"],
    "b2c_retail": ["marketplace", "offline_store", "instagram", "whatsapp"],
}


def demo_context(phase: str = "baseline") -> dict:
    ig_week = sum(C.CURRENT["instagram"]["spend"])
    g_week = C.CURRENT["google"]["spend"]
    return {
        "business_id": C.BUSINESS_ID,
        "synthetic": True,
        "name": "Aarohi Skin",
        "category": "D2C skincare",
        "business_model": "hybrid",
        "segments": ["d2c_consumer", "bulk_b2b_inquiries"],
        "city": "Pune",
        "country": "IN",
        "currency": "INR",
        "timezone": "Asia/Kolkata",
        "channels": list(C.CHANNELS),
        "products": [{"sku": s["sku"], "name": s["name"], "price": s["price"], "unit_cost": s["unit_cost"]} for s in C.SKUS],
        "goal": {
            "goal_id": "goal_q4_profitable_growth",
            "statement": "Grow profitable revenue this quarter without raising total ad spend",
            "primary_kpi": "contribution_roas",
            "secondary_kpis": ["repeat_rate", "lead_wins"],
            "horizon_days": 90,
        },
        "constraints": {
            "weekly_ad_budget_inr": float(ig_week + g_week),
            "extra_spend_allowed_inr": 0,
            "forbidden_actions": ["increase_total_ad_spend"],
            "approval_required_for": ["spend", "customer_outreach", "data_change"],
            "lead_response_sla_hours": C.SLA_HOURS,
        },
        "capacity": {
            "weekly_hours": 8, "weekly_minutes": 480, "max_minutes_per_day": 120,
            "owners": [
                {"owner_id": "owner_founder", "role": "Founder", "weekly_minutes": 300},
                {"owner_id": "owner_ops", "role": "Operations assistant", "weekly_minutes": 180},
            ],
        },
        "periods": {
            "current": {"from": C.CURRENT_START.isoformat(), "to": C.CURRENT_END.isoformat()},
            "baseline": {"from": C.BASELINE_START.isoformat(), "to": C.BASELINE_END.isoformat()},
            "day7": {"from": C.DAY7_START.isoformat(), "to": C.DAY7_END.isoformat()},
        },
        "data_phase": phase,
        "created_at": "2026-10-04T04:30:00Z",
    }


# ---------------------------------------------------------------- onboarding payload
class Goal(BaseModel):
    statement: str = Field(min_length=3)
    primary_kpi: str = "contribution_roas"
    secondary_kpis: list[str] = []
    horizon_days: int = Field(90, ge=7, le=365)


class Constraints(BaseModel):
    weekly_ad_budget_inr: float = Field(0, ge=0)
    extra_spend_allowed_inr: float = Field(0, ge=0)
    forbidden_actions: list[str] = []
    approval_required_for: list[str] = ["spend", "customer_outreach", "data_change"]
    lead_response_sla_hours: float = Field(4, gt=0)


class Capacity(BaseModel):
    weekly_hours: float = Field(8, gt=0, le=80)
    max_minutes_per_day: int = Field(120, gt=0)


class BusinessIn(BaseModel):
    name: str = Field(min_length=2)
    business_model: str = "d2c"
    category: str = "D2C"
    city: Optional[str] = None
    channels: Optional[list[str]] = None
    goal: Goal
    constraints: Constraints = Constraints()
    capacity: Capacity = Capacity()


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "business"


def context_from_onboarding(b: BusinessIn) -> dict:
    if b.business_model not in BUSINESS_MODELS:
        raise ValueError(f"business_model must be one of {BUSINESS_MODELS}")
    return {
        "business_id": f"biz_{slug(b.name)}",
        "synthetic": False,
        "name": b.name,
        "category": b.category,
        "business_model": b.business_model,
        "segments": ["d2c_consumer"] + (["bulk_b2b_inquiries"] if b.business_model == "hybrid" else []),
        "city": b.city, "country": "IN", "currency": "INR", "timezone": "Asia/Kolkata",
        "channels": b.channels or PROFILE_CHANNELS[b.business_model],
        "products": [],
        "goal": {"goal_id": "goal_1", **b.goal.model_dump()},
        "constraints": b.constraints.model_dump(),
        "capacity": {**b.capacity.model_dump(), "weekly_minutes": int(b.capacity.weekly_hours * 60), "owners": []},
        "periods": {},
        "data_phase": None,
        "created_at": None,
    }
