from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
import os
import json
import httpx

from app.database import get_db
from app import models

router = APIRouter()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

class EmployeeOut(BaseModel):
    employee_id: int
    name: str
    email: Optional[str]
    role: str
    is_active: bool
    class Config:
        from_attributes = True

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    employee_id: int
    priority: Optional[str] = "medium"
    due_date: Optional[datetime] = None
    linked_lead_id: Optional[int] = None
    linked_label: Optional[str] = None
    is_recurring: Optional[bool] = False
    template_id: Optional[int] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[datetime] = None
    linked_lead_id: Optional[int] = None
    linked_label: Optional[str] = None

class TemplateCreate(BaseModel):
    title: str
    description: Optional[str] = None
    employee_id: int
    priority: Optional[str] = "medium"
    frequency: Optional[str] = "daily"

@router.get("/employees")
def list_employees(db: Session = Depends(get_db)):
    return db.query(models.Employee).filter(models.Employee.is_active == True).all()

@router.get("/")
def list_tasks(
    employee_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Task)
    if employee_id:
        query = query.filter(models.Task.employee_id == employee_id)
    if status:
        query = query.filter(models.Task.status == status)
    tasks = query.order_by(models.Task.due_date.asc()).all()
    result = []
    for t in tasks:
        emp = db.query(models.Employee).filter(models.Employee.employee_id == t.employee_id).first()
        d = {c.name: getattr(t, c.name) for c in t.__table__.columns}
        d["employee_name"] = emp.name if emp else None
        result.append(d)
    return result

@router.post("/")
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    task = models.Task(**payload.dict())
    db.add(task)
    db.commit()
    db.refresh(task)
    emp = db.query(models.Employee).filter(models.Employee.employee_id == task.employee_id).first()
    result = {c.name: getattr(task, c.name) for c in task.__table__.columns}
    result["employee_name"] = emp.name if emp else None
    return result

@router.patch("/{task_id}")
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(task, field, value)
    if payload.status == "done" and not task.completed_at:
        task.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    emp = db.query(models.Employee).filter(models.Employee.employee_id == task.employee_id).first()
    result = {c.name: getattr(task, c.name) for c in task.__table__.columns}
    result["employee_name"] = emp.name if emp else None
    return result

@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"success": True}

@router.get("/templates")
def list_templates(db: Session = Depends(get_db)):
    templates = db.query(models.RecurringTemplate).filter(models.RecurringTemplate.is_active == True).all()
    result = []
    for t in templates:
        emp = db.query(models.Employee).filter(models.Employee.employee_id == t.employee_id).first()
        d = {c.name: getattr(t, c.name) for c in t.__table__.columns}
        d["employee_name"] = emp.name if emp else None
        result.append(d)
    return result

@router.post("/templates")
def create_template(payload: TemplateCreate, db: Session = Depends(get_db)):
    template = models.RecurringTemplate(**payload.dict())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template

@router.delete("/templates/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db)):
    t = db.query(models.RecurringTemplate).filter(models.RecurringTemplate.template_id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    t.is_active = False
    db.commit()
    return {"success": True}

@router.post("/generate-recurring")
def generate_recurring_tasks(db: Session = Depends(get_db)):
    today = datetime.utcnow().date()
    weekday = datetime.utcnow().strftime("%A").lower()
    templates = db.query(models.RecurringTemplate).filter(models.RecurringTemplate.is_active == True).all()
    created = []
    for t in templates:
        if t.frequency == "daily":
            should_run = True
        elif t.frequency == "weekly":
            should_run = weekday == "monday"
        else:
            should_run = t.frequency == weekday
        if not should_run:
            continue
        already = db.query(models.Task).filter(
            models.Task.template_id == t.template_id,
            func.date(models.Task.created_at) == today
        ).first()
        if already:
            continue
        task = models.Task(
            title=t.title,
            description=t.description,
            employee_id=t.employee_id,
            priority=t.priority,
            due_date=datetime.utcnow().replace(hour=18, minute=0, second=0),
            is_recurring=True,
            template_id=t.template_id,
            status="pending",
        )
        db.add(task)
        created.append(t.title)
    db.commit()
    return {"created": len(created), "tasks": created}

@router.get("/ai-suggestions")
async def get_ai_suggestions(db: Session = Depends(get_db)):
    employees = db.query(models.Employee).filter(models.Employee.is_active == True).all()
    emp_list = [{"id": e.employee_id, "name": e.name, "role": e.role} for e in employees]

    cutoff = datetime.utcnow() - timedelta(days=5)
    stale_leads = db.query(models.Lead).filter(
        models.Lead.updated_at <= cutoff,
        models.Lead.status.notin_(["won", "lost"])
    ).limit(10).all()
    stale_leads_data = [{
        "lead_id": l.lead_id,
        "lead_code": l.lead_code,
        "project_name": l.project_name,
        "client_name": l.client_name,
        "city": l.city,
        "status": l.status,
        "days_stale": (datetime.utcnow() - l.updated_at).days if l.updated_at else "unknown"
    } for l in stale_leads]

    overdue_invoices = db.query(models.Invoice).filter(models.Invoice.status == "unpaid").limit(5).all()
    invoice_data = [{"invoice_code": i.invoice_code, "amount": float(i.invoice_amount or 0), "lead_id": i.lead_id} for i in overdue_invoices]

    draft_boqs = db.query(models.Boq).filter(models.Boq.status == "draft").limit(5).all()
    boq_data = [{"boq_code": b.boq_code, "lead_id": b.lead_id, "category": b.category} for b in draft_boqs]

    pending_designs = db.query(models.DesignRequest).filter(models.DesignRequest.status == "pending").limit(5).all()
    design_data = [{"design_code": d.design_code, "lead_id": d.lead_id, "request_type": d.request_type} for d in pending_designs]

    open_snags = db.query(models.ProjectSnag).filter(models.ProjectSnag.status == "open").limit(5).all()
    snag_data = [{"snag_id": s.id, "lead_id": s.lead_id, "description": s.description} for s in open_snags]

    system_prompt = """You are an operations assistant for Moorgen Innovations, a smart lighting and automation company in Hyderabad.
You help the director (Hindu Reddy) generate daily task suggestions for his small team.

Employees and their roles:
- Hajira: in-house sales, follow-ups, lead activity, client communication
- Shanmukhi: lighting design, BOQ preparation, site marking, technical design
- Feroz: logistics, technical configuration, delivery coordination

Rules:
1. Suggest 5-7 specific, actionable tasks based on the live data provided
2. Match tasks to the right employee based on their role
3. Be specific — include lead names, codes, amounts where relevant
4. Priority: high = urgent/overdue, medium = normal, low = routine
5. Return ONLY valid JSON, no markdown, no explanation

Return this exact JSON format:
{
  "suggestions": [
    {
      "title": "short task title",
      "description": "specific details about what to do",
      "employee_id": <integer>,
      "employee_name": "<name>",
      "priority": "high|medium|low",
      "linked_lead_id": <integer or null>,
      "linked_label": "<e.g. Lead: LD-2526-012 - Client Name> or null",
      "reason": "one line explaining why this task is suggested today"
    }
  ]
}"""

    user_prompt = f"""Today's date: {datetime.utcnow().strftime('%Y-%m-%d')}
Employees: {json.dumps(emp_list)}
Stale leads (no activity 5+ days): {json.dumps(stale_leads_data)}
Unpaid invoices: {json.dumps(invoice_data)}
Draft BOQs not yet sent: {json.dumps(boq_data)}
Pending design requests: {json.dumps(design_data)}
Open project snags: {json.dumps(snag_data)}
Generate today's task suggestions."""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1500,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_prompt}]
                }
            )
            data = response.json()
            text = data["content"][0]["text"]
            text = text.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(text)
            return parsed
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI suggestion failed: {str(e)}")

@router.post("/assign-suggestion")
def assign_suggestion(payload: TaskCreate, db: Session = Depends(get_db)):
    task = models.Task(
        title=payload.title,
        description=payload.description,
        employee_id=payload.employee_id,
        priority=payload.priority,
        due_date=payload.due_date or datetime.utcnow().replace(hour=18, minute=0, second=0),
        linked_lead_id=payload.linked_lead_id,
        linked_label=payload.linked_label,
        is_ai_suggested=True,
        status="pending",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return {"success": True, "task_id": task.task_id}

@router.get("/stats")
def get_task_stats(db: Session = Depends(get_db)):
    total = db.query(models.Task).count()
    pending = db.query(models.Task).filter(models.Task.status == "pending").count()
    in_progress = db.query(models.Task).filter(models.Task.status == "in_progress").count()
    done = db.query(models.Task).filter(models.Task.status == "done").count()
    overdue = db.query(models.Task).filter(
        models.Task.status != "done",
        models.Task.due_date < datetime.utcnow()
    ).count()
    return {"total": total, "pending": pending, "in_progress": in_progress, "done": done, "overdue": overdue}
