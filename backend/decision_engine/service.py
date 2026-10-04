"""Engine: wires DataClient, the store and the LLM layer behind the API endpoints."""
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

from backend.common.errors import ApiError
from backend.decision_engine import outcomes as ledger
from backend.decision_engine import recommend
from backend.decision_engine import signals as signal_rules
from backend.decision_engine import templates
from backend.decision_engine.clients import DataClient, DataNotFound, DataSourceUnavailable
from backend.decision_engine.config import Settings
from backend.decision_engine.llm.synthesize import Synthesizer
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
                 store: Optional[Store] = None, synthesizer: Optional[Synthesizer] = None):
        self.settings = settings or Settings.from_env()
        self.data = data or DataClient(source=self.settings.data_source,
                                       base_url=self.settings.data_engine_url)
        self.store = store or Store()
        self.synthesizer = synthesizer or Synthesizer(self.settings)

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

    # ---------------------------------------------------- recommendations

    def generate(self, business_id: str) -> dict:
        inp = self.inputs(business_id)
        sdoc = self.signals(business_id, inp)
        now = utcnow()
        fresh = recommend.build(inp, sdoc, self.synthesizer, now)
        kept_ids = set()
        for rec in fresh:
            owner = self.store.recommendation_owner(rec["recommendation_id"])
            if owner is not None and owner != business_id:
                rec["recommendation_id"] = f"{rec['recommendation_id']}__{business_id}"
            old = self.store.get_recommendation(rec["recommendation_id"])
            if old and old["status"] in ("approved", "rejected") and rec["status"] != "blocked":
                # human decisions survive a re-run
                for k in ("status", "decision", "ledger", "created_at"):
                    rec[k] = old[k]
            kept_ids.add(rec["recommendation_id"])
        for old in self.store.recommendations_for(business_id):
            if old["recommendation_id"] not in kept_ids and old["status"] in ("approved", "rejected"):
                fresh.append(old)  # keep decided history even if its signal is gone
        ranked = recommend.rank(fresh)
        self.store.drop_recommendations(business_id, keep={r["recommendation_id"] for r in ranked})
        for rec in ranked:
            self.store.put_recommendation(rec)
        return self._recs_doc(business_id, ranked, now)

    def list_recommendations(self, business_id: str) -> dict:
        recs = self.store.recommendations_for(business_id)
        if not recs:
            return self.generate(business_id)
        return self._recs_doc(business_id, recommend.rank(recs), max(r["updated_at"] for r in recs))

    def _recs_doc(self, business_id: str, recs: list, generated_at: str) -> dict:
        return {"business_id": business_id, "synthetic": any(r["synthetic"] for r in recs),
                "generated_at": generated_at, "recommendations": recs}

    def get_recommendation(self, rec_id: str) -> dict:
        rec = self.store.get_recommendation(rec_id)
        if not rec:
            raise ApiError(404, "not_found", f"recommendation {rec_id} not found")
        return rec

    def approve(self, rec_id: str, by: Optional[str] = None, note: Optional[str] = None) -> dict:
        rec = self.get_recommendation(rec_id)
        if rec["status"] == "blocked":
            raise ApiError(409, "blocked", f"{rec_id} is blocked: {rec['blocked_reason']}")
        if rec["status"] == "approved":
            return rec
        with data_errors():
            facts = self.data.get_kpi_facts(rec["business_id"])
        now = utcnow()
        template = templates.templates_by_id()[rec["template_id"]]
        rec.update(status="approved", updated_at=now, decision={"action": "approved", "by": by, "at": now, "note": note},
                   ledger=ledger.freeze(rec, template, facts, now))
        self.store.put_recommendation(rec)
        return rec

    def reject(self, rec_id: str, by: Optional[str] = None, note: Optional[str] = None) -> dict:
        rec = self.get_recommendation(rec_id)
        if rec["status"] == "blocked":
            raise ApiError(409, "blocked", f"{rec_id} is blocked and cannot be decided")
        in_plan = [p["plan_id"] for p in self.store.plans_for(rec["business_id"])
                   if rec_id in p["recommendation_ids"]]
        if in_plan:
            raise ApiError(409, "in_plan", f"{rec_id} is part of {in_plan[0]}")
        now = utcnow()
        rec.update(status="rejected", updated_at=now, ledger=None,
                   decision={"action": "rejected", "by": by, "at": now, "note": note})
        self.store.put_recommendation(rec)
        return rec
