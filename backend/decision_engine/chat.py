"""Grounded Q&A: answers only from this week's facts and cites their fact_ids (should-have)."""
from __future__ import annotations

import re

from backend.decision_engine.diagnosis import fmt
from backend.decision_engine.llm.synthesize import Synthesizer
from backend.decision_engine.llm.validator import validate_answer

KPI_WORDS = {
    "stranger_share": ["stranger", "strangers", "new people", "new customers", "outside my circle", "friends", "reach"],
    "stranger_orders_week": ["stranger", "strangers", "new people", "new customers"],
    "orders_by_source": ["friends", "where do my orders come from", "source"],
    "reach_per_post": ["reach", "views", "seen", "post"],
    "lead_to_order_rate": ["conversion", "convert", "interested", "enquiries", "dms"],
    "orders_per_1000_reach": ["conversion", "convert"],
    "margin_pct": ["margin", "profit", "earn", "make per order"],
    "margin_per_order": ["margin", "profit", "earn", "make per order"],
    "unit_cost_full": ["cost", "costs"],
    "discount_share": ["discount", "discounts"],
    "repeat_customer_share": ["repeat", "come back", "return", "again"],
    "days_between_orders": ["repeat", "come back", "how often"],
    "orders_per_week": ["orders", "sales", "how many orders"],
    "dispatch_delay_days": ["dispatch", "delivery", "late", "slow", "ship"],
    "orders_turned_away": ["turned away", "capacity", "too many orders", "keep up"],
    "capacity_utilisation": ["capacity", "keep up", "limit"],
    "stockouts": ["stock", "stock-out", "ran out"],
}
MAX_FACTS = 4


def retrieve(question: str, facts: list[dict]) -> list[dict]:
    q = question.lower()
    scored = []
    for f in facts:
        words = KPI_WORDS.get(f["kpi"], [f["kpi"].replace("_", " ")])
        hits = sum(1 for w in words if re.search(rf"\b{re.escape(w)}", q))
        if hits:
            scored.append((hits, f))
    scored.sort(key=lambda x: -x[0])
    return [f for _, f in scored][:MAX_FACTS]


def describe(f: dict) -> str:
    label = f["kpi"].replace("_", " ")
    dim = f" ({', '.join(map(str, f['dimension'].values()))})" if f.get("dimension") else ""
    text = f"{label[0].upper()}{label[1:]}{dim} is {fmt(f['value'], f['unit'])}"
    if f.get("baseline") is not None:
        text += f", against {fmt(f['baseline'], f['unit'])} in your best weeks"
    text += f" ({f.get('source', 'derived')}, {f.get('sample_size')} orders)"
    return text + f" [{f['fact_id']}]."


def answer(question: str, business: dict, facts_doc: dict, synthesizer: Synthesizer) -> dict:
    relevant = retrieve(question, facts_doc["facts"])
    keep = ("fact_id", "kpi", "dimension", "period", "value", "unit", "baseline", "source", "sample_size")
    packet = {"task": "answer_question", "question": question, "business": {"name": business["name"]},
              "facts": [{k: f.get(k) for k in keep} for f in relevant]}

    def fallback():
        if not relevant:
            return {"answer": "That is not in your data yet. Try asking about orders from strangers, reach, "
                              "conversion, margin, repeat orders or dispatch.", "citations": []}
        return {"answer": " ".join(describe(f) for f in relevant), "citations": [f["fact_id"] for f in relevant]}

    if not relevant:
        out, meta = fallback(), {"used": False, "cached": False, "fallback": True}
    else:
        out, meta = synthesizer.run("answer_question", packet, validate_answer, fallback)
    return {"business_id": business["business_id"], "week": facts_doc["week"], "question": question,
            "answer": out["answer"], "citations": out["citations"],
            "facts_considered": [f["fact_id"] for f in relevant], "llm": meta}
