import warnings

import pytest

warnings.filterwarnings("ignore", message=".*httpx.*")

from fastapi.testclient import TestClient  # noqa: E402

from backend.decision_engine.clients import DataClientV2  # noqa: E402
from backend.decision_engine.config import Settings  # noqa: E402
from backend.decision_engine.main import app, get_engine  # noqa: E402
from backend.decision_engine.service import Engine  # noqa: E402

BB, HB = "biz_boxbox", "biz_homebaker"


@pytest.fixture
def engine(tmp_path):
    settings = Settings(llm_provider="cache", llm_cache_only=True, llm_cache_dir=tmp_path / "cache")
    return Engine(settings=settings, data=DataClientV2(source="fixture"))


@pytest.fixture
def client(engine):
    app.dependency_overrides[get_engine] = lambda: engine
    yield TestClient(app)
    app.dependency_overrides.clear()
