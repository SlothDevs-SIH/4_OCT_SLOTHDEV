"""Generated demo businesses (Box Box, home baker): calibration, honesty, invariants, and the facts engine."""
import copy
import json
import math
import statistics
from collections import Counter
from datetime import date, timedelta

import pytest

from backend.data_engine.homebiz import config as C
from backend.data_engine.homebiz import facts as F
from backend.data_engine.homebiz import generate as G
from backend.data_engine.homebiz import store as hb
from backend.data_engine.homebiz.model import BusinessData, as_of_for, d, window_weeks

KEYS = ("boxbox", "homebaker")


@pytest.fixture(scope="module", params=KEYS)
def biz(request):
    return G.build(request.param)


@pytest.fixture(scope="module")
def box():
    return G.build("boxbox")


@pytest.fixture(scope="module")
def baker():
    return G.build("homebaker")


# ------------------------------------------------------------------ determinism and labelling
def test_deterministic_and_cached_copies_are_independent():
    a, b = G.build_raw("boxbox"), G.build_raw("boxbox")
    assert a.orders == b.orders and a.leads == b.leads and a.posts == b.posts
    data = hb.load_demo("boxbox", 1)
    data.leads[0]["relationship"] = "stranger-edited"
    assert G.build("boxbox").leads[0]["relationship"] != "stranger-edited"      # the cached original is untouched


def test_everything_is_labelled_synthetic(biz):
    assert biz.profile["synthetic"] is True and biz.meta["data_card"]["synthetic"] is True
    assert all(r["synthetic"] for r in biz.orders + biz.posts + biz.leads + biz.turned_away + biz.stockouts)


def test_data_card_separates_public_calibration_from_scenario_assumptions(biz):
    card = biz.meta["data_card"]
    assert set(card) >= {"what_is_calibrated_on_public_data", "what_is_a_scenario_assumption", "note"}
    cal = card["what_is_calibrated_on_public_data"]
    assert "Olist" in cal["repeat_share_floor"]["from"] and "Online Retail II" in cal["repeat_gap_days_median"]["from"]
    assert "Online Shoppers" in cal["new_vs_returning_conversion_ratio"]["from"]
    assert "capacity_orders_per_week" in card["what_is_a_scenario_assumption"] and "relationship_shares_of_new_customers" in card["what_is_a_scenario_assumption"]


# ------------------------------------------------------------------ calibration comes from the committed public-data profiles
def test_calibration_reads_the_public_profiles():
    snap = C.SNAP
    olist = json.loads((snap / "olist_profile.json").read_text())
    retail = json.loads((snap / "retail_ii_profile.json").read_text())
    shoppers = json.loads((snap / "shoppers_profile.json").read_text())
    cal = C.CALIBRATION
    assert cal["repeat_share_floor"]["value"] == olist["repeat_buying"]["customers_of_small_sellers"]["repeat_customer_share"]
    assert cal["late_delivery_share"]["value"] == olist["delivery"]["small_sellers"]["late_share"]
    assert cal["repeat_gap_days_median"]["value"] == retail["order_metrics"]["days_between_orders_median"]
    assert cal["repeat_gap_days_p90"]["value"] == retail["order_metrics"]["days_between_orders_p90"]
    assert cal["new_vs_returning_conversion_ratio"]["value"] == shoppers["reading"]["new_vs_returning_conversion_ratio"]


def test_lognormal_parameters_reproduce_the_public_quantiles():
    med, p90 = C.CALIBRATION["repeat_gap_days_median"]["value"], C.CALIBRATION["repeat_gap_days_p90"]["value"]
    assert math.exp(C.GAP_MU) == pytest.approx(med)
    assert math.exp(C.GAP_MU + C.Z90 * C.GAP_SIGMA) == pytest.approx(p90, rel=0.01)
    # dispatch delay: median 2 days, and the share beyond 5 days equals Olist's late-delivery share
    z = (math.log(5) - math.log(2)) / C.DISPATCH_SIGMA
    share_over_5 = 0.5 * math.erfc(z / math.sqrt(2))
    assert share_over_5 == pytest.approx(C.CALIBRATION["late_delivery_share"]["value"], abs=0.005)


# ------------------------------------------------------------------ sizes and invariants
def test_size_and_timeline(biz):
    assert 170 <= len(biz.orders) <= 300 and 100 <= len(biz.leads) <= 220
    first, last = d(biz.orders[0]["date"]), d(biz.orders[-1]["date"])
    assert first >= C.HISTORY_START and last < C.END
    assert C.HISTORY_WEEKS == 10 and C.ADVISORY_WEEKS == 4 and (C.END - C.HISTORY_START).days == 98


def test_order_invariants(biz):
    refs = {}
    for o in biz.orders:
        assert o["total"] == o["gross"] - o["discount"] and o["gross"] == sum(i["qty"] * i["price"] for i in o["items"])
        assert all(i["qty"] >= 1 and i["unit_cost"] > 0 for i in o["items"]) and o["relationship"] in ("friend", "friend_of_friend", "stranger")
        if o["dispatched_at"]:
            assert d(o["dispatched_at"]) >= d(o["date"])
        refs.setdefault(o["buyer_ref"], []).append(o)
    for ref, os_ in refs.items():
        assert len({o["relationship"] for o in os_}) == 1                                  # a person keeps one relationship
        dates = sorted(d(o["date"]) for o in os_)
        assert all((b - a).days >= 7 for a, b in zip(dates, dates[1:]))                    # repeats are at least a week apart
    assert [o["order_id"] for o in biz.orders] == sorted(o["order_id"] for o in biz.orders)


def test_repeat_behaviour_is_calibrated_not_arbitrary(biz):
    per = Counter(o["buyer_ref"] for o in biz.orders)
    share = sum(1 for v in per.values() if v >= 2) / len(per)
    assert C.CALIBRATION["repeat_share_floor"]["value"] < share < 0.20
    late = [(d(o["dispatched_at"]) - d(o["date"])).days for o in biz.orders if o["dispatched_at"]]
    assert statistics.median(late) == 2 and sum(x > 5 for x in late) / len(late) < 0.15


def test_box_box_story_most_orders_from_the_circle(box):
    by = {}
    for o in box.orders:
        p = G.period_of(d(o["date"]))
        by.setdefault(p, Counter())[o["relationship"]] += 1
    hist = by["history"]
    assert 0.08 <= hist["stranger"] / sum(hist.values()) <= 0.20 and hist["friend"] > hist["friend_of_friend"] > hist["stranger"]
    assert by["week_4"]["stranger"] / sum(by["week_4"].values()) > hist["stranger"] / sum(hist.values())   # the scripted replay after the advice
    assert any("Ferrari" in p["name"] or "McLaren" in p["name"] for p in box.profile["products"])           # protected terms, on purpose
    assert len(box.stockouts) == 2 and box.turned_away == []


def test_baker_story_capacity(baker):
    cap = baker.profile["capacity_orders_per_week"]
    weekly = Counter((d(o["date"]) - C.HISTORY_START).days // 7 for o in baker.orders)
    assert max(weekly.values()) <= cap and len(baker.turned_away) > 20
    assert baker.stockouts == [] and baker.profile["serves"]["cities"] == ["Pune"]


def test_event_windows_raise_demand_as_assumed(box):
    ctx = G.context_days("f1_calendar")
    assert len(ctx) >= 6
    days = [C.HISTORY_START + timedelta(days=i) for i in range(98)]
    per_day = Counter(d(o["date"]) for o in box.orders)
    inside = sum(per_day[x] for x in days if x in ctx) / sum(1 for x in days if x in ctx)
    outside = sum(per_day[x] for x in days if x not in ctx) / sum(1 for x in days if x not in ctx)
    assert inside > 1.15 * outside


def test_costs_and_profile(biz):
    for p in biz.profile["products"]:
        assert p["unit_cost"] == biz.costs[p["name"]]["full"] and biz.costs[p["name"]]["source"] == "estimate"
        assert p["price"] > p["unit_cost"]
    f = biz.profile["fields"]
    assert f["ad_budget_inr"] == {"value": 0, "source": "exact"} and f["capacity_orders_per_week"]["source"] == "estimate"
    assert biz.profile["constraints"]["forbidden_actions"] == ["paid_ads"]


# ------------------------------------------------------------------ facts
FACT_KEYS = {"fact_id", "kpi", "bottleneck", "dimension", "period", "value", "unit", "baseline", "best_period", "delta_pct", "gap_to_best", "better",
             "numerator", "denominator", "definition_version", "quality_flag", "source", "sample_size", "sample_kind", "snapshot", "synthetic", "direction", "origin"}


def test_facts_shape_and_coverage(biz):
    fs = F.compute(biz, 1)
    assert len(fs) == 23 and all(set(f) == FACT_KEYS for f in fs)
    assert {f["bottleneck"] for f in fs} == {"reach", "conversion", "margin", "repeat_orders", "capacity"}
    assert len({f["fact_id"] for f in fs}) == 23 and fs[0]["period"] == {"from": "2026-09-07", "to": "2026-10-04"}
    assert all(f["definition_version"] == "v2" and f["snapshot"] == "week_1" and f["synthetic"] is True for f in fs)
    assert {"f_stranger_orders_week", "f_stranger_share", "f_margin_pct", "f_repeat_customer_share", "f_orders_turned_away"} <= {f["fact_id"] for f in fs}


def test_facts_by_hand(box):
    fs = {f["fact_id"]: f for f in F.compute(box, 1)}
    a, b = date(2026, 9, 7), date(2026, 10, 4)
    win = [o for o in box.orders if a <= d(o["date"]) <= b]
    strangers = [o for o in win if o["relationship"] == "stranger"]
    assert fs["f_stranger_orders_week"]["value"] == pytest.approx(len(strangers) / 4, abs=0.01) and fs["f_stranger_orders_week"]["numerator"] == len(strangers)
    assert fs["f_stranger_share"]["value"] == pytest.approx(len(strangers) / len(win), abs=1e-4) and fs["f_stranger_share"]["sample_size"] == len(win)
    revenue = sum(o["total"] for o in win)
    cost = sum(i["qty"] * i["unit_cost"] for o in win for i in o["items"])
    assert fs["f_margin_pct"]["value"] == pytest.approx((revenue - cost) / revenue, abs=1e-4)
    assert fs["f_margin_per_order"]["value"] == pytest.approx((revenue - cost) / len(win), abs=0.01)
    gross = sum(o["gross"] for o in win)
    assert fs["f_discount_share"]["value"] == pytest.approx(sum(o["discount"] for o in win) / gross, abs=1e-4)
    posts = [p for p in box.posts if a <= d(p["date"]) <= b]
    assert fs["f_reach_per_post"]["value"] == pytest.approx(sum(p["reach"] for p in posts) / len(posts), abs=0.01)
    seen = Counter(o["buyer_ref"] for o in box.orders if d(o["date"]) <= b)
    assert fs["f_repeat_customer_share"]["value"] == pytest.approx(sum(1 for v in seen.values() if v >= 2) / len(seen), abs=1e-4)
    assert fs["f_capacity_utilisation"]["value"] == pytest.approx(len(win) / 4 / box.profile["capacity_orders_per_week"], abs=1e-3)


def test_baseline_is_the_owns_best_window(biz):
    for f in F.compute(biz, 1):
        if f["better"] == "higher" and f["baseline"] is not None:
            assert f["baseline"] >= f["value"] - 1e-9 and f["gap_to_best"] == pytest.approx(max(0, (f["baseline"] - f["value"]) / f["baseline"]), abs=1e-3)
        if f["better"] == "lower" and f["baseline"] not in (None, 0):
            assert f["baseline"] <= f["value"] + 1e-9
        if f["better"] == "info":
            assert f["baseline"] is None and f["gap_to_best"] is None
    fs = {f["fact_id"]: f for f in F.compute(biz, 1)}
    assert fs["f_orders_turned_away"]["better"] == "lower"


def test_point_in_time_week_1_never_sees_week_2(box):
    as_of = as_of_for(1)
    trimmed = copy.deepcopy(box)
    trimmed.orders = [o for o in trimmed.orders if d(o["date"]) < as_of]
    trimmed.posts = [p for p in trimmed.posts if d(p["date"]) < as_of]
    trimmed.leads = [l for l in trimmed.leads if d(l["created"]) < as_of]
    trimmed.turned_away = [t for t in trimmed.turned_away if d(t["date"]) < as_of]
    for o in trimmed.orders:                                                   # a dispatch that happens after the snapshot is invisible
        if o["dispatched_at"] and d(o["dispatched_at"]) >= as_of:
            o["dispatched_at"] = None
    for l in trimmed.leads:
        l["signals"] = [s for s in l["signals"] if d(s["date"]) < as_of]
        if l["outcome_date"] and d(l["outcome_date"]) >= as_of:
            l["outcome"], l["outcome_date"] = "open", None
    full = [(f["fact_id"], f["value"], f["baseline"]) for f in F.compute(box, 1)]
    cut = [(f["fact_id"], f["value"], f["baseline"]) for f in F.compute(trimmed, 1)]
    assert full == cut
    assert full != [(f["fact_id"], f["value"], f["baseline"]) for f in F.compute(box, 2)]


def test_the_data_decides_which_bottleneck_is_big(box, baker):
    b = {f["fact_id"]: f for f in F.compute(box, 1)}
    assert b["f_stranger_orders_week"]["gap_to_best"] > 0.4 and b["f_stranger_share"]["gap_to_best"] > 0.3
    assert b["f_margin_pct"]["gap_to_best"] < 0.05 and b["f_orders_turned_away"]["value"] == 0 and b["f_capacity_utilisation"]["value"] < 0.7
    k = {f["fact_id"]: f for f in F.compute(baker, 1)}
    assert k["f_capacity_utilisation"]["value"] > 0.85 and k["f_orders_turned_away"]["value"] > 0 and k["f_orders_turned_away"]["gap_to_best"] > 0.5
    assert k["f_stranger_share"]["gap_to_best"] < 0.05                                          # reach is NOT the baker's problem


def test_replay_weeks_show_the_advice_working_for_box_box(box):
    v = [{f["fact_id"]: f for f in F.compute(box, w)}["f_stranger_orders_week"]["value"] for w in (1, 2, 3, 4)]
    assert v[0] < v[1] < v[3] and v[3] >= 3.5


def test_weekly_series(box):
    s = F.weekly_series(box, "f_stranger_orders_week", 2)
    assert s["fact_id"] == "f_stranger_orders_week" and len(s["points"]) == 11 and s["points"][0]["from"] == "2026-07-27"
    assert sum(p["value"] for p in s["points"]) == sum(1 for o in box.orders if o["relationship"] == "stranger" and d(o["date"]) < as_of_for(2))
    with pytest.raises(KeyError):
        F.weekly_series(box, "nope", 1)


# ------------------------------------------------------------------ thin data and the zero-best rule
def _tiny(n_orders: int):
    prof = {"business_id": "biz_tiny", "synthetic": False, "products": [{"name": "A", "category": "x", "price": 100, "unit_cost": 60}],
            "capacity_orders_per_week": 10, "serves": {}, "fields": {}}
    orders = []
    for i in range(n_orders):
        day = date(2026, 8, 3) + timedelta(days=(i * 56) // max(1, n_orders))
        orders.append({"order_id": f"O{i}", "date": day.isoformat(), "buyer_ref": f"b{i % 7}", "items": [{"name": "A", "category": "x", "qty": 1, "price": 100, "unit_cost": 60}],
                       "gross": 100, "discount": 0, "total": 100, "payment": "upi", "channel": "whatsapp", "relationship": "friend" if i % 3 else "stranger",
                       "post_id": None, "dispatched_at": (day + timedelta(days=1)).isoformat(), "status": "delivered", "synthetic": False})
    return BusinessData(key="tiny", profile=prof, orders=orders, meta={"history_start": "2026-08-03", "advisory_start": "2026-09-28", "max_week": 1})


def test_thin_data_is_marked_estimate_and_partial():
    t = _tiny(12)
    fs = F.compute(t, 1)
    sr = next(f for f in fs if f["fact_id"] == "f_stranger_share")
    in_window = sum(1 for o in t.orders if date(2026, 8, 31) <= d(o["date"]) <= date(2026, 9, 27))
    assert sr["sample_size"] == in_window and in_window < 30 and sr["quality_flag"] == "partial" and sr["source"] == "estimate"


def test_not_enough_history_is_an_error_not_a_guess():
    t = _tiny(40)
    t.meta["advisory_start"] = "2026-08-24"           # only 3 weeks before the snapshot
    with pytest.raises(ValueError):
        F.compute(t, 1)


def test_zero_best_gap_rule():
    fs = {f["fact_id"]: f for f in F.compute(_tiny(60), 1)}
    assert fs["f_stockouts"]["value"] == 0 and fs["f_stockouts"]["gap_to_best"] == 0.0
