"""Olist Brazilian E-Commerce Public Dataset as a small-seller behaviour corpus (public data, CC BY-NC-SA 4.0).

What it is: about 100,000 orders placed on the Olist marketplace in Brazil (2016 to 2018) across thousands of small
sellers and many product categories, with items, prices, freight, payment, delivery dates and customer reviews.
Kaggle: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce  (a Kaggle login is needed to download).

Role in this product: it shows how real small sellers' orders, repeat buying, delivery delays and reviews behave, so
the metrics for repeat orders and capacity (delays, reviews) are calibrated on something real. It is a marketplace in
Brazil (BRL), has no "friend or stranger" tag and no unit costs, and is non-commercial. It is never presented as the
user's data.

Place the 9 CSV files in data/raw/ or data/raw/olist/ (git-ignored; never redistributed), then:

    python -m backend.data_engine.external.olist --profile
"""
from __future__ import annotations

import csv
import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from ..ml.fetch_datasets import RAW

PROFILE = Path(__file__).resolve().parent / "snapshots" / "olist_profile.json"
CITATION = "Olist (2018). Brazilian E-Commerce Public Dataset by Olist. Kaggle, https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce"
LICENCE = "CC BY-NC-SA 4.0 (non-commercial)"
FILES = ["olist_customers_dataset.csv", "olist_orders_dataset.csv", "olist_order_items_dataset.csv",
         "olist_order_reviews_dataset.csv", "olist_order_payments_dataset.csv", "olist_products_dataset.csv",
         "olist_sellers_dataset.csv", "olist_geolocation_dataset.csv", "product_category_name_translation.csv"]
SMALL_SELLER = (50, 500)       # the brief's working definition of "first 50 to 500 orders"


def locate() -> Optional[Path]:
    for d in (RAW / "olist", RAW):
        if (d / "olist_orders_dataset.csv").exists():
            return d
    return None


def rows(name: str, base: Path) -> Iterator[dict]:
    with open(base / name, encoding="utf-8-sig", newline="") as f:
        yield from csv.DictReader(f)


def _ts(s: str) -> Optional[datetime]:
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S") if s else None


def _pct(values: list, q: float) -> Optional[float]:
    if not values:
        return None
    v = sorted(values)
    i = q * (len(v) - 1)
    lo = int(i)
    hi = min(lo + 1, len(v) - 1)
    return round(v[lo] + (i - lo) * (v[hi] - v[lo]), 2)


def _band(n: int) -> str:
    return "<10" if n < 10 else "10-49" if n < 50 else "50-500" if n <= 500 else ">500"


def build_profile(base: Optional[Path] = None) -> dict:
    base = base or locate()
    if base is None:
        raise FileNotFoundError("Olist CSV files not found in data/raw/ or data/raw/olist/")
    counts = {n: sum(1 for _ in rows(n, base)) for n in FILES}
    cust_unique = {r["customer_id"]: r["customer_unique_id"] for r in rows("olist_customers_dataset.csv", base)}
    orders = {r["order_id"]: r for r in rows("olist_orders_dataset.csv", base)}
    status = Counter(o["order_status"] for o in orders.values())
    dates = sorted(o["order_purchase_timestamp"][:10] for o in orders.values() if o["order_purchase_timestamp"])
    translation = {r["product_category_name"]: r["product_category_name_english"] for r in rows("product_category_name_translation.csv", base)}
    category_of = {r["product_id"]: r["product_category_name"] for r in rows("olist_products_dataset.csv", base)}

    seller_orders = defaultdict(set)
    seller_value = defaultdict(float)
    order_sellers = defaultdict(set)
    cat_lines = Counter()
    prices, freights = [], []
    for it in rows("olist_order_items_dataset.csv", base):
        seller_orders[it["seller_id"]].add(it["order_id"])
        order_sellers[it["order_id"]].add(it["seller_id"])
        price, freight = float(it["price"]), float(it["freight_value"])
        seller_value[it["seller_id"]] += price
        prices.append(price)
        freights.append(freight)
        cat = category_of.get(it["product_id"]) or "unknown"
        cat_lines[translation.get(cat, cat)] += 1

    sizes = {s: len(o) for s, o in seller_orders.items()}
    bands = Counter(_band(n) for n in sizes.values())
    total_order_sellers = sum(sizes.values())
    lo, hi = SMALL_SELLER
    small = {s for s, n in sizes.items() if lo <= n <= hi}
    small_orders = set().union(*[seller_orders[s] for s in small]) if small else set()

    def customer_repeat(order_ids) -> dict:
        per = defaultdict(set)
        for oid in order_ids:
            o = orders.get(oid)
            if o and o["order_status"] != "canceled":
                per[cust_unique.get(o["customer_id"], o["customer_id"])].add(oid)
        n = len(per)
        rep = sum(1 for v in per.values() if len(v) >= 2)
        return {"customers": n, "repeat_customers": rep, "repeat_customer_share": round(rep / n, 4) if n else None}

    delivered = [o for o in orders.values() if o["order_status"] == "delivered" and o["order_delivered_customer_date"]]

    def delivery(os_) -> dict:
        late, days, delay = 0, [], []
        for o in os_:
            got, est, bought = _ts(o["order_delivered_customer_date"]), _ts(o["order_estimated_delivery_date"]), _ts(o["order_purchase_timestamp"])
            if got and est:
                late += got > est
            if got and bought:
                days.append((got - bought).total_seconds() / 86400)
        n = len(os_)
        return {"delivered_orders": n, "late_share": round(late / n, 4) if n else None,
                "delivery_days_median": _pct(days, 0.5), "delivery_days_p90": _pct(days, 0.9)}

    review_score = {}
    scores_all = Counter()
    with_comment = 0
    n_reviews = 0
    for r in rows("olist_order_reviews_dataset.csv", base):
        n_reviews += 1
        sc = int(r["review_score"])
        review_score[r["order_id"]] = sc
        scores_all[sc] += 1
        with_comment += bool(r["review_comment_message"].strip())

    def reviews(order_ids) -> dict:
        v = [review_score[o] for o in order_ids if o in review_score]
        return {"reviewed_orders": len(v), "mean_score": round(statistics.mean(v), 3) if v else None,
                "low_score_share_1_2": round(sum(1 for x in v if x <= 2) / len(v), 4) if v else None}

    small_delivered = [orders[o] for o in small_orders if o in orders and orders[o]["order_status"] == "delivered" and orders[o]["order_delivered_customer_date"]]
    payment = Counter(r["payment_type"] for r in rows("olist_order_payments_dataset.csv", base))
    price_med = statistics.median(prices)

    return {
        "dataset": "Olist Brazilian E-Commerce Public Dataset", "citation": CITATION, "licence": LICENCE,
        "role": "small-seller behaviour corpus (orders, repeat buying, delivery delays, reviews); marketplace in Brazil, BRL, no friend/stranger tag, no unit costs",
        "files": counts, "orders": len(orders), "order_status": dict(status), "first_order": dates[0], "last_order": dates[-1],
        "sellers": {"total": len(sizes), "by_orders_per_seller": dict(sorted(bands.items())),
                    "median_orders_per_seller": statistics.median(sizes.values()),
                    "small_sellers_50_to_500_orders": len(small),
                    "share_of_seller_orders_from_small_sellers": round(sum(sizes[s] for s in small) / total_order_sellers, 4),
                    "definition_of_small": "50 to 500 orders (the project brief's working definition)"},
        "products": {"categories": len({translation.get(c, c) for c in category_of.values() if c}),
                     "top_categories_by_order_lines": cat_lines.most_common(8)},
        "price_brl": {"median": round(price_med, 2), "p90": _pct(prices, 0.9), "mean_freight": round(statistics.mean(freights), 2),
                      "freight_share_of_item_price": round(sum(freights) / sum(prices), 4)},
        "repeat_buying": {"all_customers": customer_repeat(list(orders)), "customers_of_small_sellers": customer_repeat(small_orders)},
        "delivery": {"all": delivery(delivered), "small_sellers": delivery(small_delivered)},
        "reviews": {"count": n_reviews, "score_distribution": {str(k): v for k, v in sorted(scores_all.items())},
                    "with_comment_share": round(with_comment / n_reviews, 4), "all_orders": reviews(list(orders)),
                    "small_sellers": reviews(small_orders)},
        "payment_types": dict(payment),
    }


def write_profile(base: Optional[Path] = None) -> Path:
    PROFILE.parent.mkdir(parents=True, exist_ok=True)
    PROFILE.write_text(json.dumps(build_profile(base), indent=1), encoding="utf-8")
    return PROFILE


def load_profile() -> Optional[dict]:
    return json.loads(PROFILE.read_text(encoding="utf-8")) if PROFILE.exists() else None


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", action="store_true")
    if ap.parse_args().profile:
        print(write_profile())
