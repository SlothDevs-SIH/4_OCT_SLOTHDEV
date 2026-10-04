# Backend 2: `decision_engine` (Ayush), Decision and Action

Branch: `backend-2`. You edit only `backend/decision_engine/`. Port 8002. Overview of both backends: [`BACKEND.md`](BACKEND.md). The other backend (Soham, `data_engine`) is independent of yours: you read its output only through `DataClient`, and you build against the contract examples until it is ready.

> **Status:** the contract in `contracts/API_CONTRACT.md` is the source of truth. Prepared code stubs, example fixtures (`contracts/fixtures/`) and `db/schema.sql` exist locally and are added to `main` when the team asks. Until then, code against the shapes written in the contract.

**Stack:** Python, FastAPI, Pydantic, scikit-learn, jsonschema, an LLM API behind a provider interface, PostgreSQL/Supabase.

**What you own:** signals (bottleneck rules + anomaly) → eligibility gate → priority score → constrained LLM explanation and validator → approval → 7-day plan → tasks → outcome ledger.
**What you consume:** KPI facts, lead scores, data quality, context (contract section 3) via `DataClient`.
**Tables you write:** `context_snapshot, intervention_template, signal, recommendation, plan, task, outcome` (contract section 6). Never write Soham's tables.

## Tasks

Endpoints: contract section 4.

| # | Task | Min | Part | Done when |
|---|---|---|---|---|
| 1 | Config, `DataClient` check (`fixture`/`http`/`local`), intervention template loader (from `contracts/fixtures/intervention_templates.json`) | 30 | 1 | signals can be computed from `DataClient` output |
| 2 | **Signal detection**: bottleneck rules with the **four tests** (materiality, deviation, localization, actionability): high traffic/low leads, leads high/wins low, long response time vs SLA, high spend/low contribution, revenue up/margin down, first orders high/repeat low. Opportunity detectors: high-performing channel, repeat-purchase cohort, high-value leads | 45 | 1 | `GET /signals` produces the 4 signals in the fixture from the KPI facts |
| 3 | **Anomaly detection**: seasonal median/MAD robust z-score baseline; Isolation Forest as a challenger only if it beats it on the injected incidents. Report event-level precision/recall, false alerts/week, detection delay | 30 | 1 | detects the injected Instagram CAC spike; metrics recorded |
| 4 | **Eligibility/safety gate**: block actions that violate constraints (budget, weekly hours, forbidden actions such as "increase total ad spend"), need missing data, or are unsafe. Output a `blocked_reason` | 30 | 1 | "Increase Instagram ad spend" is `blocked` with a reason in the demo |
| 5 | **Priority scorer** (`scoring.py` is already implemented and tested; wire it to real inputs). Factors I,U,F,R,T from the template and signal; **Q from data quality + model calibration + rule strength**; E,C,D from the template and constraints | 30 | 1 | ranking order on demo data: hot-leads > email retention ~ Instagram test >> (increase spend blocked) |
| 6 | **LLM constrained synthesis**: provider interface (`LLM_PROVIDER`), evidence packet in, JSON-schema output, **validator** (unknown evidence IDs, numbers not in the packet, actions outside templates, constraint violations); retry once; deterministic fallback text; **local cache** so the demo works offline | 75 | 1/2 | invalid LLM output never reaches the API; `llm.cached` shows in the response |
| 7 | **7-day plan generator**: choose approved non-conflicting recommendations, topological sort of dependencies, fit daily capacity (8 h/week), assign owner, KPI, success criterion; tasks CRUD (`PATCH /tasks/{id}`); approval endpoints | 50 | 2 | plan matches the shape in `fixtures/plan.json`; hours <= capacity |
| 8 | **Outcome ledger**: freeze baseline, expected range, guardrails, confounders at approval; `POST /plans/{id}/outcomes/evaluate` compares the day-7 snapshot with baseline and expected; separate **fidelity** (was it executed?) from **effectiveness**; label results `observational` | 50 | 2 | the three outcomes (promising / inconclusive / inconclusive) are reproduced from the day-7 data |
| 9 | Should-have: grounded chat that cites `fact_id`s; WhatsApp/email **draft preview** (never auto-send); tests | 30 | 2 | answers cite real facts; drafts require approval |

~370 min. Drop task 9 first if time runs short, then the Isolation Forest challenger.

**Part 1 (needed by 12:00, M2):** tasks 1–6 produce `recommendations` end to end with a cached LLM response. **Part 2 (needed by 2:00, M4):** tasks 7–9.

**Rules for the LLM boundary (non-negotiable):**
- The LLM never calculates a KPI or assigns a probability. It explains facts it was given and instantiates tasks from approved templates.
- Every recommendation cites `evidence_ids` that exist. Reject anything else.
- Recommendations with weak data or no measurable KPI are marked low-confidence, not dressed up.
- Human approval is required for spend, customer outreach, and data-changing actions.
- Keys come from `.env`; never log or commit them.

**Pre-existing components (list in your PR):** FastAPI, scikit-learn, jsonschema, the chosen LLM provider SDK.

## Priority equation (implement exactly, test against a hand calculation)

```
Benefit     = 0.32*I + 0.18*U + 0.18*F + 0.17*R + 0.15*T
CostPenalty = 0.45*E + 0.30*C + 0.25*D
Priority    = 100 * Benefit * (0.5 + 0.5*Q) * (1 - 0.55*CostPenalty)
```
Example: I=.8 U=1 F=.9 R=.5 T=.9 Q=.85 E=.25 C=.05 D=.10 gives Benefit .818, CostPenalty .1525, Priority **69.3**. A hard eligibility gate runs first: blocked actions are never scored.

## Integration

On `backend-integration` (2:00–2:45 PM, with Soham) you switch `DATA_SOURCE=local` so you call `data_engine` in-process. See `BACKEND.md` section 5 and `docs/WORKFLOW.md`.
