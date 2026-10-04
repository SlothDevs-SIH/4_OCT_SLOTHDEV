import json

from backend.decision_engine import chat
from backend.decision_engine.clients import DataClient
from backend.decision_engine.config import Settings
from backend.decision_engine.llm import providers
from backend.decision_engine.llm.cache import LLMCache
from backend.decision_engine.llm.synthesize import Synthesizer
from backend.decision_engine.service import Engine

BIZ = "biz_aarohi_skin"
API = "/api/v1"
FACT_IDS = {f["fact_id"] for f in DataClient("fixture").get_kpi_facts(BIZ)}


def ask(client, q):
    r = client.post(f"{API}/businesses/{BIZ}/chat", json={"question": q})
    assert r.status_code == 200
    return r.json()


def test_answer_cites_real_facts(client):
    body = ask(client, "Why is my Instagram CAC so high?")
    assert body["citations"][0] == "f_cac_instagram" and set(body["citations"]) <= FACT_IDS
    assert "INR 612" in body["answer"] and "+49.3%" in body["answer"] and "CAC (instagram)" in body["answer"]
    assert "f_cac_google" not in body["citations"]  # asked about Instagram only


def test_channel_question_stays_on_channel(client):
    body = ask(client, "Is Google profitable?")
    assert body["citations"] == ["f_croas_google"] and "data quality is partial" in body["answer"]


def test_unknown_topic_says_so(client):
    body = ask(client, "What is the weather in Pune?")
    assert body["citations"] == [] and "not in the data" in body["answer"]


def test_empty_question_rejected(client):
    assert client.post(f"{API}/businesses/{BIZ}/chat", json={"question": "  "}).status_code == 422


def test_fallback_answer_passes_validator():
    facts = DataClient("fixture").get_kpi_facts(BIZ)
    from backend.decision_engine.llm.validator import validate_answer
    for q in ("repeat rate", "reply time to leads", "ad spend on instagram", "margin and revenue"):
        rel = chat.retrieve(q, facts)
        out = {"answer": " ".join(chat.describe(f) for f in rel), "citations": [f["fact_id"] for f in rel]}
        assert validate_answer(out, {"facts": rel}) == [], q


class Hallucinator(providers.Provider):
    name, model = "fake", "fake-1"

    def complete(self, system, user):
        return json.dumps({"answer": "Instagram CAC will drop to INR 300 next week.", "citations": ["f_cac_instagram"]})


def test_hallucinated_number_never_reaches_the_user(tmp_path):
    s = Settings(llm_cache_dir=tmp_path)
    eng = Engine(settings=s, data=DataClient("fixture"),
                 synthesizer=Synthesizer(s, provider=Hallucinator(), cache=LLMCache(tmp_path)))
    body = eng.chat(BIZ, "What is Instagram CAC?")
    assert "300" not in body["answer"] and body["llm"]["fallback"] is True
    assert any("numbers not in the evidence packet" in e for e in body["llm"]["validator"]["errors"])


# ---------------------------------------------------------------- drafts


def test_hot_lead_whatsapp_drafts(client):
    client.post(f"{API}/businesses/{BIZ}/recommendations/generate")
    d = client.get(f"{API}/recommendations/rec_hot_leads/draft?channel=whatsapp").json()
    assert d["status"] == "preview" and d["auto_send"] is False and d["requires_approval"] is True
    assert d["approved"] is False and len(d["messages"]) == 8 and d["messages"][0]["to"] == "lead_0412"
    assert "your salon chain bulk inquiry" in d["messages"][0]["body"]
    client.post(f"{API}/recommendations/rec_hot_leads/approve")
    assert client.get(f"{API}/recommendations/rec_hot_leads/draft?channel=email").json()["approved"] is True


def test_email_flow_draft(client):
    client.post(f"{API}/businesses/{BIZ}/recommendations/generate")
    d = client.get(f"{API}/recommendations/rec_email_retention/draft?channel=email").json()
    assert d["messages"][0]["subject"] == "Running low on your Niacinamide serum 30 ml?"
    assert "email opt-in" in d["audience"]
    r = client.get(f"{API}/recommendations/rec_email_retention/draft?channel=whatsapp")
    assert r.status_code == 422 and r.json()["error"]["code"] == "unsupported_channel"


def test_no_drafts_for_non_outreach_or_blocked(client):
    client.post(f"{API}/businesses/{BIZ}/recommendations/generate")
    r = client.get(f"{API}/recommendations/rec_instagram_test/draft?channel=email")
    assert r.status_code == 409 and r.json()["error"]["code"] == "not_outreach"
    assert client.get(f"{API}/recommendations/rec_increase_spend/draft").status_code == 409
    assert client.get(f"{API}/recommendations/rec_hot_leads/draft?channel=sms").status_code == 422


def test_there_is_no_send_endpoint(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/recommendations/{rec_id}/draft" in paths
    assert not any("send" in p for p in paths)
