import os
import psycopg2
import psycopg2.extras
import gspread
import pickle
from google.auth.transport.requests import Request
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
SPREADSHEET_ID = "1DgD143IfVxbQTHd6scTxFmT8wW7-L9J7ypfxJBgq-Ww"
TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.pickle")


def get_gc():
    with open(TOKEN_FILE, "rb") as f:
        creds = pickle.load(f)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return gspread.Client(auth=creds)


def sheet_to_dicts(ws):
    all_values = ws.get_all_values()
    if not all_values:
        return []
    headers = all_values[0]
    return [dict(zip(headers, row)) for row in all_values[1:]]


def safe_float(value):
    try:
        if value == "" or value is None:
            return None
        cleaned = str(value).replace(",", "").replace("₹", "").replace("$", "").strip()
        return float(cleaned) if cleaned else None
    except:
        return None


def clean_str(value, max_len=None):
    if value is None:
        return None
    v = str(value).strip()
    if v == "" or v == "/" or v == "#N/A":
        return None
    if max_len:
        v = v[:max_len]
    return v


def sync_products():
    gc = get_gc()
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)

    # Connect to DB
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("DELETE FROM products")

    seen_skus = set()
    total = 0

    # ============ ARCHITECTURAL (detailed) ============
    try:
        ws = spreadsheet.worksheet("Product_Database - Architectural Lighting")
        rows = sheet_to_dicts(ws)
        arch_products = []

        for row in rows:
            raw_sku = clean_str(row.get("model_no"))
            name = clean_str(row.get("Product Name"), 255)
            if not raw_sku or not name:
                continue

            sku = f"ARCH-{raw_sku}"
            if sku in seen_skus:
                continue
            seen_skus.add(sku)

            arch_products.append((
                sku,
                name,
                "architectural",
                clean_str(row.get("Family Name"), 100),
                safe_float(row.get("mrp_gst")),
                True,
                clean_str(row.get("Family Name"), 255),        # family
                clean_str(row.get("family_no"), 100),           # family_no
                clean_str(row.get("model_no"), 100),            # model_no
                clean_str(row.get("type"), 100),                # product_type
                clean_str(row.get("trim"), 50),                 # trim
                clean_str(row.get("Cutout Size"), 50),          # cutout_size
                clean_str(row.get("Color\nTemperature"), 100),  # cct
                clean_str(row.get("Beam\nAngle"), 50),          # beam_angle
                clean_str(row.get("Power"), 50),                # power
                clean_str(row.get("Voltage"), 50),              # voltage
                clean_str(row.get("Current"), 50),              # current
                clean_str(row.get("Body"), 50),                 # body_color
                clean_str(row.get("Cup"), 50),                  # cup_color
                clean_str(row.get("Light Chip"), 100),          # led_chip
                clean_str(row.get("Color Rendering Index"), 50),# cri
                clean_str(row.get("Adjustable Angle"), 50),     # adjustable_angle
                safe_float(row.get("mrp_gst")),                 # mrp_gst
                safe_float(row.get("flagship_mrp")),            # flagship_mrp
                safe_float(row.get("dealer_mrp")),              # dealer_mrp
                safe_float(row.get("Landing_inr")),             # landing_inr
                clean_str(row.get("spec")),                     # specification
                clean_str(row.get("desc")),                     # description
            ))

        psycopg2.extras.execute_values(cur, """
            INSERT INTO products (
                sku, name, category, subcategory, unit_price, is_active,
                family, family_no, model_no, product_type, trim, cutout_size,
                cct, beam_angle, power, voltage, current, body_color, cup_color,
                led_chip, cri, adjustable_angle, mrp_gst, flagship_mrp, dealer_mrp,
                landing_inr, specification, description
            )
            VALUES %s
        """, arch_products)
        conn.commit()
        total += len(arch_products)
        print(f"✅ Architectural: {len(arch_products)} products with full attributes")

    except Exception as e:
        print(f"❌ Architectural error: {e}")
        conn.rollback()

    # ============ DECORATIVE (basic - enrich later) ============
    try:
        ws = spreadsheet.worksheet("Product_Database - Decorative Lighting")
        rows = sheet_to_dicts(ws)
        dec_products = []

        for row in rows:
            raw_sku = clean_str(row.get("model_no"))
            name = clean_str(row.get("Description"), 255)
            if not raw_sku or not name:
                continue

            sku = f"DEC-{raw_sku}"
            if sku in seen_skus:
                continue
            seen_skus.add(sku)

            dec_products.append((
                sku, name, "decorative",
                clean_str(row.get("series"), 100),
                safe_float(row.get("MRP (incl. of GST)")),
                True,
            ))

        psycopg2.extras.execute_values(cur, """
            INSERT INTO products (sku, name, category, subcategory, unit_price, is_active)
            VALUES %s
        """, dec_products)
        conn.commit()
        total += len(dec_products)
        print(f"✅ Decorative: {len(dec_products)} products")

    except Exception as e:
        print(f"❌ Decorative error: {e}")
        conn.rollback()

    # ============ ZIGBEE (basic - enrich later) ============
    try:
        ws = spreadsheet.worksheet("Product_Database - ZigbeePlus")
        rows = sheet_to_dicts(ws)
        zb_products = []

        for row in rows:
            raw_sku = clean_str(row.get("model_number"))
            name = clean_str(row.get("description"), 255)
            if not name:
                name = clean_str(row.get("name"), 255)
            if not raw_sku or not name:
                continue

            sku = f"ZBP-{raw_sku}"
            if sku in seen_skus:
                continue
            seen_skus.add(sku)

            zb_products.append((
                sku, name, "automation",
                clean_str(row.get("series"), 100),
                safe_float(row.get("mrp")),
                True,
            ))

        psycopg2.extras.execute_values(cur, """
            INSERT INTO products (sku, name, category, subcategory, unit_price, is_active)
            VALUES %s
        """, zb_products)
        conn.commit()
        total += len(zb_products)
        print(f"✅ Zigbee: {len(zb_products)} products")

    except Exception as e:
        print(f"❌ Zigbee error: {e}")
        conn.rollback()

    cur.close()
    conn.close()
    print(f"\n✅ Total: {total} products synced")


if __name__ == "__main__":
    sync_products()
