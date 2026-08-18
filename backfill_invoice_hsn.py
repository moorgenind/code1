import psycopg2

DB_URL = "postgresql://postgres:tXcpBGiZvXNSMxsDtUiJYjsJrzgLugcE@nozomi.proxy.rlwy.net:10121/railway"

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

cur.execute("""
    UPDATE invoice_line_items ili
    SET hsn_code = p.hsn_code
    FROM products p
    WHERE ili.sku = p.sku
    AND ili.hsn_code IS NULL
    AND ili.sku IS NOT NULL
""")
updated = cur.rowcount

conn.commit()

cur.execute("SELECT COUNT(*), COUNT(hsn_code) FROM invoice_line_items")
total, has_hsn = cur.fetchone()

cur.close()
conn.close()
print(f"Backfilled {updated} line items")
print(f"Total line items: {total}, with HSN: {has_hsn}")
