import io
import json

import pytest

from backend.decision_engine.config import Settings
from backend.decision_engine.llm import providers, validator
from backend.decision_engine.llm.cache import LLMCache
from backend.decision_engine.llm.providers import ProviderError
from backend.decision_engine.llm.synthesize import Synthesizer

PACKET = {
    "business": {"constraints": {"forbidden_actions": ["increase_total_ad_spend"]}},
    "recommendation": {"template_id": "tpl_x", "status": "proposed"},
    "allowed_template_ids": ["tpl_x"],
    "signals": [{"signal_id": "sig_a", "title": "8 leads waiting; p90 is 38.5 h vs 4 h"}],
    "facts": [{"fact_id": "f_a", "value": 0.214, "baseline": 0.162, "delta_pct": 32.1},
              {"fact_id": "f_b", "value": 36720.0}],
    "leads": [{"lead_id": "lead_0412", "probability": 0.46}],
}
GOOD = {"template_id": "tpl_x", "evidence_ids": ["f_a", "lead_0412"],
        "rationale": "Repeat rate is 21.4% vs 16.2% (+32.1%) and INR 36,720 is at stake; lead_0412 has a 46% chance."}


# ---------------------------------------------------------------- validator


def test_valid_output_passes():
    assert validator.validate_recommendation(GOOD, PACKET) == []


@pytest.mark.parametrize("change,needle", [
    ({"evidence_ids": ["f_zzz"]}, "unknown evidence_ids"),
    ({"evidence_ids": ["lead_0412"]}, "at least one fact_id"),
    ({"rationale": "Repeat rate will jump to 35% next week, trust me on this."}, "numbers not in the evidence packet"),
    ({"template_id": "tpl_other"}, "outside the allowed templates"),
    ({"rationale": "Increase the Instagram ad budget so CAC of 21.4% falls."}, "constraint violation"),
    ({"extra": "field"}, "schema"),
    ({"rationale": "short"}, "schema"),
])
def test_invalid_outputs_rejected(change, needle):
    errors = validator.validate_recommendation(GOOD | change, PACKET)
    assert any(needle in e for e in errors), errors


def test_ids_and_dates_are_not_numbers():
    assert validator.numbers_in_text("lead_0412 on 2026-09-29 in p90 at 38.5 h") == ["38.5"]


def test_number_forms():
    pool = {0.214, 36720.0, 38.5}
    for n in ("21.4", "0.21", "36,720", "38.5", "1"):
        assert validator.number_allowed(float(n.replace(",", "")), pool), n
    assert not validator.number_allowed(42.0, pool)


def test_answer_validator():
    ok = {"answer": "CAC on Instagram is INR 36,720 of spend.", "citations": ["f_b"]}
    assert validator.validate_answer(ok, PACKET) == []
    assert validator.validate_answer(ok | {"citations": []}, PACKET)
    assert validator.validate_answer(ok | {"citations": ["f_nope"]}, PACKET)


# ---------------------------------------------------------------- synthesizer


class FakeProvider(providers.Provider):
    name, model = "fake", "fake-1"

    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def complete(self, system, user):
        self.calls.append(user)
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return r if isinstance(r, str) else json.dumps(r)


FALLBACK = {"template_id": "tpl_x", "rationale": "deterministic text from facts", "evidence_ids": ["f_a"]}


def synth(tmp_path, provider):
    s = Settings(llm_provider="cache", llm_cache_dir=tmp_path)
    return Synthesizer(s, provider=provider, cache=LLMCache(tmp_path))


def run(sy):
    return sy.run("explain_recommendation", PACKET, validator.validate_recommendation, lambda: FALLBACK)


def test_valid_reply_is_cached_then_served_offline(tmp_path):
    out, meta = run(synth(tmp_path, FakeProvider([GOOD])))
    assert out == GOOD and meta["used"] and not meta["cached"] and not meta["fallback"]
    # second run with no provider at all: served from the cache
    sy = Synthesizer(Settings(llm_cache_only=True, llm_cache_dir=tmp_path), cache=LLMCache(tmp_path))
    assert sy.provider is None
    out, meta = run(sy)
    assert out == GOOD and meta["used"] and meta["cached"] and meta["provider"] == "fake"


def test_invalid_then_valid_retries_once(tmp_path):
    bad = GOOD | {"evidence_ids": ["f_made_up"]}
    fake = FakeProvider([bad, "```json\n" + json.dumps(GOOD) + "\n```"])
    out, meta = run(synth(tmp_path, fake))
    assert out == GOOD and meta["validator"]["retries"] == 1
    assert "previous answer was rejected" in fake.calls[1]


def test_invalid_twice_falls_back(tmp_path):
    bad = GOOD | {"rationale": "Spend jumps 99% if you trust me on this plan."}
    out, meta = run(synth(tmp_path, FakeProvider([bad, "not json"])))
    assert out == FALLBACK and meta["fallback"] and not meta["used"] and not meta["validator"]["passed"]
    assert list(tmp_path.glob("*.json")) == []  # invalid output is never cached


def test_provider_error_falls_back(tmp_path):
    out, meta = run(synth(tmp_path, FakeProvider([ProviderError("openai: HTTP 500")])))
    assert out == FALLBACK and meta["validator"]["errors"] == ["openai: HTTP 500"]


def test_cache_only_miss_falls_back(tmp_path):
    sy = Synthesizer(Settings(llm_cache_only=True, llm_cache_dir=tmp_path))
    out, meta = run(sy)
    assert out == FALLBACK and meta == meta | {"used": False, "cached": False, "fallback": True}


def test_stale_cache_entry_is_revalidated(tmp_path):
    run(synth(tmp_path, FakeProvider([GOOD])))
    entry = next(tmp_path.glob("*.json"))
    data = json.loads(entry.read_text())
    data["response"] = json.dumps(GOOD | {"evidence_ids": ["f_gone"]})
    entry.write_text(json.dumps(data))
    out, meta = run(Synthesizer(Settings(llm_cache_only=True, llm_cache_dir=tmp_path), cache=LLMCache(tmp_path)))
    assert out == FALLBACK


# ---------------------------------------------------------------- providers (HTTP shape, no network)


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.mark.parametrize("cls,reply,url_part,key_header", [
    (providers.OpenAIProvider, {"choices": [{"message": {"content": "{}"}}]}, "/v1/chat/completions", "Authorization"),
    (providers.AnthropicProvider, {"content": [{"type": "text", "text": "{}"}]}, "/v1/messages", "X-api-key"),
    (providers.GeminiProvider, {"candidates": [{"content": {"parts": [{"text": "{}"}]}}]}, ":generateContent", "X-goog-api-key"),
])
def test_provider_requests(monkeypatch, cls, reply, url_part, key_header):
    seen = {}

    def fake_urlopen(req, timeout):
        seen["url"], seen["headers"], seen["body"] = req.full_url, dict(req.header_items()), json.loads(req.data)
        return FakeResponse(json.dumps(reply).encode())

    monkeypatch.setattr(providers, "urlopen", fake_urlopen)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    assert cls("k-123", "some-model").complete("sys", "user") == "{}"
    assert url_part in seen["url"] and key_header in seen["headers"]
    assert "sys" in json.dumps(seen["body"]) and "user" in json.dumps(seen["body"])


def test_provider_error_hides_key(monkeypatch):
    from urllib.error import HTTPError

    def boom(req, timeout):
        raise HTTPError(req.full_url, 401, "unauthorized", {}, None)

    monkeypatch.setattr(providers, "urlopen", boom)
    with pytest.raises(ProviderError) as e:
        providers.OpenAIProvider("k-secret", "m").complete("s", "u")
    assert "k-secret" not in str(e.value) and "401" in str(e.value)


def test_from_settings():
    assert providers.from_settings(Settings(llm_provider="openai")) is None  # no key -> cache/fallback only
    p = providers.from_settings(Settings(llm_provider="gemini", llm_api_key="k", llm_model="m"))
    assert isinstance(p, providers.GeminiProvider)
    assert providers.from_settings(Settings(llm_provider="gemini", llm_api_key="k", llm_model="m",
                                            llm_cache_only=True)) is None
