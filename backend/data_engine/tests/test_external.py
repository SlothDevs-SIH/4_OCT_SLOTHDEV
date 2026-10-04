"""Public data: order metrics, Online Retail II validation, F1 calendar, page-view uplift, API."""
import json
from datetime import date

import pytest
from fastapi.testclient import TestClient

from backend.data_engine import importer, ordermetrics as om, public
from backend.data_engine.external import f1_calendar as cal, f1_interest as interest, retail
from backend.data_engine.main import app

client = TestClient(app)


def O(oid, day, cust, rev):
    return om.Order(oid, date.fromisoformat(day), cust, rev)


# ------------------------------------------------------------------ order metrics (hand calculated)
def test_order_metrics_by_hand():
    orders = [O("1", "2026-01-01", "A", 100), O("2", "2026-01-11", "A", 100), O("3", "2026-02-10", "A", 100),   # A: 3 orders, gaps 10 and 30
              O("4", "2026-01-05", "B", 50),                                                                  # B: 1 order
              O("5", "2026-01-06", "C", 25), O("6", "2026-01-26", "C", 25),                                    # C: 2 orders, gap 20
              O("7", "2026-01-07", None, 10)]                                                                  # no customer
    s = om.summarize(orders)
    assert (s["orders"], s["orders_without_customer"], s["customers"], s["repeat_customers"]) == (7, 1, 3, 2)
    assert s["repeat_customer_share"] == pytest.approx(2 / 3, abs=1e-4)
    assert s["revenue_total"] == 410 and s["average_order_value"] == pytest.approx(410 / 7, abs=0.01)
    assert s["days_between_orders_median"] == 20 and s["days_between_orders_p90"] == pytest.approx(28.0)
    # linked revenue: A 300, B 50, C 50 = 400 -> top1 = 0.75, top10 = 1.0, 80% needs A (75%) + one more = 2 of 3 customers
    assert s["concentration"]["top_1"] == 0.75 and s["concentration"]["top_10"] == 1.0
    assert s["concentration"]["customer_share_for_80pct_of_revenue"] == pytest.approx(2 / 3, abs=1e-4)
    assert s["concentration"]["single_customer_over_30pct"] is True
    assert (s["first_order"], s["last_order"]) == ("2026-01-01", "2026-02-10")


def test_order_metrics_edge_cases():
    assert om.summarize([])["repeat_customer_share"] is None
    one = om.summarize([O("1", "2026-01-01", "A", 10)])
    assert one["repeat_customer_share"] == 0 and one["days_between_orders_median"] is None
    assert om.monthly([O("1", "2026-01-31", "A", 5), O("2", "2026-02-01", "A", 7), O("3", "2026-02-02", "B", 3)]) == [
        {"month": "2026-01", "orders": 1, "revenue": 5}, {"month": "2026-02", "orders": 2, "revenue": 10}]


# ------------------------------------------------------------------ Online Retail II parsing
def L(inv, code, qty, price, cust, day="2010-03-01 10:00:00"):
    return {"invoice": inv, "stock_code": code, "description": "x", "quantity": str(qty), "invoice_date": day,
            "price": str(price), "customer_id": cust, "country": "United Kingdom"}


def test_stream_orders_classifies_lines():
    rows = [L("1001", "85123A", 2, 3.0, "17850"), L("1001", "21730", 1, 4.0, "17850"),           # one order of 10.0
            L("C1002", "85123A", -1, 3.0, "17850"),                                              # cancellation
            L("1003", "POST", 1, 18.0, "17850"),                                                 # postage: not a product
            L("1004", "22423", 0, 5.0, "17850"),                                                 # zero quantity
            L("1005", "22423", 3, 2.0, ""),                                                      # no customer id
            L("1006", "22423", 1, 2.0, "12347", "2010-03-05 09:00:00")]
    orders, q = retail.stream_orders(rows)
    assert q["lines"] == 7 and q["cancellation_lines"] == 1 and q["non_product_lines"] == 1
    assert q["non_positive_quantity_or_price_lines"] == 1 and q["missing_customer_id_lines"] == 1
    by_id = {o.order_id: o for o in orders}
    assert set(by_id) == {"1001", "1005", "1006"} and by_id["1001"].revenue == pytest.approx(10.0)
    assert by_id["1005"].customer is None and by_id["1006"].day == date(2010, 3, 5)


def test_import_check_runs_the_real_pipeline_without_the_inr_paise_rule():
    orders = [O("1", "2010-03-01", "A", 18000.0), O("2", "2010-03-02", "B", 25.5), O("3", "2010-03-02", None, 99.0)]
    r = retail.import_check(orders)
    assert r["rows"] == 3 and r["loaded"] == 3 and r["quarantined"] == 0 and r["repaired"] == 0     # 18000 is NOT treated as paise
    assert {"order_id", "ordered_at", "revenue"} <= set(r["mapping_auto_detected"])


def test_the_paise_rule_still_applies_to_inr_files():
    cols = ["Order ID", "Order Date", "Amount"]
    rows = [{"Order ID": "A", "Order Date": "2026-01-01", "Amount": "89900"}]
    m = {"order_id": "Order ID", "ordered_at": "Order Date", "revenue": "Amount"}
    assert importer.run_import("orders", rows, m)["clean"][0]["revenue"] == 899.0
    assert importer.run_import("orders", rows, m, paise=False)["clean"][0]["revenue"] == 89900.0


@pytest.mark.skipif(not retail.PROFILE.exists(), reason="profile not built (python -m backend.data_engine.external.retail --profile)")
def test_committed_retail_profile_is_consistent():
    p = retail.load_profile()
    assert p["licence"] == "CC BY 4.0" and "Chen" in p["citation"] and "not a benchmark" in p["role"]
    assert p["source_lines"] == retail.EXPECTED_LINES
    m = p["order_metrics"]
    assert m["orders"] == p["quality"]["orders"] and m["customers"] > 5000
    assert 0 < m["repeat_customer_share"] < 1 and 0 < m["concentration"]["top_10"] < 1
    assert p["intake_check"]["quarantined"] == 0 and p["intake_check"]["mapping_auto_detected"]["revenue"]
    assert p["intake_check"]["confidence"] == 1.0              # no campaign column, so nothing is "unattributed"
    assert sum(x["orders"] for x in p["monthly"]) == m["orders"]


@pytest.mark.skipif(not retail.CSV_PATH.exists() or not retail.PROFILE.exists(), reason="dataset CSV not converted")
def test_profile_matches_a_fresh_run_on_the_real_file():
    fresh = retail.build_profile()
    stored = retail.load_profile()
    assert fresh["order_metrics"] == stored["order_metrics"] and fresh["quality"] == stored["quality"]


# ------------------------------------------------------------------ F1 calendar
def test_calendar_snapshots():
    assert {2025, 2026} <= set(cal.available_seasons())
    c = cal.calendar(2026)
    assert len(c) == 23 and all(r["weekend_start"] <= r["race_date"] == r["weekend_end"] for r in c)
    assert [r["round"] for r in c] == sorted(r["round"] for r in c)
    assert any(r["sprint_weekend"] for r in c)


def test_weekend_lookup_and_next_race():
    w = cal.weekend_on("2026-10-03")
    assert w and w["race_date"] == "2026-10-04" and w["weekend_start"] == "2026-10-02"
    assert cal.weekend_on("2026-10-06") is None
    nxt = cal.next_race("2026-10-05")
    assert nxt["name"] == "Singapore Grand Prix" and nxt["days_until_race"] == 6
    assert cal.next_race("2026-10-04")["days_until_race"] == 0
    assert cal.next_race("2026-12-30") is None                      # season over and no snapshot for 2027 yet


def test_race_weekends_in_range_and_windows():
    names = [r["name"] for r in cal.race_weekends(2026, "2026-10-04", "2026-10-31")]
    assert "Singapore Grand Prix" in names and len(names) == 4
    assert cal.race_weekends(2026, "2026-01-01", "2026-02-01") == []
    w = cal.demand_windows(2026)[0]
    assert w["build_up"][1] < w["weekend"][0] and w["tail"][0] > w["weekend"][1]
    start = date.fromisoformat(w["build_up"][0])
    assert (date.fromisoformat(w["weekend"][0]) - start).days == 7


# ------------------------------------------------------------------ interest uplift
def test_uplift_arithmetic_on_a_synthetic_series():
    race = cal.calendar(2026)[0]
    series = {}
    d = date(2026, 1, 1)
    while d <= date(2026, 12, 31):
        series[d.isoformat()] = 100
        d = date.fromordinal(d.toordinal() + 1)
    from datetime import timedelta
    day = date.fromisoformat(race["weekend_start"])
    while day <= date.fromisoformat(race["weekend_end"]):
        series[day.isoformat()] = 300
        day += timedelta(days=1)
    u = interest.uplift((2026,), series)
    assert u["seasons"]["2026"]["mean_views_weekend"] > 100 and u["overall"]["uplift"] > 1.0


def test_real_page_views_show_race_weekends_lift_interest():
    u = interest.uplift()
    assert u["overall"]["uplift"] > 1.5 and u["overall"]["weekend_days"] > 100 and u["overall"]["other_days"] > 400
    assert set(u["seasons"]) == {"2025", "2026"} and "not sales of any brand" in u["caveat"]
    snap = interest.load()
    assert "CC0" in snap["licence"] and snap["article"] == "Formula_One" and len(snap["series"]) > 600


# ------------------------------------------------------------------ API
def test_api_market_context():
    r = client.get("/api/v1/market-context?from=2026-10-04&to=2026-10-31")
    assert r.status_code == 200
    b = r.json()
    assert len(b["race_weekends"]) == 4 and b["next_race"]["name"] and b["interest_uplift"]["overall"]["uplift"] > 1.5
    assert "not any brand" in b["note"]
    assert client.get("/api/v1/market-context?from=2020-01-01").status_code == 422


def test_api_public_data_lists_licences_roles_and_results():
    r = client.get("/api/v1/public-data").json()
    names = {d["name"]: d for d in r["datasets"]}
    assert names["UCI Online Retail II"]["licence"] == "CC BY 4.0" and "not a benchmark" in names["UCI Online Retail II"]["role"]
    assert "non-commercial" in names["Olist Brazilian E-Commerce"]["licence"]
    assert names["UCI Bank Marketing"]["status"] == "integrated" and "sanity check" in names["UCI Bank Marketing"]["role"]
    assert names["F1 race calendar (Jolpica-F1)"]["status"] == "integrated"
    assert names["Wikipedia page views: Formula One"]["result"]["uplift"] > 1.5
    assert "no stated licence" in r["not_used"] and "M5" in r["not_used"]
    assert len(r["datasets"]) == 6


# ------------------------------------------------------------------ Olist and Online Shoppers (profiles)
from backend.data_engine.external import olist, shoppers


@pytest.mark.skipif(not olist.PROFILE.exists(), reason="Olist profile not built")
def test_olist_profile_is_consistent():
    p = olist.load_profile()
    assert p["orders"] == 99441 and p["sellers"]["total"] == 3095 and p["products"]["categories"] == 73
    assert "non-commercial" in p["licence"] and "Olist" in p["citation"]
    assert sum(p["sellers"]["by_orders_per_seller"].values()) == p["sellers"]["total"]
    assert p["sellers"]["small_sellers_50_to_500_orders"] == p["sellers"]["by_orders_per_seller"]["50-500"]
    rep = p["repeat_buying"]
    assert 0 < rep["customers_of_small_sellers"]["repeat_customer_share"] < rep["all_customers"]["repeat_customer_share"] < 0.1
    assert sum(p["reviews"]["score_distribution"].values()) == p["reviews"]["count"]
    assert 0 < p["delivery"]["all"]["late_share"] < 0.2


@pytest.mark.skipif(olist.locate() is None or not olist.PROFILE.exists(), reason="Olist files not present")
def test_olist_profile_matches_a_fresh_run():
    assert json.loads(json.dumps(olist.build_profile())) == olist.load_profile()      # JSON turns tuples into lists


@pytest.mark.skipif(not shoppers.PROFILE.exists(), reason="Online Shoppers profile not built")
def test_shoppers_profile_supports_the_signal_directions():
    p = shoppers.load_profile()
    assert p["sessions"] == 12330 and p["purchases"] == 1908 and p["overall_conversion"] == pytest.approx(0.1547, abs=1e-4)
    v = p["by_visitor_type"]
    assert v["New_Visitor"]["sessions"] + v["Returning_Visitor"]["sessions"] + v["Other"]["sessions"] == 12330
    assert p["by_page_value"]["page_value > 0"]["conversion"] > 10 * p["by_page_value"]["page_value = 0"]["conversion"]   # intent >> light interest
    pages = p["by_product_pages_viewed"]
    assert pages["0-9 product pages"]["conversion"] < pages["10-49"]["conversion"] < pages["50+"]["conversion"]


@pytest.mark.skipif(not shoppers.CSV_PATH.exists() or not shoppers.PROFILE.exists(), reason="Online Shoppers file not present")
def test_shoppers_profile_matches_a_fresh_run():
    assert shoppers.build_profile() == shoppers.load_profile()
