# Cedar Heights Music Academy — Synthesized Architecture Design Document
## Workflow-Driven Music School Management System

## Executive Summary

This Architecture Design Document (ADD) defines the technical architecture for the Cedar Heights Music Academy Management System, synthesizing the business domain requirements of a music school with the GenAI Launchpad DAG-based workflow orchestration framework. Built on Python 3.11+ with FastAPI, this system implements workflow-driven business processes for enrollment, lesson scheduling, payment processing, and student management while maintaining <200ms response times for quick operations and robust workflow processing for complex business scenarios.

**Architecture Philosophy:** Workflow-driven business process automation with Chain of Responsibility pattern, emphasizing type safety through Pydantic validation, single-owner operator simplicity, and production-ready reliability with comprehensive error handling and monitoring.

## System Architecture Overview

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        CEDAR HEIGHTS MUSIC ACADEMY                            │
│                    WORKFLOW-DRIVEN MANAGEMENT SYSTEM                          │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Admin UI      │    │  Public Website │    │   Parent        │
│   (React SPA)   │    │  (Marketing)    │    │   Portal        │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │     FastAPI Gateway     │
                    │   (Load Balancer)       │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Workflow Engine       │
                    │  (Business Process)     │
                    └────────────┬────────────┘
                                 │
               ┌─────────────────┼─────────────────┐
               │                 │                 │
     ┌─────────▼─────────┐ ┌─────────▼─────────┐ ┌─────────▼─────────┐
     │   Enrollment      │ │   Lesson          │ │   Payment         │
     │   Workflows       │ │   Workflows       │ │   Workflows       │
     └─────────┬─────────┘ └─────────┬─────────┘ └─────────┬─────────┘
               │                     │                     │
               └─────────────────────┼─────────────────────┘
                                     │
                        ┌────────────▼────────────┐
                        │    TaskContext          │
                        │   (State Management)    │
                        └────────────┬────────────┘
                                     │
                     ┌───────────────┼───────────────┐
                     │               │               │
           ┌─────────▼─────────┐ ┌─────────▼─────────┐ │
           │  Business Logic   │ │  External APIs    │ │
           │  Nodes            │ │  (Stripe, Email)  │ │
           └─────────┬─────────┘ └─────────┬─────────┘ │
                     │                     │           │
                     └─────────────────────┼───────────┘
                                           │
                              ┌────────────▼────────────┐
                              │      Supabase           │
                              │  (PostgreSQL + Auth)    │
                              └─────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                            EXTERNAL INTEGRATIONS                               │
├─────────────────┬─────────────────┬─────────────────┬─────────────────────────┤
│   Stripe API    │  Email Service  │   Calendar      │    File Storage         │
│  (Payments)     │  (Brevo/SG)     │   Integration   │   (Supabase)           │
└─────────────────┴─────────────────┴─────────────────┴─────────────────────────┘
```

### Architecture Principles

#### 1. Workflow-Driven Business Processes
- **Business Logic as Workflows:** All complex business processes implemented as DAG workflows
- **Event-Driven Operations:** Asynchronous processing for enrollment, scheduling, and payments
- **Chain of Responsibility:** Sequential processing with context passing between business steps
- **Validation Framework:** Pre-execution validation of business rules and data integrity

#### 2. Single-Owner Operator Focus
- **Essential Features Only:** Core functionality without over-engineering
- **Simplified Operations:** Easy deployment and maintenance for single operator
- **Cost-Effective Architecture:** Leveraging managed services (Supabase) for reduced operational overhead
- **Scalable Foundation:** Architecture supports growth from 50 to 500+ students

#### 3. Type Safety and Business Rules
- **Pydantic Integration:** End-to-end type safety for all business data
- **Schema-Driven Design:** All business entities defined with type-safe schemas
- **Runtime Validation:** Comprehensive validation of business rules and constraints
- **Audit Trail:** Complete tracking of all business operations and changes

## Core Business Workflows

### 1. Student Enrollment Workflow

**Business Process:** Complete student onboarding from initial inquiry to first lesson

```python
class EnrollmentWorkflow(Workflow):
    workflow_schema = WorkflowSchema(
        description="Complete student enrollment and onboarding process",
        event_schema=EnrollmentEventSchema,
        start=ValidateEnrollmentNode,
        nodes=[
            NodeConfig(
                node=ValidateEnrollmentNode,
                connections=[CreateStudentAccountNode],
                description="Validate enrollment data and business rules"
            ),
            NodeConfig(
                node=CreateStudentAccountNode,
                connections=[SetupPaymentMethodNode],
                description="Create student and parent accounts in Supabase"
            ),
            NodeConfig(
                node=SetupPaymentMethodNode,
                connections=[AssignTeacherNode],
                description="Setup Stripe payment method and subscription"
            ),
            NodeConfig(
                node=AssignTeacherNode,
                connections=[ScheduleDemoLessonNode],
                description="Assign teacher based on instrument and availability"
            ),
            NodeConfig(
                node=ScheduleDemoLessonNode,
                connections=[SendWelcomeEmailsNode],
                description="Schedule initial demo lesson"
            ),
            NodeConfig(
                node=SendWelcomeEmailsNode,
                connections=[],
                description="Send welcome emails to student and parent"
            )
        ]
    )
```

**Key Workflow Nodes:**

```python
class ValidateEnrollmentNode(Node):
    """Validate enrollment data and business rules"""
    
    async def process(self, task_context: TaskContext) -> TaskContext:
        enrollment_data = task_context.event
        
        # Validate student age requirements
        if enrollment_data.student_age < 5:
            task_context.stop_workflow()
            task_context.update_node(
                self.node_name,
                error="Student must be at least 5 years old",
                status="rejected"
            )
            return task_context
        
        # Check teacher availability for instrument
        available_teachers = await self._check_teacher_availability(
            enrollment_data.instrument
        )
        
        if not available_teachers:
            task_context.stop_workflow()
            task_context.update_node(
                self.node_name,
                error=f"No teachers available for {enrollment_data.instrument}",
                status="waitlisted"
            )
            return task_context
        
        task_context.update_node(
            self.node_name,
            validation_status="passed",
            available_teachers=available_teachers
        )
        
        return task_context

class SetupPaymentMethodNode(Node):
    """Setup Stripe payment method and subscription"""
    
    async def process(self, task_context: TaskContext) -> TaskContext:
        enrollment_data = task_context.event
        student_data = task_context.nodes["CreateStudentAccountNode"]
        
        try:
            # Create Stripe customer
            stripe_customer = await self._create_stripe_customer(
                email=enrollment_data.parent_email,
                name=enrollment_data.parent_name,
                student_id=student_data["student_id"]
            )
            
            # Setup payment method
            payment_method = await self._setup_payment_method(
                customer_id=stripe_customer.id,
                payment_token=enrollment_data.payment_token
            )
            
            # Create subscription for lessons
            subscription = await self._create_lesson_subscription(
                customer_id=stripe_customer.id,
                payment_method_id=payment_method.id,
                lesson_rate=enrollment_data.lesson_rate
            )
            
            task_context.update_node(
                self.node_name,
                stripe_customer_id=stripe_customer.id,
                payment_method_id=payment_method.id,
                subscription_id=subscription.id,
                status="payment_setup_complete"
            )
            
        except Exception as e:
            task_context.update_node(
                self.node_name,
                error=f"Payment setup failed: {str(e)}",
                status="payment_failed"
            )
            # Continue workflow - manual payment setup can be done later
        
        return task_context
```

### 2. Lesson Scheduling Workflow

**Business Process:** Automated lesson scheduling with teacher availability and student preferences

```python
class LessonSchedulingWorkflow(Workflow):
    workflow_schema = WorkflowSchema(
        description="Automated lesson scheduling and management",
        event_schema=LessonSchedulingEventSchema,
        start=CheckAvailabilityNode,
        nodes=[
            NodeConfig(
                node=CheckAvailabilityNode,
                connections=[SchedulingRouterNode],
                description="Check teacher and student availability"
            ),
            NodeConfig(
                node=SchedulingRouterNode,
                connections=[ScheduleLessonNode, SuggestAlternativesNode],
                is_router=True,
                description="Route based on availability results"
            ),
            NodeConfig(
                node=ScheduleLessonNode,
                connections=[SendConfirmationNode],
                description="Create lesson booking"
            ),
            NodeConfig(
                node=SuggestAlternativesNode,
                connections=[],
                description="Suggest alternative times"
            ),
            NodeConfig(
                node=SendConfirmationNode,
                connections=[],
                description="Send lesson confirmation emails"
            )
        ]
    )
```

### 3. Payment Processing Workflow

**Business Process:** Automated payment collection and reconciliation

```python
class PaymentProcessingWorkflow(Workflow):
    workflow_schema = WorkflowSchema(
        description="Automated payment processing and reconciliation",
        event_schema=PaymentEventSchema,
        start=ProcessPaymentNode,
        nodes=[
            NodeConfig(
                node=ProcessPaymentNode,
                connections=[PaymentRouterNode],
                description="Process payment through Stripe"
            ),
            NodeConfig(
                node=PaymentRouterNode,
                connections=[PaymentSuccessNode, PaymentFailureNode],
                is_router=True,
                description="Route based on payment result"
            ),
            NodeConfig(
                node=PaymentSuccessNode,
                connections=[UpdateAccountingNode],
                description="Handle successful payment"
            ),
            NodeConfig(
                node=PaymentFailureNode,
                connections=[RetryPaymentNode],
                description="Handle failed payment"
            ),
            NodeConfig(
                node=UpdateAccountingNode,
                connections=[SendReceiptNode],
                description="Update accounting records"
            ),
            NodeConfig(
                node=SendReceiptNode,
                connections=[],
                description="Send payment receipt"
            )
        ]
    )
```

## Technology Stack Architecture

### Core Framework Stack

#### Python 3.11+ Runtime with Music School Extensions
```python
# Core Dependencies
fastapi==0.104.1          # Modern async web framework
pydantic==2.5.0           # Data validation and serialization
pydantic-ai==0.0.14       # AI integration for smart scheduling
sqlalchemy==2.0.23        # Async ORM with Supabase integration
alembic==1.13.0           # Database migration management
stripe==7.8.0             # Payment processing
supabase==2.3.0           # Backend-as-a-Service
celery==5.3.4             # Background task processing
redis==5.0.1              # Caching and task queue
```

#### Application Structure
```
app/
├── main.py                     # FastAPI application entry point
├── core/                       # Core framework components
│   ├── workflow.py            # Workflow orchestration engine
│   ├── task.py                # TaskContext state management
│   ├── schema.py              # Pydantic schema definitions
│   ├── validate.py            # Workflow validation framework
│   └── nodes/                 # Node architecture components
│       ├── base.py           # Abstract base node
│       ├── business.py       # Business logic nodes
│       ├── integration.py    # External API integration nodes
│       └── router.py         # Conditional routing nodes
├── workflows/                 # Music school business workflows
│   ├── enrollment_workflow.py
│   ├── lesson_scheduling_workflow.py
│   ├── payment_processing_workflow.py
│   └── workflow_nodes/
│       ├── enrollment/
│       ├── scheduling/
│       └── payment/
├── schemas/                   # Business domain schemas
│   ├── student_schema.py
│   ├── lesson_schema.py
│   ├── payment_schema.py
│   └── enrollment_schema.py
├── models/                    # Database models
│   ├── student.py
│   ├── teacher.py
│   ├── lesson.py
│   └── payment.py
├── services/                  # Business logic services
│   ├── student_service.py
│   ├── lesson_service.py
│   ├── payment_service.py
│   └── email_service.py
├── api/                       # FastAPI endpoints
│   ├── students.py
│   ├── lessons.py
│   ├── payments.py
│   └── enrollments.py
└── database/                  # Database integration
    ├── session.py
    ├── repository.py
    └── migrations/
```

## Business Domain Models

### Core Business Entities

```python
# Student Domain Model
class Student(BaseModel):
    id: Optional[int] = None
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    date_of_birth: date
    parent_id: int
    teacher_id: Optional[int] = None
    instrument: str = Field(..., regex=r'^(piano|guitar|violin|drums|voice)$')
    skill_level: str = Field(default="beginner", regex=r'^(beginner|intermediate|advanced)$')
    enrollment_date: date
    is_active: bool = True
    lesson_rate: Decimal = Field(..., ge=30, le=200)  # CAD per lesson
    
    @property
    def age(self) -> int:
        return (date.today() - self.date_of_birth).days // 365
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
    
    def can_schedule_lesson(self) -> bool:
        """Business rule: Active students with assigned teachers can schedule"""
        return self.is_active and self.teacher_id is not None

# Teacher Domain Model
class Teacher(BaseModel):
    id: Optional[int] = None
    user_id: int
    instruments: List[str] = Field(..., min_items=1)
    hourly_rate: Decimal = Field(..., ge=30, le=200)
    max_students: int = Field(default=30, ge=1, le=50)
    is_available: bool = True
    availability_schedule: Dict[str, List[str]] = Field(default_factory=dict)
    
    def can_accept_student(self, current_student_count: int) -> bool:
        """Business rule: Teachers can accept students up to their maximum"""
        return self.is_available and current_student_count < self.max_students

# Lesson Domain Model
class Lesson(BaseModel):
    id: Optional[int] = None
    student_id: int
    teacher_id: int
    scheduled_at: datetime
    duration_minutes: int = Field(default=30, ge=15, le=120)
    status: str = Field(default="scheduled", regex=r'^(scheduled|completed|cancelled|rescheduled)$')
    lesson_type: str = Field(default="regular", regex=r'^(demo|regular|makeup)$')
    notes: Optional[str] = None
    payment_status: str = Field(default="pending", regex=r'^(pending|paid|failed)$')
    
    @property
    def end_time(self) -> datetime:
        return self.scheduled_at + timedelta(minutes=self.duration_minutes)
    
    def can_be_rescheduled(self) -> bool:
        """Business rule: Lessons can be rescheduled up to 24 hours before"""
        return (self.scheduled_at - datetime.now()).total_seconds() > 86400

# Payment Domain Model
class Payment(BaseModel):
    id: Optional[int] = None
    student_id: int
    lesson_id: Optional[int] = None
    stripe_payment_intent_id: str
    amount: Decimal = Field(..., ge=0)
    currency: str = Field(default="CAD")
    status: str = Field(..., regex=r'^(pending|succeeded|failed|cancelled)$')
    payment_method: str = Field(..., regex=r'^(card|bank_transfer|cash)$')
    payment_date: Optional[datetime] = None
    failure_reason: Optional[str] = None
```

### Business Event Schemas

```python
# Enrollment Event Schema
class EnrollmentEventSchema(BaseModel):
    # Student Information
    student_first_name: str = Field(..., min_length=1, max_length=50)
    student_last_name: str = Field(..., min_length=1, max_length=50)
    student_date_of_birth: date
    student_email: Optional[str] = None
    
    # Parent Information
    parent_first_name: str = Field(..., min_length=1, max_length=50)
    parent_last_name: str = Field(..., min_length=1, max_length=50)
    parent_email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    parent_phone: str = Field(..., regex=r'^\+?1?[0-9]{10}$')
    
    # Lesson Preferences
    instrument: str = Field(..., regex=r'^(piano|guitar|violin|drums|voice)$')
    preferred_lesson_day: Optional[str] = Field(None, regex=r'^(monday|tuesday|wednesday|thursday|friday|saturday)$')
    preferred_lesson_time: Optional[str] = Field(None, regex=r'^(morning|afternoon|evening)$')
    lesson_duration: int = Field(default=30, ge=15, le=60)
    
    # Payment Information
    payment_token: str  # Stripe payment method token
    agreed_to_terms: bool = Field(..., const=True)
    
    @validator('student_date_of_birth')
    def validate_student_age(cls, v):
        age = (date.today() - v).days // 365
        if age < 5:
            raise ValueError('Student must be at least 5 years old')
        if age > 18:
            raise ValueError('Student enrollment requires parent information')
        return v

# Lesson Scheduling Event Schema
class LessonSchedulingEventSchema(BaseModel):
    student_id: int
    teacher_id: Optional[int] = None  # Auto-assign if not provided
    preferred_datetime: datetime
    duration_minutes: int = Field(default=30, ge=15, le=120)
    lesson_type: str = Field(default="regular", regex=r'^(demo|regular|makeup)$')
    recurring: bool = False
    recurrence_pattern: Optional[str] = Field(None, regex=r'^(weekly|biweekly|monthly)$')
    notes: Optional[str] = None
    
    @validator('preferred_datetime')
    def validate_future_datetime(cls, v):
        if v <= datetime.now():
            raise ValueError('Lesson must be scheduled in the future')
        return v

# Payment Processing Event Schema
class PaymentEventSchema(BaseModel):
    student_id: int
    lesson_id: Optional[int] = None
    amount: Decimal = Field(..., ge=0)
    payment_method_id: str  # Stripe payment method ID
    currency: str = Field(default="CAD")
    description: str
    automatic_payment: bool = True
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Payment amount must be greater than 0')
        if v > 500:  # Maximum lesson cost
            raise ValueError('Payment amount exceeds maximum allowed')
        return v
```

## Workflow Node Implementations

### Business Logic Nodes

```python
class CreateStudentAccountNode(Node):
    """Create student and parent accounts in Supabase"""
    
    async def process(self, task_context: TaskContext) -> TaskContext:
        enrollment_data = task_context.event
        
        try:
            # Create parent user account
            parent_user = await self._create_supabase_user(
                email=enrollment_data.parent_email,
                password=self._generate_temp_password(),
                user_metadata={
                    "first_name": enrollment_data.parent_first_name,
                    "last_name": enrollment_data.parent_last_name,
                    "phone": enrollment_data.parent_phone,
                    "role": "parent"
                }
            )
            
            # Create student record
            student = await self._create_student_record(
                first_name=enrollment_data.student_first_name,
                last_name=enrollment_data.student_last_name,
                date_of_birth=enrollment_data.student_date_of_birth,
                email=enrollment_data.student_email,
                parent_id=parent_user.id,
                instrument=enrollment_data.instrument
            )
            
            task_context.update_node(
                self.node_name,
                parent_user_id=parent_user.id,
                student_id=student.id,
                temp_password=self._generate_temp_password(),
                status="accounts_created"
            )
            
        except Exception as e:
            task_context.update_node(
                self.node_name,
                error=f"Account creation failed: {str(e)}",
                status="account_creation_failed"
            )
            task_context.stop_workflow()
        
        return task_context

class AssignTeacherNode(Node):
    """Assign teacher based on instrument and availability"""
    
    async def process(self, task_context: TaskContext) -> TaskContext:
        enrollment_data = task_context.event
        validation_data = task_context.nodes["ValidateEnrollmentNode"]
        
        available_teachers = validation_data["available_teachers"]
        
        # Smart teacher assignment algorithm
        best_teacher = await self._select_best_teacher(
            available_teachers=available_teachers,
            instrument=enrollment_data.instrument,
            preferred_day=enrollment_data.preferred_lesson_day,
            preferred_time=enrollment_data.preferred_lesson_time
        )
        
        if not best_teacher:
            task_context.update_node(
                self.node_name,
                error="No suitable teacher found",
                status="teacher_assignment_failed"
            )
            task_context.stop_workflow()
            return task_context
        
        # Update student record with assigned teacher
        await self._assign_teacher_to_student(
            student_id=task_context.nodes["CreateStudentAccountNode"]["student_id"],
            teacher_id=best_teacher.id
        )
        
        task_context.update_node(
            self.node_name,
            assigned_teacher_id=best_teacher.id,
            teacher_name=f"{best_teacher.first_name} {best_teacher.last_name}",
            teacher_email=best_teacher.email,
            status="teacher_assigned"
        )
        
        return task_context
    
    async def _select_best_teacher(self, available_teachers, instrument, preferred_day, preferred_time):
        """AI-powered teacher selection based on multiple criteria"""
        # This could use AI to optimize teacher-student matching
        # For now, simple algorithm based on availability and student count
        
        best_teacher = None
        best_score = 0
        
        for teacher in available_teachers:
            score = 0
            
            # Instrument match (required)
            if instrument in teacher.instruments:
                score += 10
            else:
                continue
            
            # Availability match
            if preferred_day and preferred_day in teacher.availability_schedule:
                score += 5
                if preferred_time in teacher.availability_schedule[preferred_day]:
                    score += 3
            
            # Student load (prefer teachers with fewer students)
            current_students = await self._get_teacher_student_count(teacher.id)
            load_factor = 1 - (current_students / teacher.max_students)
            score += load_factor * 5
            
            if score > best_score:
                best_score = score
                best_teacher = teacher
        
        return best_teacher

class ScheduleDemoLessonNode(Node):
    """Schedule initial demo lesson"""
    
    async def process(self, task_context: TaskContext) -> TaskContext:
        enrollment_data = task_context.event
        student_data = task_context.nodes["CreateStudentAccountNode"]
        teacher_data = task_context.nodes["AssignTeacherNode"]
        
        try:
            # Find next available slot for demo lesson
            demo_slot = await self._find_next_available_slot(
                teacher_id=teacher_data["assigned_teacher_id"],
                preferred_day=enrollment_data.preferred_lesson_day,
                preferred_time=enrollment_data.preferred_lesson_time,
                duration=enrollment_data.lesson_duration
            )
            
            if not demo_slot:
                task_context.update_node(
                    self.node_name,
                    error="No available demo lesson slots",
                    status="scheduling_failed"
                )
                return task_context
            
            # Create demo lesson
            demo_lesson = await self._create_lesson(
                student_id=student_data["student_id"],
                teacher_id=teacher_data["assigned_teacher_id"],
                scheduled_at=demo_slot,
                duration_minutes=enrollment_data.lesson_duration,
                lesson_type="demo",
                notes="Initial demo lesson - new student enrollment"
            )
            
            task_context.update_node(
                self.node_name,
                demo_lesson_id=demo_lesson.id,
                demo_lesson_datetime=demo_slot.isoformat(),
                status="demo_lesson_scheduled"
            )
            
        except Exception as e:
            task_context.update_node(
                self.node_name,
                error=f"Demo lesson scheduling failed: {str(e)}",
                status="scheduling_failed"
            )
        
        return task_context
```

### Integration Nodes

```python
class SendWelcomeEmailsNode(Node):
    """Send welcome emails to student and parent"""
    
    async def process(self, task_context: TaskContext) -> TaskContext:
        enrollment_data = task_context.event
        student_data = task_context.nodes["CreateStudentAccountNode"]
        teacher_data = task_context.nodes["AssignTeacherNode"]
        lesson_data = task_context.nodes["ScheduleDemoLessonNode"]
        
        try:
            # Send parent welcome email
            await self._send_email(
                to_email=enrollment_data.parent_email,
                template="parent_welcome",
                context={
                    "parent_name": enrollment_data.parent_first_name,
                    "student_name": enrollment_data.student_first_name,
                    "teacher_name": teacher_data["teacher_name"],
                    "demo_lesson_datetime": lesson_data["demo_lesson_datetime"],
                    "temp_password": student_data["temp_password"],
                    "login_url": "https://cedarheights.academy/login"
                }
            )
            
            # Send teacher notification email
            await self._send_email(
                to_email=teacher_data["teacher_email"],
                template="new_student_notification",
                context={
                    "teacher_name": teacher_data["teacher_name"],
                    "student_name": f"{enrollment_data.student_first_name} {enrollment_data.student_last_name}",
                    "parent_name": f"{enrollment_data.parent_first_name} {enrollment_data.parent_last_name}",
                    "instrument": enrollment_data.instrument,
                    "demo_lesson_datetime": lesson_data["demo_lesson_datetime"]
                }
            )
            
            task_context.update_node(
                self.node_name,
                parent_email_sent=True,
                teacher_email_sent=True,
                status="welcome_emails_sent"
            )
            
        except Exception as e:
            task_context.update_node(
                self.node_name,
                error=f"Email sending failed: {str(e)}",
                status="email_failed"
            )
            # Don't stop workflow - emails can be sent manually
        
        return task_context

class ProcessPaymentNode(Node):
    """Process payment through Stripe"""
    
    async def process(self, task_context: TaskContext) -> TaskContext:
        payment_data = task_context.event
        
        try:
            # Create payment intent
            payment_intent = await self._create_stripe_payment_intent(
                amount=int(payment_data.amount * 100),  # Convert to cents
                currency=payment_data.currency,
                payment_method=payment_data.payment_method_id,
                description=payment_data.description,
                automatic_payment_methods={"enabled": True}
            )
            
            # Confirm payment
            confirmed_payment = await self._confirm_payment_intent(
                payment_intent_id=payment_intent.id
            )
            
            task_context.update_node(
                self.node_name,
                payment_intent_id=payment_intent.id,
                payment_status=confirmed_payment.status,
                amount_received=confirmed_payment.amount_received / 100,
                status="payment_processed"
            )
            
        except Exception as e:
            task_context.update_node(
                self.node_name,
                error=f"Payment processing failed: {str(e)}",
                status="payment_failed"
            )
        
        return task_context
```

## API Layer Architecture

### FastAPI Application with Business Endpoints

```python
# api/enrollments.py
from fastapi import APIRouter, Depends, HTTPException
from app.workflows.enrollment_workflow import EnrollmentWorkflow
from app.schemas.enrollment_schema import EnrollmentEventSchema

router = APIRouter()

@router.post("/enrollments", response_model=Dict[str, Any])
async def create_enrollment(
    enrollment_data: En
rollment_data: EnrollmentEventSchema,
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Create new student enrollment through workflow"""
    
    try:
        # Execute enrollment workflow
        workflow = EnrollmentWorkflow()
        result = await workflow.run_async(enrollment_data.dict())
        
        return {
            "success": True,
            "enrollment_id": result.nodes.get("CreateStudentAccountNode", {}).get("student_id"),
            "workflow_status": "completed" if not result.should_stop else "failed",
            "demo_lesson": result.nodes.get("ScheduleDemoLessonNode", {}),
            "teacher_assigned": result.nodes.get("AssignTeacherNode", {}),
            "execution_time": result.metadata.get("execution_time"),
            "nodes_executed": len(result.nodes)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Enrollment workflow failed: {str(e)}"
        )

@router.get("/enrollments/{enrollment_id}/status")
async def get_enrollment_status(
    enrollment_id: int,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get enrollment status and progress"""
    
    # Implementation would check workflow execution status
    # and return current state of enrollment process
    pass

# api/lessons.py
@router.post("/lessons/schedule", response_model=Dict[str, Any])
async def schedule_lesson(
    lesson_data: LessonSchedulingEventSchema,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Schedule lesson through workflow"""
    
    try:
        workflow = LessonSchedulingWorkflow()
        result = await workflow.run_async(lesson_data.dict())
        
        return {
            "success": True,
            "lesson_id": result.nodes.get("ScheduleLessonNode", {}).get("lesson_id"),
            "scheduled_datetime": result.nodes.get("ScheduleLessonNode", {}).get("scheduled_datetime"),
            "teacher_id": result.nodes.get("CheckAvailabilityNode", {}).get("assigned_teacher_id"),
            "workflow_status": "completed" if not result.should_stop else "failed"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lesson scheduling failed: {str(e)}"
        )

# api/payments.py
@router.post("/payments/process", response_model=Dict[str, Any])
async def process_payment(
    payment_data: PaymentEventSchema,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Process payment through workflow"""
    
    try:
        workflow = PaymentProcessingWorkflow()
        result = await workflow.run_async(payment_data.dict())
        
        return {
            "success": True,
            "payment_id": result.nodes.get("ProcessPaymentNode", {}).get("payment_intent_id"),
            "payment_status": result.nodes.get("ProcessPaymentNode", {}).get("payment_status"),
            "amount_charged": result.nodes.get("ProcessPaymentNode", {}).get("amount_received"),
            "receipt_sent": result.nodes.get("SendReceiptNode", {}).get("receipt_sent", False)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Payment processing failed: {str(e)}"
        )
```

### Authentication and Authorization

```python
# core/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Extract and validate current user from Supabase JWT token"""
    
    token = credentials.credentials
    
    try:
        # Verify JWT with Supabase
        supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
        user_response = supabase_client.auth.get_user(token)
        
        if not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
        
        # Get user details from database
        user = await get_user_by_supabase_id(user_response.user.id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return user
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )

async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Require admin role for sensitive operations"""
    
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user
```

## Database Architecture

### Supabase Integration with Row Level Security

```sql
-- Core Tables Schema
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    supabase_user_id UUID UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'teacher', 'parent')),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE teachers (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    instruments TEXT[] NOT NULL,
    hourly_rate DECIMAL(10,2) NOT NULL CHECK (hourly_rate >= 30 AND hourly_rate <= 200),
    max_students INTEGER DEFAULT 30 CHECK (max_students >= 1 AND max_students <= 50),
    is_available BOOLEAN DEFAULT true,
    availability_schedule JSONB DEFAULT '{}',
    bio TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE students (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    date_of_birth DATE NOT NULL,
    parent_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    teacher_id INTEGER REFERENCES teachers(id),
    instrument VARCHAR(50) NOT NULL CHECK (instrument IN ('piano', 'guitar', 'violin', 'drums', 'voice')),
    skill_level VARCHAR(20) DEFAULT 'beginner' CHECK (skill_level IN ('beginner', 'intermediate', 'advanced')),
    lesson_rate DECIMAL(10,2) NOT NULL CHECK (lesson_rate >= 30 AND lesson_rate <= 200),
    enrollment_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT true,
    stripe_customer_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE lessons (
    id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES students(id) ON DELETE CASCADE,
    teacher_id INTEGER REFERENCES teachers(id) ON DELETE CASCADE,
    scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL,
    duration_minutes INTEGER DEFAULT 30 CHECK (duration_minutes >= 15 AND duration_minutes <= 120),
    lesson_type VARCHAR(20) DEFAULT 'regular' CHECK (lesson_type IN ('demo', 'regular', 'makeup')),
    status VARCHAR(20) DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'completed', 'cancelled', 'rescheduled')),
    payment_status VARCHAR(20) DEFAULT 'pending' CHECK (payment_status IN ('pending', 'paid', 'failed')),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES students(id) ON DELETE CASCADE,
    lesson_id INTEGER REFERENCES lessons(id),
    stripe_payment_intent_id VARCHAR(255) NOT NULL,
    amount DECIMAL(10,2) NOT NULL CHECK (amount >= 0),
    currency VARCHAR(3) DEFAULT 'CAD',
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'succeeded', 'failed', 'cancelled')),
    payment_method VARCHAR(20) NOT NULL CHECK (payment_method IN ('card', 'bank_transfer', 'cash')),
    payment_date TIMESTAMP WITH TIME ZONE,
    failure_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Workflow execution tracking
CREATE TABLE workflow_executions (
    id SERIAL PRIMARY KEY,
    workflow_name VARCHAR(100) NOT NULL,
    event_data JSONB NOT NULL,
    task_context JSONB NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('running', 'completed', 'failed', 'terminated')),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT
);

-- Row Level Security Policies
ALTER TABLE students ENABLE ROW LEVEL SECURITY;
ALTER TABLE lessons ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;

-- Students: Parents can see their own students, teachers can see their assigned students, admins see all
CREATE POLICY "Users can view relevant students" ON students
    FOR SELECT USING (
        auth.uid() IN (
            SELECT supabase_user_id FROM users 
            WHERE (
                (role = 'admin') OR
                (role = 'parent' AND id = students.parent_id) OR
                (role = 'teacher' AND id = (SELECT user_id FROM teachers WHERE id = students.teacher_id))
            )
        )
    );

-- Lessons: Similar access pattern as students
CREATE POLICY "Users can view relevant lessons" ON lessons
    FOR SELECT USING (
        auth.uid() IN (
            SELECT supabase_user_id FROM users 
            WHERE (
                (role = 'admin') OR
                (role = 'parent' AND id = (SELECT parent_id FROM students WHERE id = lessons.student_id)) OR
                (role = 'teacher' AND id = (SELECT user_id FROM teachers WHERE id = lessons.teacher_id))
            )
        )
    );
```

## Deployment Architecture

### Docker Configuration for Single-Owner Operator

```dockerfile
# docker/Dockerfile.api
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY alembic.ini .
COPY alembic/ ./alembic/

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser
RUN chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker/docker-compose.yml - Single-Owner Operator Stack
version: '3.8'

services:
  # Main API service
  api:
    build:
      context: ..
      dockerfile: docker/Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${SUPABASE_DATABASE_URL}
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
      - STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY}
      - EMAIL_API_KEY=${EMAIL_API_KEY}
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs

  # Background task processing
  celery:
    build:
      context: ..
      dockerfile: docker/Dockerfile.api
    command: celery -A app.worker.celery_app worker --loglevel=info
    environment:
      - DATABASE_URL=${SUPABASE_DATABASE_URL}
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
      - STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY}
      - EMAIL_API_KEY=${EMAIL_API_KEY}
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
    depends_on:
      - redis
    restart: unless-stopped

  # Redis for caching and task queue
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  # Nginx reverse proxy
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api
    restart: unless-stopped

volumes:
  redis_data:
```

## Testing Architecture

### Workflow Testing Framework

```python
# tests/test_enrollment_workflow.py
import pytest
from unittest.mock import AsyncMock, patch
from app.workflows.enrollment_workflow import EnrollmentWorkflow
from app.schemas.enrollment_schema import EnrollmentEventSchema

@pytest.mark.asyncio
async def test_complete_enrollment_workflow():
    """Test complete enrollment workflow execution"""
    
    # Setup test data
    enrollment_data = {
        "student_first_name": "Emma",
        "student_last_name": "Johnson",
        "student_date_of_birth": "2015-03-15",
        "parent_first_name": "Sarah",
        "parent_last_name": "Johnson",
        "parent_email": "sarah.johnson@email.com",
        "parent_phone": "9025551234",
        "instrument": "piano",
        "preferred_lesson_day": "tuesday",
        "preferred_lesson_time": "afternoon",
        "lesson_duration": 30,
        "payment_token": "pm_test_token",
        "agreed_to_terms": True
    }
    
    # Mock external services
    with patch('app.workflows.workflow_nodes.enrollment.create_supabase_user') as mock_create_user, \
         patch('app.workflows.workflow_nodes.enrollment.create_stripe_customer') as mock_stripe, \
         patch('app.workflows.workflow_nodes.enrollment.send_email') as mock_email:
        
        # Setup mocks
        mock_create_user.return_value = AsyncMock(id=123)
        mock_stripe.return_value = AsyncMock(id="cus_test123")
        mock_email.return_value = True
        
        # Execute workflow
        workflow = EnrollmentWorkflow()
        result = await workflow.run_async(enrollment_data)
        
        # Validate workflow completion
        assert not result.should_stop
        assert "CreateStudentAccountNode" in result.nodes
        assert "AssignTeacherNode" in result.nodes
        assert "ScheduleDemoLessonNode" in result.nodes
        assert "SendWelcomeEmailsNode" in result.nodes
        
        # Validate business logic
        student_data = result.nodes["CreateStudentAccountNode"]
        assert student_data["status"] == "accounts_created"
        
        teacher_data = result.nodes["AssignTeacherNode"]
        assert teacher_data["status"] == "teacher_assigned"
        assert "assigned_teacher_id" in teacher_data

@pytest.mark.asyncio
async def test_enrollment_validation_failure():
    """Test enrollment workflow with validation failure"""
    
    # Test data with invalid student age
    enrollment_data = {
        "student_first_name": "Tommy",
        "student_last_name": "Smith",
        "student_date_of_birth": "2020-01-01",  # Too young
        "parent_first_name": "John",
        "parent_last_name": "Smith",
        "parent_email": "john.smith@email.com",
        "parent_phone": "9025551234",
        "instrument": "piano",
        "payment_token": "pm_test_token",
        "agreed_to_terms": True
    }
    
    workflow = EnrollmentWorkflow()
    result = await workflow.run_async(enrollment_data)
    
    # Validate workflow stopped due to validation failure
    assert result.should_stop
    assert result.nodes["ValidateEnrollmentNode"]["status"] == "rejected"
    assert "must be at least 5 years old" in result.nodes["ValidateEnrollmentNode"]["error"]
```

## Implementation Roadmap

### Phase 1: Core Infrastructure (Weeks 1-4)
- [ ] **Workflow Engine Setup**
  - Implement base workflow orchestration framework
  - Create TaskContext and validation systems
  - Setup FastAPI application structure
  
- [ ] **Database Foundation**
  - Setup Supabase integration
  - Create core database schema with RLS policies
  - Implement basic CRUD operations
  
- [ ] **Authentication System**
  - Integrate Supabase Auth
  - Implement JWT token validation
  - Setup role-based access control

### Phase 2: Core Business Workflows (Weeks 5-8)
- [ ] **Enrollment Workflow**
  - Implement complete enrollment process
  - Student and parent account creation
  - Teacher assignment algorithm
  - Demo lesson scheduling
  
- [ ] **Payment Integration**
  - Stripe payment processing workflow
  - Subscription management
  - Payment failure handling and retry logic
  
- [ ] **Email Notifications**
  - Welcome email templates
  - Lesson confirmation emails
  - Payment receipts and reminders

### Phase 3: Lesson Management (Weeks 9-12)
- [ ] **Lesson Scheduling Workflow**
  - Teacher availability checking
  - Automated lesson scheduling
  - Conflict resolution and alternatives
  
- [ ] **Calendar Integration**
  - Teacher calendar management
  - Student lesson calendar
  - Rescheduling workflows
  
- [ ] **Lesson Tracking**
  - Lesson completion tracking
  - Progress notes and feedback
  - Makeup lesson scheduling

### Phase 4: Production Deployment (Weeks 13-16)
- [ ] **Docker Containerization**
  - Production-ready Docker setup
  - Docker Compose orchestration
  - Health checks and monitoring
  
- [ ] **Security Hardening**
  - SSL/TLS configuration
  - Rate limiting implementation
  - Security audit and testing
  
- [ ] **Monitoring and Logging**
  - Structured logging implementation
  - Application performance monitoring
  - Error tracking and alerting

### Phase 5: Advanced Features (Weeks 17-20)
- [ ] **Business Intelligence**
  - Student progress tracking
  - Revenue and payment analytics
  - Teacher performance metrics
  
- [ ] **Automated Communications**
  - Lesson reminder workflows
  - Payment due notifications
  - Student progress reports
  
- [ ] **System Optimization**
  - Performance optimization
  - Caching implementation
  - Database query optimization

## Success Metrics and Validation

### Technical Metrics
- **Response Time**: <200ms for 95% of API operations
- **Workflow Execution**: <30 seconds for complete enrollment process
- **Availability**: 99.5% uptime with automated recovery
- **Test Coverage**: >85% code coverage across all modules
- **Security**: Zero critical vulnerabilities in security scans

### Business Metrics
- **Enrollment Automation**: 95% reduction in manual enrollment processing
- **Payment Success Rate**: 99% payment success rate with automated retry
- **User Experience**: <5 second page load times for all operations
- **Data Accuracy**: 100% financial reconciliation accuracy
- **Operational Efficiency**: 70% reduction in administrative overhead

### Single-Owner Operator Benefits
- **Simplified Operations**: One-command deployment and updates
- **Cost Effectiveness**: <$100/month operational costs for 100+ students
- **Maintenance Efficiency**: <2 hours/week system maintenance required
- **Scalability**: Support growth from 50 to 500+ students without architectural changes
- **Reliability**: Automated backup and recovery procedures

## Conclusion

The Cedar Heights Music Academy Synthesized Architecture successfully combines the business domain expertise of music school management with the technical sophistication of workflow orchestration. This architecture provides:

1. **Workflow-Driven Business Logic**: All complex business processes implemented as type-safe, validated workflows
2. **Single-Owner Operator Focus**: Simplified deployment and maintenance suitable for individual operators
3. **Scalable Foundation**: Architecture supports growth while maintaining operational simplicity
4. **Modern Technology Stack**: Leveraging proven technologies (FastAPI, Supabase, Stripe) for reliability
5. **Comprehensive Automation**: Automated enrollment, scheduling, and payment processing workflows

This synthesized approach ensures that the music academy can operate efficiently with minimal manual intervention while providing excellent service to students and parents through automated, reliable business processes.

---

**Document Version:** 1.0  
**Last Updated:** 2024-12-07  
**Architecture Type:** Synthesized Workflow-Driven Business System  
**Target Deployment:** Single-Owner Operator Music School Management