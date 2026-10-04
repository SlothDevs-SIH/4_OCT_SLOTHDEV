"""data_engine routes (backend-1, Soham). Contract: contracts/API_CONTRACT.md section 3.

Stage 1a (real): onboarding, demo load, context, data summary.
Still fixture-backed (replaced in later stages): import/quality, KPIs, funnel, lead queue, model card.
"""
from fastapi import APIRouter, File, Query, UploadFile

from backend.common.errors import ApiError, not_implemented
from backend.data_engine import public, store
from backend.data_engine.context import BusinessIn, context_from_onboarding
from backend.data_engine.synth import config as C

router = APIRouter(prefix="/api/v1", tags=["data_engine"])


@router.get("/data/health")
def health():
    return {"service": "data_engine", "status": "ok", "stage": "1a"}


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
    return {**store.get_context(C.BUSINESS_ID), "demo_load": info}


@router.get("/businesses/{business_id}/data-summary")
def data_summary(business_id: str):
    s = store.summary(business_id)
    if s is None:
        raise ApiError(404, "no_data", f"no data loaded for {business_id!r}")
    return s


# --- import, mapping, validation (Stage 1b) ----------------------------------
@router.post("/businesses/{business_id}/imports")
async def upload_import(business_id: str, kind: str = Query(..., pattern="^(campaigns|leads|orders)$"),
                        file: UploadFile = File(...)):
    raise not_implemented("CSV upload and suggested mapping (Stage 1b)")


@router.post("/imports/{import_id}/confirm")
def confirm_import(import_id: str, mapping: dict):
    raise not_implemented("mapping confirmation, validation and load (Stage 1b)")


@router.get("/imports/{import_id}/report")
def import_report(import_id: str):
    return public.get_data_quality(C.BUSINESS_ID)["imports"][0]


@router.get("/businesses/{business_id}/data-quality")
def data_quality(business_id: str):
    dq = public.get_data_quality(business_id)
    if dq is None:
        raise ApiError(404, "business_not_found", f"business {business_id!r} not found")
    return dq


# --- KPIs, funnel, leads (Stage 2; still fixture-backed) ----------------------
@router.get("/businesses/{business_id}/kpis")
def kpis(business_id: str, from_: str | None = Query(None, alias="from"), to: str | None = None,
         snapshot: str = Query("baseline", pattern="^(baseline|day7)$")):
    facts = public.get_kpi_facts(business_id, from_, to, snapshot)
    if facts is None:
        raise ApiError(404, "business_not_found", f"business {business_id!r} not found")
    return {"business_id": business_id, "synthetic": True, "snapshot": snapshot, "facts": facts}


@router.get("/businesses/{business_id}/kpis/daily")
def kpis_daily(business_id: str, from_: str | None = Query(None, alias="from"), to: str | None = None,
               channel: str | None = None):
    data = public.get_kpi_series(business_id, from_, to, channel)
    if data is None:
        raise ApiError(404, "business_not_found", f"business {business_id!r} not found")
    return data


@router.get("/businesses/{business_id}/funnel")
def funnel(business_id: str):
    facts = public.get_kpi_facts(business_id) or []
    return {"business_id": business_id, "stages": [f for f in facts if f["kpi"].startswith("funnel_")]}


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
