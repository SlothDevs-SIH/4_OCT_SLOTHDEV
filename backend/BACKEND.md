# Backend: two independent modules, then integration

**Stack:** Python, FastAPI, Pydantic, pandas, scikit-learn (+ SHAP), PostgreSQL/Supabase, an LLM API behind a provider interface.
**Contract:** [`../contracts/API_CONTRACT.md`](../contracts/API_CONTRACT.md).

**Per-module task lists:** [`BACKEND_1_DATA_ENGINE.md`](BACKEND_1_DATA_ENGINE.md) (Soham) and [`BACKEND_2_DECISION_ENGINE.md`](BACKEND_2_DECISION_ENGINE.md) (Ayush).

> **Status:** the contract in `contracts/API_CONTRACT.md` is the source of truth. Prepared code stubs, example fixtures (`contracts/fixtures/`) and `db/schema.sql` exist locally and are added to `main` when the team asks. Until then, code against the shapes written in the contract.

## 1. The backend in one picture

```
 ┌────────────────────────── data_engine (backend-1, Soham) ──────────────────────────┐
 │ onboarding → CSV import → mapping → validation/quarantine → canonical tables       │
 │            → KPI registry + engine → lead-conversion model (calibrated) + RFM       │
 └──────────────────────────────────┬─────────────────────────────────────────────────┘
                                    │  KPI facts, lead scores, data quality, context
                                    │  (HTTP, or in-process via data_engine/public.py)
 ┌──────────────────────────────────▼─────────────────────────────────────────────────┐
 │ signals (bottleneck rules + anomaly) → eligibility gate → priority score            │
 │   → constrained LLM explanation + validator → approval → 7-day plan → tasks         │
 │   → outcome ledger (day-7 expected vs actual)        decision_engine (backend-2, Ayush) │
 └────────────────────────────────────────────────────────────────────────────────────┘
```

**Why this split is independent:** `decision_engine` never imports `data_engine` code directly except through `DataClient` (`DATA_SOURCE=fixture|http|local`). While `data_engine` is unfinished, Ayush develops against the fixtures in `contracts/fixtures/` (which already contain a believable Aarohi Skin week). Soham never depends on Ayush at all. Tables are split by owner (`db/schema.sql`), so there are no write conflicts.

**Why the work is equal:** each module is ~6 hours of well-bounded tasks (below), one ML component each (lead conversion vs anomaly detection), one "engineering" heavy part each (import and validation vs LLM guardrails), and one data-producing vs data-consuming half.

## 2. Run and test (from the repo root, once the code stubs are on `main`)

```bash
pip install -r backend/requirements.txt
uvicorn backend.data_engine.main:app --port 8001 --reload        # Soham
uvicorn backend.decision_engine.main:app --port 8002 --reload    # Ayush
uvicorn backend.gateway.main:app --port 8000 --reload            # integration
python -m pytest backend -q
```


## 3. The two modules at a glance

| | Backend 1: `data_engine` | Backend 2: `decision_engine` |
|---|---|---|
| Owner / branch | Soham / `backend-1` | Ayush / `backend-2` |
| Folder | `backend/data_engine/` | `backend/decision_engine/` |
| Port | 8001 | 8002 |
| Role | Produces data and ML signals | Turns signals into decisions and actions |
| ML component | Lead-conversion model (calibrated) | Anomaly/bottleneck detection |
| Heavy engineering | CSV import, validation, synthetic data, KPI engine | LLM guardrails, scoring, plan generator, outcome ledger |
| Work | ~365 min, 8 tasks | ~370 min, 9 tasks |
| Part 1 due | 11:30 (M1) | 12:00 (M2) |
| Part 2 due | 1:30 (M3) | 2:00 (M4) |

Task lists: see the two module files above.

## 4. Shared pieces (local stubs, added to `main` on request)

| File | Purpose |
|---|---|
| `backend/common/fixtures.py` | `load_fixture(name)` for contract fixtures |
| `backend/common/errors.py` | error shape `{"error": {...}}` and `not_implemented()` |
| `backend/data_engine/public.py` | in-process interface used by `DATA_SOURCE=local` |
| `backend/decision_engine/clients/data_client.py` | `DataClient` with 3 sources |
| `backend/decision_engine/scoring.py` | priority equation + tests |
| `backend/gateway/main.py` | mounts both routers for integration |

Don't restructure these. If you need a change, follow `docs/WORKFLOW.md` section 3.

## 5. Integration plan (`backend-integration` branch)

Owners: Soham + Ayush. Target 2:00–2:45 PM.

1. `git checkout -b backend-integration origin/main && git merge origin/backend-1 && git merge origin/backend-2`
2. `DATA_SOURCE=local uvicorn backend.gateway.main:app --port 8000`
3. Walk through the whole loop at `http://localhost:8000/docs` in this order:
   `POST /demo/load` → `GET /data-quality` → `GET /kpis` → `GET /leads/queue` → `GET /signals` → `POST /recommendations/generate` → `POST /recommendations/{id}/approve` → `POST /plans` → `PATCH /tasks/{id}` → `POST /demo/load?phase=day7` → `POST /plans/{id}/outcomes/evaluate`
4. Compare each response with the fixture shape (the smoke tests encode part of this; add contract tests for what you change).
5. Run `python -m pytest backend -q`. Tag `backend-green` when it all passes.
6. Switch the DB-backed tables on: run `db/schema.sql` yourselves in Supabase beforehand (the repo never executes DDL for you).

**Known integration risks to check early:** timezone/date formats between modules; `fact_id` naming used in `evidence_ids`; the day-7 snapshot being picked up by `kpis` (`snapshot` parameter); LLM cache keys; CORS.

## 6. Definition of done (per module)

- All endpoints in your section of the contract return real, correct data (or a documented 501 for dropped should-haves).
- `pytest` passes for your folder, including at least one hand-calculated check for your core math.
- Model/metric numbers are recorded in a JSON file the research branch can read (`model_card` for backend-1, anomaly metrics for backend-2).
- Your PR description lists what is pre-existing vs built today.
