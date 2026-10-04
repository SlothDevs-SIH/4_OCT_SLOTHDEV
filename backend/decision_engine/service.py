"""Engine: wires DataClient, the store and the LLM layer behind the API endpoints."""
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

from backend.common.errors import ApiError
from backend.decision_engine import signals as signal_rules
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

    # ------------------------------------------------------------- inputs

    def inputs(self, business_id: str) -> dict:
        """Everything the pipeline reads from data_engine, fetched once per run."""
        with data_errors():
            ctx = self.data.get_context(business_id)
            facts = self.data.get_kpi_facts(business_id)
            leads = self.data.get_lead_scores(business_id)
            quality = self.data.get_data_quality(business_id)
            try:
                series = self.data.get_kpi_series(business_id)
            except DataSourceUnavailable:
                series = None  # anomaly detection is skipped, rules still run
        snapshot = {"business_id": business_id, "taken_at": utcnow(), "context": ctx,
                    "fact_ids": [f["fact_id"] for f in facts]}
        self.store.add_context_snapshot(business_id, snapshot)
        return {"context": ctx, "facts": facts, "lead_scores": leads, "data_quality": quality,
                "series": series}

    # ------------------------------------------------------------ signals

    def signals(self, business_id: str, inputs: Optional[dict] = None) -> dict:
        inp = inputs or self.inputs(business_id)
        doc = signal_rules.detect(inp["context"], inp["facts"], inp["lead_scores"], inp["series"])
        doc["generated_at"] = utcnow()
        self.store.put_signals(business_id, doc)
        return doc
