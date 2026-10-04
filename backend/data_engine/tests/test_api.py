from fastapi.testclient import TestClient

from backend.common.fixtures import load_fixture
from backend.data_engine import store
from backend.data_engine.main import app

client = TestClient(app)


def setup_function(_):
    store.load_demo("baseline")


def test_health_reports_stage():
    r = client.get("/api/v1/data/health")
    assert r.status_code == 200 and r.json()["service"] == "data_engine"


def test_demo_context_matches_the_contract_fixture():
    ctx = client.get("/api/v1/businesses/biz_aarohi_skin").json()
    fixture = load_fixture("business_context")
    for key, value in fixture.items():
        if key == "created_at":
            continue
        assert ctx[key] == value, key
    assert ctx["business_model"] == "hybrid" and ctx["synthetic"] is True


def test_demo_load_switches_phase_and_reports_counts():
    r = client.post("/api/v1/demo/load?phase=day7")
    assert r.status_code == 200
    body = r.json()
    assert body["demo_load"]["phase"] == "day7" and body["demo_load"]["synthetic"] is True
    assert body["demo_load"]["counts"]["orders"] > 3000
    assert client.get("/api/v1/businesses/biz_aarohi_skin").json()["data_phase"] == "day7"
    assert client.post("/api/v1/demo/load?phase=baseline").json()["demo_load"]["phase"] == "baseline"


def test_demo_load_rejects_unknown_phase():
    assert client.post("/api/v1/demo/load?phase=nope").status_code == 422


def test_data_summary_matches_the_anchors():
    s = client.get("/api/v1/businesses/biz_aarohi_skin/data-summary").json()
    assert s["current_week"]["orders"] == 154 and s["current_week"]["revenue"] == 135560 and s["synthetic"] is True


def test_onboarding_creates_a_d2c_business():
    payload = {"name": "Kesar Tea Co", "business_model": "d2c", "category": "D2C tea", "city": "Jaipur",
               "goal": {"statement": "Grow repeat purchases", "primary_kpi": "repeat_rate"},
               "constraints": {"weekly_ad_budget_inr": 20000, "forbidden_actions": ["increase_total_ad_spend"]}}
    r = client.post("/api/v1/businesses", json=payload)
    assert r.status_code == 201, r.text
    biz = r.json()
    assert biz["business_id"] == "biz_kesar_tea_co" and biz["synthetic"] is False and "instagram" in biz["channels"]
    assert client.get(f"/api/v1/businesses/{biz['business_id']}").json()["goal"]["primary_kpi"] == "repeat_rate"
    assert client.post("/api/v1/businesses", json=payload).status_code == 409


def test_onboarding_validation():
    bad = {"name": "X", "goal": {"statement": "ok goal"}}
    assert client.post("/api/v1/businesses", json=bad).status_code == 422
    wrong_model = {"name": "Shop One", "business_model": "service", "goal": {"statement": "ok goal"}}
    r = client.post("/api/v1/businesses", json=wrong_model)
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_business_model"


def test_unknown_business_is_404_in_the_error_shape():
    r = client.get("/api/v1/businesses/biz_nope")
    assert r.status_code == 404 and r.json()["error"]["code"] == "business_not_found"


def test_stage2_endpoints_are_real():
    assert client.get("/api/v1/businesses/biz_aarohi_skin/kpis").json()["facts"][0]["fact_id"] == "f_spend_instagram"
    leads = client.get("/api/v1/businesses/biz_aarohi_skin/leads/queue").json()["leads"]
    assert leads[0]["rank"] == 1 and leads[-1]["abstain"] is True
    assert client.get("/data/health").status_code == 404
