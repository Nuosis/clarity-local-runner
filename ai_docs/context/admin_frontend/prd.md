# Cedar Heights Music Academy — Admin CRM System Product Requirements Document

## Executive Summary

Cedar Heights Music Academy requires a comprehensive Customer Relationship Management (CRM) system to support the operational needs of a solo-managed music school. This authenticated frontend admin system will serve two primary user types: the owner/teacher (management) and parents/payees, providing essential tools for lesson management, communication, financial tracking, and business operations.

**Primary Business Outcome:** Enable efficient solo-preneur management of a growing music school through automation and streamlined workflows, reducing administrative overhead by 60% while supporting scalable growth from startup to established academy.

**Timeline:** MVP delivery within 3-6 months with phased feature rollout based on immediate business impact.

## Product Vision and Objectives

**Vision:** Create a lean, efficient CRM system that empowers a solo music school owner to manage all aspects of their business without administrative burden, while providing excellent service to students and parents.

**Primary Objectives:**
1. **Administrative Efficiency:** Reduce time spent on routine administrative tasks by 60%
2. **Operational Automation:** Eliminate manual scheduling conflicts and payment tracking errors
3. **Communication Streamlining:** Automate student communication and semester renewal processes
4. **Scalability Support:** Enable business growth from startup to 100+ students with same administrative capacity

**Success Metrics:**
- **Time Savings:** Reduce weekly administrative hours from 15+ to under 6 hours
- **Error Reduction:** Eliminate scheduling conflicts and payment discrepancies
- **User Adoption:** 90%+ active usage rate within 30 days of launch
- **System Reliability:** 99%+ uptime with sub-2-second response times

## User Personas

### Primary Persona: Owner/Teacher (Management)
- **Role:** Solo music school owner and primary instructor
- **Goals:** 
  - Minimize administrative overhead
  - Automate repetitive tasks
  - Maintain clear oversight of business operations
  - Focus time on teaching rather than administration
- **Pain Points:**
  - Manual scheduling and conflict resolution
  - Payment tracking and financial reporting
  - Student communication and progress tracking
  - Semester renewal management
- **Technical Comfort:** Moderate to high
- **Access Level:** Full administrative access to all system features

### Secondary Persona: Parents/Payees
- **Role:** Parents or guardians responsible for student enrollment and payments
- **Goals:**
  - Easy access to lesson schedules
  - Clear payment history and outstanding balances
  - Direct communication with teacher
  - Track student progress
- **Pain Points:**
  - Lack of visibility into lesson schedules
  - Unclear payment status
  - Difficulty communicating with teacher
  - No insight into student progress
- **Technical Comfort:** Variable (design for low to moderate)
- **Access Level:** Limited access to their own student data and communication

### Future Persona: Additional Teachers (Staff)
- **Role:** Future hired teachers as business scales
- **Goals:** Manage assigned student rosters, record attendance, communicate with parents
- **Implementation:** Architecture should support but not implement in MVP
- **Access Level:** Limited to assigned students and basic administrative functions

## System Integration and Enrollment Flow

### Enrollment Handoff Process
1. **Public Website Enrollment:** User completes enrollment on public site with:
   - Instrument selection
   - Preferred timeslot selection
   - Student information (name, age)
   - Payee contact information
2. **Secure Handoff:** Public site calls admin system with JWT (shared secret) containing enrollment data
3. **Account Creation:** Admin system automatically:
   - Creates Supabase auth account using payee email
   - Sets selected timeslot to "pending" status
   - Validates payment method via Stripe (no charge yet)
   - Schedules demo lesson
4. **Payment Processing:** 
   - Payment method validated but not charged until teacher confirms timeslot
   - Upon confirmation: charge prorated monthly rate
   - Monthly billing begins 1st of next month, continues until semester end

### Student Lifecycle Management
- **Semester Renewal:** 1 month prior to semester end
  - Automated email to payees requesting timeslot renewal
  - Weekly reminders until secured
  - 2 weeks before semester end: timeslot offered to waitlist
  - 48-hour final notice before release
- **Teacher Override:** Teachers can "secure for payee" during attendance in final month
- **Admin Alerts:** Dashboard shows non-renewed students in last month of semester
- **Summer Break:** Similar renewal process with optional summer course offerings

## Core Functional Requirements

### 1. User Authentication and Management
- **Supabase Integration:** JWT-based authentication with role-based access control
- **User Roles:** Owner/Teacher (admin), Parent/Payee (limited)
- **Account Creation:** Automated via enrollment handoff
- **Password Management:** Standard reset/recovery flows
- **Session Management:** Secure session handling with appropriate timeouts

### 2. Lesson Scheduling and Management
- **Lesson Format:** 30-minute individual lessons only
- **Schedule Type:** Fixed weekly recurring timeslots
- **Conflict Detection:** Prevent double-booking and scheduling conflicts
- **Admin Schedule Component (Admin-Only):**
  - School-wide overview showing all teachers' schedules
  - Blocked times based on school hours of operation settings
  - Makeup week indicators in header when applicable
  - Display only makeup lessons during designated makeup weeks
  - Support both weekly and daily view modes
  - Conflict detection across all teachers and resources
- **Teacher Attendance Component (Teacher-Only):**
  - Display only lessons for the authenticated teacher's students
  - Show blocked times based on school operational hours and teacher availability
  - Quick attendance marking with makeup lesson eligibility indicators
  - Integration with teacher availability system
- **Teacher Availability Management (New Component):**
  - Day-based column layout for each available day of the week
  - Lesson slot management with start time (end time auto-calculated as +30min)
  - Student assignment (optional - can be null for open slots)
  - Validation rules preventing scheduling during school closure times
  - Cannot create conflicting time slots on same day
  - Must respect school hours of operation
- **Demo Lessons:** Special handling for initial demo lesson scheduling
- **Timeslot Management:**
  - Mark timeslots as available/pending/confirmed
  - Handle timeslot transitions during enrollment
  - Waitlist management for released timeslots

### 3. Payment Processing and Financial Management
- **Stripe Integration:** Payment method validation and processing
- **Billing Cycles:** 
  - Prorated initial charge upon timeslot confirmation
  - Monthly billing on 1st of month
  - Semester-based billing periods
- **Payment Tracking:** 
  - Payment history for all users
  - Outstanding balance tracking
  - Automated payment processing
- **Financial Reporting:**
  - Revenue tracking and analytics
  - Payment status dashboards
  - Semester financial summaries

### 4. Communication System
- **Internal Messaging:** Direct communication between teachers and parents
- **Automated Notifications:**
  - Semester renewal reminders
  - Payment confirmations and failures
  - Schedule changes and updates
- **Email Integration:** Automated email sending for key events
- **Communication History:** Searchable message history and audit trail

### 5. Student Progress Tracking
- **Lesson Notes:** Teacher notes for each lesson
- **Progress Assessments:** Periodic skill and progress evaluations
- **Parent Visibility:** Parents can view progress updates and lesson notes
- **Historical Tracking:** Long-term progress tracking across semesters

### 6. Administrative Dashboard
- **Business Metrics:** 
  - Active student count
  - Revenue tracking
  - Attendance rates
  - Renewal rates
- **Alerts and Notifications:**
  - Non-renewed students approaching deadline
  - Payment failures
  - Scheduling conflicts
- **Quick Actions:** Common administrative tasks accessible from dashboard
- **Calendar Overview:** Visual representation of lesson schedules

### 7. Application Configuration Management
- **Academic Year Calendar:**
  - Define school year starting in September
  - Configure semester start/end dates following academic calendar
  - Support multiple semesters per academic year (Fall, Winter, Spring)
  - Holiday and break period management
  - **Makeup Week Configuration:** **REQUIRED** - Define designated makeup lesson week (Sun-Sat dates) for each semester
- **Makeup Lesson Policy Management:**
  - Configure makeup week dates for each semester (mandatory field)
  - Enforce one makeup lesson per student per semester maximum
  - No refunds for additional missed lessons beyond makeup week allocation
  - System validation to prevent makeup lesson scheduling outside designated weeks
- **Pricing Configuration:**
  - Set monthly lesson rates per instrument/skill level
  - Configure billing frequency options (monthly, semester, yearly)
  - Manage pricing tiers and promotional rates
- **Timeslot Templates:** Manage available teaching time windows
- **System Settings:** Core business rules and operational parameters

### 8. Enhanced Communication System
- **Email Management:**
  - Send emails directly to parents/payees from within system
  - Track email delivery status and read receipts
  - Email response tracking and threading
- **Gmail Integration:**
  - Ingest emails from connected Gmail account
  - Automatically assign incoming emails to correct payee/parent
  - Parse and categorize email content for context
- **Document Management:**
  - Generate and issue Agreement Forms (PDF) for new payees/parents
  - Automated document delivery via email

### 9. Advanced Financial Management and Reporting
- **Income Statement Generation:**
  - Monthly income statements in Excel format
  - Automated profit and loss calculations
  - Revenue categorization by lesson type/student
- **Profit and Loss Reporting:**
  - Monthly P&L reports with zero balance (profit = owner income)
  - Year-end financial summary for tax preparation
  - Expense tracking and categorization
  - Revenue trend analysis
- **Export Capabilities:**
  - Excel spreadsheet generation via backend
  - CSV export for external accounting software
  - Formatted reports for year-end tax preparation
- **Future Integration Planning:**
  - Architecture prepared for QuickBooks Online (QBO) integration
  - Standard accounting data formats and structures

## Non-Functional Requirements

### Performance Requirements
- **Response Time:** Sub-2-second page load times for all user interactions
- **Scalability:** Support 100+ concurrent users without performance degradation
- **Database Performance:** Optimized queries for lesson scheduling and payment tracking
- **Mobile Responsiveness:** Full functionality on mobile devices

### Security Requirements
- **Authentication:** Secure JWT-based authentication via Supabase
- **Data Protection:** Encryption of sensitive data (payment info, personal details)
- **Access Control:** Role-based permissions with principle of least privilege
- **Audit Trail:** Logging of all administrative actions and data changes
- **PIPEDA Compliance:** Canadian privacy law compliance for student/parent data

### Reliability Requirements
- **Uptime:** 99%+ availability target
- **Data Backup:** Automated daily backups with point-in-time recovery
- **Error Handling:** Graceful degradation and meaningful error messages
- **Payment Security:** PCI DSS compliance through Stripe integration

### Usability Requirements
- **Intuitive Interface:** Minimal training required for both user types
- **Accessibility:** WCAG 2.1 AA compliance for inclusive access
- **Consistent Design:** Unified design language across all interfaces
- **Help System:** Contextual help and documentation

## Technical Architecture

### Technology Stack
- **Frontend:** React with TypeScript
- **Styling:** CSS/SCSS with component-based architecture
- **State Management:** Redux
- **Authentication:** Supabase Auth with JWT tokens
- **Database:** Supabase (PostgreSQL)
- **Payment Processing:** Stripe API integration
- **Hosting:** Vercel or similar low-cost hosting
- **Email:** Transactional email service (Brevo) + email status insight (delivery)
- **Document Generation:** Server-side PDF generation (jsPDF, Puppeteer, or similar)
- **Spreadsheet Generation:** Backend Excel generation (ExcelJS, xlsx, or similar)

### Integration Points
- **Public Website:** JWT-based enrollment handoff
- **Supabase:** User authentication and data storage
- **Stripe:** Payment processing and subscription management
- **Email Service:** Transactional email service for notifications and communications
- **Gmail API:** Email ingestion and automatic assignment to payees
- **PDF Generation:** Server-side PDF creation for agreements and reports
- **Excel Generation:** Backend Excel file generation for financial reports

### Data Model (Key Entities)
- **Users:** Owner/Teacher, Parents/Payees with role-based access
- **Students:** Student profiles linked to payee accounts
- **Teacher Availability:** Day-based availability definitions with lesson slots
  - Available days of the week (column-based structure)
  - Lesson slots with start time, duration (+30min), and student assignment
  - Validation rules for school hours and conflict prevention
- **Timeslots:** Available teaching slots with status tracking
- **Lessons:** Individual lesson instances with attendance and notes
- **Schedule (Admin View):** School-wide schedule overview
  - All teachers' lessons with blocked times
  - Makeup week indicators and makeup lesson display
  - Conflict detection across all resources
- **Attendance (Teacher View):** Teacher-specific attendance tracking
  - Filtered to authenticated teacher's students only
  - Integration with teacher availability and school hours
- **Makeup Lessons:** Special lesson instances scheduled during designated makeup weeks
- **Makeup Week Configuration:** Required semester-specific makeup week definitions (Sun-Sat dates)
- **Makeup Lesson Tracking:** Student makeup lesson eligibility and usage tracking per semester
- **Payments:** Payment records and billing history
- **Academic Years:** School year definitions (September start)
- **Semesters:** Academic periods within school years with configurable dates and mandatory makeup weeks
- **School Hours Configuration:** Operational hours settings for blocked time calculations
- **Communications:** Message history and email threads between users
- **Email Integration:** Gmail message ingestion and payee assignment
- **Documents:** Agreement forms, contracts, and generated reports
- **Financial Records:** Income statements, P&L reports, and expense tracking
- **System Configuration:** Pricing, calendar settings, makeup lesson policies, and business rules

## MVP Feature Prioritization

### Phase 1: Foundation (Months 1-2)
**Priority 1 (Must Have):**
- User authentication and role management
- Basic lesson scheduling with conflict detection
- Student roster management
- Payment tracking (view-only initially)
- Simple communication system
- Enrollment handoff integration
- Academic year and semester configuration
- Basic pricing configuration

### Phase 2: Core Operations (Month 3)
**Priority 1 (Must Have):**
- Attendance tracking and lesson notes
- Automated payment processing
- Basic financial reporting
- Semester renewal workflow
- Administrative dashboard
- Agreement form generation (PDF)
- Email management and tracking

### Phase 3: Advanced Features (Months 4-6)
**Priority 2 (Should Have):**
- Gmail integration and email ingestion
- Advanced financial reporting (Excel P&L statements)
- Enhanced communication features with threading
- Progress tracking and reporting
- Document template management
- Mobile optimization

### Future Phases (Post-MVP)
**Priority 3 (Nice to Have):**
- Multi-teacher support
- QuickBooks Online (QBO) integration
- Advanced analytics and forecasting
- Digital signature collection
- Automated marketing tools
- Mobile app development

## Success Criteria and Acceptance Criteria

### MVP Launch Criteria
- [ ] All user types can authenticate and access appropriate features
- [ ] Enrollment handoff from public website functions correctly
- [ ] Teachers can manage student rosters and record lesson attendance
- [ ] Parents can view schedules and payment history
- [ ] Payment processing integration works end-to-end
- [ ] Basic communication system enables teacher-parent messaging
- [ ] Academic year and semester configuration system operational
- [ ] Pricing configuration allows monthly rate setting per instrument
- [ ] Agreement form generation (PDF) works for new payees
- [ ] Email management system tracks delivery and responses
- [ ] System performs within 2-second response time targets
- [ ] Mobile-responsive design functions on common devices
- [ ] Basic security measures implemented (HTTPS, secure authentication)
- [ ] Data backup and recovery procedures operational

### Success Validation Metrics
- [ ] 90%+ user adoption rate within 30 days of launch
- [ ] 60%+ reduction in administrative time measured after 3 months
- [ ] Zero critical security incidents in first 90 days
- [ ] System supports projected student growth without performance issues
- [ ] 95%+ successful payment processing rate
- [ ] Sub-2-second average response times maintained

## Risk Assessment and Mitigation

### High-Priority Risks
1. **Solo Developer Dependency**
   - *Risk:* Single point of failure for development and maintenance
   - *Mitigation:* Comprehensive documentation, simple architecture, gradual rollout

2. **Payment Processing Complexity**
   - *Risk:* Stripe integration challenges affecting revenue
   - *Mitigation:* Thorough testing, fallback procedures, Stripe support resources

3. **Data Privacy and Security**
   - *Risk:* Student/parent information exposure
   - *Mitigation:* PIPEDA compliance, secure authentication, regular security audits

4. **Enrollment Integration Failures**
   - *Risk:* Broken handoff from public website
   - *Mitigation:* Robust error handling, monitoring, manual fallback procedures

### Medium-Priority Risks
- **User Adoption Resistance:** Comprehensive onboarding and training materials
- **Scalability Issues:** Performance testing and optimization planning
- **Third-Party Service Outages:** Monitoring and status page communications

## Compliance and Regulatory Considerations

### Canadian Privacy Requirements (PIPEDA)
- Implement consent mechanisms for data collection
- Provide data access and deletion capabilities
- Secure data transmission and storage
- Maintain audit logs for data access

### Financial Record Keeping
- Maintain transaction records for tax purposes
- Implement data retention policies
- Ensure financial data accuracy and integrity

### Payment Card Industry (PCI DSS)
- Leverage Stripe's PCI compliance for payment processing
- Never store sensitive payment data locally
- Implement secure payment workflows

## Future Considerations

### Scalability Planning
- **Multi-Teacher Support:** Architecture designed to support multiple teachers
- **Location Expansion:** Potential for multiple teaching locations
- **Advanced Features:** Waitlist management, group lessons, recital planning

### Technology Evolution
- **Mobile App:** Native mobile applications for enhanced user experience
- **Advanced Analytics:** Business intelligence and predictive analytics
- **Integration Ecosystem:** Third-party integrations (calendar apps, accounting software)

---

*This PRD serves as the foundational document for the Cedar Heights Music Academy Admin CRM System development. All feature decisions and development priorities should align with the solopreneur efficiency criteria and business objectives outlined above.*