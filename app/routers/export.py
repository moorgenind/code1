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

TERMS = [
    "Shipment: 30–60 days from order confirmation.",
    "60% advance required to confirm the order.",
    "Prices subject to change without notice.",
    "Quotation valid for 15 days from issue.",
    "Drivers added after layouts are finalized.",
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

def get_image_url_for_sku(sku, product_name=""):
    """Get Drive thumbnail URL using image_map.py"""
    try:
        from app.image_map import IMAGE_MAP
        name = str(product_name or sku or "").lower()
        best = None
        best_score = 0
        for entry in IMAGE_MAP:
            score = 0
            if entry.get("family") and entry["family"].lower() in name:
                score += 2
            if entry.get("name") and entry["name"].lower() in name:
                score += 3
            if entry.get("trim"):
                trim = entry["trim"].lower()
                if trim in name:
                    score += 1
            if entry.get("color"):
                color = entry["color"].lower()
                if color in name:
                    score += 1
            if score > best_score:
                best_score = score
                best = entry
        if best and best_score >= 3:
            return f"https://drive.google.com/thumbnail?id={best['id']}&sz=w200"
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
            {"properties": {"sheetId": 0, "title": "BOQ", "index": 0}},
            {"properties": {"sheetId": 1, "title": "Proposal Summary", "index": 1}},
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

    # Line items starting at row 7
    for idx, item in enumerate(items, 1):
        desc = item.notes or ""
        boq_values.append([
            idx,
            item.level or "",
            item.area or "",
            item.product_sku or "",
            item.product_name or "",
            "",  # Image - placeholder
            "Moorgen",
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
    area_groups = {}
    for item in items:
        area = item.area or "Other"
        area_groups[area] = area_groups.get(area, 0) + float(item.line_total or 0)

    summary_values = [
        ['=IMAGE("https://drive.google.com/uc?export=view&id=1eh_LL1RACtyrWeOtX0gb8H7pUaKlrD_k",4,60,250)', "", "", ""],
        ["", "", "", ""],
        ["Moorgen Lighting & Smart System", "", "", ""],
        ["BOQ & Pricing Proposal", "", "", ""],
        ["", "", "", ""],
        [f"Project Name: {project_name}", "", "", ""],
        [f"System Category: {category_label}", "", "", ""],
        [f"Date: {today}", "", "", ""],
        ["", "", "", ""],
        ["No.", "Sub-item", "Total Price", "Remarks"],
    ]

    for i, (area, amt) in enumerate(area_groups.items(), 1):
        summary_values.append([i, area, f"₹{amt:,.2f}", ""])

    summary_values += [
        ["", "Total", f"₹{total:,.2f}", ""],
        ["", "18% GST", f"₹{gst:,.2f}", ""],
        ["", "Grand Total", f"₹{grand_total:,.2f}", ""],
        ["", "", "", ""],
        ["Terms & Conditions", "", "", ""],
    ]
    for term in TERMS:
        summary_values.append([f"- {term}", "", "", ""])

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
        # Center all data cells
        {"repeatCell": {
            "range": {"sheetId": 0, "startRowIndex": header_row, "endRowIndex": last_item_row + 2, "startColumnIndex": 0, "endColumnIndex": 12},
            "cell": {"userEnteredFormat": {"horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"}},
            "fields": "userEnteredFormat.horizontalAlignment,userEnteredFormat.verticalAlignment"
        }},
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
            "fields": "userEnteredFormat"
        }},
        # Summary header row
        {"repeatCell": {
            "range": {"sheetId": 1, "startRowIndex": 9, "endRowIndex": 10},
            "cell": {"userEnteredFormat": {
                "backgroundColor": {"red": 0.13, "green": 0.13, "blue": 0.13},
                "textFormat": {"bold": True, "foregroundColor": WHITE},
            }},
            "fields": "userEnteredFormat"
        }},
        # Grand total bold
        {"repeatCell": {
            "range": {"sheetId": 1, "startRowIndex": 9 + len(area_groups) + 2, "endRowIndex": 9 + len(area_groups) + 3},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True, "fontSize": 11}}},
            "fields": "userEnteredFormat"
        }},
        # Terms bold header
        {"repeatCell": {
            "range": {"sheetId": 1, "startRowIndex": 9 + len(area_groups) + 4, "endRowIndex": 9 + len(area_groups) + 5},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
            "fields": "userEnteredFormat"
        }},
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
    image_updates = []
    for idx, item in enumerate(items):
        row_num = header_row + 2 + idx  # 1-indexed for A1 notation
        img_url = item.image_url or get_image_url_for_sku(item.product_sku, item.product_name or '')
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
