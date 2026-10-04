"""Engine: wires DataClient, the store and the LLM layer behind the API endpoints (contract v2 section 4)."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from backend.common.errors import ApiError
from backend.decision_engine import actions as advice
from backend.decision_engine import diagnosis as dx
from backend.decision_engine import drafts
from backend.decision_engine.clients import DataClient, DataClientError, DataNotFound, DataSourceUnavailable
from backend.decision_engine.clients.data_client import WEEKS
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
    except ValueError as e:
        raise ApiError(422, "invalid_request", str(e)) from e


def slug(business_id: str) -> str:
    return business_id.removeprefix("biz_")


class Engine:
    def __init__(self, settings: Optional[Settings] = None, data: Optional[DataClient] = None,
                 store: Optional[Store] = None, synthesizer: Optional[Synthesizer] = None):
        self.settings = settings or Settings.from_env()
        self.data = data or DataClient(source=self.settings.data_source, base_url=self.settings.data_engine_url)
        self.store = store or Store()
        self.synthesizer = synthesizer or Synthesizer(self.settings)

    def health(self) -> dict:
        return {"status": "ok", "module": "decision_engine", "contract": "v2", "data_source": self.data.source,
                "llm_provider": self.settings.llm_provider, "actions_in_library": len(advice.library()["actions"])}

    # ------------------------------------------------------------- inputs

    def inputs(self, business_id: str, week: str) -> dict:
        """Everything one week's advice reads, fetched once (point in time: only data up to `week`)."""
        if week not in WEEKS:
            raise ApiError(422, "invalid_request", f"week must be one of {WEEKS}")
        with data_errors():
            business = self.data.get_context(business_id)
            facts_doc = self.data.get_facts(business_id, week)
        context = None
        for feed in business.get("context_feeds", []):
            try:
                context = self.data.get_market_context(feed, facts_doc.get("as_of"))
                break
            except DataClientError:
                continue  # a feed that is not built yet: no timing advice, said so by the gate
        as_of = facts_doc.get("as_of") or date.today().isoformat()
        facts = {f["fact_id"]: f for f in facts_doc["facts"]}
        customers = (facts.get("f_repeat_customer_share") or {}).get("denominator")
        return {"business": business, "facts_doc": facts_doc, "facts": facts, "context": context, "as_of": as_of,
                "windows": advice.demand_windows(context, as_of),
                "partners": advice.rank_partners(business, self.store.partner_results_for(business_id)),
                "customers": customers}

    # ---------------------------------------------------------- diagnosis

    def diagnosis(self, business_id: str, week: str = "week_1", inputs: Optional[dict] = None) -> dict:
        inp = inputs or self.inputs(business_id, week)
        doc = dx.diagnose(inp["facts_doc"], lambda b: advice.actionable(b, inp["business"], inp))
        doc["generated_at"] = utcnow()
        self.store.put_diagnosis(doc)
        return doc

    # ------------------------------------------------------------ actions

    def generate_actions(self, business_id: str, week: str = "week_1") -> dict:
        inp = self.inputs(business_id, week)
        diag = self.diagnosis(business_id, week, inp)
        business = inp["business"]
        minutes = business.get("growth_minutes_per_week") or (business.get("weekly_hours", 0) * 60) // 4
        doc = {"business_id": business_id, "week": week, "as_of": inp["as_of"],
               "synthetic": business.get("synthetic", False), "bottleneck": diag["primary"],
               "minutes_available": minutes, "ranking": advice.library()["ranking"], "actions": [], "blocked": [],
               "risk_flags": [f for f in [advice.brand_risk(business)] if f]}
        if diag["primary"] is None:
            doc["message"] = diag["message"]
            self.store.drop_actions(business_id, week, keep=set())
            return doc
        primary = next(f for f in diag["bottlenecks"] if f["bottleneck"] == diag["primary"])
        cands = advice.candidates(diag["primary"], business, inp)
        chosen = advice.select(cands, minutes)
        due = (date.fromisoformat(inp["as_of"]) + timedelta(days=7)).isoformat()
        partners = {p["partner_id"]: p for p in inp["partners"]["partners"]}
        keep = set()
        for c in chosen:
            aid = f"act_{slug(business_id)}_w{week[-1]}_{c['action_key']}"
            old = self.store.get_action(aid)
            risk = [f for f in [advice.brand_risk(business, c["raises_visibility"])] if f]
            evidence = list(primary["evidence_ids"]) + ([c["partner_id"]] if c["partner_id"] else [])
            action = {
                "action_id": aid, "business_id": business_id, "week": week, "bottleneck": c["bottleneck"],
                "action_key": c["action_key"], "title": c["title"], "what": c["what"],
                "why": self._why(primary, c, partners.get(c["partner_id"]), inp["windows"]),
                "evidence_ids": evidence, "effort_min": c["effort_min"],
                "target": advice.target_for(c, inp["facts"]), "due": due,
                "status": old["status"] if old else "todo", "note": old.get("note") if old else None,
                "requires_approval": c["requires_approval"], "approval_reason": c["approval_reason"],
                "risk_flags": risk, "risks": c["risks"], "score": c["score"], "score_parts": c["parts"],
                "partner_id": c["partner_id"], "draft_channels": c["draft_channels"],
                "raises_visibility": c["raises_visibility"], "synthetic": business.get("synthetic", False),
            }
            self.store.put_action(action)
            keep.add(aid)
            doc["actions"].append(action)
        self.store.drop_actions(business_id, week, keep)
        doc["blocked"] = [{"action_key": c["action_key"], "title": c["title"], "reason": c["gate"]["blocked_reason"]}
                          for c in cands if not c["gate"]["eligible"]]
        doc["not_chosen"] = [{"action_key": c["action_key"], "title": c["title"], "score": c["score"]}
                             for c in cands if c["gate"]["eligible"] and c not in chosen]
        doc["minutes_planned"] = sum(a["effort_min"] for a in doc["actions"])
        return doc

    @staticmethod
    def _why(primary: dict, c: dict, partner: Optional[dict], windows: list) -> str:
        text = primary["cards"][0]["claim"] if primary["cards"] else ""
        if primary.get("where"):
            text += f" {primary['where'][0].upper()}{primary['where'][1:]}."
        if partner:
            p = partner["score_parts"]
            text += (f" {partner['name']} ranks first among your partners: same topic, "
                     f"{'same city' if p['location_match'] == 1.0 else 'nearby'}, and strong engagement "
                     f"({round(partner['engagement_rate'] * 100, 1):g}% comments and shares per follower).")
        if c["action_key"] == "reach_demand_window_drop" and windows:
            w = windows[0]
            text += f" {w['name']} runs {w['from']} to {w['to']}"
            text += (f"; race weekends draw about {w['interest_uplift']:g} times the usual interest in F1 "
                     f"(interest, not sales)." if w.get("interest_uplift") else ".")
        return text.strip()

    def list_actions(self, business_id: str, week: str = "week_1") -> dict:
        # recomputing is cheap and deterministic, and keeps the owner's done/skipped marks
        return self.generate_actions(business_id, week)

    def get_action(self, action_id: str) -> dict:
        a = self.store.get_action(action_id)
        if not a:
            raise ApiError(404, "not_found", f"action {action_id} not found")
        return a

    def update_action(self, action_id: str, status: Optional[str], note: Optional[str]) -> dict:
        a = self.get_action(action_id)
        if status not in (None, "todo", "done", "skipped"):
            raise ApiError(422, "invalid_request", "status must be todo, done or skipped")
        if status:
            a["status"] = status
        if note is not None:
            a["note"] = note
        a["updated_at"] = utcnow()
        self.store.put_action(a)
        return a

    def action_draft(self, action_id: str, channel: Optional[str]) -> dict:
        a = self.get_action(action_id)
        inp = self.inputs(a["business_id"], a["week"])
        channel = channel or (a["draft_channels"][0] if a["draft_channels"] else "whatsapp")
        partner = next((p for p in inp["partners"]["partners"] if p["partner_id"] == a.get("partner_id")), None)
        try:
            return drafts.action_draft(a, inp["business"], channel, inp["windows"], partner)
        except drafts.DraftError as e:
            raise ApiError(409 if e.code == "no_draft" else 422, e.code, str(e)) from e

    # ------------------------------------------------------- reach partners

    def reach_partners(self, business_id: str, week: str = "week_1") -> dict:
        inp = self.inputs(business_id, week)
        doc = inp["partners"]
        doc["week"] = week
        return doc
