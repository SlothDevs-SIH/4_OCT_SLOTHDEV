"""The daily lead list: what to do with each scored lead today, with a drafted reply where one is needed.

  Hot           reply today, most recent enquiry first; a personal reply that answers the exact question,
                with the price and how to order
  Warm          contact once when there is a reason (a new drop, a pre-order, an offer this week); once per reason
  Cold          nothing one to one; they see regular posts
  Disqualified  one polite reply, no follow-up; counted by reason as unmet demand

Drafts use only what the profile knows (prices, sizes, delivery area, order link). Anything it does not
know (stock dates, delivery charges, custom prices) is left as a {placeholder} for the owner to fill.
The advisor drafts, the owner sends: there is no send endpoint.
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import date
from typing import Optional

from backend.decision_engine.actions import brand_risk, protected_terms_in

WARM_REASONS = {
    "reach_demand_window_drop": ("drop", "a small drop for {event}"),
    "cap_preorder_drop": ("preorder", "a limited pre-order of {product}"),
    "repeat_reorder_incentive": ("offer", "a small first-order offer"),
}
NOTE = "Drafts are previews. Nothing is sent automatically; you copy each reply and send it yourself."


def _product(business: dict, name: Optional[str]) -> Optional[dict]:
    if not name:
        return None
    return next((p for p in business.get("products", []) if p["name"].lower() == name.lower()), None)


def _first_lower(text: str) -> str:
    return text[:1].lower() + text[1:] if text else text


def hot_reply(lead: dict, business: dict) -> tuple[str, list[str]]:
    asked = lead.get("asked_for") or {}
    p = _product(business, asked.get("product"))
    msg = (lead.get("last_message") or "").lower()
    placeholders, parts = [], ["Hi!"]
    if p is None:
        parts.append(f"Thanks for your message. Here is what we have and the prices: {business.get('order_link', 'link in bio')}.")
    elif re.search(r"\b(re)?stock\b|back in stock|available again", msg):
        parts.append(f"The {p['name']} is ₹{p['price']:,}. It is back in stock on {{restock_date}}; shall I keep one for you?")
        placeholders.append("{restock_date}")
    else:
        line = f"The {p['name']} is ₹{p['price']:,}"
        size = asked.get("size")
        if size and p.get("sizes") and size in p["sizes"]:
            line += f" and we make it in {size}"
        elif size:
            line += f" ({size})"
        parts.append(line + ".")
        if asked.get("design"):
            parts.append(f"Yes, we can do {asked['design']} (₹{{custom_price}} extra, if any).")
            placeholders.append("{custom_price}")
        city = asked.get("city")
        if city and city.lower() == (business.get("city") or "").lower():
            parts.append(f"We deliver in {city}.")
        elif city:
            parts.append(f"We deliver to {city}; delivery is ₹{{delivery_charge}}.")
            placeholders.append("{delivery_charge}")
        parts.append(f"You can order here: {business.get('order_link', 'link in bio')}"
                     f" (payment by {business.get('payment', 'UPI')}). Shall I keep one for you?")
    return " ".join(parts), placeholders


def warm_message(lead: dict, business: dict, reason_text: str) -> str:
    product = (lead.get("asked_for") or {}).get("product")
    about = f"the {product}" if product else "what we make"
    return (f"Hi! You liked {about} earlier. We are doing {reason_text} this week; "
            f"want me to keep one for you? Order: {business.get('order_link', 'link in bio')}")


def _unmet(reason: str) -> tuple[str, str, str]:
    """'size: XXL is not available' -> ('size', 'XXL', 'make size XXL');
    'city: cannot deliver to Jaipur' -> ('city', 'Jaipur', 'deliver to Jaipur')."""
    kind, _, rest = (reason or "other: request").partition(":")
    value = re.sub(r"^(cannot|can't|do not|don't)\s+(deliver|ship)\s+to\s+|^(not available in|no)\s+", "", rest.strip(), flags=re.I)
    value = re.sub(r"\s+(is|are)\s+not\s+(available|made|offered).*$|\s*\(.*\)$", "", value, flags=re.I).strip()
    phrase = {"city": f"deliver to {value}", "size": f"make size {value}", "design": f"make {value}"}.get(
        kind.strip(), f"offer {value}")
    return kind.strip(), value, phrase


def build(leads_doc: dict, business: dict, week_actions: list[dict], windows: list[dict],
          contacted: set) -> dict:
    leads = leads_doc.get("leads", [])
    open_leads = [l for l in leads if l.get("outcome", "open") == "open"]
    reasons_now = []
    for a in week_actions:
        if a["action_key"] in WARM_REASONS:
            key, text = WARM_REASONS[a["action_key"]]
            event = windows[0]["name"] if windows else "the next event"
            reasons_now.append({"key": f"{key}_{a['week']}",
                                "text": text.format(event=event, product=a.get("product_name") or "our best seller"),
                                "action_id": a["action_id"]})
    groups = defaultdict(list)
    unmet = defaultdict(lambda: defaultdict(int))
    for l in open_leads:
        entry = {k: l.get(k) for k in ("lead_id", "handle_ref", "source", "relationship", "score", "group", "rank",
                                       "reasons", "asked_for", "last_message", "last_activity", "intents")}
        entry["evidence_ids"] = [l["lead_id"]]
        entry["draft"], entry["placeholders"], entry["risk_flags"] = None, [], []
        if l["group"] == "hot":
            entry["next_action"] = "Reply today."
            entry["draft"], entry["placeholders"] = hot_reply(l, business)
        elif l["group"] == "warm":
            reason = next((r for r in reasons_now if (l["lead_id"], r["key"]) not in contacted), None)
            if reason:
                entry["next_action"] = f"Message once about {reason['text']}."
                entry["draft"] = warm_message(l, business, reason["text"])
                entry["contact_reason"] = reason["key"]
            else:
                entry["next_action"] = ("Wait for a reason to message (a new drop, a restock or a first-order offer); "
                                        "do not chase.")
        elif l["group"] == "cold":
            entry["next_action"] = "Nothing one to one; they will see your regular posts."
        else:
            kind, value, phrase = _unmet(l.get("disqualified_reason"))
            unmet[kind][value] += 1
            entry["next_action"] = "Reply politely once; no follow-up."
            entry["draft"] = f"Thank you for asking! We cannot {phrase} yet. I will let you know if that changes."
            entry["disqualified_reason"] = l.get("disqualified_reason")
        if entry["draft"]:
            flag = brand_risk(business)
            if flag and protected_terms_in([entry["draft"]]):
                entry["risk_flags"] = [flag]
        groups[l["group"]].append(entry)
    groups["hot"].sort(key=lambda e: (-date.fromisoformat(e["last_activity"]).toordinal(), e["rank"] or 10 ** 6))
    for g in ("warm", "cold", "disqualified"):
        groups[g].sort(key=lambda e: e["rank"] or 10 ** 6)
    unmet_list = [{"kind": k, "value": v, "count": n, "phrase": _unmet(f"{k}: {v}")[2]}
                  for k, vals in unmet.items() for v, n in vals.items()]
    unmet_list.sort(key=lambda u: -u["count"])
    closed = [l for l in leads if l.get("outcome", "open") != "open"]
    return {
        "business_id": leads_doc["business_id"], "week": leads_doc["week"], "as_of": leads_doc.get("as_of"),
        "synthetic": leads_doc.get("synthetic", False),
        "summary": {g: len(groups[g]) for g in ("hot", "warm", "cold", "disqualified")},
        "hot": groups["hot"], "warm": groups["warm"], "cold": groups["cold"], "disqualified": groups["disqualified"],
        "warm_reasons_this_week": reasons_now,
        "unmet_demand": {"items": unmet_list,
                         "text": ("People asked for things you do not offer yet: "
                                  + ", ".join(f"{u['phrase']} ({u['count']})" for u in unmet_list) + ".")
                                 if unmet_list else None},
        "outcomes": {"ordered": sum(l["outcome"] == "ordered" for l in closed),
                     "not_ordered": sum(l["outcome"] == "not_ordered" for l in closed)},
        "rules": {"hot": "reply today, newest first", "warm": "once per reason", "cold": "nothing one to one",
                  "disqualified": "one polite reply"},
        "note": NOTE,
    }
