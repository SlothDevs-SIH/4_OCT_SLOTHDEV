"""Lead qualification, intake and the next-month projection."""
import copy
from datetime import date, timedelta

import pytest

from backend.data_engine.homebiz import generate as G
from backend.data_engine.homebiz import intake, projection
from backend.data_engine.homebiz import leads as L
from backend.data_engine.homebiz.model import BusinessData, as_of_for

SERVES = {"cities": ["Pune", "Mumbai"], "sizes": ["S", "M", "L", "XL"]}
PRODUCTS = [{"name": "Ferrari F1 Tee"}, {"name": "Box Box Racing Cap"}]


def lead(lid, rel, signals, asked=None, intents=None, outcome="open", outcome_date=None):
    return {"lead_id": lid, "handle_ref": lid, "source": "dm", "relationship": rel, "signals": [{"type": t, "date": dt} for t, dt in signals],
            "asked_for": asked or {}, "intents": intents or [], "texts": [], "outcome": outcome, "outcome_date": outcome_date, "synthetic": True}


AS_OF = date(2026, 9, 25)
A = lead("A", "stranger", [("saved_or_shared", "2026-09-20"), ("comment", "2026-09-22"), ("price_question", "2026-09-24")])
B = lead("B", "friend", [("bought_before", "2026-09-01"), ("story_reply", "2026-09-24")])
C_ = lead("C", "stranger", [("comment", "2026-09-01"), ("saved_or_shared", "2026-09-02")])
D = lead("D", "stranger", [("follow_or_like", "2026-09-20")])
E = lead("E", "stranger", [("price_question", "2026-09-24")], asked={"city": "Jaipur"})


# ------------------------------------------------------------------ the design document's worked examples (section 7)
@pytest.mark.parametrize("ld,score,group", [(A, 75, "hot"), (B, 50, "hot"), (C_, 35, "warm"), (D, 15, "cold")])
def test_worked_examples(ld, score, group):
    s = L.score_lead(ld, AS_OF, SERVES)
    assert (s["score"], s["group"]) == (score, group)


def test_lead_c_a_month_later_decays_to_cold():
    s = L.score_lead(C_, date(2026, 10, 3), SERVES)
    assert s["score"] == 15 and s["group"] == "cold" and any(r["signal"] == "decay" and r["points"] == -20 for r in s["reasons"])


def test_lead_e_is_disqualified_by_fit_not_by_score():
    s = L.score_lead(E, AS_OF, SERVES)
    assert s["group"] == "disqualified" and s["score"] == 50 and "Jaipur" in s["disqualified_reason"] and s["deliverable"] is False


def test_a_ranks_above_b_new_growth_over_a_repeat_sale():
    rows = L.score_all([B, A, C_, D, E], AS_OF, SERVES)
    assert [r["lead_id"] for r in rows] == ["A", "B", "C", "D", "E"] and [r["rank"] for r in rows] == [1, 2, 3, 4, None]
    assert rows[0]["next_action"].startswith("Reply today")


def test_at_equal_score_a_stranger_ranks_above_a_friend():
    friend = lead("F", "friend", [("price_question", "2026-09-24"), ("story_reply", "2026-09-20"), ("comment", "2026-09-23")])   # 40 + 20 + 10 = 70
    stranger = lead("T", "stranger", [("price_question", "2026-09-24"), ("story_reply", "2026-09-20")])                          # 40 + 20 + 10 = 70
    rows = L.score_all([friend, stranger], AS_OF, SERVES)
    assert [r["score"] for r in rows] == [70, 70] and [r["lead_id"] for r in rows] == ["T", "F"]


def test_each_signal_counts_once():
    ld = lead("X", "friend", [("comment", "2026-09-20"), ("comment", "2026-09-21"), ("comment", "2026-09-22")])
    assert L.score_lead(ld, AS_OF, SERVES)["score"] == 10


def test_decay_applies_after_30_or_more_days_of_silence():
    ld = lead("Y", "friend", [("saved_or_shared", "2026-08-26")])
    assert L.score_lead(ld, date(2026, 9, 24), SERVES)["score"] == 15           # 29 days of silence: not yet
    assert L.score_lead(ld, date(2026, 9, 25), SERVES)["score"] == -5           # 30 days: 15 - 20


@pytest.mark.parametrize("signals,score,group", [
    (["price_question", "comment"], 50, "hot"), (["price_question", "follow_or_like"], 45, "warm"),
    (["saved_or_shared", "follow_or_like"], 20, "warm"), (["saved_or_shared"], 15, "cold")])
def test_group_thresholds(signals, score, group):
    ld = lead("Z", "friend", [(t, "2026-09-24") for t in signals])
    got = L.score_lead(ld, AS_OF, SERVES)
    assert (got["score"], got["group"]) == (score, group)             # hot starts at 50, warm at 20


def test_signals_after_the_snapshot_are_invisible():
    ld = lead("W", "stranger", [("comment", "2026-09-24"), ("price_question", "2026-09-26")])
    assert L.score_lead(ld, AS_OF, SERVES)["score"] == 20 and L.score_lead(ld, date(2026, 9, 27), SERVES)["score"] == 60


def test_fit_checks_size_city_and_custom_requests():
    big = lead("S", "friend", [("price_question", "2026-09-24")], asked={"size": "XXL"})
    assert L.score_lead(big, AS_OF, SERVES)["group"] == "disqualified" and "XXL" in L.score_lead(big, AS_OF, SERVES)["disqualified_reason"]
    custom = lead("C", "friend", [("comment", "2026-09-24")], asked={"design": "custom name"}, intents=["custom_request"])
    s = L.score_lead(custom, AS_OF, SERVES)
    assert s["group"] != "disqualified" and s["deliverable"] is None                                        # needs a check
    ok = lead("O", "friend", [("price_question", "2026-09-24")], asked={"city": "Pune", "size": "L"})
    assert L.score_lead(ok, AS_OF, SERVES)["deliverable"] is True


def test_not_a_lead_and_closed_leads_are_left_off_the_list():
    spam = lead("N", "unknown", [], intents=["not_a_lead"])
    spam["signals"] = []
    assert L.score_lead(spam, AS_OF, SERVES)["group"] == "not_a_lead"
    done = lead("Q", "friend", [("price_question", "2026-09-20")], outcome="ordered", outcome_date="2026-09-22")
    open_ = lead("R", "friend", [("price_question", "2026-09-20")])
    ids = [r["lead_id"] for r in L.score_all([spam, done, open_], AS_OF, SERVES)]
    assert ids == ["R"]
    assert [r["lead_id"] for r in L.score_all([done], date(2026, 9, 21), SERVES)] == ["Q"]               # not yet ordered on the 21st


def test_unmet_demand_counts_reasons():
    rows = L.score_all([E, lead("E2", "stranger", [("price_question", "2026-09-23")], asked={"city": "Jaipur"}),
                        lead("E3", "friend", [("price_question", "2026-09-23")], asked={"size": "XXL"})], AS_OF, SERVES)
    assert L.unmet_demand(rows) == {"city: cannot deliver to Jaipur": 2, "size: XXL is not available": 1}


# ------------------------------------------------------------------ reading intent
@pytest.mark.parametrize("text,expected", [
    ("Is the Ferrari tee available in L?", ["buying_question"]),
    ("How much with delivery to Pune?", ["buying_question"]),
    ("This one is fire 🔥", ["product_interest"]),
    ("Love your page", ["general_praise"]),
    ("Can you make one with my name on it?", ["custom_request"]),
    ("Collab? We can promote your page", ["not_a_lead"]),
    ("hello", ["general_praise"])])
def test_rule_based_intent(text, expected):
    got = L.label_intent(text)
    assert got["intents"][: len(expected)] == expected or set(expected) <= set(got["intents"])
    assert got["method"] == "rules"


def test_details_are_only_what_the_message_says():
    det = L.extract_details("Is the Ferrari tee available in L? deliver to Pune", PRODUCTS, SERVES)
    assert det == {"product": "Ferrari F1 Tee", "size": "L", "design": None, "city": "Pune"}
    assert L.extract_details("love it", PRODUCTS, SERVES) == {"product": None, "size": None, "design": None, "city": None}


def test_a_provider_can_label_but_bad_output_falls_back_to_rules():
    try:
        L.register_provider(lambda t: {"intents": ["buying_question"]})
        assert L.label_intent("hello")["method"] == "llm"
        L.register_provider(lambda t: {"intents": ["made_up_label"]})
        assert L.label_intent("how much?")["method"] == "rules"
        L.register_provider(lambda t: 1 / 0)
        assert L.label_intent("how much?")["intents"] == ["buying_question"]
    finally:
        L.register_provider(None)


def test_signals_from_messages():
    assert L.signals_from_message("dm", ["buying_question"]) == ["price_question"]
    assert L.signals_from_message("story", ["product_interest"]) == ["story_reply"]
    assert L.signals_from_message("comment", ["product_interest"]) == ["comment"]
    assert L.signals_from_message("dm", ["general_praise"]) == ["follow_or_like"] and L.signals_from_message("dm", ["not_a_lead"]) == []


# ------------------------------------------------------------------ privacy and pasted chats
def test_redaction_and_stable_pseudonyms():
    t = intake.redact("call 98765 43210 or +91 9876543210, mail riya@gmail.com, tag @riya_k")
    assert "[phone]" in t and "[email]" in t and "98765" not in t and "riya_k" not in t and "@user_" in t
    assert intake.pseudonym("Riya") == intake.pseudonym(" riya ") != intake.pseudonym("Rohan")


def test_parse_chat_both_formats():
    msgs = intake.parse_chat("@riya (dm): is the tee available in L?\n[04/10/26, 9:41 am] Rohan: price for the cap?\nrandom line\n\n", date(2026, 10, 1))
    assert [m["channel"] for m in msgs] == ["dm", "whatsapp"] and msgs[1]["date"] == "2026-10-04"
    assert all(m["handle_ref"].startswith("@user_") for m in msgs) and "riya" not in str(msgs).lower()
    assert msgs[0]["handle_ref"] == "@" + intake.pseudonym("riya")


def test_leads_from_messages_groups_people_and_reads_intent():
    msgs = intake.parse_chat("@riya (dm): is the Ferrari tee available in L?\n@riya (story): this one is fire\n@spam (dm): collab? we can promote you", date(2026, 10, 1))
    touched, created = intake.leads_from_messages(msgs, PRODUCTS, SERVES, [], 0)
    assert len(created) == 2 and len(touched) == 2
    riya = next(l for l in created if l["handle_ref"] == "@" + intake.pseudonym("riya"))
    assert {s["type"] for s in riya["signals"]} == {"price_question", "story_reply"} and riya["asked_for"]["size"] == "L"
    spam = next(l for l in created if l is not riya)
    assert spam["intents"] == ["not_a_lead"] and spam["signals"] == []
    t2, c2 = intake.leads_from_messages(msgs[:1], PRODUCTS, SERVES, created, 2)
    assert c2 == [] and len(t2) == 1 and len(riya["signals"]) == 2           # an existing person is updated, a signal is not double counted


# ------------------------------------------------------------------ weekly learning on the generated leads
def test_learning_report_on_the_demo_business():
    box = G.build("boxbox")
    rep = L.learning_report(box.leads, as_of_for(1), box.profile["serves"], box.profile["products"])
    assert rep["enough_data"] and rep["leads_with_known_outcome"] >= 60
    g = rep["by_group"]
    assert g["hot"]["conversion"] > g["warm"]["conversion"] > g["cold"]["conversion"]
    assert all(c["ok"] for c in rep["healthy_model_checks"]) and rep["points_status"].startswith("Starting guesses")
    assert rep["challenger_agreement"]["spearman_points_vs_bank_model"] > 0                     # the public model agrees on direction
    assert rep["by_signal"]["price_question"]["points_now"] == 40 and rep["by_signal"]["stranger"]["points_now"] == 10
    assert {s["direction"][:6] for s in rep["public_data_support"]} and all(s["supported"] for s in rep["public_data_support"])


def test_learning_needs_enough_outcomes_before_suggesting_changes():
    few = [lead(f"L{i}", "friend", [("price_question", "2026-09-10")], outcome="ordered" if i < 2 else "not_ordered", outcome_date="2026-09-15") for i in range(6)]
    rep = L.learning_report(few, AS_OF, SERVES)
    assert rep["enough_data"] is False and "wait" in rep["message"] and rep["by_signal"]["price_question"]["suggestion"] == "not enough outcomes yet"


def test_spearman():
    assert L.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == 1.0 and L.spearman([1, 2, 3, 4], [4, 3, 2, 1]) == -1.0
    assert L.spearman([1, 2], [1, 2]) is None


# ------------------------------------------------------------------ the next-month projection
def _flat(weekly: int, weeks: int, cap=None, away=0, feed=None):
    start = date(2026, 8, 3)
    orders = [{"order_id": f"O{w}-{i}", "date": (start + timedelta(weeks=w, days=i % 7)).isoformat()} for w in range(weeks) for i in range(weekly)]
    prof = {"business_id": "biz_t", "synthetic": False, "capacity_orders_per_week": cap, "context_feeds": [feed] if feed else [], "products": [], "fields": {}}
    turned = [{"date": (start + timedelta(weeks=w, days=1)).isoformat()} for w in range(weeks) for _ in range(away)]
    return BusinessData(key="t", profile=prof, orders=orders, turned_away=turned,
                        meta={"history_start": start.isoformat(), "advisory_start": (start + timedelta(weeks=weeks)).isoformat(), "max_week": 1})


def test_flat_history_projects_flat():
    p = projection.project(_flat(10, 8), 1)
    assert p["estimate"] is True and p["orders"] == {"low": 40, "expected": 40, "high": 40} and p["basis"]["trend_per_week"] == 0
    assert p["basis"]["context_factor"] == 1.0 and p["basis"]["weeks_used"] == 8


def test_too_little_history_says_so():
    p = projection.project(_flat(10, 5), 1)
    assert p["orders"] is None and p["confidence"] == "none" and "at least 6" in p["message"]


def test_a_rising_trend_is_damped():
    start = date(2026, 8, 3)
    weekly = [6, 8, 10, 12, 14, 16, 18, 20]
    orders = [{"order_id": f"{w}-{i}", "date": (start + timedelta(weeks=w, days=i % 7)).isoformat()} for w, n in enumerate(weekly) for i in range(n)]
    data = BusinessData(key="t", profile={"business_id": "b", "synthetic": False, "context_feeds": [], "products": [], "fields": {}}, orders=orders,
                        meta={"history_start": start.isoformat(), "advisory_start": (start + timedelta(weeks=8)).isoformat(), "max_week": 1})
    p = projection.project(data, 1)
    assert p["basis"]["trend_per_week"] == 2.0
    assert p["weekly_expected_demand"] == [21.0, 22.0, 23.0, 24.0]                    # level 20 plus half the slope per week
    assert p["orders"]["expected"] == 90


def test_capacity_caps_orders_but_not_demand_and_turned_away_counts_as_demand():
    p = projection.project(_flat(14, 8, cap=14, away=3), 1)
    assert p["demand"]["expected"] == 68 and p["orders"]["expected"] == 56 and p["capacity"]["demand_exceeds_capacity"] is True
    assert p["capacity"]["orders_lost_to_capacity_expected"] == 12 and "turned away" in p["capacity"]["message"]
    q = projection.project(_flat(10, 8, cap=30), 1)
    assert q["capacity"]["demand_exceeds_capacity"] is False


def test_range_is_ordered_and_labelled_an_estimate_for_the_demo_businesses():
    for key in ("boxbox", "homebaker"):
        p = projection.project(G.build(key), 1)
        o = p["orders"]
        assert o["low"] <= o["expected"] <= o["high"] and p["estimate"] is True and "not a forecast" in p["note"] and p["synthetic"] is True
        assert p["basis"]["method"].startswith("damped straight-line")


def test_context_factor_uses_the_calendar():
    box = G.build("boxbox")
    p = projection.project(box, 1)
    assert p["basis"]["context_source"] == "f1_calendar" and p["basis"]["context_share_next_4_weeks"] > 0
    assert p["basis"]["assumed_context_effect"] == pytest.approx(0.4)
    baker = projection.project(G.build("homebaker"), 1)
    assert baker["basis"]["context_source"] == "india_festivals" and baker["basis"]["context_factor"] > 1.0       # Dussehra and Diwali are ahead
    assert baker["capacity"]["demand_exceeds_capacity"] is True
