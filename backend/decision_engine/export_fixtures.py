"""Regenerate decision_engine's output fixtures from the real pipeline.

    python -m backend.decision_engine.export_fixtures          # write contracts/fixtures/*.json
    python -m backend.decision_engine.export_fixtures --check  # exit 1 if they are out of date

Runs the demo loop on the input fixtures with no LLM (deterministic text), so the frontend
mocks and the research demo script show exactly what the API returns. Timestamps are fixed.
"""
import json
import sys
import tempfile
from pathlib import Path

from backend.common.fixtures import FIXTURES_DIR
from backend.decision_engine.clients import DataClient
from backend.decision_engine.config import Settings
from backend.decision_engine.service import Engine

BIZ = "biz_aarohi_skin"
APPROVE = ("rec_hot_leads", "rec_email_retention", "rec_instagram_test")
NOT_DONE_BY_DAY7 = "Review"  # the Instagram readout is still open at day 7 in the demo story
TIMES = {"generated_at": "2026-10-04T05:00:00Z", "created_at": "2026-10-04T05:05:00Z",
         "updated_at": "2026-10-04T05:05:00Z", "at": "2026-10-04T05:20:00Z", "frozen_at": "2026-10-04T05:20:00Z",
         "evaluated_at": "2026-10-12T04:30:00Z", "taken_at": "2026-10-04T05:00:00Z"}


def _fix_times(obj):
    if isinstance(obj, dict):
        return {k: (TIMES[k] if k in TIMES and isinstance(v, str) else _fix_times(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_fix_times(v) for v in obj]
    return obj


def build() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        eng = Engine(settings=Settings(llm_cache_only=True, llm_cache_dir=Path(tmp)), data=DataClient("fixture"))
        signals = eng.signals(BIZ)
        recs = eng.generate(BIZ)
        for rid in APPROVE:
            eng.approve(rid, by="owner_founder")
        plan = eng.create_plan(BIZ)
        for t in plan["tasks"]:
            if not t["title"].startswith(NOT_DONE_BY_DAY7):
                eng.update_task(t["task_id"], {"status": "done"})
        outcomes = eng.evaluate_outcomes(plan["plan_id"])
    return {name: _fix_times(doc) for name, doc in
            {"signals": signals, "recommendations": recs, "plan": plan, "outcomes": outcomes}.items()}


def render(doc) -> str:
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def main(argv=None) -> int:
    check = "--check" in (argv if argv is not None else sys.argv[1:])
    stale = []
    for name, doc in build().items():
        path = FIXTURES_DIR / f"{name}.json"
        text = render(doc)
        if path.read_text(encoding="utf-8") != text:
            stale.append(path.name)
            if not check:
                path.write_text(text, encoding="utf-8")
    if check and stale:
        print("out of date:", ", ".join(stale))
        return 1
    print("updated:" if stale else "up to date", ", ".join(stale))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
