from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models

router = APIRouter()

LF_TOKEN = "LF-MOORGEN-2526-PORTAL"

@router.get("/{token}")
def get_lf_portal(token: str, db: Session = Depends(get_db)):
    if token != LF_TOKEN:
        raise HTTPException(status_code=404, detail="Invalid portal link")

    # Active leads (flagship + flagship_dealer)
    leads = db.query(models.Lead).filter(
        models.Lead.channel.in_(['flagship', 'flagship_dealer'])
    ).order_by(models.Lead.created_at.desc()).all()

    # Dealers - only LightForge dealers (those with flagship_dealer leads)
    lf_dealer_ids = set(l.dealer_id for l in leads if l.dealer_id and l.channel == "flagship_dealer")
    dealers = db.query(models.Dealer).filter(models.Dealer.dealer_id.in_(lf_dealer_ids)).all() if lf_dealer_ids else []
    dealer_map = {d.dealer_id: d for d in dealers}

    # LF Invoices
    lf_invoices = db.query(models.Invoice).filter(
        models.Invoice.invoice_from == 'LightForge'
    ).all()

    # B2B vs B2C split
    b2b_leads = [l for l in leads if l.channel == 'flagship_dealer']
    b2c_leads = [l for l in leads if l.channel == 'flagship']

    # Build lead summaries
    lead_summaries = []
    for lead in leads:
        boq_value = sum(float(b.total_amount or 0) for b in lead.boqs)
        dealer = dealer_map.get(lead.dealer_id)
        lead_summaries.append({
            "lead_id": lead.lead_id,
            "lead_code": lead.lead_code,
            "project_name": lead.project_name,
            "client_name": lead.client_name,
            "city": lead.city,
            "category": lead.category,
            "channel": lead.channel,
            "status": lead.status,
            "boq_value": boq_value,
            "dealer_name": dealer.firm_name if dealer else None,
            "dealer_city": dealer.city if dealer else None,
            "created_at": lead.created_at.isoformat() if lead.created_at else None,
        })

    # Build invoice summaries
    invoice_summaries = []
    for inv in lf_invoices:
        lead = db.query(models.Lead).filter(models.Lead.lead_id == inv.lead_id).first()
        paid = sum(float(p.amount) for p in inv.payments)
        invoice_summaries.append({
            "invoice_id": inv.invoice_id,
            "invoice_code": inv.invoice_code,
            "project_name": lead.project_name if lead else None,
            "client_name": lead.client_name if lead else None,
            "invoice_to_name": inv.invoice_to_name,
            "invoice_amount": float(inv.invoice_amount),
            "paid": paid,
            "outstanding": float(inv.invoice_amount) - paid,
            "status": inv.status,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
        })

    # Dealer pipeline
    dealer_summaries = []
    for dealer in dealers:
        dealer_leads = [l for l in lead_summaries if l['dealer_name'] == dealer.firm_name]
        dealer_invoices = [i for i in invoice_summaries if i['invoice_to_name'] and dealer.firm_name in i['invoice_to_name']]
        dealer_summaries.append({
            "dealer_id": dealer.dealer_id,
            "firm_name": dealer.firm_name,
            "city": dealer.city,
            "contact_person": dealer.contact_person,
            "phone": dealer.phone,
            "total_leads": len(dealer_leads),
            "active_leads": len([l for l in dealer_leads if l['status'] not in ['won','lost']]),
            "won_leads": len([l for l in dealer_leads if l['status'] == 'won']),
            "pipeline_value": sum(l['boq_value'] for l in dealer_leads),
            "outstanding": sum(i['outstanding'] for i in dealer_invoices),
        })

    # Summary stats
    active = [l for l in lead_summaries if l['status'] not in ['won','lost']]
    won = [l for l in lead_summaries if l['status'] == 'won']
    total_invoiced = sum(i['invoice_amount'] for i in invoice_summaries)
    total_outstanding = sum(i['outstanding'] for i in invoice_summaries)
    total_collected = sum(i['paid'] for i in invoice_summaries)

    # B2B vs B2C
    b2b_summaries = [l for l in lead_summaries if l['channel'] == 'flagship_dealer']
    b2c_summaries = [l for l in lead_summaries if l['channel'] == 'flagship']
    b2b_won = [l for l in b2b_summaries if l['status'] == 'won']
    b2c_won = [l for l in b2c_summaries if l['status'] == 'won']

    return {
        "summary": {
            "total_leads": len(lead_summaries),
            "active_leads": len(active),
            "won_leads": len(won),
            "win_rate": round(len(won) / len(lead_summaries) * 100) if lead_summaries else 0,
            "pipeline_value": sum(l['boq_value'] for l in active),
            "won_value": sum(l['boq_value'] for l in won),
            "total_invoiced": total_invoiced,
            "total_collected": total_collected,
            "total_outstanding": total_outstanding,
            "b2b": {
                "total": len(b2b_summaries),
                "won": len(b2b_won),
                "active": len([l for l in b2b_summaries if l['status'] not in ['won','lost']]),
                "win_rate": round(len(b2b_won)/len(b2b_summaries)*100) if b2b_summaries else 0,
                "pipeline_value": sum(l['boq_value'] for l in b2b_summaries if l['status'] not in ['won','lost']),
                "won_value": sum(l['boq_value'] for l in b2b_won),
            },
            "b2c": {
                "total": len(b2c_summaries),
                "won": len(b2c_won),
                "active": len([l for l in b2c_summaries if l['status'] not in ['won','lost']]),
                "win_rate": round(len(b2c_won)/len(b2c_summaries)*100) if b2c_summaries else 0,
                "pipeline_value": sum(l['boq_value'] for l in b2c_summaries if l['status'] not in ['won','lost']),
                "won_value": sum(l['boq_value'] for l in b2c_won),
            },
        },
        "leads": lead_summaries,
        "dealers": dealer_summaries,
        "invoices": sorted(invoice_summaries, key=lambda x: x['outstanding'], reverse=True),
    }
