from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app import models
import hashlib, secrets
from datetime import datetime, timedelta
from difflib import SequenceMatcher

router = APIRouter()

def sha256(s): return hashlib.sha256(s.encode()).hexdigest()

def similarity(a, b):
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()

def check_project_lock(db, city, client_name, project_name, dealer_id):
    """Check if a project is locked by another dealer."""
    active_leads = db.query(models.Lead).filter(
        models.Lead.locked_by_dealer_id != None,
        models.Lead.lock_expires_at > datetime.now(),
        models.Lead.locked_by_dealer_id != dealer_id,
        models.Lead.city.ilike(f'%{city}%')
    ).all()
    
    for lead in active_leads:
        name_sim = max(
            similarity(client_name, lead.client_name or ''),
            similarity(project_name, lead.project_name or '')
        )
        if name_sim > 0.75:
            dealer = db.query(models.Dealer).filter(models.Dealer.dealer_id == lead.locked_by_dealer_id).first()
            return {
                "locked": True,
                "locked_by": dealer.firm_name if dealer else "Another dealer",
                "locked_at": lead.locked_at.isoformat() if lead.locked_at else None,
                "expires_at": lead.lock_expires_at.isoformat() if lead.lock_expires_at else None,
                "lead_id": lead.lead_id,
            }
    return {"locked": False}

@router.post("/login")
def dealer_login(body: dict, db: Session = Depends(get_db)):
    username = body.get("username", "").lower().strip()
    password = body.get("password", "")
    dealer = db.query(models.Dealer).filter(
        models.Dealer.username == username,
        models.Dealer.is_active == True
    ).first()
    if not dealer or dealer.password_hash != sha256(password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # Reuse existing token if valid, otherwise generate new one
    if not dealer.portal_token:
        token = secrets.token_urlsafe(32)
        dealer.portal_token = token
        db.commit()
    else:
        token = dealer.portal_token
    return {
        "token": token,
        "dealer_id": dealer.dealer_id,
        "firm_name": dealer.firm_name,
        "city": dealer.city,
        "discount_pct": dealer.special_discount_pct or 50.0,
    }

@router.post("/logout")
def dealer_logout(body: dict, db: Session = Depends(get_db)):
    token = body.get("token")
    dealer = db.query(models.Dealer).filter(models.Dealer.portal_token == token).first()
    if dealer:
        dealer.portal_token = None
        db.commit()
    return {"ok": True}

def get_dealer(token: str, db: Session):
    dealer = db.query(models.Dealer).filter(
        models.Dealer.portal_token == token,
        models.Dealer.is_active == True
    ).first()
    if not dealer:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return dealer

@router.get("/me")
def get_me(token: str, db: Session = Depends(get_db)):
    dealer = get_dealer(token, db)
    return {
        "dealer_id": dealer.dealer_id,
        "firm_name": dealer.firm_name,
        "city": dealer.city,
        "discount_pct": dealer.special_discount_pct or 50.0,
        "gstin": dealer.gstin,
        "contact_person": dealer.contact_person,
        "phone": dealer.phone,
    }

@router.get("/leads")
def get_dealer_leads(token: str, db: Session = Depends(get_db)):
    dealer = get_dealer(token, db)
    leads = db.query(models.Lead).filter(
        models.Lead.dealer_id == dealer.dealer_id
    ).order_by(models.Lead.created_at.desc()).all()
    
    result = []
    for lead in leads:
        if lead.dealer_acceptance == "rejected":
            continue
        boqs = db.query(models.Boq).filter(models.Boq.lead_id == lead.lead_id).all()
        boq_value = sum(float(b.total_amount or 0) for b in boqs)
        result.append({
            "lead_id": lead.lead_id,
            "lead_code": lead.lead_code,
            "project_name": lead.project_name,
            "client_name": lead.client_name,
            "city": lead.city,
            "category": lead.category,
            "status": lead.status,
            "boq_value": boq_value,
            "locked": lead.lock_expires_at and lead.lock_expires_at > datetime.now(),
            "lock_expires_at": lead.lock_expires_at.isoformat() if lead.lock_expires_at else None,
            "created_at": lead.created_at.isoformat() if lead.created_at else None,
            "dealer_notes": lead.dealer_notes,
            "acceptance": lead.dealer_acceptance,
            "assigned_at": lead.dealer_assigned_at.isoformat() if lead.dealer_assigned_at else None,
            "assignment_reason": lead.dealer_assignment_reason,
            "client_phone": lead.client_phone if lead.dealer_acceptance != "pending" else None,
        })
    return result

@router.post("/leads")
def create_dealer_lead(body: dict, db: Session = Depends(get_db)):
    token = body.get("token")
    dealer = get_dealer(token, db)
    
    city = body.get("city", "")
    client_name = body.get("client_name", "")
    project_name = body.get("project_name", client_name)
    
    # Check project lock
    lock_check = check_project_lock(db, city, client_name, project_name, dealer.dealer_id)
    if lock_check["locked"]:
        raise HTTPException(status_code=409, detail=f"This project is already registered by {lock_check['locked_by']}. Lock expires {lock_check['expires_at'][:10]}.")
    
    # Duplicate check across ALL leads (phone / name+city), not just other dealers' locks
    from app.routers.crm import find_duplicates
    dups = find_duplicates(db, phone=body.get("client_phone"), client_name=client_name,
                           project_name=project_name, city=city)
    dups = [d for d in dups if d["reason"] == "Same client phone" or d["locked"]]
    if dups and not body.get("confirm_duplicate"):
        raise HTTPException(status_code=409, detail=f"Possible duplicate of {dups[0]['lead_code']} ({dups[0]['reason']}). Contact Moorgen India if this is a different project.")

    # Generate lead code (FY-correct, MAX-based — the old COUNT/hard-coded FY produced duplicates)
    from app.routers.leads import generate_lead_code
    from app.crm_common import rescore, log_activity
    from app import crm_logic as L
    lead_code = generate_lead_code(db)

    def _num(v):
        try:
            return float(v) if v not in (None, "") else None
        except (TypeError, ValueError):
            return None

    lead = models.Lead(
        lead_code=lead_code,
        project_name=project_name,
        client_name=client_name,
        city=city,
        client_address=body.get("address", ""),
        category=body.get("category", "architectural"),
        status="new",
        channel="dealer",
        dealer_id=dealer.dealer_id,
        dealer_notes=body.get("notes", ""),
        locked_by_dealer_id=dealer.dealer_id,
        locked_at=datetime.now(),
        lock_expires_at=datetime.now() + timedelta(days=180),
        client_phone=body.get("client_phone") or None,
        builder_name=body.get("builder_name") or None,
        property_type=body.get("property_type") or None,
        property_size_sqft=int(_num(body.get("property_size_sqft")) or 0) or None,
        construction_stage=body.get("construction_stage") or None,
        estimated_value=_num(body.get("estimated_value")),
        expected_order_date=body.get("expected_order_date") or None,
        product_interest=body.get("product_interest") or None,
        attribution_type="dealer",
        lead_source="dealer_generated",
        dealer_acceptance="accepted",
        dealer_assigned_at=datetime.now(),
        last_activity_at=datetime.now(),
        status_changed_at=datetime.now(),
    )
    arch_name = (body.get("architect_name") or "").strip()
    if arch_name:
        arch = db.query(models.Architect).filter(models.Architect.firm_name.ilike(arch_name)).first()
        if arch:
            lead.architect_id = arch.architect_id
        else:
            lead.dealer_notes = ((lead.dealer_notes or "") + f"\nArchitect: {arch_name}").strip()
    rescore(db, lead)
    db.add(lead)
    db.flush()
    log_activity(db, lead_id=lead.lead_id, dealer_id=dealer.dealer_id, activity_type="system",
                 subject=f"Project registered by {dealer.firm_name} (6-month protection)",
                 notes=body.get("notes"), performed_by=dealer.firm_name, touch=False)
    db.commit()
    db.refresh(lead)
    return {"lead_id": lead.lead_id, "lead_code": lead.lead_code, "message": "Lead created and locked for 6 months"}

@router.get("/products")

def get_dealer_products(token: str, category: str = "", db: Session = Depends(get_db)):
    dealer = get_dealer(token, db)
    disc = float(dealer.special_discount_pct or 50)
    q = db.query(models.Product).filter(models.Product.is_active == True)
    if category:
        q = q.filter(models.Product.category == category)
    products = q.order_by(models.Product.name).all()
    result = []
    for p in products:
        mrp = float(p.mrp_inr or p.unit_price or 0)
        dealer_price = round(mrp * (1 - disc/100), 2)
        result.append({
            "product_id": p.product_id,
            "sku": p.sku,
            "name": p.name,
            "category": p.category,
            "family": p.family,
            "product_type": p.product_type,
            "trim": p.trim,
            "cct": p.cct,
            "beam_angle": p.beam_angle,
            "power": p.power,
            "body_color": p.body_color,
            "cup_color": p.cup_color,
            "cutout_size": p.cutout_size,
            "mrp": mrp,
            "dealer_price": dealer_price,
            "discount_pct": disc,
            "unit": "pcs",
            "image_url": None,
        })
    return result

@router.patch("/leads/{lead_id}/status")
def update_lead_status(lead_id: int, body: dict = Body(...), db: Session = Depends(get_db)):
    dealer = get_dealer(body.get("token", ""), db)
    lead = db.query(models.Lead).filter(models.Lead.lead_id == lead_id, models.Lead.dealer_id == dealer.dealer_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    from app.crm_common import log_activity
    from app import crm_logic as L
    new_status = body.get("status", lead.status)
    if new_status != lead.status:
        log_activity(db, lead_id=lead.lead_id, dealer_id=dealer.dealer_id, activity_type="stage_change",
                     subject=f"{lead.status} → {new_status} (dealer)", notes=body.get("note"),
                     performed_by=dealer.firm_name, touch=bool(body.get("note")))
        lead.status_changed_at = L.now_utc()
    lead.status = new_status
    db.commit()
    return {"ok": True}


@router.post("/leads/{lead_id}/respond")
def respond_to_assignment(lead_id: int, body: dict = Body(...), db: Session = Depends(get_db)):
    """Dealer accepts or rejects an assigned lead (24-hour SLA)."""
    from app.crm_common import log_activity
    from app import crm_logic as L
    dealer = get_dealer(body.get("token", ""), db)
    lead = db.query(models.Lead).filter(models.Lead.lead_id == lead_id, models.Lead.dealer_id == dealer.dealer_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    decision = body.get("decision")
    if decision not in ("accepted", "rejected"):
        raise HTTPException(status_code=422, detail="decision must be 'accepted' or 'rejected'")
    if decision == "rejected" and not (body.get("reason") or "").strip():
        raise HTTPException(status_code=422, detail="Please give a reason for rejecting")
    lead.dealer_acceptance = decision
    lead.dealer_responded_at = L.now_utc()
    if decision == "rejected":
        lead.dealer_reject_reason = body.get("reason")  # stays on the dealer for the scorecard; HQ reassigns
    log_activity(db, lead_id=lead.lead_id, dealer_id=dealer.dealer_id, activity_type="system",
                 subject=f"{dealer.firm_name} {decision} the lead", notes=body.get("reason"),
                 performed_by=dealer.firm_name, touch=False)
    db.commit()
    return {"ok": True, "acceptance": decision}

@router.patch("/leads/{lead_id}/notes")
def update_lead_notes(lead_id: int, body: dict = Body(...), db: Session = Depends(get_db)):
    dealer = get_dealer(body.get("token", ""), db)
    lead = db.query(models.Lead).filter(models.Lead.lead_id == lead_id, models.Lead.dealer_id == dealer.dealer_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead.dealer_notes = body.get("notes", lead.dealer_notes)
    db.commit()
    return {"ok": True}

def get_dealer_products(token: str, category: str = "", db: Session = Depends(get_db)):
    dealer = get_dealer(token, db)
    disc = dealer.special_discount_pct or 50.0
    
    query = db.query(models.Product).filter(models.Product.is_active == True)
    if category:
        query = query.filter(models.Product.category == category)
    products = query.order_by(models.Product.family, models.Product.name).all()
    
    from app.routers.export import get_image_url_for_sku
    result = []
    for p in products:
        mrp = float(p.mrp_inr or p.unit_price or 0)
        dealer_price = round(mrp * (1 - disc/100), 2)
        result.append({
            "product_id": p.product_id,
            "sku": p.sku,
            "name": p.name,
            "category": p.category,
            "family": p.family,
            "product_type": p.product_type,
            "trim": p.trim,
            "cct": p.cct,
            "beam_angle": p.beam_angle,
            "power": p.power,
            "body_color": p.body_color,
            "cup_color": p.cup_color,
            "cutout_size": p.cutout_size,
            "mrp": mrp,
            "dealer_price": dealer_price,
            "discount_pct": disc,
            "unit": "pcs",
            "image_url": None,
        })
    return result

@router.post("/check-lock")
def check_lock(body: dict, db: Session = Depends(get_db)):
    token = body.get("token")
    dealer = get_dealer(token, db)
    return check_project_lock(db, body.get("city",""), body.get("client_name",""), body.get("project_name",""), dealer.dealer_id)

