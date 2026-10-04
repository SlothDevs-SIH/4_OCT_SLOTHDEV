"""decision_engine API (contract section 4). Run: uvicorn backend.decision_engine.main:app --port 8002"""
from functools import lru_cache

from fastapi import APIRouter, Depends, FastAPI
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


app = FastAPI(title="decision_engine")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
install_error_handlers(app)
app.include_router(router)
