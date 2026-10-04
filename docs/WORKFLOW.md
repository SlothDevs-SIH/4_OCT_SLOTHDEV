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

**`backend-integration` (target: 2:00–2:45 PM)**
1. Create it from `main`: `git checkout -b backend-integration origin/main`.
2. `git merge origin/backend-1` then `git merge origin/backend-2`. The folders don't overlap, so conflicts should be rare.
3. Set `DATA_SOURCE=local` so `decision_engine` calls `data_engine` directly (no HTTP between them).
4. Run `uvicorn backend.gateway.main:app --port 8000` from the repo root and walk through the contract at `http://localhost:8000/docs`.
5. Fix integration bugs in `backend/gateway/` or in the module that owns the bug (tell its owner).
6. Tag when green: `git tag backend-green`.

**`fullstack-integration` (target: 2:45–3:30 PM)**
1. Create from `backend-integration`. `git merge origin/frontend`.
2. Point the frontend at the gateway: `NEXT_PUBLIC_API_BASE=http://localhost:8000`.
3. Run the whole demo path end to end (see `research/RESEARCH.md`, "Demo script").
4. Fix bugs here. Feature freeze at 3:30.

**Finish (3:30–5:00 PM):** merge `fullstack-integration` and `research` into `main`, deploy from `main`, and record the demo from the deployed build.

## 5. Timeline (IST)

| Time | Milestone |
|---|---|
| 10:00–10:30 | Everyone reads their MD. Contract freeze. Environments ready. |
| 11:30 | **M1:** backend-1 part 1 works (onboarding, demo-data load, CSV import and quality report) |
| 12:00 | **M2:** backend-2 part 1 works (signals, eligibility, priority score, recommendations with cached LLM) |
| 1:00–1:30 | Lunch |
| 1:30 | **M3:** backend-1 part 2 works (KPIs, funnel, lead-conversion model and lead queue) |
| 2:00 | **M4:** backend-2 part 2 works (7-day plan, tasks, outcome evaluation) |
| 2:00–2:45 | `backend-integration` |
| 2:45–3:30 | `fullstack-integration` |
| **3:30** | **Feature freeze** |
| 3:30–4:30 | Deploy, README, seed demo data, fix bugs only |
| 4:30–5:30 | Demo video (2–3 min), slides (5–7), problem-and-solution text |
| 5:30–5:50 | Submit, then open every link in an incognito window |
| 5:50–6:00 | Buffer |

The frontend (Kaushal) integrates each milestone as it lands (see `frontend/FRONTEND.md`, stages F1–F4), so the final integration is a confirmation, not a first connection.

## 6. Definition of done for a task

- It works through the contract endpoint (not only in a notebook).
- It has at least one test or a documented manual check.
- Numbers it produces were sanity-checked (units, ranges, a hand calculation for one case).
- It's pushed to your branch.
- Anything mocked is labelled mocked.
