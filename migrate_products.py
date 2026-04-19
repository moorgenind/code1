from app.database import engine
from sqlalchemy import text

migrations = [
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS family VARCHAR(255)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS family_no VARCHAR(100)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS model_no VARCHAR(100)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS product_type VARCHAR(100)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS trim VARCHAR(50)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS cutout_size VARCHAR(50)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS cct VARCHAR(100)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS beam_angle VARCHAR(50)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS power VARCHAR(50)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS voltage VARCHAR(50)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS current VARCHAR(50)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS body_color VARCHAR(50)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS cup_color VARCHAR(50)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS led_chip VARCHAR(100)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS cri VARCHAR(50)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS adjustable_angle VARCHAR(50)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS mrp_gst NUMERIC(12,2)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS flagship_mrp NUMERIC(12,2)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS dealer_mrp NUMERIC(12,2)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS landing_inr NUMERIC(12,2)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS specification TEXT",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS description TEXT",
]

with engine.connect() as conn:
    for sql in migrations:
        conn.execute(text(sql))
        print(f"✅ {sql[:80]}")
    conn.commit()

print("\n✅ All migrations applied")
