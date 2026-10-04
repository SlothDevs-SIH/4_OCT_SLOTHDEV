# API and Data Contract: v2 (DRAFT, to be agreed by Soham and Ayush)

The shared contract that `backend-1`, `backend-2` and `frontend` code against, for **Catalyst AI** (a free advisor for home-business owners). It replaces the earlier D2C-brand contract. Change rules: `docs/WORKFLOW.md` section 3; changes are made on `main` only.

**Status of each endpoint:** `built` = exists and is tested on `backend-1` today; `v2` = to be built against this draft; `legacy` = from the earlier plan, removed once replaced. The example fixtures in `contracts/fixtures/` belong to the earlier plan (legacy) and are regenerated for Catalyst AI once this draft is agreed.

## 1. Conventions

- Base path `/api/v1`. JSON in and out. Errors: `{"error": {"code": "...", "message": "..."}}`.
- IDs are strings. Dates `YYYY-MM-DD`; timestamps ISO 8601 UTC; currency INR.
- **Labels:** every business, row and response from generated data has `"synthetic": true`. Public data carries its source. The UI shows a "demo data" badge.
- **Provenance on every number:** `source` is `exact` (from a file), `estimate` (the owner said it from memory) or `derived` (computed, with `sample_size`).
- **Evidence:** every finding, action and lead reason carries `evidence_ids` pointing at facts, leads or fields that exist. The LLM never creates a number or an evidence id.
- **Weeks:** snapshots are `week_1` to `week_4` (point in time: a snapshot only sees events up to its `as_of`).
- **Ports in dev:** `data_engine` 8001, `decision_engine` 8002, `gateway` 8000.

## 2. Core shapes

### 2.1 Business
`business_id`, `name`, `case_study` (for example `"Box Box"`, optional), `synthetic`, `products[{name, category, price, unit_cost?}]`, `channels[]` (instagram, whatsapp, ...), `team_size`, `weekly_hours`, `ad_budget_inr` (0 by default), `capacity_orders_per_week`, `goal{statement, horizon_days}`, `constraints{forbidden_actions[], approval_required_for[]}`, `context_feeds[]` (for example `f1_calendar`, `india_festivals`), `week` (current snapshot).

### 2.2 Fact
`fact_id, kpi, dimension, period{from,to}, value, unit, baseline, delta_pct, numerator, denominator, definition_version, quality_flag (ok|partial|low), snapshot` **plus** `source` (`exact|estimate|derived`) and `sample_size`. The **baseline** is the business's own best weeks. Names by bottleneck:

| Bottleneck | `fact_id`s (proposed) |
|---|---|
| Reach | `f_orders_by_source`, `f_stranger_orders_week` (**main measure**), `f_stranger_share`, `f_reach_per_post`, `f_posts_with_orders` |
| Conversion | `f_profile_visit_rate`, `f_follow_rate`, `f_orders_per_1000_reach`, `f_lead_to_order_rate` |
| Margin | `f_unit_cost_full`, `f_margin_per_order`, `f_margin_pct`, `f_discount_share` |
| Repeat orders | `f_repeat_customer_share`, `f_days_between_orders` |
| Capacity | `f_orders_per_week`, `f_dispatch_delay_days`, `f_stockouts`, `f_orders_turned_away`, `f_capacity_utilisation` |

### 2.3 Order (intake row)
`order_id, date, buyer_ref (pseudonym), items[{name, category, qty, price}], total, payment, channel, relationship (friend|friend_of_friend|stranger|unknown), post_id?, dispatched_at?`.

### 2.4 Lead
`lead_id, handle_ref, source (dm|comment|story|whatsapp|referral|order), relationship, signals[{type, date}], asked_for{product, size, design, city}, deliverable (bool), intents[] (buying_question|product_interest|general_praise|custom_request|not_a_lead), score, group (hot|warm|cold|disqualified), reasons[{signal, points}], disqualified_reason?, next_action, outcome (ordered|not_ordered|open), rank`.
**Points (v1, starting guesses):** price/size/stock/delivery question +40; bought before +30; replied to a story +20; saved or shared +15; commented +10; stranger +10; only followed or liked once +5; no activity in 30 days -20; cannot deliver = disqualified. **Groups:** hot 50+, warm 20 to 49, cold under 20. Each signal counts once; at equal score a stranger ranks above a friend.

### 2.5 Diagnosis
`business_id, week, bottlenecks[{bottleneck, gap_to_best, tests{materiality, deviation, localisation, actionability}, evidence_ids[], confidence}], primary, runners_up[], rejected[{bottleneck, reason}]`. Each finding is an **evidence card**: `claim, number, source, confidence, evidence_ids`.

### 2.6 Action
`action_id, bottleneck, title, why, evidence_ids[], effort_min, target, due, status (todo|done|skipped), requires_approval, risk_flags[]`. `risk_flags` includes `brand_ip` ("protected names, logos or characters can lead to takedowns; not legal advice").

### 2.7 Projection (next month)
`business_id, month{from,to}, orders{low, expected, high}, basis{weeks_used, trend, context_factor, context_source}, confidence, estimate: true`. Never a machine-learning forecast; if the history is too short it says so instead of projecting.

### 2.8 Follow-up
`business_id, week, actions_done[], actions_skipped[], fact_changes[{fact_id, previous, current}], main_measure{stranger_orders{previous, current}}, adjustments[]`. Fidelity (was it done?) and effectiveness (did the number move?) are separate and labelled observational.

### 2.9 Market context
`season, from, to, race_weekends[]` (or `events[]` for other calendars), `next_race`/`next_event`, `interest_uplift{overall{uplift, weekend_days, other_days}}`, `note` ("interest, not sales"). **Built.**

## 3. Endpoints owned by `data_engine` (Soham)

| Status | Method | Path | Purpose |
|---|---|---|---|
| built | GET | `/data/health` | liveness |
| built | POST / GET | `/businesses`, `/businesses/{id}` | create from the intake form and the short interview; read |
| built | GET | `/businesses/{id}/profile` | every profile field with its `source` |
| built | POST | `/demo/load?business=boxbox\|homebaker&week=1..4` | load a generated demo business at a week |
| built | POST | `/businesses/{id}/imports?kind=` | upload a CSV; returns columns and a suggested mapping (kinds: orders, costs, insights, leads, campaigns) |
| built | POST | `/imports/{id}/confirm`, `/businesses/{id}/imports/auto` | confirm the mapping (or do both at once); validate, repair, quarantine |
| built | GET | `/imports/{id}/report`, `/imports/{id}/quarantine`, `/businesses/{id}/data-quality` | what was loaded, repaired, quarantined; the quality badge |
| built | POST | `/businesses/{id}/leads/intake` | pasted chat or comment text: intent is labelled (rules now, LLM pluggable) and product, size, design, city extracted; identities are pseudonymised |
| built | GET | `/businesses/{id}/leads?group=&week=` | scored leads with reasons |
| built | PATCH | `/leads/{id}` | the owner tags the relationship, corrects an intent label, records the outcome |
| built | GET | `/businesses/{id}/leads/learning` | the weekly check: conversion by group and by signal |
| built | GET | `/businesses/{id}/facts?week=` | the facts (2.2) |
| built | GET | `/businesses/{id}/facts/weekly?fact_id=` | one fact across weeks |
| built | GET | `/businesses/{id}/projection` | next month's orders with a range |
| built | GET | `/market-context?from=&to=&feed=f1_calendar\|india_festivals` | event windows, next event, measured uplift (F1 only) |
| built | GET | `/public-data` | the public datasets in use, licences, roles, measured results |

**In-process interface** (`backend/data_engine/public.py`, used when `DATA_SOURCE=local`): `get_context`, `get_facts`, `get_leads`, `get_projection`, `get_data_quality`, `get_profile`, `get_market_context`, `get_public_data`. Each returns exactly the shape of this contract.

**Additive details (v2):** the by-source facts are three ids, `f_orders_by_source_friend`, `f_orders_by_source_friend_of_friend`, `f_orders_by_source_stranger`. `GET /businesses/{id}/projection` also returns `demand` (orders plus orders turned away) and `capacity` (`demand_exceeds_capacity`, `message`). Extra built routes: `GET /businesses/{id}/data-card`, `POST /businesses/{id}/week` (replay week 1..4), `GET /demo/sample-chat`, `GET /demo/sample-orders.csv`. Facts need at least four weeks of orders, otherwise `422 not_enough_history`.

## 4. Endpoints owned by `decision_engine` (Ayush)

| Status | Method | Path | Purpose |
|---|---|---|---|
| built | GET | `/decision/health` | liveness |
| v2 | GET | `/businesses/{id}/diagnosis?week=` | the one bottleneck, two runners-up, rejected near-misses, each with its evidence card |
| v2 | POST / GET | `/businesses/{id}/actions/generate`, `/businesses/{id}/actions` | 1 to 3 actions for the week (eligibility-filtered) |
| v2 | PATCH | `/actions/{id}` | mark done or skipped |
| v2 | GET | `/actions/{id}/draft?channel=` | a draft message (preview only, never sent) |
| v2 | GET | `/businesses/{id}/lead-list` | the daily list (hot, warm, cold, disqualified) with a drafted reply for each hot lead |
| v2 | GET | `/businesses/{id}/reach-partners` | ranked candidate partners (audience match, location, engagement, past results, cost) |
| v2 | POST / GET | `/businesses/{id}/followup?week=`, `/businesses/{id}/followups` | record what was done, compare weeks, adjust |
| v2 | GET | `/businesses/{id}/next-month` | the projection explained, tied to the one bottleneck |
| v2 | POST | `/businesses/{id}/chat` | grounded Q&A that cites fact ids (should-have) |
| legacy | * | signals, recommendations, plans, tasks, outcomes of the earlier plan | removed once replaced |

**How `decision_engine` reads data:** through `DataClient` with `DATA_SOURCE` = `fixture`, `http` or `local`.

## 5. LLM boundary

The LLM has two jobs: read messy text and label intent (`data_engine`), and explain results (`decision_engine`). It receives an **evidence packet** and must return JSON that validates against the schema. A validator rejects output that (a) cites an unknown evidence id, (b) contains a number not in the packet, (c) proposes an action outside the library, or (d) breaks a constraint. On failure: retry once, then use deterministic text. A local cache keeps the demo working offline. **The LLM never calculates a fact, a score or a projection, and never chooses the bottleneck.** Names and phone numbers are pseudonymised before any text reaches it.

## 6. Tables per owner (see `db/schema.sql`, to be updated)

`data_engine` writes business, order, cost, post, lead, signal, import and quarantine tables and fact snapshots. `decision_engine` writes diagnosis, action, follow-up and draft tables. The modules never write each other's tables; they exchange data only through this contract.
