from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from app.database import get_db
from app import models

router = APIRouter()

STAGES = ['boq', 'order_placed', 'site_coordination', 'material_delivery', 'installation', 'testing', 'handover']

class TrackingUpdate(BaseModel):
    current_stage: Optional[str] = None
    boq_date: Optional[date] = None
    order_placed_date: Optional[date] = None
    site_coordination_date: Optional[date] = None
    material_delivery_date: Optional[date] = None
    installation_date: Optional[date] = None
    testing_date: Optional[date] = None
    handover_date: Optional[date] = None
    architect_name: Optional[str] = None
    architect_phone: Optional[str] = None
    client_contact: Optional[str] = None
    client_phone: Optional[str] = None
    pmc_name: Optional[str] = None
    pmc_phone: Optional[str] = None
    false_ceiling_contractor: Optional[str] = None
    false_ceiling_phone: Optional[str] = None
    automation_team: Optional[str] = None
    lighting_team: Optional[str] = None
    civil_ready: Optional[bool] = None
    electricals_ready: Optional[bool] = None
    network_ready: Optional[bool] = None
    false_ceiling_ready: Optional[bool] = None
    pre_inspection_done: Optional[bool] = None
    notes: Optional[str] = None

class SnagCreate(BaseModel):
    description: str
    stage: Optional[str] = None
    assigned_to: Optional[str] = None
    notes: Optional[str] = None

class SnagUpdate(BaseModel):
    status: Optional[str] = None
    resolved_date: Optional[date] = None
    assigned_to: Optional[str] = None
    notes: Optional[str] = None

class SiteVisitCreate(BaseModel):
    visit_date: date
    visit_type: Optional[str] = "site_visit"
    attendees: Optional[str] = None
    observations: Optional[str] = None
    action_items: Optional[str] = None
    drive_photos_url: Optional[str] = None

def tracking_to_dict(t):
    if not t:
        return {"current_stage": "boq"}
    return {
        "current_stage": t.current_stage,
        "boq_date": t.boq_date.isoformat() if t.boq_date else None,
        "order_placed_date": t.order_placed_date.isoformat() if t.order_placed_date else None,
        "site_coordination_date": t.site_coordination_date.isoformat() if t.site_coordination_date else None,
        "material_delivery_date": t.material_delivery_date.isoformat() if t.material_delivery_date else None,
        "installation_date": t.installation_date.isoformat() if t.installation_date else None,
        "testing_date": t.testing_date.isoformat() if t.testing_date else None,
        "handover_date": t.handover_date.isoformat() if t.handover_date else None,
        "architect_name": t.architect_name,
        "architect_phone": t.architect_phone,
        "client_contact": t.client_contact,
        "client_phone": t.client_phone,
        "pmc_name": t.pmc_name,
        "pmc_phone": t.pmc_phone,
        "false_ceiling_contractor": t.false_ceiling_contractor,
        "false_ceiling_phone": t.false_ceiling_phone,
        "automation_team": t.automation_team,
        "lighting_team": t.lighting_team,
        "civil_ready": t.civil_ready,
        "electricals_ready": t.electricals_ready,
        "network_ready": t.network_ready,
        "false_ceiling_ready": t.false_ceiling_ready,
        "pre_inspection_done": t.pre_inspection_done,
        "notes": t.notes,
    }

@router.get("/")
def list_projects(db: Session = Depends(get_db)):
    leads = db.query(models.Lead).filter(models.Lead.status == 'won').all()
    result = []
    for lead in leads:
        tracking = db.query(models.ProjectTracking).filter(models.ProjectTracking.lead_id == lead.lead_id).first()
        snags = db.query(models.ProjectSnag).filter(models.ProjectSnag.lead_id == lead.lead_id).all()
        visits = db.query(models.SiteVisit).filter(models.SiteVisit.lead_id == lead.lead_id).order_by(models.SiteVisit.visit_date.desc()).all()
        result.append({
            "lead_id": lead.lead_id,
            "lead_code": lead.lead_code,
            "client_name": lead.client_name,
            "project_name": lead.project_name,
            "city": lead.city,
            "category": lead.category,
            "tracking": tracking_to_dict(tracking),
            "snags": [{"id": s.id, "description": s.description, "status": s.status, "stage": s.stage, "assigned_to": s.assigned_to, "reported_date": s.reported_date.isoformat() if s.reported_date else None, "resolved_date": s.resolved_date.isoformat() if s.resolved_date else None, "notes": s.notes} for s in snags],
            "open_snags": sum(1 for s in snags if s.status == 'open'),
            "site_visits": [{"id": v.id, "visit_date": v.visit_date.isoformat() if v.visit_date else None, "visit_type": v.visit_type, "attendees": v.attendees, "observations": v.observations, "action_items": v.action_items, "drive_photos_url": v.drive_photos_url} for v in visits],
        })
    return result

@router.patch("/{lead_id}/tracking")
def update_tracking(lead_id: int, payload: TrackingUpdate, db: Session = Depends(get_db)):
    tracking = db.query(models.ProjectTracking).filter(models.ProjectTracking.lead_id == lead_id).first()
    if not tracking:
        tracking = models.ProjectTracking(lead_id=lead_id)
        db.add(tracking)
    for field, value in payload.dict(exclude_none=True).items():
        setattr(tracking, field, value)
    tracking.updated_at = datetime.utcnow()
    db.commit()
    return {"success": True}

@router.post("/{lead_id}/snags")
def add_snag(lead_id: int, payload: SnagCreate, db: Session = Depends(get_db)):
    snag = models.ProjectSnag(lead_id=lead_id, description=payload.description, stage=payload.stage, assigned_to=payload.assigned_to, notes=payload.notes)
    db.add(snag)
    db.commit()
    return {"success": True}

@router.patch("/{lead_id}/snags/{snag_id}")
def update_snag(lead_id: int, snag_id: int, payload: SnagUpdate, db: Session = Depends(get_db)):
    snag = db.query(models.ProjectSnag).filter(models.ProjectSnag.id == snag_id, models.ProjectSnag.lead_id == lead_id).first()
    if not snag:
        raise HTTPException(status_code=404, detail="Snag not found")
    for field, value in payload.dict(exclude_none=True).items():
        setattr(snag, field, value)
    db.commit()
    return {"success": True}

@router.delete("/{lead_id}/snags/{snag_id}")
def delete_snag(lead_id: int, snag_id: int, db: Session = Depends(get_db)):
    snag = db.query(models.ProjectSnag).filter(models.ProjectSnag.id == snag_id, models.ProjectSnag.lead_id == lead_id).first()
    if not snag:
        raise HTTPException(status_code=404, detail="Snag not found")
    db.delete(snag)
    db.commit()
    return {"success": True}

@router.post("/{lead_id}/visits")
def add_visit(lead_id: int, payload: SiteVisitCreate, db: Session = Depends(get_db)):
    visit = models.SiteVisit(lead_id=lead_id, visit_date=payload.visit_date, visit_type=payload.visit_type, attendees=payload.attendees, observations=payload.observations, action_items=payload.action_items, drive_photos_url=payload.drive_photos_url)
    db.add(visit)
    db.commit()
    return {"success": True}

@router.delete("/{lead_id}/visits/{visit_id}")
def delete_visit(lead_id: int, visit_id: int, db: Session = Depends(get_db)):
    visit = db.query(models.SiteVisit).filter(models.SiteVisit.id == visit_id, models.SiteVisit.lead_id == lead_id).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    db.delete(visit)
    db.commit()
    return {"success": True}
