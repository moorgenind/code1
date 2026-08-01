"""
Creates the Architectural Lighting BOQ for LD-2526-031 (Mythili Residence, lead_id 89)
from "moorgen BOQ - Mythili Residence 230626.pdf" (50 line items).

Mirrors the exact logic of POST /boqs/ in app/routers/boqs.py:
- auto-generates boq_code
- auto-increments version for this lead_id + category
- computes line_total = qty * unit_price * (1 - discount_pct/100)
- sums total_amount
- sets lead.status = "boq_in_progress"

Run from the code1/ directory:
    python3 create_boq_mythili.py
"""
from decimal import Decimal
from datetime import datetime

from app.database import SessionLocal
from app import models

LEAD_ID = 89
CATEGORY = "architectural"
CREATED_BY = "Hindu"

# (level, area, product_sku, product_name, unit, qty, unit_price, brand, description)
ROWS = [
    ("Main Floor", "Art work", "MB3681B32412", "SPOTLIGHT - M MAGNETIC TRACK", "pcs", 15, "8474.35", "Moorgen", "Power: 12W | LED Temperature: 3000KK | Body Colour: Black | Lighting Brand: Moorgen"),
    ("Main Floor", "Art Work", "MB3652", "2000 Pre-installed Track", "mtrs", 4, "7477.37", "Moorgen", "Power: / | LED Temperature: /K | Body Colour: Black | Lighting Brand: Moorgen"),
    ("Main Floor", "Art Work", "MB3668", "0-10V magnetic track power supply box", "pcs", 4, "2492.46", "Moorgen", "Power: / | LED Temperature: /K | Body Colour: Black | Lighting Brand: Moorgen"),
    ("Main Floor", "Art Work", "MB3664", "Splicing power supply box", "pcs", 3, "498.49", "Moorgen", "Power: / | LED Temperature: /K | Body Colour: Black | Lighting Brand: Moorgen"),
    ("Main Floor", "Art Work", "MB3665", "Corner power supply box", "pcs", 2, "498.49", "Moorgen", "Power: / | LED Temperature: /K | Body Colour: Black | Lighting Brand: Moorgen"),
    ("Main Floor", "Art Work", "MB3661", "Plaster Coated L-shaped Flat Corner", "pcs", 2, "1495.47", "Moorgen", "Power: / | LED Temperature: /K | Body Colour: Black | Lighting Brand: Moorgen"),
    ("Main Floor", "Art Work", "OEM-PSU-100W-48V", "External PSU 100W 48V (0-10V) (sized for ~48W)", "pcs", 1, "2800.00", "OEM", ""),
    ("Main Floor", "Bedroom 1", "OEM-CPL-001", "Cove Profile Light", "mtrs", 18, "800.00", "OEM", ""),
    ("Main Floor", "Bedroom 1", "ARCH-MB3801W53612", "HAWAII - 55 ROUND - ADJUSTABLE - WHITE TRIM", "pcs", 6, "5608.02", "Moorgen", "HAWAII | CCT: 3500K | Beam: 36° | Power: 12W | Voltage: 36V | Current: 250mA | LED: CITIZEN | CRI: 90 | Cutout: 55mm"),
    ("Main Floor", "Bedroom 1", "OEM-RLP-001", "Recessed Linear Profile Light", "mtrs", 3, "800.00", "OEM", ""),
    ("Main Floor", "Bedroom 1 dressing", "ARCH-MB3801W53612", "HAWAII - 55 ROUND - ADJUSTABLE - WHITE TRIM", "pcs", 2, "5608.02", "Moorgen", "HAWAII | CCT: 3500K | Beam: 36° | Power: 12W | Voltage: 36V | Current: 250mA | LED: CITIZEN | CRI: 90 | Cutout: 55mm"),
    ("Main Floor", "Bedroom 1 Toilet", "ARCH-MB3930W5249", "HAWAII - 35 ROUND - ADJUSTABLE - TRIM", "pcs", 4, "4154.09", "Moorgen", "HAWAII | CCT: 3500K | Beam: 24° | Power: 9W | Voltage: 36V | Current: 200mA | Body: White | LED: ZMOLED | CRI: 90 | Cutout: 35mm"),
    ("Main Floor", "Dining area", "ARCH-MB3801W53612", "HAWAII - 55 ROUND - ADJUSTABLE - WHITE TRIM", "pcs", 8, "5608.02", "Moorgen", "HAWAII | CCT: 3500K | Beam: 36° | Power: 12W | Voltage: 36V | Current: 250mA | LED: CITIZEN | CRI: 90 | Cutout: 55mm"),
    ("Main Floor", "Dining area", "OEM-CG-001", "Curtain Grazer", "mtrs", 6, "3200.00", "OEM", ""),
    ("Main Floor", "Dining area", "OEM-CVP-001", "Curve Profile", "pcs", 3, "1250.00", "OEM", ""),
    ("Main Floor", "Dining area", "OEM-FLP-001", "Flex Profile Light", "mtrs", 9, "1200.00", "OEM", ""),
    ("Main Floor", "Drawing area", "ARCH-MB3543B3159", "JAZZ SERIES - 35 SPOTLIGHT RECESSED - ADJUSTABLE - BLACK", "pcs", 2, "4984.91", "Moorgen", "JAZZ SERIES | CCT: 3000K | Beam: 15° | Power: 9W | Voltage: 36V | Current: 250mA | Body: Black | LED: ZMOLED | CRI: 90 | Cutout: 35mm"),
    ("Main Floor", "Drawing area", "OEM-FLP-001", "Flex Profile Light", "mtrs", 20, "1200.00", "OEM", ""),
    ("Main Floor", "Drawing area", "ARCH-MB3801W53612", "HAWAII - 55 ROUND - ADJUSTABLE - WHITE TRIM", "pcs", 5, "5608.02", "Moorgen", "HAWAII | CCT: 3500K | Beam: 36° | Power: 12W | Voltage: 36V | Current: 250mA | LED: CITIZEN | CRI: 90 | Cutout: 55mm"),
    ("Main Floor", "Dry Kitchen", "OEM-RLP-001", "Recessed Linear Profile Light", "mtrs", 8, "800.00", "OEM", ""),
    ("Main Floor", "Entertainment room", "ARCH-MB3801W53612", "HAWAII - 55 ROUND - ADJUSTABLE - WHITE TRIM", "pcs", 1, "5608.02", "Moorgen", "HAWAII | CCT: 3500K | Beam: 36° | Power: 12W | Voltage: 36V | Current: 250mA | LED: CITIZEN | CRI: 90 | Cutout: 55mm"),
    ("Main Floor", "Entertainment room", "OEM-RLP-001", "Recessed Linear Profile Light", "mtrs", 12, "800.00", "OEM", ""),
    ("Main Floor", "Entertainment room", "OEM-CG-001", "Curtain Grazer", "mtrs", 10, "3200.00", "OEM", ""),
    ("Main Floor", "Entertainment room", "ARCH-MB3930W5249", "HAWAII - 35 ROUND - ADJUSTABLE - TRIM", "pcs", 12, "4154.09", "Moorgen", "HAWAII | CCT: 3500K | Beam: 24° | Power: 9W | Voltage: 36V | Current: 200mA | Body: White | LED: ZMOLED | CRI: 90 | Cutout: 35mm"),
    ("Main Floor", "Entertainment room Toilet", "ARCH-MB3930W5249", "HAWAII - 35 ROUND - ADJUSTABLE - TRIM", "pcs", 4, "4154.09", "Moorgen", "HAWAII | CCT: 3500K | Beam: 24° | Power: 9W | Voltage: 36V | Current: 200mA | Body: White | LED: ZMOLED | CRI: 90 | Cutout: 35mm"),
    ("Main Floor", "Laundry", "OEM-COB12-001", "12W COB", "pcs", 2, "1800.00", "OEM", ""),
    ("Main Floor", "Living area", "ARCH-MB3801W53612", "HAWAII - 55 ROUND - ADJUSTABLE - WHITE TRIM", "pcs", 10, "5608.02", "Moorgen", "HAWAII | CCT: 3500K | Beam: 36° | Power: 12W | Voltage: 36V | Current: 250mA | LED: CITIZEN | CRI: 90 | Cutout: 55mm"),
    ("Main Floor", "Living area", "OEM-FLP-001", "Flex Profile Light", "mtrs", 20, "1200.00", "OEM", ""),
    ("Main Floor", "Maid room", "OEM-COB12-001", "12W COB", "pcs", 6, "1800.00", "OEM", ""),
    ("Main Floor", "Maid Toilet", "OEM-COB12-001", "12W COB", "pcs", 1, "1800.00", "OEM", ""),
    ("Main Floor", "Master Bedroom", "OEM-CPL-001", "Cove Profile Light", "mtrs", 12, "800.00", "OEM", ""),
    ("Main Floor", "Master Bedroom", "OEM-TSC-001", "Tunable Stretch Ceiling", "sft", 50, "1200.00", "OEM", ""),
    ("Main Floor", "Master Bedroom", "ARCH-MB3801W53612", "HAWAII - 55 ROUND - ADJUSTABLE - WHITE TRIM", "pcs", 3, "5608.02", "Moorgen", "HAWAII | CCT: 3500K | Beam: 36° | Power: 12W | Voltage: 36V | Current: 250mA | LED: CITIZEN | CRI: 90 | Cutout: 55mm"),
    ("Main Floor", "Master Bedroom", "OEM-RLP-001", "Recessed Linear Profile Light", "mtrs", 10, "800.00", "OEM", ""),
    ("Main Floor", "Master Bedroom Closet", "OEM-RLP-001", "Recessed Linear Profile Light", "mtrs", 8, "800.00", "OEM", ""),
    ("Main Floor", "Master Bedroom Toilet", "ARCH-MB3930W5249", "HAWAII - 35 ROUND - ADJUSTABLE - TRIM", "pcs", 4, "4154.09", "Moorgen", "HAWAII | CCT: 3500K | Beam: 24° | Power: 9W | Voltage: 36V | Current: 200mA | Body: White | LED: ZMOLED | CRI: 90 | Cutout: 35mm"),
    ("Main Floor", "Photography studio", "ARCH-MB3801W53612", "HAWAII - 55 ROUND - ADJUSTABLE - WHITE TRIM", "pcs", 9, "5608.02", "Moorgen", "HAWAII | CCT: 3500K | Beam: 36° | Power: 12W | Voltage: 36V | Current: 250mA | LED: CITIZEN | CRI: 90 | Cutout: 55mm"),
    ("Main Floor", "Photography Studio", "OEM-RLP-001", "Recessed Linear Profile Light (Black Profile)", "mtrs", 6, "800.00", "OEM", ""),
    ("Main Floor", "Photography Studio", "OEM-CG-001", "Curtain Grazer", "mtrs", 5, "3200.00", "OEM", ""),
    ("Main Floor", "Photography Studio Toilet", "ARCH-MB3930W5249", "HAWAII - 35 ROUND - ADJUSTABLE - TRIM", "pcs", 4, "4154.09", "Moorgen", "HAWAII | CCT: 3500K | Beam: 24° | Power: 9W | Voltage: 36V | Current: 200mA | Body: White | LED: ZMOLED | CRI: 90 | Cutout: 35mm"),
    ("Main Floor", "Powder Room", "OEM-STC-001", "Stretch Ceiling", "sft", 25, "1000.00", "OEM", ""),
    ("Main Floor", "Powder Room", "ARCH-MB3930W5249", "HAWAII - 35 ROUND - ADJUSTABLE - TRIM", "pcs", 2, "4154.09", "Moorgen", "HAWAII | CCT: 3000K | Beam: 24° | Power: 9W | Voltage: 36V | Current: 200mA | Body: White | LED: ZMOLED | CRI: 90 | Cutout: 35mm"),
    ("Main Floor", "Puja", "ARCH-MB3801W53612", "HAWAII - 55 ROUND - ADJUSTABLE - WHITE TRIM", "pcs", 4, "5608.02", "Moorgen", "HAWAII | CCT: 3500K | Beam: 36° | Power: 12W | Voltage: 36V | Current: 250mA | LED: CITIZEN | CRI: 90 | Cutout: 55mm"),
    ("Main Floor", "Sink area", "OEM-COB12-001", "12W COB", "pcs", 2, "1800.00", "OEM", ""),
    ("Main Floor", "Sitout", "ARCH-MB3801W53612", "HAWAII - 55 ROUND - ADJUSTABLE - WHITE TRIM", "pcs", 4, "5608.02", "Moorgen", "HAWAII | CCT: 3500K | Beam: 36° | Power: 12W | Voltage: 36V | Current: 250mA | LED: CITIZEN | CRI: 90 | Cutout: 55mm"),
    ("Main Floor", "Utility", "OEM-COB12-001", "12W COB", "pcs", 6, "1800.00", "OEM", ""),
    ("Main Floor", "Wet Kitchen", "ARCH-MB3801W53612", "HAWAII - 55 ROUND - ADJUSTABLE - WHITE TRIM", "pcs", 4, "5608.02", "Moorgen", "HAWAII | CCT: 3500K | Beam: 36° | Power: 12W | Voltage: 36V | Current: 250mA | LED: CITIZEN | CRI: 90 | Cutout: 55mm"),
    ("Main Floor", "12W Fixtures", None, "12W DALI Driver", "pcs", 63, "1200.00", "", ""),
    ("Main Floor", "9W Fixtures", None, "9W DALI Driver", "pcs", 14, "1200.00", "", ""),
    ("Main Floor", "Cove + Curtain Strip", None, "DALI Driver 24V 120W", "pcs", 25, "4600.00", "", ""),
]


def calc_line_total(qty, unit_price, discount_pct=Decimal("0")):
    subtotal = Decimal(qty) * unit_price
    discount = subtotal * (discount_pct / Decimal("100"))
    return subtotal - discount


def make_notes(unit, brand, description):
    parts = [f"Unit: {unit}"]
    if brand:
        parts.append(f"Brand: {brand}")
    if description:
        parts.append(description)
    return " | ".join(parts)


def main():
    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter(models.Lead.lead_id == LEAD_ID).first()
        if not lead:
            print(f"STOP: lead_id {LEAD_ID} not found.")
            return

        # boq_code (same scheme as create_boq)
        year = datetime.now().year
        short_year = str(year)[2:]
        next_year_short = str(year + 1)[2:]
        count = db.query(models.Boq).count()
        boq_code = f"BOQ-{short_year}{next_year_short}-{str(count + 1).zfill(3)}"

        # version (per lead_id + category)
        existing = (
            db.query(models.Boq)
            .filter(models.Boq.lead_id == LEAD_ID, models.Boq.category == CATEGORY)
            .order_by(models.Boq.version.desc())
            .first()
        )
        version = (existing.version + 1) if existing else 1

        boq = models.Boq(
            boq_code=boq_code,
            lead_id=LEAD_ID,
            category=CATEGORY,
            version=version,
            status="draft",
            created_by=CREATED_BY,
        )
        db.add(boq)
        db.flush()

        for level, area, sku, name, unit, qty, price, brand, desc in ROWS:
            unit_price = Decimal(price)
            line_total = calc_line_total(qty, unit_price)
            db.add(models.BoqLineItem(
                boq_id=boq.boq_id,
                level=level,
                area=area,
                product_sku=sku,
                product_name=name,
                quantity=qty,
                unit_price=unit_price,
                discount_pct=Decimal("0"),
                line_total=line_total,
                notes=make_notes(unit, brand, desc),
            ))

        db.flush()
        boq.total_amount = sum(item.line_total for item in boq.line_items if item.line_total)
        lead.status = "boq_in_progress"

        db.commit()
        db.refresh(boq)

        print(f"Created {boq.boq_code} (boq_id={boq.boq_id}) v{boq.version} for lead_id {LEAD_ID}")
        print(f"Line items: {len(boq.line_items)}")
        print(f"Total amount: Rs {boq.total_amount}")
        print(f"Lead status -> {lead.status}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
