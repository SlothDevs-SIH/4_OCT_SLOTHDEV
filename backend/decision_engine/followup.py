"""Weekly follow-up: what was done, what changed, and how next week's advice adjusts.

Fidelity (was the action done?) is kept apart from effectiveness (did its target number move?).
Results are observational: no control group, and one business is not proof.

Adjustments:
  done and reached its target     -> double down (repeat or scale it next week)
  done and moving the right way   -> keep going one more week
  done and no change / worse      -> drop it and try the next action
  not done (skipped or still todo)-> not judged; try again if there is time, or pick a smaller action
  bottleneck changed              -> switch the plan to the new bottleneck
"""
from __future__ import annotations

from typing import Optional

OBSERVATIONAL = "Observational: no control group, and one business is not proof. Other things changed too."


def _better(direction: Optional[str], prev, cur) -> Optional[int]:
    """+1 better, -1 worse, 0 same, None unknown."""
    if prev is None or cur is None:
        return None
    if cur == prev:
        return 0
    up = cur > prev
    return (1 if up else -1) if direction != "down" else (-1 if up else 1)


def _reached(target: dict, direction: Optional[str], cur) -> bool:
    if cur is None or target.get("value") is None:
        return False
    return cur <= target["value"] if direction == "down" else cur >= target["value"]


CAPACITY_KPIS = {"orders_turned_away", "dispatch_delay_days", "stockouts"}


def demand(facts: dict) -> Optional[float]:
    """Orders plus orders turned away in the window (what people wanted, not what was made)."""
    orders = max([f.get("sample_size") or 0 for f in facts.values() if f.get("sample_kind") == "orders"] or [0])
    away = (facts.get("f_orders_turned_away") or {}).get("value") or 0
    return orders + away if orders else None


def demand_explains(fid: str, prev, cur, prev_facts: dict, cur_facts: dict) -> bool:
    """Did more demand, rather than the action, make a capacity number worse? Orders turned away: the extra
    turned away is no more than the extra demand. Dispatch delay, stock-outs: demand rose 10% or more."""
    kpi = (cur_facts.get(fid) or {}).get("kpi")
    d0, d1 = demand(prev_facts), demand(cur_facts)
    if kpi not in CAPACITY_KPIS or not d0 or not d1 or d1 <= d0 or prev is None or cur is None:
        return False
    if kpi == "orders_turned_away":
        return cur - prev <= d1 - d0
    return d1 >= 1.1 * d0


def review_action(action: dict, prev_facts: dict, cur_facts: dict) -> dict:
    t = action["target"]
    fid = t.get("fact_id")
    prev, cur = (prev_facts.get(fid) or {}).get("value"), (cur_facts.get(fid) or {}).get("value")
    direction = (cur_facts.get(fid) or prev_facts.get(fid) or {}).get("direction")
    done = action["status"] == "done"
    move = _better(direction, prev, cur)
    if not done:
        effect, adjust = "not_judged", ("Not done last week. Try it again if you have the time, or pick a smaller action."
                                        if action["status"] == "skipped" else
                                        "Still open. Do it this week or mark it skipped.")
        decision = "retry"
    elif _reached(t, direction, cur):
        effect, adjust, decision = "reached_target", "It reached its target: double down and repeat or scale it this week.", "double_down"
    elif move == 1:
        effect, adjust, decision = "moving", "The number moved the right way but not to the target: keep going one more week.", "keep"
    elif demand_explains(fid, prev, cur, prev_facts, cur_facts):
        rise = round((demand(cur_facts) / demand(prev_facts) - 1) * 100)
        effect, decision = "inconclusive", "keep"
        adjust = (f"Demand rose about {rise}% (orders plus orders turned away), so a worse number here does not show the "
                  f"action failed: keep it this week.")
    else:
        effect = "no_change" if move in (0, None) else "worse"
        adjust, decision = "The number did not improve: drop it and try the next action.", "drop"
    return {"action_id": action["action_id"], "action_key": action["action_key"], "title": action["title"],
            "status": action["status"], "fidelity": {"done": done, "status": action["status"]},
            "target": {"fact_id": fid, "value": t.get("value"), "text": t.get("text")},
            "previous": prev, "current": cur, "effectiveness": effect, "decision": decision,
            "adjustment": adjust, "observational": True}


def fact_changes(fact_ids: list[str], prev_facts: dict, cur_facts: dict) -> list[dict]:
    out = []
    for fid in fact_ids:
        p, c = prev_facts.get(fid), cur_facts.get(fid)
        if not p or not c:
            continue
        move = _better(c.get("direction"), p["value"], c["value"])
        out.append({"fact_id": fid, "kpi": c["kpi"], "unit": c["unit"], "previous": p["value"], "current": c["value"],
                    "moved": {1: "better", -1: "worse", 0: "same"}.get(move, "unknown")})
    return out


def preferences(reviews: list[dict]) -> dict:
    """What next week's selection should favour or avoid."""
    return {"boost": sorted({r["action_key"] for r in reviews if r["decision"] in ("double_down", "keep")}),
            "exclude": sorted({r["action_key"] for r in reviews if r["decision"] == "drop"})}


def build(business_id: str, week: str, prev_week: str, prev_actions: list[dict], prev_facts_doc: dict,
          cur_facts_doc: dict, prev_bottleneck: Optional[str], cur_bottleneck: Optional[str],
          partner_results: list[dict]) -> dict:
    prev_facts = {f["fact_id"]: f for f in prev_facts_doc["facts"]}
    cur_facts = {f["fact_id"]: f for f in cur_facts_doc["facts"]}
    reviews = [review_action(a, prev_facts, cur_facts) for a in prev_actions]
    for r in reviews:
        shared = [o for o in reviews if o is not r and o["fidelity"]["done"] and o["target"]["fact_id"] == r["target"]["fact_id"]]
        if r["fidelity"]["done"] and shared:
            r["shared_with"] = [o["action_id"] for o in shared]
            r["attribution_note"] = (f"{len(shared) + 1} done actions aimed at this number; "
                                     "the change cannot be split between them.")
    tracked = ["f_stranger_orders_week", "f_stranger_share"]
    tracked += [r["target"]["fact_id"] for r in reviews if r["target"]["fact_id"] not in tracked]
    sm = (prev_facts.get("f_stranger_orders_week") or {}).get("value"), (cur_facts.get("f_stranger_orders_week") or {}).get("value")
    adjustments = [f"{r['title']}: {r['adjustment']}" for r in reviews]
    if prev_bottleneck != cur_bottleneck and cur_bottleneck:
        adjustments.insert(0, f"The main bottleneck moved from {(prev_bottleneck or 'none').replace('_', ' ')} to "
                              f"{cur_bottleneck.replace('_', ' ')}: this week's actions switch to it.")
    elif prev_bottleneck and not cur_bottleneck:
        adjustments.insert(0, f"{prev_bottleneck.replace('_', ' ').capitalize()} is back at your best weeks and nothing else "
                              f"is clearly off: keep doing what works.")
    return {
        "business_id": business_id, "week": week, "compared_with": prev_week,
        "as_of": cur_facts_doc.get("as_of"), "synthetic": cur_facts_doc.get("synthetic", False),
        "actions_done": [r["action_id"] for r in reviews if r["status"] == "done"],
        "actions_skipped": [r["action_id"] for r in reviews if r["status"] == "skipped"],
        "actions_open": [r["action_id"] for r in reviews if r["status"] == "todo"],
        "reviews": reviews,
        "fact_changes": fact_changes(tracked, prev_facts, cur_facts),
        "main_measure": {"stranger_orders": {"previous": sm[0], "current": sm[1],
                                             "change": (sm[1] - sm[0]) if None not in sm else None}},
        "bottleneck": {"previous": prev_bottleneck, "current": cur_bottleneck, "changed": prev_bottleneck != cur_bottleneck},
        "partner_results": partner_results, "adjustments": adjustments, "preferences": preferences(reviews),
        "observational": True, "note": OBSERVATIONAL,
    }


def arc(business_id: str, first_facts_doc: dict, last_facts_doc: dict, followups: list[dict]) -> dict:
    """Week 1 vs week 4: stranger orders, and which advice worked (observational)."""
    f = {x["fact_id"]: x for x in first_facts_doc["facts"]}
    l = {x["fact_id"]: x for x in last_facts_doc["facts"]}
    worked, did_not = [], []
    for fu in followups:
        for r in fu["reviews"]:
            if r["effectiveness"] in ("reached_target", "moving"):
                worked.append({"week": fu["compared_with"], "title": r["title"], "effectiveness": r["effectiveness"]})
            elif r["effectiveness"] in ("no_change", "worse"):
                did_not.append({"week": fu["compared_with"], "title": r["title"], "effectiveness": r["effectiveness"]})
    first = (f.get("f_stranger_orders_week") or {}).get("value")
    last = (l.get("f_stranger_orders_week") or {}).get("value")
    share = ((f.get("f_stranger_share") or {}).get("value"), (l.get("f_stranger_share") or {}).get("value"))
    return {"business_id": business_id, "from_week": first_facts_doc["week"], "to_week": last_facts_doc["week"],
            "stranger_orders": {"first": first, "last": last}, "stranger_share": {"first": share[0], "last": share[1]},
            "worked": worked, "did_not_work": did_not, "observational": True, "note": OBSERVATIONAL}
