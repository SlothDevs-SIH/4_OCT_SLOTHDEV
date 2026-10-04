"""The data held for one home business, and weekly point-in-time snapshots.

A snapshot `week_k` is taken at the start of advisory week k (as_of = ADVISORY_START + 7*(k-1) days) and sees only events
dated BEFORE that day. Snapshot week_1 is the owner's first diagnosis (history only); week_2 sees what happened in the
first advisory week, and so on. So week 1 never sees week 2.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

from . import config as C


@dataclass
class BusinessData:
    key: str                       # 'boxbox' | 'homebaker' | a created business id
    profile: dict                  # contract 2.1 plus provenance
    orders: list = field(default_factory=list)
    costs: dict = field(default_factory=dict)      # product -> {material, making, packaging, courier, source}
    posts: list = field(default_factory=list)
    leads: list = field(default_factory=list)
    turned_away: list = field(default_factory=list)
    stockouts: list = field(default_factory=list)
    meta: dict = field(default_factory=dict)


def history_start(data: Optional["BusinessData"] = None) -> date:
    return d(data.meta["history_start"]) if data is not None and data.meta.get("history_start") else C.HISTORY_START


def advisory_start(data: Optional["BusinessData"] = None) -> date:
    return d(data.meta["advisory_start"]) if data is not None and data.meta.get("advisory_start") else C.ADVISORY_START


def max_week(data: Optional["BusinessData"] = None) -> int:
    return int(data.meta.get("max_week", C.ADVISORY_WEEKS)) if data is not None else C.ADVISORY_WEEKS


def as_of_for(week: int, data: Optional["BusinessData"] = None) -> date:
    if not 1 <= week <= max_week(data):
        raise ValueError(f"week must be between 1 and {max_week(data)}")
    return advisory_start(data) + timedelta(weeks=week - 1)


def week_label(week: int) -> str:
    return f"week_{week}"


def d(s: str) -> date:
    return date.fromisoformat(s[:10])


def visible(items: list, as_of: date, key: str = "date") -> list:
    """Events dated before the snapshot day."""
    return [x for x in items if d(x[key]) < as_of]


def week_start_of(day: date, origin: date = C.HISTORY_START) -> date:
    return origin + timedelta(weeks=(day - origin).days // 7)


def window_weeks(as_of: date, n: int = 4, origin: date = C.HISTORY_START) -> list:
    """The n complete Monday-to-Sunday weeks that end the day before `as_of`: [(start, end_inclusive), ...] oldest first."""
    out = []
    end = as_of - timedelta(days=1)
    for k in range(n):
        e = end - timedelta(weeks=n - 1 - k)
        out.append((e - timedelta(days=6), e))
    return [w for w in out if w[0] >= origin]
