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
    category = Column(String(100))  # architectural / decorative / automation / exterior
    subcategory = Column(String(100))
    unit_price = Column(Numeric(10, 2))
    is_active = Column(Boolean, default=True)


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