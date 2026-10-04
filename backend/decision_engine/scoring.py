"""Priority equation (contract section 2.4). Blocked actions are never scored.

Benefit     = 0.32*I + 0.18*U + 0.18*F + 0.17*R + 0.15*T
CostPenalty = 0.45*E + 0.30*C + 0.25*D
Priority    = 100 * Benefit * (0.5 + 0.5*Q) * (1 - 0.55*CostPenalty)
"""
BENEFIT_WEIGHTS = {"I": 0.32, "U": 0.18, "F": 0.18, "R": 0.17, "T": 0.15}
COST_WEIGHTS = {"E": 0.45, "C": 0.30, "D": 0.25}
FACTOR_KEYS = tuple("IUFRTQECD")


def _check(factors: dict) -> None:
    for k in FACTOR_KEYS:
        v = factors.get(k)
        if not isinstance(v, (int, float)) or not 0 <= v <= 1:
            raise ValueError(f"factor {k} must be a number in [0, 1], got {v!r}")


def benefit(f: dict) -> float:
    return sum(w * f[k] for k, w in BENEFIT_WEIGHTS.items())


def cost_penalty(f: dict) -> float:
    return sum(w * f[k] for k, w in COST_WEIGHTS.items())


def priority(f: dict) -> float:
    _check(f)
    return 100 * benefit(f) * (0.5 + 0.5 * f["Q"]) * (1 - 0.55 * cost_penalty(f))


def score(f: dict) -> dict:
    """Rounded breakdown shown in the API and UI."""
    p = priority(f)
    return {"benefit": round(benefit(f), 4), "cost_penalty": round(cost_penalty(f), 4), "priority": round(p, 1)}
