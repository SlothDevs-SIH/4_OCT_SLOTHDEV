"""Grounded Q&A: answers only from KPI facts and must cite their fact_ids."""
from __future__ import annotations

import re

from backend.decision_engine.llm.synthesize import Synthesizer
from backend.decision_engine.llm.validator import validate_answer
from backend.decision_engine.recommend import kpi_label

KPI_WORDS = {
    "cac": ["cac", "acquisition cost", "cost per customer", "cost to acquire"],
    "conversion_rate": ["conversion", "converting"],
    "roas": ["roas", "return on ad"],
    "contribution_roas": ["contribution", "profit", "profitable", "break-even", "break even"],
    "repeat_rate": ["repeat", "retention", "returning", "come back"],
    "response_latency_p90": ["response", "reply", "replies", "latency", "slow"],
    "unattended_leads": ["unattended", "waiting", "ignored"],
    "lead_wins": ["win", "wins", "won", "close", "closed"],
    "ad_spend": ["spend", "spending", "budget"],
    "revenue": ["revenue", "sales"],
    "orders": ["orders"],
    "aov": ["aov", "order value", "basket"],
    "gross_margin": ["margin"],
    "leads": ["leads", "enquiries", "inquiries"],
    "funnel_sessions": ["sessions", "traffic", "visitors", "funnel"],
    "funnel_qualified": ["qualified", "funnel"],
    "funnel_won": ["funnel"],
}
MAX_FACTS = 4


def _has(text: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(word)}", text) is not None


def retrieve(question: str, facts: list[dict]) -> list[dict]:
    q = question.lower()
    channels = {f["dimension"].get("channel") for f in facts} - {None}
    asked_channels = {c for c in channels if _has(q, c)}
    scored = []
    for f in facts:
        score = 2 * any(_has(q, w) for w in KPI_WORDS.get(f["kpi"], [f["kpi"].replace("_", " ")]))
        if score == 0:
            continue
        ch = f["dimension"].get("channel")
        if asked_channels:
            score += 2 if ch in asked_channels else -2  # another channel's fact is off-topic
        scored.append((score, f))
    scored.sort(key=lambda x: -x[0])
    return [f for s, f in scored if s > 0][:MAX_FACTS]


def describe(f: dict) -> str:
    def fmt(v):
        if v is None:
            return "n/a"
        if f["unit"] == "INR":
            return f"INR {v:,.10g}"
        if f["unit"] == "ratio" and f["kpi"] not in ("roas", "contribution_roas"):
            return f"{round(v * 100, 1):g}%"
        if f["unit"] == "hours":
            return f"{v:g} h"
        return f"{v:g}"

    dims = ", ".join(str(v) for v in f["dimension"].values())
    label = kpi_label(f["kpi"])
    text = f"{label[0].upper() + label[1:]}{f' ({dims})' if dims else ''} is {fmt(f['value'])}"
    if f["baseline"] is not None:
        text += f" against a baseline of {fmt(f['baseline'])}"
        if f["delta_pct"] is not None:
            text += f" ({'+' if f['delta_pct'] >= 0 else ''}{f['delta_pct']:g}%)"
    if f["quality_flag"] != "ok":
        text += f"; data quality is {f['quality_flag']}"
    return text + f" [{f['fact_id']}]."


def answer(question: str, ctx: dict, facts: list[dict], synthesizer: Synthesizer) -> dict:
    relevant = retrieve(question, facts)
    keep = ("fact_id", "kpi", "dimension", "period", "value", "unit", "baseline", "delta_pct", "quality_flag")
    packet = {"task": "answer_question", "question": question, "business": {"name": ctx.get("name")},
              "facts": [{k: f[k] for k in keep} for f in relevant]}

    def fallback():
        if not relevant:
            return {"answer": "That is not in the data I have. Try asking about CAC, conversion, spend, "
                              "repeat rate, leads or response time.", "citations": []}
        return {"answer": " ".join(describe(f) for f in relevant), "citations": [f["fact_id"] for f in relevant]}

    if not relevant:
        out, meta = fallback(), {"used": False, "cached": False, "provider": None, "model": None,
                                 "fallback": True, "validator": {"passed": True, "retries": 0, "errors": []},
                                 "prompt_version": None}
    else:
        out, meta = synthesizer.run("answer_question", packet, validate_answer, fallback)
    return {"business_id": ctx["business_id"], "question": question, "answer": out["answer"],
            "citations": out["citations"], "facts_considered": [f["fact_id"] for f in relevant], "llm": meta}
