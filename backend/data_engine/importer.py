"""CSV import: column detection, suggested mapping, validation, repair, quarantine, quality report.

Pure Python (stdlib csv/difflib/re): no pandas, so it stays small enough for serverless hosting.

Rules (documented, deterministic, no LLM):
- Dates: ISO is accepted as-is; day-first formats (dd/mm/yyyy, as used in India) are repaired to ISO and counted
  as `mixed_date_format`. Anything else is quarantined as `invalid_date`.
- Amounts: currency symbols and thousands separators are stripped. An order amount above 15,000 that is a whole
  multiple of 100 and becomes plausible when divided by 100 is treated as paise (`amount_in_paise`, repaired).
  This is a heuristic and is reported, never silent.
- Duplicates: the same order/lead/campaign id with identical values is merged (`duplicate_order`); the same id
  with different values is quarantined (`conflicting_duplicate`).
- (Only when the file has a campaign column.) A paid-channel order (instagram/google) with a blank campaign is quarantined (`missing_campaign_id`): spend
  cannot be attributed. A blank campaign on a direct/organic/email/whatsapp order is kept as `unattributed`;
  we never force an attribution.
- Confidence = max(0, 1 - 2*quarantined_share - 0.5*repaired_share - 0.5*unattributed_share).
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
from datetime import datetime
from difflib import SequenceMatcher
from typing import Optional

PAISE_LIMIT = 15000
MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 100_000
PAID_CHANNELS = {"instagram", "google"}

ISO_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d")
DAYFIRST_FORMATS = ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%d-%m-%Y %H:%M", "%d-%m-%Y", "%d/%m/%y")

CHANNEL_MAP = {
    "instagram": "instagram", "ig": "instagram", "insta": "instagram", "instagram ads": "instagram",
    "google": "google", "google ads": "google", "google cpc": "google", "adwords": "google", "cpc": "google",
    "email": "email", "e mail": "email", "newsletter": "email",
    "whatsapp": "whatsapp", "wa": "whatsapp", "whatsapp business": "whatsapp",
    "": "website", "direct": "website", "none": "website", "website": "website", "organic": "website", "web": "website",
    "referral": "referral", "friend": "referral", "friends": "referral",
    "instagram dm": "instagram_dm", "website form": "website_form",
}
PAYMENT_MAP = {"cod": "cod", "cash on delivery": "cod", "upi": "prepaid", "card": "prepaid", "prepaid": "prepaid",
               "razorpay": "prepaid", "netbanking": "prepaid", "wallet": "prepaid"}
STATUS_MAP = {"delivered": "delivered", "rto": "rto", "returned to origin": "rto", "returned": "returned",
              "return": "returned", "cancelled": "cancelled", "canceled": "cancelled"}
def relationship_of(text: str) -> str:
    t = norm_header(text)
    if not t:
        return "unknown"
    if "friend of" in t or "fof" in t.split() or "friends friend" in t or "friend s friend" in t or "mutual" in t:
        return "friend_of_friend"
    if "friend" in t or "family" in t or "relative" in t or "classmate" in t:
        return "friend"
    if any(k in t for k in ("stranger", "new", "found", "insta", "online", "cold", "unknown person", "saw your", "reel", "discovered")):
        return "stranger"
    return "unknown"


STAGE_MAP = {"new": "new", "qualified": "qualified", "won": "won", "lost": "lost", "closed won": "won", "closed lost": "lost"}

# canonical fields per kind: required flag, type, header synonyms (normalised)
SPECS = {
    "orders": {
        "id": "order_id",
        "fields": {
            "order_id": (True, "str", ["order id", "order number", "order no", "order ref", "name", "id", "invoice", "invoice no", "invoice number", "invoice id", "bill no", "bill number", "receipt no"]),
            "ordered_at": (True, "date", ["order date", "created at", "date", "ordered at", "placed at", "timestamp", "order time", "invoice date", "bill date", "sale date"]),
            "customer_id": (False, "str", ["customer", "customer id", "customer email", "email", "buyer"]),
            "channel": (False, "channel", ["utm source", "source", "channel", "traffic source", "referrer", "marketing channel"]),
            "campaign_id": (False, "str", ["utm campaign", "campaign", "campaign id", "campaign name"]),
            "payment_mode": (False, "payment", ["payment method", "payment mode", "payment", "gateway", "payment gateway"]),
            "revenue": (True, "money", ["order amount", "amount", "total", "order total", "revenue", "net amount", "grand total", "order value", "invoice amount", "bill amount", "sales", "price"]),
            "discount": (False, "money", ["discount", "discount amount", "coupon discount"]),
            "status": (False, "status", ["fulfilment status", "fulfillment status", "status", "order status", "delivery status"]),
            "items": (False, "str", ["items", "line items", "products", "sku", "skus"]),
            "relationship": (False, "relationship", ["relationship", "how found", "how did you find us", "found via", "customer type", "circle", "buyer type", "friend or stranger"]),
            "product": (False, "str", ["product", "item", "design", "item name", "product name"]),
            "quantity": (False, "int", ["quantity", "qty", "units", "pieces"]),
            "post_id": (False, "str", ["post", "post id", "from post", "source post"]),
            "dispatched_at": (False, "date", ["dispatched", "dispatch date", "shipped on", "shipped at", "sent on", "delivered on"]),
        },
    },
    "costs": {
        "id": "product",
        "fields": {
            "product": (True, "str", ["product", "item", "design", "item name", "product name"]),
            "material_cost": (False, "money", ["material", "material cost", "blank", "blank cost", "ingredients", "raw material", "cost of goods"]),
            "making_cost": (False, "money", ["making", "making cost", "printing", "printing cost", "labour", "labour cost", "production"]),
            "packaging_cost": (False, "money", ["packaging", "packaging cost", "packing", "box"]),
            "courier_cost": (False, "money", ["courier", "courier cost", "shipping", "shipping cost", "delivery cost"]),
        },
    },
    "insights": {
        "id": "post_id",
        "fields": {
            "post_id": (True, "str", ["post id", "post", "id", "media id"]),
            "post_date": (True, "date", ["date", "posted on", "post date", "published"]),
            "reach": (True, "int", ["reach", "accounts reached", "people reached"]),
            "profile_visits": (False, "int", ["profile visits", "profile views", "visits"]),
            "follows": (False, "int", ["follows", "new followers", "followers gained"]),
            "saves": (False, "int", ["saves", "saved"]),
            "shares": (False, "int", ["shares", "shared"]),
            "topic": (False, "str", ["topic", "caption", "design", "product"]),
        },
    },
    "leads": {
        "id": "lead_id",
        "fields": {
            "lead_id": (True, "str", ["lead id", "id", "inquiry id", "enquiry id"]),
            "created_at": (True, "date", ["created at", "created", "date", "inquiry date", "enquiry date", "received at"]),
            "channel": (False, "channel", ["source", "channel", "lead source", "utm source"]),
            "label": (False, "str", ["label", "inquiry", "enquiry", "description", "subject", "name"]),
            "expected_value_inr": (False, "money", ["expected value", "deal value", "value", "potential value", "est value"]),
            "first_response_at": (False, "date", ["first response", "first response at", "responded at", "first contact"]),
            "stage": (False, "stage", ["stage", "status", "lead status", "pipeline stage"]),
            "owner": (False, "str", ["owner", "assigned to", "sales owner"]),
        },
    },
    "campaigns": {
        "id": "campaign_id",
        "fields": {
            "campaign_id": (True, "str", ["campaign id", "id", "campaign name", "campaign"]),
            "channel": (True, "channel", ["channel", "platform", "source", "network"]),
            "name": (False, "str", ["name", "campaign name", "title"]),
            "spend": (False, "money", ["spend", "cost", "amount spent", "ad spend"]),
            "start_date": (False, "date", ["start date", "start", "begin"]),
            "end_date": (False, "date", ["end date", "end", "stop"]),
        },
    },
}


def norm_header(h: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (h or "").lower()).strip()


# ---------------------------------------------------------------- parsing
def parse_csv(raw: bytes) -> tuple[list, list]:
    """Return (columns, rows as dicts). Raises ValueError on an unusable file."""
    if len(raw) > MAX_BYTES:
        raise ValueError(f"file is larger than {MAX_BYTES // (1024 * 1024)} MB")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    reader = csv.DictReader(io.StringIO(text))
    columns = [c for c in (reader.fieldnames or []) if c is not None]
    if not columns:
        raise ValueError("no header row found")
    rows = []
    for r in reader:
        rows.append({k: (v or "").strip() for k, v in r.items() if k is not None})
        if len(rows) > MAX_ROWS:
            raise ValueError(f"more than {MAX_ROWS} rows")
    if not rows:
        raise ValueError("no data rows found")
    return columns, rows


def checksum(raw: bytes) -> str:
    return hashlib.sha1(raw).hexdigest()


# ---------------------------------------------------------------- mapping suggestion
def suggest_mapping(kind: str, columns: list) -> dict:
    """{field: {column, confidence, required}}: exact/synonym match first, then fuzzy (>= 0.72)."""
    spec = SPECS[kind]["fields"]
    normed = {c: norm_header(c) for c in columns}
    candidates = []
    for field, (required, _t, syns) in spec.items():
        names = [field.replace("_", " ")] + syns
        for col, n in normed.items():
            if n in names:
                score = 1.0
            else:
                score = max(SequenceMatcher(None, n, s).ratio() for s in names)
                if score < 0.72:
                    continue
            candidates.append((score, field, col))
    candidates.sort(key=lambda x: (-x[0], x[1], x[2]))
    used_f, used_c, out = set(), set(), {}
    for score, field, col in candidates:
        if field in used_f or col in used_c:
            continue
        used_f.add(field)
        used_c.add(col)
        out[field] = {"column": col, "confidence": round(score, 2), "required": spec[field][0]}
    for field, (required, _t, _s) in spec.items():
        out.setdefault(field, {"column": None, "confidence": 0.0, "required": required})
    return out


def missing_required(kind: str, mapping: dict) -> list:
    return [f for f, (req, _t, _s) in SPECS[kind]["fields"].items() if req and not mapping.get(f)]


# ---------------------------------------------------------------- value cleaning
def parse_date(text: str) -> tuple[Optional[datetime], bool]:
    """(datetime or None, was_already_iso)."""
    t = (text or "").strip()
    for f in ISO_FORMATS:
        try:
            return datetime.strptime(t, f), True
        except ValueError:
            pass
    for f in DAYFIRST_FORMATS:
        try:
            return datetime.strptime(t, f), False
        except ValueError:
            pass
    return None, False


def parse_money(text: str) -> Optional[float]:
    t = re.sub(r"(?i)(₹|rs\.?|inr)", "", text or "").replace(",", "").strip()
    if not t:
        return None
    try:
        v = float(t)
    except ValueError:
        return None
    return v if v >= 0 else None


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _lookup(table: dict, text: str, default: str) -> str:
    return table.get(norm_header(text), default)


class _Issues:
    def __init__(self):
        self.count, self.example, self.action = {}, {}, {}

    def add(self, code: str, action: str, example: str):
        self.count[code] = self.count.get(code, 0) + 1
        self.example.setdefault(code, example)
        self.action[code] = action

    def as_list(self) -> list:
        order = ["duplicate_order", "conflicting_duplicate", "missing_campaign_id", "mixed_date_format", "amount_in_paise",
                 "invalid_date", "invalid_amount", "missing_required", "unattributed"]
        codes = sorted(self.count, key=lambda c: (order.index(c) if c in order else 99, c))
        return [{"code": c, "count": self.count[c], "action": self.action[c], "example": self.example[c]} for c in codes]


# ---------------------------------------------------------------- the import run
def run_import(kind: str, rows: list, mapping: dict, paise: bool = True) -> dict:
    """mapping: {canonical_field: source column}. Returns clean rows, quarantined rows and counters.
    `paise` enables the INR amount-in-paise repair; turn it off for files in another currency."""
    spec = SPECS[kind]
    idf = spec["id"]
    issues, clean, quarantined, seen = _Issues(), [], [], {}
    repaired_rows = dup_merged = unattributed = 0
    unattributed_revenue = 0.0

    def quarantine(i, code, raw, message):
        quarantined.append({"row_number": i + 2, "reason_code": code, "raw": raw})
        issues.add(code, "quarantined", message)

    for i, raw in enumerate(rows):
        rec, repaired = {}, False
        bad = None
        for field, (required, typ, _s) in spec["fields"].items():
            col = mapping.get(field)
            val = raw.get(col, "") if col else ""
            if typ == "date":
                if not val:
                    if required:
                        bad = ("missing_required", f"{field} is blank (row {i + 2})")
                        break
                    rec[field] = None
                    continue
                dt, was_iso = parse_date(val)
                if dt is None:
                    bad = ("invalid_date", f"{val!r} is not a date (row {i + 2})")
                    break
                rec[field] = _iso(dt)
                if not was_iso:
                    repaired = True
                    issues.add("mixed_date_format", "repaired_to_iso", f"{val} -> {dt.strftime('%Y-%m-%d')}")
            elif typ == "money":
                if not val:
                    if required:
                        bad = ("missing_required", f"{field} is blank (row {i + 2})")
                        break
                    rec[field] = None
                    continue
                m = parse_money(val)
                if m is None:
                    bad = ("invalid_amount", f"{val!r} is not an amount (row {i + 2})")
                    break
                if paise and kind == "orders" and field == "revenue" and m > PAISE_LIMIT and m % 100 == 0 and m / 100 <= PAISE_LIMIT:
                    issues.add("amount_in_paise", "repaired_units", f"{int(m)} -> {m / 100:.2f} INR")
                    m, repaired = m / 100, True
                rec[field] = round(m, 2)
            elif typ == "relationship":
                rec[field] = relationship_of(val)
            elif typ == "int":
                if not val:
                    if required:
                        bad = ("missing_required", f"{field} is blank (row {i + 2})")
                        break
                    rec[field] = None
                    continue
                m = parse_money(val)
                if m is None or m != int(m):
                    bad = ("invalid_amount", f"{val!r} is not a whole number (row {i + 2})")
                    break
                rec[field] = int(m)
            elif typ == "channel":
                rec[field] = _lookup(CHANNEL_MAP, val, "other")
            elif typ == "payment":
                rec[field] = _lookup(PAYMENT_MAP, val, "unknown") if val else None
            elif typ == "status":
                rec[field] = _lookup(STATUS_MAP, val, "unknown") if val else None
            elif typ == "stage":
                rec[field] = _lookup(STAGE_MAP, val, "new") if val else "new"
            else:
                if required and not val:
                    bad = ("missing_required", f"{field} is blank (row {i + 2})")
                    break
                rec[field] = val or None
        if bad:
            quarantine(i, bad[0], raw, bad[1])
            continue

        has_campaign = bool(mapping.get("campaign_id"))     # a sheet without a campaign column is not penalised for it
        if kind == "orders" and has_campaign and not rec.get("campaign_id"):
            if rec.get("channel") in PAID_CHANNELS:
                quarantine(i, "missing_campaign_id", raw,
                           f"campaign blank on a paid {rec['channel']} order ({rec[idf]})")
                continue
        key = rec[idf]
        if key in seen:
            if seen[key] == rec:
                dup_merged += 1
                issues.add("duplicate_order" if kind == "orders" else "duplicate_order", "merged",
                           f"{key} appears twice with the same values")
            else:
                quarantine(i, "conflicting_duplicate", raw, f"{key} appears twice with different values")
            continue
        seen[key] = rec
        if repaired:
            repaired_rows += 1
        if kind == "orders" and has_campaign and not rec.get("campaign_id"):
            unattributed += 1
            unattributed_revenue += rec.get("revenue") or 0
            issues.add("unattributed", "kept_as_unattributed", f"{rec['channel']} order with no campaign ({key})")
        clean.append({**rec, "source_row": i + 2})

    total = len(rows)
    q = len(quarantined)
    confidence = round(max(0.0, 1 - 2 * (q / total) - 0.5 * (repaired_rows / total) - 0.5 * (unattributed / total)), 2) if total else 0.0
    return {"clean": clean, "quarantined": quarantined, "issues": issues.as_list(), "rows_total": total,
            "rows_loaded": len(clean), "rows_repaired": repaired_rows, "rows_quarantined": q, "duplicates_merged": dup_merged,
            "unattributed": unattributed, "unattributed_revenue": round(unattributed_revenue, 2), "confidence": confidence}


def badge(confidence: float) -> str:
    return "high" if confidence >= 0.85 else "medium" if confidence >= 0.70 else "low"


def report_for(import_id: str, kind: str, run: dict, status: str = "loaded") -> dict:
    """The `imports[]` entry of data_quality.json (contract shape)."""
    return {"import_id": import_id, "kind": kind, "status": status, "rows_total": run["rows_total"],
            "rows_loaded": run["rows_loaded"], "rows_repaired": run["rows_repaired"],
            "rows_quarantined": run["rows_quarantined"], "duplicates_merged": run["duplicates_merged"],
            "confidence": run["confidence"], "issues": run["issues"]}
