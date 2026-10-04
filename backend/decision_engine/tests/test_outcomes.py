import pytest

from backend.decision_engine import outcomes
from backend.decision_engine.clients import DataClient
from backend.decision_engine.service import Engine

BIZ = "biz_aarohi_skin"
API = "/api/v1"
DEMO = ("rec_hot_leads", "rec_email_retention", "rec_instagram_test")

LEDGER = {"baseline": 10.0, "expected": {"low": 12.0, "high": 15.0, "direction": "up"}, "window_days": 7}
DONE = {"tasks_done": 3, "tasks_total": 3, "rate": 1.0, "executed": True}
HALF = {"tasks_done": 1, "tasks_total": 3, "rate": 0.33, "executed": False}


@pytest.mark.parametrize("actual,fid,elapsed,want", [
    (13.0, DONE, 7, "promising"),
    (16.0, DONE, 7, "promising"),        # above the range still counts as reaching it
    (9.0, DONE, 7, "not_effective"),     # fully executed, KPI went the wrong way
    (10.0, DONE, 7, "not_effective"),    # no change
    (11.0, DONE, 7, "inconclusive"),     # better, but below the expected range
    (13.0, HALF, 7, "inconclusive"),     # not executed: cannot credit the action
    (13.0, DONE, 3, "inconclusive"),     # window not over
    (None, DONE, 7, "inconclusive"),     # no day-7 value
])
def test_judge(actual, fid, elapsed, want):
    assert outcomes.judge(LEDGER, actual, fid, elapsed)[0] == want


def test_judge_direction_down():
    led = {"baseline": 600.0, "expected": {"low": 450.0, "high": 540.0, "direction": "down"}, "window_days": 7}
    assert outcomes.judge(led, 500.0, DONE, 7)[0] == "promising"
    assert outcomes.judge(led, 650.0, DONE, 7)[0] == "not_effective"


def run_demo_week(client, finish_readout=False):
    client.post(f"{API}/businesses/{BIZ}/recommendations/generate")
    for rid in DEMO:
        client.post(f"{API}/recommendations/{rid}/approve")
    plan = client.post(f"{API}/businesses/{BIZ}/plans").json()
    for t in sorted(plan["tasks"], key=lambda t: t["day"]):
        if finish_readout or not t["title"].startswith("Review"):
            assert client.patch(f"{API}/tasks/{t['task_id']}", json={"status": "done"}).status_code == 200
    return plan


def test_demo_outcomes_reproduced(client):
    plan = run_demo_week(client)
    assert client.get(f"{API}/plans/{plan['plan_id']}/outcomes").status_code == 404  # not evaluated yet
    doc = client.post(f"{API}/plans/{plan['plan_id']}/outcomes/evaluate").json()
    got = {o["recommendation_id"]: o for o in doc["outcomes"]}
    assert {k: v["effectiveness"] for k, v in got.items()} == {
        "rec_hot_leads": "promising", "rec_email_retention": "inconclusive", "rec_instagram_test": "inconclusive"}
    hot = got["rec_hot_leads"]
    assert (hot["baseline"], hot["actual"], hot["fidelity"]["rate"]) == (1, 3, 1.0)
    assert hot["guardrails"][0]["value"] == 5.5 and hot["guardrails"][0]["breached"] is False
    assert got["rec_instagram_test"]["fidelity"]["tasks_done"] == 2
    assert doc["observational"] is True and all(o["observational"] for o in doc["outcomes"])
    assert doc["snapshot"]["period"] == {"from": "2026-10-05", "to": "2026-10-11"}
    assert client.get(f"{API}/plans/{plan['plan_id']}/outcomes").json() == doc


def test_finishing_the_readout_changes_fidelity_not_the_verdict(client):
    plan = run_demo_week(client, finish_readout=True)
    doc = client.post(f"{API}/plans/{plan['plan_id']}/outcomes/evaluate").json()
    ig = next(o for o in doc["outcomes"] if o["recommendation_id"] == "rec_instagram_test")
    # executed now, but 0.75 is still below the expected range -> inconclusive, not promising
    assert ig["fidelity"]["executed"] and ig["effectiveness"] == "inconclusive"
    assert ig["reasons"] == ["the KPI improved but stayed below the expected range"]


def test_guardrail_breach_is_flagged(engine):
    led = {"kpi": "lead_wins", "fact_id": "f_x", "unit": "count", "baseline": 1,
           "expected": {"low": 2, "high": 4, "direction": "up"}, "window_days": 7,
           "guardrails": [{"kpi": "response_latency_p90", "fact_id": "f_lat", "max": 24, "baseline": 38.5}],
           "confounders": []}
    plan = {"plan_id": "p", "business_id": BIZ, "recommendation_ids": ["r"],
            "tasks": [{"recommendation_id": "r", "status": "done"}]}
    day7 = [{"fact_id": "f_x", "value": 3, "period": {"from": "2026-10-05", "to": "2026-10-11"}},
            {"fact_id": "f_lat", "value": 30, "period": {"from": "2026-10-05", "to": "2026-10-11"}}]
    doc = outcomes.evaluate(plan, {"r": {"ledger": led}}, day7, "now")
    o = doc["outcomes"][0]
    assert o["guardrails"][0]["breached"] is True and "guardrail" in o["reasons"][-1]


def test_missing_day7_snapshot(tmp_path):
    class NoDay7(DataClient):
        def get_kpi_facts(self, business_id, from_date=None, to_date=None, snapshot="baseline"):
            return [] if snapshot == "day7" else super().get_kpi_facts(business_id, from_date, to_date, snapshot)

    from backend.decision_engine.config import Settings
    eng = Engine(settings=Settings(llm_cache_only=True, llm_cache_dir=tmp_path), data=NoDay7("fixture"))
    eng.generate(BIZ)
    eng.approve("rec_hot_leads")
    plan = eng.create_plan(BIZ)
    from backend.common.errors import ApiError
    with pytest.raises(ApiError) as e:
        eng.evaluate_outcomes(plan["plan_id"])
    assert e.value.status == 409 and e.value.code == "no_day7_snapshot"


def test_unknown_plan(client):
    assert client.post(f"{API}/plans/plan_nope/outcomes/evaluate").status_code == 404


def test_source_that_ignores_snapshot_is_refused(tmp_path):
    """A data source returning the baseline week for snapshot=day7 must not produce outcomes."""
    class IgnoresSnapshot(DataClient):
        def get_kpi_facts(self, business_id, from_date=None, to_date=None, snapshot="baseline"):
            return super().get_kpi_facts(business_id, from_date, to_date, "baseline")

    from backend.common.errors import ApiError
    from backend.decision_engine.config import Settings
    eng = Engine(settings=Settings(llm_cache_only=True, llm_cache_dir=tmp_path), data=IgnoresSnapshot("fixture"))
    eng.generate(BIZ)
    eng.approve("rec_hot_leads")
    plan = eng.create_plan(BIZ)
    with pytest.raises(ApiError) as e:
        eng.evaluate_outcomes(plan["plan_id"])
    assert e.value.code == "no_day7_snapshot"
