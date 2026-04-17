import os
import re
import pickle
from typing import Any, Dict
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(BASE_DIR, "..", "token.pickle")
OAUTH_FILE = os.path.join(BASE_DIR, "..", "oauth_credentials.json")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

LEADS_PARENT_FOLDER_ID = os.getenv("LEADS_PARENT_FOLDER_ID", "1jjZK0PPOyHfCFmSY9CWcxr8eoDsfaIR2")


def get_google_creds():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
    return creds


def get_drive_service():
    token_b64 = os.getenv("GOOGLE_TOKEN_BASE64")

    if token_b64:
        import base64
        import pickle
        from google.auth.transport.requests import Request
        creds = pickle.loads(base64.b64decode(token_b64))
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
    else:
        import pickle
        from google.auth.transport.requests import Request
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        TOKEN_FILE = os.path.join(BASE_DIR, "..", "token.pickle")
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

    return build("drive", "v3", credentials=creds)


def slugify(text: Any) -> str:
    text = str(text).strip() if text else ""
    text = re.sub(r"[^A-Za-z0-9]+", "_", text)
    return text.strip("_")


def create_drive_folder(folder_name: str, parent_folder_id: str) -> Dict:
    drive_service = get_drive_service()
    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_folder_id],
    }
    return drive_service.files().create(
        body=metadata,
        fields="id,name,webViewLink"
    ).execute()


def create_subfolder(parent_folder_id: str, subfolder_name: str) -> Dict:
    drive_service = get_drive_service()
    metadata = {
        "name": subfolder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_folder_id],
    }
    return drive_service.files().create(
        body=metadata,
        fields="id,name,webViewLink"
    ).execute()


def create_lead_folder_structure(
    lead_code: str,
    client_name: str,
    project_name: str,
    city: str = ""
) -> Dict:
    safe_client = slugify(client_name) or "Client"
    safe_project = slugify(project_name) or "Project"
    safe_city = slugify(city)

    parts = [lead_code, safe_client, safe_project]
    if safe_city:
        parts.append(safe_city)

    main_folder_name = "_".join(parts)
    main_folder = create_drive_folder(main_folder_name, LEADS_PARENT_FOLDER_ID)

    subfolders = [
        "01_Quotes",
        "02_Layouts",
        "03_Proposals",
        "04_Automation",
        "05_Mechanical",
        "06_Execution",
        "07_Site_Photos",
    ]

    for subfolder_name in subfolders:
        create_subfolder(main_folder["id"], subfolder_name)

    return {
        "main_folder_id": main_folder["id"],
        "main_folder_name": main_folder["name"],
        "main_folder_link": main_folder["webViewLink"],
    }