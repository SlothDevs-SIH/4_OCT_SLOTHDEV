# Contract fixtures (Aarohi Skin, synthetic)

Example payloads for every shape in `../API_CONTRACT.md`. `decision_engine` reads them through `DataClient` with `DATA_SOURCE=fixture`; the frontend copies them into its mocks. Everything here is **synthetic** demo data.

`backend/decision_engine/tests/test_fixtures.py` checks that the files agree with each other (fact arithmetic, evidence IDs, priority equation, plan capacity, outcome ranges). Run `python -m pytest backend -q` after editing any file here.

## Files

| File | Owner (produces the real data) | Shape |
|---|---|---|
| `business_context.json` | backend-1 | profile, goal, constraints (budget, forbidden actions, lead SLA), capacity per owner, demo periods |
| `kpi_facts.json` | backend-1 | KPI facts for the baseline week 2026-09-27..2026-10-03; `baseline` = trailing 4 weeks |
| `kpi_facts_day7.json` | backend-1 | the same `fact_id`s for the day-7 follow-up week 2026-10-05..2026-10-11 |
| `kpi_daily.json` | backend-1 | daily Instagram/Google series 2026-08-09..2026-10-03 plus the injected-incident ground truth |
| `lead_scores.json` | backend-1 | ranked leads (8 unattended high-value, 1 abstention) and `model_card` (**placeholder metrics**) |
| `data_quality.json` | backend-1 | overall confidence badge, per-KPI quality, import report for the messy orders CSV |
| `intervention_templates.json` | backend-2 / research | seed action library with factor defaults (I, F, R, T, E, C, D) |
| `signals.json` | backend-2 | the 4 demo signals (2 bottlenecks, 1 anomaly, 1 opportunity) |
| `recommendations.json` | backend-2 | 3 scored recommendations + 1 blocked (increase ad spend) |
| `plan.json` | backend-2 | 7-day plan, 435 of 480 minutes, at most 120 minutes per day |
| `outcomes.json` | backend-2 | day-7 results: promising / inconclusive / inconclusive |

## Additions beyond the current contract text

These were needed by backend-2 tasks 3 and 8. All are optional additions; nothing existing was renamed.

1. **`snapshot` field on KPI facts** (`"baseline"` or `"day7"`), and a `snapshot` query parameter on `GET /businesses/{id}/kpis` (`data_engine.public.get_kpi_facts(..., snapshot=)`). The day-7 facts reuse the baseline `fact_id`s, so the snapshot tells them apart.
2. **Daily series** for anomaly detection: `GET /businesses/{id}/kpis/daily?from=&to=&channel=` and `data_engine.public.get_kpi_series(business_id, from_date, to_date, channel)`, returning the `kpi_daily.json` shape.

## For backend-1: numbers to reproduce

The demo story depends on these, so the synthetic generator should hit them for the baseline week:

- Instagram: spend 36,720, 60 new customers (CAC 612 vs 410 baseline), 4,000 sessions, revenue 50,940; CAC spike injected from 2026-09-29.
- Google: spend 15,960, 42 new customers (CAC 380 vs 372), stable (false-alert control).
- 8 unattended high-value leads (expected value ≥ INR 15,000), p90 response 38.5 h vs a 4 h SLA; `lead_0412` and `lead_0388` rank first; `lead_0455` abstains.
- Email cohort repeat rate 45/210 = 0.214 vs 0.162.
- Contribution ROAS uses a 50% contribution margin with estimated shipping, so it is flagged `partial`.

**`fact_id`s that recommendations cite** (keep these names): `f_cac_instagram`, `f_conv_instagram`, `f_croas_instagram`, `f_spend_instagram`, `f_cac_google`, `f_latency_hot_leads`, `f_unattended_hot_leads`, `f_hot_lead_wins`, `f_repeat_email`, `f_repeat_rate`.

Numbers in recommendation text appear in the facts either as-is or as a percentage (0.214 → 21.4%), so the LLM validator must accept both forms.
