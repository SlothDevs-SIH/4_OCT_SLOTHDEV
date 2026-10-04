# Backend: two independent modules, then integration

**Industry focus:** D2C (direct-to-consumer) brands in India, with a `hybrid` segment (D2C brand that also takes bulk/B2B inquiries). `b2c_retail` is a profile only (see section 2).
**Stack:** Python, FastAPI, Pydantic, PostgreSQL on Supabase, scikit-learn used **offline** for training, an LLM API behind a provider interface. Public hosting: Supabase + Vercel (section 5).
**Contract:** [`../contracts/API_CONTRACT.md`](../contracts/API_CONTRACT.md) and `../contracts/fixtures/`.
**Per-module task lists:** [`BACKEND_1_DATA_ENGINE.md`](BACKEND_1_DATA_ENGINE.md) (Soham) and [`BACKEND_2_DECISION_ENGINE.md`](BACKEND_2_DECISION_ENGINE.md) (Ayush).

> **Status:** the contract and the fixtures are the source of truth. The shared stubs (section 6), `backend/requirements.txt` and `db/schema.sql` are on `main`.

## 1. The backend in one picture

```
 ┌────────────────────────── data_engine (backend-1, Soham) ──────────────────────────┐
 │ synthetic D2C tenant → CSV import → mapping → validation/quarantine                 │
 │            → KPI engine → lead-conversion model (calibrated) → lead queue           │
 └──────────────────────────────────┬─────────────────────────────────────────────────┘
                                    │  KPI facts, lead scores, data quality, context
                                    │  (HTTP, or in-process via data_engine/public.py)
 ┌──────────────────────────────────▼─────────────────────────────────────────────────┐
 │ signals (bottleneck rules + anomaly) → eligibility gate → priority score            │
 │   → constrained LLM explanation + validator → approval → 7-day plan → tasks         │
 │   → outcome ledger (day-7 expected vs actual)        decision_engine (backend-2, Ayush) │
 └────────────────────────────────────────────────────────────────────────────────────┘
```

**Why this split is independent:** `decision_engine` reads `data_engine` only through `DataClient` (`DATA_SOURCE=fixture|http|local`). While `data_engine` is unfinished, Ayush works against the fixtures, which already contain a believable Aarohi Skin week and day-7 follow-up. Soham never depends on Ayush. Tables are split by owner (`db/schema.sql`), so there are no write conflicts.

**Why the work is equal:** each module is about 6 hours of bounded tasks, with one ML component each (lead conversion vs anomaly detection), one heavy engineering part each (import and validation vs LLM guardrails), and one data-producing vs data-consuming half.

## 2. Why D2C, and what that changes in the backend

The judges' advice was to stop being generic: a medical shop and a clothing shop have very different analytics. We chose **one model: D2C brands**.

**Why D2C fits a measurable, explainable prototype**
- The whole funnel is first-party and measurable: ad spend → sessions → leads → orders → repeat purchase.
- Customer acquisition cost is the number that makes or breaks a D2C brand, and it moves weekly, so "what should I fix first?" is a real question.
- Repeat purchase and contribution margin (after product cost, shipping and returns) decide profitability, so the recommendations have clear KPIs.
- India-specific levers are concrete: COD vs prepaid, returns/RTO (return to origin), WhatsApp follow-up, festive seasons, UPI.

**Business-model profiles** (`business_model` in the business context)

| Profile | What differs | Status |
|---|---|---|
| `d2c` | Channels: Instagram, Google, email, WhatsApp, website. KPIs: CAC, ROAS, contribution ROAS, AOV, repeat rate, margin | **Built** |
| `hybrid` | Same plus a bulk/B2B inquiry lead segment (salons, corporate gifting) with high expected value and slower response | **Built** (the demo leads) |
| `b2c_retail` | Marketplaces and physical stores: different channel set, no own-site funnel, KPI subset | Config only, if time allows |

**D2C KPIs** (deterministic): ad spend, CAC (per channel and blended), conversion rate, ROAS, contribution ROAS, AOV, gross margin, repeat rate (overall and by cohort), response latency p90, unattended high-value leads, lead wins, funnel stages. **Should-have if time allows:** COD share, return/RTO rate, LTV:CAC.

**D2C action library** (backend-2 / research): lead follow-up past SLA, repeat-buyer email flow, WhatsApp win-back, channel audit + bounded creative test, landing-page fix, **blocked** "increase ad spend" when the goal forbids it. More (abandoned-cart recovery, COD-to-prepaid nudge, RTO reduction, bundle/AOV offer) are added by research.

## 3. Technology choices and why

| Choice | Why this | What we did not choose, and why | Watch out |
|---|---|---|---|
| **Python + FastAPI** | One language for API and ML; automatic request validation and `/docs`; fast to build | Node/Express: would split us across two languages for ML; Django: heavier than needed | Keep handlers thin; logic lives in plain modules so it is testable |
| **Pydantic v2** | Typed contract between modules; rejects bad input at the edge | Hand-written dicts: silent shape drift between two people's code | Keep models in sync with `contracts/API_CONTRACT.md` |
| **PostgreSQL on Supabase** | Managed Postgres, free tier, public from day one, JSONB for flexible context, SQL editor for the schema | SQLite: not shared across serverless instances; MongoDB: our data is relational (leads, orders, customers, campaigns) | Use the **pooled connection string** from serverless; free-tier limits |
| **`psycopg` 3** | Direct, small, reliable Postgres driver | A heavy ORM: more setup, more cold-start time | Connections must be short-lived on serverless |
| **Pure-Python runtime for data_engine** (stdlib `csv`, `random`, `statistics`) | Small deploy size and fast cold start on Vercel; deterministic seeded generator; easy to unit-test | pandas at runtime: ~100 MB+ with numpy and risks serverless size/time limits | pandas and scikit-learn stay in **offline** scripts only |
| **scikit-learn, offline** | Trusted, quick on CPU, includes calibration | Deep learning: no data, no time, hard to explain; AutoML: opaque | Export the trained model as a small JSON artifact |
| **Logistic regression as the selected lead model** (gradient boosting as challenger) | Interpretable (each factor's contribution is exact), well-behaved probabilities after calibration, portable as coefficients so runtime needs no scikit-learn | Boosted trees as the default: harder to explain and to ship in a tiny runtime; kept only if clearly better | Report metrics honestly; the challenger is a comparison, not a claim |
| **Isotonic calibration on a separate fold** | Prioritisation uses the *probability*, so it must be trustworthy | Raw scores: look like probabilities but are not | Needs held-out data; report Brier score and calibration error |
| **Median/MAD robust z-score for anomalies** (Isolation Forest as challenger) | Simple, explainable, works on short daily series, no training | Complex detectors by default: do not beat a simple baseline on one injected incident | Judge on the injected incident: precision, recall, false alerts, detection delay |
| **Transparent priority equation** (not an ML ranker) | We have no outcome history to train on; a visible formula is explainable and defensible | A learned ranker: would be fiction with zero outcome data | Weights are a documented assumption, to be calibrated once outcomes exist |
| **Rules for eligibility and bottlenecks** | Constraints (budget, hours, "no ad spend increase") must be enforced exactly, not guessed | Letting the LLM decide: can violate constraints | Every blocked action must show its reason |
| **LLM behind a provider interface, JSON-schema output, validator, cache** | The LLM explains and drafts; it never computes. A validator stops invented numbers and evidence; the cache keeps the demo working offline | Agent frameworks (LangChain-style): opaque control flow, harder to validate; letting the LLM do arithmetic | Numbers in text may appear as 0.214 or 21.4%; the validator accepts both |
| **JSON fixtures as the contract** | Both backends and the frontend start immediately and agree on shapes; tests check the fixtures agree with each other | Waiting for the other side to finish | Don't change shapes after contract freeze; add optional fields only |
| **Next.js on Vercel** | One-click public hosting, previews per branch | Self-hosting: no time | Keep API calls through one base URL |
| **Not used:** microservices, Kafka, Celery, a vector database, a knowledge graph, real-time streaming | None of them is needed for a weekly decision loop, and each adds failure points | – | Revisit only after the prototype |

## 4. Prototype scope: what is real, precomputed or not built

Be exact about this when presenting.

| Capability | Status in the prototype |
|---|---|
| Synthetic D2C tenant "Aarohi Skin" | **Real code, synthetic data.** Deterministic (seeded) scripted scenario, always labelled `synthetic: true`. Planted incidents are by design |
| Demo load (baseline and day-7) | **Real**: loads the generated data into the in-process store |
| CSV import, mapping, validation, quarantine, quality report | **Real** (stdlib `csv`) on uploaded files; the demo uses a prepared messy orders file |
| KPI engine | **Real computation** over generated rows; each fact has numerator, denominator, definition version |
| Lead-conversion model | **Trained offline** on UCI Bank Marketing (call duration removed, time-based split); small JSON artifact committed; **scoring is real at runtime**; metrics are measured offline. Applied to demo leads through a shared feature schema: it proves the method, not Aarohi-specific accuracy |
| Signals and anomaly detection | **Real rules and statistics** over the KPI series |
| Priority score and eligibility gate | **Real**, deterministic |
| LLM explanation | Real call when a key is set; **cached responses** for the demo; deterministic fallback text |
| 7-day plan, tasks | **Real logic** (dependency order, capacity check) |
| Day-7 outcomes | **Real comparison** against a **scripted synthetic follow-up week**. Results are scenarios, labelled observational, never real-world impact |
| Persistence | In-process store for the demo; Supabase tables for imports, approvals, tasks and outcomes where wired (state on serverless must not live in memory) |
| **Not built** | Live Shopify/Zoho/WhatsApp integrations, sending messages, authentication and multi-tenant isolation, GST/UPI adapters, forecasting, learning from outcomes |

## 5. Hosting: Supabase + Vercel (public, not local)

| Part | Where | How |
|---|---|---|
| Database | **Supabase** | Create a project. Run `db/schema.sql` yourself in the Supabase SQL editor (the AI tooling does not run DDL or data changes on a database). Copy the **pooled (transaction) connection string** into `DATABASE_URL` |
| Frontend | **Vercel** project `web` | Root directory `frontend/app`; env `NEXT_PUBLIC_API_BASE` = the API URL |
| API | **Vercel** project `api` (serverless FastAPI) | `api/index.py` exposes the gateway app; env `DATABASE_URL`, `LLM_*`, `DATA_SOURCE=local` |

Because serverless functions have size and time limits (check the current limits in Vercel's docs), the API must stay **light at runtime**:
- Runtime dependencies are the slim set in `requirements.txt` at the repo root for Vercel (FastAPI, Pydantic, httpx, psycopg). **No pandas, scikit-learn or SHAP at runtime.** Training scripts use `backend/requirements.txt`.
- The lead model ships as a JSON artifact (coefficients + calibration table).
- LLM calls are cached; set a timeout and fall back to the deterministic text.
- State (approvals, tasks, outcomes, import reports) goes to Supabase, not memory.

**Decision point (by 2:30 PM, first public deploy):** if serverless Python gives trouble, keep Vercel for the frontend and run the same API as a free web service on another host (for example Render). The code does not change.

Config files to add at deploy time: `vercel.json`, `api/index.py`, root `requirements.txt`, `frontend/app/.env.local` template.

## 6. Shared pieces (on `main`)

| File | Purpose |
|---|---|
| `backend/common/fixtures.py` | `load_fixture(name)` for contract fixtures |
| `backend/common/errors.py` | error shape `{"error": {...}}` and `not_implemented()` |
| `backend/data_engine/public.py` | in-process interface used by `DATA_SOURCE=local` |
| `backend/decision_engine/clients/data_client.py` | `DataClient` with 3 sources |
| `backend/gateway/main.py` | mounts both routers (each module's `main.py` exposes `router` with prefix `/api/v1`) |
| `db/schema.sql` | Postgres schema, run manually |

Don't restructure these. Changes follow `docs/WORKFLOW.md` section 3.

## 7. The two modules at a glance

| | Backend 1: `data_engine` | Backend 2: `decision_engine` |
|---|---|---|
| Owner / branch | Soham / `backend-1` | Ayush / `backend-2` |
| Folder / port | `backend/data_engine/` / 8001 | `backend/decision_engine/` / 8002 |
| Role | Produces data and ML signals | Turns signals into decisions and actions |
| ML component | Lead-conversion model (calibrated) | Anomaly/bottleneck detection |
| Heavy engineering | Synthetic data, CSV import and validation, KPI engine | LLM guardrails, scoring, plan generator, outcome ledger |
| **Stage 1** (due 1:00 PM) | Generator + onboarding + demo load + import/quality | Signals + gate + scorer + recommendations (cached LLM) |
| **Stage 2** (due 3:00 PM) | KPI engine + lead model + lead queue | Plan + tasks + outcome ledger |

## 8. Running (from the repo root)

```bash
pip install -r backend/requirements.txt          # development and training
uvicorn backend.data_engine.main:app --port 8001 --reload
uvicorn backend.decision_engine.main:app --port 8002 --reload
DATA_SOURCE=local uvicorn backend.gateway.main:app --port 8000 --reload
python -m pytest backend -q
```

## 9. Integration (twice)

Owners: Soham + Ayush. **#1 at 1:00–1:30 PM** (Stage 1 from both), **#2 at 3:00 PM** (Stage 2).

1. `git checkout -b backend-integration origin/main && git merge origin/backend-1 && git merge origin/backend-2`
2. `DATA_SOURCE=local uvicorn backend.gateway.main:app --port 8000`
3. Walk through the loop at `http://localhost:8000/docs`: `POST /demo/load` → `GET /data-quality` → `GET /kpis` → `GET /leads/queue` → `GET /signals` → `POST /recommendations/generate` → `POST /recommendations/{id}/approve` → `POST /plans` → `PATCH /tasks/{id}` → `POST /demo/load?phase=day7` → `POST /plans/{id}/outcomes/evaluate`
4. Compare each response with the fixture shape; add contract tests for what you change.
5. `python -m pytest backend -q`. Tag `backend-green-1` / `backend-green-2` when green.

**Risks to check early:** date/time formats between modules; `fact_id` names used in `evidence_ids`; the day-7 snapshot via the `snapshot` parameter; LLM cache keys; CORS; serverless cold start and timeouts.

## 10. Definition of done (per module)

- Every endpoint in your section returns real, correct data (or a documented 501 for a dropped should-have).
- `pytest` passes for your folder, with at least one hand-calculated check for your core math.
- Model/metric numbers are written to a JSON file that research can read.
- After each stage you can say exactly what is real, precomputed or mocked.
- Your PR description lists what is pre-existing vs built today.
