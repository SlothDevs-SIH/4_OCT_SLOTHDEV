"""Deterministic generator for the synthetic D2C tenant (pure Python, no pandas/numpy).

`build_tenant("baseline")` returns data up to 2026-10-03 (the current week).
`build_tenant("day7")` returns the same data plus the follow-up week 2026-10-05..2026-10-11 and the
actions taken in between (the replay used for the expected-vs-actual outcome screen).

The baseline part is identical in both phases, so the same seed always gives the same data.
All rows carry `synthetic: True`. This is a scripted scenario with planted incidents, not a claim
about real businesses.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from functools import lru_cache

from . import config as C

CITIES = ["Pune", "Mumbai", "Bengaluru", "Delhi", "Hyderabad", "Chennai", "Ahmedabad", "Kolkata", "Jaipur", "Nagpur"]
CITY_W = [14, 18, 16, 16, 9, 8, 6, 5, 4, 4]
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
HV_LABELS = [
    "Bulk order for salon", "Corporate gifting", "Spa retail shelf", "Boutique reorder", "Wedding hampers",
    "Gym franchise kits", "Hotel amenity kits", "Stockist inquiry", "Influencer bundle", "Clinic reseller",
]
LEAD_CHANNELS = ["whatsapp", "instagram_dm", "email", "website_form"]
LEAD_CHANNEL_W = [0.38, 0.30, 0.12, 0.20]
OWNERS = ["owner_founder", "owner_ops"]

HOT_ATTRS = {
    "lead_0412": ("success", 3, 2, 1), "lead_0388": ("nonexistent", 0, 999, 1), "lead_0397": ("success", 4, 3, 2),
    "lead_0421": ("failure", 2, 12, 2), "lead_0403": ("nonexistent", 0, 999, 2), "lead_0430": ("success", 2, 5, 1),
    "lead_0415": ("failure", 1, 20, 3), "lead_0426": ("nonexistent", 0, 999, 3),
}


@dataclass
class Tenant:
    phase: str
    campaigns: list = field(default_factory=list)
    customers: list = field(default_factory=list)
    orders: list = field(default_factory=list)
    leads: list = field(default_factory=list)
    daily: list = field(default_factory=list)   # per day and channel: spend, sessions, new_customers, revenue
    meta: dict = field(default_factory=dict)


# ----------------------------------------------------------------------------- helpers
def apportion(total: int, weights: list) -> list:
    """Split an integer total proportionally to weights (largest remainder), preserving the sum."""
    s = float(sum(weights))
    if total == 0 or s <= 0:
        return [0] * len(weights)
    raw = [total * w / s for w in weights]
    out = [int(x) for x in raw]
    order = sorted(range(len(weights)), key=lambda i: (-(raw[i] - out[i]), i))
    for i in order[: total - sum(out)]:
        out[i] += 1
    return out


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _noise(rng: random.Random, amp: float = 0.10) -> list:
    return [C.DAY_WEIGHTS[i] * (1 + rng.uniform(-amp, amp)) for i in range(7)]


def _timestamp(rng: random.Random, d: date) -> datetime:
    hour = rng.choices(range(7, 24), weights=[2, 3, 4, 4, 4, 4, 5, 5, 5, 5, 6, 7, 8, 8, 6, 4, 2])[0]
    return datetime(d.year, d.month, d.day, hour, rng.randrange(60), rng.randrange(60))


def _make_baskets(rng: random.Random, n: int, total: int) -> list:
    """n orders whose net amounts sum EXACTLY to `total` (INR), built from real SKUs with small discounts."""
    prices = [s["price"] for s in C.SKUS]
    baskets = [[0, 0, 0] for _ in range(n)]
    for b in baskets:
        b[rng.choices(range(3), weights=C.SKU_WEIGHTS)[0]] = 1

    def lt(b):
        return sum(q * p for q, p in zip(b, prices))

    lists = [lt(b) for b in baskets]
    cur = sum(lists)
    target = total / 0.96

    def score(c):
        return abs(c - target) + (10000 + (total - c) if c < total else 0)

    best = score(cur)
    for _ in range(min(3000, 800 + 30 * n)):
        i = rng.randrange(n)
        b = baskets[i][:]
        move = rng.random()
        if move < 0.4:
            b[rng.randrange(3)] += 1
        elif move < 0.7:
            j = rng.randrange(3)
            if sum(b) > 1 and b[j] > 0:
                b[j] -= 1
            else:
                continue
        else:
            b = [0, 0, 0]
            for _k in range(rng.choice([1, 1, 2, 3])):
                b[rng.choices(range(3), weights=C.SKU_WEIGHTS)[0]] += 1
        new_cur = cur - lists[i] + lt(b)
        sc = score(new_cur)
        if sc < best:
            baskets[i], lists[i], cur, best = b, lt(b), new_cur, sc
    while cur < total:  # safety net: list value >= total so discounts are never negative
        i = rng.randrange(n)
        baskets[i][0] += 1
        lists[i] += prices[0]
        cur += prices[0]
    r = total / cur
    nets = [round(l * r) for l in lists]
    diff, k = total - sum(nets), 0
    while diff != 0:  # spread the rounding residual one rupee at a time, never above the list price
        i = (len(nets) - 1 - k) % len(nets)
        step = 1 if diff > 0 else -1
        if step < 0 or nets[i] < lists[i]:
            nets[i] += step
            diff -= step
        k += 1
    out = []
    for b, l, net in zip(baskets, lists, nets):
        items = [{"sku": C.SKUS[j]["sku"], "qty": q, "unit_price": C.SKUS[j]["price"], "unit_cost": C.SKUS[j]["unit_cost"]}
                 for j, q in enumerate(b) if q]
        cogs = sum(it["qty"] * it["unit_cost"] for it in items) + C.PACKAGING_COST_INR
        out.append({"items": items, "list_total": l, "revenue": net, "discount": l - net, "cogs": cogs})
    return out


# ----------------------------------------------------------------------------- weekly + daily plan
def _split_week(w: dict, prng: random.Random) -> None:
    """Fill w['day'] with per-day arrays for every series (planned up front so counts are known exactly)."""
    def paid(ch):
        p = w[ch]
        if "daily" in p:
            d = p["daily"]
            cust = list(d["customers"])
            return list(d["spend"]), list(d["sessions"]), cust, apportion(p["revenue"], cust)
        spend = apportion(p["spend"], _noise(prng))
        # customers follow spend (steady daily CAC), so only planted incidents stand out in the series
        cust = apportion(p["customers"], [x * (1 + prng.uniform(-0.07, 0.07)) for x in spend])
        return spend, apportion(p["sessions"], _noise(prng)), cust, apportion(p["revenue"], cust)

    ig, g = paid("instagram"), paid("google")
    o = w["others"]
    o_new = apportion(o["new"], _noise(prng, 0.3))
    o_rep = apportion(o["repeat"], _noise(prng, 0.2))
    w["day"] = {
        "instagram": dict(zip(("spend", "sessions", "customers", "revenue"), ig)),
        "google": dict(zip(("spend", "sessions", "customers", "revenue"), g)),
        "others": {"new": o_new, "repeat": o_rep, "revenue": apportion(o["revenue"], [a + b for a, b in zip(o_new, o_rep)]),
                   "sessions": apportion(o["sessions"], _noise(prng))},
        "cohort": apportion(w["cohort_repeats"], _noise(prng, 0.3)) if w["cohort_repeats"] else [0] * 7,
    }


def _weeks_plan() -> list:
    """21 weekly plans: weeks 0..15 earlier history, 16..19 the baseline, 20 the current week."""
    prng = random.Random(C.SEED + 7)
    weeks = []
    for i in range(21):
        start = C.HISTORY_START + timedelta(days=7 * i)
        w = {"i": i, "start": start}
        if i <= 15:
            t = i / 15
            ig_spend = round(27000 + 5500 * t + prng.uniform(-600, 600))
            ig_cust = round(ig_spend / (415 + prng.uniform(-15, 15)))
            g_spend = round(14000 + 2100 * t + prng.uniform(-300, 300))
            g_cust = round(g_spend / (372 + prng.uniform(-10, 10)))
            o_new = prng.choice([4, 5, 6])
            o_rep = round(10 + 18 * t + prng.uniform(-2, 2))
            leads = round(115 + 33 * t + prng.uniform(-3, 3))
            w["instagram"] = {"spend": ig_spend, "customers": ig_cust, "sessions": round(ig_cust / (0.0225 + prng.uniform(-0.001, 0.001))),
                              "revenue": round(ig_cust * (848 + prng.uniform(-15, 15)))}
            w["google"] = {"spend": g_spend, "customers": g_cust, "sessions": round(g_cust / (0.0206 + prng.uniform(-0.001, 0.001))),
                           "revenue": round(g_cust * (865 + prng.uniform(-15, 15)))}
            w["others"] = {"new": o_new, "repeat": o_rep, "revenue": round((o_new + o_rep) * (930 + prng.uniform(-30, 30))),
                           "sessions": round(3000 + 700 * t + prng.uniform(-40, 40))}
            w["leads"] = {"leads": leads, "qualified": round(0.42 * leads), "won": round(0.17 * leads),
                          "hv_total": prng.choice([8, 9, 10]), "hv_unattended": 1, "hv_won": 2}
            w["cohort_repeats"] = {"2026-08-16": 3, "2026-08-23": 4}.get(start.isoformat(), 0)
        elif i <= 19:
            k = i - 16
            w["instagram"] = {n: C.IG_BASELINE[n][k] for n in ("spend", "sessions", "customers", "revenue")}
            w["google"] = {n: C.GOOGLE_BASELINE[n][k] for n in ("spend", "sessions", "customers", "revenue")}
            w["others"] = {n: C.OTHERS_BASELINE[n][k] for n in ("new", "repeat", "revenue", "sessions")}
            w["leads"] = {n: C.LEADS_BASELINE[n][k] for n in ("leads", "qualified", "won", "hv_total", "hv_unattended", "hv_won")}
            w["cohort_repeats"] = [6, 7, 7, 7][k]
        else:
            ig = C.CURRENT["instagram"]
            n_ig = sum(ig["customers"])
            w["instagram"] = {"spend": sum(ig["spend"]), "customers": n_ig, "sessions": sum(ig["sessions"]),
                              "revenue": n_ig * ig["revenue_per_customer"], "daily": ig}
            w["google"], w["others"], w["leads"] = dict(C.CURRENT["google"]), dict(C.CURRENT["others"]), dict(C.CURRENT["leads"])
            w["cohort_repeats"] = C.EMAIL_COHORT_REPEATS_CURRENT - C.EMAIL_COHORT_REPEATS_BASELINE
        _split_week(w, prng)
        weeks.append(w)
    return weeks


def _day7_plan() -> dict:
    prng = random.Random(C.SEED + 8)
    ig = C.DAY7["instagram"]
    n_ig = sum(ig["customers"])
    w = {"i": 21, "start": C.DAY7_START,
         "instagram": {"spend": sum(ig["spend"]), "customers": n_ig, "sessions": sum(ig["sessions"]),
                       "revenue": n_ig * ig["revenue_per_customer"], "daily": ig},
         "google": dict(C.DAY7["google"]), "others": dict(C.DAY7["others"]), "leads": dict(C.DAY7["leads"]),
         "cohort_repeats": C.EMAIL_COHORT_REPEATS_DAY7 - C.EMAIL_COHORT_REPEATS_CURRENT}
    _split_week(w, prng)
    return w


# ----------------------------------------------------------------------------- builder
class _Builder:
    def __init__(self, phase: str):
        self.phase = phase
        self.rng = random.Random(C.SEED)
        self.t = Tenant(phase=phase)
        self.cust_n = 0
        self.eligible: list = []     # non-cohort customers who may repeat
        self.cohort_pool: list = []  # cohort members who have not repeated yet
        self.pending: list = []      # (ready_date, customer): 10-day delay before a first repeat
        self.campaign_ids: dict = {}
        self.cohort_chosen: set = set()
        self.cohort_counter = 0

    def campaigns(self):
        n = 0
        for ch, names in C.CAMPAIGNS.items():
            for name in names:
                n += 1
                cid = f"cmp_{n:02d}"
                self.campaign_ids.setdefault(ch, []).append(cid)
                self.t.campaigns.append({
                    "campaign_id": cid, "business_id": C.BUSINESS_ID, "channel": ch, "name": name,
                    "objective": "acquisition" if ch in ("instagram", "google") else "retention",
                    "start_date": C.HISTORY_START.isoformat(), "end_date": None, "synthetic": True})

    def legacy_customers(self, n: int = 400):
        """Customers acquired before the history window (no order rows): the pool early repeat orders draw from."""
        rng = random.Random(C.SEED + 3)
        for k in range(n):
            self.cust_n += 1
            cust = {"customer_id": f"cust_{self.cust_n:05d}", "business_id": C.BUSINESS_ID,
                    "first_order_at": _iso(datetime(2026, 4, 1) + timedelta(days=rng.randrange(38))),
                    "acquisition_channel": rng.choice(["instagram", "google", "email", "referral"]),
                    "city": rng.choices(CITIES, weights=CITY_W)[0], "email_consent": rng.random() < 0.3,
                    "whatsapp_consent": rng.random() < 0.5, "repeat_orders": 0, "email_cohort": False,
                    "legacy": True, "synthetic": True}
            self.t.customers.append(cust)
            self.eligible.append(cust)

    def _campaign_for(self, channel: str):
        ids = self.campaign_ids.get(channel)
        return self.rng.choice(ids) if ids else None  # website = direct (unattributed)

    def _cohort_flag(self, d: date) -> bool:
        if (d.year, d.month) != C.EMAIL_COHORT_MONTH:
            return False
        i = self.cohort_counter
        self.cohort_counter += 1
        return i in self.cohort_chosen

    def _new_customer(self, d: date, channel: str) -> dict:
        self.cust_n += 1
        rng = self.rng
        in_cohort = self._cohort_flag(d)
        cust = {"customer_id": f"cust_{self.cust_n:05d}", "business_id": C.BUSINESS_ID,
                "first_order_at": None, "acquisition_channel": channel,
                "city": rng.choices(CITIES, weights=CITY_W)[0],
                "email_consent": in_cohort or ((d.year, d.month) != C.EMAIL_COHORT_MONTH and rng.random() < 0.30),
                "whatsapp_consent": rng.random() < 0.5, "repeat_orders": 0, "email_cohort": in_cohort, "synthetic": True}
        self.t.customers.append(cust)
        self.pending.append((d + timedelta(days=10), cust))
        return cust

    def _release(self, d: date):
        keep = []
        for ready, cust in self.pending:
            if ready <= d:
                (self.cohort_pool if cust["email_cohort"] else self.eligible).append(cust)
            else:
                keep.append((ready, cust))
        self.pending = keep

    def _orders(self, d: date, group: list, total: int):
        if not group:
            return
        for g, b in zip(group, _make_baskets(self.rng, len(group), total)):
            ts = _timestamp(self.rng, d)
            cod = self.rng.random() < C.COD_SHARE
            rto = self.rng.random() < (C.RTO_RATE_COD if cod else C.RTO_RATE_PREPAID)
            if g["first"]:
                g["customer"]["first_order_at"] = _iso(ts)
            self.t.orders.append({
                "order_id": None, "business_id": C.BUSINESS_ID, "customer_id": g["customer"]["customer_id"],
                "ordered_at": _iso(ts), "channel": g["channel"], "campaign_id": self._campaign_for(g["channel"]),
                "is_first_order": g["first"], "payment_mode": "cod" if cod else "prepaid",
                "status": "rto" if rto else "delivered", "revenue": b["revenue"], "discount": b["discount"],
                "list_total": b["list_total"], "cogs": b["cogs"], "items": b["items"], "synthetic": True})

    def week(self, w: dict):
        rng, day = self.rng, w["day"]
        for k in range(7):
            d = w["start"] + timedelta(days=k)
            self._release(d)
            for ch in ("instagram", "google"):
                s = day[ch]
                group = [{"customer": self._new_customer(d, ch), "channel": ch, "first": True} for _ in range(s["customers"][k])]
                self._orders(d, group, s["revenue"][k])
                self.t.daily.append({"date": d.isoformat(), "channel": ch, "spend": s["spend"][k], "sessions": s["sessions"][k],
                                     "new_customers": s["customers"][k], "revenue": s["revenue"][k],
                                     "cac": round(s["spend"][k] / s["customers"][k], 2) if s["customers"][k] else None,
                                     "synthetic": True})
            o = day["others"]
            group = []
            for _ in range(o["new"][k]):
                ch = rng.choices(*C.OTHER_FIRST_CHANNELS)[0]
                group.append({"customer": self._new_customer(d, ch), "channel": ch, "first": True})
            n_coh = min(day["cohort"][k], len(self.cohort_pool))
            for _ in range(n_coh):
                cust = self.cohort_pool.pop(rng.randrange(len(self.cohort_pool)))
                cust["repeat_orders"] += 1
                group.append({"customer": cust, "channel": "email", "first": False})
            for _ in range(max(0, o["repeat"][k] - n_coh)):
                cust = rng.choice(self.eligible)
                for _try in range(30):
                    if cust["repeat_orders"] < 3:
                        break
                    cust = rng.choice(self.eligible)
                cust["repeat_orders"] += 1
                group.append({"customer": cust, "channel": rng.choices(*C.OTHER_REPEAT_CHANNELS)[0], "first": False})
            rng.shuffle(group)
            self._orders(d, group, o["revenue"][k])
            self.t.daily.append({"date": d.isoformat(), "channel": "other", "spend": 0, "sessions": o["sessions"][k],
                                 "new_customers": o["new"][k], "revenue": o["revenue"][k], "cac": None, "synthetic": True})


def _attrs(rng: random.Random, created: datetime, scripted: tuple | None = None) -> dict:
    if scripted:
        po, prior, days, contacts = scripted
    else:
        po = rng.choices(["success", "failure", "nonexistent"], weights=[0.06, 0.12, 0.82])[0]
        prior = 0 if po == "nonexistent" else rng.randint(1, 5)
        days = 999 if po == "nonexistent" else rng.randint(1, 30)
        contacts = rng.randint(1, 4)
    return {"previous_outcome": po, "prior_contacts": prior, "days_since_last_contact": days,
            "contacts_this_campaign": contacts, "inquiry_month": MONTHS[created.month - 1],
            "inquiry_weekday": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][created.weekday()]}


class _LeadMaker:
    def __init__(self, rng: random.Random):
        self.rng = rng
        self.n = 1000
        self.leads: list = []

    def lead(self, *, lead_id=None, label=None, channel=None, created: datetime, response_hours=None, stage="new",
             ev=None, hv=False, attrs=None, won_at=None, owner=None):
        rng = self.rng
        if lead_id is None:
            self.n += 1
            lead_id = f"lead_{self.n}"
        responded = None if response_hours is None else created + timedelta(hours=response_hours)
        rec = {"lead_id": lead_id, "business_id": C.BUSINESS_ID, "label": label, "channel": channel,
               "created_at": _iso(created), "first_response_at": _iso(responded) if responded else None,
               "stage": stage, "won_at": _iso(won_at) if won_at else None, "expected_value_inr": ev,
               "high_value": hv, "owner": owner or (rng.choice(OWNERS) if responded else None),
               "attributes": attrs or _attrs(rng, created), "synthetic": True}
        self.leads.append(rec)
        return rec


def _week_leads(lm: _LeadMaker, w: dict, kind: str):
    """kind: 'history' | 'current' | 'day7'."""
    rng, spec, start = lm.rng, w["leads"], w["start"]
    end_ts = datetime(start.year, start.month, start.day, 23, 59, 59) + timedelta(days=6)
    cap = min(end_ts, C.AS_OF if kind != "day7" else C.AS_OF_DAY7)

    def rand_created(max_day=6):
        return _timestamp(rng, start + timedelta(days=rng.randrange(max_day + 1)))

    def won_time(created):
        return max(created + timedelta(hours=1), min(created + timedelta(hours=rng.uniform(3, 60)), cap))

    hv_q = hv_w = 0   # HV leads that are qualified-not-won / won
    n_special = 0
    if kind == "current":
        for lid, label, ch, ev, age in C.HOT_LEADS:
            lm.lead(lead_id=lid, label=label, channel=ch, created=C.AS_OF - timedelta(hours=age), stage="new", ev=ev, hv=True,
                    attrs=_attrs(rng, C.AS_OF - timedelta(hours=age), HOT_ATTRS[lid]))
        for k, (lid, label, ch, ev, resp, won) in enumerate(C.ATTENDED_HV):
            created = datetime(2026, 9, 28 + k % 2, 9 + k, 30)
            stage = "won" if won else ("qualified" if k < 3 else "new")
            lm.lead(lead_id=lid, label=label, channel=ch, created=created, response_hours=resp, stage=stage, ev=ev, hv=True,
                    won_at=created + timedelta(hours=30) if won else None)
            hv_w += 1 if won else 0
            hv_q += 1 if stage == "qualified" else 0
        lid, label, ch, ev, resp = C.LEAD_FAMILY_PACK
        lm.lead(lead_id=lid, label=label, channel=ch, created=datetime(2026, 10, 3, 9, 15), response_hours=resp, stage="qualified", ev=ev)
        lid, label, ch, ev, age = C.LEAD_INCOMPLETE
        lm.lead(lead_id=lid, label=label, channel=ch, created=C.AS_OF - timedelta(hours=age), stage="new", ev=ev,
                attrs={"previous_outcome": None, "prior_contacts": None, "days_since_last_contact": None,
                       "contacts_this_campaign": None, "inquiry_month": "oct", "inquiry_weekday": "fri"})
        n_special = len(C.HOT_LEADS) + len(C.ATTENDED_HV) + 2
        non_hv_special_q = 1  # the family-pack lead is qualified but not high value
    elif kind == "day7":
        att = [0.8, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 5.5]
        for k, resp in enumerate(att):
            created = rand_created(5)
            stage = "qualified" if k < 3 else "new"
            lm.lead(label=rng.choice(HV_LABELS), channel=rng.choices(LEAD_CHANNELS, LEAD_CHANNEL_W)[0], created=created,
                    response_hours=resp, stage=stage, ev=rng.randrange(15000, 52000, 500), hv=True)
            hv_q += 1 if stage == "qualified" else 0
        lm.lead(label=rng.choice(HV_LABELS), channel="whatsapp", created=C.AS_OF_DAY7 - timedelta(hours=5.5), stage="new",
                ev=rng.randrange(15000, 52000, 500), hv=True)  # the one unattended at the end of the week
        n_special = spec["hv_total"]
        non_hv_special_q = 0
    else:
        n_att = spec["hv_total"] - spec["hv_unattended"]
        for k in range(spec["hv_total"]):
            created = rand_created(3 if k < spec["hv_won"] else 6)
            if k < spec["hv_unattended"]:
                lm.lead(label=rng.choice(HV_LABELS), channel=rng.choices(LEAD_CHANNELS, LEAD_CHANNEL_W)[0],
                        created=rand_created(), stage="new", ev=rng.randrange(15000, 52000, 500), hv=True)
                continue
            j = k - spec["hv_unattended"]
            stage = "won" if j < spec["hv_won"] else ("qualified" if j < spec["hv_won"] + 3 else "new")
            lm.lead(label=rng.choice(HV_LABELS), channel=rng.choices(LEAD_CHANNELS, LEAD_CHANNEL_W)[0], created=created,
                    response_hours=round(rng.uniform(0.8, 6.0), 1), stage=stage, ev=rng.randrange(15000, 52000, 500), hv=True,
                    won_at=won_time(created) if stage == "won" else None)
            hv_w += 1 if stage == "won" else 0
            hv_q += 1 if stage == "qualified" else 0
        n_special = spec["hv_total"]
        non_hv_special_q = 0

    generic = spec["leads"] - n_special
    won_left = spec["won"] - hv_w
    qual_left = spec["qualified"] - spec["won"] - hv_q - non_hv_special_q
    stages = (["won"] * won_left + ["qualified"] * qual_left)
    rest = generic - len(stages)
    stages += [rng.choices(["new", "lost"], weights=[0.7, 0.3])[0] for _ in range(rest)]
    rng.shuffle(stages)
    for stage in stages:
        created = rand_created()
        responded = None if rng.random() < 0.03 else round(min(rng.expovariate(1 / 6) + 0.3, 30), 1)
        lm.lead(label="Consumer inquiry", channel=rng.choices(LEAD_CHANNELS, LEAD_CHANNEL_W)[0], created=created,
                response_hours=responded, stage=stage, ev=int(min(max(rng.lognormvariate(7.6, 0.6), 400), 12000)),
                won_at=won_time(created) if stage == "won" else None)


def _day7_actions(leads: list):
    """Between the two snapshots the team follows up the hot leads; three of them are won in the follow-up week."""
    by_id = {l["lead_id"]: l for l in leads}
    for k, (lid, *_rest) in enumerate(C.HOT_LEADS):
        lead = by_id[lid]
        lead["first_response_at"] = _iso(datetime(2026, 10, 4, 6, 0) + timedelta(minutes=25 * k))
        lead["owner"] = OWNERS[k % 2]
        lead["stage"] = "qualified"
    for lid, day in C.DAY7_BACKLOG_WINS.items():
        by_id[lid]["stage"] = "won"
        by_id[lid]["won_at"] = f"{day}T11:00:00Z"


def _build(phase: str) -> Tenant:
    b = _Builder(phase)
    b.campaigns()
    b.legacy_customers()
    weeks = _weeks_plan()
    if phase == "day7":
        weeks.append(_day7_plan())
    aug_first = sum(
        w["day"]["instagram"]["customers"][k] + w["day"]["google"]["customers"][k] + w["day"]["others"]["new"][k]
        for w in weeks for k in range(7) if ((w["start"] + timedelta(days=k)).year, (w["start"] + timedelta(days=k)).month) == C.EMAIL_COHORT_MONTH)
    b.cohort_chosen = set(random.Random(C.SEED + 11).sample(range(aug_first), C.EMAIL_COHORT_SIZE))
    for w in weeks:
        b.week(w)

    t = b.t
    t.orders.sort(key=lambda o: o["ordered_at"])
    for i, o in enumerate(t.orders):
        o["order_id"] = f"ORD-{10001 + i}"

    lm = _LeadMaker(random.Random(C.SEED + 5))
    for w in weeks:
        _week_leads(lm, w, "history" if w["i"] < 20 else "current" if w["i"] == 20 else "day7")
    if phase == "day7":
        _day7_actions(lm.leads)
    t.leads = sorted(lm.leads, key=lambda l: l["created_at"])
    t.daily.sort(key=lambda r: (r["date"], r["channel"]))
    t.meta = {"business_id": C.BUSINESS_ID, "synthetic": True, "seed": C.SEED, "phase": phase,
              "from": C.HISTORY_START.isoformat(), "to": (C.DAY7_END if phase == "day7" else C.CURRENT_END).isoformat(),
              "as_of": _iso(C.AS_OF_DAY7 if phase == "day7" else C.AS_OF),
              "counts": {"campaigns": len(t.campaigns), "customers": len(t.customers), "orders": len(t.orders), "leads": len(t.leads)}}
    return t


@lru_cache(maxsize=None)
def build_tenant(phase: str = "baseline") -> Tenant:
    if phase not in ("baseline", "day7"):
        raise ValueError("phase must be 'baseline' or 'day7'")
    return _build(phase)
