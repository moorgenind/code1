from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
from decimal import Decimal

from app.database import get_db
from app import models, schemas

router = APIRouter()


# =========================================
# HELPERS
# =========================================
def calculate_line_total(
    quantity: int,
    unit_price: Decimal,
    discount_pct: Decimal
) -> Decimal:
    subtotal = Decimal(quantity) * unit_price
    discount = subtotal * (discount_pct / Decimal("100"))
    return subtotal - discount


def calculate_boq_total(line_items: list) -> Decimal:
    return sum(item.line_total for item in line_items if item.line_total)


# =========================================
# ROUTES
# =========================================
@router.get("/", response_model=List[schemas.BoqResponse])
def list_boqs(
    lead_id: int = None,
    status: str = None,
    category: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Boq)

    if lead_id:
        query = query.filter(models.Boq.lead_id == lead_id)
    if status:
        query = query.filter(models.Boq.status == status)
    if category:
        query = query.filter(models.Boq.category == category)

    return query.order_by(models.Boq.created_at.desc()).all()


@router.get("/{boq_id}", response_model=schemas.BoqResponse)
def get_boq(boq_id: int, db: Session = Depends(get_db)):
    boq = db.query(models.Boq).filter(models.Boq.boq_id == boq_id).first()
    if not boq:
        raise HTTPException(status_code=404, detail="BOQ not found")
    return boq


@router.post("/", response_model=schemas.BoqResponse)
def create_boq(payload: schemas.BoqCreate, db: Session = Depends(get_db)):
    # Check lead exists
    lead = db.query(models.Lead).filter(
        models.Lead.lead_id == payload.lead_id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Generate BOQ code
    year = datetime.now().year
    short_year = str(year)[2:]
    next_year_short = str(year + 1)[2:]
    count = db.query(models.Boq).count()
    boq_code = f"BOQ-{short_year}{next_year_short}-{str(count + 1).zfill(3)}"

    # Check version — if BOQ exists for this lead+category, increment
    existing = db.query(models.Boq).filter(
        models.Boq.lead_id == payload.lead_id,
        models.Boq.category == payload.category,
    ).order_by(models.Boq.version.desc()).first()

    version = (existing.version + 1) if existing else 1

    # Create BOQ
    boq = models.Boq(
        boq_code=boq_code,
        lead_id=payload.lead_id,
        category=payload.category,
        version=version,
        status="draft",
        created_by=payload.created_by,
    )

    db.add(boq)
    db.flush()

    # Add line items
    for item in payload.line_items:
        line_total = calculate_line_total(
            quantity=item.quantity,
            unit_price=item.unit_price,
            discount_pct=item.discount_pct or Decimal("0"),
        )

        line_item = models.BoqLineItem(
            boq_id=boq.boq_id,
            level=item.level,
            area=item.area,
            product_sku=item.product_sku,
            product_name=item.product_name,
            quantity=item.quantity,
            unit_price=item.unit_price,
            discount_pct=item.discount_pct or Decimal("0"),
            line_total=line_total,
            notes=item.notes,
        image_url=getattr(item, "image_url", None),
        )
        db.add(line_item)

    db.flush()

    # Calculate and save total
    boq.total_amount = calculate_boq_total(boq.line_items)

    # Update lead status
    lead.status = "boq_in_progress"

    db.commit()
    db.refresh(boq)
    return boq


@router.post("/{boq_id}/line-items", response_model=schemas.BoqResponse)
def add_line_item(
    boq_id: int,
    item: schemas.BoqLineItemCreate,
    db: Session = Depends(get_db)
):
    boq = db.query(models.Boq).filter(models.Boq.boq_id == boq_id).first()
    if not boq:
        raise HTTPException(status_code=404, detail="BOQ not found")

    line_total = calculate_line_total(
        quantity=item.quantity,
        unit_price=item.unit_price,
        discount_pct=item.discount_pct or Decimal("0"),
    )

    line_item = models.BoqLineItem(
        boq_id=boq_id,
        level=item.level,
        area=item.area,
        product_sku=item.product_sku,
        product_name=item.product_name,
        quantity=item.quantity,
        unit_price=item.unit_price,
        discount_pct=item.discount_pct or Decimal("0"),
        line_total=line_total,
        notes=item.notes,
    )

    db.add(line_item)
    db.flush()

    # Recalculate BOQ total
    boq.total_amount = calculate_boq_total(boq.line_items)

    db.commit()
    db.refresh(boq)
    return boq


@router.patch("/{boq_id}/status", response_model=schemas.BoqResponse)
def update_boq_status(
    boq_id: int,
    payload: schemas.BoqStatusUpdate,
    db: Session = Depends(get_db)
):
    boq = db.query(models.Boq).filter(models.Boq.boq_id == boq_id).first()
    if not boq:
        raise HTTPException(status_code=404, detail="BOQ not found")

    boq.status = payload.status

    if payload.drive_quote_url:
        boq.drive_quote_url = payload.drive_quote_url

    if payload.status == "approved":
        boq.approved_at = datetime.now()
        # Update lead status
        lead = db.query(models.Lead).filter(
            models.Lead.lead_id == boq.lead_id
        ).first()
        if lead:
            lead.status = "quote_sent"

    db.commit()
    db.refresh(boq)
    return boq


@router.delete("/{boq_id}/line-items/{line_item_id}")
def delete_line_item(
    boq_id: int,
    line_item_id: int,
    db: Session = Depends(get_db)
):
    item = db.query(models.BoqLineItem).filter(
        models.BoqLineItem.line_item_id == line_item_id,
        models.BoqLineItem.boq_id == boq_id,
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Line item not found")

    db.delete(item)
    db.flush()

    # Recalculate BOQ total
    boq = db.query(models.Boq).filter(models.Boq.boq_id == boq_id).first()
    boq.total_amount = calculate_boq_total(boq.line_items)

    db.commit()
    return {"success": True, "message": f"Line item {line_item_id} deleted"}


BOQ_IMAGES_FOLDER_ID = "1HeXvo_bjGU6RooXz3aCWnyw74KpvEmZL"

@router.post("/{boq_id}/line-items/{line_item_id}/image")
async def upload_line_item_image(
    boq_id: int,
    line_item_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload an image for a line item and store it in Drive."""
    from app.drive import get_drive_service
    from googleapiclient.http import MediaIoBaseUpload
    import io

    line_item = db.query(models.BoqLineItem).filter(
        models.BoqLineItem.line_item_id == line_item_id,
        models.BoqLineItem.boq_id == boq_id
    ).first()
    if not line_item:
        raise HTTPException(status_code=404, detail="Line item not found")

    contents = await file.read()
    drive = get_drive_service()
    media = MediaIoBaseUpload(io.BytesIO(contents), mimetype=file.content_type)
    uploaded = drive.files().create(
        body={"name": file.filename, "parents": [BOQ_IMAGES_FOLDER_ID]},
        media_body=media,
        fields="id",
        supportsAllDrives=True
    ).execute()

    file_id = uploaded["id"]
    # Make file publicly readable
    drive.permissions().create(
        fileId=file_id,
        body={"role": "reader", "type": "anyone"},
        supportsAllDrives=True
    ).execute()

    image_url = f"https://drive.google.com/thumbnail?id={file_id}&sz=w200"
    line_item.image_url = image_url
    db.commit()
    return {"image_url": image_url}
