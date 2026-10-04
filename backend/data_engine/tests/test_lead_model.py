"""Lead-conversion model and queue: features, artifact integrity, train/serve consistency, honesty of the card, API."""
import csv
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.common.fixtures import load_fixture
from backend.data_engine import leads, public, store
from backend.data_engine.main import app
from backend.data_engine.ml import features as F
from backend.data_engine.ml.fetch_datasets import BANK_CSV
from backend.data_engine.ml.lead_model import ARTIFACT, LeadModel
from backend.data_engine.synth import config as C

client = TestClient(app)
REPORT = ARTIFACT.parent / "lead_model_report.json"


@pytest.fixture(scope="module")
def model():
    return LeadModel.load()


@pytest.fixture(scope="module")
def queue():
    return public.get_lead_scores("biz_aarohi_skin")


def A(prev="nonexistent", prior=0, days=999, contacts=1):
    return {"previous_outcome": prev, "prior_contacts": prior, "days_since_last_contact": days, "contacts_this_campaign": contacts}


# ------------------------------------------------------------------ features
def test_encoding_and_clipping():
    assert F.encode_raw(A("success", 3, 2, 1)) == [0.0, 1.0, 3.0, 0.0, 2.0, 1.0]
    assert F.encode_raw(A("nonexistent", 0, 999, 1)) == [0.0, 0.0, 0.0, 1.0, 0.0, 1.0]
    v = F.encode_raw(A("failure", 50, 45, 99))                       # values are clipped to the training range
    assert v[2] == 7.0 and v[4] == 30.0 and v[5] == 10.0


def test_missing_fields_cause_abstention_reasons():
    assert F.missing_fields(A(), "whatsapp") == []
    assert F.missing_fields(A(), None) == ["channel"]
    assert F.missing_fields({}, "email") == list(F.REQUIRED)
    assert "previous_outcome" in F.missing_fields(A(prev="maybe"), "email")


def test_excluded_features_are_documented():
    assert {"duration", "month", "job", "contact", "euribor3m"} <= set(F.EXCLUDED_FEATURES)
    assert "duration" not in "".join(F.FEATURES)


# ------------------------------------------------------------------ artifact integrity
def test_artifact_is_consistent(model):
    art = model.art
    assert len(art["coef"]) == len(art["features"]) == len(F.FEATURES) and art["features"] == F.FEATURES
    assert set(art["scaler"]) == set(F.NUMERIC)
    assert set(model.reference) == set(F.REQUIRED)


def test_calibration_is_monotone_and_probabilities_are_valid(model):
    grid = [i / 200 for i in range(201)]
    cal = [model.calibrate(p) for p in grid]
    assert all(b >= a - 1e-12 for a, b in zip(cal, cal[1:])) and all(0 <= c <= 1 for c in cal)
    for prev in F.PREVIOUS_OUTCOMES:
        for prior in (0, 2, 7):
            assert 0 <= model.probability(A(prev, prior, 999 if prev == "nonexistent" else 5, 2)) <= 1


def test_calibration_branches_work():
    fake = {"coef": [0] * 6, "intercept": 0, "scaler": {}, "reference": {}, "prevalence_train": 0.1, "model_card": {},
            "calibration": {"method": "isotonic", "x": [0.0, 0.5, 1.0], "y": [0.1, 0.4, 0.9]}}
    m = LeadModel(fake)
    assert m.calibrate(-1) == 0.1 and m.calibrate(2) == 0.9 and m.calibrate(0.25) == pytest.approx(0.25)
    fake["calibration"] = {"method": "sigmoid", "a": 1.0, "b": 0.0}
    assert LeadModel(fake).calibrate(0.5) == pytest.approx(0.5)


def test_contact_history_raises_the_probability_in_the_right_order(model):
    none = model.probability(A())
    failure = model.probability(A("failure", 2, 10, 1))
    success = model.probability(A("success", 2, 10, 1))
    assert success > failure > none
    assert model.probability(A("success", 2, 10, 8)) < success          # many contacts this campaign: fatigue


def test_explanations_make_sense(model):
    top = model.score(A("success", 3, 2, 1))
    assert top["factors"][0]["feature"] == "contact_history" and top["factors"][0]["contribution"] > 0.1
    assert "success" in top["factors"][0]["value"]
    assert model.score(A())["factors"] == [] or all(f["feature"] != "contact_history" for f in model.score(A())["factors"])


# ------------------------------------------------------------------ train / serve consistency
@pytest.mark.skipif(not Path(BANK_CSV).exists(), reason="dataset not downloaded (python -m backend.data_engine.ml.fetch_datasets)")
def test_runtime_scorer_reproduces_the_hold_out_metrics_in_the_model_card(model):
    sk = pytest.importorskip("sklearn.metrics")
    with open(BANK_CSV, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    from backend.data_engine.ml.train_lead_model import years_of
    start = years_of(rows).index(2009)
    win = rows[start:]
    test = win[int(0.8 * len(win)):]
    y = [r["y"] == "yes" for r in test]
    p = [model.probability(F.bank_row_to_attrs(r)) for r in test]
    card = model.card["metrics"]
    assert sk.average_precision_score(y, p) == pytest.approx(card["pr_auc"], abs=1e-3)
    assert sk.roc_auc_score(y, p) == pytest.approx(card["roc_auc"], abs=1e-3)
    assert sk.brier_score_loss(y, p) == pytest.approx(card["brier"], abs=1e-3)
    assert sum(y) / len(y) == pytest.approx(card["prevalence"], abs=1e-3)


# ------------------------------------------------------------------ the model card is honest
def test_model_card_is_real_and_states_its_limits(model):
    card = model.card
    fixture = load_fixture("lead_scores")["model_card"]
    assert set(fixture) - {"note"} <= set(card) and card["placeholder"] is False      # "note" only explains the placeholder
    assert set(fixture["metrics"]) == set(card["metrics"]) and all(card["metrics"][k] is not None for k in card["metrics"])
    assert card["selected"] == "logistic_regression" and card["challenger_model"] == "hist_gradient_boosting"
    assert "duration" in card["excluded_features"] and "month" in card["excluded_features"]
    text = " ".join(card["caveats"]).lower()
    assert "not calibrated to aarohi" in text and "not stationary" in text and "association, not causation" in text


def test_the_shipped_model_beats_the_baseline_and_the_report_is_complete():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    m = report["holdout_metrics"]
    assert m["logistic_regression_calibrated_SHIPPED"]["pr_auc"] > m["constant_prevalence_baseline"]["pr_auc"] + 0.1
    assert m["logistic_regression_calibrated_SHIPPED"]["roc_auc"] > 0.6
    assert m["logistic_regression_calibrated_SHIPPED"]["pr_auc"] >= m["hist_gradient_boosting_challenger"]["pr_auc"]   # why LR ships
    assert "drift_note" in report and report["split"]["positive_rate"]["holdout"] > report["split"]["positive_rate"]["development"]
    assert report["calibrator_selection"]["chosen"] in ("isotonic", "sigmoid")
    assert report["split"]["development"] != report["split"]["holdout"]


# ------------------------------------------------------------------ the queue
def test_queue_shape_matches_the_contract(queue):
    fixture = load_fixture("lead_scores")
    assert set(fixture) <= set(queue) and queue["ranking"] == fixture["ranking"]
    assert queue["high_value_threshold_inr"] == 15000 and queue["synthetic"] is True
    for lead in queue["leads"]:
        assert set(lead) == set(fixture["leads"][0]), lead["lead_id"]


def test_queue_is_ranked_by_probability_times_value(queue):
    ranked = [l for l in queue["leads"] if not l["abstain"]]
    assert [l["rank"] for l in ranked] == list(range(1, len(ranked) + 1))
    scores = [l["score_value_inr"] for l in ranked]
    assert scores == sorted(scores, reverse=True)
    for l in ranked:
        assert l["score_value_inr"] == pytest.approx(l["probability"] * l["expected_value_inr"], abs=0.01)
        assert 0 <= l["probability"] <= 1 and l["baseline"] == pytest.approx(0.178, abs=0.001)
    assert queue["leads"][-1]["abstain"] is True


def test_the_incomplete_lead_abstains(queue):
    lead = next(l for l in queue["leads"] if l["lead_id"] == "lead_0455")
    assert lead["abstain"] and lead["probability"] is None and lead["rank"] is None and lead["factors"] == []
    assert "channel" in lead["abstain_reason"] and "previous_outcome" in lead["abstain_reason"]


def test_hot_leads_are_in_the_queue_unattended(queue):
    hot = [l for l in queue["leads"] if l["high_value"] and not l["attended"]]
    assert {l["lead_id"] for l in hot} == {i for i, *_ in C.HOT_LEADS} and len(hot) == 8
    assert all(l["hours_since_inquiry"] >= 20 for l in hot)
    top3 = [l["lead_id"] for l in queue["leads"][:3]]
    assert "lead_0412" in top3                                              # the salon chain with a previous success


def test_only_open_leads_of_the_period_are_queued(queue):
    t = leads.kpis.indexed("baseline")
    ids = {l["lead_id"] for l in queue["leads"]}
    for created, lead in t.leads_in(C.CURRENT_START, C.CURRENT_END):
        assert (lead["lead_id"] in ids) == (t.stage(lead) not in ("won", "lost")), lead["lead_id"]
    assert not any(l["lead_id"] in ids for l in t.t.leads if l["created_at"][:10] < C.CURRENT_START.isoformat())


def test_limit_keeps_the_top_ranked_then_abstentions():
    top = public.get_lead_scores("biz_aarohi_skin", 3)["leads"]
    assert [l["rank"] for l in top] == [1, 2, 3]
    everything = public.get_lead_scores("biz_aarohi_skin", 10_000)["leads"]
    assert everything[-1]["abstain"] and len(everything) == len(public.get_lead_scores("biz_aarohi_skin")["leads"])


def test_day7_queue_only_has_followup_week_leads_and_one_unattended():
    q = public.get_lead_scores("biz_aarohi_skin", None, "day7")
    t = leads.kpis.indexed("day7")
    by_id = {l["lead_id"]: l for l in t.t.leads}
    assert all(C.DAY7_START.isoformat() <= by_id[l["lead_id"]]["created_at"][:10] <= C.DAY7_END.isoformat() for l in q["leads"])
    assert sum(l["high_value"] and not l["attended"] for l in q["leads"]) == 1
    assert q["scored_at"] == "2026-10-12T04:30:00Z"


def test_unknown_and_empty_businesses():
    assert public.get_lead_scores("biz_nope") is None
    client.post("/api/v1/businesses", json={"name": "Lead Free Co", "goal": {"statement": "Grow repeat"}})
    empty = public.get_lead_scores("biz_lead_free_co")
    assert empty["leads"] == [] and empty["model_card"]["placeholder"] is False


# ------------------------------------------------------------------ API
def test_api_queue_and_card():
    client.post("/api/v1/demo/load?phase=baseline")
    r = client.get("/api/v1/businesses/biz_aarohi_skin/leads/queue?limit=5")
    assert r.status_code == 200 and len(r.json()["leads"]) == 5 and r.json()["leads"][0]["rank"] == 1
    card = client.get("/api/v1/models/lead-conversion/card").json()
    assert card["placeholder"] is False and card["metrics"]["pr_auc"] > 0.6
    assert client.get("/api/v1/businesses/biz_nope/leads/queue").status_code == 404
    assert client.get("/api/v1/businesses/biz_aarohi_skin/leads/queue?limit=0").status_code == 422
    assert client.get("/api/v1/businesses/biz_aarohi_skin/leads/queue?snapshot=weird").status_code == 422


def test_api_default_follows_the_loaded_phase_but_public_defaults_to_baseline():
    client.post("/api/v1/demo/load?phase=day7")
    try:
        api = client.get("/api/v1/businesses/biz_aarohi_skin/leads/queue").json()
        assert api["scored_at"] == "2026-10-12T04:30:00Z"
        assert public.get_lead_scores("biz_aarohi_skin")["scored_at"] == "2026-10-04T04:30:00Z"   # what decision_engine calls
        assert client.get("/api/v1/businesses/biz_aarohi_skin/leads/queue?snapshot=baseline").json()["scored_at"] == "2026-10-04T04:30:00Z"
    finally:
        client.post("/api/v1/demo/load?phase=baseline")
