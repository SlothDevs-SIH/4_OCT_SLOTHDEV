"""Gateway: one app on port 8000 that mounts both modules' routers.

Each module exposes `router` (an APIRouter with prefix /api/v1) in its `main.py`.
A module that is not merged yet is skipped, so the gateway runs on any branch.

    DATA_SOURCE=local uvicorn backend.gateway.main:app --port 8000
"""
import importlib
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.common.errors import install_error_handlers

log = logging.getLogger("gateway")

app = FastAPI(title="Slothdev GrowthOS")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
install_error_handlers(app)

MODULES = ("backend.data_engine.main", "backend.decision_engine.main")
mounted = []
for name in MODULES:
    try:
        app.include_router(importlib.import_module(name).router)
        mounted.append(name)
    except ModuleNotFoundError as e:
        if e.name not in (name, name.rsplit(".", 1)[0]):
            raise  # a real missing dependency, not an unmerged module
        log.warning("gateway: %s not mounted (%s)", name, e)


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "mounted": mounted}
