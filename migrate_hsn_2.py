import psycopg2

DB_URL = "postgresql://postgres:tXcpBGiZvXNSMxsDtUiJYjsJrzgLugcE@nozomi.proxy.rlwy.net:10121/railway"

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

cur.execute("UPDATE products SET hsn_code = '8536' WHERE category = 'automation' AND hsn_code IS NULL")
cur.execute("UPDATE products SET hsn_code = '8301' WHERE category = 'smart_locks' AND hsn_code IS NULL")
cur.execute("UPDATE products SET hsn_code = '9405' WHERE category = 'oem' AND hsn_code IS NULL")

conn.commit()

cur.execute("SELECT category, COUNT(*), COUNT(hsn_code) FROM products GROUP BY category")
print("category | total | has_hsn")
for row in cur.fetchall():
    print(row)

cur.close()
conn.close()
print("Migration complete ✅")
