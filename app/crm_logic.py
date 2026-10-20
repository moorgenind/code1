"""
CRM business rules — scoring, follow-up SLAs, probabilities, approvals, scorecards.

Everything tunable lives in the constants at the top of this file, so changing
a weight or a threshold is a one-line edit, not a hunt through routers.
"""
from datetime import datetime, timedelta, timezone, date

# ─────────────────────────────────────────────────────────────────────────────
# Picklists (value -> label). Old free-text values remain valid on existing rows.
# ─────────────────────────────────────────────────────────────────────────────
LEAD_SOURCES = {
    "meta_ads": "Meta Ads", "google_ads": "Google Ads", "instagram": "Instagram (organic)",
    "website": "Website", "walk_in": "Walk-in / Showroom", "phone_inquiry": "Phone Inquiry",
    "architect_referral": "Architect Referral", "designer_referral": "Designer Referral",
    "builder_referral": "Builder Referral", "dealer_generated": "Dealer Generated",
    "employee_generated": "Employee Generated", "client_referral": "Existing Client Referral",
    "exhibition": "Exhibition", "event": "Event", "channel_partner": "Channel Partner",
    "consultant": "Consultant", "referral": "Referral (legacy)", "dealer": "Dealer (legacy)",
    "other": "Other",
}
ATTRIBUTION_TYPES = {"company": "Company Generated", "employee": "Employee Generated", "dealer": "Dealer Generated"}
BUDGET_RANGES = {"5_10L": "₹5–10 L", "10_25L": "₹10–25 L", "25_50L": "₹25–50 L", "50L_1Cr": "₹50 L – 1 Cr", "1Cr_plus": "₹1 Cr+"}
PROPERTY_TYPES = {
    "apartment": "Apartment", "villa": "Villa", "farmhouse": "Farmhouse", "penthouse": "Penthouse",
    "holiday_home": "Holiday Home", "hospitality": "Hospitality", "office": "Office",
    "commercial": "Commercial / Retail", "institutional": "Institutional", "showroom": "Showroom",
}
CONSTRUCTION_STAGES = {
    "planning": "Planning", "design": "Design Stage", "drawings": "Drawings Underway",
    "civil": "Civil Started", "mep": "MEP Started", "finishing": "Finishing Stage", "handover": "Handover Stage",
}
PURCHASE_TIMELINES = {"immediate": "Immediate", "1m": "1 Month", "3m": "3 Months", "6m": "6 Months", "12m": "12 Months", "24m": "24 Months"}
# "Brand" dimension for MIPL = product category
PRODUCT_CATEGORIES = {"architectural": "Architectural Lighting", "decorative": "Decorative Lighting", "automation": "ZigbeePlus Automation", "oem": "OEM / Factory"}
ACTIVITY_TYPES = {
    "call": "Call", "whatsapp": "WhatsApp", "email": "Email", "meeting": "Client Meeting",
    "video_meeting": "Video Meeting", "site_visit": "Site Visit", "architect_meeting": "Architect Meeting",
    "dealer_meeting": "Dealer Meeting", "showroom_visit": "Showroom Visit", "event": "Event",
    "note": "Note", "stage_change": "Stage Change", "system": "System",
}
# Activity types that count as a real touch for SLA purposes (system/stage_change alone don't)
TOUCH_TYPES = {k for k in ACTIVITY_TYPES if k not in ("system",)}
PARTNER_TYPES = {"architect": "Architect", "interior_designer": "Interior Designer", "pmc": "PMC / Consultant", "builder": "Builder / Developer"}
ARCHITECT_SEGMENTS = {"luxury_residential": "Luxury Residential", "hospitality": "Hospitality", "commercial": "Commercial", "healthcare": "Healthcare", "mixed": "Mixed"}
ARCHITECT_RANKS = {"A+": "A+ · ₹5 Cr+ influence", "A": "A · ₹2–5 Cr", "B": "B · ₹50 L–2 Cr", "C": "C · Emerging"}
DEALER_CLASSIFICATIONS = {"certified_execution": "Certified Execution Dealer", "supported": "Supported Dealer", "referral_partner": "Referral Partner"}
DEALER_LIFECYCLE = ["prospect", "evaluation", "training", "certification", "onboarding", "active", "review", "renewal", "inactive"]
DEALER_CAPABILITIES = {
    "sales": "Sales", "design": "Design", "installation": "Installation", "commissioning": "Commissioning",
    "service": "Service", "amc": "AMC", "electrical": "Electrical / MEP", "automation": "Automation",
    "networking": "Networking / AV",
}
REGIONS = ["South", "West", "North", "East", "Central"]

# ─────────────────────────────────────────────────────────────────────────────
# Lead scoring (max 100) → A ≥ 70, B ≥ 50, C ≥ 30, D below
# ─────────────────────────────────────────────────────────────────────────────
SCORE_BUDGET = {"5_10L": 5, "10_25L": 10, "25_50L": 15, "50L_1Cr": 20, "1Cr_plus": 25}
SCORE_PROPERTY = {"villa": 15, "penthouse": 15, "farmhouse": 15, "hospitality": 15, "holiday_home": 12,
                  "apartment": 10, "showroom": 10, "office": 8, "commercial": 8, "institutional": 8}
# Lighting + automation are specified during design/drawings and bought around civil/MEP
SCORE_STAGE = {"planning": 5, "design": 15, "drawings": 20, "civil": 20, "mep": 15, "finishing": 8, "handover": 3}
SCORE_TIMELINE = {"immediate": 15, "1m": 15, "3m": 12, "6m": 8, "12m": 4, "24m": 2}
SCORE_ARCHITECT = {"A+": 10, "A": 8, "B": 6, "C": 5, None: 4}   # architect attached but unranked → 4
GRADE_CUTOFFS = [(70, "A"), (50, "B"), (30, "C"), (0, "D")]


def score_lead(lead, architect_rank=None, has_architect=False):
    """Return (score, grade, breakdown). Grade is None if nothing qualifying is filled in yet."""
    interest = [c for c in (lead.product_interest or []) if c]
    parts = {
        "budget": SCORE_BUDGET.get(lead.budget_range, 0),
        "property": SCORE_PROPERTY.get(lead.property_type, 0),
        "stage": SCORE_STAGE.get(lead.construction_stage, 0),
        "interest": min(15, 5 * len(interest)),
        "timeline": SCORE_TIMELINE.get(lead.purchase_timeline, 0),
        "architect": SCORE_ARCHITECT.get(architect_rank, 4) if has_architect else 0,
    }
    filled = any([lead.budget_range, lead.property_type, lead.construction_stage, interest, lead.purchase_timeline, has_architect])
    score = sum(parts.values())
    if not filled:
        return None, None, parts
    grade = next(g for cutoff, g in GRADE_CUTOFFS if score >= cutoff)
    return score, grade, parts


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline probability by status (used for weighted forecast unless overridden)
# ─────────────────────────────────────────────────────────────────────────────
STATUS_PROBABILITY = {
    "new": 10, "qualified": 20, "active": 20, "design_in_progress": 30, "boq_in_progress": 40,
    "quote_sent": 50, "negotiation": 70, "won": 100, "lost": 0, "cold": 5,
}
OPEN_STATUSES = ["new", "qualified", "active", "design_in_progress", "boq_in_progress", "quote_sent", "negotiation"]
CLOSED_STATUSES = ["won", "lost", "cold"]


def lead_probability(lead):
    if lead.win_probability is not None:
        return max(0, min(100, int(lead.win_probability)))
    return STATUS_PROBABILITY.get(lead.status, 10)


# ─────────────────────────────────────────────────────────────────────────────
# Follow-up SLA — "no lead may remain untouched"
# max inactivity per status; escalation ladder at 1×, 2×, 3×, 4× the limit
# ─────────────────────────────────────────────────────────────────────────────
SLA_HOURS = {
    "new": 24,
    "qualified": 7 * 24, "active": 7 * 24,
    "design_in_progress": 14 * 24, "boq_in_progress": 14 * 24, "negotiation": 14 * 24,
    "quote_sent": 7 * 24,
}
ESCALATION_LADDER = ["Lead owner", "Sales manager", "Regional head", "Managing Director"]
DEALER_ACCEPT_HOURS = 24


def _aware(dt):
    if dt is None:
        return None
    if isinstance(dt, date) and not isinstance(dt, datetime):
        dt = datetime(dt.year, dt.month, dt.day)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def now_utc():
    return datetime.now(timezone.utc)


def sla_state(lead, now=None):
    """Return dict(limit_hours, idle_hours, overdue, level, escalate_to, due_at) or None if no SLA applies."""
    limit = SLA_HOURS.get(lead.status)
    if not limit:
        return None
    now = now or now_utc()
    last = _aware(lead.last_activity_at) or _aware(lead.created_at) or now
    idle_h = (now - last).total_seconds() / 3600
    level = int(idle_h // limit)  # 0 = within SLA
    level = min(level, len(ESCALATION_LADDER))
    return {
        "limit_hours": limit,
        "idle_hours": round(idle_h, 1),
        "idle_days": round(idle_h / 24, 1),
        "due_at": (last + timedelta(hours=limit)).isoformat(),
        "overdue": level >= 1,
        "level": level,
        "escalate_to": ESCALATION_LADDER[level - 1] if level >= 1 else None,
    }


def dealer_acceptance_overdue(lead, now=None):
    if lead.dealer_acceptance != "pending" or not lead.dealer_assigned_at:
        return False
    now = now or now_utc()
    return (now - _aware(lead.dealer_assigned_at)) > timedelta(hours=DEALER_ACCEPT_HOURS)


# ─────────────────────────────────────────────────────────────────────────────
# Quotation discount approval matrix
# ─────────────────────────────────────────────────────────────────────────────
APPROVAL_MATRIX = [  # (max discount inclusive, level)
    (5, "auto"),
    (10, "regional_manager"),
    (15, "national_head"),
    (100, "ceo"),
]
APPROVAL_LABELS = {"auto": "Auto-approved", "regional_manager": "Regional Manager", "national_head": "National Sales Head", "ceo": "Managing Director"}


def approval_level_for(discount_pct):
    d = float(discount_pct or 0)
    for cap, level in APPROVAL_MATRIX:
        if d <= cap:
            return level
    return "ceo"


# ─────────────────────────────────────────────────────────────────────────────
# Dealer scorecard (weights sum to 100) → Platinum / Gold / Silver / Watch List
# ─────────────────────────────────────────────────────────────────────────────
SCORECARD_WEIGHTS = {"revenue": 35, "conversion": 20, "compliance": 15, "training": 10, "installation": 10, "service": 10}
DEALER_TIERS = [(80, "Platinum"), (65, "Gold"), (45, "Silver"), (0, "Watch List")]
NEUTRAL_SCORE = 50  # used for manual components not yet rated


def dealer_tier(score):
    return next(t for cutoff, t in DEALER_TIERS if score >= cutoff)


# ─────────────────────────────────────────────────────────────────────────────
# Service SLAs
# ─────────────────────────────────────────────────────────────────────────────
SERVICE_SLA_HOURS = {"P1": 24, "P2": 72, "P3": 7 * 24}
TECH_REQUEST_DEFAULT_DAYS = {"lighting_layout": 5, "automation_proposal": 5, "canva_presentation": 3, "boq": 2, "drawing": 5, "automation_schematic": 5}
AMC_RENEWAL_WINDOW_DAYS = 30


def fy_prefix(d=None):
    """Indian financial year code, e.g. 2627 for Apr 2026 – Mar 2027."""
    d = d or date.today()
    start = d.year if d.month >= 4 else d.year - 1
    return f"{str(start)[2:]}{str(start + 1)[2:]}"


def options_payload():
    def opts(d):
        return [{"value": k, "label": v} for k, v in d.items()]
    return {
        "lead_sources": opts(LEAD_SOURCES),
        "attribution_types": opts(ATTRIBUTION_TYPES),
        "budget_ranges": opts(BUDGET_RANGES),
        "property_types": opts(PROPERTY_TYPES),
        "construction_stages": opts(CONSTRUCTION_STAGES),
        "purchase_timelines": opts(PURCHASE_TIMELINES),
        "product_categories": opts(PRODUCT_CATEGORIES),
        "activity_types": opts({k: v for k, v in ACTIVITY_TYPES.items() if k not in ("stage_change", "system")}),
        "partner_types": opts(PARTNER_TYPES),
        "architect_segments": opts(ARCHITECT_SEGMENTS),
        "architect_ranks": opts(ARCHITECT_RANKS),
        "dealer_classifications": opts(DEALER_CLASSIFICATIONS),
        "dealer_lifecycle": [{"value": s, "label": s.replace("_", " ").title()} for s in DEALER_LIFECYCLE],
        "dealer_capabilities": opts(DEALER_CAPABILITIES),
        "regions": [{"value": r, "label": r} for r in REGIONS],
        "status_probability": STATUS_PROBABILITY,
        "sla_hours": SLA_HOURS,
        "approval_matrix": [{"max_discount": c, "level": l, "label": APPROVAL_LABELS[l]} for c, l in APPROVAL_MATRIX],
        "scorecard_weights": SCORECARD_WEIGHTS,
    }
