from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from decimal import Decimal
from typing import Optional, List
from datetime import datetime
from app.database import get_db
from app import models
import jwt, os

router = APIRouter()

JWT_SECRET = os.getenv("JWT_SECRET", "moorgen_secret_2526_key")
JWT_ALGO = "HS256"

def get_role_from_header(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        return payload.get("role")
    except Exception:
        return None

# ── Schemas ──────────────────────────────────────────
class POLineItemCreate(BaseModel):
    sku: str
    product_name: str
    quantity_ordered: int
    unit_cost: Decimal
    line_total: Decimal
    supplier: Optional[str] = "Moorgen"

class POCreate(BaseModel):
    lead_id: Optional[int] = None
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
def inventory_dashboard(db: Session = Depends(get_db), role: str = Depends(get_role_from_header)):
    hide_pricing = (role == "procurement")
    pos = db.query(models.PurchaseOrder).order_by(models.PurchaseOrder.created_at.desc()).all()
    stock = db.query(models.Stock).all()

    po_list = []
    for po in pos:
        lead = db.query(models.Lead).filter(models.Lead.lead_id == po.lead_id).first()
        total = sum(float(i.line_total) for i in po.line_items)
        dealer = db.query(models.Dealer).filter(models.Dealer.dealer_id == lead.dealer_id).first() if lead and lead.dealer_id else None

        # Collect distinct projects across this PO's line items (falls back to the PO-level lead if an item has no override)
        item_lead_ids = {i.lead_id for i in po.line_items if i.lead_id} or ({po.lead_id} if po.lead_id else set())
        item_leads = db.query(models.Lead).filter(models.Lead.lead_id.in_(item_lead_ids)).all() if item_lead_ids else []
        projects = [{"lead_id": l.lead_id, "client_name": l.client_name, "project_name": l.project_name} for l in item_leads]

        po_list.append({
            "po_id": po.po_id,
            "po_code": po.po_code,
            "lead_id": po.lead_id,
            "client_name": lead.client_name if lead else None,
            "project_name": lead.project_name if lead else None,
            "city": lead.city if lead else None,
            "dealer_name": dealer.firm_name if dealer else None,
            "projects": projects,
            "status": po.status,
            "total": (None if hide_pricing else total),
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
                    "lead_id": i.lead_id,
                    "allocation_type": i.allocation_type or "stock",
                    **({} if hide_pricing else {"unit_cost": float(i.unit_cost), "line_total": float(i.line_total)}),
                    "supplier": i.supplier or "Moorgen",
                }
                for i in po.line_items
            ]
        })

    # Build incoming map from ordered/in_transit POs
    incoming_map = {}
    for po in pos:
        if po.status in ("ordered", "in_transit"):
            for item in po.line_items:
                if item.sku:
                    incoming_map[item.sku] = incoming_map.get(item.sku, 0) + item.quantity_ordered

    # Build source PI map
    from sqlalchemy import text as sqla_text
    sources = db.execute(sqla_text("""
        SELECT DISTINCT ON (pli.sku) pli.sku, po.po_code
        FROM po_line_items pli
        JOIN purchase_orders po ON po.po_id = pli.po_id
        WHERE po.status = 'received' AND pli.sku IS NOT NULL
        ORDER BY pli.sku, po.received_at DESC NULLS LAST, po.created_at DESC
    """)).fetchall()
    source_map = {r.sku: r.po_code for r in sources}
    stock_list = []
    for s in stock:
        stock_list.append({
            "id": s.id,
            "sku": s.sku,
            "product_name": s.product_name,
            "quantity_on_hand": s.quantity_on_hand,
            "quantity_reserved": s.quantity_reserved,
            "quantity_incoming": incoming_map.get(s.sku, 0),
            "available": s.quantity_on_hand - s.quantity_reserved,
            "source_po": source_map.get(s.sku, ""),
        })
    # Add SKUs that are incoming but not yet in stock
    existing_skus = {s.sku for s in stock}
    for sku, qty in incoming_map.items():
        if sku not in existing_skus:
            # Find product name from PO line items
            name = sku
            for po in pos:
                for item in po.line_items:
                    if item.sku == sku:
                        name = item.product_name
                        break
            stock_list.append({
                "id": None,
                "sku": sku,
                "product_name": name,
                "quantity_on_hand": 0,
                "quantity_reserved": 0,
                "quantity_incoming": qty,
                "available": 0,
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
    from sqlalchemy import text
    # Build incoming map
    incoming = db.execute(text("""
        SELECT pli.sku, SUM(pli.quantity_ordered) as qty, STRING_AGG(po.po_code, ', ') as po_codes
        FROM purchase_orders po
        JOIN po_line_items pli ON pli.po_id = po.po_id
        WHERE po.status IN ('ordered', 'in_transit') AND pli.sku IS NOT NULL
        GROUP BY pli.sku
    """)).fetchall()
    incoming_map = {r.sku: {'qty': int(r.qty), 'po_codes': r.po_codes} for r in incoming}
    
    # Build source PI map (most recent received PO per SKU)
    sources = db.execute(text("""
        SELECT DISTINCT ON (pli.sku) pli.sku, po.po_code
        FROM po_line_items pli
        JOIN purchase_orders po ON po.po_id = pli.po_id
        WHERE po.status = 'received' AND pli.sku IS NOT NULL
        ORDER BY pli.sku, po.received_at DESC NULLS LAST, po.created_at DESC
    """)).fetchall()
    source_map = {r.sku: r.po_code for r in sources}
    
    stock = db.query(models.Stock).all()
    return [
        {
            "sku": s.sku,
            "product_name": s.product_name,
            "quantity_on_hand": s.quantity_on_hand,
            "quantity_reserved": s.quantity_reserved,
            "quantity_incoming": incoming_map.get(s.sku, {}).get('qty', 0),
            "incoming_pos": incoming_map.get(s.sku, {}).get('po_codes', ''),
            "source_po": source_map.get(s.sku, ''),
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

    if status in ("ordered", "in_transit"):
        # Reverse stock if coming back from received
        if old_status == "received":
            for item in po.line_items:
                if not item.sku:
                    continue
                stock = db.query(models.Stock).filter(models.Stock.sku == item.sku).first()
                if stock:
                    stock.quantity_on_hand = max(0, stock.quantity_on_hand - item.quantity_received)
                    stock.updated_at = datetime.utcnow()
                item.quantity_received = 0
            po.received_at = None
        if status == "ordered":
            po.ordered_at = po.ordered_at or datetime.utcnow()
        elif status == "in_transit":
            po.ordered_at = po.ordered_at or datetime.utcnow()
            apply_reservations(po, db)
    elif status == "in_transit":
        po.ordered_at = po.ordered_at or datetime.utcnow()
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

# ── Stock Movements (samples / small orders / corrections, logged with a reason) ──
STOCK_MOVEMENT_REASONS = {"sample", "small_order", "correction", "damage", "other"}

class StockMovementCreate(BaseModel):
    sku: str
    quantity_delta: int  # negative = stock taken out (e.g. samples given away), positive = stock added back
    reason: str          # one of: sample, small_order, correction, damage, other
    notes: Optional[str] = None

@router.post("/stock/log")
def log_stock_movement(payload: StockMovementCreate, db: Session = Depends(get_db)):
    reason = payload.reason if payload.reason in STOCK_MOVEMENT_REASONS else "other"
    stock = db.query(models.Stock).filter(models.Stock.sku == payload.sku).first()
    if not stock:
        raise HTTPException(status_code=404, detail="SKU not found in stock")

    new_qty = stock.quantity_on_hand + payload.quantity_delta
    if new_qty < 0:
        raise HTTPException(status_code=400, detail=f"Only {stock.quantity_on_hand} units on hand — cannot log a deduction of {-payload.quantity_delta}")

    stock.quantity_on_hand = new_qty
    stock.updated_at = datetime.utcnow()
    db.add(models.StockMovement(
        sku=payload.sku,
        quantity_delta=payload.quantity_delta,
        reason=reason,
        notes=payload.notes,
    ))
    db.commit()
    return {"success": True, "quantity_on_hand": stock.quantity_on_hand}

@router.get("/stock/movements/{sku}")
def get_stock_movements(sku: str, db: Session = Depends(get_db)):
    rows = (
        db.query(models.StockMovement)
        .filter(models.StockMovement.sku == sku)
        .order_by(models.StockMovement.created_at.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": r.id,
            "quantity_delta": r.quantity_delta,
            "reason": r.reason,
            "notes": r.notes,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]

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
    # Parse line items line-by-line
    # Product name can appear: inline on same row, on next row, or as standalone header
    # "1 moorgen TB8317ZC27 pcs 102.65 5 US$513.24"       <- no name
    # "2 moorgen MB8956 Two-channel Smart Dimming Panel pcs 19.41 5"  <- name inline
    # "Three-channel Smart Panel"                          <- standalone header
    # "6 moorgen TB8913Z pcs 12.94 15 US$194.12"          <- gets name from header above
    items = []
    text_lines = text.split("\n")
    last_name = ""

    item_re = re.compile(
        r'^\s*(\d+)\s+moorgen\s+([A-Z0-9][A-Z0-9\-/\.]*)\s*(.*?)pcs\s+([\d\.]+)\s+([\d,]+)',
        re.IGNORECASE
    )
    header_re = re.compile(
        r'^([A-Z][a-zA-Z\s\-]{8,50})$'
    )

    for i, line in enumerate(text_lines):
        line = line.strip()
        # Check if standalone header line
        hm = header_re.match(line)
        if hm and "moorgen" not in line.lower() and "total" not in line.lower() and "unit price" not in line.lower() and "no." not in line.lower() and "(usd)" not in line.lower() and "limited" not in line.lower() and "private" not in line.lower() and "seller" not in line.lower() and "buyer" not in line.lower() and "goods sold" not in line.lower() and "contract" not in line.lower() and "zhejiang" not in line.lower():
            last_name = hm.group(1).strip()
            continue
        # Check if item row
        m = item_re.match(line)
        if m:
            sku = m.group(2).strip()
            name_part = m.group(3).strip()
            unit_cost = float(m.group(4).replace(',', ''))
            qty = int(m.group(5).replace(',', ''))
            # Check next line for product name if not inline
            if len(name_part) > 3:
                last_name = name_part
                product_name = name_part
            else:
                # Look ahead at next line
                next_line = text_lines[i+1].strip() if i+1 < len(text_lines) else ""
                nm = item_re.match(next_line)
                if not nm and len(next_line) > 3 and not next_line.startswith("(") and "moorgen" not in next_line.lower() and "pcs" not in next_line.lower() and "total" not in next_line.lower() and "unit price" not in next_line.lower() and "(usd)" not in next_line.lower() and "amount" not in next_line.lower() and "no." not in next_line.lower() and next_line[0].isupper():
                    last_name = next_line
                    product_name = next_line
                else:
                    product_name = last_name if last_name else sku
                    # Sanity check - if name looks like boilerplate, use SKU
                    boilerplate = ["bank", "seller", "buyer", "contract", "payment", "address", "details", "illuminat", "zhejiang", "moorgen", "changluo"]
                    if any(b in product_name.lower() for b in boilerplate):
                        product_name = sku
                        last_name = ""
            if sku and qty > 0 and unit_cost > 0:
                items.append({
                    "sku": sku,
                    "product_name": product_name,
                    "quantity_ordered": qty,
                    "unit_cost": unit_cost,
                    "line_total": round(qty * unit_cost, 2),
                    "supplier": "Moorgen",
                })

    # Fallback: PI page 1 format
    if not items:
        pi_pattern = re.compile(
            r'^\s*\d+\s+moorgen\s+.{5,80}?\s+([A-Z][A-Z0-9\-/\.]{3,})\s+PCS\s+US\$([\d,\.]+)\s+([\d,]+)',
            re.MULTILINE | re.IGNORECASE
        )
        for m in pi_pattern.finditer(text):
            sku = m.group(1).strip()
            unit_cost = float(m.group(2).replace(',', ''))
            qty = int(m.group(3).replace(',', ''))
            if qty > 0 and unit_cost > 0:
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

# ── Project Needs ─────────────────────────────────────
@router.get("/project-needs")
def get_project_needs(db: Session = Depends(get_db)):
    from sqlalchemy import text

    # Get all won leads (displayed alphabetically by client)
    leads = db.execute(text("""
        SELECT l.lead_id, l.client_name, l.project_name, l.lead_code, l.city
        FROM leads l
        WHERE l.status = 'won'
        ORDER BY l.client_name
    """)).fetchall()
    lead_map = {l.lead_id: l for l in leads}

    # Stock map
    stock_rows = db.execute(text("SELECT sku, quantity_on_hand, quantity_reserved FROM stock")).fetchall()
    stock_map = {r.sku: {'on_hand': r.quantity_on_hand, 'reserved': r.quantity_reserved, 'available': r.quantity_on_hand - r.quantity_reserved} for r in stock_rows}
    # LightForge stock counts as an additional available pool for covering project needs
    lf_rows = db.execute(text("SELECT sku, SUM(quantity) as qty FROM lf_stock GROUP BY sku")).fetchall()
    lf_map = {r.sku: int(r.qty) for r in lf_rows}

    # Incoming map (ordered + in_transit POs)
    incoming_rows = db.execute(text("""
        SELECT pli.sku, SUM(pli.quantity_ordered) as qty
        FROM purchase_orders po
        JOIN po_line_items pli ON pli.po_id = po.po_id
        WHERE po.status IN ('ordered', 'in_transit')
        AND pli.sku IS NOT NULL AND pli.sku != ''
        GROUP BY pli.sku
    """)).fetchall()
    incoming_map = {r.sku: int(r.qty) for r in incoming_rows}

    # Stock assignments
    assignments = db.execute(text("""
        SELECT sa.sku, sa.lead_id, sa.quantity_assigned, sa.status
        FROM stock_assignments sa WHERE sa.status IN ('reserved', 'dispatched')
    """)).fetchall()
    assignment_map = {}  # reserved
    dispatched_map = {}  # already dispatched to this project
    for a in assignments:
        key = (a.sku, a.lead_id)
        if a.status == 'reserved':
            assignment_map[key] = assignment_map.get(key, 0) + a.quantity_assigned
        else:
            dispatched_map[key] = dispatched_map.get(key, 0) + a.quantity_assigned

    # ── Pass 1: collect each won project's non-OEM SKU demand ──
    lead_items = {}      # lead_id -> [{sku, product_name, needed}]
    lead_oem_items = {}  # lead_id -> [{sku, product_name, needed}]
    sku_demand = {}      # sku -> [lead_id, ...] (every won project that needs this SKU)

    for lead in leads:
        items = db.execute(text("""
            SELECT
                CASE
                    WHEN bli.product_sku LIKE 'ARCH-%%' THEN SUBSTRING(bli.product_sku, 6)
                    WHEN bli.product_sku LIKE 'DEC-%%' THEN SUBSTRING(bli.product_sku, 5)
                    ELSE bli.product_sku
                END as clean_sku,
                bli.product_name,
                SUM(bli.quantity) as total_qty
            FROM boqs b
            JOIN boq_line_items bli ON bli.boq_id = b.boq_id
            WHERE b.lead_id = :lead_id
            AND bli.product_sku IS NOT NULL AND bli.product_sku != ''
            AND bli.product_sku NOT LIKE 'OEM%%'
            GROUP BY clean_sku, bli.product_name
            ORDER BY clean_sku
        """), {"lead_id": lead.lead_id}).fetchall()

        # Also get OEM items for this project
        oem_items = db.execute(text("""
            SELECT bli.product_sku, bli.product_name, SUM(bli.quantity) as total_qty
            FROM boqs b
            JOIN boq_line_items bli ON bli.boq_id = b.boq_id
            WHERE b.lead_id = :lead_id
            AND bli.product_sku IS NOT NULL
            AND bli.product_sku LIKE 'OEM%%'
            GROUP BY bli.product_sku, bli.product_name
            ORDER BY bli.product_sku
        """), {"lead_id": lead.lead_id}).fetchall()

        if not items and not oem_items:
            continue  # Skip projects with no trackable SKUs

        lead_items[lead.lead_id] = [
            {'sku': it.clean_sku, 'product_name': it.product_name, 'needed': int(it.total_qty)}
            for it in items
        ]
        lead_oem_items[lead.lead_id] = [
            {'sku': o.product_sku, 'product_name': o.product_name, 'needed': int(o.total_qty)}
            for o in oem_items
        ]
        for it in items:
            sku_demand.setdefault(it.clean_sku, []).append(lead.lead_id)

    # ── Pass 2: for every contested SKU, allocate the shared stock/incoming pools
    # across competing won projects in priority order, instead of letting each
    # project check raw availability in isolation (which makes the same units
    # look "available" to several projects at once).
    #
    # Priority: projects that already hold a reservation for the SKU go first
    # (they staked their claim), then the rest in lead_id order (a stable proxy
    # for the order projects were won, since there's no won_date column).
    #
    # allocation[(sku, lead_id)] -> claim from on-hand pool, claim from incoming,
    # and how much of this project's need is "blocked" — i.e. stock that exists
    # but has already been claimed by a higher-priority project.
    allocation = {}

    for sku, lead_ids in sku_demand.items():
        stock = stock_map.get(sku, {'on_hand': 0, 'reserved': 0, 'available': 0})
        lf_available = lf_map.get(sku, 0)
        pool = stock['available'] + lf_available
        incoming = incoming_map.get(sku, 0)

        competitors = []
        for lid in lead_ids:
            needed = next(it['needed'] for it in lead_items[lid] if it['sku'] == sku)
            already_assigned = assignment_map.get((sku, lid), 0)
            already_dispatched = dispatched_map.get((sku, lid), 0)
            remaining = max(0, needed - already_assigned - already_dispatched)
            competitors.append({
                'lead_id': lid,
                'remaining': remaining,
                'has_reservation': already_assigned > 0,
            })

        ordered = sorted(competitors, key=lambda c: (0 if c['has_reservation'] else 1, c['lead_id']))
        idx_of = {c['lead_id']: i for i, c in enumerate(ordered)}

        consumed_pool = 0
        consumed_incoming = 0
        log = []
        for c in ordered:
            avail_pool = max(0, pool - consumed_pool)
            claim_pool = min(c['remaining'], avail_pool)
            consumed_pool += claim_pool

            still_needed = c['remaining'] - claim_pool
            avail_incoming = max(0, incoming - consumed_incoming)
            claim_incoming = min(still_needed, avail_incoming)
            consumed_incoming += claim_incoming

            log.append({'lead_id': c['lead_id'], 'remaining': c['remaining'],
                        'claim_pool': claim_pool, 'claim_incoming': claim_incoming})

        for entry in log:
            isolated = min(entry['remaining'], pool + incoming)
            actual = entry['claim_pool'] + entry['claim_incoming']
            blocked_amount = max(0, isolated - actual)
            blocked_by = []
            if blocked_amount > 0:
                for other in log:
                    if other['lead_id'] == entry['lead_id']:
                        continue
                    if idx_of[other['lead_id']] < idx_of[entry['lead_id']] and (other['claim_pool'] + other['claim_incoming']) > 0:
                        other_lead = lead_map[other['lead_id']]
                        blocked_by.append({
                            'lead_id': other['lead_id'],
                            'client_name': other_lead.client_name,
                            'project_name': other_lead.project_name,
                            'qty': other['claim_pool'] + other['claim_incoming'],
                        })
            allocation[(sku, entry['lead_id'])] = {
                'claim_pool': entry['claim_pool'],
                'claim_incoming': entry['claim_incoming'],
                'blocked_amount': blocked_amount,
                'blocked_by': blocked_by,
            }

    # ── Pass 3: assemble each project's view using the allocation outcome ──
    result = []
    for lead in leads:
        if lead.lead_id not in lead_items:
            continue

        items = lead_items[lead.lead_id]
        oem_items = lead_oem_items[lead.lead_id]

        needs = []
        fully_covered = 0
        incoming_covered = 0
        needs_ordering = 0
        blocked_count = 0

        for item in items:
            sku = item['sku']
            needed = item['needed']
            stock = stock_map.get(sku, {'on_hand': 0, 'reserved': 0, 'available': 0})
            lf_available = lf_map.get(sku, 0)
            already_assigned = assignment_map.get((sku, lead.lead_id), 0)
            already_dispatched = dispatched_map.get((sku, lead.lead_id), 0)
            incoming = incoming_map.get(sku, 0)

            # Dispatched items count as fully covered
            if already_dispatched >= needed:
                needs.append({'sku': sku, 'product_name': item['product_name'], 'needed': needed,
                              'in_stock': stock['on_hand'], 'available': stock['available'], 'lf_available': lf_available,
                              'incoming': incoming, 'assigned': already_assigned,
                              'can_cover': needed, 'gap': 0, 'status': 'covered'})
                fully_covered += 1
                continue

            alloc = allocation.get((sku, lead.lead_id), {'claim_pool': 0, 'claim_incoming': 0, 'blocked_amount': 0, 'blocked_by': []})
            can_cover_from_pools = alloc['claim_pool'] + alloc['claim_incoming']
            can_cover = already_assigned + already_dispatched + can_cover_from_pools
            gap = max(0, needed - can_cover)

            if alloc['blocked_amount'] > 0:
                status = 'blocked'
                blocked_count += 1
            elif gap == 0:
                if (already_assigned + already_dispatched + alloc['claim_pool']) >= needed:
                    status = 'covered'
                    fully_covered += 1
                else:
                    status = 'incoming'
                    incoming_covered += 1
            elif can_cover > 0:
                status = 'partial'
                needs_ordering += 1
            else:
                status = 'needed'
                needs_ordering += 1

            entry = {
                'sku': sku,
                'product_name': item['product_name'],
                'needed': needed,
                'in_stock': stock['on_hand'],
                'available': stock['available'],
                'lf_available': lf_available,
                'incoming': incoming,
                'assigned': already_assigned,
                'can_cover': can_cover,
                'gap': gap,
                'status': status,
            }
            if alloc['blocked_amount'] > 0:
                entry['blocked_qty'] = alloc['blocked_amount']
                entry['blocked_by'] = alloc['blocked_by']
            needs.append(entry)

        # Add OEM items (sourced from Reset)
        oem_needs = []
        oem_needed = 0
        for oem in oem_items:
            oem_needs.append({
                'sku': oem['sku'],
                'product_name': oem['product_name'],
                'needed': oem['needed'],
                'in_stock': 0,
                'available': 0,
                'incoming': 0,
                'assigned': 0,
                'can_cover': 0,
                'gap': oem['needed'],
                'status': 'reset',
                'supplier': 'Reset',
            })
            oem_needed += 1

        result.append({
            'lead_id': lead.lead_id,
            'client_name': lead.client_name,
            'project_name': lead.project_name,
            'lead_code': lead.lead_code,
            'city': lead.city,
            'total_skus': len(needs) + oem_needed,
            'fully_covered': fully_covered,
            'incoming_covered': incoming_covered,
            'needs_ordering': needs_ordering,
            'blocked': blocked_count,
            'oem_skus': oem_needed,
            'items': needs + oem_needs,
        })
    return result

@router.patch("/purchase-orders/{po_id}/assign")
def assign_po_to_lead(po_id: int, lead_id: int, db: Session = Depends(get_db)):
    po = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.po_id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")
    po.lead_id = lead_id
    db.commit()
    return {"success": True}

# ── LightForge Stock ──────────────────────────────────
@router.get("/lf-stock")
def get_lf_stock(db: Session = Depends(get_db)):
    from sqlalchemy import text
    rows = db.execute(text("""
        SELECT 
            lf.id, lf.sku, 
            COALESCE(p.name, lf.product_name) as product_name,
            lf.quantity, lf.stock_type, lf.location, lf.notes
        FROM lf_stock lf
        LEFT JOIN products p ON p.sku = lf.sku
        ORDER BY lf.stock_type, lf.sku
    """)).fetchall()
    return [dict(r._mapping) for r in rows]

@router.patch("/lf-stock/{item_id}/type")
def update_lf_stock_type(item_id: int, stock_type: str, db: Session = Depends(get_db)):
    from sqlalchemy import text
    db.execute(text("UPDATE lf_stock SET stock_type = :t WHERE id = :id"), {"t": stock_type, "id": item_id})
    db.commit()
    return {"success": True}

class LFDispatch(BaseModel):
    item_id: int
    quantity: int
    lead_id: Optional[int] = None
    notes: Optional[str] = None

@router.post("/lf-stock/dispatch")
def dispatch_lf_stock(payload: LFDispatch, db: Session = Depends(get_db)):
    from sqlalchemy import text
    row = db.execute(text("SELECT * FROM lf_stock WHERE id = :id"), {"id": payload.item_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="LF stock item not found")
    if payload.quantity > row.quantity:
        raise HTTPException(status_code=400, detail=f"Only {row.quantity} units available")
    new_qty = row.quantity - payload.quantity
    if new_qty == 0:
        db.execute(text("DELETE FROM lf_stock WHERE id = :id"), {"id": payload.item_id})
    else:
        db.execute(text("UPDATE lf_stock SET quantity = :q WHERE id = :id"), {"q": new_qty, "id": payload.item_id})
    db.commit()
    return {"success": True, "remaining": new_qty}

# ── Partial Receipt ───────────────────────────────────
class PartialReceiptItem(BaseModel):
    line_item_id: int
    quantity_received: int

class PartialReceipt(BaseModel):
    items: List[PartialReceiptItem]

@router.post("/purchase-orders/{po_id}/receive")
def partial_receive(po_id: int, payload: PartialReceipt, db: Session = Depends(get_db)):
    po = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.po_id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")
    
    for receipt in payload.items:
        item = db.query(models.POLineItem).filter(models.POLineItem.id == receipt.line_item_id).first()
        if not item:
            continue
        additional = receipt.quantity_received - item.quantity_received
        if additional <= 0:
            continue
        # Update stock
        stock = db.query(models.Stock).filter(models.Stock.sku == item.sku).first()
        if stock:
            stock.quantity_on_hand += additional
            stock.updated_at = datetime.utcnow()
        else:
            stock = models.Stock(
                sku=item.sku,
                product_name=item.product_name,
                quantity_on_hand=additional,
                quantity_reserved=0,
            )
            db.add(stock)
        item.quantity_received = receipt.quantity_received

    # Check if fully received
    all_received = all(i.quantity_received >= i.quantity_ordered for i in po.line_items)
    if all_received:
        po.status = "received"
        po.received_at = datetime.utcnow()
    else:
        po.status = "in_transit"  # partial receipt = still in transit
    
    db.commit()
    return {"success": True, "fully_received": all_received}

@router.delete("/stock/{sku}")
def delete_stock(sku: str, db: Session = Depends(get_db)):
    stock = db.query(models.Stock).filter(models.Stock.sku == sku).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock item not found")
    db.delete(stock)
    db.commit()
    return {"success": True}

@router.patch("/po-line-items/{item_id}/project")
def assign_line_item_project(item_id: int, lead_id: Optional[int] = None, allocation_type: Optional[str] = None, db: Session = Depends(get_db)):
    item = db.query(models.POLineItem).filter(models.POLineItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Line item not found")

    if allocation_type == "project":
        item.allocation_type = "project"
        item.lead_id = lead_id
    elif allocation_type == "sample":
        item.allocation_type = "sample"
        item.lead_id = None
    elif allocation_type == "stock":
        item.allocation_type = "stock"
        item.lead_id = None
    elif lead_id is not None:
        # backward-compat: assigning a lead_id directly implies project allocation
        item.allocation_type = "project"
        item.lead_id = lead_id

    db.commit()
    return {"success": True}


@router.post("/purchase-orders/{po_id}/apply-project-to-all")
def apply_project_to_all_items(po_id: int, lead_id: int, db: Session = Depends(get_db)):
    """Bulk-assign a project to every line item in a PO that's still unassigned (stock).
    Items already marked sample or tied to a different project are left untouched."""
    items = db.query(models.POLineItem).filter(
        models.POLineItem.po_id == po_id,
        models.POLineItem.allocation_type == "stock"
    ).all()
    for item in items:
        item.allocation_type = "project"
        item.lead_id = lead_id
    db.commit()
    return {"updated": len(items)}


@router.patch("/purchase-orders/{po_id}/notes")
def update_po_notes(po_id: int, notes: str, db: Session = Depends(get_db)):
    po = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.po_id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")
    po.notes = notes
    db.commit()
    return {"success": True}
