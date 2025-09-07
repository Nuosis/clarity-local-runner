# Cedar Heights Music Academy — GenAI Launchpad-Powered Backend System Product Requirements Document

## Executive Summary

Cedar Heights Music Academy will leverage the GenAI Launchpad DAG-based workflow orchestration framework as the foundation for its comprehensive Python backend API system. This approach combines the power of type-safe, event-driven workflow orchestration with the specific business requirements of a solo-managed music school, creating a scalable, maintainable system that reduces administrative overhead by 60% while supporting growth to 100+ students.

**Primary Business Outcome:** Enable efficient solo-preneur management of a growing music school through a robust, workflow-driven backend that automates complex business processes while providing fast, reliable APIs for the React frontend.

**Technical Approach:** Build the Cedar Heights backend as a collection of specialized workflows within the GenAI Launchpad framework, leveraging DAG-based processing for complex operations while maintaining <200ms response times for simple API calls.

**Timeline:** MVP delivery within 4-6 months, with the GenAI Launchpad framework providing accelerated development through pre-built workflow patterns and type-safe orchestration.

## Product Vision and Unified Objectives

**Vision:** Create a workflow-driven music school management system that demonstrates the power of the GenAI Launchpad framework for real-world business applications, while delivering exceptional performance and maintainability for Cedar Heights Music Academy.

**Primary Objectives:**
1. **Workflow-Driven Architecture:** Leverage GenAI Launchpad's DAG orchestration for complex business processes
2. **API Performance:** Achieve <200ms for quick operations, <2s for workflow-orchestrated complex operations
3. **Type Safety:** Eliminate runtime errors through end-to-end Pydantic validation across workflows and APIs
4. **Business Process Automation:** Automate enrollment, payment, and scheduling through intelligent workflows
5. **Production Readiness:** Deliver enterprise-grade reliability with comprehensive monitoring and error handling

**Success Metrics:**
- **Development Velocity:** 50% reduction in backend development time through workflow reuse
- **System Performance:** <200ms API response times, <2s workflow completion times
- **Error Reduction:** 95% elimination of runtime errors through type safety
- **Business Automation:** 60% reduction in administrative overhead through workflow automation
- **System Reliability:** 99.9% uptime with automated failover and recovery

## System Architecture Overview

### Core Architecture: GenAI Launchpad + Cedar Heights Integration

```
┌─────────────────────────────────────────────────────────────┐
│                    React Frontend                           │
└─────────────────────┬───────────────────────────────────────┘
                      │ REST API Calls
┌─────────────────────▼───────────────────────────────────────┐
│                FastAPI Layer                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Quick APIs    │  │  Workflow APIs  │  │  Public APIs │ │
│  │   (<200ms)      │  │   (<2s)         │  │              │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              GenAI Launchpad Framework                      │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                Workflow Engine                          │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐ │ │
│  │  │ Enrollment  │ │  Payment    │ │    Scheduling       │ │ │
│  │  │ Workflows   │ │ Workflows   │ │    Workflows        │ │ │
│  │  └─────────────┘ └─────────────┘ └─────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Event-Driven Architecture                  │ │
│  │     Redis Streams + Celery + TaskContext               │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                 Data Layer                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │    Supabase     │  │     Redis       │  │   External   │ │
│  │   PostgreSQL    │  │    Caching      │  │   Services   │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Workflow-API Integration Pattern

The system uses a hybrid approach:
- **Quick Operations:** Direct FastAPI endpoints for simple CRUD operations
- **Complex Operations:** GenAI Launchpad workflows for multi-step business processes
- **Event-Driven Processing:** Background workflows for non-blocking operations

## Core Functional Requirements

### 1. Authentication and Authorization System

#### Quick API Operations (<200ms)
```python
# Direct FastAPI endpoints
@app.post("/api/auth/validate")
async def validate_token(token: str) -> UserInfo:
    """Direct Supabase JWT validation"""

@app.get("/api/auth/me")
async def get_current_user() -> UserProfile:
    """Quick user profile retrieval"""
```

#### Workflow-Driven Operations
```python
class AccountSetupWorkflow(Workflow):
    """Handle complex account creation from enrollment"""
    workflow_schema = WorkflowSchema(
        description="Complete account setup and onboarding",
        event_schema=EnrollmentHandoffSchema,
        start=ValidateEnrollmentNode,
        nodes=[
            NodeConfig(node=ValidateEnrollmentNode, connections=[CreateAccountNode]),
            NodeConfig(node=CreateAccountNode, connections=[SendWelcomeEmailNode]),
            NodeConfig(node=SendWelcomeEmailNode, connections=[SetupPaymentNode]),
            NodeConfig(node=SetupPaymentNode, connections=[CompleteOnboardingNode])
        ]
    )
```

### 2. Student Management System

#### Quick API Operations (<200ms)
```python
@app.get("/api/students")
async def list_students(filters: StudentFilters) -> List[Student]:
    """Fast student listing with filtering"""

@app.get("/api/students/{student_id}")
async def get_student(student_id: int) -> Student:
    """Quick student detail retrieval"""
```

#### Workflow-Driven Operations
```python
class StudentEnrollmentWorkflow(Workflow):
    """Complete student enrollment process"""
    workflow_schema = WorkflowSchema(
        description="End-to-end student enrollment",
        event_schema=EnrollmentRequestSchema,
        start=ValidateEnrollmentNode,
        nodes=[
            NodeConfig(node=ValidateEnrollmentNode, connections=[CheckAvailabilityNode]),
            NodeConfig(node=CheckAvailabilityNode, connections=[CreateStudentRecordNode]),
            NodeConfig(node=CreateStudentRecordNode, connections=[ScheduleDemoLessonNode]),
            NodeConfig(node=ScheduleDemoLessonNode, connections=[SendConfirmationNode])
        ]
    )
```

### 3. Payment Processing System

#### Quick API Operations (<200ms)
```python
@app.get("/api/payments")
async def list_payments(filters: PaymentFilters) -> List[Payment]:
    """Fast payment history retrieval"""

@app.get("/api/billing/{parent_id}")
async def get_billing_info(parent_id: int) -> BillingInfo:
    """Quick billing information lookup"""
```

#### Workflow-Driven Operations
```python
class PaymentProcessingWorkflow(Workflow):
    """Handle Stripe payment processing"""
    workflow_schema = WorkflowSchema(
        description="Complete payment processing with error handling",
        event_schema=PaymentRequestSchema,
        start=CreatePaymentIntentNode,
        nodes=[
            NodeConfig(node=CreatePaymentIntentNode, connections=[ProcessPaymentNode]),
            NodeConfig(node=ProcessPaymentNode, connections=[PaymentRouterNode]),
            NodeConfig(
                node=PaymentRouterNode, 
                connections=[PaymentSuccessNode, PaymentFailureNode],
                is_router=True
            ),
            NodeConfig(node=PaymentSuccessNode, connections=[UpdateBillingNode]),
            NodeConfig(node=PaymentFailureNode, connections=[RetryPaymentNode])
        ]
    )
```

### 4. Lesson Scheduling System

#### Quick API Operations (<200ms)
```python
@app.get("/api/lessons")
async def list_lessons(filters: LessonFilters) -> List[Lesson]:
    """Fast lesson listing"""

@app.get("/api/teachers/{teacher_id}/availability")
async def get_teacher_availability(teacher_id: int) -> AvailabilityInfo:
    """Quick availability check"""
```

#### Workflow-Driven Operations
```python
class SchedulingWorkflow(Workflow):
    """Intelligent lesson scheduling with conflict resolution"""
    workflow_schema = WorkflowSchema(
        description="Automated lesson scheduling with optimization",
        event_schema=SchedulingRequestSchema,
        start=CheckAvailabilityNode,
        nodes=[
            NodeConfig(node=CheckAvailabilityNode, connections=[ConflictDetectionNode]),
            NodeConfig(node=ConflictDetectionNode, connections=[SchedulingRouterNode]),
            NodeConfig(
                node=SchedulingRouterNode,
                connections=[DirectScheduleNode, ConflictResolutionNode],
                is_router=True
            ),
            NodeConfig(node=ConflictResolutionNode, connections=[OptimizeScheduleNode]),
            NodeConfig(node=OptimizeScheduleNode, connections=[FinalizeScheduleNode])
        ]
    )
```

### 5. Communication and Notification System

#### Workflow-Driven Operations
```python
class NotificationWorkflow(Workflow):
    """Multi-channel notification delivery"""
    workflow_schema = WorkflowSchema(
        description="Intelligent notification routing and delivery",
        event_schema=NotificationRequestSchema,
        start=DetermineChannelsNode,
        nodes=[
            NodeConfig(node=DetermineChannelsNode, connections=[NotificationRouterNode]),
            NodeConfig(
                node=NotificationRouterNode,
                connections=[EmailNode, SMSNode, InAppNode],
                is_router=True
            ),
            NodeConfig(
                node=EmailNode,
                connections=[TrackDeliveryNode],
                concurrent_nodes=[SMSNode, InAppNode]
            ),
            NodeConfig(node=TrackDeliveryNode, connections=[])
        ]
    )
```

## Workflow Node Specifications

### Core Node Types for Cedar Heights

#### 1. Validation Nodes
```python
class ValidateEnrollmentNode(Node):
    """Validate enrollment data with comprehensive checks"""
    
    class OutputType(BaseModel):
        is_valid: bool
        validation_errors: List[str]
        sanitized_data: Dict[str, Any]
    
    async def process(self, task_context: TaskContext) -> TaskContext:
        # Comprehensive validation logic
        enrollment_data = task_context.event.enrollment_data
        
        # Validate required fields, format, business rules
        validation_result = await self.validate_enrollment(enrollment_data)
        
        task_context.update_node(self.node_name, **validation_result.dict())
        
        if not validation_result.is_valid:
            task_context.stop_workflow()
            
        return task_context
```

#### 2. External Service Integration Nodes
```python
class StripePaymentNode(Node):
    """Handle Stripe payment processing with error handling"""
    
    class OutputType(BaseModel):
        payment_intent_id: str
        status: str
        amount: int
        error_message: Optional[str] = None
    
    async def process(self, task_context: TaskContext) -> TaskContext:
        payment_data = task_context.event.payment_data
        
        try:
            # Stripe API integration
            payment_intent = await self.create_payment_intent(payment_data)
            result = self.OutputType(
                payment_intent_id=payment_intent.id,
                status=payment_intent.status,
                amount=payment_intent.amount
            )
        except StripeError as e:
            result = self.OutputType(
                payment_intent_id="",
                status="failed",
                amount=0,
                error_message=str(e)
            )
        
        task_context.update_node(self.node_name, **result.dict())
        return task_context
```

#### 3. Business Logic Nodes
```python
class ScheduleOptimizationNode(Node):
    """Optimize lesson scheduling based on constraints"""
    
    class OutputType(BaseModel):
        optimized_schedule: List[LessonSlot]
        conflicts_resolved: int
        optimization_score: float
    
    async def process(self, task_context: TaskContext) -> TaskContext:
        scheduling_request = task_context.event.scheduling_request
        
        # Complex scheduling algorithm
        optimizer = ScheduleOptimizer()
        result = await optimizer.optimize(scheduling_request)
        
        task_context.update_node(self.node_name, **result.dict())
        return task_context
```

#### 4. Router Nodes for Business Logic
```python
class EnrollmentRouterNode(RouterNode):
    """Route enrollment based on student type and availability"""
    
    async def determine_next_nodes(self, task_context: TaskContext) -> List[Type[Node]]:
        enrollment_data = task_context.nodes.get("ValidateEnrollmentNode", {})
        
        if enrollment_data.get("is_returning_student"):
            return [ReturningStudentNode]
        elif enrollment_data.get("requires_demo"):
            return [DemoLessonNode]
        else:
            return [DirectEnrollmentNode]
```

## Data Models and Schemas

### Event Schemas
```python
class EnrollmentRequestSchema(BaseModel):
    """Enrollment request from public website"""
    student_name: str
    parent_email: str
    instrument: str
    preferred_teacher_id: Optional[int] = None
    preferred_times: List[str]
    demo_lesson_required: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)

class PaymentRequestSchema(BaseModel):
    """Payment processing request"""
    student_id: int
    amount: int  # in cents
    payment_method_id: str
    billing_cycle: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SchedulingRequestSchema(BaseModel):
    """Lesson scheduling request"""
    student_id: int
    teacher_id: int
    lesson_type: str
    preferred_times: List[datetime]
    duration_minutes: int = 30
    recurring: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

### Output Schemas
```python
class WorkflowResultSchema(BaseModel):
    """Standardized workflow result"""
    success: bool
    workflow_name: str
    execution_time: float
    nodes_executed: List[str]
    final_result: Dict[str, Any]
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

## API Integration Patterns

### FastAPI + Workflow Integration
```python
@app.post("/api/enrollments/process")
async def process_enrollment(
    enrollment_data: EnrollmentRequestSchema,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Process enrollment through workflow"""
    
    # Quick validation and immediate response
    if not enrollment_data.student_name or not enrollment_data.parent_email:
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    # Trigger workflow asynchronously
    workflow = EnrollmentWorkflow()
    background_tasks.add_task(
        execute_enrollment_workflow,
        workflow,
        enrollment_data.dict()
    )
    
    return {
        "success": True,
        "message": "Enrollment processing started",
        "enrollment_id": generate_enrollment_id(),
        "estimated_completion": "2-5 minutes"
    }

async def execute_enrollment_workflow(workflow: EnrollmentWorkflow, event_data: dict):
    """Execute enrollment workflow in background"""
    try:
        result = await workflow.run_async(event_data)
        # Handle workflow completion
        await notify_enrollment_completion(result)
    except Exception as e:
        # Handle workflow failure
        await handle_enrollment_failure(event_data, str(e))
```

### Workflow Status Tracking
```python
@app.get("/api/workflows/{workflow_id}/status")
async def get_workflow_status(workflow_id: str) -> WorkflowStatusSchema:
    """Get workflow execution status"""
    
    # Quick status lookup from Redis/database
    status = await get_workflow_status_from_cache(workflow_id)
    
    return WorkflowStatusSchema(
        workflow_id=workflow_id,
        status=status.status,
        progress=status.progress,
        current_node=status.current_node,
        estimated_completion=status.estimated_completion,
        results=status.partial_results
    )
```

## Performance and Scalability

### Response Time Targets
- **Quick APIs:** <200ms (95th percentile)
  - Student/teacher lookups
  - Payment history
  - Basic scheduling queries
  
- **Workflow APIs:** <2s (95th percentile)
  - Enrollment processing
  - Payment workflows
  - Complex scheduling
  
- **Background Workflows:** <30s completion
  - Email processing
  - Report generation
  - Bulk operations

### Scalability Architecture
```python
# Horizontal scaling through stateless design
class WorkflowExecutor:
    """Stateless workflow executor for horizontal scaling"""
    
    def __init__(self, redis_client: Redis, db_session: AsyncSession):
        self.redis = redis_client
        self.db = db_session
    
    async def execute_workflow(self, workflow_name: str, event_data: dict):
        """Execute workflow with full state persistence"""
        workflow = get_workflow_by_name(workflow_name)
        
        # All state stored in Redis/DB, not in memory
        task_context = await self.load_or_create_context(event_data)
        
        result = await workflow.run_async(event_data, context=task_context)
        
        await self.persist_workflow_result(result)
        return result
```

## Deployment and Infrastructure

### Docker Configuration
```dockerfile
# Multi-stage build for GenAI Launchpad + Cedar Heights
FROM python:3.11-slim as base

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen

# Copy application code
COPY app/ ./app/
COPY ai_docs/ ./ai_docs/

# Production stage
FROM base as production
ENV ENVIRONMENT=production
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Configuration
```yaml
# docker-compose.yml
version: '3.8'
services:
  api:
    build:
      context: .
      target: production
    environment:
      - DATABASE_URL=${SUPABASE_DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY}
    depends_on:
      - redis
      - celery-worker

  celery-worker:
    build:
      context: .
      target: production
    command: celery -A app.worker.tasks worker --loglevel=info
    environment:
      - DATABASE_URL=${SUPABASE_DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

## Testing Strategy

### Workflow Testing
```python
@pytest.mark.asyncio
async def test_enrollment_workflow():
    """Test complete enrollment workflow"""
    
    # Setup
    workflow = EnrollmentWorkflow()
    test_event = {
        "student_name": "John Doe",
        "parent_email": "parent@example.com",
        "instrument": "piano",
        "demo_lesson_required": True
    }
    
    # Execute
    result = await workflow.run_async(test_event)
    
    # Validate workflow completion
    assert result.success is True
    assert "ValidateEnrollmentNode" in result.nodes
    assert "ScheduleDemoLessonNode" in result.nodes
    assert result.nodes["ScheduleDemoLessonNode"]["demo_scheduled"] is True

@pytest.mark.asyncio
async def test_payment_workflow_failure_handling():
    """Test payment workflow with Stripe failure"""
    
    workflow = PaymentProcessingWorkflow()
    test_event = {
        "student_id": 1,
        "amount": 5000,  # $50.00
        "payment_method_id": "pm_card_declined"
    }
    
    # Mock Stripe failure
    with patch('stripe.PaymentIntent.create') as mock_create:
        mock_create.side_effect = StripeError("Card declined")
        
        result = await workflow.run_async(test_event)
        
        # Validate failure handling
        assert result.success is False
        assert "PaymentFailureNode" in result.nodes
        assert result.nodes["PaymentFailureNode"]["retry_scheduled"] is True
```

### API Integration Testing
```python
@pytest.mark.asyncio
async def test_enrollment_api_workflow_integration():
    """Test API endpoint triggering workflow"""
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/enrollments/process", json={
            "student_name": "Jane Doe",
            "parent_email": "jane@example.com",
            "instrument": "violin"
        })
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "enrollment_id" in data
    
    # Verify workflow was triggered
    # (Implementation depends on workflow tracking system)
```

## Risk Assessment and Mitigation

### High-Priority Risks

#### 1. Workflow Complexity Management
- **Risk:** Complex workflows becoming difficult to debug and maintain
- **Impact:** Medium - Development velocity reduction
- **Mitigation:**
  - Comprehensive workflow visualization tools
  - Extensive logging and monitoring at each node
  - Clear workflow documentation and testing
  - Modular node design for reusability

#### 2. Performance Under Load
- **Risk:** Workflow orchestration overhead affecting performance
- **Impact:** Medium - User experience degradation
- **Mitigation:**
  - Hybrid quick API + workflow approach
  - Comprehensive performance testing
  - Redis caching for workflow state
  - Horizontal scaling capabilities

#### 3. External Service Dependencies
- **Risk:** Stripe, Supabase, or email service failures
- **Impact:** High - Business process interruption
- **Mitigation:**
  - Circuit breaker patterns in workflow nodes
  - Comprehensive retry logic with exponential backoff
  - Dead letter queues for failed operations
  - Graceful degradation strategies

## Success Criteria and Acceptance Criteria

### MVP Launch Criteria
- [ ] GenAI Launchpad framework integrated and operational
- [ ] Core workflows implemented (enrollment, payment, scheduling)
- [ ] Quick APIs delivering <200ms response times
- [ ] Workflow APIs completing within <2s
- [ ] Comprehensive error handling and logging
- [ ] Type safety enforced across all workflows and APIs
- [ ] Supabase integration with RLS policies
- [ ] Stripe payment processing workflows
- [ ] Email notification workflows
- [ ] Docker deployment on Hetzner infrastructure
- [ ] >90% test coverage including workflow testing
- [ ] API documentation with OpenAPI/Swagger
- [ ] Monitoring and alerting operational

### Production Readiness Criteria
- [ ] All complex business processes automated through workflows
- [ ] Performance targets met under load testing
- [ ] Security audit passed with no critical vulnerabilities
- [ ] PIPEDA compliance validated
- [ ] Disaster recovery procedures tested
- [ ] 24/7 monitoring and alerting configured
- [ ] Documentation complete for development and operations
- [ ] Business continuity plan validated

### Business Impact Validation
- [ ] 60% reduction in administrative overhead achieved
- [ ] Frontend integration completed with all required APIs
- [ ] User acceptance testing passed for all user roles
- [ ] Financial accuracy validated (100% payment reconciliation)
- [ ] System reliability demonstrated (99.9% uptime)

## Future Roadmap

### Phase 2: Advanced Workflow Features (Months 7-12)
- **AI-Powered Scheduling:** Intelligent scheduling optimization using GenAI
- **Predictive Analytics:** Student retention and revenue forecasting workflows
- **Advanced Reporting:** Complex report generation through workflow orchestration
- **Multi-School Support:** Tenant-aware workflows for multiple music schools

### Phase 3: Ecosystem Expansion (Year 2)
- **Workflow Marketplace:** Reusable workflow templates for music schools
- **Mobile API Optimization:** Mobile-specific workflow patterns
- **Integration Hub:** Third-party service integration workflows
- **Advanced Analytics:** Machine learning-powered business insights

---

*This synthesized PRD demonstrates how the GenAI Launchpad workflow orchestration framework serves as the foundation for building the Cedar Heights Music Academy backend system, providing both the technical architecture and business process automation needed for a successful music school management platform.*