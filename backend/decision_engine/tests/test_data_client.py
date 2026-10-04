import json
import sys
import threading
import types
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import pytest

from backend.common.fixtures import load_fixture
from backend.decision_engine.clients import DataClient, DataNotFound, DataSourceUnavailable

BIZ = "biz_aarohi_skin"


# ---------------------------------------------------------------- fixture


def test_default_source_is_fixture(monkeypatch):
    monkeypatch.delenv("DATA_SOURCE", raising=False)
    assert DataClient().source == "fixture"


def test_unknown_source_rejected():
    with pytest.raises(ValueError):
        DataClient(source="carrier_pigeon")


def test_fixture_context_and_quality():
    c = DataClient(source="fixture")
    ctx = c.get_context(BIZ)
    assert ctx["synthetic"] is True
    assert "increase_total_ad_spend" in ctx["constraints"]["forbidden_actions"]
    assert c.get_data_quality(BIZ)["overall"]["confidence"] == 0.82


def test_fixture_unknown_business():
    c = DataClient(source="fixture")
    for call in (c.get_context, c.get_kpi_facts, c.get_lead_scores, c.get_data_quality, c.get_kpi_series):
        with pytest.raises(DataNotFound):
            call("biz_nope")


def test_fixture_kpi_facts_and_snapshot():
    c = DataClient(source="fixture")
    facts = {f["fact_id"]: f for f in c.get_kpi_facts(BIZ)}
    assert facts["f_cac_instagram"]["value"] == 612.0
    day7 = {f["fact_id"]: f for f in c.get_kpi_facts(BIZ, snapshot="day7")}
    assert day7["f_hot_lead_wins"]["period"]["from"] == "2026-10-05"
    assert c.get_kpi_facts(BIZ, from_date="2026-10-04") == []
    with pytest.raises(ValueError):
        c.get_kpi_facts(BIZ, snapshot="day30")


def test_fixture_lead_limit_keeps_rank_order():
    leads = DataClient(source="fixture").get_lead_scores(BIZ, limit=3)["leads"]
    assert [l["lead_id"] for l in leads] == ["lead_0412", "lead_0388", "lead_0397"]


def test_fixture_series_filters():
    s = DataClient(source="fixture").get_kpi_series(BIZ, from_date="2026-09-27", channel="instagram")
    assert len(s["series"]) == 7
    assert sum(r["spend"] for r in s["series"]) == 36720


def test_fixture_results_are_copies():
    c = DataClient(source="fixture")
    c.get_context(BIZ)["name"] = "changed"
    assert c.get_context(BIZ)["name"] == "Aarohi Skin"


# ------------------------------------------------------------------- http


@pytest.fixture
def http_server():
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            url = urlparse(self.path)
            calls.append((url.path, parse_qs(url.query)))
            routes = {
                f"/api/v1/businesses/{BIZ}": load_fixture("business_context"),
                f"/api/v1/businesses/{BIZ}/kpis": {"facts": load_fixture("kpi_facts")},
                f"/api/v1/businesses/{BIZ}/leads/queue": load_fixture("lead_scores"),
                f"/api/v1/businesses/{BIZ}/data-quality": load_fixture("data_quality"),
            }
            body = routes.get(url.path)
            status = 200 if body is not None else 404
            payload = json.dumps(body or {"error": {"code": "not_found", "message": "nope"}}).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}", calls
    server.shutdown()


def test_http_source(http_server):
    url, calls = http_server
    c = DataClient(source="http", base_url=url)
    assert c.get_context(BIZ)["business_id"] == BIZ
    assert any(f["fact_id"] == "f_cac_instagram" for f in c.get_kpi_facts(BIZ, from_date="2026-09-27"))
    assert calls[-1][1] == {"from": ["2026-09-27"], "snapshot": ["baseline"]}
    c.get_lead_scores(BIZ, limit=5)
    assert calls[-1][1] == {"limit": ["5"]}
    assert c.get_data_quality(BIZ)["business_id"] == BIZ
    with pytest.raises(DataNotFound):
        c.get_context("biz_nope")


def test_http_unreachable():
    c = DataClient(source="http", base_url="http://127.0.0.1:9", timeout=1)
    with pytest.raises(DataSourceUnavailable):
        c.get_context(BIZ)


# ------------------------------------------------------------------ local


@pytest.fixture
def fake_public(monkeypatch):
    mod = types.ModuleType("backend.data_engine.public")
    mod.get_context = lambda business_id: load_fixture("business_context") if business_id == BIZ else None
    mod.get_kpi_facts = lambda business_id, from_date, to_date: load_fixture("kpi_facts")
    mod.get_lead_scores = lambda business_id, limit: load_fixture("lead_scores")
    mod.get_data_quality = lambda business_id: load_fixture("data_quality")
    monkeypatch.setitem(sys.modules, "backend.data_engine", types.ModuleType("backend.data_engine"))
    monkeypatch.setitem(sys.modules, "backend.data_engine.public", mod)
    return mod


def test_local_source(fake_public):
    c = DataClient(source="local")
    assert c.get_context(BIZ)["business_id"] == BIZ
    assert len(c.get_kpi_facts(BIZ)) == len(load_fixture("kpi_facts"))
    with pytest.raises(DataNotFound):
        c.get_context("biz_nope")
    # public.get_kpi_facts has no `snapshot` parameter and no get_kpi_series yet
    with pytest.raises(DataSourceUnavailable):
        c.get_kpi_facts(BIZ, snapshot="day7")
    with pytest.raises(DataSourceUnavailable):
        c.get_kpi_series(BIZ)


def test_local_passes_snapshot_when_supported(fake_public):
    seen = {}

    def get_kpi_facts(business_id, from_date, to_date, snapshot="baseline"):
        seen["snapshot"] = snapshot
        return []

    fake_public.get_kpi_facts = get_kpi_facts
    DataClient(source="local").get_kpi_facts(BIZ, snapshot="day7")
    assert seen["snapshot"] == "day7"


def test_local_without_data_engine(monkeypatch):
    monkeypatch.setitem(sys.modules, "backend.data_engine.public", None)
    with pytest.raises(DataSourceUnavailable):
        DataClient(source="local").get_context(BIZ)
