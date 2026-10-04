# Workflow: branches, ownership, merge flow, today's timeline

## 1. Branches

```
main  (shared docs + contract)
 ├── backend-1    (Soham)     ─┐
 ├── backend-2    (Ayush)     ─┴─► backend-integration ─┐
 ├── frontend     (Kaushal)   ──────────────────────────┴─► fullstack-integration ─► main
 └── research     (Vedashree) ───────────────────────────────────────────────────►  (docs merged at the end)
```

| Branch | Owner | Edits only |
|---|---|---|
| `backend-1` | Soham | `backend/data_engine/` |
| `backend-2` | Ayush | `backend/decision_engine/` |
| `frontend` | Kaushal | `frontend/` |
| `research` | Vedashree | `research/` |
| `backend-integration` | Soham + Ayush | `backend/gateway/` plus conflict fixes |
| `fullstack-integration` | Kaushal + Soham | anything needed to run end to end |

Each person edits only their own folder. The shared files (`contracts/`, `docs/`, the three backend docs) change only on `main`.

## 2. Everyday commands

```bash
git clone https://github.com/SlothDevs-SIH/4_OCT_SLOTHDEV.git && cd 4_OCT_SLOTHDEV
git fetch origin && git checkout backend-1        # or backend-2 / frontend / research
# work, then
git add <your folder> && git commit -m "data_engine: add lead scoring" && git push origin backend-1
# pick up shared docs and contract changes from main at least once an hour
git fetch origin && git merge origin/main
```

Commit small and often; push every 30 to 45 minutes (the push is the backup). Never force-push. Never commit `.env` or raw datasets (`data/raw/` is git-ignored).

## 3. Changing the contract

`contracts/API_CONTRACT.md` is what everyone codes against. To change it: tell the affected person, commit the change **on `main`** in a small commit, and everyone merges `origin/main`. Adding an optional field is cheap; renaming or removing one is not.

## 4. Integration

1. `git checkout -b backend-integration origin/main && git merge origin/backend-1 && git merge origin/backend-2`
2. `DATA_SOURCE=local uvicorn backend.gateway.main:app --port 8000`
3. Walk the loop: load week 1 → diagnose → advise → daily lead list → record what was done → load week 2 → follow up. Tag when green (`backend-green`).
4. `fullstack-integration`: merge `frontend`, point it at the gateway, run the whole demo path, fix bugs there.
5. Finish: merge into `main`, deploy from `main` (Vercel and Supabase), record the demo from the **public** build.

## 5. Today

| Step | What |
|---|---|
| Now | Contract v2 agreed (Soham and Ayush); datasets in place (`docs/DATASET.md`) |
| Next | Build in parallel: backend 1 (generated demo businesses, intake, facts, leads, projection); backend 2 (diagnosis, actions, lead list); frontend on mocks; research deliverables |
| Integration | `backend-integration`, then `fullstack-integration`; first public deploy |
| **5:00 PM** | **Working, public prototype shown** |
| After | Demo video (2 to 3 minutes), 5 to 7 slides, problem-and-solution text, submission checks. Confirm the official submission cutoff |

After each stage, the owner reports exactly what works and what is generated, precomputed or not built, before starting the next stage.

## 6. Definition of done for a task

- It works through the contract endpoint (not only in a notebook).
- It has a test or a documented manual check.
- Numbers it produces were sanity-checked (units, ranges, one hand calculation).
- It is pushed to your branch.
- Anything generated, scripted or mocked is labelled.
