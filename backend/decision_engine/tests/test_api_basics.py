from backend.decision_engine import templates
from backend.decision_engine.config import Settings

import pytest


def test_health(client):
    body = client.get("/api/v1/decision/health").json()
    assert body["status"] == "ok" and body["data_source"] == "fixture" and body["templates"] == 6


def test_templates_endpoint(client):
    body = client.get("/api/v1/intervention-templates").json()
    ids = {t["template_id"] for t in body["templates"]}
    assert {"tpl_hot_lead_followup", "tpl_increase_ad_spend"} <= ids


def test_template_validation_rejects_bad_dependencies():
    bad = templates.templates_by_id()["tpl_repeat_email_flow"]
    bad["tasks"][1]["after"] = ["nope"]
    with pytest.raises(templates.TemplateError):
        templates.validate_template(bad)


def test_templates_for_trigger():
    ids = [t["template_id"] for t in templates.templates_for_trigger("high_spend_low_contribution")]
    assert ids == ["tpl_instagram_attribution_test", "tpl_increase_ad_spend"]


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("LLM_CACHE_ONLY", "true")
    monkeypatch.setenv("LLM_API_KEY", "secret")
    s = Settings.from_env()
    assert s.llm_provider == "anthropic" and s.llm_cache_only is True
    assert "secret" not in repr(s)
    monkeypatch.setenv("LLM_PROVIDER", "nope")
    with pytest.raises(ValueError):
        Settings.from_env()


def test_unknown_route_error_shape(client):
    assert client.get("/api/v1/nope").status_code == 404
