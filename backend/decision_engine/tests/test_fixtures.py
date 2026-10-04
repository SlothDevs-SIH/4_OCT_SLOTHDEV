"""The contract fixtures must agree with each other and with the contract's rules."""
from collections import defaultdict

import pytest

from backend.common.fixtures import load_fixture

ctx = load_fixture("business_context")
facts = {f["fact_id"]: f for f in load_fixture("kpi_facts")}
facts_d7 = {f["fact_id"]: f for f in load_fixture("kpi_facts_day7")}
leads = {l["lead_id"]: l for l in load_fixture("lead_scores")["leads"]}
signals = {s["signal_id"]: s for s in load_fixture("signals")["signals"]}
templates = {t["template_id"]: t for t in load_fixture("intervention_templates")["templates"]}
recs = {r["recommendation_id"]: r for r in load_fixture("recommendations")["recommendations"]}
plan = load_fixture("plan")
outcomes = load_fixture("outcomes")
daily = load_fixture("kpi_daily")


def priority(f):
    benefit = 0.32 * f["I"] + 0.18 * f["U"] + 0.18 * f["F"] + 0.17 * f["R"] + 0.15 * f["T"]
    cost = 0.45 * f["E"] + 0.30 * f["C"] + 0.25 * f["D"]
    return 100 * benefit * (0.5 + 0.5 * f["Q"]) * (1 - 0.55 * cost)


def test_contract_example_fact():
    f = facts["f_cac_instagram"]
    assert (f["value"], f["baseline"], f["delta_pct"]) == (612.0, 410.0, 49.3)
    assert (f["numerator"], f["denominator"]) == (36720.0, 60)


@pytest.mark.parametrize("f", list(facts.values()) + list(facts_d7.values()), ids=lambda f: f["fact_id"])
def test_fact_arithmetic(f):
    assert f["quality_flag"] in ("ok", "partial", "low")
    if f["numerator"] is not None and f["unit"] != "count":
        assert f["numerator"] / f["denominator"] == pytest.approx(f["value"], abs=0.06)
    if f["baseline"]:
        assert f["delta_pct"] == pytest.approx((f["value"] - f["baseline"]) / f["baseline"] * 100, abs=0.06)


def test_day7_has_every_outcome_kpi():
    for o in outcomes["outcomes"]:
        assert o["fact_id"] in facts and o["fact_id"] in facts_d7
        assert o["baseline"] == facts[o["fact_id"]]["value"]
        assert o["actual"] == facts_d7[o["fact_id"]]["value"]


def test_daily_series_sums_to_weekly_facts():
    week = [r for r in daily["series"] if r["date"] >= "2026-09-27"]
    ig = [r for r in week if r["channel"] == "instagram"]
    assert sum(r["spend"] for r in ig) == facts["f_spend_instagram"]["value"]
    assert sum(r["new_customers"] for r in ig) == facts["f_cac_instagram"]["denominator"]
    assert sum(r["sessions"] for r in ig) == facts["f_conv_instagram"]["denominator"]
    prior = [r for r in daily["series"] if r["channel"] == "instagram" and "2026-08-30" <= r["date"] <= "2026-09-26"]
    assert sum(r["spend"] for r in prior) / sum(r["new_customers"] for r in prior) == pytest.approx(410.0, abs=0.01)


def test_funnel_and_lead_invariants():
    assert facts["f_funnel_qualified"]["value"] <= facts["f_funnel_leads"]["value"]
    assert facts["f_funnel_won"]["value"] <= facts["f_funnel_qualified"]["value"]
    unattended = [l for l in leads.values() if l["high_value"] and not l["attended"]]
    assert len(unattended) == facts["f_unattended_hot_leads"]["value"]
    assert sum(l["abstain"] for l in leads.values()) >= 1
    ranked = sorted((l for l in leads.values() if not l["abstain"]), key=lambda l: l["rank"])
    assert [l["score_value_inr"] for l in ranked] == sorted((l["score_value_inr"] for l in ranked), reverse=True)


def test_evidence_ids_exist():
    known = set(facts) | set(leads) | set(signals)
    for s in signals.values():
        assert set(s["evidence_ids"]) <= known, s["signal_id"]
        assert set(s["candidate_template_ids"]) <= set(templates)
    for r in recs.values():
        assert set(r["evidence_ids"]) <= known, r["recommendation_id"]
        assert set(r["signal_ids"]) <= set(signals)
        assert r["template_id"] in templates


def test_signals_cover_the_demo():
    types = sorted(s["type"] for s in signals.values())
    assert types == ["anomaly", "bottleneck", "bottleneck", "opportunity"]
    assert signals["sig_instagram_cac_spike"]["detected_on"] == "2026-09-29"


def test_priorities_and_ranking():
    for r in recs.values():
        if r["status"] == "blocked":
            assert r["priority"] is None and r["blocked_reason"]
            continue
        assert r["priority"] == pytest.approx(priority(r["factors"]), abs=0.05)
        for k in "IFRTECD":
            assert r["factors"][k] == templates[r["template_id"]]["factors"][k]
    ordered = sorted((r for r in recs.values() if r["priority"] is not None), key=lambda r: r["rank"])
    assert [r["recommendation_id"] for r in ordered] == ["rec_hot_leads", "rec_email_retention", "rec_instagram_test"]
    blocked = recs["rec_increase_spend"]
    assert templates[blocked["template_id"]]["spend_change"] in ctx["constraints"]["forbidden_actions"]


def test_plan_fits_capacity_and_dependencies():
    tasks = {t["task_id"]: t for t in plan["tasks"]}
    assert plan["planned_minutes"] == sum(t["effort_min"] for t in tasks.values()) <= ctx["capacity"]["weekly_minutes"]
    per_day, per_owner = defaultdict(int), defaultdict(int)
    for t in tasks.values():
        per_day[t["day"]] += t["effort_min"]
        per_owner[t["owner"]] += t["effort_min"]
        assert 1 <= t["day"] <= 7
        assert t["recommendation_id"] in plan["recommendation_ids"]
        for dep in t["depends_on"]:
            assert tasks[dep]["day"] <= t["day"]
    assert max(per_day.values()) <= ctx["capacity"]["max_minutes_per_day"]
    limits = {o["owner_id"]: o["weekly_minutes"] for o in ctx["capacity"]["owners"]}
    assert all(per_owner[o] <= limits[o] for o in per_owner)
    for rid in plan["recommendation_ids"]:
        assert recs[rid]["status"] != "blocked"
        assert sum(t["effort_min"] for t in tasks.values() if t["recommendation_id"] == rid) == templates[recs[rid]["template_id"]]["effort_min"]


def test_outcomes_match_expected_ranges():
    want = {"rec_hot_leads": "promising", "rec_email_retention": "inconclusive", "rec_instagram_test": "inconclusive"}
    for o in outcomes["outcomes"]:
        assert o["observational"] is True
        assert o["effectiveness"] == want[o["recommendation_id"]]
        exp = recs[o["recommendation_id"]]["expected"]
        assert (o["expected"]["low"], o["expected"]["high"]) == (exp["low"], exp["high"])
        in_range = o["expected"]["low"] <= o["actual"] <= o["expected"]["high"]
        assert in_range == (o["effectiveness"] == "promising")
