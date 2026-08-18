from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from decimal import Decimal
from typing import Optional, List
from app.database import get_db
from app import models

router = APIRouter()


class DCLineItemCreate(BaseModel):
    sku: Optional[str] = None
    product_name: Optional[str] = None
    quantity: int
    unit: Optional[str] = "pcs"
    approx_value: Optional[Decimal] = None


class DCCreate(BaseModel):
    lead_id: Optional[int] = None
    shipment_id: Optional[int] = None
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    purpose: Optional[str] = "stock_transfer"
    vehicle_number: Optional[str] = None
    transporter: Optional[str] = None
    notes: Optional[str] = None
    created_by: Optional[str] = None
    line_items: List[DCLineItemCreate] = []


def generate_dc_code(db: Session) -> str:
    fy = "2627"
    pattern = f"DC-{fy}-%"
    last = db.query(func.max(models.DeliveryChallan.dc_code)).filter(
        models.DeliveryChallan.dc_code.like(pattern)
    ).scalar()
    if last:
        try:
            num = int(last.split("-")[-1]) + 1
        except:
            num = 1
    else:
        num = 1
    return f"DC-{fy}-{str(num).zfill(3)}"


@router.post("/")
def create_dc(payload: DCCreate, db: Session = Depends(get_db)):
    dc = models.DeliveryChallan(
        dc_code=generate_dc_code(db),
        lead_id=payload.lead_id,
        shipment_id=payload.shipment_id,
        from_location=payload.from_location,
        to_location=payload.to_location,
        purpose=payload.purpose,
        vehicle_number=payload.vehicle_number,
        transporter=payload.transporter,
        notes=payload.notes,
        created_by=payload.created_by,
    )
    db.add(dc)
    db.flush()

    for item in payload.line_items:
        hsn = None
        if item.sku:
            product = db.query(models.Product).filter(models.Product.sku == item.sku).first()
            if product:
                hsn = product.hsn_code
        db.add(models.DeliveryChallanLineItem(
            dc_id=dc.dc_id, sku=item.sku, product_name=item.product_name,
            hsn_code=hsn, quantity=item.quantity, unit=item.unit,
            approx_value=item.approx_value,
        ))

    db.commit()
    db.refresh(dc)
    return {"dc_id": dc.dc_id, "dc_code": dc.dc_code}


@router.get("/")
def list_dcs(lead_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(models.DeliveryChallan)
    if lead_id:
        query = query.filter(models.DeliveryChallan.lead_id == lead_id)
    dcs = query.order_by(models.DeliveryChallan.created_at.desc()).all()
    result = []
    for dc in dcs:
        d = {c.name: getattr(dc, c.name) for c in dc.__table__.columns}
        d["items_count"] = len(dc.line_items)
        result.append(d)
    return result


@router.get("/{dc_id}")
def get_dc(dc_id: int, db: Session = Depends(get_db)):
    dc = db.query(models.DeliveryChallan).filter(models.DeliveryChallan.dc_id == dc_id).first()
    if not dc:
        raise HTTPException(status_code=404, detail="Delivery Challan not found")
    d = {c.name: getattr(dc, c.name) for c in dc.__table__.columns}
    d["line_items"] = [
        {c.name: getattr(item, c.name) for c in item.__table__.columns}
        for item in dc.line_items
    ]
    return d


@router.delete("/{dc_id}")
def delete_dc(dc_id: int, db: Session = Depends(get_db)):
    dc = db.query(models.DeliveryChallan).filter(models.DeliveryChallan.dc_id == dc_id).first()
    if not dc:
        raise HTTPException(status_code=404, detail="Delivery Challan not found")
    db.query(models.DeliveryChallanLineItem).filter(models.DeliveryChallanLineItem.dc_id == dc_id).delete()
    db.delete(dc)
    db.commit()
    return {"status": "deleted"}
