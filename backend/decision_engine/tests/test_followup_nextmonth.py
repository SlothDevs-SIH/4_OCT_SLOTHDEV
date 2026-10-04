import json

from backend.decision_engine import explain, followup as fu
from backend.decision_engine.clients import DataClient
from backend.decision_engine.config import Settings
from backend.decision_engine.llm import providers
from backend.decision_engine.llm.cache import LLMCache
from backend.decision_engine.llm.synthesize import Synthesizer
from backend.decision_engine.llm.validator import validate_answer, validate_explanation
from backend.decision_engine.service import Engine

API = "/api/v1"
BB, HB = "biz_boxbox", "biz_homebaker"


def week1_actions(client, biz=BB):
    return client.post(f"{API}/businesses/{biz}/actions/generate?week=week_1").json()["actions"]


# ---------------------------------------------------------------- follow-up


def test_week_2_followup_box_box(client):
    acts = week1_actions(client)
    ids = [a["action_id"] for a in acts]
    body = {"actions_done": ids[:2], "actions_skipped": ids[2:], "partner_results": [{"partner_id": "rp_bb_3", "stranger_leads": 3}]}
    f = client.post(f"{API}/businesses/{BB}/followup?week=week_2", json=body).json()
    assert f["main_measure"]["stranger_orders"] == {"previous": 1, "current": 3, "change": 2}
    reviews = {r["action_key"]: r for r in f["reviews"]}
    collab = reviews["reach_partner_collab"]
    assert collab["fidelity"]["done"] and collab["effectiveness"] == "reached_target" and collab["decision"] == "double_down"
    assert "cannot be split" in collab["attribution_note"]                       # two done actions, one number
    assert reviews["reach_community_share"]["effectiveness"] == "not_judged"     # fidelity kept apart
    assert f["observational"] is True and f["actions_skipped"] == ids[2:]
    nxt = {a["action_key"]: a for a in f["next_actions"]}
    assert nxt["reach_partner_collab"]["score_parts"]["follow_up_bonus"] == 10
    assert "United States Grand Prix" in nxt["reach_demand_window_drop"]["title"]


def test_partner_results_feed_the_ranking(client):
    acts = week1_actions(client)
    client.post(f"{API}/businesses/{BB}/followup?week=week_2",
                json={"actions_done": [acts[0]["action_id"]], "partner_results": [{"partner_id": "rp_bb_3", "stranger_leads": 5}]})
    p = client.get(f"{API}/businesses/{BB}/reach-partners?week=week_2").json()["partners"][0]
    assert p["partner_id"] == "rp_bb_3" and p["past_stranger_leads"] == [5] and p["score_parts"]["past_results"] == 1.0


def test_bottleneck_switch_is_an_adjustment(client):
    for w in ("week_1", "week_2"):
        client.post(f"{API}/businesses/{HB}/actions/generate?week={w}")
    f = client.post(f"{API}/businesses/{HB}/followup?week=week_3").json()
    assert f["bottleneck"] == {"previous": "reach", "current": "capacity", "changed": True}
    assert f["adjustments"][0].startswith("The main bottleneck moved from reach to capacity")
    assert {a["bottleneck"] for a in f["next_actions"]} == {"capacity"}


def test_drop_what_did_not_move():
    action = {"action_id": "a", "action_key": "k", "title": "T", "status": "done",
              "target": {"fact_id": "f_x", "value": 5, "text": ""}}
    prev = {"f_x": {"value": 3, "direction": "up"}}
    assert fu.review_action(action, prev, {"f_x": {"value": 3, "direction": "up"}})["decision"] == "drop"
    assert fu.review_action(action, prev, {"f_x": {"value": 4, "direction": "up"}})["decision"] == "keep"
    assert fu.review_action(action, prev, {"f_x": {"value": 2, "direction": "up"}})["effectiveness"] == "worse"
    assert fu.review_action(dict(action, target={"fact_id": "f_x", "value": 1.0}), {"f_x": {"value": 2, "direction": "down"}},
                            {"f_x": {"value": 1.0, "direction": "down"}})["decision"] == "double_down"


def test_dropped_action_is_not_offered_again(engine):
    engine.generate_actions(BB, "week_1")
    prefs = {"boost": [], "exclude": ["reach_partner_collab"]}
    doc = engine.generate_actions(BB, "week_2", prefs)
    assert "reach_partner_collab" not in [a["action_key"] for a in doc["actions"]]
    assert any(b["action_key"] == "reach_partner_collab" and "Dropped" in b["reason"] for b in doc["blocked"])


def test_four_week_arc(client):
    for wk in ("week_2", "week_3", "week_4"):
        prev = f"week_{int(wk[-1]) - 1}"
        acts = client.get(f"{API}/businesses/{BB}/actions?week={prev}").json()["actions"]
        client.post(f"{API}/businesses/{BB}/followup?week={wk}", json={"actions_done": [a["action_id"] for a in acts]})
    f = client.get(f"{API}/businesses/{BB}/followups").json()["followups"]
    assert [x["week"] for x in f] == ["week_2", "week_3", "week_4"]
    arc = f[-1]["four_week_arc"]
    assert arc["stranger_orders"] == {"first": 1, "last": 6} and arc["worked"] and arc["observational"]


def test_followup_rejects_week_1_and_foreign_ids(client):
    assert client.post(f"{API}/businesses/{BB}/followup?week=week_1").status_code == 422
    r = client.post(f"{API}/businesses/{BB}/followup?week=week_2", json={"actions_done": ["act_nope"]})
    assert r.status_code == 422


# ---------------------------------------------------------------- next month


def test_next_month_box_box(client):
    n = client.get(f"{API}/businesses/{BB}/next-month").json()
    assert n["estimate"] is True and n["orders"] == {"low": 68, "expected": 80, "high": 92}
    assert n["limiting_bottleneck"] == "reach" and not n["limited_by_capacity"]
    assert [w["name"] for w in n["demand_windows"]][:2] == ["Mexico City Grand Prix", "Brazilian Grand Prix"]
    assert "This is an estimate" in n["text"]


def test_next_month_baker_is_capped_by_capacity(client):
    n = client.get(f"{API}/businesses/{HB}/next-month").json()
    # 20 a week x 30/7 days = 86 < 105 expected
    assert n["capacity_month"] == 86 and n["limited_by_capacity"] and n["limiting_bottleneck"] == "capacity"
    assert n["primary_bottleneck"] == "reach" and "Diwali" in n["text"]


def test_next_month_without_projection(tmp_path):
    class NoProjection(DataClient):
        def get_projection(self, *a, **k):
            from backend.decision_engine.clients import DataSourceUnavailable
            raise DataSourceUnavailable("not built")
    eng = Engine(settings=Settings(llm_cache_only=True, llm_cache_dir=tmp_path), data=NoProjection("fixture"))
    n = eng.next_month(BB)
    assert n["status"] == "no_projection" and "not enough history" in n["explanation"]["text"]


# ---------------------------------------------------------------- explanations and chat


def test_fallback_explanations_pass_the_validator(engine):
    for biz in (BB, HB):
        for w in ("week_1", "week_3"):
            inp = engine.inputs(biz, w)
            d = engine.diagnosis(biz, w, inp)
            packet = explain.diagnosis_packet(d, inp["business"], inp["facts"])
            out = explain.diagnosis_fallback(d)
            assert validate_explanation(out, packet) == [], (biz, w)
            assert d["explanation"]["llm"]["used"] is False


class Hallucinator(providers.Provider):
    name, model = "fake", "fake-1"

    def complete(self, system, user):
        return json.dumps({"summary": "Run Instagram ads and you will get 40 more orders from strangers next week.",
                           "evidence_ids": ["f_stranger_share"]})


def test_bad_llm_explanation_never_reaches_the_owner(tmp_path):
    s = Settings(llm_cache_dir=tmp_path)
    eng = Engine(settings=s, data=DataClient("fixture"),
                 synthesizer=Synthesizer(s, provider=Hallucinator(), cache=LLMCache(tmp_path)))
    e = eng.diagnosis(BB)["explanation"]
    assert "Instagram ads" not in e["text"] and e["llm"]["fallback"] is True
    errors = " ".join(e["llm"]["validator"]["errors"])
    assert "numbers not in the evidence packet" in errors and "paid ads" in errors


def test_chat_cites_facts(client):
    a = client.post(f"{API}/businesses/{BB}/chat", json={"question": "How many orders came from strangers?"}).json()
    assert "f_stranger_share" in a["citations"] and "8.8%" in a["answer"]
    packet = {"facts": [{"fact_id": c} for c in a["citations"]]}
    off = client.post(f"{API}/businesses/{BB}/chat", json={"question": "What's the weather?"}).json()
    assert off["citations"] == [] and "not in your data" in off["answer"]
    assert client.post(f"{API}/businesses/{BB}/chat", json={"question": " "}).status_code == 422


def test_chat_fallback_passes_validator(engine):
    from backend.decision_engine import chat
    facts = engine.data.get_facts(BB, "week_1")["facts"]
    for q in ("are my margins ok", "is dispatch slow", "do people come back", "strangers"):
        rel = chat.retrieve(q, facts)
        out = {"answer": " ".join(chat.describe(f) for f in rel), "citations": [f["fact_id"] for f in rel]}
        assert validate_answer(out, {"facts": rel}) == [], q
