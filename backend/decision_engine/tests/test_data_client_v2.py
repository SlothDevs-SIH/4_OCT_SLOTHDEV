"""Integration step 1: decision_engine reads data_engine's contract v2 output the same way from fixtures, in-process calls and HTTP."""
import socket
import threading
import time

import pytest
import uvicorn

from backend.common.fixtures import FIXTURES_DIR
from backend.data_engine.main import app
from backend.decision_engine.clients import DataClientV2, DataNotFound, DataSourceUnavailable

BIZ = {"boxbox": "biz_boxbox", "homebaker": "biz_homebaker"}


@pytest.fixture(scope="module")
def server():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    t = threading.Thread(target=srv.run, daemon=True)
    t.start()
    for _ in range(100):
        if srv.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    srv.should_exit = True
    t.join(5)


def clients(server):
    return {"fixture": DataClientV2(source="fixture"), "local": DataClientV2(source="local"), "http": DataClientV2(source="http", base_url=server)}


# ---------------------------------------------------------------- the three sources agree
@pytest.mark.parametrize("key", ["boxbox", "homebaker"])
@pytest.mark.parametrize("week", [1, 2, 3, 4])
def test_fixture_local_and_http_return_the_same_data(server, key, week):
    cs = clients(server)
    bid = BIZ[key]
    for name in ("local", "http"):
        cs[name].load_demo(key, week)
    for method, args in (("get_facts", ()), ("get_leads", ()), ("get_projection", ())):
        results = {n: getattr(c, method)(bid, *args, week=week) for n, c in cs.items()}
        assert results["fixture"] == results["local"] == results["http"], f"{method} differs for {key} week {week}"
    business = {n: c.get_business(bid, week=week) for n, c in cs.items()}
    assert business["fixture"] == business["local"] == business["http"]


def test_market_context_and_quality_agree(server):
    cs = clients(server)
    for n in ("local", "http"):
        cs[n].load_demo("boxbox", 1)
    for feed in ("f1_calendar", "india_festivals"):
        got = {n: c.get_market_context("2026-10-05", "2026-12-31", feed=feed) for n, c in cs.items()}
        assert got["fixture"] == got["local"] == got["http"]
    q = {n: c.get_data_quality("biz_boxbox") for n, c in cs.items() if n != "http"}
    assert q["fixture"]["overall"]["badge"] == q["local"]["overall"]["badge"]
    assert cs["http"].get_data_quality("biz_boxbox")["overall"]["badge"] == q["local"]["overall"]["badge"]


# ---------------------------------------------------------------- fixture mode on its own
def test_fixture_defaults_and_filters():
    c = DataClientV2(source="fixture")
    facts = c.get_facts("biz_boxbox")
    assert len(facts) == 23 and facts[0]["snapshot"] == "week_1"
    reach = c.get_facts("biz_boxbox", week="week_3", bottleneck="reach")
    assert reach and {f["bottleneck"] for f in reach} == {"reach"} and reach[0]["snapshot"] == "week_3"
    hot = c.get_leads("biz_boxbox", group="hot")
    assert hot and all(l["group"] == "hot" and l["score"] >= 50 for l in hot)
    p = c.get_projection("biz_homebaker", week=2)
    assert p["orders"]["low"] <= p["orders"]["expected"] <= p["orders"]["high"] and p["estimate"] is True
    assert c.get_business("biz_boxbox", week=4)["week"] == "week_4"
    assert c.get_market_context(feed="india_festivals")["feed"] == "india_festivals"


def test_fixture_results_are_copies():
    c = DataClientV2(source="fixture")
    c.get_facts("biz_boxbox")[0]["value"] = -1
    c.get_business("biz_boxbox")["name"] = "x"
    assert c.get_facts("biz_boxbox")[0]["value"] != -1 and c.get_business("biz_boxbox")["name"] == "Box Box"


def test_errors():
    c = DataClientV2(source="fixture")
    for call in (c.get_business, c.get_facts, c.get_leads, c.get_projection, c.get_data_quality):
        with pytest.raises(DataNotFound):
            call("biz_nope")
    with pytest.raises(ValueError):
        c.get_facts("biz_boxbox", week=5)
    with pytest.raises(ValueError):
        c.get_leads("biz_boxbox", group="lukewarm")
    with pytest.raises(ValueError):
        c.get_market_context(feed="weather")
    with pytest.raises(ValueError):
        c.load_demo("pizza")
    with pytest.raises(DataNotFound):
        DataClientV2(source="fixture", fixture_dir=FIXTURES_DIR / "does_not_exist").get_facts("biz_boxbox")
    with pytest.raises(DataSourceUnavailable):
        DataClientV2(source="http", base_url="http://127.0.0.1:9", timeout=0.5).get_facts("biz_boxbox")


def test_not_found_over_http_and_in_process(server):
    c = DataClientV2(source="http", base_url=server)
    with pytest.raises(DataNotFound):
        c.get_business("biz_not_loaded_anywhere")
    with pytest.raises(DataNotFound):
        DataClientV2(source="local").get_facts("biz_not_loaded_anywhere")


# ---------------------------------------------------------------- the stand-ins and the real output share the fields decision_engine reads
FACT_CORE = {"fact_id", "kpi", "dimension", "period", "value", "unit", "baseline", "delta_pct", "numerator", "denominator", "definition_version",
             "quality_flag", "snapshot", "source", "sample_size", "direction", "origin", "synthetic"}
LEAD_CORE = {"lead_id", "handle_ref", "source", "relationship", "signals", "asked_for", "last_message", "deliverable", "intents", "score", "group", "reasons",
             "disqualified_reason", "rank", "outcome", "last_activity", "synthetic"}
BUSINESS_CORE = {"business_id", "name", "case_study", "synthetic", "category", "city", "ships_to", "topics", "products", "channels", "payment", "order_link",
                 "team_size", "weekly_hours", "growth_minutes_per_week", "ad_budget_inr", "capacity_orders_per_week", "goal", "constraints", "context_feeds",
                 "reach_candidates", "provenance", "week"}
PROJECTION_CORE = {"business_id", "week", "synthetic", "month", "orders", "basis", "confidence", "estimate"}


@pytest.mark.parametrize("folder", ["v2", "v2_engine"])
@pytest.mark.parametrize("key", ["boxbox", "homebaker"])
def test_both_fixture_sets_have_the_core_fields(folder, key):
    c = DataClientV2(source="fixture", fixture_dir=FIXTURES_DIR / folder)
    bid = BIZ[key]
    for week in (1, 4):
        assert all(FACT_CORE <= set(f) for f in c.get_facts(bid, week))
        assert all(LEAD_CORE <= set(l) for l in c.get_leads(bid, week=week))
        assert PROJECTION_CORE <= set(c.get_projection(bid, week))
    assert BUSINESS_CORE <= set(c.get_business(bid))
    assert {"hot", "warm", "cold"} <= {l["group"] for l in c.get_leads(bid, week=1)} or key == "homebaker"
    ids = {f["fact_id"] for f in c.get_facts(bid)}
    assert {"f_stranger_orders_week", "f_stranger_share", "f_margin_pct", "f_repeat_customer_share", "f_capacity_utilisation", "f_orders_per_week"} <= ids


def test_the_main_measure_is_the_same_fact_in_both_sets():
    stand = DataClientV2(source="fixture", fixture_dir=FIXTURES_DIR / "v2")
    real = DataClientV2(source="fixture")
    for bid in BIZ.values():
        s = {f["fact_id"] for f in stand.get_facts(bid)}
        r = {f["fact_id"] for f in real.get_facts(bid)}
        assert s == r, (bid, s ^ r)
