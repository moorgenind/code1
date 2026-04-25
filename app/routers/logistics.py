from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from app.database import get_db
from app import models

router = APIRouter()

class ShipmentCreate(BaseModel):
    direction: str  # inbound / outbound
    po_id: Optional[int] = None
    lead_id: Optional[int] = None
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    expected_date: Optional[date] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    notes: Optional[str] = None

class ShipmentUpdate(BaseModel):
    status: Optional[str] = None
    actual_date: Optional[date] = None
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    notes: Optional[str] = None

def generate_shipment_code(db: Session, direction: str) -> str:
    count = db.query(models.Shipment).count()
    prefix = "INB" if direction == "inbound" else "OUT"
    return f"{prefix}-2627-{str(count + 1).zfill(3)}"

@router.get("/")
def list_shipments(db: Session = Depends(get_db)):
    shipments = db.query(models.Shipment).order_by(models.Shipment.created_at.desc()).all()
    result = []
    for s in shipments:
        lead = db.query(models.Lead).filter(models.Lead.lead_id == s.lead_id).first() if s.lead_id else None
        po = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.po_id == s.po_id).first() if s.po_id else None
        result.append({
            "id": s.id,
            "shipment_code": s.shipment_code,
            "direction": s.direction,
            "po_code": po.po_code if po else None,
            "client_name": lead.client_name if lead else None,
            "project_name": lead.project_name if lead else None,
            "from_location": s.from_location,
            "to_location": s.to_location,
            "carrier": s.carrier,
            "tracking_number": s.tracking_number,
            "status": s.status,
            "expected_date": s.expected_date.isoformat() if s.expected_date else None,
            "actual_date": s.actual_date.isoformat() if s.actual_date else None,
            "driver_name": s.driver_name,
            "driver_phone": s.driver_phone,
            "notes": s.notes,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        })
    return result

@router.post("/")
def create_shipment(payload: ShipmentCreate, db: Session = Depends(get_db)):
    shipment = models.Shipment(
        shipment_code=generate_shipment_code(db, payload.direction),
        direction=payload.direction,
        po_id=payload.po_id,
        lead_id=payload.lead_id,
        from_location=payload.from_location,
        to_location=payload.to_location,
        carrier=payload.carrier,
        tracking_number=payload.tracking_number,
        expected_date=payload.expected_date,
        driver_name=payload.driver_name,
        driver_phone=payload.driver_phone,
        notes=payload.notes,
    )
    db.add(shipment)
    db.commit()
    db.refresh(shipment)
    return {"id": shipment.id, "shipment_code": shipment.shipment_code}

@router.patch("/{shipment_id}")
def update_shipment(shipment_id: int, payload: ShipmentUpdate, db: Session = Depends(get_db)):
    shipment = db.query(models.Shipment).filter(models.Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    for field, value in payload.dict(exclude_none=True).items():
        setattr(shipment, field, value)
    db.commit()
    return {"success": True}

@router.delete("/{shipment_id}")
def delete_shipment(shipment_id: int, db: Session = Depends(get_db)):
    shipment = db.query(models.Shipment).filter(models.Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    db.delete(shipment)
    db.commit()
    return {"success": True}
