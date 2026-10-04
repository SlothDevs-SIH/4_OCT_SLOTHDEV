# Backend 1: `data_engine` (Soham), Data and Intelligence

Branch: `backend-1`. You edit only `backend/data_engine/`. Port 8001. Overview of both backends: [`BACKEND.md`](BACKEND.md). The other backend (Ayush, `decision_engine`) is independent of yours: it reads your output only through the contract.

> **Status:** the contract in `contracts/API_CONTRACT.md` and the fixtures in `contracts/fixtures/` are the source of truth. The shared stubs (section 4 of `BACKEND.md`), `backend/requirements.txt` and `db/schema.sql` are on `main`.

**Stack:** Python, FastAPI, Pydantic, pandas, scikit-learn (+ SHAP), PostgreSQL/Supabase.

**What you own:** onboarding → CSV import → mapping → validation and quarantine → canonical tables → KPI engine → lead-conversion model → lead queue.
**What you produce for others:** KPI facts, lead scores, data-quality report, business context (contract section 3). Ayush consumes them via `DataClient` (`DATA_SOURCE=fixture|http|local`).
**Tables you write:** `business, goal, product, campaign, lead, customer, orders, order_item, import_job, quarantine_row, kpi_snapshot, lead_score` (contract section 6). Never write Ayush's tables.

## Tasks

Endpoints: contract section 3.

| # | Task | Min | Part | Done when |
|---|---|---|---|---|
| 1 | DB connection and config; onboarding endpoints (`POST/GET /businesses`) persisting business, goal, constraints | 30 | 1 | context round-trips through the DB |
| 2 | **Synthetic demo tenant "Aarohi Skin"** generator: 180 daily periods, 18 campaigns, 4,000 leads, 1,500 customers, 3,200 orders, 3 SKUs; injected incidents (Instagram CAC spike, 8 unattended high-value leads, improving email repeat cohort); **day-7 snapshot** for the outcome replay. Use a causal skeleton, not independent random columns | 60 | 1 | `POST /demo/load?phase=baseline\|day7` fills the tables; invariants hold (see below). **Critical path: do this first.** |
| 3 | **CSV import**: upload, detect columns, suggest mapping, confirm; **validation and quality report**: duplicates (merge), missing campaign IDs (quarantine), mixed date formats (repair to ISO), currency/units; confidence score; "unattributed" kept as unattributed | 60 | 1 | the intentionally messy demo CSV yields a report matching `fixtures/data_quality.json` shape; quarantined rows are stored with reasons |
| 4 | **KPI registry and engine** (deterministic SQL/pandas, never LLM): conversion rate, CAC, ROAS, contribution ROAS, gross margin, repeat rate, AOV, sales velocity, response latency p90, funnel stage rates. Each fact has numerator, denominator, definition version, baseline, delta | 60 | 2 | `GET /kpis` returns real facts that match hand-calculated values for 3 KPIs |
| 5 | **Lead-conversion model**: UCI Bank Marketing, **drop call duration** (not known pre-contact), chronological split, logistic-regression baseline + gradient-boosted challenger (HistGradientBoosting/LightGBM), calibration (isotonic/sigmoid on a separate fold), metrics: PR-AUC, ROC-AUC, Brier, lift@10%, calibration error. Save the model and a `model_card` JSON | 60 | 2 | metrics written to the model card; challenger only kept if it beats the baseline |
| 6 | **Lead queue serving**: score the demo leads using the same feature schema, rank by probability x expected value, top positive/negative factors (LR coefficients or SHAP), **abstain** when key fields are missing | 45 | 2 | `GET /leads/queue` returns ranked leads including at least one abstention |
| 7 | Public interface `data_engine/public.py` returns real data (replace the fixture bodies); keep signatures | 20 | 2 | `decision_engine` works with `DATA_SOURCE=local` unchanged |
| 8 | RFM segments and retention cohort (should-have), tests for KPI math and validation rules | 30 | 2 | `GET /segments/rfm` works; tests pass |

~365 min. If time runs short, drop task 8 first, then simplify the challenger model in task 5 (baseline LR is acceptable).

**Part 1 (needed by 11:30, milestone M1):** tasks 1–3. **Part 2 (needed by 1:30, M3):** tasks 4–7.

**Data rules (leakage and honesty):**
- Split by time, not random rows. Fit encoders and calibration inside training folds only. Tune thresholds on validation, not test.
- Never use post-outcome fields (final duration, closed date, final lost reason, future touches).
- Public datasets are used standalone. **Do not pretend UCI Bank Marketing and Online Retail II belong to the same company.** The relational demo company is the synthetic tenant.
- Label every synthetic row/response `synthetic: true`.
- **Sanity-check units and ranges** on every number before it leaves the module (a hand calculation for one KPI, a plot for one series).
- Synthetic invariants to test: qualified leads <= leads; wins do not precede opportunities; attributed revenue <= compatible order revenue; no future timestamps; referential integrity.

**Pre-existing components (list in your PR):** pandas, scikit-learn, SHAP, FastAPI; UCI Bank Marketing dataset (check licence/citation terms before redistributing).

## Integration

On `backend-integration` (2:00–2:45 PM, with Ayush) your branch is merged with `backend-2`; `data_engine/public.py` is the in-process interface `decision_engine` calls when `DATA_SOURCE=local`. Keep its function signatures stable: `get_context`, `get_kpi_facts`, `get_lead_scores`, `get_data_quality`, each returning the contract shape. See `BACKEND.md` section 5 and `docs/WORKFLOW.md`.
