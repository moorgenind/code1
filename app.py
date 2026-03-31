import os
import re
import pickle
from datetime import datetime
from typing import Dict, Any, Optional, List

import gspread
from dateutil import tz
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# =========================================
# CONFIG
# =========================================
SPREADSHEET_NAME = "Moorgen_CRM"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OAUTH_FILE = os.path.join(BASE_DIR, "oauth_credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.pickle")

LEADS_SHEET_NAME = "Leads"
COUNTERS_SHEET_NAME = "Counters"
ACTIVITY_LOG_SHEET_NAME = "Activity_Log"
DESIGN_TASKS_SHEET_NAME = "Design_Tasks"
BOQ_QUEUE_SHEET_NAME = "BOQ_Request_Queue"
PROJECTS_SHEET_NAME = "Projects"

TIMEZONE = "Asia/Kolkata"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

DEFAULT_STAGE = "New_Enquiry"
DEFAULT_NEXT_ACTION = "Gather Requirements"

# Replace with your actual Drive folder ID
LEADS_PARENT_FOLDER_ID = "YOUR_REAL_DRIVE_FOLDER_ID_HERE"

REQUIRED_FIELDS = [
    "Client_Name",
    "Phone/ Email",
    "Project_Name",
    "Project_Location",
    "Assigned_Sales",
]

SCOPE_FIELDS = [
    "Arch_Lighting",
    "Decorative_Lighting",
    "Automation_Required",
    "Mechanical_Keypads_Required",
    "Smart_Lock_Required",
]


# =========================================
# AUTH
# =========================================
def get_google_creds():
    creds = None

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(OAUTH_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)

    return creds


creds = get_google_creds()
gc = gspread.authorize(creds)
spreadsheet = gc.open(SPREADSHEET_NAME)

leads_ws = spreadsheet.worksheet(LEADS_SHEET_NAME)
counters_ws = spreadsheet.worksheet(COUNTERS_SHEET_NAME)
activity_log_ws = spreadsheet.worksheet(ACTIVITY_LOG_SHEET_NAME)
design_tasks_ws = spreadsheet.worksheet(DESIGN_TASKS_SHEET_NAME)
boq_queue_ws = spreadsheet.worksheet(BOQ_QUEUE_SHEET_NAME)
projects_ws = spreadsheet.worksheet(PROJECTS_SHEET_NAME)

drive_service = build("drive", "v3", credentials=creds)


# =========================================
# HELPERS
# =========================================
def now_ist() -> datetime:
    return datetime.now(tz=tz.gettz(TIMEZONE))

def current_date_str() -> str:
    return now_ist().strftime("%d/%m/%Y")

def current_timestamp_str() -> str:
    return now_ist().strftime("%d/%m/%Y %H:%M:%S")

def current_year() -> int:
    return now_ist().year

def safe_str(value: Any) -> str:
    return "" if value is None else str(value).strip()

def normalize_yes_no(value: Any) -> bool:
    if value is None:
        return False
    value = str(value).strip().lower()
    return value in {"yes", "y", "true", "1", "checked", "tick"}

def is_yes(value: Any) -> bool:
    return normalize_yes_no(value)

def clean_header(header: str) -> str:
    return str(header).strip()

def slugify(text: Any) -> str:
    text = safe_str(text)
    text = re.sub(r"[^A-Za-z0-9]+", "_", text)
    return text.strip("_")


# =========================================
# SHEET HELPERS
# =========================================
def get_headers(ws) -> List[str]:
    return [clean_header(h) for h in ws.row_values(1)]

def get_column_index_map(ws) -> Dict[str, int]:
    headers = get_headers(ws)
    return {header: idx + 1 for idx, header in enumerate(headers)}

def get_row_dict_by_row_number(ws, row_number: int) -> Dict[str, Any]:
    headers = get_headers(ws)
    row_values = ws.row_values(row_number)
    row_values += [""] * (len(headers) - len(row_values))
    return dict(zip(headers, row_values))

def update_row_fields(ws, row_number: int, updates: Dict[str, Any]):
    col_map = get_column_index_map(ws)
    cells_to_update = []

    for field, value in updates.items():
        if field not in col_map:
            raise ValueError(f"Column '{field}' not found in sheet '{ws.title}'")
        cell = ws.cell(row_number, col_map[field])
        cell.value = value
        cells_to_update.append(cell)

    if cells_to_update:
        ws.update_cells(cells_to_update, value_input_option="USER_ENTERED")


# =========================================
# COUNTERS / IDS
# =========================================
def find_counter_row(entity: str, year: int) -> Optional[int]:
    records = counters_ws.get_all_records()
    for idx, row in enumerate(records, start=2):
        if safe_str(row.get("Entity")) == entity and int(row.get("Year")) == year:
            return idx
    return None

def ensure_counter_row(entity: str, year: int, prefix: str) -> int:
    row_num = find_counter_row(entity, year)
    if row_num:
        return row_num

    counters_ws.append_row([entity, year, 0, prefix], value_input_option="USER_ENTERED")
    return find_counter_row(entity, year)

def generate_next_id(entity: str, prefix: str, year: Optional[int] = None, pad: int = 3) -> str:
    if year is None:
        year = current_year()

    row_num = ensure_counter_row(entity, year, prefix)
    row_data = get_row_dict_by_row_number(counters_ws, row_num)

    last_number = int(row_data.get("Last_Number", 0) or 0)
    next_number = last_number + 1

    update_row_fields(counters_ws, row_num, {"Last_Number": next_number})

    return f"{prefix}-{year}-{str(next_number).zfill(pad)}"


# =========================================
# LOGGING
# =========================================
def write_log(
    user: str,
    action: str,
    record_type: str,
    record_id: str,
    status: str,
    message: str,
    error_details: str = "",
):
    log_id = generate_next_id(entity="Log", prefix="LOG")

    activity_log_ws.append_row(
        [
            log_id,
            current_timestamp_str(),
            user,
            action,
            record_type,
            record_id,
            status,
            message,
            error_details,
        ],
        value_input_option="USER_ENTERED",
    )


# =========================================
# VALIDATION
# =========================================
def validate_lead_row(row_data: Dict[str, Any]) -> Dict[str, Any]:
    errors = []

    for field in REQUIRED_FIELDS:
        if not safe_str(row_data.get(field)):
            errors.append(f"Missing required field: {field}")

    selected_scopes = [
        field for field in SCOPE_FIELDS
        if normalize_yes_no(row_data.get(field))
    ]

    if not selected_scopes:
        errors.append(
            "At least one scope must be selected from: " + ", ".join(SCOPE_FIELDS)
        )

    if safe_str(row_data.get("Lead_ID")):
        errors.append("Lead_ID already exists for this row")

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "selected_scopes": selected_scopes,
    }


# =========================================
# DRIVE
# =========================================
def create_drive_folder(folder_name: str, parent_folder_id: str) -> Dict[str, str]:
    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_folder_id],
    }

    folder = drive_service.files().create(
        body=metadata,
        fields="id,name,webViewLink"
    ).execute()

    return folder

def create_subfolder(parent_folder_id: str, subfolder_name: str) -> Dict[str, str]:
    metadata = {
        "name": subfolder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_folder_id],
    }

    folder = drive_service.files().create(
        body=metadata,
        fields="id,name,webViewLink"
    ).execute()

    return folder

def create_lead_folder_structure(
    lead_id: str,
    client_name: str,
    project_name: str,
    project_location: str = ""
) -> Dict[str, Any]:
    safe_client = slugify(client_name) or "Client"
    safe_project = slugify(project_name) or "Project"
    safe_location = slugify(project_location)

    parts = [lead_id, safe_client, safe_project]
    if safe_location:
        parts.append(safe_location)

    main_folder_name = "_".join(parts)

    main_folder = create_drive_folder(
        folder_name=main_folder_name,
        parent_folder_id=LEADS_PARENT_FOLDER_ID
    )

    subfolders = [
        "01_Quotes",
        "02_Layouts",
        "03_Proposals",
        "04_Automation",
        "05_Mechanical",
        "06_Execution",
        "07_Site_Photos",
    ]

    created_subfolders = []
    for subfolder_name in subfolders:
        subfolder = create_subfolder(main_folder["id"], subfolder_name)
        created_subfolders.append(subfolder)

    return {
        "main_folder_id": main_folder["id"],
        "main_folder_name": main_folder["name"],
        "main_folder_link": main_folder["webViewLink"],
        "subfolders": created_subfolders,
    }


# =========================================
# LEADS
# =========================================
def create_lead_record(row_number: int, user_name: str = "Moorgen User") -> Dict[str, Any]:
    try:
        row_data = get_row_dict_by_row_number(leads_ws, row_number)
        validation = validate_lead_row(row_data)

        if not validation["is_valid"]:
            error_text = " | ".join(validation["errors"])

            update_row_fields(leads_ws, row_number, {
                "Automation_Status": "Error",
                "Automation_Error": error_text,
                "Last_Action_Time": current_timestamp_str(),
            })

            write_log(
                user=user_name,
                action="Create Lead Record",
                record_type="Lead",
                record_id="N/A",
                status="Failed",
                message=f"Lead creation failed for row {row_number}",
                error_details=error_text,
            )

            return {
                "success": False,
                "row_number": row_number,
                "errors": validation["errors"],
            }

        lead_id = generate_next_id(entity="Lead", prefix="LD")

        drive_result = create_lead_folder_structure(
            lead_id=lead_id,
            client_name=row_data.get("Client_Name", ""),
            project_name=row_data.get("Project_Name", ""),
            project_location=row_data.get("Project_Location", ""),
        )

        updates = {
            "Lead_ID": lead_id,
            "Created_Date": current_date_str(),
            "Current_Stage": DEFAULT_STAGE,
            "Next_Action": DEFAULT_NEXT_ACTION,
            "Last_Action_Time": current_timestamp_str(),
            "Drive_Folder_Link": drive_result["main_folder_link"],
            "Automation_Status": "Done",
            "Automation_Error": "",
        }

        update_row_fields(leads_ws, row_number, updates)

        write_log(
            user=user_name,
            action="Create Lead Record",
            record_type="Lead",
            record_id=lead_id,
            status="Success",
            message=f"Lead created successfully for row {row_number}",
            error_details="",
        )

        return {
            "success": True,
            "row_number": row_number,
            "lead_id": lead_id,
            "drive_folder_link": drive_result["main_folder_link"],
            "selected_scopes": validation["selected_scopes"],
        }

    except HttpError as e:
        error_text = str(e)

        update_row_fields(leads_ws, row_number, {
            "Automation_Status": "Error",
            "Automation_Error": error_text,
            "Last_Action_Time": current_timestamp_str(),
        })

        write_log(
            user=user_name,
            action="Create Lead Record",
            record_type="Lead",
            record_id="N/A",
            status="Drive Error",
            message=f"Drive error for row {row_number}",
            error_details=error_text,
        )

        return {
            "success": False,
            "row_number": row_number,
            "errors": [error_text],
        }

    except Exception as e:
        error_text = str(e)

        update_row_fields(leads_ws, row_number, {
            "Automation_Status": "Error",
            "Automation_Error": error_text,
            "Last_Action_Time": current_timestamp_str(),
        })

        write_log(
            user=user_name,
            action="Create Lead Record",
            record_type="Lead",
            record_id="N/A",
            status="Error",
            message=f"Unexpected error for row {row_number}",
            error_details=error_text,
        )

        return {
            "success": False,
            "row_number": row_number,
            "errors": [error_text],
        }


# =========================================
# DESIGN
# =========================================
def get_design_types_from_lead(row_data: Dict[str, Any]) -> List[str]:
    design_types = []

    if is_yes(row_data.get("Arch_Lighting")) and is_yes(row_data.get("Lighting_Design_Required")):
        design_types.append("Architectural Lighting Layout")

    if is_yes(row_data.get("Decorative_Lighting")):
        design_types.append("Decorative Layout")

    if is_yes(row_data.get("Automation_Required")) and is_yes(row_data.get("Automation_Concept_Required")):
        design_types.append("Automation Layout")

    if is_yes(row_data.get("Mechanical_Keypads_Required")):
        design_types.append("Keypad Positioning Layout")

    return design_types

def create_design_tasks_from_lead(row_number: int, user_name: str = "Moorgen User") -> Dict[str, Any]:
    row_data = get_row_dict_by_row_number(leads_ws, row_number)

    lead_id = safe_str(row_data.get("Lead_ID"))
    if not lead_id:
        return {"success": False, "message": "Lead_ID missing. Create lead first."}

    if not is_yes(row_data.get("Design_Required")):
        return {"success": False, "message": "Design_Required is not Yes."}

    design_types = get_design_types_from_lead(row_data)
    if not design_types:
        return {"success": False, "message": "No design task types derived from this lead."}

    created_ids = []

    for design_type in design_types:
        design_id = generate_next_id(entity="DesignTask", prefix="DSG")

        design_tasks_ws.append_row(
            [
                design_id,
                lead_id,
                safe_str(row_data.get("Client_Name")),
                safe_str(row_data.get("Project_Name")),
                safe_str(row_data.get("Project_Location")),
                design_type,
                safe_str(row_data.get("Assigned_Sales")),
                current_date_str(),
                "",
                "Pending",
                "",
                safe_str(row_data.get("Notes")),
            ],
            value_input_option="USER_ENTERED",
        )

        created_ids.append(design_id)

    boq_required = is_yes(row_data.get("BOQ_Required"))

    if boq_required:
        current_stage = "Design_And_BOQ_Requested"
        next_action = "Start Design and Process BOQ Queue"
    else:
        current_stage = "Design_Requested"
        next_action = "Start Design Work"

    update_row_fields(leads_ws, row_number, {
        "Design_Status": "Pending",
        "Latest_Design_ID": ", ".join(created_ids),
        "Current_Stage": current_stage,
        "Next_Action": next_action,
        "Last_Action_Time": current_timestamp_str(),
    })

    write_log(
        user=user_name,
        action="Create Design Tasks",
        record_type="Lead",
        record_id=lead_id,
        status="Success",
        message=f"Created {len(created_ids)} design task(s)",
        error_details="",
    )

    return {
        "success": True,
        "lead_id": lead_id,
        "created_design_ids": created_ids,
        "current_stage": current_stage,
        "next_action": next_action,
    }


# =========================================
# BOQ
# =========================================
def get_boq_categories_from_lead(row_data: Dict[str, Any]) -> List[str]:
    categories = []

    if is_yes(row_data.get("Arch_Lighting")):
        categories.append("Architectural Lighting")

    if is_yes(row_data.get("Decorative_Lighting")):
        categories.append("Decorative Lighting")

    if is_yes(row_data.get("Automation_Required")):
        categories.append("Automation")

    return categories

def create_boq_request_from_lead(row_number: int, user_name: str = "Moorgen User") -> Dict[str, Any]:
    row_data = get_row_dict_by_row_number(leads_ws, row_number)

    lead_id = safe_str(row_data.get("Lead_ID"))
    if not lead_id:
        return {
            "success": False,
            "message": "Lead_ID missing. Create lead first."
        }

    if not is_yes(row_data.get("BOQ_Required")):
        return {
            "success": False,
            "message": "BOQ_Required is not Yes."
        }

    boq_categories = get_boq_categories_from_lead(row_data)
    if not boq_categories:
        return {
            "success": False,
            "message": "No BOQ categories derived from this lead."
        }

    created_request_ids = []

    for category in boq_categories:
        request_id = generate_next_id(entity="BOQRequest", prefix="BRQ")

        scope_arch = "Yes" if category == "Architectural Lighting" else "No"
        scope_decorative = "Yes" if category == "Decorative Lighting" else "No"
        scope_automation = "Yes" if category == "Automation" else "No"

        boq_queue_ws.append_row(
            [
                request_id,
                lead_id,
                safe_str(row_data.get("Client_Name")),
                safe_str(row_data.get("Project_Name")),
                safe_str(row_data.get("Project_Location")),
                scope_arch,
                scope_decorative,
                scope_automation,
                user_name,
                current_date_str(),
                "Pending",
                "",
                "",
                "",
                safe_str(row_data.get("Notes")),
            ],
            value_input_option="USER_ENTERED",
        )

        created_request_ids.append(request_id)

    design_required = is_yes(row_data.get("Design_Required"))

    if design_required:
        current_stage = "Design_And_BOQ_Requested"
        next_action = "Start Design and Process BOQ Queue"
    else:
        current_stage = "BOQ_Requested"
        next_action = "Process BOQ Queue"

    update_row_fields(leads_ws, row_number, {
        "BOQ_Status": "Pending",
        "Latest_BOQ_ID": ", ".join(created_request_ids),
        "Current_Stage": current_stage,
        "Next_Action": next_action,
        "Last_Action_Time": current_timestamp_str(),
    })

    write_log(
        user=user_name,
        action="Create BOQ Request",
        record_type="Lead",
        record_id=lead_id,
        status="Success",
        message=f"Created {len(created_request_ids)} BOQ request(s)",
        error_details="",
    )

    return {
        "success": True,
        "lead_id": lead_id,
        "request_ids": created_request_ids,
        "categories": boq_categories,
        "current_stage": current_stage,
        "next_action": next_action,
    }


# =========================================
# ORDER CONFIRMATION / PROJECTS
# =========================================
def confirm_order_from_lead(row_number: int, user_name: str = "Moorgen User") -> Dict[str, Any]:
    row_data = get_row_dict_by_row_number(leads_ws, row_number)

    lead_id = safe_str(row_data.get("Lead_ID"))
    if not lead_id:
        return {
            "success": False,
            "message": "Lead_ID missing. Create lead first."
        }

    if not is_yes(row_data.get("Order_Confirmed")):
        return {
            "success": False,
            "message": "Order_Confirmed is not Yes."
        }

    existing_project_id = safe_str(row_data.get("Project_ID"))
    if existing_project_id:
        return {
            "success": False,
            "message": f"Project already exists: {existing_project_id}"
        }

    project_id = generate_next_id(entity="Project", prefix="PRJ")

    advance_required = is_yes(row_data.get("Advance_Required"))
    advance_status = safe_str(row_data.get("Advance_Status"))
    if not advance_status:
        advance_status = "Pending" if advance_required else "Not Required"

    order_confirmed_date = safe_str(row_data.get("Order_Confirmed_Date")) or current_date_str()

    projects_ws.append_row(
        [
            project_id,
            lead_id,
            safe_str(row_data.get("Client_Name")),
            safe_str(row_data.get("Project_Name")),
            safe_str(row_data.get("Project_Location")),
            safe_str(row_data.get("Assigned_Sales")),
            order_confirmed_date,
            advance_status,
            safe_str(row_data.get("Advance_Amount")),
            "Order Confirmed",
            safe_str(row_data.get("Drive_Folder_Link")),
            safe_str(row_data.get("Notes")),
        ],
        value_input_option="USER_ENTERED",
    )

    current_stage = "Order_Confirmed"
    next_action = "Collect Advance" if advance_required else "Start Project Planning"

    update_row_fields(leads_ws, row_number, {
        "Project_ID": project_id,
        "Order_Confirmed_Date": order_confirmed_date,
        "Order_Confirmed_By": user_name,
        "Advance_Status": advance_status,
        "Current_Stage": current_stage,
        "Next_Action": next_action,
        "Last_Action_Time": current_timestamp_str(),
    })

    write_log(
        user=user_name,
        action="Confirm Order",
        record_type="Lead",
        record_id=lead_id,
        status="Success",
        message=f"Order confirmed and project created: {project_id}",
        error_details="",
    )

    return {
        "success": True,
        "lead_id": lead_id,
        "project_id": project_id,
        "current_stage": current_stage,
        "next_action": next_action,
    }


# =========================================
# POST-LEAD ACTIONS
# =========================================
def process_post_lead_actions(row_number: int, user_name: str = "Moorgen User") -> Dict[str, Any]:
    row_data = get_row_dict_by_row_number(leads_ws, row_number)

    lead_id = safe_str(row_data.get("Lead_ID"))
    if not lead_id:
        return {"success": False, "message": "Lead_ID missing. Run lead creation first."}

    results = {
        "success": True,
        "lead_id": lead_id,
        "design": None,
        "boq": None,
    }

    post_action = safe_str(row_data.get("Post_Lead_Action")).lower()

    if post_action in {"design", "design + boq"} or is_yes(row_data.get("Design_Required")):
        if not safe_str(row_data.get("Latest_Design_ID")):
            results["design"] = create_design_tasks_from_lead(row_number, user_name=user_name)

    if post_action in {"boq", "design + boq"} or is_yes(row_data.get("BOQ_Required")):
        if safe_str(row_data.get("BOQ_Status")).lower() not in {"pending", "generated"}:
            results["boq"] = create_boq_request_from_lead(row_number, user_name=user_name)

    return results


# =========================================
# BULK PROCESSORS
# =========================================
def should_process_lead(row_data: Dict[str, Any]) -> bool:
    if safe_str(row_data.get("Lead_ID")):
        return False

    status = safe_str(row_data.get("Automation_Status")).lower()
    if status not in {"", "pending"}:
        return False

    if not safe_str(row_data.get("Client_Name")) and not safe_str(row_data.get("Project_Name")):
        return False

    return True

def process_all_pending_leads(user_name: str = "Moorgen Auto") -> Dict[str, Any]:
    all_values = leads_ws.get_all_values()

    processed = 0
    failed = 0
    results = []

    for row_number in range(2, len(all_values) + 1):
        row_data = get_row_dict_by_row_number(leads_ws, row_number)

        if not should_process_lead(row_data):
            continue

        result = create_lead_record(row_number=row_number, user_name=user_name)
        results.append(result)

        if result["success"]:
            processed += 1
        else:
            failed += 1

    return {
        "success": True,
        "processed": processed,
        "failed": failed,
        "results": results,
    }

def process_all_post_lead_actions(user_name: str = "Moorgen Auto") -> Dict[str, Any]:
    all_values = leads_ws.get_all_values()

    processed = 0
    results = []

    for row_number in range(2, len(all_values) + 1):
        row_data = get_row_dict_by_row_number(leads_ws, row_number)

        if not safe_str(row_data.get("Lead_ID")):
            continue

        needs_design = is_yes(row_data.get("Design_Required")) and not safe_str(row_data.get("Latest_Design_ID"))
        needs_boq = is_yes(row_data.get("BOQ_Required")) and safe_str(row_data.get("BOQ_Status")).lower() not in {"pending", "generated"}

        if not needs_design and not needs_boq:
            continue

        result = process_post_lead_actions(row_number=row_number, user_name=user_name)
        results.append(result)
        processed += 1

    return {
        "success": True,
        "processed_rows": processed,
        "results": results,
    }

def process_all_order_confirmations(user_name: str = "Moorgen Auto") -> Dict[str, Any]:
    all_values = leads_ws.get_all_values()

    processed = 0
    failed = 0
    results = []

    for row_number in range(2, len(all_values) + 1):
        row_data = get_row_dict_by_row_number(leads_ws, row_number)

        if not safe_str(row_data.get("Lead_ID")):
            continue

        if not is_yes(row_data.get("Order_Confirmed")):
            continue

        if safe_str(row_data.get("Project_ID")):
            continue

        result = confirm_order_from_lead(row_number=row_number, user_name=user_name)
        results.append(result)

        if result["success"]:
            processed += 1
        else:
            failed += 1

    return {
        "success": True,
        "processed": processed,
        "failed": failed,
        "results": results,
    }


# =========================================
# MAIN
# =========================================
if __name__ == "__main__":
    print("1. Process pending leads")
    print("2. Process post-lead actions")
    print("3. Process order confirmations")
    choice = input("Enter choice (1, 2 or 3): ").strip()

    if choice == "1":
        output = process_all_pending_leads(user_name="Moorgen Auto")
        print(output)
    elif choice == "2":
        output = process_all_post_lead_actions(user_name="Moorgen Auto")
        print(output)
    elif choice == "3":
        output = process_all_order_confirmations(user_name="Moorgen Auto")
        print(output)
    else:
        print("Invalid choice")
