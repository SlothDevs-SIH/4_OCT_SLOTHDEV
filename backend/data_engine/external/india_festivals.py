"""India festival and holiday calendar as market context (public data: the `holidays` open-source package, MIT).

Why it matters: festivals are demand windows for many home businesses (gifting, sweets, clothing, decor). The advisor
can time an action or warn about capacity before one. Unlike the F1 calendar, there is NO measured demand uplift for
festivals in our public data, so the uplift is a labelled scenario assumption, never a measured fact.

A snapshot is committed so the runtime needs no extra library. Refresh with (needs `pip install holidays`):

    python -m backend.data_engine.external.india_festivals --refresh 2025 2026 2027
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Optional

SNAPSHOT = Path(__file__).resolve().parent / "snapshots" / "india_festivals.json"
BUILD_UP_DAYS = 7
# Major gifting / consumption festivals (the full public-holiday list also has official holidays that are not demand windows)
DEMAND_FESTIVALS = ("diwali", "deepavali", "dussehra", "holi", "raksha bandhan", "rakshabandhan", "eid", "christmas",
                    "ganesh", "navratri", "durga", "onam", "pongal", "makar sankranti", "baisakhi", "janmashtami", "karwa")


def refresh(*years: int) -> Path:
    import holidays
    events = []
    for y in years:
        for d, name in sorted(holidays.India(years=[y]).items()):
            events.append({"name": name, "date": d.isoformat(), "demand_window": any(k in name.lower() for k in DEMAND_FESTIVALS)})
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps({"source": "python-holidays (MIT), India calendar", "years": list(years),
                                    "note": "Dates of festivals and public holidays. No measured demand uplift exists for them in our data.",
                                    "events": events}, indent=1), encoding="utf-8")
    return SNAPSHOT


@lru_cache(maxsize=1)
def events() -> list:
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))["events"]


def demand_events(start: Optional[str] = None, end: Optional[str] = None) -> list:
    """Demand-window festivals whose build-up or day falls in [start, end]; each has window_start (7 days before) and window_end."""
    a = date.fromisoformat(start) if start else date.min
    b = date.fromisoformat(end) if end else date.max
    out = []
    for e in events():
        if not e["demand_window"]:
            continue
        d = date.fromisoformat(e["date"])
        w0 = d - timedelta(days=BUILD_UP_DAYS)
        if w0 <= b and d >= a:
            out.append({"name": e["name"], "date": e["date"], "window_start": w0.isoformat(), "window_end": e["date"],
                        "kind": "festival"})
    return out


def next_event(day: str) -> Optional[dict]:
    d = date.fromisoformat(day)
    upcoming = [e for e in events() if e["demand_window"] and date.fromisoformat(e["date"]) >= d]
    if not upcoming:
        return None
    e = min(upcoming, key=lambda x: x["date"])
    return {**e, "days_until": (date.fromisoformat(e["date"]) - d).days}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", type=int, nargs="+")
    a = ap.parse_args()
    if a.refresh:
        print(refresh(*a.refresh))
