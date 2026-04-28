from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


# =========================================
# DEALER SCHEMAS
# =========================================
class DealerCreate(BaseModel):
    firm_name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None


class DealerResponse(BaseModel):
    dealer_id: int
    firm_name: str
    contact_person: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    city: Optional[str]
    state: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# =========================================
# CLIENT SCHEMAS
# =========================================
class ClientCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    city: Optional[str] = None
    client_type: str  # direct / dealer
    dealer_id: Optional[int] = None


class ClientResponse(BaseModel):
    client_id: int
    name: str
    phone: Optional[str]
    email: Optional[str]
    city: Optional[str]
    client_type: str
    dealer_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# =========================================
# LEAD SCHEMAS
# =========================================
class LeadCreate(BaseModel):
    client_id: Optional[int] = None
    dealer_id: Optional[int] = None
    project_name: str
    city: Optional[str] = None
    channel: str  # direct / dealer
    category: str  # architectural / decorative / automation / exterior / mixed
    lead_source: Optional[str] = None
    assigned_to: Optional[str] = None
    remarks: Optional[str] = None
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    client_email: Optional[str] = None
    client_address: Optional[str] = None
    created_at: Optional[str] = None

    # Scope flags — determines what BOQs and design requests get created
    arch_lighting: bool = False
    decorative_lighting: bool = False
    automation: bool = False
    exterior_lighting: bool = False
    design_required: bool = False


class LeadStatusUpdate(BaseModel):
    status: str
    lost_reason: Optional[str] = None


class LeadResponse(BaseModel):
    lead_id: int
    lead_code: str
    client_id: Optional[int]
    dealer_id: Optional[int]
    project_name: str
    city: Optional[str]
    channel: str
    category: str
    lead_source: Optional[str]
    assigned_to: Optional[str]
    status: str
    lost_reason: Optional[str]
    drive_folder_url: Optional[str]
    remarks: Optional[str]
    client_name: Optional[str]
    client_phone: Optional[str]
    client_email: Optional[str]
    client_address: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =========================================
# BOQ SCHEMAS
# =========================================
class BoqLineItemCreate(BaseModel):
    level: str
    area: str
    product_sku: Optional[str] = None
    product_name: str
    quantity: int
    unit_price: Decimal
    discount_pct: Optional[Decimal] = Decimal("0")
    notes: Optional[str] = None
    image_url: Optional[str] = None


class BoqCreate(BaseModel):
    lead_id: int
    category: str  # architectural / decorative / automation / exterior
    created_by: Optional[str] = None
    line_items: Optional[List[BoqLineItemCreate]] = []


class BoqStatusUpdate(BaseModel):
    status: str  # draft / sent / approved / rejected
    drive_quote_url: Optional[str] = None


class BoqLineItemResponse(BaseModel):
    line_item_id: int
    boq_id: int
    level: str
    area: str
    product_sku: Optional[str]
    product_name: str
    quantity: int
    unit_price: Decimal
    discount_pct: Decimal
    line_total: Decimal
    notes: Optional[str]
    image_url: Optional[str] = None

    class Config:
        from_attributes = True


class BoqResponse(BaseModel):
    boq_id: int
    boq_code: str
    lead_id: int
    category: str
    version: int
    status: str
    drive_quote_url: Optional[str]
    total_amount: Optional[Decimal]
    created_by: Optional[str]
    created_at: datetime
    approved_at: Optional[datetime]
    line_items: List[BoqLineItemResponse] = []

    class Config:
        from_attributes = True


# =========================================
# DESIGN REQUEST SCHEMAS
# =========================================
class DesignRequestCreate(BaseModel):
    lead_id: int
    boq_id: Optional[int] = None
    request_type: str  # lighting_layout / automation_proposal / canva_presentation
    assigned_to: Optional[str] = None
    notes: Optional[str] = None


class DesignRequestStatusUpdate(BaseModel):
    status: str  # pending / in_progress / completed / approved
    drive_output_url: Optional[str] = None
    completed_at: Optional[datetime] = None


class DesignRequestResponse(BaseModel):
    design_request_id: int
    design_code: str
    lead_id: int
    boq_id: Optional[int]
    request_type: str
    status: str
    assigned_to: Optional[str]
    drive_output_url: Optional[str]
    notes: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True