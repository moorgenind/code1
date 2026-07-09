from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from app.database import get_db
from app import models

router = APIRouter()

PIPELINE_STATUSES = ['active', 'design_in_progress', 'boq_in_progress', 'negotiation', 'won']
BOQ_CATEGORIES = ['architectural', 'automation', 'decorative']


# ── 1. Pipeline value by stage ────────────────────────────────────────────
def pipeline_by_stage(db: Session):
    # latest BOQ version per (lead, category), summed per lead, grouped by lead status
    rows = db.execute(text("""
        SELECT l.status, COALESCE(SUM(b.total_amount), 0) AS boq_value, COUNT(DISTINCT l.lead_id) AS lead_count
        FROM leads l
        LEFT JOIN (
            SELECT DISTINCT ON (lead_id, category) lead_id, category, total_amount
            FROM boqs
            ORDER BY lead_id, category, version DESC
        ) b ON b.lead_id = l.lead_id
        WHERE l.status = ANY(:statuses)
        GROUP BY l.status
    """), {"statuses": PIPELINE_STATUSES}).fetchall()

    by_status = {r.status: {"status": r.status, "boq_value": float(r.boq_value or 0), "lead_count": r.lead_count} for r in rows}
    return [
        by_status.get(s, {"status": s, "boq_value": 0.0, "lead_count": 0})
        for s in PIPELINE_STATUSES
    ]


# ── 2. Monthly revenue ────────────────────────────────────────────────────
def monthly_revenue(db: Session):
    now = datetime.utcnow()
    this_month_start = datetime(now.year, now.month, 1)
    if now.month == 1:
        last_month_start = datetime(now.year - 1, 12, 1)
    else:
        last_month_start = datetime(now.year, now.month - 1, 1)

    invoiced_this_month = db.query(models.Invoice).filter(
        models.Invoice.created_at >= this_month_start
    ).with_entities(models.Invoice.invoice_amount).all()
    invoiced_last_month = db.query(models.Invoice).filter(
        models.Invoice.created_at >= last_month_start,
        models.Invoice.created_at < this_month_start
    ).with_entities(models.Invoice.invoice_amount).all()

    total_invoiced_this_month = sum(float(r[0] or 0) for r in invoiced_this_month)
    total_invoiced_last_month = sum(float(r[0] or 0) for r in invoiced_last_month)

    collected_this_month = db.query(models.Payment).filter(
        models.Payment.payment_date >= this_month_start
    ).with_entities(models.Payment.amount).all()
    total_collected_this_month = sum(float(r[0] or 0) for r in collected_this_month)

    return {
        "invoiced_this_month": total_invoiced_this_month,
        "invoiced_last_month": total_invoiced_last_month,
        "collected_this_month": total_collected_this_month,
        "month_label": this_month_start.strftime("%B %Y"),
        "last_month_label": last_month_start.strftime("%B %Y"),
    }


# ── 3. Outstanding by dealer ──────────────────────────────────────────────
def outstanding_by_dealer(db: Session, limit: int = 10):
    invoices = db.query(models.Invoice).filter(models.Invoice.status.in_(['unpaid', 'partial'])).all()
    dealer_totals = {}
    for inv in invoices:
        lead = db.query(models.Lead).filter(models.Lead.lead_id == inv.lead_id).first()
        if not lead or not lead.dealer_id:
            continue
        paid = sum(float(p.amount or 0) for p in inv.payments)
        outstanding = float(inv.invoice_amount or 0) - paid
        if outstanding <= 0:
            continue
        dealer_totals.setdefault(lead.dealer_id, {"outstanding": 0.0, "invoice_count": 0})
        dealer_totals[lead.dealer_id]["outstanding"] += outstanding
        dealer_totals[lead.dealer_id]["invoice_count"] += 1

    dealer_ids = list(dealer_totals.keys())
    dealers = db.query(models.Dealer).filter(models.Dealer.dealer_id.in_(dealer_ids)).all() if dealer_ids else []
    dealer_map = {d.dealer_id: d.firm_name for d in dealers}

    result = [
        {
            "dealer_id": did,
            "dealer_name": dealer_map.get(did, "Unknown Dealer"),
            "outstanding": data["outstanding"],
            "invoice_count": data["invoice_count"],
        }
        for did, data in dealer_totals.items()
    ]
    result.sort(key=lambda x: x["outstanding"], reverse=True)
    return result[:limit]


# ── 4. Stock value on hand ────────────────────────────────────────────────
def stock_value_by_category(db: Session):
    rows = db.execute(text("""
        SELECT p.category,
               COALESCE(SUM(s.quantity_on_hand), 0) AS total_units,
               COALESCE(SUM(s.quantity_on_hand * COALESCE(p.landing_inr, p.dealer_cost, 0)), 0) AS stock_value
        FROM stock s
        JOIN products p ON p.sku = s.sku
        WHERE p.category = ANY(:categories)
        GROUP BY p.category
    """), {"categories": BOQ_CATEGORIES}).fetchall()

    by_category = {r.category: {"category": r.category, "total_units": int(r.total_units or 0), "stock_value": float(r.stock_value or 0)} for r in rows}
    breakdown = [by_category.get(c, {"category": c, "total_units": 0, "stock_value": 0.0}) for c in BOQ_CATEGORIES]
    return {
        "breakdown": breakdown,
        "total_units": sum(c["total_units"] for c in breakdown),
        "total_value": sum(c["stock_value"] for c in breakdown),
    }


# ── 5. Projects by delivery status ────────────────────────────────────────
def projects_by_delivery_status(db: Session):
    won_leads = db.query(models.Lead).filter(models.Lead.status == 'won').all()
    counts = {"not_started": 0, "in_progress": 0, "delivered": 0}
    for lead in won_leads:
        tracking = db.query(models.ProjectTracking).filter(models.ProjectTracking.lead_id == lead.lead_id).first()
        if not tracking or tracking.current_stage in (None, 'boq'):
            counts["not_started"] += 1
        elif tracking.current_stage == 'handover':
            counts["delivered"] += 1
        else:
            counts["in_progress"] += 1
    return {
        "not_started": counts["not_started"],
        "in_progress": counts["in_progress"],
        "delivered": counts["delivered"],
        "total_won_projects": len(won_leads),
    }


@router.get("/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    return {
        "pipeline_by_stage": pipeline_by_stage(db),
        "monthly_revenue": monthly_revenue(db),
        "outstanding_by_dealer": outstanding_by_dealer(db),
        "stock_value": stock_value_by_category(db),
        "projects_by_delivery_status": projects_by_delivery_status(db),
    }
