"""Integration stage 2: the whole advisor loop through the gateway, both backends together, on the real generated data.

load week 1 -> diagnose -> advise (1 to 3 actions) -> lead list with drafts -> load week 2 -> follow up -> ... -> week 4 -> next month -> chat
"""
import socket
import threading
import time

import pytest
import uvicorn
from fastapi.testclient import TestClient

from backend.data_engine import public
from backend.data_engine.main import app as data_app
from backend.decision_engine.config import Settings
from backend.decision_engine.main import get_engine
from backend.decision_engine.service import Engine
from backend.decision_engine.store import Store
from backend.gateway.main import app

A = "/api/v1"
EXPECTED = {"boxbox": "reach", "homebaker": "capacity"}


def _engine(tmp_path, source="local", url="http://localhost:8001"):
    s = Settings(data_source=source, data_engine_url=url, llm_provider="cache", llm_cache_only=True, llm_cache_dir=tmp_path / "llm")
    return Engine(settings=s, store=Store())


@pytest.fixture
def client(tmp_path):
    eng = _engine(tmp_path)                       # one engine for the whole test, so recorded actions persist between calls
    app.dependency_overrides[get_engine] = lambda: eng
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_the_gateway_serves_both_backends(client):
    h = client.get(f"{A}/health").json()
    assert h["mounted"] == ["backend.data_engine.main", "backend.decision_engine.main"]
    assert client.get(f"{A}/decision/health").json()["data_source"] == "local"
    assert client.get(f"{A}/data/health").status_code == 200


@pytest.mark.parametrize("key", ["boxbox", "homebaker"])
def test_week_1_diagnosis_advice_and_lead_list(client, key):
    bid = f"biz_{key}"
    assert client.post(f"{A}/demo/load?business={key}&week=1").status_code == 200
    d = client.get(f"{A}/businesses/{bid}/diagnosis?week=week_1").json()
    assert d["status"] == "ok" and d["primary"] == EXPECTED[key] and d["orders_in_window"] >= 20 and d["synthetic"] is True
    assert d["main_measure"]["fact_id"] == "f_stranger_orders_week" and len(d["runners_up"]) == 2 and d["rejected"]

    g = client.post(f"{A}/businesses/{bid}/actions/generate?week=week_1").json()
    acts = g["actions"]
    assert 1 <= len(acts) <= 3 and g["bottleneck"] == EXPECTED[key]
    assert sum(a["effort_min"] for a in acts) <= g["minutes_available"] and g["minutes_planned"] == sum(a["effort_min"] for a in acts)
    assert all(a["evidence_ids"] and a["why"] and a["target"] and a["due"] for a in acts)                # every action carries its evidence
    assert not any("paid_ads" in a["action_key"] for a in acts)                                          # no ad budget: never advised
    if key == "boxbox":
        assert any(b["action_key"] == "reach_paid_ads" for b in g["blocked"])
        assert all(any(f["flag"] == "brand_ip" for f in a["risk_flags"]) for a in acts)                  # F1, Ferrari, McLaren product names
    dr = client.get(f"{A}/actions/{acts[0]['action_id']}/draft").json()
    assert dr["status"] == "preview" and dr["auto_send"] is False and dr["text"]                          # never sent by the system
    assert client.get(f"{A}/businesses/{bid}/actions?week=week_1").json()["actions"][0]["action_id"] == acts[0]["action_id"]

    ll = client.get(f"{A}/businesses/{bid}/lead-list?week=week_1").json()
    mine = public.get_leads(bid, None, 1)
    for grp in ("hot", "warm", "cold", "disqualified"):
        assert ll["summary"][grp] == sum(1 for x in mine if x["group"] == grp) == len(ll[grp])          # the same leads backend 1 scored
    assert ll["hot"] and all(h["draft"] and h["score"] >= 50 for h in ll["hot"])
    assert all(isinstance(h["draft"], (str, dict)) for h in ll["hot"])
    rp = client.get(f"{A}/businesses/{bid}/reach-partners?week=week_1").json()
    assert rp["recommended"] and rp["synthetic"] is True


def test_the_four_week_loop_for_box_box(client):
    key, bid = "boxbox", "biz_boxbox"
    client.post(f"{A}/demo/load?business={key}&week=1")
    prev = client.post(f"{A}/businesses/{bid}/actions/generate?week=week_1").json()["actions"]
    seen = [client.get(f"{A}/businesses/{bid}/diagnosis?week=week_1").json()["main_measure"]["stranger_orders_per_week"]]
    for w in (2, 3, 4):
        assert client.post(f"{A}/demo/load?business={key}&week={w}").status_code == 200
        f = client.post(f"{A}/businesses/{bid}/followup?week=week_{w}", json={"actions_done": [a["action_id"] for a in prev]})
        assert f.status_code == 200, f.text
        f = f.json()
        sm = f["main_measure"]["stranger_orders"]
        assert sm["previous"] == seen[-1] and sm["current"] > sm["previous"]                              # the scripted replay: more strangers each week
        seen.append(sm["current"])
        assert f["observational"] is True and f["reviews"] and f["adjustments"] and f["compared_with"] == f"week_{w - 1}"
        prev = f["next_actions"]
        assert 1 <= len(prev) <= 3
        if w == 4:
            assert f["four_week_arc"]
    assert seen == [1.5, 2.0, 3.0, 3.75]
    assert len(client.get(f"{A}/businesses/{bid}/followups").json()["followups"]) == 3
    assert client.post(f"{A}/businesses/{bid}/followup?week=week_1", json={}).status_code == 422          # nothing to compare week 1 with


def test_skipped_actions_are_recorded_and_wrong_week_ids_rejected(client):
    bid = "biz_boxbox"
    client.post(f"{A}/demo/load?business=boxbox&week=1")
    acts = client.post(f"{A}/businesses/{bid}/actions/generate?week=week_1").json()["actions"]
    client.post(f"{A}/demo/load?business=boxbox&week=2")
    f = client.post(f"{A}/businesses/{bid}/followup?week=week_2", json={"actions_done": [acts[0]["action_id"]], "actions_skipped": [acts[1]["action_id"]]}).json()
    assert f["actions_done"] == [acts[0]["action_id"]] and f["actions_skipped"] == [acts[1]["action_id"]] and acts[2]["action_id"] in f["actions_open"]
    client.post(f"{A}/demo/load?business=boxbox&week=3")
    bad = client.post(f"{A}/businesses/{bid}/followup?week=week_3", json={"actions_done": [acts[0]["action_id"]]})
    assert bad.status_code == 422 and "not week_2 actions" in bad.json()["error"]["message"]


@pytest.mark.parametrize("key", ["boxbox", "homebaker"])
def test_next_month_and_chat_use_backend_1_numbers(client, key):
    bid = f"biz_{key}"
    client.post(f"{A}/demo/load?business={key}&week=4")
    nm = client.get(f"{A}/businesses/{bid}/next-month?week=week_4").json()
    proj = public.get_projection(bid, 4)
    assert nm["orders"] == proj["orders"] and nm["estimate"] is True and nm["month"] == proj["month"]      # explained, never recalculated
    if key == "homebaker":
        assert nm["demand"]["expected"] > nm["orders"]["expected"]                                         # capacity caps the month
    ch = client.post(f"{A}/businesses/{bid}/chat?week=week_4", json={"question": "How many orders came from strangers?"}).json()
    assert "[f_stranger_orders_week]" in ch["answer"]
    stranger = next(f for f in public.get_facts(bid, 4) if f["fact_id"] == "f_stranger_orders_week")
    assert f"{stranger['value']:g}" in ch["answer"]                                                         # the number is backend 1's number


def test_unknown_business_and_bad_week(client):
    assert client.get(f"{A}/businesses/biz_nope/diagnosis?week=week_1").status_code == 404
    assert client.get(f"{A}/businesses/biz_boxbox/diagnosis?week=week_9").status_code == 422


# ---------------------------------------------------------------- deployed layout: two services, decision_engine reads data_engine over HTTP
@pytest.fixture(scope="module")
def data_server():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    srv = uvicorn.Server(uvicorn.Config(data_app, host="127.0.0.1", port=port, log_level="warning"))
    t = threading.Thread(target=srv.run, daemon=True)
    t.start()
    for _ in range(100):
        if srv.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    srv.should_exit = True
    t.join(5)


def _provide(engine):
    return lambda: engine


def test_decision_engine_over_http_gives_the_same_answers(data_server, tmp_path):
    from backend.decision_engine.main import app as decision_app
    local = _engine(tmp_path / "a", "local")
    remote = _engine(tmp_path / "b", "http", data_server)
    out = {}
    for name, eng in (("local", local), ("http", remote)):
        decision_app.dependency_overrides[get_engine] = _provide(eng)
        c = TestClient(decision_app)
        assert c.get(f"{A}/decision/health").json()["data_source"] == name
        d = c.get(f"{A}/businesses/biz_homebaker/diagnosis?week=week_1").json()
        acts = c.post(f"{A}/businesses/biz_homebaker/actions/generate?week=week_1").json()["actions"]
        ll = c.get(f"{A}/businesses/biz_homebaker/lead-list?week=week_1").json()["summary"]
        nm = c.get(f"{A}/businesses/biz_homebaker/next-month?week=week_1").json()["orders"]
        out[name] = (d["primary"], d["runners_up"], [a["action_key"] for a in acts], ll, nm)
    decision_app.dependency_overrides.clear()
    assert out["local"] == out["http"] and out["http"][0] == "capacity"
