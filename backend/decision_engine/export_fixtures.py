"""Generate decision_engine's v2 output fixtures from the real pipeline (frontend mocks, demo script).

    python -m backend.decision_engine.export_fixtures          # write contracts/fixtures/v2/<business>/out_*.json
    python -m backend.decision_engine.export_fixtures --check  # exit 1 if they are out of date

Plays the scripted, labelled 4-week replay for both demo businesses with no LLM (deterministic text).
Which actions get done each week and what partners produced is part of the script (below), not data.
"""
import json
import sys
import tempfile
from pathlib import Path

from backend.common.fixtures import FIXTURES_DIR
from backend.decision_engine.clients import DataClient
from backend.decision_engine.config import Settings
from backend.decision_engine.service import Engine

# scripted replay: per business, per week -> which of that week's actions were done, and partner results
SCRIPT = {
    "biz_boxbox": {
        "week_1": {"skip": ["reach_community_share"], "partners": [{"partner_id": "rp_bb_3", "stranger_leads": 3}]},
        "week_2": {"skip": [], "partners": [{"partner_id": "rp_bb_3", "stranger_leads": 4}]},
        "week_3": {"skip": [], "partners": [{"partner_id": "rp_bb_3", "stranger_leads": 5}]},
    },
    "biz_homebaker": {
        "week_1": {"skip": ["reach_community_share"], "partners": [{"partner_id": "rp_hb_1", "stranger_leads": 2}]},
        "week_2": {"skip": [], "partners": [{"partner_id": "rp_hb_1", "stranger_leads": 3}]},
        "week_3": {"skip": [], "partners": []},
    },
}
SLUGS = {"biz_boxbox": "boxbox", "biz_homebaker": "homebaker"}
VOLATILE = {"generated_at", "updated_at"}


def _strip(obj):
    if isinstance(obj, dict):
        return {k: _strip(v) for k, v in obj.items() if k not in VOLATILE}
    if isinstance(obj, list):
        return [_strip(v) for v in obj]
    return obj


def build() -> dict:
    out = {}
    with tempfile.TemporaryDirectory() as tmp:
        eng = Engine(settings=Settings(llm_cache_only=True, llm_cache_dir=Path(tmp)), data=DataClient("fixture"))
        for biz, slug in SLUGS.items():
            docs = {"diagnosis_week_1": eng.diagnosis(biz, "week_1"),
                    "actions_week_1": eng.generate_actions(biz, "week_1"),
                    "lead_list_week_1": eng.lead_list(biz, "week_1"),
                    "reach_partners_week_1": eng.reach_partners(biz, "week_1"),
                    "next_month_week_1": eng.next_month(biz, "week_1")}
            first = docs["actions_week_1"]["actions"][0]
            if first["draft_channels"]:
                docs["action_draft_week_1"] = eng.action_draft(first["action_id"], None)
            for n in (2, 3, 4):
                prev, week = f"week_{n - 1}", f"week_{n}"
                step = SCRIPT[biz][prev]
                acts = eng.store.actions_for(biz, prev)
                done = [a["action_id"] for a in acts if a["action_key"] not in step["skip"]]
                skipped = [a["action_id"] for a in acts if a["action_key"] in step["skip"]]
                docs[f"followup_{week}"] = eng.followup(biz, week, done, skipped, step["partners"])
                docs[f"diagnosis_{week}"] = eng.store.get_diagnosis(biz, week)
            out.update({f"{slug}/out_{name}": _strip(doc) for name, doc in docs.items()})
    return out


def render(doc) -> str:
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def main(argv=None) -> int:
    check = "--check" in (argv if argv is not None else sys.argv[1:])
    stale = []
    for name, doc in build().items():
        path = FIXTURES_DIR / "v2" / f"{name}.json"
        text = render(doc)
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            stale.append(name)
            if not check:
                path.write_text(text, encoding="utf-8")
    if check and stale:
        print("out of date:", ", ".join(stale))
        return 1
    print(("updated: " + ", ".join(stale)) if stale else "up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
