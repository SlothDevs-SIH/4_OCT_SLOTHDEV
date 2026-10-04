"""Diagnosis on data_engine's real v2 facts (contracts/fixtures/v2_engine) and on golden-set style cases."""
import pytest

from backend.decision_engine import diagnosis
from backend.decision_engine.clients import DataClientV2

ALWAYS = lambda b: (True, 30, None)  # noqa: E731
BB, HB = "biz_boxbox", "biz_homebaker"
DATA = DataClientV2("fixture")


def doc(biz=BB, week=1, **changes):
    facts = DATA.get_facts(biz, week)
    for f in facts:
        if f["fact_id"] in changes:
            f.update(changes[f["fact_id"]])
    return {"business_id": biz, "week": f"week_{week}", "window_weeks": 4, "facts": facts}


def finding(d, b):
    return next(f for f in d["bottlenecks"] if f["bottleneck"] == b)


# ---------------------------------------------------------------- the real demo weeks


def test_box_box_reach_then_back_to_its_best():
    got = {w: diagnosis.diagnose(doc(BB, w), ALWAYS) for w in (1, 2, 3, 4)}
    assert [got[w]["primary"] for w in (1, 2, 3, 4)] == ["reach", "reach", None, None]
    assert got[3]["status"] == got[4]["status"] == "no_clear_bottleneck"


def test_box_box_week_1_reach_hand_check():
    d = diagnosis.diagnose(doc(), ALWAYS)
    reach = finding(d, "reach")
    # stranger orders 1.5 a week vs 3.25 in the best 4-week window: gap (3.25-1.5)/3.25 = 0.5385, worth 7 orders
    assert reach["key_fact"] == "f_stranger_orders_week" and reach["gap_to_best"] == pytest.approx(0.5385)
    assert reach["impact"] == "about 7 orders in the last 4 weeks"
    assert reach["where"].startswith("the gap is in orders from strangers: 57 of 63 orders")
    c = reach["cards"][0]
    assert c["claim"] == "Orders from strangers: 1.5 a week on average over the last 4 weeks (best weeks: 3.25 a week)."
    assert c["best_weeks"]["period"] == {"from": "2026-08-10", "to": "2026-09-06"}
    assert set(c["evidence_ids"]) >= {"f_stranger_orders_week", "f_orders_by_source_stranger"}


def test_baker_is_capacity_every_week():
    for w in (1, 2, 3, 4):
        d = diagnosis.diagnose(doc(HB, w), ALWAYS)
        assert d["primary"] == "capacity", w
        assert finding(d, "capacity")["key_fact"] == "f_orders_turned_away"
    cap = finding(diagnosis.diagnose(doc(HB, 1), ALWAYS), "capacity")
    assert cap["cards"][0]["claim"] == "10 orders were turned away in the last 4 weeks, against 5 in your best weeks."


def test_grouped_by_tag_not_by_id():
    d = diagnosis.diagnose(doc(), ALWAYS)
    tagged = {f["fact_id"] for f in DATA.get_facts(BB, 1) if f["bottleneck"] == "conversion"}
    conv = finding(d, "conversion")
    assert set(conv["supporting_fact_ids"]) | {conv["key_fact"]} == tagged


def test_tiny_gaps_do_not_win():
    d = diagnosis.diagnose(doc(), ALWAYS)
    cap = finding(d, "capacity")      # 1 stock-out vs 0: a 100% gap, but one item
    assert cap["gap_to_best"] == 1.0 and cap["tests"]["materiality"] is False
    conv = finding(d, "conversion")   # 20% vs 26.5% of 30 leads: under 2 orders
    assert conv["tests"]["materiality"] is False and conv["reason"] == "too small to matter yet"


def test_every_finding_has_four_part_evidence():
    for biz in (BB, HB):
        for f in diagnosis.diagnose(doc(biz), ALWAYS)["bottlenecks"]:
            for c in f["cards"]:
                assert c["claim"] and c["number"]["display"] and c["source"]["fact_id"]
                assert c["confidence"] in ("exact", "estimate", "derived")


def test_runners_up_prefer_material_gaps():
    d = diagnosis.diagnose(doc(), ALWAYS)
    assert d["runners_up"][0] == "margin"   # material (about INR 2,495) even though below 20%


# ---------------------------------------------------------------- golden-set style cases on real facts


AT_BEST_REACH = {"f_stranger_orders_week": {"value": 3.25, "gap_to_best": 0.0}, "f_stranger_share": {"value": 0.1605, "gap_to_best": 0.0}}


def test_margin_case():
    d = diagnosis.diagnose(doc(**AT_BEST_REACH, f_margin_pct={"value": 0.25, "gap_to_best": 0.42}), ALWAYS)
    assert d["primary"] == "margin" and finding(d, "margin")["cards"][0]["number"]["display"] == "25%"


def test_repeat_case():
    d = diagnosis.diagnose(doc(**AT_BEST_REACH, f_repeat_customer_share={"value": 0.03, "baseline": 0.12, "gap_to_best": 0.75}), ALWAYS)
    assert d["primary"] == "repeat_orders"


def test_capacity_case():
    d = diagnosis.diagnose(doc(**AT_BEST_REACH, f_dispatch_delay_days={"value": 4.0, "gap_to_best": 1.0}), ALWAYS)
    assert d["primary"] == "capacity" and finding(d, "capacity")["where"] == "the limit is dispatch"


def test_thin_data_case():
    facts = doc()
    for f in facts["facts"]:
        f["sample_size"] = 12
    d = diagnosis.diagnose(facts, ALWAYS)
    assert d["status"] == "not_enough_data" and d["primary"] is None and "Only 12 orders" in d["message"]
    assert all(c["confidence"] == "estimate" for f in d["bottlenecks"] for c in f["cards"])


def test_no_eligible_action_means_not_primary():
    d = diagnosis.diagnose(doc(), lambda b: (b != "reach", 30, "every reach action is blocked"))
    assert d["primary"] != "reach"
    assert {r["bottleneck"]: r["reason"] for r in d["rejected"]}["reach"] == "every reach action is blocked"


def test_tie_goes_to_less_effort():
    d0 = doc(**AT_BEST_REACH, f_margin_pct={"value": 0.2, "gap_to_best": 0.5},
             f_dispatch_delay_days={"value": 3.0, "gap_to_best": 0.5})
    d = diagnosis.diagnose(d0, lambda b: (True, {"margin": 90, "capacity": 30}.get(b, 60), None))
    assert finding(d, "margin")["gap_to_best"] == finding(d, "capacity")["gap_to_best"] == 0.5
    assert d["primary"] == "capacity"


def test_missing_facts_are_not_guessed():
    facts = doc()
    facts["facts"] = [f for f in facts["facts"] if f["bottleneck"] != "margin"]
    m = finding(diagnosis.diagnose(facts, ALWAYS), "margin")
    assert m["gap_to_best"] is None and m["reason"] == "the facts for this bottleneck are missing"


def test_gap_clips_and_needs_a_direction():
    assert diagnosis.gap({"better": "lower", "value": 1, "baseline": 0, "gap_to_best": 1.9}) == 1.0
    assert diagnosis.gap({"better": "info", "value": 5, "baseline": None}) is None
    assert diagnosis.gap({"better": "higher", "value": 5, "baseline": 10}) == 0.5


def test_diagnosis_endpoint(client):
    d = client.get("/api/v1/businesses/biz_homebaker/diagnosis?week=week_1").json()
    assert d["primary"] == "capacity" and d["as_of"] == "2026-10-05"
    assert client.get("/api/v1/businesses/biz_nope/diagnosis").status_code == 404
