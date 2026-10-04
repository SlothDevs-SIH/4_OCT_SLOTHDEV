# Backend 2: `decision_engine` (Ayush), Diagnosis, Advice and Follow-up

Branch: `backend-2`. You edit only `backend/decision_engine/`. Port 8002. Overview of both backends: [`BACKEND.md`](BACKEND.md). Datasets: [`../docs/DATASET.md`](../docs/DATASET.md). Backend 1 (Soham, `data_engine`) produces the facts, lead scores and projection; you read them only through `DataClient`.

**Your job in one sentence:** from the facts, name the single biggest bottleneck among reach, conversion, margin, repeat orders and capacity; give the owner one to three actions for this week with the evidence behind each, plus a daily list of leads to answer; and every week check what was done and what changed.

**The rule:** the calculations decide what is wrong; the LLM only explains, using numbers the engine produced. If a number is missing, the finding is not shown.

## 1. The user and what it means for the rules

Home-business owners of any product: first 50 to 500 orders, selling through Instagram or WhatsApp, **no ad budget**, one to three people with limited hours. Box Box (F1 merchandise) is the first case study and demo; a home baker is the second sample. Reach is the *likely* bottleneck for Box Box, but **the data decides, not the assumption**.

## 2. Diagnosis

| Step | What it does |
|---|---|
| **Score the five bottlenecks** | Reach, conversion, margin, repeat orders, capacity. Each is scored from backend 1's facts against a target. The first target is the business's **own best weeks**; typical figures per business type are added later and need a source |
| **Four tests per bottleneck** | Materiality (enough orders to matter), deviation (worse than its own best), localisation (which stage or source), actionability (a feasible action exists). Near-misses are listed as rejected, with the reason |
| **Pick one, show two runners-up** | The bottleneck with the largest gap to the owner's own best weeks, among those that pass the four tests, wins. Ties are broken by what the owner can act on with the time and budget they stated |
| **Evidence on every finding** | Four parts: the **claim**, the **number**, the **source** (which file or answer), the **confidence** (`exact` / `estimate` / `derived`) |
| **Low data = low confidence** | Under the minimum sample size the finding is shown as an estimate, or not shown. Never dressed up |

## 3. Advice: one to three actions this week

Actions come from an approved library keyed by bottleneck, then filtered by the owner's constraints. Each action has the evidence that chose it, an effort in minutes, a measurable target and a deadline. The library is **generic** (works for any product); research reviews the content.

| Bottleneck | Example actions |
|---|---|
| **Reach** | Collaborate with niche fan pages or creators related to the product's subject; ask college or local communities to share; time a launch or post for a demand window from the market-context calendar; ask each buyer to tag or share (aimed at strangers, not friends) |
| **Conversion** | Fix the profile and the link; pin the best-converting post; shorten the ordering path in DMs |
| **Margin** | Re-price one product; bundle two; ask the supplier or courier for a better rate |
| **Repeat orders** | A thank-you and next-drop message to past buyers; a small reorder incentive |
| **Capacity** | Batch making; limited pre-order drops; a dispatch schedule |

**Reach partners:** when reach is the bottleneck, rank candidate partners (fan pages, creators, communities) by audience match, location match, engagement (comments and shares per post, not followers), past results and cost, recommend the top few to approach each week, and afterwards record how many stranger leads each produced.

**Eligibility gate (kept, with new rules):**
- **No paid ads** (no budget); anything over the owner's weekly hours or budget is blocked, with the reason shown.
- Needs missing data → blocked, with the reason.
- **Brand and IP risk (rule-based, general):** some products use protected names, logos or characters (for Box Box: F1, team names, logos, driver names). The advisor flags protected terms found in product or design names and shows a plain "this is not legal advice" warning, more strongly when a reach action would raise visibility.

## 4. The daily lead list (from the lead score)

Backend 1 scores each lead as Hot, Warm, Cold or Disqualified. You turn that into actions and drafts:

| Group | What the advisor tells the owner | What it drafts |
|---|---|---|
| **Hot** | Reply today, most recent enquiry first | A personal reply that answers the exact question, with the price and an order link or payment details |
| **Warm** | Contact once when there is a reason: a new drop, a restock, a small first-order offer | A short message tied to the product they showed interest in |
| **Cold** | Do nothing one to one; they see regular posts | Nothing |
| **Disqualified** | Reply politely once, no follow-up | A short "not available yet" reply |

Each entry shows the reasons behind the score (the evidence). **The advisor drafts, the owner sends:** there is no send endpoint. A Warm lead is contacted once per reason. Disqualified leads are summarised by reason as unmet demand (a size, design or city people keep asking for).

## 5. Next month's sales

Backend 1 computes a transparent projection with a range. You show it, explain it with its basis, and tie the one bottleneck to the next month: "the projection is X to Y orders; the bottleneck that most limits it is Z; here is what to do". It is always labelled an **estimate**.

## 6. Follow-up every week (what makes it an advisor, not a report)

Each week: record what was done, read the new facts (point in time, so week 1 never sees week 2), compare with the frozen baseline, then **double down on what worked and drop what did not**.
- **Main measure:** orders from strangers, week over week.
- Separate **fidelity** (was the action done?) from **effectiveness** (did the number move?). Results are labelled observational: no control group, and one business is not proof.
- Four-week arc: week 1 collect, diagnose, first actions; weeks 2 and 3 review and adjust; week 4 compare stranger orders against week 1 and write down which advice worked and why. In the demo, weeks 2 to 4 come from a **scripted, labelled replay**.

## 7. The LLM boundary (kept)

- **Input:** an evidence packet: the profile, the facts and sources it may use, the allowed actions.
- **Output:** JSON validated against a schema.
- **Validator rejects:** unknown evidence ids, numbers not in the packet, actions outside the library, constraint violations. Retry once, then deterministic fallback text.
- **Cache** so the demo works offline. Drafts are **previews only**.
- The LLM never computes a fact and never chooses the bottleneck.

## 8. Tasks and status (reuse refers to code already in `backend/decision_engine/`)

| # | Task | Reuse | Stage |
|---|---|---|---|
| 1 | **Contract v2** with Soham (facts, lead, projection, context, weekly snapshots) | `DataClient` | S3, first |
| 2 | **Bottleneck scoring** for the five families with the four tests; evidence on every finding | Signal framework | S3 |
| 3 | **Action library** for the five bottlenecks (generic), including reach partners and demand-window timing; research reviews the content | Template loader | S3 |
| 4 | **Eligibility rules**: no paid ads, owner hours, missing data, brand risk | Eligibility gate | S3 |
| 5 | **Ranking of actions** (visible formula; ties broken by effort) and the 1 to 3 selection | Priority scorer | S3 |
| 6 | **Daily lead list** with drafted replies (Hot, Warm, Cold, Disqualified) | Drafts | S3 |
| 7 | **LLM explanation** with the validator, cache and fallback | LLM layer | S4 |
| 8 | **Weekly follow-up**: record done, compare weeks, adjust | Outcome ledger and planner | S4 |
| 9 | **Next-month explanation** using the projection | – | S4 |
| 10 | Grounded chat citing fact ids; tests including one finding checked by hand end to end | Chat, tests | S4, if time |

**Legacy (to be removed once replaced):** ad-channel anomaly detection, ad-spend and hot-lead-of-a-brand rules, the day-7 replay format.

## 9. Integration

On `backend-integration` (with Soham) you switch to `DATA_SOURCE=local` so you call `data_engine` in-process. The loop to walk end to end: load week 1 → diagnose → advise → daily lead list → record what was done → load week 2 → follow up. See `BACKEND.md` section 10.

## 10. Definition of done

- Given week-1 facts for Box Box and for the home baker, the engine names one bottleneck, shows two runners-up, and every finding carries claim, number, source and confidence.
- Weekly actions respect the owner's constraints, and blocked actions show why.
- The daily list gives a drafted reply for every Hot lead, and nothing is ever sent.
- The weekly follow-up reports stranger orders week over week and what changed.
- No number shown to the owner comes from the LLM.
- Tests pass; you can say exactly what is real, precomputed or mocked.
