"""F1 race calendar as market context (public data: Jolpica-F1, the open successor of the Ergast API).

Why it matters: race weekends are the demand windows for F1 merchandise, so the advisor can time actions
(a design drop, a post, a collaboration) around them. The calendar is factual public data; a snapshot is
committed so the product works offline. Refresh with:

    python -m backend.data_engine.external.f1_calendar --refresh 2026

Source: https://api.jolpi.ca/ergast/f1/<season>.json (open, no key, rate-limited; one request per season).
"""
from __future__ import annotations

import json
import urllib.request
from bisect import bisect_left
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Optional

SNAPSHOTS = Path(__file__).resolve().parent / "snapshots"
URL = "https://api.jolpi.ca/ergast/f1/{season}.json?limit=40"
UA = {"User-Agent": "slothdev-hackathon/1.0 (student project; github.com/SlothDevs-SIH/4_OCT_SLOTHDEV)"}
SESSION_KEYS = ["FirstPractice", "SprintQualifying", "SecondPractice", "Sprint", "ThirdPractice", "Qualifying"]


def _simplify(race: dict) -> dict:
    sessions = {k: race[k]["date"] for k in SESSION_KEYS if k in race}
    race_day = date.fromisoformat(race["date"])
    start = min([date.fromisoformat(d) for d in sessions.values()] + [race_day])
    return {"season": int(race["season"]), "round": int(race["round"]), "name": race["raceName"],
            "circuit": race["Circuit"]["circuitName"], "country": race["Circuit"]["Location"]["country"],
            "locality": race["Circuit"]["Location"]["locality"], "race_date": race["date"],
            "weekend_start": start.isoformat(), "weekend_end": race["date"], "sessions": sessions,
            "sprint_weekend": "Sprint" in race or "SprintQualifying" in race}


def fetch_season(season: int) -> list:
    req = urllib.request.Request(URL.format(season=season), headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        data = json.load(r)
    return [_simplify(x) for x in data["MRData"]["RaceTable"]["Races"]]


def refresh(season: int) -> Path:
    races = fetch_season(season)
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOTS / f"f1_calendar_{season}.json"
    path.write_text(json.dumps({"season": season, "source": "Jolpica-F1 (Ergast API successor), https://api.jolpi.ca",
                                "races": races}, indent=1), encoding="utf-8")
    return path


@lru_cache(maxsize=8)
def calendar(season: int) -> list:
    """Races of a season from the committed snapshot (offline). Raises FileNotFoundError if there is none."""
    return json.loads((SNAPSHOTS / f"f1_calendar_{season}.json").read_text(encoding="utf-8"))["races"]


def available_seasons() -> list:
    return sorted(int(p.stem.split("_")[-1]) for p in SNAPSHOTS.glob("f1_calendar_*.json"))


def race_weekends(season: int, start: Optional[str] = None, end: Optional[str] = None) -> list:
    """Race weekends overlapping [start, end] (ISO dates)."""
    a = date.fromisoformat(start) if start else date.min
    b = date.fromisoformat(end) if end else date.max
    return [r for r in calendar(season) if date.fromisoformat(r["weekend_start"]) <= b and date.fromisoformat(r["weekend_end"]) >= a]


def weekend_on(day: str) -> Optional[dict]:
    """The race weekend a date falls in, or None."""
    d = date.fromisoformat(day)
    for r in calendar(d.year):
        if date.fromisoformat(r["weekend_start"]) <= d <= date.fromisoformat(r["weekend_end"]):
            return r
    return None


def next_race(day: str) -> Optional[dict]:
    """The first race whose race day is on or after `day`, with days until it."""
    d = date.fromisoformat(day)
    for season in (d.year, d.year + 1):
        try:
            races = calendar(season)
        except FileNotFoundError:
            continue
        dates = [date.fromisoformat(r["race_date"]) for r in races]
        i = bisect_left(dates, d)
        if i < len(races):
            return {**races[i], "days_until_race": (dates[i] - d).days}
    return None


def demand_windows(season: int, lead_days: int = 7, tail_days: int = 2) -> list:
    """For each race: the build-up window (the lead_days before the weekend), the weekend itself and a short tail.
    A drop or post planned for the build-up window reaches fans while attention is rising."""
    out = []
    for r in calendar(season):
        s, e = date.fromisoformat(r["weekend_start"]), date.fromisoformat(r["weekend_end"])
        out.append({"round": r["round"], "race": r["name"], "build_up": [(s - timedelta(days=lead_days)).isoformat(), (s - timedelta(days=1)).isoformat()],
                    "weekend": [s.isoformat(), e.isoformat()], "tail": [(e + timedelta(days=1)).isoformat(), (e + timedelta(days=tail_days)).isoformat()]})
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", type=int, nargs="+", help="season(s) to download, e.g. 2025 2026")
    for s in ap.parse_args().refresh or []:
        print(refresh(s))
