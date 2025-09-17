# DevTeam Runner Service — Atomic Task List (Hierarchical)

Provenance: Expanded from [ai_docs/context/core_docs/wbs.md](ai_docs/context/core_docs/wbs.md)

Phases are sequential: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9

<!-- Phase 1: Foundations & Ops Validation (Dependencies: [])

- 1.1 Compose up/down scripts verified (Dependencies: [])
  - 1.1.1 Build images: run "docker compose build"
  - 1.1.2 Start services: run "docker compose up -d api worker redis db"
  - 1.1.3 Verify services: run "docker ps" and confirm api, worker, redis, db are up
  - 1.1.4 Stop services: run "docker compose down -v" and confirm containers removed
  - 1.1.5 Validate outputs of Task 1.1
  - 1.1.6 Verify correctness of Task 1.1 against acceptance criteria
    • <criterion 1: Docker services start within ≤10s (p95) [source: PRD]>
    • <criterion 2: All required services (api, worker, redis, db) are running and healthy [source: PRD]>
    • <criterion 3: Container cleanup completes within ≤60s after docker compose down [source: PRD]>
    • <criterion 4: Service availability meets 99.9% uptime target during operation [source: PRD]>
  - 1.1.7 Document results of Task 1.1 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

- 1.2 Run Alembic migrations (Dependencies: [1.1])
  - 1.2.1 Start database service: run "cd docker && ./start.sh"
  - 1.2.2 Run migrations: execute "alembic upgrade head" inside API container
  - 1.2.3 Verify migration: confirm alembic version table and head applied

- 1.3 Validate dependency tools available in containers (Dependencies: [1.1])
  - 1.3.1 Check git: run "git --version" inside API container
  - 1.3.2 Check node: run "npm --version" or "node --version" inside API container
  - 1.3.3 Check aider: run "aider --version" inside API container (or document absence) -->
PHASE 1 COMPLETED

Phase 2: Events → Worker Wire-up (Dependencies: [1])

- 2.1 Mount events router; validate request schema; persist Event (Dependencies: [1.2])
  - 2.1.1 Add router mount for events in API
  - 2.1.2 Implement request schema validation for POST /events
  - 2.1.3 Persist incoming event to database via repository
  - 2.1.4 Create smoke test for POST /events endpoint
  - 2.1.5 Execute smoke test and verify 202 response

- 2.2 Dispatch Celery task with correlationId (Dependencies: [2.1])
  - 2.2.1 Enqueue Celery job from POST /events with correlationId
  - 2.2.2 Confirm task appears in worker logs with structured fields

- 2.3 Confirm worker consumes and logs structured event (Dependencies: [2.2])
  - 2.3.1 Start worker service and tail logs
  - 2.3.2 Assert processed event includes correlationId and projectId


Phase 3: Workflow Engine Integration (Dependencies: [2])
- 3.1 Register DEVTEAM_AUTOMATION workflow (Dependencies: [2.3])
  - 3.1.1 Add workflow registration in workflow registry
  - 3.1.2 Ensure workflow can be resolved by name/id

- 3.2 Implement minimal nodes to prove SELECT→PREP skeleton (Dependencies: [3.1])
  - 3.2.1 Implement SELECT node stub returning fixed plan
  - 3.2.2 Implement PREP node stub persisting initial task_context

- 3.3 Execute Workflow.run and persist task_context (Dependencies: [3.2])
  - 3.3.1 Trigger workflow execution path from worker task
  - 3.3.2 Verify task_context written to database

Phase 4: Repository Initialization Workflow (Dependencies: [3])
- 4.1 Implement repository cache management (Dependencies: [3.3])
  - 4.1.1 Create cache directory structure for repositories
  - 4.1.2 Implement repository existence check logic

- 4.2 Implement repository clone functionality (Dependencies: [4.1])
  - 4.2.1 Clone repository if absent from cache
  - 4.2.2 Validate successful clone operation

- 4.3 Implement repository fetch functionality (Dependencies: [4.1])
  - 4.3.1 Fetch latest changes if repository exists
  - 4.3.2 Validate successful fetch operation

- 4.4 Ensure default template is only referenced (no task_lists.md creation) (Dependencies: [4.2, 4.3])
  - 4.4.1 Read default template without writing files into target repo

- 4.5 Implement per-project container management (Dependencies: [4.2, 4.3])
  - 4.5.1 Start or reuse per-project container

- 4.6 Implement container healthcheck (Dependencies: [4.5])
  - 4.6.1 Run "git --version" inside the container
  - 4.6.2 Run "node --version" inside the container
  - 4.6.3 Validate healthcheck results

Phase 5: DevTeam Automation API (Profile B) (Dependencies: [4])
- 5.1 POST /api/devteam/automation/initialize (Dependencies: [4.6])
  - 5.1.1 Implement endpoint returning 202 with {executionId,eventId}
  - 5.1.2 Wire endpoint to enqueue initial workflow event

- 5.2 Implement status projection data model (Dependencies: [5.1])
  - 5.2.1 Define status projection schema
  - 5.2.2 Implement status projection read model

- 5.3 GET /api/devteam/automation/status/{projectId} (Dependencies: [5.2])
  - 5.3.1 Implement status endpoint
  - 5.3.2 Return JSON state for projectId

- 5.4 POST /api/devteam/automation/pause/{projectId} (Dependencies: [5.1])
  - 5.4.1 Implement transition running→paused with validation

- 5.5 POST /api/devteam/automation/resume/{projectId} (Dependencies: [5.4])
  - 5.5.1 Implement transition paused→running with validation

- 5.6 POST /api/devteam/automation/stop/{projectId} (Dependencies: [5.1])
  - 5.6.1 Implement transition running→stopped with validation

- 5.7 Optional Idempotency-Key support (TTL 6h) (Dependencies: [5.1])
  - 5.7.1 Implement idempotency key handling on initialize

Phase 6: WebSocket /ws/devteam (Profile C) (Dependencies: [5])

- 6.1 Implement WS endpoint /ws/devteam (Dependencies: [5.3])
  - 6.1.1 Implement endpoint accepting connections by projectId
  - 6.1.2 Implement connection routing by projectId

- 6.2 Implement WebSocket frame transmission (Dependencies: [6.1])
  - 6.2.1 Send execution-update frames with ≤500ms latency
  - 6.2.2 Send execution-log frames with ≤500ms latency

- 6.3 Envelope {type, ts, projectId, payload} (Dependencies: [6.2])
  - 6.3.1 Implement standardized envelope for all frames

- 6.4 Linear reconnect; payload size limits at gateway (Dependencies: [6.2])
  - 6.4.1 Implement client linear reconnect logic in demo client

Phase 7: Execute Code Change + Verify (combined) (Dependencies: [6])

- 7.1 Generate deterministic prompt (Dependencies: [6.4])
  - 7.1.1 Generate prompt from templates and context

- 7.2 Execute Aider code changes (Dependencies: [7.1])
  - 7.2.1 Run Aider to apply code changes

- 7.3 Capture execution artifacts (Dependencies: [7.2])
  - 7.3.1 Capture diff output
  - 7.3.2 Capture stdout output
  - 7.3.3 Capture filesModified list

- 7.4 Execute build verification (Dependencies: [7.3])
  - 7.4.1 Execute "npm ci" in target repository
  - 7.4.2 Execute "npm run build" in target repository

- 7.5 Implement build retry logic (Dependencies: [7.4])
  - 7.5.1 Implement retry mechanism for failed builds
  - 7.5.2 Limit retries to maximum of 2 attempts
  - 7.5.3 Capture logs for each retry attempt

- 7.6 Merge changes to main branch (Dependencies: [7.5])
  - 7.6.1 Merge changes to main branch

- 7.7 Push changes to remote repository (Dependencies: [7.6])
  - 7.7.1 Push to remote repository

- 7.8 Update status projection (Dependencies: [7.7])
  - 7.8.1 Update status model with completion

Phase 8: Persistence & Observability Polish (Dependencies: [7])

- 8.1 Ensure task_context schema stable; status projection matches API (Dependencies: [3.3,5.2])
  - 8.1.1 Review and stabilize task_context schema
  - 8.1.2 Align status projection fields with API contract

- 8.2 Add structured logging fields across API and Worker (Dependencies: [2.3])
  - 8.2.1 Add correlationId, projectId, executionId to logs
  - 8.2.2 Ensure logs redact tokens/secrets

- 8.3 Record queue latency and verification duration (minimal) (Dependencies: [7.8])
  - 8.3.1 Emit metric for queue latency (enqueue→consume)
  - 8.3.2 Emit metric for verification duration

Phase 9: Local Scripts for Build/Run (Dependencies: [8])

- 9.1 Create/validate shell targets for build/test/migrate/run (Dependencies: [1.1,1.2,7.8])
  - 9.1.1 Implement build script target
  - 9.1.2 Implement test script target
  - 9.1.3 Implement migrate script target (alembic upgrade head)
  - 9.1.4 Implement run script to bring up stack

- 9.2 Document rollback procedure (Dependencies: [9.1])
  - 9.2.1 Write rollback steps for failed deployments