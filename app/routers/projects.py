from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from app.database import get_db
from app import models

router = APIRouter()

STAGES = ['boq', 'order_placed', 'delivered', 'installation', 'handover']

class TrackingUpdate(BaseModel):
    current_stage: Optional[str] = None
    boq_date: Optional[date] = None
    order_placed_date: Optional[date] = None
    delivered_date: Optional[date] = None
    installation_date: Optional[date] = None
    handover_date: Optional[date] = None
    notes: Optional[str] = None

class SnagCreate(BaseModel):
    description: str
    stage: Optional[str] = None
    notes: Optional[str] = None

class SnagUpdate(BaseModel):
    status: Optional[str] = None
    resolved_date: Optional[date] = None
    notes: Optional[str] = None

@router.get("/")
def list_projects(db: Session = Depends(get_db)):
    leads = db.query(models.Lead).filter(models.Lead.status == 'won').all()
    result = []
    for lead in leads:
        tracking = db.query(models.ProjectTracking).filter(
            models.ProjectTracking.lead_id == lead.lead_id
        ).first()
        snags = db.query(models.ProjectSnag).filter(
            models.ProjectSnag.lead_id == lead.lead_id
        ).all()
        result.append({
            "lead_id": lead.lead_id,
            "lead_code": lead.lead_code,
            "client_name": lead.client_name,
            "project_name": lead.project_name,
            "city": lead.city,
            "category": lead.category,
            "tracking": {
                "current_stage": tracking.current_stage if tracking else "boq",
                "boq_date": tracking.boq_date.isoformat() if tracking and tracking.boq_date else None,
                "order_placed_date": tracking.order_placed_date.isoformat() if tracking and tracking.order_placed_date else None,
                "delivered_date": tracking.delivered_date.isoformat() if tracking and tracking.delivered_date else None,
                "installation_date": tracking.installation_date.isoformat() if tracking and tracking.installation_date else None,
                "handover_date": tracking.handover_date.isoformat() if tracking and tracking.handover_date else None,
                "notes": tracking.notes if tracking else None,
            } if tracking else {"current_stage": "boq"},
            "snags": [
                {
                    "id": s.id,
                    "description": s.description,
                    "status": s.status,
                    "stage": s.stage,
                    "reported_date": s.reported_date.isoformat() if s.reported_date else None,
                    "resolved_date": s.resolved_date.isoformat() if s.resolved_date else None,
                    "notes": s.notes,
                }
                for s in snags
            ],
            "open_snags": sum(1 for s in snags if s.status == 'open'),
        })
    return result

@router.patch("/{lead_id}/tracking")
def update_tracking(lead_id: int, payload: TrackingUpdate, db: Session = Depends(get_db)):
    tracking = db.query(models.ProjectTracking).filter(
        models.ProjectTracking.lead_id == lead_id
    ).first()
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
    snag = models.ProjectSnag(
        lead_id=lead_id,
        description=payload.description,
        stage=payload.stage,
        notes=payload.notes,
    )
    db.add(snag)
    db.commit()
    return {"success": True}

@router.patch("/{lead_id}/snags/{snag_id}")
def update_snag(lead_id: int, snag_id: int, payload: SnagUpdate, db: Session = Depends(get_db)):
    snag = db.query(models.ProjectSnag).filter(
        models.ProjectSnag.id == snag_id,
        models.ProjectSnag.lead_id == lead_id
    ).first()
    if not snag:
        raise HTTPException(status_code=404, detail="Snag not found")
    for field, value in payload.dict(exclude_none=True).items():
        setattr(snag, field, value)
    db.commit()
    return {"success": True}

@router.delete("/{lead_id}/snags/{snag_id}")
def delete_snag(lead_id: int, snag_id: int, db: Session = Depends(get_db)):
    snag = db.query(models.ProjectSnag).filter(
        models.ProjectSnag.id == snag_id,
        models.ProjectSnag.lead_id == lead_id
    ).first()
    if not snag:
        raise HTTPException(status_code=404, detail="Snag not found")
    db.delete(snag)
    db.commit()
    return {"success": True}
