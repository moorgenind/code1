import psycopg2

DB_URL = "postgresql://postgres:tXcpBGiZvXNSMxsDtUiJYjsJrzgLugcE@nozomi.proxy.rlwy.net:10121/railway"

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()
cur.execute("ALTER TABLE po_line_items ADD COLUMN IF NOT EXISTS lead_id INTEGER REFERENCES leads(lead_id)")
conn.commit()
cur.close()
conn.close()
print("Migration complete ✅")
