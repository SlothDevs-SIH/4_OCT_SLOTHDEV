# Backend 1: `data_engine` (Soham), Intake and Measurement

Branch: `backend-1`. You edit only `backend/data_engine/`. Port 8001. Overview of both backends: [`BACKEND.md`](BACKEND.md). Backend 2 (Ayush, `decision_engine`) reads your output only through the contract, so it can be built in parallel.

**Your job in one sentence:** turn whatever the founder has (an order list, costs, Instagram insights, a short interview) into one trustworthy business profile and compute the facts that show which of five bottlenecks is holding the business back, week by week.

**Stack:** Python, FastAPI, Pydantic, PostgreSQL/Supabase. The runtime is pure Python (stdlib `csv`, `statistics`); pandas and other heavy libraries are used only in offline scripts so the API stays small for Vercel.

## 1. What you produce for Ayush

| Output | Contract shape |
|---|---|
| Business profile (type, size, goal, constraints, hours, no ad budget) | `business_context` |
| Facts: value, baseline, numerator, denominator, **source** (`exact`/`estimate`/`derived`), **sample size**, quality flag | `kpi_facts` (additive fields `source`, `sample_size`) |
| Data-quality badge and import reports | `data_quality` |
| Weekly snapshots (week 1 to week 4), point in time | `snapshot` on each fact |
| Market context: upcoming race weekends | `market_context` (new, additive) |

## 2. Inputs (the "intake")

| Input | What it contains | Notes |
|---|---|---|
| **Order list** | order id, date, buyer (pseudonymised), item/design, size, quantity, price, payment, channel, **how the buyer found the brand** | The core file. Messy by default (mixed dates, duplicates, missing fields) |
| **Cost per unit** | blank tee, printing, packaging, courier | Gives the margin. Estimates are labelled `estimate` |
| **Instagram insights** | per post: date, reach, profile visits, follows, which posts led to orders | CSV export or typed in |
| **Customer source** | friend / friend of friend / stranger | From a column, or inferred from "how did you find us?" answers |
| **Interview answers** | hours per week, capacity, goal, what he tried, constraints | A short form first; voice later (not built) |

**Privacy:** buyer names and phone numbers are pseudonymised before any text is sent to an LLM.

## 3. The profile: a source on every field

Each field stores three things: the **value**, where it **came from**, and how **sure** we are.
- A figure from the order sheet is `exact`.
- A figure the founder said from memory is `estimate`.
- A figure we derived (for example, "12 of 140 orders came from strangers") is `derived`, with the count behind it.

This is what makes evidence-linked advice possible, and what lets the product say "this is an estimate" when data is thin.

## 4. The metrics (deterministic, never an LLM)

All facts use the existing fact shape. Proposed `fact_id`s (final names are agreed in contract v2).

| Bottleneck | Facts |
|---|---|
| **Reach** | `f_orders_by_source` (friend / friend of friend / stranger), `f_stranger_orders_week` (**main measure**), `f_stranger_share`, `f_reach_per_post`, `f_posts_with_orders` |
| **Conversion** | `f_profile_visit_rate`, `f_follow_rate`, `f_orders_per_1000_reach` |
| **Margin** | `f_unit_cost_full`, `f_margin_per_order`, `f_margin_pct`, `f_discount_share` |
| **Repeat orders** | `f_repeat_customer_share`, `f_days_between_orders` |
| **Capacity** | `f_orders_per_week`, `f_dispatch_delay_days`, `f_stockouts`, `f_orders_turned_away`, `f_capacity_utilisation` (orders per week vs what he says he can make) |

Rules: every fact carries its **sample size**; with fewer than a minimum number of orders, the fact is `estimate` with a warning, never presented as a verdict. The **baseline** for the first target is the business's **own best weeks**; typical figures per business type are added later and need a source.

## 5. Tasks and status

Reuse columns refer to code already in `backend/data_engine/`.

| # | Task | Reuse | Stage |
|---|---|---|---|
| 1 | **Contract v2** with Ayush: new fact list, `source` and `sample_size` fields, weekly snapshots, `market_context`; regenerate fixtures for Box Box | – | S3, first |
| 2 | **Box Box synthetic tenant**: ~14 weeks, about 240 orders, 3 to 5 designs, costs per unit, Instagram posts, customer source. **Planted pattern:** most orders come from friends and friends of friends, a few from strangers, reach per post is low, margin and capacity are fine, repeat is modest, and orders rise on race weekends. Deterministic, `synthetic: true`. Replaced by real data if Box Box shares it | Generator structure, determinism, anchors tests | S3 |
| 3 | **Intake**: order sheet, cost sheet, Instagram insights through the existing import pipeline; add the customer-source field and pseudonymisation | Import pipeline (mapping, repair, quarantine, quality badge) | S3 |
| 4 | **Profile with provenance** and the short interview form | – | S3 |
| 5 | **Metrics engine** for the five bottleneck families and the main measure | KPI engine registry and point-in-time rule | S3 |
| 6 | **Weekly snapshots** for weeks 1 to 4, including the scripted replay (what he did, what changed) | Point-in-time design from the day-7 replay | S4 |
| 7 | **Public data modules** (section 6): Online Retail II validation, F1 calendar | Dataset fetch script | S3 |
| 8 | `public.py` in-process interface returns the new facts; tests | Existing interface and tests | S4 |

## 6. Public datasets: what, why, and licences

The earlier plan used UCI Bank Marketing to train a lead-conversion model. **That is retired**: the new target user has no lead pipeline, and the brief wants diagnosis by calculation. We searched for public data that fits the *new* inputs.

| Dataset | What it is | Licence and access | Role in this product |
|---|---|---|---|
| **UCI Online Retail II** | Real order-level transactions of a UK gift-ware retailer, Dec 2009 to Dec 2011, about 1.07M rows (invoice, product, quantity, date, price, customer, country). Many buyers are wholesalers | **CC BY 4.0**, direct download from UCI, no login | **Validation corpus for intake and the order-based metrics.** Proves the pipeline handles real, messy order data (cancellation invoices, missing customer ids, returns) and that repeat-customer share and customer concentration compute correctly at scale |
| **F1 race calendar** (Jolpica, the Ergast successor) | Race schedule per season, including 2026: race dates and practice/qualifying dates | Open API, no key, rate-limited (cache a snapshot) | **Market context.** Race weekends are demand windows for F1 merchandise, so actions (drops, posts, collaborations) can be timed around them |
| **Wikipedia page views** (Wikimedia API) | Daily views of articles such as "Formula One" or a driver | Open API, no key | **Optional.** A proxy for F1 interest around race weekends |
| Instagram post insights (tutorial CSV, 119 posts) | Reach by source, likes, saves, profile visits, follows | Circulated on GitHub/Kaggle with **no stated licence** | **Not integrated.** Test-only if used at all; never redistributed. The demo uses synthetic insights |
| Medical appointment no-shows, CRM sales opportunities, Rossmann stores, Olist | Fit other business types (clinics, B2B, stores, marketplace sellers) | Need a Kaggle or Maven login; some are non-commercial | **Not used.** The brief explicitly narrowed away from those types |

**Why Online Retail II and not another:** it is the only order-level public dataset that is directly downloadable with a clear open licence, and the brief's core data is an order list. **Honest limits:** it is a wholesaler (not a student maker), so it validates the *engine* and is **not** a benchmark for Box Box. No public dataset contains "friend vs stranger" or a founder's unit costs; those come from Box Box or from the synthetic tenant.

Download: `python -m backend.data_engine.ml.fetch_datasets --retail`. Files go to `data/raw/` (git-ignored; never redistributed). Cite: Chen, D. (2012), *Online Retail II*, UCI Machine Learning Repository, https://doi.org/10.24432/C5CG6D.

## 7. Data rules (honesty)

- Every synthetic row and response is labelled `synthetic: true`; real and public data are labelled with their source.
- Public data is never presented as Box Box's data.
- Sanity-check units and ranges on every number before it leaves the module (a hand calculation for one fact per family).
- Small samples: always report the count; below the minimum, mark `estimate`.
- Invariants to test: orders have a date and price; stranger + friend + friend-of-friend orders add up to all orders; a repeat order never precedes the first; no future timestamps.

## 8. Integration

On `backend-integration` your branch is merged with `backend-2`; `data_engine/public.py` is the in-process interface Ayush's `DataClient` calls with `DATA_SOURCE=local`. Keep the signatures stable and agree the new fact list in contract v2 **before** either side builds on it. See `BACKEND.md` section 9.

## 9. Current state of the code (before this plan)

Built and tested for the earlier D2C plan (75 tests): synthetic tenant, import pipeline with quality report, KPI engine with point-in-time snapshots, the Bank Marketing lead model and queue. The import pipeline and the point-in-time design carry over; the tenant, the ad-spend facts and the lead model are retired (section 4 of `BACKEND.md`).
