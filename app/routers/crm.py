"""
CRM upgrade — lead qualification, scoring, activity log, follow-up SLAs,
dealer assignment engine, duplicate checks, forecasting and discount approvals.
Mounted at /crm.
"""
import re
from datetime import datetime, timedelta, date
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app import crm_logic as L
from app.crm_common import (row_dict, rescore, log_activity, user_name, is_approver, jsonable)

router = APIRouter()


# ═════════════════════════════════════════════════════════════════════════════
# Options / config
# ═════════════════════════════════════════════════════════════════════════════
@router.get("/options")
def crm_options(db: Session = Depends(get_db)):
    data = L.options_payload()
    data["employees"] = [
        {"value": e.employee_id, "label": e.name, "role": e.role}
        for e in db.query(models.Employee).filter(models.Employee.is_active == True).order_by(models.Employee.name).all()
    ]
    data["architects"] = [
        {"value": a.architect_id, "label": a.firm_name + (f" — {a.principal_name}" if a.principal_name else ""), "ranking": a.ranking, "city": a.city}
        for a in db.query(models.Architect).filter(models.Architect.is_active == True).order_by(models.Architect.firm_name).all()
    ]
    return data


# ═════════════════════════════════════════════════════════════════════════════
# Lead qualification profile + insights
# ═════════════════════════════════════════════════════════════════════════════
class LeadProfile(BaseModel):
    attribution_type: Optional[str] = None
    owner_employee_id: Optional[int] = None
    source_employee_id: Optional[int] = None
    architect_id: Optional[int] = None
    builder_name: Optional[str] = None
    lead_source: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    project_location: Optional[str] = None
    budget_range: Optional[str] = None
    property_type: Optional[str] = None
    property_size_sqft: Optional[int] = None
    construction_stage: Optional[str] = None
    expected_possession_date: Optional[date] = None
    purchase_timeline: Optional[str] = None
    product_interest: Optional[List[str]] = None
    estimated_value: Optional[float] = None
    win_probability: Optional[int] = None
    expected_order_date: Optional[date] = None


def _lead_or_404(db, lead_id):
    lead = db.query(models.Lead).filter(models.Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")
    return lead


def _employee_name(db, emp_id):
    if not emp_id:
        return None
    e = db.query(models.Employee).filter(models.Employee.employee_id == emp_id).first()
    return e.name if e else None


def _lead_value(db, lead):
    if lead.estimated_value:
        return float(lead.estimated_value)
    v = db.query(func.coalesce(func.sum(models.Boq.total_amount), 0)).filter(models.Boq.lead_id == lead.lead_id).scalar()
    return float(v or 0)


@router.patch("/leads/{lead_id}/profile")
def update_lead_profile(lead_id: int, payload: LeadProfile, request: Request, db: Session = Depends(get_db)):
    lead = _lead_or_404(db, lead_id)
    data = payload.dict(exclude_unset=True)
    for k, v in data.items():
        if isinstance(v, str) and v.strip() == "":
            v = None
        setattr(lead, k, v)
    # Owner employee also drives the legacy free-text assigned_to
    if "owner_employee_id" in data:
        name = _employee_name(db, lead.owner_employee_id)
        if name:
            lead.assigned_to = name
    if "architect_id" in data and lead.architect_id:
        arch = db.query(models.Architect).filter(models.Architect.architect_id == lead.architect_id).first()
        if arch:
            tracking = db.query(models.ProjectTracking).filter(models.ProjectTracking.lead_id == lead.lead_id).first()
            if tracking and not tracking.architect_name:
                tracking.architect_name = arch.firm_name
                tracking.architect_phone = arch.phone
    old_grade = lead.lead_grade
    rescore(db, lead)
    if lead.lead_grade and not lead.qualified_at:
        lead.qualified_at = L.now_utc()
    if old_grade != lead.lead_grade and lead.lead_grade:
        log_activity(db, lead_id=lead.lead_id, activity_type="system",
                     subject=f"Lead graded {lead.lead_grade} (score {lead.lead_score})",
                     performed_by=user_name(request), touch=False)
    db.commit()
    return lead_insights(lead_id, db)


@router.get("/leads/{lead_id}/insights")
def lead_insights(lead_id: int, db: Session = Depends(get_db)):
    lead = _lead_or_404(db, lead_id)
    arch = None
    if lead.architect_id:
        a = db.query(models.Architect).filter(models.Architect.architect_id == lead.architect_id).first()
        if a:
            arch = {"architect_id": a.architect_id, "firm_name": a.firm_name, "principal_name": a.principal_name, "ranking": a.ranking, "phone": a.phone}
    score, grade, parts = L.score_lead(lead, architect_rank=(arch or {}).get("ranking"), has_architect=bool(arch))
    acts = (db.query(models.CrmActivity).filter(models.CrmActivity.lead_id == lead_id)
            .order_by(models.CrmActivity.activity_at.desc()).limit(200).all())
    dealer = None
    if lead.dealer_id:
        d = db.query(models.Dealer).filter(models.Dealer.dealer_id == lead.dealer_id).first()
        if d:
            dealer = {"dealer_id": d.dealer_id, "firm_name": d.firm_name, "city": d.city}
    value = _lead_value(db, lead)
    prob = L.lead_probability(lead)
    return {
        "lead": row_dict(lead),
        "score": score, "grade": grade, "score_breakdown": parts,
        "probability": prob, "probability_source": "manual" if lead.win_probability is not None else "stage",
        "value": value, "weighted_value": round(value * prob / 100, 2),
        "sla": L.sla_state(lead),
        "architect": arch,
        "dealer": dealer,
        "dealer_acceptance_overdue": L.dealer_acceptance_overdue(lead),
        "owner_name": _employee_name(db, lead.owner_employee_id),
        "source_employee_name": _employee_name(db, lead.source_employee_id),
        "activities": [row_dict(a) for a in acts],
    }


@router.post("/rescore")
def rescore_all(db: Session = Depends(get_db)):
    leads = db.query(models.Lead).all()
    for lead in leads:
        rescore(db, lead)
    db.commit()
    dist = {}
    for lead in leads:
        dist[lead.lead_grade or "unscored"] = dist.get(lead.lead_grade or "unscored", 0) + 1
    return {"rescored": len(leads), "grades": dist}


# ═════════════════════════════════════════════════════════════════════════════
# Activity log
# ═════════════════════════════════════════════════════════════════════════════
class ActivityCreate(BaseModel):
    lead_id: Optional[int] = None
    architect_id: Optional[int] = None
    dealer_id: Optional[int] = None
    activity_type: str
    subject: Optional[str] = None
    notes: Optional[str] = None
    outcome: Optional[str] = None
    employee_id: Optional[int] = None
    performed_by: Optional[str] = None
    activity_at: Optional[datetime] = None
    next_followup_at: Optional[datetime] = None
    create_followup_task: bool = False


@router.post("/activities")
def create_activity(payload: ActivityCreate, request: Request, db: Session = Depends(get_db)):
    if not (payload.lead_id or payload.architect_id or payload.dealer_id):
        raise HTTPException(422, "Activity must be linked to a lead, architect or dealer")
    if payload.activity_type not in L.ACTIVITY_TYPES:
        raise HTTPException(422, f"Unknown activity type '{payload.activity_type}'")
    performer = payload.performed_by or _employee_name(db, payload.employee_id) or user_name(request)
    act = log_activity(
        db, lead_id=payload.lead_id, architect_id=payload.architect_id, dealer_id=payload.dealer_id,
        activity_type=payload.activity_type, subject=payload.subject, notes=payload.notes,
        outcome=payload.outcome, employee_id=payload.employee_id, performed_by=performer,
        activity_at=payload.activity_at, next_followup_at=payload.next_followup_at,
    )
    if payload.create_followup_task and payload.next_followup_at:
        emp_id = payload.employee_id
        label = None
        if payload.lead_id:
            lead = _lead_or_404(db, payload.lead_id)
            emp_id = emp_id or lead.owner_employee_id
            label = f"{lead.lead_code} · {lead.project_name}"
        if emp_id:
            db.add(models.Task(
                title=f"Follow up: {payload.subject or L.ACTIVITY_TYPES[payload.activity_type]}",
                description=payload.notes, employee_id=emp_id, assigned_by=performer,
                priority="medium", status="pending", due_date=payload.next_followup_at.replace(tzinfo=None),
                linked_lead_id=payload.lead_id, linked_label=label,
            ))
    db.commit()
    db.refresh(act)
    return row_dict(act)


@router.get("/activities")
def list_activities(lead_id: Optional[int] = None, architect_id: Optional[int] = None, dealer_id: Optional[int] = None,
                    employee_id: Optional[int] = None, activity_type: Optional[str] = None,
                    date_from: Optional[date] = None, date_to: Optional[date] = None, limit: int = 300,
                    db: Session = Depends(get_db)):
    q = db.query(models.CrmActivity)
    if lead_id: q = q.filter(models.CrmActivity.lead_id == lead_id)
    if architect_id: q = q.filter(models.CrmActivity.architect_id == architect_id)
    if dealer_id: q = q.filter(models.CrmActivity.dealer_id == dealer_id)
    if employee_id: q = q.filter(models.CrmActivity.employee_id == employee_id)
    if activity_type: q = q.filter(models.CrmActivity.activity_type == activity_type)
    if date_from: q = q.filter(models.CrmActivity.activity_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to: q = q.filter(models.CrmActivity.activity_at < datetime.combine(date_to + timedelta(days=1), datetime.min.time()))
    acts = q.order_by(models.CrmActivity.activity_at.desc()).limit(min(limit, 1000)).all()
    # attach labels
    lead_ids = {a.lead_id for a in acts if a.lead_id}
    arch_ids = {a.architect_id for a in acts if a.architect_id}
    dealer_ids = {a.dealer_id for a in acts if a.dealer_id}
    leads = {l.lead_id: l for l in db.query(models.Lead).filter(models.Lead.lead_id.in_(lead_ids)).all()} if lead_ids else {}
    archs = {a.architect_id: a.firm_name for a in db.query(models.Architect).filter(models.Architect.architect_id.in_(arch_ids)).all()} if arch_ids else {}
    dealers = {d.dealer_id: d.firm_name for d in db.query(models.Dealer).filter(models.Dealer.dealer_id.in_(dealer_ids)).all()} if dealer_ids else {}
    out = []
    for a in acts:
        d = row_dict(a)
        if a.lead_id in leads:
            d["lead_label"] = f"{leads[a.lead_id].lead_code} · {leads[a.lead_id].project_name}"
        d["architect_label"] = archs.get(a.architect_id)
        d["dealer_label"] = dealers.get(a.dealer_id)
        out.append(d)
    return out


@router.delete("/activities/{activity_id}")
def delete_activity(activity_id: int, db: Session = Depends(get_db)):
    act = db.query(models.CrmActivity).filter(models.CrmActivity.activity_id == activity_id).first()
    if not act:
        raise HTTPException(404, "Activity not found")
    db.delete(act)
    db.commit()
    return {"ok": True}


# ═════════════════════════════════════════════════════════════════════════════
# Follow-up SLA board + escalations
# ═════════════════════════════════════════════════════════════════════════════
def _sla_rows(db, owner_employee_id=None, only_overdue=False):
    q = db.query(models.Lead).filter(models.Lead.status.in_(list(L.SLA_HOURS.keys())))
    if owner_employee_id:
        q = q.filter(models.Lead.owner_employee_id == owner_employee_id)
    leads = q.all()
    emp = {e.employee_id: e.name for e in db.query(models.Employee).all()}
    dealers = {d.dealer_id: d.firm_name for d in db.query(models.Dealer).all()}
    rows = []
    for l in leads:
        s = L.sla_state(l)
        if not s or (only_overdue and not s["overdue"]):
            continue
        rows.append({
            "lead_id": l.lead_id, "lead_code": l.lead_code, "project_name": l.project_name,
            "client_name": l.client_name, "city": l.city, "status": l.status, "grade": l.lead_grade,
            "owner": emp.get(l.owner_employee_id) or l.assigned_to, "owner_employee_id": l.owner_employee_id,
            "dealer": dealers.get(l.dealer_id), "last_activity_at": jsonable(l.last_activity_at), **s,
        })
    rows.sort(key=lambda r: (-r["level"], -(r["idle_hours"] / r["limit_hours"])))
    return rows


@router.get("/followups")
def followup_board(owner_employee_id: Optional[int] = None, db: Session = Depends(get_db)):
    rows = _sla_rows(db, owner_employee_id)
    today = date.today()
    arch_due = (db.query(models.Architect)
                .filter(models.Architect.is_active == True, models.Architect.next_followup_date != None,
                        models.Architect.next_followup_date <= today + timedelta(days=7))
                .order_by(models.Architect.next_followup_date).all())
    pending_dealer = db.query(models.Lead).filter(models.Lead.dealer_acceptance.in_(["pending", "rejected"])).all()
    dealers = {d.dealer_id: d.firm_name for d in db.query(models.Dealer).all()}
    return {
        "summary": {
            "tracked": len(rows),
            "overdue": sum(1 for r in rows if r["overdue"]),
            "by_level": {lvl: sum(1 for r in rows if r["level"] == i + 1) for i, lvl in enumerate(L.ESCALATION_LADDER)},
        },
        "leads": rows,
        "architects_due": [{
            "architect_id": a.architect_id, "firm_name": a.firm_name, "ranking": a.ranking,
            "next_followup_date": jsonable(a.next_followup_date), "overdue": a.next_followup_date < today,
            "owner": _employee_name(db, a.relationship_owner_id),
        } for a in arch_due],
        "dealer_acceptance": [{
            "lead_id": l.lead_id, "lead_code": l.lead_code, "project_name": l.project_name,
            "dealer": dealers.get(l.dealer_id), "assigned_at": jsonable(l.dealer_assigned_at),
            "acceptance": l.dealer_acceptance, "reject_reason": l.dealer_reject_reason,
            "overdue": L.dealer_acceptance_overdue(l),
        } for l in pending_dealer],
    }


@router.post("/sla/run")
def run_sla_escalations(db: Session = Depends(get_db)):
    """Create today's follow-up tasks for every overdue lead (deduped per day).
    Level 1 → lead owner (or the CRM follow-up role); level 2+ also notifies the escalation role holder."""
    from app.routers.tasks import auto_task, get_emp_by_role, ROLE_CRM_FOLLOWUP
    crm_emp = get_emp_by_role(db, ROLE_CRM_FOLLOWUP)
    created = 0
    for r in _sla_rows(db, only_overdue=True):
        target = r["owner_employee_id"] or (crm_emp.employee_id if crm_emp else None)
        if not target:
            continue
        prio = "high" if r["level"] >= 2 else "medium"
        title = f"[SLA] {r['lead_code']} idle {int(r['idle_days'])}d — {r['status'].replace('_', ' ')}"
        desc = f"No activity for {r['idle_days']} days (limit {r['limit_hours'] // 24 or 1}d). Escalation: {r['escalate_to']}. Log a call/meeting to clear."
        if auto_task(db, title, desc, target, prio, r["lead_id"], f"{r['lead_code']} · {r['project_name']}"):
            created += 1
        if r["level"] >= 2 and crm_emp and crm_emp.employee_id != target:
            if auto_task(db, f"[Escalation L{r['level']}] {r['lead_code']}", desc, crm_emp.employee_id, "high", r["lead_id"], r["project_name"]):
                created += 1
    for l in db.query(models.Lead).filter(models.Lead.dealer_acceptance == "pending").all():
        if L.dealer_acceptance_overdue(l) and crm_emp:
            if auto_task(db, f"[Dealer SLA] {l.lead_code} not accepted in 24h", "Dealer hasn't accepted the assigned lead. Call the dealer or reassign.", crm_emp.employee_id, "high", l.lead_id, l.project_name):
                created += 1
    db.commit()
    return {"tasks_created": created}


# ═════════════════════════════════════════════════════════════════════════════
# Duplicate detection
# ═════════════════════════════════════════════════════════════════════════════
def _digits(s):
    d = re.sub(r"\D", "", s or "")
    return d[-10:] if len(d) >= 10 else d


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def find_duplicates(db, phone=None, client_name=None, project_name=None, city=None, exclude_lead_id=None, architect_id=None):
    from difflib import SequenceMatcher
    q = db.query(models.Lead)
    if exclude_lead_id:
        q = q.filter(models.Lead.lead_id != exclude_lead_id)
    pd = _digits(phone)
    hits = {}
    if pd and len(pd) >= 10:
        for l in q.filter(models.Lead.client_phone != None).all():
            if _digits(l.client_phone) == pd:
                hits[l.lead_id] = (l, "Same client phone")
    if client_name or project_name:
        cand = q
        if city:
            cand = cand.filter(func.lower(models.Lead.city) == city.strip().lower())
        cn, pn = _norm(client_name), _norm(project_name)
        for l in cand.all():
            if l.lead_id in hits:
                continue
            sims = []
            if cn and l.client_name: sims.append(SequenceMatcher(None, cn, _norm(l.client_name)).ratio())
            if pn and l.project_name: sims.append(SequenceMatcher(None, pn, _norm(l.project_name)).ratio())
            if sims and max(sims) >= 0.82:
                reason = "Similar name" + (f" in {l.city}" if city else "")
                if architect_id and l.architect_id == architect_id:
                    reason += ", same architect"
                hits[l.lead_id] = (l, reason)
    dealers = {d.dealer_id: d.firm_name for d in db.query(models.Dealer).all()}
    return [{
        "lead_id": l.lead_id, "lead_code": l.lead_code, "project_name": l.project_name,
        "client_name": l.client_name, "city": l.city, "status": l.status,
        "dealer": dealers.get(l.dealer_id), "reason": reason,
        "locked": bool(l.lock_expires_at and L._aware(l.lock_expires_at) > L.now_utc()),
    } for l, reason in hits.values()]


@router.get("/duplicates")
def check_duplicates(phone: Optional[str] = None, client_name: Optional[str] = None, project_name: Optional[str] = None,
                     city: Optional[str] = None, exclude_lead_id: Optional[int] = None, db: Session = Depends(get_db)):
    return find_duplicates(db, phone, client_name, project_name, city, exclude_lead_id)


# ═════════════════════════════════════════════════════════════════════════════
# Dealer assignment engine
# ═════════════════════════════════════════════════════════════════════════════
def _dealer_open_loads(db):
    rows = (db.query(models.Lead.dealer_id, func.count(models.Lead.lead_id))
            .filter(models.Lead.dealer_id != None, models.Lead.status.in_(L.OPEN_STATUSES))
            .group_by(models.Lead.dealer_id).all())
    return dict(rows)


@router.get("/leads/{lead_id}/dealer-suggestions")
def dealer_suggestions(lead_id: int, db: Session = Depends(get_db)):
    lead = _lead_or_404(db, lead_id)
    dealers = db.query(models.Dealer).filter(or_(models.Dealer.is_active == True, models.Dealer.is_active == None)).all()
    loads = _dealer_open_loads(db)
    max_load = max(loads.values()) if loads else 0
    city = (lead.city or "").strip().lower()
    state = (lead.state or "").strip().lower()
    interest = set(lead.product_interest or ([lead.category] if lead.category in L.PRODUCT_CATEGORIES else []))
    arch_dealers = set()
    if lead.architect_id:
        arch_dealers = {r[0] for r in db.query(models.Lead.dealer_id).filter(models.Lead.architect_id == lead.architect_id, models.Lead.dealer_id != None).all()}
    out = []
    for d in dealers:
        if (d.lifecycle_stage or "active") in ("prospect", "inactive"):
            continue
        reasons, score = [], 0
        terr = [c.strip().lower() for c in (d.territory_cities or [])]
        if city and (city == (d.city or "").strip().lower() or city in terr):
            score += 40; reasons.append("Covers the city")
        elif state and (state == (d.state or "").strip().lower() or state in [s.lower() for s in (d.portal_states or [])]):
            score += 25; reasons.append("Same state")
        certs = set(d.certified_categories or [])
        if interest:
            covered = interest & certs
            if covered == interest:
                score += 25; reasons.append("Certified for all categories")
            elif covered:
                score += 12; reasons.append(f"Certified for {', '.join(sorted(covered))}")
        caps = set(d.capabilities or [])
        if {"installation", "commissioning"} <= caps:
            score += 10; reasons.append("Can install & commission")
        load = loads.get(d.dealer_id, 0)
        if max_load:
            score += round(15 * (1 - load / max_load))
        else:
            score += 15
        reasons.append(f"{load} open leads")
        if d.dealer_id in arch_dealers:
            score += 10; reasons.append("Worked with this architect")
        out.append({"dealer_id": d.dealer_id, "firm_name": d.firm_name, "city": d.city, "classification": d.classification,
                    "score": score, "reasons": reasons})
    out.sort(key=lambda x: -x["score"])
    return out[:8]


class AssignDealer(BaseModel):
    dealer_id: Optional[int] = None
    reason: Optional[str] = None


@router.post("/leads/{lead_id}/assign-dealer")
def assign_dealer(lead_id: int, payload: AssignDealer, request: Request, db: Session = Depends(get_db)):
    lead = _lead_or_404(db, lead_id)
    who = user_name(request)
    if payload.dealer_id is None:
        lead.dealer_id = None
        lead.dealer_acceptance = None
        log_activity(db, lead_id=lead_id, activity_type="system", subject="Dealer unassigned", notes=payload.reason, performed_by=who, touch=False)
    else:
        d = db.query(models.Dealer).filter(models.Dealer.dealer_id == payload.dealer_id).first()
        if not d:
            raise HTTPException(404, "Dealer not found")
        lead.dealer_id = d.dealer_id
        lead.dealer_assigned_at = L.now_utc()
        lead.dealer_assigned_by = who
        lead.dealer_assignment_reason = payload.reason
        lead.dealer_acceptance = "pending"
        lead.dealer_responded_at = None
        lead.dealer_reject_reason = None
        if lead.channel == "direct":
            lead.channel = "dealer"
        log_activity(db, lead_id=lead_id, dealer_id=d.dealer_id, activity_type="system",
                     subject=f"Assigned to {d.firm_name} — awaiting acceptance (24h)", notes=payload.reason, performed_by=who, touch=False)
    db.commit()
    return lead_insights(lead_id, db)


# ═════════════════════════════════════════════════════════════════════════════
# Dealer scorecard
# ═════════════════════════════════════════════════════════════════════════════
def dealer_scorecards(db, months=12):
    since = L.now_utc() - timedelta(days=30 * months)
    dealers = db.query(models.Dealer).all()
    leads = db.query(models.Lead).filter(models.Lead.dealer_id != None).all()
    by_dealer = {}
    for l in leads:
        by_dealer.setdefault(l.dealer_id, []).append(l)
    # revenue = MIPL invoices on the dealer's leads in the window
    rev_rows = (db.query(models.Lead.dealer_id, func.coalesce(func.sum(models.Invoice.invoice_amount), 0))
                .join(models.Invoice, models.Invoice.lead_id == models.Lead.lead_id)
                .filter(models.Lead.dealer_id != None, models.Invoice.created_at >= since,
                        or_(models.Invoice.invoice_from == "MIPL", models.Invoice.invoice_from == None))
                .group_by(models.Lead.dealer_id).all())
    revenue = {k: float(v or 0) for k, v in rev_rows}
    top_rev = max(revenue.values()) if revenue else 0
    tickets = db.query(models.ServiceTicket).filter(models.ServiceTicket.dealer_id != None).all()
    t_by_dealer = {}
    for t in tickets:
        t_by_dealer.setdefault(t.dealer_id, []).append(t)
    claims = {}
    for t in tickets:
        if t.ticket_type == "warranty_claim":
            claims[t.dealer_id] = claims.get(t.dealer_id, 0) + 1
    out = []
    for d in dealers:
        ls = by_dealer.get(d.dealer_id, [])
        won = sum(1 for l in ls if l.status == "won")
        lost = sum(1 for l in ls if l.status in ("lost", "cold"))
        assigned = [l for l in ls if l.dealer_assigned_at]
        accepted = [l for l in assigned if l.dealer_acceptance == "accepted"]
        rejected = [l for l in assigned if l.dealer_acceptance == "rejected"]
        on_time = [l for l in accepted if l.dealer_responded_at and (L._aware(l.dealer_responded_at) - L._aware(l.dealer_assigned_at)) <= timedelta(hours=L.DEALER_ACCEPT_HOURS)]
        open_ls = [l for l in ls if l.status in L.SLA_HOURS]
        within_sla = [l for l in open_ls if not (L.sla_state(l) or {}).get("overdue")]
        rev = revenue.get(d.dealer_id, 0.0)
        comp_rev = (rev / top_rev * 100) if top_rev else L.NEUTRAL_SCORE
        comp_conv = (won / (won + lost) * 100) if (won + lost) else L.NEUTRAL_SCORE
        parts_c = []
        if assigned: parts_c.append(len(on_time) / len(assigned) * 100)
        if open_ls: parts_c.append(len(within_sla) / len(open_ls) * 100)
        comp_compliance = sum(parts_c) / len(parts_c) if parts_c else L.NEUTRAL_SCORE
        comp_training = d.training_score if d.training_score is not None else L.NEUTRAL_SCORE
        comp_install = d.installation_score if d.installation_score is not None else L.NEUTRAL_SCORE
        tk = t_by_dealer.get(d.dealer_id, [])
        closed = [t for t in tk if t.resolved_at]
        if closed:
            ok = [t for t in closed if t.sla_due_at and L._aware(t.resolved_at) <= L._aware(t.sla_due_at)]
            comp_service = len(ok) / len(closed) * 100
        else:
            comp_service = d.service_score if d.service_score is not None else L.NEUTRAL_SCORE
        comps = {"revenue": comp_rev, "conversion": comp_conv, "compliance": comp_compliance,
                 "training": comp_training, "installation": comp_install, "service": comp_service}
        total = sum(comps[k] * w / 100 for k, w in L.SCORECARD_WEIGHTS.items())
        out.append({
            "dealer_id": d.dealer_id, "firm_name": d.firm_name, "city": d.city, "region": d.region,
            "classification": d.classification, "lifecycle_stage": d.lifecycle_stage,
            "leads_received": len(ls), "leads_accepted": len(accepted), "leads_rejected": len(rejected),
            "pending_acceptance": sum(1 for l in ls if l.dealer_acceptance == "pending"),
            "projects_registered": sum(1 for l in ls if l.locked_by_dealer_id == d.dealer_id),
            "orders_closed": won, "revenue_12m": rev, "warranty_claims": claims.get(d.dealer_id, 0),
            "open_tickets": sum(1 for t in tk if t.status not in ("resolved", "closed")),
            "components": {k: round(v, 1) for k, v in comps.items()},
            "score": round(total, 1), "tier": L.dealer_tier(total),
            "agreement_end": jsonable(d.agreement_end),
        })
    out.sort(key=lambda x: -x["score"])
    return out


@router.get("/dealers/scorecard")
def get_dealer_scorecard(months: int = 12, db: Session = Depends(get_db)):
    return dealer_scorecards(db, months)


# ═════════════════════════════════════════════════════════════════════════════
# Forecast (probability-weighted pipeline)
# ═════════════════════════════════════════════════════════════════════════════
@router.get("/forecast")
def forecast(db: Session = Depends(get_db)):
    leads = db.query(models.Lead).filter(models.Lead.status.in_(L.OPEN_STATUSES)).all()
    boq_totals = dict(db.query(models.Boq.lead_id, func.coalesce(func.sum(models.Boq.total_amount), 0))
                      .group_by(models.Boq.lead_id).all())
    by_status, by_month, rows = {}, {}, []
    for l in leads:
        value = float(l.estimated_value or boq_totals.get(l.lead_id) or 0)
        p = L.lead_probability(l)
        w = value * p / 100
        bs = by_status.setdefault(l.status, {"status": l.status, "count": 0, "value": 0.0, "weighted": 0.0, "probability": L.STATUS_PROBABILITY.get(l.status)})
        bs["count"] += 1; bs["value"] += value; bs["weighted"] += w
        month = l.expected_order_date.strftime("%Y-%m") if l.expected_order_date else "unscheduled"
        bm = by_month.setdefault(month, {"month": month, "count": 0, "value": 0.0, "weighted": 0.0})
        bm["count"] += 1; bm["value"] += value; bm["weighted"] += w
        rows.append({"lead_id": l.lead_id, "lead_code": l.lead_code, "project_name": l.project_name, "status": l.status,
                     "grade": l.lead_grade, "value": value, "probability": p, "weighted": round(w, 2),
                     "expected_order_date": jsonable(l.expected_order_date)})
    rows.sort(key=lambda r: -r["weighted"])
    order = {s: i for i, s in enumerate(L.OPEN_STATUSES)}
    return {
        "total_pipeline": round(sum(r["value"] for r in rows), 2),
        "weighted_pipeline": round(sum(r["weighted"] for r in rows), 2),
        "by_status": sorted(by_status.values(), key=lambda x: order.get(x["status"], 99)),
        "by_month": sorted(by_month.values(), key=lambda x: (x["month"] == "unscheduled", x["month"])),
        "leads": rows,
        "missing_value": sum(1 for r in rows if not r["value"]),
        "missing_date": sum(1 for r in rows if not r["expected_order_date"]),
    }


# ═════════════════════════════════════════════════════════════════════════════
# Discount approval matrix (BOQ / quotation)
# ═════════════════════════════════════════════════════════════════════════════
def _reference_price(product, lead, dealer):
    """List price the quote is measured against: MRP for direct/flagship clients,
    dealer cost for dealer-channel quotes (so a normal dealer price isn't flagged as a 50% discount)."""
    mrp = float(product.mrp_gst or product.mrp_inr or product.unit_price or 0)
    if lead and lead.channel in ("dealer", "flagship_dealer"):
        if product.dealer_cost:
            return float(product.dealer_cost)
        disc = float(dealer.special_discount_pct) if (dealer and dealer.special_discount_pct is not None) else 50.0
        return mrp * (1 - disc / 100)
    return mrp


def evaluate_boq_discount(db, boq):
    """Effective discount = value-weighted gap between quoted net price and list price,
    across every line whose SKU is in the catalogue (also honours per-line discount_pct)."""
    items = db.query(models.BoqLineItem).filter(models.BoqLineItem.boq_id == boq.boq_id).all()
    lead = db.query(models.Lead).filter(models.Lead.lead_id == boq.lead_id).first()
    dealer = db.query(models.Dealer).filter(models.Dealer.dealer_id == lead.dealer_id).first() if (lead and lead.dealer_id) else None
    skus = {i.product_sku for i in items if i.product_sku}
    products = {p.sku: p for p in db.query(models.Product).filter(models.Product.sku.in_(skus)).all()} if skus else {}
    list_total = net_total = 0.0
    max_line = 0.0
    unpriced = 0
    for i in items:
        qty = float(i.quantity or 0)
        net_unit = float(i.unit_price or 0) * (1 - float(i.discount_pct or 0) / 100)
        p = products.get(i.product_sku)
        ref = _reference_price(p, lead, dealer) if p else 0
        if ref <= 0 or qty <= 0:
            unpriced += 1
            if float(i.discount_pct or 0) > max_line:
                max_line = float(i.discount_pct or 0)
            continue
        list_total += ref * qty
        net_total += net_unit * qty
        max_line = max(max_line, (1 - net_unit / ref) * 100)
    overall = max(0.0, (1 - net_total / list_total) * 100) if list_total else max_line
    overall = round(overall, 2)
    level = L.approval_level_for(overall)
    boq.max_discount_pct = overall
    rank = {"auto": 0, "regional_manager": 1, "national_head": 2, "ceo": 3}
    if level == "auto":
        boq.approval_level, boq.approval_status = "auto", "not_required"
    else:
        prev_level, prev_status = boq.approval_level, boq.approval_status
        escalated = rank.get(level, 3) > rank.get(prev_level or "auto", 0)
        if prev_status in (None, "not_required") or escalated:
            # first time over the limit, or discount raised past what was approved/requested
            boq.approval_status = "required"
        boq.approval_level = level if (escalated or prev_status in (None, "not_required", "required")) else prev_level
    return {"boq_id": boq.boq_id, "max_discount_pct": overall, "max_line_discount_pct": round(max_line, 2),
            "lines_without_list_price": unpriced, "list_value": round(list_total, 2), "approval_level": boq.approval_level,
            "approval_label": L.APPROVAL_LABELS.get(boq.approval_level), "approval_status": boq.approval_status}


def boq_send_blocker(db, boq):
    """Return an error message if this BOQ may not be sent yet, else None."""
    ev = evaluate_boq_discount(db, boq)
    if ev["approval_level"] != "auto" and boq.approval_status != "approved":
        return (f"Discount of {ev['max_discount_pct']:.1f}% off list needs {ev['approval_label']} approval before this quote can be sent. "
                f"Request approval from the BOQ page.")
    return None


@router.get("/boqs/{boq_id}/approval")
def boq_approval_state(boq_id: int, db: Session = Depends(get_db)):
    boq = db.query(models.Boq).filter(models.Boq.boq_id == boq_id).first()
    if not boq:
        raise HTTPException(404, "BOQ not found")
    ev = evaluate_boq_discount(db, boq)
    db.commit()
    return {**ev, **{k: jsonable(getattr(boq, k)) for k in ("approval_requested_at", "approval_requested_by", "approval_decided_at", "approval_decided_by", "approval_notes")}}


class ApprovalRequest(BaseModel):
    notes: Optional[str] = None


@router.post("/boqs/{boq_id}/request-approval")
def request_boq_approval(boq_id: int, payload: ApprovalRequest, request: Request, db: Session = Depends(get_db)):
    boq = db.query(models.Boq).filter(models.Boq.boq_id == boq_id).first()
    if not boq:
        raise HTTPException(404, "BOQ not found")
    ev = evaluate_boq_discount(db, boq)
    if ev["approval_level"] == "auto":
        db.commit()
        return {**ev, "message": "Within auto-approval limit — no approval needed."}
    boq.approval_status = "pending"
    boq.approval_requested_at = L.now_utc()
    boq.approval_requested_by = user_name(request)
    boq.approval_notes = payload.notes
    log_activity(db, lead_id=boq.lead_id, activity_type="system",
                 subject=f"Discount approval requested on {boq.boq_code} ({ev['max_discount_pct']:.1f}% → {ev['approval_label']})",
                 notes=payload.notes, performed_by=boq.approval_requested_by, touch=False)
    db.commit()
    return boq_approval_state(boq_id, db)


class ApprovalDecision(BaseModel):
    decision: str  # approved / rejected
    notes: Optional[str] = None


@router.post("/boqs/{boq_id}/decide")
def decide_boq_approval(boq_id: int, payload: ApprovalDecision, request: Request, db: Session = Depends(get_db)):
    if not is_approver(request):
        raise HTTPException(403, "Only approvers can approve discounts")
    if payload.decision not in ("approved", "rejected"):
        raise HTTPException(422, "decision must be 'approved' or 'rejected'")
    boq = db.query(models.Boq).filter(models.Boq.boq_id == boq_id).first()
    if not boq:
        raise HTTPException(404, "BOQ not found")
    evaluate_boq_discount(db, boq)
    boq.approval_status = payload.decision
    boq.approval_decided_at = L.now_utc()
    boq.approval_decided_by = user_name(request)
    if payload.notes:
        boq.approval_notes = ((boq.approval_notes + "\n") if boq.approval_notes else "") + f"[{payload.decision}] {payload.notes}"
    log_activity(db, lead_id=boq.lead_id, activity_type="system",
                 subject=f"Discount {payload.decision} on {boq.boq_code} by {boq.approval_decided_by}",
                 notes=payload.notes, performed_by=boq.approval_decided_by, touch=False)
    db.commit()
    return boq_approval_state(boq_id, db)


@router.get("/approvals")
def list_approvals(status: str = "pending", db: Session = Depends(get_db)):
    q = db.query(models.Boq)
    if status != "all":
        q = q.filter(models.Boq.approval_status == status)
    else:
        q = q.filter(models.Boq.approval_status.in_(["pending", "approved", "rejected", "required"]))
    boqs = q.order_by(models.Boq.approval_requested_at.desc().nullslast()).limit(200).all()
    leads = {l.lead_id: l for l in db.query(models.Lead).filter(models.Lead.lead_id.in_({b.lead_id for b in boqs})).all()} if boqs else {}
    return [{
        "boq_id": b.boq_id, "boq_code": b.boq_code, "category": b.category, "total_amount": jsonable(b.total_amount),
        "lead_id": b.lead_id, "lead_code": getattr(leads.get(b.lead_id), "lead_code", None),
        "project_name": getattr(leads.get(b.lead_id), "project_name", None),
        "max_discount_pct": jsonable(b.max_discount_pct), "approval_level": b.approval_level,
        "approval_label": L.APPROVAL_LABELS.get(b.approval_level), "approval_status": b.approval_status,
        "requested_by": b.approval_requested_by, "requested_at": jsonable(b.approval_requested_at),
        "decided_by": b.approval_decided_by, "decided_at": jsonable(b.approval_decided_at), "notes": b.approval_notes,
    } for b in boqs]
