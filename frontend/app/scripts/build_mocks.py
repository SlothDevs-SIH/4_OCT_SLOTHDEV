"""Record the real backend's answers for the offline demo (NEXT_PUBLIC_USE_MOCKS=true).

    python frontend/app/scripts/build_mocks.py        # from the repo root

Runs the whole advisor loop in-process for both demo businesses, weeks 1 to 4, and writes JSON into frontend/app/public/mock/.
Deterministic: running it twice gives identical files (apart from `generated_at` stamps, which are removed).
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ["DATA_SOURCE"] = "local"

from fastapi.testclient import TestClient  # noqa: E402

from backend.gateway.main import app  # noqa: E402

OUT = ROOT / "frontend" / "app" / "public" / "mock"
A = "/api/v1"
c = TestClient(app)


def strip(o):
    if isinstance(o, dict):
        return {k: strip(v) for k, v in o.items() if k not in ("generated_at", "request_id")}
    if isinstance(o, list):
        return [strip(x) for x in o]
    return o


def ok(r):
    assert r.status_code < 300, (r.request.url, r.status_code, r.text[:300])
    return strip(r.json())


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


for key in ("boxbox", "homebaker"):
    bid = f"biz_{key}"
    d = OUT / key
    prev_actions = None
    followups = []
    for w in (1, 2, 3, 4):
        label = f"week_{w}"
        ok(c.post(f"{A}/demo/load?business={key}&week={w}"))
        if w == 1:
            dump(d / "business.json", ok(c.get(f"{A}/businesses/{bid}")))
            dump(d / "data_quality.json", ok(c.get(f"{A}/businesses/{bid}/data-quality")))
        dump(d / f"facts_w{w}.json", ok(c.get(f"{A}/businesses/{bid}/facts?week={w}")))
        dump(d / f"weekly_stranger_w{w}.json", ok(c.get(f"{A}/businesses/{bid}/facts/weekly?fact_id=f_stranger_orders_week")))
        dump(d / f"diagnosis_w{w}.json", ok(c.get(f"{A}/businesses/{bid}/diagnosis?week={label}")))
        acts = ok(c.post(f"{A}/businesses/{bid}/actions/generate?week={label}"))
        dump(d / f"actions_w{w}.json", acts)
        drafts = {}
        for a in acts["actions"]:
            for ch in a["draft_channels"]:
                drafts.setdefault(a["action_id"], {})[ch] = ok(c.get(f"{A}/actions/{a['action_id']}/draft?channel={ch}"))
        dump(d / f"drafts_w{w}.json", drafts)
        dump(d / f"lead_list_w{w}.json", ok(c.get(f"{A}/businesses/{bid}/lead-list?week={label}")))
        dump(d / f"next_month_w{w}.json", ok(c.get(f"{A}/businesses/{bid}/next-month?week={label}")))
        dump(d / f"sample_chat_w{w}.json", ok(c.get(f"{A}/demo/sample-chat?business={key}&week={w}")))
        if w >= 2 and prev_actions:
            body = {"actions_done": [a["action_id"] for a in prev_actions]}
            f = ok(c.post(f"{A}/businesses/{bid}/followup?week={label}", json=body))
            dump(d / f"followup_w{w}.json", f)
            followups.append(f)
        prev_actions = acts["actions"]
    dump(d / "followups.json", {"business_id": bid, "followups": followups})

dump(OUT / "public_data.json", ok(c.get(f"{A}/public-data")))
print("wrote", sum(1 for _ in OUT.rglob("*.json")), "files to", OUT)
