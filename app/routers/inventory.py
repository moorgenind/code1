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

    # Build incoming map from ordered/in_transit POs
    incoming_map = {}
    for po in pos:
        if po.status in ("ordered", "in_transit"):
            for item in po.line_items:
                if item.sku:
                    incoming_map[item.sku] = incoming_map.get(item.sku, 0) + item.quantity_ordered

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

    elif status in ("ordered", "in_transit"):
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

    # Get all won leads
    leads = db.execute(text("""
        SELECT l.lead_id, l.client_name, l.project_name, l.lead_code, l.city
        FROM leads l
        WHERE l.status = 'won'
        ORDER BY l.client_name
    """)).fetchall()

    # Stock map
    stock_rows = db.execute(text("SELECT sku, quantity_on_hand, quantity_reserved FROM stock")).fetchall()
    stock_map = {r.sku: {'on_hand': r.quantity_on_hand, 'reserved': r.quantity_reserved, 'available': r.quantity_on_hand - r.quantity_reserved} for r in stock_rows}

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

    result = []
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

        if not items:
            continue  # Skip projects with no trackable SKUs

        needs = []
        fully_covered = 0
        incoming_covered = 0
        needs_ordering = 0

        for item in items:
            sku = item.clean_sku
            needed = int(item.total_qty)
            stock = stock_map.get(sku, {'on_hand': 0, 'reserved': 0, 'available': 0})
            already_assigned = assignment_map.get((sku, lead.lead_id), 0)
            already_dispatched = dispatched_map.get((sku, lead.lead_id), 0)
            available = stock['available'] + already_assigned
            # Dispatched items count as fully covered
            if already_dispatched >= needed:
                needs.append({'sku': sku, 'product_name': item.product_name, 'needed': needed, 'in_stock': stock['on_hand'], 'available': stock['available'], 'incoming': incoming_map.get(sku,0), 'assigned': already_assigned, 'can_cover': needed, 'gap': 0, 'status': 'covered'})
                fully_covered += 1
                continue
            incoming = incoming_map.get(sku, 0)

            can_cover_stock = min(needed, available)
            remaining_after_stock = max(0, needed - can_cover_stock)
            can_cover_incoming = min(remaining_after_stock, incoming)
            gap = max(0, needed - can_cover_stock - can_cover_incoming)

            if gap == 0 and can_cover_stock >= needed:
                status = 'covered'
                fully_covered += 1
            elif gap == 0 and can_cover_incoming > 0:
                status = 'incoming'
                incoming_covered += 1
            elif can_cover_stock > 0 or can_cover_incoming > 0:
                status = 'partial'
                needs_ordering += 1
            else:
                status = 'needed'
                needs_ordering += 1

            needs.append({
                'sku': sku,
                'product_name': item.product_name,
                'needed': needed,
                'in_stock': stock['on_hand'],
                'available': stock['available'],
                'incoming': incoming,
                'assigned': already_assigned,
                'can_cover': can_cover_stock + can_cover_incoming,
                'gap': gap,
                'status': status,
            })

        result.append({
            'lead_id': lead.lead_id,
            'client_name': lead.client_name,
            'project_name': lead.project_name,
            'lead_code': lead.lead_code,
            'city': lead.city,
            'total_skus': len(needs),
            'fully_covered': fully_covered,
            'incoming_covered': incoming_covered,
            'needs_ordering': needs_ordering,
            'items': needs,
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
