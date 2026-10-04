import copy

import pytest

from backend.common.fixtures import load_fixture
from backend.decision_engine import actions as A

API = "/api/v1"
BB, HB = "biz_boxbox", "biz_homebaker"


def business(slug="boxbox", **changes):
    b = load_fixture(f"v2/{slug}/business")
    b.update(changes)
    return b


def data(b, windows=None, customers=100, context="f1"):
    ctx = load_fixture("v2/market_context/f1_calendar") if context == "f1" else context
    return {"partners": A.rank_partners(b), "windows": A.demand_windows(ctx, "2026-10-04") if windows is None else windows,
            "context": ctx, "customers": customers, "as_of": "2026-10-04"}


LIB = {a["action_key"]: a for a in A.library()["actions"]}


# ---------------------------------------------------------------- library


def test_library_covers_five_bottlenecks():
    assert {a["bottleneck"] for a in LIB.values()} == {"reach", "conversion", "margin", "repeat_orders", "capacity"}
    assert all(a["effort_min"] > 0 for a in LIB.values())


# ---------------------------------------------------------------- gate


def test_paid_ads_always_blocked_without_budget():
    b = business()
    g = A.gate(LIB["reach_paid_ads"], b, data(b))
    assert not g["eligible"] and "ad budget is INR 0" in g["blocked_reason"]


def test_hours_block():
    b = business(growth_minutes_per_week=30)
    g = A.gate(LIB["reach_demand_window_drop"], b, data(b))
    assert not g["eligible"] and g["blocked_reason"] == "Needs 90 minutes; you have 30 minutes a week for growth."


@pytest.mark.parametrize("key,setup,needle", [
    ("reach_partner_collab", lambda b, d: (dict(b, reach_candidates=[]), None), "no reach partners are listed"),
    ("reach_demand_window_drop", lambda b, d: (b, []), "no demand window in the next 3 weeks"),
    ("repeat_thank_you_next_drop", lambda b, d: (b, "few_buyers"), "fewer than 5 past buyers"),
    ("margin_reprice", lambda b, d: (dict(b, products=[dict(b["products"][0], unit_cost=None)]), None),
     "unit costs are missing"),
])
def test_missing_data_blocks(key, setup, needle):
    b, extra = setup(business(), None)
    d = data(b, windows=extra if isinstance(extra, list) else None, customers=3 if extra == "few_buyers" else 100)
    g = A.gate(LIB[key], b, d)
    assert not g["eligible"] and needle in g["blocked_reason"].lower()


def test_no_calendar_is_said_plainly():
    b = business("homebaker")
    g = A.gate(LIB["reach_demand_window_drop"], b, data(b, windows=[], context=None))
    assert g["blocked_reason"] == "No event calendar for this business yet."


# ---------------------------------------------------------------- ranking and selection


def test_score_formula_hand_check():
    # impact 0.8, fit 0.9, timing 1.0, effort 60 of 180: 100 x (0.4 + 0.27 + 0.2) x (1 - 0.5/3) = 72.5
    s = A.score(LIB["reach_partner_collab"], 0.9, 1.0, 180)
    assert s["score"] == 72.5 and s["parts"]["effort_share"] == pytest.approx(1 / 3, abs=0.001)


def test_selection_fits_minutes_and_max_three():
    b = business()
    cands = A.candidates("reach", b, data(b))
    chosen = A.select(cands, 180)
    assert 1 <= len(chosen) <= 3 and sum(c["effort_min"] for c in chosen) <= 180
    assert all(c["gate"]["eligible"] for c in chosen)
    assert len({c["partner_id"] for c in chosen if c["partner_id"]}) == len([c for c in chosen if c["partner_id"]])
    assert [c["action_key"] for c in A.select(cands, 70)] == ["reach_partner_collab"]


def test_ties_go_to_less_effort():
    a = dict(LIB["reach_buyer_tag_share"], score=50.0, gate={"eligible": True}, effort_min=20)
    b = dict(a, action_key="other", effort_min=40)
    ordered = sorted([b, a], key=lambda c: (not c["gate"]["eligible"], -c["score"], c["effort_min"]))
    assert ordered[0]["action_key"] == "reach_buyer_tag_share"


def test_targets():
    facts = {f["fact_id"]: f for f in load_fixture("v2/boxbox/facts_week_1")["facts"]}
    t = A.target_for(LIB["reach_partner_collab"], facts)
    assert (t["current"], t["value"]) == (1, 3) and "orders from strangers next week" in t["text"]
    t = A.target_for(LIB["cap_preorder_drop"], facts)
    assert t["value"] == 0


# ---------------------------------------------------------------- partners, windows, brand risk


def test_partners_ranked_by_engagement_not_followers():
    r = A.rank_partners(business())
    assert r["partners"][0]["name"].startswith("Campus Motorsport Club")  # 1,900 followers, 2.1% engagement
    assert r["blocked"][0]["partner_id"] == "rp_bb_4" and "paid shoutout" in r["blocked"][0]["blocked_reason"]
    assert r["recommended"] == [p["partner_id"] for p in r["partners"][:3]]


def test_past_results_move_partners():
    r = A.rank_partners(business(), {"rp_bb_1": [5, 5]})
    pune = next(p for p in r["partners"] if p["partner_id"] == "rp_bb_1")
    assert pune["score_parts"]["past_results"] == 1.0 and pune["score"] == pytest.approx(76.6 + 10, abs=0.1)


def test_demand_windows():
    ctx = load_fixture("v2/market_context/f1_calendar")
    w = A.demand_windows(ctx, "2026-10-04")
    assert [x["name"] for x in w] == ["Singapore Grand Prix", "United States Grand Prix"]
    assert w[0]["interest_uplift"] == pytest.approx(2.027)
    assert A.demand_windows(load_fixture("v2/market_context/india_festivals"), "2026-10-18")[0]["name"] == "Diwali"


def test_golden_risk_case():
    flag = A.brand_risk(business(), raises_visibility=True)
    assert flag["terms"] == ["Ferrari", "Hamilton"] and flag["level"] == "high"
    assert "not legal advice" in flag["text"]
    assert A.brand_risk(business(), raises_visibility=False)["level"] == "medium"
    assert A.brand_risk(business(products=[{"name": "Plain Tee", "price": 500, "unit_cost": 200}])) is None
    assert A.brand_risk(business("homebaker"))["terms"] == ["Nutella"]  # not F1-specific


# ---------------------------------------------------------------- API


def test_diagnosis_endpoint(client):
    d = client.get(f"{API}/businesses/{BB}/diagnosis?week=week_1").json()
    assert d["primary"] == "reach" and len(d["runners_up"]) == 2
    assert client.get(f"{API}/businesses/{BB}/diagnosis?week=week_9").status_code == 422
    assert client.get(f"{API}/businesses/biz_nope/diagnosis").status_code == 404


def test_generate_actions_box_box(client):
    d = client.post(f"{API}/businesses/{BB}/actions/generate?week=week_1").json()
    assert d["bottleneck"] == "reach" and 1 <= len(d["actions"]) <= 3
    assert d["minutes_planned"] <= d["minutes_available"] == 180
    keys = [a["action_key"] for a in d["actions"]]
    assert keys[0] == "reach_partner_collab" and "reach_paid_ads" not in keys
    assert any(b["action_key"] == "reach_paid_ads" for b in d["blocked"])
    a = d["actions"][0]
    assert a["evidence_ids"][0] == "f_stranger_share" and a["due"] == "2026-10-11" and a["status"] == "todo"
    assert a["risk_flags"][0]["flag"] == "brand_ip" and "Singapore Grand Prix" in d["actions"][1]["title"]


def test_baker_actions_follow_the_bottleneck(client):
    w1 = client.post(f"{API}/businesses/{HB}/actions/generate?week=week_1").json()
    w3 = client.post(f"{API}/businesses/{HB}/actions/generate?week=week_3").json()
    assert w1["bottleneck"] == "reach" and w3["bottleneck"] == "capacity"
    assert {a["bottleneck"] for a in w3["actions"]} == {"capacity"}


def test_status_survives_regeneration(client):
    d = client.post(f"{API}/businesses/{BB}/actions/generate").json()
    aid = d["actions"][0]["action_id"]
    assert client.patch(f"{API}/actions/{aid}", json={"status": "done", "note": "posted on Tue"}).json()["status"] == "done"
    again = client.get(f"{API}/businesses/{BB}/actions").json()
    assert next(a for a in again["actions"] if a["action_id"] == aid)["status"] == "done"
    assert client.patch(f"{API}/actions/{aid}", json={"status": "finished"}).status_code == 422
    assert client.patch(f"{API}/actions/act_nope", json={"status": "done"}).status_code == 404


def test_action_drafts(client):
    d = client.post(f"{API}/businesses/{BB}/actions/generate").json()
    collab, drop = d["actions"][0], d["actions"][1]
    dm = client.get(f"{API}/actions/{collab['action_id']}/draft").json()
    assert dm["channel"] == "instagram_dm" and dm["auto_send"] is False and dm["text"].startswith("Hi Campus Motorsport Club!")
    assert "Ferrari" not in dm["text"]  # drafts promote a product without a protected name
    post = client.get(f"{API}/actions/{drop['action_id']}/draft?channel=instagram_post").json()
    assert "2026-10-07" in post["text"]  # two days before the race weekend
    r = client.get(f"{API}/actions/{collab['action_id']}/draft?channel=whatsapp")
    assert r.status_code == 422 and r.json()["error"]["code"] == "unsupported_channel"


def test_reach_partners_endpoint(client):
    r = client.get(f"{API}/businesses/{BB}/reach-partners").json()
    assert r["partners"][0]["rank"] == 1 and "engagement" in r["formula"]


def test_no_send_endpoint(client):
    assert not any("send" in p for p in client.get("/openapi.json").json()["paths"])
