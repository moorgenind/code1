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


def sync_products():
    gc = get_gc()
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)

    seen_skus = set()
    all_products = []

    def add_product(sku, name, category, subcategory, unit_price):
        if not sku or not name:
            return False
        if sku in seen_skus:
            return False
        seen_skus.add(sku)
        all_products.append((sku, name[:255], category, (subcategory or '')[:100], unit_price, True))
        return True

    # Architectural
    try:
        ws = spreadsheet.worksheet("Product_Database - Architectural Lighting")
        rows = sheet_to_dicts(ws)
        count = 0
        for row in rows:
            sku = str(row.get("model_no", "")).strip()
            name = str(row.get("Product Name", "")).strip()
            if add_product(f"ARCH-{sku}", name, "architectural",
                str(row.get("Family Name", "")).strip(),
                safe_float(row.get("mrp_gst"))):
                count += 1
        print(f"✅ Architectural: {count} products")
    except Exception as e:
        print(f"❌ Architectural error: {e}")

    # Decorative
    try:
        ws = spreadsheet.worksheet("Product_Database - Decorative Lighting")
        rows = sheet_to_dicts(ws)
        count = 0
        for row in rows:
            sku = str(row.get("model_no", "")).strip()
            name = str(row.get("Description", "")).strip()
            if add_product(f"DEC-{sku}", name, "decorative",
                str(row.get("series", "")).strip(),
                safe_float(row.get("MRP (incl. of GST)"))):
                count += 1
        print(f"✅ Decorative: {count} products")
    except Exception as e:
        print(f"❌ Decorative error: {e}")

    # Zigbee
    try:
        ws = spreadsheet.worksheet("Product_Database - ZigbeePlus")
        rows = sheet_to_dicts(ws)
        count = 0
        for row in rows:
            sku = str(row.get("model_number", "")).strip()
            name = str(row.get("description", "")).strip()
            if not name:
                name = str(row.get("name", "")).strip()
            if add_product(f"ZBP-{sku}", name, "automation",
                str(row.get("series", "")).strip(),
                safe_float(row.get("mrp"))):
                count += 1
        print(f"✅ Zigbee: {count} products")
    except Exception as e:
        print(f"❌ Zigbee error: {e}")

    print(f"\nTotal collected: {len(all_products)} unique products")

    # Bulk insert
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("DELETE FROM products")
    psycopg2.extras.execute_values(cur, """
        INSERT INTO products (sku, name, category, subcategory, unit_price, is_active)
        VALUES %s
    """, all_products)
    conn.commit()
    cur.close()
    conn.close()
    print(f"✅ Inserted {len(all_products)} products into Postgres")


if __name__ == "__main__":
    sync_products()
