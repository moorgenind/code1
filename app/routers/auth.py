from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel
import hashlib, jwt, os
from datetime import datetime, timedelta
from app.database import get_db
from app import models

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

@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(
        models.User.email == req.email,
        models.User.is_active == True
    ).first()
    if not user or user.password_hash != hash_pw(req.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = make_token(user.user_id, user.email, user.name)
    return {"token": token, "name": user.name, "email": user.email}

@router.get("/me")
def me(payload: dict = Depends(verify_token)):
    return payload
