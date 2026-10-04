import copy

import pytest

from backend.common.fixtures import load_fixture
from backend.decision_engine import anomaly, signals

BIZ = "biz_aarohi_skin"


# ---------------------------------------------------------------- anomaly


def test_robust_z_hand_calculation():
    # each weekday's 4 history values are 98, 100, 102, 100 -> seasonal median 100,
    # residuals -2, 0, 2, 0 -> MAD 1 -> scale 1.4826; a value of 110 gives z = 10 / 1.4826
    history = [v for v in (98, 100, 102, 100) for _ in range(7)]
    points = [(f"2026-01-{i + 1:02d}", float(v)) for i, v in enumerate(history)] + [("2026-01-29", 110.0)]
    [score] = anomaly.robust_z_scores(points)
    assert score["expected"] == 100
    assert score["z"] == pytest.approx(10 / 1.4826, abs=0.01)


def test_events_and_metrics_hand_calculation():
    events = anomaly.to_events(["2026-09-21", "2026-09-29", "2026-09-30", "2026-10-01"])
    assert events == [{"from": "2026-09-21", "to": "2026-09-21"}, {"from": "2026-09-29", "to": "2026-10-01"}]
    m = anomaly.evaluate(events, [{"from": "2026-09-30", "to": "2026-10-03"}], eval_days=28)
    assert (m["precision"], m["recall"], m["false_alerts_per_week"], m["detection_delay_days"]) == (0.5, 1.0, 0.25, 0)


def test_detects_injected_instagram_spike_on_day_one():
    found = anomaly.detect(load_fixture("kpi_daily"), "2026-09-27", "2026-10-03")
    assert [f["channel"] for f in found] == ["instagram"]  # Google (control) stays quiet
    assert found[0]["first_alert"] == "2026-09-29"
    assert found[0]["alert_dates"] == ["2026-09-29", "2026-09-30", "2026-10-01", "2026-10-02", "2026-10-03"]


def test_benchmark_keeps_simple_baseline():
    report = anomaly.benchmark(load_fixture("kpi_daily"))
    base, challenger = report["summary"]["robust_z_mad"], report["summary"]["isolation_forest"]
    assert base["recall"] == 1.0 and base["detection_delay_days"] == 0
    assert report["selected"] == "robust_z_mad"
    assert base["f1"] >= challenger["f1"]


def test_choose_rule():
    m = {"f1": 0.5, "false_alerts_per_week": 1.0, "detection_delay_days": 1}
    assert anomaly.choose(m, dict(m, f1=0.6)) == "isolation_forest"
    assert anomaly.choose(m, dict(m, false_alerts_per_week=0.5)) == "isolation_forest"
    assert anomaly.choose(m, dict(m)) == "robust_z_mad"  # ties go to the simpler method


def test_report_written(tmp_path):
    path = anomaly.write_report(anomaly.benchmark(load_fixture("kpi_daily")), tmp_path / "m.json")
    assert '"selected": "robust_z_mad"' in path.read_text()


# ---------------------------------------------------------------- signals


def _detect(facts=None, leads=None, series="default", ctx=None):
    return signals.detect(ctx or load_fixture("business_context"),
                          facts if facts is not None else load_fixture("kpi_facts"),
                          leads or load_fixture("lead_scores"),
                          load_fixture("kpi_daily") if series == "default" else series)


def test_demo_signals_match_fixture():
    got = {s["signal_id"]: s for s in _detect()["signals"]}
    want = {s["signal_id"]: s for s in load_fixture("signals")["signals"]}
    assert set(got) == set(want)
    for sid, w in want.items():
        g = got[sid]
        for key in ("type", "rule", "kpi", "dimension", "tests", "urgency", "candidate_template_ids", "title",
                    "severity", "score"):
            assert g[key] == w[key], (sid, key)
        assert g["evidence_ids"] == w["evidence_ids"], sid


def test_every_signal_passes_four_tests_and_cites_real_ids():
    doc = _detect()
    known = {f["fact_id"] for f in load_fixture("kpi_facts")} | {l["lead_id"] for l in load_fixture("lead_scores")["leads"]}
    for s in doc["signals"]:
        assert all(s["tests"].values())
        assert set(s["evidence_ids"]) <= known


def test_localization_failure_is_rejected_not_emitted():
    facts = load_fixture("kpi_facts")
    for f in facts:
        if f["fact_id"] == "f_croas_google":  # Google also below break-even and falling
            f["value"], f["delta_pct"] = 0.8, -31.8
    doc = _detect(facts=facts)
    ids = {s["signal_id"] for s in doc["signals"]}
    assert "sig_instagram_low_contribution" not in ids
    rejected = {r["signal_id"]: r for r in doc["rejected"]}
    assert rejected["sig_instagram_low_contribution"]["failed"] == ["localization"]


def test_no_series_skips_anomaly_only():
    doc = _detect(series=None)
    assert doc["anomaly_skipped"] is True
    assert {s["signal_id"] for s in doc["signals"]} == {
        "sig_hot_leads_unattended", "sig_instagram_low_contribution", "sig_email_repeat_cohort"}


def test_latency_within_sla_gives_no_signal():
    facts = load_fixture("kpi_facts")
    for f in facts:
        if f["fact_id"] == "f_latency_hot_leads":
            f["value"], f["delta_pct"] = 3.0, -50.0
    assert "sig_hot_leads_unattended" not in {s["signal_id"] for s in _detect(facts=facts)["signals"]}


def test_funnel_rule_fires_when_leads_collapse():
    facts = load_fixture("kpi_facts")
    for f in facts:
        if f["fact_id"] == "f_funnel_leads":
            f["value"], f["delta_pct"] = 90, -39.2  # traffic flat, lead rate down ~37%
    got = {s["signal_id"]: s for s in _detect(facts=facts)["signals"]}
    assert got["sig_high_traffic_low_leads"]["candidate_template_ids"] == ["tpl_landing_page_fix"]


def test_deviation_without_template_is_rejected():
    facts = load_fixture("kpi_facts")
    for f in facts:
        if f["fact_id"] == "f_funnel_won":
            f["value"], f["delta_pct"] = 12, -53.8  # leads up, wins collapse
    rejected = {r["signal_id"]: r for r in _detect(facts=facts)["rejected"]}
    # no approved template targets this rule yet -> rejected with the reason, not emitted
    assert rejected["sig_leads_high_wins_low"]["failed"] == ["actionability"]


def test_signals_endpoint(client):
    body = client.get(f"/api/v1/businesses/{BIZ}/signals").json()
    assert len(body["signals"]) == 4 and body["synthetic"] is True
    assert client.get("/api/v1/businesses/biz_nope/signals").status_code == 404
    err = client.get("/api/v1/businesses/biz_nope/signals").json()
    assert err["error"]["code"] == "not_found"


def test_missing_daily_endpoint_skips_anomalies_only(tmp_path):
    """data_engine without the optional /kpis/daily endpoint (HTTP 404) still gets signals."""
    from backend.decision_engine.clients import DataClient, DataNotFound
    from backend.decision_engine.config import Settings
    from backend.decision_engine.service import Engine

    class NoDaily(DataClient):
        def get_kpi_series(self, *a, **k):
            raise DataNotFound("GET /kpis/daily returned 404")

    eng = Engine(settings=Settings(llm_cache_only=True, llm_cache_dir=tmp_path), data=NoDaily("fixture"))
    doc = eng.signals(BIZ)
    assert doc["anomaly_skipped"] is True and len(doc["signals"]) == 3
