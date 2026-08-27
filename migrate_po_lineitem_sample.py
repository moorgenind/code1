import psycopg2

DB_URL = "postgresql://postgres:tXcpBGiZvXNSMxsDtUiJYjsJrzgLugcE@nozomi.proxy.rlwy.net:10121/railway"

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()
cur.execute("ALTER TABLE po_line_items ADD COLUMN IF NOT EXISTS is_sample BOOLEAN DEFAULT FALSE")
conn.commit()
cur.close()
conn.close()
print("Migration complete ✅")
