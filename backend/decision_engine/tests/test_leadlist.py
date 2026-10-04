"""Daily lead list, including the golden-set lead cases (lead_a, lead_b, lead_c, lead_e)."""
API = "/api/v1"
BB, HB = "biz_boxbox", "biz_homebaker"


def lead_list(client, biz=BB, week="week_1"):
    r = client.get(f"{API}/businesses/{biz}/lead-list?week={week}")
    assert r.status_code == 200
    return r.json()


def by_id(doc):
    return {e["lead_id"]: e for g in ("hot", "warm", "cold", "disqualified") for e in doc[g]}


def test_groups_and_rules(client):
    d = lead_list(client)
    assert d["summary"] == {"hot": 4, "warm": 3, "cold": 3, "disqualified": 2}
    assert all(e["draft"] for e in d["hot"])                   # a drafted reply for every hot lead
    assert all(e["draft"] is None for e in d["cold"])          # nothing one to one
    assert all(e["evidence_ids"] == [e["lead_id"]] and e["reasons"] for g in ("hot", "warm", "cold") for e in d[g])


def test_golden_lead_a_and_b(client):
    leads = by_id(lead_list(client))
    a, b = leads["lead_bb_01"], leads["lead_bb_02"]
    assert (a["group"], a["score"], b["group"], b["score"]) == ("hot", 75, "hot", 50)
    assert {r["signal"]: r["points"] for r in a["reasons"]} == {
        "asked_price_size_stock_delivery": 40, "saved_or_shared": 15, "commented": 10, "stranger": 10}
    assert a["rank"] < b["rank"]
    assert "₹799" in a["draft"] and "in L" in a["draft"] and "link in bio" in a["draft"]


def test_golden_lead_c_warm_and_lead_e_disqualified(client):
    leads = by_id(lead_list(client))
    assert (leads["lead_bb_03"]["group"], leads["lead_bb_03"]["score"]) == ("warm", 35)
    e = leads["lead_bb_04"]
    assert e["group"] == "disqualified" and e["draft"].startswith("Thank you for asking! We cannot deliver to Dubai")


def test_hot_newest_first_and_stranger_before_friend(client):
    hot = lead_list(client)["hot"]
    dates = [e["last_activity"] for e in hot]
    assert dates == sorted(dates, reverse=True)
    same_day = [e for e in hot if e["last_activity"] == "2026-10-04"]
    assert [e["lead_id"] for e in same_day] == ["lead_bb_01", "lead_bb_11"]


def test_drafts_never_invent_unknowns(client):
    leads = by_id(lead_list(client))
    custom = leads["lead_bb_11"]          # "Can you print my name on the back?"
    assert "{custom_price}" in custom["draft"] and "stock" not in custom["draft"]
    restock = leads["lead_bb_02"]         # "When is the cap back in stock?"
    assert restock["placeholders"] == ["{restock_date}"]
    mumbai = leads["lead_bb_05"]
    assert "{delivery_charge}" in mumbai["draft"]


def test_warm_once_per_reason(client):
    d = lead_list(client)
    reason = d["warm_reasons_this_week"][0]
    assert "Singapore Grand Prix" in reason["text"]
    warm = d["warm"][0]
    assert warm["draft"] and warm["contact_reason"] == reason["key"]
    client.post(f"{API}/businesses/{BB}/lead-list/contacted", json={"lead_id": warm["lead_id"], "reason": reason["key"]})
    again = by_id(lead_list(client))[warm["lead_id"]]
    assert again["draft"] is None and "Wait for a reason" in again["next_action"]


def test_warm_waits_without_a_reason(client):
    warm = lead_list(client, HB)["warm"]
    assert warm and all(e["draft"] is None for e in warm)


def test_unmet_demand(client):
    u = lead_list(client)["unmet_demand"]
    assert {(i["kind"], i["value"]) for i in u["items"]} == {("city", "Dubai"), ("size", "XXL")}
    assert "make size XXL (1)" in u["text"]


def test_brand_risk_on_drafts_naming_protected_products(client):
    leads = by_id(lead_list(client))
    assert leads["lead_bb_06"]["risk_flags"][0]["terms"] == ["Ferrari", "Hamilton"]   # Ferrari Red Tribute Tee
    assert leads["lead_bb_01"]["risk_flags"] == []                                     # Monza Tee


def test_later_weeks_show_outcomes(client):
    d = lead_list(client, BB, "week_2")
    assert d["outcomes"]["ordered"] == 2 and "lead_bb_01" not in by_id(d)
