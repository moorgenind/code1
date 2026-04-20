from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, extract
from typing import Optional
from app.database import get_db
from app import models

router = APIRouter()

@router.get("/{token}")
def get_dealer_portal(
    token: str,
    month: Optional[int] = None,
    quarter: Optional[int] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db)
):
    # Validate token
    dealer = db.query(models.Dealer).filter(models.Dealer.dealer_token == token).first()
    if not dealer:
        raise HTTPException(status_code=404, detail="Invalid portal link")

    # Default: rolling 12 months if no filters specified
    from datetime import timedelta
    if not year and not month and not quarter:
        twelve_months_ago = datetime.utcnow() - timedelta(days=365)
        query = query.filter(models.Lead.created_at >= twelve_months_ago)

    # Build leads query — by state or manually assigned
    states = dealer.portal_states or []
    assigned_ids = dealer.assigned_lead_ids or []

    query = db.query(models.Lead).filter(
        or_(
            models.Lead.city.in_(get_cities_for_states(states)),
            models.Lead.dealer_id == dealer.dealer_id,
            models.Lead.lead_id.in_(assigned_ids)
        )
    )

    # Time filters
    if year:
        query = query.filter(extract('year', models.Lead.created_at) == year)
    if month:
        query = query.filter(extract('month', models.Lead.created_at) == month)
    if quarter:
        query = query.filter(extract('quarter', models.Lead.created_at) == quarter)

    leads = query.order_by(models.Lead.created_at.desc()).all()

    # Compute summary metrics
    total = len(leads)
    by_status = {}
    for l in leads:
        by_status[l.status] = by_status.get(l.status, 0) + 1

    active_leads = [l for l in leads if l.status not in ('lost',)]
    lost_leads = [l for l in leads if l.status == 'lost']
    won_leads = [l for l in leads if l.status == 'won']

    pipeline_value = sum(float(b.total_amount or 0) for l in active_leads for b in l.boqs)
    won_value = sum(float(b.total_amount or 0) for l in won_leads for b in l.boqs)
    total_value = sum(float(b.total_amount or 0) for l in leads for b in l.boqs)

    win_rate = round(len(won_leads) / total * 100) if total > 0 else 0
    avg_project_size = round(pipeline_value / len(active_leads)) if active_leads else 0

    # Category breakdown
    by_category = {}
    for l in leads:
        cat = l.category or 'other'
        by_category[cat] = by_category.get(cat, 0) + 1

    return {
        "dealer": {
            "dealer_id": dealer.dealer_id,
            "firm_name": dealer.firm_name,
            "contact_person": dealer.contact_person,
            "city": dealer.city,
            "state": dealer.state,
        },
        "leads": [
            {
                "lead_id": l.lead_id,
                "lead_code": l.lead_code,
                "client_name": l.client_name,
                "project_name": l.project_name,
                "city": l.city,
                "status": l.status,
                "category": l.category,
                "created_at": l.created_at.isoformat() if l.created_at else None,
                "boq_value": sum(float(b.total_amount or 0) for b in l.boqs),
                "boqs": [
                    {
                        "boq_id": b.boq_id,
                        "boq_code": b.boq_code,
                        "category": b.category,
                        "status": b.status,
                        "total_amount": float(b.total_amount) if b.total_amount else 0,
                        "line_items": [
                            {
                                "line_item_id": i.line_item_id,
                                "level": i.level,
                                "area": i.area,
                                "product_sku": i.product_sku,
                                "product_name": i.product_name,
                                "quantity": i.quantity,
                                "unit_price": float(i.unit_price) if i.unit_price else 0,
                                "line_total": float(i.line_total) if i.line_total else 0,
                                "image_url": i.image_url,
                            }
                            for i in b.line_items
                        ]
                    }
                    for b in l.boqs
                ]
            }
            for l in leads
        ],
        "summary": {
            "total_leads": total,
            "active_leads": len(active_leads),
            "won_leads": len(won_leads),
            "lost_leads": len(lost_leads),
            "win_rate": win_rate,
            "pipeline_value": pipeline_value,
            "won_value": won_value,
            "total_boq_value": total_value,
            "avg_project_size": avg_project_size,
            "by_status": by_status,
            "by_category": by_category,
        }
    }

def get_cities_for_states(states):
    """Map states to their major cities."""
    city_map = {
        "Telangana": ["Hyderabad", "Warangal", "Nizamabad", "Karimnagar", "Khammam"],
        "Andhra Pradesh": ["Vijayawada", "Visakhapatnam", "Guntur", "Nellore", "Tirupati", "Kakinada", "Rajahmundry"],
    }
    cities = []
    for state in states:
        cities.extend(city_map.get(state, []))
    return cities
