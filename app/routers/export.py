from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
import pickle, base64, os
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

router = APIRouter()

def get_sheets_service():
    token_b64 = os.getenv("GOOGLE_TOKEN_BASE64")
    if token_b64:
        creds = pickle.loads(base64.b64decode(token_b64))
    else:
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(BASE_DIR, "token.pickle"), "rb") as f:
            creds = pickle.load(f)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("sheets", "v4", credentials=creds)

def get_drive_svc():
    from app.drive import get_drive_service
    return get_drive_service()

@router.post("/boq/{boq_id}/sheets")
def export_boq_to_sheets(boq_id: int, db: Session = Depends(get_db)):
    boq = db.query(models.Boq).filter(models.Boq.boq_id == boq_id).first()
    if not boq:
        raise HTTPException(status_code=404, detail="BOQ not found")

    lead = db.query(models.Lead).filter(models.Lead.lead_id == boq.lead_id).first()
    items = boq.line_items

    sheets = get_sheets_service()
    drive = get_drive_svc()

    # Create spreadsheet
    title = f"{lead.client_name or lead.project_name} — {boq.boq_code}"
    spreadsheet = sheets.spreadsheets().create(body={
        "properties": {"title": title},
        "sheets": [
            {"properties": {"sheetId": 0, "title": "BOQ", "index": 0}},
            {"properties": {"sheetId": 1, "title": "Summary", "index": 1}},
        ]
    }).execute()

    ss_id = spreadsheet["spreadsheetId"]

    # ── BOQ Sheet ──────────────────────────────────────
    boq_header = [["LEVEL", "AREA", "PRODUCT NAME", "SKU", "QTY", "UNIT PRICE (MRP)", "TOTAL", "NOTES"]]
    boq_rows = []
    for item in items:
        boq_rows.append([
            item.level or "",
            item.area or "",
            item.product_name or "",
            item.product_sku or "",
            item.quantity or 0,
            float(item.unit_price or 0),
            float(item.line_total or 0),
            item.notes or "",
        ])

    total_row = [["", "", "", "", "", "GRAND TOTAL", f"=SUM(G3:G{len(boq_rows)+2})", ""]]

    boq_data = boq_header + boq_rows + [[]] + total_row

    # ── Summary Sheet ──────────────────────────────────
    # Group by area
    area_totals = {}
    category_totals = {}
    for item in items:
        area = item.area or "Other"
        area_totals[area] = area_totals.get(area, 0) + float(item.line_total or 0)

    summary_rows = [
        ["MOORGEN INNOVATIONS — BOQ SUMMARY"],
        [],
        ["BOQ Code", boq.boq_code],
        ["Project", lead.project_name or ""],
        ["Client", lead.client_name or ""],
        ["Category", boq.category or ""],
        ["Status", boq.status or ""],
        [],
        ["BY AREA", "", "AMOUNT (₹)"],
    ]
    for area, total in sorted(area_totals.items()):
        summary_rows.append(["", area, total])

    summary_rows += [
        [],
        ["", "GRAND TOTAL", float(boq.total_amount or 0)],
        [],
        ["Total Line Items", len(items)],
    ]

    # Write data
    sheets.spreadsheets().values().batchUpdate(ss_id, body={"valueInputOption": "USER_ENTERED", "data": [
        {"range": "BOQ!A1", "values": boq_data},
        {"range": "Summary!A1", "values": summary_rows},
    ]}).execute()

    # Format BOQ sheet
    requests = [
        # Header row bold + green background
        {"repeatCell": {
            "range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1},
            "cell": {"userEnteredFormat": {
                "backgroundColor": {"red": 0.11, "green": 0.68, "blue": 0.49},
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
            }},
            "fields": "userEnteredFormat"
        }},
        # Freeze header row
        {"updateSheetProperties": {
            "properties": {"sheetId": 0, "gridProperties": {"frozenRowCount": 1}},
            "fields": "gridProperties.frozenRowCount"
        }},
        # Summary header bold
        {"repeatCell": {
            "range": {"sheetId": 1, "startRowIndex": 0, "endRowIndex": 1},
            "cell": {"userEnteredFormat": {
                "textFormat": {"bold": True, "fontSize": 14},
            }},
            "fields": "userEnteredFormat"
        }},
        # Column widths BOQ
        {"updateDimensionProperties": {
            "range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 8},
            "properties": {"pixelSize": 180},
            "fields": "pixelSize"
        }},
    ]
    sheets.spreadsheets().batchUpdate(ss_id, body={"requests": requests}).execute()

    # Move to project Drive folder if exists
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
