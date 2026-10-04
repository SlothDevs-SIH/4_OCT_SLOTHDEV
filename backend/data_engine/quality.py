"""Data-quality view (contract shape: contracts/fixtures/data_quality.json) built from the import jobs.

For the demo business the messy orders export is imported once through the same pipeline a user upload goes
through, so the badge and the report are computed, not typed in.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from . import importer, store

# KPI -> how trustworthy its inputs are. Contribution metrics use estimated shipping costs, so they are partial.
KPI_QUALITY = {
    "cac": "ok", "conversion_rate": "ok", "roas": "ok", "contribution_roas": "partial",
    "repeat_rate": "ok", "response_latency_p90": "ok", "gross_margin": "ok",
}


def data_quality(business_id: str) -> Optional[dict]:
    ctx = store.get_context(business_id)
    if ctx is None:
        return None
    from .homebiz import store as hb
    if ctx.get("synthetic") and not hb.is_v2(business_id):
        store.ensure_demo_import()
    jobs = [j for j in store.list_imports(business_id) if j["status"] == "loaded"]
    base = {"business_id": business_id, "synthetic": bool(ctx.get("synthetic")),
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    if not jobs:
        return {**base, "overall": {"confidence": None, "badge": "none", "summary": "No data imported yet.",
                                    "unattributed_revenue_pct": None}, "kpi_quality": {}, "imports": []}
    reports = [importer.report_for(j["import_id"], j["kind"], j["run"]) for j in jobs]
    rows = sum(r["rows_total"] for r in reports)
    confidence = round(sum(r["confidence"] * r["rows_total"] for r in reports) / rows, 2)
    clean_orders = [c for j in jobs if j["kind"] == "orders" for c in j["run"]["clean"]]
    revenue = sum(c.get("revenue") or 0 for c in clean_orders)
    unattributed = sum(j["run"]["unattributed_revenue"] for j in jobs if j["kind"] == "orders")
    repaired = sum(r["rows_repaired"] for r in reports)
    quarantined = sum(r["rows_quarantined"] for r in reports)
    summary = (f"{repaired} rows repaired and {quarantined} quarantined across {len(reports)} import(s); "
               "shipping costs are estimated, so contribution metrics are partial.")
    return {**base,
            "overall": {"confidence": confidence, "badge": importer.badge(confidence), "summary": summary,
                        "unattributed_revenue_pct": round(100 * unattributed / revenue, 1) if revenue else None},
            "kpi_quality": dict(KPI_QUALITY), "imports": reports}
