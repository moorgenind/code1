import psycopg2, hashlib

DB_URL = "postgresql://postgres:tXcpBGiZvXNSMxsDtUiJYjsJrzgLugcE@nozomi.proxy.rlwy.net:10121/railway"

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()
cur.execute(
    """
    INSERT INTO users (name, email, password_hash, role, is_active)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (email) DO NOTHING
    """,
    ("Procurement", "procurement@moorgenindia.co", hash_pw("moorgen@2526"), "procurement", True),
)
conn.commit()
cur.close()
conn.close()
print("Procurement user created ✅")
