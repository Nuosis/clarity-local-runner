# Product Requirements Document (PRD)
Cedar Heights Music Academy — MVP

Document version: 0.1  
Date: 2025-08-10  
Status: Draft for Review

1. Product Overview and Objectives
- Purpose: Deliver a minimal, stable backend-driven system to operate a music school’s core workflows: enrollment, fixed weekly lesson scheduling, and payment handling via Stripe, with an admin web UI and a minimal parent web UI for self-booking and payment setup. Target delivery in 2 weeks.
- Primary Objectives
  - Enable Admin to create/manage payees, students, teachers; publish fixed lesson slots; assign students; track attendance/no-shows; and manage make-up lessons.
  - Enable Parents to self-book from pre-published fixed weekly 30-minute slots and set up payment via Stripe with selected payment frequency.
  - Use Stripe as the system of record for payment objects and frequency; the app queries Stripe live and stores only link/identity references.
  - Achieve operational reliability aligned with the project charter’s NFRs.

2. Scope
2.1 In-Scope for MVP
- Admin Web UI:
  - Manage payees, students, teachers, instruments, teacher pay per lesson
  - Define teacher weekly availability; publish fixed 30-minute weekly timeslots
  - Assign students to published slots (conflict-safe, atomic)
  - Track attendance; mark no-shows; trigger make-up lesson flow
  - View dashboard for today’s lessons, upcoming week, provisional bookings aging, no-shows, Stripe payment status, make-up utilization
- Parent Web UI (minimal):
  - Account creation via Supabase Auth (email verification)
  - Browse/select teacher (if more than one exists), view published fixed 30-minute weekly slots, select a slot
  - Create Stripe Customer; add default payment method
  - Select service and payment frequency (from Stripe options) and complete booking flow
  - Receive email confirmations and instructions for provisional holds if prerequisites fail
- Payments and Billing:
  - Stripe is the source of truth for payment objects and payment frequency
  - Support three payment frequencies in MVP:
    - Month-to-month: monthly subscription; bills on the 1st
    - Yearly with monthly installments (school-year plan): charge first + last month at signup; 9 monthly installments scheduled; last month retained if cancelled, otherwise applied to final month
    - Semester lump sum: single invoice at semester start
  - Start date rules:
    - Month-to-month: first of month
    - School-year: school-year start date; if today > start, option unavailable (admin may override)
    - Semester: semester start date; if start < today, option unavailable (admin may override)
    - If first lesson > first week of month, full month is charged; admin may issue manual credits (no automation)
- Lesson Scheduling:
  - Fixed weekly, recurring, 30-minute lessons
  - One active weekly slot per student
  - Parents choose from pre-published fixed slots only (no ad-hoc times)
  - Conflict prevention with atomic booking
- Attendance, No-Shows, and Make-Up Lessons:
  - Admin marks attendance/no-shows per scheduled occurrence
  - Make-up lessons available only to students on Semester or Yearly plans
  - Admin defines specific make-up weeks per semester (Fall, Winter, Spring, Summer)
  - Make-up slot must align to student’s regular day/time window; once booked, no additional make-ups; if not used within defined weeks, it is forfeited
  - On no-show, system emails parent with make-up slot link (when eligible)
- Emails (MVP set):
  1) Booking confirmation to parent
  2) Provisional booking notice to parent (required actions; 2-week expiry)
  3) No-show notice to parent (make-up eligibility)
  4) Make-up slots available email to parent (unique booking link)
  5) Make-up confirmation to parent
  6) Admin alert (failed Stripe setup or expired provisional hold)
- Data Retention/Privacy:
  - Active customer PII retained while account active
  - Upon closure: retain invoices/financial links for 7 years
  - Attendance/booking anonymized after 24 months
  - Support parent deletion requests with legal exceptions for financial records (PIPEDA/BC PIPA aligned)

2.2 Out of Scope for MVP
- Native mobile apps
- Group lessons, events/recitals, complex calendar integrations
- Automated refunds/credits logic (manual handling only)
- Student progress tracking/grading
- Multi-location support
- Social logins (beyond Supabase email verification)

3. User Personas
- Admin (Teacher/Owner)
  - Goals: Publish/manage schedule; enroll students; ensure payments; track attendance/no-shows; operate smoothly day-to-day
  - Pain points: Administrative overhead; ensuring payment compliance; handling make-ups consistently
  - Capabilities: High; can perform manual overrides when needed
- Parent (Payee)
  - Goals: Quickly book lessons at a suitable time; set up payments; receive clear confirmations and policies
  - Pain points: Confusing scheduling; payment setup friction; unclear make-up rules
  - Capabilities: General consumer web proficiency; email-based account verification
- Student
  - Indirect user; receives lessons tied to parent/payee

4. User Journeys
4.1 Parent Self-Booking (MVP)
1) Create account (Supabase Auth; email verification)  
2) Select published 30-minute fixed weekly slot (pick teacher if multiple)  
3) Define student and instrument  
4) Select service & payment frequency (from Stripe)  
5) Create Stripe Customer (name = student; company = “{parentName} {studentName}”)  
6) Add default payment method in Stripe  
7) Agree to amount, payment frequency, and cancellation policy (consent stored)  
8) Atomic reservation of slot, create Stripe subscription/invoice per chosen frequency  
9) On success: store Stripe IDs on Student (and/or Enrollment); send confirmation email; update UI  
10) On failure at any required step: place slot in provisional reserved state (2 weeks), send email with required actions; if unresolved post-expiry, admin verification returns slot to available  
Concurrency: Lock at selection; first transaction wins; latecomer gets “slot no longer available”; no Stripe objects/charges for the second attempt.

4.2 Admin Core Workflow (MVP)
- Manage payees/students
- Add teacher records; define instruments taught; set pay per lesson
- Define teacher availability; publish fixed weekly slots
- Assign students to slots (atomic, conflict-safe)
- Initiate Stripe customer/payment method creation when missing (parent completes via Stripe)
- Mark attendance/no-shows; triggering make-up policy flow and emails as applicable

5. Functional Requirements
5.1 Authentication and Authorization
- F-Auth-1: Parent accounts via Supabase Auth with email verification
- F-Auth-2: Admin account(s) with elevated permissions (non-public)
- F-Auth-3: Only Admin can manage teachers, payees, students, and slots globally; Parents can manage their own student records and bookings

5.2 Teacher, Instrument, and Availability
- F-TI-1: Admin can create/update Teacher profiles and pay-per-lesson
- F-TI-2: Admin can assign instruments to Teachers
- F-TI-3: Admin can define weekly availability and publish fixed 30-minute recurring slots
- F-TI-4: System prevents overlapping/conflicting slots for the same teacher

5.3 Payees and Students
- F-PS-1: Admin can create/update Payee and linked Student records
- F-PS-2: Parent can create Student profiles under their Payee account
- F-PS-3: Store Stripe linkage fields on Student and/or Enrollment (customer_id, payment_method_id, subscription_id)

5.4 Scheduling and Enrollment
- F-SE-1: Parents can view published fixed weekly 30-minute slots and select one (no ad-hoc times)
- F-SE-2: One active weekly slot per student; enforce atomic booking and prevent conflicts/double-booking
- F-SE-3: Admin can manually assign students to slots following the same conflict rules
- F-SE-4: Track Enrollment (student → timeslot) and Attendance per occurrence

5.5 Attendance, No-Shows, and Make-Ups
- F-AM-1: Admin can mark attendance/no-shows for scheduled occurrences
- F-AM-2: On no-show, if student is on Semester or Yearly plan, system emails make-up info and link when make-up weeks are defined
- F-AM-3: Admin defines make-up weeks per semester; student can book one make-up in those windows aligned to their regular day/time
- F-AM-4: If make-up not used in designated weeks, it is forfeited; once a make-up is booked, no additional make-up is offered

5.6 Payments and Billing (Stripe as System of Record)
- F-PB-1: Month-to-month
  - Monthly subscription; bills on the 1st of each month
- F-PB-2: Yearly with monthly installments (school-year plan)
  - At signup: charge first + last month immediately (two charges)
  - Then: schedule 9 monthly installments
  - If cancelled mid-year: retain last-month charge as compensation
  - If not cancelled: last-month charge applies to the final month automatically
  - If today > school-year start: plan not available (admin override possible)
- F-PB-3: Semester lump sum
  - Single invoice at semester start
  - If semester start < today: option not available (admin override possible)
- F-PB-4: If first lesson > first week of month: full month is charged; admin may issue manual credits; no automation
- F-PB-5: The product uses live Stripe queries; local system stores only internal IDs and Stripe object IDs; no denormalized local cache
- F-PB-6: No automated refunds/credits in MVP; handled manually by Admin

5.7 Provisional Reservations and Failure Handling
- F-PR-1: If any required step fails (Stripe customer, default payment method, subscription/invoice creation, email send), place slot in provisional reserved state for 2 weeks
- F-PR-2: Send provisional booking notice to parent with required actions and expiry date
- F-PR-3: If unresolved at expiry, notify Admin; after admin verification, revert slot to available and notify parent
- F-PR-4: Concurrency: lock slot on selection; first completion wins; second fails cleanly with no Stripe side-effects

5.8 Emails (MVP)
- F-EM-1: Booking confirmation (to parent): student, teacher, fixed day/time, payment frequency, cancellation policy link
- F-EM-2: Provisional booking notice (to parent): actions required, 2-week expiry details
- F-EM-3: No-show notice (to parent): make-up eligibility info
- F-EM-4: Make-up slots available (to parent): unique booking link restricted to student’s regular day/time during defined make-up weeks
- F-EM-5: Make-up confirmation (to parent)
- F-EM-6: Admin alert: failed Stripe setup or expired provisional hold

6. Non-Functional Requirements (NFRs)
- NFR-1 Uptime: 95% for MVP
- NFR-2 Performance: p95 ≤ 500ms for core reads/writes excluding Stripe network calls; Stripe operations may exceed
- NFR-3 Email Delivery: within 2 minutes for transactional notifications
- NFR-4 Security/Compliance:
  - PIPEDA and BC PIPA-aligned privacy posture
  - TLS for all data in transit; no card details stored locally (PCI handled by Stripe)
- NFR-5 Maintainability: simple code structure, clear domain boundaries, minimal local state, Stripe live linking
- NFR-6 Observability: basic logging for booking attempts, Stripe API outcomes, email send results

7. Data Requirements and Model
7.1 Entities (Local)
- Payee
  - Attributes: id, name, email, phone, created_at, updated_at, status
- Student
  - Attributes: id, payee_id, name, instrument_id, teacher_pref_id (nullable), consent_policy_accepted_at, stripe_customer_id, stripe_default_payment_method_id, created_at, updated_at
- Teacher
  - Attributes: id, name, email (optional), pay_per_lesson, created_at, updated_at
- Instrument
  - Attributes: id, name (e.g., piano, guitar, drums, bass)
- Timeslot (published weekly slot)
  - Attributes: id, teacher_id, weekday (0-6), start_time, end_time, active_flag, created_at, updated_at
- Enrollment (student → timeslot)
  - Attributes: id, student_id, timeslot_id, start_date, status (active, provisional, cancelled), stripe_subscription_id (nullable), stripe_invoice_id (nullable), created_at, updated_at
- Attendance (per scheduled occurrence)
  - Attributes: id, enrollment_id, date, status (present, no_show), notes, created_at
- MakeUpRecord
  - Attributes: id, student_id, semester_id, status (available, booked, forfeited), booked_date (nullable), created_at, updated_at
- Semester
  - Attributes: id, name (Fall/Winter/Spring/Summer), start_date, end_date, created_at, updated_at

7.2 Stripe Linkage and Strategy
- Store stripe_customer_id and stripe_default_payment_method_id on Student (or Payee if business rules change later)
- Store stripe_subscription_id and/or stripe_invoice_id on Enrollment where relevant
- Live Stripe queries for operations; avoid local denormalized cache

7.3 Data Lifecycle and Retention
- Active PII retained while account active
- Upon account closure: retain invoices/financial links for 7 years
- Attendance/booking records anonymized after 24 months
- Support data export and deletion/anonymization requests with legal exceptions

8. Interface Requirements
- Admin Web UI:
  - Manage entities (Teachers, Instruments, Payees, Students)
  - Publish weekly fixed timeslots
  - Assign students to slots; mark attendance/no-shows
  - Dashboard:
    1) Today’s lessons (teacher, student, time, status; mark attendance/no-show)
    2) Upcoming week schedule overview per teacher
    3) Provisional bookings aging with days remaining
    4) No-show incidents this week with make-up eligibility flags
    5) Stripe payment status feed (recent succeeded/failed)
    6) Open make-up slots utilization per semester
- Parent Web UI (minimal):
  - Supabase Auth signup/login with email verification
  - Select teacher (if multiple); choose from published fixed weekly slots
  - Define student + instrument
  - Select service/payment frequency
  - Stripe customer/payment method setup
  - Booking confirmation or provisional state with instructions

9. Constraints and Assumptions
- Single location/timezone (BC)
- English-only UI for MVP
- Start with one teacher but support multiple
- Refunds/credits managed manually by Admin (no automation)
- “Scheduling” strictly refers to lessons; “Payment frequency” refers to billing cadence (Stripe)

10. Acceptance Criteria
10.1 Parent Booking Flow Success (Happy Path)
- AC-Parent-1: Parent account verified via email (Supabase)
- AC-Parent-2: Parent selects published fixed weekly 30-min slot and teacher (if multiple); system locks slot
- AC-Parent-3: Student record created with instrument and consent to cancellation policy recorded
- AC-Parent-4: Stripe customer created; default payment method added
- AC-Parent-5: Stripe subscription or invoice created per selected payment frequency and start rules
- AC-Parent-6: Enrollment created; slot reserved atomically to student; Stripe IDs stored
- AC-Parent-7: Confirmation email sent; Parent UI shows confirmed booking

10.2 Parent Booking Flow Failure and Provisional State
- AC-Parent-Prov-1: If any required step fails, a provisional reservation is created with a 2-week expiry
- AC-Parent-Prov-2: Provisional email sent with required actions; Admin dashboard reflects aging
- AC-Parent-Prov-3: If unresolved at expiry, Admin alert sent; upon admin verification, slot reverts to available; parent notified

10.3 Concurrency
- AC-Con-1: Simultaneous attempts on the same slot result in one success and one failure with a clear “slot no longer available” message; no Stripe objects or charges created for the failing attempt

10.4 Attendance and Make-Ups
- AC-AM-1: Admin can mark attendance/no-show per occurrence
- AC-AM-2: Eligible no-shows (Semester/Yearly) trigger make-up email with unique link
- AC-AM-3: Make-up booking restricted to defined make-up weeks and aligned to student’s regular day/time; once booked, no additional make-ups; if not used within window, forfeited

10.5 Payments and Frequencies
- AC-Pay-1: Month-to-month: subscription bills on the 1st; handles full charge if first lesson > first week of month (manual credit possible)
- AC-Pay-2: Yearly: first + last charged at signup; 9 monthly installments scheduled; retain last month if cancelled; otherwise apply to final month
- AC-Pay-3: Semester: single invoice at semester start
- AC-Pay-4: Availability gating based on start dates, with admin override capability

11. Prioritization
- P0 (Must-have):
  - Admin CRUD for Teachers/Payees/Students/Instruments
  - Publish fixed weekly 30-min slots; conflict-safe atomic bookings
  - Parent self-booking flow with Stripe setup and confirmations/provisional handling
  - Attendance/no-show tracking; make-up rules and emails
  - Stripe live integration and linkage fields
  - Dashboard core widgets (today’s lessons; provisional aging; payment feed)
  - Core email templates (1–6)
- P1 (Should-have):
  - Upcoming week schedule overview; make-up utilization per semester
  - Teacher utilization metrics (basic)
- P2 (Nice-to-have / Post-MVP):
  - Social logins
  - Advanced reporting and analytics
  - Automated refund/credit workflows
  - Multi-language support
  - Group lessons/events

12. Edge Cases and Error Scenarios
- E-1: Concurrency on slot booking — lock and first-wins behavior; clean failure for others
- E-2: Stripe network/API errors — retry with backoff on server; surface provisional state when blocking
- E-3: Email provider delays — queue send and monitor; surface status in logs/UI
- E-4: Parent abandons Stripe payment method step — provisional handling persists with clear parent/admin prompts
- E-5: Parent attempts ineligible plan after start date — inform of ineligibility; offer admin contact/override path

13. Implementation Notes
- Tech Stack (per charter):
  - Backend: Python + FastAPI
  - DB: PostgreSQL
  - Auth: Supabase Auth (parents)
  - Payments: Stripe
  - Hosting: Hetzner + Docker
- Data Boundaries:
  - Local DB stores operational scheduling entities and linkage to Stripe
  - Stripe is authoritative for payment frequency/objects
  - No local denormalized payment cache; use live Stripe queries
- Observability:
  - Log booking transitions (selected → locked → confirmed/provisional/released)
  - Log Stripe calls and outcomes; correlate with user/session IDs
  - Log email send outcomes

14. Compliance and Privacy
- PIPEDA and BC PIPA aligned handling of PII
- TLS for all traffic; minimal PII stored; no card data at rest
- Data retention as specified (7 years for financial links; anonymize attendance/booking after 24 months)
- Document admin process for data access/export/deletion requests

15. Open Questions and Future Considerations
- Teacher notifications (email/SMS) for new bookings and daily schedule — post-MVP
- Parent ability to view/manage upcoming lessons and payment info — incremental improvements post-MVP
- Self-serve cancellations/withdrawals and automated policy enforcement — post-MVP

Appendix A — Email Template Minimum Content
- Booking Confirmation (Parent)
  - Subject: Lesson Confirmed — {Student} with {Teacher} on {Weekday} {Time}
  - Body: Student, Teacher, Day/Time, Start date, Payment frequency summary, Cancellation policy link, Contact info
- Provisional Booking Notice (Parent)
  - Subject: Action Required — Complete Your Lesson Booking
  - Body: Steps outstanding (Stripe customer/payment method and/or frequency selection), 2-week expiry date, link to resume, support contact
- No-Show Notice (Parent)
  - Subject: Attendance Update — No-Show Recorded for {Student}
  - Body: Date/time missed, eligibility for make-up (if any), link to info/policy
- Make-Up Slots Available (Parent)
  - Subject: Make-Up Lesson Slots Available for {Student}
  - Body: Window (semester make-up weeks), link to unique booking page constrained to regular day/time
- Make-Up Confirmation (Parent)
  - Subject: Make-Up Lesson Confirmed — {Date/Time}
  - Body: Date/time, teacher, location/online details if applicable
- Admin Alert (Internal)
  - Subject: Booking Requires Attention — {Student}/{Parent}
  - Body: What failed (Stripe setup, provisional expired), days left/expired status, actionable link in admin UI

Appendix B — Acceptance Test Checklist (Sample)
- Parent self-booking happy path completes with:
  - Slot lock → Stripe customer + default payment method → subscription/invoice creation → Enrollment write → Confirmation email
- Failure at any step results in provisional reservation, email, and dashboard entry
- Concurrency test with two parents selecting the same slot: one confirm, one graceful failure, no stray Stripe objects
- Admin can mark no-show and eligible parent receives make-up link; make-up booking adheres to semester and time alignment rules

End of Document