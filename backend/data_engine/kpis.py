"""KPI registry and deterministic engine (pure Python). The LLM never computes a KPI.

Every fact has numerator, denominator, definition version, quality flag, baseline and delta.

Definitions (v1)
- Baseline window: the 4 full Sunday..Saturday weeks that end on or before the day before the period starts.
  Sum/count facts: baseline = mean of the 4 weekly values. Ratio facts: baseline = pooled (sum / sum) over the 28 days.
  The email-cohort fact: baseline = the same measure as of the end of the baseline window.
- Point in time: a snapshot only sees events at or before its `as_of` time. A period is observed at 06:00 on the
  morning after it ends (or at `as_of` if that is earlier). A lead not yet answered at that moment has response
  latency `observation time - created_at`, so an old unanswered lead does not distort later weeks.
  Stages/wins that happen after `as_of` are invisible.
- CAC = ad spend / new customers (first orders). Conversion rate = new customers / sessions (per channel).
- ROAS = attributed revenue / ad spend. Contribution ROAS uses a flat 50% contribution margin (estimated
  shipping, so quality is `partial`). Gross margin = (revenue - product cost - packaging) / revenue.
- Repeat rate = repeat orders / orders. Email cohort = customers on the email list whose first order was in
  Aug 2026: share with at least one repeat order by the period end.
- High value lead = expected value >= INR 15,000. p90 latency uses linear interpolation. Unattended = high-value
  lead created in the period with no response by the period end.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from functools import lru_cache
from typing import Optional

from .synth import config as C
from .synth.generate import Tenant, build_tenant

DEFINITION_VERSION = "v1"
CONTRIBUTION_MARGIN = 0.5
QUALITY = {"contribution_roas": "partial"}      # estimated shipping costs


def _dt(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


def _d(s: str) -> date:
    return date.fromisoformat(s[:10])


def percentile(values: list, q: float) -> float:
    v = sorted(values)
    if not v:
        return 0.0
    i = q * (len(v) - 1)
    lo = int(math.floor(i))
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (i - lo) * (v[hi] - v[lo])


def baseline_window(period_from: date) -> tuple[date, date]:
    """4 full Sun..Sat weeks ending on or before the day before `period_from`."""
    end = period_from - timedelta(days=1)
    while end.weekday() != 5:       # Saturday
        end -= timedelta(days=1)
    return end - timedelta(days=27), end


class Indexed:
    """A tenant with the lookups the KPI functions need (built once per phase)."""

    def __init__(self, t: Tenant):
        self.t = t
        self.as_of = _dt(t.meta["as_of"])
        self.orders = [(_d(o["ordered_at"]), o) for o in t.orders]
        self.daily = {}
        for r in t.daily:
            self.daily[(r["channel"], r["date"])] = r
        self.leads = [(_d(l["created_at"]), _dt(l["created_at"]), l) for l in t.leads]
        self.first_order = {o["customer_id"]: _d(o["ordered_at"]) for o in t.orders if o["is_first_order"]}
        self.cohort = [c["customer_id"] for c in t.customers if c.get("email_cohort")]
        repeats = {}
        for o in t.orders:
            if not o["is_first_order"]:
                repeats.setdefault(o["customer_id"], []).append(_d(o["ordered_at"]))
        self.repeats = repeats
        self.last_day = max(_d(r["date"]) for r in t.daily)
        self.first_day = min(_d(r["date"]) for r in t.daily)

    # ---------------------------------------------------------- orders and ad channels
    def orders_in(self, a: date, b: date) -> list:
        return [o for d, o in self.orders if a <= d <= b]

    def channel_sum(self, channel: str, field: str, a: date, b: date) -> float:
        total, d = 0, a
        while d <= b:
            r = self.daily.get((channel, d.isoformat()))
            if r:
                total += r[field]
            d += timedelta(days=1)
        return total

    # ---------------------------------------------------------- leads (point in time)
    def seen(self, ts: Optional[str]) -> Optional[datetime]:
        """A timestamp, only if it had already happened at the snapshot's as_of."""
        if not ts:
            return None
        v = _dt(ts)
        return v if v <= self.as_of else None

    def stage(self, lead: dict) -> str:
        st = lead["stage"]
        if st in ("qualified", "won") and lead["first_response_at"] and not self.seen(lead["first_response_at"]):
            return "new"                                  # the follow-up has not happened yet at as_of
        if st == "won" and lead["won_at"] and not self.seen(lead["won_at"]):
            return "qualified"
        return st

    def leads_in(self, a: date, b: date, high_value: Optional[bool] = None) -> list:
        return [(c, l) for d, c, l in self.leads if a <= d <= b and (high_value is None or l["high_value"] == high_value)]

    def observed_at(self, b: date) -> datetime:
        """When a period ending on `b` is measured: 06:00 the next morning, or as_of if earlier."""
        nxt = datetime(b.year, b.month, b.day, 6) + timedelta(days=1)
        return min(nxt, self.as_of)

    def latency_hours(self, created: datetime, lead: dict, obs: datetime) -> float:
        resp = self.seen(lead["first_response_at"])
        if resp is not None and resp > obs:
            resp = None                                     # answered only after the period was measured
        return ((resp or obs) - created).total_seconds() / 3600

    def unattended(self, a: date, b: date) -> int:
        end = min(datetime(b.year, b.month, b.day, 23, 59, 59), self.as_of)
        n = 0
        for created, l in self.leads_in(a, b, True):
            resp = self.seen(l["first_response_at"])
            if resp is None or resp > end:
                n += 1
        return n

    def wins(self, a: date, b: date) -> int:
        n = 0
        for l in self.t.leads:
            if l["high_value"] and l["won_at"]:
                w = self.seen(l["won_at"])
                if w and a <= w.date() <= b:
                    n += 1
        return n

    # ---------------------------------------------------------- email cohort
    def cohort_repeat(self, as_of_day: date) -> tuple:
        n = sum(1 for cid in self.cohort if any(d <= as_of_day for d in self.repeats.get(cid, [])))
        return n, len(self.cohort)


@lru_cache(maxsize=2)
def indexed(phase: str) -> Indexed:
    return Indexed(build_tenant(phase))


# ---------------------------------------------------------------- the registry
def _ratio(n, d):
    return (n / d) if d else None


def _paid(channel):
    def spend(ix, a, b):
        return ix.channel_sum(channel, "spend", a, b), None, None

    def cac(ix, a, b):
        s, c = ix.channel_sum(channel, "spend", a, b), ix.channel_sum(channel, "new_customers", a, b)
        return _ratio(s, c), s, c

    def conv(ix, a, b):
        c, s = ix.channel_sum(channel, "new_customers", a, b), ix.channel_sum(channel, "sessions", a, b)
        return _ratio(c, s), c, s

    def roas(ix, a, b):
        r, s = ix.channel_sum(channel, "revenue", a, b), ix.channel_sum(channel, "spend", a, b)
        return _ratio(r, s), r, s

    def croas(ix, a, b):
        r, s = ix.channel_sum(channel, "revenue", a, b), ix.channel_sum(channel, "spend", a, b)
        n = round(r * CONTRIBUTION_MARGIN, 2)
        return _ratio(n, s), n, s

    return spend, cac, conv, roas, croas


def _all(ix, a, b):
    return ix.orders_in(a, b)


def _cac_blended(ix, a, b):
    spend = sum(ix.channel_sum(c, "spend", a, b) for c in ("instagram", "google"))
    new = sum(1 for o in ix.orders_in(a, b) if o["is_first_order"])
    return _ratio(spend, new), spend, new


def _revenue(ix, a, b):
    return sum(o["revenue"] for o in ix.orders_in(a, b)), None, None


def _orders(ix, a, b):
    return len(ix.orders_in(a, b)), None, None


def _aov(ix, a, b):
    o = ix.orders_in(a, b)
    rev = sum(x["revenue"] for x in o)
    return _ratio(rev, len(o)), rev, len(o)


def _gm(ix, a, b):
    o = ix.orders_in(a, b)
    rev = sum(x["revenue"] for x in o)
    gp = round(sum(x["revenue"] - x["cogs"] for x in o), 2)
    return _ratio(gp, rev), gp, rev


def _repeat(ix, a, b):
    o = ix.orders_in(a, b)
    rep = sum(1 for x in o if not x["is_first_order"])
    return _ratio(rep, len(o)), rep, len(o)


def _leads(ix, a, b):
    return len(ix.leads_in(a, b)), None, None


def _latency(ix, a, b):
    obs = ix.observed_at(b)
    vals = [ix.latency_hours(c, l, obs) for c, l in ix.leads_in(a, b, True)]
    return (percentile(vals, 0.9) if vals else None), None, None


def _unattended(ix, a, b):
    return ix.unattended(a, b), None, None


def _wins(ix, a, b):
    return ix.wins(a, b), None, None


def _sessions(ix, a, b):
    return sum(ix.channel_sum(c, "sessions", a, b) for c in ("instagram", "google", "other")), None, None


def _qualified(ix, a, b):
    ls = ix.leads_in(a, b)
    q = sum(1 for _c, l in ls if ix.stage(l) in ("qualified", "won"))
    return q, q, len(ls)


def _won(ix, a, b):
    ls = ix.leads_in(a, b)
    q = sum(1 for _c, l in ls if ix.stage(l) in ("qualified", "won"))
    w = sum(1 for _c, l in ls if ix.stage(l) == "won")
    return w, w, q


# fact_id, kpi, dimension, unit, baseline kind ('ratio' pooled | 'weekly' mean of 4 weeks), function
def _registry():
    ig = _paid("instagram")
    g = _paid("google")
    r = []
    r += [("f_spend_instagram", "ad_spend", {"channel": "instagram"}, "INR", "weekly", ig[0]),
          ("f_cac_instagram", "cac", {"channel": "instagram"}, "INR", "ratio", ig[1]),
          ("f_conv_instagram", "conversion_rate", {"channel": "instagram"}, "ratio", "ratio", ig[2]),
          ("f_roas_instagram", "roas", {"channel": "instagram"}, "ratio", "ratio", ig[3]),
          ("f_croas_instagram", "contribution_roas", {"channel": "instagram"}, "ratio", "ratio", ig[4]),
          ("f_spend_google", "ad_spend", {"channel": "google"}, "INR", "weekly", g[0]),
          ("f_cac_google", "cac", {"channel": "google"}, "INR", "ratio", g[1]),
          ("f_croas_google", "contribution_roas", {"channel": "google"}, "ratio", "ratio", g[4]),
          ("f_cac_blended", "cac", {}, "INR", "ratio", _cac_blended),
          ("f_revenue_total", "revenue", {}, "INR", "weekly", _revenue),
          ("f_orders_total", "orders", {}, "count", "weekly", _orders),
          ("f_aov", "aov", {}, "INR", "ratio", _aov),
          ("f_gross_margin", "gross_margin", {}, "ratio", "ratio", _gm),
          ("f_repeat_rate", "repeat_rate", {}, "ratio", "ratio", _repeat),
          ("f_repeat_email", "repeat_rate", {"channel": "email", "cohort": "first_order_2026-08"}, "ratio", "cohort", None),
          ("f_leads_total", "leads", {}, "count", "weekly", _leads),
          ("f_latency_hot_leads", "response_latency_p90", {"segment": "high_value"}, "hours", "weekly", _latency),
          ("f_unattended_hot_leads", "unattended_leads", {"segment": "high_value"}, "count", "weekly", _unattended),
          ("f_hot_lead_wins", "lead_wins", {"segment": "high_value"}, "count", "weekly", _wins),
          ("f_funnel_sessions", "funnel_sessions", {}, "count", "weekly", _sessions),
          ("f_funnel_leads", "funnel_leads", {}, "count", "weekly", _leads),
          ("f_funnel_qualified", "funnel_qualified", {}, "count", "weekly", _qualified),
          ("f_funnel_won", "funnel_won", {}, "count", "weekly", _won)]
    return r


REGISTRY = _registry()
KPI_DEFINITIONS = {fid: {"kpi": kpi, "dimension": dim, "unit": unit, "baseline": kind} for fid, kpi, dim, unit, kind, _f in REGISTRY}


def _round(value, unit, kpi):
    if value is None:
        return None
    if unit == "count":
        return int(round(value))
    if unit == "ratio":
        return round(value, 3)
    return round(value, 1)


def _num(v):
    if v is None:
        return None
    return int(v) if float(v).is_integer() and isinstance(v, int) else round(float(v), 2)


def period_for(snapshot: str) -> tuple[date, date, str]:
    if snapshot == "day7":
        return C.DAY7_START, C.DAY7_END, "day7"
    return C.CURRENT_START, C.CURRENT_END, "baseline"


def compute_facts(snapshot: str = "baseline", period_from: Optional[str] = None, period_to: Optional[str] = None) -> list:
    """All KPI facts for a snapshot ('baseline' = current week, 'day7' = follow-up week) or a custom period."""
    if snapshot not in ("baseline", "day7"):
        raise ValueError("snapshot must be 'baseline' or 'day7'")
    a, b, phase = period_for(snapshot)
    if period_from or period_to:
        a = date.fromisoformat(period_from) if period_from else a
        b = date.fromisoformat(period_to) if period_to else b
    if a > b:
        raise ValueError("'from' must not be after 'to'")
    ix = indexed("day7" if (snapshot == "day7" or b > C.CURRENT_END) else "baseline")
    if a < ix.first_day or b > ix.last_day:
        raise ValueError(f"period must lie within {ix.first_day}..{ix.last_day}")
    ba, bb = baseline_window(a)
    weeks = [(ba + timedelta(days=7 * k), ba + timedelta(days=7 * k + 6)) for k in range(4)]
    facts = []
    for fid, kpi, dim, unit, kind, fn in REGISTRY:
        if kind == "cohort":
            num, den = ix.cohort_repeat(b)
            value = _ratio(num, den)
            bn, bd = ix.cohort_repeat(bb)
            base = _ratio(bn, bd)
        else:
            value, num, den = fn(ix, a, b)
            if kind == "ratio":
                base = fn(ix, ba, bb)[0]
            else:
                vals = [fn(ix, wa, wb)[0] for wa, wb in weeks]
                vals = [v for v in vals if v is not None]
                base = sum(vals) / len(vals) if vals else None
        v = _round(value, unit, kpi)
        bl = _round(base, unit, kpi) if unit != "count" else (round(base, 1) if base is not None else None)
        delta = round((v - bl) / bl * 100, 1) if (v is not None and bl) else None
        facts.append({
            "fact_id": fid, "kpi": kpi, "dimension": dim, "period": {"from": a.isoformat(), "to": b.isoformat()},
            "value": v if unit != "INR" or v is None else float(v), "unit": unit, "baseline": bl, "delta_pct": delta,
            "numerator": _num(num), "denominator": _num(den), "definition_version": DEFINITION_VERSION,
            "quality_flag": QUALITY.get(kpi, "ok"), "snapshot": snapshot})
    return facts


def daily_series(period_from: Optional[str] = None, period_to: Optional[str] = None, channel: Optional[str] = None) -> dict:
    """Daily per-channel series (instagram, google) for anomaly detection, plus the injected-incident ground truth."""
    a = date.fromisoformat(period_from) if period_from else date(2026, 8, 9)
    b = date.fromisoformat(period_to) if period_to else C.CURRENT_END
    phase = "day7" if b > C.CURRENT_END else "baseline"
    ix = indexed(phase)
    rows = [r for (ch, ds), r in sorted(ix.daily.items(), key=lambda kv: (kv[0][1], kv[0][0]))
            if ch in ("instagram", "google") and a.isoformat() <= ds <= b.isoformat() and (channel is None or ch == channel)]
    series = [{k: r[k] for k in ("date", "channel", "spend", "sessions", "new_customers", "revenue", "cac")} for r in rows]
    return {"business_id": C.BUSINESS_ID, "synthetic": True, "definition_version": DEFINITION_VERSION,
            "period": {"from": a.isoformat(), "to": b.isoformat()}, "series": series,
            "injected_incidents": [{
                "incident_id": "inc_instagram_cac_spike", "kpi": "cac", "dimension": {"channel": "instagram"},
                "from": "2026-09-29", "to": "2026-10-03",
                "description": "Injected Instagram CAC spike (synthetic ground truth for anomaly precision/recall and detection delay). "
                               "Google has no incident and serves as the false-alert control."}]}
