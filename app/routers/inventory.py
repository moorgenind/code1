from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from decimal import Decimal
from typing import Optional, List
from datetime import datetime
from app.database import get_db
from app import models

router = APIRouter()

# ── Schemas ──────────────────────────────────────────
class POLineItemCreate(BaseModel):
    sku: str
    product_name: str
    quantity_ordered: int
    unit_cost: Decimal
    line_total: Decimal

class POCreate(BaseModel):
    lead_id: int
    supplier: Optional[str] = "Moolken"
    notes: Optional[str] = None
    line_items: List[POLineItemCreate] = []

class StockAdjust(BaseModel):
    sku: str
    product_name: str
    quantity_delta: int
    notes: Optional[str] = None

# ── Helpers ───────────────────────────────────────────
def generate_po_code(db: Session) -> str:
    count = db.query(models.PurchaseOrder).count()
    return f"PO-2627-{str(count + 1).zfill(3)}"

# ── Routes ────────────────────────────────────────────
@router.get("/dashboard")
def inventory_dashboard(db: Session = Depends(get_db)):
    pos = db.query(models.PurchaseOrder).order_by(models.PurchaseOrder.created_at.desc()).all()
    stock = db.query(models.Stock).all()

    po_list = []
    for po in pos:
        lead = db.query(models.Lead).filter(models.Lead.lead_id == po.lead_id).first()
        total = sum(float(i.line_total) for i in po.line_items)
        received = all(i.quantity_received >= i.quantity_ordered for i in po.line_items) if po.line_items else False
        po_list.append({
            "po_id": po.po_id,
            "po_code": po.po_code,
            "lead_id": po.lead_id,
            "client_name": lead.client_name if lead else None,
            "project_name": lead.project_name if lead else None,
            "supplier": po.supplier,
            "status": po.status,
            "total": total,
            "items_count": len(po.line_items),
            "created_at": po.created_at.isoformat() if po.created_at else None,
            "ordered_at": po.ordered_at.isoformat() if po.ordered_at else None,
            "received_at": po.received_at.isoformat() if po.received_at else None,
            "line_items": [
                {
                    "id": i.id,
                    "sku": i.sku,
                    "product_name": i.product_name,
                    "quantity_ordered": i.quantity_ordered,
                    "quantity_received": i.quantity_received,
                    "unit_cost": float(i.unit_cost),
                    "line_total": float(i.line_total),
                }
                for i in po.line_items
            ]
        })

    return {
        "summary": {
            "total_pos": len(pos),
            "draft": sum(1 for p in pos if p.status == "draft"),
            "ordered": sum(1 for p in pos if p.status == "ordered"),
            "received": sum(1 for p in pos if p.status == "received"),
            "total_stock_skus": len(stock),
            "total_stock_units": sum(s.quantity_on_hand for s in stock),
        },
        "purchase_orders": po_list,
        "stock": [
            {
                "id": s.id,
                "sku": s.sku,
                "product_name": s.product_name,
                "quantity_on_hand": s.quantity_on_hand,
                "quantity_reserved": s.quantity_reserved,
                "available": s.quantity_on_hand - s.quantity_reserved,
            }
            for s in stock
        ]
    }

@router.post("/purchase-orders")
def create_po(payload: POCreate, db: Session = Depends(get_db)):
    po = models.PurchaseOrder(
        po_code=generate_po_code(db),
        lead_id=payload.lead_id,
        supplier=payload.supplier,
        notes=payload.notes,
        status="draft",
    )
    db.add(po)
    db.flush()
    for item in payload.line_items:
        li = models.POLineItem(
            po_id=po.po_id,
            sku=item.sku,
            product_name=item.product_name,
            quantity_ordered=item.quantity_ordered,
            unit_cost=item.unit_cost,
            line_total=item.line_total,
        )
        db.add(li)
    db.commit()
    db.refresh(po)
    return {"po_id": po.po_id, "po_code": po.po_code}

@router.patch("/purchase-orders/{po_id}/status")
def update_po_status(po_id: int, status: str, db: Session = Depends(get_db)):
    po = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.po_id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")
    po.status = status
    if status == "ordered":
        po.ordered_at = datetime.utcnow()
    if status == "received":
        po.received_at = datetime.utcnow()
        # Update stock
        for item in po.line_items:
            stock = db.query(models.Stock).filter(models.Stock.sku == item.sku).first()
            if stock:
                stock.quantity_on_hand += item.quantity_ordered - item.quantity_received
                stock.updated_at = datetime.utcnow()
            else:
                stock = models.Stock(
                    sku=item.sku,
                    product_name=item.product_name,
                    quantity_on_hand=item.quantity_ordered,
                )
                db.add(stock)
            item.quantity_received = item.quantity_ordered
    db.commit()
    return {"success": True}

@router.post("/stock/adjust")
def adjust_stock(payload: StockAdjust, db: Session = Depends(get_db)):
    stock = db.query(models.Stock).filter(models.Stock.sku == payload.sku).first()
    if stock:
        stock.quantity_on_hand += payload.quantity_delta
        stock.updated_at = datetime.utcnow()
    else:
        stock = models.Stock(
            sku=payload.sku,
            product_name=payload.product_name,
            quantity_on_hand=payload.quantity_delta,
        )
        db.add(stock)
    db.commit()
    return {"success": True}
