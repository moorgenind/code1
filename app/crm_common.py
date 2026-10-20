"""Shared helpers for the CRM upgrade routers."""
import os
from datetime import datetime, date
from decimal import Decimal

import jwt
from fastapi import Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app import crm_logic as L

JWT_SECRET = os.getenv("JWT_SECRET", "moorgen_secret_2526_key")
# Comma-separated emails allowed to approve discounts / see all-company numbers
APPROVER_EMAILS = {e.strip().lower() for e in os.getenv("CRM_APPROVER_EMAILS", "info@moorgenindia.co").split(",") if e.strip()}


def current_user(request: Request):
    """Best-effort decode of the bearer token (routes stay open, as elsewhere in the app)."""
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    try:
        return jwt.decode(auth.split(" ", 1)[1], JWT_SECRET, algorithms=["HS256"])
    except Exception:
        return None


def user_name(request: Request, fallback="system"):
    u = current_user(request)
    return (u or {}).get("name") or (u or {}).get("email") or fallback


def is_approver(request: Request):
    u = current_user(request)
    return bool(u and (u.get("email") or "").lower() in APPROVER_EMAILS)


def jsonable(v):
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return v


def row_dict(obj):
    return {c.name: jsonable(getattr(obj, c.name)) for c in obj.__table__.columns}


def next_code(db: Session, model, code_col, prefix_root):
    """MAX-based code generator (never COUNT): e.g. SRV-2627-001."""
    prefix = f"{prefix_root}-{L.fy_prefix()}-"
    col = getattr(model, code_col)
    n = 0
    for (code,) in db.query(col).filter(col.like(f"{prefix}%")).all():
        try:
            n = max(n, int(code.rsplit("-", 1)[-1]))  # numeric max: "1000" > "999"
        except (ValueError, AttributeError):
            continue
    return f"{prefix}{str(n + 1).zfill(3)}"


def rescore(db: Session, lead):
    rank, has_arch = None, False
    if lead.architect_id:
        arch = db.query(models.Architect).filter(models.Architect.architect_id == lead.architect_id).first()
        if arch:
            has_arch, rank = True, arch.ranking
    score, grade, _ = L.score_lead(lead, architect_rank=rank, has_architect=has_arch)
    lead.lead_score, lead.lead_grade = score, grade
    return score, grade


def log_activity(db: Session, *, lead_id=None, architect_id=None, dealer_id=None, activity_type="note",
                 subject=None, notes=None, performed_by=None, employee_id=None, outcome=None,
                 activity_at=None, next_followup_at=None, touch=True):
    act = models.CrmActivity(
        lead_id=lead_id, architect_id=architect_id, dealer_id=dealer_id,
        activity_type=activity_type, subject=subject, notes=notes, outcome=outcome,
        performed_by=performed_by, employee_id=employee_id,
        activity_at=activity_at or L.now_utc(), next_followup_at=next_followup_at,
    )
    db.add(act)
    if touch and activity_type in L.TOUCH_TYPES:
        when = act.activity_at
        if lead_id:
            lead = db.query(models.Lead).filter(models.Lead.lead_id == lead_id).first()
            if lead and (lead.last_activity_at is None or L._aware(lead.last_activity_at) < L._aware(when)):
                lead.last_activity_at = when
        if architect_id and activity_type in ("architect_meeting", "meeting", "video_meeting", "site_visit", "event", "showroom_visit"):
            arch = db.query(models.Architect).filter(models.Architect.architect_id == architect_id).first()
            if arch and (arch.last_meeting_date is None or L._aware(arch.last_meeting_date) < L._aware(when)):
                arch.last_meeting_date = when
    if architect_id and next_followup_at:
        arch = db.query(models.Architect).filter(models.Architect.architect_id == architect_id).first()
        if arch:
            arch.next_followup_date = L._aware(next_followup_at).date()
    return act
