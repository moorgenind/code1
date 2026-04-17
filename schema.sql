-- DEALERS
CREATE TABLE dealers (
    dealer_id SERIAL PRIMARY KEY,
    firm_name VARCHAR(255) NOT NULL,
    contact_person VARCHAR(255),
    phone VARCHAR(20),
    email VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW()
);

-- CLIENTS
CREATE TABLE clients (
    client_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(255),
    city VARCHAR(100),
    client_type VARCHAR(50) NOT NULL, -- 'direct' or 'dealer'
    dealer_id INTEGER REFERENCES dealers(dealer_id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- PRODUCTS
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    sku VARCHAR(100) UNIQUE,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100), -- architectural / decorative / automation / exterior
    subcategory VARCHAR(100),
    unit_price NUMERIC(10,2),
    is_active BOOLEAN DEFAULT TRUE
);

-- LEADS
CREATE TABLE leads (
    lead_id SERIAL PRIMARY KEY,
    client_id INTEGER REFERENCES clients(client_id),
    dealer_id INTEGER REFERENCES dealers(dealer_id),
    project_name VARCHAR(255),
    city VARCHAR(100),
    channel VARCHAR(50), -- 'direct' or 'dealer'
    category VARCHAR(100), -- architectural / decorative / automation / exterior / mixed
    lead_source VARCHAR(100),
    status VARCHAR(100) DEFAULT 'new',
    -- new / qualified / boq_in_progress / design_in_progress / 
    -- quote_sent / negotiation / won / lost
    lost_reason TEXT,
    drive_folder_url TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- BOQS
CREATE TABLE boqs (
    boq_id SERIAL PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(lead_id),
    category VARCHAR(100), -- architectural / decorative / automation / exterior
    version INTEGER DEFAULT 1,
    status VARCHAR(50) DEFAULT 'draft',
    -- draft / sent / approved / rejected
    drive_quote_url TEXT,
    total_amount NUMERIC(12,2),
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    approved_at TIMESTAMP
);

-- BOQ LINE ITEMS
CREATE TABLE boq_line_items (
    line_item_id SERIAL PRIMARY KEY,
    boq_id INTEGER REFERENCES boqs(boq_id),
    level VARCHAR(100),       -- Ground Floor / First Floor etc
    area VARCHAR(100),        -- Living Room / Master Bedroom etc
    product_sku VARCHAR(100), -- soft reference, not hard FK
    product_name VARCHAR(255),
    quantity INTEGER,
    unit_price NUMERIC(10,2),
    discount_pct NUMERIC(5,2) DEFAULT 0,
    line_total NUMERIC(12,2),
    notes TEXT
);

-- DESIGN REQUESTS
CREATE TABLE design_requests (
    design_request_id SERIAL PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(lead_id),
    boq_id INTEGER REFERENCES boqs(boq_id),
    request_type VARCHAR(100),
    -- lighting_layout / automation_proposal / canva_presentation
    status VARCHAR(50) DEFAULT 'pending',
    -- pending / in_progress / completed / approved
    assigned_to VARCHAR(255),
    drive_output_url TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
