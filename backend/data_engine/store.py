"""In-process store for data_engine (prototype).

State lives in memory: the demo tenant is regenerated deterministically from the seed, and businesses
created through onboarding are kept in a dict. On serverless hosting, anything that must survive between
requests (import reports, approvals) belongs in Supabase; the demo tenant does not need it because it is
reproducible from the seed.
"""
from __future__ import annotations

from typing import Optional

from .context import demo_context
from .synth import config as C
from .synth.generate import Tenant, build_tenant

_contexts: dict = {}        # business_id -> context (onboarding-created businesses)
_active_phase: dict = {"phase": "baseline"}


def active_phase() -> str:
    return _active_phase["phase"]


def load_demo(phase: str) -> dict:
    """Make `phase` ('baseline' or 'day7') the active data for the demo business. Returns load info."""
    t = build_tenant(phase)
    _active_phase["phase"] = phase
    return {"phase": phase, "from": t.meta["from"], "to": t.meta["to"], "as_of": t.meta["as_of"],
            "counts": t.meta["counts"], "synthetic": True, "seed": C.SEED}


def get_context(business_id: str) -> Optional[dict]:
    if business_id == C.BUSINESS_ID:
        return demo_context(active_phase())
    return _contexts.get(business_id)


def save_context(ctx: dict) -> dict:
    _contexts[ctx["business_id"]] = ctx
    return ctx


def get_tenant(business_id: str, phase: Optional[str] = None) -> Optional[Tenant]:
    if business_id != C.BUSINESS_ID:
        return None
    return build_tenant(phase or active_phase())


def summary(business_id: str) -> Optional[dict]:
    t = get_tenant(business_id)
    if t is None:
        return None
    cur = (C.CURRENT_START.isoformat(), C.CURRENT_END.isoformat())
    wk = [o for o in t.orders if cur[0] <= o["ordered_at"][:10] <= cur[1]]
    return {
        "business_id": business_id, "synthetic": True, "phase": t.phase, "from": t.meta["from"], "to": t.meta["to"],
        "counts": t.meta["counts"],
        "current_week": {"from": cur[0], "to": cur[1], "orders": len(wk), "revenue": sum(o["revenue"] for o in wk)},
        "note": "Synthetic, deterministic scenario with planted incidents. Not real business data.",
    }
