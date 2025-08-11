
# WBS Scratchpad — Targeted Updates

- Expand app/.env.example to include STRIPE_, MAILJET_, JWT_SECRET, ADMIN_EMAIL_ALLOWLIST, DATABASE_URL, REDIS_URL, CORS_ORIGINS.
- Document that parent/admin SPA is out-of-repo for now. Backend should expose REST endpoints only. Include CORS config stub in FastAPI.
Session start: 2025-08-11
Context reviewed:
- Charter: MVP in 2 weeks; FastAPI, Postgres, Stripe; single admin now, parent portal minimal later
- PRD: Parent self-booking of fixed 30-min weekly slots; Stripe as source of truth; make-up rules; emails; concurrency + provisional holds
- ADD: FastAPI + Celery + Redis + Postgres; Supabase Auth; endpoints list + booking orchestration; Alembic; Mailjet
- Current WBS doc empty
- FastAPI app entry: app/main.py wiring to api.router

Initial planning anchors:
- MVP Epics: Auth exchange; Admin CRUD; Timeslot publish; Parent booking API; Booking worker (Stripe + emails); Webhooks; Dashboard P0; Make-ups (minimal); Emails; Observability; DB & Alembic; Docker & Deploy; CI
- Constraints: 2 weeks, single dev; align with existing /app structure and docker-compose
Open items to clarify:
- Admin UI delivery scope (server-rendered minimal vs deferred)
- Parent SPA scope this sprint vs API-only
- Exact environment targets (local + single prod) and CI runner
Next action:
- Propose WBS skeleton + confirm MVP cut (API-first vs include minimal SPAs); then sequence & estimates
Decision: API-first MVP (no UIs this sprint)
WBS Epics (backend-only):
- Auth/Identity: Supabase JWT verify + backend JWT exchange/refresh; admin allowlist
- DB & Migrations: Alembic baseline for entities (Payee, Student, Teacher, Instrument, Timeslot, Enrollment, Attendance, MakeUpRecord, Semester, EmailLog, StripeEvent, DeadLetter) + constraints/indexes
- Admin CRUD APIs: Teachers, Instruments, Payees, Students, Timeslots, Enrollments(assign/cancel), Attendance, Make-ups(admin windows), Dashboard(toda y, provisionals, payments)
- Public/Parent APIs: Public discovery (teachers, timeslots), Parent payee self-upsert, Students CRUD (scoped), Bookings (init + status), Make-ups list/book
- Booking Orchestration: DB locking, provisional enrollment creation, Celery booking pipeline (Stripe customer, payment method ensure, subscription/invoice), status update
- Payments/Stripe: Live queries, linkage fields, webhooks handling (idempotent)
- Emails/Mailjet: Jinja templates, send worker, logging, retries, admin alerts
- Observability & Admin Dashboard Data: EmailLog, StripeEvent, DeadLetter surfacing via endpoints
- Provisional Expiry: scheduled worker to revert expired provisional enrollments; admin alert
- CI/CD & Docker: compose services (api, worker, redis, db), env config, migrations on release, basic test workflow

Dependencies:
- DB baseline → CRUD + booking → workers/webhooks → dashboard/observability
- Auth exchange → protect admin/parent endpoints
- Celery & Redis up → booking pipeline, email sender, expiry worker operational
- Mailjet/Stripe keys → booking flow + emails

Sequence (high-level):
1) DB baseline + constraints (Alembic)
2) Auth exchange/refresh + admin allowlist
3) Admin CRUD (teachers, instruments, payees, students, timeslots)
4) Parent/public read + student create + payee self-upsert
5) Booking init/status + Celery booking pipeline + Stripe integration
6) Webhooks (Stripe) + idempotency
7) Emails + templates + logging
8) Provisional expiry worker + admin alert
9) Dashboard endpoints (today, provisionals, payments)
10) CI pipeline + Docker polish + smoke tests

Next: Draft detailed task list with acceptance criteria and estimates; then confirm to generate wbs.md.
Drafting detailed WBS (API-first). Will await confirmation before writing ai_docs/context/core_docs/wbs.md.

Detailed WBS (outline):
- Epic A: Auth & Security
  - A1: Backend JWT exchange endpoint (POST /auth/exchange) — AC: validates Supabase JWT; returns HS256 JWT; 2h exp
  - A2: Refresh endpoint (POST /auth/refresh) — AC: returns new backend JWT when Supabase JWT valid
  - A3: Admin allowlist config + dependency injection — AC: admin gating in routers
  - A4: Middleware/CORS config — AC: CORS locked to env; auth dependency reusable
  - Tests: unit for token utils, integration for endpoints with mocked Supabase JWT

- Epic B: DB Schema & Alembic
  - B1: Alembic baseline migration with all entities + enums
  - B2: Constraints/indexes (Timeslot unique; Enrollment partial unique; EmailLog, StripeEvent, etc.)
  - B3: Seed scripts: instruments basic set (piano/guitar/drums/bass)
  - Tests: migration up/down; constraint enforcement

- Epic C: Admin CRUD APIs
  - C1: Teachers CRUD
  - C2: Instruments CRUD
  - C3: Payees CRUD
  - C4: Students CRUD
  - C5: Timeslots CRUD + active_flag
  - C6: Enrollments assign/cancel (Admin)
  - C7: Attendance mark/get
  - C8: Make-up windows admin (Semesters); status by student
  - Tests: happy path + authZ; input validation

- Epic D: Public/Parent APIs
  - D1: Public teachers list
  - D2: Public timeslots query with filters
  - D3: Payee self-upsert (idempotent via Supabase identity)
  - D4: Parent-managed students: create/list
  - D5: Booking init (POST /parent/bookings) → provisional Enrollment; lock + enqueue Celery job
  - D6: Booking status polling
  - D7: Make-ups eligible slots + book
  - Tests: scope checks (only own payee), booking 202 lifecycle

- Epic E: Booking Orchestration (Celery)
  - E1: Celery setup (broker=Redis, result backend=Postgres), worker config
  - E2: Booking job with idempotency key = enrollment_id
  - E3: Stripe steps orchestration via services: ensure customer → ensure default PM → create subscription/invoice per frequency
  - E4: Update Enrollment status/fields; failure_reason on error; retries with backoff
  - Tests: unit with Stripe client mocked; retry semantics

- Epic F: Stripe Integration & Webhooks
  - F1: Stripe client wrapper (idempotent keys; telemetry)
  - F2: Webhooks receiver with signature verify, persist StripeEvent, idempotency guard
  - F3: Handlers for event types updating local linkages/status
  - Tests: signature verification; replay idempotency

- Epic G: Emails (Mailjet)
  - G1: Jinja templates: booking_confirmation, provisional_notice, no_show_notice, make_up_invite, make_up_confirmation, admin_alert
  - G2: Email sender worker; logging to EmailLog; retries; DLQ on terminal failure
  - Tests: template render; provider mock

- Epic H: Provisional Expiry
  - H1: Scheduled task scanning Enrollment where status=provisional & expired
  - H2: Revert slot to available; set failure_reason; send admin alert
  - Tests: time-based logic; idempotency

- Epic I: Dashboard P0 Endpoints
  - I1: /admin/dashboard/today
  - I2: /admin/dashboard/provisionals
  - I3: /admin/dashboard/payments (from StripeEvent)
  - Tests: query correctness; performance basic

- Epic J: Observability & DLQ
  - J1: Structured logging context for bookings, Stripe ops, emails
  - J2: DeadLetter table write paths + admin alert surfacing
  - Tests: log fields presence; DLQ insert on terminal failure

- Epic K: CI/CD & Docker
  - K1: docker-compose services verified (api, worker, redis, db); env samples
  - K2: Start scripts; migrations on start for dev
  - K3: CI workflow: lint, unit/integration tests (DB service), alembic migrate, build
  - K4: Release step: run migrations, deploy containers
  - Tests: CI green on cold run

Dependencies & Sequencing:
1) B → A → C → D → E → F → G → H → I → J → K
Key external prereqs: Stripe + Mailjet creds present; Supabase JWKS for verification

Estimation (t-shirt):
- A: S
- B: M
- C: M-L
- D: M
- E: M-L
- F: M
- G: S-M
- H: S
- I: S-M
- J: S
- K: S-M

Risks/mitigations:
- Stripe flows complexity → use idempotent keys + retries + clear failure_reason
- Concurrency on booking → strict SELECT FOR UPDATE + partial unique index
- Time constraints → defer non-critical admin UI, limit dashboard to P0 widgets

Next step proposal:
- If approved, I will compile this into the final wbs.md with acceptance criteria per task, dependency mapping, and a 2-week sprint plan.