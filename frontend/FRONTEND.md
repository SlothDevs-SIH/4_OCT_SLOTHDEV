# Frontend: all UI/UX (Kaushal)

**Stack:** Next.js + TypeScript, Tailwind (shadcn-style components), Recharts or Plotly for charts.
**Contract:** [`../contracts/API_CONTRACT.md`](../contracts/API_CONTRACT.md) and `../contracts/fixtures/`. You build against fixtures first, then swap in the real backends as each milestone lands.
**Branch:** `frontend`. You edit only `frontend/`. Deploy target: a public link the judges can open in one click.

## 1. The product the UI must make obvious

> A seven-day growth operating system. Not a chatbot: **evidence → priority → action → measured outcome.**

The user is an Indian D2C / service SMB owner (2–30 people) with spreadsheets and no analyst. Demo business: **Aarohi Skin** (Pune, synthetic: always show a "Demo data" badge).
The owner should be able to answer in ten seconds: *What is wrong? Why do you say that? What should I do first? Did it work?*

## 2. Mock-first setup (so you're never blocked by the backends)

```bash
cd frontend
npx create-next-app@latest app --typescript --tailwind --eslint --app --no-src-dir --import-alias "@/*"
```

Put the app in `frontend/app/`. Then:

1. **API layer:** one file `frontend/app/lib/api.ts` exposing a function per contract endpoint. Base URL from `NEXT_PUBLIC_API_BASE`.
2. **Mock mode:** `NEXT_PUBLIC_USE_MOCKS=true` makes `api.ts` return the JSON from `contracts/fixtures/` (copy or import them into `frontend/app/mocks/`). Same shapes as the real API, so turning mocks off is a one-line change.
3. **Dev proxy until the gateway exists** (`next.config.js`): rewrite `/api/v1/*` to `http://localhost:8001` for data_engine paths and `http://localhost:8002` for decision_engine paths. Paths owned by each module are listed in the contract (sections 3 and 4). After integration, point `NEXT_PUBLIC_API_BASE` to the gateway on port 8000 and delete the rewrites.
4. **Types:** write TypeScript types straight from contract section 2 (KPI fact, lead score, signal, recommendation, plan/task, outcome).
5. Copy `.env.example` values you need into `frontend/app/.env.local` (never commit it).

## 3. Work in stages (matches the backend milestones)

You work on one part of one backend at a time, then the other. Each stage is: build the screen on mocks, then connect it to the real endpoint when the backend owner announces the milestone.

| Stage | Time | Build the UI for | Backend part | Backend milestone |
|---|---|---|---|---|
| **F0** | 10:00–10:45 | Project setup, layout, navigation, design tokens, API layer, mock mode, "Demo data" badge, loading/empty/error components | – | – |
| **F1** | 10:45–12:00 | **Onboarding** (business type, goal, constraints, weekly capacity) and **Import + mapping + data-quality report** (upload, suggested mapping, repaired/quarantined counts, confidence badge) | **backend-1 part 1** | M1 at 11:30 |
| **F2** | 12:00–1:00 | **Recommendation feed**: signals, ranked recommendation cards, **priority-factor breakdown**, evidence links, blocked-recommendation state, approve/reject | **backend-2 part 1** | M2 at 12:00 |
| – | 1:00–1:30 | Lunch | | |
| **F3** | 1:30–2:15 | **KPI scorecard + funnel + metric provenance** (numerator/denominator/definition) and **lead queue** with probability, baseline, SHAP-style reasons, abstention state, model card drawer | **backend-1 part 2** | M3 at 1:30 |
| **F4** | 2:00–2:45 | **7-day plan** (timeline by day, owner, KPI, success criterion, dependencies), task status, **draft preview** (WhatsApp/email, "requires approval"), **Outcome review** (day-7: baseline vs expected vs actual, promising/inconclusive) | **backend-2 part 2** | M4 at 2:00 |
| **F5** | 2:45–3:30 | Full-stack integration on `fullstack-integration`, demo mode path, polish | all | integration |
| – | 3:30 | **Feature freeze.** After that: bug fixes only. | | |

If a milestone slips, keep going on mocks. Don't wait.

## 4. Screens and what each must show

### S1. Onboarding
- Business type (D2C / service), city, currency (INR), goal (a KPI + sentence), constraints (weekly execution hours, weekly discretionary budget in INR, forbidden actions, lead-response SLA).
- A "Load demo business (Aarohi Skin)" button (`POST /demo/load`). This is the fast path for the demo.

### S2. Import and data quality
- Upload three CSV types: campaigns, leads, orders.
- **Suggested mapping table** (source column → canonical field, editable, confirm button).
- **Quality report:** rows loaded / repaired / quarantined, issue list with counts and examples (duplicates, missing campaign ID, mixed date formats), attribution coverage, **confidence badge**.
- This screen proves "we do real data engineering", so make the messy-data story visible.

### S3. Dashboard (KPI scorecard)
- KPI cards: value, baseline, delta (colour-coded and with an arrow/label: don't rely on colour alone), small trend chart.
- **Provenance on click:** numerator, denominator, definition version, source, quality flag.
- Funnel view (traffic → lead → qualified → opportunity → won → first order → repeat).
- **Every number comes from the API.** No hardcoded numbers in components.

### S4. Lead queue
- Ranked list: name, channel, calibrated probability vs portfolio baseline, expected value, hours since last touch.
- Row expands to show top positive/negative factors, the recommended action, and a note "association, not causation".
- **Abstention state:** "Needs data" with the missing fields, not a made-up score.
- A small "model card" drawer: model, data, split, PR-AUC, Brier, lift@10%, caveat.

### S5. Recommendations (the hero screen)
- Ranked cards with title, problem, recommended action, expected KPI direction/range, effort, cost, confidence.
- **Priority breakdown:** the nine factors (I,U,F,R,T,Q,E,C,D) as a small bar/table plus the formula, so judges see *why* hot-lead follow-up ranks above "increase ad spend".
- **Evidence chips** linking to the KPI fact or lead (`evidence_ids`).
- **Blocked state:** "Increase Instagram ad spend: blocked. Violates: do not increase total acquisition spend."
- Approve / Reject. Anything touching spend, outreach, or data changes shows "Requires your approval".
- A data-confidence badge next to each recommendation.

### S6. 7-day plan
- Day-by-day timeline with task cards: title, reason, effort, owner, KPI, success criterion, dependencies.
- Status toggle (todo / doing / done) calling `PATCH /tasks/{id}`.
- Capacity bar: planned hours vs the weekly limit.
- **Draft preview** for WhatsApp/email with a clear "Preview only: not sent. Needs approval" label.

### S7. Outcome review (day 7)
- Per recommendation: baseline, expected range, actual, fidelity (executed or not), effectiveness (promising / inconclusive / not effective), and the "observational, no control group" note.
- A "Switch to day-7 data" action (`POST /demo/load?phase=day7`, then `POST /plans/{id}/outcomes/evaluate`).

### S8. Grounded chat (should-have)
- Answers cite `fact_id` chips. If the backend returns 501, hide the screen.

## 5. UX rules

- **Trust first:** show what we know, what we inferred, confidence, and what would falsify it. Use the words "estimate", "expected range", "observational" instead of "will".
- Always show the "Demo data" badge on synthetic data. Never present scenario numbers as real-world impact.
- Clear **loading, empty, error, and 501 "coming soon"** states on every screen (the backend returns 501 for unimplemented endpoints).
- Mobile-friendly (judges and owners may open it on a phone); keyboard navigable; colour is never the only signal (contrast >= 4.5:1).
- Optional language toggle (English / Hindi / Marathi) for **explanations only**: metrics stay language-neutral. Put strings in a dictionary from the start.
- The demo path must work without the network: keep mocks and a recorded fallback.

## 6. Demo path to keep working at all times (3 minutes)

1. Onboarding → "Load Aarohi Skin" → 2. Import the messy CSV; show mapping and the quality report → 3. Dashboard KPI evidence (CAC up, Instagram conversion down, email repeat up) → 4. Lead queue with reasons and one abstention → 5. Recommendations: hot-lead follow-up ranks above "increase ad spend", which is blocked → 6. Approve and generate the 7-day plan → 7. Switch to day 7 and show expected vs actual.

The research branch owns the script (`research/RESEARCH.md`, "Demo script"). Rehearse this exact path on the deployed build.

## 7. Definition of done

- Every screen works on mocks and on the real API.
- No hardcoded business numbers; types match the contract.
- Loading/empty/error states exist; no unhandled promise rejections in the console on the demo path.
- Deployed link works in an incognito window on a phone.
- The README in `frontend/` has run/build/deploy steps.

## 8. Folder layout (suggested)

```
frontend/
  FRONTEND.md          this file
  app/                 the Next.js app (created with create-next-app)
    app/               routes: onboarding, import, dashboard, leads, recommendations, plan, outcomes
    components/        KpiCard, LeadRow, RecommendationCard, PriorityBreakdown, EvidenceChip, ...
    lib/api.ts         one function per contract endpoint (+ mock mode)
    lib/types.ts       types from contract section 2
    mocks/             copies of contracts/fixtures/*.json
```
