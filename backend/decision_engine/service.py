"""Engine: wires DataClient, the store and the LLM layer behind the API endpoints."""
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

from backend.common.errors import ApiError
from backend.decision_engine import templates
from backend.decision_engine.clients import DataClient, DataNotFound, DataSourceUnavailable
from backend.decision_engine.config import Settings
from backend.decision_engine.store import Store


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@contextmanager
def data_errors():
    """Turn DataClient errors into contract error responses."""
    try:
        yield
    except DataNotFound as e:
        raise ApiError(404, "not_found", str(e)) from e
    except DataSourceUnavailable as e:
        raise ApiError(503, "data_source_unavailable", str(e)) from e


class Engine:
    def __init__(self, settings: Optional[Settings] = None, data: Optional[DataClient] = None,
                 store: Optional[Store] = None):
        self.settings = settings or Settings.from_env()
        self.data = data or DataClient(source=self.settings.data_source,
                                       base_url=self.settings.data_engine_url)
        self.store = store or Store()

    def health(self) -> dict:
        return {"status": "ok", "module": "decision_engine", "data_source": self.data.source,
                "llm_provider": self.settings.llm_provider,
                "templates": len(templates.library()["templates"])}

    def intervention_templates(self) -> dict:
        return templates.library()
