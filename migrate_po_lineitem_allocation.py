import psycopg2

DB_URL = "postgresql://postgres:tXcpBGiZvXNSMxsDtUiJYjsJrzgLugcE@nozomi.proxy.rlwy.net:10121/railway"

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()
cur.execute("ALTER TABLE po_line_items ADD COLUMN IF NOT EXISTS allocation_type VARCHAR(20) DEFAULT 'stock'")

# Backfill from existing data: sample flag wins, then lead_id -> project, else stock (already the default)
cur.execute("UPDATE po_line_items SET allocation_type = 'sample' WHERE is_sample = TRUE")
cur.execute("UPDATE po_line_items SET allocation_type = 'project' WHERE lead_id IS NOT NULL AND (is_sample IS NULL OR is_sample = FALSE)")

conn.commit()
cur.execute("SELECT allocation_type, COUNT(*) FROM po_line_items GROUP BY allocation_type")
for row in cur.fetchall():
    print(row)
cur.close()
conn.close()
print("Migration complete ✅")
