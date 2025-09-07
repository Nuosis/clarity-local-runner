
# Cedar Heights Music Academy — API Endpoints Specification
## Phase 1.3 Core API Infrastructure Implementation

**Document Version:** 1.0  
**Created:** 2025-01-07  
**Phase:** 1.3 Core API Infrastructure  
**Status:** Ready for Implementation

## Executive Summary

This document provides a comprehensive specification of all API endpoints required for Phase 1.3 implementation of the Cedar Heights Music Academy backend system. The endpoints are organized by functional domains and include authentication requirements, request/response schemas, and core features needed to support the admin frontend, public website, and workflow-driven business processes.

**Key Implementation Principles:**
- **Performance Target**: <200ms response times for quick operations
- **Workflow Integration**: Support for GenAI Launchpad workflow orchestration
- **Role-Based Access**: ADMIN, TEACHER, PARENT role-based authorization
- **Type Safety**: Comprehensive Pydantic validation for all endpoints
- **Error Handling**: Structured error responses with meaningful messages

## Authentication & Authorization Framework

### Authentication Headers
All authenticated endpoints require:
```http
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

### Role-Based Access Control
- **ADMIN**: Full system access
- **TEACHER**: Access to assigned students and lessons
- **PARENT**: Access to own student data only
- **PUBLIC**: No authentication required

### Standard Response Format
```json
{
  "success": boolean,
  "data": object | array | null,
  "message": string,
  "errors": array | null,
  "metadata": {
    "timestamp": "ISO8601",
    "request_id": "uuid",
    "execution_time_ms": number
  }
}
```

## 1. Authentication & User Management

### 1.1 Authentication Endpoints

#### POST /api/auth/login
**Purpose**: Authenticate user with Supabase JWT  
**Access**: Public  
**Performance Target**: <200ms

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access_token": "jwt_token",
    "refresh_token": "refresh_token",
    "expires_in": 3600,
    "user": {
      "id": 1,
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "role": "parent",
      "is_active": true
    }
  },
  "message": "Login successful"
}
```

#### POST /api/auth/logout
**Purpose**: Invalidate user session  
**Access**: Authenticated  
**Performance Target**: <200ms

**Request:** Empty body

**Response:**
```json
{
  "success": true,
  "data": null,
  "message": "Logout successful"
}
```

#### POST /api/auth/refresh
**Purpose**: Refresh JWT token  
**Access**: Public (with refresh token)  
**Performance Target**: <200ms

**Request:**
```json
{
  "refresh_token": "refresh_token_here"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access_token": "new_jwt_token",
    "expires_in": 3600
  },
  "message": "Token refreshed"
}
```

#### GET /api/auth/me
**Purpose**: Get current user profile  
**Access**: Authenticated  
**Performance Target**: <200ms

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1-902-555-0123",
    "role": "parent",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z",
    "metadata": {}
  }
}
```

#### PUT /api/auth/profile
**Purpose**: Update user profile  
**Access**: Authenticated  
**Performance Target**: <200ms

**Request:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1-902-555-0123"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1-902-555-0123",
    "updated_at": "2024-01-01T12:00:00Z"
  },
  "message": "Profile updated successfully"
}
```

## 2. Student Management

### 2.1 Student CRUD Operations

#### GET /api/students
**Purpose**: List students with filtering and pagination  
**Access**: ADMIN (all), TEACHER (assigned), PARENT (own)  
**Performance Target**: <200ms

**Query Parameters:**
- `page`: integer (default: 1)
- `limit`: integer (default: 20, max: 100)
- `teacher_id`: integer (filter by teacher)
- `instrument`: string (filter by instrument)
- `is_active`: boolean (filter by active status)
- `search`: string (search by name)

**Response:**
```json
{
  "success": true,
  "data": {
    "students": [
      {
        "id": 1,
        "first_name": "Emma",
        "last_name": "Johnson",
        "email": "emma@example.com",
        "date_of_birth": "2015-03-15",
        "age": 8,
        "instrument": "piano",
        "skill_level": "beginner",
        "lesson_rate": 125.00,
        "enrollment_date": "2024-09-01",
        "is_active": true,
        "parent": {
          "id": 2,
          "first_name": "Sarah",
          "last_name": "Johnson",
          "email": "sarah@example.com",
          "phone": "+1-902-555-1234"
        },
        "teacher": {
          "id": 1,
          "first_name": "Michael",
          "last_name": "Smith",
          "email": "michael@cedarheights.com"
        },
        "stripe_customer_id": "cus_123456789",
        "created_at": "2024-09-01T10:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 45,
      "pages": 3,
      "has_next": true,
      "has_prev": false
    }
  }
}
```

#### GET /api/students/{student_id}
**Purpose**: Get student details  
**Access**: ADMIN (all), TEACHER (assigned), PARENT (own)  
**Performance Target**: <200ms

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "first_name": "Emma",
    "last_name": "Johnson",
    "email": "emma@example.com",
    "date_of_birth": "2015-03-15",
    "age": 8,
    "instrument": "piano",
    "skill_level": "beginner",
    "lesson_rate": 125.00,
    "enrollment_date": "2024-09-01",
    "is_active": true,
    "notes": "Enthusiastic learner, practices regularly",
    "parent": {
      "id": 2,
      "first_name": "Sarah",
      "last_name": "Johnson",
      "email": "sarah@example.com",
      "phone": "+1-902-555-1234"
    },
    "teacher": {
      "id": 1,
      "first_name": "Michael",
      "last_name": "Smith",
      "email": "michael@cedarheights.com",
      "instruments": ["piano", "guitar"]
    },
    "stripe_customer_id": "cus_123456789",
    "created_at": "2024-09-01T10:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z"
  }
}
```

#### POST /api/students
**Purpose**: Create new student  
**Access**: ADMIN only  
**Performance Target**: <200ms

**Request:**
```json
{
  "first_name": "Emma",
  "last_name": "Johnson",
  "email": "emma@example.com",
  "date_of_birth": "2015-03-15",
  "parent_id": 2,
  "teacher_id": 1,
  "instrument": "piano",
  "skill_level": "beginner",
  "lesson_rate": 125.00,
  "enrollment_date": "2024-09-01",
  "notes": "New student from enrollment workflow"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "first_name": "Emma",
    "last_name": "Johnson",
    "email": "emma@example.com",
    "date_of_birth": "2015-03-15",
    "parent_id": 2,
    "teacher_id": 1,
    "instrument": "piano",
    "skill_level": "beginner",
    "lesson_rate": 125.00,
    "enrollment_date": "2024-09-01",
    "is_active": true,
    "created_at": "2024-09-01T10:00:00Z"
  },
  "message": "Student created successfully"
}
```

#### PUT /api/students/{student_id}
**Purpose**: Update student information  
**Access**: ADMIN (all), TEACHER (assigned - limited fields)  
**Performance Target**: <200ms

**Request:**
```json
{
  "first_name": "Emma",
  "last_name": "Johnson",
  "email": "emma@example.com",
  "skill_level": "intermediate",
  "lesson_rate": 135.00,
  "notes": "Progressing well, ready for intermediate pieces",
  "is_active": true
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "first_name": "Emma",
    "last_name": "Johnson",
    "skill_level": "intermediate",
    "lesson_rate": 135.00,
    "notes": "Progressing well, ready for intermediate pieces",
    "updated_at": "2024-01-01T12:00:00Z"
  },
  "message": "Student updated successfully"
}
```

#### DELETE /api/students/{student_id}
**Purpose**: Deactivate student (soft delete)  
**Access**: ADMIN only  
**Performance Target**: <200ms

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "is_active": false,
    "updated_at": "2024-01-01T12:00:00Z"
  },
  "message": "Student deactivated successfully"
}
```

## 3. Teacher Management

### 3.1 Teacher CRUD Operations

#### GET /api/teachers
**Purpose**: List teachers with availability information  
**Access**: ADMIN (all), TEACHER (self), PARENT (basic info only)  
**Performance Target**: <200ms

**Query Parameters:**
- `page`: integer (default: 1)
- `limit`: integer (default: 20)
- `instrument`: string (filter by instrument)
- `is_available`: boolean (filter by availability)
- `include_availability`: boolean (include availability slots)

**Response:**
```json
{
  "success": true,
  "data": {
    "teachers": [
      {
        "id": 1,
        "user_id": 3,
        "first_name": "Michael",
        "last_name": "Smith",
        "email": "michael@cedarheights.com",
        "instruments": ["piano", "guitar"],
        "hourly_rate": 125.00,
        "max_students": 30,
        "current_students": 18,
        "is_available": true,
        "bio": "Professional musician with 15 years teaching experience",
        "photo_url": "https://example.com/photos/michael.jpg",
        "availability": [
          {
            "day_of_week": 1,
            "day_name": "Monday",
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "available_slots": 16
          }
        ],
        "created_at": "2024-01-01T00:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 3,
      "pages": 1
    }
  }
}
```

#### GET /api/teachers/{teacher_id}
**Purpose**: Get teacher details  
**Access**: ADMIN (all), TEACHER (self), PARENT (basic info)  
**Performance Target**: <200ms

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "user_id": 3,
    "first_name": "Michael",
    "last_name": "Smith",
    "email": "michael@cedarheights.com",
    "phone": "+1-902-555-5678",
    "instruments": ["piano", "guitar"],
    "hourly_rate": 125.00,
    "max_students": 30,
    "current_students": 18,
    "is_available": true,
    "bio": "Professional musician with 15 years teaching experience",
    "photo_url": "https://example.com/photos/michael.jpg",
    "students": [
      {
        "id": 1,
        "first_name": "Emma",
        "last_name": "Johnson",
        "instrument": "piano",
        "skill_level": "beginner"
      }
    ],
    "availability": [
      {
        "id": 1,
        "day_of_week": 1,
        "day_name": "Monday",
        "start_time": "09:00:00",
        "end_time": "09:30:00",
        "is_recurring": true,
        "is_active": true
      }
    ],
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

#### PUT /api/teachers/{teacher_id}
**Purpose**: Update teacher information  
**Access**: ADMIN (all), TEACHER (self - limited fields)  
**Performance Target**: <200ms

**Request:**
```json
{
  "instruments": ["piano", "guitar", "violin"],
  "hourly_rate": 135.00,
  "max_students": 35,
  "is_available": true,
  "bio": "Updated bio with new qualifications",
  "photo_url": "https://example.com/photos/michael-new.jpg"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "instruments": ["piano", "guitar", "violin"],
    "hourly_rate": 135.00,
    "max_students": 35,
    "is_available": true,
    "bio": "Updated bio with new qualifications",
    "photo_url": "https://example.com/photos/michael-new.jpg",
    "updated_at": "2024-01-01T12:00:00Z"
  },
  "message": "Teacher updated successfully"
}
```

### 3.2 Teacher Availability Management

#### GET /api/teachers/{teacher_id}/availability
**Purpose**: Get teacher availability slots  
**Access**: ADMIN, TEACHER (self), PARENT (read-only)  
**Performance Target**: <200ms

**Query Parameters:**
- `day_of_week`: integer (0-6, filter by day)
- `is_active`: boolean (filter by active status)
- `include_bookings`: boolean (include current bookings)

**Response:**
```json
{
  "success": true,
  "data": {
    "teacher_id": 1,
    "availability": [
      {
        "id": 1,
        "day_of_week": 1,
        "day_name": "Monday",
        "start_time": "09:00:00",
        "end_time": "09:30:00",
        "duration_minutes": 30,
        "is_recurring": true,
        "is_active": true,
        "student_id": null,
        "is_available": true,
        "created_at": "2024-01-01T00:00:00Z"
      },
      {
        "id": 2,
        "day_of_week": 1,
        "day_name": "Monday",
        "start_time": "09:30:00",
        "end_time": "10:00:00",
        "duration_minutes": 30,
        "is_recurring": true,
        "is_active": true,
        "student_id": 1,
        "student_name": "Emma Johnson",
        "is_available": false,
        "created_at": "2024-01-01T00:00:00Z"
      }
    ]
  }
}
```

#### POST /api/teachers/{teacher_id}/availability
**Purpose**: Create availability slot  
**Access**: ADMIN, TEACHER (self)  
**Performance Target**: <200ms

**Request:**
```json
{
  "day_of_week": 1,
  "start_time": "14:00:00",
  "end_time": "14:30:00",
  "is_recurring": true,
  "is_active": true
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 15,
    "teacher_id": 1,
    "day_of_week": 1,
    "start_time": "14:00:00",
    "end_time": "14:30:00",
    "duration_minutes": 30,
    "is_recurring": true,
    "is_active": true,
    "created_at": "2024-01-01T12:00:00Z"
  },
  "message": "Availability slot created successfully"
}
```

#### PUT /api/teachers/{teacher_id}/availability/{slot_id}
**Purpose**: Update availability slot  
**Access**: ADMIN, TEACHER (self)  
**Performance Target**: <200ms

**Request:**
```json
{
  "start_time": "14:30:00",
  "end_time": "15:00:00",
  "is_active": true,
  "student_id": 2
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 15,
    "start_time": "14:30:00",
    "end_time": "15:00:00",
    "student_id": 2,
    "is_available": false,
    "updated_at": "2024-01-01T12:00:00Z"
  },
  "message": "Availability slot updated successfully"
}
```

#### DELETE /api/teachers/{teacher_id}/availability/{slot_id}
**Purpose**: Remove availability slot  
**Access**: ADMIN, TEACHER (self)  
**Performance Target**: <200ms

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 15,
    "is_active": false,
    "updated_at": "2024-01-01T12:00:00Z"
  },
  "message": "Availability slot removed successfully"
}
```

#### GET /api/teachers/{teacher_id}/availability/schedule
**Purpose**: Get teacher's weekly availability schedule  
**Access**: ADMIN, TEACHER (self), PARENT (read-only)  
**Performance Target**: <200ms

**Query Parameters:**
- `week_start`: date (start of week, default: current week)
- `include_booked`: boolean (include booked slots)

**Response:**
```json
{
  "success": true,
  "data": {
    "teacher_id": 1,
    "teacher_name": "Michael Smith",
    "week_start": "2024-01-08",
    "week_end": "2024-01-14",
    "schedule": [
      {
        "date": "2024-01-08",
        "day_name": "Monday",
        "day_of_week": 1,
        "slots": [
          {
            "id": 1,
            "start_time": "09:00:00",
            "end_time": "09:30:00",
            "is_available": true,
            "student_id": null
          },
          {
            "id": 2,
            "start_time": "09:30:00",
            "end_time": "10:00:00",
            "is_available": false,
            "student_id": 1,
            "student_name": "Emma Johnson"
          }
        ]
      }
    ],
    "summary": {
      "total_slots": 40,
      "available_slots": 22,
      "booked_slots": 18,
      "availability_percentage": 55.0
    }
  }
}
```


## 4. Lesson Management

### 4.1 Lesson CRUD Operations

#### GET /api/lessons
**Purpose**: List lessons with filtering and pagination  
**Access**: ADMIN (all), TEACHER (assigned), PARENT (own students)  
**Performance Target**: <200ms

**Query Parameters:**
- `page`: integer (default: 1)
- `limit`: integer (default: 20)
- `student_id`: integer (filter by student)
- `teacher_id`: integer (filter by teacher)
- `status`: string (filter by status)
- `lesson_type`: string (filter by type)
- `date_from`: date (filter from date)
- `date_to`: date (filter to date)
- `include_notes`: boolean (include lesson notes)

**Response:**
```json
{
  "success": true,
  "data": {
    "lessons": [
      {
        "id": 1,
        "student_id": 1,
        "student_name": "Emma Johnson",
        "teacher_id": 1,
        "teacher_name": "Michael Smith",
        "scheduled_at": "2024-01-08T09:00:00Z",
        "duration_minutes": 30,
        "lesson_type": "regular",
        "status": "scheduled",
        "payment_status": "paid",
        "attendance_marked": false,
        "teacher_notes": null,
        "student_progress_notes": null,
        "timeslot_id": 1,
        "semester_id": 1,
        "created_at": "2024-01-01T10:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 156,
      "pages": 8
    }
  }
}
```

#### GET /api/lessons/{lesson_id}
**Purpose**: Get lesson details  
**Access**: ADMIN (all), TEACHER (assigned), PARENT (own students)  
**Performance Target**: <200ms

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "student": {
      "id": 1,
      "first_name": "Emma",
      "last_name": "Johnson",
      "instrument": "piano",
      "skill_level": "beginner"
    },
    "teacher": {
      "id": 1,
      "first_name": "Michael",
      "last_name": "Smith",
      "email": "michael@cedarheights.com"
    },
    "scheduled_at": "2024-01-08T09:00:00Z",
    "duration_minutes": 30,
    "lesson_type": "regular",
    "status": "scheduled",
    "payment_status": "paid",
    "attendance_marked": false,
    "teacher_notes": "Student is progressing well with scales",
    "student_progress_notes": "Needs to work on hand positioning",
    "timeslot_id": 1,
    "semester_id": 1,
    "makeup_lesson_id": null,
    "original_lesson_id": null,
    "created_at": "2024-01-01T10:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z"
  }
}
```

#### POST /api/lessons
**Purpose**: Create new lesson  
**Access**: ADMIN, TEACHER (for assigned students)  
**Performance Target**: <200ms

**Request:**
```json
{
  "student_id": 1,
  "teacher_id": 1,
  "scheduled_at": "2024-01-15T09:00:00Z",
  "duration_minutes": 30,
  "lesson_type": "regular",
  "timeslot_id": 1,
  "semester_id": 1,
  "notes": "Regular weekly lesson"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 25,
    "student_id": 1,
    "teacher_id": 1,
    "scheduled_at": "2024-01-15T09:00:00Z",
    "duration_minutes": 30,
    "lesson_type": "regular",
    "status": "scheduled",
    "payment_status": "pending",
    "timeslot_id": 1,
    "semester_id": 1,
    "created_at": "2024-01-01T12:00:00Z"
  },
  "message": "Lesson created successfully"
}
```

#### PUT /api/lessons/{lesson_id}
**Purpose**: Update lesson information  
**Access**: ADMIN, TEACHER (assigned lessons)  
**Performance Target**: <200ms

**Request:**
```json
{
  "status": "completed",
  "attendance_marked": true,
  "teacher_notes": "Excellent progress on Chopin piece",
  "student_progress_notes": "Ready to move to intermediate level",
  "payment_status": "paid"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "status": "completed",
    "attendance_marked": true,
    "teacher_notes": "Excellent progress on Chopin piece",
    "student_progress_notes": "Ready to move to intermediate level",
    "payment_status": "paid",
    "updated_at": "2024-01-01T12:00:00Z"
  },
  "message": "Lesson updated successfully"
}
```

## 5. Payment Management

### 5.1 Payment CRUD Operations

#### GET /api/payments
**Purpose**: List payments with filtering  
**Access**: ADMIN (all), PARENT (own payments)  
**Performance Target**: <200ms

**Query Parameters:**
- `page`: integer (default: 1)
- `limit`: integer (default: 20)
- `student_id`: integer (filter by student)
- `status`: string (filter by status)
- `date_from`: date (filter from date)
- `date_to`: date (filter to date)

**Response:**
```json
{
  "success": true,
  "data": {
    "payments": [
      {
        "id": 1,
        "student_id": 1,
        "student_name": "Emma Johnson",
        "lesson_id": 1,
        "stripe_payment_intent_id": "pi_1234567890",
        "amount": 125.00,
        "currency": "CAD",
        "status": "succeeded",
        "payment_method": "card",
        "payment_date": "2024-01-01T10:00:00Z",
        "billing_cycle": "monthly",
        "description": "Piano lesson - January 2024",
        "created_at": "2024-01-01T09:30:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 89,
      "pages": 5
    },
    "summary": {
      "total_amount": 11125.00,
      "successful_payments": 87,
      "failed_payments": 2,
      "pending_payments": 0
    }
  }
}
```

#### GET /api/payments/{payment_id}
**Purpose**: Get payment details  
**Access**: ADMIN (all), PARENT (own payments)  
**Performance Target**: <200ms

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "student": {
      "id": 1,
      "first_name": "Emma",
      "last_name": "Johnson"
    },
    "lesson": {
      "id": 1,
      "scheduled_at": "2024-01-08T09:00:00Z",
      "teacher_name": "Michael Smith"
    },
    "stripe_payment_intent_id": "pi_1234567890",
    "stripe_customer_id": "cus_123456789",
    "amount": 125.00,
    "currency": "CAD",
    "status": "succeeded",
    "payment_method": "card",
    "payment_date": "2024-01-01T10:00:00Z",
    "billing_cycle": "monthly",
    "description": "Piano lesson - January 2024",
    "failure_reason": null,
    "metadata": {
      "lesson_month": "2024-01",
      "instrument": "piano"
    },
    "created_at": "2024-01-01T09:30:00Z"
  }
}
```

## 6. Workflow Integration Endpoints

### 6.1 Enrollment Workflow

#### POST /api/workflows/enrollment
**Purpose**: Trigger enrollment workflow  
**Access**: ADMIN only  
**Performance Target**: <2s (workflow operation)

**Request:**
```json
{
  "student_first_name": "Emma",
  "student_last_name": "Johnson",
  "student_date_of_birth": "2015-03-15",
  "parent_first_name": "Sarah",
  "parent_last_name": "Johnson",
  "parent_email": "sarah@example.com",
  "parent_phone": "+1-902-555-1234",
  "instrument": "piano",
  "preferred_lesson_day": "monday",
  "preferred_lesson_time": "afternoon",
  "lesson_duration": 30,
  "payment_token": "pm_test_token",
  "agreed_to_terms": true
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "workflow_id": "wf_enrollment_123456",
    "status": "completed",
    "execution_time": 1.8,
    "results": {
      "student_id": 1,
      "parent_user_id": 2,
      "teacher_assigned": {
        "teacher_id": 1,
        "teacher_name": "Michael Smith"
      },
      "demo_lesson": {
        "lesson_id": 25,
        "scheduled_at": "2024-01-15T14:00:00Z"
      },
      "payment_setup": {
        "stripe_customer_id": "cus_123456789",
        "subscription_id": "sub_123456789"
      },
      "emails_sent": {
        "parent_welcome": true,
        "teacher_notification": true
      }
    }
  },
  "message": "Enrollment workflow completed successfully"
}
```

#### GET /api/workflows/enrollment/{workflow_id}/status
**Purpose**: Get enrollment workflow status  
**Access**: ADMIN only  
**Performance Target**: <200ms

**Response:**
```json
{
  "success": true,
  "data": {
    "workflow_id": "wf_enrollment_123456",
    "status": "completed",
    "progress": 100,
    "current_node": "SendWelcomeEmailsNode",
    "nodes_executed": [
      "ValidateEnrollmentNode",
      "CreateStudentAccountNode",
      "SetupPaymentMethodNode",
      "AssignTeacherNode",
      "ScheduleDemoLessonNode",
      "SendWelcomeEmailsNode"
    ],
    "execution_time": 1.8,
    "started_at": "2024-01-01T10:00:00Z",
    "completed_at": "2024-01-01T10:00:01.8Z"
  }
}
```

### 6.2 Payment Processing Workflow

#### POST /api/workflows/payment
**Purpose**: Trigger payment processing workflow  
**Access**: ADMIN only  
**Performance Target**: <2s (workflow operation)

**Request:**
```json
{
  "student_id": 1,
  "lesson_id": 1,
  "amount": 125.00,
  "payment_method_id": "pm_1234567890",
  "currency": "CAD",
  "description": "Piano lesson - January 2024",
  "automatic_payment": true
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "workflow_id": "wf_payment_789012",
    "status": "completed",
    "execution_time": 0.9,
    "results": {
      "payment_id": 15,
      "stripe_payment_intent_id": "pi_1234567890",
      "payment_status": "succeeded",
      "amount_charged": 125.00,
      "receipt_sent": true,
      "accounting_updated": true
    }
  },
  "message": "Payment workflow completed successfully"
}
```

### 6.3 Lesson Scheduling Workflow

#### POST /api/workflows/scheduling
**Purpose**: Trigger lesson scheduling workflow  
**Access**: ADMIN, TEACHER  
**Performance Target**: <2s (workflow operation)

**Request:**
```json
{
  "student_id": 1,
  "teacher_id": 1,
  "preferred_datetime": "2024-01-15T14:00:00Z",
  "duration_minutes": 30,
  "lesson_type": "regular",
  "recurring": true,
  "recurrence_pattern": "weekly"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "workflow_id": "wf_scheduling_345678",
    "status": "completed",
    "execution_time": 1.2,
    "results": {
      "lesson_id": 26,
      "scheduled_at": "2024-01-15T14:00:00Z",
      "conflicts_resolved": 0,
      "recurring_lessons_created": 12,
      "confirmations_sent": true
    }
  },
  "message": "Scheduling workflow completed successfully"
}
```

## 7. Public API Endpoints (Frontend Integration)

### 7.1 Public Website Support

#### GET /public/teachers
**Purpose**: Get teacher information for public website  
**Access**: Public  
**Performance Target**: <200ms

**Response:**
```json
{
  "success": true,
  "data": {
    "teachers": [
      {
        "id": 1,
        "first_name": "Michael",
        "last_name": "Smith",
        "instruments": ["piano", "guitar"],
        "bio": "Professional musician with 15 years teaching experience",
        "photo_url": "https://example.com/photos/michael.jpg",
        "is_available": true
      }
    ]
  }
}
```

#### GET /public/timeslots
**Purpose**: Get available timeslots for enrollment  
**Access**: Public  
**Performance Target**: <200ms

**Query Parameters:**
- `teacher_id`: integer (filter by teacher)
- `instrument`: string (filter by instrument)
- `weekday`: integer (filter by day of week)
- `active`: boolean (filter by active status)

**Response:**
```json
{
  "success": true,
  "data": {
    "timeslots": [
      {
        "id": 1,
        "teacher_id": 1,
        "teacher_name": "Michael Smith",
        "day_of_week": 1,
        "day_name": "Monday",
        "start_time": "14:00:00",
        "end_time": "14:30:00",
        "duration_minutes": 30,
        "is_available": true,
        "instrument": "piano"
      }
    ]
  }
}
```

#### GET /public/pricing
**Purpose**: Get current pricing information  
**Access**: Public  
**Performance Target**: <200ms

**Response:**
```json
{
  "success": true,
  "data": {
    "pricing": [
      {
        "instrument": "piano",
        "rate_per_lesson": 125.00,
        "currency": "CAD",
        "billing_frequency": "monthly",
        "lesson_duration": 30,
        "effective_date": "2024-01-01"
      }
    ],
    "current_semester": {
      "id": 1,
      "name": "Fall 2024",
",
      "end_date": "2024-12-15"
    }
  }
}
```

## 8. System Configuration & Management

### 8.1 Academic Calendar Management

#### GET /api/academic/years
**Purpose**: List academic years  
**Access**: ADMIN (all), TEACHER (read-only), PARENT (read-only)  
**Performance Target**: <200ms

**Response:**
```json
{
  "success": true,
  "data": {
    "academic_years": [
      {
        "id": 1,
        "name": "2024-2025",
        "start_date": "2024-09-01",
        "end_date": "2025-06-30",
        "is_current": true,
        "created_at": "2024-01-01T00:00:00Z"
      }
    ]
  }
}
```

#### GET /api/academic/semesters
**Purpose**: List semesters  
**Access**: ADMIN (all), TEACHER (read-only), PARENT (read-only)  
**Performance Target**: <200ms

**Query Parameters:**
- `academic_year_id`: integer (filter by academic year)
- `is_current`: boolean (filter by current semester)

**Response:**
```json
{
  "success": true,
  "data": {
    "semesters": [
      {
        "id": 1,
        "academic_year_id": 1,
        "name": "Fall 2024",
        "start_date": "2024-09-01",
        "end_date": "2024-12-15",
        "is_current": true,
        "makeup_weeks": [
          {
            "id": 1,
            "name": "Fall 2024 Makeup Week",
            "start_date": "2024-12-16",
            "end_date": "2024-12-22",
            "is_active": true
          }
        ],
        "created_at": "2024-01-01T00:00:00Z"
      }
    ]
  }
}
```

### 8.2 System Settings

#### GET /api/settings
**Purpose**: Get system settings  
**Access**: ADMIN (all), PUBLIC (public settings only)  
**Performance Target**: <200ms

**Query Parameters:**
- `category`: string (filter by category)
- `is_public`: boolean (filter by public visibility)

**Response:**
```json
{
  "success": true,
  "data": {
    "settings": [
      {
        "id": 1,
        "setting_key": "school_name",
        "setting_value": "Cedar Heights Music Academy",
        "setting_type": "string",
        "description": "Name of the music school",
        "is_public": true,
        "category": "general"
      },
      {
        "id": 2,
        "setting_key": "default_lesson_duration",
        "setting_value": "30",
        "setting_type": "number",
        "description": "Default lesson duration in minutes",
        "is_public": true,
        "category": "lessons"
      }
    ]
  }
}
```

#### PUT /api/settings/{setting_id}
**Purpose**: Update system setting  
**Access**: ADMIN only  
**Performance Target**: <200ms

**Request:**
```json
{
  "setting_value": "35",
  "description": "Updated default lesson duration"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 2,
    "setting_key": "default_lesson_duration",
    "setting_value": "35",
    "setting_type": "number",
    "description": "Updated default lesson duration",
    "updated_at": "2024-01-01T12:00:00Z"
  },
  "message": "Setting updated successfully"
}
```

## 9. Missing Teacher Availability Management

### 9.1 Teacher Availability CRUD Operations

#### GET /api/teachers/{teacher_id}/availability
**Purpose**: Get teacher availability slots  
**Access**: ADMIN, TEACHER (self), PARENT (read-only)  
**Performance Target**: <200ms

**Query Parameters:**
- `day_of_week`: integer (0-6, filter by day)
- `is_active`: boolean (filter by active status)
- `include_bookings`: boolean (include current bookings)

**Response:**
```json
{
  "success": true,
  "data": {
    "teacher_id": 1,
    "availability": [
      {
        "id": 1,
        "day_of_week": 1,
        "day_name": "Monday",
        "start_time": "09:00:00",
        "end_time": "09:30:00",
        "duration_minutes": 30,
        "is_recurring": true,
        "is_active": true,
        "student_id": null,
        "is_available": true,
        "created_at": "2024-01-01T00:00:00Z"
      },
      {
        "id": 2,
        "day_of_week": 1,
        "day_name": "Monday",
        "start_time": "09:30:00",
        "end_time": "10:00:00",
        "duration_minutes": 30,
        "is_recurring": true,
        "is_active": true,
        "student_id": 1,
        "student_name": "Emma Johnson",
        "is_available": false,
        "created_at": "2024-01-01T00:00:00Z"
      }
    ]
  }
}
```

#### POST /api/teachers/{teacher_id}/availability
**Purpose**: Create availability slot  
**Access**: ADMIN, TEACHER (self)  
**Performance Target**: <200ms

**Request:**
```json
{
  "day_of_week": 1,
  "start_time": "14:00:00",
  "end_time": "14:30:00",
  "is_recurring": true,
  "is_active": true
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 15,
    "teacher_id": 1,
    "day_of_week": 1,
    "start_time": "14:00:00",
    "end_time": "14:30:00",
    "duration_minutes": 30,
    "is_recurring": true,
    "is_active": true,
    "created_at": "2024-01-01T12:00:00Z"
  },
  "message": "Availability slot created successfully"
}
```

#### PUT /api/teachers/{teacher_id}/availability/{slot_id}
**Purpose**: Update availability slot  
**Access**: ADMIN, TEACHER (self)  
**Performance Target**: <200ms

**Request:**
```json
{
  "start_time": "14:30:00",
  "end_time": "15:00:00",
  "is_active": true,
  "student_id": 2
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 15,
    "start_time": "14:30:00",
    "end_time": "15:00:00",
    "student_id": 2,
    "is_available": false,
    "updated_at": "2024-01-01T12:00:00Z"
  },
  "message": "Availability slot updated successfully"
}
```

#### DELETE /api/teachers/{teacher_id}/availability/{slot_id}
**Purpose**: Remove availability slot  
**Access**: ADMIN, TEACHER (self)  
**Performance Target**: <200ms

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 15,
    "is_active": false,
    "updated_at": "2024-01-01T12:00:00Z"
  },
  "message": "Availability slot removed successfully"
}
```

## 10. Missing Lesson Management Endpoints

### 10.1 Lesson Cancellation and Rescheduling

#### DELETE /api/lessons/{lesson_id}
**Purpose**: Cancel lesson  
**Access**: ADMIN, TEACHER (assigned lessons)  
**Performance Target**: <200ms

**Request:**
```json
{
  "cancellation_reason": "Student illness",
  "notify_parent": true,
  "offer_makeup": true
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "status": "cancelled",
    "cancellation_reason": "Student illness",
    "makeup_lesson_offered": true,
    "updated_at": "2024-01-01T12:00:00Z"
  },
  "message": "Lesson cancelled successfully"
}
```

### 10.2 Lesson Scheduling Support

#### GET /api/lessons/schedule
**Purpose**: Get lesson schedule view  
**Access**: ADMIN (all), TEACHER (assigned), PARENT (own students)  
**Performance Target**: <200ms

**Query Parameters:**
- `view`: string (day, week, month - default: week)
- `date`: date (center date for view)
- `teacher_id`: integer (filter by teacher)
- `student_id`: integer (filter by student)

**Response:**
```json
{
  "success": true,
  "data": {
    "view": "week",
    "date_range": {
      "start": "2024-01-08",
      "end": "2024-01-14"
    },
    "schedule": [
      {
        "date": "2024-01-08",
        "day_name": "Monday",
        "lessons": [
          {
            "id": 1,
            "time": "09:00:00",
            "duration_minutes": 30,
            "student_name": "Emma Johnson",
            "teacher_name": "Michael Smith",
            "status": "scheduled",
            "lesson_type": "regular"
          }
        ]
      }
    ],
    "teachers": [
      {
        "id": 1,
        "name": "Michael Smith",
        "lessons_count": 18
      }
    ]
  }
}
```

#### POST /api/lessons/schedule/conflicts
**Purpose**: Check for scheduling conflicts  
**Access**: ADMIN, TEACHER  
**Performance Target**: <200ms

**Request:**
```json
{
  "teacher_id": 1,
  "scheduled_at": "2024-01-15T09:00:00Z",
  "duration_minutes": 30,
  "exclude_lesson_id": null
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "has_conflicts": false,
    "conflicts": [],
    "available": true,
    "suggested_times": [
      "2024-01-15T09:30:00Z",
      "2024-01-15T10:00:00Z",
      "2024-01-15T10:30:00Z"
    ]
  }
}
```

## 11. Communication & Messaging

### 11.1 Internal Messaging

#### GET /api/messages
**Purpose**: List messages for current user  
**Access**: Authenticated  
**Performance Target**: <200ms

**Query Parameters:**
- `page`: integer (default: 1)
- `limit`: integer (default: 20)
- `conversation_with`: integer (filter by user ID)
- `is_read`: boolean (filter by read status)
- `message_type`: string (filter by type)

**Response:**
```json
{
  "success": true,
  "data": {
    "messages": [
      {
        "id": 1,
        "sender_id": 2,
        "sender_name": "Sarah Johnson",
        "recipient_id": 1,
        "subject": "Question about Emma's progress",
        "body": "Hi, I wanted to ask about Emma's piano progress...",
        "message_type": "message",
        "priority": "normal",
        "is_read": false,
        "student_id": 1,
        "lesson_id": null,
        "created_at": "2024-01-01T10:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 15,
      "pages": 1
    }
  }
}

## 15. Academic Calendar Management

### 15.1 Academic Years

#### GET /api/academic/years
**Purpose**: List academic years  
**Access**: ADMIN (all), TEACHER (read-only), PARENT (read-only)  
**Performance Target**: <200ms

**Response:**
```json
{
  "success": true,
  "data": {
    "academic_years": [
      {
        "id": 1,
        "name": "2024-2025",
        "start_date": "2024-09-01",
        "end_date": "2025-06-30",
        "is_current": true,
        "created_at": "2024-01-01T00:00:00Z"
      }
    ]
  }
}
```

#### POST /api/academic/years
**Purpose**: Create academic year  
**Access**: ADMIN only  
**Performance Target**: <200ms

**Request:**
```json
{
  "name": "2025-2026",
  "start_date": "2025-09-01",
  "end_date": "2026-06-30",
  "is_current": false
}
```

### 15.2 Semesters

#### GET /api/academic/semesters
**Purpose**: List semesters  
**Access**: ADMIN (all), TEACHER (read-only), PARENT (read-only)  
**Performance Target**: <200ms

**Query Parameters:**
- `academic_year_id`: integer (filter by academic year)
- `is_current`: boolean (filter by current semester)

**Response:**
```json
{
  "success": true,
  "data": {
    "semesters": [
      {
        "id": 1,
        "academic_year_id": 1,
        "name": "Fall 2024",
        "start_date": "2024-09-01",
        "end_date": "2024-12-15",
        "is_current": true,
        "makeup_weeks": [
          {
            "id": 1,
            "name": "Fall 2024 Makeup Week",
            "start_date": "2024-12-16",
            "end_date": "2024-12-22",
            "is_active": true
          }
        ]
      }
    ]
  }
}
```

## 16. Timeslots Management

### 16.1 Timeslot Operations

#### GET /api/timeslots
**Purpose**: List available timeslots  
**Access**: ADMIN (all), TEACHER (assigned), PARENT (read-only)  
**Performance Target**: <200ms

**Query Parameters:**
- `teacher_id`: integer (filter by teacher)
- `day_of_week`: integer (filter by day)
- `status`: string (filter by status)
- `student_id`: integer (filter by student)

**Response:**
```json
{
  "success": true,
  "data": {
    "timeslots": [
      {
        "id": 1,
        "teacher_id": 1,
        "teacher_name": "Michael Smith",
        "day_of_week": 1,
        "day_name": "Monday",
        "start_time": "09:00:00",
        "end_time": "09:30:00",
        "duration_minutes": 30,
        "status": "available",
        "student_id": null,
        "semester_id": 1,
        "is_recurring": true,
        "is_active": true
      }
    ]
  }
}
```

#### POST /api/timeslots
**Purpose**: Create timeslot  
**Access**: ADMIN, TEACHER (self)  
**Performance Target**: <200ms

**Request:**
```json
{
  "teacher_id": 1,
  "day_of_week": 1,
  "start_time": "14:00:00",
  "end_time": "14:30:00",
  "duration_minutes": 30,
  "status": "available",
  "semester_id": 1,
  "is_recurring": true
}
```

## 17. Subscription Management

### 17.1 Stripe Subscriptions

#### GET /api/subscriptions
**Purpose**: List subscriptions  
**Access**: ADMIN (all), PARENT (own subscriptions)  
**Performance Target**: <200ms

**Query Parameters:**
- `student_id`: integer (filter by student)
- `status`: string (filter by status)

**Response:**
```json
{
  "success": true,
  "data": {
    "subscriptions": [
      {
        "id": 1,
        "student_id": 1,
        "student_name": "Emma Johnson",
        "stripe_subscription_id": "sub_123456789",
        "stripe_customer_id": "cus_123456789",
        "status": "active",
        "current_period_start": "2024-01-01T00:00:00Z",
        "current_period_end": "2024-02-01T00:00:00Z",
        "billing_cycle": "monthly",
        "amount": 125.00,
        "currency": "CAD",
        "created_at": "2024-01-01T00:00:00Z"
      }
    ]
  }
}
```

#### POST /api/subscriptions/{subscription_id}/cancel
**Purpose**: Cancel subscription  
**Access**: ADMIN, PARENT (own subscription)  
**Performance Target**: <200ms

**Request:**
```json
{
  "cancellation_reason": "Student no longer taking lessons",
  "cancel_at_period_end": true
}
```

## 18. Billing Records

### 18.1 Financial Tracking

#### GET /api/billing
**Purpose**: List billing records  
**Access**: ADMIN (all), PARENT (own records)  
**Performance Target**: <200ms

**Query Parameters:**
- `student_id`: integer (filter by student)
- `status`: string (filter by status)
- `date_from`: date (filter from date)
- `date_to`: date (filter to date)

**Response:**
```json
{
  "success": true,
  "data": {
    "billing_records": [
      {
        "id": 1,
        "student_id": 1,
        "student_name": "Emma Johnson",
        "payment_id": 1,
        "subscription_id": 1,
        "amount": 125.00,
        "currency": "CAD",
        "transaction_type": "charge",
        "description": "Monthly piano lessons",
        "billing_date": "2024-01-01",
        "due_date": "2024-01-15",
        "status": "paid",
        "created_at": "2024-01-01T00:00:00Z"
      }
    ]
  }
}
```

## 19. Email Tracking

### 19.1 Communication Tracking

#### GET /api/communications/emails
**Purpose**: List email tracking records  
**Access**: ADMIN only  
**Performance Target**: <200ms

**Query Parameters:**
- `recipient_email`: string (filter by recipient)
- `status`: string (filter by status)
- `date_from`: date (filter from date)

**Response:**
```json
{
  "success": true,
  "data": {
    "emails": [
      {
        "id": 1,
        "message_id": 1,
        "recipient_email": "parent@example.com",
        "sender_email": "info@cedarheights.com",
        "subject": "Welcome to Cedar Heights Music Academy",
        "email_service_id": "msg_123456789",
        "status": "delivered",
        "delivery_attempts": 1,
        "delivered_at": "2024-01-01T10:05:00Z",
        "opened_at": "2024-01-01T10:15:00Z",
        "created_at": "2024-01-01T10:00:00Z"
      }
    ]
  }
}
```

## 20. System Configuration

### 20.1 Settings Management

#### GET /api/settings
**Purpose**: Get system settings  
**Access**: ADMIN (all), PUBLIC (public settings only)  
**Performance Target**: <200ms

**Query Parameters:**
- `category`: string (filter by category)
- `is_public`: boolean (filter by public visibility)

**Response:**
```json
{
  "success": true,
  "data": {
    "settings": [
      {
        "id": 1,
        "setting_key": "school_name",
        "setting_value": "Cedar Heights Music Academy",
        "setting_type": "string",
        "description": "Name of the music school",
        "is_public": true,
        "category": "general"
      }
    ]
  }
}
```

#### PUT /api/settings/{setting_id}
**Purpose**: Update system setting  
**Access**: ADMIN only  
**Performance Target**: <200ms

**Request:**
```json
{
  "setting_value": "Cedar Heights Music Academy - Halifax",
  "description": "Updated school name with location"
}
```

### 20.2 Pricing Configuration

#### GET /api/pricing
**Purpose**: Get pricing configuration  
**Access**: ADMIN (all), PUBLIC (active pricing only)  
**Performance Target**: <200ms

**Response:**
```json
{
  "success": true,
  "data": {
    "pricing": [
      {
        "id": 1,
        "instrument": "piano",
        "skill_level": "all",
        "lesson_duration": 30,
        "rate_per_lesson": 125.00,
        "currency": "CAD",
        "billing_frequency": "monthly",
        "is_active": true,
        "effective_date": "2024-01-01"
      }
    ]
  }
}
```

## 21. Audit and Compliance

### 21.1 Audit Trail

#### GET /api/audit
**Purpose**: List audit entries  
**Access**: ADMIN only  
**Performance Target**: <200ms

**Query Parameters:**
- `table_name`: string (filter by table)
- `record_id`: integer (filter by record)
- `action`: string (filter by action)
- `changed_by`: integer (filter by user)
- `date_from`: date (filter from date)

**Response:**
```json
{
  "success": true,
  "data": {
    "audit_entries": [
      {
        "id": 1,
        "table_name": "students",
        "record_id": 1,
        "action": "UPDATE",
        "old_values": {"skill_level": "beginner"},
        "new_values": {"skill_level": "intermediate"},
        "changed_by": 1,
        "changed_by_name": "Admin User",
        "changed_at": "2024-01-01T12:00:00Z",
        "ip_address": "192.168.1.100"
      }
    ]
  }
}
```

## 22. Makeup Lesson Management

### 22.1 Makeup Lesson Tracking

#### GET /api/students/{student_id}/makeup-lessons
**Purpose**: Get makeup lesson status for student  
**Access**: ADMIN, TEACHER (assigned), PARENT (own student)  
**Performance Target**: <200ms

**Response:**
```json
{
  "success": true,
  "data": {
    "student_id": 1,
    "current_semester": {
      "semester_id": 1,
      "semester_name": "Fall 2024",
      "makeup_lessons_used": 0,
      "makeup_lessons_allowed": 1,
      "makeup_lessons_remaining": 1
    },
    "makeup_history": [
      {
        "semester_id": 1,
        "original_lesson_id": 15,
        "makeup_lesson_id": 25,
        "reason": "Student illness",
        "scheduled_at": "2024-01-15T14:00:00Z",
        "status": "completed"
      }
    ]
  }
}
```

#### PUT /api/students/{student_id}/makeup-lessons
**Purpose**: Update makeup lesson tracking  
**Access**: ADMIN only  
**Performance Target**: <200ms

**Request:**
```json
{
  "semester_id": 1,
  "makeup_lessons_allowed": 2,
  "reason": "Extended illness accommodation"
}
```

```

#### POST /api/messages
**Purpose**: Send message  
**Access**: Authenticated  
**Performance Target**: <200ms

**Request:**
```json
{
  "recipient_id": 1,
  "subject": "Question about lesson schedule",
  "body": "Hi, I need to reschedule Emma's lesson next week...",
  "message_type": "message",
  "priority": "normal",
  "student_id": 1
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 25,
    "sender_id": 2,
    "recipient_id": 1,
    "subject": "Question about lesson schedule",
    "body": "Hi, I need to reschedule Emma's lesson next week...",
    "message_type": "message",
    "priority": "normal",
    "is_read": false,
    "student_id": 1,
    "created_at": "2024-01-01T12:00:00Z"
  },
  "message": "Message sent successfully"
}
```

#### PUT /api/messages/{message_id}/read
**Purpose**: Mark message as read  
**Access**: Authenticated (recipient only)  
**Performance Target**: <200ms

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "is_read": true,
    "read_at": "2024-01-01T12:00:00Z"
  },
  "message": "Message marked as read"
}
```

### 11.2 Notifications

#### GET /api/notifications
**Purpose**: Get user notifications  
**Access**: Authenticated  
**Performance Target**: <200ms

**Query Parameters:**
- `page`: integer (default: 1)
- `limit`: integer (default: 20)
- `notification_type`: string (filter by type)
- `is_read`: boolean (filter by read status)

**Response:**
```json
{
  "success": true,
  "data": {
    "notifications": [
      {
        "id": 1,
        "title": "Payment Successful",
        "message": "Your payment for Emma's piano lesson has been processed successfully.",
        "notification_type": "payment_success",
        "priority": "normal",
        "is_read": false,
        "action_url": "/payments/1",
        "student_id": 1,
        "lesson_id": 1,
        "expires_at": null,
        "created_at": "2024-01-01T10:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 8,
      "pages": 1
    },
    "unread_count": 3
  }
}
```

#### PUT /api/notifications/{notification_id}/read
**Purpose**: Mark notification as read  
**Access**: Authenticated (owner only)  
**Performance Target**: <200ms

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "is_read": true,
    "read_at": "2024-01-01T12:00:00Z"
  },
  "message": "Notification marked as read"
}
```

## 12. Health & Monitoring

### 12.1 System Health

#### GET /api/health
**Purpose**: System health check  
**Access**: Public  
**Performance Target**: <100ms

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": "2024-01-01T12:00:00Z",
    "version": "1.0.0",
    "services": {
      "database": "healthy",
      "redis": "healthy",
      "supabase": "healthy",
      "stripe": "healthy"
    },
    "uptime": 86400
  }
}
```

#### GET /api/health/detailed
**Purpose**: Detailed system health  
**Access**: ADMIN only  
**Performance Target**: <200ms

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": "2024-01-01T12:00:00Z",
    "version": "1.0.0",
    "services": {
      "database": {
        "status": "healthy",
        "response_time_ms": 15,
        "connections": 5,
        "max_connections": 100
      },
      "redis": {
        "status": "healthy",
        "response_time_ms": 2,
        "memory_usage": "45MB",
        "connected_clients": 3
      },
      "supabase": {
        "status": "healthy",
        "response_time_ms": 120
      },
      "stripe": {
        "status": "healthy",
        "response_time_ms": 180
      }
    },
    "metrics": {
      "active_users": 45,
      "total_lessons_today": 12,
      "successful_payments_today": 8,
      "api_requests_per_minute": 25
    }
  }
}
```

## 13. Error Handling & Response Codes

### 13.1 Standard HTTP Status Codes

- **200 OK**: Successful GET, PUT requests
- **201 Created**: Successful POST requests
- **204 No Content**: Successful DELETE requests
- **400 Bad Request**: Invalid request data or parameters
- **401 Unauthorized**: Missing or invalid authentication
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **409 Conflict**: Resource conflict (e.g., scheduling conflict)
- **422 Unprocessable Entity**: Validation errors
- **429 Too Many Requests**: Rate limiting
- **500 Internal Server Error**: Server errors

### 13.2 Error Response Format

```json
{
  "success": false,
  "data": null,
  "message": "Validation failed",
  "errors": [
    {
      "field": "email",
      "code": "INVALID_FORMAT",
      "message": "Email format is invalid"
    },
    {
      "field": "date_of_birth",
      "code": "INVALID_AGE",
      "message": "Student must be at least 5 years old"
    }
  ],
  "metadata": {
    "timestamp": "2024-01-01T12:00:00Z",
    "request_id": "req_123456789",
    "execution_time_ms": 45
  }
}
```

### 13.3 Common Error Codes

- **VALIDATION_ERROR**: Input validation failed
- **AUTHENTICATION_REQUIRED**: Authentication token required
- **INSUFFICIENT_PERMISSIONS**: User lacks required permissions
- **RESOURCE_NOT_FOUND**: Requested resource does not exist
- **SCHEDULING_CONFLICT**: Lesson scheduling conflict detected
- **PAYMENT_FAILED**: Payment processing failed
- **WORKFLOW_ERROR**: Workflow execution failed
- **RATE_LIMIT_EXCEEDED**: Too many requests

## 14. Implementation Summary

### 14.1 Endpoint Count by Domain

- **Authentication & User Management**: 5 endpoints
- **Student Management**: 5 endpoints
- **Teacher Management**: 4 endpoints + 5 availability endpoints
- **Lesson Management**: 6 endpoints + 2 scheduling endpoints + 1 cancellation
- **Payment Management**: 2 endpoints
- **Workflow Integration**: 6 endpoints
- **Public API**: 3 endpoints
- **System Configuration**: 4 endpoints
- **Communication**: 4 endpoints
- **Health & Monitoring**: 2 endpoints
- **Academic Calendar Management**: 4 endpoints
- **Timeslots Management**: 3 endpoints
- **Subscription Management**: 3 endpoints
- **Billing Records**: 2 endpoints
- **Email Tracking**: 1 endpoint
- **System Settings**: 4 endpoints
- **Audit and Compliance**: 1 endpoint
- **Makeup Lesson Management**: 2 endpoints

**Total**: 69 comprehensive API endpoints

### 14.2 Performance Targets Summary

- **Quick Operations**: <200ms (95% of endpoints)
- **Workflow Operations**: <2s (workflow endpoints)
- **Health Checks**: <100ms
- **Database Queries**: Optimized with proper indexing
- **External API Calls**: Cached where appropriate

### 14.3 Security Implementation

- **JWT Authentication**: All authenticated endpoints
- **Role-Based Access Control**: ADMIN, TEACHER, PARENT roles
- **Row Level Security**: Database-level access control
- **Input Validation**: Comprehensive Pydantic validation
- **Rate Limiting**: Prevent abuse and ensure fair usage
- **Audit Logging**: Track all significant operations

### 14.4 Next Steps for Implementation

1. **Setup FastAPI application structure** with proper routing
2. **Implement authentication middleware** with Supabase integration
3. **Create Pydantic schemas** for all request/response models
4. **Implement CRUD operations** for each domain
5. **Add workflow integration** endpoints
6. **Setup comprehensive error handling** and logging
7. **Add OpenAPI documentation** generation
8. **Implement rate limiting** and security measures
9. **Create comprehensive test suite** for all endpoints
10. **Setup monitoring and health checks**

---

**Document Status**: ✅ COMPLETE  
**Total Endpoints Specified**: 47  
**Ready for Phase 1.3 Implementation**: Yes  
**Last Updated**: 2025-01-07
      "start_date": "2024-09-01