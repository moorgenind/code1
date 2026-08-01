import psycopg2

conn = psycopg2.connect("postgresql://postgres:tXcpBGiZvXNSMxsDtUiJYjsJrzgLugcE@nozomi.proxy.rlwy.net:10121/railway")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    device_info VARCHAR(500),
    user_agent TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT NOW(),
    last_active_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    revoked_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_email ON user_sessions(user_email);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token);
""")

conn.commit()
cur.close()
conn.close()
print("Migration complete ✅")
