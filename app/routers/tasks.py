from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel
import os

from app.database import get_db
from app import models

router = APIRouter()

HAJIRA_NAME = "Hajira"
SHANMUKHI_NAME = "Shanmukhi"
FEROZ_NAME = "Feroz"

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

def get_emp(db, name):
    return db.query(models.Employee).filter(models.Employee.name == name).first()

def today_eod():
    return datetime.utcnow().replace(hour=18, minute=0, second=0, microsecond=0)

def task_exists_today(db, employee_id, title):
    today = datetime.utcnow().date()
    return db.query(models.Task).filter(
        models.Task.employee_id == employee_id,
        models.Task.title == title,
        func.date(models.Task.created_at) == today
    ).first() is not None

def auto_task(db, title, description, employee_id, priority, linked_lead_id=None, linked_label=None):
    if task_exists_today(db, employee_id, title):
        return None
    task = models.Task(
        title=title, description=description, employee_id=employee_id,
        priority=priority, due_date=today_eod(),
        linked_lead_id=linked_lead_id, linked_label=linked_label,
        is_ai_suggested=True, status="pending",
    )
    db.add(task)
    return task

@router.get("/employees")
def list_employees(db: Session = Depends(get_db)):
    return db.query(models.Employee).filter(models.Employee.is_active == True).all()

@router.get("/")
def list_tasks(employee_id: Optional[int] = None, status: Optional[str] = None, db: Session = Depends(get_db)):
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
        if t.frequency == "daily": should_run = True
        elif t.frequency == "weekly": should_run = weekday == "monday"
        else: should_run = t.frequency == weekday
        if not should_run: continue
        already = db.query(models.Task).filter(models.Task.template_id == t.template_id, func.date(models.Task.created_at) == today).first()
        if already: continue
        task = models.Task(title=t.title, description=t.description, employee_id=t.employee_id, priority=t.priority, due_date=today_eod(), is_recurring=True, template_id=t.template_id, status="pending")
        db.add(task)
        created.append(t.title)
    db.commit()
    return {"created": len(created), "tasks": created}

@router.post("/generate-smart")
def generate_smart_tasks(db: Session = Depends(get_db)):
    hajira = get_emp(db, HAJIRA_NAME)
    shanmukhi = get_emp(db, SHANMUKHI_NAME)
    feroz = get_emp(db, FEROZ_NAME)
    if not all([hajira, shanmukhi, feroz]):
        raise HTTPException(status_code=400, detail="Employees not found")
    created = []
    now = datetime.utcnow()
    d3 = now - timedelta(days=3)
    d5 = now - timedelta(days=5)
    d7 = now - timedelta(days=7)

    # HAJIRA - new leads stale 3+ days
    for lead in db.query(models.Lead).filter(models.Lead.status == "new", models.Lead.updated_at <= d3).all():
        t = auto_task(db, f"Follow up: {lead.client_name or lead.project_name}", f"New lead {lead.lead_code} from {lead.city or 'unknown'} — no activity 3+ days. Call to qualify.", hajira.employee_id, "high", lead.lead_id, f"Lead: {lead.lead_code} — {lead.project_name or lead.client_name}")
        if t: created.append(t.title)

    # HAJIRA - quote sent no response 3+ days
    for lead in db.query(models.Lead).filter(models.Lead.status == "quote_sent", models.Lead.updated_at <= d3).all():
        t = auto_task(db, f"Chase quote: {lead.client_name or lead.project_name}", f"Quote sent for {lead.lead_code} — no response in 3+ days. Follow up to push for decision.", hajira.employee_id, "high", lead.lead_id, f"Lead: {lead.lead_code} — {lead.project_name or lead.client_name}")
        if t: created.append(t.title)

    # HAJIRA - negotiation stale 5+ days
    for lead in db.query(models.Lead).filter(models.Lead.status == "negotiation", models.Lead.updated_at <= d5).all():
        t = auto_task(db, f"Negotiation follow-up: {lead.client_name or lead.project_name}", f"{lead.lead_code} in negotiation 5+ days. Check status and try to close.", hajira.employee_id, "high", lead.lead_id, f"Lead: {lead.lead_code} — {lead.project_name or lead.client_name}")
        if t: created.append(t.title)

    # HAJIRA - unpaid invoices 7+ days
    for inv in db.query(models.Invoice).filter(models.Invoice.status.in_(["unpaid", "partial"]), models.Invoice.created_at <= d7).all():
        lead = db.query(models.Lead).filter(models.Lead.lead_id == inv.lead_id).first()
        client = lead.client_name if lead else "Client"
        paid = sum(float(p.amount) for p in inv.payments)
        outstanding = float(inv.invoice_amount) - paid
        t = auto_task(db, f"Chase payment: {client} — Rs.{outstanding:,.0f} due", f"Invoice {inv.invoice_code} has Rs.{outstanding:,.0f} outstanding 7+ days. Call to arrange payment.", hajira.employee_id, "high", inv.lead_id, f"Invoice: {inv.invoice_code} — {client}")
        if t: created.append(t.title)

    # SHANMUKHI - draft BOQs 3+ days
    for boq in db.query(models.Boq).filter(models.Boq.status == "draft", models.Boq.created_at <= d3).all():
        lead = db.query(models.Lead).filter(models.Lead.lead_id == boq.lead_id).first()
        project = lead.project_name if lead else "Project"
        t = auto_task(db, f"Complete BOQ: {project} ({boq.category})", f"BOQ {boq.boq_code} for {project} still draft after 3+ days. Complete and send for approval.", shanmukhi.employee_id, "high", boq.lead_id, f"BOQ: {boq.boq_code} — {project}")
        if t: created.append(t.title)

    # SHANMUKHI - pending design requests 3+ days
    for design in db.query(models.DesignRequest).filter(models.DesignRequest.status == "pending", models.DesignRequest.created_at <= d3).all():
        lead = db.query(models.Lead).filter(models.Lead.lead_id == design.lead_id).first()
        project = lead.project_name if lead else "Project"
        t = auto_task(db, f"Design request pending: {project}", f"Design request {design.design_code} ({design.request_type}) for {project} pending 3+ days.", shanmukhi.employee_id, "medium", design.lead_id, f"Design: {design.design_code} — {project}")
        if t: created.append(t.title)

    # SHANMUKHI - open snags in active project stages
    for pt in db.query(models.ProjectTracking).filter(models.ProjectTracking.current_stage.in_(["site_coordination", "installation", "testing"])).all():
        open_snags = db.query(models.ProjectSnag).filter(models.ProjectSnag.lead_id == pt.lead_id, models.ProjectSnag.status == "open").count()
        if open_snags > 0:
            lead = db.query(models.Lead).filter(models.Lead.lead_id == pt.lead_id).first()
            project = lead.project_name if lead else "Project"
            t = auto_task(db, f"Resolve snags: {project} ({open_snags} open)", f"Project {project} in {pt.current_stage} has {open_snags} open snag(s). Review and coordinate resolution.", shanmukhi.employee_id, "high", pt.lead_id, f"Project: {project} — {pt.current_stage}")
            if t: created.append(t.title)

    # SHANMUKHI - boq_in_progress stale 5+ days
    for lead in db.query(models.Lead).filter(models.Lead.status == "boq_in_progress", models.Lead.updated_at <= d5).all():
        t = auto_task(db, f"Update BOQ status: {lead.project_name or lead.client_name}", f"Lead {lead.lead_code} in BOQ stage for 5+ days. Check progress and update status.", shanmukhi.employee_id, "medium", lead.lead_id, f"Lead: {lead.lead_code} — {lead.project_name or lead.client_name}")
        if t: created.append(t.title)

    # FEROZ - material delivery no confirmation
    for pt in db.query(models.ProjectTracking).filter(models.ProjectTracking.current_stage == "material_delivery", models.ProjectTracking.actual_delivery == None).all():
        lead = db.query(models.Lead).filter(models.Lead.lead_id == pt.lead_id).first()
        project = lead.project_name if lead else "Project"
        t = auto_task(db, f"Confirm delivery: {project}", f"Project {project} in material delivery stage but no delivery confirmed. Check with supplier and update.", feroz.employee_id, "high", pt.lead_id, f"Project: {project} — material delivery")
        if t: created.append(t.title)

    # FEROZ - installation with automation scope
    for pt in db.query(models.ProjectTracking).filter(models.ProjectTracking.current_stage == "installation").all():
        lead = db.query(models.Lead).filter(models.Lead.lead_id == pt.lead_id, models.Lead.category.in_(["automation", "mixed"])).first()
        if lead:
            t = auto_task(db, f"Automation config: {lead.project_name or lead.client_name}", f"Project {lead.project_name} in installation with automation scope. Check ZigbeePlus configuration.", feroz.employee_id, "high", lead.lead_id, f"Project: {lead.project_name} — installation")
            if t: created.append(t.title)

    # FEROZ - won leads with no project tracking
    for lead in db.query(models.Lead).filter(models.Lead.status == "won").all():
        pt = db.query(models.ProjectTracking).filter(models.ProjectTracking.lead_id == lead.lead_id).first()
        if not pt:
            t = auto_task(db, f"Setup project tracking: {lead.project_name or lead.client_name}", f"Lead {lead.lead_code} is won but has no project tracking. Set up and coordinate logistics.", feroz.employee_id, "medium", lead.lead_id, f"Lead: {lead.lead_code} — {lead.project_name or lead.client_name}")
            if t: created.append(t.title)

    # FEROZ - draft POs 3+ days
    for po in db.query(models.PurchaseOrder).filter(models.PurchaseOrder.status == "draft", models.PurchaseOrder.created_at <= d3).all():
        lead = db.query(models.Lead).filter(models.Lead.lead_id == po.lead_id).first()
        project = lead.project_name if lead else "Project"
        t = auto_task(db, f"Place PO: {po.po_code} — {project}", f"Purchase order {po.po_code} for {project} still draft after 3+ days. Review and place with supplier.", feroz.employee_id, "high", po.lead_id, f"PO: {po.po_code} — {project}")
        if t: created.append(t.title)

    db.commit()
    return {"created": len(created), "tasks": created}

@router.get("/stats")
def get_task_stats(db: Session = Depends(get_db)):
    total = db.query(models.Task).count()
    pending = db.query(models.Task).filter(models.Task.status == "pending").count()
    in_progress = db.query(models.Task).filter(models.Task.status == "in_progress").count()
    done = db.query(models.Task).filter(models.Task.status == "done").count()
    overdue = db.query(models.Task).filter(models.Task.status != "done", models.Task.due_date < datetime.utcnow()).count()
    return {"total": total, "pending": pending, "in_progress": in_progress, "done": done, "overdue": overdue}

@router.post("/assign-suggestion")
def assign_suggestion(payload: TaskCreate, db: Session = Depends(get_db)):
    task = models.Task(title=payload.title, description=payload.description, employee_id=payload.employee_id, priority=payload.priority, due_date=payload.due_date or today_eod(), linked_lead_id=payload.linked_lead_id, linked_label=payload.linked_label, is_ai_suggested=True, status="pending")
    db.add(task)
    db.commit()
    db.refresh(task)
    return {"success": True, "task_id": task.task_id}
