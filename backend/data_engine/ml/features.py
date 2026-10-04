"""Feature schema shared by training and serving (pure Python, so there is no train/serve skew).

The model is trained on UCI Bank Marketing but may only use fields that ALSO exist on an Aarohi Skin lead
(the "shared feature schema"). Banking-specific fields (job, marital, education, default, housing, loan, the
macro-economic indicators), `contact` and `day_of_week` have no meaning for a skincare lead and are excluded.
`duration` is excluded because it is only known after the outcome (leakage). `month` is excluded because in a
two-year dataset it cannot be separated from the campaign period (the bank's conversion rate shifted a lot
between periods), so it does not generalise.

Bank column -> lead attribute
  poutcome  -> previous_outcome         (nonexistent | failure | success)
  previous  -> prior_contacts           (contacts before this inquiry)
  pdays     -> days_since_last_contact  (999 = never contacted)
  campaign  -> contacts_this_campaign
"""
from __future__ import annotations

from typing import Optional

PREVIOUS_OUTCOMES = ["nonexistent", "failure", "success"]
REQUIRED = ("previous_outcome", "prior_contacts", "days_since_last_contact", "contacts_this_campaign")

FEATURES = ["previous_outcome=failure", "previous_outcome=success", "prior_contacts", "never_contacted",
            "days_since_last_contact", "contacts_this_campaign"]
NUMERIC = ["prior_contacts", "days_since_last_contact", "contacts_this_campaign"]

# Explanation groups. previous_outcome, prior_contacts and days_since_last_contact are three views of ONE fact
# (the contact history: "nonexistent" <=> 0 prior contacts <=> 999 days), so they are explained together.
GROUP_ATTRS = {
    "contact_history": ["previous_outcome", "prior_contacts", "days_since_last_contact"],
    "contacts_this_campaign": ["contacts_this_campaign"],
}


def describe_group(name: str, attrs: dict):
    """Human-readable value of an explanation group."""
    if name == "contact_history":
        if attrs["previous_outcome"] == "nonexistent" or int(attrs["days_since_last_contact"]) >= 999:
            return "no previous contact"
        return f"previous outcome {attrs['previous_outcome']}; {attrs['prior_contacts']} prior contacts; last contact {attrs['days_since_last_contact']} days ago"
    return attrs[GROUP_ATTRS[name][0]]


EXCLUDED_FEATURES = {
    "duration": "known only after the call: leakage",
    "job": "banking-specific", "marital": "banking-specific", "education": "banking-specific",
    "default": "banking-specific", "housing": "banking-specific", "loan": "banking-specific",
    "contact": "no equivalent on a skincare lead", "day_of_week": "bank data has weekdays only; leads arrive on weekends too",
    "age": "not collected on leads, and not an actionable factor",
    "month": "confounded with the campaign period in a two-year dataset; does not generalise",
    "emp.var.rate": "macro indicator for Portugal", "cons.price.idx": "macro indicator for Portugal",
    "cons.conf.idx": "macro indicator for Portugal", "euribor3m": "macro indicator for Portugal",
    "nr.employed": "macro indicator for Portugal",
}


def bank_row_to_attrs(row: dict) -> dict:
    return {"previous_outcome": row["poutcome"], "prior_contacts": int(row["previous"]),
            "days_since_last_contact": int(row["pdays"]), "contacts_this_campaign": int(row["campaign"])}


def missing_fields(attrs: Optional[dict], channel: Optional[str] = None) -> list:
    """Fields that are absent or invalid. A lead with any of these is not scored (abstention)."""
    attrs = attrs or {}
    out = [] if channel else ["channel"]
    for f in REQUIRED:
        v = attrs.get(f)
        if v is None or (f == "previous_outcome" and v not in PREVIOUS_OUTCOMES):
            out.append(f)
    return out


def encode_raw(attrs: dict) -> list:
    """Unscaled feature vector in FEATURES order. Caller must have checked missing_fields()."""
    po = attrs["previous_outcome"]
    days = int(attrs["days_since_last_contact"])
    never = 1.0 if days >= 999 else 0.0
    vec = {
        "previous_outcome=failure": float(po == "failure"), "previous_outcome=success": float(po == "success"),
        "prior_contacts": float(min(max(int(attrs["prior_contacts"]), 0), 7)),
        "never_contacted": never,
        "days_since_last_contact": 0.0 if never else float(min(max(days, 0), 30)),
        "contacts_this_campaign": float(min(max(int(attrs["contacts_this_campaign"]), 1), 10)),
    }
    return [vec[f] for f in FEATURES]


def scale(vec: list, scaler: dict) -> list:
    out = list(vec)
    for i, name in enumerate(FEATURES):
        if name in scaler:
            out[i] = (vec[i] - scaler[name]["mean"]) / scaler[name]["std"]
    return out
