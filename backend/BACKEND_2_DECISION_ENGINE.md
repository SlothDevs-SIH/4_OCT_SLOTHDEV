# Backend 2: `decision_engine` (Ayush), Diagnosis, Advice and Follow-up

Branch: `backend-2`. You edit only `backend/decision_engine/`. Port 8002. Overview of both backends: [`BACKEND.md`](BACKEND.md). Backend 1 (Soham, `data_engine`) produces the facts; you read them only through `DataClient`.

**Your job in one sentence:** from the facts, name the single biggest bottleneck among reach, conversion, margin, repeat orders and capacity, give the founder one to three actions for this week with the evidence behind each, and every week check what was done and what changed.

**The rule:** the calculations decide what is wrong; the LLM only explains, using numbers the engine produced. If a number is missing, the finding is not shown.

## 1. The user and what it means for the rules

Small early-stage maker-sellers: first 50 to 500 orders, selling through Instagram or WhatsApp, **no ad budget**, one to three people (often students with limited hours). Example: Box Box (F1 merchandise). Reach is the *likely* bottleneck for Box Box, but **the data decides, not the assumption**.

## 2. Diagnosis

| Step | What it does |
|---|---|
| **Score the five bottlenecks** | Reach, conversion, margin, repeat orders, capacity. Each is scored from backend 1's facts against a target. The first target is the business's **own best weeks**; typical figures per business type are added later and need a source |
| **Four tests per bottleneck** | Materiality (enough orders to matter), deviation (worse than its own best), localisation (which stage or source), actionability (a feasible action exists). Near-misses are listed as rejected, with the reason |
| **Pick one, show two runners-up** | The bottleneck with the largest estimated monthly value for the effort wins. Value = extra orders gained × margin per order. Effort is estimated from the founder's hours |
| **Evidence on every finding** | Four parts: the **claim**, the **number**, the **source** (which file or answer), the **confidence** (`exact` / `estimate` / `derived`) |
| **Low data = low confidence** | Under the minimum sample size the finding is shown as an estimate, or not shown. It is never dressed up |

## 3. Advice: one to three actions this week

Actions come from an approved library, keyed by bottleneck, then filtered by the founder's constraints. Each action has the evidence that chose it, an effort in minutes, a measurable target and a deadline.

| Bottleneck | Example actions (reviewed by research) |
|---|---|
| **Reach** (the Box Box case) | Collaborate with F1 fan pages; send product to small creators; post in college communities; time a design drop for a race weekend (backend 1 supplies the calendar); ask each buyer to tag or share (aimed at strangers, not friends) |
| **Conversion** | Fix the profile and link; pin the best-converting post; shorten the ordering path in DMs |
| **Margin** | Re-price one design; bundle two; ask the printer or courier for a better rate |
| **Repeat orders** | A thank-you and next-drop message to past buyers; a small reorder incentive |
| **Capacity** | Batch printing; limited pre-order drops; a dispatch schedule |

**Eligibility gate (kept, with new rules):**
- **No paid ads** (no budget), and any action over the founder's weekly hours or budget is blocked, with the reason shown.
- Needs missing data → blocked with the reason.
- **Trademark risk (new, rule-based):** the brief notes that F1, team names, logos and driver names are trademarked, so unlicensed merchandise risks takedowns as the brand gets more visible. The advisor flags protected terms found in design or product names and shows a plain "this is not legal advice" warning. The risk is shown more strongly when a reach action would raise visibility.

## 4. Follow-up every week (what makes it an advisor, not a report)

Each week: record what was done, read the new facts (point in time, so week 1 never sees week 2), compare with the frozen baseline, then **double down on what worked and drop what did not**.
- **Main measure:** orders from strangers, week over week.
- Separate **fidelity** (was the action done?) from **effectiveness** (did the number move?). Results are labelled observational: no control group, and one business is not proof.
- Four-week arc: week 1 collect, diagnose, first actions; weeks 2 and 3 review and adjust; week 4 compare stranger orders against week 1 and write down which advice worked and why.

## 5. The LLM boundary (kept)

- **Input:** an evidence packet: the profile, the facts and sources it may use, and the allowed actions.
- **Output:** JSON validated against a schema.
- **Validator rejects:** unknown evidence ids, numbers not in the packet, actions outside the library, constraint violations. Retry once, then deterministic fallback text.
- **Cache** so the demo works offline. Drafts (a DM, a caption, a collaboration pitch) are **previews only**; there is no send endpoint.
- The LLM never computes a fact and never chooses the bottleneck.

## 6. Tasks and status (reuse refers to code already in `backend/decision_engine/`)

| # | Task | Reuse | Stage |
|---|---|---|---|
| 1 | **Contract v2** with Soham (fact list, `source`, `sample_size`, weekly snapshots) | `DataClient` | S3, first |
| 2 | **Bottleneck scoring** for the five families with the four tests and rupee estimate; evidence on every finding | Signal framework (the four tests) | S3 |
| 3 | **Action library** for the five bottlenecks, including reach partners (F1 fan pages, creators, college communities) and race-weekend timing; research reviews the content | Template loader | S3 |
| 4 | **Eligibility rules**: no paid ads, founder hours, missing data, trademark risk | Eligibility gate | S3 |
| 5 | **Ranking of actions** (visible formula; ties broken by effort) and the 1 to 3 selection | Priority scorer | S3 |
| 6 | **LLM explanation** with the validator, cache and fallback; drafts | LLM layer, validator, cache | S4 |
| 7 | **Weekly follow-up**: record done, compare weeks, adjust | Outcome ledger and planner | S4 |
| 8 | Grounded chat that cites fact ids | Chat | S4, if time |
| 9 | Tests, including a hand-calculated check of one finding end to end | Existing tests | S4 |

**Retired:** ad-channel anomaly detection, the ad-spend and lead-based rules, the day-7 replay format (replaced by weekly snapshots).

## 7. Integration

On `backend-integration` (with Soham) you switch to `DATA_SOURCE=local` so you call `data_engine` in-process. The loop to walk end to end: load week 1 → diagnose → advise → record what was done → load week 2 → follow up. See `BACKEND.md` section 9.

## 8. Definition of done

- Given Box Box's week-1 facts, the engine names one bottleneck, shows two runners-up, and every finding carries claim, number, source and confidence.
- Weekly actions respect the founder's constraints, and blocked actions show why.
- The weekly follow-up reports stranger orders week over week and what changed.
- No number shown to the founder comes from the LLM.
- Tests pass; you can say exactly what is real, precomputed or mocked.
