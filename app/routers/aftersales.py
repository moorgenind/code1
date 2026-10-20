"""
After-sales — technical request turnaround, installations, service tickets,
warranty registry and AMC contracts. Mounted at /aftersales.
"""
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app import crm_logic as L
from app.crm_common import row_dict, jsonable, next_code, log_activity, user_name

router = APIRouter()


def _add_months(d, months):
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    from calendar import monthrange
    return date(y, m, min(d.day, monthrange(y, m)[1]))


def _lead_labels(db, ids):
    ids = {i for i in ids if i}
    if not ids:
        return {}
    return {l.lead_id: l for l in db.query(models.Lead).filter(models.Lead.lead_id.in_(ids)).all()}


# ═════════════════════════════════════════════════════════════════════════════
# Technical requests (design requests) — turnaround tracking
# ═════════════════════════════════════════════════════════════════════════════
@router.get("/tech-requests")
def tech_requests(status: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(models.DesignRequest)
    if status == "open":
        q = q.filter(models.DesignRequest.status.in_(["pending", "in_progress"]))
    elif status:
        q = q.filter(models.DesignRequest.status == status)
    reqs = q.order_by(models.DesignRequest.created_at.desc()).limit(500).all()
    leads = _lead_labels(db, [r.lead_id for r in reqs])
    now = L.now_utc()
    rows, tats = [], []
    for r in reqs:
        created = L._aware(r.created_at)
        target = L._aware(r.target_date) or (created + timedelta(days=L.TECH_REQUEST_DEFAULT_DAYS.get(r.request_type, 5)) if created else None)
        done = L._aware(r.completed_at)
        tat_days = round((done - created).total_seconds() / 86400, 1) if (done and created) else None
        if tat_days is not None:
            tats.append(tat_days)
        open_ = r.status in ("pending", "in_progress")
        overdue = bool(open_ and target and now > target)
        late = bool(done and target and done > target)
        lead = leads.get(r.lead_id)
        rows.append({
            **row_dict(r), "lead_code": getattr(lead, "lead_code", None), "project_name": getattr(lead, "project_name", None),
            "effective_target": jsonable(target), "tat_days": tat_days, "age_days": round((now - created).total_seconds() / 86400, 1) if created else None,
            "overdue": overdue, "completed_late": late,
        })
    completed = [r for r in rows if r["tat_days"] is not None]
    return {
        "summary": {
            "open": sum(1 for r in rows if r["status"] in ("pending", "in_progress")),
            "overdue": sum(1 for r in rows if r["overdue"]),
            "avg_tat_days": round(sum(tats) / len(tats), 1) if tats else None,
            "on_time_pct": round(sum(1 for r in completed if not r["completed_late"]) / len(completed) * 100) if completed else None,
            "revisions": sum(r.get("revision_count") or 0 for r in rows),
        },
        "requests": rows,
    }


class TechRequestPatch(BaseModel):
    target_date: Optional[datetime] = None
    requested_by: Optional[str] = None
    assigned_to: Optional[str] = None


@router.patch("/tech-requests/{design_request_id}")
def patch_tech_request(design_request_id: int, payload: TechRequestPatch, db: Session = Depends(get_db)):
    r = db.query(models.DesignRequest).filter(models.DesignRequest.design_request_id == design_request_id).first()
    if not r:
        raise HTTPException(404, "Request not found")
    for k, v in payload.dict(exclude_unset=True).items():
        setattr(r, k, v)
    db.commit()
    return row_dict(r)


# ═════════════════════════════════════════════════════════════════════════════
# Installations — delivery → installation → testing → commissioning → handover → training → sign-off
# ═════════════════════════════════════════════════════════════════════════════
INSTALL_STEPS = [
    ("material_delivery_date", "Delivery"), ("installation_date", "Installation"), ("testing_date", "Testing"),
    ("commissioning_date", "Commissioning"), ("handover_date", "Handover"), ("client_training_date", "Training"),
    ("signoff_date", "Sign-off"),
]


@router.get("/installations")
def installations(db: Session = Depends(get_db)):
    leads = db.query(models.Lead).filter(models.Lead.status == "won").order_by(models.Lead.updated_at.desc()).all()
    tracking = {t.lead_id: t for t in db.query(models.ProjectTracking).filter(models.ProjectTracking.lead_id.in_([l.lead_id for l in leads] or [0])).all()}
    warranty_leads = {r[0] for r in db.query(models.WarrantyRecord.lead_id).distinct().all()}
    dealers = {d.dealer_id: d.firm_name for d in db.query(models.Dealer).all()}
    out = []
    for l in leads:
        t = tracking.get(l.lead_id)
        steps = [{"key": k, "label": lbl, "date": jsonable(getattr(t, k, None)) if t else None} for k, lbl in INSTALL_STEPS]
        done = sum(1 for s in steps if s["date"])
        out.append({
            "lead_id": l.lead_id, "lead_code": l.lead_code, "project_name": l.project_name, "client_name": l.client_name,
            "city": l.city, "dealer": dealers.get(l.dealer_id), "current_stage": getattr(t, "current_stage", None),
            "steps": steps, "progress_pct": round(done / len(steps) * 100), "signed_off_by": getattr(t, "signed_off_by", None),
            "signoff_doc_url": getattr(t, "signoff_doc_url", None), "warranty_registered": l.lead_id in warranty_leads,
        })
    return out


# ═════════════════════════════════════════════════════════════════════════════
# Warranty registry
# ═════════════════════════════════════════════════════════════════════════════
class WarrantyIn(BaseModel):
    lead_id: int
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[int] = 1
    serial_numbers: Optional[str] = None
    install_date: Optional[date] = None
    warranty_months: Optional[int] = 24
    notes: Optional[str] = None


def _warranty_row(w, today=None):
    today = today or date.today()
    d = row_dict(w)
    d["active"] = bool(w.warranty_end and w.warranty_end >= today)
    d["days_left"] = (w.warranty_end - today).days if w.warranty_end else None
    return d


@router.get("/warranty")
def list_warranty(lead_id: Optional[int] = None, q: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.WarrantyRecord)
    if lead_id:
        query = query.filter(models.WarrantyRecord.lead_id == lead_id)
    if q:
        like = f"%{q}%"
        query = query.filter((models.WarrantyRecord.product_sku.ilike(like)) | (models.WarrantyRecord.product_name.ilike(like)) | (models.WarrantyRecord.serial_numbers.ilike(like)))
    rows = query.order_by(models.WarrantyRecord.warranty_end.desc().nullslast()).limit(1000).all()
    leads = _lead_labels(db, [r.lead_id for r in rows])
    out = []
    for r in rows:
        d = _warranty_row(r)
        lead = leads.get(r.lead_id)
        d["lead_code"] = getattr(lead, "lead_code", None)
        d["project_name"] = getattr(lead, "project_name", None)
        d["client_name"] = getattr(lead, "client_name", None)
        out.append(d)
    return out


@router.post("/warranty")
def add_warranty(payload: WarrantyIn, db: Session = Depends(get_db)):
    lead = db.query(models.Lead).filter(models.Lead.lead_id == payload.lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")
    w = models.WarrantyRecord(**payload.dict(), dealer_id=lead.dealer_id)
    if w.install_date and w.warranty_months:
        w.warranty_end = _add_months(w.install_date, w.warranty_months)
    db.add(w)
    db.commit()
    db.refresh(w)
    return _warranty_row(w)


class WarrantyFromLead(BaseModel):
    install_date: Optional[date] = None
    warranty_months: int = 24
    automation_warranty_months: Optional[int] = None


@router.post("/warranty/from-lead/{lead_id}")
def warranty_from_lead(lead_id: int, payload: WarrantyFromLead, db: Session = Depends(get_db)):
    """Register every product on the lead's latest BOQs (one per category) as installed base."""
    lead = db.query(models.Lead).filter(models.Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")
    if db.query(models.WarrantyRecord).filter(models.WarrantyRecord.lead_id == lead_id).first():
        raise HTTPException(409, "Warranty already registered for this project — edit the existing records")
    t = db.query(models.ProjectTracking).filter(models.ProjectTracking.lead_id == lead_id).first()
    install = payload.install_date or (t and (t.handover_date or t.installation_date) and (t.handover_date or t.installation_date).date()) or date.today()
    boqs = db.query(models.Boq).filter(models.Boq.lead_id == lead_id).order_by(models.Boq.version.desc()).all()
    latest = {}
    for b in boqs:
        latest.setdefault(b.category, b)
    agg = {}
    for b in latest.values():
        for li in db.query(models.BoqLineItem).filter(models.BoqLineItem.boq_id == b.boq_id).all():
            key = li.product_sku or li.product_name
            if not key:
                continue
            a = agg.setdefault(key, {"sku": li.product_sku, "name": li.product_name, "category": b.category, "qty": 0})
            a["qty"] += int(li.quantity or 0)
    created = 0
    for a in agg.values():
        months = payload.automation_warranty_months if (a["category"] == "automation" and payload.automation_warranty_months) else payload.warranty_months
        db.add(models.WarrantyRecord(
            lead_id=lead_id, dealer_id=lead.dealer_id, product_sku=a["sku"], product_name=a["name"], category=a["category"],
            quantity=a["qty"] or 1, install_date=install, warranty_months=months, warranty_end=_add_months(install, months),
        ))
        created += 1
    db.commit()
    return {"registered": created, "install_date": install.isoformat()}


@router.patch("/warranty/{warranty_id}")
def update_warranty(warranty_id: int, payload: dict, db: Session = Depends(get_db)):
    w = db.query(models.WarrantyRecord).filter(models.WarrantyRecord.warranty_id == warranty_id).first()
    if not w:
        raise HTTPException(404, "Record not found")
    for k in ("product_sku", "product_name", "quantity", "serial_numbers", "install_date", "warranty_months", "notes"):
        if k in payload:
            setattr(w, k, payload[k] or None)
    if w.install_date and w.warranty_months:
        inst = w.install_date if isinstance(w.install_date, date) else date.fromisoformat(str(w.install_date))
        w.install_date = inst
        w.warranty_end = _add_months(inst, int(w.warranty_months))
    db.commit()
    return _warranty_row(w)


@router.delete("/warranty/{warranty_id}")
def delete_warranty(warranty_id: int, db: Session = Depends(get_db)):
    w = db.query(models.WarrantyRecord).filter(models.WarrantyRecord.warranty_id == warranty_id).first()
    if not w:
        raise HTTPException(404, "Record not found")
    db.delete(w)
    db.commit()
    return {"ok": True}


# ═════════════════════════════════════════════════════════════════════════════
# Service tickets (complaints, warranty claims, service & AMC visits)
# ═════════════════════════════════════════════════════════════════════════════
class TicketIn(BaseModel):
    lead_id: Optional[int] = None
    dealer_id: Optional[int] = None
    amc_id: Optional[int] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    ticket_type: Optional[str] = None
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    issue: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    resolution: Optional[str] = None
    cost: Optional[float] = None


def _ticket_row(t, leads=None, dealers=None, now=None):
    now = now or L.now_utc()
    d = row_dict(t)
    open_ = t.status not in ("resolved", "closed")
    due = L._aware(t.sla_due_at)
    d["sla_breached"] = bool(due and ((open_ and now > due) or (t.resolved_at and L._aware(t.resolved_at) > due)))
    d["hours_to_due"] = round((due - now).total_seconds() / 3600, 1) if (due and open_) else None
    if leads is not None:
        lead = leads.get(t.lead_id)
        d["lead_code"] = getattr(lead, "lead_code", None)
        d["project_name"] = getattr(lead, "project_name", None)
    if dealers is not None:
        d["dealer_name"] = dealers.get(t.dealer_id)
    return d


@router.get("/tickets")
def list_tickets(status: Optional[str] = None, ticket_type: Optional[str] = None, lead_id: Optional[int] = None,
                 dealer_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(models.ServiceTicket)
    if status == "open":
        q = q.filter(models.ServiceTicket.status.notin_(["resolved", "closed"]))
    elif status:
        q = q.filter(models.ServiceTicket.status == status)
    if ticket_type: q = q.filter(models.ServiceTicket.ticket_type == ticket_type)
    if lead_id: q = q.filter(models.ServiceTicket.lead_id == lead_id)
    if dealer_id: q = q.filter(models.ServiceTicket.dealer_id == dealer_id)
    tickets = q.order_by(models.ServiceTicket.created_at.desc()).limit(500).all()
    leads = _lead_labels(db, [t.lead_id for t in tickets])
    dealers = {d.dealer_id: d.firm_name for d in db.query(models.Dealer).all()}
    rows = [_ticket_row(t, leads, dealers) for t in tickets]
    resolved = [t for t in tickets if t.resolved_at and t.created_at]
    return {
        "summary": {
            "open": sum(1 for r in rows if r["status"] not in ("resolved", "closed")),
            "breached": sum(1 for r in rows if r["sla_breached"] and r["status"] not in ("resolved", "closed")),
            "warranty_claims_open": sum(1 for r in rows if r["ticket_type"] == "warranty_claim" and r["status"] not in ("resolved", "closed")),
            "avg_resolution_hours": round(sum((L._aware(t.resolved_at) - L._aware(t.created_at)).total_seconds() for t in resolved) / len(resolved) / 3600, 1) if resolved else None,
        },
        "tickets": rows,
    }


@router.post("/tickets")
def create_ticket(payload: TicketIn, request: Request, db: Session = Depends(get_db)):
    data = payload.dict(exclude_unset=True)
    t = models.ServiceTicket(**{k: v for k, v in data.items() if v not in (None, "")})
    t.ticket_code = next_code(db, models.ServiceTicket, "ticket_code", "SRV")
    t.ticket_type = t.ticket_type or "complaint"
    t.priority = t.priority if t.priority in L.SERVICE_SLA_HOURS else "P2"
    t.status = t.status or "open"
    t.sla_due_at = L.now_utc() + timedelta(hours=L.SERVICE_SLA_HOURS[t.priority])
    if t.lead_id:
        lead = db.query(models.Lead).filter(models.Lead.lead_id == t.lead_id).first()
        if lead:
            t.dealer_id = t.dealer_id or lead.dealer_id
            t.customer_name = t.customer_name or lead.client_name
            t.customer_phone = t.customer_phone or lead.client_phone
        wq = db.query(models.WarrantyRecord).filter(models.WarrantyRecord.lead_id == t.lead_id)
        if t.product_sku:
            wq = wq.filter(models.WarrantyRecord.product_sku == t.product_sku)
        recs = wq.all()
        if recs:
            t.under_warranty = any(r.warranty_end and r.warranty_end >= date.today() for r in recs)
    db.add(t)
    db.flush()
    if t.lead_id:
        log_activity(db, lead_id=t.lead_id, activity_type="system", subject=f"Service ticket {t.ticket_code} opened ({t.priority})",
                     notes=t.issue, performed_by=user_name(request), touch=False)
    db.commit()
    db.refresh(t)
    return _ticket_row(t)


@router.patch("/tickets/{ticket_id}")
def update_ticket(ticket_id: int, payload: TicketIn, db: Session = Depends(get_db)):
    t = db.query(models.ServiceTicket).filter(models.ServiceTicket.ticket_id == ticket_id).first()
    if not t:
        raise HTTPException(404, "Ticket not found")
    data = payload.dict(exclude_unset=True)
    for k, v in data.items():
        setattr(t, k, v)
    if "priority" in data and t.priority in L.SERVICE_SLA_HOURS and t.created_at:
        t.sla_due_at = L._aware(t.created_at) + timedelta(hours=L.SERVICE_SLA_HOURS[t.priority])
    if t.status in ("resolved", "closed") and not t.resolved_at:
        t.resolved_at = L.now_utc()
    if t.status not in ("resolved", "closed"):
        t.resolved_at = None
    if t.status in ("resolved", "closed") and t.ticket_type == "amc_visit" and t.amc_id:
        amc = db.query(models.AmcContract).filter(models.AmcContract.amc_id == t.amc_id).first()
        if amc:
            _record_amc_visit(amc, date.today())
    db.commit()
    return _ticket_row(t)


# ═════════════════════════════════════════════════════════════════════════════
# AMC contracts
# ═════════════════════════════════════════════════════════════════════════════
class AmcIn(BaseModel):
    lead_id: Optional[int] = None
    dealer_id: Optional[int] = None
    customer_name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    visits_per_year: Optional[int] = None
    contract_value: Optional[float] = None
    next_visit_date: Optional[date] = None
    status: Optional[str] = None
    notes: Optional[str] = None


def _record_amc_visit(amc, visit_date):
    amc.last_visit_date = visit_date
    gap = max(1, 12 // max(1, amc.visits_per_year or 2))
    nxt = _add_months(visit_date, gap)
    amc.next_visit_date = nxt if (not amc.end_date or nxt <= amc.end_date) else None


def _amc_row(a, today=None, leads=None):
    today = today or date.today()
    d = row_dict(a)
    status = a.status
    if status == "active" and a.end_date and a.end_date < today:
        status = "expired"
    d["effective_status"] = status
    d["renewal_due"] = bool(status == "active" and a.end_date and (a.end_date - today).days <= L.AMC_RENEWAL_WINDOW_DAYS)
    d["visit_due"] = bool(status == "active" and a.next_visit_date and a.next_visit_date <= today + timedelta(days=7))
    if leads is not None:
        lead = leads.get(a.lead_id)
        d["lead_code"] = getattr(lead, "lead_code", None)
        d["project_name"] = getattr(lead, "project_name", None)
    return d


@router.get("/amc")
def list_amc(db: Session = Depends(get_db)):
    rows = db.query(models.AmcContract).order_by(models.AmcContract.end_date.asc().nullslast()).all()
    leads = _lead_labels(db, [r.lead_id for r in rows])
    out = [_amc_row(r, leads=leads) for r in rows]
    active = [r for r in out if r["effective_status"] == "active"]
    return {
        "summary": {
            "active": len(active),
            "annual_value": round(sum(float(r["contract_value"] or 0) for r in active), 2),
            "renewals_due": sum(1 for r in out if r["renewal_due"]),
            "visits_due": sum(1 for r in out if r["visit_due"]),
        },
        "contracts": out,
    }


@router.post("/amc")
def create_amc(payload: AmcIn, db: Session = Depends(get_db)):
    a = models.AmcContract(**{k: v for k, v in payload.dict(exclude_unset=True).items() if v not in (None, "")})
    a.amc_code = next_code(db, models.AmcContract, "amc_code", "AMC")
    a.status = a.status or "active"
    a.visits_per_year = a.visits_per_year or 2
    if a.lead_id:
        lead = db.query(models.Lead).filter(models.Lead.lead_id == a.lead_id).first()
        if lead:
            a.customer_name = a.customer_name or lead.client_name or lead.project_name
            a.dealer_id = a.dealer_id or lead.dealer_id
    if a.start_date and not a.end_date:
        a.end_date = _add_months(a.start_date, 12) - timedelta(days=1)
    if a.start_date and not a.next_visit_date:
        a.next_visit_date = _add_months(a.start_date, max(1, 12 // a.visits_per_year))
    db.add(a)
    db.commit()
    db.refresh(a)
    return _amc_row(a)


@router.patch("/amc/{amc_id}")
def update_amc(amc_id: int, payload: AmcIn, db: Session = Depends(get_db)):
    a = db.query(models.AmcContract).filter(models.AmcContract.amc_id == amc_id).first()
    if not a:
        raise HTTPException(404, "AMC not found")
    for k, v in payload.dict(exclude_unset=True).items():
        setattr(a, k, v)
    db.commit()
    return _amc_row(a)


@router.post("/amc/{amc_id}/visit")
def log_amc_visit(amc_id: int, payload: dict, request: Request, db: Session = Depends(get_db)):
    a = db.query(models.AmcContract).filter(models.AmcContract.amc_id == amc_id).first()
    if not a:
        raise HTTPException(404, "AMC not found")
    vd = date.fromisoformat(payload["visit_date"]) if payload.get("visit_date") else date.today()
    _record_amc_visit(a, vd)
    if a.lead_id:
        log_activity(db, lead_id=a.lead_id, activity_type="site_visit", subject=f"AMC visit ({a.amc_code})",
                     notes=payload.get("notes"), performed_by=user_name(request), touch=False)
    db.commit()
    return _amc_row(a)


@router.post("/amc/{amc_id}/renew")
def renew_amc(amc_id: int, payload: dict, db: Session = Depends(get_db)):
    a = db.query(models.AmcContract).filter(models.AmcContract.amc_id == amc_id).first()
    if not a:
        raise HTTPException(404, "AMC not found")
    start = (a.end_date + timedelta(days=1)) if a.end_date else date.today()
    new = models.AmcContract(
        amc_code=next_code(db, models.AmcContract, "amc_code", "AMC"), lead_id=a.lead_id, dealer_id=a.dealer_id,
        customer_name=a.customer_name, start_date=start, end_date=_add_months(start, 12) - timedelta(days=1),
        visits_per_year=a.visits_per_year, contract_value=payload.get("contract_value", a.contract_value),
        next_visit_date=_add_months(start, max(1, 12 // (a.visits_per_year or 2))), status="active",
        notes=f"Renewal of {a.amc_code}",
    )
    a.status = "expired" if a.end_date and a.end_date < date.today() else a.status
    db.add(new)
    db.commit()
    db.refresh(new)
    return _amc_row(new)
