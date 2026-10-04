# Backend: intake and diagnosis in two independent modules

**Product (from the project brief, 4 Oct 2026):** an advisor for **small, early-stage maker-sellers**: small e-commerce, homegrown and student-run businesses with their first 50 to 500 orders, selling mainly through Instagram or WhatsApp, with no ad budget, run by one to three people. First case study: **Box Box** (F1 merchandise, run by a final-year student).
**The loop:** intake (messy data plus a short interview) → diagnosis (the single biggest bottleneck) → advice (1 to 3 actions this week, each with evidence) → weekly follow-up (what was done, what changed, adjust).
**Main success measure:** **orders from strangers**, not from friends. If that number rises over four weeks, the advice is working.
**Contract:** [`../contracts/API_CONTRACT.md`](../contracts/API_CONTRACT.md) (fact shape is unchanged; the fact list changes, see section 3).
**Module docs:** [`BACKEND_1_DATA_ENGINE.md`](BACKEND_1_DATA_ENGINE.md) (Soham) and [`BACKEND_2_DECISION_ENGINE.md`](BACKEND_2_DECISION_ENGINE.md) (Ayush).

> **Status of this document:** this is the plan after the stakeholder brief changed the target user. Code written for the earlier D2C-brand plan is being migrated; section 4 says exactly what is kept, adapted or retired.

## 1. The backend in one picture

```
 ┌──────────────── data_engine (backend 1, Soham): INTAKE + MEASUREMENT ────────────────┐
 │ order list · cost per unit · Instagram insights · customer source · interview answers │
 │   → validate, repair, quarantine → one business profile (value + source + confidence)  │
 │   → metrics for the five bottlenecks + "orders from strangers" → weekly snapshots      │
 │   → public data: validation corpus + F1 race calendar (market context)                 │
 └───────────────────────────────────────┬──────────────────────────────────────────────┘
                                         │ facts (value, baseline, numerator, denominator, source, confidence)
 ┌───────────────────────────────────────▼──────────────────────────────────────────────┐
 │ decision_engine (backend 2, Ayush): DIAGNOSIS + ADVICE + FOLLOW-UP                    │
 │   rank reach / conversion / margin / repeat orders / capacity → name ONE bottleneck   │
 │   → 1 to 3 weekly actions from a library, filtered by the founder's constraints       │
 │   → explanation by an LLM that may only use numbers the engine produced               │
 │   → weekly follow-up: what was done, what changed, adjust next week                   │
 └───────────────────────────────────────────────────────────────────────────────────────┘
```

**The AI does not decide what is wrong. The calculations do.** The LLM's jobs are to read messy input (a DM, a UPI note, an interview answer) and to explain the result in plain language, using only numbers the engine produced. If a number is missing, the finding is not shown.

## 2. Why this user, and what that changes in the backend

The brief compared segments (offline shops, small manufacturers, kirana stores, freelancers, family businesses, small e-commerce sellers) and chose the sellers who **feel the pain daily, already look for help, and have at least partly digital data**, narrowed to the earliest stage. The rule that decided it: *target a business that needs help and knows it.*

What this means for the engineering:
- **No ad data.** There is no ad budget, so CAC, ROAS and ad-spend signals do not apply. Reach, not attribution, is the problem.
- **Messy data is the norm.** Orders live in DMs, UPI apps and a sheet. Intake must work with that or founders drop off.
- **Tiny volumes.** 50 to 500 orders means small samples. Every metric carries a sample size and a confidence label, and thin data produces "estimate", not a verdict.
- **The data decides.** Reach is the *likely* bottleneck for Box Box, but the engine must compute all five and let the numbers choose.
- **Advice must be specific.** A chatbot is the real competitor. Our difference is advice tied to the seller's own numbers, with the evidence shown, and a weekly follow-up a chatbot does not do.

## 3. The five bottlenecks and the facts that show them

| Bottleneck | Meaning | What shows it (facts the engine computes) |
|---|---|---|
| **Reach** | Too few new people see the brand | Share of orders from friends vs friends of friends vs strangers; stranger orders per week; Instagram reach per post |
| **Conversion** | People see it but do not buy | Profile visits and follows per post vs orders; orders per 1,000 reached |
| **Margin** | Each order earns too little to fund growth | Price minus full unit cost (blank + printing + packaging + courier); margin per order and in % |
| **Repeat orders** | Buyers do not come back | Share of customers with a second order; days between orders |
| **Capacity** | He cannot make or ship more | Dispatch delay, stock-outs, orders turned away, orders per week vs what he says he can make |

Every fact keeps the existing contract shape (`fact_id, kpi, dimension, period, value, unit, baseline, delta_pct, numerator, denominator, definition_version, quality_flag, snapshot`) and gains two additive fields: `source` (`exact` | `estimate` | `derived`) and `sample_size`. Snapshots become weekly (week 1 to week 4) instead of "baseline / day 7".

## 4. What is kept, adapted or retired from the earlier plan

| Piece | Decision |
|---|---|
| CSV import: column detection, mapping, repair, quarantine, quality badge | **Keep and extend.** Orders, cost sheet and Instagram-insights files go through it; add a `customer source` field |
| Point-in-time snapshots (a snapshot only sees events before its `as_of` time) | **Keep.** Used for the weekly follow-up, so week 1 never sees week 2 |
| Fact shape, evidence IDs, data client (`fixture`, `http`, `local`) | **Keep** |
| Eligibility gate (blocks forbidden or unaffordable actions) | **Keep.** New rules: no paid ads, student hours, trademark risk |
| LLM boundary: evidence packet, JSON-schema output, validator, cache, deterministic fallback | **Keep** |
| Outcome ledger (baseline frozen, expected vs actual, fidelity vs effectiveness) | **Adapt** into the weekly follow-up |
| Planner (capacity-aware scheduling) | **Adapt** to "1 to 3 actions this week" |
| D2C-brand tenant "Aarohi Skin", ad-spend KPIs (CAC, ROAS), hot-lead queue | **Retire** (code stays in the repo, unused) |
| Lead-conversion model on UCI Bank Marketing | **Retire.** The product has no lead pipeline, and the brief calls for diagnosis by calculation, not a prediction model |
| Anomaly detection on ad-channel CAC | **Retire** (no ad channels). May return for weekly orders |

## 5. Data strategy: three kinds of data, each labelled

| Kind | Source | Role | Labelled |
|---|---|---|---|
| **Real case study** | Box Box's own order list, unit costs, Instagram insights, customer source, interview | The truth the advisor is built around. Used if he shares it | `real` |
| **Synthetic Box Box** | Generated by us, deterministic, with planted patterns | Lets the prototype run and be tested when real data is not available | `synthetic: true` always |
| **Public data** | UCI Online Retail II; the F1 race calendar (Jolpica API); optionally Wikipedia page views | **Validation and context only.** Never presented as Box Box's data | `public`, with source and licence |

Details, licences and exact roles: `BACKEND_1_DATA_ENGINE.md`, section "Public datasets". Short version:
- **UCI Online Retail II** (CC BY 4.0, direct download): a real order-level file used to test that intake and the repeat-order and concentration metrics work on messy, real transactions at scale. It is a UK gift wholesaler, so it is **not** a benchmark for student makers.
- **F1 race calendar** (Jolpica, open, no key): race weekends are demand windows for F1 merchandise, so the advisor can time actions (drops, posts, collaborations) around them.

## 6. Technology choices and why

| Choice | Why | What we did not choose |
|---|---|---|
| **Python + FastAPI + Pydantic** | One language for API and analysis; typed contracts between two people's modules | Node: would split the team across languages |
| **Pure-Python runtime for the engines** (stdlib `csv`, `statistics`) | Small deploy size and fast cold start on serverless hosting; deterministic and easy to test | pandas at runtime: heavy for serverless. pandas stays in offline scripts only |
| **Deterministic metrics, no ML model as the decision-maker** | The brief: calculations decide, the AI explains. With 50 to 500 orders there is too little data for a trained predictor, and a visible formula can be shown to the founder | A learned ranker: it would be fiction at this volume |
| **LLM for messy intake and for explanation** | The only part of the product that needs language understanding: DMs, UPI notes, interview answers, plain-language advice | Letting the LLM diagnose or do arithmetic |
| **Evidence validator and cache** | The LLM may only cite facts it was given; rejects invented numbers and unknown evidence; the cache keeps the demo working offline | Trusting raw LLM output |
| **PostgreSQL on Supabase** | Managed, free tier, JSON for the profile (the profile changes shape per business) | SQLite: not shared across serverless instances |
| **Vercel (frontend and API)** | Mobile-first web app from a link, no install; one codebase; judges open it from a link | Native app: slower to build, needs installing |
| **Not used** | Microservices, queues, vector databases, native apps, a WhatsApp bot (later) | Each adds failure points without helping a weekly decision loop |

## 7. Prototype scope: real, precomputed, or not built

| Capability | Status |
|---|---|
| Intake of an order sheet, cost sheet, Instagram insights (CSV) with repair and quarantine | **Real** (existing pipeline, extended) |
| Customer-source tagging (friend / friend of friend / stranger) | **Real**, from a column or from the interview |
| Profile with source and confidence on every field | **Real** |
| Metrics for the five bottlenecks and orders from strangers; weekly snapshots | **Real computation** over rows |
| Diagnosis of one bottleneck plus two runners-up, with evidence | **Real**, deterministic |
| Weekly actions (1 to 3) and the weekly follow-up | **Real logic**; follow-up data for weeks 2 to 4 comes from a **scripted synthetic replay** until real weeks exist |
| LLM explanation and drafts (DM, caption, collaboration pitch) | Real call when a key is set; **cached** for the demo; deterministic fallback; drafts are previews, never sent |
| Public data (Online Retail II validation, F1 calendar) | **Real**, labelled as public context |
| **Not built** | Voice interview, WhatsApp bot, reading DM screenshots, UPI statement parsing, automatic Instagram connection, authentication, payments |

## 8. Hosting (Supabase + Vercel)

Database on Supabase (you run `db/schema.sql` yourself; the AI tooling does not run DDL or data changes on a database). Frontend and API on Vercel; the API stays light at runtime (no pandas or scikit-learn) so it fits serverless limits. Decision point at the first public deploy: if serverless Python gives trouble, run the same API on a free web service and keep Vercel for the frontend.

## 9. Stages and integration

| Stage | Owner | Output |
|---|---|---|
| **S3: contract v2** (first) | both | New fact list, `source` and `sample_size` fields, weekly snapshots; fixtures regenerated for Box Box. Until this is agreed, neither module can finish |
| **S3: intake and metrics** | Soham | Box Box synthetic tenant, intake for the three sheets, the five bottleneck metric families, weekly snapshots, public-data modules |
| **S3: diagnosis and advice** | Ayush | Bottleneck ranking, action library, eligibility rules, trademark risk rule |
| **S4: follow-up and explanation** | Ayush | Weekly follow-up, evidence-checked LLM explanation, drafts |
| **S4: integration** | both | `backend-integration`: merge, run the loop end to end |

Integration steps are unchanged: merge `backend-1` and `backend-2` into `backend-integration`, run the gateway with `DATA_SOURCE=local`, walk the loop (load week 1 → diagnose → advise → record what was done → load week 2 → follow up), tag when green.

## 10. Definition of done (per module)

- Every endpoint in the module's section returns real, correct data, or a documented 501 for a dropped should-have.
- Tests pass, with hand-calculated checks for the core math.
- After each stage the owner can say exactly what is real, precomputed or mocked.
- Every claim shown to the founder carries its evidence: the claim, the number, the source and the confidence.
