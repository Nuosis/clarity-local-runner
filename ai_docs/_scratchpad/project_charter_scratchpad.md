# Cedar Heights Music Academy - Project Charter Scratchpad

## Initial Requirements Captured
- **Project Name:** Cedar Heights Music Academy Backend
- **Scale:** Small music school
  - 1-5 teachers
  - 20-100 students
- **Key Principle:** Simplicity and stability over complexity and robustness
- **Focus:** Small-load optimization
- **Status:** New school starting from scratch (no legacy systems)
- **Instruments:** Piano, guitar, drums, and bass
- **Lesson Format:** Individual one-on-one lessons only
- **Payment Options:**
  - Yearly (school year, paid monthly installments)
  - Semester (lump sum payment)
  - Monthly (month-to-month)
- **Lesson Schedule:** 30-minute lessons, once per week
- **Users:**
  - Phase 1: Single user (Teacher/Owner)
  - Phase 2: Parents (view payments, pay, signup children)

## Core Features (MVP)
- Student enrollment and registration management
- Lesson scheduling (simplified day-of-week + timeslot system)
  - Teacher sets availability slots
  - Parents search/book available teaching slots
- Payment tracking and billing
  - Basic checkbook-style bookkeeping
  - Stripe integration for payment processing
  - Automated invoices/receipts generation
  - Online payment acceptance

## Technical Stack
- **Backend:** Python with FastAPI (already instantiated in /app/)
- **Architecture:** GenAI Launchpad workflow architecture (event-driven optional)
- **Database:** TBD (PostgreSQL likely for simplicity)
- **Payment:** Stripe API
- **Hosting:** Hetzner with Docker containers
- **Authentication:** TBD (JWT likely)

## Timeline
- **MVP Target:** 2 weeks (ASAP)
- **Priority:** Speed to market with core functionality
- **Approach:** Minimal viable features, iterate after launch

## Compliance Requirements (BC, Canada)
- **PIPEDA:** Personal Information Protection (consent for collection, secure storage)
- **BC PIPA:** Personal Information Protection Act (British Columbia)
- **Payment:** PCI DSS handled by Stripe (no card data stored locally)
- **Minors:** Parental consent for students under 18
- **Recommendations:**
  - SSL/TLS for all data transmission
  - Encrypted database for personal information
  - Clear privacy policy and terms of service
  - Audit trail for data access
  - Data retention policy

## Growth Expectations
- **Year 1:** Stay small (1-2 teachers, under 50 students)
- **Focus:** Prove the model, refine operations
- **System Design:** Built for current scale, not over-engineered

## Data Management Requirements

### Core Entities

#### Payee (Parent/Contracting School)
- payee_id (PK)
- name
- type (individual/organization)
- stripe_customer_id

#### Email
- email_id (PK)
- email_address
- is_verified
- is_primary

#### Phone
- phone_id (PK)
- phone_number
- phone_type (mobile/home/work)
- is_primary

#### Address
- address_id (PK)
- street_line_1
- street_line_2
- city
- province
- postal_code
- country

#### Payee_Emails
- payee_id (FK)
- email_id (FK)

#### Payee_Phones
- payee_id (FK)
- phone_id (FK)

#### Payee_Addresses
- payee_id (FK)
- address_id (FK)

#### Student
- student_id (PK)
- payee_id (FK)
- first_name
- last_name
- emergency_contact_name
- emergency_contact_phone
- emergency_contact_relationship

#### Teacher
- teacher_id (PK)
- first_name
- last_name
- credentials
- hourly_rate

#### Teacher_Emails
- teacher_id (FK)
- email_id (FK)

#### Teacher_Phones
- teacher_id (FK)
- phone_id (FK)

#### Instruments
- instrument_id (PK)
- name (piano/guitar/drums/bass)

#### Teacher_Instruments
- teacher_id (FK)
- instrument_id (FK)

#### Availability
- availability_id (PK)
- teacher_id (FK)
- day_of_week
- time_slot
- is_available

#### Service_Records (Lessons)
- service_id (PK)
- student_id (FK)
- teacher_id (FK)
- availability_id (FK)
- instrument_id (FK)
- payment_term (monthly/semester/yearly)
- start_date
- end_date
- status (active/completed/cancelled)

#### Payment_Records
- payment_id (PK)
- payee_id (FK)
- service_id (FK)
- amount
- stripe_transaction_id
- payment_date
- status

#### Invoices
- invoice_id (PK)
- payee_id (FK)
- amount
- due_date
- paid_date
- stripe_invoice_id

## Areas to Explore
- [x] Core business objectives
- [x] User roles and permissions
- [x] Key features needed
- [x] Technical constraints
- [x] Timeline and milestones
- [x] Compliance requirements
- [x] Growth considerations
- [x] Data management requirements

## Questions Queue
- Business model and revenue streams
- Core workflows (enrollment, scheduling, payments)
- Communication needs
- Reporting requirements
- Mobile/web access needs