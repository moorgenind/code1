"""
CRM upgrade schema migration — idempotent, safe to run on every boot.

`Base.metadata.create_all` creates brand-new tables (architects, crm_activities,
service_tickets, ...) but never adds columns to tables that already exist. This
module adds the new CRM columns to existing tables with ADD COLUMN IF NOT EXISTS,
so the backend can never boot against a schema that is missing them.

Run standalone (same as the other migrate_*.py scripts):
    python3 -m app.crm_migrations
"""
from sqlalchemy import text
from sqlalchemy.schema import CreateColumn

from app import models

# table -> new column names (types/defaults are read from the SQLAlchemy models)
NEW_COLUMNS = {
    "dealers": [
        "region", "classification", "lifecycle_stage", "certified_categories", "capabilities",
        "territory_cities", "training_score", "installation_score", "service_score",
        "agreement_start", "agreement_end", "crm_notes",
    ],
    "leads": [
        "attribution_type", "owner_employee_id", "source_employee_id", "architect_id", "builder_name",
        "state", "pincode", "project_location", "budget_range", "property_type", "property_size_sqft",
        "construction_stage", "expected_possession_date", "purchase_timeline", "product_interest",
        "lead_score", "lead_grade", "estimated_value", "win_probability", "expected_order_date",
        "qualified_at", "last_activity_at", "status_changed_at",
        "dealer_assigned_at", "dealer_assigned_by", "dealer_assignment_reason",
        "dealer_acceptance", "dealer_responded_at", "dealer_reject_reason",
    ],
    "boqs": [
        "max_discount_pct", "approval_level", "approval_status", "approval_requested_at",
        "approval_requested_by", "approval_decided_at", "approval_decided_by", "approval_notes",
    ],
    "design_requests": ["requested_by", "target_date", "started_at", "revision_count"],
    "project_tracking": [
        "commissioning_date", "client_training_date", "signoff_date", "signed_off_by", "signoff_doc_url",
    ],
}

FOREIGN_KEYS = {
    ("leads", "owner_employee_id"): "employees(employee_id)",
    ("leads", "source_employee_id"): "employees(employee_id)",
    ("leads", "architect_id"): "architects(architect_id)",
}

INDEXES = [
    "CREATE INDEX IF NOT EXISTS ix_leads_architect_id ON leads (architect_id)",
    "CREATE INDEX IF NOT EXISTS ix_leads_owner_employee_id ON leads (owner_employee_id)",
    "CREATE INDEX IF NOT EXISTS ix_leads_dealer_id ON leads (dealer_id)",
    "CREATE INDEX IF NOT EXISTS ix_crm_activities_activity_at ON crm_activities (activity_at)",
]


def _column_ddl(engine, table_name, col_name):
    table = models.Base.metadata.tables[table_name]
    col = table.columns[col_name]
    # Render "name TYPE" without NOT NULL / FK; defaults applied separately.
    ddl = str(CreateColumn(col).compile(dialect=engine.dialect))
    ddl = ddl.replace(" NOT NULL", "")
    return ddl


def run(engine, verbose=False):
    added = []
    with engine.begin() as conn:
        for table_name, cols in NEW_COLUMNS.items():
            existing = {
                r[0] for r in conn.execute(
                    text("SELECT column_name FROM information_schema.columns WHERE table_name = :t"),
                    {"t": table_name},
                )
            }
            if not existing:
                continue  # table doesn't exist yet; create_all will build it whole
            for col_name in cols:
                if col_name in existing:
                    continue
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {_column_ddl(engine, table_name, col_name)}"))
                added.append(f"{table_name}.{col_name}")
                fk = FOREIGN_KEYS.get((table_name, col_name))
                if fk:
                    conn.execute(text(
                        f"ALTER TABLE {table_name} ADD CONSTRAINT fk_{table_name}_{col_name} "
                        f"FOREIGN KEY ({col_name}) REFERENCES {fk}"
                    ))
        # One-time backfills — only on the boot that first adds each column, so later
        # deploys never reset anyone's follow-up clock.
        if "design_requests.revision_count" in added:
            conn.execute(text("UPDATE design_requests SET revision_count = 0 WHERE revision_count IS NULL"))
        if "dealers.lifecycle_stage" in added:
            conn.execute(text("UPDATE dealers SET lifecycle_stage = 'active' WHERE lifecycle_stage IS NULL AND COALESCE(is_active, TRUE)"))
        if "leads.last_activity_at" in added:
            # SLA clock for existing open leads starts at go-live (no day-one wall of MD escalations)
            conn.execute(text(
                "UPDATE leads SET last_activity_at = CASE WHEN status IN ('won','lost','cold') "
                "THEN COALESCE(updated_at, created_at) ELSE NOW() END WHERE last_activity_at IS NULL"
            ))
        if "leads.status_changed_at" in added:
            conn.execute(text(
                "UPDATE leads SET status_changed_at = COALESCE(updated_at, created_at) WHERE status_changed_at IS NULL"
            ))
        for stmt in INDEXES:
            conn.execute(text(stmt))
    if verbose:
        print(f"CRM migration: added {len(added)} columns" + (": " + ", ".join(added) if added else ""))
    return added


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    from app.database import engine
    models.Base.metadata.create_all(bind=engine)
    run(engine, verbose=True)
