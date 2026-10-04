"""The deliberately messy orders export used for the import demo (synthetic, deterministic).

It is the same orders as the demo tenant, written the way a real store export looks (odd headers, mixed
date formats, channel names that vary, amounts in paise, duplicate rows, blank campaigns), with the
defect counts below injected on purpose. `ground_truth` says exactly what was injected so the importer
can be tested against it.
"""
from __future__ import annotations

import csv
import io
import random
from datetime import datetime

from . import config as C
from .generate import build_tenant

HEADERS = ["Order ID", "Order Date", "Customer", "UTM Source", "UTM Campaign", "Payment Method",
           "Order Amount (INR)", "Discount (INR)", "Fulfilment Status", "Items"]

N_DUPLICATES = 25
N_MISSING_CAMPAIGN = 47      # paid-social/search orders with a blank campaign (before the baseline window)
N_US_DATES = 0
N_DMY_DATES = 189            # dates written dd/mm/yyyy instead of ISO
N_PAISE = 25                 # amounts written in paise (89900 instead of 899)
CLEAN_BEFORE = "2026-08-30"  # injected quarantines only touch orders before the baseline window, so KPI anchors stay exact

SOURCE_VARIANTS = {
    "instagram": ["instagram", "Instagram", "ig", "insta"],
    "google": ["google", "Google Ads", "google_cpc"],
    "email": ["email", "Email", "newsletter"],
    "whatsapp": ["whatsapp", "WhatsApp", "wa"],
    "website": ["", "direct", "(direct)"],
    "referral": ["referral", "Referral"],
}
STATUS_TEXT = {"delivered": ["Delivered", "delivered", "DELIVERED"], "rto": ["RTO", "Returned to origin", "rto"]}
PAYMENT_TEXT = {"cod": ["COD", "Cash on Delivery", "cod"], "prepaid": ["UPI", "Card", "Prepaid", "Razorpay"]}


def _items(o: dict) -> str:
    return "; ".join(f"{it['sku']} x{it['qty']}" for it in o["items"])


def build_rows() -> tuple[list, dict]:
    """Return (rows as dicts keyed by HEADERS, ground_truth)."""
    t = build_tenant("baseline")
    rng = random.Random(C.SEED + 101)
    camp_name = {c["campaign_id"]: c["name"] for c in t.campaigns}
    orders = list(t.orders)

    missing_ids = set()
    pool = [o["order_id"] for o in orders if o["channel"] in ("instagram", "google") and o["ordered_at"][:10] < CLEAN_BEFORE]
    missing_ids = set(rng.sample(pool, N_MISSING_CAMPAIGN))
    dmy_ids = set(rng.sample([o["order_id"] for o in orders], N_DMY_DATES))
    paise_ids = set(rng.sample([o["order_id"] for o in orders if o["order_id"] not in missing_ids], N_PAISE))
    dup_ids = rng.sample([o["order_id"] for o in orders if o["order_id"] not in missing_ids], N_DUPLICATES)

    rows, by_id = [], {}
    for o in orders:
        ts = datetime.strptime(o["ordered_at"], "%Y-%m-%dT%H:%M:%SZ")
        date_txt = ts.strftime("%d/%m/%Y %H:%M") if o["order_id"] in dmy_ids else ts.strftime("%Y-%m-%d %H:%M:%S")
        amount = o["revenue"] * 100 if o["order_id"] in paise_ids else o["revenue"]
        campaign = "" if (o["order_id"] in missing_ids or not o["campaign_id"]) else camp_name[o["campaign_id"]]
        row = {
            "Order ID": o["order_id"], "Order Date": date_txt, "Customer": o["customer_id"],
            "UTM Source": rng.choice(SOURCE_VARIANTS[o["channel"]]), "UTM Campaign": campaign,
            "Payment Method": rng.choice(PAYMENT_TEXT[o["payment_mode"]]), "Order Amount (INR)": amount,
            "Discount (INR)": o["discount"], "Fulfilment Status": rng.choice(STATUS_TEXT[o["status"]]), "Items": _items(o),
        }
        rows.append(row)
        by_id[o["order_id"]] = row
    for oid in dup_ids:
        rows.append(dict(by_id[oid]))
    rng.shuffle(rows)  # a real export is not neatly ordered

    unattributed = [o for o in orders if o["order_id"] not in missing_ids and not o["campaign_id"]]
    truth = {
        "rows_total": len(rows), "orders": len(orders), "duplicates": N_DUPLICATES, "missing_campaign": N_MISSING_CAMPAIGN,
        "dmy_dates": N_DMY_DATES, "paise": N_PAISE, "unattributed_orders": len(unattributed),
        "unattributed_revenue": sum(o["revenue"] for o in unattributed),
        "missing_ids": sorted(missing_ids), "dmy_ids": sorted(dmy_ids), "paise_ids": sorted(paise_ids), "dup_ids": sorted(dup_ids),
        "total_revenue": sum(o["revenue"] for o in orders),
    }
    return rows, truth


def build_csv() -> str:
    rows, _ = build_rows()
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=HEADERS)
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def ground_truth() -> dict:
    return build_rows()[1]
