from app.database import engine
from sqlalchemy import text

with engine.begin() as conn:
    lead = conn.execute(text("SELECT lead_id FROM leads WHERE lead_code = 'LD-2526-031'")).fetchone()
    if not lead:
        print('Lead not found')
    else:
        lead_id = lead.lead_id
        invoices = conn.execute(text('SELECT invoice_id, invoice_code FROM invoices WHERE lead_id = :id'), {'id': lead_id}).fetchall()
        print(f'Invoices to delete: {invoices}')

        payments_deleted = conn.execute(text('''
            DELETE FROM payments
            WHERE invoice_id IN (SELECT invoice_id FROM invoices WHERE lead_id = :id)
        '''), {'id': lead_id})
        print(f'Payments deleted: {payments_deleted.rowcount}')

        line_items_deleted = conn.execute(text('''
            DELETE FROM invoice_line_items
            WHERE invoice_id IN (SELECT invoice_id FROM invoices WHERE lead_id = :id)
        '''), {'id': lead_id})
        print(f'Invoice line items deleted: {line_items_deleted.rowcount}')

        invoices_deleted = conn.execute(text('DELETE FROM invoices WHERE lead_id = :id'), {'id': lead_id})
        print(f'Invoices deleted: {invoices_deleted.rowcount}')

        print(f'Cleared all invoices, line items, and payments for lead {lead_id} (LD-2526-031). Ready to recreate.')
