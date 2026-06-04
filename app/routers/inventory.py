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
    supplier: Optional[str] = "Moorgen"

class POCreate(BaseModel):
    lead_id: int
    notes: Optional[str] = None
    line_items: List[POLineItemCreate] = []

class StockAdjust(BaseModel):
    sku: str
    product_name: str
    quantity_delta: int
    notes: Optional[str] = None

# ── Helpers ───────────────────────────────────────────
def generate_po_code(db: Session) -> str:
    from sqlalchemy import func
    max_id = db.query(func.max(models.PurchaseOrder.po_id)).scalar() or 0
    return f"PO-2627-{str(max_id + 1).zfill(3)}"

def release_reservations(po: models.PurchaseOrder, db: Session):
    """Release stock reservations for all line items in a PO."""
    for item in po.line_items:
        if not item.sku:
            continue
        stock = db.query(models.Stock).filter(models.Stock.sku == item.sku).first()
        if stock:
            stock.quantity_reserved = max(0, stock.quantity_reserved - item.quantity_ordered)
            stock.updated_at = datetime.utcnow()

def apply_reservations(po: models.PurchaseOrder, db: Session):
    """Reserve stock for all Moorgen line items in a PO."""
    for item in po.line_items:
        if not item.sku or item.supplier != "Moorgen":
            continue
        stock = db.query(models.Stock).filter(models.Stock.sku == item.sku).first()
        if stock:
            stock.quantity_reserved += item.quantity_ordered
            stock.updated_at = datetime.utcnow()

# ── Routes ────────────────────────────────────────────
@router.get("/dashboard")
def inventory_dashboard(db: Session = Depends(get_db)):
    pos = db.query(models.PurchaseOrder).order_by(models.PurchaseOrder.created_at.desc()).all()
    stock = db.query(models.Stock).all()

    po_list = []
    for po in pos:
        lead = db.query(models.Lead).filter(models.Lead.lead_id == po.lead_id).first()
        total = sum(float(i.line_total) for i in po.line_items)
        po_list.append({
            "po_id": po.po_id,
            "po_code": po.po_code,
            "lead_id": po.lead_id,
            "client_name": lead.client_name if lead else None,
            "project_name": lead.project_name if lead else None,
            "status": po.status,
            "total": total,
            "items_count": len(po.line_items),
            "created_at": po.created_at.isoformat() if po.created_at else None,
            "ordered_at": po.ordered_at.isoformat() if po.ordered_at else None,
            "received_at": po.received_at.isoformat() if po.received_at else None,
            "notes": po.notes,
            "line_items": [
                {
                    "id": i.id,
                    "sku": i.sku,
                    "product_name": i.product_name,
                    "quantity_ordered": i.quantity_ordered,
                    "quantity_received": i.quantity_received,
                    "unit_cost": float(i.unit_cost),
                    "line_total": float(i.line_total),
                    "supplier": i.supplier or "Moorgen",
                }
                for i in po.line_items
            ]
        })

    stock_list = []
    for s in stock:
        stock_list.append({
            "id": s.id,
            "sku": s.sku,
            "product_name": s.product_name,
            "quantity_on_hand": s.quantity_on_hand,
            "quantity_reserved": s.quantity_reserved,
            "available": s.quantity_on_hand - s.quantity_reserved,
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
        "stock": stock_list,
    }

@router.get("/stock")
def get_stock(db: Session = Depends(get_db)):
    stock = db.query(models.Stock).all()
    return [
        {
            "sku": s.sku,
            "product_name": s.product_name,
            "quantity_on_hand": s.quantity_on_hand,
            "quantity_reserved": s.quantity_reserved,
            "available": s.quantity_on_hand - s.quantity_reserved,
        }
        for s in stock
    ]

@router.post("/purchase-orders")
def create_po(payload: POCreate, db: Session = Depends(get_db)):
    po = models.PurchaseOrder(
        po_code=generate_po_code(db),
        lead_id=payload.lead_id,
        supplier="Mixed",
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
            supplier=item.supplier or "Moorgen",
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

    old_status = po.status
    po.status = status

    if status == "ordered":
        po.ordered_at = datetime.utcnow()
        # Reserve Moorgen stock when ordered
        apply_reservations(po, db)

    elif status == "received":
        po.received_at = datetime.utcnow()
        # Release reservations and add to stock
        for item in po.line_items:
            if not item.sku:
                continue
            stock = db.query(models.Stock).filter(models.Stock.sku == item.sku).first()
            if stock:
                stock.quantity_on_hand += item.quantity_ordered - item.quantity_received
                stock.quantity_reserved = max(0, stock.quantity_reserved - item.quantity_ordered)
                stock.updated_at = datetime.utcnow()
            else:
                stock = models.Stock(
                    sku=item.sku,
                    product_name=item.product_name,
                    quantity_on_hand=item.quantity_ordered,
                    quantity_reserved=0,
                )
                db.add(stock)
            item.quantity_received = item.quantity_ordered

    elif status == "cancelled":
        # Release any reservations
        if old_status == "ordered":
            release_reservations(po, db)

    db.commit()
    return {"success": True}

@router.delete("/purchase-orders/{po_id}")
def delete_po(po_id: int, db: Session = Depends(get_db)):
    po = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.po_id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")
    # Release reservations if ordered
    if po.status == "ordered":
        release_reservations(po, db)
    # Delete line items first
    db.query(models.POLineItem).filter(models.POLineItem.po_id == po_id).delete()
    db.delete(po)
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

# ── Stock Assignments ─────────────────────────────────
class StockAssignmentCreate(BaseModel):
    sku: str
    lead_id: int
    quantity_assigned: int
    notes: Optional[str] = None

@router.get("/stock/assignments")
def get_stock_assignments(db: Session = Depends(get_db)):
    from sqlalchemy import text
    rows = db.execute(text("""
        SELECT sa.id, sa.sku, sa.lead_id, sa.quantity_assigned, sa.quantity_dispatched,
               sa.status, sa.notes, sa.created_at, sa.dispatched_at,
               l.client_name, l.project_name, l.lead_code,
               s.product_name
        FROM stock_assignments sa
        LEFT JOIN leads l ON l.lead_id = sa.lead_id
        LEFT JOIN stock s ON s.sku = sa.sku
        ORDER BY sa.created_at DESC
    """)).fetchall()
    return [dict(r._mapping) for r in rows]

@router.post("/stock/assign")
def assign_stock(payload: StockAssignmentCreate, db: Session = Depends(get_db)):
    # Check available stock
    stock = db.query(models.Stock).filter(models.Stock.sku == payload.sku).first()
    if not stock:
        raise HTTPException(status_code=404, detail="SKU not found in stock")
    available = stock.quantity_on_hand - stock.quantity_reserved
    if payload.quantity_assigned > available:
        raise HTTPException(status_code=400, detail=f"Only {available} units available")
    # Create assignment
    from sqlalchemy import text
    db.execute(text("""
        INSERT INTO stock_assignments (sku, lead_id, quantity_assigned, notes, status)
        VALUES (:sku, :lead_id, :qty, :notes, 'reserved')
    """), {"sku": payload.sku, "lead_id": payload.lead_id, "qty": payload.quantity_assigned, "notes": payload.notes})
    # Update reserved count
    stock.quantity_reserved += payload.quantity_assigned
    stock.updated_at = datetime.utcnow()
    db.commit()
    return {"success": True}

@router.patch("/stock/assignments/{assignment_id}/dispatch")
def dispatch_assignment(assignment_id: int, db: Session = Depends(get_db)):
    from sqlalchemy import text
    row = db.execute(text("SELECT * FROM stock_assignments WHERE id = :id"), {"id": assignment_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if row.status == "dispatched":
        raise HTTPException(status_code=400, detail="Already dispatched")
    qty = row.quantity_assigned - row.quantity_dispatched
    # Deduct from stock
    stock = db.query(models.Stock).filter(models.Stock.sku == row.sku).first()
    if stock:
        stock.quantity_on_hand = max(0, stock.quantity_on_hand - qty)
        stock.quantity_reserved = max(0, stock.quantity_reserved - row.quantity_assigned)
        stock.updated_at = datetime.utcnow()
    db.execute(text("""
        UPDATE stock_assignments 
        SET status='dispatched', quantity_dispatched=quantity_assigned, dispatched_at=NOW()
        WHERE id=:id
    """), {"id": assignment_id})
    db.commit()
    return {"success": True}

@router.delete("/stock/assignments/{assignment_id}")
def cancel_assignment(assignment_id: int, db: Session = Depends(get_db)):
    from sqlalchemy import text
    row = db.execute(text("SELECT * FROM stock_assignments WHERE id = :id"), {"id": assignment_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if row.status == "reserved":
        stock = db.query(models.Stock).filter(models.Stock.sku == row.sku).first()
        if stock:
            stock.quantity_reserved = max(0, stock.quantity_reserved - row.quantity_assigned)
            stock.updated_at = datetime.utcnow()
    db.execute(text("DELETE FROM stock_assignments WHERE id = :id"), {"id": assignment_id})
    db.commit()
    return {"success": True}

# ── PI Upload & Parse ─────────────────────────────────
from fastapi import UploadFile, File
import pdfplumber
import io
import re

def parse_pi_pdf(pdf_bytes: bytes) -> dict:
    """Extract PI number, date, and line items from a Moorgen PI PDF."""
    text = ""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"

    # Extract PI number
    pi_match = re.search(r'PI\s*#[:\s]*([A-Z0-9\-/\.]+)', text)
    pi_number = pi_match.group(1).strip() if pi_match else ""

    # Extract date
    date_match = re.search(r'Date[:\s]+([A-Za-z0-9\s\./,]+?)(?:\n|PI)', text)
    date_str = date_match.group(1).strip() if date_match else ""

    # Extract supplier (customer field tells us it's Reset or direct)
    supplier = "Moorgen"
    if "Reset Illuminat" in text:
        supplier = "Moorgen"

    # Extract total
    total_match = re.search(r'Total Amount[：:]\s*US\$?([\d,\.]+)', text)
    total_usd = float(total_match.group(1).replace(',', '')) if total_match else 0

    # Parse line items from the contract section (more reliable)
    # Look for the A-1 GOODS SOLD section
    items = []
    seen = set()

    # Pattern: row number, brand, module/sku, product name, unit, qty, price
    # Try contract format first: "1 moorgen SKU Product Name pcs qty price"
    contract_pattern = re.compile(
        r'^\s*(\d+)\s+moorgen\s+([A-Z0-9\-/\.]+)\s+(.+?)\s+pcs\s+([\d,\.]+)\s+([\d,\.]+)',
        re.MULTILINE | re.IGNORECASE
    )
    for m in contract_pattern.finditer(text):
        sku = m.group(2).strip()
        name = m.group(3).strip()
        qty = int(float(m.group(4).replace(',', '')))
        unit_cost = float(m.group(5).replace(',', ''))
        key = f"{sku}-{qty}"
        if key not in seen and sku and qty > 0 and unit_cost > 0:
            seen.add(key)
            items.append({
                "sku": sku,
                "product_name": name,
                "quantity_ordered": qty,
                "unit_cost": unit_cost,
                "line_total": round(qty * unit_cost, 2),
                "supplier": "Moorgen",
            })

    # Fallback: PI page format "1 moorgen ProductName SKU PCS US$price qty US$total"
    if not items:
        pi_pattern = re.compile(
            r'^\s*(\d+)\s+moorgen\s+.{0,60}?\s+([A-Z][A-Z0-9\-/\.]{3,})\s+PCS\s+US\$([\d,\.]+)\s+(\d+)',
            re.MULTILINE | re.IGNORECASE
        )
        for m in pi_pattern.finditer(text):
            sku = m.group(2).strip()
            unit_cost = float(m.group(3).replace(',', ''))
            qty = int(m.group(4))
            key = f"{sku}-{qty}"
            if key not in seen and qty > 0 and unit_cost > 0:
                seen.add(key)
                items.append({
                    "sku": sku,
                    "product_name": sku,
                    "quantity_ordered": qty,
                    "unit_cost": unit_cost,
                    "line_total": round(qty * unit_cost, 2),
                    "supplier": "Moorgen",
                })

    return {
        "pi_number": pi_number,
        "date": date_str,
        "supplier": supplier,
        "total_usd": total_usd,
        "items": items,
        "raw_text_preview": text[:500],
    }

@router.post("/parse-pi")
async def parse_pi(file: UploadFile = File(...)):
    contents = await file.read()
    try:
        result = parse_pi_pdf(contents)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {str(e)}")
