"""Lead-conversion model at runtime: logistic regression coefficients + isotonic calibration, pure Python.

Trained offline by `train_lead_model.py` and shipped as a small JSON artifact, so the API needs no
scikit-learn at runtime (important for serverless hosting).
"""
from __future__ import annotations

import json
import math
from bisect import bisect_right
from functools import lru_cache
from pathlib import Path

from . import features as F

ARTIFACT = Path(__file__).resolve().parent / "artifacts" / "lead_model.json"


def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


class LeadModel:
    def __init__(self, art: dict):
        self.art = art
        self.coef = art["coef"]
        self.intercept = art["intercept"]
        self.scaler = art["scaler"]
        self.cal = art["calibration"]
        self.cal_x = self.cal.get("x")
        self.cal_y = self.cal.get("y")
        self.reference = art["reference"]
        self.prevalence = art["prevalence_train"]   # base rate of the development period
        self.card = art["model_card"]

    @classmethod
    @lru_cache(maxsize=1)
    def load(cls) -> "LeadModel":
        return cls(json.loads(ARTIFACT.read_text(encoding="utf-8")))

    def raw_probability(self, attrs: dict) -> float:
        x = F.scale(F.encode_raw(attrs), self.scaler)
        return _sigmoid(self.intercept + sum(w * v for w, v in zip(self.coef, x)))

    def calibrate(self, p: float) -> float:
        if self.cal["method"] == "sigmoid":
            q = min(max(p, 1e-6), 1 - 1e-6)
            return _sigmoid(self.cal["a"] * math.log(q / (1 - q)) + self.cal["b"])
        xs, ys = self.cal_x, self.cal_y
        if p <= xs[0]:
            return ys[0]
        if p >= xs[-1]:
            return ys[-1]
        i = bisect_right(xs, p) - 1
        x0, x1, y0, y1 = xs[i], xs[i + 1], ys[i], ys[i + 1]
        return y0 if x1 == x0 else y0 + (y1 - y0) * (p - x0) / (x1 - x0)

    def probability(self, attrs: dict) -> float:
        return self.calibrate(self.raw_probability(attrs))

    def contributions(self, attrs: dict) -> list:
        """Effect of each explanation group on the probability, in probability points, versus a typical lead
        with no previous contact (the reference values), other groups unchanged. Sorted by size."""
        full = self.probability(attrs)
        out = []
        for name, attr_list in F.GROUP_ATTRS.items():
            alt = dict(attrs)
            for a in attr_list:
                alt[a] = self.reference[a]
            out.append({"feature": name, "value": F.describe_group(name, attrs), "contribution": round(full - self.probability(alt), 3)})
        return sorted(out, key=lambda c: -abs(c["contribution"]))

    def score(self, attrs: dict, top: int = 4) -> dict:
        p = self.probability(attrs)
        factors = [c for c in self.contributions(attrs) if abs(c["contribution"]) >= 0.005][:top]
        return {"probability": round(p, 3), "factors": factors}
