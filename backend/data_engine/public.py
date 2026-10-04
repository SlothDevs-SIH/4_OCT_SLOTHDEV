"""In-process interface used by decision_engine when DATA_SOURCE=local.

Stages 1a-2b: every function is real (context, data quality, KPI facts, daily series, lead scores).
Signatures stay the same. Each function returns exactly the contract fixture shape, or None
when the business is unknown.
"""
from typing import Optional

from backend.common.fixtures import load_fixture
from backend.data_engine import kpis, leads, quality, store
from backend.data_engine.synth import config as C


def _for(business_id: str, name: str):
    data = load_fixture(name)
    return data if data.get("business_id") == business_id else None


def get_context(business_id: str) -> Optional[dict]:
    """Real (Stage 1a): the demo tenant's context or a business created through onboarding."""
    return store.get_context(business_id)


def get_kpi_facts(business_id: str, from_date: Optional[str] = None, to_date: Optional[str] = None,
                  snapshot: str = "baseline") -> Optional[list]:
    """Real (Stage 2a): computed by the KPI engine. `snapshot` 'baseline' = current week, 'day7' = follow-up week.
    `from_date`/`to_date` (ISO) compute a custom period. Raises ValueError for a bad period or snapshot."""
    if store.get_context(business_id) is None:
        return None
    if business_id != C.BUSINESS_ID:
        return []                       # a business with no data loaded has no facts
    return kpis.compute_facts(snapshot, from_date, to_date)


def get_lead_scores(business_id: str, limit: Optional[int] = None, snapshot: str = "baseline") -> Optional[dict]:
    """Real (Stage 2b): the trained model scores the open leads of the snapshot's period.
    `limit` keeps the top-ranked leads; abstentions come after them. Default snapshot is the baseline week."""
    if store.get_context(business_id) is None:
        return None
    if business_id != C.BUSINESS_ID:
        return {"business_id": business_id, "synthetic": False, "scored_at": None,
                "high_value_threshold_inr": C.HIGH_VALUE_THRESHOLD_INR, "ranking": "probability x expected_value_inr",
                "model_card": leads.model_card(), "leads": []}
    return leads.lead_scores(business_id, limit, snapshot)


def get_data_quality(business_id: str) -> Optional[dict]:
    """Real (Stage 1b): computed from the import jobs (the demo business imports its messy orders export)."""
    return quality.data_quality(business_id)


def get_kpi_series(business_id: str, from_date: Optional[str] = None, to_date: Optional[str] = None,
                   channel: Optional[str] = None) -> Optional[dict]:
    """Real (Stage 2a): daily per-channel series (instagram, google) + injected-incident ground truth."""
    if store.get_context(business_id) is None:
        return None
    if business_id != C.BUSINESS_ID:
        return {"business_id": business_id, "synthetic": False, "series": [], "injected_incidents": []}
    return kpis.daily_series(from_date, to_date, channel)


def get_market_context(from_date: Optional[str] = None, to_date: Optional[str] = None) -> dict:
    """Market context for timing advice: F1 race weekends in the range, the next race, and how much race weekends
    lift interest (public data: Jolpica-F1 calendar, Wikimedia page views). Not tied to one business."""
    from backend.data_engine.external import f1_calendar, f1_interest
    start = from_date or "2026-10-01"
    season = int(start[:4])
    end = to_date or f"{season}-12-31"
    return {"source": {"calendar": "Jolpica-F1 (Ergast successor), snapshot", "interest": "Wikimedia page views (CC0), snapshot"},
            "season": season, "from": start, "to": end,
            "race_weekends": f1_calendar.race_weekends(season, start, end),
            "next_race": f1_calendar.next_race(start),
            "interest_uplift": f1_interest.uplift(),
            "note": "Race weekends are demand windows for F1 merchandise. Page views measure interest in F1, not any brand's sales."}


def get_public_data() -> dict:
    """The public datasets in use, their licences, what each is for, and what we measured on them."""
    from backend.data_engine.external import f1_calendar, f1_interest, olist, retail, shoppers
    rp, op, sp = retail.load_profile(), olist.load_profile(), shoppers.load_profile()
    uplift = f1_interest.uplift()
    return {"datasets": [
        {"name": "Olist Brazilian E-Commerce", "domain": "small sellers on a marketplace (Brazil, 2016-2018)", "licence": olist.LICENCE,
         "citation": olist.CITATION, "role": "small-seller behaviour: orders per seller, repeat buying, delivery delays, reviews",
         "status": "integrated" if op else "not profiled yet",
         "result": ({"orders": op["orders"], "sellers": op["sellers"]["total"], "small_sellers_50_to_500_orders": op["sellers"]["small_sellers_50_to_500_orders"],
                     "repeat_customer_share_small_sellers": op["repeat_buying"]["customers_of_small_sellers"]["repeat_customer_share"],
                     "late_delivery_share": op["delivery"]["all"]["late_share"], "mean_review_score": op["reviews"]["all_orders"]["mean_score"]} if op else None)},
        {"name": "UCI Online Retail II", "domain": "e-commerce orders (UK gift-ware retailer, 2009-2011)", "licence": retail.LICENCE,
         "citation": retail.CITATION, "role": "validation corpus for order-sheet intake and order metrics; not a benchmark for small sellers",
         "status": "integrated" if rp else "not profiled yet",
         "result": ({"source_lines": rp["source_lines"], "orders": rp["order_metrics"]["orders"], "customers": rp["order_metrics"]["customers"],
                     "repeat_customer_share": rp["order_metrics"]["repeat_customer_share"],
                     "top_10_customer_revenue_share": rp["order_metrics"]["concentration"]["top_10"],
                     "intake_check": rp["intake_check"]} if rp else None)},
        {"name": "UCI Online Shoppers Purchasing Intention", "domain": "website sessions of an online shop", "licence": shoppers.LICENCE,
         "citation": shoppers.CITATION, "role": "conversion and new-vs-returning visitors; checks that intent signals outweigh light interest",
         "status": "integrated" if sp else "not profiled yet",
         "result": ({"sessions": sp["sessions"], "overall_conversion": sp["overall_conversion"],
                     "new_visitor_conversion": sp["by_visitor_type"]["New_Visitor"]["conversion"],
                     "returning_visitor_conversion": sp["by_visitor_type"]["Returning_Visitor"]["conversion"],
                     "page_value_lift": sp["reading"]["page_value_lift"]} if sp else None)},
        {"name": "UCI Bank Marketing", "domain": "bank phone campaigns (contact history and outcome)", "licence": "see UCI page; cited, not redistributed",
         "role": "learned challenger and sanity check for the lead score: contact history (bought before, recency)", "status": "integrated",
         "result": "trained logistic regression on 4 contact-history inputs (see the lead model card)"},
        {"name": "F1 race calendar (Jolpica-F1)", "domain": "motorsport schedule", "licence": "open API, no key; factual schedule",
         "role": "market context for the Box Box case study: race weekends are demand windows", "status": "integrated",
         "result": {"seasons": f1_calendar.available_seasons()}},
        {"name": "Wikipedia page views: Formula One", "domain": "public attention", "licence": "Wikimedia pageviews: CC0",
         "role": "evidence that race weekends raise interest, so timing advice can cite a number", "status": "integrated",
         "result": uplift.get("overall")},
    ], "not_used": "Instagram insights tutorial CSV (no stated licence); M5 (Kaggle competition terms, non-commercial); Kaggle/Maven datasets that fit other business types"}
