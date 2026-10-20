# CRM upgrade (Oct 2026) — adapted from the Jaeger & Reloto CRM blueprint

## What's new
| Area | Backend | Frontend |
|---|---|---|
| Lead qualification, attribution, A–D scoring | `app/crm_logic.py`, `PATCH /crm/leads/{id}/profile`, `GET /crm/leads/{id}/insights` | Lead page → Qualification card; New Lead form |
| Activity log (calls, meetings, site visits, notes) | `crm_activities` table, `/crm/activities` | Lead page → Activity; Architect page; Follow-ups → Activity feed |
| Follow-up SLAs + escalation (new 24h · qualified 7d · design/BOQ/negotiation 14d · quote sent 7d) | `GET /crm/followups`, `POST /crm/sla/run` (creates Tasks) | CRM → Follow-ups |
| "No stage move without activity" | `PATCH /leads/{id}/status` returns 422 `activity_required` if nothing logged in 7 days and no note | Status dropdowns ask for a note only when needed |
| Architects / IDA module (A+/A/B/C, owner, follow-ups, leads, revenue, conversion) | `/architects` | CRM → Architects |
| Dealer assignment engine + 24h accept/decline | `/crm/leads/{id}/dealer-suggestions`, `/crm/leads/{id}/assign-dealer`, `/dealer-auth/leads/{id}/respond` | Lead page → Dealer assignment; Dealer portal → accept/decline |
| Dealer operating model + weighted scorecard (Platinum/Gold/Silver/Watch List) | new `dealers` columns, `GET /crm/dealers/scorecard` | Dealers → Profile; Command Centre → Dealer scorecard |
| Duplicate checks (phone / similar name + city) | `GET /crm/duplicates`; enforced on dealer registration | New Lead form warning |
| Probability-weighted forecast | `GET /crm/forecast` | CRM → Pipeline |
| Discount approval matrix (0–5% auto · 5–10% RM · 10–15% NSH · 15%+ MD, vs list price) | `/crm/boqs/{id}/approval`, `request-approval`, `decide`; blocks BOQ "sent" until approved | BOQ strip on lead page + BOQ builder; Pipeline → Discount approvals |
| After-sales: tech-request TAT, installation sign-off, service tickets (P1 24h/P2 72h/P3 7d), warranty registry, AMC | `/aftersales/*` | After-sales page; Projects → sign-off fields |
| Command Centre: MD dashboard, early warnings, team KPIs vs targets, marketing spend / cost per lead | `/crm-dashboard/*` | Command Centre (admin only) |

## Deploy order
1. **Backend first** (`code1`): run `python3 -c "from app.main import app"`, commit, push. On boot `app/crm_migrations.py`
   adds the new columns (idempotent, `ADD COLUMN IF NOT EXISTS`) and `create_all` adds the new tables. Nothing is dropped.
   You can also run it by hand first: `python3 -m app.crm_migrations`.
2. Wait ~60s for Railway, then **frontend** (`frontend2`): `npx vercel --prod`.
3. Optional one-offs after deploy: Architects → "Import from Projects" (turns typed architect names into records);
   `POST /crm/rescore` (scores every lead once you've filled qualification fields).

## Switches (Railway env vars)
- `CRM_REQUIRE_ACTIVITY=0` — allow stage moves without a recent activity/note.
- `CRM_ENFORCE_DISCOUNT_APPROVAL=0` — stop blocking "sent" on BOQs that need discount approval.
- `CRM_APPROVER_EMAILS=a@x,b@y` — who can approve discounts (default `info@moorgenindia.co`).

All weights, thresholds and picklists live at the top of `app/crm_logic.py`.

## Also fixed
- SQLAlchemy 2.1+ defaults `postgresql://` to psycopg v3 (not installed) → the URL is now pinned to psycopg2, so an unpinned rebuild can't crash on boot.
- Lead/BOQ/design codes use the Indian FY (Apr–Mar) and numeric MAX — dealer-portal leads were hard-coded to FY 2526 with COUNT (duplicate codes).
