import os, psycopg2

conn = psycopg2.connect(os.environ["DB_URL"])
cur = conn.cursor()
fmt = lambda v: f"{float(v or 0):,.0f}"

print("== A) Invoiced decorative pieces (by invoicing entity) ==")
cur.execute("""
SELECT i.invoice_from,
       COUNT(DISTINCT i.invoice_id),
       SUM(ili.quantity),
       SUM(ili.quantity * p.mrp_inr),
       SUM(CASE WHEN p.mrp_inr IS NULL THEN ili.quantity ELSE 0 END)
FROM invoice_line_items ili
JOIN invoices i ON i.invoice_id = ili.invoice_id
JOIN products p ON p.sku IN (ili.sku, REGEXP_REPLACE(ili.sku, '^(DEC|ARCH)-', ''))
WHERE p.category = 'decorative'
GROUP BY ROLLUP(i.invoice_from)
""")
for r in cur.fetchall():
    print(f"{r[0] or 'TOTAL':8} invoices={r[1]}  pcs={fmt(r[2])}  MRP value=Rs {fmt(r[3])}  pcs with no MRP on file={fmt(r[4])}")

print()
print("== B) Decorative pieces in BOQs of WON leads (latest version per lead+category) ==")
cur.execute("""
WITH latest AS (
  SELECT DISTINCT ON (b.lead_id, b.category) b.boq_id, b.lead_id
  FROM boqs b JOIN leads l ON l.lead_id = b.lead_id
  WHERE l.status = 'won'
  ORDER BY b.lead_id, b.category, b.version DESC, b.boq_id DESC
)
SELECT COUNT(DISTINCT latest.lead_id),
       SUM(bli.quantity),
       SUM(bli.quantity * p.mrp_inr),
       SUM(CASE WHEN p.mrp_inr IS NULL THEN bli.quantity ELSE 0 END)
FROM latest
JOIN boq_line_items bli ON bli.boq_id = latest.boq_id
JOIN products p ON p.sku IN (bli.product_sku, REGEXP_REPLACE(bli.product_sku, '^(DEC|ARCH)-', ''))
WHERE p.category = 'decorative'
""")
r = cur.fetchone()
print(f"won leads={r[0]}  pcs={fmt(r[1])}  MRP value=Rs {fmt(r[2])}  pcs with no MRP on file={fmt(r[3])}")
conn.close()
