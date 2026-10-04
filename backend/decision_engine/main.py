"""decision_engine API (contract section 4). Run: uvicorn backend.decision_engine.main:app --port 8002"""
from functools import lru_cache

from typing import Optional

from fastapi import APIRouter, Body, Depends, FastAPI, Query
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from backend.common.errors import install_error_handlers
from backend.decision_engine.service import Engine

router = APIRouter(prefix="/api/v1", tags=["decision_engine"])


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return Engine()


@router.get("/decision/health")
def health(engine: Engine = Depends(get_engine)):
    return engine.health()


@router.get("/intervention-templates")
def intervention_templates(engine: Engine = Depends(get_engine)):
    return engine.intervention_templates()


@router.get("/businesses/{business_id}/signals")
def signals(business_id: str, engine: Engine = Depends(get_engine)):
    return engine.signals(business_id)


class Decision(BaseModel):
    by: Optional[str] = None
    note: Optional[str] = None


@router.post("/businesses/{business_id}/recommendations/generate")
def generate(business_id: str, engine: Engine = Depends(get_engine)):
    return engine.generate(business_id)


@router.get("/businesses/{business_id}/recommendations")
def list_recommendations(business_id: str, engine: Engine = Depends(get_engine)):
    return engine.list_recommendations(business_id)


@router.get("/recommendations/{rec_id}")
def get_recommendation(rec_id: str, engine: Engine = Depends(get_engine)):
    return engine.get_recommendation(rec_id)


@router.post("/recommendations/{rec_id}/approve")
def approve(rec_id: str, body: Optional[Decision] = Body(None), engine: Engine = Depends(get_engine)):
    body = body or Decision()
    return engine.approve(rec_id, body.by, body.note)


@router.post("/recommendations/{rec_id}/reject")
def reject(rec_id: str, body: Optional[Decision] = Body(None), engine: Engine = Depends(get_engine)):
    body = body or Decision()
    return engine.reject(rec_id, body.by, body.note)


class PlanRequest(BaseModel):
    start_date: Optional[str] = None
    recommendation_ids: Optional[list[str]] = None


class TaskUpdate(BaseModel):
    status: Optional[str] = None
    owner: Optional[str] = None
    note: Optional[str] = None


@router.post("/businesses/{business_id}/plans")
def create_plan(business_id: str, body: Optional[PlanRequest] = Body(None), engine: Engine = Depends(get_engine)):
    body = body or PlanRequest()
    return engine.create_plan(business_id, body.start_date, body.recommendation_ids)


@router.get("/plans/{plan_id}")
def get_plan(plan_id: str, engine: Engine = Depends(get_engine)):
    return engine.get_plan(plan_id)


@router.patch("/tasks/{task_id}")
def update_task(task_id: str, body: TaskUpdate, engine: Engine = Depends(get_engine)):
    return engine.update_task(task_id, body.model_dump())


@router.post("/plans/{plan_id}/outcomes/evaluate")
def evaluate_outcomes(plan_id: str, engine: Engine = Depends(get_engine)):
    return engine.evaluate_outcomes(plan_id)


@router.get("/plans/{plan_id}/outcomes")
def get_outcomes(plan_id: str, engine: Engine = Depends(get_engine)):
    return engine.get_outcomes(plan_id)


class ChatRequest(BaseModel):
    question: str


@router.post("/businesses/{business_id}/chat")
def chat(business_id: str, body: ChatRequest, engine: Engine = Depends(get_engine)):
    return engine.chat(business_id, body.question)


@router.get("/recommendations/{rec_id}/draft")
def draft(rec_id: str, channel: str = Query("whatsapp", pattern="^(whatsapp|email)$"),
          engine: Engine = Depends(get_engine)):
    return engine.draft(rec_id, channel)


app = FastAPI(title="decision_engine")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
install_error_handlers(app)
app.include_router(router)
