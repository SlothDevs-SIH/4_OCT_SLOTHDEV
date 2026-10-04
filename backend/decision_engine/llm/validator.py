"""Validator for LLM output. Rejects (a) unknown evidence IDs, (b) numbers that are not in
the evidence packet, (c) actions outside the allowed templates, (d) constraint violations,
plus anything that does not match the JSON schema."""
from __future__ import annotations

import re

import jsonschema

NUMBER_RE = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?")
DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}(?:T[\d:]+Z?)?\b")
TRIVIAL_NUMBERS = {0.0, 1.0}
SPEND_UP_RE = re.compile(r"\b(increase|increasing|raise|raising|boost|boosting|double|scale up|scaling up|add)\b"
                         r"[^.]{0,40}\b(spend|spending|budget|ad budget|bids?)\b", re.I)

RECOMMENDATION_SCHEMA = {
    "type": "object",
    "required": ["template_id", "rationale", "evidence_ids"],
    "additionalProperties": False,
    "properties": {
        "template_id": {"type": "string"},
        "rationale": {"type": "string", "minLength": 20, "maxLength": 700},
        "evidence_ids": {"type": "array", "minItems": 1, "maxItems": 12, "items": {"type": "string"}},
        "assumptions": {"type": "array", "maxItems": 4, "items": {"type": "string", "maxLength": 200}},
    },
}

ANSWER_SCHEMA = {
    "type": "object",
    "required": ["answer", "citations"],
    "additionalProperties": False,
    "properties": {
        "answer": {"type": "string", "minLength": 1, "maxLength": 900},
        "citations": {"type": "array", "items": {"type": "string"}},
    },
}


def _to_float(token: str) -> float:
    return float(token.replace(",", ""))


def numbers_in_text(text: str) -> list[str]:
    return NUMBER_RE.findall(DATE_RE.sub(" ", text))


def packet_numbers(obj, out=None) -> set:
    """Every number in the packet, including numbers written inside its strings."""
    out = set() if out is None else out
    if isinstance(obj, bool):
        return out
    if isinstance(obj, (int, float)):
        out.add(float(obj))
    elif isinstance(obj, str):
        out.update(_to_float(t) for t in numbers_in_text(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            packet_numbers(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            packet_numbers(v, out)
    return out


def number_allowed(n: float, pool: set) -> bool:
    if n in TRIVIAL_NUMBERS:
        return True
    for v in pool:
        forms = {abs(v)}
        if abs(v) <= 1.5:
            forms.add(abs(v) * 100)  # 0.214 may be written as 21.4%
        for f in forms:
            if abs(f - n) < 1e-9 or any(round(f, d) == n for d in range(4)):
                return True
    return False


def unknown_numbers(texts: list[str], pool: set) -> list[str]:
    bad = []
    for text in texts:
        for token in numbers_in_text(text):
            if not number_allowed(_to_float(token), pool):
                bad.append(token)
    return bad


def schema_errors(out, schema: dict) -> list[str]:
    try:
        jsonschema.validate(out, schema)
        return []
    except jsonschema.ValidationError as e:
        return [f"schema: {e.message}"]


def packet_ids(packet: dict) -> set:
    ids = {f["fact_id"] for f in packet.get("facts", [])}
    ids |= {l["lead_id"] for l in packet.get("leads", [])}
    ids |= {s["signal_id"] for s in packet.get("signals", [])}
    return ids


def validate_recommendation(out, packet: dict) -> list[str]:
    errors = schema_errors(out, RECOMMENDATION_SCHEMA)
    if errors:
        return errors
    rec = packet["recommendation"]
    if out["template_id"] not in packet["allowed_template_ids"] or out["template_id"] != rec["template_id"]:
        errors.append(f"action outside the allowed templates: {out['template_id']}")
    known = packet_ids(packet)
    unknown = [e for e in out["evidence_ids"] if e not in known]
    if unknown:
        errors.append(f"unknown evidence_ids: {unknown}")
    fact_ids = {f["fact_id"] for f in packet.get("facts", [])}
    if not any(e in fact_ids for e in out["evidence_ids"]):
        errors.append("evidence_ids must cite at least one fact_id")
    texts = [out["rationale"]] + out.get("assumptions", [])
    bad = unknown_numbers(texts, packet_numbers(packet))
    if bad:
        errors.append(f"numbers not in the evidence packet: {bad}")
    forbidden = packet["business"]["constraints"].get("forbidden_actions", [])
    if rec["status"] != "blocked" and "increase_total_ad_spend" in forbidden:
        if any(SPEND_UP_RE.search(t) for t in texts):
            errors.append("constraint violation: proposes increasing ad spend")
    return errors


def validate_answer(out, packet: dict) -> list[str]:
    errors = schema_errors(out, ANSWER_SCHEMA)
    if errors:
        return errors
    known = packet_ids(packet)
    unknown = [c for c in out["citations"] if c not in known]
    if unknown:
        errors.append(f"unknown citations: {unknown}")
    bad = unknown_numbers([out["answer"]], packet_numbers(packet))
    if bad:
        errors.append(f"numbers not in the evidence packet: {bad}")
    if bad == [] and numbers_in_text(out["answer"]) and not out["citations"]:
        errors.append("an answer with numbers must cite fact_ids")
    return errors
