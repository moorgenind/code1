import os, psycopg2
cur = psycopg2.connect(os.environ["DB_URL"]).cursor()
cur.execute("""
WITH latest AS (
  SELECT DISTINCT ON (b.lead_id, b.category) b.boq_id
  FROM boqs b JOIN leads l ON l.lead_id=b.lead_id WHERE l.status='won'
  ORDER BY b.lead_id, b.category, b.version DESC, b.boq_id DESC)
SELECT COALESCE(p.category,'(no product match)') cat, COUNT(*) lines,
  SUM((abs(bli.unit_price - p.mrp_inr) < 1)::int)            eq_mrp_inr,
  SUM((abs(bli.unit_price - p.mrp_inr*1.1) < 2)::int)        eq_mrp_x1_1,
  SUM((abs(bli.unit_price - p.mrp_gst) < 1)::int)            eq_mrp_gst,
  SUM((abs(bli.unit_price - p.dealer_mrp) < 1)::int)         eq_dealer,
  SUM((abs(bli.unit_price - p.flagship_mrp) < 1)::int)       eq_flagship,
  SUM((bli.discount_pct > 0)::int)                           has_line_disc,
  SUM((bli.list_price = bli.unit_price)::int)                list_eq_unit
FROM latest JOIN boq_line_items bli ON bli.boq_id = latest.boq_id
LEFT JOIN products p ON p.sku IN (bli.product_sku, regexp_replace(bli.product_sku,'^(DEC|ARCH)-',''))
GROUP BY 1 ORDER BY 2 DESC""")
cols = ["category","lines","=mrp_inr","=mrp×1.1","=mrp_gst","=dealer","=flagship","line disc>0","list=unit"]
print("".join(f"{c:>18}" for c in cols))
for r in cur.fetchall(): print("".join(f"{str(v):>18}" for v in r))
