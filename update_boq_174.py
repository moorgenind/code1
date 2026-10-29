import requests

API = "https://code1-production.up.railway.app"
BOQ_ID = 174

# ── Step 1: delete all existing line items ──
current = requests.get(f"{API}/boqs/{BOQ_ID}").json()
for item in current["line_items"]:
    r = requests.delete(f"{API}/boqs/{BOQ_ID}/line-items/{item['line_item_id']}")
    print("deleted", item["line_item_id"], r.status_code)

# ── Step 2: rebuild from the PDF, exactly ──
PATTAYA_NOTES = "PATTAYA SERIES III | CCT: 3500K | Beam: 36° | Power: 12W | Voltage: 36V | Current: 250mA | Body: White | LED: TEENLED | CRI: 90 | Cutout: 75mm"
JAZZ_NOTES = "JAZZ SERIES | CCT: 2700K | Beam: 24° | Power: 9W | Voltage: 36V | Current: 250mA | Body: Black | LED: ZMOLED | CRI: 90 | Cutout: 35mm"
HAWAII_NOTES = "HAWAII | CCT: 3500K | Beam: 36° | Power: 12W | Voltage: 30V | Current: 300mA | Body: White | LED: CITIZEN | CRI: 90 | Cutout: 75mm"

items = [
    ("Third Floor", "Bedroom 1", "ARCH-MB3316W53612", "PATTAYA SERIES III — PATTAYA SERIES III 75 ROUND - ADJUSTABLE - WHITE TRIM", 5, 2714.01, PATTAYA_NOTES),
    ("Third Floor", "Kitchen", "ARCH-MB3316W53612", "PATTAYA SERIES III — PATTAYA SERIES III 75 ROUND - ADJUSTABLE - WHITE TRIM", 2, 2714.01, PATTAYA_NOTES),
    ("Third Floor", "Pooja", "ARCH-MB3316W53612", "PATTAYA SERIES III — PATTAYA SERIES III 75 ROUND - ADJUSTABLE - WHITE TRIM", 2, 2714.01, PATTAYA_NOTES),
    ("Third Floor", "Drawing Room", "OEM-LSP-001", "Laser Spots", 2, 1250.00, ""),
    ("Third Floor", "Living Room", "OEM-CG-001", "Curtain Grazer", 4, 3200.00, ""),
    ("Third Floor", "Dining Room", "OEM-CPL-001", "Cove Profile Light", 6, 800.00, ""),
    ("Third Floor", "Dining Room", "ARCH-MB3316W53612", "PATTAYA SERIES III — PATTAYA SERIES III 75 ROUND - ADJUSTABLE - WHITE TRIM", 9, 2714.01, PATTAYA_NOTES),
    ("Third Floor", "Living room", "ARCH-MB3316W53612", "PATTAYA SERIES III — PATTAYA SERIES III 75 ROUND - ADJUSTABLE - WHITE TRIM", 12, 2714.01, PATTAYA_NOTES),
    ("Third Floor", "Store", "ARCH-MB3316W53612", "PATTAYA SERIES III — PATTAYA SERIES III 75 ROUND - ADJUSTABLE - WHITE TRIM", 2, 2714.01, PATTAYA_NOTES),
    ("Third Floor", "Bedroom 1 Toilet", "OEM-COB7-001", "7W Recessed COB", 6, 950.00, ""),
    ("Third Floor", "Master Bedroom", "ARCH-MB3543B2249", "JAZZ SERIES — 35 SPOTLIGHT RECESSED - ADJUSTABLE - BLACK", 2, 4984.91, JAZZ_NOTES),
    ("Third Floor", "Master Bedroom", "OEM-LSP-001", "Laser Spots", 3, 1250.00, ""),
    ("Third Floor", "Master Bedroom", "OEM-CPL-001", "Cove Profile Light", 14, 800.00, ""),
    ("Third Floor", "Dining Room", "OEM-RLP-001", "Recessed Linear Profile Light", 4, 800.00, ""),
    ("Third Floor", "Drawing Room", "ARCH-MB3316W53612", "PATTAYA SERIES III — PATTAYA SERIES III 75 ROUND - ADJUSTABLE - WHITE TRIM", 6, 2714.01, PATTAYA_NOTES),
    ("Third Floor", "Master Bedroom", "ARCH-MB3316W53612", "PATTAYA SERIES III — PATTAYA SERIES III 75 ROUND - ADJUSTABLE - WHITE TRIM", 5, 2714.01, PATTAYA_NOTES),
    ("Third Floor", "Master Bedroom Toilet", "OEM-COB7-001", "7W Recessed COB", 6, 950.00, ""),
    ("Third Floor", "Balconies", "OEM-COB18-001", "18W Surface COB", 14, 1600.00, ""),
    ("Third Floor", "Drawing Room", "OEM-CG-001", "Curtain Grazer", 4, 3200.00, ""),
    ("Third Floor", "Bedroom 1", "OEM-CPL-001", "Cove Profile Light", 8, 800.00, ""),
    ("Third Floor", "Kitchen", "OEM-RLP-001", "Recessed Linear Profile Light", 8, 800.00, ""),
    ("Fourth Floor", "Living Hall/Family Area", "ARCH-MB3316W53612", "PATTAYA SERIES III — PATTAYA SERIES III 75 ROUND - ADJUSTABLE - WHITE TRIM", 13, 2714.01, PATTAYA_NOTES),
    ("Fourth Floor", "Bedroom 2 Toilet", "OEM-COB7-001", "7W Recessed COB", 2, 950.00, ""),
    ("Fourth Floor", "Bedroom 1", "ARCH-MB3652", "2000 Pre Installed Track", 4, 7477.37, ""),
    ("Fourth Floor", "Bedroom 1", "ARCH-MB3689B52412", "12 SPOTS - LINEAR MAGNETIC TRACK", 8, 7477.37, ""),
    ("Fourth Floor", "Bedroom 2", "OEM-LSP-001", "Laser Spots", 3, 1250.00, ""),
    ("Fourth Floor", "Balconies", "OEM-COB18-001", "18W Surface COB", 20, 1600.00, ""),
    ("Fourth Floor", "Bedroom 2", "OEM-CPL-001", "Cove Profile Light", 10, 800.00, ""),
    ("Fourth Floor", "Living Hall/Family Area", "OEM-RLP-001", "Recessed Linear Profile Light", 20, 800.00, ""),
    ("Fourth Floor", "Bedroom 1", "OEM-MTD100-001", "Magnetic Track Driver 100W", 2, 1750.00, ""),
    ("Fourth Floor", "Bedroom 1", "ARCH-MB3668", "0-10V magnetic track power supply box", 7, 2492.46, ""),
    ("Fourth Floor", "Master Bedroom", "ARCH-MB3316W53612", "PATTAYA SERIES III — PATTAYA SERIES III 75 ROUND - ADJUSTABLE - WHITE TRIM", 8, 2714.01, PATTAYA_NOTES),
    ("Fourth Floor", "Master Bedroom Toilet", "OEM-COB7-001", "7W Recessed COB", 5, 950.00, ""),
    ("Fourth Floor", "Master Bedroom", "OEM-CG-001", "Curtain Grazer", 4, 3200.00, ""),
    ("Fourth Floor", "Living Hall/Family Area", "OEM-CPL-001", "Cove Profile Light", 28, 800.00, ""),
    ("Fourth Floor", "Bedroom 2", "ARCH-MB3316W53612", "PATTAYA SERIES III — PATTAYA SERIES III 75 ROUND - ADJUSTABLE - WHITE TRIM", 10, 2714.01, PATTAYA_NOTES),
    ("Fourth Floor", "Toilet 1", "OEM-COB7-001", "7W Recessed COB", 3, 950.00, ""),
    ("Fourth Floor", "Master Bedroom", "ARCH-MB3543B2249", "JAZZ SERIES — 35 SPOTLIGHT RECESSED - ADJUSTABLE - BLACK", 2, 4984.91, JAZZ_NOTES),
    ("Fourth Floor", "Bedroom 1", "OEM-LSP-001", "Laser Spots", 3, 1250.00, ""),
    ("Fourth Floor", "Bedroom 1", "OEM-CPL-001", "Cove Profile Light", 8, 800.00, ""),
    ("Fourth Floor", "Master Bedroom", "OEM-CPL-001", "Cove Profile Light", 24, 800.00, ""),
    ("Fifth Floor", "Kitchen", "ARCH-MB3316W53612", "PATTAYA SERIES III — PATTAYA SERIES III 75 ROUND - ADJUSTABLE - WHITE TRIM", 9, 2714.01, PATTAYA_NOTES),
    ("Fifth Floor", "Pooja", "ARCH-MB3316W53612", "PATTAYA SERIES III — PATTAYA SERIES III 75 ROUND - ADJUSTABLE - WHITE TRIM", 2, 2714.01, PATTAYA_NOTES),
    ("Fifth Floor", "Master Bedroom Toilet", "OEM-COB7-001", "7W Recessed COB", 6, 950.00, ""),
    ("Fifth Floor", "Master Bedroom", "ARCH-MB3543B2249", "JAZZ SERIES — 35 SPOTLIGHT RECESSED - ADJUSTABLE - BLACK", 2, 4984.91, JAZZ_NOTES),
    ("Fifth Floor", "Staircase", "ARCH-MB3824W53612", "HAWAII — WATERPROOF SPOTLIGHT ROUND - TRIM", 6, 7269.66, HAWAII_NOTES),
    ("Fifth Floor", "Bedroom 1", "OEM-CPL-001", "Cove Profile Light", 10, 800.00, ""),
    ("Fifth Floor", "Living Hall/Family Area", "ARCH-MB3316W53612", "PATTAYA SERIES III — PATTAYA SERIES III 75 ROUND - ADJUSTABLE - WHITE TRIM", 13, 2714.01, PATTAYA_NOTES),
    ("Fifth Floor", "Toilet 1", "OEM-COB7-001", "7W Recessed COB", 3, 950.00, ""),
    ("Fifth Floor", "Living Hall/Family Area", "OEM-LSP-001", "Laser Spots", 4, 1250.00, ""),
    ("Fifth Floor", "Bedroom 1", "ARCH-MB3652", "2000 Pre Installed Track", 4, 7477.37, ""),
    ("Fifth Floor", "Bedroom 1", "ARCH-MB3689B52412", "12 SPOTS - LINEAR MAGNETIC TRACK", 8, 7477.37, ""),
    ("Fifth Floor", "Balconies", "OEM-COB18-001", "18W Surface COB", 20, 1600.00, ""),
    ("Fifth Floor", "Living Room", "OEM-CPL-001", "Cove Profile Light", 28, 800.00, ""),
    ("Fifth Floor", "Bedroom 1", "OEM-MTD100-001", "Magnetic Track Driver 100W", 2, 1750.00, ""),
    ("Fifth Floor", "Bedroom 2", "OEM-LSP-001", "Laser Spots", 3, 1250.00, ""),
    ("Fifth Floor", "Bedroom 1", "ARCH-MB3316W53612", "PATTAYA SERIES III — PATTAYA SERIES III 75 ROUND - ADJUSTABLE - WHITE TRIM", 2, 2714.01, PATTAYA_NOTES),
    ("Fifth Floor", "Master Bedroom", "ARCH-MB3316W53612", "PATTAYA SERIES III — PATTAYA SERIES III 75 ROUND - ADJUSTABLE - WHITE TRIM", 11, 2714.01, PATTAYA_NOTES),
    ("Fifth Floor", "Store", "OEM-LSP-001", "Laser Spots", 2, 1250.00, ""),
    ("Fifth Floor", "Staircase", "ARCH-MB3824W53612", "HAWAII — WATERPROOF SPOTLIGHT ROUND - TRIM", 7, 7269.66, HAWAII_NOTES),
    ("Fifth Floor", "Master Bedroom", "OEM-CPL-001", "Cove Profile Light", 25, 800.00, ""),
    ("Fifth Floor", "Bedroom 1", "ARCH-MB3668", "0-10V magnetic track power supply box", 7, 2492.46, ""),
    ("Sixth Floor", "Bathrooms", "OEM-COB7-001", "7W Recessed COB", 6, 950.00, ""),
    ("Sixth Floor", "Gym Area", "ARCH-MB3316W53612", "PATTAYA SERIES III — PATTAYA SERIES III 75 ROUND - ADJUSTABLE - WHITE TRIM", 4, 2714.01, PATTAYA_NOTES),
    ("Sixth Floor", "Gym Area", "OEM-RLP-001", "Recessed Linear Profile Light", 10, 800.00, ""),
    ("Sixth Floor", "Home Theatre", "ARCH-MB3316W53612", "PATTAYA SERIES III — PATTAYA SERIES III 75 ROUND - ADJUSTABLE - WHITE TRIM", 4, 2714.01, PATTAYA_NOTES),
    ("Sixth Floor", "Bar area", "OEM-COB7-001", "7W Recessed COB", 6, 950.00, ""),
    ("Sixth Floor", "Home Theatre", "OEM-RLP-001", "Recessed Linear Profile Light", 26, 800.00, ""),
    ("All Floors", "Staircase", "OEM-CPL-001", "Under Stairs lighting", 70, 800.00, ""),
    # Dimming drivers
    ("All Floors", "For all Pattaya", None, "0-10V Dimming Driver — 12W (Pattaya)", 58, 1300.00, ""),
    ("All Floors", "For all Cove lights", None, "0-10V Dimming Driver — Cove Profile Light", 14, 5200.00, ""),
    ("All Floors", "For all Linear profiles", None, "0-10V Dimming Driver — Linear Profile", 2, 5200.00, ""),
    ("All Floors", "For all Laser blades", None, "0-10V Dimming Driver — Laser Blade", 11, 1300.00, ""),
    ("All Floors", "For all Hawaii 35", None, "0-10V Dimming Driver — 9W (Hawaii 35)", 6, 1300.00, ""),
]

for level, area, sku, name, qty, price, notes in items:
    payload = {
        "level": level,
        "area": area,
        "product_sku": sku,
        "product_name": name,
        "quantity": qty,
        "unit_price": price,
        "discount_pct": 0,
        "notes": notes,
    }
    r = requests.post(f"{API}/boqs/{BOQ_ID}/line-items", json=payload)
    if r.status_code != 200:
        print("FAILED:", level, area, name, r.status_code, r.text)

# ── Step 3: confirm final total ──
final = requests.get(f"{API}/boqs/{BOQ_ID}").json()
print("Final item count:", len(final["line_items"]))
print("Final total_amount:", final["total_amount"])
