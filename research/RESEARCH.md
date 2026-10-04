# Research, model analysis and innovation (Vedashree)

**Branch:** `research`. You edit only `research/`. Your job: make sure what we build is **well-chosen, correctly evaluated and convincingly explained**, and keep the team honest about what's real.

**Source:** the Perplexity research report (`research_perplexity_perplexity.pdf`, 4 Oct 2026, kept locally, not in the repo). Section 1 below is its decisions in short. The report is AI-generated and cites sources: **verify any fact (prices, product features, dataset licences) before it goes on a slide.**

## 1. Decisions already made (from the research)

| Decision | Choice | Why |
|---|---|---|
| Problem statement | **PS3: AI Business Growth Advisor** | Workflow fits our skills: data, KPIs, prediction, prioritisation, action plan |
| Product | **Slothdev GrowthOS**, a 7-day growth operating system for **Indian D2C (direct-to-consumer) brands** | Judges' advice: don't be generic. One model, deeply: D2C has a measurable first-party funnel, high acquisition cost, repeat-purchase economics and India-specific levers (COD/RTO, WhatsApp, festive seasons) |
| Model profiles | `d2c` (built), `hybrid` = D2C + bulk/B2B inquiries (built in the demo), `b2c_retail` (profile only, if time) | Covers D2C, hybrid and B2C without pretending to serve everyone |
| Core loop | validated data → KPI facts → ML signals → rules → candidate interventions → **priority score** → constrained LLM explanation → human approval → tasks → **outcome tracking** | The defensible part is the loop, not the chat |
| ML scope | **Two components only:** (1) calibrated lead-conversion probability, (2) anomaly/bottleneck detection. RFM as transparent analytics, not a headline model | Depth and honest evaluation beat ten shallow models |
| Datasets | UCI **Bank Marketing** (lead conversion; **drop call duration**), UCI **Online Retail II** (RFM/cohorts), plus a **synthetic relational demo tenant** ("Aarohi Skin") | Public datasets can't be truthfully joined; synthetic tenant unifies the story and is labelled synthetic |
| Stack | Next.js (Vercel) + FastAPI + PostgreSQL (Supabase); scikit-learn used offline; LLM API behind an interface | Fast to build, publicly hosted, light at runtime (see `backend/BACKEND.md` sections 3 and 5) |
| LLM role | Explain and instantiate tasks from **evidence packets**; never calculate KPIs or invent evidence | Prevents hallucinated numbers |
| Human in the loop | Approval for spend, outreach and data-changing actions | Safety |
| Avoid | Ten models, autonomous spending, knowledge graph, Kubernetes, real-time streaming, scraping competitors, causal-ROI claims without experiments, joining unrelated public datasets | Scope and honesty |

**Honest positioning (from the research):** incumbents already do chat-over-data, CRM scoring, anomaly alerts and agents (Zoho Zia, HubSpot Breeze, Salesforce, Shopify Sidekick, Tableau Pulse, Looker, ChatGPT/Gemini with connectors). So *"personalised advice"*, *"multi-source data"* and *"AI recommendations"* are **not** differentiators. Ours is: an evidence-linked, effort-aware, transparent recommendation compiler plus an expected-vs-actual outcome ledger, packaged for low-setup SMB use. Call it an **architectural/product innovation, not a new ML algorithm.**

## 1b. Judges' feedback and what we changed

Feedback at the 11:00 meeting: **don't make it too generic** (a medical shop and a clothing shop need different analytics). Our response: **D2C brands**, with `hybrid` and `b2c_retail` as profiles. Write the slides, script and Q&A around D2C:
- *Who:* founder/growth lead of an Indian D2C brand.
- *Pain:* rising customer acquisition cost, unattended high-value inquiries, repeat-purchase potential left unused.
- *India-specific levers:* COD vs prepaid, returns/RTO, WhatsApp follow-up, festive seasons, UPI.
- Say what is **built** (D2C and the hybrid bulk-inquiry segment) and what is **profile only** (`b2c_retail`).

## 2. Your deliverables

Work in this order. Each item says who needs it and when.

| # | Deliverable | File | Needed by | Who uses it |
|---|---|---|---|---|
| R1 | **Dataset readiness:** confirm Bank Marketing and Online Retail II are downloadable, record licence/citation terms, list columns, confirm the duration column is excluded, note target definition and class balance. Hand the checked file paths/notes to Soham | `research/datasets.md` | 10:45 | Soham (backend-1 task 5) |
| R2 | **Model analysis** (section 3): a model card per component with rationale, alternatives rejected, metrics, risks | `research/models.md` | 11:30 | Soham, Ayush, slides |
| R3 | **D2C intervention library:** 12–15 approved action templates specific to D2C (trigger, eligibility, KPI, expected direction, effort, cost, time-to-signal, approval, risks). Include abandoned-cart recovery, COD-to-prepaid nudge, RTO/return reduction, repeat-buyer flow, WhatsApp win-back, bundle/AOV offer, creative test, landing-page fix, restock/replenishment reminder, review request, plus the blocked "increase ad spend" Extend the seed in `contracts/fixtures/intervention_templates.json` and send changes to `main` per `docs/WORKFLOW.md` section 3 | `research/intervention_library.md` (+ the fixture) | 12:00 | Ayush (backend-2 tasks 1, 4, 5) |
| R4 | **Evaluation plan and acceptance gates** (section 4) | `research/evaluation.md` | 12:30 | Soham, Ayush |
| R5 | **Golden set:** 30–50 recommendation cases scored on the rubric in section 4. Start with the 4 demo recommendations | `research/golden_set.csv` (template included) | 2:00 | backend-2 evaluation, slides |
| R6 | **Innovation and differentiation** (section 5): competitor one-pager, our wedge, claims ledger | `research/innovation.md`, `research/claims_ledger.md` | 1:30 | slides, Q&A |
| R7 | **Reality checks on backend outputs:** sanity-check units and numbers coming out of backend-1/2 (a hand calculation for 3 KPIs; check the demo story is internally consistent) | comments in PRs / `research/checks.md` | rolling, 12:30 on | everyone |
| R8 | **Demo script, slides (5–7), problem-and-solution text, video storyboard** (section 7) | `research/demo_script.md`, `research/slides_outline.md`, `research/problem_solution.md` | 3:30 (drafts at 2:30) | whole team |
| R9 | **Q&A bank** with answer skeletons and risk register (section 8) | `research/qa_bank.md`, `research/risks.md` | 4:30 | whole team |

If time gets tight, do R1, R3, R5 (the 4 demo cases), R7 and R8 first. They directly improve the demo and the build.

## 3. Model analysis to write (R2)

For each component write: **what it does, why this model, alternatives considered, features, metrics, known failure modes, how we explain it.**

| Component | Choice | Notes to research and write up |
|---|---|---|
| **Lead-conversion probability** | Logistic regression baseline; gradient-boosted trees (HistGradientBoosting / LightGBM / XGBoost) as challenger; **probability calibration** (isotonic or sigmoid) | Why a baseline first. Why calibration matters (probabilities drive prioritisation). Class imbalance handling. **Leakage:** call duration is unknown before outcome, so exclude it. Time-based split. Features available at prediction time only |
| **Explainability** | LR coefficients (global), SHAP (local, for trees) | Show top positive and negative factors; **only actionable factors drive advice** (response latency, engagement, stage age); never advise on non-actionable or protected traits; "association, not causation" |
| **Anomaly / bottleneck detection** | Seasonal median/MAD robust z-score baseline; Isolation Forest challenger; change-point rules | Compare on the **injected incidents**; if similar, ship the simpler one. Four tests for a bottleneck: materiality, deviation, localization, actionability |
| **Segmentation (analytics only)** | Quantile RFM (K-means only if stable and actionable) | Evaluate by stability and actionability, not silhouette alone |
| **Priority scorer (not ML)** | The transparent equation in `contracts/API_CONTRACT.md` 2.4 | Explain each weight; sanity-test with edge cases; explain why a visible equation beats an opaque model with sparse outcome data; weights are a documented assumption to be calibrated later |
| **LLM** | Provider behind an interface; JSON-schema constrained output; validator; cache | Compare **2 providers** on a small test: JSON-schema adherence, hallucinated numbers, latency, cost, rate limits. Recommend one + a fallback. Document the prompt/evidence-packet design |
| **Outcome evaluation** | Expected-vs-actual with baseline, range, fidelity vs effectiveness, observational label | Why we don't claim causality without a control/holdout; later idea: conservative Bayesian shrinkage of template reliability |
| **Forecasting, churn model, next-best-action ML, knowledge graph, RL** | **Not built** | Write one line each on why not now (data/time/honesty). This is "future scope" and shows judgement |

Also record **what's possible in 8 hours and what isn't**, so no one over-promises.

## 4. Evaluation plan (R4) and golden set (R5)

**Acceptance gates** (no universal accuracy target is defensible before experimenting):
- Lead model beats the prevalence/prior baseline on **PR-AUC**; improves **lift in the top follow-up capacity band** (e.g. lift@10%); reasonably calibrated (**Brier score**, reliability diagram); stable across time/channel slices.
- Anomaly detector: event-level **precision/recall** on injected incidents, **false alerts per week**, **detection delay**; use the simple method if the challenger isn't clearly better.
- Import validation: every injected data issue is detected; none silently dropped.
- Plans: total hours <= weekly capacity; dependencies respected; every task has a KPI and success criterion.
- Recommendations: pass the golden-set rubric.

**Golden-set rubric (score each 0–2):** evidence correctness · consistency with rules/constraints · feasibility · specificity · expected-impact logic · uncertainty disclosure · harmlessness. Template: `research/golden_set_template.csv`. Ask a business mentor to review a sample if one is reachable.

**Report honestly:** held-out data, N, baseline, slices, failure cases. No number without its context.

## 5. Innovation and differentiation (R6)

Write one page each:
1. **Competitor map** (short): the groups above and what each already does; where they stop (no D2C-specific experiment ledger, insight stops before outcome, enterprise setup).
2. **Our wedge, in one sentence:** "Unlike [X], which [does A], GrowthOS [does B] so that [C]."
3. **Innovation list we can defend** (only things we actually build): evidence-linked recommendation compiler · visible priority equation with hard eligibility gate · data-quality-aware abstention · calibrated lead value · human-approved plan · day-7 expected-vs-actual ledger.
4. **India-specific parts that change decisions** (not "Indian English"): INR/GST fields, Indian fiscal year, festival seasonality, WhatsApp-first task drafts with consent, UPI/PSP export normalisation (future), regional-language explanation layer. Say which are built and which are future scope.
5. **Claims ledger** (`research/claims_ledger.md`): every claim we plan to make on slides/video, with status (built / partial / mocked / planned) and evidence. Update from 10:00; freeze at 5:00; cut anything the final video doesn't show.

## 6. Dataset and synthetic-data notes (supports R1 and backend-1)

- **Bank Marketing:** use as the supervised-learning proof. Remove call duration. Chronological split.
- **Online Retail II:** customer analytics (RFM, repeat, cohorts). Handle cancellations, negative quantities, missing customer IDs, recency cutoffs. Use standalone.
- **Synthetic "Aarohi Skin":** generated from a causal skeleton (season + channel + spend → clicks → leads → opportunity → win → order → repeat), not independent random columns. Injected incidents: Instagram CAC spike; 8 high-value leads past SLA; improving email repeat cohort; plus data issues (duplicate leads, missing campaign IDs, mixed date formats). Validate: schema/keys, business invariants, funnel ratios, seasonality plots. Always labelled synthetic.
- Never claim real-world uplift from synthetic results. All demo outcomes are **scenarios**.

## 6b. Key numbers in the demo story (so everyone says the same thing)

Source of truth: `contracts/fixtures/`. If the backends generate different numbers, update the script, not the other way round.

| Fact | Value |
|---|---|
| Business | Aarohi Skin, Pune, D2C skincare, 3 SKUs (synthetic) |
| Goal | Improve contribution revenue without increasing total acquisition spend |
| Constraint | 8 execution hours and Rs 10,000 discretionary budget per week; response SLA 4 h |
| Incident 1 | Instagram CAC Rs 612 vs Rs 410 baseline (+49%); conversion 2.1% vs 3.4%; contribution ROAS 0.82 vs 1.45 |
| Incident 2 | 8 high-value leads waiting ~19 h vs a 4 h SLA |
| Opportunity | Email cohort repeat purchase 31% vs 24% |
| Top recommendation | Follow up with the 8 hot leads: priority 69.3 |
| Others | Email repeat-buyer flow 45.1; Instagram audit + bounded test 44.2 |
| Blocked | "Increase Instagram ad spend": violates the no-spend-increase constraint |
| Day-7 replay | Hot-leads: promising; email flow: inconclusive; Instagram test: inconclusive (scenario numbers) |

## 7. Demo script, slides and submission text (R8)

**Demo script (3 minutes, from the research):**

| Time | Beat |
|---|---|
| 0:00–0:25 | **Problem.** "Aarohi has dashboards and spreadsheets but can't decide whether to fix ads, chase leads or invest in retention." |
| 0:25–0:55 | **Input and trust.** Upload three files; show mapping, duplicates, missing attribution and quarantined-row count. Judges see data engineering, not a prompt box |
| 0:55–1:30 | **Intelligence.** KPI evidence (CAC up, Instagram conversion down, email repeat up); calibrated lead queue with reasons and one abstention |
| 1:30–2:05 | **Decision.** Three recommendations and the factor breakdown. Hot-lead follow-up outranks "increase ad spend" (blocked by the constraint) |
| 2:05–2:40 | **Action.** Generate the 7-day plan (owner, due date, KPI, success criterion, dependency). Show a WhatsApp/email draft preview that needs approval |
| 2:40–3:10 | **Measurement.** Switch to the day-7 snapshot: task fidelity and expected vs actual; one intervention promising, one inconclusive |
| 3:10–3:30 | **Thesis.** "This is not data-to-chat. It is data → evidence → priority → action → measured outcome." |

Record a fallback video and keep cached LLM responses in case connectivity fails.

**Submission pieces to draft** (the rules require all five): working prototype link · repo/deployed link · **2–3 min demo video** · **5–7 slide deck** (suggested: 1 title+problem, 2 users and pain, 3 solution loop, 4 live demo screenshots, 5 AI/tech and evaluation, 6 differentiation and India fit, 7 impact, limitations and next steps) · **short problem-and-solution description**.

**Impact statements (honest):** process outcomes first: time-to-decision, unresolved data errors, plan completion, recommendation acceptance/edit rate, top-k lead lift, calibrated expected-vs-actual impact. If we state time saved, measure it (time one weekly analysis manually vs assisted, report medians and N). Don't claim a conversion uplift without a baseline or control.

## 8. Judge Q&A and risks (R9)

Prepare short, evidence-backed answers to:
- "Isn't this just ChatGPT on business data?" (Answer from section 1 and the research: the moat is the application state, evidence model and measurement loop, not the LLM.)
- "Where is the AI?" · "Why these two models?" · "How do you know the lead model works?" (held-out, baseline, calibration) · "What stops hallucinated numbers?" (deterministic KPIs, evidence IDs, validator) · "What's real and what's mocked?" · "Is the data real?" (synthetic tenant, labelled) · "How does it help an Indian SMB?" · "What happens if the LLM is down?" (cache and deterministic fallback) · "Who owns the data and how is privacy handled?" · "What would you build next?"

**Risk register** (starting point from the research): hallucinated recommendation · bad input data · data leakage · correlation treated as causation · privacy breach · too-broad MVP · competitor imitation · sparse outcome data · demo failure. For each: mitigation and who owns it.

## 9. How you work with the others

- **Soham (backend-1):** you give him dataset notes (R1) and the model analysis (R2); he gives you model metrics (the `model_card`).
- **Ayush (backend-2):** you give him the intervention library (R3) and the golden set; he gives you anomaly metrics and recommendation outputs for review.
- **Kaushal (frontend):** you give him UX copy (plain-language labels, "estimate/expected range/observational" wording, tooltips for KPI definitions) and the demo script.
- Read their PRs for **numbers that don't make sense**. This is the highest-value thing you can do: a wrong unit or an impossible ratio found at 1 PM saves the demo.

## 10. Definition of done

- Every deliverable above exists, is accurate and is cross-checked against what's built.
- Every slide claim appears in the claims ledger with evidence.
- The team can answer the Q&A bank without notes.
- Sources are named; AI-generated claims were verified before use.
