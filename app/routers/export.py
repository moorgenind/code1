from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
import pickle, base64, os, requests
from datetime import datetime
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

router = APIRouter()

MOORGEN_LOGO_URL = "https://drive.google.com/uc?export=download&id=1_logo_file_id"
MOORGEN_LOGO_DRIVE_ID = "1HeXvo_bjGU6RooXz3aCWcxr8eoDsfaIR2"  # boq_images folder

def get_terms(category):
    if category == 'decorative':
        advance, delivery = "80%", "60-90"
    elif category == 'automation':
        advance, delivery = "60%", "45-90"
    else:
        advance, delivery = "60%", "45-60"
    return [
        "Prices valid for 15 days from date of quotation.",
        f"{advance} advance required to confirm the order; balance before dispatch.",
        f"Delivery: {delivery} working days from order confirmation.",
        "Installation not included unless separately agreed in writing.",
        "Drivers and control gear added after layouts are finalized.",
        "Prices subject to change without notice.",
        "No returns under any circumstances.",
    ]

def get_creds():
    token_b64 = os.getenv("GOOGLE_TOKEN_BASE64")
    if token_b64:
        creds = pickle.loads(base64.b64decode(token_b64))
    else:
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        with open(os.path.join(BASE_DIR, "token.pickle"), "rb") as f:
            creds = pickle.load(f)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds

def get_sheets():
    return build("sheets", "v4", credentials=get_creds())

def get_drive():
    return build("drive", "v3", credentials=get_creds())

def get_product_name_from_db(sku, db=None):
    """Fetch full product name from DB by SKU for better image matching."""
    if not db or not sku:
        return None
    try:
        from app import models
        p = db.query(models.Product).filter(models.Product.sku == sku).first()
        return p.name if p else None
    except:
        return None

def get_image_url_for_sku(sku, product_name="", db=None):
    """Get Drive thumbnail URL using image_map.py"""
    try:
        from app.image_map import IMAGE_MAP
        # Try to get full product name from DB for better matching
        if db:
            db_name = get_product_name_from_db(sku, db)
            if db_name:
                product_name = db_name
        name = str(product_name or sku or "").lower()
        best = None
        best_score = 0
        for entry in IMAGE_MAP:
            score = 0
            family = entry.get("family", "").lower()
            entry_name = entry.get("name", "").lower()
            entry_color = entry.get("color", "").lower()
            entry_trim = entry.get("trim", "").lower()

            # For automation entries — detect by SKU prefix TB/MT/MQ
            is_automation_sku = str(sku or "").upper().startswith(("TB", "MT", "MQ"))
            is_oem_sku = str(sku or "").upper().startswith("OEM")
            is_dec_sku = str(sku or "").upper().startswith("DEC")
            if family == "automation":
                if not is_automation_sku:
                    continue
            elif family == "oem":
                if not is_oem_sku:
                    continue
                if entry_name and entry_name in name:
                    score += 3
            elif family == "decorative":
                if not is_dec_sku:
                    continue
                # Match by product_type from DB
                if db:
                    try:
                        from app import models
                        prod = db.query(models.Product).filter(models.Product.sku == sku).first()
                        if prod and prod.product_type:
                            ptype = prod.product_type.lower()
                            if entry_name and entry_name in ptype:
                                score += 3
                            elif entry_name and ptype in entry_name:
                                score += 3
                    except Exception:
                        pass
                if entry_name and entry_name in name:
                    score += 2
            else:
                if family and family in name:
                    score += 2
                if entry_name and entry_name in name:
                    score += 3
                if entry_trim and entry_trim in name:
                    score += 1
                if entry_color and entry_color in name:
                    score += 1

            if score > best_score:
                best_score = score
                best = entry

        if best and best_score >= 3:
            return 'https://drive.google.com/uc?export=view&id=' + best['id']
    except Exception as e:
        print(f"Image lookup error: {e}")
    return None

@router.post("/boq/{boq_id}/sheets")
def export_boq_to_sheets(boq_id: int, db: Session = Depends(get_db)):
    boq = db.query(models.Boq).filter(models.Boq.boq_id == boq_id).first()
    if not boq:
        raise HTTPException(status_code=404, detail="BOQ not found")

    lead = db.query(models.Lead).filter(models.Lead.lead_id == boq.lead_id).first()
    items = boq.line_items
    today = datetime.now().strftime("%d-%b-%Y")
    project_name = lead.project_name or lead.client_name or ""
    category_label = f"{boq.category.title()} Lighting" if boq.category else "Lighting"

    sheets = get_sheets()
    drive = get_drive()

    # Create spreadsheet with 2 tabs
    title = f"moorgen BOQ - {project_name}"
    spreadsheet = sheets.spreadsheets().create(body={
        "properties": {"title": title},
        "sheets": [
            {"properties": {"sheetId": 0, "title": "BOQ", "index": 1}},
            {"properties": {"sheetId": 1, "title": "Proposal Summary", "index": 0}},
        ]
    }).execute()

    ss_id = spreadsheet["spreadsheetId"]

    # ── BOQ Sheet Data ──────────────────────────────────
    boq_values = [
        ['=IMAGE("https://drive.google.com/uc?export=view&id=1eh_LL1RACtyrWeOtX0gb8H7pUaKlrD_k",4,60,250)', "", "", "", "", "", "", "", "", "", "", ""],  # Row 1 - logo
        ["", "", "", "", "", "", "", "", "", "", "", ""],
        [f"{category_label} – BOQ", "", "", "", "", "", "", "", "", "", "", ""],  # Row 3
        [f"Project: {project_name}", "", "", "", "", f"Date: {today}", "", "", "", "", "", ""],  # Row 4
        ["", "", "", "", "", "", "", "", "", "", "", ""],  # Row 5 empty
        ["S.No.", "Level", "Area", "Model No.", "Product Name", "Image", "Brand", "Description", "Unit", "Qty", "Unit Price (₹)", "Total Price (₹)"],  # Row 6 headers
    ]

    # Line items sorted by floor level (no header rows)
    LEVEL_ORDER = ['basement','ground floor','ground','first floor','first','second floor','second','third floor','third','fourth floor','fourth','fifth floor','fifth','sixth floor','sixth','terrace','roof','top floor','penthouse']
    def level_sort_key(l):
        try: return LEVEL_ORDER.index((l or '').lower())
        except: return 99
    from collections import OrderedDict
    grouped = OrderedDict()
    for item in items:
        lvl = item.level or 'Unassigned'
        if lvl not in grouped: grouped[lvl] = []
        grouped[lvl].append(item)
    sorted_levels = sorted(grouped.keys(), key=level_sort_key)
    sorted_items = []
    for level in sorted_levels:
        sorted_items.extend(grouped[level])
    level_header_rows = []
    for idx, item in enumerate(sorted_items, 1):
        desc = item.notes or ""
        is_oem = str(item.product_sku or "").upper().startswith("OEM")
        brand = "OEM" if is_oem else "Moorgen"
        # If no notes, try to get specs from DB
        if not desc and db:
            try:
                from app import models as _models
                prod = db.query(_models.Product).filter(_models.Product.sku == item.product_sku).first()
                if prod:
                    parts = []
                    if prod.cct: parts.append(f"CCT: {prod.cct}")
                    if prod.beam_angle: parts.append(f"Beam: {prod.beam_angle}")
                    if prod.power: parts.append(f"Power: {prod.power}")
                    if prod.body_color: parts.append(f"Color: {prod.body_color}")
                    if prod.cutout_size: parts.append(f"Cutout: {prod.cutout_size}mm")
                    if prod.specification: parts.append(prod.specification)
                    if prod.material: parts.append(prod.material)
                    desc = " | ".join(parts) if parts else (prod.name or "")
            except Exception:
                pass
        if not desc:
            desc = item.product_name or ""
        boq_values.append([
            idx,
            item.level or "",
            item.area or "",
            item.product_sku or "",
            item.product_name or "",
            "",  # Image placeholder
            brand,
            desc,
            "pcs",
            item.quantity or 0,
            float(item.unit_price or 0),
            float(item.line_total or 0),
        ])
    # Grand total row
    last_data_row = 6 + len(items)
    boq_values.append(["", "", "", "", "", "", "", "", "", "", "Grand Total", f"=SUM(L7:L{last_data_row})"])

    # ── Summary Sheet Data ──────────────────────────────
    total = float(boq.total_amount or 0)
    gst = round(total * 0.18, 2)
    grand_total = round(total + gst, 2)

    # Group by area
    # Single row summary by BOQ category
    category_label_map = {"architectural": "Architectural Lighting", "decorative": "Decorative Lighting", "automation": "Automation", "oem": "OEM Products", "smart_locks": "Smart Locks"}
    cat_display = category_label_map.get(boq.category, boq.category.title() if boq.category else "Lighting")
    total_amt = float(boq.total_amount or 0)
    category_label_map2 = {"architectural": "Architectural", "decorative": "Decorative", "automation": "Automation", "oem": "OEM", "smart_locks": "Smart Locks"}
    cat_display2 = category_label_map2.get(boq.category, boq.category.title() if boq.category else "Lighting")
    from datetime import date as _date
    today_long = _date.today().strftime("%B %-d, %Y")
    summary_values = [
        ["=IMAGE(\"https://drive.google.com/uc?export=view&id=1eh_LL1RACtyrWeOtX0gb8H7pUaKlrD_k\",4,60,250)", "", "", "", ""],
        ["", "", "", "", ""],
        ["Moorgen Lighting & Smart System", "", "", "", ""],
        ["BOQ & Pricing Proposal", "", "", "", ""],
        ["", "", "", "", ""],
        [f"Project Name: {project_name}", "", "", "", ""],
        [f"System Category: {cat_display2}", "", "", "", ""],
        [f"Date: {today_long}", "", "", "", ""],
        ["", "", "", "", ""],
        ["No.", "Sub-Item", "Total Price", "Remarks", ""],
    ]
    area_groups = {cat_display: total_amt}
    for i, (area, amt) in enumerate(area_groups.items(), 1):
        summary_values.append([i, area, f"₹{amt:,.2f}", "", ""])
    summary_values += [
        ["", "Total", f"₹{total:,.2f}", "", ""],
        ["", "18% GST", f"₹{gst:,.2f}", "", ""],
        ["", "Grand Total", f"₹{grand_total:,.2f}", "", ""],
        ["", "", "", "", ""],
        ["Terms & Conditions", "", "", "", ""],
    ]
    TERMS = get_terms(boq.category)
    for term in TERMS:
        summary_values.append([f"- {term}", "", "", "", ""])

    # ── Write data ──────────────────────────────────────
    sheets.spreadsheets().values().batchUpdate(
        spreadsheetId=ss_id,
        body={"valueInputOption": "USER_ENTERED", "data": [
            {"range": "BOQ!A1", "values": boq_values},
            {"range": "Proposal Summary!A1", "values": summary_values},
        ]}
    ).execute()

    # ── Formatting ──────────────────────────────────────
    header_row = 5  # 0-indexed row 6
    last_item_row = 6 + len(items)  # 0-indexed

    GREEN = {"red": 0.0, "green": 0.0, "blue": 0.0}  # black header like template
    WHITE = {"red": 1.0, "green": 1.0, "blue": 1.0}
    DARK = {"red": 0.1, "green": 0.1, "blue": 0.1}
    LIGHT_GRAY = {"red": 0.95, "green": 0.95, "blue": 0.95}

    requests_fmt = [
        # Logo row height 150px
        {"updateDimensionProperties": {
            "range": {"sheetId": 0, "dimension": "ROWS", "startIndex": 0, "endIndex": 1},
            "properties": {"pixelSize": 150}, "fields": "pixelSize"
        }},
        # Merge logo cell A1:C1
        {"mergeCells": {
            "range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 3},
            "mergeType": "MERGE_ALL"
        }},
        # Summary logo row height
        {"updateDimensionProperties": {
            "range": {"sheetId": 1, "dimension": "ROWS", "startIndex": 0, "endIndex": 1},
            "properties": {"pixelSize": 150}, "fields": "pixelSize"
        }},
        {"mergeCells": {
            "range": {"sheetId": 1, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 3},
            "mergeType": "MERGE_ALL"
        }},
        # Title row bold large
        {"repeatCell": {
            "range": {"sheetId": 0, "startRowIndex": 2, "endRowIndex": 3},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True, "fontSize": 14}}},
            "fields": "userEnteredFormat.textFormat"
        }},
        # Header row - black bg white text bold
        {"repeatCell": {
            "range": {"sheetId": 0, "startRowIndex": header_row, "endRowIndex": header_row + 1},
            "cell": {"userEnteredFormat": {
                "backgroundColor": {"red": 0.13, "green": 0.13, "blue": 0.13},
                "textFormat": {"bold": True, "foregroundColor": WHITE, "fontSize": 10},
                "horizontalAlignment": "CENTER",
                "verticalAlignment": "MIDDLE",
            }},
            "fields": "userEnteredFormat"
        }},
        # Freeze header row
        {"updateSheetProperties": {
            "properties": {"sheetId": 0, "gridProperties": {"frozenRowCount": header_row + 1}},
            "fields": "gridProperties.frozenRowCount"
        }},

        # Column widths BOQ
        {"updateDimensionProperties": {
            "range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1},
            "properties": {"pixelSize": 55}, "fields": "pixelSize"
        }},
        {"updateDimensionProperties": {
            "range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 2},
            "properties": {"pixelSize": 110}, "fields": "pixelSize"
        }},
        {"updateDimensionProperties": {
            "range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 2, "endIndex": 3},
            "properties": {"pixelSize": 110}, "fields": "pixelSize"
        }},
        {"updateDimensionProperties": {
            "range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 3, "endIndex": 4},
            "properties": {"pixelSize": 150}, "fields": "pixelSize"
        }},
        {"updateDimensionProperties": {
            "range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 4, "endIndex": 5},
            "properties": {"pixelSize": 220}, "fields": "pixelSize"
        }},
        {"updateDimensionProperties": {
            "range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 5, "endIndex": 6},
            "properties": {"pixelSize": 120}, "fields": "pixelSize"
        }},
        {"updateDimensionProperties": {
            "range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 6, "endIndex": 7},
            "properties": {"pixelSize": 90}, "fields": "pixelSize"
        }},
        {"updateDimensionProperties": {
            "range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 7, "endIndex": 8},
            "properties": {"pixelSize": 300}, "fields": "pixelSize"
        }},
        {"updateDimensionProperties": {
            "range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 8, "endIndex": 9},
            "properties": {"pixelSize": 55}, "fields": "pixelSize"
        }},
        {"updateDimensionProperties": {
            "range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 9, "endIndex": 10},
            "properties": {"pixelSize": 55}, "fields": "pixelSize"
        }},
        {"updateDimensionProperties": {
            "range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 10, "endIndex": 11},
            "properties": {"pixelSize": 130}, "fields": "pixelSize"
        }},
        {"updateDimensionProperties": {
            "range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 11, "endIndex": 12},
            "properties": {"pixelSize": 130}, "fields": "pixelSize"
        }},
        # Row heights for data rows (tall for images)
        {"updateDimensionProperties": {
            "range": {"sheetId": 0, "dimension": "ROWS", "startIndex": header_row + 1, "endIndex": last_item_row},
            "properties": {"pixelSize": 80}, "fields": "pixelSize"
        }},
        # Borders on header
        {"updateBorders": {
            "range": {"sheetId": 0, "startRowIndex": header_row, "endRowIndex": last_item_row + 1, "startColumnIndex": 0, "endColumnIndex": 12},
            "top": {"style": "SOLID", "color": {"red": 0.7, "green": 0.7, "blue": 0.7}},
            "bottom": {"style": "SOLID", "color": {"red": 0.7, "green": 0.7, "blue": 0.7}},
            "left": {"style": "SOLID", "color": {"red": 0.7, "green": 0.7, "blue": 0.7}},
            "right": {"style": "SOLID", "color": {"red": 0.7, "green": 0.7, "blue": 0.7}},
            "innerHorizontal": {"style": "SOLID", "color": {"red": 0.85, "green": 0.85, "blue": 0.85}},
            "innerVertical": {"style": "SOLID", "color": {"red": 0.85, "green": 0.85, "blue": 0.85}},
        }},
        # Wrap text for description column
        {"repeatCell": {
            "range": {"sheetId": 0, "startRowIndex": header_row + 1, "endRowIndex": last_item_row, "startColumnIndex": 7, "endColumnIndex": 8},
            "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP", "verticalAlignment": "TOP", "textFormat": {"fontSize": 8}}},
            "fields": "userEnteredFormat"
        }},
        {"repeatCell": {
            "range": {"sheetId": 0, "startRowIndex": header_row, "endRowIndex": last_item_row + 2, "startColumnIndex": 0, "endColumnIndex": 12},
            "cell": {"userEnteredFormat": {"horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE", "wrapStrategy": "WRAP", "textFormat": {"fontFamily": "Arial", "fontSize": 10}}},
            "fields": "userEnteredFormat(horizontalAlignment,verticalAlignment,wrapStrategy,textFormat)"
        }},
        {"repeatCell": {
            "range": {"sheetId": 0, "startRowIndex": header_row, "endRowIndex": header_row + 1, "startColumnIndex": 0, "endColumnIndex": 12},
            "cell": {"userEnteredFormat": {"textFormat": {"fontFamily": "Arial", "fontSize": 10, "bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}}},
            "fields": "userEnteredFormat.textFormat"
        }},
        # Center all data cells
        # Description column left align
        {"repeatCell": {
            "range": {"sheetId": 0, "startRowIndex": header_row, "endRowIndex": last_item_row, "startColumnIndex": 7, "endColumnIndex": 8},
            "cell": {"userEnteredFormat": {"horizontalAlignment": "LEFT"}},
            "fields": "userEnteredFormat.horizontalAlignment"
        }},
        # Grand total row - green highlight
        {"repeatCell": {
            "range": {"sheetId": 0, "startRowIndex": last_item_row, "endRowIndex": last_item_row + 1, "startColumnIndex": 0, "endColumnIndex": 12},
            "cell": {"userEnteredFormat": {
                "backgroundColor": {"red": 0.07, "green": 0.07, "blue": 0.07},
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                "horizontalAlignment": "CENTER",
            }},
            "fields": "userEnteredFormat"
        }},
        # Date right align
        {"repeatCell": {
            "range": {"sheetId": 0, "startRowIndex": 3, "endRowIndex": 4, "startColumnIndex": 0, "endColumnIndex": 12},
            "cell": {"userEnteredFormat": {"horizontalAlignment": "RIGHT"}},
            "fields": "userEnteredFormat.horizontalAlignment"
        }},
        # Project name left align
        {"repeatCell": {
            "range": {"sheetId": 0, "startRowIndex": 3, "endRowIndex": 4, "startColumnIndex": 0, "endColumnIndex": 5},
            "cell": {"userEnteredFormat": {"horizontalAlignment": "LEFT"}},
            "fields": "userEnteredFormat.horizontalAlignment"
        }},
        # Merge date cell F4:L4
        {"mergeCells": {
            "range": {"sheetId": 0, "startRowIndex": 3, "endRowIndex": 4, "startColumnIndex": 5, "endColumnIndex": 12},
            "mergeType": "MERGE_ALL"
        }},
        # Merge title cell
        {"mergeCells": {
            "range": {"sheetId": 0, "startRowIndex": 2, "endRowIndex": 3, "startColumnIndex": 0, "endColumnIndex": 6},
            "mergeType": "MERGE_ALL"
        }},
        # Summary sheet title bold
        {"repeatCell": {
            "range": {"sheetId": 1, "startRowIndex": 2, "endRowIndex": 4},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True, "fontSize": 12}}},
            "fields": "userEnteredFormat.textFormat"
        }},
        # Summary data rows center align (all rows first)
        {"repeatCell": {
            "range": {"sheetId": 1, "startRowIndex": 9, "endRowIndex": 14, "startColumnIndex": 0, "endColumnIndex": 4},
            "cell": {"userEnteredFormat": {
                "textFormat": {"fontFamily": "Arial", "fontSize": 10},
                "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"
            }},
            "fields": "userEnteredFormat(textFormat,horizontalAlignment,verticalAlignment)"
        }},
        # Grand total row bold
        {"repeatCell": {
            "range": {"sheetId": 1, "startRowIndex": 13, "endRowIndex": 14, "startColumnIndex": 0, "endColumnIndex": 4},
            "cell": {"userEnteredFormat": {
                "textFormat": {"bold": True, "fontFamily": "Arial", "fontSize": 10},
                "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"
            }},
            "fields": "userEnteredFormat(textFormat,horizontalAlignment,verticalAlignment)"
        }},
        # Terms & Conditions bold
        {"repeatCell": {
            "range": {"sheetId": 1, "startRowIndex": 15, "endRowIndex": 16, "startColumnIndex": 0, "endColumnIndex": 4},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True, "fontFamily": "Arial", "fontSize": 10}}},
            "fields": "userEnteredFormat.textFormat"
        }},
        # Header row black fill - specific fields only (not overwriting borders)
        {"repeatCell": {
            "range": {"sheetId": 1, "startRowIndex": 9, "endRowIndex": 10, "startColumnIndex": 0, "endColumnIndex": 4},
            "cell": {"userEnteredFormat": {
                "backgroundColor": {"red": 0, "green": 0, "blue": 0},
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}, "fontFamily": "Arial", "fontSize": 10},
                "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"
            }},
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"
        }},
        # Border LAST so repeatCell doesn't overwrite it
        {"updateBorders": {
            "range": {"sheetId": 1, "startRowIndex": 9, "endRowIndex": 14, "startColumnIndex": 0, "endColumnIndex": 4},
            "top": {"style": "SOLID_MEDIUM", "color": {"red": 0, "green": 0, "blue": 0}},
            "bottom": {"style": "SOLID_MEDIUM", "color": {"red": 0, "green": 0, "blue": 0}},
            "left": {"style": "SOLID_MEDIUM", "color": {"red": 0, "green": 0, "blue": 0}},
            "right": {"style": "SOLID_MEDIUM", "color": {"red": 0, "green": 0, "blue": 0}},
            "innerHorizontal": {"style": "SOLID", "color": {"red": 0.6, "green": 0.6, "blue": 0.6}},
            "innerVertical": {"style": "SOLID", "color": {"red": 0.6, "green": 0.6, "blue": 0.6}}
        }},
        # Summary col widths
        # Summary col widths
        {"updateDimensionProperties": {
            "range": {"sheetId": 1, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1},
            "properties": {"pixelSize": 50}, "fields": "pixelSize"
        }},
        {"updateDimensionProperties": {
            "range": {"sheetId": 1, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 2},
            "properties": {"pixelSize": 220}, "fields": "pixelSize"
        }},
        {"updateDimensionProperties": {
            "range": {"sheetId": 1, "dimension": "COLUMNS", "startIndex": 2, "endIndex": 3},
            "properties": {"pixelSize": 160}, "fields": "pixelSize"
        }},
        {"updateDimensionProperties": {
            "range": {"sheetId": 1, "dimension": "COLUMNS", "startIndex": 3, "endIndex": 4},
            "properties": {"pixelSize": 200}, "fields": "pixelSize"
        }},
    ]

    # Hide gridlines on both sheets
    requests_fmt.insert(0, {"updateSheetProperties": {
        "properties": {"sheetId": 0, "gridProperties": {"hideGridlines": True}},
        "fields": "gridProperties.hideGridlines"
    }})
    requests_fmt.insert(1, {"updateSheetProperties": {
        "properties": {"sheetId": 1, "gridProperties": {"hideGridlines": True}},
        "fields": "gridProperties.hideGridlines"
    }})

    # Append cleanup at the END so it overrides any spillover
    requests_fmt.extend([
        {"repeatCell": {
            "range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": last_item_row + 10, "startColumnIndex": 12, "endColumnIndex": 26},
            "cell": {"userEnteredFormat": {
                "backgroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                "textFormat": {"bold": False, "foregroundColor": {"red": 0, "green": 0, "blue": 0}}
            }},
            "fields": "userEnteredFormat"
        }},
    ])

    sheets.spreadsheets().batchUpdate(
        spreadsheetId=ss_id,
        body={"requests": requests_fmt}
    ).execute()

    # Format currency columns (K=10, L=11) as ₹
    sheets.spreadsheets().values().batchUpdate(
        spreadsheetId=ss_id,
        body={"valueInputOption": "USER_ENTERED", "data": []}
    )
    sheets.spreadsheets().batchUpdate(
        spreadsheetId=ss_id,
        body={"requests": [
            {"repeatCell": {
                "range": {"sheetId": 0, "startRowIndex": header_row + 1, "endRowIndex": last_item_row + 1, "startColumnIndex": 10, "endColumnIndex": 12},
                "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "₹#,##0.00"}}},
                "fields": "userEnteredFormat.numberFormat"
            }},
        ]}
    ).execute()

    # Format currency columns (K=10, L=11) as ₹
    sheets.spreadsheets().values().batchUpdate(
        spreadsheetId=ss_id,
        body={"valueInputOption": "USER_ENTERED", "data": []}
    )
    sheets.spreadsheets().batchUpdate(
        spreadsheetId=ss_id,
        body={"requests": [
            {"repeatCell": {
                "range": {"sheetId": 0, "startRowIndex": header_row + 1, "endRowIndex": last_item_row + 1, "startColumnIndex": 10, "endColumnIndex": 12},
                "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "₹#,##0.00"}}},
                "fields": "userEnteredFormat.numberFormat"
            }},
        ]}
    ).execute()

    # ── Insert product images via IMAGE formula ─────────
    # Build a map of item -> actual row number accounting for level headers
    # Insert images in sequential row order
    image_updates = []
    for i, item in enumerate(sorted_items):
        row_num = header_row + 2 + i  # 1-indexed
        img_url = get_image_url_for_sku(item.product_sku, item.product_name or '', db=db)
        if img_url:
            image_updates.append({
                "range": f"BOQ!F{row_num}",
                "values": [[f'=IMAGE("{img_url}")']],
            })
    if image_updates:
        sheets.spreadsheets().values().batchUpdate(
            spreadsheetId=ss_id,
            body={"valueInputOption": "USER_ENTERED", "data": image_updates}
        ).execute()

    # ── Format level header rows ─────────────────────────
    if level_header_rows:
        format_reqs = []
        for offset in level_header_rows:
            row_idx = header_row + 1 + offset
            format_reqs.append({
                "repeatCell": {
                    "range": {"sheetId": 0, "startRowIndex": row_idx, "endRowIndex": row_idx + 1, "startColumnIndex": 0, "endColumnIndex": 12},
                    "cell": {"userEnteredFormat": {
                        "backgroundColor": {"red": 0.1, "green": 0.1, "blue": 0.1},
                        "textFormat": {"bold": True, "foregroundColor": {"red": 0.78, "green": 0.66, "blue": 0.43}},
                        "borders": {"top": {"style": "SOLID_MEDIUM", "color": {"red": 0.78, "green": 0.66, "blue": 0.43}}, "bottom": {"style": "SOLID", "color": {"red": 0.3, "green": 0.3, "blue": 0.3}}}
                    }},
                    "fields": "userEnteredFormat(backgroundColor,textFormat,borders)"
                }
            })
        if format_reqs:
            sheets.spreadsheets().batchUpdate(spreadsheetId=ss_id, body={"requests": format_reqs}).execute()

    # ── Move to project Drive folder ────────────────────
    if lead.drive_folder_url:
        try:
            folder_id = lead.drive_folder_url.rstrip('/').split('/')[-1].split('?')[0]
            drive.files().update(
                fileId=ss_id,
                addParents=folder_id,
                removeParents='root',
                supportsAllDrives=True,
                fields='id'
            ).execute()
        except Exception as e:
            print(f"Could not move to Drive folder: {e}")

    sheet_url = f"https://docs.google.com/spreadsheets/d/{ss_id}"
    return {"sheet_url": sheet_url, "spreadsheet_id": ss_id}

# ── Company & Dealer Master Data ─────────────────────
MIPL = {
    "name": "Moorgen Innovations Private Limited",
    "address": "Basement, Plot No.51 SY No.41P, Siri Park View,\nGuttala Begumpet, Madhapur, Hyderabad - 500033",
    "gstin": "36AATCM2958B1Z7",
    "email": "info@moorgenindia.co",
    "phone": "+91 ",
    "bank_name": "ICICI Bank",
    "account_no": "193905000667",
    "ifsc": "ICIC0001939",
    "branch": "Banjara Hills Road No.10",
}

DEALERS = {
    "murano": {
        "name": "Murano India Pvt Ltd",
        "address": "No.61 Greater Kailash Part 1, Delhi - 110048",
        "gstin": "07AACCM2448M2Z8",
    },
    "flogloo": {
        "name": "Floglo International LLP",
        "address": "320, Valluvar Kotam High Road, 1st Floor,\nNungambakam, Chennai - 600034",
        "gstin": "33AAFFF5487K1Z3",
    },
    "elements": {
        "name": "Elements and Essentials Private Limited",
        "address": "Near Sankalp Square-3, Sindhubhavan Road,\nDaskroi, Ahmedabad, Gujarat - 380059",
        "gstin": "24AAJCE1849B1ZY",
    },
    "mahavir": {
        "name": "Soundroom Lifestyle Technologies Pvt Ltd",
        "address": "Level 4, Mercedes Benz Towers, Madhapur,\nHyderabad - 500033, Telangana",
        "gstin": "36AARCS0399G1ZU",
    },
    "lightforge": {
        "name": "LightForge Distribution Pvt Ltd",
        "address": "Hyderabad, Telangana",
        "gstin": "",
    },
}


@router.post("/dealer/boq/{boq_id}/sheets")
def export_dealer_boq_to_sheets(boq_id: int, token: str, db: Session = Depends(get_db)):
    from app.routers.dealer_auth import get_dealer
    dealer = get_dealer(token, db)
    drive = get_drive()
    DEALERS_ROOT_NAME = "Moorgen Dealers BOQs"
    res = drive.files().list(
        q=f"name='{DEALERS_ROOT_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id,name)"
    ).execute()
    if res['files']:
        root_id = res['files'][0]['id']
    else:
        f = drive.files().create(body={"name": DEALERS_ROOT_NAME, "mimeType": "application/vnd.google-apps.folder"}, fields="id").execute()
        root_id = f['id']
    dealer_folder_name = f"{dealer.firm_name} - {dealer.city}"
    res2 = drive.files().list(
        q=f"name='{dealer_folder_name}' and mimeType='application/vnd.google-apps.folder' and '{root_id}' in parents and trashed=false",
        fields="files(id,name)"
    ).execute()
    if res2['files']:
        dealer_folder_id = res2['files'][0]['id']
    else:
        f2 = drive.files().create(body={"name": dealer_folder_name, "mimeType": "application/vnd.google-apps.folder", "parents": [root_id]}, fields="id").execute()
        dealer_folder_id = f2['id']
        drive.permissions().create(fileId=dealer_folder_id, body={"role": "reader", "type": "anyone"}).execute()
    result = export_boq_to_sheets(boq_id, db)
    ss_id = result['spreadsheet_id']
    drive.files().update(fileId=ss_id, addParents=dealer_folder_id, removeParents='root', supportsAllDrives=True, fields='id').execute()
    drive.permissions().create(fileId=ss_id, body={"role": "reader", "type": "anyone"}).execute()
    folder_url = f"https://drive.google.com/drive/folders/{dealer_folder_id}"
    return {"sheet_url": result['sheet_url'], "folder_url": folder_url}

@router.post("/invoice/{invoice_id}/sheets")
def export_invoice_to_sheets(invoice_id: int, dealer_key: str = "", db: Session = Depends(get_db)):
    from app import models as m
    from datetime import datetime

    invoice = db.query(m.Invoice).filter(m.Invoice.invoice_id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    lead = db.query(m.Lead).filter(m.Lead.lead_id == invoice.lead_id).first()
    sheets = get_sheets()
    drive = get_drive()

    today = datetime.now().strftime("%d-%b-%Y")
    inv_amount = float(invoice.invoice_amount or 0)
    subtotal = float(invoice.subtotal or inv_amount)
    discount_amt = float(invoice.discount_amount or 0)
    gst_amt = float(invoice.gst_amount or 0)
    taxable = subtotal - discount_amt

    # Bill To party
    if dealer_key and dealer_key.lower() in DEALERS:
        bill_to = DEALERS[dealer_key.lower()]
    elif lead and lead.channel in ['flagship', 'flagship_dealer']:
        bill_to = DEALERS['lightforge']
    else:
        bill_to = {
            "name": lead.client_name or lead.project_name or "Client",
            "address": lead.client_address or "",
            "gstin": "",
        }

    title = f"Invoice {invoice.invoice_code} - {bill_to['name']}"
    ss = sheets.spreadsheets().create(body={
        "properties": {"title": title},
        "sheets": [{"properties": {"sheetId": 0, "title": "Invoice"}}]
    }).execute()
    ss_id = ss["spreadsheetId"]

    LOGO = f'=IMAGE("https://drive.google.com/uc?export=view&id=1eh_LL1RACtyrWeOtX0gb8H7pUaKlrD_k",4,50,200)'

    data_start = 13
    items = invoice.line_items
    rows = []
    for i, item in enumerate(items, 1):
        rows.append([
            i, item.product_name or "", item.sku or "", "pcs",
            item.quantity or 0,
            float(item.unit_price or 0),
            float(item.discount_pct or 0),
            float(item.line_total or 0),
            item.hsn_code or "",
        ])

    total_row = data_start + len(rows)
    mipl_gstin = MIPL["gstin"]
    mipl_email = MIPL["email"]
    bill_gstin = bill_to.get("gstin", "")
    bill_name = bill_to["name"]
    bill_addr = bill_to["address"]
    proj_name = lead.project_name if lead else ""
    city = lead.city if lead else ""

    values = [
        [LOGO, "", "", "", "", "", "TAX INVOICE", "", "", ""],                           # Row 1
        [MIPL["name"], "", "", "", "", "", "Invoice No:", invoice.invoice_code, "", ""], # Row 2
        [MIPL["address"], "", "", "", "", "", "Date:", today, "", ""],                  # Row 3
        [f"GSTIN: {mipl_gstin}", "", "", "", "", "", "Place of Supply:", city, "", ""], # Row 4
        [f"Email: {mipl_email}", "", "", "", "", "", "", "", "", ""],                # Row 5
        ["", "", "", "", "", "", "", "", "", ""],                                        # Row 6 spacer
        ["BILL TO", "", "", "", "", "", "", "", "", ""],                                 # Row 7
        [bill_name, "", "", "", "", "", "", "", "", ""],                                 # Row 8
        [bill_addr, "", "", "", "", "", "", "", "", ""],                                 # Row 9
        [f"GSTIN: {bill_gstin}" if bill_gstin else "", "", "", "", "", "", "Project:", proj_name, "", ""], # Row 10
        ["", "", "", "", "", "", "", "", "", ""],                                        # Row 11 spacer
        ["S.No.", "Product / Description", "SKU", "Unit", "Qty", "Unit Price (₹)", "Disc %", "Amount (₹)", "HSN", ""],  # Row 12 header
    ] + rows + [
        ["", "", "", "", "", "", "Subtotal", f"₹{subtotal:,.2f}", "", ""],
        ["", "", "", "", "", "", f"Discount ({invoice.discount_pct or 0}%)", f"-₹{discount_amt:,.2f}", "", ""] if discount_amt > 0 else ["", "", "", "", "", "", "", "", "", ""],
        ["", "", "", "", "", "", "Taxable Amount", f"₹{taxable:,.2f}", "", ""],
        ["", "", "", "", "", "", "GST @ 18%", f"₹{gst_amt:,.2f}", "", ""],
        ["", "", "", "", "", "", "GRAND TOTAL", f"₹{inv_amount:,.2f}", "", ""],
        ["", "", "", "", "", "", "", "", "", ""],
        ["BANK DETAILS FOR PAYMENT", "", "", "", "", "", "", "", "", ""],  # bold heading
        [f"Bank: {MIPL['bank_name']} | Branch: {MIPL['branch']}", "", "", "", "", "", "", "", "", ""],
        [f"A/C No: {MIPL['account_no']} | IFSC: {MIPL['ifsc']}", "", "", "", "", "", "", "", "", ""],
        ["", "", "", "", "", "", "", "", "", ""],
        ["TERMS & CONDITIONS", "", "", "", "", "", "", "", "", ""],  # bold heading
        ["- Payment due within 7 days of invoice date.", "", "", "", "", "", "", "", "", ""],
        ["- Balance payment to be cleared before dispatch.", "", "", "", "", "", "", "", "", ""],
        ["- Warranty: 2 years on Moorgen products from date of delivery.", "", "", "", "", "", "", "", "", ""],
        ["- Defective products must be reported within 7 days of delivery.", "", "", "", "", "", "", "", "", ""],
        ["- Goods once dispatched cannot be returned unless defective.", "", "", "", "", "", "", "", "", ""],
        ["- Late payment attracts 18% interest per annum.", "", "", "", "", "", "", "", "", ""],
        ["- Disputes subject to Hyderabad jurisdiction only.", "", "", "", "", "", "", "", "", ""],
        ["- E&OE — Errors and Omissions Excepted.", "", "", "", "", "", "", "", "", ""],
        ["- This is a computer generated invoice.", "", "", "", "", "", "", "", "", ""],
    ]

    sheets.spreadsheets().values().batchUpdate(
        spreadsheetId=ss_id,
        body={"valueInputOption": "USER_ENTERED", "data": [{"range": "Invoice!A1", "values": values}]}
    ).execute()

    BLACK = {"red": 0.07, "green": 0.07, "blue": 0.07}
    WHITE = {"red": 1, "green": 1, "blue": 1}
    LIGHT = {"red": 0.95, "green": 0.95, "blue": 0.95}

    reqs = [
        {"updateSheetProperties": {"properties": {"sheetId": 0, "gridProperties": {"hideGridlines": True}}, "fields": "gridProperties.hideGridlines"}},
        # Logo row height
        {"updateDimensionProperties": {"range": {"sheetId": 0, "dimension": "ROWS", "startIndex": 0, "endIndex": 1}, "properties": {"pixelSize": 80}, "fields": "pixelSize"}},
        # Header row black
        # Header row 12 (index 11) black
        {"repeatCell": {"range": {"sheetId": 0, "startRowIndex": 11, "endRowIndex": 12, "startColumnIndex": 0, "endColumnIndex": 8},
            "cell": {"userEnteredFormat": {"backgroundColor": BLACK, "textFormat": {"bold": True, "foregroundColor": WHITE}, "horizontalAlignment": "CENTER"}},
            "fields": "userEnteredFormat"}},
        # Right align all amount cells
        {"repeatCell": {"range": {"sheetId": 0, "startRowIndex": 12, "endRowIndex": total_row + 5, "startColumnIndex": 5, "endColumnIndex": 8},
            "cell": {"userEnteredFormat": {"horizontalAlignment": "RIGHT"}},
            "fields": "userEnteredFormat.horizontalAlignment"}},
        # Center qty and unit cols
        {"repeatCell": {"range": {"sheetId": 0, "startRowIndex": 12, "endRowIndex": total_row, "startColumnIndex": 3, "endColumnIndex": 5},
            "cell": {"userEnteredFormat": {"horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"}},
            "fields": "userEnteredFormat"}},
        # Center S.No col
        {"repeatCell": {"range": {"sheetId": 0, "startRowIndex": 12, "endRowIndex": total_row, "startColumnIndex": 0, "endColumnIndex": 1},
            "cell": {"userEnteredFormat": {"horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"}},
            "fields": "userEnteredFormat"}},
        # Center ALL table contents including header
        {"repeatCell": {"range": {"sheetId": 0, "startRowIndex": 11, "endRowIndex": total_row, "startColumnIndex": 0, "endColumnIndex": 8},
            "cell": {"userEnteredFormat": {"horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE", "wrapStrategy": "WRAP"}},
            "fields": "userEnteredFormat"}},
        # Reapply black header AFTER center (so it overrides)
        {"repeatCell": {"range": {"sheetId": 0, "startRowIndex": 11, "endRowIndex": 12, "startColumnIndex": 0, "endColumnIndex": 8},
            "cell": {"userEnteredFormat": {"backgroundColor": {"red": 0.07, "green": 0.07, "blue": 0.07}, "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}, "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"}},
            "fields": "userEnteredFormat"}},
        # Borders on totals section
        {"updateBorders": {
            "range": {"sheetId": 0, "startRowIndex": total_row - 1, "endRowIndex": total_row + 4, "startColumnIndex": 5, "endColumnIndex": 8},
            "top": {"style": "SOLID", "color": {"red": 0.7, "green": 0.7, "blue": 0.7}},
            "bottom": {"style": "SOLID", "color": {"red": 0.7, "green": 0.7, "blue": 0.7}},
            "left": {"style": "SOLID", "color": {"red": 0.7, "green": 0.7, "blue": 0.7}},
            "right": {"style": "SOLID", "color": {"red": 0.7, "green": 0.7, "blue": 0.7}},
            "innerHorizontal": {"style": "SOLID", "color": {"red": 0.85, "green": 0.85, "blue": 0.85}},
        }},
        # Grand total row black F:H
        {"repeatCell": {"range": {"sheetId": 0, "startRowIndex": total_row + 3, "endRowIndex": total_row + 4, "startColumnIndex": 5, "endColumnIndex": 8},
            "cell": {"userEnteredFormat": {"backgroundColor": BLACK, "textFormat": {"bold": True, "foregroundColor": WHITE}, "horizontalAlignment": "RIGHT"}},
            "fields": "userEnteredFormat"}},
        # Right align H2:H4 (values)
        {"repeatCell": {"range": {"sheetId": 0, "startRowIndex": 1, "endRowIndex": 4, "startColumnIndex": 7, "endColumnIndex": 8},
            "cell": {"userEnteredFormat": {"horizontalAlignment": "LEFT"}},
            "fields": "userEnteredFormat.horizontalAlignment"}},
        # Left align F2:G4 (labels)
        {"repeatCell": {"range": {"sheetId": 0, "startRowIndex": 1, "endRowIndex": 4, "startColumnIndex": 5, "endColumnIndex": 7},
            "cell": {"userEnteredFormat": {"horizontalAlignment": "LEFT"}},
            "fields": "userEnteredFormat.horizontalAlignment"}},
        # Bill To bold
        {"repeatCell": {"range": {"sheetId": 0, "startRowIndex": 6, "endRowIndex": 7},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True, "fontSize": 10}}},
            "fields": "userEnteredFormat"}},
        # Company name bold large
        {"repeatCell": {"range": {"sheetId": 0, "startRowIndex": 1, "endRowIndex": 2},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True, "fontSize": 13}}},
            "fields": "userEnteredFormat"}},
        # TAX INVOICE bold right - merge G1:H1
        {"mergeCells": {"range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 6, "endColumnIndex": 8}, "mergeType": "MERGE_ALL"}},
        {"repeatCell": {"range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 6, "endColumnIndex": 8},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True, "fontSize": 16}, "horizontalAlignment": "RIGHT"}},
            "fields": "userEnteredFormat"}},
        # Borders on line items
        {"updateBorders": {
            "range": {"sheetId": 0, "startRowIndex": 12, "endRowIndex": total_row, "startColumnIndex": 0, "endColumnIndex": 8},
            "top": {"style": "SOLID", "color": {"red": 0.7, "green": 0.7, "blue": 0.7}},
            "bottom": {"style": "SOLID", "color": {"red": 0.7, "green": 0.7, "blue": 0.7}},
            "left": {"style": "SOLID", "color": {"red": 0.7, "green": 0.7, "blue": 0.7}},
            "right": {"style": "SOLID", "color": {"red": 0.7, "green": 0.7, "blue": 0.7}},
            "innerHorizontal": {"style": "SOLID", "color": {"red": 0.85, "green": 0.85, "blue": 0.85}},
            "innerVertical": {"style": "SOLID", "color": {"red": 0.85, "green": 0.85, "blue": 0.85}},
        }},
        # Col widths
        {"updateDimensionProperties": {"range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1}, "properties": {"pixelSize": 40}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 2}, "properties": {"pixelSize": 100}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 2, "endIndex": 3}, "properties": {"pixelSize": 280}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 3, "endIndex": 4}, "properties": {"pixelSize": 140}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 5, "endIndex": 6}, "properties": {"pixelSize": 50}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 5, "endIndex": 6}, "properties": {"pixelSize": 50}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 6, "endIndex": 7}, "properties": {"pixelSize": 120}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 7, "endIndex": 8}, "properties": {"pixelSize": 80}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 8, "endIndex": 9}, "properties": {"pixelSize": 130}, "fields": "pixelSize"}},
        # Row heights for image rows
        {"updateDimensionProperties": {"range": {"sheetId": 0, "dimension": "ROWS", "startIndex": 12, "endIndex": 12 + len(items)}, "properties": {"pixelSize": 80}, "fields": "pixelSize"}},
        # Freeze top rows
        {"updateSheetProperties": {"properties": {"sheetId": 0, "gridProperties": {"frozenRowCount": 12}}, "fields": "gridProperties.frozenRowCount"}},
        # Merge company name
        # A1:B1 logo merge
        {"mergeCells": {"range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 2}, "mergeType": "MERGE_ALL"}},
        # A2:C2 company name
        {"mergeCells": {"range": {"sheetId": 0, "startRowIndex": 1, "endRowIndex": 2, "startColumnIndex": 0, "endColumnIndex": 3}, "mergeType": "MERGE_ALL"}},
        # A3 address (single row)
        {"mergeCells": {"range": {"sheetId": 0, "startRowIndex": 2, "endRowIndex": 3, "startColumnIndex": 0, "endColumnIndex": 5}, "mergeType": "MERGE_ALL"}},
        # A5 GSTIN
        {"mergeCells": {"range": {"sheetId": 0, "startRowIndex": 4, "endRowIndex": 5, "startColumnIndex": 0, "endColumnIndex": 5}, "mergeType": "MERGE_ALL"}},
        # A6 bank
        {"mergeCells": {"range": {"sheetId": 0, "startRowIndex": 5, "endRowIndex": 6, "startColumnIndex": 0, "endColumnIndex": 8}, "mergeType": "MERGE_ALL"}},
        # F2:G2 Invoice No label
        {"mergeCells": {"range": {"sheetId": 0, "startRowIndex": 1, "endRowIndex": 2, "startColumnIndex": 5, "endColumnIndex": 7}, "mergeType": "MERGE_ALL"}},
        {"repeatCell": {"range": {"sheetId": 0, "startRowIndex": 1, "endRowIndex": 4, "startColumnIndex": 5, "endColumnIndex": 6},
            "cell": {"userEnteredFormat": {"horizontalAlignment": "RIGHT"}},
            "fields": "userEnteredFormat.horizontalAlignment"}},
        {"repeatCell": {"range": {"sheetId": 0, "startRowIndex": 1, "endRowIndex": 4, "startColumnIndex": 7, "endColumnIndex": 8},
            "cell": {"userEnteredFormat": {"horizontalAlignment": "RIGHT"}},
            "fields": "userEnteredFormat.horizontalAlignment"}},
        # Bill To name
        {"mergeCells": {"range": {"sheetId": 0, "startRowIndex": 7, "endRowIndex": 8, "startColumnIndex": 0, "endColumnIndex": 5}, "mergeType": "MERGE_ALL"}},
        # Bill To address (single row)
        {"mergeCells": {"range": {"sheetId": 0, "startRowIndex": 8, "endRowIndex": 9, "startColumnIndex": 0, "endColumnIndex": 5}, "mergeType": "MERGE_ALL"}},
    ]

    sheets.spreadsheets().batchUpdate(spreadsheetId=ss_id, body={"requests": reqs}).execute()

    # Move to project Drive folder
    if lead and lead.drive_folder_url:
        try:
            folder_id = lead.drive_folder_url.rstrip('/').split('/')[-1].split('?')[0]
            drive.files().update(fileId=ss_id, addParents=folder_id, removeParents='root', supportsAllDrives=True, fields='id').execute()
        except Exception as e:
            print(f"Could not move to Drive: {e}")

    return {"sheet_url": f"https://docs.google.com/spreadsheets/d/{ss_id}"}
