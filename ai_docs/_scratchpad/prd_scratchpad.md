# PRD Development Scratchpad - Cedar Heights Music Academy

## Project Context
- Music school in BC, Canada
- MVP in 2 weeks
- Starting with 1 teacher/owner, scaling to 1-2 teachers, 50 students Year 1
- Individual music lessons (30-min weekly)
- Instruments: piano, guitar, drums, bass

## Key Business Drivers
- Replace manual processes
- Enable digital payments via Stripe
- Reduce admin time by 50%
- 95% uptime requirement

## Requirements Space Coverage

### User Personas
- [ ] Teacher/Owner (Admin) - Phase 1
- [ ] Parents (Payees) - Phase 2
- [ ] Students (indirect users)
- [ ] Contracting schools (payees)

### Core Functional Areas
- [ ] Student enrollment & registration
- [ ] Lesson scheduling (day/timeslot based)
- [ ] Payment processing (Stripe)
- [ ] Billing & invoicing
- [ ] Teacher availability management
- [ ] Parent booking interface

### Non-Functional Requirements
- [ ] Performance (small load: 1-5 teachers, 20-100 students)
- [ ] Security (PIPEDA, BC PIPA compliance)
- [ ] Usability requirements
- [ ] Reliability (95% uptime)
- [ ] Maintainability

### Data Requirements
- [ ] Student profiles
- [ ] Payee information
- [ ] Teacher profiles
- [ ] Schedule/availability
- [ ] Payment records
- [ ] Invoice generation

### Integration Points
- [ ] Stripe API
- [ ] Email notifications
- [ ] Future parent portal

### Constraints & Assumptions
- [ ] 2-week timeline
- [ ] Single developer
- [ ] Existing FastAPI codebase
- [ ] Hetzner hosting with Docker

### Edge Cases & Error Scenarios
- [ ] Payment failures
- [ ] Schedule conflicts
- [ ] Data privacy for minors
- [ ] System downtime handling

## Questions to Explore
- User journey details for each persona
- Specific business rules for scheduling
- Payment term details and edge cases
- Notification requirements
- Reporting needs
- Data retention policies
- Backup/recovery requirements
<!-- Session 2025-08-10 -->
- MVP scope: Admin ops + Parent self-booking REQUIRED
- Admin must: create payees/students, set teacher availability, assign weekly 30-min slots, generate invoices, process Stripe
- Parent must: self-book available timeslots (Phase 1)
- Parent self-booking: choose from pre-published fixed 30-min weekly slots only; enforce one student per slot; prevent double-booking; no ad-hoc times
- Billing/Payments: Stripe is system of record (knowledge store) for services, schedules, invoices, and payments; app defers to Stripe data
- MVP billing terms: support all three — yearly (monthly installments), semester lump sum, month-to-month; Stripe to auto-generate according to plan
- Data strategy: Query Stripe live for operations; store only internal IDs and Stripe object IDs; no local denormalized cache
- Clarification: “Scheduling” = lessons (timeslots/enrollments) managed by our system; “Payment frequency” = billing cadence managed by Stripe (subscriptions, lump sum, monthly)
- Stripe role: system of record for payment objects and frequency; live queries only; we store internal + Stripe IDs
- Parent self-booking MVP workflow (save):
  1) Parent creates account (Supabase auth)
  2) Select published fixed 30-min timeslot
  3) Define student + instrument
  4) Select preferred teacher (when multiple teachers exist)
  5) Select service and payment frequency (from Stripe)
  6) Create Stripe Customer: name = student name; company = "{parentName} {studentName}"
  7) Store Stripe customer reference in Student table record
  8) Provide valid credit card (Stripe)
  9) Store Stripe payment method reference in Student table record
  10) Agree to amount + payment frequency
  11) Agree to cancellation policy (track consent in Student table record)
  12) Assign timeslot to Student table record
  13) Send confirmation email
  14) Update UI to reflect confirmed booking
- Lesson scheduling rules (confirmed):
  - Fixed weekly 30-min lessons; one active slot per student
  - Admin can track no-shows; no general rescheduling capability
  - Prevent conflicts with atomic booking
- Make-up lesson policy:
  - Admin defines specific make-up weeks per semester (Fall, Winter, Spring, Summer)
  - Eligibility: only students on Semester or Yearly plans
  - Make-up availability constrained to student's regular day/time (e.g., Tue 3:00)
  - Process: on no-show, send email with available make-up slots; parent confirms via link
  - Limits: once a make-up is booked, no additional make-ups; if make-up weeks fill up, inform parent and do not offer additional link
  - If a make-up is not used within designated weeks, it is forfeited
- Admin MVP workflow (confirmed + extensions):
  - Manage payees/students (create/update)
  - Add teacher records; define teacher instruments; set pay per lesson
  - Set teacher availability and publish fixed weekly 30-min slots
  - Manually assign student to slot (conflict-safe, atomic)
  - Initiate Stripe customer/payment method creation when missing
  - Mark no-shows to trigger make-up flow (per semester rules)
- Data model (MVP, confirmed):
  - Entities: Payee, Student, Teacher, Instrument, Timeslot (published weekly slot), Enrollment (student→timeslot), Attendance (per occurrence), NoShow/MakeUp records
  - Stripe linkage fields on Student/Enrollment as needed: customer_id, payment_method_id, subscription_id
- NFR baselines (MVP): uptime 95%; p95 &lt;= 500ms for core ops (excludes Stripe); Stripe ops may exceed; email delivery within 2 minutes
- Parent booking acceptance criteria + fallback:
  - Success requires: Stripe customer + default payment method on file; atomic reservation of fixed slot; Stripe subscription/invoice created per chosen frequency; confirmation email sent
  - Failure handling: if any required step fails, keep slot in provisional reserved state for 2 weeks with clear actions for payee/admin; if unresolved, admin verifies and slot reverts to available
- Concurrency edge case: lock slot at selection; first transaction completes; second gets "slot no longer available"; do not create/charge Stripe objects for the second
- Interfaces (MVP): admin web UI + minimal parent web UI (self-booking/payments); Supabase Auth with email verification; no native apps
- MVP Emails (confirmed):
  1) Booking confirmation to parent: student, teacher, fixed day/time, payment frequency, cancellation policy link
  2) Provisional booking notice to parent: actions required (Stripe setup, etc.), 2-week expiry
  3) No-show notice to parent: make-up eligibility info per semester rules
  4) Make-up slots available email to parent: unique booking link scoped to student’s regular day/time within designated make-up week(s)
  5) Make-up confirmation to parent
  6) Admin alert: failed Stripe setup or expired provisional hold
- Admin dashboard (MVP, confirmed):
  1) Today’s lessons: teacher, student, time, status; actions: mark attendance/no‑show
  2) Upcoming week schedule overview per teacher
  3) Provisional bookings aging list with days remaining and action links
  4) No‑show incidents this week with make‑up eligibility flags
  5) Payments status feed from Stripe: recent succeeded/failed events
  6) Open make‑up slots utilization per semester
- Data retention & privacy (MVP):
  - Active customer PII: retain indefinitely while account is active
  - Upon account closure: retain invoices/financial links for 7 years
  - Attendance/booking records: anonymize after 24 months
  - Parent rights: allow data deletion requests; financial records exempted due to legal retention; document process to export and delete/anonymize
- Constraints & assumptions (MVP, confirmed):
  - Single location/timezone: BC
  - English-only UI
  - Start with one teacher; support multiple teachers
  - Refunds/credits handled manually (no automation in MVP)
- Payment frequency mapping and start rules:
  - Month-to-month: Stripe monthly subscription; start date = first of month
  - Yearly with monthly installments: school-year Stripe subscription with monthly billing; start date = school-year start
    - If today &gt; school-year start: school-year option not available (admin can override)
  - Semester lump sum: one-time Stripe invoice per semester; start date = semester start
    - If semester start &lt; today: semester option not available (admin can override)
  - If first lesson &gt; first week of month: charge full month; admin may issue manual credits
- Yearly plan specifics:
  - Collect first and last month at signup
  - Remaining payments stretched over 9 months
  - One month retained as compensation if plan is cancelled; otherwise applied to the final month and no payment collected then
  - If user cancels while on Month-to-month or Semester plan, no credit is issued
- Yearly plan Stripe implementation (confirmed):
  - At signup: charge first + last month immediately (two charges)
  - Then: schedule 9 monthly installments
  - Cancellation: retain last-month charge as compensation
  - If not cancelled: apply last-month charge to final month automatically
  - Month-to-month: bill on the 1st of each month
  - Semester: single invoice at semester start