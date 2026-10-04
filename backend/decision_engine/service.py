"""Engine: wires DataClient, the store and the LLM layer behind the API endpoints (contract v2 section 4)."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from backend.common.errors import ApiError
from backend.decision_engine import actions as advice
from backend.decision_engine import diagnosis as dx
from backend.decision_engine import chat as grounded_chat
from backend.decision_engine import drafts, explain, leadlist, nextmonth
from backend.decision_engine import followup as fu
from backend.decision_engine.clients import DataClientError, DataClientV2, DataNotFound, DataSourceUnavailable
from backend.decision_engine.clients.v2 import DEMO_BUSINESSES

WEEKS = ("week_1", "week_2", "week_3", "week_4")
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
    def __init__(self, settings: Optional[Settings] = None, data: Optional[DataClientV2] = None,
                 store: Optional[Store] = None, synthesizer: Optional[Synthesizer] = None):
        self.settings = settings or Settings.from_env()
        self.data = data or DataClientV2(source=self.settings.data_source, base_url=self.settings.data_engine_url)
        self.store = store or Store()
        self.synthesizer = synthesizer or Synthesizer(self.settings)

    def health(self) -> dict:
        return {"status": "ok", "module": "decision_engine", "contract": "v2", "data_source": self.data.source,
                "llm_provider": self.settings.llm_provider, "actions_in_library": len(advice.library()["actions"])}

    # ------------------------------------------------------------- inputs

    def _read(self, fn, business_id: str, *args, week: Optional[str] = None, **kwargs):
        """Call a data_engine read; outside fixture mode a demo business is loaded on first use."""
        try:
            return fn(business_id, *args, **kwargs)
        except DataNotFound:
            slug_ = slug(business_id)
            if self.data.source == "fixture" or slug_ not in DEMO_BUSINESSES:
                raise
            self.data.load_demo(slug_, int((week or "week_1")[-1]))
            return fn(business_id, *args, **kwargs)

    def facts_doc(self, business_id: str, week: str) -> dict:
        with data_errors():
            facts = self._read(self.data.get_facts, business_id, week, week=week)
        ends = [f["period"]["to"] for f in facts if f.get("period")]
        # the advisory week starts the day after the facts' window ends (2026-10-05 for week 1)
        as_of = (date.fromisoformat(max(ends)) + timedelta(days=1)).isoformat() if ends else None
        return {"business_id": business_id, "week": week, "as_of": as_of, "window_weeks": 4,
                "synthetic": any(f.get("synthetic") for f in facts), "facts": facts}

    def inputs(self, business_id: str, week: str) -> dict:
        """Everything one week's advice reads, fetched once (point in time: only data up to `week`)."""
        if week not in WEEKS:
            raise ApiError(422, "invalid_request", f"week must be one of {WEEKS}")
        with data_errors():
            business = self._read(self.data.get_business, business_id, week, week=week)
        facts_doc = self.facts_doc(business_id, week)
        as_of = facts_doc["as_of"] or date.today().isoformat()
        context = None
        for feed in business.get("context_feeds", []):
            try:
                context = self.data.get_market_context(as_of, None, feed=feed)
                break
            except (DataClientError, ValueError):
                continue  # a feed that is not built: no timing advice, and the gate says so
        facts = {f["fact_id"]: f for f in facts_doc["facts"]}
        customers = (facts.get("f_repeat_customer_share") or {}).get("denominator")
        try:
            leads = self._read(self.data.get_leads, business_id, None, week, week=week)
        except DataClientError:
            leads = []
        names = {p["name"] for p in business.get("products", [])}
        demand = {}
        for l in leads:
            name = (l.get("asked_for") or {}).get("product")
            if name in names:
                demand[name] = demand.get(name, 0) + 1
        asked = sorted(demand, key=lambda n: -demand[n])
        return {"business": business, "facts_doc": facts_doc, "facts": facts, "context": context, "as_of": as_of,
                "windows": advice.demand_windows(context, as_of),
                "partners": advice.rank_partners(business, self.store.partner_results_for(business_id)),
                "customers": customers, "leads": leads, "asked_products": asked}

    # ---------------------------------------------------------- diagnosis

    def diagnosis(self, business_id: str, week: str = "week_1", inputs: Optional[dict] = None) -> dict:
        inp = inputs or self.inputs(business_id, week)
        doc = dx.diagnose(inp["facts_doc"], lambda b: advice.actionable(b, inp["business"], inp))
        doc["explanation"] = explain.explain_diagnosis(doc, inp["business"], inp["facts"], self.synthesizer)
        doc["generated_at"] = utcnow()
        self.store.put_diagnosis(doc)
        return doc

    # ------------------------------------------------------------ actions

    def generate_actions(self, business_id: str, week: str = "week_1", prefs: Optional[dict] = None) -> dict:
        inp = self.inputs(business_id, week)
        if prefs is None:  # a recorded follow-up for this week keeps steering the advice
            prefs = (self.store.followups.get((business_id, week)) or {}).get("preferences")
        diag = self.diagnosis(business_id, week, inp)
        business = inp["business"]
        minutes = business.get("growth_minutes_per_week") or (business.get("weekly_hours", 0) * 60) // 4
        doc = {"business_id": business_id, "week": week, "as_of": inp["as_of"],
               "synthetic": business.get("synthetic", False), "bottleneck": diag["primary"],
               "minutes_available": minutes, "ranking": advice.library()["ranking"], "actions": [], "blocked": [],
               "risk_flags": [f for f in [advice.brand_risk(business)] if f]}
        target_bottleneck, doc["mode"] = diag["primary"], "fix"
        if diag["primary"] is None and diag["status"] == "no_clear_bottleneck":
            # nothing is off its best: keep up the actions behind last week's bottleneck (or the main measure)
            prev = self.store.get_diagnosis(business_id, f"week_{int(week[-1]) - 1}") if week != "week_1" else None
            target_bottleneck, doc["mode"] = (prev or {}).get("primary") or "reach", "maintain"
            doc["message"] = (f"{diag['message']} These actions keep up the "
                              f"{target_bottleneck.replace('_', ' ')} work that got you here.")
        if target_bottleneck is None:
            doc["message"] = diag["message"]
            self.store.drop_actions(business_id, week, keep=set())
            return doc
        doc["bottleneck"] = target_bottleneck
        primary = next(f for f in diag["bottlenecks"] if f["bottleneck"] == target_bottleneck)
        cands = advice.candidates(target_bottleneck, business, inp)
        if prefs:
            for c in cands:
                if c["action_key"] in prefs.get("exclude", []) and c["gate"]["eligible"]:
                    c["gate"] = dict(c["gate"], eligible=False,
                                     blocked_reason="Dropped after last week's follow-up: the number did not move.")
                elif c["action_key"] in prefs.get("boost", []):
                    c["score"] = round(c["score"] + 10, 1)
                    c["parts"] = dict(c["parts"], follow_up_bonus=10)
            cands.sort(key=lambda c: (not c["gate"]["eligible"], -c["score"], c["effort_min"]))
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
                "partner_id": c["partner_id"], "product_name": c["product_name"], "draft_channels": c["draft_channels"],
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
        if primary.get("where") and primary.get("passed"):
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

    # ----------------------------------------------------------- lead list

    def lead_list(self, business_id: str, week: str = "week_1") -> dict:
        inp = self.inputs(business_id, week)
        with data_errors():
            leads = {"business_id": business_id, "week": week, "as_of": inp["as_of"],
                     "synthetic": inp["business"].get("synthetic", False),
                     "leads": self._read(self.data.get_leads, business_id, None, week, week=week)}
        week_actions = self.store.actions_for(business_id, week) or self.generate_actions(business_id, week)["actions"]
        return leadlist.build(leads, inp["business"], week_actions, inp["windows"],
                              self.store.warm_contacted(business_id))

    def mark_contacted(self, business_id: str, lead_id: str, reason: str) -> dict:
        if not reason:
            raise ApiError(422, "invalid_request", "reason is required")
        self.store.mark_warm_contacted(business_id, lead_id, reason)
        return {"business_id": business_id, "lead_id": lead_id, "reason": reason, "contacted": True}

    # ----------------------------------------------------------- follow-up

    def followup(self, business_id: str, week: str, done: Optional[list] = None, skipped: Optional[list] = None,
                 partner_results: Optional[list] = None) -> dict:
        if week not in WEEKS or week == "week_1":
            raise ApiError(422, "invalid_request", "the follow-up compares a week with the one before: use week_2 to week_4")
        prev = f"week_{int(week[-1]) - 1}"
        prev_actions = self.store.actions_for(business_id, prev) or self.generate_actions(business_id, prev)["actions"]
        ids = {a["action_id"] for a in prev_actions}
        unknown = [i for i in (done or []) + (skipped or []) if i not in ids]
        if unknown:
            raise ApiError(422, "invalid_request", f"not {prev} actions: {unknown}")
        for aid in done or []:
            self.update_action(aid, "done", None)
        for aid in skipped or []:
            self.update_action(aid, "skipped", None)
        for r in partner_results or []:
            self.store.add_partner_result(business_id, r["partner_id"], int(r["stranger_leads"]))
        prev_actions = self.store.actions_for(business_id, prev)
        if self.data.source != "fixture" and slug(business_id) in DEMO_BUSINESSES:
            with data_errors():
                self.data.load_demo(slug(business_id), int(week[-1]))  # advance the replay to this week
        prev_facts, cur_facts = self.facts_doc(business_id, prev), self.facts_doc(business_id, week)
        prev_diag = self.store.get_diagnosis(business_id, prev) or self.diagnosis(business_id, prev)
        cur_diag = self.diagnosis(business_id, week)
        doc = fu.build(business_id, week, prev, prev_actions, prev_facts, cur_facts, prev_diag["primary"],
                       cur_diag["primary"], partner_results or [])
        self.store.put_followup(doc)
        doc["next_actions"] = self.generate_actions(business_id, week, doc["preferences"])["actions"]
        if week == "week_4":
            first = self.facts_doc(business_id, "week_1")
            doc["four_week_arc"] = fu.arc(business_id, first, cur_facts, self.store.followups_for(business_id))
        doc["generated_at"] = utcnow()
        self.store.put_followup(doc)
        return doc

    def followups(self, business_id: str) -> dict:
        with data_errors():
            self._read(self.data.get_business, business_id)
        return {"business_id": business_id, "followups": self.store.followups_for(business_id)}

    # ---------------------------------------------------------- next month

    def next_month(self, business_id: str, week: str = "week_1") -> dict:
        inp = self.inputs(business_id, week)
        diag = self.store.get_diagnosis(business_id, week) or self.diagnosis(business_id, week, inp)
        try:
            projection = self._read(self.data.get_projection, business_id, week, week=week)
        except DataClientError:
            projection = None
        doc = nextmonth.build(projection, diag, inp["business"], inp["context"])
        doc["explanation"] = explain.explain_next_month(doc, inp["business"], diag, inp["facts"], self.synthesizer)
        return doc

    # ---------------------------------------------------------------- chat

    def chat(self, business_id: str, question: str, week: str = "week_1") -> dict:
        question = (question or "").strip()
        if not question:
            raise ApiError(422, "invalid_request", "question is required")
        inp = self.inputs(business_id, week)
        return grounded_chat.answer(question[:500], inp["business"], inp["facts_doc"], self.synthesizer)
