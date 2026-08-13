import psycopg2

DB_URL = "postgresql://postgres:tXcpBGiZvXNSMxsDtUiJYjsJrzgLugcE@nozomi.proxy.rlwy.net:10121/railway"

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

cur.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS automation_role VARCHAR(100)")

cur.execute("UPDATE employees SET automation_role = 'crm_followup' WHERE name = 'Hajira'")
cur.execute("UPDATE employees SET automation_role = 'boq_design' WHERE name = 'Shanmukhi'")
cur.execute("UPDATE employees SET automation_role = 'logistics' WHERE name = 'Feroz'")

conn.commit()
cur.close()
conn.close()
print("Migration complete ✅")
