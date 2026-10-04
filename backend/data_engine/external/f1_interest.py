"""F1 interest from Wikipedia page views (public data: Wikimedia REST API, no key).

Why: the advisor suggests timing a design drop or a post around a race weekend. This module measures, from
public data, whether attention really rises on race weekends, so the advice can cite a number instead of an
assumption. It is a proxy for interest in F1, not for sales of any brand, and it says so.

Daily views of the English Wikipedia article "Formula One" (users only, all access), snapshotted offline.

    python -m backend.data_engine.external.f1_interest --refresh
"""
from __future__ import annotations

import json
import urllib.request
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from statistics import mean
from typing import Optional

from . import f1_calendar

SNAPSHOT = Path(__file__).resolve().parent / "snapshots" / "f1_interest_formula_one.json"
URL = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/"
       "{article}/daily/{start}/{end}")
UA = {"User-Agent": "slothdev-hackathon/1.0 (student project; github.com/SlothDevs-SIH/4_OCT_SLOTHDEV)"}
ARTICLE = "Formula_One"


def fetch(article: str, start: str, end: str) -> dict:
    req = urllib.request.Request(URL.format(article=article, start=start.replace("-", ""), end=end.replace("-", "")), headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        items = json.load(r)["items"]
    return {f"{it['timestamp'][:4]}-{it['timestamp'][4:6]}-{it['timestamp'][6:8]}": it["views"] for it in items}


def refresh(start: str = "2025-01-01", end: str = "2026-10-03") -> Path:
    series = fetch(ARTICLE, start, end)
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps({
        "article": ARTICLE, "project": "en.wikipedia", "metric": "daily page views (users, all access)",
        "source": "Wikimedia REST API", "licence": "Wikimedia pageview data is released under CC0",
        "caveat": "A proxy for general interest in F1, not for any brand's sales.",
        "from": start, "to": end, "series": series}), encoding="utf-8")
    return SNAPSHOT


@lru_cache(maxsize=1)
def load() -> Optional[dict]:
    return json.loads(SNAPSHOT.read_text(encoding="utf-8")) if SNAPSHOT.exists() else None


def uplift(seasons: tuple = (2025, 2026), series: Optional[dict] = None) -> dict:
    """Mean daily views on race-weekend days vs all other days, overall and per season, with the sample sizes."""
    series = series or (load() or {}).get("series", {})
    days = {date.fromisoformat(k): v for k, v in series.items()}
    out = {"seasons": {}}
    all_w, all_o = [], []
    for season in seasons:
        try:
            cal = f1_calendar.calendar(season)
        except FileNotFoundError:
            continue
        weekend_days = set()
        for r in cal:
            d, end = date.fromisoformat(r["weekend_start"]), date.fromisoformat(r["weekend_end"])
            while d <= end:
                weekend_days.add(d)
                d += timedelta(days=1)
        w = [v for d, v in days.items() if d.year == season and d in weekend_days]
        o = [v for d, v in days.items() if d.year == season and d not in weekend_days]
        if w and o:
            out["seasons"][str(season)] = {"weekend_days": len(w), "other_days": len(o), "mean_views_weekend": round(mean(w)),
                                           "mean_views_other": round(mean(o)), "uplift": round(mean(w) / mean(o), 3)}
            all_w += w
            all_o += o
    if all_w and all_o:
        out["overall"] = {"weekend_days": len(all_w), "other_days": len(all_o), "uplift": round(mean(all_w) / mean(all_o), 3)}
    out["caveat"] = "Interest in F1 in general (Wikipedia page views), not sales of any brand."
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    if ap.parse_args().refresh:
        print(refresh())
