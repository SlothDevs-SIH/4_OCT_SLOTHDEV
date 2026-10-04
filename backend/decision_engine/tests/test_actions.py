"""Actions, eligibility, ranking, reach partners and brand risk on data_engine's real v2 output."""
import pytest

from backend.decision_engine import actions as A
from backend.decision_engine.clients import DataClientV2

API = "/api/v1"
BB, HB = "biz_boxbox", "biz_homebaker"
DATA = DataClientV2("fixture")
LIB = {a["action_key"]: a for a in A.library()["actions"]}


def business(biz=BB, **changes):
    b = DATA.get_business(biz)
    b.update(changes)
    return b


def data(b, windows=None, customers=100, feed="f1_calendar"):
    ctx = DATA.get_market_context(feed=feed) if feed else None
    return {"partners": A.rank_partners(b), "windows": A.demand_windows(ctx, "2026-10-05") if windows is None else windows,
            "context": ctx, "customers": customers, "as_of": "2026-10-05", "asked_products": []}


# ---------------------------------------------------------------- library and gate


def test_library_covers_five_bottlenecks():
    assert {a["bottleneck"] for a in LIB.values()} == {"reach", "conversion", "margin", "repeat_orders", "capacity"}


def test_paid_ads_always_blocked_without_budget():
    b = business()
    g = A.gate(LIB["reach_paid_ads"], b, data(b))
    assert not g["eligible"] and "ad budget is INR 0" in g["blocked_reason"]


def test_hours_block():
    b = business(growth_minutes_per_week=30)
    assert A.gate(LIB["reach_demand_window_drop"], b, data(b))["blocked_reason"] == \
        "Needs 90 minutes; you have 30 minutes a week for growth."


@pytest.mark.parametrize("key,changes,kwargs,needle", [
    ("reach_partner_collab", {"reach_candidates": []}, {}, "no reach partners are listed"),
    ("reach_demand_window_drop", {}, {"windows": []}, "no demand window in the next 3 weeks"),
    ("repeat_thank_you_next_drop", {}, {"customers": 3}, "fewer than 5 past buyers"),
])
def test_missing_data_blocks(key, changes, kwargs, needle):
    b = business(**changes)
    g = A.gate(LIB[key], b, data(b, **kwargs))
    assert not g["eligible"] and needle in g["blocked_reason"].lower()


def test_missing_unit_cost_blocks_repricing():
    b = business()
    b["products"][0]["unit_cost"] = None
    assert "unit costs are missing" in A.gate(LIB["margin_reprice"], b, data(b))["blocked_reason"].lower()


def test_no_calendar_is_said_plainly():
    b = business(HB)
    g = A.gate(LIB["reach_demand_window_drop"], b, data(b, windows=[], feed=None))
    assert g["blocked_reason"] == "No event calendar for this business yet."


# ---------------------------------------------------------------- ranking, selection, targets


def test_score_formula_hand_check():
    # impact 0.8, fit 0.9, timing 1.0, effort 60 of 180: 100 x (0.4 + 0.27 + 0.2) x (1 - 0.5/3) = 72.5
    assert A.score(LIB["reach_partner_collab"], 0.9, 1.0, 180)["score"] == 72.5


def test_selection_fits_minutes_and_max_three():
    b = business()
    cands = A.candidates("reach", b, data(b))
    chosen = A.select(cands, 180)
    assert 1 <= len(chosen) <= 3 and sum(c["effort_min"] for c in chosen) <= 180
    partners = [c["partner_id"] for c in chosen if c["partner_id"]]
    assert len(partners) == len(set(partners))   # never the same partner twice
    assert [c["action_key"] for c in A.select(cands, 70)] == ["reach_partner_collab"]


def test_targets_on_real_facts():
    facts = {f["fact_id"]: f for f in DATA.get_facts(BB, 1)}
    t = A.target_for(LIB["reach_partner_collab"], facts)
    assert (t["current"], t["value"]) == (1.5, 3.5) and "orders from strangers a week" in t["text"]
    hb = {f["fact_id"]: f for f in DATA.get_facts(HB, 1)}
    assert A.target_for(LIB["cap_batch_making"], hb)["text"] == \
        "5 orders turned away or fewer, as in your best weeks (now 10)"


# ---------------------------------------------------------------- partners, windows, brand risk


def test_partners_ranked_by_engagement_not_followers():
    r = A.rank_partners(business())
    assert r["partners"][0]["partner_id"] == "rp_bb_3"           # 1,900 followers, 2.1% engagement
    assert [p["partner_id"] for p in r["blocked"]] == ["rp_bb_4"]  # paid shoutout, no ad budget


def test_past_results_move_partners():
    before = {p["partner_id"]: p["score"] for p in A.rank_partners(business())["partners"]}
    after = {p["partner_id"]: p["score"] for p in A.rank_partners(business(), {"rp_bb_1": [5, 5]})["partners"]}
    assert after["rp_bb_1"] == pytest.approx(before["rp_bb_1"] + 10, abs=0.1)


def test_demand_windows_real_calendars():
    f1 = A.demand_windows(DATA.get_market_context(feed="f1_calendar"), "2026-10-05")
    assert [w["name"] for w in f1] == ["Singapore Grand Prix", "United States Grand Prix"]
    assert f1[0]["interest_uplift"] == pytest.approx(2.027, abs=0.01)
    fest = A.demand_windows(DATA.get_market_context(feed="india_festivals"), "2026-10-05")
    assert fest[0]["name"] == "Dussehra"


def test_brand_risk_is_rule_based():
    flag = A.brand_risk(business(), raises_visibility=True)
    assert set(flag["terms"]) == {"F1", "Ferrari", "McLaren", "Verstappen"} and flag["level"] == "high"
    assert "not legal advice" in flag["text"]
    assert A.brand_risk(business(HB)) is None   # the baker's product names are clean


# ---------------------------------------------------------------- API


def test_box_box_week_1_actions(client):
    d = client.post(f"{API}/businesses/{BB}/actions/generate?week=week_1").json()
    assert d["mode"] == "fix" and d["bottleneck"] == "reach" and d["minutes_planned"] <= 180
    keys = [a["action_key"] for a in d["actions"]]
    assert keys[0] == "reach_partner_collab" and "reach_paid_ads" not in keys
    assert any(b["action_key"] == "reach_paid_ads" for b in d["blocked"])
    a = d["actions"][0]
    assert a["evidence_ids"][0] == "f_stranger_orders_week" and a["due"] == "2026-10-12" and a["status"] == "todo"
    assert "Singapore Grand Prix" in d["actions"][1]["title"]


def test_baker_gets_capacity_actions_for_what_people_ask_for(client):
    d = client.post(f"{API}/businesses/{HB}/actions/generate?week=week_1").json()
    assert d["bottleneck"] == "capacity" and {a["bottleneck"] for a in d["actions"]} == {"capacity"}
    pre = next(a for a in d["actions"] if a["action_key"] == "cap_preorder_drop")
    draft = client.get(f"{API}/actions/{pre['action_id']}/draft?channel=instagram_post").json()
    assert pre["product_name"] in pre["title"] and pre["product_name"] in draft["text"]


def test_maintain_mode_when_nothing_is_off(client):
    for w in ("week_1", "week_2"):
        client.post(f"{API}/businesses/{BB}/actions/generate?week={w}")
    d = client.post(f"{API}/businesses/{BB}/actions/generate?week=week_3").json()
    assert d["mode"] == "maintain" and d["bottleneck"] == "reach" and d["actions"]
    assert "Keep doing what works" in d["message"]


def test_status_survives_regeneration(client):
    aid = client.post(f"{API}/businesses/{BB}/actions/generate").json()["actions"][0]["action_id"]
    assert client.patch(f"{API}/actions/{aid}", json={"status": "done"}).json()["status"] == "done"
    again = client.get(f"{API}/businesses/{BB}/actions").json()["actions"]
    assert next(a for a in again if a["action_id"] == aid)["status"] == "done"
    assert client.patch(f"{API}/actions/{aid}", json={"status": "finished"}).status_code == 422


def test_action_drafts(client):
    d = client.post(f"{API}/businesses/{BB}/actions/generate").json()
    dm = client.get(f"{API}/actions/{d['actions'][0]['action_id']}/draft").json()
    assert dm["auto_send"] is False and dm["text"].startswith("Hi Campus Motorsport Club!")
    assert "Box Box Racing Cap" in dm["text"]   # promotes the one product without a protected name
    post = client.get(f"{API}/actions/{d['actions'][1]['action_id']}/draft?channel=instagram_post").json()
    assert "2026-10-07" in post["text"]          # two days before the Singapore race weekend


def test_reach_partners_and_no_send_endpoint(client):
    assert client.get(f"{API}/businesses/{BB}/reach-partners").json()["partners"][0]["rank"] == 1
    assert not any("send" in p for p in client.get("/openapi.json").json()["paths"])
