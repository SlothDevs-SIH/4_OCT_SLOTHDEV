"""Standalone data_engine app, and the `router` the gateway mounts.

    uvicorn backend.data_engine.main:app --port 8001 --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.common.errors import install_error_handlers
from backend.data_engine.router import router  # noqa: F401  (the gateway imports `router` from here)

app = FastAPI(title="Slothdev GrowthOS: data_engine")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
install_error_handlers(app)
app.include_router(router)
