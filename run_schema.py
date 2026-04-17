import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def run_schema():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    with open("schema.sql", "r") as f:
        sql = f.read()
    
    cur.execute(sql)
    conn.commit()
    
    cur.close()
    conn.close()
    print("✅ Schema created successfully")

if __name__ == "__main__":
    run_schema()