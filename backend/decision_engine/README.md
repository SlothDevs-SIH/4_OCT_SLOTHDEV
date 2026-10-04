# decision_engine (backend-2)

Turns data_engine's facts into decisions: signals → eligibility gate → priority score → constrained LLM explanation → human approval → 7-day plan → day-7 outcome ledger. Contract: `contracts/API_CONTRACT.md` section 4.

## Run and test (from the repo root)

```bash
pip install -r backend/requirements.txt
uvicorn backend.decision_engine.main:app --port 8002 --reload     # docs at http://localhost:8002/docs
python -m pytest backend -q
python -m backend.decision_engine.anomaly                          # anomaly benchmark -> reports/anomaly_metrics.json
python -m backend.decision_engine.export_fixtures                  # regenerate output fixtures
```

| Env var | Default | Meaning |
|---|---|---|
| `DATA_SOURCE` | `fixture` | `fixture` (contracts/fixtures), `http` (`DATA_ENGINE_URL`), `local` (in-process `data_engine.public`) |
| `LLM_PROVIDER` | `cache` | `openai`, `anthropic`, `gemini` or `cache` |
| `LLM_API_KEY`, `LLM_MODEL` | – | needed for a live provider; never logged |
| `LLM_CACHE_ONLY` | `false` | `true` = never call the network; cached answers or deterministic text |
| `LLM_CACHE_DIR` | `backend/decision_engine/llm_cache` | where validated LLM answers are stored |
| `LLM_BASE_URL`, `LLM_TIMEOUT_S` | provider default, 30 | optional overrides |

**Demo with a real LLM, offline:** set the provider, key and model, run `python -m backend.decision_engine.llm.warm_cache biz_aarohi_skin` once, then start the server with `LLM_CACHE_ONLY=true`. Without a key everything still works: explanations use deterministic text built from the facts (`llm.used: false`).

## Demo loop

`GET /signals` → `POST /recommendations/generate` → `POST /recommendations/{id}/approve` → `GET /recommendations/{id}/draft` → `POST /plans` → `PATCH /tasks/{id}` → (data_engine: `POST /demo/load?phase=day7`) → `POST /plans/{id}/outcomes/evaluate` → `POST /chat`.

On the demo data this gives 4 signals; hot leads 70.1 > email 55.2 > Instagram test 49.6, with "increase ad spend" blocked; a 435-minute plan; and promising / inconclusive / inconclusive at day 7.

## How each part works

| File | Task | What it does |
|---|---|---|
| `clients/data_client.py` | 1 | the only way to read data_engine (`fixture` / `http` / `local`) |
| `templates.py` | 1 | loads and schema-checks the action library |
| `signals.py` | 2 | 6 bottleneck rules + 3 opportunity detectors; a signal must pass materiality, deviation, localization and actionability; near-misses are listed under `rejected` |
| `anomaly.py` | 3 | seasonal median/MAD robust z (same weekday, 28-day window, \|z\| > 3.5); Isolation Forest challenger kept only if better. Demo: spike caught on day 1, F1 0.667 vs 0.143, 0.125 false alerts/week |
| `eligibility.py` | 4 | blocks forbidden, over-budget, over-capacity, missing-data and unapproved spend/outreach actions with a `blocked_reason` |
| `scoring.py`, `factors.py` | 5 | the priority equation; Q = 0.5·data quality (confidence × KPI quality) + 0.25·model calibration (lead actions only) + 0.25·rule strength |
| `llm/`, `recommend.py` | 6 | evidence packet → provider → validator (unknown IDs, numbers not in the packet, other actions, spend increase) → one retry → deterministic fallback; cache for offline use |
| `planner.py` | 7 | least-slack list scheduling within the day cap, weekly minutes and owner limits; whole recommendations only |
| `outcomes.py` | 8 | baseline frozen at approval; fidelity vs effectiveness; window, guardrails, confounders; always observational |
| `chat.py`, `drafts.py` | 9 | grounded Q&A citing `fact_id`s; WhatsApp/email previews, never auto-sent (there is no send endpoint) |

## Known limits

- Storage is in memory (`store.py`); a restart clears recommendations and plans. `db/schema.sql` has the tables for a Postgres store with the same methods.
- `http` mode is tested against a local stub server, not yet against the real data_engine.
- The model card metrics in `lead_scores.json` are placeholders until backend-1 trains the model.

## Pre-existing components (for the PR)

FastAPI, Pydantic, Uvicorn, scikit-learn (Isolation Forest), NumPy, jsonschema, httpx (tests), pytest. LLM providers are called over their public HTTP APIs (no SDK). Everything else in this folder was built during the event.
