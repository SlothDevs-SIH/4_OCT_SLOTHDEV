# Frontend Implementation Plan (Backend-Driven)

**Stack:** Next.js + TypeScript, Tailwind, Recharts.

This document serves as the single source of truth for the frontend implementation. The frontend is built incrementally to map directly to the backend functionalities (Backend 1A, 1B, 2A, 2B). We do not invent APIs or workflows that do not exist.

## 1. Project Frontend Overview
The product is a seven-day growth operating system designed for Indian D2C brands. It is not a generic tool; it focuses on measurable outcomes (evidence → priority → action → measured outcome). 

## 2. Existing Frontend Architecture
- **Framework:** Next.js with App Router.
- **Components:** Found in `frontend/app/components/` (AppShell, DraftView, TrendChart, ui).
- **API/Service Layer:** Segregated by backend (`backend1/backend1A.ts`, etc.) mapping to the specific backend functionality.
- **State Management:** Simple React hooks (`useAsync.ts`) managing loading, success, error, empty data states.
- **Authentication/Session:** Lightweight session context via `session.ts`. 

## 3. Backend Architecture Understanding
The backend is split into two independent modules:
- **Backend 1 (`data_engine`):** Data import, validation, KPI calculations, lead conversion scoring.
- **Backend 2 (`decision_engine`):** Anomaly detection, priority scoring, LLM synthesis (recommendations), 7-day plans, tasks, outcome ledgers.

## 4. Phase-Wise Implementation

### Phase 1 — Backend 1 Frontend

#### 1A Frontend
*Maps to Backend 1A: Onboarding, Demo Load, CSV Import, Data Quality.*
- **Screens/Routes:** `/` (Onboarding), `/import` (Data Import & Quality)
- **APIs:** 
  - `POST /businesses`, `GET /businesses`
  - `POST /demo/load`
  - `POST /businesses/{id}/imports/auto`
- **Functionality:** 
  - Business model configuration (D2C/hybrid).
  - CSV upload with suggested mapping.
  - Data quality report (repaired, quarantined).

#### 1B Frontend
*Maps to Backend 1B: KPI Engine, Funnel, Lead Queue, Lead Conversion Model.*
- **Screens/Routes:** `/dashboard` (KPIs & Funnel), `/leads` (Lead Queue)
- **APIs:**
  - `GET /businesses/{id}/kpis`
  - `GET /businesses/{id}/leads/queue`
- **Functionality:**
  - KPI scorecard with provenance.
  - Ranked lead queue with probability and expected value.
  - Model card drawer.

---

### Phase 2 — Backend 2 Frontend

#### 2A Frontend
*Maps to Backend 2A: Signals, Priority Gate, Recommendations.*
- **Screens/Routes:** `/recommendations`
- **APIs:**
  - `GET /signals`
  - `POST /recommendations/generate`
  - `POST /recommendations/{id}/approve`
- **Functionality:**
  - Recommendation feed (signals, ranked cards, priority breakdown).
  - Approve/Reject functionality.
  - Evidence chips (linking facts).

#### 2B Frontend
*Maps to Backend 2B: 7-day plan, Tasks, Outcomes.*
- **Screens/Routes:** `/plan`, `/outcomes`, `/chat`
- **APIs:**
  - `POST /plans`
  - `PATCH /tasks/{id}`
  - `POST /plans/{id}/outcomes/evaluate`
- **Functionality:**
  - Timeline of task cards.
  - WhatsApp/Email draft previews.
  - Day-7 outcome evaluation (expected vs actual).

---

### Phase 3 — Backend 1 + Backend 2 Integration
**[NOT IMPLEMENTED YET]**
- **Plan:** Only integrate once the backend gateway provides cohesive state coordination.
- **Expected Touchpoints:** Synchronizing business IDs between engines, shared session context.

### Phase 4 — Final Integrated Frontend
**[FUTURE PHASE]**
- **Plan:** To be implemented after End-to-End integration passes all tests.

## 5. Traceability Matrix

| Backend | API/Feature | Frontend Screen | Component | State | Status |
|---|---|---|---|---|---|
| 1A | `POST /businesses`, `POST /demo/load` | `/` (Onboarding) | `AppShell` | Loading/Success/Error | [COMPLETED] |
| 1A | `POST /businesses/{id}/imports/auto` | `/import` | UI layout | Loading/Empty/Success | [COMPLETED] |
| 1B | `GET /businesses/{id}/kpis` | `/dashboard` | `TrendChart`, KPI Card | Loading/Error | [COMPLETED] |
| 1B | `GET /businesses/{id}/leads/queue` | `/leads` | Lead Row, Drawer | Loading/Empty | [COMPLETED] |
| 2A | `GET /signals`, `POST /recommendations/generate` | `/recommendations` | `RecommendationCard` | Loading/Empty/Blocked | [COMPLETED] |
| 2B | `POST /plans`, `PATCH /tasks/{id}` | `/plan` | Task Card, `DraftView` | Loading/Success | [COMPLETED] |
| 2B | `POST /plans/{id}/outcomes/evaluate` | `/outcomes` | Outcome Matrix | Loading/Success | [COMPLETED] |

## 6. Testing Strategy
- User actions must be validated against actual endpoints using `NEXT_PUBLIC_USE_MOCKS=false` where available.
- Network failure, missing data, and error boundaries must be tested.

## 7. Known Limitations & Blockers
- **Pending Backend Dependencies:** Full backend-1 to backend-2 integration relies on the `gateway` routing properly. `decision_engine` currently connects via local HTTP requests.


## Run the site (what is built)

The app lives in `frontend/app` (Next.js 15, React 19, Tailwind 4 utilities, React Bits components). Pages: landing, `/login` (pick a demo business or start your own), `/signup`, and under `/dashboard`: overview, diagnosis, this week, daily lead list, weekly follow-up, next month, your data, ask a question, where the numbers come from.

```bash
# 1. backend: both modules behind one gateway (port 8000 is often taken, so 8011 here)
DATA_SOURCE=local python -m uvicorn backend.gateway.main:app --port 8011

# 2. frontend
cd frontend/app
npm install
printf 'NEXT_PUBLIC_API_BASE=http://localhost:8011
NEXT_PUBLIC_USE_MOCKS=false
' > .env.local
npm run dev                                   # http://localhost:3000
```

**Offline demo (no backend):** set `NEXT_PUBLIC_USE_MOCKS=true`. The app then replays recorded backend answers from `public/mock/`, so the demo path works with the network off. Re-record them with `python frontend/app/scripts/build_mocks.py` (from the repo root) after any backend change. Uploads, creating a business and pasted chats need the live backend and say so.

**Build check:** `npm run typecheck && npm run build`. `NEXT_DIST_DIR=.next-build npx next build` builds beside a running dev server.
