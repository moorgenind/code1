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
