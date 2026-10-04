"""Daily lead list on data_engine's real scored leads (contracts/fixtures/v2_engine)."""
from backend.decision_engine.clients import DataClientV2
from backend.decision_engine.leadlist import _unmet

API = "/api/v1"
BB, HB = "biz_boxbox", "biz_homebaker"
DATA = DataClientV2("fixture")


def lead_list(client, biz=BB, week="week_1"):
    r = client.get(f"{API}/businesses/{biz}/lead-list?week={week}")
    assert r.status_code == 200
    return r.json()


def by_id(doc):
    return {e["lead_id"]: e for g in ("hot", "warm", "cold", "disqualified") for e in doc[g]}


def test_groups_match_data_engine(client):
    d = lead_list(client)
    leads = DATA.get_leads(BB, week=1)
    assert d["summary"] == {g: sum(l["group"] == g for l in leads) for g in ("hot", "warm", "cold", "disqualified")}
    assert all(e["draft"] for e in d["hot"])                  # a drafted reply for every hot lead
    assert all(e["draft"] is None for e in d["cold"])         # nothing one to one
    for e in d["hot"] + d["warm"]:
        assert e["evidence_ids"] == [e["lead_id"]] and e["reasons"]   # the reasons behind the score


def test_hot_newest_first_with_price_and_order_link(client):
    hot = lead_list(client)["hot"]
    dates = [e["last_activity"] for e in hot]
    assert dates == sorted(dates, reverse=True)
    business = DATA.get_business(BB)
    for e in hot:
        product = next(p for p in business["products"] if p["name"] == e["asked_for"]["product"])
        assert f"₹{product['price']:,}" in e["draft"] and business["order_link"] in e["draft"]


def test_drafts_never_invent_unknowns(client):
    for e in lead_list(client)["hot"]:
        city = e["asked_for"]["city"]
        if city and city != "Pune":
            assert "{delivery_charge}" in e["draft"] and "{delivery_charge}" in e["placeholders"]


def test_warm_once_per_reason(client):
    d = lead_list(client)
    reason = d["warm_reasons_this_week"][0]
    assert reason["text"] == "a small drop for Singapore Grand Prix"
    warm = next(e for e in d["warm"] if e["draft"])
    client.post(f"{API}/businesses/{BB}/lead-list/contacted", json={"lead_id": warm["lead_id"], "reason": reason["key"]})
    again = by_id(lead_list(client))[warm["lead_id"]]
    assert again["draft"] is None and "Wait for a reason" in again["next_action"]


def test_baker_warm_reason_names_the_preorder_product(client):
    d = lead_list(client, HB)
    assert d["warm_reasons_this_week"][0]["text"].startswith("a limited pre-order of ")
    assert "what we make" in d["warm"][0]["draft"] or "the " in d["warm"][0]["draft"]


def test_disqualified_and_unmet_demand(client):
    bb, hb = lead_list(client), lead_list(client, HB)
    assert bb["disqualified"][0]["draft"].startswith("Thank you for asking! We cannot make size XXL yet")
    assert bb["unmet_demand"]["items"] == [{"kind": "size", "value": "XXL", "count": 1, "phrase": "make size XXL"}]
    assert hb["unmet_demand"]["text"] == "People asked for things you do not offer yet: deliver to Jaipur (1)."


def test_unmet_parser():
    assert _unmet("size: XXL is not available") == ("size", "XXL", "make size XXL")
    assert _unmet("city: cannot deliver to Jaipur") == ("city", "Jaipur", "deliver to Jaipur")


def test_brand_risk_on_drafts_naming_protected_products(client):
    for e in lead_list(client)["hot"]:
        named = any(t in (e["draft"] or "") for t in ("Ferrari", "Verstappen", "McLaren", "F1"))
        assert bool(e["risk_flags"]) == named


def test_every_week_has_a_list(client):
    for biz in (BB, HB):
        for w in ("week_2", "week_3", "week_4"):
            d = lead_list(client, biz, w)
            assert sum(d["summary"].values()) == len(DATA.get_leads(biz, week=int(w[-1])))
