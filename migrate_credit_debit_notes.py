import psycopg2

DB_URL = "postgresql://postgres:tXcpBGiZvXNSMxsDtUiJYjsJrzgLugcE@nozomi.proxy.rlwy.net:10121/railway"

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS credit_debit_notes (
    note_id SERIAL PRIMARY KEY,
    note_code VARCHAR(50) UNIQUE NOT NULL,
    note_type VARCHAR(10) NOT NULL,
    invoice_id INTEGER NOT NULL REFERENCES invoices(invoice_id),
    lead_id INTEGER REFERENCES leads(lead_id),
    amount NUMERIC(14,2) NOT NULL,
    gst_amount NUMERIC(14,2) DEFAULT 0,
    reason VARCHAR(100) NOT NULL,
    notes TEXT,
    created_by VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
)
""")

conn.commit()
cur.close()
conn.close()
print("Migration complete ✅")
