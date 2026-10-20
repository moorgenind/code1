"""
CRM dashboards — MD command centre, employee KPIs vs targets, early-warning
system and marketing ROI. Mounted at /crm-dashboard.
"""
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app import crm_logic as L
from app.crm_common import row_dict, jsonable

router = APIRouter()

MEETING_TYPES = ("meeting", "video_meeting", "architect_meeting", "dealer_meeting", "site_visit", "showroom_visit")


def _month_bounds(month: Optional[str]):
    """'YYYY-MM' → (start, end) as aware datetimes (IST month ≈ UTC month for reporting)."""
    if month:
        y, m = map(int, month.split("-"))
    else:
        t = date.today(); y, m = t.year, t.month
    start = datetime(y, m, 1, tzinfo=L.now_utc().tzinfo)
    end = datetime(y + (m == 12), (m % 12) + 1, 1, tzinfo=start.tzinfo)
    return start, end, f"{y:04d}-{m:02d}"


def _fy_start(today=None):
    today = today or date.today()
    y = today.year if today.month >= 4 else today.year - 1
    return datetime(y, 4, 1, tzinfo=L.now_utc().tzinfo)


def _mipl_invoices(db, start=None, end=None):
    q = db.query(models.Invoice).filter(or_(models.Invoice.invoice_from == "MIPL", models.Invoice.invoice_from == None))
    if start: q = q.filter(models.Invoice.created_at >= start)
    if end: q = q.filter(models.Invoice.created_at < end)
    return q.all()


def _lead_values(db, leads):
    ids = [l.lead_id for l in leads] or [0]
    boq = dict(db.query(models.Boq.lead_id, func.coalesce(func.sum(models.Boq.total_amount), 0))
               .filter(models.Boq.lead_id.in_(ids)).group_by(models.Boq.lead_id).all())
    return {l.lead_id: float(l.estimated_value or boq.get(l.lead_id) or 0) for l in leads}


# ═════════════════════════════════════════════════════════════════════════════
# Early-warning system
# ═════════════════════════════════════════════════════════════════════════════
def early_warnings(db):
    now, today = L.now_utc(), date.today()
    w = []

    def add(severity, area, title, detail, link=None, count=1):
        w.append({"severity": severity, "area": area, "title": title, "detail": detail, "link": link, "count": count})

    open_leads = db.query(models.Lead).filter(models.Lead.status.in_(list(L.SLA_HOURS.keys()))).all()
    overdue = [(l, L.sla_state(l)) for l in open_leads]
    overdue = [(l, s) for l, s in overdue if s and s["overdue"]]
    critical = [x for x in overdue if x[1]["level"] >= 3]
    if critical:
        add("high", "Leads", f"{len(critical)} leads escalated to Regional/MD level",
            ", ".join(l.lead_code for l, _ in critical[:6]), "/crm/followups", len(critical))
    if len(overdue) > len(critical):
        add("medium", "Leads", f"{len(overdue) - len(critical)} leads past follow-up SLA", "Untouched beyond their stage limit", "/crm/followups", len(overdue) - len(critical))
    new_untouched = [l for l in open_leads if l.status == "new" and (now - L._aware(l.created_at)).total_seconds() > 86400 and (l.last_activity_at is None or L._aware(l.last_activity_at) <= L._aware(l.created_at) + timedelta(minutes=5))]
    if new_untouched:
        add("high", "Leads", f"{len(new_untouched)} new leads not qualified within 24h", ", ".join(l.lead_code for l in new_untouched[:6]), "/crm/followups", len(new_untouched))
    hot_unowned = [l for l in open_leads if l.lead_grade in ("A", "B") and not l.owner_employee_id]
    if hot_unowned:
        add("medium", "Leads", f"{len(hot_unowned)} A/B leads without an owner", ", ".join(l.lead_code for l in hot_unowned[:6]), "/leads", len(hot_unowned))

    pend = [l for l in db.query(models.Lead).filter(models.Lead.dealer_acceptance == "pending").all() if L.dealer_acceptance_overdue(l)]
    if pend:
        add("high", "Dealers", f"{len(pend)} dealer assignments not accepted in 24h", ", ".join(l.lead_code for l in pend[:6]), "/crm/followups", len(pend))
    rej = db.query(models.Lead).filter(models.Lead.dealer_acceptance == "rejected", models.Lead.status.in_(L.OPEN_STATUSES)).count()
    if rej:
        add("medium", "Dealers", f"{rej} leads rejected by dealers — need reassignment", "", "/crm/followups", rej)
    soon = db.query(models.Dealer).filter(models.Dealer.agreement_end != None, models.Dealer.agreement_end <= today + timedelta(days=45)).all()
    if soon:
        add("medium", "Dealers", f"{len(soon)} dealer agreements expire within 45 days", ", ".join(d.firm_name for d in soon[:5]), "/dealers", len(soon))

    approvals = db.query(models.Boq).filter(models.Boq.approval_status == "pending").count()
    if approvals:
        add("medium", "Quotes", f"{approvals} discount approvals waiting", "", "/crm/approvals", approvals)

    a_rank = db.query(models.Architect).filter(models.Architect.is_active == True, models.Architect.ranking.in_(["A+", "A"])).all()
    cold_a = [a for a in a_rank if not a.last_meeting_date or (now - L._aware(a.last_meeting_date)).days > 30]
    if cold_a:
        add("medium", "Architects", f"{len(cold_a)} A+/A architects not met in 30+ days", ", ".join(a.firm_name for a in cold_a[:5]), "/architects", len(cold_a))
    fu = db.query(models.Architect).filter(models.Architect.is_active == True, models.Architect.next_followup_date < today).count()
    if fu:
        add("low", "Architects", f"{fu} architect follow-ups overdue", "", "/architects", fu)

    tech = db.query(models.DesignRequest).filter(models.DesignRequest.status.in_(["pending", "in_progress"])).all()
    tech_late = [r for r in tech if (L._aware(r.target_date) or (L._aware(r.created_at) + timedelta(days=L.TECH_REQUEST_DEFAULT_DAYS.get(r.request_type, 5)))) < now]
    if tech_late:
        add("medium", "Technical", f"{len(tech_late)} design/technical requests overdue", ", ".join(r.design_code or "" for r in tech_late[:6]), "/aftersales", len(tech_late))

    tk = db.query(models.ServiceTicket).filter(models.ServiceTicket.status.notin_(["resolved", "closed"])).all()
    tk_late = [t for t in tk if t.sla_due_at and L._aware(t.sla_due_at) < now]
    if tk_late:
        sev = "high" if any(t.priority == "P1" for t in tk_late) else "medium"
        add(sev, "Service", f"{len(tk_late)} service tickets past SLA", ", ".join(t.ticket_code for t in tk_late[:6]), "/aftersales", len(tk_late))
    amc_due = db.query(models.AmcContract).filter(models.AmcContract.status == "active", models.AmcContract.end_date != None,
                                                  models.AmcContract.end_date <= today + timedelta(days=L.AMC_RENEWAL_WINDOW_DAYS)).count()
    if amc_due:
        add("low", "Service", f"{amc_due} AMC contracts due for renewal", "", "/aftersales", amc_due)

    # Collections: unpaid invoices older than 30 days
    old_unpaid = db.query(models.Invoice).filter(models.Invoice.status.in_(["unpaid", "partial"]), models.Invoice.created_at < now - timedelta(days=30)).all()
    if old_unpaid:
        amt = 0.0
        for inv in old_unpaid:
            amt += float(inv.invoice_amount or 0) - sum(float(p.amount or 0) for p in inv.payments)
        if amt > 0:
            add("high" if amt > 1000000 else "medium", "Collections", f"₹{amt/100000:.1f} L outstanding beyond 30 days",
                f"{len(old_unpaid)} invoices", "/finance", len(old_unpaid))

    order = {"high": 0, "medium": 1, "low": 2}
    w.sort(key=lambda x: (order[x["severity"]], -x["count"]))
    return w


@router.get("/warnings")
def get_warnings(db: Session = Depends(get_db)):
    return early_warnings(db)


# ═════════════════════════════════════════════════════════════════════════════
# MD / CEO command centre
# ═════════════════════════════════════════════════════════════════════════════
@router.get("/ceo")
def ceo_dashboard(month: Optional[str] = None, db: Session = Depends(get_db)):
    from app.routers.crm import dealer_scorecards
    m_start, m_end, month_key = _month_bounds(month)
    fy_start = _fy_start()
    now = L.now_utc()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    all_leads = db.query(models.Lead).all()
    by_id = {l.lead_id: l for l in all_leads}
    values = _lead_values(db, all_leads)
    month_leads = [l for l in all_leads if l.created_at and m_start <= L._aware(l.created_at) < m_end]
    open_leads = [l for l in all_leads if l.status in L.OPEN_STATUSES]
    won_month = [l for l in all_leads if l.status == "won" and l.status_changed_at and m_start <= L._aware(l.status_changed_at) < m_end]

    def bucket(items, key):
        out = {}
        for i in items:
            k = key(i) or "unassigned"
            out[k] = out.get(k, 0) + 1
        return sorted([{"key": k, "count": v} for k, v in out.items()], key=lambda x: -x["count"])

    # Revenue (MIPL invoices) — month & FY, attributed through the lead
    inv_month = _mipl_invoices(db, m_start, m_end)
    inv_fy = _mipl_invoices(db, fy_start, None)
    emps = {e.employee_id: e.name for e in db.query(models.Employee).all()}
    dealers = {d.dealer_id: d.firm_name for d in db.query(models.Dealer).all()}
    archs = {a.architect_id: a.firm_name for a in db.query(models.Architect).all()}

    def rev_by(invs, fn):
        out = {}
        for inv in invs:
            lead = by_id.get(inv.lead_id)
            k = fn(lead) if lead else None
            k = k or "Unattributed"
            out[k] = out.get(k, 0.0) + float(inv.invoice_amount or 0)
        return sorted([{"key": k, "value": round(v, 2)} for k, v in out.items()], key=lambda x: -x["value"])

    def cat_of(l):
        ints = l.product_interest or []
        if len(ints) == 1: return L.PRODUCT_CATEGORIES.get(ints[0], ints[0])
        if l.category in L.PRODUCT_CATEGORIES: return L.PRODUCT_CATEGORIES[l.category]
        return (l.category or "Mixed").title()

    collected_month = db.query(func.coalesce(func.sum(models.Payment.amount), 0)).filter(
        models.Payment.payment_date >= m_start.replace(tzinfo=None), models.Payment.payment_date < m_end.replace(tzinfo=None)).scalar()

    # Marketing
    spend_rows = db.query(models.MarketingSpend).filter(models.MarketingSpend.month == month_key).all()
    spend = {}
    for r in spend_rows:
        spend[r.source] = spend.get(r.source, 0.0) + float(r.amount or 0)
    leads_by_source = {}
    for l in month_leads:
        leads_by_source[l.lead_source or "unknown"] = leads_by_source.get(l.lead_source or "unknown", 0) + 1
    won_by_source = {}
    for l in all_leads:
        if l.status == "won":
            won_by_source[l.lead_source or "unknown"] = won_by_source.get(l.lead_source or "unknown", 0) + 1
    marketing = []
    for src in sorted(set(spend) | set(leads_by_source)):
        s_amt = spend.get(src, 0.0)
        n = leads_by_source.get(src, 0)
        marketing.append({"source": src, "label": L.LEAD_SOURCES.get(src, src), "spend": s_amt, "leads": n,
                          "cost_per_lead": round(s_amt / n) if (s_amt and n) else None})
    total_spend = sum(spend.values())

    scorecards = dealer_scorecards(db)
    warnings = early_warnings(db)
    emp_kpis = employee_kpis(month_key, db)

    weighted = sum(values[l.lead_id] * L.lead_probability(l) / 100 for l in open_leads)
    tickets_open = db.query(models.ServiceTicket).filter(models.ServiceTicket.status.notin_(["resolved", "closed"])).all()

    return {
        "month": month_key,
        "commercial": {
            "leads_today": sum(1 for l in all_leads if l.created_at and L._aware(l.created_at) >= today_start),
            "leads_month": len(month_leads),
            "open_opportunities": len(open_leads),
            "pipeline_value": round(sum(values[l.lead_id] for l in open_leads), 2),
            "weighted_pipeline": round(weighted, 2),
            "won_month": len(won_month),
            "won_value_month": round(sum(values[l.lead_id] for l in won_month), 2),
            "revenue_month": round(sum(float(i.invoice_amount or 0) for i in inv_month), 2),
            "revenue_fy": round(sum(float(i.invoice_amount or 0) for i in inv_fy), 2),
            "collected_month": float(collected_month or 0),
        },
        "leads_by_source": [{**x, "label": "Not set" if x["key"] == "unassigned" else L.LEAD_SOURCES.get(x["key"], x["key"])} for x in bucket(month_leads, lambda l: l.lead_source)],
        "leads_by_grade": bucket([l for l in all_leads if l.status in L.OPEN_STATUSES], lambda l: l.lead_grade or "unscored"),
        "leads_by_attribution": bucket(month_leads, lambda l: l.attribution_type),
        "revenue_by_category": rev_by(inv_fy, cat_of),
        "revenue_by_dealer": rev_by(inv_fy, lambda l: dealers.get(l.dealer_id) or ("Direct" if not l.dealer_id else None))[:10],
        "revenue_by_employee": rev_by(inv_fy, lambda l: emps.get(l.owner_employee_id) or l.assigned_to)[:10],
        "revenue_by_architect": rev_by(inv_fy, lambda l: archs.get(l.architect_id))[:10],
        "revenue_by_state": rev_by(inv_fy, lambda l: l.state or l.city)[:10],
        "service": {
            "tickets_open": len(tickets_open),
            "warranty_claims_open": sum(1 for t in tickets_open if t.ticket_type == "warranty_claim"),
            "amc_active": db.query(models.AmcContract).filter(models.AmcContract.status == "active").count(),
        },
        "dealer_rankings": scorecards[:10],
        "employee_rankings": sorted(emp_kpis["employees"], key=lambda e: -e["actual"]["revenue"])[:10],
        "marketing": {"total_spend": total_spend, "leads": len(month_leads),
                      "cost_per_lead": round(total_spend / len(month_leads)) if (total_spend and month_leads) else None,
                      "by_source": marketing},
        "warnings": warnings,
    }


# ═════════════════════════════════════════════════════════════════════════════
# Employee KPIs vs targets
# ═════════════════════════════════════════════════════════════════════════════
KPI_KEYS = ["architect_meetings", "dealer_meetings", "new_architects", "new_dealers", "leads_generated", "site_visits", "revenue", "collections"]


@router.get("/employees")
def employee_kpis(month: Optional[str] = None, db: Session = Depends(get_db)):
    m_start, m_end, month_key = _month_bounds(month)
    emps = db.query(models.Employee).filter(models.Employee.is_active == True).order_by(models.Employee.name).all()
    acts = db.query(models.CrmActivity).filter(models.CrmActivity.activity_at >= m_start, models.CrmActivity.activity_at < m_end).all()
    leads = db.query(models.Lead).all()
    by_lead = {l.lead_id: l for l in leads}
    archs_new = db.query(models.Architect).filter(models.Architect.created_at >= m_start, models.Architect.created_at < m_end).all()
    arch_owned = {}
    for a in db.query(models.Architect).filter(models.Architect.is_active == True).all():
        if a.relationship_owner_id:
            arch_owned[a.relationship_owner_id] = arch_owned.get(a.relationship_owner_id, 0) + 1
    invs = _mipl_invoices(db, m_start, m_end)
    pays = db.query(models.Payment).filter(models.Payment.payment_date >= m_start.replace(tzinfo=None), models.Payment.payment_date < m_end.replace(tzinfo=None)).all()
    inv_lead = {i.invoice_id: i.lead_id for i in db.query(models.Invoice.invoice_id, models.Invoice.lead_id).all()}
    targets = {t.employee_id: t for t in db.query(models.EmployeeTarget).filter(models.EmployeeTarget.month == month_key).all()}
    # dealer "new" = activity type dealer_meeting with subject containing onboarding is too fuzzy; count dealers created in month owned via activity
    new_dealer_ids = {d.dealer_id for d in db.query(models.Dealer).filter(models.Dealer.created_at >= m_start, models.Dealer.created_at < m_end).all()}

    def owner(lead):
        return lead.owner_employee_id if lead else None

    out = []
    for e in emps:
        mine = [a for a in acts if a.employee_id == e.employee_id or (a.employee_id is None and a.performed_by == e.name)]
        a_meet = sum(1 for a in mine if a.activity_type == "architect_meeting" or (a.architect_id and a.activity_type in MEETING_TYPES))
        d_meet = sum(1 for a in mine if a.activity_type == "dealer_meeting" or (a.dealer_id and a.activity_type in MEETING_TYPES))
        visits = sum(1 for a in mine if a.activity_type == "site_visit")
        calls = sum(1 for a in mine if a.activity_type in ("call", "whatsapp", "email"))
        my_new_arch = [a for a in archs_new if a.relationship_owner_id == e.employee_id]
        gen = [l for l in leads if l.created_at and m_start <= L._aware(l.created_at) < m_end and (l.source_employee_id == e.employee_id or (not l.source_employee_id and l.owner_employee_id == e.employee_id))]
        owned = [l for l in leads if l.owner_employee_id == e.employee_id]
        won = [l for l in owned if l.status == "won"]
        lost = [l for l in owned if l.status in ("lost", "cold")]
        opps = [l for l in owned if l.status in L.OPEN_STATUSES and l.status != "new"]
        rev = sum(float(i.invoice_amount or 0) for i in invs if owner(by_lead.get(i.lead_id)) == e.employee_id)
        coll = sum(float(p.amount or 0) for p in pays if owner(by_lead.get(inv_lead.get(p.invoice_id))) == e.employee_id)
        overdue = sum(1 for l in owned if (L.sla_state(l) or {}).get("overdue"))
        open_tracked = sum(1 for l in owned if L.sla_state(l))
        new_dealers = len({a.dealer_id for a in mine if a.dealer_id in new_dealer_ids})
        actual = {
            "architect_meetings": a_meet, "dealer_meetings": d_meet, "new_architects": len(my_new_arch),
            "new_dealers": new_dealers, "leads_generated": len(gen), "site_visits": visits,
            "revenue": round(rev, 2), "collections": round(coll, 2),
        }
        t = targets.get(e.employee_id)
        target = {k: (jsonable(getattr(t, k)) if t else None) for k in KPI_KEYS}
        attainment = {k: (round(actual[k] / float(target[k]) * 100) if target[k] else None) for k in KPI_KEYS}
        out.append({
            "employee_id": e.employee_id, "name": e.name, "role": e.role,
            "actual": actual, "target": target, "attainment": attainment,
            "extra": {
                "calls": calls, "total_activities": len(mine), "architects_mapped": arch_owned.get(e.employee_id, 0),
                "opportunities": len(opps), "won": len(won), "lost": len(lost),
                "conversion_pct": round(len(won) / (len(won) + len(lost)) * 100, 1) if (won or lost) else None,
                "activity_compliance_pct": round((open_tracked - overdue) / open_tracked * 100) if open_tracked else None,
                "overdue_leads": overdue,
            },
        })
    return {"month": month_key, "kpis": KPI_KEYS, "employees": out}


class TargetIn(BaseModel):
    employee_id: int
    month: str
    architect_meetings: Optional[int] = None
    dealer_meetings: Optional[int] = None
    new_architects: Optional[int] = None
    new_dealers: Optional[int] = None
    leads_generated: Optional[int] = None
    site_visits: Optional[int] = None
    revenue: Optional[float] = None
    collections: Optional[float] = None


@router.put("/targets")
def upsert_target(payload: TargetIn, db: Session = Depends(get_db)):
    t = db.query(models.EmployeeTarget).filter(models.EmployeeTarget.employee_id == payload.employee_id,
                                               models.EmployeeTarget.month == payload.month).first()
    if not t:
        t = models.EmployeeTarget(employee_id=payload.employee_id, month=payload.month)
        db.add(t)
    for k in KPI_KEYS:
        if k in payload.dict(exclude_unset=True):
            setattr(t, k, getattr(payload, k))
    db.commit()
    return row_dict(t)


@router.post("/targets/copy")
def copy_targets(from_month: str, to_month: str, db: Session = Depends(get_db)):
    src = db.query(models.EmployeeTarget).filter(models.EmployeeTarget.month == from_month).all()
    n = 0
    for s in src:
        if db.query(models.EmployeeTarget).filter(models.EmployeeTarget.employee_id == s.employee_id, models.EmployeeTarget.month == to_month).first():
            continue
        db.add(models.EmployeeTarget(employee_id=s.employee_id, month=to_month, **{k: getattr(s, k) for k in KPI_KEYS}))
        n += 1
    db.commit()
    return {"copied": n}


# ═════════════════════════════════════════════════════════════════════════════
# Marketing spend
# ═════════════════════════════════════════════════════════════════════════════
class SpendIn(BaseModel):
    month: str
    source: str
    amount: float
    notes: Optional[str] = None


@router.get("/marketing-spend")
def list_spend(month: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(models.MarketingSpend)
    if month:
        q = q.filter(models.MarketingSpend.month == month)
    return [row_dict(r) for r in q.order_by(models.MarketingSpend.month.desc(), models.MarketingSpend.source).all()]


@router.post("/marketing-spend")
def add_spend(payload: SpendIn, db: Session = Depends(get_db)):
    r = models.MarketingSpend(**payload.dict())
    db.add(r)
    db.commit()
    db.refresh(r)
    return row_dict(r)


@router.delete("/marketing-spend/{spend_id}")
def delete_spend(spend_id: int, db: Session = Depends(get_db)):
    r = db.query(models.MarketingSpend).filter(models.MarketingSpend.spend_id == spend_id).first()
    if not r:
        raise HTTPException(404, "Not found")
    db.delete(r)
    db.commit()
    return {"ok": True}
