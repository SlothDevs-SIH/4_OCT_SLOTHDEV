"""Contract v2 routes owned by data_engine (see contracts/API_CONTRACT.md section 3). Included into the main router (prefix /api/v1)."""
from __future__ import annotations

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Query, Response
from pydantic import BaseModel, Field

from backend.common.errors import ApiError
from backend.data_engine.homebiz import facts as F
from backend.data_engine.homebiz import generate, intake, messy, projection
from backend.data_engine.homebiz import leads as L
from backend.data_engine.homebiz import store as hb
from backend.data_engine.homebiz.model import as_of_for, d

router = APIRouter(tags=["data_engine v2"])


def _biz(business_id: str):
    data = hb.get(business_id)
    if data is None:
        raise ApiError(404, "business_not_found", f"business {business_id!r} not found (load a demo business or create one first)")
    return data


def _week(data, business_id: str, week: Optional[int]) -> int:
    w = week or hb.current_week(business_id)
    try:
        as_of_for(w, data)
    except ValueError as e:
        raise ApiError(422, "invalid_week", str(e))
    return w


@router.get("/businesses/{business_id}/profile")
def profile(business_id: str):
    """Every profile field with where it came from (exact, estimate, derived)."""
    data = _biz(business_id)
    return {"business_id": business_id, "synthetic": bool(data.profile.get("synthetic")), "week": hb.current_week(business_id),
            "fields": data.profile["fields"], "profile": data.profile, "data": hb.counts(data)}


@router.get("/businesses/{business_id}/data-card")
def data_card(business_id: str):
    """What is calibrated on public data and what is a scenario assumption (demo businesses)."""
    data = _biz(business_id)
    card = data.meta.get("data_card")
    if card is None:
        raise ApiError(404, "no_data_card", "this business is not generated; its data is whatever the owner uploaded")
    return card


class WeekIn(BaseModel):
    week: int = Field(ge=1, le=4)


@router.post("/businesses/{business_id}/week")
def set_week(business_id: str, body: WeekIn):
    """Move the snapshot (week_1 .. week_4). Week 1 never sees week 2."""
    data = _biz(business_id)
    try:
        hb.set_week(business_id, body.week)
    except ValueError as e:
        raise ApiError(422, "invalid_week", str(e))
    return {"business_id": business_id, "week": body.week, "as_of": as_of_for(body.week, data).isoformat()}


# ------------------------------------------------------------------ demo helpers
@router.get("/demo/sample-chat")
def sample_chat(business: str = Query("boxbox", pattern="^(boxbox|homebaker)$"), week: int = Query(1, ge=1, le=4)):
    """Recent enquiries in a pasted-chat format, to try the lead intake."""
    data = generate.build(business)
    return {"business": business, "week": week, "format": "@handle (dm|comment|story|whatsapp): message",
            "text": generate.sample_chat(data, as_of_for(week, data)), "synthetic": True}


@router.get("/demo/sample-orders.csv")
def sample_orders_csv(business: str = Query("boxbox", pattern="^(boxbox|homebaker)$"), week: int = Query(1, ge=1, le=4)):
    """The deliberately messy orders sheet of a demo business (download it, then upload it to try the import)."""
    data = generate.build(business)
    return Response(messy.build_csv(data, week), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{business}_orders_messy.csv"'})


# ------------------------------------------------------------------ leads
class ChatIn(BaseModel):
    text: str = Field(min_length=1, max_length=20000)


@router.post("/businesses/{business_id}/leads/intake", status_code=201)
def leads_intake(business_id: str, body: ChatIn):
    """Pasted chat or comment text: identities are pseudonymised, intent is read, signals are added to each person's lead."""
    data = _biz(business_id)
    week = hb.current_week(business_id)
    as_of = as_of_for(week, data)
    msgs = intake.parse_chat(body.text, as_of - timedelta(days=1))
    if not msgs:
        raise ApiError(422, "no_messages", "no lines matched. Use '@handle (dm|comment|story|whatsapp): message' or a WhatsApp export line")
    nums = [int(l["lead_id"].split("_")[1]) for l in data.leads] or [0]
    touched, created = intake.leads_from_messages(msgs, data.profile["products"], data.profile.get("serves", {}), data.leads, max(nums))
    data.leads += created
    scored = {r["lead_id"]: r for r in L.score_all(touched, as_of, data.profile.get("serves"), data.profile["products"])}
    out = []
    for lead in touched:
        r = scored.get(lead["lead_id"])
        out.append({"lead_id": lead["lead_id"], "handle_ref": lead["handle_ref"], "intents": lead["intents"],
                    "messages": [{"text": t["text"], "intents": t.get("intents"), "method": t.get("method")} for t in lead["texts"]],
                    "score": r["score"] if r else None, "group": r["group"] if r else "not_a_lead", "reasons": r["reasons"] if r else []})
    not_leads = sum(1 for l in touched if "not_a_lead" in l["intents"] and not l["signals"])
    return {"business_id": business_id, "messages_read": len(msgs), "leads_created": len(created), "leads_updated": len(touched) - len(created),
            "not_a_lead": not_leads, "leads": out, "privacy": "names, phone numbers, e-mails and handles were pseudonymised before reading"}


@router.get("/businesses/{business_id}/leads")
def leads_list(business_id: str, group: Optional[str] = Query(None, pattern="^(hot|warm|cold|disqualified)$"), week: Optional[int] = Query(None, ge=1, le=4)):
    """Scored open leads (the daily list): hot first; at the same score a stranger ranks above a friend."""
    data = _biz(business_id)
    w = _week(data, business_id, week)
    as_of = as_of_for(w, data)
    rows = L.score_all(data.leads, as_of, data.profile.get("serves"), data.profile["products"])
    counts = {g: sum(1 for r in rows if r["group"] == g) for g in ("hot", "warm", "cold", "disqualified")}
    return {"business_id": business_id, "synthetic": bool(data.profile.get("synthetic")), "snapshot": f"week_{w}", "as_of": as_of.isoformat(),
            "counts": counts, "unmet_demand": L.unmet_demand(rows), "points_status": "starting guesses; see /leads/learning",
            "leads": [r for r in rows if group is None or r["group"] == group]}


class LeadPatch(BaseModel):
    relationship: Optional[str] = None
    intents: Optional[list[str]] = None
    outcome: Optional[str] = None
    outcome_date: Optional[str] = None


@router.patch("/leads/{lead_id}")
def lead_patch(lead_id: str, body: LeadPatch):
    """The owner tags friend or stranger, corrects an intent label, or records the outcome."""
    data, lead = hb.find_lead(lead_id)
    if lead is None:
        raise ApiError(404, "lead_not_found", f"lead {lead_id!r} not found")
    if body.relationship is not None:
        if body.relationship not in L.RELATIONSHIPS:
            raise ApiError(422, "invalid_relationship", f"relationship must be one of {L.RELATIONSHIPS}")
        lead["relationship"] = body.relationship
    if body.intents is not None:
        if not body.intents or any(i not in L.INTENTS for i in body.intents):
            raise ApiError(422, "invalid_intents", f"intents must be a non-empty subset of {L.INTENTS}")
        lead["intents"] = body.intents
        lead["intents_corrected_by_owner"] = True
    if body.outcome is not None:
        if body.outcome not in ("open", "ordered", "not_ordered"):
            raise ApiError(422, "invalid_outcome", "outcome must be open, ordered or not_ordered")
        lead["outcome"] = body.outcome
        if body.outcome == "open":
            lead["outcome_date"] = None
        else:
            as_of = as_of_for(hb.current_week(data.profile["business_id"]), data)
            lead["outcome_date"] = body.outcome_date or (as_of - timedelta(days=1)).isoformat()
    as_of = as_of_for(hb.current_week(data.profile["business_id"]), data)
    row = next((r for r in L.score_all([lead], as_of, data.profile.get("serves"), data.profile["products"])), None)
    return {"lead": {k: lead[k] for k in ("lead_id", "handle_ref", "relationship", "intents", "outcome", "outcome_date")}, "scored": row}


@router.get("/businesses/{business_id}/leads/learning")
def leads_learning(business_id: str, week: Optional[int] = Query(None, ge=1, le=4)):
    """The weekly check: do Hot, Warm and Cold leads order at different rates, which signals predict orders, and what public data says."""
    data = _biz(business_id)
    w = _week(data, business_id, week)
    return {"business_id": business_id, "snapshot": f"week_{w}", **L.learning_report(data.leads, as_of_for(w, data), data.profile.get("serves"), data.profile["products"])}


# ------------------------------------------------------------------ facts and projection
@router.get("/businesses/{business_id}/facts")
def facts_list(business_id: str, week: Optional[int] = Query(None, ge=1, le=4), bottleneck: Optional[str] = Query(None, pattern="^(reach|conversion|margin|repeat_orders|capacity)$")):
    """The facts for the five bottlenecks and the main measure at a weekly snapshot. Baseline = the business's own best weeks."""
    data = _biz(business_id)
    w = _week(data, business_id, week)
    try:
        fs = F.compute(data, w)
    except ValueError as e:
        raise ApiError(422, "not_enough_history", str(e))
    return {"business_id": business_id, "synthetic": bool(data.profile.get("synthetic")), "snapshot": f"week_{w}", "as_of": as_of_for(w, data).isoformat(),
            "main_measure": "f_stranger_orders_week", "facts": [f for f in fs if bottleneck is None or f["bottleneck"] == bottleneck]}


@router.get("/businesses/{business_id}/facts/weekly")
def facts_weekly(business_id: str, fact_id: str, week: Optional[int] = Query(None, ge=1, le=4)):
    data = _biz(business_id)
    w = _week(data, business_id, week)
    try:
        return {"business_id": business_id, **F.weekly_series(data, fact_id, w)}
    except KeyError:
        raise ApiError(404, "unknown_fact", f"unknown fact {fact_id!r}; known: {sorted(F.SPEC_BY_ID)}")


@router.get("/businesses/{business_id}/projection")
def projection_get(business_id: str, week: Optional[int] = Query(None, ge=1, le=4)):
    """Next month's orders with a range. An estimate, labelled as one; says so when there is too little history."""
    data = _biz(business_id)
    return projection.project(data, _week(data, business_id, week))
