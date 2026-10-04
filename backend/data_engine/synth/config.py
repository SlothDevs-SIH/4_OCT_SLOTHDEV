"""Constants for the synthetic D2C tenant "Aarohi Skin".

Everything generated from here is SYNTHETIC and labelled `synthetic: True`.
The numbers below are the scripted anchors from contracts/fixtures/README.md: the generator is a
deterministic scenario with planted incidents, not a statistical claim about real businesses.
"""
from datetime import date, datetime

SEED = 20261004
BUSINESS_ID = "biz_aarohi_skin"

# Weeks run Sunday..Saturday. 21 weeks of history, then the "current" week.
HISTORY_START = date(2026, 5, 10)
CURRENT_START = date(2026, 9, 27)
CURRENT_END = date(2026, 10, 3)
BASELINE_START = date(2026, 8, 30)       # 4 full weeks before the current week
BASELINE_END = date(2026, 9, 26)
DAY7_START = date(2026, 10, 5)           # the follow-up week (outcome replay)
DAY7_END = date(2026, 10, 11)

AS_OF = datetime(2026, 10, 4, 4, 30)     # "now" for the baseline snapshot (UTC)
AS_OF_DAY7 = datetime(2026, 10, 12, 4, 30)

SLA_HOURS = 4
HIGH_VALUE_THRESHOLD_INR = 15000
PACKAGING_COST_INR = 13.5                  # per order, added to unit costs (so gross margin ~ 0.62)

# name, price, unit cost (same as contracts/fixtures/business_context.json)
SKUS = [
    {"sku": "ARS-SERUM-30", "name": "Niacinamide serum 30 ml", "price": 899, "unit_cost": 310},
    {"sku": "ARS-SUNSCREEN-50", "name": "Mineral sunscreen 50 g", "price": 749, "unit_cost": 270},
    {"sku": "ARS-CLEANSER-100", "name": "Gentle cleanser 100 ml", "price": 549, "unit_cost": 190},
]
SKU_WEIGHTS = [0.45, 0.30, 0.25]

CHANNELS = ["instagram", "google", "email", "whatsapp", "website"]

# campaigns per channel (18 in total)
CAMPAIGNS = {
    "instagram": ["Reels: niacinamide launch", "Reels: sunscreen summer", "Creator collab", "Retargeting: cart", "Lookalike: buyers", "Diwali pre-launch"],
    "google": ["Brand search", "Generic: serum", "Generic: sunscreen", "Shopping: all SKUs", "Performance Max", "YouTube: skincare routine"],
    "email": ["Welcome series", "Post-purchase", "Newsletter"],
    "whatsapp": ["Order updates + offers", "Win-back"],
    "referral": ["Friends and family"],
}

# Attribution of the non-paid orders (first orders / repeat orders)
OTHER_FIRST_CHANNELS = (["email", "whatsapp", "website", "referral"], [0.20, 0.35, 0.30, 0.15])
OTHER_REPEAT_CHANNELS = (["email", "whatsapp", "website"], [0.40, 0.35, 0.25])

COD_SHARE = 0.38
RTO_RATE_COD = 0.07
RTO_RATE_PREPAID = 0.01

# The August email cohort (customers whose first order was in Aug 2026 and who are on the email list)
EMAIL_COHORT_MONTH = (2026, 8)
EMAIL_COHORT_SIZE = 210
EMAIL_COHORT_REPEATS_BASELINE = 34       # repeat purchasers by 2026-09-26   (34/210 = 0.162)
EMAIL_COHORT_REPEATS_CURRENT = 45        # by 2026-10-03                      (45/210 = 0.214)
EMAIL_COHORT_REPEATS_DAY7 = 46           # by 2026-10-11                      (46/210 = 0.219)

# Scripted high-value (bulk / gifting) inquiries left unattended in the current week: (lead_id, label, channel, EV, age in hours)
HOT_LEADS = [
    ("lead_0388", "Corporate Diwali gifting (120 kits)", "instagram_dm", 54000, 61),
    ("lead_0412", "Salon chain bulk inquiry", "whatsapp", 42000, 39),
    ("lead_0397", "Boutique spa reorder", "email", 28000, 34),
    ("lead_0421", "Pharmacy stockist inquiry", "website_form", 36000, 33),
    ("lead_0403", "Wedding gifting hampers", "instagram_dm", 24000, 31),
    ("lead_0430", "Yoga studio retail shelf", "whatsapp", 18000, 28),
    ("lead_0415", "Hotel amenity kits trial", "website_form", 30000, 24),
    ("lead_0426", "Influencer collab bundle order", "instagram_dm", 15000, 20),
]
# High-value leads that were answered quickly in the same week: (lead_id, label, channel, EV, response hours, won?)
ATTENDED_HV = [
    ("lead_0431", "Cafe chain amenity kits", "whatsapp", 21000, 1.5, True),
    ("lead_0432", "Gym franchise retail", "email", 19000, 2.0, False),
    ("lead_0433", "Resort welcome kits", "website_form", 26000, 3.0, False),
    ("lead_0434", "Dermat clinic reseller", "instagram_dm", 17000, 4.5, False),
]
LEAD_FAMILY_PACK = ("lead_0441", "Family pack repeat order", "whatsapp", 3500, 3.0)
LEAD_INCOMPLETE = ("lead_0455", "Website inquiry, details missing", None, None, 20)
# Backlog leads that get answered and partly won in the day-7 week
DAY7_BACKLOG_WINS = {"lead_0412": "2026-10-07", "lead_0397": "2026-10-08", "lead_0430": "2026-10-09"}

# Weekly plans for the four baseline weeks and the incident weeks. Sums are the anchors.
IG_BASELINE = {
    "spend": [32900, 33500, 33000, 33440],          # 132,840 = 4 x 33,210
    "sessions": [3480, 3560, 3500, 3622],            # 14,162
    "customers": [80, 82, 81, 81],                   # 324  -> CAC 410.0
    "revenue": [68200, 69600, 68900, 68232],         # 274,932 -> ROAS 2.07
}
GOOGLE_BASELINE = {
    "spend": [16200, 16350, 16300, 16250],           # 65,100
    "sessions": [2190, 2215, 2210, 2210],            # 8,825
    "customers": [43, 44, 44, 44],                   # 175  -> CAC 372.0
    "revenue": [38000, 38300, 38100, 38295],         # 152,695
}
OTHERS_BASELINE = {
    "new": [6, 6, 6, 6],
    "repeat": [30, 31, 30, 29],
    "revenue": [34300, 34200, 34300, 34373],         # total revenue per week 140,500 .. 142,100 (avg 141,200)
    "sessions": [3680, 3720, 3700, 3712],
}
LEADS_BASELINE = {
    "leads": [146, 150, 147, 149],
    "qualified": [63, 65, 64, 64],
    "won": [25, 27, 26, 26],
    "hv_total": [10, 10, 10, 10],
    "hv_unattended": [1, 1, 1, 1],
    "hv_won": [2, 3, 2, 3],
}

CURRENT = {
    "instagram": {
        "spend": [5265, 4980, 5150, 5300, 5275, 5400, 5350],     # 36,720
        "sessions": [565, 522, 590, 580, 560, 590, 593],         # 4,000
        "customers": [13, 12, 8, 7, 6, 7, 7],                    # 60   (CAC spike from 2026-09-29)
        "revenue_per_customer": 849,                              # 50,940
    },
    "google": {"spend": 15960, "sessions": 2100, "customers": 42, "revenue": 36540},
    "others": {"new": 18, "repeat": 34, "revenue": 48080, "sessions": 3100},
    "leads": {"leads": 152, "qualified": 61, "won": 23, "hv_total": 12, "hv_unattended": 8, "hv_won": 1},
}
DAY7 = {
    "instagram": {
        "spend": [5000, 5050, 5000, 5050, 5000, 5000, 5000],     # 35,100
        "sessions": [550] * 7,                                    # 3,850
        "customers": [9, 9, 9, 9, 9, 9, 8],                       # 62  -> CAC 566.1
        "revenue_per_customer": 849,                              # 52,638 -> contribution ROAS 0.75
    },
    "google": {"spend": 15800, "sessions": 2100, "customers": 41, "revenue": 35670},
    "others": {"new": 18, "repeat": 36, "revenue": 50400, "sessions": 3150},
    "leads": {"leads": 155, "qualified": 64, "won": 26, "hv_total": 10, "hv_unattended": 1, "hv_won": 0},
}

# Day-by-day relative weights used when a week has no scripted daily pattern (Mon..Sun-ish noise is added)
DAY_WEIGHTS = [1.00, 0.97, 1.02, 1.05, 1.00, 1.08, 1.10]
