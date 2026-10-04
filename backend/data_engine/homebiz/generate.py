"""Deterministic generator for the demo businesses (Box Box and a home baker). Pure Python.

Same seed, same data. Everything is `synthetic: True`. What is calibrated on public data and what is a scenario assumption is
listed in `config.data_card(key)`. Weeks 2 to 4 of the advisory period are a scripted replay of what could happen after the
advice (more strangers, more reach), never a prediction.
"""
from __future__ import annotations

import math
import random
from collections import defaultdict
from datetime import date, timedelta
from functools import lru_cache

from ..external import f1_calendar, india_festivals
from . import config as C
from . import leads as L
from .model import BusinessData

SEEDS = {"boxbox": 20261004, "homebaker": 20261005}
WEEKDAY_FACTOR = (0.94, 0.94, 0.94, 0.94, 0.94, 1.15, 1.15)      # weekends 15% busier; averages to 1.0
PERIODS = ["history"] + [f"week_{k}" for k in range(1, C.ADVISORY_WEEKS + 1)]


def poisson(rng: random.Random, lam: float) -> int:
    if lam <= 0:
        return 0
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= limit:
            return k - 1


def period_of(day: date) -> str:
    return "history" if day < C.ADVISORY_START else f"week_{(day - C.ADVISORY_START).days // 7 + 1}"


def context_days(feed: str) -> set:
    """Days inside the market-context windows (race weekends, or the week before each festival)."""
    start, end = C.HISTORY_START.isoformat(), (C.END - timedelta(days=1)).isoformat()
    out = set()
    if feed == "f1_calendar":
        wins = [(w["weekend_start"], w["weekend_end"]) for w in f1_calendar.race_weekends(2026, start, end)]
    else:
        wins = [(w["window_start"], w["window_end"]) for w in india_festivals.demand_events(start, end)]
    for a, b in wins:
        day, e = date.fromisoformat(a), date.fromisoformat(b)
        while day <= e:
            out.add(day)
            day += timedelta(days=1)
    return out


def _choose(rng: random.Random, items: list, weights: list):
    return rng.choices(items, weights=weights)[0]


def _posts(rng: random.Random, s: dict) -> list:
    posts, n = [], 0
    for w in range(C.HISTORY_WEEKS + C.ADVISORY_WEEKS):
        start = C.HISTORY_START + timedelta(weeks=w)
        period = period_of(start)
        days = sorted(rng.sample(range(7), s["posts_per_week"]))
        for off in days:
            n += 1
            reach = max(40, int(rng.lognormvariate(math.log(s["reach_median"] * s["reach_multiplier"][period]), s["reach_sigma"])))
            visits = max(0, int(reach * s["profile_visit_rate"] * rng.uniform(0.7, 1.3)))
            follows = max(0, int(visits * s["follow_rate"] * rng.uniform(0.6, 1.4)))
            posts.append({"post_id": f"post_{n:03d}", "date": (start + timedelta(days=off)).isoformat(), "reach": reach,
                          "profile_visits": visits, "follows": follows, "saves": int(reach * 0.02 * rng.uniform(0.5, 1.5)),
                          "shares": int(reach * 0.006 * rng.uniform(0.5, 1.5)), "topic": rng.choice(s["products"])["name"],
                          "led_to_orders": 0, "synthetic": True})
    return posts


def _message(rng: random.Random, sig: str, product: str, size, city) -> str | None:
    if sig == "price_question":
        opts = [f"is the {product} available" + (f" in {size}?" if size else "?"), f"how much for the {product}?" + (f" deliver to {city}?" if city else ""),
                f"do you have the {product}" + (f" in size {size}" if size else "")]
        return rng.choice(opts)
    if sig == "story_reply":
        return rng.choice(["this one is fire 🔥", "need this!!", "so good 😍"])
    if sig == "comment":
        return rng.choice(["love this design", "want this!", "stunning"])
    if sig == "follow_or_like":
        return "love your page"
    return None


def build_raw(key: str) -> BusinessData:
    s = C.SCENARIOS[key]
    rng = random.Random(SEEDS[key])
    ctx = context_days(s["context_feed"])
    products = s["products"]
    names = [p["name"] for p in products]
    cap = s["capacity_orders_per_week"]
    posts = _posts(rng, s)
    posts_by_day = defaultdict(list)
    for p in posts:
        posts_by_day[p["date"]].append(p)

    customers, scheduled = [], defaultdict(list)
    orders, turned, weekly = [], [], defaultdict(int)
    p_rep = min(0.95, s["repeat_customer_target"] / 0.62)
    days = [C.HISTORY_START + timedelta(days=i) for i in range((C.END - C.HISTORY_START).days)]

    def make_order(day: date, cust: dict, first: bool):
        wk = (day - C.HISTORY_START).days // 7
        if weekly[wk] >= cap:
            turned.append({"date": day.isoformat(), "reason": "over capacity", "synthetic": True})
            return
        weekly[wk] += 1
        n_items = _choose(rng, [1, 2, 3], [0.80, 0.15, 0.05])
        items = []
        for _ in range(n_items):
            p = products[names.index(_choose(rng, names, s["product_weights"]))]
            items.append({"name": p["name"], "category": p["category"], "qty": 1, "price": p["price"],
                          "unit_cost": p["material"] + p["making"] + p["packaging"] + p["courier"]})
        merged = {}
        for it in items:
            if it["name"] in merged:
                merged[it["name"]]["qty"] += 1
            else:
                merged[it["name"]] = dict(it)
        items = list(merged.values())
        gross = sum(i["qty"] * i["price"] for i in items)
        discount = round(0.10 * gross) if rng.random() < 0.05 else 0
        rel = cust["relationship"]
        channel = _choose(rng, ["instagram_dm", "whatsapp"], [0.75, 0.25] if rel == "stranger" else [0.5, 0.5])
        post_id = None
        recent = [p for k in range(0, 8) for p in posts_by_day.get((day - timedelta(days=k)).isoformat(), [])]
        if recent and rng.random() < {"stranger": s["post_to_order_share"], "friend_of_friend": 0.12}.get(rel, 0.0):
            chosen = rng.choice(recent)
            chosen["led_to_orders"] += 1
            post_id = chosen["post_id"]
        util = weekly[wk] / cap
        delay = math.exp(math.log(2.0) + C.DISPATCH_SIGMA * rng.gauss(0, 1)) * (1 + 1.5 * max(0.0, util - 0.85))
        disp = day + timedelta(days=int(round(delay)))
        orders.append({"order_id": f"ORD-{len(orders) + 1:04d}", "date": day.isoformat(), "buyer_ref": cust["ref"], "items": items,
                       "gross": gross, "discount": discount, "total": gross - discount,
                       "payment": "upi" if rng.random() < 0.85 else "cod", "channel": channel, "relationship": rel, "post_id": post_id,
                       "dispatched_at": disp.isoformat() if disp < C.END else None, "status": "delivered" if disp < C.END else "open",
                       "is_first_order": first, "synthetic": True})
        if first and rng.random() < p_rep:
            target = day + timedelta(days=max(7, int(math.exp(C.GAP_MU + C.GAP_SIGMA * rng.gauss(0, 1)))))
            if target < C.END:
                scheduled[target].append(cust)
        cust["n"] += 1

    for day in days:
        period = period_of(day)
        lam = (s["base_orders_per_week"] / 7) * WEEKDAY_FACTOR[day.weekday()] * s["week_order_multiplier"][period] * (s["context_order_factor"] if day in ctx else 1.0)
        for cust in scheduled.pop(day, []):
            make_order(day, cust, first=False)
        shares = s["shares"][period]
        for _ in range(poisson(rng, lam)):
            rel = _choose(rng, ["friend", "friend_of_friend", "stranger"], shares)
            cust = {"ref": f"buyer_{len(customers) + 1:04d}", "relationship": rel, "n": 0,
                    "city": _choose(rng, s["serves"]["cities"], [0.6] + [0.4 / max(1, len(s["serves"]["cities"]) - 1)] * (len(s["serves"]["cities"]) - 1))}
            customers.append(cust)
            make_order(day, cust, first=True)

    # ------------------------------------------------------------------ leads
    leads, lead_n = [], 0
    serves = s["serves"]
    for day in days:
        period = period_of(day)
        lam = (s["leads_per_week"] / 7) * WEEKDAY_FACTOR[day.weekday()] * (s["reach_multiplier"][period] ** 0.5)
        for _ in range(poisson(rng, lam)):
            lead_n += 1
            rel = _choose(rng, ["friend", "friend_of_friend", "stranger"], s["shares"][period])
            k = _choose(rng, [1, 2, 3, 4], [0.40, 0.35, 0.20, 0.05])
            pool = ["price_question", "story_reply", "saved_or_shared", "comment", "follow_or_like", "bought_before"]
            w = [0.26, 0.20, 0.25, 0.30, 0.30, 0.35 if rel != "stranger" else 0.0]
            types = []
            while len(types) < k and any(w):
                t = _choose(rng, pool, w)
                if t not in types:
                    types.append(t)
                w[pool.index(t)] = 0.0
                if not any(w):
                    break
            product = rng.choice(names)
            size = rng.choice(serves["sizes"]) if serves["sizes"] and rng.random() < 0.92 else ("XXL" if serves["sizes"] else None)
            city = (rng.choice(serves["cities"]) if rng.random() < 0.90 else "Jaipur") if "price_question" in types else None
            asked = {"product": product, "size": size, "design": None, "city": city} if "price_question" in types else {"product": None, "size": None, "design": None, "city": None}
            if "price_question" in types and rng.random() < 0.05:
                asked = {**asked, "product": None, "product_text": "a design we do not make"}
            signals, texts, intents = [], [], set()
            for t in types:
                sd = min(C.END - timedelta(days=1), day + timedelta(days=rng.randint(0, 6)))
                signals.append({"type": t, "date": sd.isoformat()})
                msg = _message(rng, t, product, size, city)
                if msg:
                    texts.append({"channel": "dm" if t == "price_question" else "story" if t == "story_reply" else "comment", "date": sd.isoformat(), "text": msg})
                intents.add({"price_question": "buying_question", "story_reply": "product_interest", "comment": "product_interest",
                             "saved_or_shared": "product_interest", "follow_or_like": "general_praise"}.get(t, "product_interest"))
            signals.sort(key=lambda x: x["date"])
            lead = {"lead_id": f"lead_{lead_n:04d}", "handle_ref": f"@user_{lead_n:04d}",
                    "source": _choose(rng, ["dm", "comment", "story", "whatsapp"], [0.5, 0.25, 0.15, 0.10]), "relationship": rel,
                    "created": day.isoformat(), "signals": signals, "asked_for": asked, "intents": sorted(intents) or ["general_praise"],
                    "texts": texts, "outcome": "open", "outcome_date": None, "synthetic": True}
            last = date.fromisoformat(signals[-1]["date"])
            eval_day = last + timedelta(days=1)
            sc = L.score_lead(lead, eval_day, serves, products)
            od = last + timedelta(days=rng.randint(2, 9))
            if sc["group"] == "disqualified":
                lead["outcome"], lead["outcome_date"] = ("not_ordered", od.isoformat()) if od < C.END else ("open", None)
            elif od < C.END:
                p = {"hot": 0.45, "warm": 0.15, "cold": 0.03}[sc["group"]]
                lead["outcome"], lead["outcome_date"] = ("ordered" if rng.random() < p else "not_ordered"), od.isoformat()
            leads.append(lead)

    stock = []
    if key == "boxbox":
        stock = [{"date": (C.HISTORY_START + timedelta(weeks=5, days=2)).isoformat(), "product": "McLaren Papaya Hoodie", "size": "L", "synthetic": True},
                 {"date": (C.HISTORY_START + timedelta(weeks=8, days=1)).isoformat(), "product": "Ferrari F1 Tee", "size": "M", "synthetic": True}]

    costs = {p["name"]: {"material": p["material"], "making": p["making"], "packaging": p["packaging"], "courier": p["courier"],
                         "full": p["material"] + p["making"] + p["packaging"] + p["courier"], "source": "estimate"} for p in products}
    f = {k: {"value": v, "source": src} for k, v, src in [
        ("weekly_hours", s["weekly_hours"], "estimate"), ("capacity_orders_per_week", cap, "estimate"), ("ad_budget_inr", 0, "exact"),
        ("team_size", s["team_size"], "exact"), ("goal", s["interview"]["goal"], "exact"), ("tried_before", s["interview"]["tried"], "exact")]}
    profile = {
        "business_id": s["business_id"], "name": s["name"], "case_study": s["case_study"], "synthetic": True, "kind": s["kind"],
        "products": [{"name": p["name"], "category": p["category"], "price": p["price"],
                      "unit_cost": costs[p["name"]]["full"]} for p in products],
        "channels": s["channels"], "team_size": s["team_size"], "weekly_hours": s["weekly_hours"], "ad_budget_inr": 0,
        "capacity_orders_per_week": cap, "goal": {"statement": s["interview"]["goal"], "horizon_days": 30},
        "constraints": {"forbidden_actions": ["paid_ads"], "approval_required_for": ["customer_outreach"], "notes": s["interview"]["constraints"]},
        "context_feeds": [s["context_feed"]], "serves": serves, "history_weeks": C.HISTORY_WEEKS, "fields": f,
    }
    return BusinessData(key=key, profile=profile, orders=orders, costs=costs, posts=posts, leads=leads, turned_away=turned, stockouts=stock,
                        meta={"seed": SEEDS[key], "history_start": C.HISTORY_START.isoformat(), "advisory_start": C.ADVISORY_START.isoformat(),
                              "end": C.END.isoformat(), "customers": len(customers), "story": s["story"], "data_card": C.data_card(key),
                              "max_week": C.ADVISORY_WEEKS, "context_effect": s["context_order_factor"] - 1})


@lru_cache(maxsize=4)
def build(key: str) -> BusinessData:
    if key not in C.SCENARIOS:
        raise KeyError(f"unknown demo business {key!r}; choose one of {sorted(C.SCENARIOS)}")
    return build_raw(key)


def sample_chat(data: BusinessData, as_of: date, n: int = 14) -> str:
    """Pasted-chat text for the intake demo: recent enquiries in a WhatsApp-like format, one per line."""
    rows = []
    for lead in data.leads:
        for t in lead.get("texts", []):
            if date.fromisoformat(t["date"]) < as_of and date.fromisoformat(t["date"]) >= as_of - timedelta(days=10):
                rows.append((t["date"], lead["handle_ref"], t["channel"], t["text"]))
    rows.sort()
    return "\n".join(f"{h} ({ch}): {tx}" for _d, h, ch, tx in rows[-n:])
