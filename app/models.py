from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, 
    Text, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Dealer(Base):
    __tablename__ = "dealers"

    dealer_id = Column(Integer, primary_key=True, index=True)
    firm_name = Column(String(255), nullable=False)
    contact_person = Column(String(255))
    phone = Column(String(20))
    email = Column(String(255))
    city = Column(String(100))
    state = Column(String(100))
    status = Column(String(50), default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    dealer_token = Column(String(255), unique=True, nullable=True)
    slug = Column(String(100), unique=True, nullable=True)
    portal_states = Column(ARRAY(String), nullable=True)
    assigned_lead_ids = Column(ARRAY(Integer), nullable=True)

    clients = relationship("Client", back_populates="dealer")
    leads = relationship("Lead", back_populates="dealer")


class Client(Base):
    __tablename__ = "clients"

    client_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(20))
    email = Column(String(255))
    city = Column(String(100))
    client_type = Column(String(50), nullable=False)  # direct / dealer
    dealer_id = Column(Integer, ForeignKey("dealers.dealer_id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    dealer = relationship("Dealer", back_populates="clients")
    leads = relationship("Lead", back_populates="client")


class Product(Base):
    __tablename__ = "products"
    product_id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), unique=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100))
    subcategory = Column(String(100))
    unit_price = Column(Numeric(10, 2))
    is_active = Column(Boolean, default=True)
    family = Column(String(255))
    family_no = Column(String(100))
    model_no = Column(String(100))
    product_type = Column(String(100))
    trim = Column(String(50))
    cutout_size = Column(String(50))
    cct = Column(String(100))
    beam_angle = Column(String(50))
    power = Column(String(50))
    voltage = Column(String(50))
    current = Column(String(50))
    body_color = Column(String(50))
    cup_color = Column(String(50))
    led_chip = Column(String(100))
    cri = Column(String(50))
    adjustable_angle = Column(String(50))
    mrp_gst = Column(Numeric(12, 2))
    flagship_mrp = Column(Numeric(12, 2))
    dealer_mrp = Column(Numeric(12, 2))
    landing_inr = Column(Numeric(12, 2))
    specification = Column(Text)
    description = Column(Text)
    # Decorative / shared extra fields
    product_type2 = Column(String(100))
    material = Column(String(255))
    dimensions = Column(String(255))
    protocol = Column(String(100))
    total_power = Column(String(50))
    mrp_inr = Column(Numeric(12, 2))
    dealer_cost = Column(Numeric(12, 2))
    flagship_cost = Column(Numeric(12, 2))


class Lead(Base):
    __tablename__ = "leads"

    lead_id = Column(Integer, primary_key=True, index=True)
    lead_code = Column(String(50), unique=True)  # e.g. LD-2526-001
    client_id = Column(Integer, ForeignKey("clients.client_id"), nullable=True)
    dealer_id = Column(Integer, ForeignKey("dealers.dealer_id"), nullable=True)
    project_name = Column(String(255))
    city = Column(String(100))
    channel = Column(String(50))  # direct / dealer
    category = Column(String(100))  # architectural / decorative / automation / exterior / mixed
    lead_source = Column(String(100))
    assigned_to = Column(String(255))
    status = Column(String(100), default="new")
    # new / qualified / boq_in_progress / design_in_progress /
    # quote_sent / negotiation / won / lost
    lost_reason = Column(Text)
    drive_folder_url = Column(Text)
    remarks = Column(Text)
    client_name = Column(String(255))
    client_phone = Column(String(20))
    client_email = Column(String(255))
    client_address = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    client = relationship("Client", back_populates="leads")
    dealer = relationship("Dealer", back_populates="leads")
    boqs = relationship("Boq", back_populates="lead")
    design_requests = relationship("DesignRequest", back_populates="lead")


class Boq(Base):
    __tablename__ = "boqs"

    boq_id = Column(Integer, primary_key=True, index=True)
    boq_code = Column(String(50), unique=True)  # e.g. BOQ-2526-001
    lead_id = Column(Integer, ForeignKey("leads.lead_id"))
    category = Column(String(100))  # architectural / decorative / automation / exterior
    version = Column(Integer, default=1)
    status = Column(String(50), default="draft")
    # draft / sent / approved / rejected
    drive_quote_url = Column(Text)
    total_amount = Column(Numeric(12, 2))
    created_by = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime(timezone=True))

    lead = relationship("Lead", back_populates="boqs")
    line_items = relationship("BoqLineItem", back_populates="boq")
    design_requests = relationship("DesignRequest", back_populates="boq")


class BoqLineItem(Base):
    __tablename__ = "boq_line_items"

    line_item_id = Column(Integer, primary_key=True, index=True)
    boq_id = Column(Integer, ForeignKey("boqs.boq_id"))
    level = Column(String(100))       # Ground Floor / First Floor
    area = Column(String(100))        # Living Room / Master Bedroom
    product_sku = Column(String(100)) # soft reference
    product_name = Column(String(255))
    quantity = Column(Integer)
    unit_price = Column(Numeric(10, 2))
    discount_pct = Column(Numeric(5, 2), default=0)
    line_total = Column(Numeric(12, 2))
    notes = Column(Text)
    image_url = Column(Text, nullable=True)

    boq = relationship("Boq", back_populates="line_items")


class DesignRequest(Base):
    __tablename__ = "design_requests"

    design_request_id = Column(Integer, primary_key=True, index=True)
    design_code = Column(String(50), unique=True)  # e.g. DSG-2526-001
    lead_id = Column(Integer, ForeignKey("leads.lead_id"))
    boq_id = Column(Integer, ForeignKey("boqs.boq_id"), nullable=True)
    request_type = Column(String(100))
    # lighting_layout / automation_proposal / canva_presentation
    status = Column(String(50), default="pending")
    # pending / in_progress / completed / approved
    assigned_to = Column(String(255))
    drive_output_url = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    lead = relationship("Lead", back_populates="design_requests")
    boq = relationship("Boq", back_populates="design_requests")

class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="admin")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Invoice(Base):
    __tablename__ = "invoices"
    invoice_id = Column(Integer, primary_key=True, index=True)
    invoice_code = Column(String(50), unique=True, nullable=False)
    lead_id = Column(Integer, ForeignKey("leads.lead_id"))
    boq_id = Column(Integer, ForeignKey("boqs.boq_id"), nullable=True)
    invoice_amount = Column(Numeric(14,2), nullable=False)
    status = Column(String(50), default="unpaid")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    payments = relationship("Payment", back_populates="invoice")
    line_items = relationship("InvoiceLineItem", back_populates="invoice")

class Payment(Base):
    __tablename__ = "payments"
    payment_id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.invoice_id"))
    payment_type = Column(String(50), nullable=False)
    amount = Column(Numeric(14,2), nullable=False)
    payment_date = Column(DateTime, nullable=False)
    payment_mode = Column(String(50), nullable=True)
    reference = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    invoice = relationship("Invoice", back_populates="payments")

class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.invoice_id"))
    sku = Column(String(100), nullable=True)
    product_name = Column(String(255), nullable=True)
    quantity = Column(Integer)
    unit_price = Column(Numeric(14,2))
    discount_pct = Column(Numeric(5,2), default=0)
    line_total = Column(Numeric(14,2))
    invoice = relationship("Invoice", back_populates="line_items")

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    po_id = Column(Integer, primary_key=True, index=True)
    po_code = Column(String(50), unique=True, nullable=False)
    lead_id = Column(Integer, ForeignKey("leads.lead_id"))
    supplier = Column(String(255), default="Moolken")
    status = Column(String(50), default="draft")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    ordered_at = Column(DateTime, nullable=True)
    received_at = Column(DateTime, nullable=True)
    line_items = relationship("POLineItem", back_populates="po")

class POLineItem(Base):
    __tablename__ = "po_line_items"
    id = Column(Integer, primary_key=True, index=True)
    po_id = Column(Integer, ForeignKey("purchase_orders.po_id"))
    sku = Column(String(100), nullable=True)
    product_name = Column(String(255), nullable=True)
    quantity_ordered = Column(Integer)
    quantity_received = Column(Integer, default=0)
    unit_cost = Column(Numeric(14,2))
    line_total = Column(Numeric(14,2))
    po = relationship("PurchaseOrder", back_populates="line_items")

class Stock(Base):
    __tablename__ = "stock"
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), unique=True, nullable=False)
    product_name = Column(String(255), nullable=True)
    quantity_on_hand = Column(Integer, default=0)
    quantity_reserved = Column(Integer, default=0)
    updated_at = Column(DateTime, nullable=True)

class ProjectTracking(Base):
    __tablename__ = "project_tracking"
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.lead_id"), unique=True)
    current_stage = Column(String(50), default="boq")
    boq_date = Column(DateTime, nullable=True)
    order_placed_date = Column(DateTime, nullable=True)
    site_coordination_date = Column(DateTime, nullable=True)
    material_delivery_date = Column(DateTime, nullable=True)
    installation_date = Column(DateTime, nullable=True)
    testing_date = Column(DateTime, nullable=True)
    handover_date = Column(DateTime, nullable=True)
    architect_name = Column(String(255), nullable=True)
    architect_phone = Column(String(50), nullable=True)
    client_contact = Column(String(255), nullable=True)
    client_phone = Column(String(50), nullable=True)
    pmc_name = Column(String(255), nullable=True)
    pmc_phone = Column(String(50), nullable=True)
    false_ceiling_contractor = Column(String(255), nullable=True)
    false_ceiling_phone = Column(String(50), nullable=True)
    automation_team = Column(String(255), nullable=True)
    lighting_team = Column(String(255), nullable=True)
    civil_ready = Column(Boolean, default=False)
    electricals_ready = Column(Boolean, default=False)
    network_ready = Column(Boolean, default=False)
    false_ceiling_ready = Column(Boolean, default=False)
    pre_inspection_done = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    updated_at = Column(DateTime, nullable=True)

class ProjectSnag(Base):
    __tablename__ = "project_snags"
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.lead_id"))
    description = Column(Text, nullable=False)
    status = Column(String(50), default="open")
    stage = Column(String(50), nullable=True)
    assigned_to = Column(String(255), nullable=True)
    reported_date = Column(DateTime, nullable=True)
    resolved_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SiteVisit(Base):
    __tablename__ = "site_visits"
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.lead_id"))
    visit_date = Column(DateTime, nullable=False)
    visit_type = Column(String(100), default="site_visit")
    attendees = Column(Text, nullable=True)
    observations = Column(Text, nullable=True)
    action_items = Column(Text, nullable=True)
    drive_photos_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
