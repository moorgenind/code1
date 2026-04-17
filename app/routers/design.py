from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from app.database import get_db
from app import models, schemas

router = APIRouter()


# =========================================
# ROUTES
# =========================================
@router.get("/", response_model=List[schemas.DesignRequestResponse])
def list_design_requests(
    lead_id: int = None,
    status: str = None,
    request_type: str = None,
    assigned_to: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.DesignRequest)

    if lead_id:
        query = query.filter(models.DesignRequest.lead_id == lead_id)
    if status:
        query = query.filter(models.DesignRequest.status == status)
    if request_type:
        query = query.filter(models.DesignRequest.request_type == request_type)
    if assigned_to:
        query = query.filter(models.DesignRequest.assigned_to == assigned_to)

    return query.order_by(models.DesignRequest.created_at.desc()).all()


@router.get("/{design_request_id}", response_model=schemas.DesignRequestResponse)
def get_design_request(design_request_id: int, db: Session = Depends(get_db)):
    dr = db.query(models.DesignRequest).filter(
        models.DesignRequest.design_request_id == design_request_id
    ).first()
    if not dr:
        raise HTTPException(status_code=404, detail="Design request not found")
    return dr


@router.post("/", response_model=schemas.DesignRequestResponse)
def create_design_request(
    payload: schemas.DesignRequestCreate,
    db: Session = Depends(get_db)
):
    # Check lead exists
    lead = db.query(models.Lead).filter(
        models.Lead.lead_id == payload.lead_id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Check boq exists if provided
    if payload.boq_id:
        boq = db.query(models.Boq).filter(
            models.Boq.boq_id == payload.boq_id
        ).first()
        if not boq:
            raise HTTPException(status_code=404, detail="BOQ not found")

    # Generate design code
    year = datetime.now().year
    short_year = str(year)[2:]
    next_year_short = str(year + 1)[2:]
    count = db.query(models.DesignRequest).count()
    design_code = f"DSG-{short_year}{next_year_short}-{str(count + 1).zfill(3)}"

    dr = models.DesignRequest(
        design_code=design_code,
        lead_id=payload.lead_id,
        boq_id=payload.boq_id,
        request_type=payload.request_type,
        status="pending",
        assigned_to=payload.assigned_to,
        notes=payload.notes,
    )

    db.add(dr)

    # Update lead status
    lead.status = "design_in_progress"

    db.commit()
    db.refresh(dr)
    return dr


@router.patch("/{design_request_id}/status", response_model=schemas.DesignRequestResponse)
def update_design_request_status(
    design_request_id: int,
    payload: schemas.DesignRequestStatusUpdate,
    db: Session = Depends(get_db)
):
    dr = db.query(models.DesignRequest).filter(
        models.DesignRequest.design_request_id == design_request_id
    ).first()
    if not dr:
        raise HTTPException(status_code=404, detail="Design request not found")

    dr.status = payload.status

    if payload.drive_output_url:
        dr.drive_output_url = payload.drive_output_url

    if payload.status == "completed":
        dr.completed_at = payload.completed_at or datetime.now()
        # Update lead status
        lead = db.query(models.Lead).filter(
            models.Lead.lead_id == dr.lead_id
        ).first()
        if lead:
            lead.status = "design_in_progress"

    if payload.status == "approved":
        lead = db.query(models.Lead).filter(
            models.Lead.lead_id == dr.lead_id
        ).first()
        if lead:
            lead.status = "quote_sent"

    db.commit()
    db.refresh(dr)
    return dr


@router.delete("/{design_request_id}")
def delete_design_request(
    design_request_id: int,
    db: Session = Depends(get_db)
):
    dr = db.query(models.DesignRequest).filter(
        models.DesignRequest.design_request_id == design_request_id
    ).first()
    if not dr:
        raise HTTPException(status_code=404, detail="Design request not found")

    db.delete(dr)
    db.commit()
    return {"success": True, "message": f"Design request {design_request_id} deleted"}