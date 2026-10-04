"""Run one constrained LLM task: cache -> provider (retry once) -> deterministic fallback.

Invalid LLM output never leaves this module: if neither the cache nor the provider gives
a valid answer, the caller's deterministic fallback is returned instead.
"""
from __future__ import annotations

import json
import re
from typing import Callable, Optional

from backend.decision_engine.llm.cache import LLMCache, packet_key
from backend.decision_engine.llm.providers import Provider, ProviderError, from_settings

PROMPT_VERSION = "v1"

RULES = """Rules (non-negotiable):
- Use only the facts, signals and leads in the evidence packet. Never calculate a new KPI or probability.
- Every number you write must appear in the packet (a ratio such as 0.214 may be written as 21.4%).
- Cite the IDs you rely on (fact_id, lead_id or signal_id) exactly as written in the packet.
- Do not propose actions; the engine already chose them. Never suggest paid ads: the owner has no ad budget.
- Be plain and specific. If data quality is partial, say so.
- Reply with one JSON object only, no markdown."""

SYSTEM_PROMPTS = {
    "explain_diagnosis": f"""You explain to a home-business owner what is holding their business back this week.
The engine already chose the bottleneck from their numbers; you explain it in plain, warm language.
{RULES}
Return: {{"summary": "<3-4 short sentences: the bottleneck, the evidence, the runners-up>", "evidence_ids": ["<fact_ids you cite>"]}}""",
    "explain_next_month": f"""You explain next month's projected orders to a home-business owner.
It is an estimate; say so. Tie it to the bottleneck the engine named.
{RULES}
Return: {{"summary": "<2-3 short sentences>", "evidence_ids": ["<fact_ids you cite>"]}}""",
    "answer_question": f"""You answer the owner's question using only the business facts provided.
{RULES}
If the packet does not contain the answer, say that the data is not available.
Return: {{"answer": "<2-4 sentences>", "citations": ["<fact_ids you used>"]}}""",
}

FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.M)


def parse_json(text: str):
    try:
        out = json.loads(FENCE_RE.sub("", text.strip()))
    except (ValueError, TypeError):
        return None, ["response is not valid JSON"]
    if not isinstance(out, dict):
        return None, ["response is not a JSON object"]
    return out, []


class Synthesizer:
    def __init__(self, settings, provider: Optional[Provider] = None, cache: Optional[LLMCache] = None):
        self.settings = settings
        self.provider = provider if provider is not None else from_settings(settings)
        self.cache = cache or LLMCache(settings.llm_cache_dir)

    def run(self, task: str, packet: dict, validate: Callable[[dict, dict], list],
            fallback: Callable[[], dict]) -> tuple[dict, dict]:
        system = SYSTEM_PROMPTS[task]
        key = packet_key(packet, system)
        errors: list[str] = []

        hit = self.cache.get(key)
        if hit:
            out, errs = parse_json(hit["response"])
            errs = errs or validate(out, packet)
            if not errs:
                return out, self._meta(True, True, hit.get("provider"), hit.get("model"), False, 0, [])
            errors += [f"cache: {e}" for e in errs]

        if self.provider is None:
            return fallback(), self._meta(False, False, None, None, True, 0, errors)

        user = json.dumps(packet, ensure_ascii=False)
        message, attempts = user, 0
        for attempts in range(2):
            try:
                text = self.provider.complete(system, message)
            except ProviderError as e:
                errors.append(str(e))
                break
            out, errs = parse_json(text)
            errs = errs or validate(out, packet)
            if not errs:
                self.cache.put(key, text, self.provider.name, self.provider.model, task)
                return out, self._meta(True, False, self.provider.name, self.provider.model, False, attempts, errors)
            errors += errs
            message = (f"{user}\n\nYour previous answer was rejected: {'; '.join(errs)}. "
                       "Return a corrected JSON object only.")
        return fallback(), self._meta(False, False, self.provider.name, self.provider.model, True, attempts, errors)

    @staticmethod
    def _meta(used, cached, provider, model, fallback, retries, errors) -> dict:
        return {"used": used, "cached": cached, "provider": provider, "model": model, "fallback": fallback,
                "validator": {"passed": not fallback, "retries": retries, "errors": errors[-6:]},
                "prompt_version": PROMPT_VERSION}
