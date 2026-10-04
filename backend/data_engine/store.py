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

DEMO_IMPORT_ID = "imp_aarohi_orders_messy"

_contexts: dict = {}        # business_id -> context (onboarding-created businesses)
_imports: dict = {}         # import_id -> job (raw rows, mapping, run result). In memory: see the module docstring
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
    if business_id in _contexts:
        return _contexts[business_id]
    from .homebiz import store as hb          # businesses of the home-business product (contract v2)
    data = hb.get(business_id)
    return hb.contract_view(data, hb.current_week(business_id)) if data is not None else None


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


# ---------------------------------------------------------------- imports
def save_import(job: dict) -> dict:
    _imports[job["import_id"]] = job
    return job


def get_import(import_id: str) -> Optional[dict]:
    if import_id == DEMO_IMPORT_ID:
        ensure_demo_import()
    return _imports.get(import_id)


def list_imports(business_id: str) -> list:
    return [j for j in _imports.values() if j["business_id"] == business_id]


def ensure_demo_import() -> dict:
    """Run the deliberately messy orders export through the real import pipeline (once)."""
    if DEMO_IMPORT_ID not in _imports:
        from . import importer
        from .synth import messy
        raw = messy.build_csv().encode("utf-8")
        columns, rows = importer.parse_csv(raw)
        suggested = importer.suggest_mapping("orders", columns)
        mapping = {f: m["column"] for f, m in suggested.items() if m["column"]}
        run = importer.run_import("orders", rows, mapping)
        _imports[DEMO_IMPORT_ID] = {
            "import_id": DEMO_IMPORT_ID, "business_id": C.BUSINESS_ID, "kind": "orders", "filename": "aarohi_orders_messy.csv",
            "checksum": importer.checksum(raw), "columns": columns, "rows": rows, "suggested": suggested,
            "mapping": mapping, "status": "loaded", "run": run}
    return _imports[DEMO_IMPORT_ID]
