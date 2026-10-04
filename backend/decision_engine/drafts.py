"""Message draft previews for outreach recommendations. Never sent automatically:
there is no send endpoint; a person copies the text after approving the recommendation."""
from __future__ import annotations

DRAFTS = {
    ("tpl_hot_lead_followup", "whatsapp"): {
        "body": "Hi {first_name}, this is {sender} from {business}. Thank you for reaching out about your "
                "{inquiry}, and sorry for the slow reply. Could I share options and pricing with you today?"},
    ("tpl_hot_lead_followup", "email"): {
        "subject": "Your enquiry with {business}",
        "body": "Hi {first_name},\n\nThank you for getting in touch about your {inquiry}, and sorry we took a while "
                "to reply. I would be glad to share options and pricing. When is a good time for a short call?\n\n"
                "{sender}, {business}"},
    ("tpl_repeat_email_flow", "email"): {
        "subject": "Running low on your {product}?",
        "body": "Hi {first_name},\n\nIt has been about three weeks since your first order. If your {product} is "
                "running low, you can reorder in one click here: {link}\n\nThank you for trying {business}."},
    ("tpl_winback_whatsapp", "whatsapp"): {
        "body": "Hi {first_name}, it's {business}. We have missed you! Your favourites are back in stock: {link}. "
                "Reply STOP to opt out."},
}
NOTE = "Preview only. Nothing is sent automatically; a person sends it after the recommendation is approved."


class DraftError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def build(rec: dict, template: dict, channel: str, ctx: dict, lead_index: dict) -> dict:
    if template["action_type"] != "outreach":
        raise DraftError("not_outreach", f"{rec['recommendation_id']} does not contact customers")
    spec = DRAFTS.get((template["template_id"], channel))
    if not spec:
        supported = sorted(c for t, c in DRAFTS if t == template["template_id"])
        raise DraftError("unsupported_channel", f"{channel} is not available for this action; use {', '.join(supported)}")
    values = {"business": ctx.get("name", "our team"), "sender": "the team",
              "product": (ctx.get("products") or [{"name": "favourite product"}])[0]["name"],
              "link": "{reorder_link}", "first_name": "{first_name}"}
    messages = []
    if rec["targets"]["lead_ids"]:
        for lid in rec["targets"]["lead_ids"]:
            lead = lead_index.get(lid, {})
            label = lead.get("label") or "request"
            v = dict(values, inquiry=label[0].lower() + label[1:])
            messages.append({"to": lid, **{k: t.format(**v) for k, t in spec.items()}})
        audience = f"{len(messages)} leads"
    else:
        v = dict(values, inquiry="order")
        messages.append({"to": "segment", **{k: t.format(**v) for k, t in spec.items()}})
        audience = "first-time buyers about 21 days after their first order (email opt-in only)" \
            if template["template_id"] == "tpl_repeat_email_flow" else "customers who opted in"
    return {"recommendation_id": rec["recommendation_id"], "channel": channel, "status": "preview",
            "auto_send": False, "requires_approval": True, "approved": rec["status"] == "approved",
            "audience": audience, "messages": messages, "placeholders": ["{first_name}", "{reorder_link}"],
            "note": NOTE}
