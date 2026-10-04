"""Lead qualification (design: the team document Lead_Qualification_Model.docx).

A lead is any person who showed interest on a channel the owner uses: a DM, a comment, a save or share, a story reply, or
a past order. Six steps: collect, read (intent labels), score (points), group, act (backend 2), learn (weekly).

The points and thresholds are STARTING GUESSES, as the design says. The weekly step replaces guesses with the owner's own
outcomes. Reading intent is pluggable: the prototype ships deterministic rules (also the fallback when an LLM is not
available); a provider can be registered to label with a language model, and its output is validated the same way.
"""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Callable, Optional

POINTS = {"price_question": 40, "bought_before": 30, "story_reply": 20, "saved_or_shared": 15, "comment": 10,
          "follow_or_like": 5}
STRANGER_BONUS = 10
DECAY_DAYS, DECAY_POINTS = 30, -20
HOT, WARM = 50, 20
SIGNAL_TYPES = tuple(POINTS)
INTENTS = ("buying_question", "product_interest", "general_praise", "custom_request", "not_a_lead")
RELATIONSHIPS = ("friend", "friend_of_friend", "stranger", "unknown")
MIN_OUTCOMES_FOR_SUGGESTION = 30
SNAP = Path(__file__).resolve().parents[1] / "external" / "snapshots"

SIGNAL_LABELS = {"price_question": "Asked about price, size, stock or delivery", "bought_before": "Bought before",
                 "story_reply": "Replied to a product story", "saved_or_shared": "Saved or shared a post",
                 "comment": "Commented on a post", "follow_or_like": "Followed or liked", "stranger": "Is a stranger (growth bonus)",
                 "decay": "No activity in the last 30 days"}


def _d(s: str) -> date:
    return date.fromisoformat(s[:10])


# ------------------------------------------------------------------ step 2: read the intent
_NOT_A_LEAD = re.compile(r"\b(collab(oration)?|promote|promotion|sponsor(ed)?|supplier|wholesale offer|follow back|boost your|"
                         r"buy followers|ads? agency|paid partnership|dm for)\b", re.I)
_BUYING = re.compile(r"\b(price|cost|how much|rate|rates|available|availability|in stock|stock|size|sizes|deliver(y|ed)?|ship(ping)?|"
                     r"cod|can i (get|order|buy)|do you have|i want to (order|buy)|want to order|order)\b", re.I)
_CUSTOM = re.compile(r"\b(custom(ised|ized)?|personali[sz]ed|my name|name on|with my|design for me|make one)\b", re.I)
_INTEREST = re.compile(r"(\bfire\b|\bwant (this|it)\b|\bneed (this|it)\b|\bso good\b|\bstunning\b|\bobsessed\b|this one|🔥|😍|\blove (this|the)\b)", re.I)
_PRAISE = re.compile(r"\b(love your page|great page|nice page|awesome page|amazing page|beautiful page|love your work|good work|nice work)\b", re.I)

_provider: Optional[Callable[[str], Optional[dict]]] = None


def register_provider(fn: Optional[Callable[[str], Optional[dict]]]) -> None:
    """Plug in an LLM labeller: fn(text) -> {"intents": [...]} or None. Output is validated; on any problem the rules are used."""
    global _provider
    _provider = fn


def label_intent(text: str) -> dict:
    """Intent labels for one message. {'intents': [...], 'method': 'llm'|'rules'}."""
    if _provider is not None:
        try:
            out = _provider(text)
            if out and out.get("intents") and all(i in INTENTS for i in out["intents"]):
                return {"intents": list(out["intents"]), "method": "llm"}
        except Exception:   # noqa: BLE001: any provider failure falls back to rules
            pass
    t = text or ""
    if _NOT_A_LEAD.search(t):
        return {"intents": ["not_a_lead"], "method": "rules"}
    found = []
    if _BUYING.search(t):
        found.append("buying_question")
    if _CUSTOM.search(t):
        found.append("custom_request")
    if _INTEREST.search(t):
        found.append("product_interest")
    if _PRAISE.search(t) and not found:
        found.append("general_praise")
    return {"intents": found or ["general_praise"], "method": "rules"}


_SIZE = re.compile(r"\b(?:size\s*)?(xxl|xl|xs|s|m|l)\b(?=[\s?.,!]|$)", re.I)
_SIZE_STRICT = re.compile(r"(?:\bsize\s*(xxl|xl|xs|s|m|l)\b|\bin\s+(xxl|xl|xs|s|m|l)\b|\b(xxl|xl|xs)\b)", re.I)
INDIAN_CITIES = ["Pune", "Mumbai", "Delhi", "Bangalore", "Bengaluru", "Hyderabad", "Chennai", "Kolkata", "Ahmedabad", "Jaipur",
                 "Lucknow", "Nagpur", "Surat", "Kochi", "Indore", "Chandigarh", "Goa", "Bhopal", "Patna"]


def extract_details(text: str, products: list, serves: Optional[dict] = None) -> dict:
    """What they asked for: product, size, design (free text), delivery city. Only what the message actually says."""
    t = text or ""
    out = {"product": None, "size": None, "design": None, "city": None}
    m = _SIZE_STRICT.search(t)
    if m:
        out["size"] = next(g for g in m.groups() if g).upper()
    cities = set(INDIAN_CITIES) | set((serves or {}).get("cities", []))
    for c in sorted(cities, key=len, reverse=True):
        if re.search(rf"\b{re.escape(c)}\b", t, re.I):
            out["city"] = c
            break
    low = t.lower()
    best, best_hits = None, 0
    for p in products:
        words = [w for w in re.findall(r"[a-z0-9]+", p["name"].lower()) if len(w) > 2 and w not in ("tee", "box", "the", "for")]
        hits = sum(1 for w in words if w in low)
        if hits > best_hits:
            best, best_hits = p["name"], hits
    out["product"] = best
    m2 = re.search(r"(?:design|with)\s+([a-z0-9 ]{3,30}?)(?:\?|\.|,|$)", low)
    if m2 and "my name" in low:
        out["design"] = "custom name"
    return out


def signals_from_message(channel: str, intents: list) -> list:
    """Map an interaction (where it happened + what it meant) to the signals that earn points. Each signal counts once per lead."""
    if "not_a_lead" in intents:
        return []
    out = []
    if "buying_question" in intents:
        out.append("price_question")
    if "custom_request" in intents:
        out.append("comment")                      # interested; needs a fit check (see deliverable)
    if "product_interest" in intents:
        out.append("story_reply" if channel == "story" else "comment")
    if "general_praise" in intents and not out:
        out.append("follow_or_like")
    return out


# ------------------------------------------------------------------ step 3 and 4: score and group
def _fit(asked: dict, serves: dict, products: list, intents: list) -> tuple:
    """(deliverable, disqualified_reason). deliverable None means 'needs a check'."""
    city, size, product = asked.get("city"), asked.get("size"), asked.get("product")
    if city and serves.get("cities") and city not in serves["cities"]:
        return False, f"city: cannot deliver to {city}"
    if size and serves.get("sizes") and size not in serves["sizes"]:
        return False, f"size: {size} is not available"
    if asked.get("design") and "custom_request" in intents:
        return None, None
    if product is None and asked.get("product_text") and "custom_request" not in intents:
        return False, f"design: {asked['product_text']} is not something the owner makes"
    return True, None


def score_lead(lead: dict, as_of: date, serves: Optional[dict] = None, products: Optional[list] = None) -> dict:
    """Score a lead using only what happened before `as_of`. Each signal counts once."""
    serves, products = serves or {}, products or []
    seen = sorted([s for s in lead.get("signals", []) if _d(s["date"]) < as_of], key=lambda s: s["date"])
    types = []
    for s in seen:
        if s["type"] in POINTS and s["type"] not in types:
            types.append(s["type"])
    intents = lead.get("intents") or []
    if "not_a_lead" in intents and not types:
        return {"score": None, "group": "not_a_lead", "reasons": [], "disqualified_reason": None, "deliverable": None,
                "last_signal": None, "rank_key": None}
    reasons = [{"signal": t, "label": SIGNAL_LABELS[t], "points": POINTS[t]} for t in types]
    if lead.get("relationship") == "stranger":
        reasons.append({"signal": "stranger", "label": SIGNAL_LABELS["stranger"], "points": STRANGER_BONUS})
    last = _d(seen[-1]["date"]) if seen else None
    if last is not None and last <= as_of - timedelta(days=DECAY_DAYS):
        reasons.append({"signal": "decay", "label": SIGNAL_LABELS["decay"], "points": DECAY_POINTS})
    score = sum(r["points"] for r in reasons)
    deliverable, dq = _fit(lead.get("asked_for") or {}, serves, products, intents)
    group = "disqualified" if dq else "hot" if score >= HOT else "warm" if score >= WARM else "cold"
    # at equal score a stranger ranks above a friend; then the most recent enquiry first
    rank_key = (-score, 0 if lead.get("relationship") == "stranger" else 1, -(last.toordinal() if last else 0), lead["lead_id"])
    return {"score": score, "group": group, "reasons": reasons, "disqualified_reason": dq, "deliverable": deliverable,
            "last_signal": last.isoformat() if last else None, "rank_key": rank_key}


NEXT_ACTION = {"hot": "Reply today with the price and an order link (most recent enquiry first)",
               "warm": "Contact once when there is a reason: a new drop, a restock or a small first-order offer",
               "cold": "No one-to-one effort; they see your regular posts",
               "disqualified": "Reply politely once that it is not available yet; log it, do not chase",
               "not_a_lead": "Ignore: not a lead"}


def score_all(leads: list, as_of: date, serves: Optional[dict] = None, products: Optional[list] = None, group: Optional[str] = None) -> list:
    """Scored leads (the daily list): open leads, hot first. Closed leads (ordered or not ordered by `as_of`) are excluded."""
    rows = []
    for lead in leads:
        if lead.get("outcome") in ("ordered", "not_ordered") and lead.get("outcome_date") and _d(lead["outcome_date"]) < as_of:
            continue
        if not any(_d(s["date"]) < as_of for s in lead.get("signals", [])):
            continue
        sc = score_lead(lead, as_of, serves, products)
        if sc["group"] == "not_a_lead":
            continue
        rows.append({"lead_id": lead["lead_id"], "handle_ref": lead["handle_ref"], "source": lead["source"],
                     "relationship": lead["relationship"], "signals": [s for s in lead["signals"] if _d(s["date"]) < as_of],
                     "asked_for": lead.get("asked_for") or {}, "intents": lead.get("intents") or [], "score": sc["score"],
                     "group": sc["group"], "reasons": sc["reasons"], "deliverable": sc["deliverable"],
                     "disqualified_reason": sc["disqualified_reason"], "next_action": NEXT_ACTION[sc["group"]],
                     "outcome": "open", "last_signal": sc["last_signal"], "_k": sc["rank_key"], "synthetic": lead.get("synthetic", False)})
    rows.sort(key=lambda r: ({"hot": 0, "warm": 1, "cold": 2, "disqualified": 3}[r["group"]], r["_k"]))
    out = []
    rank = 0
    for r in rows:
        k = r.pop("_k")
        if r["group"] != "disqualified":
            rank += 1
            r["rank"] = rank
        else:
            r["rank"] = None
        out.append(r)
    return [r for r in out if group is None or r["group"] == group]


def unmet_demand(rows: list) -> dict:
    """Disqualified leads counted by reason: a size, design or city people keep asking for is itself advice."""
    c: dict = {}
    for r in rows:
        if r["group"] == "disqualified" and r["disqualified_reason"]:
            c[r["disqualified_reason"]] = c.get(r["disqualified_reason"], 0) + 1
    return dict(sorted(c.items(), key=lambda kv: -kv[1]))


# ------------------------------------------------------------------ step 6: learn from results (weekly)
def _bank_attrs(lead: dict, as_of: date) -> dict:
    """What the public contact-history model can see about a lead: did they buy before, and how recent was the last contact.
    A lead's own signals are NOT 'contacts the seller made' (the bank data's meaning), so they are not counted as contacts."""
    seen = sorted([s for s in lead.get("signals", []) if _d(s["date"]) < as_of], key=lambda s: s["date"])
    bought = [s for s in seen if s["type"] == "bought_before"]
    if not bought:
        return {"previous_outcome": "nonexistent", "prior_contacts": 0, "days_since_last_contact": 999, "contacts_this_campaign": 1}
    return {"previous_outcome": "success", "prior_contacts": 1, "days_since_last_contact": max(0, (as_of - _d(seen[-1]["date"])).days),
            "contacts_this_campaign": 1}


def _ranks(xs: list) -> list:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(a: list, b: list) -> Optional[float]:
    if len(a) < 3:
        return None
    ra, rb = _ranks(a), _ranks(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5
    return round(num / den, 3) if den else None


def public_data_support() -> list:
    """Which design directions the committed public-data profiles support (they check directions, not point values)."""
    out = []
    sp = SNAP / "shoppers_profile.json"
    if sp.exists():
        s = json.loads(sp.read_text(encoding="utf-8"))
        pv = s["by_page_value"]
        out.append({"direction": "intent outweighs light interest (price question +40 vs follow or like +5)",
                    "evidence": f"Online Shoppers: sessions with page value convert at {pv['page_value > 0']['conversion']:.1%} vs {pv['page_value = 0']['conversion']:.1%}",
                    "supported": pv["page_value > 0"]["conversion"] > 5 * pv["page_value = 0"]["conversion"]})
        v = s["by_visitor_type"]
        out.append({"direction": "new people behave differently from people the shop already knows (stranger bonus)",
                    "evidence": f"Online Shoppers: new visitors convert at {v['New_Visitor']['conversion']:.1%} vs {v['Returning_Visitor']['conversion']:.1%}",
                    "supported": v["New_Visitor"]["conversion"] != v["Returning_Visitor"]["conversion"],
                    "caveat": "the +10 stranger bonus is a growth choice, not a measured effect"})
    mc = Path(__file__).resolve().parents[1] / "ml" / "artifacts" / "lead_model.json"
    if mc.exists():
        out.append({"direction": "history raises the chance (bought before +30) and a long silence lowers it (decay -20)",
                    "evidence": "Bank Marketing model on contact history: a previous success scores highest and a longer gap lowers the score "
                                f"(hold-out PR-AUC {json.loads(mc.read_text(encoding='utf-8'))['model_card']['metrics']['pr_auc']} vs {json.loads(mc.read_text(encoding='utf-8'))['model_card']['metrics']['prevalence']} baseline)",
                    "supported": True, "caveat": "a different industry and 4 inputs; the size of 30 and 20 points is a guess"})
    return out


def learning_report(leads: list, as_of: date, serves: Optional[dict] = None, products: Optional[list] = None) -> dict:
    """Weekly check: do Hot, Warm and Cold leads order at different rates? Which signals predict orders?"""
    closed = [l for l in leads if l.get("outcome") in ("ordered", "not_ordered") and l.get("outcome_date") and _d(l["outcome_date"]) < as_of]
    rows = []
    for l in closed:
        evaluate_at = min(as_of, _d(l["outcome_date"]))          # score as it looked when the outcome happened
        sc = score_lead(l, evaluate_at, serves, products)
        if sc["group"] in ("not_a_lead", "disqualified") or sc["score"] is None:
            continue
        rows.append((l, sc, l["outcome"] == "ordered"))
    n = len(rows)
    overall = sum(o for _, _, o in rows) / n if n else None
    groups = {}
    for g in ("hot", "warm", "cold"):
        sub = [o for _, sc, o in rows if sc["group"] == g]
        groups[g] = {"leads": len(sub), "ordered": sum(sub), "conversion": round(sum(sub) / len(sub), 4) if sub else None}
    per_signal = {}
    for t in list(POINTS) + ["stranger"]:
        has = [o for l, sc, o in rows if any(r["signal"] == t for r in sc["reasons"])]
        no = [o for l, sc, o in rows if not any(r["signal"] == t for r in sc["reasons"])]
        c1 = sum(has) / len(has) if has else None
        c0 = sum(no) / len(no) if no else None
        entry = {"leads_with_signal": len(has), "conversion_with": round(c1, 4) if c1 is not None else None,
                 "conversion_without": round(c0, 4) if c0 is not None else None}
        if t != "stranger":
            entry["points_now"] = POINTS[t]
        else:
            entry["points_now"] = STRANGER_BONUS
        if len(has) >= MIN_OUTCOMES_FOR_SUGGESTION and c1 is not None and overall:
            lift = c1 / overall
            entry["lift_vs_overall"] = round(lift, 2)
            entry["suggestion"] = "raise" if lift > 1.3 else "lower" if lift < 0.7 else "keep"
        else:
            entry["suggestion"] = "not enough outcomes yet"
        per_signal[t] = entry
    hc, wc, cc = (groups[g]["conversion"] for g in ("hot", "warm", "cold"))
    checks = []
    if None not in (hc, wc, cc):
        checks.append({"check": "Hot converts more than Warm, and Warm more than Cold", "ok": hc > wc > cc})
        checks.append({"check": "Hot and Warm do not convert at about the same rate", "ok": abs(hc - wc) > 0.05})
    from ..ml.lead_model import LeadModel
    try:
        model = LeadModel.load()
        pts, prob = [], []
        for l, sc, _ in rows:
            at = min(as_of, _d(l["outcome_date"]))
            pts.append(sc["score"])
            prob.append(model.probability(_bank_attrs(l, at)))
        agree = {"leads": len(pts), "spearman_points_vs_bank_model": spearman(pts, prob),
                 "note": "Rank agreement between the points score and the model trained on public contact-history data. That model only sees whether the person bought before and how recent the last contact was, so it checks those two ideas (a challenger and sanity check, not the score)"}
    except Exception:   # noqa: BLE001: the challenger is optional
        agree = None
    return {"as_of": as_of.isoformat(), "leads_with_known_outcome": n, "overall_conversion": round(overall, 4) if overall is not None else None,
            "by_group": groups, "by_signal": per_signal, "healthy_model_checks": checks,
            "enough_data": n >= MIN_OUTCOMES_FOR_SUGGESTION,
            "message": ("Enough outcomes to read the groups." if n >= MIN_OUTCOMES_FOR_SUGGESTION else
                        f"Only {n} leads have a known outcome; wait for about {MIN_OUTCOMES_FOR_SUGGESTION} before changing any points."),
            "challenger_agreement": agree, "public_data_support": public_data_support(),
            "points_status": "Starting guesses. Change them only from the owner's own outcomes."}
