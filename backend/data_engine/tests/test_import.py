"""CSV import: mapping suggestions, repairs, quarantine, report shape, API flow, checked against ground truth."""
import io

import pytest
from fastapi.testclient import TestClient

from backend.common.fixtures import load_fixture
from backend.data_engine import importer, store
from backend.data_engine.main import app
from backend.data_engine.synth import messy
from backend.data_engine.synth.generate import build_tenant

client = TestClient(app)


@pytest.fixture(scope="module")
def truth():
    return messy.ground_truth()


@pytest.fixture(scope="module")
def demo_job():
    return store.ensure_demo_import()


def _csv(header, *rows):
    return (",".join(header) + "\n" + "\n".join(",".join(r) for r in rows) + "\n").encode()


# ------------------------------------------------------------------ mapping
def test_messy_headers_are_mapped_automatically(demo_job):
    s = demo_job["suggested"]
    assert all(s[f]["column"] for f in ("order_id", "ordered_at", "revenue", "channel", "campaign_id", "payment_mode", "status"))
    assert s["revenue"]["column"] == "Order Amount (INR)" and s["campaign_id"]["column"] == "UTM Campaign"
    assert len({m["column"] for m in s.values() if m["column"]}) == len([m for m in s.values() if m["column"]])  # no column used twice


def test_unrecognised_headers_are_left_unmapped():
    s = importer.suggest_mapping("orders", ["foo", "bar"])
    assert all(m["column"] is None for m in s.values())
    assert importer.missing_required("orders", {}) == ["order_id", "ordered_at", "revenue"]


# ------------------------------------------------------------------ the planted defects are found exactly
def test_defect_counts_match_what_was_injected(demo_job, truth):
    run = demo_job["run"]
    assert run["rows_total"] == truth["rows_total"] == truth["orders"] + truth["duplicates"]
    assert run["duplicates_merged"] == truth["duplicates"]
    assert run["rows_quarantined"] == truth["missing_campaign"]
    by = {i["code"]: i["count"] for i in run["issues"]}
    assert by["duplicate_order"] == 25 and by["missing_campaign_id"] == 47
    assert by["mixed_date_format"] == truth["dmy_dates"] and by["amount_in_paise"] == truth["paise"]
    assert run["unattributed"] == truth["unattributed_orders"]
    assert run["rows_loaded"] == run["rows_total"] - run["rows_quarantined"] - run["duplicates_merged"]


def test_cleaned_rows_equal_the_original_orders(demo_job, truth):
    t = build_tenant("baseline")
    orig = {o["order_id"]: o for o in t.orders}
    clean = {c["order_id"]: c for c in demo_job["run"]["clean"]}
    assert set(clean) == set(orig) - set(truth["missing_ids"])
    for oid, c in clean.items():
        o = orig[oid]
        assert c["revenue"] == o["revenue"], oid                       # paise repaired
        assert c["ordered_at"][:10] == o["ordered_at"][:10], oid       # dates repaired to ISO
        assert c["channel"] == o["channel"] and c["payment_mode"] == o["payment_mode"] and c["status"] == o["status"]
    assert sum(c["revenue"] for c in clean.values()) == truth["total_revenue"] - sum(orig[i]["revenue"] for i in truth["missing_ids"])


def test_quarantine_only_touches_orders_outside_the_kpi_windows(demo_job):
    assert all(q["raw"]["Order Date"][:10] < "2026-08-30" or "/" in q["raw"]["Order Date"] for q in demo_job["run"]["quarantined"])
    t = build_tenant("baseline")
    orig = {o["order_id"]: o for o in t.orders}
    assert all(orig[q["raw"]["Order ID"]]["ordered_at"][:10] < "2026-08-30" for q in demo_job["run"]["quarantined"])


def test_report_matches_the_contract_shape(demo_job):
    fixture_import = load_fixture("data_quality")["imports"][0]
    report = importer.report_for(demo_job["import_id"], "orders", demo_job["run"])
    assert set(report) == set(fixture_import)
    assert {"code", "count", "action", "example"} <= set(report["issues"][0])
    assert {i["code"] for i in report["issues"]} <= {i["code"] for i in fixture_import["issues"]} | {"invalid_date", "invalid_amount", "missing_required", "conflicting_duplicate"}


# ------------------------------------------------------------------ rules on small files
def test_rules_on_a_small_file():
    cols = ["id", "date", "amount", "source", "campaign"]
    rows = [
        {"id": "A1", "date": "2026-09-01", "amount": "899", "source": "instagram", "campaign": "Reels"},      # clean
        {"id": "A1", "date": "2026-09-01", "amount": "899", "source": "instagram", "campaign": "Reels"},      # duplicate merged
        {"id": "A2", "date": "03/10/2026", "amount": "Rs. 1,299", "source": "google", "campaign": "Brand"},    # date + comma repaired
        {"id": "A3", "date": "2026-09-02", "amount": "89900", "source": "email", "campaign": ""},             # paise, unattributed
        {"id": "A4", "date": "2026-09-02", "amount": "499", "source": "instagram", "campaign": ""},          # paid, no campaign: quarantined
        {"id": "A5", "date": "not a date", "amount": "499", "source": "email", "campaign": "N"},             # invalid date
        {"id": "A6", "date": "2026-09-03", "amount": "abc", "source": "email", "campaign": "N"},             # invalid amount
        {"id": "A7", "date": "2026-09-03", "amount": "100", "source": "email", "campaign": "N"},
        {"id": "A7", "date": "2026-09-03", "amount": "200", "source": "email", "campaign": "N"},             # conflicting duplicate
        {"id": "", "date": "2026-09-03", "amount": "100", "source": "email", "campaign": "N"},               # missing id
    ]
    mapping = {"order_id": "id", "ordered_at": "date", "revenue": "amount", "channel": "source", "campaign_id": "campaign"}
    run = importer.run_import("orders", rows, mapping)
    by = {i["code"]: i["count"] for i in run["issues"]}
    assert by == {"duplicate_order": 1, "missing_campaign_id": 1, "mixed_date_format": 1, "amount_in_paise": 1,
                  "invalid_date": 1, "invalid_amount": 1, "conflicting_duplicate": 1, "missing_required": 1, "unattributed": 1}
    assert [c["order_id"] for c in run["clean"]] == ["A1", "A2", "A3", "A7"]
    a2, a3 = run["clean"][1], run["clean"][2]
    assert a2["ordered_at"] == "2026-10-03T00:00:00Z" and a2["revenue"] == 1299.0
    assert a3["revenue"] == 899.0 and a3["campaign_id"] is None
    assert (run["rows_total"], run["rows_loaded"], run["rows_quarantined"], run["duplicates_merged"]) == (10, 4, 5, 1)
    q, r, u = 5 / 10, 2 / 10, 1 / 10
    assert run["confidence"] == round(max(0, 1 - 2 * q - 0.5 * r - 0.5 * u), 2)


def test_badge_thresholds():
    assert (importer.badge(0.9), importer.badge(0.75), importer.badge(0.5)) == ("high", "medium", "low")


def test_leads_import_uses_the_same_engine():
    cols = ["Lead ID", "Created", "Source", "Deal Value", "Status"]
    rows = [{"Lead ID": "L1", "Created": "2026-10-01", "Source": "WhatsApp", "Deal Value": "42,000", "Status": "Closed Won"}]
    s = importer.suggest_mapping("leads", cols)
    run = importer.run_import("leads", rows, {f: m["column"] for f, m in s.items() if m["column"]})
    assert run["clean"][0]["stage"] == "won" and run["clean"][0]["channel"] == "whatsapp" and run["clean"][0]["expected_value_inr"] == 42000.0


# ------------------------------------------------------------------ API flow
def test_full_api_flow_with_the_downloadable_sample():
    csv_text = client.get("/api/v1/demo/sample-import/orders.csv")
    assert csv_text.status_code == 200 and csv_text.headers["content-type"].startswith("text/csv")
    up = client.post("/api/v1/businesses/biz_aarohi_skin/imports?kind=orders",
                     files={"file": ("orders.csv", csv_text.content, "text/csv")})
    assert up.status_code == 201, up.text
    body = up.json()
    assert body["status"] == "uploaded" and body["rows_total"] == 3015 and body["missing_required"] == []
    assert client.get(f"/api/v1/imports/{body['import_id']}/report").status_code == 409   # not confirmed yet
    mapping = {f: m["column"] for f, m in body["suggested_mapping"].items() if m["column"]}
    rep = client.post(f"/api/v1/imports/{body['import_id']}/confirm", json={"mapping": mapping})
    assert rep.status_code == 200, rep.text
    r = rep.json()
    assert (r["rows_total"], r["rows_quarantined"], r["duplicates_merged"]) == (3015, 47, 25) and r["status"] == "loaded"
    assert client.get(f"/api/v1/imports/{body['import_id']}/report").json() == r
    qr = client.get(f"/api/v1/imports/{body['import_id']}/quarantine?limit=5").json()
    assert qr["total"] == 47 and len(qr["rows"]) == 5 and qr["rows"][0]["reason_code"] == "missing_campaign_id"


def test_auto_import_endpoint():
    data = _csv(["Order #", "Placed At", "Total", "Source", "Campaign"],
                ["B1", "2026-09-01", "500", "email", "N"], ["B2", "02/09/2026", "700", "whatsapp", ""])
    r = client.post("/api/v1/businesses/biz_aarohi_skin/imports/auto?kind=orders", files={"file": ("o.csv", data, "text/csv")})
    assert r.status_code == 201, r.text
    assert r.json()["report"]["rows_loaded"] == 2 and r.json()["report"]["rows_repaired"] == 1


def test_import_errors():
    ok = _csv(["Order ID", "Order Date", "Amount"], ["1", "2026-09-01", "5"])
    assert client.post("/api/v1/businesses/biz_nope/imports?kind=orders", files={"file": ("a.csv", ok)}).status_code == 404
    assert client.post("/api/v1/businesses/biz_aarohi_skin/imports?kind=orders", files={"file": ("a.csv", b"")}).json()["error"]["code"] == "invalid_csv"
    assert client.post("/api/v1/businesses/biz_aarohi_skin/imports?kind=widgets", files={"file": ("a.csv", ok)}).status_code == 422
    up = client.post("/api/v1/businesses/biz_aarohi_skin/imports?kind=orders", files={"file": ("a.csv", _csv(["x", "y"], ["1", "2"]))}).json()
    assert up["missing_required"] == ["order_id", "ordered_at", "revenue"]
    bad = client.post(f"/api/v1/imports/{up['import_id']}/confirm", json={"mapping": {"order_id": "x"}})
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "missing_required_mapping"
    unknown = client.post(f"/api/v1/imports/{up['import_id']}/confirm", json={"mapping": {"order_id": "nope", "ordered_at": "x", "revenue": "y"}})
    assert unknown.json()["error"]["code"] == "unknown_column"
    assert client.post("/api/v1/imports/imp_missing/confirm", json={"mapping": {}}).status_code == 404


def test_demo_import_and_data_quality():
    r = client.post("/api/v1/demo/import-sample").json()
    assert r["import_id"] == store.DEMO_IMPORT_ID and r["report"]["rows_quarantined"] == 47
    dq = client.get("/api/v1/businesses/biz_aarohi_skin/data-quality").json()
    fixture = load_fixture("data_quality")
    assert set(fixture) - {"generated_at"} <= set(dq)
    assert set(fixture["overall"]) == set(dq["overall"]) and dq["overall"]["badge"] in ("high", "medium", "low")
    assert dq["kpi_quality"] == fixture["kpi_quality"]
    assert 0 < dq["overall"]["unattributed_revenue_pct"] < 15 and dq["synthetic"] is True
    assert client.get("/api/v1/imports/imp_aarohi_orders_messy/report").json()["rows_total"] == 3015


def test_business_without_imports_has_no_badge():
    client.post("/api/v1/businesses", json={"name": "Quiet Brand", "goal": {"statement": "Grow repeat"}})
    dq = client.get("/api/v1/businesses/biz_quiet_brand/data-quality").json()
    assert dq["overall"]["badge"] == "none" and dq["imports"] == [] and dq["synthetic"] is False
