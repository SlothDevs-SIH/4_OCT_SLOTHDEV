"""Message drafts. Previews only: the advisor drafts, the owner sends. There is no send endpoint."""
from __future__ import annotations

from datetime import date, timedelta

from backend.decision_engine.actions import brand_risk, protected_terms_in

NOTE = "Preview only. Nothing is sent automatically; you copy it and send it yourself."

ACTION_DRAFTS = {
    ("reach_partner_collab", "instagram_dm"):
        "Hi {partner_name}! I run {business}, a small {category} business from {city}. Your posts get real "
        "conversation from people who'd like what I make. Could we do a small collab: I send you a free {product} "
        "and you share a story or post tagging us? Happy to keep it simple. Thank you!",
    ("reach_community_share", "whatsapp"):
        "Hi all! I started {business} ({category}, made in {city}). If you know anyone who'd like it, could you "
        "share our page? Orders: {order_link}. Thank you so much!",
    ("reach_buyer_tag_share", "whatsapp"):
        "Thank you for ordering from {business}! If you post a photo, please tag us. It really helps a small "
        "business reach new people.",
    ("reach_demand_window_drop", "instagram_post"):
        "{event_name} is coming ({event_dates}). A small drop of {product} goes live on {drop_date}. Limited "
        "pieces; order via {order_link}.",
    ("repeat_thank_you_next_drop", "whatsapp"):
        "Hi {{first_name}}, thank you for ordering from {business}! Something new is coming next week: {product}. "
        "Shall I keep one for you?",
    ("cap_preorder_drop", "instagram_post"):
        "Pre-orders for {product} are open until {close_date}. We make them in one batch and deliver from "
        "{delivery_date}. Limited to {limit} orders so every one is made fresh.",
}


class DraftError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _flags(business: dict, text: str, visible: bool) -> list:
    flag = brand_risk(business, raises_visibility=visible)
    if flag and protected_terms_in([text]):
        return [flag]
    return [flag] if flag and visible else []


def action_draft(action: dict, business: dict, channel: str, windows: list, partner: dict | None) -> dict:
    tmpl = ACTION_DRAFTS.get((action["action_key"], channel))
    if not tmpl:
        options = sorted(c for k, c in ACTION_DRAFTS if k == action["action_key"])
        if not options:
            raise DraftError("no_draft", f"{action['title']} does not need a message")
        raise DraftError("unsupported_channel", f"use {', '.join(options)} for this action")
    as_of = date.fromisoformat(action["due"]) - timedelta(days=7)
    products = business.get("products", [])
    safe = next((p["name"] for p in products if not protected_terms_in([p["name"]])), products[0]["name"])
    target_product = action.get("product_name") or safe
    w = windows[0] if windows else None
    values = {
        "business": business["name"], "category": business.get("category", "small"), "city": business.get("city", ""),
        "order_link": business.get("order_link", "the link in our bio"), "product": safe,
        "partner_name": partner["name"].split(" (")[0] if partner else "there",
        "event_name": w["name"] if w else "", "event_dates": f"{w['from']} to {w['to']}" if w else "",
        "drop_date": (date.fromisoformat(w["from"]) - timedelta(days=2)).isoformat() if w else "",
        "close_date": (as_of + timedelta(days=4)).isoformat(),
        "delivery_date": (as_of + timedelta(days=7)).isoformat(),
        "limit": business.get("capacity_orders_per_week", 20),
    }
    if action["action_key"] == "cap_preorder_drop":
        values["product"] = target_product
    text = tmpl.format(**values)
    return {"action_id": action["action_id"], "channel": channel, "status": "preview", "auto_send": False,
            "requires_approval": action["requires_approval"], "text": text,
            "placeholders": ["{first_name}"] if "{first_name}" in text else [],
            "risk_flags": _flags(business, text, action.get("raises_visibility", False)), "note": NOTE}
