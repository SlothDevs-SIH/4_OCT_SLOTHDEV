# Backend 1: `data_engine` (Soham), Intake, Measurement and Lead Scoring

Branch: `backend-1`. You edit only `backend/data_engine/`. Port 8001. Overview of both backends: [`BACKEND.md`](BACKEND.md). Datasets: [`../docs/DATASET.md`](../docs/DATASET.md). Backend 2 (Ayush, `decision_engine`) reads your output only through the contract, so both can be built in parallel.

**Your job in one sentence:** turn whatever a home-business owner has (an order list, costs, Instagram insights, pasted chats, a short interview) into one trustworthy business profile, compute the facts that show which of five bottlenecks is holding the business back week by week, score the people who show interest, and project next month's orders.

**Stack:** Python, FastAPI, Pydantic, PostgreSQL/Supabase. The runtime is pure Python (stdlib `csv`, `statistics`); pandas and scikit-learn are used only in offline scripts so the API stays small for Vercel.

## 1. What you produce for Ayush

| Output | Contract shape |
|---|---|
| Business profile (type, products, size, goal, constraints, hours, no ad budget) | `business` |
| Facts: value, baseline, numerator, denominator, **source** (`exact`/`estimate`/`derived`), **sample size**, quality flag | `fact` |
| Weekly snapshots (week 1 to 4), point in time | `snapshot` on each fact |
| **Leads**: record, intent labels, points, group (Hot/Warm/Cold/Disqualified), reasons | `lead` |
| **Next-month projection** with a range | `projection` |
| Data-quality badge and import reports | `data_quality` |
| Market context (event calendars) | `market_context` |

## 2. Inputs (the intake)

| Input | Contents | Notes |
|---|---|---|
| **Order list** | order id, date, buyer (pseudonymised), items (any product), quantity, price, payment, channel, **how the buyer found the brand** | The core file; messy by default |
| **Cost per unit** | materials or blank, making, packaging, courier | Gives the margin; estimates labelled `estimate` |
| **Instagram insights** | per post: date, reach, profile visits, follows, which posts led to orders | CSV or typed in |
| **Pasted chats and comments** | DMs, comments, story replies, WhatsApp text | Pasted text only; screenshots are **not built** |
| **Customer source** | friend / friend of a friend / stranger | A tag at intake, or inferred from "how did you find us?" |
| **Interview answers** | hours per week, capacity, goal, what was tried, constraints | A short form first; voice not built |

**Privacy:** names and phone numbers are pseudonymised before any text goes to an LLM; store only what the model needs, per owner, deletable.

## 3. The profile: a source on every field

Each field stores the **value**, where it **came from**, and how **sure** we are. A figure from the order sheet is `exact`; one the owner said from memory is `estimate`; one we derived (for example "12 of 140 orders came from strangers") is `derived`, with the count behind it. This is what makes evidence-linked advice possible.

## 4. Facts (deterministic, never an LLM)

All facts use the contract fact shape. Names are final in contract v2.

| Bottleneck | Facts |
|---|---|
| **Reach** | `f_orders_by_source`, `f_stranger_orders_week` (**main measure**), `f_stranger_share`, `f_reach_per_post`, `f_posts_with_orders` |
| **Conversion** | `f_profile_visit_rate`, `f_follow_rate`, `f_orders_per_1000_reach`, `f_lead_to_order_rate` |
| **Margin** | `f_unit_cost_full`, `f_margin_per_order`, `f_margin_pct`, `f_discount_share` |
| **Repeat orders** | `f_repeat_customer_share`, `f_days_between_orders` |
| **Capacity** | `f_orders_per_week`, `f_dispatch_delay_days`, `f_stockouts`, `f_orders_turned_away`, `f_capacity_utilisation` |

Rules: every fact carries its **sample size**; under a minimum number of orders it is an `estimate` with a warning, never a verdict. The first target is the business's **own best weeks**.

## 5. Lead qualification (from the team document `Lead_Qualification_Model.docx`, shared outside the repo)

**What is a lead:** any person who showed interest on a channel the owner uses: a DM, a comment, a save or share, a story reply, or a past order. Not a form fill.

**Lead record:** handle, source (DM / comment / story / WhatsApp / referral), **relationship** (friend / friend of a friend / stranger), signals with dates, what they asked for (product, size, design, delivery city), **deliverable?**, score, group, next action, outcome (ordered / not ordered / open).

**Six steps:** collect → **read** (LLM labels intent) → **score** (points) → **group** → **act** (backend 2) → **learn** (weekly).

| Intent label (LLM) | Signals |
|---|---|
| Buying question ("Is this available in L?", "how much with delivery to Pune?") | strongest |
| Product interest ("this one is fire" on a product story) | interested in a specific item |
| General praise ("love your page") | weak |
| Custom request ("can you make one with my name?") | interested, needs a fit check |
| Not a lead (spam, collaboration pitches, supplier messages) | removed |

| Signal | Points |
|---|---|
| Asked about price, size, stock or delivery | **+40** |
| Bought before | **+30** |
| Replied to a product story | **+20** |
| Saved or shared a post | **+15** |
| Commented on a post | **+10** |
| Is a stranger (not from the owner's circle) | **+10** (growth bonus) |
| Only followed or liked once | **+5** |
| No activity in the last 30 days | **-20** (decay) |
| Wants something the owner cannot deliver (size, design, city) | **Disqualified** (fit check) |

A signal counts **once per lead**, so the score stays explainable. **Groups:** Hot 50 or more, Warm 20 to 49, Cold under 20, Disqualified at any score. **Ranking:** at the same score, a stranger ranks above a friend (new growth over a repeat sale from the circle). **Disqualified leads are counted by reason** (a size, design or city people keep asking for is itself advice).

**Status honesty:** the points and thresholds are **starting guesses**, as the design says. The weekly step replaces guesses with evidence.

**Weekly learning:** each week mark the outcome of every scored lead; compute the share of Hot, Warm and Cold leads that ordered, and per signal how often leads with it ordered; raise predictive signals and lower the rest. Healthy: Hot converts far more than Warm, Warm more than Cold. If Hot and Warm convert alike, the signals or the threshold are wrong. With **about 100 or more leads with known outcomes**, a logistic regression can learn the weights; the weights stay visible.

**How public data supports it (see `DATASET.md`):**
- **Bank Marketing** (contact history only: previous outcome, prior contacts, days since last contact, contacts this campaign): a logistic regression is already trained and tested (PR-AUC 0.680 vs 0.512 on a strictly later hold-out). Its learned direction agrees with the points ("bought before" highest, a longer gap lowers the score). It is the **learned challenger and sanity check**, not the first version.
- **Online Shoppers**: intent beats light interest (sessions with page value convert at 56.3% vs 3.9%) and new visitors behave differently. This supports "intent outweighs interest" and the stranger bonus as a design direction. We will turn it into an explicit check (does the rule order agree with the data?).
- **Reach partners** (fan pages, creators, college communities) are qualified with the same idea: audience match, location match, engagement not followers, past results, cost. Backend 2 owns this advice.

**Contact rules:** the owner sends every message himself (the advisor drafts, never sends); one-to-one messages only go to people who contacted the brand or bought before; a Warm lead is contacted once per reason.

## 6. Next month's sales

A transparent projection of next month's orders with a **range**: the recent weekly trend (last 4 to 8 weeks) times a context factor from the market-context calendar, with the range from the historical week-to-week variation. Labelled an **estimate**, with its basis shown (which weeks, which factor). No machine-learning forecast. If there are fewer than a minimum number of weeks, say so instead of projecting.

## 7. Market context

A context module turns an event calendar into demand windows. **Built:** the F1 race calendar (2025 and 2026) and a measured page-view uplift (race weekends lift F1 interest about 2.0 times), used for the Box Box case. **Planned:** an India festival and holiday calendar for businesses that are not about F1. The interface is the same for any calendar (`market_context`: race or event weekends in a range, the next event, the measured uplift if there is one).

## 8. Tasks and status

"Reuse" refers to code already in `backend/data_engine/`.

| # | Task | Reuse | Status |
|---|---|---|---|
| 1 | **Contract v2** with Ayush (facts, lead, projection, context, weekly snapshots) | – | S3, first |
| 2 | **Generated demo businesses** (Box Box and a home baker): about 14 weeks, about 240 orders each, calibrated on public data, scenario assumptions listed (DATASET.md section 4), deterministic, `synthetic: true` | Generator structure, determinism tests | S3 |
| 3 | **Intake**: orders, costs, insights through the import pipeline; customer-source field; pseudonymisation | Import pipeline (built, 93 tests) | S3 |
| 4 | **Profile with provenance** and the short interview form | – | S3 |
| 5 | **Facts** for the five bottlenecks and the main measure | KPI registry, point-in-time rule, order metrics | S3 |
| 6 | **Leads**: record, intent labelling (LLM, validator, cache, fallback), points, groups, ranking, disqualification by reason | Bank Marketing model as the challenger | S3 |
| 7 | **Weekly snapshots** (weeks 1 to 4) including the scripted replay; **weekly lead learning** report | Point-in-time design | S4 |
| 8 | **Projection** with a range | – | S4 |
| 9 | **Context modules**: F1 (built), India festival calendar | F1 modules (built) | S4 |
| 10 | `public.py` in-process interface returns the new outputs; tests | Existing interface | S4 |

## 9. Built and tested already (public data and shared code)

93 tests pass. Built: the import pipeline (mapping, repair, quarantine, quality badge); order metrics reused on every order list (repeat share, days between orders, concentration); profiles of Olist, Online Retail II and Online Shoppers; the F1 calendar and page-view uplift; the Bank Marketing lead model. See `GET /api/v1/public-data` and `GET /api/v1/market-context`.

## 10. Data rules (honesty)

- Every generated row and response is `synthetic: true`; real and public data carry their source.
- Public data is never shown as a user's data.
- Sanity-check units and ranges on every number (a hand calculation per fact family).
- Small samples: always report the count; under the minimum, mark `estimate`.
- Invariants to test: stranger + friend + friend-of-friend orders add up to all orders; a repeat order never precedes the first; no future timestamps; a lead has at most one count per signal.

## 11. Integration

On `backend-integration` your branch is merged with `backend-2`; `data_engine/public.py` is the in-process interface Ayush's `DataClient` calls with `DATA_SOURCE=local`. Keep the signatures stable and agree contract v2 **before** either side builds on it. See `BACKEND.md` section 10.

## 12. Legacy code

Built earlier for the D2C-brand plan: the synthetic tenant "Aarohi Skin", D2C KPI facts (CAC, ROAS), the lead queue for hot leads of a brand. They stay until the new engine replaces them, then are removed.
