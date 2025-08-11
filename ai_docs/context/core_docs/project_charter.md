# Cedar Heights Music Academy - Project Charter

## Executive Summary

Cedar Heights Music Academy is a new music school in British Columbia, Canada, starting operations with a focus on individual music instruction. The school requires a simple, stable backend system to manage student enrollment, lesson scheduling, and payment processing. This project will deliver a minimal viable product (MVP) within 2 weeks to enable immediate operations.

## Project Vision

To create a streamlined, user-friendly backend system that enables Cedar Heights Music Academy to efficiently manage their music education services while maintaining simplicity and stability over complex features.

## Business Objectives

### Primary Goals
1. **Enable Digital Operations**: Transition from manual processes to a digital platform for managing the music school
2. **Streamline Administration**: Reduce administrative overhead through automation of scheduling, billing, and enrollment
3. **Ensure Payment Security**: Implement secure payment processing through Stripe integration
4. **Support Growth**: Build a foundation that can accommodate controlled growth (1-2 teachers, up to 50 students in Year 1)

### Success Metrics
- Successfully enroll and manage 20+ students within first month
- Process all payments electronically through the system
- Reduce administrative time by 50% compared to manual processes
- Achieve 95% uptime for critical operations

## Stakeholder Analysis

### Primary Stakeholders
- **Teacher/Owner**: Primary system user managing all operations initially
- **Parents**: Will access system to view payments, make payments, and register children (Phase 2)
- **Students**: Indirect beneficiaries receiving music instruction

### User Roles
1. **Phase 1**: Single admin user (Teacher/Owner) with full system access
2. **Phase 2**: Parent portal for payment and enrollment management

## Project Scope

### In Scope - MVP Features

#### 1. Student Enrollment & Registration
- Manage student profiles linked to payees (parents or contracting schools)
- Track basic student information and emergency contacts
- Assign students to teachers and instruments

#### 2. Lesson Scheduling
- Simplified day-of-week + timeslot scheduling system
- Teacher availability management
- Parent-accessible booking for available slots
- Support for 30-minute weekly lessons

#### 3. Payment & Billing
- Checkbook-style bookkeeping system
- Stripe integration for payment processing
- Support for multiple payment terms:
  - Yearly (school year with monthly installments)
  - Semester (lump sum)
  - Monthly (month-to-month)
- Automated invoice and receipt generation

### Out of Scope
- Group lessons or workshops
- Complex calendar integration
- Student progress tracking or grading
- Recital/event management
- Practice room booking
- Multi-location support

## Technical Architecture

### Technology Stack
- **Backend Framework**: Python with FastAPI (existing codebase in /app/)
- **Database**: PostgreSQL
- **Payment Processing**: Stripe API
- **Authentication**: JWT-based authentication
- **Hosting**: Hetzner with Docker containers
- **Architecture Pattern**: Optional event-driven using GenAI Launchpad workflow

### Data Architecture

The system will implement a normalized relational database structure with the following core entities:

#### Contact Information Tables
- **Email**: Centralized email storage with verification status
- **Phone**: Phone numbers with type classification
- **Address**: Full address details for Canadian format

#### Business Entities
- **Payee**: Parents or contracting schools responsible for payment
- **Student**: Individual students linked to payees
- **Teacher**: Instructors with credentials and rates
- **Instruments**: Available instruments (piano, guitar, drums, bass)
- **Availability**: Teacher schedule slots
- **Service_Records**: Active lesson enrollments
- **Payment_Records**: Transaction history
- **Invoices**: Billing records

#### Relationship Tables
- Payee_Emails, Payee_Phones, Payee_Addresses
- Teacher_Emails, Teacher_Phones
- Teacher_Instruments

## Compliance & Security

### Regulatory Requirements
- **PIPEDA**: Federal privacy law compliance
- **BC PIPA**: Provincial privacy law compliance
- **PCI DSS**: Handled through Stripe (no local card storage)

### Security Measures
- SSL/TLS encryption for all data transmission
- Encrypted database for personal information
- Parental consent workflow for minors
- Comprehensive audit trail for data access
- Clear privacy policy and terms of service
- Defined data retention policies

## Project Constraints

### Timeline
- **MVP Delivery**: 2 weeks from project start
- **Approach**: Minimal viable features with post-launch iteration

### Technical Constraints
- Optimize for small load (1-5 teachers, 20-100 students)
- Prioritize simplicity and stability over feature complexity
- Leverage existing FastAPI project structure

### Resource Constraints
- Single developer/owner initially
- Limited budget requiring cost-effective solutions
- Must be maintainable by small team

## Risk Assessment

### High Priority Risks
1. **Timeline Risk**: 2-week deadline is aggressive
   - *Mitigation*: Focus on absolute minimum features, defer nice-to-haves
   
2. **Payment Integration**: Stripe setup and testing complexity
   - *Mitigation*: Use Stripe's well-documented APIs and test mode

3. **Data Privacy**: Handling minor's information
   - *Mitigation*: Implement proper consent workflows and encryption

### Medium Priority Risks
1. **Scalability**: System may need updates if growth exceeds expectations
   - *Mitigation*: Design with clean architecture for future refactoring

2. **User Adoption**: Parents may need training on system use
   - *Mitigation*: Create simple, intuitive interfaces

## Implementation Approach

### Development Methodology
- Agile/iterative development with daily progress reviews
- Test-driven development for critical features
- Continuous deployment via Docker

### Phase 1 (Week 1)
- Database schema implementation
- Core API endpoints for CRUD operations
- Teacher/Admin authentication
- Basic enrollment management

### Phase 2 (Week 2)
- Stripe payment integration
- Scheduling system
- Invoice generation
- Basic reporting
- Deployment and testing

### Post-Launch Iterations
- Parent portal access
- Enhanced scheduling features
- Performance optimizations
- Additional reporting capabilities

## Success Criteria

The project will be considered successful when:
1. System can register and manage student enrollments
2. Teachers can set availability and parents can book lessons
3. Payments can be processed through Stripe
4. System maintains 95% uptime
5. Basic operations require no technical support

## Next Steps

1. **Immediate Actions**:
   - Set up development environment
   - Initialize database schema
   - Configure Stripe test account
   - Create project task breakdown

2. **Stakeholder Actions**:
   - Provide Stripe account credentials
   - Confirm business rules and workflows
   - Review and approve UI mockups

3. **Technical Setup**:
   - Configure Hetzner hosting environment
   - Set up CI/CD pipeline
   - Implement monitoring and logging

## Approval

This project charter establishes the foundation for the Cedar Heights Music Academy backend system. Upon approval, development will commence immediately to meet the 2-week delivery timeline.

---

*Document Version*: 1.0  
*Date*: 2025-08-10  
*Status*: Pending Approval