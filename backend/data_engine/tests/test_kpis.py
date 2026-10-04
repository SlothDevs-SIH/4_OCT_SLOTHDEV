"""KPI engine: matches the contract fixtures, hand calculations, point-in-time rule, API."""
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient

from backend.common.fixtures import load_fixture
from backend.data_engine import kpis, public, store
from backend.data_engine.main import app
from backend.data_engine.synth import config as C
from backend.data_engine.synth.generate import build_tenant

client = TestClient(app)

# Baselines that differ from the fixtures on purpose: the fixtures' baselines are not mutually consistent
# (e.g. orders 158 with repeat rate 0.2 and blended CAC 349.1 cannot all hold), so the engine derives them
# from the data. The current-week VALUES are all exact.
BASELINES_THAT_DIFFER = {"f_cac_blended", "f_orders_total", "f_aov", "f_repeat_rate", "f_latency_hot_leads",
                         "f_repeat_email", "f_cac_google", "f_hot_lead_wins", "f_unattended_hot_leads"}


@pytest.fixture(scope="module")
def base():
    return {f["fact_id"]: f for f in kpis.compute_facts("baseline")}


@pytest.fixture(scope="module")
def day7():
    return {f["fact_id"]: f for f in kpis.compute_facts("day7")}


def _same(a, b, rel=0.002):
    return a == b or (a is not None and b is not None and abs(a - b) <= max(0.0006, rel * abs(b)))


def test_all_23_facts_with_the_contract_shape(base):
    fixture = {f["fact_id"]: f for f in load_fixture("kpi_facts")}
    assert set(base) == set(fixture) and len(base) == 23
    for fid, f in base.items():
        assert set(f) == set(fixture[fid]), fid
        assert f["snapshot"] == "baseline" and f["definition_version"] == "v1" and f["quality_flag"] in ("ok", "partial", "low")


def test_current_week_values_match_the_fixtures_exactly(base):
    for fid, fx in {f["fact_id"]: f for f in load_fixture("kpi_facts")}.items():
        m = base[fid]
        assert _same(m["value"], fx["value"]), (fid, m["value"], fx["value"])
        assert m["period"] == fx["period"] and m["unit"] == fx["unit"] and m["dimension"] == fx["dimension"], fid
        if fid != "f_gross_margin":
            assert _same(m["numerator"], fx["numerator"]) and _same(m["denominator"], fx["denominator"]), fid
        assert m["quality_flag"] == fx["quality_flag"], fid


def test_baselines_match_the_fixtures_except_the_documented_ones(base):
    for fid, fx in {f["fact_id"]: f for f in load_fixture("kpi_facts")}.items():
        if fid in BASELINES_THAT_DIFFER:
            continue
        assert _same(base[fid]["baseline"], fx["baseline"], rel=0.005), (fid, base[fid]["baseline"], fx["baseline"])
        assert base[fid]["delta_pct"] == pytest.approx(fx["delta_pct"], abs=0.3), fid


def test_day7_values_match_the_fixtures(day7):
    fixture = {f["fact_id"]: f for f in load_fixture("kpi_facts_day7")}
    assert set(fixture) <= set(day7)
    for fid, fx in fixture.items():
        assert _same(day7[fid]["value"], fx["value"]), (fid, day7[fid]["value"], fx["value"])
        assert day7[fid]["period"] == fx["period"] and day7[fid]["snapshot"] == "day7"
        if fx["numerator"] is not None:
            assert _same(day7[fid]["numerator"], fx["numerator"]) and _same(day7[fid]["denominator"], fx["denominator"]), fid


def test_arithmetic_of_every_fact(base, day7):
    for f in list(base.values()) + list(day7.values()):
        if f["numerator"] is not None and f["denominator"] and f["unit"] not in ("count",):
            assert f["numerator"] / f["denominator"] == pytest.approx(f["value"], abs=0.0006 + 0.0005 * abs(f["value"])), f["fact_id"]
        if f["baseline"]:
            assert f["delta_pct"] == pytest.approx((f["value"] - f["baseline"]) / f["baseline"] * 100, abs=0.06), f["fact_id"]


def test_hand_calculations_from_the_raw_rows(base):
    t = build_tenant("baseline")
    wk = [o for o in t.orders if "2026-09-27" <= o["ordered_at"][:10] <= "2026-10-03"]
    revenue = sum(o["revenue"] for o in wk)
    assert base["f_revenue_total"]["value"] == revenue
    assert base["f_aov"]["value"] == pytest.approx(revenue / len(wk), abs=0.05)
    assert base["f_gross_margin"]["value"] == pytest.approx(sum(o["revenue"] - o["cogs"] for o in wk) / revenue, abs=0.0006)
    ig_orders = [o for o in wk if o["channel"] == "instagram"]
    assert base["f_roas_instagram"]["value"] == pytest.approx(sum(o["revenue"] for o in ig_orders) / 36720, abs=0.0006)
    assert base["f_cac_instagram"]["value"] == pytest.approx(36720 / sum(o["is_first_order"] for o in ig_orders), abs=0.05)
    assert base["f_croas_instagram"]["value"] == pytest.approx(0.5 * 50940 / 36720, abs=0.0006)
    assert base["f_repeat_rate"]["numerator"] == sum(not o["is_first_order"] for o in wk)


def test_baseline_window_rule():
    assert kpis.baseline_window(date(2026, 9, 27)) == (date(2026, 8, 30), date(2026, 9, 26))
    assert kpis.baseline_window(date(2026, 10, 5)) == (date(2026, 9, 6), date(2026, 10, 3))


def test_percentile_linear_interpolation():
    assert kpis.percentile([1.5, 2, 3, 4.5, 20, 24, 28, 31, 33, 34, 39, 61], 0.9) == pytest.approx(38.5)
    assert kpis.percentile([], 0.9) == 0.0 and kpis.percentile([7], 0.9) == 7


def test_story_directions(base, day7):
    assert base["f_cac_instagram"]["delta_pct"] > 40 and base["f_croas_instagram"]["delta_pct"] < -25
    assert base["f_latency_hot_leads"]["delta_pct"] > 100 and base["f_unattended_hot_leads"]["value"] == 8
    assert base["f_repeat_email"]["delta_pct"] > 20 and abs(base["f_cac_google"]["delta_pct"]) < 5
    assert day7["f_latency_hot_leads"]["delta_pct"] < 0 and day7["f_hot_lead_wins"]["value"] == 3
    assert day7["f_cac_instagram"]["value"] < base["f_cac_instagram"]["value"]


def test_point_in_time_the_baseline_week_is_the_same_inside_the_day7_data():
    """The day-7 dataset contains follow-ups after the baseline snapshot; viewed at the baseline as_of they must be invisible."""
    ix = kpis.Indexed(build_tenant("day7"))
    ix.as_of = datetime.strptime(build_tenant("baseline").meta["as_of"], "%Y-%m-%dT%H:%M:%SZ")
    a, b = C.CURRENT_START, C.CURRENT_END
    base_ix = kpis.indexed("baseline")
    for fn in (kpis._latency, kpis._unattended, kpis._wins, kpis._qualified, kpis._won, kpis._leads):
        assert fn(ix, a, b) == fn(base_ix, a, b), fn.__name__


def test_late_follow_ups_are_visible_once_as_of_moves_on():
    ix = kpis.indexed("day7")
    assert kpis._unattended(ix, C.CURRENT_START, C.CURRENT_END)[0] == 8      # answered, but only after the week ended
    assert kpis._wins(ix, C.DAY7_START, C.DAY7_END)[0] == 3


def test_custom_period_and_validation():
    facts = kpis.compute_facts("baseline", "2026-09-20", "2026-09-26")
    assert facts[0]["period"] == {"from": "2026-09-20", "to": "2026-09-26"}
    assert next(f for f in facts if f["fact_id"] == "f_cac_instagram")["value"] == pytest.approx(33440 / 81, abs=0.1)
    with pytest.raises(ValueError):
        kpis.compute_facts("baseline", "2026-09-30", "2026-09-20")
    with pytest.raises(ValueError):
        kpis.compute_facts("baseline", "2020-01-01", "2020-01-07")
    with pytest.raises(ValueError):
        kpis.compute_facts("nope")


def test_daily_series_shape_and_incident():
    fixture = load_fixture("kpi_daily")
    d = kpis.daily_series()
    assert set(d) == set(fixture) and d["period"] == fixture["period"] and d["injected_incidents"] == fixture["injected_incidents"]
    assert set(d["series"][0]) == set(fixture["series"][0]) and len(d["series"]) == len(fixture["series"]) == 112
    ig = [r for r in d["series"] if r["channel"] == "instagram" and r["date"] >= "2026-09-27"]
    assert (sum(r["spend"] for r in ig), sum(r["new_customers"] for r in ig)) == (36720, 60)
    assert {r["channel"] for r in kpis.daily_series(channel="google")["series"]} == {"google"}
    assert kpis.daily_series("2026-10-01", "2026-10-03")["series"][0]["date"] == "2026-10-01"


def test_daily_series_is_clean_outside_the_planted_incident():
    """Only the planted spike days stand out (robust z-score), so anomaly detection can be judged fairly."""
    import statistics as st
    for ch, expected in (("instagram", {"2026-09-29", "2026-09-30", "2026-10-01", "2026-10-02", "2026-10-03"}), ("google", set())):
        rows = [r for r in kpis.daily_series(channel=ch)["series"] if r["cac"]]
        pre = [r["cac"] for r in rows if r["date"] < "2026-09-29"]
        med = st.median(pre)
        mad = st.median([abs(c - med) for c in pre])
        flagged = {r["date"] for r in rows if abs(0.6745 * (r["cac"] - med) / mad) > 3.5}
        assert flagged == expected, ch


# ------------------------------------------------------------------ public interface and API
def test_public_interface_defaults_match_what_decision_engine_calls():
    facts = public.get_kpi_facts("biz_aarohi_skin")
    assert len(facts) == 23 and facts[0]["snapshot"] == "baseline"
    assert public.get_kpi_facts("biz_nope") is None
    assert len(public.get_kpi_facts("biz_aarohi_skin", snapshot="day7")) == 23
    assert public.get_kpi_series("biz_aarohi_skin")["series"] and public.get_kpi_series("biz_nope") is None


def test_api_default_snapshot_follows_the_loaded_phase():
    client.post("/api/v1/demo/load?phase=baseline")
    assert client.get("/api/v1/businesses/biz_aarohi_skin/kpis").json()["snapshot"] == "baseline"
    client.post("/api/v1/demo/load?phase=day7")
    try:
        body = client.get("/api/v1/businesses/biz_aarohi_skin/kpis").json()
        assert body["snapshot"] == "day7" and body["facts"][0]["period"]["from"] == "2026-10-05"
        assert client.get("/api/v1/businesses/biz_aarohi_skin/kpis?snapshot=baseline").json()["facts"][0]["period"]["from"] == "2026-09-27"
    finally:
        client.post("/api/v1/demo/load?phase=baseline")


def test_api_errors_and_funnel():
    assert client.get("/api/v1/businesses/biz_nope/kpis").status_code == 404
    r = client.get("/api/v1/businesses/biz_aarohi_skin/kpis?from=2026-09-30&to=2026-09-20")
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_period"
    assert client.get("/api/v1/businesses/biz_aarohi_skin/kpis?snapshot=weird").status_code == 422
    f = client.get("/api/v1/businesses/biz_aarohi_skin/funnel").json()["stages"]
    values = [s["value"] for s in sorted(f, key=lambda s: ["funnel_sessions", "funnel_leads", "funnel_qualified", "funnel_won"].index(s["kpi"]))]
    assert values == sorted(values, reverse=True) and len(values) == 4
    assert client.get("/api/v1/businesses/biz_aarohi_skin/kpis/daily?channel=google").json()["series"][0]["channel"] == "google"
    assert client.get("/api/v1/businesses/biz_nope/kpis/daily").status_code == 404
