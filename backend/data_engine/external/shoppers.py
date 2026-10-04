"""UCI Online Shoppers Purchasing Intention as a conversion corpus (public data).

What it is: 12,330 website sessions (one per user over a year) of an online shop, each labelled with whether the session
ended in a purchase. It records visitor type (new or returning), pages visited, bounce and exit rates and the page
value of the pages seen. Sakar, C. and Kastro, Y. (2018). Online Shoppers Purchasing Intention Dataset. UCI Machine
Learning Repository. https://doi.org/10.24432/C5F88Q   (UCI's metadata lists no licence: confirm the terms on the UCI page.)

Role in this product: the closest public analogue to "new visitors vs people the shop already knows" and to the
conversion step (people see the shop but do not buy). It checks the direction of the lead-score signals: intent
(high page value, product pages) should outweigh light interest, and new visitors behave differently from returning
ones. It is not Box Box's data.

    python -m backend.data_engine.external.shoppers --fetch --profile
"""
from __future__ import annotations

import csv
import io
import json
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Optional

from ..ml.fetch_datasets import RAW

URL = "https://archive.ics.uci.edu/static/public/468/online+shoppers+purchasing+intention+dataset.zip"
CSV_PATH = RAW / "online_shoppers_intention.csv"
PROFILE = Path(__file__).resolve().parent / "snapshots" / "shoppers_profile.json"
CITATION = ("Sakar, C. and Kastro, Y. (2018). Online Shoppers Purchasing Intention Dataset. UCI Machine Learning Repository. "
            "https://doi.org/10.24432/C5F88Q")
LICENCE = "not stated in UCI's metadata: confirm on the UCI page; cited, not redistributed"


def fetch(force: bool = False) -> Path:
    if CSV_PATH.exists() and not force:
        return CSV_PATH
    RAW.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(URL, timeout=120) as r:
        z = zipfile.ZipFile(io.BytesIO(r.read()))
    name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
    CSV_PATH.write_bytes(z.read(name))
    return CSV_PATH


def _rate(n: int, d: int) -> Optional[float]:
    return round(n / d, 4) if d else None


def build_profile(path: Path = CSV_PATH) -> dict:
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    buy = lambda r: r["Revenue"].strip().lower() == "true"   # noqa: E731
    n, bought = len(rows), sum(buy(r) for r in rows)

    def group(key) -> dict:
        g = defaultdict(lambda: [0, 0])
        for r in rows:
            k = key(r)
            g[k][0] += 1
            g[k][1] += buy(r)
        return {k: {"sessions": v[0], "purchases": v[1], "conversion": _rate(v[1], v[0])} for k, v in sorted(g.items())}

    by_visitor = group(lambda r: r["VisitorType"])
    by_value = group(lambda r: "page_value > 0" if float(r["PageValues"]) > 0 else "page_value = 0")
    by_product_pages = group(lambda r: "0-9 product pages" if int(r["ProductRelated"]) < 10 else "10-49" if int(r["ProductRelated"]) < 50 else "50+")
    by_bounce = group(lambda r: "bounce rate = 0" if float(r["BounceRates"]) == 0 else "bounce rate > 0")
    by_weekend = group(lambda r: "weekend" if r["Weekend"].strip().lower() == "true" else "weekday")
    new, ret = by_visitor.get("New_Visitor", {}), by_visitor.get("Returning_Visitor", {})
    return {
        "dataset": "UCI Online Shoppers Purchasing Intention", "citation": CITATION, "licence": LICENCE,
        "role": "conversion corpus; checks the direction of lead-score signals; new vs returning visitors; not Box Box's data",
        "sessions": n, "purchases": bought, "overall_conversion": _rate(bought, n),
        "by_visitor_type": by_visitor, "by_page_value": by_value, "by_product_pages_viewed": by_product_pages,
        "by_bounce": by_bounce, "by_weekend": by_weekend,
        "reading": {"new_vs_returning_conversion_ratio": round(new["conversion"] / ret["conversion"], 3) if new and ret else None,
                    "page_value_lift": round(by_value["page_value > 0"]["conversion"] / by_value["page_value = 0"]["conversion"], 1)},
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
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--profile", action="store_true")
    a = ap.parse_args()
    if a.fetch:
        print(fetch())
    if a.profile:
        print(write_profile())
