"""data_engine routes (backend-1, Soham). Contract: contracts/API_CONTRACT.md section 3.

Stage 1a (real): onboarding, demo load, context, data summary.
Stage 1b (real): CSV import (upload, mapping, validate, repair, quarantine), quality report, data-quality badge.
Stage 2a (real): KPI facts, daily series, funnel.
Still fixture-backed (Stage 2b): lead queue, model card.
"""
from fastapi import APIRouter, File, Query, Response, UploadFile

from backend.common.errors import ApiError, not_implemented
from backend.data_engine import importer, public, store
from backend.data_engine.context import BusinessIn, context_from_onboarding
from backend.data_engine.synth import config as C, messy

router = APIRouter(prefix="/api/v1", tags=["data_engine"])


@router.get("/data/health")
def health():
    return {"service": "data_engine", "status": "ok", "stage": "2a"}


# --- onboarding and demo data (real) -----------------------------------------
@router.post("/businesses", status_code=201)
def create_business(payload: BusinessIn):
    try:
        ctx = context_from_onboarding(payload)
    except ValueError as e:
        raise ApiError(422, "invalid_business_model", str(e))
    if store.get_context(ctx["business_id"]) is not None:
        raise ApiError(409, "business_exists", f"{ctx['business_id']} already exists")
    return store.save_context(ctx)


@router.get("/businesses/{business_id}")
def get_business(business_id: str):
    ctx = public.get_context(business_id)
    if ctx is None:
        raise ApiError(404, "business_not_found", f"business {business_id!r} not found")
    return ctx


@router.post("/demo/load")
def load_demo(phase: str = Query("baseline", pattern="^(baseline|day7)$")):
    """Load the synthetic Aarohi Skin tenant: the baseline week, or the day-7 follow-up replay."""
    info = store.load_demo(phase)
    store.ensure_demo_import()
    return {**store.get_context(C.BUSINESS_ID), "demo_load": info}


@router.get("/businesses/{business_id}/data-summary")
def data_summary(business_id: str):
    s = store.summary(business_id)
    if s is None:
        raise ApiError(404, "no_data", f"no data loaded for {business_id!r}")
    return s


# --- import, mapping, validation (Stage 1b, real) -----------------------------
def _job_or_404(import_id: str) -> dict:
    job = store.get_import(import_id)
    if job is None:
        raise ApiError(404, "import_not_found", f"import {import_id!r} not found (state is in memory: re-upload after a restart)")
    return job


def _upload_response(job: dict) -> dict:
    return {"import_id": job["import_id"], "business_id": job["business_id"], "kind": job["kind"], "filename": job["filename"],
            "status": job["status"], "rows_total": len(job["rows"]), "columns": job["columns"],
            "suggested_mapping": job["suggested"], "missing_required": importer.missing_required(
                job["kind"], {f: m["column"] for f, m in job["suggested"].items() if m["column"]}),
            "preview": job["rows"][:5]}


async def _read_job(business_id: str, kind: str, file: UploadFile) -> dict:
    if store.get_context(business_id) is None:
        raise ApiError(404, "business_not_found", f"business {business_id!r} not found")
    raw = await file.read()
    try:
        columns, rows = importer.parse_csv(raw)
    except ValueError as e:
        raise ApiError(422, "invalid_csv", str(e))
    return {"import_id": f"imp_{kind}_{importer.checksum(raw)[:8]}", "business_id": business_id, "kind": kind,
            "filename": file.filename, "checksum": importer.checksum(raw), "columns": columns, "rows": rows,
            "suggested": importer.suggest_mapping(kind, columns), "mapping": None, "status": "uploaded", "run": None}


def _confirm(job: dict, mapping: dict) -> dict:
    unknown = [c for c in mapping.values() if c and c not in job["columns"]]
    if unknown:
        raise ApiError(422, "unknown_column", f"columns not in the file: {unknown}")
    missing = importer.missing_required(job["kind"], mapping)
    if missing:
        raise ApiError(422, "missing_required_mapping", f"map these required fields: {missing}")
    job["run"] = importer.run_import(job["kind"], job["rows"], {f: c for f, c in mapping.items() if c})
    job["mapping"], job["status"] = mapping, "loaded"
    return importer.report_for(job["import_id"], job["kind"], job["run"])


@router.post("/businesses/{business_id}/imports", status_code=201)
async def upload_import(business_id: str, kind: str = Query(..., pattern="^(campaigns|leads|orders)$"),
                        file: UploadFile = File(...)):
    """Step 1: upload a CSV. Returns the detected columns and a suggested mapping to confirm or edit."""
    return _upload_response(store.save_import(await _read_job(business_id, kind, file)))


@router.post("/imports/{import_id}/confirm")
def confirm_import(import_id: str, body: dict):
    """Step 2: confirm or edit the mapping (`{"mapping": {field: column}}`), then validate, repair, quarantine, load."""
    job = _job_or_404(import_id)
    return _confirm(job, body.get("mapping", body))


@router.post("/businesses/{business_id}/imports/auto", status_code=201)
async def auto_import(business_id: str, kind: str = Query(..., pattern="^(campaigns|leads|orders)$"),
                      file: UploadFile = File(...)):
    """One call (upload + accept the suggested mapping). Convenient for demos and stateless hosting."""
    job = store.save_import(await _read_job(business_id, kind, file))
    mapping = {f: m["column"] for f, m in job["suggested"].items() if m["column"]}
    report = _confirm(job, mapping)
    return {**_upload_response(job), "report": report}


@router.get("/imports/{import_id}/report")
def import_report(import_id: str):
    job = _job_or_404(import_id)
    if job["status"] != "loaded":
        raise ApiError(409, "not_confirmed", "confirm the mapping first")
    return importer.report_for(job["import_id"], job["kind"], job["run"])


@router.get("/imports/{import_id}/quarantine")
def import_quarantine(import_id: str, limit: int = Query(50, ge=1, le=500)):
    """Rows that were not loaded, with the reason (additive endpoint)."""
    job = _job_or_404(import_id)
    if job["status"] != "loaded":
        raise ApiError(409, "not_confirmed", "confirm the mapping first")
    q = job["run"]["quarantined"]
    return {"import_id": import_id, "total": len(q), "rows": q[:limit]}


@router.get("/businesses/{business_id}/data-quality")
def data_quality(business_id: str):
    dq = public.get_data_quality(business_id)
    if dq is None:
        raise ApiError(404, "business_not_found", f"business {business_id!r} not found")
    return dq


@router.get("/demo/sample-import/orders.csv")
def sample_orders_csv():
    """The deliberately messy synthetic orders export (download it, then upload it to try the import)."""
    return Response(messy.build_csv(), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="aarohi_orders_messy.csv"'})


@router.post("/demo/import-sample")
def import_sample():
    """Run the messy sample through the real import pipeline and return the upload view plus the report."""
    job = store.ensure_demo_import()
    return {**_upload_response(job), "report": importer.report_for(job["import_id"], job["kind"], job["run"])}


# --- KPIs and funnel (Stage 2a, real) -----------------------------------------
@router.get("/businesses/{business_id}/kpis")
def kpis(business_id: str, from_: str | None = Query(None, alias="from"), to: str | None = None,
         snapshot: str | None = Query(None, pattern="^(baseline|day7)$")):
    """KPI facts. `snapshot` defaults to the loaded demo phase (baseline = current week, day7 = follow-up week)."""
    snap = snapshot or store.active_phase()
    try:
        facts = public.get_kpi_facts(business_id, from_, to, snap)
    except ValueError as e:
        raise ApiError(422, "invalid_period", str(e))
    if facts is None:
        raise ApiError(404, "business_not_found", f"business {business_id!r} not found")
    return {"business_id": business_id, "synthetic": business_id == C.BUSINESS_ID, "snapshot": snap, "facts": facts}


@router.get("/businesses/{business_id}/kpis/daily")
def kpis_daily(business_id: str, from_: str | None = Query(None, alias="from"), to: str | None = None,
               channel: str | None = None):
    try:
        data = public.get_kpi_series(business_id, from_, to, channel)
    except ValueError as e:
        raise ApiError(422, "invalid_period", str(e))
    if data is None:
        raise ApiError(404, "business_not_found", f"business {business_id!r} not found")
    return data


@router.get("/businesses/{business_id}/funnel")
def funnel(business_id: str, snapshot: str | None = Query(None, pattern="^(baseline|day7)$")):
    snap = snapshot or store.active_phase()
    facts = public.get_kpi_facts(business_id, None, None, snap)
    if facts is None:
        raise ApiError(404, "business_not_found", f"business {business_id!r} not found")
    return {"business_id": business_id, "snapshot": snap, "stages": [f for f in facts if f["kpi"].startswith("funnel_")]}


@router.get("/businesses/{business_id}/segments/rfm")
def rfm(business_id: str):
    raise not_implemented("RFM segments (should-have)")


@router.get("/businesses/{business_id}/leads/queue")
def lead_queue(business_id: str, limit: int | None = None):
    data = public.get_lead_scores(business_id, limit)
    if data is None:
        raise ApiError(404, "business_not_found", f"business {business_id!r} not found")
    return data


@router.get("/models/lead-conversion/card")
def model_card():
    return public.get_lead_scores(C.BUSINESS_ID)["model_card"]
