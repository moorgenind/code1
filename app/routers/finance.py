from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from decimal import Decimal
from typing import Optional, List
from datetime import date
from app.database import get_db
from app import models

router = APIRouter()

# ── Schemas ──────────────────────────────────────────

class InvoiceLineItemCreate(BaseModel):
    sku: Optional[str] = None
    product_name: Optional[str] = None
    quantity: int
    unit_price: Decimal
    discount_pct: Optional[Decimal] = Decimal("0")
    line_total: Decimal

class InvoiceCreate(BaseModel):
    lead_id: int
    boq_id: Optional[int] = None
    invoice_amount: Decimal
    pricing_tier: Optional[str] = "client"
    discount_pct: Optional[Decimal] = Decimal("0")
    subtotal: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    gst_amount: Optional[Decimal] = None
    notes: Optional[str] = None
    line_items: Optional[List[InvoiceLineItemCreate]] = []
    invoice_from: Optional[str] = "MIPL"       # MIPL or LightForge
    invoice_to: Optional[str] = "client"        # client / lightforge / dealer
    invoice_to_name: Optional[str] = None       # name of recipient

class PaymentCreate(BaseModel):
    payment_type: str
    amount: Decimal
    payment_date: date
    payment_mode: Optional[str] = None
    reference: Optional[str] = None
    notes: Optional[str] = None

# ── Helpers ───────────────────────────────────────────

def generate_invoice_code(db: Session, entity: str = "MIPL") -> str:
    prefix = "INV" if entity == "MIPL" else "LF"
    count = db.query(models.Invoice).filter(models.Invoice.invoice_from == entity).count()
    return f"{prefix}-2627-{str(count + 1).zfill(3)}"

def invoice_summary(inv, lead):
    paid = sum(float(p.amount) for p in inv.payments)
    outstanding = float(inv.invoice_amount) - paid
    return {
        "invoice_id": inv.invoice_id,
        "invoice_code": inv.invoice_code,
        "lead_id": inv.lead_id,
        "client_name": lead.client_name if lead else None,
        "project_name": lead.project_name if lead else None,
        "lead_channel": lead.channel if lead else None,
        "lead_dealer_id": lead.dealer_id if lead else None,
        "invoice_amount": float(inv.invoice_amount),
        "paid": paid,
        "outstanding": outstanding,
        "status": inv.status,
        "invoice_from": inv.invoice_from or "MIPL",
        "invoice_to": inv.invoice_to or "client",
        "invoice_to_name": inv.invoice_to_name,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
        "payments": [
            {
                "payment_id": p.payment_id,
                "payment_type": p.payment_type,
                "amount": float(p.amount),
                "payment_date": p.payment_date.isoformat() if p.payment_date else None,
                "payment_mode": p.payment_mode,
                "reference": p.reference,
            }
            for p in inv.payments
        ]
    }

# ── Routes ────────────────────────────────────────────

@router.get("/dashboard")
def finance_dashboard(db: Session = Depends(get_db)):
    invoices = db.query(models.Invoice).all()
    payments = db.query(models.Payment).all()

    def entity_summary(entity_invoices):
        total_invoiced = sum(float(i.invoice_amount) for i in entity_invoices)
        entity_payments = [p for i in entity_invoices for p in i.payments]
        total_collected = sum(float(p.amount) for p in entity_payments)
        return {
            "total_invoiced": total_invoiced,
            "total_collected": total_collected,
            "total_outstanding": total_invoiced - total_collected,
            "advance_collected": sum(float(p.amount) for p in entity_payments if p.payment_type == 'advance'),
            "balance_collected": sum(float(p.amount) for p in entity_payments if p.payment_type == 'balance'),
            "invoice_count": len(entity_invoices),
        }

    mipl_invoices = [i for i in invoices if (i.invoice_from or 'MIPL') == 'MIPL']
    lf_invoices = [i for i in invoices if (i.invoice_from or 'MIPL') == 'LightForge']

    invoice_summaries = []
    for inv in invoices:
        lead = db.query(models.Lead).filter(models.Lead.lead_id == inv.lead_id).first()
        invoice_summaries.append(invoice_summary(inv, lead))

    return {
        "summary": entity_summary(invoices),
        "mipl_summary": entity_summary(mipl_invoices),
        "lf_summary": entity_summary(lf_invoices),
        "invoices": sorted(invoice_summaries, key=lambda x: x["outstanding"], reverse=True)
    }

@router.post("/invoices")
def create_invoice(payload: InvoiceCreate, db: Session = Depends(get_db)):
    invoice = models.Invoice(
        invoice_code=generate_invoice_code(db, payload.invoice_from or "MIPL"),
        lead_id=payload.lead_id,
        boq_id=payload.boq_id,
        invoice_amount=payload.invoice_amount,
        pricing_tier=payload.pricing_tier,
        discount_pct=payload.discount_pct,
        subtotal=payload.subtotal,
        discount_amount=payload.discount_amount,
        gst_amount=payload.gst_amount,
        notes=payload.notes,
        invoice_from=payload.invoice_from or "MIPL",
        invoice_to=payload.invoice_to or "client",
        invoice_to_name=payload.invoice_to_name,
    )
    db.add(invoice)
    db.flush()
    for item in payload.line_items:
        li = models.InvoiceLineItem(
            invoice_id=invoice.invoice_id,
            sku=item.sku,
            product_name=item.product_name,
            quantity=item.quantity,
            unit_price=item.unit_price,
            discount_pct=item.discount_pct,
            line_total=item.line_total,
        )
        db.add(li)
    db.commit()
    db.refresh(invoice)
    return {"invoice_id": invoice.invoice_id, "invoice_code": invoice.invoice_code}

@router.get("/invoices")
def list_invoices(db: Session = Depends(get_db)):
    invoices = db.query(models.Invoice).order_by(models.Invoice.created_at.desc()).all()
    result = []
    for inv in invoices:
        lead = db.query(models.Lead).filter(models.Lead.lead_id == inv.lead_id).first()
        result.append(invoice_summary(inv, lead))
    return result

@router.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(models.Invoice).filter(models.Invoice.invoice_id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    lead = db.query(models.Lead).filter(models.Lead.lead_id == invoice.lead_id).first()
    paid = sum(float(p.amount or 0) for p in invoice.payments)
    return {
        "invoice_id": invoice.invoice_id,
        "invoice_code": invoice.invoice_code,
        "lead_id": invoice.lead_id,
        "client_name": lead.client_name if lead else None,
        "project_name": lead.project_name if lead else None,
        "invoice_amount": float(invoice.invoice_amount or 0),
        "subtotal": float(invoice.subtotal or 0),
        "discount_pct": float(invoice.discount_pct or 0),
        "discount_amount": float(invoice.discount_amount or 0),
        "gst_amount": float(invoice.gst_amount or 0),
        "pricing_tier": invoice.pricing_tier,
        "status": invoice.status,
        "notes": invoice.notes,
        "invoice_from": invoice.invoice_from or "MIPL",
        "invoice_to": invoice.invoice_to or "client",
        "invoice_to_name": invoice.invoice_to_name,
        "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
        "amount_paid": paid,
        "payments": [
            {"payment_id": p.payment_id, "payment_type": p.payment_type, "amount": float(p.amount or 0), "payment_date": p.payment_date.isoformat() if p.payment_date else None, "notes": p.notes}
            for p in invoice.payments
        ],
        "line_items": [
            {"sku": li.sku, "product_name": li.product_name, "quantity": li.quantity, "unit_price": float(li.unit_price or 0), "discount_pct": float(li.discount_pct or 0), "line_total": float(li.line_total or 0)}
            for li in invoice.line_items
        ],
    }

@router.post("/invoices/{invoice_id}/payments")
def add_payment(invoice_id: int, payload: PaymentCreate, db: Session = Depends(get_db)):
    invoice = db.query(models.Invoice).filter(models.Invoice.invoice_id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    payment = models.Payment(
        invoice_id=invoice_id, payment_type=payload.payment_type, amount=payload.amount,
        payment_date=payload.payment_date, payment_mode=payload.payment_mode,
        reference=payload.reference, notes=payload.notes,
    )
    db.add(payment)
    total_paid = sum(float(p.amount) for p in invoice.payments) + float(payload.amount)
    if total_paid >= float(invoice.invoice_amount): invoice.status = 'paid'
    elif total_paid > 0: invoice.status = 'partial'
    db.commit()
    return {"success": True}

@router.delete("/invoices/{invoice_id}")
def delete_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(models.Invoice).filter(models.Invoice.invoice_id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    db.query(models.Payment).filter(models.Payment.invoice_id == invoice_id).delete()
    db.query(models.InvoiceLineItem).filter(models.InvoiceLineItem.invoice_id == invoice_id).delete()
    db.delete(invoice)
    db.commit()
    return {"success": True}

@router.delete("/invoices/{invoice_id}/payments/{payment_id}")
def delete_payment(invoice_id: int, payment_id: int, db: Session = Depends(get_db)):
    payment = db.query(models.Payment).filter(models.Payment.payment_id == payment_id, models.Payment.invoice_id == invoice_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    db.delete(payment)
    db.commit()
    return {"success": True}
