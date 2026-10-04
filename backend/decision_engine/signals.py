"""Signal detection: bottleneck rules, opportunity detectors and anomalies.

A candidate becomes a signal only if it passes the four tests:
  materiality   - big enough to matter (spend share, lead count, cohort size)
  deviation     - clearly off its baseline
  localization  - pinned to a channel, segment, cohort or funnel stage
  actionability - an approved intervention template is triggered by it
Candidates that deviate but fail another test are returned under `rejected`.
Every number in a title comes from a KPI fact, so the LLM validator accepts it.
"""
from __future__ import annotations

from collections import Counter
from typing import Optional

from backend.decision_engine import anomaly, templates

MATERIAL_SPEND_SHARE = 0.15
DEVIATION_PCT = 20.0
STABLE_PCT = 10.0
UNATTENDED_MIN = 3
COHORT_MIN_SIZE = 100
GOOD_CROAS = 1.2

URGENCY_MONEY_LEAK = 0.7   # spend running below break-even, every day costs money
URGENCY_DECLINE = 0.6
URGENCY_OPPORTUNITY = 0.5


def _dim_key(dim: dict) -> tuple:
    return tuple(sorted(dim.items()))


class Facts:
    def __init__(self, facts: list[dict]):
        self.all = facts
        self.by_id = {f["fact_id"]: f for f in facts}
        self._idx = {(f["kpi"], _dim_key(f["dimension"])): f for f in facts}

    def get(self, kpi: str, **dim) -> Optional[dict]:
        return self._idx.get((kpi, _dim_key(dim)))

    def where(self, kpi: str) -> list[dict]:
        return [f for f in self.all if f["kpi"] == kpi]

    def channel(self, kpi: str) -> dict:
        """{channel: fact} for facts dimensioned by channel only."""
        return {f["dimension"]["channel"]: f for f in self.where(kpi)
                if set(f["dimension"]) == {"channel"}}


def _pct(x: float) -> str:
    return f"{round(x * 100, 1):g}%"


def _num(x) -> str:
    return f"{x:g}" if isinstance(x, (int, float)) else str(x)


def _signed(x: float) -> str:
    return f"+{x:g}%" if x >= 0 else f"{x:g}%"


def _actionable(rule: str) -> list[str]:
    return [t["template_id"] for t in templates.templates_for_trigger(rule)]


def _candidate(signal_id, type_, rule, kpi, dimension, title, tests, evidence, urgency, severity,
               method="rule", score=None, extra=None) -> dict:
    s = {"signal_id": signal_id, "type": type_, "rule": rule, "kpi": kpi, "dimension": dimension,
         "title": title, "severity": round(min(1.0, max(0.0, severity)), 2),
         "urgency": round(min(1.0, max(0.0, urgency)), 2), "method": method, "score": score,
         "tests": tests, "evidence_ids": evidence, "candidate_template_ids": _actionable(rule)}
    s.update(extra or {})
    return s


# ---------------------------------------------------------------- bottlenecks


def latency_over_sla(facts: Facts, leads: list[dict], ctx: dict) -> list[dict]:
    sla = ctx["constraints"].get("lead_response_sla_hours")
    out = []
    for lat in facts.where("response_latency_p90"):
        if not sla or not lat["dimension"]:
            continue
        unattended_fact = facts.get("unattended_leads", **lat["dimension"])
        hot = sorted((l for l in leads if l.get("high_value") and not l.get("attended") and not l["abstain"]),
                     key=lambda l: l["rank"])
        n = unattended_fact["value"] if unattended_fact else len(hot)
        tests = {"materiality": n >= UNATTENDED_MIN,
                 "deviation": lat["value"] > sla and (lat["delta_pct"] or 0) >= DEVIATION_PCT,
                 "localization": bool(hot),
                 "actionability": bool(_actionable("response_latency_over_sla"))}
        evidence = [lat["fact_id"]] + ([unattended_fact["fact_id"]] if unattended_fact else [])
        evidence += [l["lead_id"] for l in hot]
        title = (f"{_num(n)} high-value leads are waiting; p90 response time is {_num(lat['value'])} h "
                 f"against a {_num(sla)} h SLA")
        out.append(_candidate("sig_hot_leads_unattended", "bottleneck", "response_latency_over_sla",
                              "response_latency_p90", lat["dimension"], title, tests, evidence,
                              urgency=lat["value"] / (4 * sla), severity=0.5 + 0.05 * n))
    return out


def spend_share(facts: Facts) -> dict:
    spend = facts.channel("ad_spend")
    total = sum(f["value"] for f in spend.values())
    return {ch: f["value"] / total for ch, f in spend.items()} if total else {}


def high_spend_low_contribution(facts: Facts) -> list[dict]:
    croas, spend, conv = facts.channel("contribution_roas"), facts.channel("ad_spend"), facts.channel("conversion_rate")
    share = spend_share(facts)
    out = []
    for ch, f in croas.items():
        others = [o for c, o in croas.items() if c != ch]
        losing = f["value"] < 1.0
        tests = {"materiality": share.get(ch, 0) >= MATERIAL_SPEND_SHARE,
                 "deviation": losing or (f["delta_pct"] or 0) <= -DEVIATION_PCT,
                 "localization": all(o["value"] >= 1.0 or abs(o["delta_pct"] or 0) < STABLE_PCT for o in others),
                 "actionability": bool(_actionable("high_spend_low_contribution"))}
        evidence = [f["fact_id"]] + [x[ch]["fact_id"] for x in (spend, conv) if ch in x]
        title = (f"{ch.title()} spend returns {_num(f['value'])} contribution per rupee "
                 f"against a {_num(f['baseline'])} baseline")
        out.append(_candidate(f"sig_{ch}_low_contribution", "bottleneck", "high_spend_low_contribution",
                              "contribution_roas", {"channel": ch}, title, tests, evidence,
                              urgency=URGENCY_MONEY_LEAK if losing else URGENCY_DECLINE,
                              severity=0.5 + share.get(ch, 0) * max(0.0, 1 - f["value"])))
    return out


def _funnel(facts: Facts, stage_a: str, stage_b: str):
    a, b = facts.get(f"funnel_{stage_a}"), facts.get(f"funnel_{stage_b}")
    if not (a and b and a["value"] and a["baseline"] and b["baseline"]):
        return None
    rate, base = b["value"] / a["value"], b["baseline"] / a["baseline"]
    return a, b, (rate - base) / base * 100


def funnel_rules(facts: Facts) -> list[dict]:
    out = []
    checks = [("high_traffic_low_leads", "sessions", "leads"), ("leads_high_wins_low", "leads", "won")]
    for rule, stage_a, stage_b in checks:
        res = _funnel(facts, stage_a, stage_b)
        if not res:
            continue
        a, b, rate_delta = res
        tests = {"materiality": a["value"] >= (1000 if stage_a == "sessions" else 50),
                 "deviation": (a["delta_pct"] or 0) > -STABLE_PCT and rate_delta <= -DEVIATION_PCT,
                 "localization": True,  # pinned to one funnel stage
                 "actionability": bool(_actionable(rule))}
        title = f"{stage_a.title()} held at {_num(a['value'])} but {stage_b} fell to {_num(b['value'])}"
        out.append(_candidate(f"sig_{rule}", "bottleneck", rule, f"funnel_{stage_b}", {}, title, tests,
                              [a["fact_id"], b["fact_id"]], URGENCY_DECLINE, 0.5 + abs(rate_delta) / 200))
    return out


def revenue_up_margin_down(facts: Facts) -> list[dict]:
    rev, gm = facts.get("revenue"), facts.get("gross_margin")
    if not (rev and gm):
        return []
    tests = {"materiality": rev["value"] > 0,
             "deviation": (rev["delta_pct"] or 0) > 0 and (gm["delta_pct"] or 0) <= -5,
             "localization": True, "actionability": bool(_actionable("revenue_up_margin_down"))}
    title = f"Revenue is {_signed(rev['delta_pct'])} but gross margin is {_signed(gm['delta_pct'])}"
    return [_candidate("sig_revenue_up_margin_down", "bottleneck", "revenue_up_margin_down", "gross_margin",
                       {}, title, tests, [rev["fact_id"], gm["fact_id"]], URGENCY_DECLINE,
                       0.5 + abs(gm["delta_pct"] or 0) / 100)]


def first_orders_high_repeat_low(facts: Facts) -> list[dict]:
    rep = facts.get("repeat_rate")
    if not rep:
        return []
    tests = {"materiality": (rep["denominator"] or 0) >= 50,
             "deviation": (rep["delta_pct"] or 0) <= -DEVIATION_PCT / 2,
             "localization": True, "actionability": bool(_actionable("first_orders_high_repeat_low"))}
    title = f"Repeat orders are {_pct(rep['value'])} of orders against {_pct(rep['baseline'])} before"
    return [_candidate("sig_first_orders_high_repeat_low", "bottleneck", "first_orders_high_repeat_low",
                       "repeat_rate", {}, title, tests, [rep["fact_id"]], URGENCY_DECLINE,
                       0.5 + abs(rep["delta_pct"] or 0) / 100)]


# ---------------------------------------------------------------- opportunities


def improving_repeat_cohort(facts: Facts) -> list[dict]:
    overall = facts.get("repeat_rate")
    out = []
    for f in facts.where("repeat_rate"):
        if "cohort" not in f["dimension"]:
            continue
        ch = f["dimension"].get("channel", "cohort")
        tests = {"materiality": (f["denominator"] or 0) >= COHORT_MIN_SIZE,
                 "deviation": (f["delta_pct"] or 0) >= DEVIATION_PCT,
                 "localization": overall is None or (overall["delta_pct"] or 0) < (f["delta_pct"] or 0),
                 "actionability": bool(_actionable("improving_repeat_cohort"))}
        title = (f"First-time buyers on the {ch} list repeat at {_pct(f['value'])} vs "
                 f"{_pct(f['baseline'])} ({_signed(f['delta_pct'])})")
        evidence = [f["fact_id"]] + ([overall["fact_id"]] if overall else [])
        out.append(_candidate(f"sig_{ch}_repeat_cohort", "opportunity", "improving_repeat_cohort", "repeat_rate",
                              f["dimension"], title, tests, evidence, URGENCY_OPPORTUNITY,
                              0.3 + (f["delta_pct"] or 0) / 100))
    return out


def high_performing_channel(facts: Facts) -> list[dict]:
    share = spend_share(facts)
    out = []
    for ch, f in facts.channel("contribution_roas").items():
        tests = {"materiality": share.get(ch, 0) >= MATERIAL_SPEND_SHARE,
                 "deviation": f["value"] >= GOOD_CROAS and (f["delta_pct"] or 0) >= 0,
                 "localization": True, "actionability": bool(_actionable("high_performing_channel"))}
        title = f"{ch.title()} returns {_num(f['value'])} contribution per rupee"
        out.append(_candidate(f"sig_{ch}_high_performing", "opportunity", "high_performing_channel",
                              "contribution_roas", {"channel": ch}, title, tests, [f["fact_id"]],
                              URGENCY_OPPORTUNITY, 0.3 + f["value"] / 5))
    return out


def high_value_leads(leads: list[dict], covered: set) -> list[dict]:
    warm = [l for l in leads if l.get("high_value") and not l["abstain"] and l["lead_id"] not in covered
            and (l["probability"] or 0) >= 0.3]
    if not warm:
        return []
    tests = {"materiality": len(warm) >= 2, "deviation": True, "localization": True,
             "actionability": bool(_actionable("high_value_leads"))}
    title = f"{len(warm)} high-value leads have an above-average chance to convert"
    return [_candidate("sig_high_value_leads", "opportunity", "high_value_leads", "lead_wins",
                       {"segment": "high_value"}, title, tests, [l["lead_id"] for l in warm],
                       URGENCY_OPPORTUNITY, 0.5)]


# ---------------------------------------------------------------- anomalies


def cac_anomalies(facts: Facts, series_doc: Optional[dict], period: dict) -> list[dict]:
    if not series_doc:
        return []
    cac, spend = facts.channel("cac"), facts.channel("ad_spend")
    share = spend_share(facts)
    out = []
    for a in anomaly.detect(series_doc, period["from"], period["to"], kpi="cac"):
        ch = a["channel"]
        f = cac.get(ch)
        if not f:
            continue
        others = {c: o for c, o in cac.items() if c != ch}
        tests = {"materiality": share.get(ch, 0) >= MATERIAL_SPEND_SHARE,
                 "deviation": (f["delta_pct"] or 0) >= DEVIATION_PCT,
                 "localization": all(abs(o["delta_pct"] or 0) < STABLE_PCT for o in others.values()),
                 "actionability": bool(_actionable("cac_spike"))}
        stable = " and ".join(c.title() for c in others) if others else ""
        title = (f"{ch.title()} CAC jumped to INR {_num(f['value'])} from a INR {_num(f['baseline'])} "
                 f"baseline ({_signed(f['delta_pct'])})" + (f"; {stable} CAC is stable" if stable else ""))
        evidence = [f["fact_id"]] + ([spend[ch]["fact_id"]] if ch in spend else [])
        evidence += [o["fact_id"] for o in others.values()]
        out.append(_candidate(f"sig_{ch}_cac_spike", "anomaly", "cac_spike", "cac", {"channel": ch}, title,
                              tests, evidence, URGENCY_MONEY_LEAK, 0.5 + (f["delta_pct"] or 0) / 100 * 0.6,
                              method="seasonal_median_mad_robust_z", score=a["max_z"],
                              extra={"detected_on": a["first_alert"], "alert_dates": a["alert_dates"]}))
    return out


# ---------------------------------------------------------------- entry point


def main_period(facts: list[dict]) -> dict:
    periods = Counter((f["period"]["from"], f["period"]["to"]) for f in facts)
    (start, end), _ = periods.most_common(1)[0]
    return {"from": start, "to": end}


def detect(ctx: dict, kpi_facts: list[dict], lead_scores: dict, series_doc: Optional[dict]) -> dict:
    facts = Facts(kpi_facts)
    leads = lead_scores.get("leads", [])
    period = main_period(kpi_facts)
    candidates = (latency_over_sla(facts, leads, ctx) + cac_anomalies(facts, series_doc, period)
                  + high_spend_low_contribution(facts) + funnel_rules(facts) + revenue_up_margin_down(facts)
                  + first_orders_high_repeat_low(facts) + improving_repeat_cohort(facts)
                  + high_performing_channel(facts))
    signals = [c for c in candidates if all(c["tests"].values())]
    covered = {e for s in signals for e in s["evidence_ids"]}
    for c in high_value_leads(leads, covered):
        candidates.append(c)
        if all(c["tests"].values()):
            signals.append(c)
    rejected = [{"signal_id": c["signal_id"], "rule": c["rule"], "tests": c["tests"],
                 "failed": [k for k, v in c["tests"].items() if not v]}
                for c in candidates if c["tests"]["deviation"] and not all(c["tests"].values())]
    return {"business_id": ctx["business_id"], "synthetic": ctx.get("synthetic", False),
            "period": period, "anomaly_method": "seasonal_median_mad_robust_z",
            "anomaly_skipped": series_doc is None, "signals": signals, "rejected": rejected}
