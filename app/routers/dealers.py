from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, date

from app.database import get_db
from app import models

router = APIRouter()


class DealerCreate(BaseModel):
    firm_name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    region: Optional[str] = None
    classification: Optional[str] = None
    lifecycle_stage: Optional[str] = None
    certified_categories: Optional[List[str]] = None
    capabilities: Optional[List[str]] = None
    territory_cities: Optional[List[str]] = None
    training_score: Optional[int] = None
    installation_score: Optional[int] = None
    service_score: Optional[int] = None
    agreement_start: Optional[date] = None
    agreement_end: Optional[date] = None
    crm_notes: Optional[str] = None
    gstin: Optional[str] = None


class DealerUpdate(BaseModel):
    firm_name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    status: Optional[str] = None
    region: Optional[str] = None
    classification: Optional[str] = None
    lifecycle_stage: Optional[str] = None
    certified_categories: Optional[List[str]] = None
    capabilities: Optional[List[str]] = None
    territory_cities: Optional[List[str]] = None
    training_score: Optional[int] = None
    installation_score: Optional[int] = None
    service_score: Optional[int] = None
    agreement_start: Optional[date] = None
    agreement_end: Optional[date] = None
    crm_notes: Optional[str] = None
    gstin: Optional[str] = None


class DealerResponse(BaseModel):
    dealer_id: int
    firm_name: str
    contact_person: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    city: Optional[str]
    state: Optional[str]
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    region: Optional[str] = None
    classification: Optional[str] = None
    lifecycle_stage: Optional[str] = None
    certified_categories: Optional[List[str]] = None
    capabilities: Optional[List[str]] = None
    territory_cities: Optional[List[str]] = None
    training_score: Optional[int] = None
    installation_score: Optional[int] = None
    service_score: Optional[int] = None
    agreement_start: Optional[date] = None
    agreement_end: Optional[date] = None
    crm_notes: Optional[str] = None
    gstin: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/", response_model=List[DealerResponse])
def list_dealers(db: Session = Depends(get_db)):
    return db.query(models.Dealer).order_by(models.Dealer.firm_name).all()


@router.get("/{dealer_id}", response_model=DealerResponse)
def get_dealer(dealer_id: int, db: Session = Depends(get_db)):
    dealer = db.query(models.Dealer).filter(models.Dealer.dealer_id == dealer_id).first()
    if not dealer:
        raise HTTPException(status_code=404, detail="Dealer not found")
    return dealer


@router.post("/", response_model=DealerResponse)
def create_dealer(payload: DealerCreate, db: Session = Depends(get_db)):
    dealer = models.Dealer(
        firm_name=payload.firm_name,
        contact_person=payload.contact_person,
        phone=payload.phone,
        email=payload.email,
        city=payload.city,
        state=payload.state,
        status="active",
    )
    for f in DealerCreate.__fields__:
        if f not in ("firm_name", "contact_person", "phone", "email", "city", "state"):
            v = getattr(payload, f, None)
            if v is not None:
                setattr(dealer, f, v)
    if not dealer.lifecycle_stage:
        dealer.lifecycle_stage = "active"
    db.add(dealer)
    db.commit()
    db.refresh(dealer)
    return dealer


@router.patch("/{dealer_id}", response_model=DealerResponse)
def update_dealer(dealer_id: int, payload: DealerUpdate, db: Session = Depends(get_db)):
    dealer = db.query(models.Dealer).filter(models.Dealer.dealer_id == dealer_id).first()
    if not dealer:
        raise HTTPException(status_code=404, detail="Dealer not found")

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(dealer, field, value)

    db.commit()
    db.refresh(dealer)
    return dealer


@router.delete("/{dealer_id}")
def delete_dealer(dealer_id: int, db: Session = Depends(get_db)):
    dealer = db.query(models.Dealer).filter(models.Dealer.dealer_id == dealer_id).first()
    if not dealer:
        raise HTTPException(status_code=404, detail="Dealer not found")
    db.delete(dealer)
    db.commit()
    return {"success": True, "message": f"Dealer {dealer_id} deleted"}
