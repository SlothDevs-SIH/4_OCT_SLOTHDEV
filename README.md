# Slothdev GrowthOS

**Helpreneur AI Buildathon 2026 | PS3: AI Business Growth Advisor | Team Slothdev**

> A seven-day growth operating system that turns messy SMB data into explainable priorities, assigned actions and measured outcomes.

It is not a chatbot over business data. The loop is: **evidence → priority → action → measured outcome**.

```
data import → validation → KPIs + ML signals → bottlenecks/opportunities
   → eligibility gate → priority score → constrained LLM explanation
   → human approval → 7-day plan → day-7 outcome vs expected
```

Demo business (synthetic and labelled as such): **Aarohi Skin**, a Pune D2C skincare brand.

## Team and branches

| Branch | Owner | Folder they edit | What |
|---|---|---|---|
| `backend-1` | Soham | `backend/data_engine/` | Data and intelligence: import, validation, KPIs, lead-conversion ML |
| `backend-2` | Ayush | `backend/decision_engine/` | Decision and action: signals, priority score, LLM, plan, outcomes |
| `frontend` | Kaushal | `frontend/` | All UI/UX |
| `research` | Vedashree | `research/` | Model analysis, innovation, evaluation, demo and pitch material |
| `backend-integration` | Soham + Ayush | `backend/gateway/` | Merges `backend-1` + `backend-2` into one API |
| `fullstack-integration` | Kaushal + Soham | all | Merges `backend-integration` + `frontend` (+ `research`) |

`main` holds the shared scaffold, `contracts/` and docs. Final code is merged into `main` at the end.

## Where to read

| Doc | For |
|---|---|
| [`docs/WORKFLOW.md`](docs/WORKFLOW.md) | Branch rules, merge flow, timeline, git commands |
| [`backend/BACKEND.md`](backend/BACKEND.md) | Backend overview, the two modules side by side, integration plan |
| [`backend/BACKEND_1_DATA_ENGINE.md`](backend/BACKEND_1_DATA_ENGINE.md) | Soham's module: tasks, data rules |
| [`backend/BACKEND_2_DECISION_ENGINE.md`](backend/BACKEND_2_DECISION_ENGINE.md) | Ayush's module: tasks, scoring, LLM rules |
| [`frontend/FRONTEND.md`](frontend/FRONTEND.md) | Screens, stages, mock-first approach |
| [`research/RESEARCH.md`](research/RESEARCH.md) | Decisions from the research, models, evaluation, demo |
| [`contracts/API_CONTRACT.md`](contracts/API_CONTRACT.md) | The shared API and data contract (all branches code against this) |

## Status

Docs, the shared contract, example fixtures (`contracts/fixtures/`), shared backend stubs and the Postgres schema (`db/schema.sql`) are on `main`. Run instructions: `backend/BACKEND.md` section 2.

## Rules we follow

- Built during the event. Public libraries, datasets and APIs are listed in the README of each module under "Pre-existing components".
- No secrets in the repo. Use `.env`.
- Every claim in the demo is backed by something built or measured. Synthetic data is always labelled synthetic.
