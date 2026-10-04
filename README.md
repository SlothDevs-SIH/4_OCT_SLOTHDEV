# Catalyst AI

**Helpreneur AI Buildathon 2026 | PS3: AI Business Growth Advisor | Team Slothdev**

> A free growth advisor for **home-business owners**. It takes whatever data they already have, however messy, finds the one thing holding the business back, and tells them what to do this week and what to focus on for next month's sales. Then it checks back every week.

**Who it is for:** anyone who makes or sells something (shirts, candles, baked goods, jewellery, anything), takes orders through Instagram or WhatsApp, has no ad budget, and runs the business alone or with one or two others. The first case study is **Box Box**, an F1 merchandise seller. Existing tools show a seller their numbers; Catalyst AI tells a seller with no dashboard, no ad budget and no team what to do next.

**The loop:** intake → diagnosis (one of five bottlenecks: reach, conversion, margin, repeat orders, capacity) → advice (1 to 3 actions with evidence, plus a daily list of leads to answer) → weekly follow-up.
**Main measure:** orders from **strangers**, not from friends.
**The rule:** the calculations decide what is wrong; the AI reads messy input and explains the result. Every finding shows its evidence.

## Team and branches

| Branch | Owner | Folder | What |
|---|---|---|---|
| `backend-1` | Soham | `backend/data_engine/` | Intake, metrics, lead scoring, projection, public data |
| `backend-2` | Ayush | `backend/decision_engine/` | Diagnosis, advice, daily lead list, weekly follow-up |
| `frontend` | Kaushal | `frontend/` | The mobile-first web app |
| `research` | Vedashree | `research/` | Research, action library, demo, claims |
| `backend-integration` | Soham + Ayush | `backend/gateway/` | Merges the two backends |
| `fullstack-integration` | Kaushal + Soham | all | Merges backend and frontend |

`main` holds the shared docs and contract. Details: [`docs/WORKFLOW.md`](docs/WORKFLOW.md).

## Where to read

| Doc | For |
|---|---|
| [`docs/DATASET.md`](docs/DATASET.md) | Every dataset we use, why, licences, measured numbers, limits |
| [`backend/BACKEND.md`](backend/BACKEND.md) | Backend overview, the five bottlenecks, what is real vs not built |
| [`backend/BACKEND_1_DATA_ENGINE.md`](backend/BACKEND_1_DATA_ENGINE.md) | Soham's module: intake, facts, lead scoring, projection |
| [`backend/BACKEND_2_DECISION_ENGINE.md`](backend/BACKEND_2_DECISION_ENGINE.md) | Ayush's module: diagnosis, advice, follow-up |
| [`contracts/API_CONTRACT.md`](contracts/API_CONTRACT.md) | The shared API and data contract (v2 draft) |
| [`frontend/FRONTEND.md`](frontend/FRONTEND.md) | Screens and approach for Kaushal |
| [`research/RESEARCH.md`](research/RESEARCH.md) | Vedashree's deliverables, competitors, demo script, Q&A |

## Quick start (backend, from the repo root)

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv/Scripts/activate
pip install -r backend/requirements.txt
cp .env.example .env                                   # keys stay local, never committed
uvicorn backend.data_engine.main:app --port 8001 --reload
uvicorn backend.decision_engine.main:app --port 8002 --reload
DATA_SOURCE=local uvicorn backend.gateway.main:app --port 8000 --reload   # both merged
python -m pytest backend -q
```

Public data: `GET /api/v1/public-data` and `GET /api/v1/market-context` (see `docs/DATASET.md` for how to download the raw files).

## Status

Docs and the shared contract are on `main`. Backend 1 has the import pipeline, order metrics, public-data modules and the contact-history model built and tested; backend 2 has the decision loop built for an earlier plan and is being re-pointed at the five bottlenecks. **Some earlier code and fixtures (a D2C-brand demo called "Aarohi Skin") are legacy** and are removed once the new engine replaces them.

## Rules we follow

- Built during the event. Public libraries, datasets and APIs are cited and listed.
- No secrets in the repo. Use `.env`.
- Public data is never shown as a user's data; generated data is always labelled `synthetic`; every claim is backed by something built or measured.
- The advisor drafts messages; the owner sends them. The product is free for everyone.
