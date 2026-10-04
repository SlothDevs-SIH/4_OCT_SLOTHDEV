"""LLM providers behind one interface. Switch with LLM_PROVIDER; keys come from .env.

Each provider turns (system, user) into the model's text reply. Plain HTTP via urllib,
so no SDK is required. Errors raise ProviderError; the caller falls back.
"""
from __future__ import annotations

import json
import os
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ProviderError(RuntimeError):
    pass


class Provider:
    name = "none"
    model: Optional[str] = None

    def complete(self, system: str, user: str) -> str:
        raise NotImplementedError


class _HttpProvider(Provider):
    default_base = ""

    def __init__(self, api_key: str, model: str, timeout: float = 30.0, base_url: Optional[str] = None):
        if not api_key or not model:
            raise ProviderError(f"{self.name}: LLM_API_KEY and LLM_MODEL are required")
        self.api_key, self.model, self.timeout = api_key, model, timeout
        self.base_url = (base_url or os.getenv("LLM_BASE_URL") or self.default_base).rstrip("/")

    def _post(self, url: str, body: dict, headers: dict) -> dict:
        req = Request(url, data=json.dumps(body).encode(), method="POST",
                      headers={"Content-Type": "application/json", **headers})
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode())
        except HTTPError as e:
            # never include headers (they hold the key) in the message
            raise ProviderError(f"{self.name}: HTTP {e.code}") from None
        except (URLError, TimeoutError, ValueError) as e:
            raise ProviderError(f"{self.name}: {type(e).__name__}") from None


class OpenAIProvider(_HttpProvider):
    name, default_base = "openai", "https://api.openai.com"

    def complete(self, system: str, user: str) -> str:
        body = {"model": self.model, "temperature": 0, "response_format": {"type": "json_object"},
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        data = self._post(f"{self.base_url}/v1/chat/completions", body,
                          {"Authorization": f"Bearer {self.api_key}"})
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise ProviderError("openai: unexpected response shape") from None


class AnthropicProvider(_HttpProvider):
    name, default_base = "anthropic", "https://api.anthropic.com"

    def complete(self, system: str, user: str) -> str:
        body = {"model": self.model, "max_tokens": 1024, "temperature": 0, "system": system,
                "messages": [{"role": "user", "content": user}]}
        data = self._post(f"{self.base_url}/v1/messages", body,
                          {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"})
        try:
            return "".join(b["text"] for b in data["content"] if b.get("type") == "text")
        except (KeyError, TypeError):
            raise ProviderError("anthropic: unexpected response shape") from None


class GeminiProvider(_HttpProvider):
    name, default_base = "gemini", "https://generativelanguage.googleapis.com"

    def complete(self, system: str, user: str) -> str:
        body = {"systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}}
        data = self._post(f"{self.base_url}/v1beta/models/{self.model}:generateContent", body,
                          {"x-goog-api-key": self.api_key})
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError):
            raise ProviderError("gemini: unexpected response shape") from None


PROVIDERS = {"openai": OpenAIProvider, "anthropic": AnthropicProvider, "gemini": GeminiProvider}


def from_settings(settings) -> Optional[Provider]:
    """The live provider, or None when only the cache may be used."""
    if settings.llm_cache_only or settings.llm_provider == "cache":
        return None
    if not settings.llm_api_key or not settings.llm_model:
        return None
    return PROVIDERS[settings.llm_provider](settings.llm_api_key, settings.llm_model, settings.llm_timeout_s)
