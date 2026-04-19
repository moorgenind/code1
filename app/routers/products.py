from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from decimal import Decimal

from app.database import get_db
from app import models

router = APIRouter()


class ProductResponse(BaseModel):
    product_id: int
    sku: str
    name: str
    category: Optional[str]
    subcategory: Optional[str]
    unit_price: Optional[Decimal]

    class Config:
        from_attributes = True


@router.get("/", response_model=List[ProductResponse])
def search_products(
    q: str = Query(None, description="Search by name or SKU"),
    category: str = Query(None),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(models.Product).filter(models.Product.is_active == True)

    if category:
        query = query.filter(models.Product.category == category)

    if q:
        search = f"%{q}%"
        query = query.filter(
            models.Product.name.ilike(search) |
            models.Product.sku.ilike(search)
        )

    return query.limit(limit).all()


@router.get("/filters/architectural")
def get_architectural_filters(
    family: str = None,
    product_type: str = None,
    trim: str = None,
    cutout: str = None,
    cct: str = None,
    beam_angle: str = None,
    body_color: str = None,
    cup_color: str = None,
    db: Session = Depends(get_db),
):
    """Returns available filter options for architectural lighting, cascading based on selections."""
    query = db.query(models.Product).filter(models.Product.category == "architectural")

    if family:
        query = query.filter(models.Product.family == family)
    if product_type:
        query = query.filter(models.Product.product_type == product_type)
    if trim:
        query = query.filter(models.Product.trim == trim)
    if cutout:
        query = query.filter(models.Product.cutout_size == cutout)
    if cct:
        query = query.filter(models.Product.cct == cct)
    if beam_angle:
        query = query.filter(models.Product.beam_angle == beam_angle)
    if body_color:
        query = query.filter(models.Product.body_color == body_color)
    if cup_color:
        query = query.filter(models.Product.cup_color == cup_color)

    products = query.all()

    def unique_nonempty(field):
        vals = set()
        for p in products:
            v = getattr(p, field, None)
            if v and str(v).strip() and str(v).strip() != "/":
                vals.add(str(v).strip())
        return sorted(vals)

    return {
        "families": unique_nonempty("family"),
        "types": unique_nonempty("product_type"),
        "trims": unique_nonempty("trim"),
        "cutouts": unique_nonempty("cutout_size"),
        "ccts": unique_nonempty("cct"),
        "beam_angles": unique_nonempty("beam_angle"),
        "body_colors": unique_nonempty("body_color"),
        "cup_colors": unique_nonempty("cup_color"),
        "matching_products": [
            {
                "sku": p.sku,
                "product_name": p.product_name,
                "family": p.family,
                "mrp_gst": p.mrp_gst,
                "flagship_mrp": p.flagship_mrp,
                "dealer_mrp": p.dealer_mrp,
            }
            for p in products[:20]
        ],
        "total_matches": len(products),
    }


@router.get("/filters/architectural")
def get_architectural_filters(
    family: str = None,
    product_type: str = None,
    trim: str = None,
    cutout_size: str = None,
    cct: str = None,
    beam_angle: str = None,
    body_color: str = None,
    cup_color: str = None,
    db: Session = Depends(get_db),
):
    """Cascading filter options for architectural lighting."""
    query = db.query(models.Product).filter(models.Product.category == "architectural")

    if family:
        query = query.filter(models.Product.family == family)
    if product_type:
        query = query.filter(models.Product.product_type == product_type)
    if trim:
        query = query.filter(models.Product.trim == trim)
    if cutout_size:
        query = query.filter(models.Product.cutout_size == cutout_size)
    if cct:
        query = query.filter(models.Product.cct == cct)
    if beam_angle:
        query = query.filter(models.Product.beam_angle == beam_angle)
    if body_color:
        query = query.filter(models.Product.body_color == body_color)
    if cup_color:
        query = query.filter(models.Product.cup_color == cup_color)

    products = query.all()

    def unique(field):
        vals = set()
        for p in products:
            v = getattr(p, field, None)
            if v and str(v).strip() and str(v).strip() != "/":
                vals.add(str(v).strip())
        return sorted(vals)

    return {
        "families": unique("family"),
        "types": unique("product_type"),
        "trims": unique("trim"),
        "cutouts": unique("cutout_size"),
        "ccts": unique("cct"),
        "beam_angles": unique("beam_angle"),
        "body_colors": unique("body_color"),
        "cup_colors": unique("cup_color"),
        "matches": [
            {
                "sku": p.sku,
                "name": p.name,
                "family": p.family,
                "product_type": p.product_type,
                "mrp_gst": float(p.mrp_gst) if p.mrp_gst else None,
                "flagship_mrp": float(p.flagship_mrp) if p.flagship_mrp else None,
                "dealer_mrp": float(p.dealer_mrp) if p.dealer_mrp else None,
            }
            for p in products[:50]
        ],
        "total_matches": len(products),
    }
