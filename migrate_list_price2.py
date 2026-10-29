import os, psycopg2
conn = psycopg2.connect(os.environ["DB_URL"]); cur = conn.cursor()
cur.execute("""
UPDATE boq_line_items bli SET list_price = COALESCE(
  (SELECT COALESCE(p.mrp_inr, p.mrp_gst) FROM products p
   WHERE p.sku IN (bli.product_sku, regexp_replace(bli.product_sku,'^(DEC|ARCH)-',''))
     AND COALESCE(p.mrp_inr, p.mrp_gst) IS NOT NULL LIMIT 1),
  bli.unit_price)""")
print("recomputed", cur.rowcount, "lines")
conn.commit(); conn.close()
