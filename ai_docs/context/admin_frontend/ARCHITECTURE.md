# Cedar Heights Music Academy - Admin CRM Frontend Architecture

## Executive Summary

This document defines the comprehensive system architecture for the Cedar Heights Music Academy Admin CRM frontend application. The system is designed as a React-based TypeScript application that serves as the administrative interface for managing a solo-operated music school, with a focus on efficiency, maintainability, and user experience.

**Key Architectural Decisions:**
- **Separate Repository Strategy**: Admin CRM frontend is one of three independent repositories (public frontend, admin CRM, backend)
- **REST API Integration**: All backend communication through centralized API with JWT authentication
- **Modern React Stack**: TypeScript + Material UI + TanStack Query + Zustand
- **Static Deployment**: Pure frontend application hosted on Vercel with no server-side logic

## Project Context and Business Objectives

### Primary Business Outcome
Enable efficient solo-preneur management of a growing music school through automation and streamlined workflows, reducing administrative overhead by 60% while supporting scalable growth from startup to established academy.

### Target Users
- **Owner/Teacher (Management)**: Full administrative access to all system features
- **Parents/Payees**: Limited access to their student data, schedules, and payments
- **Future Staff (Teachers)**: Role-based access to assigned students (architecture supports, not implemented in MVP)

### Success Metrics
- **Time Savings**: Reduce weekly administrative hours from 15+ to under 6 hours
- **Error Reduction**: Eliminate scheduling conflicts and payment discrepancies
- **User Adoption**: 90%+ active usage rate within 30 days of launch
- **System Reliability**: 99%+ uptime with sub-2-second response times

## System Architecture Overview

### Repository Structure
```
Cedar Heights Music Academy System:
├── Public Frontend (separate repo)
│   ├── Marketing website
│   ├── Enrollment configurator
│   └── Public teacher/timeslot discovery
├── Admin CRM Frontend (this repo)
│   ├── Authenticated admin interface
│   ├── Student/lesson management
│   └── Payment tracking and communication
└── Backend API (separate repo)
    ├── REST API endpoints
    ├── Supabase integration
    └── External service integrations
```

### Service Boundaries and Integration

**Admin CRM Frontend Responsibilities:**
- User interface for all administrative functions
- Client-side state management and caching
- Form validation and user input handling
- Real-time data presentation and updates

**Backend API Responsibilities:**
- Authentication and authorization
- Business logic and data validation
- Database operations via Supabase
- External integrations (Stripe, email services)

**Integration Pattern:**
- **Data Flow**: Frontend → Backend API → Database/External Services
- **Authentication**: JWT tokens issued by backend, managed by frontend
- **Communication**: RESTful API calls with JSON payloads

## Technical Stack and Dependencies

### Core Technologies
- **Language**: TypeScript
- **Framework**: React 19
- **Build Tool**: Vite
- **UI Library**: Material UI (chosen over Tailwind due to React 19 compatibility)
- **State Management**: TanStack Query + Zustand
- **Routing**: React Router DOM
- **HTTP Client**: Axios (via TanStack Query)

### State Management Architecture
- **Server State**: TanStack Query
  - API data caching and synchronization
  - Background refetching and optimistic updates
  - Built-in loading and error states
  - Automatic retry mechanisms
- **Client State**: Zustand
  - UI state (modals, forms, user preferences)
  - Authentication state (JWT tokens, user info)
  - Application-level state management

### Benefits of Technology Choices
- **Material UI**: Comprehensive component library, built-in theming, accessibility compliance
- **TanStack Query**: Excellent caching, background updates, optimistic updates
- **Zustand**: Lightweight, TypeScript-first, minimal boilerplate
- **TypeScript**: Type safety, better developer experience, reduced runtime errors

## Authentication and Security Architecture

### Authentication Flow
1. **Backend Integration**: REST API with centralized authentication (not direct Supabase client)
2. **Supabase Role**: Database + Auth provider for backend, not direct frontend integration
3. **Frontend Auth**: JWT tokens from backend API, managed by TanStack Query + Zustand
4. **Token Management**: Secure storage and automatic refresh handling

### Security Benefits
- **Better Security Separation**: Sensitive auth logic stays on server
- **Easier Testing**: Frontend doesn't need to mock Supabase directly
- **Centralized Business Logic**: All auth rules in one place
- **Flexibility**: Can easily switch auth providers later

### User Creation and Role Management
- **Automated Account Creation**: Via enrollment handoff from public site
- **Role-Based Access**: Owner/Teacher (admin), Parents/Payees (limited)
- **Secure Handoff**: JWT-based transfer from public site to admin system

## Feature Implementation Strategy

### MVP Phase 1 Features (All Critical)
- User authentication and role management
- **Admin-only Schedule component**: School overview with blocked times based on admin settings for hours of operation, makeup lesson week indicators, day view capability
- **Teacher-only Attendance component**: Display only teacher's students with blocked times based on school hours and teacher availability
- **Teacher Availability Management**: Day-based column layout for defining available days, lesson slots with start time (+30min duration), and student assignment
- Student roster management
- Payment tracking (view-only initially)
- Simple communication system
- Enrollment handoff integration
- Academic year and semester configuration with mandatory makeup week definition
- Makeup lesson policy enforcement and tracking
- Basic pricing configuration

## Component Architecture Changes

### Schedule Component (Admin-Only)
- **Purpose**: Provide school-wide overview for administrative management
- **Access**: Admin/Owner role only
- **Features**:
  - Display all teachers' schedules in unified view
  - Show blocked times based on school hours of operation settings
  - Indicate makeup lesson weeks in header when applicable
  - Display only makeup lessons during designated makeup weeks
  - Support both weekly and daily view modes
  - Conflict detection across all teachers and resources

### Attendance Component (Teacher-Only)
- **Purpose**: Lesson attendance tracking for individual teachers
- **Access**: Teacher role only (including dual Admin/Teacher users in teacher mode)
- **Features**:
  - Display only lessons for the authenticated teacher's students
  - Show blocked times based on school operational hours
  - Respect teacher's individual availability settings
  - Quick attendance marking with makeup lesson eligibility indicators
  - Integration with teacher availability system

### Teacher Availability Component (New)
- **Purpose**: Availability management system for teachers to define their working schedule
- **Access**: Teacher role (including dual Admin/Teacher users)
- **Architecture**:
  - **Column-based Layout**: Each available day of the week renders as a separate column
  - **Lesson Slot Management**: Teachers can add lesson slots with:
    - Start time (required) - end time automatically calculated as +30 minutes
    - Student assignment (optional - can be null for open slots)
    - Recurring weekly pattern
  - **Validation Rules**:
    - Cannot schedule during school closure times
    - Cannot create conflicting time slots on same day
    - Must respect school hours of operation
  - **Integration**: Feeds into both Schedule (admin view) and Attendance (teacher view) components

### Removed Components
- **Makeup Lessons Component**: Functionality integrated into Schedule and Attendance components
- Makeup lesson management now handled within the context of regular scheduling
- Policy enforcement remains through existing makeup policy system

### Revised Implementation Order (Revenue-Focused)
1. **Foundation Layer**: Auth + User roles + Basic data models
2. **Revenue-Critical**: Enrollment handoff + Student roster + Payment tracking (view-only)
3. **Core Operations**: Lesson scheduling + Conflict detection
4. **User Experience**: Communication + Configuration management

### Implementation Rationale
- Prioritize enrollment handoff early for immediate revenue generation
- Student roster needed to support enrollment processing
- Payment tracking provides cash flow visibility from day 1
- Lesson scheduling can build on established student data

## Error Handling and User Experience Patterns

### Comprehensive Error Handling Strategy
- **Notifications**: Material UI Snackbars for success/error/info messages
- **Crash Recovery**: React Error Boundaries with fallback UI and error reporting
- **API Errors**: TanStack Query built-in error states with retry mechanisms
- **Loading States**: Material UI Skeleton components and loading animations
- **Form Validation**: Real-time validation with clear error messages
- **Offline Handling**: TanStack Query background sync when connection restored
- **User Feedback**: Progress indicators for long operations, confirmation dialogs for destructive actions

### User Experience Principles
- **Graceful Degradation**: System continues to function even when components fail
- **Meaningful Error Messages**: Clear, actionable feedback for users
- **Progress Indicators**: Visual feedback for all long-running operations
- **Consistent Design**: Material UI design system ensures consistency
- **Accessibility**: WCAG 2.1 AA compliance through Material UI components

## Deployment and Infrastructure

### Hosting Strategy
- **Frontend Hosting**: Vercel (automatic deployments, static hosting only)
- **Benefits**: Perfect Vite integration, zero-config deployments, excellent DX
- **CI/CD**: Git-based deployments (push to main = deploy to production)
- **Environment Management**: Vercel environment variables for API endpoints
- **Architecture**: Pure static frontend, all server-side logic handled by separate backend
- **Cost**: Free tier suitable for MVP, scales with usage
- **No Edge Functions**: All functionality routed through dedicated backend API

### Deployment Benefits
- **Simpler Architecture**: Frontend is purely presentational
- **Better Security**: No server-side logic exposed in frontend
- **Easier Testing**: Clear boundaries between frontend and backend
- **Cost Effective**: Static hosting is cheaper and faster
- **Better Caching**: Static assets cache perfectly at CDN level

## Data Flow and API Integration

### Enrollment Handoff Requirements
- Secure JWT-based handoff from public site
- Automatic parent/payee account creation
- Timeslot reservation during enrollment
- Payment method validation (Stripe)
- Demo lesson scheduling

### API Communication Patterns
- **RESTful Endpoints**: Standard HTTP methods and status codes
- **JSON Payloads**: Consistent data format for all API communication
- **Error Handling**: Standardized error responses with user-friendly messages
- **Caching Strategy**: TanStack Query manages all API caching and synchronization
- **Optimistic Updates**: Immediate UI updates with rollback on failure

## Performance and Scalability Considerations

### Frontend Performance
- **Bundle Optimization**: Vite's built-in tree shaking and code splitting
- **Lazy Loading**: Route-based code splitting with React.lazy
- **Caching Strategy**: TanStack Query intelligent caching and deduplication
- **Memory Management**: Proper cleanup of event listeners and subscriptions
- **DOM Performance**: Material UI's optimized component rendering

### Scalability Architecture
- **Stateless Frontend**: No server-side state, scales horizontally
- **CDN Distribution**: Vercel's global CDN for fast content delivery
- **API Caching**: Backend handles data caching and optimization
- **Progressive Enhancement**: Core functionality works without JavaScript

## Security and Compliance

### Frontend Security Measures
- **JWT Token Management**: Secure storage and automatic refresh
- **Input Validation**: Client-side validation with server-side verification
- **XSS Prevention**: React's built-in XSS protection
- **HTTPS Everywhere**: All communication over secure connections
- **Content Security Policy**: Implemented via Vercel headers

### PIPEDA Compliance Considerations
- **Data Minimization**: Only collect and display necessary data
- **User Consent**: Clear consent mechanisms for data collection
- **Data Access**: Users can view and request deletion of their data
- **Audit Trails**: All data access and modifications logged

## Testing Strategy

### Testing Approach
- **Unit Testing**: Component and utility function testing
- **Integration Testing**: API integration and user workflow testing
- **End-to-End Testing**: Complete user journey validation
- **Accessibility Testing**: WCAG compliance verification
- **Performance Testing**: Core Web Vitals monitoring

### Testing Tools and Patterns
- **Jest + React Testing Library**: Component and integration testing
- **MSW (Mock Service Worker)**: API mocking for tests
- **Playwright**: End-to-end testing
- **Axe**: Accessibility testing
- **Lighthouse**: Performance monitoring

## Monitoring and Observability

### Frontend Monitoring
- **Error Tracking**: React Error Boundaries with error reporting
- **Performance Monitoring**: Core Web Vitals tracking
- **User Analytics**: Basic usage analytics (privacy-compliant)
- **API Monitoring**: TanStack Query error and performance metrics

### Development Tools
- **TypeScript**: Compile-time error detection
- **ESLint**: Code quality and consistency
- **Prettier**: Code formatting
- **Husky**: Git hooks for quality gates

## Future Considerations and Extensibility

### Planned Enhancements (Post-MVP)
- **Multi-teacher Support**: Role-based access for additional staff
- **Advanced Analytics**: Business intelligence and reporting
- **Mobile App**: React Native application using shared business logic
- **Offline Support**: Progressive Web App capabilities

### Architecture Flexibility
- **Modular Design**: Easy to add new features and modules
- **API-First**: Backend changes don't require frontend modifications
- **Component Library**: Reusable UI components for consistency
- **State Management**: Zustand's simplicity allows easy feature additions

## Development Guidelines and Best Practices

### Code Quality Standards
- **TypeScript**: Strict type checking enabled
- **Component Design**: Single responsibility principle
- **Custom Hooks**: Reusable business logic extraction
- **Error Boundaries**: Graceful error handling at component level
- **Performance**: React.memo and useMemo for optimization

### File Structure and Organization
```
src/
├── components/          # Reusable UI components
├── pages/              # Route-level components
├── hooks/              # Custom React hooks
├── services/           # API service functions
├── stores/             # Zustand store definitions
├── types/              # TypeScript type definitions
├── utils/              # Utility functions
└── constants/          # Application constants
```

### Development Workflow
- **Feature Branches**: Git flow with pull request reviews
- **Automated Testing**: CI/CD pipeline with test gates
- **Code Reviews**: Peer review for all changes
- **Documentation**: Inline comments and README updates

## Conclusion

This architecture provides a solid foundation for the Cedar Heights Music Academy Admin CRM frontend, balancing developer efficiency with user experience and system reliability. The chosen technologies and patterns support the solo-developer model while providing room for future growth and enhancement.

The architecture emphasizes:
- **Developer Efficiency**: Modern tooling and minimal configuration
- **User Experience**: Professional UI with comprehensive error handling
- **Maintainability**: Clean separation of concerns and modular design
- **Scalability**: Stateless frontend with efficient caching and performance optimization
- **Security**: Proper authentication and data protection measures

This foundation will enable the successful delivery of the MVP while supporting the long-term growth and evolution of the Cedar Heights Music Academy system.