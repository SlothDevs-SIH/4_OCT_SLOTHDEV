"""Offline training of the lead-conversion model (needs numpy + scikit-learn; not used at runtime).

    python -m backend.data_engine.ml.train_lead_model

Method (leakage-safe, and honest about the data)
- Data: UCI Bank Marketing (bank-additional-full), used standalone. The file is in chronological order
  (May 2008 .. Nov 2010).
- Features: only the shared feature schema (features.py). `duration` is never used; `month` is excluded (it is
  confounded with the campaign period and does not generalise).
- Modeling window: from March 2009 onward. 2008 (67% of the file) has almost no previous-campaign information
  (97% "nonexistent", 35 successes), so including it teaches the model "no history means no conversion" and hides
  previous_outcome, the strongest predictor (a previous success converts at 65%). The window is chosen from data
  coverage, not from model scores.
- Hold-out: the LAST 20% of the window (strictly the latest period) is never touched until the final evaluation.
- Selection: logistic-regression C by out-of-fold PR-AUC, and the calibrator (isotonic vs sigmoid) by
  cross-validated Brier on the out-of-fold predictions, both with BLOCKED time-contiguous cross-validation inside
  the development set. The calibrator is fitted on out-of-fold predictions only.
- Compared on the hold-out: constant-prevalence baseline, logistic regression (shipped: portable and
  explainable), gradient-boosting challenger, and an ablation that adds the month feature back.
- Metrics: PR-AUC, ROC-AUC, Brier score, expected calibration error, lift@10%.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from . import features as F
from .fetch_datasets import BANK_CSV, BANK_ROWS, checksum, fetch_bank

OUT = Path(__file__).resolve().parent / "artifacts"
FOLDS = 4
YEARS = [2008, 2009, 2010]
MONTH_ORDER = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]


def load_rows() -> list:
    fetch_bank()
    with open(BANK_CSV, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    assert len(rows) == BANK_ROWS, len(rows)
    return rows


def years_of(rows) -> list:
    year, prev, out = 2008, None, []
    for r in rows:
        m = MONTH_ORDER.index(r["month"])
        if prev is not None and m < prev:
            year += 1
        prev = m
        out.append(year)
    return out


def span(rows, years) -> str:
    return f"{MONTH_ORDER.index(rows[0]['month']) + 1:02d}/{years[0]} .. {MONTH_ORDER.index(rows[-1]['month']) + 1:02d}/{years[-1]}"


def ece(y, p, bins: int = 10) -> float:
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, bins - 1)
    total = 0.0
    for b in range(bins):
        m = idx == b
        if m.any():
            total += m.mean() * abs(p[m].mean() - y[m].mean())
    return float(total)


def lift_at(y, p, frac: float = 0.10) -> float:
    k = max(1, int(len(y) * frac))
    top = np.argsort(-p, kind="stable")[:k]
    return float(y[top].mean() / y.mean())


def metrics(y, p) -> dict:
    return {"pr_auc": round(float(average_precision_score(y, p)), 4), "roc_auc": round(float(roc_auc_score(y, p)), 4),
            "brier": round(float(brier_score_loss(y, p)), 4), "calibration_error": round(ece(y, p), 4),
            "lift_at_10pct": round(lift_at(y, p), 2), "prevalence": round(float(y.mean()), 4), "n": int(len(y))}


def matrix(rows) -> np.ndarray:
    return np.array([F.encode_raw(F.bank_row_to_attrs(r)) for r in rows], dtype=float)


def oof_predict(make_model, X, y, folds=FOLDS):
    """Out-of-fold predictions with contiguous (blocked) folds: each block is predicted by a model that never saw it."""
    out = np.zeros(len(y))
    blocks = np.array_split(np.arange(len(y)), folds)
    for b in blocks:
        train = np.ones(len(y), dtype=bool)
        train[b] = False
        out[b] = make_model().fit(X[train], y[train]).predict_proba(X[b])[:, 1]
    return out


def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p)).reshape(-1, 1)


def fit_sigmoid(p, t):
    m = LogisticRegression(C=1e6, max_iter=1000).fit(logit(p), t)
    return float(m.coef_[0][0]), float(m.intercept_[0])


def apply_sigmoid(ab, p):
    return 1 / (1 + np.exp(-(ab[0] * logit(p).ravel() + ab[1])))


def main():
    all_rows = load_rows()
    all_years = years_of(all_rows)
    start = all_years.index(2009)                      # modeling window: previous-campaign information exists from 2009
    rows, years = all_rows[start:], all_years[start:]
    n = len(rows)
    i2 = int(0.8 * n)
    dev, test = rows[:i2], rows[i2:]
    y_dev = np.array([r["y"] == "yes" for r in dev], dtype=float)
    y_te = np.array([r["y"] == "yes" for r in test], dtype=float)
    X_dev_raw, X_te_raw = matrix(dev), matrix(test)

    names = list(F.FEATURES)
    scaler = {}
    for i, name in enumerate(names):
        if name in F.NUMERIC:
            col = X_dev_raw[:, i]
            scaler[name] = {"mean": float(col.mean()), "std": float(col.std() or 1.0)}
    X_dev = np.array([F.scale(list(r), scaler) for r in X_dev_raw])
    X_te = np.array([F.scale(list(r), scaler) for r in X_te_raw])

    # 1. choose C by out-of-fold PR-AUC (blocked CV inside the development set)
    grid = {}
    for C in (0.01, 0.1, 1.0, 10.0):
        grid[C] = float(average_precision_score(y_dev, oof_predict(lambda C=C: LogisticRegression(C=C, max_iter=2000), X_dev, y_dev)))
    C_best = max(grid, key=grid.get)
    p_oof = oof_predict(lambda: LogisticRegression(C=C_best, max_iter=2000), X_dev, y_dev)

    # 2. choose the calibrator by cross-validated Brier on the out-of-fold predictions (blocked folds)
    def cv_brier(kind):
        total, blocks = 0.0, np.array_split(np.arange(len(p_oof)), FOLDS)
        for b in blocks:
            tr = np.ones(len(p_oof), dtype=bool)
            tr[b] = False
            if kind == "isotonic":
                pred = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0).fit(p_oof[tr], y_dev[tr]).predict(p_oof[b])
            else:
                pred = apply_sigmoid(fit_sigmoid(p_oof[tr], y_dev[tr]), p_oof[b])
            total += brier_score_loss(y_dev[b], pred)
        return total / FOLDS

    cv = {"isotonic": cv_brier("isotonic"), "sigmoid": cv_brier("sigmoid")}
    method = min(cv, key=cv.get)
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0).fit(p_oof, y_dev)
    ab = fit_sigmoid(p_oof, y_dev)

    # 3. final model on the whole development set, evaluated ONCE on the untouched hold-out
    lr = LogisticRegression(C=C_best, max_iter=2000).fit(X_dev, y_dev)
    p_raw = lr.predict_proba(X_te)[:, 1]
    p_iso, p_sig = iso.predict(p_raw), apply_sigmoid(ab, p_raw)
    p_cal = p_sig if method == "sigmoid" else p_iso
    hgb = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_depth=3, random_state=0).fit(X_dev_raw, y_dev)
    p_hgb = hgb.predict_proba(X_te_raw)[:, 1]
    def with_month(Xs_, rows_):
        cols = [[float(r["month"] == m) for m in MONTH_ORDER[2:]] for r in rows_]      # mar..dec
        return np.hstack([Xs_, np.array(cols)])

    p_month = LogisticRegression(C=C_best, max_iter=2000).fit(with_month(X_dev, dev), y_dev).predict_proba(with_month(X_te, test))[:, 1]
    prev_dev = float(y_dev.mean())

    report = {
        "dataset": {"name": "UCI Bank Marketing (bank-additional-full)", "rows_in_file": len(all_rows), "rows_in_window": n,
                    "sha1": checksum(BANK_CSV)[:12], "citation": "Moro, Cortez and Rita (2014)"},
        "split": {"method": "modeling window = rows from 2009 onward; development = first 80%; hold-out = last 20% (strictly later in time)",
                  "window": f"rows {start + 1}..{len(all_rows)} ({span(rows, years)})",
                  "development": f"{span(dev, years[:i2])}",
                  "holdout": f"{span(test, years[i2:])}",
                  "sizes": {"development": len(dev), "holdout": len(test)},
                  "positive_rate": {"development": round(prev_dev, 4), "holdout": round(float(y_te.mean()), 4)},
                  "selection": f"blocked time-contiguous {FOLDS}-fold CV inside the development set",
                  "why_2009_onward": "2008 has almost no previous-campaign information (97% 'nonexistent'); including it hides previous_outcome",
                  "why_no_month": "month is confounded with the campaign period in a two-year dataset"},
        "development_cv": {"oof_pr_auc_by_C": {str(k): round(v, 4) for k, v in grid.items()}, "chosen_C": C_best,
                           "oof_metrics_of_chosen_C": metrics(y_dev, p_oof)},
        "calibrator_selection": {"criterion": f"{FOLDS}-fold blocked cross-validated Brier on out-of-fold predictions",
                                 "cv_brier": {k: round(v, 4) for k, v in cv.items()}, "chosen": method},
        "holdout_metrics": {
            "constant_prevalence_baseline": metrics(y_te, np.full(len(y_te), prev_dev)),
            "logistic_regression_uncalibrated": metrics(y_te, p_raw),
            "logistic_regression_isotonic": metrics(y_te, p_iso),
            "logistic_regression_sigmoid": metrics(y_te, p_sig),
            "logistic_regression_calibrated_SHIPPED": metrics(y_te, p_cal),
            "hist_gradient_boosting_challenger": metrics(y_te, p_hgb),
            "ablation_logistic_regression_WITH_month": metrics(y_te, p_month),
        },
        "drift_note": "The positive rate rises from {:.1%} (development) to {:.1%} (hold-out): the data is not stationary, so a calibration learned on "
                      "earlier periods does not fully transfer to a later one.".format(prev_dev, float(y_te.mean())),
    }
    shipped = report["holdout_metrics"]["logistic_regression_calibrated_SHIPPED"]
    art = {
        "model_id": "lead_conversion_v1", "version": 1, "features": names, "scaler": scaler,
        "coef": [round(float(c), 6) for c in lr.coef_[0]], "intercept": round(float(lr.intercept_[0]), 6),
        "calibration": ({"method": "sigmoid", "a": round(ab[0], 6), "b": round(ab[1], 6)} if method == "sigmoid" else
                        {"method": "isotonic", "x": [round(float(v), 6) for v in iso.X_thresholds_],
                         "y": [round(float(v), 6) for v in iso.y_thresholds_]}),
        "reference": {"previous_outcome": "nonexistent", "prior_contacts": 0, "days_since_last_contact": 999,
                      "contacts_this_campaign": 2},
        "prevalence_train": round(prev_dev, 4),
        "model_card": {
            "model_id": "lead_conversion_v1", "placeholder": False,
            "dataset": "UCI Bank Marketing (bank-additional-full), used standalone",
            "excluded_features": list(F.EXCLUDED_FEATURES), "excluded_reasons": F.EXCLUDED_FEATURES,
            "shared_feature_schema": list(F.REQUIRED),
            "split": "modeling window from 2009 onward; chronological hold-out = last 20% untouched; selection by blocked time-contiguous cross-validation in the first 80%",
            "baseline_model": "logistic_regression", "challenger_model": "hist_gradient_boosting",
            "selected": "logistic_regression", "calibration": f"{method} (fitted on out-of-fold predictions; chosen by cross-validated Brier)",
            "metrics": {k: shipped[k] for k in ("pr_auc", "roc_auc", "brier", "lift_at_10pct", "calibration_error", "prevalence")},
            "evaluated_on": f"held-out last 20% of the 2009+ window (n={shipped['n']}, {span(test, years[i2:])})",
            "comparison": {"shipped_pr_auc": shipped["pr_auc"],
                           "challenger_pr_auc": report["holdout_metrics"]["hist_gradient_boosting_challenger"]["pr_auc"],
                           "constant_baseline_pr_auc": report["holdout_metrics"]["constant_prevalence_baseline"]["pr_auc"]},
            "caveats": [
                "Trained on a public bank telemarketing dataset, not on Aarohi Skin data",
                "Scores on demo leads use the shared feature schema only (4 inputs); banking fields are not available on a lead",
                "Probabilities are NOT calibrated to Aarohi Skin: they carry the bank data's base rates. Use them to RANK leads; absolute values are illustrative",
                "The dataset is not stationary: the positive rate was {:.1%} in the development period and {:.1%} in the hold-out period".format(
                    prev_dev, float(y_te.mean())),
                "Month is excluded on purpose (confounded with the campaign period); 2008 data is excluded because it has no previous-campaign information",
                "Association, not causation: probabilities rank leads, they do not prove that contacting a lead changes the outcome",
            ],
        },
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "lead_model.json").write_text(json.dumps(art, indent=2), encoding="utf-8")
    (OUT / "lead_model_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
