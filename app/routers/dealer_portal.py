from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app import models

router = APIRouter()

STAGE_LABELS = {
    'boq': 'BOQ Preparation',
    'order_placed': 'Order Placed',
    'site_coordination': 'Site Coordination',
    'material_delivery': 'Material Delivery',
    'installation': 'Installation',
    'testing': 'Testing & Commissioning',
    'handover': 'Handover',
}

STAGE_ORDER = ['boq', 'order_placed', 'site_coordination', 'material_delivery', 'installation', 'testing', 'handover']

@router.get("/{token}")
def get_dealer_portal(token: str, db: Session = Depends(get_db)):
    dealer = db.query(models.Dealer).filter(
        (models.Dealer.dealer_token == token) | (models.Dealer.slug == token)
    ).first()
    if not dealer:
        raise HTTPException(status_code=404, detail="Invalid portal link")

    # Only show won leads linked to this dealer
    leads = db.query(models.Lead).filter(
        models.Lead.dealer_id == dealer.dealer_id,
        models.Lead.status == 'won'
    ).order_by(models.Lead.created_at.desc()).all()

    projects = []
    for lead in leads:
        tracking = db.query(models.ProjectTracking).filter(
            models.ProjectTracking.lead_id == lead.lead_id
        ).first()
        snags = db.query(models.ProjectSnag).filter(
            models.ProjectSnag.lead_id == lead.lead_id,
            models.ProjectSnag.status == 'open'
        ).count()
        visits = db.query(models.SiteVisit).filter(
            models.SiteVisit.lead_id == lead.lead_id
        ).order_by(models.SiteVisit.visit_date.desc()).first()

        current_stage = tracking.current_stage if tracking else 'boq'
        stage_idx = STAGE_ORDER.index(current_stage) if current_stage in STAGE_ORDER else 0

        boq_value = sum(float(b.total_amount or 0) for b in lead.boqs)

        projects.append({
            "lead_id": lead.lead_id,
            "lead_code": lead.lead_code,
            "client_name": lead.client_name,
            "project_name": lead.project_name,
            "city": lead.city,
            "category": lead.category,
            "boq_value": boq_value,
            "created_at": lead.created_at.isoformat() if lead.created_at else None,
            "current_stage": current_stage,
            "current_stage_label": STAGE_LABELS.get(current_stage, current_stage),
            "stage_index": stage_idx,
            "total_stages": len(STAGE_ORDER),
            "open_snags": snags,
            "last_visit": visits.visit_date.isoformat() if visits and visits.visit_date else None,
            "tracking": {
                "order_placed_date": tracking.order_placed_date.isoformat() if tracking and tracking.order_placed_date else None,
                "material_delivery_date": tracking.material_delivery_date.isoformat() if tracking and tracking.material_delivery_date else None,
                "installation_date": tracking.installation_date.isoformat() if tracking and tracking.installation_date else None,
                "handover_date": tracking.handover_date.isoformat() if tracking and tracking.handover_date else None,
                "expected_delivery": tracking.expected_delivery.isoformat() if tracking and tracking.expected_delivery else None,
            } if tracking else {},
        })

    return {
        "dealer": {
            "dealer_id": dealer.dealer_id,
            "firm_name": dealer.firm_name,
            "contact_person": dealer.contact_person,
            "city": dealer.city,
            "state": dealer.state,
        },
        "projects": projects,
        "summary": {
            "total_projects": len(projects),
            "in_progress": len([p for p in projects if p['current_stage'] not in ['handover']]),
            "completed": len([p for p in projects if p['current_stage'] == 'handover']),
            "open_snags": sum(p['open_snags'] for p in projects),
        }
    }
