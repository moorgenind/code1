from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import secrets
import psycopg2

router = APIRouter()

DB_URL = "postgresql://postgres:tXcpBGiZvXNSMxsDtUiJYjsJrzgLugcE@nozomi.proxy.rlwy.net:10121/railway"

VALID_USERS = {
    "info@moorgenindia.co": "moorgen@2526",
    "sales@moorgenindia.co": "moorgen@2526",
    "design@moorgenindia.co": "moorgen@2526",
}

def parse_device(user_agent: str) -> str:
    ua = (user_agent or "").lower()
    browser = (
        "Chrome" if "chrome" in ua else
        "Safari" if "safari" in ua else
        "Firefox" if "firefox" in ua else
        "Unknown Browser"
    )
    os_name = (
        "Mac OS" if "mac os" in ua else
        "Windows" if "windows" in ua else
        "iOS" if "iphone" in ua or "ipad" in ua else
        "Android" if "android" in ua else
        "Unknown OS"
    )
    return f"{browser} on {os_name}"


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(payload: LoginRequest, request: Request):
    expected = VALID_USERS.get(payload.email)
    if not expected or expected != payload.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = secrets.token_hex(32)
    ua = request.headers.get("user-agent", "")
    ip = request.client.host if request.client else None

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO user_sessions (user_email, session_token, device_info, user_agent, ip_address)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (payload.email, token, parse_device(ua), ua, ip),
    )
    conn.commit()
    cur.close()
    conn.close()

    return {"token": token, "email": payload.email}


@router.get("/sessions/{email}")
def list_sessions(email: str):
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, device_info, ip_address, created_at, last_active_at, is_active
        FROM user_sessions
        WHERE user_email = %s
        ORDER BY last_active_at DESC
        """,
        (email,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {
            "id": r[0],
            "device": r[1],
            "ip": r[2],
            "created_at": r[3],
            "last_active": r[4],
            "active": r[5],
        }
        for r in rows
    ]


@router.post("/sessions/{session_id}/revoke")
def revoke_session(session_id: int):
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE user_sessions SET is_active = FALSE, revoked_at = NOW()
        WHERE id = %s
        """,
        (session_id,),
    )
    conn.commit()
    cur.close()
    conn.close()
    return {"status": "revoked"}
