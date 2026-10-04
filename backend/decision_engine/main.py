"""decision_engine API (contract section 4). Run: uvicorn backend.decision_engine.main:app --port 8002"""
from functools import lru_cache

from typing import Optional

from fastapi import APIRouter, Body, Depends, FastAPI
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


app = FastAPI(title="decision_engine")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
install_error_handlers(app)
app.include_router(router)
