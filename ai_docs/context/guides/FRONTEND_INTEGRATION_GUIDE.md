# Frontend Integration Guide
Cedar Heights Music Academy — API-first MVP

Purpose
- Enable frontend developers to build wireframes and integrate with the backend using a consistent auth model, endpoint contracts, and event-driven workflows.
- Scope aligns with API-first MVP: Admin and Parent UIs are deferred, but this guide specifies how those UIs will integrate when built.

Audience
- Frontend engineers building:
  - Parent SPA (React/Vite) for self-booking and status polling
  - Minimal Admin UI (future) for CRUD/attendance/dashboard


1. Authentication and Session Model

1.1 Identity Provider (Supabase Auth)
- Parents and Admins authenticate using Supabase Auth (email verification).
- Frontend uses Supabase JavaScript SDK for sign-up, login, and session management.

1.2 Backend Session Token (FastAPI)
- After a valid Supabase session exists, frontend calls:
  - POST /auth/exchange → back-end issues short-lived HS256 JWT (2h)
  - POST /auth/refresh → when Supabase JWT still valid, obtain a fresh backend JWT
- Backend JWT is required in Authorization: Bearer headers for all protected API calls.

1.3 Roles
- MVP role policy via admin email allowlist (config). Everyone else is parent.
- Role is encoded in backend JWT claims (role=admin|parent).
- Admin endpoints require admin role.

1.4 Token Handling (Frontend)
- Store Supabase session per Supabase SDK guidance.
- Store backend JWT in memory (avoid persistent localStorage if possible).
- Refresh patterns:
  - On app boot, if Supabase session is present: call /auth/exchange
  - On 401 from API with a valid Supabase session: call /auth/refresh, retry original request
- CORS: backend restricts allowed origins in non-dev environments.

Sequence: Parent Login and Session Bootstrapping
1) User signs in/up via Supabase SDK → obtain session
2) Call POST /auth/exchange with supabase_jwt → receive backend_jwt, expires_in
3) Use backend_jwt in Authorization header for subsequent API calls
4) Near expiry or on 401, call POST /auth/refresh with current supabase_jwt → update backend_jwt


2. API Overview and Contracts

2.1 Auth
- POST /auth/exchange
  - Body: { "supabase_jwt": string }
  - Response: { "backend_jwt": string, "expires_in": number }
  - Usage: exchange Supabase JWT for backend JWT

- POST /auth/refresh
  - Body: { "supabase_jwt": string }
  - Response: { "backend_jwt": string, "expires_in": number }
  - Usage: refresh backend JWT when Supabase session is still valid

2.2 Public Discovery (no auth required)
- GET /public/teachers
  - Returns a list of available teachers
- GET /public/timeslots?teacher_id=&weekday=&active=true
  - Returns published fixed weekly 30-min slots
  - Filters: teacher_id (optional), weekday (0-6), active=true (default)

2.3 Parent-Scoped Operations (backend JWT required)
Attach Authorization: Bearer {backend_jwt}

- POST /parent/payees/self
  - Purpose: idempotent self-upsert of current authenticated parent’s Payee record
  - Body: {}
  - Response: { payee_id, name, email, ... } (server resolves identity from Supabase claims)

- POST /parent/students
  - Create a student under the authenticated parent’s payee
  - Body:
    {
      "name": "string",
      "instrument_id": "uuid",
      "teacher_pref_id": "uuid|null",
      "consent_policy_accepted_at": "timestamp"
    }
  - Response: { id, ... }

- GET /parent/students
  - List students under the authenticated parent’s payee

- POST /parent/bookings
  - Initiate booking:
    - Locks target Timeslot transactionally
    - Creates provisional Enrollment (status=provisional, provisional_expires_at=now()+14d)
    - Enqueues background booking job (Stripe steps)
  - Body:
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

- GET /parent/bookings/{enrollment_id}/status
  - Poll for booking status
  - Response:
    {
      "status": "provisional|active|cancelled",
      "failure_reason": "string|null",
      "stripe_subscription_id": "string|null",
      "stripe_invoice_id": "string|null"
    }

- GET /parent/makeups/slots
  - If eligible (Semester/Yearly plans and make-up windows defined), returns constrained make-up slots

- POST /parent/makeups/book
  - Book one make-up within defined windows aligned to student’s regular day/time

2.4 Admin API (backend JWT with role=admin)
- CRUD endpoints:
  - /admin/teachers
  - /admin/instruments
  - /admin/payees
  - /admin/students
  - /admin/timeslots
  - /admin/enrollments (assign/cancel)
  - /admin/attendance
  - /admin/makeups/windows (define semesters), /admin/makeups/status
- Dashboard (P0):
  - GET /admin/dashboard/today
  - GET /admin/dashboard/provisionals
  - GET /admin/dashboard/payments

2.5 Webhooks (Server-to-Server)
- POST /webhooks/stripe
  - Stripe signs requests; server verifies signatures
  - Frontend does not call this; used for backend reconciliation of payment events


3. Booking Workflow: Frontend Perspective

3.1 Parent Booking Happy Path
1) Parent logs in via Supabase; exchange for backend JWT
2) Discover teachers and timeslots:
   - GET /public/teachers
   - GET /public/timeslots?teacher_id=&weekday=&active=true
3) Ensure Payee exists:
   - POST /parent/payees/self (idempotent)
4) Create Student:
   - POST /parent/students
5) Choose payment frequency (monthly|yearly|semester)
6) Initiate booking:
   - POST /parent/bookings
   - Receive 202 with tracking_id and provisional_expires_at
7) Show “Booking in progress” state; poll:
   - GET /parent/bookings/{tracking_id}/status at intervals (e.g., 2-5s with max duration/backoff)
8) Backend booking worker executes Stripe steps:
   - Ensure stripe_customer_id on Student (create if missing)
   - Ensure default payment method (if out-of-band required → stays provisional)
   - Create subscription (monthly/yearly) or invoice (semester) per PRD rules
9) On success:
   - Enrollment becomes active, status returns active with Stripe IDs
   - Backend queues booking_confirmation email

UI Guidance
- Show provisional/status states clearly with timers (days remaining from provisional_expires_at)
- If status remains provisional with failure_reason (e.g., missing payment method), prompt user to complete payment method in Stripe-hosted flow if applicable
- On active, show confirmation screen; optionally list lesson day/time and start date rules from PRD

3.2 Failure and Provisional Handling
- If any required Stripe step fails:
  - Enrollment remains provisional
  - Provisional expiry set (2 weeks)
  - Provisional email sent to parent with instructions
- Frontend should display:
  - Clear message of provisional state and required actions (per email content)
  - Time remaining before expiry
  - Contact admin path if needed

3.3 Concurrency Behavior
- Locking: First completion wins; second attempt receives “slot no longer available” outcome with no Stripe side-effects
- UX: On conflict, display a friendly message and prompt user to select a different slot


4. Make-Up Lessons: Frontend Perspective

4.1 Eligibility
- Offered only to students on Semester or Yearly plans
- Admin defines make-up weeks (Semesters)
- Make-up slots constrained to the student’s regular day/time window

4.2 Flow
- No-show recorded by Admin triggers no_show_notice email
- When make-up windows open for eligible students:
  - Frontend fetches GET /parent/makeups/slots
  - Parent selects a single eligible slot and confirms via POST /parent/makeups/book
- Rules:
  - One make-up per incident; once booked, cannot book another for the same window
  - If not used within window, forfeited
- UX:
  - Indicate window dates and regular time constraint
  - Confirmations and errors surfaced to parent


5. Emails and Notifications (Reference for UI Messaging)

Templates emitted by backend (Mailjet):
- booking_confirmation: Booking confirmed details
- provisional_notice: Action required and expiry date; shows what to complete (e.g., payment method)
- no_show_notice: Attendance update and make-up eligibility info
- make_up_invite: Eligibility and link to selective slots
- make_up_confirmation: Confirmed date/time for make-up
- admin_alert: Operational alert for admins (not user-facing)

Frontend should align copy and UX states with these lifecycle events where possible to reduce confusion.


6. Data and Entities Relevant to Frontend

Key Entities (read/write relevance):
- Teacher: id, name, instruments (derived)
- Instrument: id, name (piano, guitar, drums, bass)
- Timeslot: id, teacher_id, weekday(0-6), start_time, end_time, active_flag
- Payee: id, name, email (server-resolved for parent)
- Student: id, payee_id, name, instrument_id, teacher_pref_id (nullable), stripe_customer_id?, stripe_default_payment_method_id?
- Enrollment (Tracking ID for bookings): id, student_id, timeslot_id, start_date, status (provisional|active|cancelled), stripe_subscription_id?, stripe_invoice_id?, provisional_expires_at?, failure_reason?
- Attendance, MakeUpRecord, Semester (read flows; Admin writes)

Notes:
- Stripe linkage lives on Student and Enrollment. Frontend never handles card data; Stripe-hosted flows or backend workers handle creation/attachment.


7. Error Handling and UX Recommendations

7.1 Standard API Errors
- 400: Validation errors — display field-level messaging
- 401: Missing/invalid tokens — prompt re-auth or refresh
- 403: Forbidden — show “not authorized”
- 404: Resource not found — show friendly message, refresh list
- 409: Conflict (e.g., slot already booked) — show “slot unavailable” and prompt to reselect
- 429/5xx: Retry/backoff messaging; allow user to retry later

7.2 Booking-Specific UX
- Provisional with failure_reason:
  - Show reason and instructions (from provisional_notice content guidance)
  - Provide link or CTA to complete payment method if relevant
- Status polling:
  - Use exponential backoff (e.g., 2s, 4s, 8s up to cap)
  - Provide cancel/close option; on re-open, continue polling or show last known status

7.3 Accessibility/Internationalization
- MVP is English-only, but aim for accessible and clear wording for parents
- Time formatting consistent with local timezone (BC)


8. Environment and Configuration

8.1 Dev/Local
- Base URL: http://127.0.0.1:8080 (compose default)
- Supabase project URL and anon key for Auth in the frontend
- Stripe in test mode; Mailjet can be mocked in dev
- CORS: allow localhost dev origins

8.2 Headers and Auth
- Authorization: Bearer <backend_jwt> for protected endpoints
- Content-Type: application/json

8.3 Timezone Conventions
- Weekday 0-6; confirm convention (0=Sunday) consistent with backend
- All timestamps are ISO 8601; display in local time for users


9. Example Integration Snippets (Pseudo/TypeScript-ish)

9.1 Exchange Supabase JWT for Backend JWT
async function exchange(supabaseJwt: string) {
  const res = await fetch("/auth/exchange", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ supabase_jwt: supabaseJwt }),
  });
  if (!res.ok) throw new Error("Exchange failed");
  return res.json(); // { backend_jwt, expires_in }
}

9.2 Fetch Public Timeslots
async function getTimeslots(params) {
  const qs = new URLSearchParams(params).toString();
  const res = await fetch(`/public/timeslots?${qs}`);
  if (!res.ok) throw new Error("Failed to fetch timeslots");
  return res.json();
}

9.3 Self-Upsert Payee (Parent)
async function upsertPayeeSelf(backendJwt: string) {
  const res = await fetch("/parent/payees/self", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${backendJwt}`,
    },
    body: JSON.stringify({}),
  });
  if (!res.ok) throw new Error("Payee upsert failed");
  return res.json();
}

9.4 Create Student
async function createStudent(backendJwt: string, payload) {
  const res = await fetch("/parent/students", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${backendJwt}`,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Student create failed");
  return res.json();
}

9.5 Initiate Booking and Poll Status
async function bookAndPoll(backendJwt: string, payload) {
  const initRes = await fetch("/parent/bookings", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${backendJwt}`,
    },
    body: JSON.stringify(payload),
  });
  if (initRes.status !== 202) throw new Error("Booking init failed");
  const initData = await initRes.json(); // { tracking_id, status, provisional_expires_at }

  let delay = 2000; // start 2s
  for (let i = 0; i < 8; i++) {
    await new Promise(r => setTimeout(r, delay));
    const st = await fetch(`/parent/bookings/${initData.tracking_id}/status`, {
      headers: { "Authorization": `Bearer ${backendJwt}` },
    });
    if (!st.ok) throw new Error("Status poll failed");
    const data = await st.json();
    if (data.status === "active" || data.status === "cancelled") return data;
    delay = Math.min(delay * 2, 15000); // backoff up to 15s
  }
  return { status: "provisional", ...initData };
}


10. Workflow/Event Reference

10.1 Booking Workflow (Server-driven)
- Initiation (POST /parent/bookings):
  - DB lock on Timeslot, create Enrollment provisional, enqueue job
- Worker steps:
  - Ensure Stripe Customer (Student-level)
  - Ensure default payment method (may require user action)
  - Create subscription (monthly/yearly) or invoice (semester)
  - Update Enrollment active on success; set failure_reason on error
  - Enqueue confirmation/provisional emails
- Frontend:
  - Poll status; render states and instructions

10.2 Stripe Webhooks
- Backend receives and verifies:
  - invoice.payment_succeeded/failed (payment feed)
  - customer.subscription.created/updated/deleted
  - payment_method.attached, customer.created
- Frontend does not call; may reflect derived state via dashboard endpoints or booking status

10.3 Provisional Expiry
- Scheduled job checks expired provisionals:
  - Reverts slot availability
  - Sets failure_reason; admin_alert email
- Frontend:
  - When polling shows provisional beyond expiry window, instruct user to retry booking or contact admin


11. Admin UI Notes (For Future Sprint)
- CRUD pages for Teachers/Instruments/Payees/Students/Timeslots
- Attendance marking
- Dashboard widgets:
  - Today’s lessons: list with mark present/no_show
  - Provisionals with days remaining
  - Payments feed from StripeEvent


12. Checklists for Frontend Dev

Parent SPA Minimum (Wireframe Ready)
- Auth bootstrap:
  - Supabase SDK setup, email verification flow
  - Exchange/refresh backend JWT
- Discovery:
  - Teachers list, timeslots list with filtering
- Account data:
  - Self-upsert Payee
  - Create/list Students
- Booking:
  - Initiate booking (student + timeslot + frequency)
  - Poll booking status with backoff
  - Handle provisional states and messages
- Make-ups (if implemented in UI now):
  - View slots, book one, show confirmations

Admin UI Minimum (Future)
- Admin-auth gate
- CRUD forms and tables for core entities
- Dashboard P0 pages (today, provisionals, payments)


Appendix: Common Status/Copy Snippets
- Provisional booking:
  - “Your booking is pending. Please complete payment setup if prompted. This hold expires on {date}.”
- Slot conflict:
  - “This time slot is no longer available. Please select a different slot.”
- Booking confirmed:
  - “Your weekly lesson is confirmed: {weekday} {time} with {teacher}. Check your email for details.”
- Make-up eligibility:
  - “A make-up lesson is available between {start_date} and {end_date}, aligned to your regular day/time.”


End of Guide