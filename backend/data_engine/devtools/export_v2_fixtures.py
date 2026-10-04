"""Write the real output of data_engine for the two demo businesses as contract v2 fixture files (same layout as the stand-ins).

    python -m backend.data_engine.devtools.export_v2_fixtures [--out contracts/fixtures/v2_engine]

Deterministic: running it twice gives identical files. Every file is `synthetic: true` (generated, calibrated on public data).
`--out contracts/fixtures/v2` replaces decision_engine's stand-ins with this output.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.data_engine import public
from backend.data_engine.homebiz import config as C
from backend.data_engine.homebiz import facts as F
from backend.data_engine.homebiz import store as hb
from backend.data_engine.homebiz.model import as_of_for
from backend.data_engine.main import app

API = "/api/v1"
GROUPS = {"hot": "50+", "warm": "20-49", "cold": "under 20", "disqualified": "cannot deliver"}
ROOT = Path(__file__).resolve().parents[3]


def _dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def export(out: Path) -> list:
    client = TestClient(app)
    written = []
    for key, scenario in C.SCENARIOS.items():
        bid = scenario["business_id"]
        for week in range(1, C.ADVISORY_WEEKS + 1):
            r = client.post(f"{API}/demo/load?business={key}&week={week}")
            assert r.status_code == 200, r.text
            data = hb.get(bid)
            as_of = as_of_for(week, data).isoformat()
            label = f"week_{week}"
            if week == 1:
                _dump(out / key / "business.json", public.get_business(bid))
                _dump(out / key / "data_quality.json", {k: v for k, v in client.get(f"{API}/businesses/{bid}/data-quality").json().items() if k != "generated_at"})
                written += [out / key / "business.json", out / key / "data_quality.json"]
            _dump(out / key / f"facts_{label}.json", {"business_id": bid, "week": label, "as_of": as_of, "synthetic": True, "window_weeks": 4,
                                                      "baseline_rule": "the owner's own best 4-week window so far", "facts": public.get_facts(bid, week)})
            _dump(out / key / f"leads_{label}.json", {"business_id": bid, "week": label, "as_of": as_of, "synthetic": True, "points_version": "v1",
                                                      "groups": GROUPS, "leads": public.get_leads(bid, None, week)})
            _dump(out / key / f"projection_{label}.json", public.get_projection(bid, week))
            written += [out / key / f"{n}_{label}.json" for n in ("facts", "leads", "projection")]
        hb.load_demo(key, C.ADVISORY_WEEKS)
        history = {fid: F.weekly_series(hb.get(bid), fid, C.ADVISORY_WEEKS)["points"] for fid in ("f_orders_per_week", "f_stranger_orders_week", "f_reach_per_post", "f_margin_pct")}
        _dump(out / key / "weekly_history.json", {"business_id": bid, "week": f"week_{C.ADVISORY_WEEKS}", "synthetic": True, "series": history})
        written.append(out / key / "weekly_history.json")
        hb.load_demo(key, 1)
    f1 = client.get(f"{API}/market-context?from=2026-10-05&to=2026-12-31").json()
    fest = client.get(f"{API}/market-context?feed=india_festivals&from=2026-10-05&to=2026-12-31").json()
    _dump(out / "market_context" / "f1_calendar.json", f1)
    _dump(out / "market_context" / "india_festivals.json", fest)
    written += [out / "market_context" / "f1_calendar.json", out / "market_context" / "india_festivals.json"]
    return written


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "contracts" / "fixtures" / "v2_engine"))
    args = ap.parse_args()
    files = export(Path(args.out))
    print(f"wrote {len(files)} files to {args.out}")
