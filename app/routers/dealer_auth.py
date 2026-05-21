from fastapi import APIRouter, Depends, HTTPException
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
    token = secrets.token_urlsafe(32)
    dealer.portal_token = token
    db.commit()
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
    
    # Generate lead code
    from datetime import date
    fy = "2526" if date.today().month >= 4 else "2425"
    count = db.query(models.Lead).count()
    lead_code = f"LD-{fy}-{str(count+1).zfill(3)}"
    
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
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return {"lead_id": lead.lead_id, "lead_code": lead.lead_code, "message": "Lead created and locked for 6 months"}

@router.post("/check-lock")
def check_lock(body: dict, db: Session = Depends(get_db)):
    token = body.get("token")
    dealer = get_dealer(token, db)
    return check_project_lock(db, body.get("city",""), body.get("client_name",""), body.get("project_name",""), dealer.dealer_id)

@router.get("/products")
def get_dealer_products(token: str, category: str = "", db: Session = Depends(get_db)):
    dealer = get_dealer(token, db)
    disc = dealer.special_discount_pct or 50.0
    
    query = db.query(models.Product).filter(models.Product.is_active == True)
    if category:
        query = query.filter(models.Product.category == category)
    products = query.order_by(models.Product.family, models.Product.name).all()
    
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
            "mrp": mrp,
            "dealer_price": dealer_price,
            "discount_pct": disc,
            "unit": "pcs",
        })
    return result
