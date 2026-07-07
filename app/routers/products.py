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
    q: str = None,
    category: str = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    results = db.query(models.Product).filter(models.Product.is_active == True)
    if category and isinstance(category, str):
        results = results.filter(models.Product.category == category)
    if q and isinstance(q, str):
        search = f"%{q}%"
        results = results.filter(
            models.Product.name.ilike(search) |
            models.Product.sku.ilike(search)
        )
    return results.limit(limit).all()

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
    length: str = None,
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
            if v is not None and str(v).strip() and str(v).strip() != "/":
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
                "image_url": _get_dec_image_url(p.sku),
            }
            for p in products[:50]
        ],
        "total_matches": len(products),
    }
# patch applied below — see get_architectural_filters fix


# ── One-time admin: bulk price update (Jul 2026) ──────────────────────────────
_PRICE_UPDATE_TOKEN = "mg-price-jul26-x9k2"

_NEW_PRICES = {
    '331.50.35Z': 22575.49, '331.51.32Z': 28364.08, '331.51.53Z': 28364.08,
    '335.50.03': 4341.44,
    'DS157-00B00': 3060.43,
    'MQ8005D25': 32700.31, 'MQ8005D37': 32700.31, 'MQ8005F18': 32700.31,
    'MQ8006D25': 32700.31, 'MQ8006D37': 32700.31, 'MQ8006F18': 36789.08,
    'MQ8021C27': 4541.44, 'MQ8021C56': 4541.44, 'MQ8027C56': 2273.18,
    'MQ8106D37': 4541.44,
    'MQ8288C02': 10898.46, 'MQ8288C22': 10898.46, 'MQ8288C27': 10898.46,
    'MQ8288C50': 10898.46, 'MQ8288C56': 13324.17, 'MQ8288C57': 10898.46,
    'MQ8288C58': 10898.46, 'MQ8288D37': 29069.13, 'MQ8288F18': 29069.13,
    'MQ8288L01': 50260.86, 'MQ8288L05': 50260.86, 'MQ8288S01': 23012.24,
    'MQ8601C25': 24527.70, 'MQ8601D37': 24527.70, 'MQ8601F18': 24527.70,
    'MQ8637': 10598.33,
    'MQ8701C27': 43603.70, 'MQ8701D37': 43603.70, 'MQ8701F18': 43603.70,
    'MQ8702C25': 24527.70, 'MQ8702D37': 24527.70, 'MQ8702F18': 24527.70,
    'MT7002': 86828.82,
    'TB2009Z': 11577.18, 'TB2021Z': 10419.46, 'TB2060Z': 15677.43,
    'TB2061Z': 7637.72, 'TB2062Z': 16883.38, 'TB2211Z': 8843.68,
    'TB2236Z': 18089.34, 'TB2267Z': 9647.65,
    'TB3003Z': 57885.88,
    'TB5012AZ': 11255.59, 'TB5012ZP56': 19295.29,
    'TB5029ZP27': 20903.24, 'TB5029ZP56': 20903.24,
    'TB5031ZP27': 32158.82, 'TB5031ZP56': 32158.82,
    'TB5036ZP27': 25727.06, 'TB5036ZP56': 25727.06,
    'TB5037Z': 19295.29,
    'TB5050ZP27': 9647.65, 'TB5050ZP56': 9647.65,
    'TB5202Z': 14471.47,
    'TB6002Z': 10419.46,
    'TB7001ZKP22': 28942.94, 'TB7001ZKP27': 28942.94,
    'TB7001ZKP56': 28942.94, 'TB7001ZKP57': 28942.94,
    'TB7003Z': 26627.51,
    'TB7003ZKP22': 28942.94, 'TB7003ZKP27': 28942.94,
    'TB7003ZKP56': 28942.94, 'TB7003ZKP57': 28942.94,
    'TB7015Z': 5788.59, 'TB7202Z': 7525.16, 'TB7206Z': 28942.94,
    'TB7257Z': 6946.31, 'TB7261Z': 11577.18,
    'TB8011ZC25': 37625.82, 'TB8011ZD37': 31837.24, 'TB8011ZF18': 37625.82,
    'TB8012ZC25': 26048.65, 'TB8012ZD37': 20260.06, 'TB8012ZF18': 26048.65,
    'TB8017ZKP22': 20260.06, 'TB8017ZKP27': 20260.06,
    'TB8017ZKP56': 20260.06, 'TB8017ZKP57': 20260.06,
    'TB8028ZKP22': 14471.47, 'TB8028ZKP27': 14471.47,
    'TB8028ZKP56': 14471.47, 'TB8028ZKP57': 14471.47,
    'TB8035ZKP22': 18812.91, 'TB8035ZKP27': 18812.91,
    'TB8035ZKP56': 18812.91, 'TB8035ZKP57': 18812.91,
    'TB8060Z': 101300.29, 'TB8062Z': 101300.29,
    'TB8125ZL52': 86828.82, 'TB8125ZL54': 72357.35,
    'TB8126ZD37': 101300.29, 'TB8126ZF18': 115771.76,
    'TB8150Z': 130243.24, 'TB8151Z': 130243.24,
    'TB8153ZC25': 49203.00, 'TB8153ZD37': 43414.41, 'TB8153ZF18': 49203.00,
    'TB8167ZKC22': 28942.94, 'TB8167ZKC27': 28942.94,
    'TB8167ZKC50': 28942.94, 'TB8167ZKC57': 28942.94,
    'TB8167ZKD37': 54991.59, 'TB8167ZKF18': 60780.18,
    'TB8168ZKC22': 37625.82, 'TB8168ZKC27': 37625.82,
    'TB8168ZKC50': 37625.82, 'TB8168ZKC57': 37625.82,
    'TB8168ZKD37': 63674.47, 'TB8168ZKF18': 69463.06,
    'TB8170ZKG56': 28364.08, 'TB8170ZKG57': 28364.08,
    'TB8171ZKG56': 24890.93, 'TB8171ZKG57': 24890.93,
    'TB8173Z': 115771.76, 'TB8175Z': 144714.71,
    'TB8213ZKC02': 20260.06, 'TB8213ZKC22': 20260.06,
    'TB8213ZKC27': 20260.06, 'TB8213ZKC50': 20260.06,
    'TB8213ZKC56': 22575.49, 'TB8213ZKC57': 20260.06,
    'TB8213ZKD37': 37625.82, 'TB8213ZKF18': 37625.82, 'TB8213ZKS01': 31837.24,
    'TB8217ZKC02': 28942.94, 'TB8217ZKC22': 28942.94,
    'TB8217ZKC27': 28942.94, 'TB8217ZKC50': 28942.94,
    'TB8217ZKC56': 31258.38, 'TB8217ZKC57': 28942.94, 'TB8217ZKC58': 28942.94,
    'TB8217ZKD37': 46308.71, 'TB8217ZKF18': 46308.71,
    'TB8217ZKL01': 81184.95, 'TB8217ZKL05': 81184.95, 'TB8217ZKS01': 40520.12,
    'TB8223ZKC22': 31837.24, 'TB8223ZKC27': 31837.24,
    'TB8223ZKC50': 31837.24, 'TB8223ZKC57': 31837.24,
    'TB8223ZKD37': 57885.88, 'TB8223ZKF18': 63674.47,
    'TB8225ZC27': 52097.29, 'TB8225ZD37': 72357.35, 'TB8225ZF18': 72357.35,
    'TB8226ZC27': 54991.59, 'TB8226ZD37': 75251.65, 'TB8226ZF18': 75251.65,
    'TB8228ZKC02': 23154.35, 'TB8228ZKC22': 23154.35,
    'TB8228ZKC27': 23154.35, 'TB8228ZKC50': 23154.35,
    'TB8228ZKC56': 25469.79, 'TB8228ZKC57': 23154.35,
    'TB8228ZKD37': 40520.12, 'TB8228ZKF18': 40520.12,
    'TB8228ZKL01': 72791.50, 'TB8228ZKL05': 72791.50, 'TB8228ZKS01': 34731.53,
    'TB8261Z': 72357.35, 'TB8262Z': 101300.29,
    'TB8303Z': 37625.82, 'TB8305Z': 21707.21,
    'TB8317ZC27': 60201.32, 'TB8317ZD37': 80461.38, 'TB8317ZF18': 80461.38,
    'TB8358ZKP27': 12156.04, 'TB8358ZKP57': 12156.04,
    'TB8363ZC27': 18812.91,
    'TB8365ZKP27': 15050.33, 'TB8365ZKP57': 15050.33,
    'TB8392ZC25': 45968.20,
    'TB8396ZC25': 85807.31, 'TB8397ZC25': 45968.20,
    'TB8509ZS09': 76613.67,
}


@router.get("/admin/apply-price-update")
def admin_apply_price_update(
    token: str = Query(...),
    commit: bool = Query(False),
    db: Session = Depends(get_db)
):
    """One-time admin endpoint to apply Jul 2026 automation price updates."""
    if token != _PRICE_UPDATE_TOKEN:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Invalid token")

    results = {"updated": [], "skipped_not_found": [], "skipped_no_change": []}

    for sku, new_price in _NEW_PRICES.items():
        product = db.query(models.Product).filter(
            models.Product.sku == sku,
            models.Product.category == "automation"
        ).first()
        if not product:
            results["skipped_not_found"].append(sku)
            continue
        old_price = float(product.unit_price) if product.unit_price else 0.0
        if abs(old_price - new_price) < 0.01:
            results["skipped_no_change"].append(sku)
            continue
        results["updated"].append({
            "sku": sku,
            "old": old_price,
            "new": new_price,
            "pct": round((new_price - old_price) / old_price * 100, 1) if old_price else None
        })
        if commit:
            product.unit_price = new_price

    if commit:
        db.commit()

    return {
        "mode": "COMMITTED" if commit else "DRY_RUN",
        "total_updated": len(results["updated"]),
        "not_found_in_db": len(results["skipped_not_found"]),
        "no_change": len(results["skipped_no_change"]),
        "details": results
    }
