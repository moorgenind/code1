from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import os
import traceback
from fastapi import Request
from app.database import get_db
from app import models, schemas
from app import crm_logic as L
from app.crm_common import rescore, log_activity, user_name
from app.drive import create_lead_folder_structure

# "No stage movement without an activity log" — set CRM_REQUIRE_ACTIVITY=0 to relax
REQUIRE_ACTIVITY = os.getenv("CRM_REQUIRE_ACTIVITY", "1") != "0"
RECENT_ACTIVITY_DAYS = 7
CRM_FIELDS = [
    "attribution_type", "owner_employee_id", "source_employee_id", "architect_id", "builder_name",
    "state", "pincode", "project_location", "budget_range", "property_type", "property_size_sqft",
    "construction_stage", "expected_possession_date", "purchase_timeline", "product_interest",
    "estimated_value", "expected_order_date",
]

router = APIRouter()


# =========================================
# HELPERS
# =========================================
def generate_lead_code(db: Session) -> str:
    # Indian FY prefix (LD-2627-…) and numeric MAX, never COUNT
    from app.crm_common import next_code
    return next_code(db, models.Lead, "lead_code", "LD")


def generate_boq_code(db: Session) -> str:
    # Same MAX-of-code rule as boqs.py so the two paths can never collide
    from app.crm_common import next_code
    db.flush()
    return next_code(db, models.Boq, "boq_code", "BOQ")


def generate_design_code(db: Session) -> str:
    # MAX-based (COUNT produced duplicate codes once requests were deleted)
    from app.crm_common import next_code
    db.flush()
    return next_code(db, models.DesignRequest, "design_code", "DSG")


# =========================================
# ROUTES
# =========================================
@router.get("/")
def list_leads(
    status: str = None,
    city: str = None,
    channel: str = None,
    category: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Lead)

    if status:
        query = query.filter(models.Lead.status == status)
    if city:
        query = query.filter(models.Lead.city == city)
    if channel:
        query = query.filter(models.Lead.channel == channel)

    if category:
        query = query.filter(models.Lead.category == category)
    leads = query.order_by(models.Lead.created_at.desc()).all()

    from sqlalchemy import func, text
    lead_ids = [l.lead_id for l in leads]
    boq_totals = {}
    if lead_ids:
        rows = db.execute(text("""
            WITH latest AS (
              SELECT DISTINCT ON (lead_id, category) boq_id, lead_id
              FROM boqs WHERE lead_id = ANY(:ids)
              ORDER BY lead_id, category, version DESC, boq_id DESC)
            SELECT latest.lead_id,
                   COALESCE(SUM(bli.quantity * COALESCE(bli.list_price, bli.unit_price)), 0),
                   COALESCE(SUM(bli.line_total), 0)
            FROM latest JOIN boq_line_items bli ON bli.boq_id = latest.boq_id
            GROUP BY latest.lead_id
        """), {"ids": lead_ids}).fetchall()
        boq_totals = {r[0]: (float(r[1] or 0), float(r[2] or 0)) for r in rows}

    result = []
    for lead in leads:
        boq_list, boq_value = boq_totals.get(lead.lead_id, (0.0, 0.0))
        d = {c.name: getattr(lead, c.name) for c in lead.__table__.columns}
        d["boq_value"] = boq_value
        d["boq_list_value"] = boq_list
        d["boq_discount_pct"] = round((1 - boq_value / boq_list) * 100, 1) if boq_list else None
        sla = L.sla_state(lead)
        d["sla_overdue"] = bool(sla and sla["overdue"])
        d["sla_level"] = sla["level"] if sla else 0
        d["idle_days"] = sla["idle_days"] if sla else None
        d["probability"] = L.lead_probability(lead)
        d["dealer_acceptance_overdue"] = L.dealer_acceptance_overdue(lead)
        result.append(d)
    return result


@router.get("/{lead_id}", response_model=schemas.LeadResponse)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(models.Lead).filter(models.Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.post("/", response_model=schemas.LeadResponse)
def create_lead(payload: schemas.LeadCreate, db: Session = Depends(get_db)):
    import traceback
    # Generate lead code
    lead_code = generate_lead_code(db)

    # Create lead in DB
    lead = models.Lead(
        lead_code=lead_code,
        client_id=payload.client_id,
        dealer_id=payload.dealer_id,
        project_name=payload.project_name,
        city=payload.city,
        channel=payload.channel,
        category=payload.category,
        lead_source=payload.lead_source,
        assigned_to=payload.assigned_to,
        remarks=payload.remarks,
        client_name=payload.client_name,
        client_phone=payload.client_phone,
        client_email=payload.client_email,
        client_address=payload.client_address,
        status="new",
    )
    for f in CRM_FIELDS:
        v = getattr(payload, f, None)
        if v not in (None, "", []):
            setattr(lead, f, v)
    if lead.owner_employee_id and not lead.assigned_to:
        emp = db.query(models.Employee).filter(models.Employee.employee_id == lead.owner_employee_id).first()
        if emp:
            lead.assigned_to = emp.name
    if not lead.attribution_type:
        lead.attribution_type = "dealer" if payload.dealer_id and payload.lead_source in ("dealer", "dealer_generated") else (
            "employee" if lead.source_employee_id else "company")
    if lead.dealer_id:
        lead.dealer_assigned_at = L.now_utc()
        lead.dealer_acceptance = "accepted" if lead.attribution_type == "dealer" else "pending"
    lead.last_activity_at = L.now_utc()
    lead.status_changed_at = L.now_utc()
    rescore(db, lead)
    if lead.lead_grade:
        lead.qualified_at = L.now_utc()

    db.add(lead)
    db.flush()  # get lead_id before commit
    log_activity(db, lead_id=lead.lead_id, activity_type="system", subject="Lead created",
                 notes=payload.remarks, performed_by=payload.assigned_to, touch=False)

    # Create Google Drive folder in background (non-blocking)
    import threading
    def create_drive_folder():
        try:
            client_obj = db.query(models.Client).filter(
                models.Client.client_id == payload.client_id
            ).first()
            client_name = client_obj.name if client_obj else 'Client'
            drive_result = create_lead_folder_structure(
                lead_code=lead_code,
                client_name=client_name,
                project_name=payload.project_name,
                city=payload.city or '',
            )
            from app.database import SessionLocal
            bg_db = SessionLocal()
            bg_db.query(models.Lead).filter(models.Lead.lead_id == lead.lead_id).update(
                {"drive_folder_url": drive_result["main_folder_link"]}
            )
            bg_db.commit()
            bg_db.close()
        except Exception as e:
            print(f"Drive folder creation failed: {e}")
    threading.Thread(target=create_drive_folder, daemon=True).start()

    # Auto-create BOQs based on scope flags
    boq_categories = []
    if payload.arch_lighting:
        boq_categories.append("architectural")
    if payload.decorative_lighting:
        boq_categories.append("decorative")
    if payload.automation:
        boq_categories.append("automation")
    if payload.exterior_lighting:
        boq_categories.append("exterior")

    for category in boq_categories:
        boq_code = generate_boq_code(db)
        boq = models.Boq(
            boq_code=boq_code,
            lead_id=lead.lead_id,
            category=category,
            version=1,
            status="draft",
        )
        db.add(boq)

    # Auto-create design requests if needed
    if payload.design_required:
        if payload.arch_lighting:
            design_code = generate_design_code(db)
            db.add(models.DesignRequest(
                design_code=design_code,
                lead_id=lead.lead_id,
                request_type="lighting_layout",
                status="pending",
            ))
        if payload.automation:
            design_code = generate_design_code(db)
            db.add(models.DesignRequest(
                design_code=design_code,
                lead_id=lead.lead_id,
                request_type="automation_proposal",
                status="pending",
            ))

    # Update lead status
    if boq_categories:
        lead.status = "boq_in_progress"

    db.commit()
    db.refresh(lead)
    return lead


@router.patch("/{lead_id}/status", response_model=schemas.LeadResponse)
def update_lead_status(
    lead_id: int,
    payload: schemas.LeadStatusUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    lead = db.query(models.Lead).filter(models.Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    old_status = lead.status
    note = (payload.note or "").strip()
    if payload.status != old_status:
        recent = False
        if lead.last_activity_at:
            recent = (L.now_utc() - L._aware(lead.last_activity_at)).days < RECENT_ACTIVITY_DAYS
        if REQUIRE_ACTIVITY and not recent and not note:
            raise HTTPException(status_code=422, detail={
                "code": "activity_required",
                "message": f"No activity logged in the last {RECENT_ACTIVITY_DAYS} days. Add a note on what happened before moving this lead.",
            })
        if payload.status in ("lost", "cold") and not (payload.lost_reason or lead.lost_reason or note):
            raise HTTPException(status_code=422, detail={"code": "reason_required", "message": "Give a reason for losing this lead."})

    lead.status = payload.status
    if payload.lost_reason:
        lead.lost_reason = payload.lost_reason
    if payload.status != old_status:
        lead.status_changed_at = L.now_utc()
        if payload.status == "qualified" and not lead.qualified_at:
            lead.qualified_at = L.now_utc()
        who = payload.performed_by or user_name(request)
        # A stage move with a note counts as a touch (resets the follow-up clock); a bare move doesn't
        log_activity(db, lead_id=lead.lead_id, activity_type="stage_change",
                     subject=f"{old_status.replace('_', ' ')} → {payload.status.replace('_', ' ')}",
                     notes=note or payload.lost_reason, performed_by=who, touch=bool(note))

    db.commit()
    db.refresh(lead)
    return lead


@router.patch("/{lead_id}", response_model=schemas.LeadResponse)
def update_lead(lead_id: int, payload: schemas.LeadCreate, db: Session = Depends(get_db)):
    lead = db.query(models.Lead).filter(models.Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    old_dealer = lead.dealer_id
    for field, value in payload.dict(exclude_unset=True).items():
        if field in ['arch_lighting', 'decorative_lighting', 'automation', 'exterior_lighting', 'mechanical_switches', 'smart_locks', 'design_required']:
            continue
        if field == 'status':
            continue  # status changes go through PATCH /leads/{id}/status
        if field == 'created_at' and value:
            from datetime import datetime
            setattr(lead, field, datetime.fromisoformat(value))
            continue
        if hasattr(lead, field):
            setattr(lead, field, value)

    if lead.dealer_id != old_dealer:
        if lead.dealer_id:
            lead.dealer_assigned_at = L.now_utc()
            lead.dealer_acceptance = "pending"
            lead.dealer_responded_at = None
        else:
            lead.dealer_acceptance = None
    rescore(db, lead)
    try:
        db.commit()
        db.refresh(lead)
        return lead
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{lead_id}")
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(models.Lead).filter(models.Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    db.delete(lead)
    db.commit()
    return {"success": True, "message": f"Lead {lead_id} deleted"}