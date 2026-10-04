"""The synthetic D2C tenant hits the contract anchors (contracts/fixtures/README.md) and its invariants."""
from datetime import datetime

import pytest

from backend.common.fixtures import load_fixture
from backend.data_engine.synth import config as C
from backend.data_engine.synth.generate import apportion, build_tenant

CUR = (C.CURRENT_START.isoformat(), C.CURRENT_END.isoformat())
BASE = (C.BASELINE_START.isoformat(), C.BASELINE_END.isoformat())
D7 = (C.DAY7_START.isoformat(), C.DAY7_END.isoformat())


def _in(ts, rng):
    return rng[0] <= ts[:10] <= rng[1]


def _daily(t, ch, rng):
    return [r for r in t.daily if r["channel"] == ch and _in(r["date"], rng)]


def _ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


def _p90(values):
    v = sorted(values)
    i = 0.9 * (len(v) - 1)
    lo = int(i)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (i - lo) * (v[hi] - v[lo])


@pytest.fixture(scope="module")
def t():
    return build_tenant("baseline")


@pytest.fixture(scope="module")
def d7():
    return build_tenant("day7")


def test_apportion_preserves_total():
    assert sum(apportion(101, [1, 2, 3.3])) == 101
    assert apportion(0, [1, 1]) == [0, 0]


def test_deterministic_and_phases_share_the_baseline(t, d7):
    again = build_tenant.__wrapped__("baseline")
    assert again.orders == t.orders and again.leads == t.leads
    assert [o for o in d7.orders if o["ordered_at"][:10] <= CUR[1]] == t.orders


def test_everything_is_labelled_synthetic(t):
    assert all(r["synthetic"] for r in t.orders + t.customers + t.leads + t.daily + t.campaigns)
    assert t.meta["synthetic"] is True


def test_instagram_and_google_weekly_anchors(t):
    ig = _daily(t, "instagram", CUR)
    assert (sum(r["spend"] for r in ig), sum(r["sessions"] for r in ig), sum(r["new_customers"] for r in ig),
            sum(r["revenue"] for r in ig)) == (36720, 4000, 60, 50940)
    g = _daily(t, "google", CUR)
    assert (sum(r["spend"] for r in g), sum(r["new_customers"] for r in g), sum(r["revenue"] for r in g)) == (15960, 42, 36540)


def test_instagram_cac_spike_starts_on_the_29th(t):
    ig = {r["date"]: r["cac"] for r in _daily(t, "instagram", ("2026-09-22", "2026-10-03"))}
    before = [v for d, v in ig.items() if d < "2026-09-29"]
    after = [v for d, v in ig.items() if d >= "2026-09-29"]
    assert max(before) < 450 < min(after)


def test_baseline_pooled_values_match_the_fixture_baselines(t):
    ig, g = _daily(t, "instagram", BASE), _daily(t, "google", BASE)
    assert sum(r["spend"] for r in ig) / sum(r["new_customers"] for r in ig) == pytest.approx(410.0, abs=0.05)
    assert sum(r["spend"] for r in g) / sum(r["new_customers"] for r in g) == pytest.approx(372.0, abs=0.05)
    assert sum(r["revenue"] for r in ig) / sum(r["spend"] for r in ig) == pytest.approx(2.07, abs=0.005)


def test_daily_rows_equal_the_orders_behind_them(t):
    for ch in ("instagram", "google"):
        for r in _daily(t, ch, CUR):
            orders = [o for o in t.orders if o["channel"] == ch and o["ordered_at"][:10] == r["date"]]
            assert sum(o["revenue"] for o in orders) == r["revenue"]
            assert sum(o["is_first_order"] for o in orders) == r["new_customers"]


def test_current_week_orders(t):
    wk = [o for o in t.orders if _in(o["ordered_at"], CUR)]
    assert len(wk) == 154
    assert sum(o["revenue"] for o in wk) == 135560
    assert sum(not o["is_first_order"] for o in wk) == 34
    assert sum(o["is_first_order"] for o in wk) == 120          # blended CAC denominator
    assert sum(o["revenue"] - o["cogs"] for o in wk) / 135560 == pytest.approx(0.62, abs=0.005)


def test_email_cohort(t):
    cohort = {c["customer_id"] for c in t.customers if c["email_cohort"]}
    assert len(cohort) == 210
    repeats = {}
    for o in t.orders:
        if not o["is_first_order"] and o["customer_id"] in cohort:
            repeats.setdefault(o["customer_id"], []).append(o["ordered_at"][:10])
    assert sum(any(d <= C.BASELINE_END.isoformat() for d in v) for v in repeats.values()) == 34
    assert sum(any(d <= C.CURRENT_END.isoformat() for d in v) for v in repeats.values()) == 45
    # every cohort member made their first order in August 2026
    first = {c["customer_id"]: c["first_order_at"] for c in t.customers if c["email_cohort"]}
    assert all(v.startswith("2026-08") for v in first.values())


def test_current_week_leads_and_hot_leads(t):
    wk = [l for l in t.leads if _in(l["created_at"], CUR)]
    assert (len(wk), sum(l["stage"] in ("qualified", "won") for l in wk), sum(l["stage"] == "won" for l in wk)) == (152, 61, 23)
    hv = [l for l in wk if l["high_value"]]
    assert len(hv) == 12 and all(l["expected_value_inr"] >= C.HIGH_VALUE_THRESHOLD_INR for l in hv)
    assert sum(not l["first_response_at"] for l in hv) == 8
    lat = [((_ts(l["first_response_at"]) if l["first_response_at"] else C.AS_OF) - _ts(l["created_at"])).total_seconds() / 3600 for l in hv]
    assert _p90(lat) == pytest.approx(38.5, abs=0.01)
    wins = [l for l in t.leads if l["high_value"] and l["won_at"] and _in(l["won_at"], CUR)]
    assert len(wins) == 1
    incomplete = next(l for l in t.leads if l["lead_id"] == "lead_0455")
    assert incomplete["channel"] is None and incomplete["attributes"]["previous_outcome"] is None


def test_day7_replay(d7):
    ig = _daily(d7, "instagram", D7)
    assert (sum(r["spend"] for r in ig), sum(r["sessions"] for r in ig), sum(r["new_customers"] for r in ig),
            sum(r["revenue"] for r in ig)) == (35100, 3850, 62, 52638)
    g = _daily(d7, "google", D7)
    assert (sum(r["spend"] for r in g), sum(r["new_customers"] for r in g)) == (15800, 41)
    hv = [l for l in d7.leads if l["high_value"] and _in(l["created_at"], D7)]
    lat = [((_ts(l["first_response_at"]) if l["first_response_at"] else C.AS_OF_DAY7) - _ts(l["created_at"])).total_seconds() / 3600 for l in hv]
    assert _p90(lat) == pytest.approx(5.5, abs=0.01) and sum(not l["first_response_at"] for l in hv) == 1
    wins = [l for l in d7.leads if l["high_value"] and l["won_at"] and _in(l["won_at"], D7)]
    assert len(wins) == 3
    cohort = {c["customer_id"] for c in d7.customers if c["email_cohort"]}
    repeaters = {o["customer_id"] for o in d7.orders if not o["is_first_order"] and o["customer_id"] in cohort and o["ordered_at"][:10] <= D7[1]}
    assert len(repeaters) == 46


def test_point_in_time_view_of_the_baseline_week_inside_day7(d7):
    """Events after the baseline snapshot time must be invisible when measuring the baseline week."""
    hv = [l for l in d7.leads if l["high_value"] and _in(l["created_at"], CUR)]
    lat = []
    for l in hv:
        seen = l["first_response_at"] and _ts(l["first_response_at"]) <= C.AS_OF
        lat.append(((_ts(l["first_response_at"]) if seen else C.AS_OF) - _ts(l["created_at"])).total_seconds() / 3600)
    assert _p90(lat) == pytest.approx(38.5, abs=0.01)


def test_invariants(t):
    ids = {c["customer_id"] for c in t.customers}
    campaigns = {c["campaign_id"] for c in t.campaigns}
    assert len(t.campaigns) == 18
    assert len({o["order_id"] for o in t.orders}) == len(t.orders)
    assert all(o["customer_id"] in ids for o in t.orders)
    assert all(o["campaign_id"] is None or o["campaign_id"] in campaigns for o in t.orders)
    assert all(0 <= o["discount"] <= 0.25 * o["list_total"] and o["revenue"] == o["list_total"] - o["discount"] for o in t.orders)
    assert all(o["ordered_at"][:10] <= CUR[1] for o in t.orders)
    assert all(l["created_at"][:10] <= CUR[1] for l in t.leads)
    qualified_or_won = sum(l["stage"] in ("qualified", "won") for l in t.leads)
    assert sum(l["stage"] == "won" for l in t.leads) <= qualified_or_won <= len(t.leads)
    firsts = [o for o in t.orders if o["is_first_order"]]
    assert len({o["customer_id"] for o in firsts}) == len(firsts)          # one first order per customer
    cust_first = {c["customer_id"]: c["first_order_at"] for c in t.customers if not c.get("legacy")}
    assert all(cust_first[o["customer_id"]] == o["ordered_at"] for o in firsts)
    for o in t.orders:
        if not o["is_first_order"] and o["customer_id"] in cust_first:     # a repeat comes after the first order
            assert o["ordered_at"] > cust_first[o["customer_id"]]
    assert 0.30 < sum(o["payment_mode"] == "cod" for o in t.orders) / len(t.orders) < 0.45


def test_hot_leads_match_the_contract_fixture_ids(t):
    fixture = {l["lead_id"] for l in load_fixture("lead_scores")["leads"] if l["lead_id"] != "lead_0441"}
    mine = {l["lead_id"] for l in t.leads}
    assert {"lead_0412", "lead_0388", "lead_0397", "lead_0455"} <= mine
    assert fixture - {"lead_0455"} <= mine
