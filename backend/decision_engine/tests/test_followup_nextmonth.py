"""Weekly follow-up, next month, explanations and chat on data_engine's real v2 output."""
import json

from backend.decision_engine import chat, explain, followup as fu
from backend.decision_engine.clients import DataClientV2, DataSourceUnavailable
from backend.decision_engine.config import Settings
from backend.decision_engine.llm import providers
from backend.decision_engine.llm.cache import LLMCache
from backend.decision_engine.llm.synthesize import Synthesizer
from backend.decision_engine.llm.validator import validate_answer, validate_explanation
from backend.decision_engine.service import Engine

API = "/api/v1"
BB, HB = "biz_boxbox", "biz_homebaker"


def actions(client, biz, week):
    return client.get(f"{API}/businesses/{biz}/actions?week={week}").json()["actions"]


def run_weeks(client, biz, skip_last=True):
    out = {}
    for n in (2, 3, 4):
        acts = actions(client, biz, f"week_{n - 1}")
        done = [a["action_id"] for a in (acts[:2] if skip_last else acts)]
        skipped = [a["action_id"] for a in acts if a["action_id"] not in done]
        out[n] = client.post(f"{API}/businesses/{biz}/followup?week=week_{n}",
                             json={"actions_done": done, "actions_skipped": skipped}).json()
    return out


# ---------------------------------------------------------------- follow-up


def test_box_box_follow_up(client):
    f = run_weeks(client, BB)
    assert f[2]["main_measure"]["stranger_orders"] == {"previous": 1.5, "current": 2.0, "change": 0.5}
    reviews = {r["action_key"]: r for r in f[2]["reviews"]}
    assert reviews["reach_partner_collab"]["effectiveness"] == "moving" and reviews["reach_partner_collab"]["decision"] == "keep"
    assert reviews["reach_community_share"]["effectiveness"] == "not_judged"   # fidelity kept apart
    assert f[3]["bottleneck"] == {"previous": "reach", "current": None, "changed": True}
    assert f[3]["adjustments"][0].startswith("Reach is back at your best weeks")
    assert f[3]["next_actions"]                                                 # keep doing what works
    arc = f[4]["four_week_arc"]
    assert arc["stranger_orders"] == {"first": 1.5, "last": 3.75} and arc["observational"]


def test_baker_demand_surge_is_not_blamed_on_the_action(client):
    f = run_weeks(client, HB, skip_last=False)
    w3 = {r["action_key"]: r for r in f[3]["reviews"]}
    pre = w3["cap_preorder_drop"]
    assert (pre["previous"], pre["current"]) == (7, 23)
    assert pre["effectiveness"] == "inconclusive" and pre["decision"] == "keep" and "Demand rose" in pre["adjustment"]


def test_review_rules():
    action = {"action_id": "a", "action_key": "k", "title": "T", "status": "done",
              "target": {"fact_id": "f_x", "value": 5, "text": ""}}
    prev = {"f_x": {"value": 3, "direction": "up", "kpi": "x"}}
    assert fu.review_action(action, prev, {"f_x": {"value": 3, "direction": "up", "kpi": "x"}})["decision"] == "drop"
    assert fu.review_action(action, prev, {"f_x": {"value": 4, "direction": "up", "kpi": "x"}})["decision"] == "keep"
    assert fu.review_action(action, prev, {"f_x": {"value": 5, "direction": "up", "kpi": "x"}})["decision"] == "double_down"


def test_partner_results_feed_the_ranking(client):
    acts = actions(client, BB, "week_1")
    client.post(f"{API}/businesses/{BB}/followup?week=week_2",
                json={"actions_done": [acts[0]["action_id"]], "partner_results": [{"partner_id": "rp_bb_3", "stranger_leads": 5}]})
    top = client.get(f"{API}/businesses/{BB}/reach-partners?week=week_2").json()["partners"][0]
    assert top["partner_id"] == "rp_bb_3" and top["past_stranger_leads"] == [5]


def test_dropped_action_is_not_offered_again(engine):
    engine.generate_actions(BB, "week_1")
    doc = engine.generate_actions(BB, "week_2", {"boost": [], "exclude": ["reach_partner_collab"]})
    assert "reach_partner_collab" not in [a["action_key"] for a in doc["actions"]]
    assert any(b["action_key"] == "reach_partner_collab" and "Dropped" in b["reason"] for b in doc["blocked"])


def test_followup_rejects_week_1_and_foreign_ids(client):
    assert client.post(f"{API}/businesses/{BB}/followup?week=week_1").status_code == 422
    assert client.post(f"{API}/businesses/{BB}/followup?week=week_2", json={"actions_done": ["act_nope"]}).status_code == 422


# ---------------------------------------------------------------- next month


def test_next_month_box_box(client):
    n = client.get(f"{API}/businesses/{BB}/next-month").json()
    assert n["estimate"] is True and n["month"] == {"from": "2026-10-05", "to": "2026-11-01"}
    assert n["orders"] == {"low": 46, "expected": 55, "high": 65} and not n["limited_by_capacity"]
    assert n["limiting_bottleneck"] == "reach"
    names = [w["name"] for w in n["demand_windows"]]
    assert names == ["Singapore Grand Prix", "United States Grand Prix", "Mexico City Grand Prix"]  # no duplicates


def test_next_month_baker_capacity_from_the_projection(client):
    n = client.get(f"{API}/businesses/{HB}/next-month").json()
    assert n["limited_by_capacity"] and n["limiting_bottleneck"] == "capacity"
    assert n["demand"]["expected"] == 59 and n["capacity"]["orders_per_month"] == 56
    assert "about 3 orders would be turned away" in n["text"]


def test_next_month_without_projection(tmp_path):
    class NoProjection(DataClientV2):
        def get_projection(self, *a, **k):
            raise DataSourceUnavailable("not built")
    eng = Engine(settings=Settings(llm_cache_only=True, llm_cache_dir=tmp_path), data=NoProjection("fixture"))
    assert eng.next_month(BB)["status"] == "no_projection"


# ---------------------------------------------------------------- explanations over real facts


def test_fallback_explanations_pass_the_validator(engine):
    for biz in (BB, HB):
        for w in ("week_1", "week_2", "week_3", "week_4"):
            inp = engine.inputs(biz, w)
            d = engine.diagnosis(biz, w, inp)
            if d["primary"] is None:
                continue
            packet = explain.diagnosis_packet(d, inp["business"], inp["facts"])
            assert validate_explanation(explain.diagnosis_fallback(d), packet) == [], (biz, w)
            assert d["explanation"]["llm"]["used"] is False


class Hallucinator(providers.Provider):
    name, model = "fake", "fake-1"

    def complete(self, system, user):
        return json.dumps({"summary": "Run Instagram ads and you will get 40 more orders from strangers next week.",
                           "evidence_ids": ["f_stranger_share"]})


def test_bad_llm_explanation_never_reaches_the_owner(tmp_path):
    s = Settings(llm_cache_dir=tmp_path)
    eng = Engine(settings=s, data=DataClientV2("fixture"),
                 synthesizer=Synthesizer(s, provider=Hallucinator(), cache=LLMCache(tmp_path)))
    e = eng.diagnosis(BB)["explanation"]
    assert "Instagram ads" not in e["text"] and e["llm"]["fallback"] is True
    errors = " ".join(e["llm"]["validator"]["errors"])
    assert "numbers not in the evidence packet" in errors and "paid ads" in errors


class GoodModel(providers.Provider):
    """Behaves like a well-behaved model: reuses the packet's numbers and ids only."""
    name, model = "fake", "fake-1"

    def complete(self, system, user):
        p = json.loads(user)
        f = p["facts"][0]
        return json.dumps({"summary": f"{p['primary'].replace('_', ' ').capitalize()} is the main gap this week. {f['claim']}",
                           "evidence_ids": [f["fact_id"]]})


def test_llm_explanation_over_real_facts_is_accepted_and_cached(tmp_path):
    s = Settings(llm_cache_dir=tmp_path)
    eng = Engine(settings=s, data=DataClientV2("fixture"),
                 synthesizer=Synthesizer(s, provider=GoodModel(), cache=LLMCache(tmp_path)))
    e = eng.diagnosis(HB)["explanation"]
    assert e["llm"]["used"] and not e["llm"]["fallback"] and "10 orders were turned away" in e["text"]
    offline = Engine(settings=Settings(llm_cache_only=True, llm_cache_dir=tmp_path), data=DataClientV2("fixture"))
    assert offline.diagnosis(HB)["explanation"]["llm"]["cached"] is True


# ---------------------------------------------------------------- chat


def test_chat_cites_real_facts(client):
    a = client.post(f"{API}/businesses/{BB}/chat", json={"question": "How many orders came from strangers?"}).json()
    assert "f_stranger_share" in a["citations"] and "9.5%" in a["answer"]
    off = client.post(f"{API}/businesses/{BB}/chat", json={"question": "What's the weather?"}).json()
    assert off["citations"] == [] and "not in your data" in off["answer"]


def test_chat_fallback_passes_validator(engine):
    facts = engine.facts_doc(HB, "week_1")["facts"]
    for q in ("are my margins ok", "is dispatch slow", "do people come back", "strangers", "turned away"):
        rel = chat.retrieve(q, facts)
        out = {"answer": " ".join(chat.describe(f) for f in rel), "citations": [f["fact_id"] for f in rel]}
        assert validate_answer(out, {"facts": rel}) == [], q
