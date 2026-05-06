from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
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

class PaymentCreate(BaseModel):
    payment_type: str  # advance / balance / partial
    amount: Decimal
    payment_date: date
    payment_mode: Optional[str] = None  # cash / bank / upi
    reference: Optional[str] = None
    notes: Optional[str] = None

# ── Helpers ───────────────────────────────────────────
def generate_invoice_code(db: Session) -> str:
    count = db.query(models.Invoice).count()
    return f"INV-2627-{str(count + 1).zfill(3)}"

# ── Routes ────────────────────────────────────────────
@router.get("/dashboard")
def finance_dashboard(db: Session = Depends(get_db)):
    invoices = db.query(models.Invoice).all()
    total_invoiced = sum(float(i.invoice_amount) for i in invoices)
    
    payments = db.query(models.Payment).all()
    total_collected = sum(float(p.amount) for p in payments)
    total_outstanding = total_invoiced - total_collected

    advance_collected = sum(float(p.amount) for p in payments if p.payment_type == 'advance')
    balance_collected = sum(float(p.amount) for p in payments if p.payment_type == 'balance')

    # Per invoice summary
    invoice_summaries = []
    for inv in invoices:
        paid = sum(float(p.amount) for p in inv.payments)
        outstanding = float(inv.invoice_amount) - paid
        lead = db.query(models.Lead).filter(models.Lead.lead_id == inv.lead_id).first()
        invoice_summaries.append({
            "invoice_id": inv.invoice_id,
            "invoice_code": inv.invoice_code,
            "lead_id": inv.lead_id,
            "client_name": lead.client_name if lead else None,
            "project_name": lead.project_name if lead else None,
            "invoice_amount": float(inv.invoice_amount),
            "paid": paid,
            "outstanding": outstanding,
            "status": inv.status,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
        })

    return {
        "summary": {
            "total_invoiced": total_invoiced,
            "total_collected": total_collected,
            "total_outstanding": total_outstanding,
            "advance_collected": advance_collected,
            "balance_collected": balance_collected,
            "invoice_count": len(invoices),
        },
        "invoices": sorted(invoice_summaries, key=lambda x: x["outstanding"], reverse=True)
    }

@router.post("/invoices")
def create_invoice(payload: InvoiceCreate, db: Session = Depends(get_db)):
    invoice = models.Invoice(
        invoice_code=generate_invoice_code(db),
        lead_id=payload.lead_id,
        boq_id=payload.boq_id,
        invoice_amount=payload.invoice_amount,
        pricing_tier=payload.pricing_tier,
        discount_pct=payload.discount_pct,
        subtotal=payload.subtotal,
        discount_amount=payload.discount_amount,
        gst_amount=payload.gst_amount,
        notes=payload.notes,
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
        paid = sum(float(p.amount) for p in inv.payments)
        lead = db.query(models.Lead).filter(models.Lead.lead_id == inv.lead_id).first()
        result.append({
            "invoice_id": inv.invoice_id,
            "invoice_code": inv.invoice_code,
            "client_name": lead.client_name if lead else None,
            "project_name": lead.project_name if lead else None,
            "invoice_amount": float(inv.invoice_amount),
            "paid": paid,
            "outstanding": float(inv.invoice_amount) - paid,
            "status": inv.status,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
            "payments": [
                {
                    "payment_id": p.payment_id,
                    "payment_type": p.payment_type,
                    "amount": float(p.amount),
                    "payment_date": p.payment_date.isoformat(),
                    "payment_mode": p.payment_mode,
                    "reference": p.reference,
                }
                for p in inv.payments
            ]
        })
    return result

@router.post("/invoices/{invoice_id}/payments")
def add_payment(invoice_id: int, payload: PaymentCreate, db: Session = Depends(get_db)):
    invoice = db.query(models.Invoice).filter(models.Invoice.invoice_id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    payment = models.Payment(
        invoice_id=invoice_id,
        payment_type=payload.payment_type,
        amount=payload.amount,
        payment_date=payload.payment_date,
        payment_mode=payload.payment_mode,
        reference=payload.reference,
        notes=payload.notes,
    )
    db.add(payment)

    # Update invoice status
    total_paid = sum(float(p.amount) for p in invoice.payments) + float(payload.amount)
    if total_paid >= float(invoice.invoice_amount):
        invoice.status = 'paid'
    elif total_paid > 0:
        invoice.status = 'partial'

    db.commit()
    return {"success": True}

@router.delete("/invoices/{invoice_id}/payments/{payment_id}")
def delete_payment(invoice_id: int, payment_id: int, db: Session = Depends(get_db)):
    payment = db.query(models.Payment).filter(
        models.Payment.payment_id == payment_id,
        models.Payment.invoice_id == invoice_id
    ).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    db.delete(payment)
    db.commit()
    return {"success": True}
