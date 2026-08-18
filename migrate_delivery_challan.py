import psycopg2

DB_URL = "postgresql://postgres:tXcpBGiZvXNSMxsDtUiJYjsJrzgLugcE@nozomi.proxy.rlwy.net:10121/railway"

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS delivery_challans (
    dc_id SERIAL PRIMARY KEY,
    dc_code VARCHAR(50) UNIQUE NOT NULL,
    lead_id INTEGER REFERENCES leads(lead_id),
    shipment_id INTEGER REFERENCES shipments(id),
    from_location VARCHAR(255),
    to_location VARCHAR(255),
    purpose VARCHAR(50) NOT NULL DEFAULT 'stock_transfer',
    vehicle_number VARCHAR(50),
    transporter VARCHAR(255),
    notes TEXT,
    created_by VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS delivery_challan_line_items (
    id SERIAL PRIMARY KEY,
    dc_id INTEGER REFERENCES delivery_challans(dc_id),
    sku VARCHAR(100),
    product_name VARCHAR(255),
    hsn_code VARCHAR(20),
    quantity INTEGER NOT NULL,
    unit VARCHAR(20) DEFAULT 'pcs',
    approx_value NUMERIC(14,2)
)
""")

conn.commit()
cur.close()
conn.close()
print("Migration complete ✅")
