import psycopg2

DB_URL = "postgresql://postgres:tXcpBGiZvXNSMxsDtUiJYjsJrzgLugcE@nozomi.proxy.rlwy.net:10121/railway"

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

cur.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS hsn_code VARCHAR(20)")
cur.execute("ALTER TABLE invoice_line_items ADD COLUMN IF NOT EXISTS hsn_code VARCHAR(20)")

# Lighting fixtures (architectural + decorative) -> 9405. Leave automation/oem blank for now — different HSN, confirm with CA.
cur.execute("""
    UPDATE products SET hsn_code = '9405'
    WHERE category IN ('architectural', 'decorative') AND hsn_code IS NULL
""")

conn.commit()

cur.execute("SELECT category, COUNT(*), COUNT(hsn_code) FROM products GROUP BY category")
print("category | total | has_hsn")
for row in cur.fetchall():
    print(row)

cur.close()
conn.close()
print("Migration complete ✅")
