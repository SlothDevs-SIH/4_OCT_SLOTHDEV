"""Fill the local LLM cache before the demo so it runs offline.

    LLM_PROVIDER=anthropic LLM_API_KEY=... LLM_MODEL=... python -m backend.decision_engine.llm.warm_cache biz_aarohi_skin

Then run the demo with LLM_CACHE_ONLY=true: every explanation is served from the cache.
"""
import sys

from backend.decision_engine.service import Engine


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    business_id = argv[0] if argv else "biz_aarohi_skin"
    engine = Engine()
    if engine.synthesizer.provider is None:
        print("No live provider: set LLM_PROVIDER (openai|anthropic|gemini), LLM_API_KEY and LLM_MODEL, "
              "and LLM_CACHE_ONLY=false.")
        return 1
    ok = True
    for rec in engine.generate(business_id)["recommendations"]:
        llm = rec["llm"]
        state = "blocked (no LLM)" if rec["status"] == "blocked" else \
            "cached" if llm["cached"] else "LLM" if llm["used"] else f"FALLBACK {llm['validator']['errors']}"
        ok &= rec["status"] == "blocked" or llm["used"]
        print(f"{rec['recommendation_id']:<24} {state}")
    print(f"cache: {engine.settings.llm_cache_dir}")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
