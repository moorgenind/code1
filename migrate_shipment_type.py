import psycopg2

DB_URL = "postgresql://postgres:tXcpBGiZvXNSMxsDtUiJYjsJrzgLugcE@nozomi.proxy.rlwy.net:10121/railway"

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()
cur.execute("ALTER TABLE shipments ADD COLUMN IF NOT EXISTS shipment_type VARCHAR(20) DEFAULT 'regular'")
conn.commit()
cur.close()
conn.close()
print("Migration complete ✅")
