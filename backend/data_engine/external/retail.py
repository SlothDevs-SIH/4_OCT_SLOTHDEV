"""UCI Online Retail II as a validation corpus for intake and order metrics (public data, CC BY 4.0).

What it is: all transactions of a UK-based, non-store online gift-ware retailer, Dec 2009 to Dec 2011
(about 1.07M lines; many customers are wholesalers). Chen, D. (2012). Online Retail II. UCI Machine Learning
Repository. https://doi.org/10.24432/C5CG6D

Role in this product: proves that the order-sheet intake and the repeat-customer and concentration metrics work on
real, messy transaction data at scale. It is NOT a benchmark for student maker-sellers and is never presented as
Box Box's data.

    python -m backend.data_engine.ml.fetch_datasets --retail     # download (45 MB zip)
    python -m backend.data_engine.external.retail --convert       # xlsx -> csv (a few minutes, needs openpyxl)
    python -m backend.data_engine.external.retail --profile       # stream the CSV, write the committed profile
"""
from __future__ import annotations

import csv
import io
import json
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from .. import importer, ordermetrics
from ..ml.fetch_datasets import RAW

ZIP = RAW / "online-retail-ii.zip"
CSV_PATH = RAW / "online_retail_ii.csv"
PROFILE = Path(__file__).resolve().parent / "snapshots" / "retail_ii_profile.json"
COLUMNS = ["invoice", "stock_code", "description", "quantity", "invoice_date", "price", "customer_id", "country"]
CITATION = "Chen, D. (2012). Online Retail II. UCI Machine Learning Repository. https://doi.org/10.24432/C5CG6D"
LICENCE = "CC BY 4.0"
EXPECTED_LINES = 1_067_371


def convert(force: bool = False) -> Path:
    """Stream the xlsx inside the zip to a CSV (one file, both sheets). Offline script; needs openpyxl."""
    if CSV_PATH.exists() and not force:
        return CSV_PATH
    from openpyxl import load_workbook
    with zipfile.ZipFile(ZIP) as z:
        name = next(n for n in z.namelist() if n.lower().endswith(".xlsx"))
        data = io.BytesIO(z.read(name))
    wb = load_workbook(data, read_only=True, data_only=True)
    tmp = CSV_PATH.with_suffix(".csv.part")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for ws in wb.worksheets:
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if i == 0:
                    continue                                  # header of each sheet
                inv, code, desc, qty, dt, price, cust, country = row[:8]
                if isinstance(dt, datetime):
                    dt = dt.strftime("%Y-%m-%d %H:%M:%S")
                cust = "" if cust is None else str(int(cust)) if isinstance(cust, (int, float)) else str(cust)
                w.writerow([inv, code, desc, qty, dt, price, cust, country])
    tmp.replace(CSV_PATH)
    return CSV_PATH


def lines(path: Path = CSV_PATH) -> Iterator[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        yield from csv.DictReader(f)


def _is_product(code: str) -> bool:
    """Real products have stock codes starting with a digit; postage, fees, manual adjustments and samples do not."""
    return bool(code) and code[0].isdigit()


def stream_orders(rows) -> tuple:
    """One pass over the lines. Returns (orders, quality counters). An order = a non-cancelled invoice with a customer id."""
    q = Counter()
    inv = {}
    for r in rows:
        q["lines"] += 1
        invoice = r["invoice"]
        qty, price = float(r["quantity"] or 0), float(r["price"] or 0)
        if invoice.startswith("C"):
            q["cancellation_lines"] += 1
            continue
        if qty <= 0 or price <= 0:
            q["non_positive_quantity_or_price_lines"] += 1
            continue
        if not _is_product(r["stock_code"]):
            q["non_product_lines"] += 1                       # postage, bank charges, adjustments, samples
            continue
        if not r["customer_id"]:
            q["missing_customer_id_lines"] += 1
        o = inv.setdefault(invoice, {"day": r["invoice_date"][:10], "customer": r["customer_id"] or None, "revenue": 0.0})
        o["revenue"] += qty * price
    orders = [ordermetrics.Order(k, datetime.strptime(v["day"], "%Y-%m-%d").date(), v["customer"], v["revenue"]) for k, v in inv.items()]
    q["orders"] = len(orders)
    return orders, q


def import_check(orders: list, sample: Optional[int] = None) -> dict:
    """Push the invoices through OUR import pipeline (as an order sheet) and report what it repaired or quarantined."""
    orders = orders[:sample] if sample else orders
    rows = [{"Invoice": o.order_id, "Date": o.day.isoformat(), "Customer": o.customer or "",
             "Amount": f"{o.revenue:.2f}"} for o in orders]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["Invoice", "Date", "Customer", "Amount"])
    w.writeheader()
    w.writerows(rows)
    columns, parsed = importer.parse_csv(buf.getvalue().encode("utf-8"))
    sug = importer.suggest_mapping("orders", columns)
    mapping = {f: m["column"] for f, m in sug.items() if m["column"]}
    run = importer.run_import("orders", parsed, mapping, paise=False)        # amounts are GBP here
    return {"rows": run["rows_total"], "loaded": run["rows_loaded"], "repaired": run["rows_repaired"],
            "quarantined": run["rows_quarantined"], "mapping_auto_detected": {f: c for f, c in mapping.items()},
            "date_format_repaired": next((i["count"] for i in run["issues"] if i["code"] == "mixed_date_format"), 0),
            "confidence": run["confidence"]}


def build_profile(path: Path = CSV_PATH) -> dict:
    orders, q = stream_orders(lines(path))
    summary = ordermetrics.summarize(orders)
    linked = [o for o in orders if o.customer]
    return {
        "dataset": "UCI Online Retail II", "citation": CITATION, "licence": LICENCE,
        "role": "validation corpus for intake and order metrics; not a benchmark for student maker-sellers",
        "source_lines": q["lines"], "quality": dict(q),
        "quality_share": {k: round(v / q["lines"], 4) for k, v in q.items() if k not in ("lines", "orders")},
        "order_metrics": summary, "monthly": ordermetrics.monthly(orders),
        "intake_check": import_check(orders),
        "linked_orders": len(linked),
    }


def write_profile(path: Path = CSV_PATH) -> Path:
    PROFILE.parent.mkdir(parents=True, exist_ok=True)
    PROFILE.write_text(json.dumps(build_profile(path), indent=1), encoding="utf-8")
    return PROFILE


def load_profile() -> Optional[dict]:
    return json.loads(PROFILE.read_text(encoding="utf-8")) if PROFILE.exists() else None


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--convert", action="store_true")
    ap.add_argument("--profile", action="store_true")
    a = ap.parse_args()
    if a.convert:
        print(convert())
    if a.profile:
        print(write_profile())
