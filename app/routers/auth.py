from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel
import hashlib, jwt, os, secrets
from datetime import datetime, timedelta
from app.database import get_db
from app import models
from sqlalchemy import text

router = APIRouter()
security = HTTPBearer()

SECRET = os.getenv("JWT_SECRET", "moorgen_secret_2526_key")
ALGO = "HS256"

class LoginRequest(BaseModel):
    email: str
    password: str

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def make_token(user_id: int, email: str, name: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "name": name,
        "exp": datetime.utcnow() + timedelta(days=30)
    }
    return jwt.encode(payload, SECRET, algorithm=ALGO)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET, algorithms=[ALGO])
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

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


@router.post("/login")
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(
        models.User.email == req.email,
        models.User.is_active == True
    ).first()
    if not user or user.password_hash != hash_pw(req.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = make_token(user.user_id, user.email, user.name)

    # Log this login as a session
    ua = request.headers.get("user-agent", "")
    ip = request.client.host if request.client else None
    session_token = secrets.token_hex(16)
    db.execute(
        text(
            """
            INSERT INTO user_sessions (user_email, session_token, device_info, user_agent, ip_address)
            VALUES (:email, :token, :device, :ua, :ip)
            """
        ),
        {"email": user.email, "token": session_token, "device": parse_device(ua), "ua": ua, "ip": ip},
    )
    db.commit()

    return {"token": token, "name": user.name, "email": user.email}


@router.get("/me")
def me(payload: dict = Depends(verify_token)):
    return payload


@router.get("/sessions/{email}")
def list_sessions(email: str, db: Session = Depends(get_db)):
    rows = db.execute(
        text(
            """
            SELECT id, device_info, ip_address, created_at, last_active_at, is_active
            FROM user_sessions
            WHERE user_email = :email
            ORDER BY last_active_at DESC
            """
        ),
        {"email": email},
    ).fetchall()
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
def revoke_session(session_id: int, db: Session = Depends(get_db)):
    db.execute(
        text(
            "UPDATE user_sessions SET is_active = FALSE, revoked_at = NOW() WHERE id = :id"
        ),
        {"id": session_id},
    )
    db.commit()
    return {"status": "revoked"}
