"""Diagnosis on the demo data and on the golden-set cases (research/golden_set_template.csv)."""
import copy

import pytest

from backend.common.fixtures import load_fixture
from backend.decision_engine import diagnosis

ALWAYS = lambda b: (True, 30, None)  # noqa: E731


def facts(slug="boxbox", week="week_1", **changes):
    doc = load_fixture(f"v2/{slug}/facts_{week}")
    for f in doc["facts"]:
        if f["fact_id"] in changes:
            f.update(changes[f["fact_id"]])
    return doc


def finding(d, b):
    return next(f for f in d["bottlenecks"] if f["bottleneck"] == b)


# ---------------------------------------------------------------- demo data


def test_box_box_week_1_is_reach():
    d = diagnosis.diagnose(facts(), ALWAYS)
    assert d["status"] == "ok" and d["primary"] == "reach" and len(d["runners_up"]) == 2
    reach = finding(d, "reach")
    assert reach["passed"] and all(reach["tests"].values())
    # hand check: share 6/68 = 0.088 vs best 0.247 -> gap (0.247-0.088)/0.247 = 0.644
    assert reach["gap_to_best"] == pytest.approx((0.247 - 0.088) / 0.247, abs=0.001)
    assert "58 of 68 orders" in reach["where"]
    first = reach["cards"][0]
    assert set(first) >= {"claim", "number", "source", "confidence", "evidence_ids"}
    assert first["number"]["display"] == "8.8%" and first["source"]["fact_id"] == "f_stranger_share"
    assert d["main_measure"]["stranger_orders_this_week"] == 1


def test_every_finding_has_four_part_evidence():
    d = diagnosis.diagnose(facts(), ALWAYS)
    for f in d["bottlenecks"]:
        for c in f["cards"]:
            assert c["claim"] and c["number"]["display"] and c["source"]["fact_id"] and c["confidence"] in (
                "exact", "estimate", "derived")


def test_baker_switches_from_reach_to_capacity():
    got = {w: diagnosis.diagnose(facts("homebaker", w), ALWAYS)["primary"] for w in ("week_1", "week_2", "week_3", "week_4")}
    assert got == {"week_1": "reach", "week_2": "reach", "week_3": "capacity", "week_4": "capacity"}
    cap = finding(diagnosis.diagnose(facts("homebaker", "week_4"), ALWAYS), "capacity")
    assert "dispatch" in cap["where"] and "15 orders turned away" in cap["impact"]


def test_rejected_have_reasons():
    d = diagnosis.diagnose(facts(), ALWAYS)
    assert {r["bottleneck"] for r in d["rejected"]} == {"conversion", "margin", "repeat_orders", "capacity"}
    assert all("within 20%" in r["reason"] for r in d["rejected"])


# ---------------------------------------------------------------- golden-set cases


AT_BEST_REACH = {"f_stranger_share": {"value": 0.247}}


def test_golden_margin_case():
    d = diagnosis.diagnose(facts(**AT_BEST_REACH, f_margin_pct={"value": 0.25}), ALWAYS)
    assert d["primary"] == "margin"
    assert finding(d, "margin")["cards"][0]["number"]["display"] == "25%"


def test_golden_repeat_case():
    d = diagnosis.diagnose(facts(**AT_BEST_REACH, f_repeat_customer_share={"value": 0.05}), ALWAYS)
    assert d["primary"] == "repeat_orders"


def test_golden_capacity_case():
    d = diagnosis.diagnose(facts(**AT_BEST_REACH, f_dispatch_delay_days={"value": 4.0},
                                 f_orders_turned_away={"value": 5, "denominator": 73}), ALWAYS)
    assert d["primary"] == "capacity"
    assert "5 orders were turned away" in " ".join(c["claim"] for c in finding(d, "capacity")["cards"])


def test_golden_thin_data_case():
    doc = facts()
    for f in doc["facts"]:
        f["sample_size"] = 12
    d = diagnosis.diagnose(doc, ALWAYS)
    assert d["status"] == "not_enough_data" and d["primary"] is None
    assert "Only 12 orders" in d["message"]
    assert all(c["confidence"] == "estimate" for f in d["bottlenecks"] for c in f["cards"])


# ---------------------------------------------------------------- rules


def test_no_eligible_action_means_not_primary():
    blocked = lambda b: (b != "reach", 30, "every reach action is blocked by your constraints")  # noqa: E731
    d = diagnosis.diagnose(facts(), blocked)
    assert d["primary"] != "reach"
    rej = {r["bottleneck"]: r["reason"] for r in d["rejected"]}
    assert rej["reach"] == "every reach action is blocked by your constraints"


def test_no_clear_bottleneck():
    d = diagnosis.diagnose(facts(**AT_BEST_REACH), ALWAYS)
    assert d["status"] == "no_clear_bottleneck" and d["primary"] is None


def test_tie_goes_to_less_effort():
    doc = facts(**{"f_stranger_share": {"value": 0.124, "baseline": 0.248}, "f_margin_pct": {"value": 0.219}})
    effort = {"reach": 90, "margin": 30}
    d = diagnosis.diagnose(doc, lambda b: (True, effort.get(b, 60), None))
    assert finding(d, "reach")["gap_to_best"] == finding(d, "margin")["gap_to_best"] == 0.5
    assert d["primary"] == "margin"


def test_missing_facts_are_not_guessed():
    doc = facts()
    doc["facts"] = [f for f in doc["facts"] if not f["kpi"].startswith("margin") and f["kpi"] != "unit_cost_full"]
    m = finding(diagnosis.diagnose(doc, ALWAYS), "margin")
    assert m["gap_to_best"] is None and m["reason"] == "the facts for this bottleneck are missing"


def test_gap_directions():
    assert diagnosis.gap({"value": 5, "baseline": 10, "direction": "up"}) == 0.5
    assert diagnosis.gap({"value": 3, "baseline": 2, "direction": "down"}) == 0.5
    assert diagnosis.gap({"value": 12, "baseline": 10, "direction": "up"}) == 0.0
    assert diagnosis.gap({"value": 9, "baseline": 2, "direction": "down"}) == 1.0  # clipped
