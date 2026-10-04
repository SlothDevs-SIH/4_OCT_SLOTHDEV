"""Contract v2 routes of data_engine: demo businesses, profile, intake, leads, facts, projection, market context."""
import csv
import io
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from backend.data_engine import importer, public
from backend.data_engine.homebiz import generate as G
from backend.data_engine.homebiz import intake, messy
from backend.data_engine.main import app

client = TestClient(app)
API = "/api/v1"


def load(biz="boxbox", week=1):
    r = client.post(f"{API}/demo/load?business={biz}&week={week}")
    assert r.status_code == 200, r.text
    return r.json()


# ------------------------------------------------------------------ demo load, profile, data card
def test_demo_load_both_businesses():
    for biz, bid in (("boxbox", "biz_boxbox"), ("homebaker", "biz_homebaker")):
        r = load(biz, 1)
        assert r["business_id"] == bid and r["synthetic"] is True and r["week"] == 1
        dl = r["demo_load"]
        assert dl["synthetic"] is True and dl["counts"]["orders"] > 150 and dl["import_id"] == f"imp_{biz}_orders_messy"
        assert client.get(f"{API}/businesses/{bid}").json()["business_id"] == bid
    assert client.post(f"{API}/demo/load?business=nope").status_code == 422
    assert client.post(f"{API}/demo/load?business=boxbox&week=9").status_code == 422


def test_profile_has_a_source_on_every_field_and_a_data_card():
    load("boxbox")
    p = client.get(f"{API}/businesses/biz_boxbox/profile").json()
    assert p["synthetic"] is True and all({"value", "source"} <= set(v) and v["source"] in ("exact", "estimate", "derived") for v in p["fields"].values())
    assert p["fields"]["ad_budget_inr"] == {"value": 0, "source": "exact"} and p["data"]["orders"] > 200
    card = client.get(f"{API}/businesses/biz_boxbox/data-card").json()
    assert "Olist" in str(card["what_is_calibrated_on_public_data"]) and card["synthetic"] is True
    assert client.get(f"{API}/businesses/biz_nope/profile").status_code == 404


# ------------------------------------------------------------------ the messy orders sheet goes through the real import
def test_the_demo_import_finds_exactly_the_injected_defects():
    for biz in ("boxbox", "homebaker"):
        load(biz, 1)
        data = G.build(biz)
        rows, truth = messy.build_rows(data, 1)
        dq = client.get(f"{API}/businesses/biz_{biz}/data-quality").json()
        imp = dq["imports"][0]
        by = {i["code"]: i["count"] for i in imp["issues"]}
        assert by["duplicate_order"] == truth["duplicates"] == 6 and by["mixed_date_format"] >= truth["dmy_dates"] - 1
        assert imp["rows_total"] == truth["rows_total"] and imp["rows_quarantined"] == 0 and dq["synthetic"] is True
        assert dq["overall"]["badge"] == "high" and dq["overall"]["confidence"] >= 0.9


def test_cleaned_rows_rebuild_the_original_orders():
    data = G.build("boxbox")
    text = messy.build_csv(data, 1).encode("utf-8")
    cols, rows = importer.parse_csv(text)
    sug = importer.suggest_mapping("orders", cols)
    assert all(sug[f]["column"] for f in ("order_id", "ordered_at", "revenue", "relationship", "items", "dispatched_at", "post_id"))
    run = importer.run_import("orders", rows, {f: m["column"] for f, m in sug.items() if m["column"]})
    rebuilt = {o["order_id"]: o for o in intake.orders_from_clean(run["clean"])}
    _, truth = messy.build_rows(data, 1)
    assert len(rebuilt) == truth["orders"] and sum(o["total"] for o in rebuilt.values()) == truth["total_revenue"]       # rupee amounts parsed
    orig = {o["order_id"]: o for o in data.orders}
    known = [o for o in rebuilt.values() if o["relationship"] != "unknown"]
    assert len(rebuilt) - len(known) == truth["unknown_relationship"]
    assert all(o["relationship"] == orig[o["order_id"]]["relationship"] for o in known)                                  # free text mapped back
    assert all(o["date"] == orig[o["order_id"]]["date"] for o in rebuilt.values())                                       # dd/mm/yyyy repaired


def test_relationship_free_text():
    for t, rel in [("friend", "friend"), ("close friend", "friend"), ("family", "friend"), ("friend of a friend", "friend_of_friend"),
                   ("FOF", "friend_of_friend"), ("friends friend", "friend_of_friend"), ("stranger", "stranger"),
                   ("found you on insta", "stranger"), ("new customer", "stranger"), ("saw your reel", "stranger"), ("", "unknown"), ("???", "unknown")]:
        assert importer.relationship_of(t) == rel, t


def test_sample_downloads():
    r = client.get(f"{API}/demo/sample-orders.csv?business=homebaker&week=2")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv") and "Order ID" in r.text.splitlines()[0]
    chat = client.get(f"{API}/demo/sample-chat?business=boxbox&week=1").json()
    assert chat["synthetic"] is True and "(dm)" in chat["text"] or "(comment)" in chat["text"]


# ------------------------------------------------------------------ facts
def test_facts_endpoint():
    load("boxbox", 1)
    r = client.get(f"{API}/businesses/biz_boxbox/facts").json()
    assert r["snapshot"] == "week_1" and r["main_measure"] == "f_stranger_orders_week" and len(r["facts"]) == 22 and r["synthetic"] is True
    reach = client.get(f"{API}/businesses/biz_boxbox/facts?bottleneck=reach").json()["facts"]
    assert reach and {f["bottleneck"] for f in reach} == {"reach"}
    assert client.get(f"{API}/businesses/biz_boxbox/facts?bottleneck=weird").status_code == 422
    assert client.get(f"{API}/businesses/biz_boxbox/facts?week=7").status_code == 422
    assert client.get(f"{API}/businesses/biz_nope/facts").status_code == 404
    w = client.get(f"{API}/businesses/biz_boxbox/facts/weekly?fact_id=f_stranger_orders_week").json()
    assert w["fact_id"] == "f_stranger_orders_week" and len(w["points"]) == 10
    assert client.get(f"{API}/businesses/biz_boxbox/facts/weekly?fact_id=nope").json()["error"]["code"] == "unknown_fact"


def test_the_snapshot_week_moves_and_week_2_sees_more():
    load("boxbox", 1)
    v1 = {f["fact_id"]: f for f in client.get(f"{API}/businesses/biz_boxbox/facts").json()["facts"]}
    r = client.post(f"{API}/businesses/biz_boxbox/week", json={"week": 3})
    assert r.status_code == 200 and r.json()["as_of"] == "2026-10-19"
    v3 = {f["fact_id"]: f for f in client.get(f"{API}/businesses/biz_boxbox/facts").json()["facts"]}
    assert v3["f_stranger_orders_week"]["snapshot"] == "week_3" and v3["f_stranger_orders_week"]["value"] > v1["f_stranger_orders_week"]["value"]
    assert client.post(f"{API}/businesses/biz_boxbox/week", json={"week": 5}).status_code == 422
    load("boxbox", 1)                                                            # reloading resets to week 1


# ------------------------------------------------------------------ leads
def test_leads_list_groups_and_counts():
    load("boxbox", 1)
    r = client.get(f"{API}/businesses/biz_boxbox/leads").json()
    assert r["snapshot"] == "week_1" and sum(r["counts"].values()) == len(r["leads"]) and r["leads"][0]["group"] == "hot"
    hot = client.get(f"{API}/businesses/biz_boxbox/leads?group=hot").json()["leads"]
    assert hot and all(l["group"] == "hot" and l["score"] >= 50 and l["reasons"] for l in hot)
    assert [l["rank"] for l in hot] == list(range(1, len(hot) + 1))
    assert client.get(f"{API}/businesses/biz_boxbox/leads?group=lukewarm").status_code == 422


def test_owner_tags_a_lead_and_the_score_follows():
    load("boxbox", 1)
    leads = client.get(f"{API}/businesses/biz_boxbox/leads").json()["leads"]
    target = next(l for l in leads if l["relationship"] != "stranger" and l["group"] in ("warm", "hot"))
    r = client.patch(f"{API}/leads/{target['lead_id']}", json={"relationship": "stranger"})
    assert r.status_code == 200 and r.json()["scored"]["score"] == target["score"] + 10
    assert any(x["signal"] == "stranger" for x in r.json()["scored"]["reasons"])
    assert client.patch(f"{API}/leads/{target['lead_id']}", json={"relationship": "cousin"}).status_code == 422
    assert client.patch(f"{API}/leads/{target['lead_id']}", json={"intents": ["nonsense"]}).status_code == 422
    done = client.patch(f"{API}/leads/{target['lead_id']}", json={"outcome": "ordered"}).json()
    assert done["lead"]["outcome"] == "ordered" and done["lead"]["outcome_date"] == "2026-10-04" and done["scored"] is None   # closed leads leave the list
    assert client.patch(f"{API}/leads/{target['lead_id']}", json={"outcome": "maybe"}).status_code == 422
    assert client.patch(f"{API}/leads/lead_nope", json={}).status_code == 404
    load("boxbox", 1)                                                            # a fresh load discards the edits


def test_intake_reads_pasted_chat_and_protects_identities():
    load("homebaker", 1)
    chat = client.get(f"{API}/demo/sample-chat?business=homebaker&week=1").json()["text"]
    body = chat + "\n@newbuyer (dm): how much for the brownie box? call me 9876543210\n@spammer (dm): collab? we can promote your page"
    r = client.post(f"{API}/businesses/biz_homebaker/leads/intake", json={"text": body})
    assert r.status_code == 201
    j = r.json()
    assert j["messages_read"] >= 10 and j["leads_created"] >= 8 and j["not_a_lead"] == 1 and "pseudonymised" in j["privacy"]
    assert "9876543210" not in r.text and "newbuyer" not in r.text and "spammer" not in r.text
    new = next(l for l in j["leads"] if any("[phone]" in m["text"] for m in l["messages"]))
    assert new["group"] in ("warm", "hot") and new["score"] >= 40 and new["messages"][0]["method"] == "rules"
    assert client.post(f"{API}/businesses/biz_homebaker/leads/intake", json={"text": "just some words"}).json()["error"]["code"] == "no_messages"
    assert client.post(f"{API}/businesses/biz_homebaker/leads/intake", json={"text": ""}).status_code == 422
    load("homebaker", 1)


def test_learning_and_projection_endpoints():
    load("boxbox", 1)
    lr = client.get(f"{API}/businesses/biz_boxbox/leads/learning").json()
    assert lr["enough_data"] and lr["by_group"]["hot"]["conversion"] > lr["by_group"]["cold"]["conversion"] and lr["public_data_support"]
    pr = client.get(f"{API}/businesses/biz_boxbox/projection").json()
    assert pr["estimate"] is True and pr["orders"]["low"] <= pr["orders"]["expected"] <= pr["orders"]["high"] and pr["month"]["from"] == "2026-10-05"
    load("homebaker", 1)
    bk = client.get(f"{API}/businesses/biz_homebaker/projection").json()
    assert bk["capacity"]["demand_exceeds_capacity"] is True and "turned away" in bk["capacity"]["message"]
    assert client.get(f"{API}/businesses/biz_homebaker/projection?week=0").status_code == 422


# ------------------------------------------------------------------ a business created from the form, with its own files
def _orders_csv(weeks=8, per_week=7):
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Order ID", "Order Date", "Customer", "Items", "Amount", "How did you find us?", "Dispatched On"])
    start = date(2026, 8, 3)
    n = 0
    rels = ["friend", "friend of a friend", "found you on insta", "friend"]
    for wk in range(weeks):
        for i in range(per_week):
            n += 1
            day = start + timedelta(weeks=wk, days=i % 7)
            w.writerow([f"S{n:03d}", day.strftime("%d/%m/%Y") if n % 7 == 0 else day.isoformat(), f"Customer {n % 11}", "Walnut Candle x1" if n % 2 else "Soy Candle x2", 300 if n % 2 else 560,
                        rels[n % 4], (day + timedelta(days=2)).isoformat()])
    return out.getvalue().encode("utf-8")


def test_create_business_from_the_form_then_import_its_files():
    form = {"name": "Wick & Wax", "kind": "handmade candles", "products": [{"name": "Walnut Candle", "category": "candles", "price": 300, "unit_cost": 120},
                                                                          {"name": "Soy Candle", "category": "candles", "price": 280}],
            "weekly_hours": 12, "capacity_orders_per_week": 15, "serves_cities": ["Pune"], "context_feed": "india_festivals"}
    r = client.post(f"{API}/businesses", json=form)
    assert r.status_code == 201, r.text
    prof = r.json()
    assert prof["business_id"] == "biz_wick_wax" and prof["synthetic"] is False and prof["constraints"]["forbidden_actions"] == ["paid_ads"]
    assert prof["fields"]["capacity_orders_per_week"] == {"value": 15, "source": "estimate"}
    assert client.post(f"{API}/businesses", json=form).status_code == 409
    assert client.post(f"{API}/businesses", json={**form, "name": "x", "products": []}).status_code == 422
    assert client.get(f"{API}/businesses/biz_wick_wax").json()["name"] == "Wick & Wax"
    assert client.get(f"{API}/businesses/biz_wick_wax/facts").json()["error"]["code"] == "not_enough_history"

    up = client.post(f"{API}/businesses/biz_wick_wax/imports/auto?kind=orders", files={"file": ("orders.csv", _orders_csv(), "text/csv")})
    assert up.status_code == 201, up.text
    assert up.json()["report"]["attached_to_business"] == "orders" and up.json()["report"]["rows_quarantined"] == 0
    facts = {f["fact_id"]: f for f in client.get(f"{API}/businesses/biz_wick_wax/facts").json()["facts"]}
    assert facts["f_orders_per_week"]["value"] == 7.0 and facts["f_stranger_orders_week"]["value"] == pytest.approx(7 * 0.25, abs=0.3)
    assert facts["f_stranger_share"]["source"] == "estimate" and facts["f_stranger_share"]["sample_size"] == 28
    assert facts["f_capacity_utilisation"]["value"] == pytest.approx(7 / 15, abs=1e-3) and "f_reach_per_post" not in facts      # no insights yet
    assert client.get(f"{API}/businesses/biz_wick_wax/profile").json()["data"]["orders"] == 56

    costs = "Product,Material,Making,Packaging,Courier\nWalnut Candle,60,30,15,25\nSoy Candle,70,30,15,25\n".encode("utf-8")
    c = client.post(f"{API}/businesses/biz_wick_wax/imports/auto?kind=costs", files={"file": ("costs.csv", costs, "text/csv")})
    assert c.status_code == 201 and c.json()["report"]["attached_to_business"] == "costs"
    ins = "Post ID,Date,Reach,Profile Visits,Follows\np1,2026-09-01,400,20,3\np2,2026-09-08,350,15,2\n".encode("utf-8")
    i = client.post(f"{API}/businesses/biz_wick_wax/imports/auto?kind=insights", files={"file": ("insights.csv", ins, "text/csv")})
    assert i.status_code == 201 and i.json()["report"]["attached_to_business"] == "insights"
    facts = {f["fact_id"]: f for f in client.get(f"{API}/businesses/biz_wick_wax/facts").json()["facts"]}
    assert facts["f_reach_per_post"]["value"] == 375.0 and facts["f_reach_per_post"]["quality_flag"] == "partial"           # 2 posts: thin
    assert client.get(f"{API}/businesses/biz_wick_wax/projection").json()["basis"]["context_source"] == "india_festivals"
    assert client.get(f"{API}/businesses/biz_wick_wax/data-quality").json()["overall"]["badge"] in ("high", "medium")
    assert client.get(f"{API}/businesses/biz_wick_wax/data-card").status_code == 404                                         # not generated
    assert client.post(f"{API}/businesses/biz_wick_wax/week", json={"week": 2}).status_code == 422                         # only week 1 exists


# ------------------------------------------------------------------ market context and the in-process interface
def test_market_context_feeds():
    f1 = client.get(f"{API}/market-context?from=2026-10-05&to=2026-11-01").json()
    assert f1["feed"] == "f1_calendar" and len(f1["events"]) == 3 and f1["interest_uplift"]["overall"]["uplift"] > 1.5
    fest = client.get(f"{API}/market-context?feed=india_festivals&from=2026-10-05&to=2026-11-30").json()
    assert [e["name"] for e in fest["events"]] == ["Dussehra", "Diwali (Deepavali)"] and fest["interest_uplift"] is None
    assert "No measured demand uplift" in fest["note"] and fest["next_event"]["name"] == "Dussehra"
    assert client.get(f"{API}/market-context?feed=weather").status_code == 422


def test_in_process_interface_for_decision_engine():
    load("boxbox", 1)
    assert len(public.get_facts("biz_boxbox")) == 22 and public.get_facts("biz_boxbox", 2)[0]["snapshot"] == "week_2"
    assert public.get_leads("biz_boxbox")[0]["group"] == "hot" and public.get_leads("biz_boxbox", "cold") is not None
    assert public.get_projection("biz_boxbox")["estimate"] is True and public.get_profile("biz_boxbox")["profile"]["name"] == "Box Box"
    assert public.get_facts("biz_nope") is None and public.get_leads("biz_nope") is None and public.get_projection("biz_nope") is None
    assert public.get_market_context("2026-10-05", "2026-11-01")["feed"] == "f1_calendar"
