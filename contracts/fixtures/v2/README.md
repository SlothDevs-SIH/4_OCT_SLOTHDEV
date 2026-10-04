# Contract v2 fixtures (Catalyst AI): STAND-IN, synthetic

Input fixtures for the two demo businesses in the contract v2 shapes, so backend 2 and the frontend can build before backend 1's generator lands (`docs/DATASET.md` section 4). **Everything is synthetic** (`"synthetic": true`). When backend 1 ships the real generated businesses, these files are replaced by its output in the same shapes.

Regenerate (deterministic): `python -m backend.decision_engine.devtools.standin_fixtures`

| Path | Shape (contract v2) | Notes |
|---|---|---|
| `<business>/business.json` | 2.1 Business | plus additive fields: `topics`, `ships_to`, `growth_minutes_per_week`, `reach_candidates[]` (owner's list of possible partners), `provenance` |
| `<business>/facts_week_N.json` | 2.2 Fact (list in a `{business_id, week, as_of, facts}` envelope) | facts for the five bottlenecks; `source`, `sample_size`, plus additive `direction` and `origin` |
| `<business>/leads_week_N.json` | 2.4 Lead | points from `BACKEND_1_DATA_ENGINE.md` section 5; plus additive `last_message` (pseudonymised) and `last_activity` |
| `<business>/projection_week_N.json` | 2.7 Projection | stand-in context factors are **assumptions**, labelled in `basis.context_source` |
| `<business>/data_quality.json` | data quality | |
| `<business>/weekly_history.json` | – | the scenario's weekly numbers the facts are computed from |
| `market_context/f1_calendar.json` | 2.9 Market context | **real** output of backend 1's built module (Jolpica-F1 calendar, Wikimedia page views) |
| `market_context/india_festivals.json` | 2.9 (events) | stand-in until backend 1 builds the festival calendar; verify dates |

Businesses: `boxbox` (`biz_boxbox`, Box Box, F1 merchandise) and `homebaker` (`biz_homebaker`, Butter Lane Bakes). Weeks: `week_1` is the state as of 2026-10-04 after 14 weeks of history; `week_2` to `week_4` are the **scripted replay** (Box Box gains stranger orders after a partner collab and a race-weekend drop; the baker hits capacity as Diwali orders arrive).

**Fact rules used here** (backend 1 owns the real definitions): rates use the last 4 weeks; `baseline` is the mean of the business's 3 best weeks (or 4-week windows) so far; `quality_flag` is `low` under 10 orders, `partial` under 20.

**Fact ids added for the breakdown:** `f_orders_by_source` is split into `f_orders_by_source_friend`, `..._friend_of_friend`, `..._stranger`, `..._unknown` (kpi `orders_by_source`, dimension `source`).

## Output fixtures (generated from the real decision_engine pipeline)

`<business>/out_*.json` are what decision_engine's endpoints return for the scripted replay: `out_diagnosis_week_N`, `out_actions_week_1`, `out_action_draft_week_1`, `out_lead_list_week_1`, `out_reach_partners_week_1`, `out_next_month_week_1`, `out_followup_week_2..4` (week 4 includes the four-week arc). Regenerate with `python -m backend.decision_engine.export_fixtures`; a test fails if they drift from the code. Explanations in them are the deterministic text (no LLM).

## Additions to contract v2 used by decision_engine (all optional, additive)

- Business: `topics`, `ships_to`, `growth_minutes_per_week` (interview answer: minutes a week the owner can spend on growth), `reach_candidates[]` (the owner's list of fan pages, creators and communities: `partner_id, name, type, topics, city, followers, avg_comments_per_post, avg_shares_per_post, cost_inr`), `provenance`.
- Fact: `direction` (`up` / `down`) and `origin` (which file or answer).
- Lead: `last_message` (pseudonymised) and `last_activity`.
- Market context: `feed` parameter on `GET /market-context`, and `data_engine.public.get_market_context(from, to, feed=...)` so a second calendar (festivals) can plug in.
- decision_engine endpoints beyond the draft: `POST /businesses/{id}/lead-list/contacted` (Warm once per reason) and `GET /action-library`.
