# System Architecture Document (ADD)
Cedar Heights Music Academy — MVP

Version: 0.1
Date: 2025-08-11
Status: Draft for Review

1. Executive Summary
- Goal: Deliver a minimal, stable system to run a music school: enrollment, fixed weekly lesson scheduling, and billing via Stripe. Parent-facing SPA, Admin UI, and reliable backend with async workflows.
- Scope (MVP): Fixed weekly 30-min lessons, one active slot per student, parent self-booking, Stripe as the system of record for all payment objects, attendance/no-shows, basic make-up policy, essential emails, observability/logging.
- Architecture Shape:
  - FastAPI backend (single service) for Admin + Parent APIs
  - Celery workers for async/long-running tasks and retries
  - React/Vite SPA for parent flows
  - PostgreSQL for operational data
  - Redis for Celery broker, Postgres for Celery result backend
  - Stripe integration (live queries, no denormalized payment cache)
  - Mailjet for transactional email (in-repo Jinja templates)

2. Architecture Decisions (Key ADRs)
- Payment Source of Truth: Stripe authoritative. Store only Stripe IDs locally; no denormalized payment state or schedules. Query live with idempotent operations.
- Identity & Roles:
  - Supabase Auth for all identities (parents and admins unified).
  - MVP role policy: Hardcoded admin email allowlist; everyone else is parent.
- API/Worker Topology:
  - Single FastAPI app for synchronous endpoints and orchestration
  - Celery workers for async tasks: Stripe ops, email sending, provisional expiry
  - Follow existing /app/ structure (api + services for quick interactions; workflows for complex/longer processes).
- Concurrency/Locking:
  - Use Postgres transactional locking (SELECT ... FOR UPDATE) to enforce atomic booking of timeslots and enrollment creation.
- Emails:
  - Provider: Mailjet
  - Templating: In-repo Jinja templates rendered server-side; raw HTML sent via API
- Frontend:
  - Parent UI is a separate SPA (React/Vite) consuming FastAPI APIs
- Authentication Flow (SPA ↔ Backend):
  - SPA authenticates with Supabase JS SDK
  - Backend verifies Supabase JWT and issues its own HS256 JWT session token (2h expiry)
  - Refresh endpoint issues new backend JWT when a valid Supabase JWT is presented
- Async vs Sync:
  - Sync in API request: Acquire DB lock and write Enrollment in provisional status
  - Async via Celery: Stripe operations (customer, payment method, subscription/invoice), email sends, provisional expiry checks
- Webhooks:
  - Subscribe to: customer.created, payment_method.attached, invoice.payment_failed, invoice.payment_succeeded, customer.subscription.created/updated/deleted
  - Idempotent handling; failures persisted and retried; admin alert on exhaustion
- Celery Broker/Backend:
  - Redis as broker
  - Postgres as result backend for persistence
- Retries and DLQ:
  - Exponential backoff 2^n up to 5 retries for external calls (Stripe, Mailjet)
  - Persist terminal failures to dead-letter table and raise Admin alert
- Migrations:
  - All schema changes gated via Alembic with versioned migrations committed to repo

3. Services and Modules
- FastAPI Service (app/main.py)
  - Routers:
    - Admin API: CRUD for teachers, instruments, payees, students, timeslots; dashboard queries; attendance/no-shows; make-up administration
    - Parent API: Discovery of teachers/timeslots; booking orchestration; booking status polling; student creation under payee
    - Webhooks: Stripe webhooks receiver (idempotent, secure, signed)
    - Auth Exchange: Endpoint to verify Supabase JWT and mint backend session JWT; refresh endpoint
- Celery Workers (app/worker)
  - Tasks:
    - Booking pipeline worker: performs Stripe steps and finalizes enrollment
    - Email worker: renders Jinja templates and sends via Mailjet
    - Provisional expiry worker: scans expirations and reverts slots with admin alert
    - Webhook post-processors: reconcile and update entities; emit admin alerts when needed
- Workflow Coordination
  - Workflow registry used to orchestrate long-running operations consistently with the existing code pattern under app/workflows

4. Data Model (MVP)
Note: IDs are UUID unless specified. created_at/updated_at are timestamptz with defaults. Soft-delete not required for MVP unless stated.

4.1 Entities
- Payee
  - id (UUID PK)
  - name (text)
  - email (text, unique when used for login mapping; stored for contact/reference)
  - phone (text, nullable)
  - status (enum: active, inactive) default active
  - created_at, updated_at

- Student
  - id (UUID PK)
  - payee_id (FK → Payee.id)
  - name (text)
  - instrument_id (FK → Instrument.id)
  - teacher_pref_id (FK → Teacher.id, nullable)
  - consent_policy_accepted_at (timestamptz)
  - stripe_customer_id (text, nullable)
  - stripe_default_payment_method_id (text, nullable)
  - created_at, updated_at

- Teacher
  - id (UUID PK)
  - name (text)
  - email (text, nullable)
  - pay_per_lesson (numeric(10,2))
  - created_at, updated_at

- Instrument
  - id (UUID PK)
  - name (text unique; e.g., piano, guitar, drums, bass)

- Timeslot (published weekly recurring slot)
  - id (UUID PK)
  - teacher_id (FK → Teacher.id)
  - weekday (int 0-6; 0=Sunday or choose convention)
  - start_time (time without tz)
  - end_time (time without tz)
  - active_flag (boolean)
  - created_at, updated_at
  - Unique constraint (teacher_id, weekday, start_time, end_time)

- Enrollment (student → timeslot mapping)
  - id (UUID PK)
  - student_id (FK → Student.id)
  - timeslot_id (FK → Timeslot.id)
  - start_date (date)
  - status (enum: provisional, active, cancelled)
  - stripe_subscription_id (text, nullable)
  - stripe_invoice_id (text, nullable)
  - provisional_expires_at (timestamptz, nullable)
  - failure_reason (text, nullable)
  - created_at, updated_at
  - Unique partial index ensuring one active/provisional enrollment per student (enforce “one active weekly slot per student”)

- Attendance (per scheduled occurrence)
  - id (UUID PK)
  - enrollment_id (FK → Enrollment.id)
  - date (date)
  - status (enum: present, no_show)
  - notes (text, nullable)
  - created_at

- MakeUpRecord
  - id (UUID PK)
  - student_id (FK → Student.id)
  - semester_id (FK → Semester.id)
  - status (enum: available, booked, forfeited)
  - booked_date (date, nullable)
  - created_at, updated_at

- Semester
  - id (UUID PK)
  - name (enum/text: Fall, Winter, Spring, Summer)
  - start_date (date)
  - end_date (date)
  - created_at, updated_at

- EmailLog
  - id (UUID PK)
  - recipient (text)
  - template (text)  // e.g., booking_confirmation, provisional_notice, no_show, make_up_invite, make_up_confirmation, admin_alert
  - provider_message_id (text, nullable)
  - status (enum: queued, sent, failed)
  - payload (jsonb) // rendered variables snapshot
  - error (text, nullable)
  - created_at, updated_at
  - Index on (recipient, created_at desc)

- StripeEvent (for idempotency and debugging)
  - id (UUID PK)
  - stripe_event_id (text unique)
  - type (text)
  - payload (jsonb)
  - processed (boolean default false)
  - error (text, nullable)
  - created_at, updated_at

- DeadLetter (generic DLQ)
  - id (UUID PK)
  - task_name (text)
  - payload (jsonb)
  - last_error (text)
  - attempts (int)
  - created_at, updated_at

4.2 Indexing and Constraints
- Unique constraints on Timeslot windows per teacher
- Partial unique index on Enrollment to enforce one active/provisional slot per student
- EmailLog indexing on recipient and created_at
- StripeEvent unique on stripe_event_id

5. API Endpoints
All backend endpoints expect the backend session JWT (issued after Supabase verification) unless noted public.

5.1 Auth
- POST /auth/exchange
  - Body: { supabase_jwt: string }
  - Response: { backend_jwt: string, expires_in: number }
  - Validates Supabase JWT signature and claims; checks admin allowlist if applicable; issues HS256 backend JWT (2h)
- POST /auth/refresh
  - Body: { supabase_jwt: string }
  - Response: { backend_jwt: string, expires_in: number }

5.2 Admin API (requires admin email allowlist)
- Teachers:
  - POST /admin/teachers
  - GET /admin/teachers
  - GET /admin/teachers/{id}
  - PUT /admin/teachers/{id}
  - DELETE /admin/teachers/{id}
- Instruments:
  - POST /admin/instruments
  - GET /admin/instruments
  - PUT /admin/instruments/{id}
  - DELETE /admin/instruments/{id}
- Payees:
  - POST /admin/payees
  - GET /admin/payees
  - GET /admin/payees/{id}
  - PUT /admin/payees/{id}
  - DELETE /admin/payees/{id}
- Students:
  - POST /admin/students
  - GET /admin/students?payee_id=
  - GET /admin/students/{id}
  - PUT /admin/students/{id}
  - DELETE /admin/students/{id}
- Timeslots:
  - POST /admin/timeslots
  - GET /admin/timeslots?teacher_id=&weekday=
  - PUT /admin/timeslots/{id}
  - DELETE /admin/timeslots/{id}
- Enrollments (admin assignment/override):
  - POST /admin/enrollments  // assign student to timeslot atomically
  - PUT /admin/enrollments/{id}/cancel
  - GET /admin/enrollments?status=&student_id=&timeslot_id=
- Attendance:
  - POST /admin/attendance  // mark for a date
  - GET /admin/attendance?enrollment_id=&date=
- Make-Ups:
  - POST /admin/makeups/windows  // define make-up weeks (Semesters)
  - GET /admin/makeups/status?student_id=
- Dashboard (P0):
  - GET /admin/dashboard/today  // today’s lessons with student/teacher/time; actions to mark attendance/no-show
  - GET /admin/dashboard/provisionals  // list provisional enrollments with days remaining to expiry
  - GET /admin/dashboard/payments  // recent Stripe payment events (success/failed)

5.3 Parent/Public API
- Public discovery (read-only; may be public or require session depending on policy):
  - GET /public/teachers
  - GET /public/timeslots?teacher_id=&weekday=&active=true
- Parent operations (backend session required):
  - POST /parent/payees/self  // idempotent upsert of current user as payee based on Supabase identity (if needed)
  - POST /parent/students     // create student under current payee
  - GET  /parent/students
  - POST /parent/bookings     // initiate booking: student_id, timeslot_id, payment_frequency
    - Behavior: Acquire DB lock, create provisional Enrollment with provisional_expires_at, enqueue booking job, return 202 with tracking_id=enrollment_id
  - GET  /parent/bookings/{enrollment_id}/status  // poll for status=provisional|active with optional failure_reason
  - GET  /parent/makeups/slots  // if eligible, returns make-up slots constrained to regular day/time during defined windows
  - POST /parent/makeups/book   // book make-up; constraints enforced; single use

5.4 Webhooks (Stripe)
- POST /webhooks/stripe
  - Validates signature; idempotent by stripe_event_id
  - Persists StripeEvent
  - Handles:
    - customer.created
    - payment_method.attached
    - invoice.payment_failed
    - invoice.payment_succeeded
    - customer.subscription.created/updated/deleted
  - Updates local linkages/status; enqueues retry tasks when appropriate
  - Returns 200 OK on success; 2xx on idempotent replay

6. Request/Response Contracts (Selected)
- POST /parent/bookings
  - Request:
    {
      "student_id": "uuid",
      "timeslot_id": "uuid",
      "payment_frequency": "monthly|yearly|semester"
    }
  - Response: 202 Accepted
    {
      "tracking_id": "uuid",   // enrollment_id
      "status": "provisional",
      "provisional_expires_at": "timestamp"
    }
- GET /parent/bookings/{id}/status
  - Response:
    {
      "status": "provisional|active|cancelled",
      "failure_reason": "string|null",
      "stripe_subscription_id": "string|null",
      "stripe_invoice_id": "string|null"
    }
- Admin Dashboard Samples:
  - GET /admin/dashboard/today
    [
      {
        "time": "HH:MM",
        "teacher": { "id": "...", "name": "..." },
        "student": { "id": "...", "name": "..." },
        "enrollment_id": "...",
        "status": "scheduled|present|no_show"
      },
      ...
    ]
  - GET /admin/dashboard/provisionals
    [
      {
        "enrollment_id": "...",
        "student": "name",
        "teacher": "name",
        "timeslot": { "weekday": 2, "start_time": "16:00" },
        "expires_in_days": 10
      },
      ...
    ]
  - GET /admin/dashboard/payments
    [
      {
        "stripe_event_id": "...",
        "type": "invoice.payment_succeeded|invoice.payment_failed",
        "customer_id": "...",
        "student_id": "...",
        "occurred_at": "timestamp"
      },
      ...
    ]

7. Booking Orchestration and Concurrency
7.1 Sequence (Parent Self-Booking)
- API receives booking request with student_id, timeslot_id, payment_frequency
- Begin DB transaction:
  - SELECT timeslot FOR UPDATE to lock
  - Validate no conflicting active/provisional enrollment for student
  - Insert Enrollment with status=provisional, provisional_expires_at=now()+interval '14 days'
  - Commit
- Enqueue Celery booking job with enrollment_id and requested frequency
- Return 202 + tracking_id=enrollment_id
- Celery booking job:
  - Idempotency key: enrollment_id
  - Stripe steps with retries/backoff:
    1) Ensure stripe_customer_id on Student (create if missing)
    2) Ensure default payment method (enqueue email to parent if out-of-band required; otherwise proceed)
    3) Create subscription/invoice based on selected frequency and PRD rules
  - On success: update Enrollment.status=active; set stripe_subscription_id/invoice_id; send booking confirmation
  - On failure: record failure_reason; send provisional notice email; leave status=provisional
- SPA polls /parent/bookings/{id}/status until active or manual intervention

7.2 Locking Model
- Use Postgres SELECT ... FOR UPDATE on Timeslot and/or target Enrollment rows inside a single authoritative write path to prevent double-booking
- Enforce partial unique index on Enrollment for a student’s active/provisional states to guarantee “one weekly slot” rule even under concurrency

8. Payments Design
- Frequencies:
  - Month-to-month: subscription bills on 1st
  - Yearly w/ installments: first + last charged at signup; schedule remaining 9 installments; admin retains last month if cancelled; otherwise applied to final month
  - Semester lump sum: single invoice at semester start
- Start date gating per PRD; admin override possible
- If first lesson beyond week 1, still charge full month; admin may issue manual credits
- Stripe live queries; store only linkage IDs locally
- Webhooks update local Enrollment/payment statuses but no denormalized caches

9. Email Design (Mailjet)
- Templates (in-repo, Jinja):
  - booking_confirmation
  - provisional_notice
  - no_show_notice
  - make_up_invite
  - make_up_confirmation
  - admin_alert
- Email worker flow:
  - Render Jinja HTML using context payload
  - Send via Mailjet API
  - Log to EmailLog with status and provider_message_id
  - Retries with backoff; on terminal failure → DeadLetter + Admin alert

10. Security
- TLS for all traffic end-to-end
- AuthN:
  - SPA uses Supabase for login; backend verifies Supabase JWT and issues short-lived backend JWT
  - Backend JWT: HS256, 2h expiry; includes subject (user id/email), role (admin|parent), issued_at, expiry
  - Refresh: requires presenting a current valid Supabase JWT for a new backend JWT
- AuthZ:
  - Admin endpoints gated by admin email allowlist in config for MVP
  - Parent endpoints restricted to the authenticated user’s payee_id scope
- PII:
  - Store minimal PII: payee, student; no card data (PCI handled by Stripe)
- Webhooks:
  - Verify Stripe signatures; store stripe_event_id for idempotency
- Compliance: PIPEDA/BC PIPA aligned retention; anonymize attendance/booking after 24 months; retain financial links 7 years

11. Observability & Monitoring
- Structured logging:
  - Booking transitions: selected → locked → provisional → active/cancelled
  - Stripe API calls and outcomes with correlation IDs
  - Email sends and outcomes
- Tables for operational insight:
  - EmailLog, StripeEvent, DeadLetter
- Admin dashboard widgets (P0) surface system health indicators relevant to operations

12. Deployment & Infrastructure
- Dockerized services per docker/docker-compose.launchpad.yml
  - api: FastAPI app exposed on 127.0.0.1:8080 for local/dev
  - celery_worker: processes async tasks
  - redis: Celery broker
  - db: Supabase Postgres image serving as Postgres
- ENV configuration driven by docker env; secrets mounted via .env
- Hetzner hosting target; production deploy mirrors compose with appropriate hardening
- Migrations via Alembic; CI/CD runs migrations on release

13. Testing Strategy
- Unit tests: domain services (booking orchestration sans external calls), email rendering
- Integration tests: API booking flow with DB locking and mock Celery; Stripe calls mocked with VCR-like cassettes
- Webhook tests: signature verification and idempotency
- E2E smoke: SPA → API booking 202 + polling cycle; simulated worker completion; confirmation email enqueued

14. Open Questions (Next Iterations)
- Admin UI delivery form: server-rendered vs SPA; MVP assumes Admin UI can be served as simple pages or a minimal admin SPA later
- Teacher notifications (email/SMS) for new bookings and daily schedules (post-MVP)
- Self-serve cancellations and policy enforcement automation (post-MVP)
- Parent portal enhancements: upcoming lessons view, payment info (post-MVP)
- Role management beyond hardcoded admin allowlist (Supabase custom claims or Roles table)

15. Endpoint Checklist (Implementation Order)
1) Auth
- POST /auth/exchange
- POST /auth/refresh
2) Parent Booking Core
- GET /public/teachers
- GET /public/timeslots
- POST /parent/payees/self
- POST /parent/students
- GET /parent/students
- POST /parent/bookings
- GET /parent/bookings/{id}/status
3) Admin Core
- CRUD: /admin/teachers, /admin/instruments, /admin/payees, /admin/students, /admin/timeslots
- /admin/enrollments (assign/cancel)
- /admin/attendance
- /admin/makeups/windows, /admin/makeups/status
- /admin/dashboard/today, /admin/dashboard/provisionals, /admin/dashboard/payments
4) Webhooks
- POST /webhooks/stripe
5) Background Tasks
- Celery booking pipeline, email sender, provisional expiry, webhook processors

16. Database Schema Fields (Tabular Summary)
- Payee(id, name, email, phone, status, created_at, updated_at)
- Student(id, payee_id, name, instrument_id, teacher_pref_id, consent_policy_accepted_at, stripe_customer_id, stripe_default_payment_method_id, created_at, updated_at)
- Teacher(id, name, email, pay_per_lesson, created_at, updated_at)
- Instrument(id, name)
- Timeslot(id, teacher_id, weekday, start_time, end_time, active_flag, created_at, updated_at)
- Enrollment(id, student_id, timeslot_id, start_date, status, stripe_subscription_id, stripe_invoice_id, provisional_expires_at, failure_reason, created_at, updated_at)
- Attendance(id, enrollment_id, date, status, notes, created_at)
- MakeUpRecord(id, student_id, semester_id, status, booked_date, created_at, updated_at)
- Semester(id, name, start_date, end_date, created_at, updated_at)
- EmailLog(id, recipient, template, provider_message_id, status, payload, error, created_at, updated_at)
- StripeEvent(id, stripe_event_id, type, payload, processed, error, created_at, updated_at)
- DeadLetter(id, task_name, payload, last_error, attempts, created_at, updated_at)

17. Migration Plan (Alembic)
- Baseline migration introducing all MVP tables and enums
- Subsequent revisions for indexes/constraints:
  - Unique constraint on Timeslot (teacher_id, weekday, start_time, end_time)
  - Partial unique index on Enrollment for one active/provisional per student
  - Indexes on EmailLog(recipient, created_at desc), StripeEvent(stripe_event_id unique)

18. Security Model Details (Backend JWT)
- Algorithm: HS256
- Claims: sub (Supabase user id or email), email, role (admin|parent), iat, exp (2h)
- Rotation: Refresh by POST /auth/refresh with valid Supabase JWT
- Storage: SPA stores backend JWT in memory (avoid localStorage if possible); attach Authorization: Bearer header
- CORS: Lock down origins to SPA’s origin(s) in production

19. Failure Handling Matrix (External Ops)
- Stripe (customer, payment method, subscription/invoice):
  - Retry: exponential backoff 2^n up to 5
  - On terminal failure: persist to DeadLetter, set Enrollment.failure_reason, keep status=provisional, Admin alert, dashboard visible
- Mailjet:
  - Retry: exponential backoff 2^n up to 5
  - On terminal failure: EmailLog.status=failed, DeadLetter insert, Admin alert

20. Diagrams (Described)
- Booking Flow:
  - SPA → POST /parent/bookings → API locks Timeslot + provisional Enrollment → Celery booking job enqueued → SPA polls status → Celery executes Stripe steps → On success, Enrollment active + confirmation email; on failure, Enrollment remains provisional + provisional notice email
- Webhook Flow:
  - Stripe → /webhooks/stripe (verify + persist) → idempotency check → update Enrollment / Student linkages → enqueue follow-ups if needed → admin dashboard feed updates
- Admin Dashboard Data:
  - Today’s lessons: join Teacher × Timeslot × Enrollment × Student filtered to current day/time windows
  - Provisionals: Enrollment where status=provisional; compute days remaining
  - Payments feed: derived from StripeEvent within recent timeframe

End of Document