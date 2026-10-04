"""Intake: privacy, pasted chats, and turning imported rows into the business's data. Pure Python.

Privacy: names, phone numbers, e-mail addresses and @handles are replaced by stable pseudonyms BEFORE any text is read by a
language model or stored with a lead. The same person always gets the same pseudonym (a salted hash), so history still links.
"""
from __future__ import annotations

import hashlib
import re
from datetime import date, datetime, timedelta
from typing import Optional

from . import leads as L

SALT = "catalyst-ai-demo"
_PHONE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_HANDLE = re.compile(r"(?<![\w.])@([A-Za-z0-9_.]{2,30})")


def pseudonym(value: str, prefix: str = "user") -> str:
    h = hashlib.sha1((SALT + (value or "").strip().lower()).encode("utf-8")).hexdigest()[:6]
    return f"{prefix}_{h}"


def redact(text: str) -> str:
    """Remove phone numbers, e-mail addresses and @handles from free text."""
    t = _EMAIL.sub("[email]", text or "")
    t = _PHONE.sub("[phone]", t)
    t = _HANDLE.sub(lambda m: "@" + pseudonym(m.group(1)), t)
    return t


# ------------------------------------------------------------------ pasted chats
_APP = re.compile(r"^\s*@?(?P<handle>[A-Za-z0-9_.]{2,30})\s*\((?P<channel>dm|comment|story|whatsapp)\)\s*:\s*(?P<text>.+)$", re.I)
_WA = re.compile(r"^\s*\[?(?P<d>\d{1,2}[/-]\d{1,2}[/-]\d{2,4}),?\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:[ap]m)?\]?\s*(?:-\s*)?(?P<name>[^:]{1,40}):\s*(?P<text>.+)$", re.I)


def _wa_date(s: str) -> Optional[date]:
    for fmt in ("%d/%m/%y", "%d/%m/%Y", "%d-%m-%y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def parse_chat(text: str, default_day: date) -> list:
    """Lines like `@riya (dm): is the tee available in L?` or a WhatsApp export line `[04/10/26, 9:41 am] Riya: price?`.
    Returns [{handle_ref, channel, date, text}] with identities pseudonymised and the text redacted. Lines that match neither format are skipped."""
    out = []
    for line in (text or "").splitlines():
        if not line.strip():
            continue
        m = _APP.match(line)
        if m:
            out.append({"handle_ref": "@" + pseudonym(m.group("handle")), "channel": m.group("channel").lower(), "date": default_day.isoformat(),
                        "text": redact(m.group("text").strip())})
            continue
        m = _WA.match(line)
        if m:
            day = _wa_date(m.group("d")) or default_day
            out.append({"handle_ref": "@" + pseudonym(m.group("name")), "channel": "whatsapp", "date": day.isoformat(),
                        "text": redact(m.group("text").strip())})
    return out


def leads_from_messages(messages: list, products: list, serves: dict, existing: list, start_id: int) -> tuple:
    """Group messages by person, read each one's intent, and add signals. Returns (leads_created_or_updated, new_leads)."""
    by_handle = {l["handle_ref"]: l for l in existing}
    touched, created = [], []
    n = start_id
    for m in messages:
        lead = by_handle.get(m["handle_ref"])
        if lead is None:
            n += 1
            lead = {"lead_id": f"lead_{n:04d}", "handle_ref": m["handle_ref"], "source": "whatsapp" if m["channel"] == "whatsapp" else m["channel"],
                    "relationship": "unknown", "created": m["date"], "signals": [], "asked_for": {"product": None, "size": None, "design": None, "city": None},
                    "intents": [], "texts": [], "outcome": "open", "outcome_date": None, "synthetic": False}
            by_handle[m["handle_ref"]] = lead
            created.append(lead)
        if lead not in touched:
            touched.append(lead)
        lab = L.label_intent(m["text"])
        lead["texts"].append({"channel": m["channel"], "date": m["date"], "text": m["text"], "intents": lab["intents"], "method": lab["method"]})
        for i in lab["intents"]:
            if i not in lead["intents"]:
                lead["intents"].append(i)
        if "not_a_lead" in lab["intents"]:
            continue
        det = L.extract_details(m["text"], products, serves)
        for k in ("product", "size", "design", "city"):
            if det.get(k) and not lead["asked_for"].get(k):
                lead["asked_for"][k] = det[k]
        for sig in L.signals_from_message(m["channel"], lab["intents"]):
            if not any(s["type"] == sig for s in lead["signals"]):
                lead["signals"].append({"type": sig, "date": m["date"]})
    return touched, created


# ------------------------------------------------------------------ imported rows -> the business's data
def _items(row: dict) -> list:
    """Items from `product` + `quantity`, or from a text like `Ferrari F1 Tee x2; Cap x1`."""
    if row.get("product"):
        return [{"name": row["product"], "category": None, "qty": int(row.get("quantity") or 1), "price": None, "unit_cost": None}]
    out = []
    for part in re.split(r"[;|]", row.get("items") or ""):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"(.+?)\s*[x×]\s*(\d+)\s*$", part, re.I)
        out.append({"name": (m.group(1) if m else part).strip(), "category": None, "qty": int(m.group(2)) if m else 1, "price": None, "unit_cost": None})
    return out


def orders_from_clean(rows: list, costs: Optional[dict] = None) -> list:
    """Cleaned import rows -> order records. Buyer identities are pseudonymised. Unit costs come from the cost sheet when the product is known."""
    costs = costs or {}
    out = []
    for r in rows:
        items = _items(r)
        total = float(r.get("revenue") or 0)
        disc = float(r.get("discount") or 0)
        total_qty = sum(i["qty"] for i in items) or 1
        for it in items:
            it["price"] = round((total + disc) / total_qty, 2)
            it["unit_cost"] = costs.get(it["name"], {}).get("full", 0)
        out.append({"order_id": r["order_id"], "date": r["ordered_at"][:10], "buyer_ref": pseudonym(r.get("customer_id") or r["order_id"], "buyer"),
                    "items": items, "gross": round(total + disc, 2), "discount": disc, "total": total, "payment": r.get("payment_mode") or "unknown",
                    "channel": r.get("channel") or "other", "relationship": r.get("relationship") or "unknown", "post_id": r.get("post_id"),
                    "dispatched_at": r["dispatched_at"][:10] if r.get("dispatched_at") else None,
                    "status": r.get("status") or ("delivered" if r.get("dispatched_at") else "open"), "is_first_order": None, "synthetic": False})
    return out


def costs_from_clean(rows: list) -> dict:
    out = {}
    for r in rows:
        parts = [float(r.get(k) or 0) for k in ("material_cost", "making_cost", "packaging_cost", "courier_cost")]
        out[r["product"]] = {"material": parts[0], "making": parts[1], "packaging": parts[2], "courier": parts[3], "full": sum(parts), "source": "estimate"}
    return out


def posts_from_clean(rows: list) -> list:
    return [{"post_id": r["post_id"], "date": r["post_date"][:10], "reach": int(float(r.get("reach") or 0)),
             "profile_visits": int(float(r.get("profile_visits") or 0)), "follows": int(float(r.get("follows") or 0)),
             "saves": int(float(r.get("saves") or 0)), "shares": int(float(r.get("shares") or 0)), "topic": r.get("topic"),
             "led_to_orders": 0, "synthetic": False} for r in rows]
