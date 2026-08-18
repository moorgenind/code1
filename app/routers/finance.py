from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from decimal import Decimal
from typing import Optional, List
from datetime import date
from app.database import get_db
from app import models

router = APIRouter()

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
    invoice_from: Optional[str] = "MIPL"
    invoice_to: Optional[str] = "client"
    invoice_to_name: Optional[str] = None

class PaymentCreate(BaseModel):
    payment_type: str
    amount: Decimal
    payment_date: date
    payment_mode: Optional[str] = None
    reference: Optional[str] = None
    notes: Optional[str] = None

def generate_invoice_code(db: Session, entity: str = "MIPL") -> str:
    from sqlalchemy import func
    prefix = "INV" if entity == "MIPL" else "LF"
    fy = "2627"
    pattern = f"{prefix}-{fy}-%"
    last = db.query(func.max(models.Invoice.invoice_code)).filter(
        models.Invoice.invoice_code.like(pattern)
    ).scalar()
    if last:
        try:
            num = int(last.split("-")[-1]) + 1
        except:
            num = 1
    else:
        num = 1
    return f"{prefix}-{fy}-{str(num).zfill(3)}"

def build_invoice_summary(inv, lead):
    paid = sum(float(p.amount) for p in inv.payments)
    outstanding = float(inv.invoice_amount) - paid
    advance = sum(float(p.amount) for p in inv.payments if p.payment_type == 'advance')
    balance = sum(float(p.amount) for p in inv.payments if p.payment_type == 'balance')
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
        "advance": advance,
        "balance": balance,
        "status": inv.status,
        "invoice_from": inv.invoice_from or "MIPL",
        "invoice_to": inv.invoice_to or "client",
        "invoice_to_name": inv.invoice_to_name,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
        "payments": [
            {"payment_id": p.payment_id, "payment_type": p.payment_type, "amount": float(p.amount),
             "payment_date": p.payment_date.isoformat() if p.payment_date else None,
             "payment_mode": p.payment_mode, "reference": p.reference}
            for p in inv.payments
        ]
    }

@router.get("/dashboard")
def finance_dashboard(db: Session = Depends(get_db)):
    invoices = db.query(models.Invoice).all()

    all_summaries = []
    for inv in invoices:
        lead = db.query(models.Lead).filter(models.Lead.lead_id == inv.lead_id).first()
        all_summaries.append(build_invoice_summary(inv, lead))

    def calc_summary(summaries):
        return {
            "total_invoiced": sum(s["invoice_amount"] for s in summaries),
            "total_collected": sum(s["paid"] for s in summaries),
            "total_outstanding": sum(s["outstanding"] for s in summaries),
            "advance_collected": sum(s["advance"] for s in summaries),
            "balance_collected": sum(s["balance"] for s in summaries),
            "invoice_count": len(summaries),
        }

    mipl = [s for s in all_summaries if s["invoice_from"] == "MIPL"]
    lf = [s for s in all_summaries if s["invoice_from"] == "LightForge"]

    return {
        "summary": calc_summary(all_summaries),
        "mipl_summary": calc_summary(mipl),
        "lf_summary": calc_summary(lf),
        "invoices": sorted(all_summaries, key=lambda x: x["outstanding"], reverse=True)
    }

@router.post("/invoices")
def create_invoice(payload: InvoiceCreate, db: Session = Depends(get_db)):
    invoice = models.Invoice(
        invoice_code=generate_invoice_code(db, payload.invoice_from or "MIPL"),
        lead_id=payload.lead_id, boq_id=payload.boq_id,
        invoice_amount=payload.invoice_amount, pricing_tier=payload.pricing_tier,
        discount_pct=payload.discount_pct, subtotal=payload.subtotal,
        discount_amount=payload.discount_amount, gst_amount=payload.gst_amount,
        notes=payload.notes,
        invoice_from=payload.invoice_from or "MIPL",
        invoice_to=payload.invoice_to or "client",
        invoice_to_name=payload.invoice_to_name,
    )
    db.add(invoice)
    db.flush()
    for item in payload.line_items:
        hsn = None
        if item.sku:
            product = db.query(models.Product).filter(models.Product.sku == item.sku).first()
            if product:
                hsn = product.hsn_code
        db.add(models.InvoiceLineItem(
            invoice_id=invoice.invoice_id, sku=item.sku, product_name=item.product_name,
            hsn_code=hsn,
            quantity=item.quantity, unit_price=item.unit_price,
            discount_pct=item.discount_pct, line_total=item.line_total,
        ))
    db.commit()
    db.refresh(invoice)
    return {"invoice_id": invoice.invoice_id, "invoice_code": invoice.invoice_code}

@router.get("/invoices")
def list_invoices(db: Session = Depends(get_db)):
    invoices = db.query(models.Invoice).order_by(models.Invoice.created_at.desc()).all()
    result = []
    for inv in invoices:
        lead = db.query(models.Lead).filter(models.Lead.lead_id == inv.lead_id).first()
        result.append(build_invoice_summary(inv, lead))
    return result

@router.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(models.Invoice).filter(models.Invoice.invoice_id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    lead = db.query(models.Lead).filter(models.Lead.lead_id == invoice.lead_id).first()
    paid = sum(float(p.amount or 0) for p in invoice.payments)
    return {
        "invoice_id": invoice.invoice_id, "invoice_code": invoice.invoice_code,
        "lead_id": invoice.lead_id,
        "client_name": lead.client_name if lead else None,
        "project_name": lead.project_name if lead else None,
        "invoice_amount": float(invoice.invoice_amount or 0),
        "subtotal": float(invoice.subtotal or 0),
        "discount_pct": float(invoice.discount_pct or 0),
        "discount_amount": float(invoice.discount_amount or 0),
        "gst_amount": float(invoice.gst_amount or 0),
        "pricing_tier": invoice.pricing_tier, "status": invoice.status, "notes": invoice.notes,
        "invoice_from": invoice.invoice_from or "MIPL",
        "invoice_to": invoice.invoice_to or "client",
        "invoice_to_name": invoice.invoice_to_name,
        "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
        "amount_paid": paid,
        "payments": [
            {"payment_id": p.payment_id, "payment_type": p.payment_type, "amount": float(p.amount or 0),
             "payment_date": p.payment_date.isoformat() if p.payment_date else None, "notes": p.notes}
            for p in invoice.payments
        ],
        "line_items": [
            {"sku": li.sku, "product_name": li.product_name, "quantity": li.quantity,
             "unit_price": float(li.unit_price or 0), "discount_pct": float(li.discount_pct or 0),
             "line_total": float(li.line_total or 0)}
            for li in invoice.line_items
        ],
    }

@router.post("/invoices/{invoice_id}/payments")
def add_payment(invoice_id: int, payload: PaymentCreate, db: Session = Depends(get_db)):
    invoice = db.query(models.Invoice).filter(models.Invoice.invoice_id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    db.add(models.Payment(
        invoice_id=invoice_id, payment_type=payload.payment_type, amount=payload.amount,
        payment_date=payload.payment_date, payment_mode=payload.payment_mode,
        reference=payload.reference, notes=payload.notes,
    ))
    total_paid = sum(float(p.amount) for p in invoice.payments) + float(payload.amount)
    if total_paid >= float(invoice.invoice_amount): invoice.status = 'paid'
    elif total_paid > 0: invoice.status = 'partial'
    db.commit()
    return {"success": True}

@router.delete("/invoices/{invoice_id}")
def delete_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(models.Invoice).filter(models.Invoice.invoice_id == invoice_id).first()
    if not invoice: raise HTTPException(status_code=404, detail="Invoice not found")
    db.query(models.Payment).filter(models.Payment.invoice_id == invoice_id).delete()
    db.query(models.InvoiceLineItem).filter(models.InvoiceLineItem.invoice_id == invoice_id).delete()
    db.delete(invoice)
    db.commit()
    return {"success": True}

@router.delete("/invoices/{invoice_id}/payments/{payment_id}")
def delete_payment(invoice_id: int, payment_id: int, db: Session = Depends(get_db)):
    payment = db.query(models.Payment).filter(
        models.Payment.payment_id == payment_id, models.Payment.invoice_id == invoice_id).first()
    if not payment: raise HTTPException(status_code=404, detail="Payment not found")
    db.delete(payment)
    db.commit()
    return {"success": True}
