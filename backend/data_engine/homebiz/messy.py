"""A deliberately messy orders export for a demo business (the way a home seller's sheet really looks), with known defects.

Headers are odd, dates are written two ways, amounts have currency symbols and commas, "how did they find you?" is free text,
and a few rows are duplicated. `truth` says exactly what was injected, so the importer can be checked against it.
"""
from __future__ import annotations

import csv
import io
import random
from datetime import date

from .model import BusinessData, as_of_for, d

HEADERS = ["Order ID", "Order Date", "Customer", "Items", "Amount (INR)", "Discount (INR)", "How did they find you?", "Channel",
           "Payment", "Dispatched On", "Source Post"]
FRIEND_TEXT = ["friend", "Friend", "close friend", "family"]
FOF_TEXT = ["friend of a friend", "friends friend", "FOF", "mutual friend"]
STRANGER_TEXT = ["stranger", "found you on insta", "new customer", "saw your reel"]
N_DUP, N_DMY, N_UNKNOWN, N_RUPEE = 6, 15, 8, 12


def _items(o: dict) -> str:
    return "; ".join(f"{i['name']} x{i['qty']}" for i in o["items"])


def build_rows(data: BusinessData, week: int) -> tuple:
    as_of = as_of_for(week, data)
    rng = random.Random(len(data.orders) * 7 + week)
    orders = [o for o in data.orders if d(o["date"]) < as_of]
    ids = [o["order_id"] for o in orders]
    dmy = set(rng.sample(ids, min(N_DMY, len(ids))))
    unknown = set(rng.sample([i for i in ids if i not in dmy], min(N_UNKNOWN, len(ids))))
    rupee = set(rng.sample(ids, min(N_RUPEE, len(ids))))
    dups = rng.sample(ids, min(N_DUP, len(ids)))
    rows, by_id = [], {}
    for o in orders:
        dt = d(o["date"])
        date_txt = dt.strftime("%d/%m/%Y") if o["order_id"] in dmy else dt.isoformat()
        text = "" if o["order_id"] in unknown else rng.choice({"friend": FRIEND_TEXT, "friend_of_friend": FOF_TEXT, "stranger": STRANGER_TEXT}[o["relationship"]])
        amount = f"₹ {o['total']:,}" if o["order_id"] in rupee else str(o["total"])
        row = {"Order ID": o["order_id"], "Order Date": date_txt, "Customer": o["buyer_ref"], "Items": _items(o), "Amount (INR)": amount,
               "Discount (INR)": o["discount"], "How did they find you?": text, "Channel": o["channel"].replace("_", " "),
               "Payment": o["payment"].upper(), "Dispatched On": o["dispatched_at"] or "", "Source Post": o["post_id"] or ""}
        rows.append(row)
        by_id[o["order_id"]] = row
    for oid in dups:
        rows.append(dict(by_id[oid]))
    rng.shuffle(rows)
    truth = {"rows_total": len(rows), "orders": len(orders), "duplicates": len(dups), "dmy_dates": len(dmy), "unknown_relationship": len(unknown),
             "rupee_amounts": len(rupee), "total_revenue": sum(o["total"] for o in orders)}
    return rows, truth


def build_csv(data: BusinessData, week: int) -> str:
    rows, _ = build_rows(data, week)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=HEADERS)
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()
