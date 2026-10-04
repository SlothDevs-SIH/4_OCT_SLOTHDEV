from collections import defaultdict

import datetime

import pytest

from backend.common.fixtures import load_fixture
from backend.decision_engine import planner, templates

BIZ = "biz_aarohi_skin"
API = "/api/v1"
DEMO = ("rec_hot_leads", "rec_email_retention", "rec_instagram_test")


def approve(client, *ids):
    client.post(f"{API}/businesses/{BIZ}/recommendations/generate")
    for rid in ids:
        assert client.post(f"{API}/recommendations/{rid}/approve").status_code == 200


def check_plan(plan, ctx):
    tasks = {t["task_id"]: t for t in plan["tasks"]}
    tmpl = templates.templates_by_id()
    per_day, per_owner = defaultdict(int), defaultdict(int)
    for t in tasks.values():
        per_day[t["day"]] += t["effort_min"]
        per_owner[t["owner"]] += t["effort_min"]
        assert 1 <= t["day"] <= 7 and t["status"] == "todo"
        for d in t["depends_on"]:
            assert tasks[d]["day"] <= t["day"]
    cap = ctx["capacity"]
    assert plan["planned_minutes"] == sum(per_day.values()) <= cap["weekly_minutes"]
    assert max(per_day.values()) <= cap["max_minutes_per_day"]
    limits = {o["owner_id"]: o["weekly_minutes"] for o in cap["owners"]}
    assert all(m <= limits[o] for o, m in per_owner.items())
    template_of = {"rec_hot_leads": "tpl_hot_lead_followup", "rec_email_retention": "tpl_repeat_email_flow",
                   "rec_instagram_test": "tpl_instagram_attribution_test"}
    for rid in plan["recommendation_ids"]:  # whole recommendation or nothing
        rec_tasks = [t for t in tasks.values() if t["recommendation_id"] == rid]
        assert len(rec_tasks) == len(tmpl[template_of[rid]]["tasks"])


def test_demo_plan(client):
    approve(client, *DEMO)
    plan = client.post(f"{API}/businesses/{BIZ}/plans").json()
    assert plan["recommendation_ids"] == list(DEMO) and plan["skipped"] == []
    assert plan["week"] == {"from": "2026-10-05", "to": "2026-10-11"}
    assert plan["planned_minutes"] == 435
    check_plan(plan, load_fixture("business_context"))
    fixture_task_keys = set(load_fixture("plan")["tasks"][0])
    assert fixture_task_keys <= set(plan["tasks"][0]) | {"requires_approval"}
    hot = [t for t in plan["tasks"] if t["recommendation_id"] == "rec_hot_leads"]
    assert "lead_0412, lead_0388, lead_0397, lead_0421" in hot[0]["title"]
    assert client.get(f"{API}/plans/{plan['plan_id']}").json() == plan


def test_gap_days_respected(client):
    approve(client, *DEMO)
    tasks = {t["task_id"]: t for t in client.post(f"{API}/businesses/{BIZ}/plans").json()["tasks"]}
    launch = next(t for t in tasks.values() if t["title"].startswith("Launch"))
    readout = next(t for t in tasks.values() if t["title"].startswith("Review"))
    audit = next(t for t in tasks.values() if t["title"].startswith("Audit"))
    assert launch["day"] >= audit["day"] + 2 and readout["day"] >= launch["day"] + 3


def test_only_approved_are_planned(client):
    approve(client, "rec_email_retention")
    plan = client.post(f"{API}/businesses/{BIZ}/plans").json()
    assert plan["recommendation_ids"] == ["rec_email_retention"]


def test_nothing_approved_and_already_planned(client):
    client.post(f"{API}/businesses/{BIZ}/recommendations/generate")
    r = client.post(f"{API}/businesses/{BIZ}/plans")
    assert r.status_code == 409 and r.json()["error"]["code"] == "nothing_approved"
    approve(client, "rec_hot_leads")
    assert client.post(f"{API}/businesses/{BIZ}/plans").status_code == 200
    r = client.post(f"{API}/businesses/{BIZ}/plans")
    assert r.status_code == 409 and r.json()["error"]["code"] == "already_planned"
    # a rec in an active plan can no longer be rejected
    assert client.post(f"{API}/recommendations/rec_hot_leads/reject").status_code == 409


def _recs(engine):
    engine.generate(BIZ)
    for rid in DEMO:
        engine.approve(rid)
    return engine.store.recommendations_for(BIZ)


def test_tight_capacity_drops_lowest_priority_whole(engine):
    ctx = load_fixture("business_context")
    ctx["capacity"]["weekly_minutes"] = 320
    plan = planner.build("p", _recs(engine), ctx, datetime.date(2026, 10, 5), 1, "now")
    assert plan["recommendation_ids"] == ["rec_hot_leads", "rec_email_retention"]
    assert plan["skipped"] == [{"recommendation_id": "rec_instagram_test",
                                "reason": "its tasks do not fit in this week's capacity"}]
    assert plan["planned_minutes"] == 300


def test_no_capacity_is_an_error(engine):
    ctx = load_fixture("business_context")
    ctx["capacity"]["max_minutes_per_day"] = 20
    with pytest.raises(planner.PlanError):
        planner.build("p", _recs(engine), ctx, datetime.date(2026, 10, 5), 1, "now")


def test_conflicting_spend_changes_on_one_channel():
    a = {"recommendation_id": "a", "status": "approved", "priority": 60, "template_id": "tpl_instagram_attribution_test",
         "targets": {"channel": "instagram"}}
    b = dict(a, recommendation_id="b", priority=50, template_id="tpl_increase_ad_spend")
    chosen, skipped = planner.select([b, a])
    assert [r["recommendation_id"] for r in chosen] == ["a"] and skipped[0]["recommendation_id"] == "b"


def test_cycle_detected():
    tasks = [{"task_id": "x", "depends_on": ["y"], "_gap": 0}, {"task_id": "y", "depends_on": ["x"], "_gap": 0}]
    with pytest.raises(planner.PlanError):
        planner.latest_days(tasks)


def test_task_updates(client):
    approve(client, *DEMO)
    plan = client.post(f"{API}/businesses/{BIZ}/plans").json()
    first = plan["tasks"][0]["task_id"]
    t = client.patch(f"{API}/tasks/{first}", json={"status": "doing"}).json()
    assert t["status"] == "doing"
    assert client.patch(f"{API}/tasks/{first}", json={"status": "finished"}).status_code == 422
    assert client.patch(f"{API}/tasks/task_999", json={"status": "done"}).status_code == 404
    follow = next(t for t in plan["tasks"] if t["depends_on"])
    r = client.patch(f"{API}/tasks/{follow['task_id']}", json={"status": "done"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "dependencies_open"
    for d in follow["depends_on"]:
        client.patch(f"{API}/tasks/{d}", json={"status": "done"})
    assert client.patch(f"{API}/tasks/{follow['task_id']}", json={"status": "done"}).json()["status"] == "done"
    saved = {t["task_id"]: t for t in client.get(f"{API}/plans/{plan['plan_id']}").json()["tasks"]}
    assert saved[follow["task_id"]]["status"] == "done"
