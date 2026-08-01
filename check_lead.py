from app.database import engine
from sqlalchemy import text

with engine.begin() as conn:
    lead = conn.execute(text("SELECT lead_id FROM leads WHERE lead_code = 'LD-2526-031'")).fetchone()
    if not lead:
        print('Lead not found')
    else:
        lead_id = lead.lead_id
        checks = {
            'invoices': 'SELECT invoice_code FROM invoices WHERE lead_id = :id',
            'design_requests': 'SELECT design_code FROM design_requests WHERE lead_id = :id',
            'project_tracking': 'SELECT id FROM project_tracking WHERE lead_id = :id',
            'project_snags': 'SELECT id FROM project_snags WHERE lead_id = :id',
            'site_visits': 'SELECT id FROM site_visits WHERE lead_id = :id',
            'purchase_orders': 'SELECT po_code FROM purchase_orders WHERE lead_id = :id',
            'shipments': 'SELECT id FROM shipments WHERE lead_id = :id',
            'tasks': 'SELECT task_id FROM tasks WHERE linked_lead_id = :id',
        }
        blockers = {name: conn.execute(text(q), {'id': lead_id}).fetchall() for name, q in checks.items()}
        blockers = {k: v for k, v in blockers.items() if v}

        boqs = conn.execute(text('SELECT boq_id, boq_code, total_amount FROM boqs WHERE lead_id = :id'), {'id': lead_id}).fetchall()
        print(f'Lead ID: {lead_id}')
        print(f'BOQs: {boqs}')

        if blockers:
            print('STOP — related records exist, do not delete blindly:')
            for k, v in blockers.items():
                print(f'  {k}: {v}')
        else:
            for b in boqs:
                conn.execute(text('DELETE FROM boq_line_items WHERE boq_id = :bid'), {'bid': b.boq_id})
            conn.execute(text('DELETE FROM boqs WHERE lead_id = :id'), {'id': lead_id})
            conn.execute(text('DELETE FROM leads WHERE lead_id = :id'), {'id': lead_id})
            print(f'Deleted lead {lead_id} (LD-2526-031) and {len(boqs)} BOQ(s)')
