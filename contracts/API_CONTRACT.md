# API and Data Contract

The single source of truth that `backend-1`, `backend-2`, `frontend` and `research` all code against.
Example payloads (`fixtures/`) and endpoint stubs are prepared and will be added to `main` on request. Until then, the shapes below are the contract.

Change rules: see `docs/WORKFLOW.md` section 3. Changes happen on `main` only.

## 1. Conventions

- Base path: `/api/v1`. JSON in, JSON out. Errors: `{"error": {"code": "string", "message": "string"}}` with the right HTTP status.
- IDs are strings. The demo business is `biz_aarohi_skin`.
- Timestamps: ISO 8601 UTC (`2026-10-04T10:30:00Z`). Dates: `YYYY-MM-DD`. Currency: INR (amounts are numbers, not strings).
- **Synthetic data is labelled.** Every business, import and demo payload has `"synthetic": true` where relevant. The UI shows a "demo data" badge.
- **Every number is a fact with provenance** (section 2.1). The LLM never computes a number; it only explains facts it was given.
- Every recommendation carries `evidence_ids` that point to `fact_id`, `lead_id` or `signal_id` values that exist.
- **Ports in dev:** `data_engine` 8001, `decision_engine` 8002, `gateway` 8000 (both merged). The frontend uses one base URL (`NEXT_PUBLIC_API_BASE`). Until the gateway exists, use the Next.js rewrite proxy described in `frontend/FRONTEND.md`.

## 2. Core shapes

### 2.1 KPI fact (`fixtures/kpi_facts.json`)
```json
{
  "fact_id": "f_cac_instagram",
  "kpi": "cac",
  "dimension": {"channel": "instagram"},
  "period": {"from": "2026-09-27", "to": "2026-10-03"},
  "value": 612.0, "unit": "INR",
  "baseline": 410.0, "delta_pct": 49.3,
  "numerator": 36720.0, "denominator": 60,
  "definition_version": "v1",
  "quality_flag": "ok"
}
```
`quality_flag`: `ok | partial | low`. `numerator`/`denominator` are null where not applicable.

### 2.2 Lead score (`fixtures/lead_scores.json`)
`probability` is calibrated. `baseline` is portfolio prevalence. `abstain: true` means data is too incomplete to score (UI shows "needs data", not a number). `factors` have signed `contribution` (positive raises probability).

### 2.3 Signal (`fixtures/signals.json`)
`type`: `bottleneck | opportunity | anomaly`. Includes the four bottleneck tests (`materiality`, `deviation`, `localization`, `actionability`) as booleans plus `evidence_ids`.

### 2.4 Recommendation (`fixtures/recommendations.json`)
Includes the factor inputs (`I,U,F,R,T,Q,E,C,D` in 0–1), the computed `priority`, `status` (`proposed | approved | rejected | blocked`), `blocked_reason` if blocked, `evidence_ids`, `expected` (KPI, direction, range), `confidence`, `assumptions`, and `llm` (`{"used": true, "cached": true}`).

**Priority equation** (implemented in `decision_engine`, shown in the UI):
```
Benefit     = 0.32*I + 0.18*U + 0.18*F + 0.17*R + 0.15*T
CostPenalty = 0.45*E + 0.30*C + 0.25*D
Priority    = 100 * Benefit * (0.5 + 0.5*Q) * (1 - 0.55*CostPenalty)
```
A hard eligibility gate comes first: actions that violate a constraint (budget, capacity, "no spend increase"), are unsafe, or have insufficient data are `blocked` regardless of score.

### 2.5 Plan and tasks (`fixtures/plan.json`)
7 days. Each task: `task_id`, `day`, `title`, `reason`, `effort_min`, `owner`, `kpi`, `success_criterion`, `depends_on[]`, `status` (`todo | doing | done`), `recommendation_id`.

### 2.6 Outcome (`fixtures/outcomes.json`)
Per recommendation: `baseline`, `expected` (low/high), `actual`, `fidelity` (was it executed?), `effectiveness` (`promising | inconclusive | not_effective`), `observational: true` (we don't claim causality without a control).

## 3. Endpoints owned by `data_engine` (backend-1, Soham)

| Method | Path | Purpose | Fixture |
|---|---|---|---|
| GET | `/data/health` | liveness | – |
| POST | `/businesses` | onboarding: profile, goal, constraints, capacity | `business_context.json` |
| GET | `/businesses/{id}` | read context | `business_context.json` |
| POST | `/demo/load?phase=baseline\|day7` | load the synthetic Aarohi Skin tenant (baseline week, or day-7 follow-up snapshot) | `business_context.json` |
| POST | `/businesses/{id}/imports` | upload a CSV (`kind`: `campaigns\|leads\|orders`), returns `import_id`, detected columns and a **suggested mapping** | – |
| POST | `/imports/{import_id}/confirm` | confirm or edit mapping, runs validation and load | – |
| GET | `/imports/{import_id}/report` | quality report: rows loaded, repaired, quarantined, reasons | `data_quality.json` |
| GET | `/businesses/{id}/data-quality` | overall data confidence badge | `data_quality.json` |
| GET | `/businesses/{id}/kpis?from=&to=` | list of KPI facts | `kpi_facts.json` |
| GET | `/businesses/{id}/funnel` | stage counts and drop rates | in `kpi_facts.json` (`kpi: funnel_*`) |
| GET | `/businesses/{id}/segments/rfm` | RFM segments (should-have) | – |
| GET | `/businesses/{id}/leads/queue?limit=` | ranked leads with probability, factors, abstention | `lead_scores.json` |
| GET | `/models/lead-conversion/card` | metrics (PR-AUC, Brier, lift@10%), data used, caveats | in `lead_scores.json` (`model_card`) |

**In-process interface** (used by `decision_engine` when `DATA_SOURCE=local`), in `backend/data_engine/public.py`:
`get_context(business_id)`, `get_kpi_facts(business_id, from_date, to_date)`, `get_lead_scores(business_id, limit)`, `get_data_quality(business_id)`. Each returns exactly the fixture shape.

## 4. Endpoints owned by `decision_engine` (backend-2, Ayush)

| Method | Path | Purpose | Fixture |
|---|---|---|---|
| GET | `/decision/health` | liveness | – |
| GET | `/businesses/{id}/signals` | bottlenecks, opportunities, anomalies | `signals.json` |
| POST | `/businesses/{id}/recommendations/generate` | run the full pipeline (signals → eligibility → priority → LLM explanation) | `recommendations.json` |
| GET | `/businesses/{id}/recommendations` | ranked list incl. blocked | `recommendations.json` |
| GET | `/recommendations/{id}` | one recommendation with factor breakdown | `recommendations.json` |
| POST | `/recommendations/{id}/approve` and `/reject` | human approval (required for spend, outreach, data changes) | – |
| GET | `/recommendations/{id}/draft?channel=whatsapp\|email` | message draft **preview** (never auto-sent) | – |
| POST | `/businesses/{id}/plans` | build the 7-day plan from approved recommendations | `plan.json` |
| GET | `/plans/{id}` | read the plan with tasks | `plan.json` |
| PATCH | `/tasks/{id}` | update task status | – |
| POST | `/plans/{id}/outcomes/evaluate` | compare day-7 snapshot with baseline and expected | `outcomes.json` |
| GET | `/plans/{id}/outcomes` | read evaluated outcomes | `outcomes.json` |
| GET | `/intervention-templates` | the approved action library | `intervention_templates.json` |
| POST | `/businesses/{id}/chat` | grounded Q&A, answers cite `fact_id`s (should-have) | – |

**How `decision_engine` gets data:** through `DataClient` (`decision_engine/clients/data_client.py`), with `DATA_SOURCE` = `fixture` (reads `contracts/fixtures/`), `http` (calls `DATA_ENGINE_URL`) or `local` (imports `data_engine.public`). This is what lets backend-1 and backend-2 be built in parallel.

## 5. LLM boundary (decision_engine)

The LLM receives an **evidence packet** (business context + the facts/signals/lead scores it may use + allowed intervention templates) and must return JSON that validates against the recommendation schema. A validator rejects output that (a) cites an unknown `evidence_id`, (b) contains a number not present in the packet, (c) proposes an action outside the allowed templates, or (d) breaks a constraint. On failure: retry once, then fall back to the deterministic template text. A local cache keeps the demo working with no network.

## 6. Tables per owner (see `db/schema.sql`)

| Owner | Tables |
|---|---|
| `data_engine` | `business`, `goal`, `product`, `campaign`, `lead`, `customer`, `orders`, `order_item`, `import_job`, `quarantine_row`, `kpi_snapshot`, `lead_score` |
| `decision_engine` | `context_snapshot`, `intervention_template`, `signal`, `recommendation`, `plan`, `task`, `outcome` |

The two modules never write to each other's tables. They only exchange data through the endpoints/interfaces above.
