"""7-day plan generator.

1. Take approved recommendations, best priority first; drop conflicting ones (two actions
   that change spend on the same channel).
2. Expand each into its template's task blueprints.
3. List-schedule: of the tasks whose dependencies are placed, take the one with the least
   slack (latest feasible day, from its dependency chain) and put it on the earliest day
   that respects dependencies (+ gap days), the per-day cap and the owner's weekly minutes.
4. A recommendation is planned whole or not at all. If something does not fit, the
   lowest-priority recommendation is dropped (reported under `skipped`) and the rest
   are rescheduled.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

from backend.decision_engine import templates
from backend.decision_engine.recommend import format_text, kpi_label

DAYS = 7
SPEND_CHANGES = {"increase_total_ad_spend", "reallocate_within_channel_budget"}


class PlanError(ValueError):
    pass


def select(recs: list[dict]) -> tuple[list[dict], list[dict]]:
    """Approved, non-conflicting recommendations (best first) and the ones dropped."""
    tmpl = templates.templates_by_id()
    chosen, skipped, spend_channels = [], [], set()
    for rec in sorted((r for r in recs if r["status"] == "approved"), key=lambda r: -(r["priority"] or 0)):
        t = tmpl[rec["template_id"]]
        ch = rec["targets"].get("channel")
        if t["spend_change"] in SPEND_CHANGES and ch:
            if ch in spend_channels:
                skipped.append({"recommendation_id": rec["recommendation_id"],
                                "reason": f"conflicts with another spend change on {ch}"})
                continue
            spend_channels.add(ch)
        chosen.append(rec)
    return chosen, skipped


def latest_days(tasks: list[dict]) -> dict:
    """Latest day each task can happen and still let its whole chain finish by day 7."""
    by_id = {t["task_id"]: t for t in tasks}
    children = defaultdict(list)
    for t in tasks:
        for d in t["depends_on"]:
            if d not in by_id:
                raise PlanError(f"{t['task_id']} depends on unknown task {d}")
            children[d].append(by_id[t["task_id"]])
    memo = {}

    def latest(tid, stack=()):
        if tid in stack:
            raise PlanError("task dependencies contain a cycle")
        if tid not in memo:
            memo[tid] = min([DAYS] + [latest(c["task_id"], stack + (tid,)) - c["_gap"] for c in children[tid]])
        return memo[tid]

    return {t["task_id"]: latest(t["task_id"]) for t in tasks}


def _owner_for(role: str, owners: list[dict], used: dict, minutes: int) -> Optional[str]:
    """The owner with that role if they have the minutes, else anyone with spare minutes."""
    same = [o for o in owners if o["role"] == role]
    others = sorted((o for o in owners if o["role"] != role), key=lambda o: used[o["owner_id"]] - o["weekly_minutes"])
    for o in same + others:
        if used[o["owner_id"]] + minutes <= o["weekly_minutes"]:
            return o["owner_id"]
    return None


def schedule(tasks: list[dict], ctx: dict) -> tuple[list[dict], set]:
    """List scheduling: among tasks whose dependencies are placed, place the one with the least
    slack (earliest latest-day) first, on the earliest day that fits. Returns (placed, failed recs)."""
    cap = ctx["capacity"]
    weekly = cap.get("weekly_minutes") or cap.get("weekly_hours", 8) * 60
    per_day = cap.get("max_minutes_per_day") or weekly
    owners = cap.get("owners") or [{"owner_id": "owner", "role": "Owner", "weekly_minutes": weekly}]
    latest = latest_days(tasks)
    day_used, owner_used, total = defaultdict(int), defaultdict(int), 0
    placed, failed = {}, set()
    pending = list(tasks)
    while pending:
        ready = [t for t in pending if all(d in placed for d in t["depends_on"])]
        if not ready:  # only tasks of failed recommendations are left
            failed |= {t["recommendation_id"] for t in pending}
            break
        t = min(ready, key=lambda t: (latest[t["task_id"]], t["_order"]))
        pending.remove(t)
        earliest = max([t["_earliest"]] + [placed[d]["day"] + t["_gap"] for d in t["depends_on"]])
        for day in range(earliest, DAYS + 1):
            if day_used[day] + t["effort_min"] > per_day or total + t["effort_min"] > weekly:
                continue
            owner = _owner_for(t["_role"], owners, owner_used, t["effort_min"])
            if owner:
                t.update(day=day, owner=owner)
                day_used[day] += t["effort_min"]
                owner_used[owner] += t["effort_min"]
                total += t["effort_min"]
                placed[t["task_id"]] = t
                break
        else:
            failed.add(t["recommendation_id"])
    return sorted(placed.values(), key=lambda t: (t["day"], t["_order"])), failed


def expand(recs: list[dict], ctx: dict, first_task_no: int) -> list[dict]:
    tmpl = templates.templates_by_id()
    tasks, n = [], first_task_no
    for rank, rec in enumerate(recs):
        t = tmpl[rec["template_id"]]
        ids = {}
        for i, bp in enumerate(t["tasks"]):
            ids[bp["key"]] = f"task_{n:02d}"
            n += 1
        for i, bp in enumerate(t["tasks"]):
            kpi = rec["expected"]["kpi"]
            tasks.append({
                "task_id": ids[bp["key"]], "day": None, "date": None,
                "title": format_text(bp["title"], ctx, rec["targets"]),
                "reason": bp.get("reason", ""), "effort_min": bp["effort_min"], "owner": None,
                "kpi": kpi, "kpi_label": kpi_label(kpi),
                "success_criterion": format_text(bp.get("success_criterion", ""), ctx, rec["targets"]),
                "depends_on": [ids[k] for k in bp["after"]], "status": "todo",
                "recommendation_id": rec["recommendation_id"], "requires_approval": bp.get("requires_approval", False),
                "_order": (rank, i), "_earliest": bp["earliest_day"], "_gap": bp["gap_days"], "_role": bp["owner_role"],
            })
    return tasks


def build(plan_id: str, recs: list[dict], ctx: dict, start: date, first_task_no: int, now: str) -> dict:
    chosen, skipped = select(recs)
    if not chosen:
        raise PlanError("no approved recommendations to plan")
    while True:
        # a recommendation is planned whole or not at all; when the week is too full,
        # the lowest-priority one is dropped and the rest are rescheduled
        placed, failed = schedule(expand(chosen, ctx, first_task_no), ctx)
        if not failed:
            break
        dropped = chosen.pop()
        skipped.append({"recommendation_id": dropped["recommendation_id"],
                        "reason": "its tasks do not fit in this week's capacity"})
        if not chosen:
            raise PlanError("none of the approved recommendations fit this week's capacity")
    failed = set()
    for t in placed:
        t["date"] = (start + timedelta(days=t["day"] - 1)).isoformat()
        for k in ("_order", "_earliest", "_gap", "_role"):
            t.pop(k, None)
    planned = [r["recommendation_id"] for r in chosen if r["recommendation_id"] not in failed]
    if not planned:
        raise PlanError("none of the approved recommendations fit this week's capacity")
    cap = ctx["capacity"]
    return {
        "plan_id": plan_id, "business_id": ctx["business_id"], "synthetic": ctx.get("synthetic", False),
        "status": "active", "created_at": now,
        "week": {"from": start.isoformat(), "to": (start + timedelta(days=DAYS - 1)).isoformat()},
        "recommendation_ids": planned, "skipped": skipped,
        "capacity": {"weekly_minutes": cap.get("weekly_minutes"), "max_minutes_per_day": cap.get("max_minutes_per_day")},
        "planned_minutes": sum(t["effort_min"] for t in placed), "tasks": placed,
    }
