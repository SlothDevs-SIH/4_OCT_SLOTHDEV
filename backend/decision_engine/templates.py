"""Intervention template library: the only actions decision_engine may recommend."""
import copy
from functools import lru_cache

import jsonschema

from backend.common.fixtures import load_fixture

FACTOR = {"type": "number", "minimum": 0, "maximum": 1}
TASK_SCHEMA = {
    "type": "object",
    "required": ["key", "title", "effort_min", "owner_role", "after", "gap_days", "earliest_day"],
    "properties": {
        "key": {"type": "string"},
        "effort_min": {"type": "integer", "minimum": 1},
        "after": {"type": "array", "items": {"type": "string"}},
        "gap_days": {"type": "integer", "minimum": 0},
        "earliest_day": {"type": "integer", "minimum": 1, "maximum": 7},
    },
}
TEMPLATE_SCHEMA = {
    "type": "object",
    "required": ["template_id", "title", "action_type", "kpi", "expected_direction", "triggers",
                 "factors", "effort_min", "cost_inr", "time_to_signal_days", "requires_approval",
                 "requires_data", "spend_change", "recommendation_slug", "expected_change",
                 "measurement_window_days", "guardrails", "tasks"],
    "properties": {
        "template_id": {"type": "string", "pattern": "^tpl_"},
        "expected_direction": {"enum": ["up", "down"]},
        "triggers": {"type": "array", "minItems": 1, "items": {"type": "string"}},
        "factors": {"type": "object", "required": list("IFRTECD"),
                    "properties": {k: FACTOR for k in "IFRTECD"}},
        "effort_min": {"type": "integer", "minimum": 1},
        "cost_inr": {"type": "number", "minimum": 0},
        "expected_change": {"type": "object", "required": ["method"],
                            "properties": {"method": {"enum": ["relative", "lead_probability_sum"]}}},
        "tasks": {"type": "array", "minItems": 1, "items": TASK_SCHEMA},
    },
}


class TemplateError(ValueError):
    pass


def validate_template(t: dict) -> None:
    try:
        jsonschema.validate(t, TEMPLATE_SCHEMA)
    except jsonschema.ValidationError as e:
        raise TemplateError(f"{t.get('template_id', '?')}: {e.message}") from e
    keys = [task["key"] for task in t["tasks"]]
    if len(set(keys)) != len(keys):
        raise TemplateError(f"{t['template_id']}: duplicate task keys")
    for task in t["tasks"]:
        unknown = set(task["after"]) - set(keys)
        if unknown:
            raise TemplateError(f"{t['template_id']}: task {task['key']} depends on unknown {sorted(unknown)}")
    if sum(task["effort_min"] for task in t["tasks"]) != t["effort_min"]:
        raise TemplateError(f"{t['template_id']}: task minutes do not add up to effort_min")


@lru_cache(maxsize=1)
def _library() -> tuple:
    data = load_fixture("intervention_templates")
    for t in data["templates"]:
        validate_template(t)
    return data["version"], tuple(data["templates"])


def library() -> dict:
    """`{"version": ..., "templates": [...]}` as served by GET /intervention-templates."""
    version, templates = _library()
    return {"version": version, "templates": copy.deepcopy(list(templates))}


def templates_by_id() -> dict:
    return {t["template_id"]: t for t in library()["templates"]}


def templates_for_trigger(rule: str) -> list:
    return [t for t in library()["templates"] if rule in t["triggers"]]
