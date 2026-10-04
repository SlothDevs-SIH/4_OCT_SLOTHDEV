"""decision_engine API (contract v2 section 4). Run: uvicorn backend.decision_engine.main:app --port 8002"""
from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, Body, Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.common.errors import install_error_handlers
from backend.decision_engine.service import Engine

router = APIRouter(prefix="/api/v1", tags=["decision_engine"])
WEEK = Query("week_1", pattern="^week_[1-4]$")


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return Engine()


class ActionUpdate(BaseModel):
    status: Optional[str] = None
    note: Optional[str] = None


@router.get("/decision/health")
def health(engine: Engine = Depends(get_engine)):
    return engine.health()


@router.get("/action-library")
def action_library():
    from backend.decision_engine.actions import library
    return library()


@router.get("/businesses/{business_id}/diagnosis")
def diagnosis(business_id: str, week: str = WEEK, engine: Engine = Depends(get_engine)):
    return engine.diagnosis(business_id, week)


@router.post("/businesses/{business_id}/actions/generate")
def generate_actions(business_id: str, week: str = WEEK, engine: Engine = Depends(get_engine)):
    return engine.generate_actions(business_id, week)


@router.get("/businesses/{business_id}/actions")
def list_actions(business_id: str, week: str = WEEK, engine: Engine = Depends(get_engine)):
    return engine.list_actions(business_id, week)


@router.patch("/actions/{action_id}")
def update_action(action_id: str, body: ActionUpdate, engine: Engine = Depends(get_engine)):
    return engine.update_action(action_id, body.status, body.note)


@router.get("/actions/{action_id}/draft")
def action_draft(action_id: str, channel: Optional[str] = Query(None, pattern="^(whatsapp|instagram_dm|instagram_post)$"),
                 engine: Engine = Depends(get_engine)):
    return engine.action_draft(action_id, channel)


@router.get("/businesses/{business_id}/reach-partners")
def reach_partners(business_id: str, week: str = WEEK, engine: Engine = Depends(get_engine)):
    return engine.reach_partners(business_id, week)


class Contacted(BaseModel):
    lead_id: str
    reason: str


@router.get("/businesses/{business_id}/lead-list")
def lead_list(business_id: str, week: str = WEEK, engine: Engine = Depends(get_engine)):
    return engine.lead_list(business_id, week)


@router.post("/businesses/{business_id}/lead-list/contacted")
def lead_contacted(business_id: str, body: Contacted, engine: Engine = Depends(get_engine)):
    """Record that a Warm lead was messaged for a reason, so it is not suggested again for that reason."""
    return engine.mark_contacted(business_id, body.lead_id, body.reason)


class PartnerResult(BaseModel):
    partner_id: str
    stranger_leads: int


class FollowUp(BaseModel):
    actions_done: Optional[list[str]] = None
    actions_skipped: Optional[list[str]] = None
    partner_results: Optional[list[PartnerResult]] = None


class ChatRequest(BaseModel):
    question: str


@router.post("/businesses/{business_id}/followup")
def followup(business_id: str, week: str = Query(..., pattern="^week_[2-4]$"), body: Optional[FollowUp] = Body(None),
             engine: Engine = Depends(get_engine)):
    body = body or FollowUp()
    return engine.followup(business_id, week, body.actions_done, body.actions_skipped,
                           [r.model_dump() for r in body.partner_results or []])


@router.get("/businesses/{business_id}/followups")
def followups(business_id: str, engine: Engine = Depends(get_engine)):
    return engine.followups(business_id)


@router.get("/businesses/{business_id}/next-month")
def next_month(business_id: str, week: str = WEEK, engine: Engine = Depends(get_engine)):
    return engine.next_month(business_id, week)


@router.post("/businesses/{business_id}/chat")
def chat(business_id: str, body: ChatRequest, week: str = WEEK, engine: Engine = Depends(get_engine)):
    return engine.chat(business_id, body.question, week)


app = FastAPI(title="decision_engine (Catalyst AI)")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
install_error_handlers(app)
app.include_router(router)
