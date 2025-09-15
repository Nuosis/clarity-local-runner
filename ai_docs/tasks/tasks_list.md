# DevTeam Runner Service — Atomic Task List (Hierarchical)

Provenance: Expanded from [ai_docs/context/core_docs/wbs.md](ai_docs/context/core_docs/wbs.md)

Phases are sequential: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9

Phase 1: Foundations & Ops Validation (Dependencies: [])

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
  - 1.2.1 Start database service: run "docker compose up -d db"
  - 1.2.2 Run migrations: execute "alembic upgrade head" inside API container
  - 1.2.3 Verify migration: confirm alembic version table and head applied
  - 1.2.4 Validate outputs of Task 1.2
  - 1.2.5 Verify correctness of Task 1.2 against acceptance criteria
    • <criterion 1: Alembic migrations complete successfully with no errors [source: PRD/ADD]>
    • <criterion 2: Database schema matches expected Event model structure [source: ADD]>
    • <criterion 3: Migration execution completes within reasonable time limits [source: PRD]>
    • <criterion 4: Database connection and persistence layer operational [source: ADD]>
  - 1.2.6 Document results of Task 1.2 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

- 1.3 Validate dependency tools available in containers (Dependencies: [1.1])
  - 1.3.1 Check git: run "git --version" inside API container
  - 1.3.2 Check node: run "npm --version" or "node --version" inside API container
  - 1.3.3 Check aider: run "aider --version" inside API container (or document absence)
  - 1.3.4 Validate outputs of Task 1.3
  - 1.3.5 Verify correctness of Task 1.3 against acceptance criteria
    • <criterion 1: Git tool available and functional in API container [source: PRD]>
    • <criterion 2: Node/npm tools available for build verification [source: ADD]>
    • <criterion 3: Aider tool availability documented (present or absent) [source: PRD]>
    • <criterion 4: All dependency tools meet version requirements [source: PRD]>
  - 1.3.6 Document results of Task 1.3 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

Phase 2: Events → Worker Wire-up (Dependencies: [1])

- 2.1 Mount events router; validate request schema; persist Event (Dependencies: [1.2])
  - 2.1.1 Add router mount for events in API
  - 2.1.2 Implement request schema validation for POST /events
  - 2.1.3 Persist incoming event to database via repository
  - 2.1.4 Create smoke test for POST /events endpoint
  - 2.1.5 Execute smoke test and verify 202 response
  - 2.1.6 Validate outputs of Task 2.1
  - 2.1.7 Verify correctness of Task 2.1 against acceptance criteria
    • <criterion 1: POST /events endpoint responds with 202 Accepted and task_id [source: PRD]>
    • <criterion 2: Request schema validation enforced with comprehensive input validation [source: PRD]>
    • <criterion 3: Event persistence to database completes within ≤1s [source: PRD]>
    • <criterion 4: Smoke test passes with proper 202 response validation [source: PRD]>
    • <criterion 5: Structured logging includes correlationId and projectId [source: ADD]>
  - 2.1.8 Document results of Task 2.1 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

- 2.2 Dispatch Celery task with correlationId (Dependencies: [2.1])
  - 2.2.1 Enqueue Celery job from POST /events with correlationId
  - 2.2.2 Confirm task appears in worker logs with structured fields
  - 2.2.3 Validate outputs of Task 2.2
  - 2.2.4 Verify correctness of Task 2.2 against acceptance criteria
    • <criterion 1: Celery task enqueued successfully with correlationId [source: PRD/ADD]>
    • <criterion 2: Queue latency p95 ≤5s from POST /events to worker execution [source: PRD]>
    • <criterion 3: Task appears in worker logs with structured fields [source: ADD]>
    • <criterion 4: Celery worker concurrency ≥4 workers operational [source: PRD]>
  - 2.2.5 Document results of Task 2.2 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

- 2.3 Confirm worker consumes and logs structured event (Dependencies: [2.2])
  - 2.3.1 Start worker service and tail logs
  - 2.3.2 Assert processed event includes correlationId and projectId
  - 2.3.3 Validate outputs of Task 2.3
  - 2.3.4 Verify correctness of Task 2.3 against acceptance criteria
    • <criterion 1: Worker consumes events successfully with structured logging [source: ADD]>
    • <criterion 2: Processed event includes correlationId and projectId fields [source: ADD]>
    • <criterion 3: Worker logs show proper event processing flow [source: ADD]>
    • <criterion 4: Error handling and graceful degradation operational [source: PRD]>
  - 2.3.5 Document results of Task 2.3 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

Phase 3: Workflow Engine Integration (Dependencies: [2])

- 3.1 Register DEVTEAM_AUTOMATION workflow (Dependencies: [2.3])
  - 3.1.1 Add workflow registration in workflow registry
  - 3.1.2 Ensure workflow can be resolved by name/id
  - 3.1.3 Validate outputs of Task 3.1
  - 3.1.4 Verify correctness of Task 3.1 against acceptance criteria
    • <criterion 1: DEVTEAM_AUTOMATION workflow registered successfully in workflow registry [source: ADD]>
    • <criterion 2: Workflow can be resolved by name/id through WorkflowRegistry [source: ADD]>
    • <criterion 3: Workflow follows GenAI Launchpad engine patterns [source: PRD/ADD]>
    • <criterion 4: Pydantic-validated event schemas properly configured [source: ADD]>
  - 3.1.5 Document results of Task 3.1 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

- 3.2 Implement minimal nodes to prove SELECT→PREP skeleton (Dependencies: [3.1])
  - 3.2.1 Implement SELECT node stub returning fixed plan
  - 3.2.2 Implement PREP node stub persisting initial task_context
  - 3.2.3 Validate outputs of Task 3.2
  - 3.2.4 Verify correctness of Task 3.2 against acceptance criteria
    • <criterion 1: SELECT node returns fixed plan successfully [source: ADD]>
    • <criterion 2: PREP node persists initial task_context to database [source: ADD]>
    • <criterion 3: Node execution follows workflow DAG patterns [source: ADD]>
    • <criterion 4: Task context persistence completes within ≤1s [source: PRD]>
  - 3.2.5 Document results of Task 3.2 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

- 3.3 Execute Workflow.run and persist task_context (Dependencies: [3.2])
  - 3.3.1 Trigger workflow execution path from worker task
  - 3.3.2 Verify task_context written to database
  - 3.3.3 Validate outputs of Task 3.3
  - 3.3.4 Verify correctness of Task 3.3 against acceptance criteria
    • <criterion 1: Workflow.run() executes successfully from worker task [source: ADD]>
    • <criterion 2: Task_context written to database with proper structure [source: ADD]>
    • <criterion 3: Workflow execution follows SELECT→PREP skeleton [source: ADD]>
    • <criterion 4: Event.task_context persistence within ≤1s SLA [source: PRD]>
  - 3.3.5 Document results of Task 3.3 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

Phase 4: Repository Initialization Workflow (Dependencies: [3])

- 4.1 Implement repository cache management (Dependencies: [3.3])
  - 4.1.1 Create cache directory structure for repositories
  - 4.1.2 Implement repository existence check logic
  - 4.1.3 Validate outputs of Task 4.1
  - 4.1.4 Verify correctness of Task 4.1 against acceptance criteria
    • <criterion 1: Cache directory structure created successfully for repositories [source: ADD]>
    • <criterion 2: Repository existence check logic operational [source: ADD]>
    • <criterion 3: Resource management and cleanup policies implemented [source: PRD]>
    • <criterion 4: Customer isolation with separate working directories [source: PRD]>
  - 4.1.5 Document results of Task 4.1 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

- 4.2 Implement repository clone functionality (Dependencies: [4.1])
  - 4.2.1 Clone repository if absent from cache
  - 4.2.2 Validate successful clone operation
  - 4.2.3 Validate outputs of Task 4.2
  - 4.2.4 Verify correctness of Task 4.2 against acceptance criteria
    • <criterion 1: Repository clone operation completes successfully [source: ADD]>
    • <criterion 2: Git authentication with minimal permissions enforced [source: PRD]>
    • <criterion 3: Clone operation includes proper error handling [source: PRD]>
    • <criterion 4: Repository accessible with provided authentication [source: PRD]>
  - 4.2.5 Document results of Task 4.2 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

- 4.3 Implement repository fetch functionality (Dependencies: [4.1])
  - 4.3.1 Fetch latest changes if repository exists
  - 4.3.2 Validate successful fetch operation
  - 4.3.3 Validate outputs of Task 4.3
  - 4.3.4 Verify correctness of Task 4.3 against acceptance criteria
    • <criterion 1: Repository fetch operation retrieves latest changes successfully [source: ADD]>
    • <criterion 2: Fetch operation handles network failures gracefully [source: PRD]>
    • <criterion 3: Git operations maintain repository integrity [source: PRD]>
    • <criterion 4: Fetch completes within reasonable time limits [source: PRD]>
  - 4.3.5 Document results of Task 4.3 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

- 4.4 Ensure default template is only referenced (no task_lists.md creation) (Dependencies: [4.2, 4.3])
  - 4.4.1 Read default template without writing files into target repo
  - 4.4.2 Validate outputs of Task 4.4
  - 4.4.3 Verify correctness of Task 4.4 against acceptance criteria
    • <criterion 1: Default template read successfully without file creation [source: ADD]>
    • <criterion 2: Template content properly formatted and valid [source: ADD]>
    • <criterion 3: No unauthorized file writes to target repository [source: ADD]>
    • <criterion 4: Template reference maintains data integrity [source: PRD]>
  - 4.4.4 Document results of Task 4.4 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

- 4.5 Implement per-project container management (Dependencies: [4.2, 4.3])
  - 4.5.1 Start or reuse per-project container
  - 4.5.2 Validate outputs of Task 4.5
  - 4.5.3 Verify correctness of Task 4.5 against acceptance criteria
    • <criterion 1: Per-project container starts or reuses successfully [source: ADD]>
    • <criterion 2: Container bootstrap time p50 ≤5s, p95 ≤10s [source: PRD]>
    • <criterion 3: Container resource limits enforced (1 vCPU, 1 GiB RAM) [source: ADD]>
    • <criterion 4: Container isolation and security policies applied [source: PRD]>
  - 4.5.4 Document results of Task 4.5 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

- 4.6 Implement container healthcheck (Dependencies: [4.5])
  - 4.6.1 Run "git --version" inside the container
  - 4.6.2 Run "node --version" inside the container
  - 4.6.3 Validate healthcheck results
  - 4.6.4 Validate outputs of Task 4.6
  - 4.6.5 Verify correctness of Task 4.6 against acceptance criteria
    • <criterion 1: Git version check passes in container [source: ADD]>
    • <criterion 2: Node version check passes in container [source: ADD]>
    • <criterion 3: Healthcheck command executes successfully [source: ADD]>
    • <criterion 4: Container restart policy operational (always restart) [source: ADD]>
  - 4.6.6 Document results of Task 4.6 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

Phase 5: DevTeam Automation API (Profile B) (Dependencies: [4])

- 5.1 POST /api/devteam/automation/initialize (Dependencies: [4.6])
  - 5.1.1 Implement endpoint returning 202 with {executionId,eventId}
  - 5.1.2 Wire endpoint to enqueue initial workflow event
  - 5.1.3 Validate outputs of Task 5.1
  - 5.1.4 Verify correctness of Task 5.1 against acceptance criteria
    • <criterion 1: Endpoint returns 202 Accepted with executionId and eventId [source: PRD/ADD]>
    • <criterion 2: Workflow event enqueued successfully to Celery [source: PRD]>
    • <criterion 3: Comprehensive input validation enforced [source: PRD]>
    • <criterion 4: Idempotency-Key support operational (TTL 6h) [source: ADD]>
    • <criterion 5: Structured logging includes correlationId and projectId [source: ADD]>
  - 5.1.5 Document results of Task 5.1 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

- 5.2 Implement status projection data model (Dependencies: [5.1])
  - 5.2.1 Define status projection schema
  - 5.2.2 Implement status projection read model
  - 5.2.3 Validate outputs of Task 5.2
  - 5.2.4 Verify correctness of Task 5.2 against acceptance criteria
    • <criterion 1: Status projection schema matches API contract [source: ADD]>
    • <criterion 2: Read model projects from Event.task_context successfully [source: ADD]>
    • <criterion 3: Status transitions follow defined state machine [source: ADD]>
    • <criterion 4: Data consistency maintained across projections [source: PRD]>
  - 5.2.5 Document results of Task 5.2 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

- 5.3 GET /api/devteam/automation/status/{projectId} (Dependencies: [5.2])
  - 5.3.1 Implement status endpoint
  - 5.3.2 Return JSON state for projectId
  - 5.3.3 Validate outputs of Task 5.3
  - 5.3.4 Verify correctness of Task 5.3 against acceptance criteria
    • <criterion 1: Status endpoint responds within ≤200ms (quick API) [source: PRD]>
    • <criterion 2: JSON response includes all required status fields [source: ADD]>
    • <criterion 3: ProjectId routing and validation operational [source: ADD]>
    • <criterion 4: Error handling for non-existent projects [source: PRD]>
  - 5.3.5 Document results of Task 5.3 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

- 5.4 POST /api/devteam/automation/pause/{projectId} (Dependencies: [5.1])
  - 5.4.1 Implement transition running→paused with validation
  - 5.4.2 Validate outputs of Task 5.4
  - 5.4.3 Verify correctness of Task 5.4 against acceptance criteria
    • <criterion 1: State transition running→paused enforced [source: ADD]>
    • <criterion 2: Invalid transitions return 409 Conflict [source: ADD]>
    • <criterion 3: Idempotent operations with proper validation [source: PRD]>
    • <criterion 4: Workflow execution paused successfully [source: ADD]>
  - 5.4.4 Document results of Task 5.4 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

- 5.5 POST /api/devteam/automation/resume/{projectId} (Dependencies: [5.4])
  - 5.5.1 Implement transition paused→running with validation
  - 5.5.2 Validate outputs of Task 5.5
  - 5.5.3 Verify correctness of Task 5.5 against acceptance criteria
    • <criterion 1: State transition paused→running enforced [source: ADD]>
    • <criterion 2: Invalid transitions return 409 Conflict [source: ADD]>
    • <criterion 3: Workflow execution resumes successfully [source: ADD]>
    • <criterion 4: Resume operation maintains execution context [source: PRD]>
  - 5.5.4 Document results of Task 5.5 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

- 5.6 POST /api/devteam/automation/stop/{projectId} (Dependencies: [5.1])
  - 5.6.1 Implement transition running→stopped with validation
  - 5.6.2 Validate outputs of Task 5.6
  - 5.6.3 Verify correctness of Task 5.6 against acceptance criteria
    • <criterion 1: State transition running→stopping→stopped enforced [source: ADD]>
    • <criterion 2: Invalid transitions return 409 Conflict [source: ADD]>
    • <criterion 3: Workflow execution stops gracefully [source: ADD]>
    • <criterion 4: Resource cleanup initiated on stop [source: PRD]>
  - 5.6.4 Document results of Task 5.6 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

- 5.7 Optional Idempotency-Key support (TTL 6h) (Dependencies: [5.1])
  - 5.7.1 Implement idempotency key handling on initialize
  - 5.7.2 Validate outputs of Task 5.7
  - 5.7.3 Verify correctness of Task 5.7 against acceptance criteria
    • <criterion 1: Idempotency-Key header processing operational [source: ADD]>
    • <criterion 2: Key hash stored with 6h TTL [source: ADD]>
    • <criterion 3: Duplicate requests return 409 with Location header [source: ADD]>
    • <criterion 4: Replay protection prevents duplicate operations [source: PRD]>
  - 5.7.4 Document results of Task 5.7 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

Phase 6: WebSocket /ws/devteam (Profile C) (Dependencies: [5])

- 6.1 Implement WS endpoint /ws/devteam (Dependencies: [5.3])
  - 6.1.1 Implement endpoint accepting connections by projectId
  - 6.1.2 Implement connection routing by projectId
  - 6.1.3 Validate outputs of Task 6.1
  - 6.1.4 Verify correctness of Task 6.1 against acceptance criteria
    • <criterion 1: WebSocket endpoint /ws/devteam operational [source: ADD]>
    • <criterion 2: Connection routing by projectId functional [source: ADD]>
    • <criterion 3: WebSocket handshake completes within ≤300ms [source: PRD]>
    • <criterion 4: API gateway auth passthrough operational [source: ADD]>
  - 6.1.5 Document results of Task 6.1 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

- 6.2 Implement WebSocket frame transmission (Dependencies: [6.1])
  - 6.2.1 Send execution-update frames with ≤500ms latency
  - 6.2.2 Send execution-log frames with ≤500ms latency
  - 6.2.3 Validate outputs of Task 6.2
  - 6.2.4 Verify correctness of Task 6.2 against acceptance criteria
    • <criterion 1: Execution-update frames delivered within ≤500ms latency [source: PRD]>
    • <criterion 2: Execution-log frames delivered within ≤500ms latency [source: PRD]>
    • <criterion 3: Frame transmission best-effort delivery operational [source: ADD]>
    • <criterion 4: Real-time progress and log streaming functional [source: PRD]>
  - 6.2.5 Document results of Task 6.2 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

- 6.3 Envelope {type, ts, projectId, payload} (Dependencies: [6.2])
  - 6.3.1 Implement standardized envelope for all frames
  - 6.3.2 Validate outputs of Task 6.3
  - 6.3.3 Verify correctness of Task 6.3 against acceptance criteria
    • <criterion 1: Standardized envelope format {type, ts, projectId, payload} implemented [source: ADD]>
    • <criterion 2: All WebSocket frames use consistent envelope structure [source: ADD]>
    • <criterion 3: Message validation enforces envelope schema [source: PRD]>
    • <criterion 4: ProjectId included for proper frontend routing [source: PRD]>
  - 6.3.4 Document results of Task 6.3 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

- 6.4 Linear reconnect; payload size limits at gateway (Dependencies: [6.2])
  - 6.4.1 Implement client linear reconnect logic in demo client
  - 6.4.2 Validate outputs of Task 6.4
  - 6.4.3 Verify correctness of Task 6.4 against acceptance criteria
    • <criterion 1: Linear reconnect logic operational with backoff capped at 30s [source: PRD/ADD]>
    • <criterion 2: Connection recovery from failures automatic [source: PRD]>
    • <criterion 3: Payload size limits enforced at gateway level [source: ADD]>
    • <criterion 4: Demo client demonstrates reconnection functionality [source: ADD]>
  - 6.4.4 Document results of Task 6.4 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

Phase 7: Execute Code Change + Verify (combined) (Dependencies: [6])

- 7.1 Generate deterministic prompt (Dependencies: [6.4])
  - 7.1.1 Generate prompt from templates and context
  - 7.1.2 Validate prompt generation
  - 7.1.3 Validate outputs of Task 7.1
  - 7.1.4 Verify correctness of Task 7.1 against acceptance criteria
    • <criterion 1: Deterministic prompt template generates consistent output [source: ADD]>
    • <criterion 2: Prompt construction completes within ≤2s (prep operation) [source: PRD]>
    • <criterion 3: Template includes proper task context and requirements [source: ADD]>
    • <criterion 4: Generated prompts maintain quality and consistency [source: PRD]>
  - 7.1.5 Document results of Task 7.1 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

- 7.2 Execute Aider code changes (Dependencies: [7.1])
  - 7.2.1 Run Aider to apply code changes
  - 7.2.2 Validate Aider execution
  - 7.2.3 Validate outputs of Task 7.2
  - 7.2.4 Verify correctness of Task 7.2 against acceptance criteria
    • <criterion 1: Aider tool integration executes successfully [source: PRD]>
    • <criterion 2: Code changes complete within ≤30s (implement operation) [source: PRD]>
    • <criterion 3: Aider execution includes proper error handling [source: PRD]>
    • <criterion 4: Tool remains stable and available for implementation [source: PRD]>
  - 7.2.5 Document results of Task 7.2 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

- 7.3 Capture execution artifacts (Dependencies: [7.2])
  - 7.3.1 Capture diff output
  - 7.3.2 Capture stdout output
  - 7.3.3 Capture filesModified list
  - 7.3.4 Validate outputs of Task 7.3
  - 7.3.5 Verify correctness of Task 7.3 against acceptance criteria
    • <criterion 1: Diff output captured with complete change details [source: PRD]>
    • <criterion 2: Stdout output captured for operation visibility [source: PRD]>
    • <criterion 3: FilesModified list accurately reflects changes [source: PRD]>
    • <criterion 4: Artifacts available for verification and audit [source: PRD]>
  - 7.3.6 Document results of Task 7.3 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

- 7.4 Execute build verification (Dependencies: [7.3])
  - 7.4.1 Execute "npm ci" in target repository
  - 7.4.2 Execute "npm run build" in target repository
  - 7.4.3 Validate outputs of Task 7.4
  - 7.4.4 Verify correctness of Task 7.4 against acceptance criteria
    • <criterion 1: Build verification completes within ≤60s (verify operation) [source: PRD]>
    • <criterion 2: npm ci and npm run build execute successfully [source: ADD]>
    • <criterion 3: Build-only verification policy enforced (MVP) [source: ADD]>
    • <criterion 4: Stop-on-error semantics prevent progression on build failures [source: PRD]>
  - 7.4.5 Document results of Task 7.4 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

- 7.5 Implement build retry logic (Dependencies: [7.4])
  - 7.5.1 Implement retry mechanism for failed builds
  - 7.5.2 Limit retries to maximum of 2 attempts
  - 7.5.3 Capture logs for each retry attempt
  - 7.5.4 Validate outputs of Task 7.5
  - 7.5.5 Verify correctness of Task 7.5 against acceptance criteria
    • <criterion 1: Retry mechanism limited to maximum 2 attempts [source: ADD]>
    • <criterion 2: Each retry attempt logged with structured details [source: ADD]>
    • <criterion 3: Error recovery and graceful degradation operational [source: PRD]>
    • <criterion 4: Retry logic prevents infinite loops and resource exhaustion [source: PRD]>
  - 7.5.6 Document results of Task 7.5 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

- 7.6 Merge changes to main branch (Dependencies: [7.5])
  - 7.6.1 Merge changes to main branch
  - 7.6.2 Validate merge operation
  - 7.6.3 Validate outputs of Task 7.6
  - 7.6.4 Verify correctness of Task 7.6 against acceptance criteria
    • <criterion 1: Changes merged to main branch successfully [source: ADD]>
    • <criterion 2: Merge operation maintains repository integrity [source: PRD]>
    • <criterion 3: Git operations follow standard development practices [source: PRD]>
    • <criterion 4: Branch merge completes without conflicts [source: ADD]>
  - 7.6.5 Document results of Task 7.6 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

- 7.7 Push changes to remote repository (Dependencies: [7.6])
  - 7.7.1 Push to remote repository
  - 7.7.2 Validate push operation
  - 7.7.3 Validate outputs of Task 7.7
  - 7.7.4 Verify correctness of Task 7.7 against acceptance criteria
    • <criterion 1: Push to remote repository completes successfully [source: ADD]>
    • <criterion 2: Remote repository updated with latest changes [source: ADD]>
    • <criterion 3: Push operation includes proper authentication [source: PRD]>
    • <criterion 4: Git push maintains version control integrity [source: PRD]>
  - 7.7.5 Document results of Task 7.7 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

- 7.8 Update status projection (Dependencies: [7.7])
  - 7.8.1 Update status model with completion
  - 7.8.2 Validate status update
  - 7.8.3 Validate outputs of Task 7.8
  - 7.8.4 Verify correctness of Task 7.8 against acceptance criteria
    • <criterion 1: Status projection updated with completion status [source: ADD]>
    • <criterion 2: Status model reflects current execution state [source: ADD]>
    • <criterion 3: Status update persisted within ≤1s [source: PRD]>
    • <criterion 4: Execution state available via status API [source: ADD]>
  - 7.8.5 Document results of Task 7.8 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

Phase 8: Persistence & Observability Polish (Dependencies: [7])

- 8.1 Ensure task_context schema stable; status projection matches API (Dependencies: [3.3,5.2])
  - 8.1.1 Review and stabilize task_context schema
  - 8.1.2 Align status projection fields with API contract
  - 8.1.3 Validate outputs of Task 8.1
  - 8.1.4 Verify correctness of Task 8.1 against acceptance criteria
    • <criterion 1: Task_context schema stabilized and consistent [source: ADD]>
    • <criterion 2: Status projection fields aligned with API contract [source: ADD]>
    • <criterion 3: Schema changes maintain backward compatibility [source: PRD]>
    • <criterion 4: Data consistency maintained across all projections [source: PRD]>
  - 8.1.5 Document results of Task 8.1 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

- 8.2 Add structured logging fields across API and Worker (Dependencies: [2.3])
  - 8.2.1 Add correlationId, projectId, executionId to logs
  - 8.2.2 Ensure logs redact tokens/secrets
  - 8.2.3 Validate outputs of Task 8.2
  - 8.2.4 Verify correctness of Task 8.2 against acceptance criteria
    • <criterion 1: Structured logging includes correlationId, projectId, executionId [source: ADD]>
    • <criterion 2: Logs redact tokens and secrets properly [source: ADD]>
    • <criterion 3: Logging spans both API and Worker components [source: ADD]>
    • <criterion 4: Log levels and structured fields operational [source: PRD]>
  - 8.2.5 Document results of Task 8.2 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

- 8.3 Record queue latency and verification duration (minimal) (Dependencies: [7.8])
  - 8.3.1 Emit metric for queue latency (enqueue→consume)
  - 8.3.2 Emit metric for verification duration
  - 8.3.3 Validate outputs of Task 8.3
  - 8.3.4 Verify correctness of Task 8.3 against acceptance criteria
    • <criterion 1: Queue latency metrics emitted (enqueue→consume) [source: ADD]>
    • <criterion 2: Verification duration metrics captured [source: ADD]>
    • <criterion 3: Metrics collection minimal and efficient [source: ADD]>
    • <criterion 4: Performance monitoring operational [source: PRD]>
  - 8.3.5 Document results of Task 8.3 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

Phase 9: Local Scripts for Build/Run (Dependencies: [8])

- 9.1 Create/validate shell targets for build/test/migrate/run (Dependencies: [1.1,1.2,7.8])
  - 9.1.1 Implement build script target
  - 9.1.2 Implement test script target
  - 9.1.3 Implement migrate script target (alembic upgrade head)
  - 9.1.4 Implement run script to bring up stack
  - 9.1.5 Validate outputs of Task 9.1
  - 9.1.6 Verify correctness of Task 9.1 against acceptance criteria
    • <criterion 1: Build script target operational [source: ADD]>
    • <criterion 2: Test script target functional [source: ADD]>
    • <criterion 3: Migrate script executes alembic upgrade head [source: ADD]>
    • <criterion 4: Run script brings up complete stack [source: ADD]>
    • <criterion 5: All scripts validated and documented [source: PRD]>
  - 9.1.7 Document results of Task 9.1 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)

- 9.2 Document rollback procedure (Dependencies: [9.1])
  - 9.2.1 Write rollback steps for failed deployments
  - 9.2.2 Validate outputs of Task 9.2
  - 9.2.3 Verify correctness of Task 9.2 against acceptance criteria
  - 9.2.4 Document results of Task 9.2 in [ai_docs/tasks/task_outcomes.md](ai_docs/tasks/task_outcomes.md)