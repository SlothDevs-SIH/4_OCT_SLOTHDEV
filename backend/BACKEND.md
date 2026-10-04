# Backend: intake, measurement and advice in two independent modules

**Product: Catalyst AI.** A free advisor for **home-business owners**: people who make or sell something (shirts, candles, baked goods, jewellery, anything), take orders through Instagram or WhatsApp, have no ad budget, and run the business alone or with one or two others. It gives them analytics to **focus on next month's sales**.
**First case study:** Box Box, an F1 merchandise seller run by a final-year student. It is the demo, not the scope: every metric and rule works for any product.
**The loop:** intake (messy data plus a short interview) → diagnosis (the one biggest bottleneck) → advice (1 to 3 actions this week, each with evidence, plus a daily list of leads to answer) → weekly follow-up (what was done, what changed, adjust).
**Main measure:** **orders from strangers**, not from friends. **The product is free for everyone.**
**Datasets:** [`../docs/DATASET.md`](../docs/DATASET.md). **Contract (v2 draft):** [`../contracts/API_CONTRACT.md`](../contracts/API_CONTRACT.md).
**Module docs:** [`BACKEND_1_DATA_ENGINE.md`](BACKEND_1_DATA_ENGINE.md) (Soham) and [`BACKEND_2_DECISION_ENGINE.md`](BACKEND_2_DECISION_ENGINE.md) (Ayush).

## 1. The backend in one picture

```
 ┌─────────── data_engine (backend 1, Soham): INTAKE + MEASUREMENT + LEAD SCORING ───────────┐
 │ orders · costs · Instagram insights · pasted chats · interview answers                     │
 │   → validate, repair, quarantine → one profile (value + source + confidence)                │
 │   → facts for the five bottlenecks + "orders from strangers" → weekly snapshots             │
 │   → lead records: AI reads intent → points → Hot / Warm / Cold / Disqualified              │
 │   → next-month projection · market context (event calendars) · public-data validation     │
 └────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                          │ facts, lead scores, projection, context
 ┌────────────────────────────────────────▼─────────────────────────────────────────────────┐
 │ decision_engine (backend 2, Ayush): DIAGNOSIS + ADVICE + FOLLOW-UP                         │
 │   rank reach / conversion / margin / repeat orders / capacity → name ONE bottleneck        │
 │   → 1 to 3 weekly actions from a library, filtered by the owner's constraints              │
 │   → daily lead list with drafted replies (Hot / Warm / Cold) · reach-partner suggestions  │
 │   → LLM explanation that may only use numbers the engine produced                         │
 │   → weekly follow-up: what was done, what changed, adjust next week                        │
 └────────────────────────────────────────────────────────────────────────────────────────────┘
```

**The AI does not decide what is wrong. The calculations do.** An LLM has exactly two jobs: **read messy input** (a DM, a comment, an interview answer) and label its intent, and **explain** the result in plain language using only numbers the engine produced. If a number is missing, the finding is not shown.

## 2. Who it is for, and what that means for the engineering

Target user (working definition, adjusted after founder interviews): a maker-seller with their first 50 to 500 orders, selling mainly through Instagram or WhatsApp, with no ad budget, run by one to three people. **Not for:** venture-backed startups, mid-size companies, or established brands with a store, an ad budget and an agency.

- **Any product.** Orders carry a free-form product name and category. Nothing in the engine is specific to one product type.
- **No ad data.** Reach, not ad attribution, is the problem. CAC and ROAS do not apply.
- **Messy data is the norm.** Orders live in DMs, UPI apps and a sheet. The prototype takes **pasted text and CSV**; reading screenshots is not built.
- **Tiny volumes.** Every fact carries a sample size and a confidence label; thin data produces "estimate", never a verdict.
- **The data decides.** Reach is the likely bottleneck for Box Box, but the engine computes all five and lets the numbers choose.
- **Advice must be specific.** A chatbot is the real competitor. Our difference is advice tied to the owner's own numbers, with the evidence shown, and a weekly follow-up.

## 3. The five bottlenecks and the facts that show them

| Bottleneck | Meaning | Facts the engine computes |
|---|---|---|
| **Reach** | Too few new people see the brand | Orders by source (friend / friend of friend / stranger); **stranger orders per week**; Instagram reach per post |
| **Conversion** | People see it but do not buy | Profile visits and follows per post vs orders; orders per 1,000 reached; lead-to-order rate |
| **Margin** | Each order earns too little to fund growth | Price minus full unit cost; margin per order and in % |
| **Repeat orders** | Buyers do not come back | Share of customers with a second order; days between orders |
| **Capacity** | Cannot make or ship more | Dispatch delay, stock-outs, orders turned away, orders per week vs the stated limit |

Every fact keeps the contract shape (`fact_id, kpi, dimension, period, value, unit, baseline, delta_pct, numerator, denominator, definition_version, quality_flag, snapshot`) and gains `source` (`exact` | `estimate` | `derived`) and `sample_size`. Snapshots are weekly. The **baseline for the first target is the business's own best weeks**; typical figures per business type are added later and need a source.

## 4. Lead qualification and next month's sales

- **Lead scoring (backend 1)** follows the team document `Lead_Qualification_Model.docx` (shared outside the repo): any person who showed interest is a lead; an LLM labels each message's intent; transparent points per signal; Hot / Warm / Cold / Disqualified; strangers rank above friends at the same score; weekly learning from outcomes. A logistic regression trained on public contact-history data is the **learned challenger and sanity check**, not the first version. Details: `BACKEND_1_DATA_ENGINE.md`.
- **From scores to actions (backend 2):** Hot means reply today with a drafted reply; Warm means one targeted message when there is a reason; Cold means nothing one to one; Disqualified means a polite single reply, counted as unmet demand. The advisor drafts, the owner sends.
- **Next month's sales (backend 1 computes, backend 2 explains):** a simple, transparent projection of next month's orders with a range, from the recent weekly trend and the market-context calendar. It is clearly labelled an **estimate**. No machine-learning forecast.

## 5. Data strategy

Three kinds of data, each labelled: **public datasets** (validate the engine and calibrate how generated data behaves), **generated demo businesses** (Box Box and a home baker, `synthetic: true`), and **the owner's own data** (`real`). Full detail, licences, measured numbers and limits: [`../docs/DATASET.md`](../docs/DATASET.md).

## 6. What is kept, adapted or retired from earlier work

| Piece | Decision |
|---|---|
| CSV import with column detection, repair, quarantine and quality badge | **Keep and extend** (orders, costs, insights; add a customer-source field) |
| Point-in-time snapshots | **Keep** (the weekly follow-up: week 1 never sees week 2) |
| Fact shape, evidence ids, data client (`fixture`, `http`, `local`) | **Keep** |
| Order metrics (repeat share, days between orders, concentration) | **Keep** (built once, reused on every order list) |
| Eligibility gate, LLM boundary (evidence packet, validator, cache, fallback) | **Keep**, with new rules (no paid ads, owner hours, brand risk) |
| Outcome ledger, planner | **Adapt** into the weekly follow-up and "1 to 3 actions" |
| Public-data modules (Olist, Online Retail II, Online Shoppers, F1 context) | **Keep** |
| Bank Marketing model | **Keep as the lead-score challenger** (4 contact-history inputs) |
| Earlier D2C tenant "Aarohi Skin", ad-spend facts, ad-channel anomaly detection | **Legacy**: code stays until replaced by the new engine, then is removed |

## 7. Technology choices and why

| Choice | Why | Not chosen |
|---|---|---|
| Python, FastAPI, Pydantic | One language for API and analysis; typed contracts between two people's modules | Node: splits the team across languages |
| Pure-Python runtime (stdlib `csv`, `statistics`) | Small deploy and fast cold start on serverless hosting; deterministic, easy to test | pandas at runtime (offline scripts only) |
| Deterministic metrics decide, no ML as decision-maker | The product rule; with 50 to 500 orders there is too little data for a trained predictor, and a visible formula can be shown to the owner | A learned ranker: fiction at this volume |
| LLM for messy intake, intent labels and explanation | The only places that need language understanding | LLM diagnosis or arithmetic |
| Evidence validator and cache | The LLM may only cite facts it was given; the cache keeps the demo working offline | Trusting raw LLM output |
| Transparent lead points first, learned model later | Few leads per seller; the owner must see why a lead is ranked where it is | A black-box score |
| PostgreSQL on Supabase | Managed, free tier, JSON for a profile whose shape varies | SQLite (not shared across serverless instances) |
| Vercel (frontend and API) | A mobile-first web app from a link, no install | A native app: slower to build, needs installing |

## 8. Prototype scope: real, precomputed, or not built

| Capability | Status |
|---|---|
| Intake of orders, costs and Instagram insights (CSV) with repair and quarantine | **Real** (existing pipeline, extended) |
| Customer-source tagging | **Real**, from a column or the interview |
| Profile with source and confidence on every field | **Real** |
| Metrics for the five bottlenecks and the stranger-order measure; weekly snapshots | **Real computation** |
| Lead intent labelling (LLM) and the points score | Real call when a key is set; **cached** for the demo; deterministic fallback |
| Diagnosis, weekly actions, daily lead list, follow-up | **Real, deterministic** logic; weeks 2 to 4 of the demo come from a **scripted, labelled replay** |
| Next-month projection | **Real**, simple and labelled an estimate |
| Public-data modules | **Real**, labelled as public context |
| **Not built** | Screenshot reading, voice interview, WhatsApp bot, automatic Instagram connection, authentication, payments (the product is free) |

## 9. Hosting

Database on Supabase (you run `db/schema.sql` yourself; the AI tooling does not run DDL or data changes on a database). Frontend and API on Vercel; the API stays light at runtime so it fits serverless limits. Decision point at the first public deploy: if serverless Python gives trouble, run the same API on a free web service and keep Vercel for the frontend.

## 10. Stages and integration (today)

| Stage | Owner | Output |
|---|---|---|
| **S3: contract v2** (first) | Soham + Ayush | The draft in `contracts/API_CONTRACT.md` agreed; fixtures regenerated for Box Box and the home baker |
| **S3: intake, metrics, leads** | Soham | Generated demo businesses calibrated on public data, intake, five-bottleneck facts, lead records and scores, projection |
| **S3: diagnosis and advice** | Ayush | Bottleneck ranking, action library, eligibility rules, brand-risk rule, lead actions |
| **S4: follow-up and explanation** | Ayush | Weekly follow-up, evidence-checked explanation, drafts |
| **S4: integration** | both | `backend-integration`: merge, run the loop: load week 1 → diagnose → advise → record what was done → load week 2 → follow up |

### Integration status (`backend-integration`, updated as each part lands)

| Step | What | Status |
|---|---|---|
| 1 | Merge `backend-1` and `backend-2` (no conflicts); all tests pass together | **Done** |
| 2 | `DataClientV2` (`decision_engine/clients/v2.py`): business, facts, leads, projection, market context, data quality from `fixture`, `local` and `http`; the three return identical data for both businesses, weeks 1 to 4 | **Done**, tested |
| 3 | Gateway runs data_engine routes (`DATA_SOURCE=local uvicorn backend.gateway.main:app`) | **Done** (decision_engine routes mount when `decision_engine/main.py` exists) |
| 4 | Diagnosis (bottleneck ranking) reads `DataClientV2.get_facts` | Waiting for Ayush |
| 5 | Actions, eligibility, lead list with drafted replies | Waiting for Ayush |
| 6 | Weekly follow-up: load week 2, compare, adjust | Waiting for Ayush |
| 7 | Explanation (LLM with validator) over the real facts | Layer built by Ayush; to be wired to step 4 |

Fixtures: `contracts/fixtures/v2_engine/` is data_engine's real output (regenerate with `python -m backend.data_engine.devtools.export_v2_fixtures`); `contracts/fixtures/v2/` holds Ayush's stand-ins. `DataClientV2` reads `v2_engine` by default; set `V2_FIXTURE_DIR` to use the stand-ins.

## 11. Definition of done (per module)

- Every endpoint in the module's section of the contract returns real, correct data, or a documented 501 for a dropped should-have.
- Tests pass, with hand-calculated checks for the core math.
- After each stage the owner can say exactly what is real, precomputed or mocked.
- Every claim shown to the owner carries its evidence: the claim, the number, the source and the confidence.
