import psycopg2

conn = psycopg2.connect(
    "postgresql://postgres:tXcpBGiZvXNSMxsDtUiJYjsJrzgLugcE@nozomi.proxy.rlwy.net:10121/railway"
)
conn.autocommit = True
cur = conn.cursor()

print("Running tasks module migration...")

cur.execute("""
CREATE TABLE IF NOT EXISTS employees (
    employee_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    role VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
""")
print("✓ employees table")

cur.execute("""
CREATE TABLE IF NOT EXISTS recurring_templates (
    template_id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    employee_id INTEGER NOT NULL REFERENCES employees(employee_id),
    priority VARCHAR(20) DEFAULT 'medium',
    frequency VARCHAR(20) DEFAULT 'daily',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
""")
print("✓ recurring_templates table")

cur.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    task_id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    employee_id INTEGER NOT NULL REFERENCES employees(employee_id),
    assigned_by VARCHAR(100) DEFAULT 'admin',
    priority VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(20) DEFAULT 'pending',
    due_date TIMESTAMP,
    linked_lead_id INTEGER REFERENCES leads(lead_id),
    linked_label VARCHAR(255),
    is_ai_suggested BOOLEAN DEFAULT FALSE,
    is_recurring BOOLEAN DEFAULT FALSE,
    template_id INTEGER REFERENCES recurring_templates(template_id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
""")
print("✓ tasks table")

cur.execute("""
INSERT INTO employees (name, role) VALUES
    ('Hajira', 'sales'),
    ('Shanmukhi', 'design'),
    ('Feroz', 'logistics')
ON CONFLICT DO NOTHING;
""")
print("✓ seeded Hajira, Shanmukhi, Feroz")

cur.execute("""
INSERT INTO recurring_templates (title, description, employee_id, priority, frequency)
SELECT 'Daily lead follow-up calls', 'Call all leads not contacted in last 2 days',
    employee_id, 'high', 'daily' FROM employees WHERE name = 'Hajira';
""")
cur.execute("""
INSERT INTO recurring_templates (title, description, employee_id, priority, frequency)
SELECT 'Update CRM with call notes', 'Log all client interactions from today into the system',
    employee_id, 'medium', 'daily' FROM employees WHERE name = 'Hajira';
""")
cur.execute("""
INSERT INTO recurring_templates (title, description, employee_id, priority, frequency)
SELECT 'Check pending BOQ status', 'Review all draft BOQs and update progress',
    employee_id, 'medium', 'daily' FROM employees WHERE name = 'Shanmukhi';
""")
cur.execute("""
INSERT INTO recurring_templates (title, description, employee_id, priority, frequency)
SELECT 'Weekly inventory check', 'Check ZigbeePlus panel and module stock levels',
    employee_id, 'medium', 'weekly' FROM employees WHERE name = 'Feroz';
""")
cur.execute("""
INSERT INTO recurring_templates (title, description, employee_id, priority, frequency)
SELECT 'Delivery status update', 'Check and update status of all active shipments',
    employee_id, 'high', 'daily' FROM employees WHERE name = 'Feroz';
""")
print("✓ seeded recurring templates")

cur.close()
conn.close()
print("\n✅ Migration complete!")
