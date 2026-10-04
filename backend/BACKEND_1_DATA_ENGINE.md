# Backend 1: `data_engine` (Soham), Data and Intelligence

Branch: `backend-1`. You edit only `backend/data_engine/`. Port 8001. Overview of both backends: [`BACKEND.md`](BACKEND.md). The other backend (Ayush, `decision_engine`) is independent of yours: it reads your output only through the contract.

> **Status:** the contract in `contracts/API_CONTRACT.md` and the fixtures in `contracts/fixtures/` are the source of truth. The shared stubs (section 6 of `BACKEND.md`), `backend/requirements.txt` and `db/schema.sql` are on `main`.

**Stack:** Python, FastAPI, Pydantic, PostgreSQL/Supabase. **Runtime is pure Python (stdlib `csv`, `random`, `statistics`)**; pandas and scikit-learn are used only in offline training scripts so the API stays small enough for Vercel (see `BACKEND.md` sections 3 and 5). Industry: D2C with a hybrid bulk-inquiry segment.

**What you own:** onboarding → CSV import → mapping → validation and quarantine → canonical tables → KPI engine → lead-conversion model → lead queue.
**What you produce for others:** KPI facts, lead scores, data-quality report, business context (contract section 3). Ayush consumes them via `DataClient` (`DATA_SOURCE=fixture|http|local`).
**Tables you write:** `business, goal, product, campaign, lead, customer, orders, order_item, import_job, quarantine_row, kpi_snapshot, lead_score` (contract section 6). Never write Ayush's tables.

## Tasks

Endpoints: contract section 3.

| # | Task | Min | Part | Done when |
|---|---|---|---|---|
| 1 | DB connection and config; onboarding endpoints (`POST/GET /businesses`) persisting business, goal, constraints | 30 | 1 | context round-trips through the DB |
| 2 | **Synthetic D2C tenant "Aarohi Skin"**: deterministic (seeded) scripted scenario, about 180 days of leads, customers and orders across Instagram, Google, email, WhatsApp and website, 3 SKUs, payment mode (COD/prepaid) and order status. **Must reproduce the numbers listed in `contracts/fixtures/README.md`** (Instagram spend 36,720 / 60 new customers; Google 15,960 / 42; 8 unattended high-value leads; email repeat cohort 45/210) and the **day-7 follow-up week**. Plants the incidents on purpose: Instagram CAC spike from 2026-09-29, unattended bulk inquiries, improving email cohort, and a **messy orders CSV** | 60 | 1 | `POST /demo/load?phase=baseline\|day7` loads the data; invariants hold (listed below); same seed gives identical data |
| 3 | **CSV import**: upload, detect columns, suggest mapping, confirm; **validation and quality report**: duplicates (merge), missing campaign IDs (quarantine), mixed date formats (repair to ISO), currency/units; confidence score; "unattributed" kept as unattributed | 60 | 1 | the intentionally messy demo CSV yields a report matching `fixtures/data_quality.json` shape; quarantined rows are stored with reasons |
| 4 | **KPI registry and engine** (deterministic pure Python, never LLM): conversion rate, CAC, ROAS, contribution ROAS, gross margin, repeat rate, AOV, sales velocity, response latency p90, funnel stage rates. Each fact has numerator, denominator, definition version, baseline, delta | 60 | 2 | `GET /kpis` returns real facts that match hand-calculated values for 3 KPIs |
| 5 | **Lead-conversion model**: UCI Bank Marketing, **drop call duration** (not known pre-contact), chronological split, logistic-regression baseline + gradient-boosted challenger (HistGradientBoosting/LightGBM), calibration (isotonic/sigmoid on a separate fold), metrics: PR-AUC, ROC-AUC, Brier, lift@10%, calibration error. Save the model and a `model_card` JSON | 60 | 2 | metrics written to the model card; challenger only kept if it beats the baseline |
| 6 | **Lead queue serving**: score the demo leads using the same feature schema, rank by probability x expected value, top positive/negative factors (LR coefficients or SHAP), **abstain** when key fields are missing | 45 | 2 | `GET /leads/queue` returns ranked leads including at least one abstention |
| 7 | Public interface `data_engine/public.py` returns real data (replace the fixture bodies); keep signatures | 20 | 2 | `decision_engine` works with `DATA_SOURCE=local` unchanged |
| 8 | RFM segments and retention cohort (should-have), tests for KPI math and validation rules | 30 | 2 | `GET /segments/rfm` works; tests pass |

~365 min. If time runs short, drop task 8 first, then simplify the challenger model in task 5 (baseline LR is acceptable).

**Stage 1 (due 1:00 PM):** tasks 1–3. **Stage 2 (due 3:00 PM):** tasks 4–7. After each stage, report exactly what works and what is generated, precomputed or mocked.

**Build order inside the stages (stop and report after each):**
1. Stage 1a: generator, business context, `POST /demo/load`, real `public.get_context`.
2. Stage 1b: CSV import, mapping, validation, quarantine, quality report.
3. Stage 2a: KPI engine and `GET /kpis` (+ `/kpis/daily`, `/funnel`); `public.get_kpi_facts` and `get_kpi_series` become real.
4. Stage 2b: offline lead-model training, JSON artifact, lead queue and model card.

**Data rules (leakage and honesty):**
- Split by time, not random rows. Fit encoders and calibration inside training folds only. Tune thresholds on validation, not test.
- Never use post-outcome fields (final duration, closed date, final lost reason, future touches).
- Public datasets are used standalone. **Do not pretend UCI Bank Marketing and Online Retail II belong to the same company.** The relational demo company is the synthetic tenant.
- Label every synthetic row/response `synthetic: true`.
- **Sanity-check units and ranges** on every number before it leaves the module (a hand calculation for one KPI, a plot for one series).
- Synthetic invariants to test: qualified leads <= leads; wins do not precede opportunities; attributed revenue <= compatible order revenue; no future timestamps; referential integrity.

**Pre-existing components (list in your PR):** FastAPI, Pydantic; offline only: pandas, scikit-learn; UCI Bank Marketing dataset (check licence/citation terms before redistributing).

## Integration

On `backend-integration` (#1 at 1:00–1:30 PM, #2 at 3:00 PM, with Ayush) your branch is merged with `backend-2`; `data_engine/public.py` is the in-process interface `decision_engine` calls when `DATA_SOURCE=local`. Keep its function signatures stable: `get_context`, `get_kpi_facts`, `get_lead_scores`, `get_data_quality`, each returning the contract shape. See `BACKEND.md` section 9 and `docs/WORKFLOW.md`.


## Status (what is built, verified by tests)

| Stage | Built | Tests |
|---|---|---|
| 1a | Synthetic D2C tenant (deterministic), context, onboarding (`d2c`/`hybrid`/`b2c_retail`), demo load, data summary | anchors, invariants, determinism |
| 1b | CSV import: mapping suggestions, validation/repair/quarantine, quality report and badge; messy sample file | planted defects found exactly; cleaned rows reconstruct the originals |
| 2a | KPI engine: 23 facts for the baseline and day-7 snapshots, daily series, funnel, point-in-time rule | every current-week value equals the contract fixtures |
| 2b | Lead model trained on UCI Bank Marketing, lead queue, model card | runtime scorer reproduces the card's hold-out metrics; queue shape matches the contract |
| **Not built** | RFM segments (should-have), Postgres persistence of import jobs, Online Retail II | – |

## Lead model: decisions and measured results

Trained offline (`python -m backend.data_engine.ml.train_lead_model`; scikit-learn and numpy are needed only there). The runtime reads a small JSON artifact (`ml/artifacts/lead_model.json`) and is pure Python.

- **Data:** UCI Bank Marketing, used standalone (download with `python -m backend.data_engine.ml.fetch_datasets`; the file is git-ignored). `duration` is never used (leakage).
- **Shared feature schema (4 inputs):** previous outcome, prior contacts, days since last contact, contacts this campaign. Banking-specific fields have no meaning for a skincare lead.
- **Modeling window = 2009 onward.** 2008 (67% of the file) has almost no previous-campaign information (97% "nonexistent"), so including it hides the strongest predictor (a previous success converts at 65%). This was decided from data coverage, not from scores.
- **`month` excluded.** It cannot be separated from the campaign period in a two-year dataset; it is reported only as an ablation.
- **Evaluation:** the last 20% of the window (strictly the latest period) is untouched until the end. Model and calibrator selection use blocked time-contiguous cross-validation inside the first 80%; the calibrator is fitted on out-of-fold predictions.
- **Results on the hold-out** (n = 2,700, positive rate 51.2%): PR-AUC **0.680** vs 0.512 for the constant baseline, ROC-AUC 0.682, lift@10% 1.6. The gradient-boosting challenger scored 0.660, so the portable, explainable logistic regression ships.
- **Known limits (also on the model card):** the positive rate shifts from 17.8% (development) to 51.2% (hold-out), so calibration is weak (calibration error 0.29). **Use the probabilities to rank leads, not as absolute chances.** They are not calibrated to Aarohi Skin.
- **Explanations:** previous outcome, prior contacts and days since last contact are three views of one fact, so they are explained together as one "contact history" factor (the effect versus a lead with no previous contact).

## Additive API (backend-1), to be added to the contract on `main`

| Method | Path | Purpose |
|---|---|---|
| GET | `/businesses/{id}/data-summary` | counts per table, date range, current-week orders and revenue, "synthetic" flag (lets anyone check what is loaded) |
| POST | `/demo/load?phase=` | response is the business context plus an additive `demo_load` object (`phase`, `from`, `to`, `as_of`, `counts`, `seed`) |
| – | business context | additive fields `business_model` (`d2c`/`hybrid`/`b2c_retail`), `segments`, `data_phase` |
| POST | `/businesses/{id}/imports/auto?kind=` | upload + accept the suggested mapping in one call (demos, stateless hosting); returns the upload view plus the `report` |
| GET | `/imports/{id}/quarantine?limit=` | rows that were not loaded, with the reason |
| GET | `/demo/sample-import/orders.csv` | download the deliberately messy synthetic orders export |
| POST | `/demo/import-sample` | run that sample through the real import pipeline; returns mapping and report |
| POST | `/imports/{id}/confirm` | body is `{"mapping": {field: column}}` (a bare mapping object is also accepted) |
| GET | `/businesses/{id}/leads/queue?limit=&snapshot=` | `snapshot` defaults to the loaded demo phase; in-process `public.get_lead_scores` defaults to `baseline` |
| GET | `/businesses/{id}/kpis?snapshot=` | already in the contract; response wraps the facts as `{business_id, synthetic, snapshot, facts: [...]}` |

**Point-in-time rule (used by the KPI engine in Stage 2):** a snapshot only sees events that happened before its `as_of` time. The baseline snapshot (`as_of` 2026-10-04T04:30Z) must not see the follow-ups that happen in the day-7 replay, so the baseline week reads the same in both phases. Lead response latency for a lead that has not been answered yet is `as_of - created_at`.
