from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import get_db
from app import models, schemas
from app.drive import create_lead_folder_structure

router = APIRouter()


# =========================================
# HELPERS
# =========================================
def generate_lead_code(db: Session) -> str:
    year = datetime.now().year
    short_year = str(year)[2:]
    next_year_short = str(year + 1)[2:]
    prefix = f"LD-{short_year}{next_year_short}"

    last = db.query(models.Lead).filter(models.Lead.lead_code.like(f"{prefix}-%")).order_by(models.Lead.lead_code.desc()).first()
    last_num = 0
    if last and last.lead_code:
        try: last_num = int(last.lead_code.split("-")[-1])
        except: pass
    number = str(last_num + 1).zfill(3)
    return f"{prefix}-{number}"


def generate_boq_code(db: Session) -> str:
    year = datetime.now().year
    short_year = str(year)[2:]
    next_year_short = str(year + 1)[2:]
    prefix = f"BOQ-{short_year}{next_year_short}"

    count = db.query(models.Boq).count()
    number = str(count + 1).zfill(3)
    return f"{prefix}-{number}"


def generate_design_code(db: Session) -> str:
    year = datetime.now().year
    short_year = str(year)[2:]
    next_year_short = str(year + 1)[2:]
    prefix = f"DSG-{short_year}{next_year_short}"

    count = db.query(models.DesignRequest).count()
    number = str(count + 1).zfill(3)
    return f"{prefix}-{number}"


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
    result = []
    for lead in leads:
        boq_value = sum(float(b.total_amount or 0) for b in lead.boqs)
        d = {c.name: getattr(lead, c.name) for c in lead.__table__.columns}
        d["boq_value"] = boq_value
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

    db.add(lead)
    db.flush()  # get lead_id before commit

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
    db: Session = Depends(get_db)
):
    lead = db.query(models.Lead).filter(models.Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead.status = payload.status
    if payload.lost_reason:
        lead.lost_reason = payload.lost_reason

    db.commit()
    db.refresh(lead)
    return lead


@router.patch("/{lead_id}", response_model=schemas.LeadResponse)
def update_lead(lead_id: int, payload: schemas.LeadCreate, db: Session = Depends(get_db)):
    lead = db.query(models.Lead).filter(models.Lead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    for field, value in payload.dict(exclude_unset=True).items():
        if field in ['arch_lighting', 'decorative_lighting', 'automation', 'exterior_lighting', 'mechanical_switches', 'smart_locks', 'design_required']:
            continue
        if field == 'created_at' and value:
            from datetime import datetime
            setattr(lead, field, datetime.fromisoformat(value))
            continue
        if hasattr(lead, field):
            setattr(lead, field, value)

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