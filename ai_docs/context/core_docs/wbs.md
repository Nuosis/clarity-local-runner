# Work Breakdown Structure (WBS)
Cedar Heights Music Academy — MVP (API-first)

Scope confirmation: Backend/API-first delivery for MVP within 2 weeks. Admin and Parent UIs are deferred to next sprint. Aligns with existing /app FastAPI structure, Celery workers, Postgres, Redis, Docker compose, and Stripe/Mailjet integrations per ADD.

Document Includes:
- Epics and features with concrete tasks
- Dependencies and sequencing
- Acceptance criteria per epic
- Estimation (t-shirt sizes)
- Testing strategy
- CI/CD approach
- Risk mitigation
- Progress tracking plan

------------------------------------------------------------
1. Epics, Features, and Tasks
------------------------------------------------------------

Epic A: Auth & Security (S)
- A1: Backend JWT Exchange (POST /auth/exchange)
  - Tasks:
    - Implement Supabase JWT verification (JWKS fetch/verify)
    - Issue HS256 backend JWT (2h expiry) with claims: sub/email/role/iat/exp
    - Config: admin email allowlist; env wiring
    - Route registration in existing app/api/router.py
    - Error handling and logging (invalid token, expired)
  - Acceptance Criteria:
    - Valid Supabase JWT → 200 with backend_jwt + expires_in
    - Invalid/expired Supabase JWT → 401 with clear error
    - JWT contains role based on admin allowlist

- A2: Backend JWT Refresh (POST /auth/refresh)
  - Tasks:
    - Verify current Supabase JWT; mint new backend JWT
    - Reuse token utils; unify error model
  - Acceptance Criteria:
    - Valid Supabase JWT → 200 with new backend_jwt
    - Invalid/expired → 401

- A3: AuthZ Integration
  - Tasks:
    - Dependency/decorator for admin-only routes
    - Parent-scoped dependency to restrict to own payee_id
  - Acceptance Criteria:
    - Admin routes reject non-admin with 403
    - Parent routes restricted to authenticated user’s scope

- A4: CORS & Security Headers
  - Tasks:
    - CORS configured via env for allowed origins
    - Basic security headers for API
  - Acceptance Criteria:
    - CORS works in dev; restricted in prod

Testing:
- Unit: JWT utils, role derivation
- Integration: exchange/refresh endpoints with mocked Supabase JWKS

Dependencies:
- None (can be built alongside DB baseline)

------------------------------------------------------------

Epic B: Database Schema & Alembic (M)
- B1: Baseline Migration
  - Entities:
    - Payee(id, name, email, phone, status, timestamps)
    - Student(id, payee_id, name, instrument_id, teacher_pref_id, consent_policy_accepted_at, stripe_customer_id, stripe_default_payment_method_id, timestamps)
    - Teacher(id, name, email, pay_per_lesson, timestamps)
    - Instrument(id, name)
    - Timeslot(id, teacher_id, weekday, start_time, end_time, active_flag, timestamps)
    - Enrollment(id, student_id, timeslot_id, start_date, status, stripe_subscription_id, stripe_invoice_id, provisional_expires_at, failure_reason, timestamps)
    - Attendance(id, enrollment_id, date, status, notes, created_at)
    - MakeUpRecord(id, student_id, semester_id, status, booked_date, timestamps)
    - Semester(id, name, start_date, end_date, timestamps)
    - EmailLog(id, recipient, template, provider_message_id, status, payload, error, timestamps)
    - StripeEvent(id, stripe_event_id, type, payload, processed, error, timestamps)
    - DeadLetter(id, task_name, payload, last_error, attempts, timestamps)

- B2: Indexes/Constraints
  - Unique (Timeslot.teacher_id, weekday, start_time, end_time)
  - Partial unique index on Enrollment to ensure one active/provisional per student
  - EmailLog index (recipient, created_at desc)
  - StripeEvent.stripe_event_id unique

- B3: Seed Data
  - Instruments: piano, guitar, drums, bass

Acceptance Criteria:
- Alembic upgrade/downgrade runs clean on dev DB
- Constraints enforce booking rules
- Seed script populates instruments

Testing:
- Migration tests; constraint violation tests; seed verification

Dependencies:
- None (foundation for CRUD and booking)

------------------------------------------------------------

Epic C: Admin CRUD APIs (M-L)
- C1: Teachers CRUD
- C2: Instruments CRUD
- C3: Payees CRUD
- C4: Students CRUD
- C5: Timeslots CRUD (+active_flag)
- C6: Enrollments (Admin assign/cancel)
- C7: Attendance (mark/get)
- C8: Make-up windows (Semesters admin); status by student
- C9: Admin gating via allowlist

Tasks (for each resource):
- Pydantic schemas
- Repository/service layer
- Routes under /admin/
- AuthZ: admin-only
- Validation: required fields/foreign keys

Acceptance Criteria:
- Standard CRUD semantics
- 4xx on validation/foreign key errors
- Admin guard enforced

Testing:
- Integration tests with admin-auth dependencies mocked or using seeded admin

Dependencies:
- A (Auth), B (DB)

------------------------------------------------------------

Epic D: Public/Parent APIs (M)
- D1: Public discovery
  - GET /public/teachers
  - GET /public/timeslots?teacher_id=&weekday=&active=true
- D2: Parent payee self-upsert
  - POST /parent/payees/self (idempotent based on identity)
- D3: Parent students
  - POST /parent/students; GET /parent/students
- D4: Booking init/status
  - POST /parent/bookings → provisional Enrollment, lock, enqueue Celery job
  - GET /parent/bookings/{id}/status
- D5: Make-ups
  - GET /parent/makeups/slots
  - POST /parent/makeups/book

Tasks:
- Scoping: restrict to authenticated parent’s payee
- Locking on booking init: SELECT ... FOR UPDATE on Timeslot
- Provisional expiry set at now()+14d

Acceptance Criteria:
- Public endpoints readable without auth
- Parent endpoints enforce scope
- Booking returns 202 with tracking_id and provisional_expires_at
- Status reflects provisional/active/cancelled with failure_reason if any

Testing:
- Integration: scope enforcement; booking lifecycle start; concurrency lock simulation

Dependencies:
- A, B, C (for Timeslots, Students, etc.), E (for async job execution readiness, but D4 can enqueue before E ready)

------------------------------------------------------------

Epic E: Booking Orchestration (Celery) (M-L)
- E1: Celery setup (Redis broker, Postgres result backend)
- E2: Booking pipeline worker with idempotency key=enrollment_id
- E3: Stripe orchestration steps:
  - Ensure stripe_customer_id on Student (create if missing)
  - Ensure default payment method (if missing: send provisional notice, leave provisional)
  - Create subscription or invoice per selected frequency (monthly/yearly/semester) and PRD start rules
- E4: Update Enrollment status/fields; manage retries with exponential backoff (2^n, up to 5)
- E5: Structured logging and failure_reason population

Acceptance Criteria:
- Happy path advances Enrollment to active; stripe_subscription_id or stripe_invoice_id stored
- Missing PM results in provisional + provisional_notice email enqueued
- Retries honored; idempotency safe on re-entrance
- No double-book under concurrent attempts

Testing:
- Unit: Stripe client mocked; retry behavior; idempotency
- Integration: DB state changes across worker execution with a test queue

Dependencies:
- B, D (booking init), F/G (Stripe client and emails wiring)

------------------------------------------------------------

Epic F: Stripe Integration & Webhooks (M)
- F1: Stripe client wrapper
  - Idempotency keys; telemetry tags; error normalization
- F2: Webhook receiver (POST /webhooks/stripe)
  - Signature verification
  - Persist StripeEvent with unique stripe_event_id (idempotent)
- F3: Event handlers:
  - customer.created
  - payment_method.attached
  - invoice.payment_failed / succeeded
  - customer.subscription.created/updated/deleted
  - Reconcile Enrollment/Student linkage as needed

Acceptance Criteria:
- Webhooks validated; 2xx on idempotent replay
- Local linkages updated correctly
- Terminal failures recorded and retries scheduled

Testing:
- Signature verification tests
- Replay/idempotency tests
- Handler state transitions

Dependencies:
- B (StripeEvent), E (orchestration), G (emails for alerts)

------------------------------------------------------------

Epic G: Emails (Mailjet) (S-M)
- G1: Jinja templates:
  - booking_confirmation
  - provisional_notice
  - no_show_notice
  - make_up_invite
  - make_up_confirmation
  - admin_alert
- G2: Email sender worker
  - Render templates; send via Mailjet; log EmailLog; retries; DLQ on terminal failure

Acceptance Criteria:
- Templates render with provided contexts
- EmailLog entries persisted with provider_message_id when available
- Retry strategy applied; on terminal failure → DeadLetter + admin_alert

Testing:
- Unit: template rendering
- Integration: provider mock; EmailLog entries; DLQ path

Dependencies:
- B (EmailLog, DeadLetter), E/F (trigger points)

------------------------------------------------------------

Epic H: Provisional Expiry (S)
- H1: Scheduled worker scans Enrollment where status=provisional and provisional_expires_at < now()
- H2: Revert slot to available; set failure_reason; send admin_alert email

Acceptance Criteria:
- Expired provisionals moved out of holding; related Timeslot effectively free for booking
- Admin alert logged and email enqueued

Testing:
- Time-based logic with frozen time
- Idempotency on repeated runs

Dependencies:
- B, G

------------------------------------------------------------

Epic I: Admin Dashboard P0 Endpoints (S-M)
- I1: GET /admin/dashboard/today
- I2: GET /admin/dashboard/provisionals
- I3: GET /admin/dashboard/payments (from StripeEvent)

Acceptance Criteria:
- Correct aggregations for today’s lessons, provisional aging, and recent payments
- Performance reasonable for MVP dataset

Testing:
- Integration queries; edge cases with empty data

Dependencies:
- C (entities), F (StripeEvent), H (provisionals accurate)

------------------------------------------------------------

Epic J: Observability & DLQ (S)
- J1: Structured logging across booking/Stripe/emails with correlation IDs
- J2: DeadLetter write paths; admin alert surfacing

Acceptance Criteria:
- Logs include request_id/enrollment_id where applicable
- DLQ receives terminal failures

Testing:
- Log shape tests (fields present)
- DLQ insertion on simulated terminal failures

Dependencies:
- B, E/F/G

------------------------------------------------------------

Epic K: CI/CD & Docker (S-M)
- K1: Docker Compose verification: api, celery_worker, redis, db; env examples
- K2: Start scripts; dev migrations on start
- K3: CI workflow:
  - Lint/type checks (ruff/pyright)
  - Unit/integration tests with DB service
  - Alembic migrate
  - Build images
- K4: Release path:
  - Run migrations
  - Deploy containers (Hetzner target follow-up)
- K5: Dev convenience scripts (docker/start.sh, stop.sh)

Acceptance Criteria:
- One-command local bring-up with compose
- CI green from clean checkout

Testing:
- CI pipeline passes; compose boots; health checks OK

Dependencies:
- B (migrations), E (worker), A/C/D endpoints present for smoke tests

------------------------------------------------------------
2. Dependencies and Sequencing
------------------------------------------------------------
Preferred order (with overlap where feasible):
1) B: DB baseline + constraints
2) A: Auth exchange/refresh + AuthZ scaffolding
3) C: Admin CRUD (Teachers, Instruments, Payees, Students, Timeslots, Enrollments, Attendance, Make-ups)
4) D: Public/Parent core (discovery, payee self-upsert, students, booking init/status, make-ups)
5) E: Booking orchestration worker + Celery wiring + Stripe client integration
6) F: Stripe webhooks + idempotent event handling
7) G: Emails + templates + EmailLog/DLQ
8) H: Provisional expiry job + admin alert
9) I: Dashboard P0 endpoints
10) J: Observability & DLQ polish
11) K: CI/CD and Docker polish + smoke tests

External prerequisites:
- Stripe keys (test mode)
- Mailjet keys (or mock provider for dev)
- Supabase JWKS URL or config for signature verification

------------------------------------------------------------
3. Estimation (T-shirt sizes)
------------------------------------------------------------
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

Rationale:
- Heavier time in C/E due to breadth of APIs and booking pipeline complexity.

------------------------------------------------------------
4. Sprint Plan (2 Weeks)
------------------------------------------------------------
Week 1:
- Day 1–2: B (DB baseline + constraints) + A (Auth exchange/refresh, AuthZ)
- Day 2–4: C (Admin CRUD: Teachers, Instruments, Payees, Students, Timeslots)
- Day 4–5: D (Public discovery, payee self-upsert, parent students)
- Ongoing: K1/K2 initial Docker bring-up

Week 2:
- Day 1–2: D (Booking init/status) + E (Booking worker + Stripe client)
- Day 2–3: F (Webhooks) + G (Emails)
- Day 3: H (Provisional expiry) + I (Dashboard P0)
- Day 4: J (Observability/DLQ polish), K3/K4 (CI setup, test run, release prep)
- Day 5: Hardening, test passes, documentation touch-ups for endpoints

Milestones:
- M1 (End Week 1): All CRUD and auth in place; compose boots; seed data present
- M2 (Mid Week 2): Booking happy path works end-to-end with Stripe test; status polling returns active
- M3 (End Week 2): Webhooks, emails, provisional expiry, dashboards P0, CI green

------------------------------------------------------------
5. Testing Strategy
------------------------------------------------------------
- Unit:
  - Token/JWT utils; role derivation
  - Booking orchestration logic (Stripe client mocked)
  - Email rendering templates
  - Webhook signature verification

- Integration:
  - Admin CRUD routes (admin-auth enforced)
  - Parent scope routes (self-upsert, students)
  - Booking init/status with DB locking and provisional creation
  - Celery worker executing booking pipeline (test queue/broker)
  - Webhook processing with idempotency (replay handling)
  - Provisional expiry transitions
  - Dashboard endpoint correctness

- E2E Smoke (API-only):
  - Sequence: public discovery → parent self-upsert → student create → booking init (202) → simulate worker completion → status active → confirmation email enqueued

- Observability:
  - Validate log fields for booking attempts, Stripe outcomes, email sends
  - DLQ entries on terminal failures

Test Data/Fixtures:
- Seed instruments; sample teacher/timeslots; sample payee/student identities
- Stripe in test mode; Mailjet mocked for CI

------------------------------------------------------------
6. CI/CD Pipeline Design
------------------------------------------------------------
- CI Stages:
  - Setup Python env
  - Lint (ruff) and type-check (pyright)
  - Start services (Postgres, Redis) for integration tests
  - Alembic upgrade
  - Run unit + integration tests
  - Build Docker images (api, worker)

- CD (Release outline):
  - Run migrations on target
  - Deploy updated containers
  - Verify health endpoints
  - Post-deploy smoke: booking init 202 + worker completes with mocked Stripe if prod test env; otherwise staging

Artifacts:
- Test reports, coverage (if enabled)
- Built images tagged with commit SHA

------------------------------------------------------------
7. Quality Assurance Measures
------------------------------------------------------------
- Code standards: ruff-configured lint; docstrings for services; clear error handling
- PR checklist: migration impact, API contract changes, security review
- Structured logging: correlation IDs on booking flows
- Idempotency: enrollment_id as orchestration key; stripe_event_id uniqueness for webhooks
- Database constraints to prevent logical inconsistencies (double-booking)

------------------------------------------------------------
8. Risk Mitigation
------------------------------------------------------------
- Stripe complexity: use idempotency keys; retries with exponential backoff; clear failure_reason; strong logging
- Concurrency/double-booking: SELECT ... FOR UPDATE and partial unique index on Enrollment; transactional writes
- Time constraints: strictly API-first; Dashboard limited to P0; defer non-essential features
- External services availability: circuit breaker-ish retry policies; DLQ on terminal failure; admin alerts
- Security: Supabase JWT verification; strict admin allowlist; CORS locked in prod; webhook signature verification

------------------------------------------------------------
9. Progress Tracking
------------------------------------------------------------
- Daily standup checkpoints:
  - Migrations status
  - Endpoint coverage vs checklist
  - Booking pipeline E2E status
  - Webhook and email paths verified
  - CI state (green/red)
- Burndown on epics:
  - Track completion of subtasks by epic
- Done Definition per task:
  - Code + tests + docs/comments + migrations applied + endpoints wired in router + relevant logs/metrics verified

------------------------------------------------------------
10. Task Checklist (Condensed)
------------------------------------------------------------
- [ ] B: Alembic baseline and constraints
- [ ] A: /auth/exchange and /auth/refresh; AuthZ deps
- [ ] C: Admin CRUD (Teachers, Instruments, Payees, Students, Timeslots, Enrollments, Attendance, Make-ups)
- [ ] D: Public/Parent APIs (discovery, payee self-upsert, students, booking init/status, make-ups)
- [ ] E: Celery booking pipeline (customer/PM/subscription-or-invoice) + retries
- [ ] F: Stripe webhooks + idempotency + reconciliation
- [ ] G: Emails (templates, sender, logging, retries, DLQ)
- [ ] H: Provisional expiry worker
- [ ] I: Dashboard P0 endpoints
- [ ] J: Observability + DLQ pathways
- [ ] K: CI/CD + Docker polish + smoke tests

Notes:
- All features align with existing /app modules: api/router, services, worker, workflows per ADD. No divergence from docker/docker-compose.* patterns. Migrations via Alembic in app/alembic.

End of Document