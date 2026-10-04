# decision_engine outputs on data_engine's real v2 data (synthetic demo businesses)

What decision_engine's endpoints return for Box Box (`boxbox/`) and Meera's Kitchen (`homebaker/`), computed from `contracts/fixtures/v2_engine/` (data_engine's output). Weeks 2 to 4 are the scripted, labelled replay. Explanations are the deterministic text (no LLM).

Files per business: `diagnosis_week_1..4`, `actions_week_1`, `action_draft_week_1`, `lead_list_week_1`, `reach_partners_week_1`, `next_month_week_1`, `followup_week_2..4` (week 4 includes the four-week arc).

Regenerate: `python -m backend.decision_engine.export_fixtures` (a test fails if these drift from the code). Frontend mocks can use these directly.
