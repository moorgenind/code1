"""
Architects & Interior Designers (IDA) — the influence channel. Mounted at /architects.
Covers architects, interior designers, PMCs and builders/developers (partner_type).
"""
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app import crm_logic as L
from app.crm_common import row_dict, jsonable, rescore, log_activity, user_name

router = APIRouter()


class ArchitectIn(BaseModel):
    partner_type: Optional[str] = None
    firm_name: Optional[str] = None
    principal_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    address: Optional[str] = None
    instagram: Optional[str] = None
    segment: Optional[str] = None
    ranking: Optional[str] = None
    annual_project_volume: Optional[int] = None
    relationship_owner_id: Optional[int] = None
    next_followup_date: Optional[date] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


def _metrics(db, architect_ids=None):
    """leads, active projects, won, lost, pipeline value, revenue (MIPL invoices) per architect."""
    q = db.query(models.Lead).filter(models.Lead.architect_id != None)
    if architect_ids is not None:
        q = q.filter(models.Lead.architect_id.in_(architect_ids))
    leads = q.all()
    boq_totals = dict(db.query(models.Boq.lead_id, func.coalesce(func.sum(models.Boq.total_amount), 0))
                      .filter(models.Boq.lead_id.in_([l.lead_id for l in leads] or [0])).group_by(models.Boq.lead_id).all())
    rev = dict(db.query(models.Lead.architect_id, func.coalesce(func.sum(models.Invoice.invoice_amount), 0))
               .join(models.Invoice, models.Invoice.lead_id == models.Lead.lead_id)
               .filter(models.Lead.architect_id != None,
                       or_(models.Invoice.invoice_from == "MIPL", models.Invoice.invoice_from == None))
               .group_by(models.Lead.architect_id).all())
    m = {}
    year_ago = L.now_utc() - timedelta(days=365)
    for l in leads:
        d = m.setdefault(l.architect_id, {"leads": 0, "leads_12m": 0, "active": 0, "won": 0, "lost": 0, "pipeline_value": 0.0})
        d["leads"] += 1
        if l.created_at and L._aware(l.created_at) >= year_ago:
            d["leads_12m"] += 1
        if l.status in L.OPEN_STATUSES:
            d["active"] += 1
            d["pipeline_value"] += float(l.estimated_value or boq_totals.get(l.lead_id) or 0)
        elif l.status == "won":
            d["won"] += 1
        elif l.status in ("lost", "cold"):
            d["lost"] += 1
    for aid, d in m.items():
        d["revenue"] = float(rev.get(aid, 0) or 0)
        closed = d["won"] + d["lost"]
        d["conversion_pct"] = round(d["won"] / closed * 100, 1) if closed else None
    for aid, v in rev.items():
        if aid not in m:
            m[aid] = {"leads": 0, "leads_12m": 0, "active": 0, "won": 0, "lost": 0, "pipeline_value": 0.0, "revenue": float(v or 0), "conversion_pct": None}
    return m


def _empty_metrics():
    return {"leads": 0, "leads_12m": 0, "active": 0, "won": 0, "lost": 0, "pipeline_value": 0.0, "revenue": 0.0, "conversion_pct": None}


@router.get("/")
def list_architects(q: Optional[str] = None, city: Optional[str] = None, ranking: Optional[str] = None,
                    owner_id: Optional[int] = None, partner_type: Optional[str] = None,
                    include_inactive: bool = False, db: Session = Depends(get_db)):
    query = db.query(models.Architect)
    if not include_inactive:
        query = query.filter(models.Architect.is_active == True)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(models.Architect.firm_name.ilike(like), models.Architect.principal_name.ilike(like),
                                 models.Architect.phone.ilike(like)))
    if city: query = query.filter(func.lower(models.Architect.city) == city.lower())
    if ranking: query = query.filter(models.Architect.ranking == ranking)
    if owner_id: query = query.filter(models.Architect.relationship_owner_id == owner_id)
    if partner_type: query = query.filter(models.Architect.partner_type == partner_type)
    archs = query.order_by(models.Architect.firm_name).all()
    metrics = _metrics(db, [a.architect_id for a in archs])
    emps = {e.employee_id: e.name for e in db.query(models.Employee).all()}
    today = date.today()
    out = []
    for a in archs:
        d = row_dict(a)
        d["metrics"] = metrics.get(a.architect_id, _empty_metrics())
        d["owner_name"] = emps.get(a.relationship_owner_id)
        last = L._aware(a.last_meeting_date)
        d["days_since_meeting"] = (L.now_utc() - last).days if last else None
        d["followup_overdue"] = bool(a.next_followup_date and a.next_followup_date < today)
        out.append(d)
    return out


@router.post("/")
def create_architect(payload: ArchitectIn, request: Request, db: Session = Depends(get_db)):
    if not (payload.firm_name or "").strip():
        raise HTTPException(422, "Firm name is required")
    dup = None
    if payload.phone:
        digits = "".join(c for c in payload.phone if c.isdigit())[-10:]
        if len(digits) == 10:
            for a in db.query(models.Architect).filter(models.Architect.phone != None).all():
                if "".join(c for c in a.phone if c.isdigit())[-10:] == digits:
                    dup = a
                    break
    if not dup:
        dup = db.query(models.Architect).filter(func.lower(models.Architect.firm_name) == payload.firm_name.strip().lower(),
                                                func.lower(func.coalesce(models.Architect.city, "")) == (payload.city or "").strip().lower()).first()
    if dup:
        raise HTTPException(409, f"Already exists: {dup.firm_name} (#{dup.architect_id})")
    a = models.Architect(**{k: v for k, v in payload.dict(exclude_unset=True).items() if v is not None})
    a.partner_type = a.partner_type or "architect"
    a.is_active = True if a.is_active is None else a.is_active
    db.add(a)
    db.flush()
    log_activity(db, architect_id=a.architect_id, activity_type="system", subject="Added to CRM",
                 performed_by=user_name(request), touch=False)
    db.commit()
    db.refresh(a)
    return row_dict(a)


@router.get("/{architect_id}")
def get_architect(architect_id: int, db: Session = Depends(get_db)):
    a = db.query(models.Architect).filter(models.Architect.architect_id == architect_id).first()
    if not a:
        raise HTTPException(404, "Architect not found")
    d = row_dict(a)
    d["metrics"] = _metrics(db, [architect_id]).get(architect_id, _empty_metrics())
    owner = db.query(models.Employee).filter(models.Employee.employee_id == a.relationship_owner_id).first() if a.relationship_owner_id else None
    d["owner_name"] = owner.name if owner else None
    leads = db.query(models.Lead).filter(models.Lead.architect_id == architect_id).order_by(models.Lead.created_at.desc()).all()
    boq_totals = dict(db.query(models.Boq.lead_id, func.coalesce(func.sum(models.Boq.total_amount), 0))
                      .filter(models.Boq.lead_id.in_([l.lead_id for l in leads] or [0])).group_by(models.Boq.lead_id).all())
    d["leads"] = [{
        "lead_id": l.lead_id, "lead_code": l.lead_code, "project_name": l.project_name, "client_name": l.client_name,
        "city": l.city, "status": l.status, "grade": l.lead_grade,
        "value": float(l.estimated_value or boq_totals.get(l.lead_id) or 0), "created_at": jsonable(l.created_at),
    } for l in leads]
    acts = (db.query(models.CrmActivity).filter(models.CrmActivity.architect_id == architect_id)
            .order_by(models.CrmActivity.activity_at.desc()).limit(200).all())
    d["activities"] = [row_dict(x) for x in acts]
    return d


@router.patch("/{architect_id}")
def update_architect(architect_id: int, payload: ArchitectIn, db: Session = Depends(get_db)):
    a = db.query(models.Architect).filter(models.Architect.architect_id == architect_id).first()
    if not a:
        raise HTTPException(404, "Architect not found")
    rank_changed = "ranking" in payload.dict(exclude_unset=True) and payload.ranking != a.ranking
    for k, v in payload.dict(exclude_unset=True).items():
        setattr(a, k, (None if isinstance(v, str) and v.strip() == "" else v))
    if rank_changed:  # architect rank feeds lead scores
        for l in db.query(models.Lead).filter(models.Lead.architect_id == architect_id).all():
            rescore(db, l)
    db.commit()
    db.refresh(a)
    return row_dict(a)


@router.delete("/{architect_id}")
def deactivate_architect(architect_id: int, db: Session = Depends(get_db)):
    a = db.query(models.Architect).filter(models.Architect.architect_id == architect_id).first()
    if not a:
        raise HTTPException(404, "Architect not found")
    a.is_active = False  # soft delete — leads keep their attribution
    db.commit()
    return {"ok": True}


@router.post("/import-from-projects")
def import_from_project_tracking(db: Session = Depends(get_db)):
    """One-off: create architect records from the free-text architect names already on Projects,
    and link those leads to them."""
    created, linked = 0, 0
    rows = db.query(models.ProjectTracking).filter(models.ProjectTracking.architect_name != None).all()
    for t in rows:
        name = (t.architect_name or "").strip()
        if not name:
            continue
        lead = db.query(models.Lead).filter(models.Lead.lead_id == t.lead_id).first()
        a = db.query(models.Architect).filter(func.lower(models.Architect.firm_name) == name.lower()).first()
        if not a:
            a = models.Architect(firm_name=name, phone=t.architect_phone, city=lead.city if lead else None,
                                 partner_type="architect", is_active=True)
            db.add(a)
            db.flush()
            created += 1
        if lead and not lead.architect_id:
            lead.architect_id = a.architect_id
            rescore(db, lead)
            linked += 1
    db.commit()
    return {"architects_created": created, "leads_linked": linked}
