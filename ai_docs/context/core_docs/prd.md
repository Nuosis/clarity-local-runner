# DevTeam Runner Service - Product Requirements Document
**MVP READY**

## Product Overview

The DevTeam Runner Service is a critical backend microservice that enables autonomous development task execution for the Clarity CRM Frontend's DevTeam feature. This Python/FastAPI service orchestrates automated development workflows through a SELECT→PREP→IMPLEMENT→VERIFY pipeline, transforming manual task-by-task development into continuous, automated progression.

**Value Proposition**: Enable ≥80% autonomous task completion without human intervention, supporting parallel customer project workflows while maintaining quality through automated verification.

## Scope Additions (Integration Alignment)
- Docker Container Orchestration: per-task isolated containers with health checks, CPU/RAM limits, automatic cleanup, and restart/backoff policies; isolated volumes/workspaces.
- WebSocket Communication Infrastructure: connection pooling, project/user routing, reconnection with backoff, backpressure/throttling, authN/Z, and message validation.
- DevTeam Automation API: initialize/status/pause/resume/stop automation; repository validate; task list read/update; error details; task injection; active/history listings.
- Workflow Ownership: Repository Initialization Workflow; Task Execution State Machine; Execute Code Change Workflow (GenAI Launchpad); and related GenAI workflows.
- MVP vs Roadmap: MVP delivers the core runner + Automation API for repo init, task state, and code change (Aider). Phase 2 extends to full GenAI workflow engine (Ollama prompt construction, GPT-5 Medium execution) without changing external contracts.

## Event-Driven and DAG Architecture Alignment
- Primary ingestion via POST /events using the existing event system; FastAPI router mounts events API at [router.include_router](app/api/router.py:14) and the handler persists events in the database in [events_endpoint()](app/api/endpoint.py:43) before queuing Celery.
- Asynchronous execution handled by Celery using [process_incoming_event()](app/worker/tasks.py:19), which loads the Event, dispatches a DAG workflow via [Workflow.run()](app/core/workflow.py:105), and persists results to Event.task_context.
- DAG orchestration follows the GenAI Launchpad engine in [Workflow.run()](app/core/workflow.py:105) and its schema parsing at [Workflow.__run()](app/core/workflow.py:119-135), ensuring Pydantic-validated event schemas feed node execution.
- Persistence model uses Event storage with raw data and task_context in [Event](app/database/event.py:13); migrations are managed with Alembic ([env.py](app/alembic/env.py:11)). Supabase PostgreSQL backs persistence (docker-compose.supabase).
- Queueing and scalability use Celery+Redis per [celery_app](app/worker/config.py:39); API returns 202 Accepted with task_id upon enqueue.

## Personas (≤3)

### 1. Frontend Developer (Primary User)
- **Goals**: Execute development tasks automatically through DevTeam interface, monitor real-time progress, focus on high-value work
- **Pain Points**: Manual task execution bottlenecks, context switching between projects, repetitive implementation work
- **Technical Level**: High - familiar with Git workflows, development tools, and CI/CD processes

### 2. Project Manager (Secondary User)  
- **Goals**: Monitor multiple customer project progress, track completion rates, identify bottlenecks across teams
- **Pain Points**: Lack of visibility into development progress, difficulty coordinating multiple projects, manual status reporting
- **Technical Level**: Medium - understands development concepts but focuses on project coordination

### 3. Backend Developer (System Maintainer)
- **Goals**: Maintain service reliability, integrate with external tools, troubleshoot execution failures
- **Pain Points**: Complex Git repository management, tool integration failures, debugging distributed execution issues
- **Technical Level**: High - expert in backend systems, containerization, and service integration

## Primary Journeys (3)

### Journey 1: Autonomous Task Execution
**Start**: Frontend developer initiates task execution → **Finish**: Task completed with verification passed

**Flow**:
1. DevTeam UI submits a DevTeamAutomation event to POST /events (workflow_type=DEVTEAM_AUTOMATION; payload includes projectId/task context)
2. API validates payload, persists Event, and enqueues Celery task (202 Accepted with task_id) via [celery_app.send_task](app/api/endpoint.py:72)
3. Celery worker loads Event and dispatches DAG via [WorkflowRegistry](app/worker/tasks.py:7-8) → [Workflow.run()](app/core/workflow.py:105)
4. Nodes perform SELECT→PREP→IMPLEMENT→VERIFY within the workflow DAG (tools, repo prep, verification)
5. Node outputs and execution state accumulate in Event.task_context and are committed to DB
6. On completion or failure, final status recorded in Event.task_context; idempotency handled at event layer
7. Frontend polls or subscribes to updates (WS/EDA integration) to render progress and results

### Journey 2: Real-time Progress Monitoring
**Start**: User connects to execution session → **Finish**: Complete visibility of task progress and logs

**Flow**:
1. Frontend establishes WebSocket connection to /ws/devteam
2. Service streams execution-update events with progress percentages
3. Service streams execution-log events with detailed operation logs
4. User receives real-time feedback on current operation status
5. Connection maintains stability with automatic reconnection on failures
### Journey 3: Multi-Customer Project Management
**Start**: Multiple customer projects queued → **Finish**: Parallel execution with isolated progress tracking

**Flow**:
1. Service receives execution requests for different customer projects
2. Resource isolation ensures separate working directories per customer
3. Parallel task execution maintains independent progress tracking
4. WebSocket events include customerId for proper frontend routing
5. Completion artifacts stored separately per customer project

## Workflow Responsibilities
- Repository Initialization Workflow: clone/pull repository, ensure task_lists.md exists and is valid (create from template if missing), start local runner container, verify runner health.
- Task Execution State Machine: SELECT → PREP → IMPLEMENT → VERIFY → MERGE → PUSH → UPDATE_TASKLIST → DONE with error paths to injected error-resolution task and optional human review; idempotent transitions and correlation IDs.
- Execute Code Change Workflow (GenAI Launchpad):
  - GatherContextNode: create isolated container and clone repo
  - ConstructTaskPromptNode: build focused prompt (Ollama Qwen3 8B) [Phase 2]; MVP uses deterministic prompt template
  - CodeExecutionNode: execute code changes (GPT-5 Medium) [Phase 2]; MVP uses Aider-driven changes
  - VerifyNode: build/test checks, ≤2 retries, container cleanup
- Additional GenAI workflows: orchestrated by this service and activated per project policy; planned for Phase 2.

## Functional Requirements by Journey (MoSCoW)

### Journey 1: Autonomous Task Execution
**Must Have**:
- Health check endpoint validates all dependencies (git, aider, filesystem)
- Task selection from tasks_list.md with dependency resolution
- Repository preparation with branch creation (task/<taskId>-<kebab-title>)
- Aider tool integration for implementation with artifact capture
- Quality verification against test coverage, type checking, documentation
- Stop-on-error semantics preventing progression on failures
- Idempotent operations with idempotencyKey support

**Should Have**:
- Automatic cleanup of old working directories
- Comprehensive error classification and recovery mechanisms
- Structured logging with correlation IDs

**Could Have**:
- Multiple tool support beyond Aider
- Advanced dependency resolution algorithms
- Automatic conflict resolution for Git operations

### Journey 2: Real-time Progress Monitoring
**Must Have**:
- WebSocket server at /ws/devteam endpoint
- Execution-update events with progress percentages
- Execution-log events with operation details
- Event delivery within ≤500ms latency
- Connection recovery with exponential backoff

**Should Have**:
- Event throttling for high-frequency updates
- Client-side connection state management
- Historical event replay on reconnection

**Could Have**:
- Event filtering by log level or operation type
- Real-time performance metrics streaming

### Journey 3: Multi-Customer Project Management
**Must Have**:
- Customer isolation with separate working directories
- Parallel execution support for multiple customers
- CustomerId included in all WebSocket events
- Resource limits per customer execution

**Should Have**:
- Customer-specific configuration management
- Execution queue management per customer
- Resource usage monitoring per customer

**Could Have**:
- Customer priority-based execution scheduling
- Cross-customer resource sharing optimization

## Non-Functional Requirements (Targets)
### Performance Requirements
- **Response Times**: ≤2s for /prep operations, ≤30s for /implement operations, ≤60s for /verify operations
- **WebSocket Latency**: Real-time events delivered within ≤500ms
- **Concurrent Executions**: Support minimum 5 parallel customer executions
- **Resource Cleanup**: Automatic cleanup of working directories >24 hours old
- **Container Bootstrap Time**: ≤5s (p50), ≤10s (p95)
- **Container Teardown**: Cleanup within ≤60s after completion
- **WebSocket Handshake**: ≤300ms; reconnect backoff capped at 30s
- **Per-Execution Resource Quotas**: Default 1 vCPU, 2 GiB RAM (configurable per project)
- **Celery Queue SLA**: Time-to-start p95 ≤5s from POST /events to worker execution; default worker concurrency ≥4
- **DB Write SLA**: Event.task_context persistence within ≤1s after node completion


### Reliability Requirements
- **Uptime Target**: 99.9% service availability
- **Autonomous Completion Rate**: ≥80% of atomic tasks completed without human intervention
- **Error Recovery**: Graceful degradation when external tools unavailable
- **Idempotency**: All state-changing operations must be idempotent
### Security Requirements
- **Input Validation**: Comprehensive validation for all request parameters
- **Output Sanitization**: Redact secrets and tokens from all outputs
- **Repository Access**: Secure Git authentication with minimal permissions
- **Process Isolation**: Sandboxed execution of external tools
- **Audit Logging**: Complete audit trail for all operations
- **WebSocket AuthZ**: JWT/session validation and per-project authorization on /ws/devteam
- **Message Validation**: Strict schema and size limits; drop malformed frames
- **Container Sandbox**: Restrict filesystem to workspace; limit egress to Git/AI services; no host mounts by default


## Core Data Objects (≤5)

### 0. Event Record
```json
{
  "id": "uuid",
  "workflow_type": "DEVTEAM_AUTOMATION",
  "data": {
    "projectId": "customer-123/project-abc",
    "task": { "id": "1.1.1", "title": "…" },
    "options": { "stopPoint": null, "idempotencyKey": "…" }
  },
  "task_context": {
    "nodes": { "SelectNode": { "status": "completed" } },
    "metadata": { "correlationId": "…" }
  },
  "created_at": "2025-01-14T18:25:00Z",
  "updated_at": "2025-01-14T18:30:00Z"
}
```

### 1. Task Definition
```json
{
  "id": "1.1.1",
  "title": "Add DEVTEAM_ENABLED flag to src/config.js", 
  "description": "Add DEVTEAM_ENABLED flag with default false and JSDoc",
  "type": "atomic",
  "dependencies": [],
  "files": ["src/config.js"],
  "criteria": {
    "test.coverage": "≥80%",
    "type.strict": "0 errors", 
    "doc.updated": "task_outcomes.md"
  },
  "status": "pending"
}
```

### 2. Execution State
```json
{
  "customerId": "customer-123",
  "currentTask": "1.1.1", 
  "status": "IMPLEMENTING",
  "branch": "task/1-1-1-add-devteam-enabled-flag",
  "progress": 45.2,
  "startTime": "2025-01-14T18:25:00Z",
  "artifacts": {
    "repoPath": "/workspace/repos/repo-hash",
    "logs": ["Implementation started", "Aider tool initialized"]
  }
}
```

### 3. Operation Artifact
```json
{
  "operation": "implement",
  "taskId": "1.1.1",
  "tool": "aider",
  "success": true,
  "duration": 12.5,
  "outputs": {
    "diff": "git diff output",
    "stdout": "Tool execution output", 
    "filesModified": ["src/config.js"],
    "linesChanged": 5
  }
}
```

### 4. WebSocket Event
```json
{
  "type": "execution-update",
  "customerId": "customer-123", 
  "taskId": "1.1.1",
  "status": "IMPLEMENTING",
  "progress": 45.2,
  "timestamp": "2025-01-14T18:30:00Z"
}
```

### 5. Verification Result
```json
{
  "taskId": "1.1.1",
  "success": true,
  "results": {
    "test.coverage": {"passed": true, "actual": "85%", "required": "≥80%"},
    "type.strict": {"passed": true, "actual": "0 errors", "required": "0 errors"},
    "doc.updated": {"passed": true, "files": ["docs/DevTeam/task_outcomes.md"]}
  }
}
```

## Acceptance Criteria (Given/When/Then) per Journey

### Journey 1: Autonomous Task Execution
**Given** a valid DevTeamAutomation event payload for a repository with tasks_list.md
**When** the frontend submits the event to POST /events
**Then** the API persists the Event and returns 202 with task_id
**And** Celery processes the Event via DAG workflow and persists results to Event.task_context
**And** ≥80% of atomic tasks complete end-to-end within SLA timeframes
**And** artifacts and verification outcomes are available via persisted task_context
**And** stop-on-error prevents progression when verification fails

### Journey 2: Real-time Progress Monitoring  
**Given** an active task execution session  
**When** user connects via WebSocket to /ws/devteam  
**Then** real-time execution-update events are received within ≤500ms  
**And** execution-log events provide detailed operation visibility  
**And** connection automatically recovers from failures with exponential backoff  
**And** events include customerId for proper frontend routing

### Journey 3: Multi-Customer Project Management
**Given** multiple customer projects with pending tasks  
**When** parallel execution requests are submitted  
**Then** each customer execution runs in isolated working directory  
**And** progress tracking remains independent per customer  
**And** WebSocket events are properly routed by customerId  
**And** resource limits prevent one customer from impacting others  
**And** minimum 5 concurrent executions are supported
## API Endpoints Summary

Event-Driven API (Primary)
- **POST /events** - Ingest event (e.g., DEVTEAM_AUTOMATION). Returns 202 with Celery task_id and event_id. See [events_endpoint()](app/api/endpoint.py:43).
- (Internal) Celery Worker executes [process_incoming_event()](app/worker/tasks.py:19) → [Workflow.run()](app/core/workflow.py:105). Results are persisted to [Event.task_context](app/database/event.py:13).

Core Runner API
- **GET /health** - Service health and dependency validation
- **POST /prep** - Repository preparation and branch creation
- **POST /implement** - Task implementation using specified tool
- **POST /verify** - Task verification against quality criteria
- **GET /tasks/next** - Task selection with dependency resolution
- **WS /ws/devteam** - Real-time progress and log streaming

DevTeam Automation API
- **POST /api/devteam/automation/initialize** - Start autonomous execution for a project (optional stopPoint)
- **GET /api/devteam/automation/status/{projectId}** - Current automation status and progress
- **POST /api/devteam/automation/pause/{projectId}** - Pause automation
- **POST /api/devteam/automation/resume/{projectId}** - Resume automation
- **POST /api/devteam/automation/stop/{projectId}** - Stop automation
- **POST /api/devteam/repository/validate** - Validate repository URL/permissions and task list
- **GET /api/devteam/repository/tasks/{projectId}** - Read parsed task list
- **PUT /api/devteam/repository/tasks/{projectId}/{taskId}** - Update task status/metadata
- **GET /api/devteam/errors/{executionId}/{errorId}** - Retrieve error context/details
- **POST /api/devteam/tasks/inject** - Inject a task (priority|replace|positional)
- **GET /api/devteam/executions/active/{userId}** - List active executions for user
- **GET /api/devteam/executions/history/{userId}?limit={n}** - Execution history

Notes
- All state-changing endpoints are idempotent via Idempotency-Key header
- WebSocket events include projectId and executionId for routing

## Success Metrics

- **Autonomous Completion Rate**: ≥80% of atomic tasks completed end-to-end without human intervention
- **Performance Compliance**: 95% of operations meet SLA timeframes (≤2s prep, ≤30s implement, ≤60s verify)
- **System Reliability**: 99.9% uptime with comprehensive error handling and recovery
- **Real-time Responsiveness**: WebSocket events delivered within ≤500ms latency
- **Multi-customer Support**: Successful parallel execution of minimum 5 customer projects

## Constraints and Assumptions

### Technical Constraints
- Python/FastAPI technology stack (non-negotiable)
- Event ingestion via POST /events with Celery+Redis asynchronous processing
- DAG workflows executed via GenAI Launchpad engine ([Workflow.run()](app/core/workflow.py:105))
- Supabase PostgreSQL for Event persistence; Redis as Celery broker/backend
- Alembic migrations applied before runtime (e.g., docker-compose exec api alembic upgrade head)
- Docker containerization required
- Phase 1 limited to Aider tool integration
- Stop-on-error semantics for MVP

### Business Constraints  
- 4-week delivery timeline for MVP
- Integration with existing Clarity CRM Frontend DevTeam interface
- Must support existing Git repository structures and workflows

### Assumptions
- Target repositories contain properly formatted tasks_list.md files
- Aider tool remains stable and available for implementation
- Git repositories are accessible with provided authentication
- Frontend DevTeam interface handles WebSocket connection management
- Customer projects follow standard development practices (testing, documentation)