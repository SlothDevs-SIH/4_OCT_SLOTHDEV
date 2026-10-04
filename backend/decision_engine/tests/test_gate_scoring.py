import copy

import pytest

from backend.common.fixtures import load_fixture
from backend.decision_engine import eligibility, factors, scoring, templates

T = templates.templates_by_id()


def inputs(**changes):
    inp = {"context": load_fixture("business_context"), "facts": load_fixture("kpi_facts"),
           "lead_scores": load_fixture("lead_scores"), "data_quality": load_fixture("data_quality")}
    for k, v in changes.items():
        inp[k] = v
    return inp


IG_SIGNAL = {"signal_id": "sig_instagram_cac_spike", "type": "anomaly", "method": "seasonal_median_mad_robust_z",
             "dimension": {"channel": "instagram"}, "urgency": 0.7}


# ---------------------------------------------------------------- scoring


def test_priority_hand_calculation_from_the_docs():
    f = dict(I=.8, U=1, F=.9, R=.5, T=.9, Q=.85, E=.25, C=.05, D=.10)
    s = scoring.score(f)
    assert (s["benefit"], s["cost_penalty"], s["priority"]) == (0.818, 0.1525, 69.3)


def test_priority_bounds_and_validation():
    assert scoring.priority(dict.fromkeys("IUFRTQ", 1.0) | dict.fromkeys("ECD", 0.0)) == pytest.approx(100)
    assert scoring.priority(dict.fromkeys("IUFRTQECD", 0.0)) == 0
    with pytest.raises(ValueError):
        scoring.priority(dict.fromkeys("IUFRTQECD", 0.5) | {"Q": 1.2})
    with pytest.raises(ValueError):
        scoring.priority({"I": 0.5})


def test_better_data_raises_priority():
    f = dict(I=.8, U=1, F=.9, R=.5, T=.9, Q=.5, E=.25, C=.05, D=.10)
    assert scoring.priority(f | {"Q": .9}) > scoring.priority(f)
    assert scoring.priority(f | {"E": .9}) < scoring.priority(f)


# ---------------------------------------------------------------- factors


def test_q_hand_calculation():
    # hot leads: data 0.82 (confidence, KPI quality ok), rule 1.0, model 1 - 10*0.015 = 0.85
    # Q = 0.5*0.82 + 0.25*1.0 + 0.25*0.85 = 0.8725
    sig = {"type": "bottleneck", "method": "rule", "urgency": 1.0}
    f, parts = factors.assemble(T["tpl_hot_lead_followup"], [sig], [], load_fixture("business_context"),
                                load_fixture("data_quality"), load_fixture("lead_scores"))
    assert parts == {"data": 0.82, "rule": 1.0, "model": 0.85}
    assert f["Q"] == 0.87 and f["U"] == 1.0


def test_partial_kpi_quality_lowers_q():
    croas = next(x for x in load_fixture("kpi_facts") if x["fact_id"] == "f_croas_instagram")
    f, parts = factors.assemble(T["tpl_instagram_attribution_test"], [IG_SIGNAL], [croas],
                                load_fixture("business_context"), load_fixture("data_quality"), {})
    assert parts["data"] == pytest.approx(0.82 * 0.75, abs=0.001) and "model" not in parts
    # anomaly-only evidence: rule strength 0.9 -> Q = (0.5*0.615 + 0.25*0.9) / 0.75 = 0.71
    assert parts["rule"] == 0.9 and f["Q"] == 0.71


def test_small_team_raises_effort_penalty():
    ctx = load_fixture("business_context")
    ctx["capacity"]["weekly_minutes"] = 120
    f, _ = factors.assemble(T["tpl_hot_lead_followup"], [IG_SIGNAL], [], ctx, load_fixture("data_quality"),
                            load_fixture("lead_scores"))
    assert f["E"] == 0.75  # 180 min of a 120 min week


# ---------------------------------------------------------------- gate


def test_increase_spend_is_blocked_with_reason():
    g = eligibility.gate(T["tpl_increase_ad_spend"], [IG_SIGNAL], inputs())
    assert g["eligible"] is False
    assert g["blocked_reason"].startswith("Violates the constraint 'no increase in total ad spend'")
    assert "Instagram CAC is up 49.3% and contribution ROAS is 0.694" in g["blocked_reason"]


def test_demo_actions_pass_the_gate():
    for tid in ("tpl_hot_lead_followup", "tpl_repeat_email_flow", "tpl_instagram_attribution_test"):
        g = eligibility.gate(T[tid], [IG_SIGNAL], inputs())
        assert g["eligible"], (tid, g)


def test_budget_blocks_paid_action_even_if_not_forbidden():
    ctx = load_fixture("business_context")
    ctx["constraints"]["forbidden_actions"] = []
    g = eligibility.gate(T["tpl_increase_ad_spend"], [IG_SIGNAL], inputs(context=ctx))
    assert not g["eligible"] and g["blocked_reason"].startswith("Needs INR 10000 of extra spend")


def test_capacity_blocks_large_action():
    ctx = load_fixture("business_context")
    ctx["capacity"]["weekly_minutes"] = 100
    g = eligibility.gate(T["tpl_hot_lead_followup"], [], inputs(context=ctx))
    assert not g["eligible"] and "180 minutes" in g["blocked_reason"]


def test_missing_data_blocks():
    ctx = load_fixture("business_context")
    ctx["channels"] = ["instagram", "google"]  # no email list
    g = eligibility.gate(T["tpl_repeat_email_flow"], [], inputs(context=ctx))
    assert not g["eligible"] and "email_consent" in g["blocked_reason"]
    leads = load_fixture("lead_scores")
    for l in leads["leads"]:
        l["abstain"] = True
    g = eligibility.gate(T["tpl_hot_lead_followup"], [], inputs(lead_scores=leads))
    assert not g["eligible"] and "lead_scores" in g["blocked_reason"]


def test_outreach_without_approval_is_unsafe():
    t = copy.deepcopy(T["tpl_hot_lead_followup"])
    t["requires_approval"] = False
    g = eligibility.gate(t, [], inputs())
    assert not g["eligible"] and "approval" in g["blocked_reason"]
