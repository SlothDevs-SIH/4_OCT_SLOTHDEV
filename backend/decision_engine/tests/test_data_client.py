import json
import sys
import threading
import types
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import pytest

from backend.common.fixtures import load_fixture
from backend.decision_engine.clients import DataClient, DataNotFound, DataSourceUnavailable

BB, HB = "biz_boxbox", "biz_homebaker"


# ---------------------------------------------------------------- fixture


def test_default_source_is_fixture(monkeypatch):
    monkeypatch.delenv("DATA_SOURCE", raising=False)
    assert DataClient().source == "fixture"


def test_unknown_source_rejected():
    with pytest.raises(ValueError):
        DataClient(source="carrier_pigeon")


def test_fixture_context_both_businesses():
    c = DataClient("fixture")
    assert c.get_context(BB)["case_study"] == "Box Box" and c.get_context(BB)["ad_budget_inr"] == 0
    assert c.get_context(HB)["context_feeds"] == ["india_festivals"]


def test_fixture_facts_are_point_in_time():
    c = DataClient("fixture")
    w1, w2 = c.get_facts(BB, "week_1"), c.get_facts(BB, "week_2")
    assert w1["as_of"] == "2026-10-04" and w2["as_of"] == "2026-10-11"
    assert all(f["period"]["to"] <= w1["as_of"] for f in w1["facts"])
    with pytest.raises(ValueError):
        c.get_facts(BB, "week_9")


def test_fixture_leads_group_filter():
    hot = DataClient("fixture").get_leads(BB, "week_1", group="hot")["leads"]
    assert hot and all(l["group"] == "hot" for l in hot)


def test_fixture_unknown_business():
    c = DataClient("fixture")
    for call in (c.get_context, c.get_facts, c.get_leads, c.get_projection, c.get_data_quality):
        with pytest.raises(DataNotFound):
            call("biz_nope")


def test_fixture_market_context():
    c = DataClient("fixture")
    f1 = c.get_market_context("f1_calendar")
    assert any(r["name"] == "United States Grand Prix" for r in f1["race_weekends"])
    assert c.get_market_context("india_festivals")["events"][0]["name"] == "Diwali"
    with pytest.raises(DataSourceUnavailable):
        c.get_market_context("moon_calendar")


def test_fixture_results_are_copies():
    c = DataClient("fixture")
    c.get_context(BB)["name"] = "changed"
    assert c.get_context(BB)["name"] == "Box Box"


# ------------------------------------------------------------------- http


@pytest.fixture
def http_server():
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            url = urlparse(self.path)
            calls.append((url.path, parse_qs(url.query)))
            routes = {
                f"/api/v1/businesses/{BB}": load_fixture("v2/boxbox/business"),
                f"/api/v1/businesses/{BB}/facts": load_fixture("v2/boxbox/facts_week_2")["facts"],  # bare list
                f"/api/v1/businesses/{BB}/leads": load_fixture("v2/boxbox/leads_week_1"),
                f"/api/v1/businesses/{BB}/projection": load_fixture("v2/boxbox/projection_week_1"),
                "/api/v1/market-context": load_fixture("v2/market_context/f1_calendar"),
            }
            body = routes.get(url.path)
            self.send_response(200 if body is not None else 404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(body or {"error": {"code": "not_found", "message": "nope"}}).encode())

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}", calls
    server.shutdown()


def test_http_source(http_server):
    url, calls = http_server
    c = DataClient("http", base_url=url)
    assert c.get_context(BB)["business_id"] == BB
    facts = c.get_facts(BB, "week_2")
    assert facts["week"] == "week_2" and len(facts["facts"]) > 10  # a bare list is wrapped
    assert calls[-1][1] == {"week": ["week_2"]}
    c.get_leads(BB, "week_1", group="hot")
    assert calls[-1][1] == {"week": ["week_1"], "group": ["hot"]}
    assert c.get_projection(BB)["estimate"] is True
    assert c.get_market_context("f1_calendar", "2026-10-01")["season"] == 2026
    assert calls[-1][1] == {"from": ["2026-10-01"], "feed": ["f1_calendar"]}
    with pytest.raises(DataNotFound):
        c.get_context("biz_nope")


def test_http_unreachable():
    with pytest.raises(DataSourceUnavailable):
        DataClient("http", base_url="http://127.0.0.1:9", timeout=1).get_context(BB)


# ------------------------------------------------------------------ local


@pytest.fixture
def fake_public(monkeypatch):
    mod = types.ModuleType("backend.data_engine.public")
    mod.get_context = lambda b: load_fixture("v2/boxbox/business") if b == BB else None
    mod.get_facts = lambda b, week: load_fixture(f"v2/boxbox/facts_{week}")["facts"]
    mod.get_market_context = lambda from_date=None, to_date=None: load_fixture("v2/market_context/f1_calendar")
    monkeypatch.setitem(sys.modules, "backend.data_engine", types.ModuleType("backend.data_engine"))
    monkeypatch.setitem(sys.modules, "backend.data_engine.public", mod)
    return mod


def test_local_source(fake_public):
    c = DataClient("local")
    assert c.get_context(BB)["business_id"] == BB
    assert c.get_facts(BB, "week_1")["facts"][0]["snapshot"] == "week_1"
    assert c.get_market_context("f1_calendar")["season"] == 2026
    with pytest.raises(DataNotFound):
        c.get_context("biz_nope")
    with pytest.raises(DataSourceUnavailable):      # v2 function not built in data_engine yet
        c.get_projection(BB)
    with pytest.raises(DataSourceUnavailable):      # festival calendar not built yet
        c.get_market_context("india_festivals")


def test_local_without_data_engine(monkeypatch):
    monkeypatch.setitem(sys.modules, "backend.data_engine.public", None)
    with pytest.raises(DataSourceUnavailable):
        DataClient("local").get_context(BB)
