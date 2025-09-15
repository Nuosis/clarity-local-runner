# DevTeam Runner Service Implementation Guide

**Document Version**: 1.0  
**Created**: 2025-01-14  
**Target Audience**: Backend Development Team  
**Purpose**: Implementation requirements for the DevTeam Runner Service supporting automated development task execution

## Overview

The DevTeam Runner Service is a backend microservice that orchestrates automated development tasks through a SELECT → PREP → IMPLEMENT → VERIFY pipeline. This service enables the frontend DevTeam interface to execute development tasks automatically with stop-on-error semantics for Phase 1 MVP functionality.

## Service Architecture Requirements

### Core Service Structure
- **Technology Stack**: Python/FastAPI
- **Base URL**: Configurable via environment variable `DEVTEAM_RUNNER_BASE_URL`
- **Port**: Configurable (default: 8081)
- **Protocol**: HTTP/HTTPS with WebSocket support
- **Deployment**: Docker containerized service

### Infrastructure Dependencies
- **Git Repository Access**: Read/write access to target repositories
- **File System**: Persistent storage for repository clones and working directories
- **Process Management**: Ability to spawn and manage child processes (git, aider, test runners)
- **WebSocket Server**: Real-time communication with frontend clients

## API Endpoints Specification

### 1. Health Check Endpoint

**Endpoint**: `GET /health`

**Purpose**: Service health verification before PREP operations

**Request**: No parameters

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-14T18:30:00Z",
  "version": "1.0.0",
  "dependencies": {
    "git": "available",
    "aider": "available",
    "<service>": "available/unhealthy",
    "filesystem": "writable"
  }
}
```

**Success Criteria**:
- Returns HTTP 200 status
- Response time ≤ 500ms
- All dependencies report as available

### 2. Repository Preparation Endpoint

**Endpoint**: `POST /prep`

**Purpose**: Ensure local repository exists and create task branch

**Request Body**:
```json
{
  "repoUrl": "https://github.com/user/repo.git",
  "taskId": "1.1.1",
  "idempotencyKey": "uuid-v4-string"
}
```

**Response**:
```json
{
  "success": true,
  "taskId": "1.1.1",
  "branch": "task/1-1-1-add-devteam-enabled-flag",
  "repoPath": "/workspace/repos/repo-hash",
  "idempotencyKey": "uuid-v4-string",
  "artifacts": {
    "cloned": true,
    "branchCreated": true,
    "workingDirectory": "/workspace/repos/repo-hash"
  }
}
```

**Success Criteria**:
- Repository cloned or updated successfully
- Task branch created using pattern: `task/<taskId>-<kebab-title>`
- Idempotent operations (re-running same request returns same result)
- Working directory established and accessible

**Error Handling**:
- HTTP 400: Invalid request parameters
- HTTP 409: Repository access denied
- HTTP 500: File system or git operation failure

### 3. Task Implementation Endpoint

**Endpoint**: `POST /implement`

**Purpose**: Execute task implementation using specified tool

**Request Body**:
```json
{
  "taskId": "1.1.1",
  "branch": "task/1-1-1-add-devteam-enabled-flag",
  "tool": "aider",
  "criteria": {
    "description": "Add DEVTEAM_ENABLED flag to src/config.js with default false and JSDoc",
    "files": ["src/config.js"],
    "requirements": ["Feature flag with default false", "JSDoc documentation"]
  }
}
```

**Response**:
```json
{
  "success": true,
  "taskId": "1.1.1",
  "tool": "aider",
  "artifacts": {
    "diff": "git diff output showing changes",
    "stdout": "Tool execution output",
    "stderr": "Any error output (redacted)",
    "filesModified": ["src/config.js"],
    "linesChanged": 5
  },
  "duration": 12.5
}
```

**Success Criteria**:
- Default tool is Aider unless specified otherwise
- Minimal, file-scoped diffs captured as artifacts
- All outputs redact secrets and sensitive tokens
- Changes committed to task branch

**Error Handling**:
- HTTP 400: Invalid task parameters
- HTTP 404: Task branch not found
- HTTP 500: Tool execution failure (triggers STOP-ON-ERROR)

### 4. Task Verification Endpoint

**Endpoint**: `POST /verify`

**Purpose**: Verify task completion against quality criteria

**Request Body**:
```json
{
  "taskId": "1.1.1",
  "branch": "task/1-1-1-add-devteam-enabled-flag",
  "criteria": {
    "test.coverage": "≥80%",
    "type.strict": "0 errors",
    "doc.updated": "task_outcomes.md"
  }
}
```

**Response**:
```json
{
  "success": true,
  "taskId": "1.1.1",
  "results": {
    "test.coverage": {
      "passed": true,
      "actual": "85%",
      "required": "≥80%"
    },
    "type.strict": {
      "passed": true,
      "actual": "0 errors",
      "required": "0 errors"
    },
    "doc.updated": {
      "passed": true,
      "files": ["docs/DevTeam/task_outcomes.md"]
    }
  },
  "artifacts": {
    "testOutput": "Test execution results",
    "coverageReport": "Coverage analysis",
    "typeCheckOutput": "TypeScript validation results"
  }
}
```

**Success Criteria**:
- Test coverage meets project threshold (≥80% for touched scope)
- TypeScript validation passes with 0 errors (if applicable)
- Documentation updated (task_outcomes.md and related docs)
- Verification failure triggers STOP-ON-ERROR

**Error Handling**:
- HTTP 400: Invalid verification criteria
- HTTP 422: Verification criteria not met (triggers STOP-ON-ERROR)
- HTTP 500: Verification process failure

### 5. Task Selection Endpoint

**Endpoint**: `GET /tasks/next`

**Purpose**: SELECT logic - obtain next incomplete atomic task

**Query Parameters**:
- `customerId`: Customer/project identifier
- `excludeCompleted`: Boolean (default: true)

**Response**:
```json
{
  "task": {
    "id": "1.1.2",
    "title": "Export DEVTEAM_RUNNER_BASE_URL in src/config.js",
    "description": "Export DEVTEAM_RUNNER_BASE_URL in src/config.js with placeholder value and JSDoc",
    "dependencies": ["1.1.1"],
    "type": "atomic",
    "files": ["src/config.js"],
    "criteria": {
      "test.coverage": "≥80%",
      "type.strict": "0 errors",
      "doc.updated": "task_outcomes.md"
    }
  },
  "dependenciesSatisfied": true,
  "totalTasks": 45,
  "completedTasks": 12,
  "progress": 26.7
}
```

**Success Criteria**:
- Returns first incomplete atomic task from tasks_list.md
- Dependency satisfaction enforced by runner
- Null result handled gracefully when no tasks available
- Selection is deterministic for given repository state

## WebSocket Interface

### Connection Endpoint
**Endpoint**: `WS /ws/devteam`

**Purpose**: Real-time updates for execution progress and logs

### Event Types

#### 1. Execution Update Events
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

#### 2. Execution Log Events
```json
{
  "type": "execution-log",
  "customerId": "customer-123",
  "taskId": "1.1.1",
  "level": "info",
  "message": "Starting implementation with Aider",
  "timestamp": "2025-01-14T18:30:00Z"
}
```

### WebSocket Requirements
- **Exponential Backoff**: Implement reconnection with exponential backoff
- **Event Throttling**: Client-side throttling for high-frequency events
- **Connection Recovery**: Automatic reconnection without UI freeze
- **Real-time Performance**: Updates visible in UI within ≤500ms

## Data Models

### Task Definition Structure
```json
{
  "id": "1.1.1",
  "title": "Add DEVTEAM_ENABLED flag to src/config.js",
  "description": "Add DEVTEAM_ENABLED flag to src/config.js with default false and JSDoc",
  "type": "atomic",
  "dependencies": [],
  "files": ["src/config.js"],
  "criteria": {
    "test.coverage": "≥80%",
    "type.strict": "0 errors",
    "doc.updated": "task_outcomes.md"
  },
  "phase": 1,
  "status": "pending"
}
```

### Execution State Model
```json
{
  "customerId": "customer-123",
  "currentTask": "1.1.1",
  "status": "IMPLEMENTING",
  "branch": "task/1-1-1-add-devteam-enabled-flag",
  "progress": 45.2,
  "startTime": "2025-01-14T18:25:00Z",
  "lastUpdate": "2025-01-14T18:30:00Z",
  "artifacts": {
    "repoPath": "/workspace/repos/repo-hash",
    "logs": ["Implementation started", "Aider tool initialized"]
  }
}
```

## Implementation Requirements

### 1. Idempotency
- **All POST endpoints** must include and respect `idempotencyKey`
- **Duplicate requests** with same key return identical results
- **State transitions** are idempotent (re-running completed step is no-op)
- **Key storage** persisted for reasonable duration (24 hours minimum)

### 2. Error Handling and Resilience
- **Graceful degradation** when external tools unavailable
- **Comprehensive logging** with structured format
- **Error classification** for different failure types
- **Recovery mechanisms** for transient failures
- **Resource cleanup** on operation failure

### 3. Security Requirements
- **Input validation** for all request parameters
- **Output sanitization** to redact secrets and tokens
- **Repository access** via secure authentication
- **Process isolation** for tool execution
- **Audit logging** for all operations

### 4. Performance Requirements
- **Response times**: ≤2s for /prep, ≤30s for /implement, ≤60s for /verify
- **Concurrent executions**: Support multiple customers simultaneously
- **Resource limits**: CPU and memory constraints for tool execution
- **Cleanup processes**: Automatic cleanup of old working directories

### 5. Observability
- **Structured logging** with correlation IDs
- **Metrics collection** for operation durations and success rates
- **Health monitoring** for service dependencies
- **Error tracking** with categorization and alerting

## Integration Points

### 1. Task List File Integration
- **File location**: `docs/DevTeam/tasks_list.md` in target repository
- **Format parsing**: Structured markdown with task definitions
- **Dependency resolution**: Parse and validate task dependencies
- **Progress tracking**: Update task completion status

### 2. Git Repository Management
- **Clone operations**: Fresh clone or fetch/pull for updates
- **Branch management**: Create, switch, and merge task branches
- **Commit operations**: Atomic commits for each task completion
- **Conflict resolution**: Handle merge conflicts gracefully

### 3. Tool Integration
- **Aider integration**: Primary implementation tool
- **Test runners**: Jest, pytest, or project-specific test commands
- **Type checkers**: TypeScript, Flow, or other type validation tools
- **Documentation generators**: Automatic doc updates

## Deployment Configuration

### Environment Variables
```bash
# Service Configuration
DEVTEAM_RUNNER_PORT=8080
DEVTEAM_RUNNER_BASE_URL=http://localhost:8080

# Repository Configuration
WORKSPACE_DIR=/workspace/repos
GIT_USERNAME=devteam-runner
GIT_TOKEN=github_pat_xxx

# Tool Configuration
AIDER_PATH=/usr/local/bin/aider
NODE_PATH=/usr/local/bin/node
PYTHON_PATH=/usr/local/bin/python

# Database Configuration (if needed)
DATABASE_URL=postgresql://user:pass@localhost:5432/devteam

# Logging Configuration
LOG_LEVEL=info
LOG_FORMAT=json
```

### Docker Configuration
```dockerfile
FROM node:18-alpine
# or FROM python:3.11-slim

# Install system dependencies
RUN apk add --no-cache git

# Install development tools
RUN npm install -g aider-chat
# or pip install aider-chat

# Application setup
WORKDIR /app
COPY package*.json ./
RUN npm install

COPY . .
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/healthz || exit 1

CMD ["npm", "start"]
```

## Testing Requirements

### 1. Unit Tests
- **Endpoint handlers**: Test all API endpoints with various inputs
- **Business logic**: Test task selection, dependency resolution
- **Error scenarios**: Test failure modes and error handling
- **Idempotency**: Verify duplicate request handling

### 2. Integration Tests
- **Git operations**: Test repository cloning, branching, committing
- **Tool integration**: Test Aider and other tool executions
- **WebSocket communication**: Test real-time event delivery
- **End-to-end workflows**: Test complete SELECT→PREP→IMPLEMENT→VERIFY cycles

### 3. Performance Tests
- **Load testing**: Multiple concurrent task executions
- **Resource usage**: Memory and CPU consumption monitoring
- **Response time validation**: Ensure SLA compliance
- **Cleanup verification**: Proper resource cleanup after operations

## Success Criteria Summary

### Functional Requirements ✅
- [ ] All API endpoints implemented and tested
- [ ] WebSocket real-time communication functional
- [ ] Task selection logic working with dependency resolution
- [ ] PREP operations clone/update repositories and create branches
- [ ] IMPLEMENT operations execute with Aider and capture artifacts
- [ ] VERIFY operations validate against quality criteria
- [ ] STOP-ON-ERROR semantics prevent progression on failures

### Non-Functional Requirements ✅
- [ ] Response times meet SLA (≤2s prep, ≤30s implement, ≤60s verify)
- [ ] Idempotency implemented for all state-changing operations
- [ ] Security measures in place (input validation, output sanitization)
- [ ] Comprehensive logging and error handling
- [ ] Docker containerization with health checks
- [ ] Unit and integration test coverage ≥80%

### Integration Requirements ✅
- [ ] Frontend can successfully call all endpoints
- [ ] WebSocket events received by frontend within ≤500ms
- [ ] Task list file parsing and dependency resolution working
- [ ] Git repository operations successful
- [ ] Tool integrations (Aider, test runners) functional

## Delivery Timeline

### Phase 1 - Core Service (Week 1-2)
- Basic HTTP server with health check
- Repository cloning and branch management
- Task selection logic implementation

### Phase 2 - Pipeline Implementation (Week 2-3)
- PREP, IMPLEMENT, VERIFY endpoint implementation
- Aider tool integration
- Basic error handling and logging

### Phase 3 - Real-time & Polish (Week 3-4)
- WebSocket implementation
- Comprehensive testing
- Docker containerization and deployment

### Phase 4 - Production Readiness (Week 4)
- Performance optimization
- Security hardening
- Documentation completion
- Production deployment

---

**Questions for Backend Team:**

1. **Technology Stack Preference**: Node.js/Express or Python/FastAPI?
2. **Database Requirements**: Do you need persistent storage beyond file system?
3. **Authentication**: How should the service authenticate with Git repositories?
4. **Deployment Environment**: Kubernetes, Docker Compose, or standalone containers?
5. **Monitoring Integration**: Existing observability stack (Prometheus, Grafana, etc.)?

**Next Steps:**
1. Review this specification with the team
2. Clarify any technical questions or requirements
3. Set up development environment and repository
4. Begin implementation starting with Phase 1 core service