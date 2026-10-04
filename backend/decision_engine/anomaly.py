"""Anomaly detection on daily channel KPIs.

Baseline: seasonal median / MAD robust z-score. For day t, the expected value is the
median of the same weekday over the previous 4 weeks; the scale is 1.4826 * MAD of
the de-seasonalised residuals in that 28-day window. A day alerts when |z| > 3.5 in
the "bad" direction for the KPI (CAC up, conversion down).

Challenger: Isolation Forest, kept only if it beats the baseline on the injected
incidents (event-level F1, then false alerts per week, then detection delay).
"""
from __future__ import annotations

import json
import statistics
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

HISTORY_DAYS = 28
Z_THRESHOLD = 3.5
MAD_TO_SIGMA = 1.4826
BAD_DIRECTION = {"cac": "up", "conversion_rate": "down"}
REPORT_PATH = Path(__file__).resolve().parent / "reports" / "anomaly_metrics.json"


def metric_points(series: list[dict], channel: str, kpi: str) -> list[tuple[str, float]]:
    """Daily (date, value) for one channel; days without customers/sessions are skipped."""
    out = []
    for r in sorted((r for r in series if r["channel"] == channel), key=lambda r: r["date"]):
        if kpi == "cac" and r["new_customers"] > 0:
            out.append((r["date"], r["spend"] / r["new_customers"]))
        elif kpi == "conversion_rate" and r["sessions"] > 0:
            out.append((r["date"], r["new_customers"] / r["sessions"]))
    return out


def robust_z_scores(points: list[tuple[str, float]], history: int = HISTORY_DAYS) -> list[dict]:
    """Seasonal median/MAD z-score for every day that has `history` days before it."""
    out = []
    values = [v for _, v in points]
    for i in range(history, len(points)):
        window = values[i - history:i]
        # same-weekday values in the window (offsets 7, 14, 21, 28 days back)
        seasonal = [window[j] for j in range(len(window)) if (i - (i - history + j)) % 7 == 0]
        expected = statistics.median(seasonal)
        residuals = []
        for j, x in enumerate(window):
            same_day = [window[k] for k in range(j % 7, len(window), 7)]
            residuals.append(x - statistics.median(same_day))
        med_r = statistics.median(residuals)
        mad = statistics.median(abs(r - med_r) for r in residuals)
        scale = max(MAD_TO_SIGMA * mad, 0.01 * abs(expected), 1e-9)
        out.append({"date": points[i][0], "value": round(values[i], 4), "expected": round(expected, 4),
                    "z": round((values[i] - expected) / scale, 2)})
    return out


def baseline_alerts(scores: list[dict], direction: str, threshold: float = Z_THRESHOLD) -> list[str]:
    if direction == "up":
        return [s["date"] for s in scores if s["z"] > threshold]
    if direction == "down":
        return [s["date"] for s in scores if s["z"] < -threshold]
    return [s["date"] for s in scores if abs(s["z"]) > threshold]


def isolation_forest_alerts(series: list[dict], channel: str, history: int = HISTORY_DAYS,
                            seed: int = 0) -> list[str]:
    """Fit on the first `history` days, flag outliers among the later days."""
    import numpy as np
    from sklearn.ensemble import IsolationForest

    rows = sorted((r for r in series if r["channel"] == channel and r["new_customers"] > 0
                   and r["sessions"] > 0), key=lambda r: r["date"])
    if len(rows) <= history:
        return []
    feats = np.array([[r["spend"] / r["new_customers"], r["new_customers"] / r["sessions"],
                       r["spend"], r["new_customers"]] for r in rows])
    model = IsolationForest(n_estimators=200, contamination="auto", random_state=seed)
    model.fit(feats[:history])
    flags = model.predict(feats[history:])
    return [rows[history + i]["date"] for i, f in enumerate(flags) if f == -1]


def to_events(alert_dates: list[str]) -> list[dict]:
    """Group consecutive alert days into events."""
    events = []
    for d in sorted(alert_dates):
        day = date.fromisoformat(d)
        if events and date.fromisoformat(events[-1]["to"]) + timedelta(days=1) == day:
            events[-1]["to"] = d
        else:
            events.append({"from": d, "to": d})
    return events


def _overlaps(event: dict, incident: dict) -> bool:
    return event["from"] <= incident["to"] and incident["from"] <= event["to"]


def evaluate(events: list[dict], incidents: list[dict], eval_days: int) -> dict:
    """Event-level precision/recall, false alerts per week and detection delay."""
    tp_events = [e for e in events if any(_overlaps(e, i) for i in incidents)]
    false_events = len(events) - len(tp_events)
    delays, detected = [], 0
    for inc in incidents:
        hits = [e for e in events if _overlaps(e, inc)]
        if hits:
            detected += 1
            first = min(max(e["from"], inc["from"]) for e in hits)
            delays.append((date.fromisoformat(first) - date.fromisoformat(inc["from"])).days)
    precision = len(tp_events) / len(events) if events else (1.0 if not incidents else 0.0)
    recall = detected / len(incidents) if incidents else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"events": len(events), "true_events": len(tp_events), "false_events": false_events,
            "precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3),
            "false_alerts_per_week": round(false_events / (eval_days / 7), 3),
            "detection_delay_days": round(sum(delays) / len(delays), 2) if delays else None}


def _pool(results: list[dict], eval_days: int) -> dict:
    events = sum(r["events"] for r in results)
    true_events = sum(r["true_events"] for r in results)
    false_events = sum(r["false_events"] for r in results)
    incidents = sum(r["incidents"] for r in results)
    detected = sum(r["detected"] for r in results)
    precision = true_events / events if events else 0.0
    recall = detected / incidents if incidents else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    delays = [r["detection_delay_days"] for r in results if r["detection_delay_days"] is not None]
    weeks = eval_days / 7 * len(results)
    return {"precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3),
            "false_alerts_per_week": round(false_events / weeks, 3) if weeks else 0.0,
            "detection_delay_days": round(sum(delays) / len(delays), 2) if delays else None}


def benchmark(series_doc: dict, kpi: str = "cac") -> dict:
    """Compare baseline and challenger on every channel's injected incidents (and controls)."""
    series, incidents = series_doc["series"], series_doc.get("injected_incidents", [])
    channels = sorted({r["channel"] for r in series})
    per_method = {"robust_z_mad": [], "isolation_forest": []}
    for ch in channels:
        points = metric_points(series, ch, kpi)
        scores = robust_z_scores(points)
        eval_days = len(scores)
        ch_incidents = [i for i in incidents if i["kpi"] == kpi and i["dimension"].get("channel") == ch]
        alerts = {"robust_z_mad": baseline_alerts(scores, BAD_DIRECTION[kpi]),
                  "isolation_forest": isolation_forest_alerts(series, ch)}
        for method, dates in alerts.items():
            m = evaluate(to_events(dates), ch_incidents, eval_days)
            per_method[method].append(dict(m, channel=ch, incidents=len(ch_incidents),
                                           detected=round(m["recall"] * len(ch_incidents)),
                                           alert_dates=dates))
    eval_days = len(robust_z_scores(metric_points(series, channels[0], kpi))) if channels else 0
    summary = {m: _pool(r, eval_days) for m, r in per_method.items()}
    return {"kpi": kpi, "synthetic": series_doc.get("synthetic", True),
            "evaluation_window_days": eval_days, "z_threshold": Z_THRESHOLD,
            "history_days": HISTORY_DAYS, "per_channel": per_method, "summary": summary,
            "selected": choose(summary["robust_z_mad"], summary["isolation_forest"])}


def choose(baseline: dict, challenger: dict) -> str:
    """Keep the challenger only if it is clearly better; ties go to the simpler baseline."""
    def delay(m):
        return m["detection_delay_days"] if m["detection_delay_days"] is not None else float("inf")
    if challenger["f1"] > baseline["f1"]:
        return "isolation_forest"
    if (challenger["f1"] == baseline["f1"]
            and challenger["false_alerts_per_week"] < baseline["false_alerts_per_week"]
            and delay(challenger) <= delay(baseline)):
        return "isolation_forest"
    return "robust_z_mad"


def write_report(report: dict, path: Path = REPORT_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    slim = json.loads(json.dumps(report))
    for rows in slim["per_channel"].values():
        for r in rows:
            r.pop("alert_dates", None)
    path.write_text(json.dumps(slim, indent=2) + "\n")
    return path


def detect(series_doc: dict, period_from: str, period_to: str, kpi: str = "cac",
           method: str = "robust_z_mad") -> list[dict]:
    """Anomalies per channel whose alerts fall inside [period_from, period_to]."""
    series = series_doc["series"]
    found = []
    for ch in sorted({r["channel"] for r in series}):
        scores = robust_z_scores(metric_points(series, ch, kpi))
        if method == "isolation_forest":
            dates = isolation_forest_alerts(series, ch)
        else:
            dates = baseline_alerts(scores, BAD_DIRECTION[kpi])
        in_period = [d for d in dates if period_from <= d <= period_to]
        if not in_period:
            continue
        z_in = [s for s in scores if s["date"] in in_period]
        found.append({"channel": ch, "kpi": kpi, "method": method, "alert_dates": in_period,
                      "first_alert": in_period[0],
                      "max_z": max((s["z"] for s in z_in), key=abs) if z_in else None})
    return found


def main(argv: Optional[list] = None) -> None:
    """python -m backend.decision_engine.anomaly  -> writes reports/anomaly_metrics.json"""
    from backend.common.fixtures import load_fixture
    report = benchmark(load_fixture("kpi_daily"))
    path = write_report(report)
    print(json.dumps(report["summary"], indent=2), "\nselected:", report["selected"], "\n->", path)


if __name__ == "__main__":
    main()
