def patch(path, old, new):
    s = open(path).read()
    assert s.count(old) == 1, f"{path}: expected 1 match, got {s.count(old)}"
    open(path, "w").write(s.replace(old, new))

# 1) model column
patch("app/models.py",
'''    notes = Column(Text)
    image_url = Column(Text, nullable=True)

    boq = relationship("Boq", back_populates="line_items")
''',
'''    notes = Column(Text)
    image_url = Column(Text, nullable=True)
    list_price = Column(Numeric(12, 2), nullable=True)  # MRP snapshot at quote time

    boq = relationship("Boq", back_populates="line_items")
''')

# 2) auto-fill list_price on insert / sku change
open("app/models.py", "a").write('''

# ── list price snapshot for BOQ lines ──
import re as _re
from sqlalchemy import event as _event, text as _text, inspect as _inspect

def _lookup_list_price(connection, sku, fallback):
    sku = sku or ""
    row = connection.execute(
        _text("SELECT mrp_inr FROM products WHERE sku IN (:a, :b) AND mrp_inr IS NOT NULL LIMIT 1"),
        {"a": sku, "b": _re.sub(r"^(DEC|ARCH)-", "", sku)},
    ).first()
    return row[0] if row else fallback

@_event.listens_for(BoqLineItem, "before_insert")
def _boq_line_set_list_price(mapper, connection, target):
    if target.list_price is None:
        target.list_price = _lookup_list_price(connection, target.product_sku, target.unit_price)

@_event.listens_for(BoqLineItem, "before_update")
def _boq_line_refresh_list_price(mapper, connection, target):
    if _inspect(target).attrs.product_sku.history.has_changes():
        target.list_price = _lookup_list_price(connection, target.product_sku, target.unit_price)
''')

# 3) leads list: latest BOQ per category, list vs final
patch("app/routers/leads.py",
'''    from sqlalchemy import func
    lead_ids = [l.lead_id for l in leads]
    boq_totals = dict(
        db.query(models.Boq.lead_id, func.coalesce(func.sum(models.Boq.total_amount), 0))
        .filter(models.Boq.lead_id.in_(lead_ids))
        .group_by(models.Boq.lead_id)
        .all()
    ) if lead_ids else {}
''',
'''    from sqlalchemy import func, text
    lead_ids = [l.lead_id for l in leads]
    boq_totals = {}
    if lead_ids:
        rows = db.execute(text("""
            WITH latest AS (
              SELECT DISTINCT ON (lead_id, category) boq_id, lead_id
              FROM boqs WHERE lead_id = ANY(:ids)
              ORDER BY lead_id, category, version DESC, boq_id DESC)
            SELECT latest.lead_id,
                   COALESCE(SUM(bli.quantity * COALESCE(bli.list_price, bli.unit_price)), 0),
                   COALESCE(SUM(bli.line_total), 0)
            FROM latest JOIN boq_line_items bli ON bli.boq_id = latest.boq_id
            GROUP BY latest.lead_id
        """), {"ids": lead_ids}).fetchall()
        boq_totals = {r[0]: (float(r[1] or 0), float(r[2] or 0)) for r in rows}
''')
patch("app/routers/leads.py",
'''        boq_value = float(boq_totals.get(lead.lead_id, 0) or 0)
        d = {c.name: getattr(lead, c.name) for c in lead.__table__.columns}
        d["boq_value"] = boq_value
''',
'''        boq_list, boq_value = boq_totals.get(lead.lead_id, (0.0, 0.0))
        d = {c.name: getattr(lead, c.name) for c in lead.__table__.columns}
        d["boq_value"] = boq_value
        d["boq_list_value"] = boq_list
        d["boq_discount_pct"] = round((1 - boq_value / boq_list) * 100, 1) if boq_list else None
''')

# 4) schema
patch("app/schemas.py",
"    boq_value: Optional[float] = None\n",
"    boq_value: Optional[float] = None\n    boq_list_value: Optional[float] = None\n    boq_discount_pct: Optional[float] = None\n")
print("patched")
