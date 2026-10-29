import os, psycopg2
conn = psycopg2.connect(os.environ["DB_URL"]); cur = conn.cursor()
cur.execute("ALTER TABLE boq_line_items ADD COLUMN IF NOT EXISTS list_price NUMERIC(12,2)")
cur.execute("""
UPDATE boq_line_items bli SET list_price = COALESCE(
  (SELECT p.mrp_inr FROM products p
   WHERE p.sku IN (bli.product_sku, regexp_replace(bli.product_sku,'^(DEC|ARCH)-',''))
     AND p.mrp_inr IS NOT NULL LIMIT 1),
  bli.unit_price)
WHERE bli.list_price IS NULL""")
print("backfilled", cur.rowcount, "lines")
conn.commit(); conn.close()
