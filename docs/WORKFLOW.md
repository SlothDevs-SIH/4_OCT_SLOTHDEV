# Workflow: branches, ownership, merge flow

## 1. Branches

```
main  (scaffold + contracts + docs)
 ├── backend-1    (Soham)    ─┐
 ├── backend-2    (Ayush)    ─┴─► backend-integration ─┐
 ├── frontend     (Kaushal)  ──────────────────────────┴─► fullstack-integration ─► main
 └── research     (Vedashree) ───────────────────────────────────────────────────►  (docs merged at the end)
```

| Branch | Owner | Edits only | Merge target |
|---|---|---|---|
| `backend-1` | Soham | `backend/data_engine/` | `backend-integration` |
| `backend-2` | Ayush | `backend/decision_engine/` | `backend-integration` |
| `frontend` | Kaushal | `frontend/` | `fullstack-integration` |
| `research` | Vedashree | `research/` (and review comments elsewhere) | `main` at the end |
| `backend-integration` | Soham + Ayush | `backend/gateway/` plus conflict fixes | `fullstack-integration` |
| `fullstack-integration` | Kaushal + Soham | anything needed to make the app run end to end | `main` |

**Why this avoids merge conflicts:** each person edits only their own folder. The only shared files are in `contracts/`, `db/` and `docs/`, which change only on `main` (section 3).

## 2. Everyday commands

```bash
git clone https://github.com/SlothDevs-SIH/4_OCT_SLOTHDEV.git
cd 4_OCT_SLOTHDEV
git fetch origin
git checkout backend-1        # or backend-2 / frontend / research

# work, then
git add <your folder>
git commit -m "data_engine: add CSV upload and mapping"
git push origin backend-1

# pick up changes to contracts/docs from main (do this at least once an hour)
git fetch origin
git merge origin/main
```

- Commit small and often. Push at least every 30–45 minutes (the push is our backup and shows work happened during the event).
- Never force-push. Never commit `.env`.
- Don't edit another person's folder. If you need something from them, ask or change the contract (section 3).

## 3. Changing the contract

`contracts/API_CONTRACT.md` and `contracts/fixtures/*.json` are what everyone codes against. To change them:

1. Tell the affected people in the group chat first (what field, why).
2. Commit the change **on `main`** only, in a small commit.
3. Everyone merges `origin/main` into their branch.

Adding a new optional field is cheap. Renaming or removing a field is not. Avoid it after 11:00.

## 4. Integration

Integration happens twice so problems show up early.

**`backend-integration`**
1. Create it from `main`: `git checkout -b backend-integration origin/main`.
2. `git merge origin/backend-1` then `git merge origin/backend-2`. The folders don't overlap, so conflicts should be rare.
3. Set `DATA_SOURCE=local` so `decision_engine` calls `data_engine` directly (no HTTP between them).
4. Run `uvicorn backend.gateway.main:app --port 8000` from the repo root and walk through the contract at `http://localhost:8000/docs`.
5. Fix integration bugs in `backend/gateway/` or in the module that owns the bug (tell its owner).
6. Tag when green: `git tag backend-green-1` (after Stage 1) and `backend-green-2` (after Stage 2).

**`fullstack-integration`**
1. Create from `backend-integration`. `git merge origin/frontend`.
2. Point the frontend at the gateway: `NEXT_PUBLIC_API_BASE=http://localhost:8000` (or the public API URL).
3. Run the whole demo path end to end (see `research/RESEARCH.md`, "Demo script").
4. Fix bugs here. Feature freeze at 4:30.

**Finish:** merge `fullstack-integration` and `research` into `main`, deploy from `main` (Vercel + Supabase), and record the demo from the **public** build.

## 5. Stages and timeline (IST)

Meetings: **11:00, 1:00, 3:00, 5:00.** Target: about 80% of the prototype done by the 3:00 meeting, a **working, publicly hosted prototype by 5:00**, then video, slides and submission until 6:00.

| Time | What |
|---|---|
| 11:00 | **Meeting 1.** Problem statement, D2C focus, plan |
| 11:40–1:00 | **Stage 1** (backend part 1, pushed to each branch). backend-1: synthetic D2C tenant, onboarding, demo load, CSV import with validation and quality report. backend-2: signals, eligibility gate, priority score, recommendations with cached LLM. frontend: setup, mocks, onboarding and import screens. research: dataset check, intervention library |
| 1:00 | **Meeting 2.** Review Stage 1 |
| 1:00–1:30 | Lunch. `backend-integration` #1: merge Stage 1 from both backends and run the gateway |
| 1:30–3:00 | **Stage 2** (backend part 2). backend-1: KPI engine, lead-conversion model, lead queue. backend-2: 7-day plan, tasks, outcome ledger. frontend phase 1: connect the single screens to the real API as each endpoint lands. First **public deploy** of what exists (Supabase + Vercel) by 2:30 so hosting problems surface early |
| 3:00 | **Meeting 3 (about 80% done).** Both backends merged and green. Frontend phase 1 connected. Public URL exists |
| 3:00–4:30 | `backend-integration` #2, `fullstack-integration`, frontend phase 2 (recommendations, plan, outcomes), fixes. **Feature freeze 4:30** |
| 4:30–5:00 | Redeploy from `main`, test the public link on a phone and in an incognito window, record the demo from the public build |
| 5:00 | **Meeting 4. Working prototype ready and public.** |
| 5:00–6:00 | Demo video (2–3 min), slides (5–7), problem-and-solution text, final checks. Confirm the official submission cutoff and submit before it |

The frontend (Kaushal) connects each endpoint as it lands, so the final integration is a confirmation, not a first connection.

**After each stage the builder reports exactly what works** (endpoints, tests, what is still mocked or precomputed) before starting the next stage.

## 6. Definition of done for a task

- It works through the contract endpoint (not only in a notebook).
- It has at least one test or a documented manual check.
- Numbers it produces were sanity-checked (units, ranges, a hand calculation for one case).
- It's pushed to your branch.
- Anything mocked is labelled mocked.
