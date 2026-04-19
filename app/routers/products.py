from fastapi import APIRouter, Depends, Query, Response
import requests as http_requests
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from decimal import Decimal

from app.database import get_db
from app import models
try:
    from app.image_map import get_image_url as _get_image_url
except Exception as e:
    print(f"image_map import failed: {e}")
    def _get_image_url(*args, **kwargs):
        return None

try:
    from app.dec_image_map import DEC_IMAGE_MAP
except Exception as e:
    print(f"dec_image_map import failed: {e}")
    DEC_IMAGE_MAP = {}

import re as _re

def _get_dec_image_url(sku: str):
    match = _re.search(r'DEC-([A-Z]\d+)', sku)
    if match:
        series = match.group(1)
        file_id = DEC_IMAGE_MAP.get(series)
        if file_id:
            return f"https://drive.google.com/thumbnail?id={file_id}&sz=w200"
    return None

router = APIRouter()

def build_auto_description(p):
    """Build a clean one-line description from key product attributes."""
    parts = []
    if p.family:
        parts.append(str(p.family))
    if p.cct:
        parts.append(f"CCT: {p.cct}")
    if p.beam_angle:
        parts.append(f"Beam: {p.beam_angle}")
    if p.power:
        parts.append(f"Power: {p.power}")
    if p.voltage:
        parts.append(f"Voltage: {p.voltage}")
    if p.current:
        parts.append(f"Current: {p.current}")
    if p.body_color:
        parts.append(f"Body: {p.body_color}")
    if p.led_chip:
        parts.append(f"LED: {p.led_chip}")
    if p.cri:
        parts.append(f"CRI: {p.cri}")
    if p.cutout_size:
        parts.append(f"Cutout: {p.cutout_size}mm")
    return " | ".join(parts) if parts else ""



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
                "specification": p.specification,
                "description": p.description,
                "auto_description": build_auto_description(p),
                "image_url": _get_image_url(p.family, p.name, p.body_color, p.trim),
            }
            for p in products[:50]
        ],
        "total_matches": len(products),
    }


@router.get("/image-proxy")
def image_proxy(file_id: str):
    """Proxy Google Drive images to avoid CORS issues."""
    try:
        url = f"https://drive.google.com/uc?export=view&id={file_id}"
        resp = http_requests.get(url, timeout=10, allow_redirects=True)
        content_type = resp.headers.get("Content-Type", "image/png")
        return Response(content=resp.content, media_type=content_type)
    except Exception as e:
        return Response(status_code=404)


@router.get("/image-proxy-sku")
def image_by_sku(sku: str, db: Session = Depends(get_db)):
    """Return image URL for a product SKU."""
    product = db.query(models.Product).filter(models.Product.sku == sku).first()
    if not product:
        from fastapi import Response
        return Response(status_code=404)
    # Try decorative first
    if sku.startswith("DEC-"):
        url = _get_dec_image_url(sku)
    else:
        url = _get_image_url(product.family, product.name, product.body_color, product.trim)
    if not url:
        from fastapi import Response
        return Response(status_code=404)
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=url)


@router.get("/filters/decorative")
def get_decorative_filters(
    product_type: str = None,
    family: str = None,
    material: str = None,
    cct: str = None,
    db: Session = Depends(get_db),
):
    """Cascading filter options for decorative lighting."""
    query = db.query(models.Product).filter(models.Product.category == "decorative")

    if product_type:
        query = query.filter(models.Product.product_type == product_type)
    if family:
        query = query.filter(models.Product.family == family)
    if material:
        query = query.filter(models.Product.material == material)
    if cct:
        query = query.filter(models.Product.cct == cct)

    products = query.all()

    def unique(field):
        vals = set()
        for p in products:
            v = getattr(p, field, None)
            if v and str(v).strip() and str(v).strip() not in ("/", "#N/A"):
                vals.add(str(v).strip())
        return sorted(vals)

    return {
        "types": unique("product_type"),
        "families": unique("family"),
        "materials": unique("material"),
        "ccts": unique("cct"),
        "matches": [
            {
                "sku": p.sku,
                "name": p.name,
                "family": p.family,
                "product_type": p.product_type,
                "material": p.material,
                "dimensions": p.dimensions,
                "cct": p.cct,
                "mrp_gst": float(p.mrp_gst) if p.mrp_gst else None,
                "dealer_mrp": float(p.dealer_mrp) if p.dealer_mrp else None,
                "description": p.description,
                "specification": p.specification,
            }
            for p in products[:50]
        ],
        "total_matches": len(products),
    }
