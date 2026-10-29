import os, psycopg2
cur = psycopg2.connect(os.environ["DB_URL"]).cursor()
f = lambda v: f"{float(v or 0):>12,.0f}"
H = f"{'pcs':>5}{'MRP value':>13}{'Quoted(pre-disc)':>17}{'Final(post-disc)':>17}{'Disc%':>7}"
def pct(q, fnl):
    q = float(q or 0); return f"{(1 - float(fnl or 0)/q)*100:6.1f}%" if q else "     -"

print("== A) INVOICED decorative lines, per invoice ==")
cur.execute("""
SELECT i.invoice_code, i.invoice_from, i.status, i.discount_pct, i.discount_amount,
       SUM(ili.quantity), SUM(ili.quantity*p.mrp_inr),
       SUM(ili.quantity*ili.unit_price), SUM(ili.line_total)
FROM invoice_line_items ili
JOIN invoices i ON i.invoice_id = ili.invoice_id
JOIN products p ON p.sku IN (ili.sku, REGEXP_REPLACE(ili.sku,'^(DEC|ARCH)-',''))
WHERE p.category='decorative'
GROUP BY i.invoice_id, i.invoice_code, i.invoice_from, i.status, i.discount_pct, i.discount_amount
ORDER BY i.invoice_code""")
print(f"{'invoice':16}{'from':10}{'status':10}{H}   invoice-level disc% / amt")
T=[0]*4
for r in cur.fetchall():
    print(f"{r[0]:16}{str(r[1]):10}{str(r[2]):10}{int(r[5]):>5}{f(r[6])}{f(r[7])}{f(r[8])}{pct(r[7],r[8])}   {r[3]} / {r[4]}")
    for k,v in enumerate(r[5:9]): T[k]+=float(v or 0)
print(f"{'TOTAL':36}{int(T[0]):>5}{f(T[1])}{f(T[2])}{f(T[3])}{pct(T[2],T[3])}")

print("\n== B) WON-LEAD BOQs (latest version per lead+category), decorative lines, per BOQ ==")
cur.execute("""
WITH latest AS (
  SELECT DISTINCT ON (b.lead_id, b.category) b.boq_id, b.lead_id, b.boq_code, b.category, b.version, b.status
  FROM boqs b JOIN leads l ON l.lead_id=b.lead_id
  WHERE l.status='won'
  ORDER BY b.lead_id, b.category, b.version DESC, b.boq_id DESC)
SELECT latest.boq_code, latest.category, latest.version, latest.status, l.client_name,
       SUM(bli.quantity), SUM(bli.quantity*p.mrp_inr),
       SUM(bli.quantity*bli.unit_price), SUM(bli.line_total),
       SUM(CASE WHEN p.mrp_inr IS NULL THEN bli.quantity ELSE 0 END)
FROM latest
JOIN leads l ON l.lead_id=latest.lead_id
JOIN boq_line_items bli ON bli.boq_id=latest.boq_id
JOIN products p ON p.sku IN (bli.product_sku, REGEXP_REPLACE(bli.product_sku,'^(DEC|ARCH)-',''))
WHERE p.category='decorative'
GROUP BY latest.boq_code, latest.category, latest.version, latest.status, l.client_name
ORDER BY latest.boq_code""")
print(f"{'boq':14}{'cat':12}{'v':>3} {'status':10}{'client':22}{H}  noMRP")
T=[0]*4
for r in cur.fetchall():
    print(f"{str(r[0]):14}{str(r[1])[:11]:12}{r[2]:>3} {str(r[3]):10}{str(r[4])[:21]:22}{int(r[5]):>5}{f(r[6])}{f(r[7])}{f(r[8])}{pct(r[7],r[8])}  {int(r[9])}")
    for k,v in enumerate(r[5:9]): T[k]+=float(v or 0)
print(f"{'TOTAL':61}{int(T[0]):>5}{f(T[1])}{f(T[2])}{f(T[3])}{pct(T[2],T[3])}")
