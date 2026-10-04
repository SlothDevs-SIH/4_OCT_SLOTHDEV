"""decision_engine settings, read from the environment (see .env.example)."""
import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CACHE_DIR = Path(__file__).resolve().parent / "llm_cache"
LLM_PROVIDERS = ("openai", "gemini", "anthropic", "cache")


def _bool(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    data_source: str = "fixture"
    data_engine_url: str = "http://localhost:8001"
    llm_provider: str = "cache"
    llm_api_key: str = field(default="", repr=False)  # never logged
    llm_model: str = ""
    llm_cache_only: bool = False
    llm_cache_dir: Path = DEFAULT_CACHE_DIR
    llm_timeout_s: float = 30.0

    @classmethod
    def from_env(cls) -> "Settings":
        provider = (os.getenv("LLM_PROVIDER") or "cache").strip().lower()
        if provider not in LLM_PROVIDERS:
            raise ValueError(f"LLM_PROVIDER must be one of {LLM_PROVIDERS}, got {provider!r}")
        return cls(
            data_source=(os.getenv("DATA_SOURCE") or "fixture").strip().lower(),
            data_engine_url=os.getenv("DATA_ENGINE_URL") or "http://localhost:8001",
            llm_provider=provider,
            llm_api_key=os.getenv("LLM_API_KEY") or "",
            llm_model=os.getenv("LLM_MODEL") or "",
            llm_cache_only=_bool(os.getenv("LLM_CACHE_ONLY") or "false"),
            llm_cache_dir=Path(os.getenv("LLM_CACHE_DIR") or DEFAULT_CACHE_DIR),
            llm_timeout_s=float(os.getenv("LLM_TIMEOUT_S") or 30),
        )
