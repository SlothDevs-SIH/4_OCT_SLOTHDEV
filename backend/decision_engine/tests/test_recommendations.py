import json

from backend.decision_engine import recommend, templates
from backend.decision_engine.clients import DataClient
from backend.decision_engine.config import Settings
from backend.decision_engine.llm import providers
from backend.decision_engine.llm.cache import LLMCache
from backend.decision_engine.llm.synthesize import Synthesizer
from backend.decision_engine.llm.validator import validate_recommendation
from backend.decision_engine.service import Engine
from backend.decision_engine.signals import Facts

BIZ = "biz_aarohi_skin"
API = "/api/v1"


def test_generate_ranks_and_blocks(client):
    body = client.post(f"{API}/businesses/{BIZ}/recommendations/generate").json()
    recs = body["recommendations"]
    assert [r["recommendation_id"] for r in recs] == ["rec_hot_leads", "rec_email_retention", "rec_instagram_test",
                                                       "rec_increase_spend"]
    assert [r["rank"] for r in recs] == [1, 2, 3, None]
    hot, email, ig, spend = recs
    assert hot["priority"] > email["priority"] > ig["priority"]
    assert spend["status"] == "blocked" and spend["priority"] is None
    assert spend["blocked_reason"].startswith("Violates the constraint 'no increase in total ad spend'")
    assert hot["confidence"] == "high" and ig["confidence"] == "medium"
    assert (hot["expected"]["low"], hot["expected"]["high"]) == (2, 4)
    assert hot["targets"]["lead_ids"][:2] == ["lead_0412", "lead_0388"]
    for r in recs:
        assert r["llm"]["used"] is False  # no key and no cache entry in tests -> deterministic text


def test_every_fallback_passes_the_validator(engine):
    inp = engine.inputs(BIZ)
    sdoc = engine.signals(BIZ, inp)
    facts = Facts(inp["facts"])
    leads = {l["lead_id"]: l for l in inp["lead_scores"]["leads"]}
    tmpl = templates.templates_by_id()
    for rec in recommend.build(inp, sdoc, engine.synthesizer, "2026-10-04T00:00:00Z"):
        if rec["status"] == "blocked":
            continue
        sigs = [s for s in sdoc["signals"] if s["signal_id"] in rec["signal_ids"]]
        packet = recommend.evidence_packet(rec, tmpl[rec["template_id"]], sigs, facts, leads, inp["context"])
        out = {"template_id": rec["template_id"], "rationale": rec["rationale"], "evidence_ids": rec["evidence_ids"]}
        assert validate_recommendation(out, packet) == [], rec["recommendation_id"]


def test_evidence_ids_exist(client):
    recs = client.get(f"{API}/businesses/{BIZ}/recommendations").json()["recommendations"]
    known = {f["fact_id"] for f in DataClient("fixture").get_kpi_facts(BIZ)}
    known |= {l["lead_id"] for l in DataClient("fixture").get_lead_scores(BIZ)["leads"]}
    for r in recs:
        assert r["evidence_ids"] and set(r["evidence_ids"]) <= known


class EchoProvider(providers.Provider):
    """Answers like a well-behaved model: cites the packet and reuses its numbers."""
    name, model = "fake", "fake-1"

    def __init__(self):
        self.calls = 0

    def complete(self, system, user):
        self.calls += 1
        p = json.loads(user)
        fact = p["facts"][0]
        return json.dumps({"template_id": p["recommendation"]["template_id"],
                           "rationale": f"{p['signals'][0]['title']}. The plan is to {p['template']['title'].lower()}.",
                           "evidence_ids": [fact["fact_id"]], "assumptions": ["The owner has time this week"]})


def test_llm_path_then_offline_cache(tmp_path):
    settings = Settings(llm_cache_dir=tmp_path)
    fake = EchoProvider()
    eng = Engine(settings=settings, data=DataClient("fixture"),
                 synthesizer=Synthesizer(settings, provider=fake, cache=LLMCache(tmp_path)))
    recs = eng.generate(BIZ)["recommendations"]
    live = [r for r in recs if r["status"] != "blocked"]
    assert fake.calls == 3 and all(r["llm"]["used"] and not r["llm"]["cached"] for r in live)
    assert "The owner has time this week" in live[0]["assumptions"]
    offline = Engine(settings=Settings(llm_cache_only=True, llm_cache_dir=tmp_path), data=DataClient("fixture"))
    again = [r for r in offline.generate(BIZ)["recommendations"] if r["status"] != "blocked"]
    assert all(r["llm"]["used"] and r["llm"]["cached"] for r in again)
    assert [r["rationale"] for r in again] == [r["rationale"] for r in live]


def test_approve_freezes_ledger(client):
    client.post(f"{API}/businesses/{BIZ}/recommendations/generate")
    rec = client.post(f"{API}/recommendations/rec_hot_leads/approve", json={"by": "founder"}).json()
    assert rec["status"] == "approved" and rec["decision"]["by"] == "founder"
    led = rec["ledger"]
    assert (led["fact_id"], led["baseline"], led["expected"]["low"], led["expected"]["high"]) == ("f_hot_lead_wins", 1, 2, 4)
    assert led["guardrails"] == [{"kpi": "response_latency_p90", "fact_id": "f_latency_hot_leads", "max": 24, "baseline": 38.5}]
    ig = client.post(f"{API}/recommendations/rec_instagram_test/approve").json()
    assert ig["ledger"]["guardrails"][0] == {"kpi": "ad_spend", "fact_id": "f_spend_instagram", "max": 36720.0,
                                             "baseline": 36720.0}


def test_blocked_cannot_be_approved(client):
    client.post(f"{API}/businesses/{BIZ}/recommendations/generate")
    r = client.post(f"{API}/recommendations/rec_increase_spend/approve")
    assert r.status_code == 409 and r.json()["error"]["code"] == "blocked"


def test_reject_and_unknown(client):
    client.post(f"{API}/businesses/{BIZ}/recommendations/generate")
    rec = client.post(f"{API}/recommendations/rec_email_retention/reject", json={"note": "not now"}).json()
    assert rec["status"] == "rejected" and rec["ledger"] is None
    assert client.get(f"{API}/recommendations/rec_nope").status_code == 404


def test_decisions_survive_regeneration(client):
    client.post(f"{API}/businesses/{BIZ}/recommendations/generate")
    client.post(f"{API}/recommendations/rec_hot_leads/approve")
    client.post(f"{API}/recommendations/rec_email_retention/reject")
    recs = {r["recommendation_id"]: r for r in client.post(f"{API}/businesses/{BIZ}/recommendations/generate").json()["recommendations"]}
    assert recs["rec_hot_leads"]["status"] == "approved" and recs["rec_hot_leads"]["ledger"]
    assert recs["rec_email_retention"]["status"] == "rejected"
    assert recs["rec_instagram_test"]["status"] == "proposed"


def test_get_one_has_factor_breakdown(client):
    client.post(f"{API}/businesses/{BIZ}/recommendations/generate")
    r = client.get(f"{API}/recommendations/rec_hot_leads").json()
    assert set(r["factors"]) == set("IUFRTQECD") and r["q_breakdown"]["model"] == 0.85
    assert {c["check"] for c in r["eligibility"]} == {"forbidden_action", "budget", "capacity", "data", "approval"}
