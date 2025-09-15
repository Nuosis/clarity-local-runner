# DevTeam Runner Service — System Architecture Document

Status: MVP Profiles locked (Containers=C, WebSocket=C, Automation API=B, Verify/TaskList/Concurrency=B)

Source inputs:
- [project_charter.md](ai_docs/context/core_docs/project_charter.md)
- [prd.md](ai_docs/context/core_docs/prd.md)
- [devTeam_integration_patterns.md](ai_docs/context/core_docs/devTeam_integration_patterns.md)
- [devTeam_autonomous_execution_workflows.md](ai_docs/context/core_docs/devTeam_autonomous_execution_workflows.md)

## 1. Executive Summary
FastAPI microservice enabling autonomous SELECT→PREP→IMPLEMENT→VERIFY execution with real-time visibility and per-project shared containers for fastest bootstrap.

## 2. MVP Operating Profiles (decisions)
- Containers: Profile C — per-project long-lived container; 1 vCPU, 1 GiB RAM; single named volume TTL 7 days; env-scoped secrets; open egress; healthcheck + always restart.
- WebSocket: Profile C — API-gateway-auth passthrough, route by projectId only; envelope {type, ts, projectId, payload}; no throttle; best-effort; linear reconnect; no replay.
- DevTeam Automation API: Profile B — Idempotency-Key optional (TTL 6h); replay returns 409 with Location of original; status model {status, progress, currentTask, totals{completed,total}, executionId}; transitions: idle→initializing→running→paused→running→completed|error; stop only from running; injection anytime; conflicts 409.
- Verify/TaskList/Concurrency: Profile B — lenient task_lists.md parsing; Verify uses build-only (npm ci; npm run build); concurrency per-project=1, global=5, round-robin fairness.

## 3. Architecture Overview
- API layer (FastAPI) exposes Core Runner + DevTeam Automation endpoints.
- Event ingestion at POST /events persists Event and enqueues Celery task.
- Worker executes DAG via Workflow engine, persists task_context.
- WebSocket service streams progress/logs.
- Container manager provisions per-project shared dev container.
- Persistence: Supabase Postgres for Event; Redis for Celery broker/backend.

Key code anchors:
- Events API mount: [router.include_router](app/api/router.py:14)
- Event handler: [events_endpoint()](app/api/endpoint.py:43)
- Celery enqueue: [celery_app.send_task](app/api/endpoint.py:72)
- Worker task: [process_incoming_event()](app/worker/tasks.py:19)
- Workflow engine: [Workflow.run()](app/core/workflow.py:105)
- Workflow schema parse: [Workflow.__run()](app/core/workflow.py:119)
- Event model: [Event](app/database/event.py:13)
- Alembic env: [env.py](app/alembic/env.py:11)
- Celery config: [celery_app](app/worker/config.py:39)

## 4. Data Flow
1) Client calls POST /api/devteam/automation/initialize → creates executionId.
2) Service writes Event, enqueues Celery; returns 202.
3) Worker loads Event, runs workflow nodes, updates Event.task_context.
4) WebSocket emits execution-update and execution-log frames.
5) On completion/failure, status available via GET /api/devteam/automation/status/{projectId}.

## 5. API Specification
### 5.1 Core Runner API
- GET /health → dependency validation (git, aider, FS).
- POST /prep → repo prep and branch creation.
- POST /implement → run implementation tool (Aider).
- POST /verify → build-only verify for MVP.
- GET /tasks/next → task selection.
- WS /ws/devteam → real-time streaming.

### 5.2 DevTeam Automation API (Profile B)
- POST /api/devteam/automation/initialize
  - Headers: Idempotency-Key (optional, TTL 6h)
  - Body: { projectId, userId, stopPoint? }
  - 202 Accepted: { executionId, eventId }
  - 409 Conflict (idempotent replay): Location: /api/devteam/automation/status/{projectId}

- GET /api/devteam/automation/status/{projectId}
  - 200 OK: { status, progress, currentTask, totals:{completed,total}, executionId, branch?, startedAt?, updatedAt? }

- POST /api/devteam/automation/pause/{projectId}
  - Allowed from: running → paused
  - 409 if invalid transition

- POST /api/devteam/automation/resume/{projectId}
  - Allowed from: paused → running
  - 409 if invalid transition

- POST /api/devteam/automation/stop/{projectId}
  - Allowed from: running → stopping → stopped
  - 409 if invalid transition

- POST /api/devteam/repository/validate
  - Body: { repositoryUrl }
  - 200 OK: { valid, defaultBranch, hasTaskList }

- GET /api/devteam/repository/tasks/{projectId}
  - 200 OK: { tasks: [...] }

- PUT /api/devteam/repository/tasks/{projectId}/{taskId}
  - Headers: Idempotency-Key (optional)
  - Body: { status, ... }

- GET /api/devteam/errors/{executionId}/{errorId}
- POST /api/devteam/tasks/inject
- GET /api/devteam/executions/active/{userId}
- GET /api/devteam/executions/history/{userId}?limit=n

Idempotency (Profile B):
- Optional header; store key hash for 6h; if duplicate, 409 + Location.

## 6. WebSocket Communication (Profile C)
- Endpoint: /ws/devteam (single).
- Auth: Passthrough from API gateway only; no per-message auth.
- Routing: projectId-only.
- Envelope: { type, ts, projectId, payload }
- Types: execution-update, execution-log, error, completion.
- Flow control: No throttle; best-effort send; linear reconnect; no replay.
- Note: Since permissive, ensure payload size limits at gateway.

## 7. Container Orchestration (Profile C)
- Per-project long-lived container reused for tasks.
- Resources: 1 vCPU, 1 GiB RAM.
- Storage: single named Docker volume per project; TTL 7 days; daily cleanup.
- Secrets: env vars scoped per project; not written to volume.
- Network: open egress.
- Lifecycle: healthcheck command (git --version && node --version); restart=always.
- Concurrency: per-project=1; global=5; scheduler round-robin across projects.
- Implication: fastest bootstrap (p50), weaker isolation accepted for MVP.

## 8. Repository Initialization Workflow
Steps:
1) Check local repo cache; clone if missing; fetch if present.
2) Ensure task_lists.md exists; create from default template if missing.
3) Parse leniently; warn on missing fields; auto-fill defaults.
4) Start/reuse project container; verify health.
5) Return repository context (paths, branch).

Errors → actionable messages; do not over-engineer conflict resolution in MVP.

## 9. Task Execution State Machine
States: SELECT → PREP → IMPLEMENT → VERIFY → MERGE → PUSH → UPDATE_TASKLIST → DONE
Error paths: IMPLEMENT|VERIFY|MERGE|PUSH → ERROR_INJECT → INJECT_TASK → SELECT
Idempotent transitions; retry counters in task_context; correlationId per Event.
Stop-on-error semantics for MVP.

## 10. Execute Code Change Workflow (MVP)
- GatherContext: prepare container + clone repo.
- ConstructPrompt: deterministic prompt template (Phase 2: Ollama).
- CodeExecution: Aider-driven changes.
- Verify: build-only (npm ci; npm run build). Skip tests in MVP.
- On success: merge/push; update task_lists.md.
- On failure: inject single error-resolution task; optional human escalation after retries.

## 11. Verification Policy (Profile B)
- Build-only verification to keep MVP fast and simple.
- Scripts required: npm ci; npm run build.
- If scripts missing: mark verifySkipped with warning; proceed to next task (stop-on-error applies only to build failures).

## 12. task_lists.md Parsing (Profile B)
- Lenient parser accepts tasks with missing optional fields.
- Auto-defaults: priority=medium, status=pending, estimated_duration=unknown.
- Warnings emitted via execution-log frames.
- Update flow: upon DONE, write completion timestamp and summary; commit and push.

## 13. Persistence Model
- Event row stores original data and evolving task_context.
- Execution state projected from Event.task_context:
  { customerId?, projectId, status, progress, currentTask, branch, artifacts }
- DB write SLA: ≤1s after node completion.

## 14. Observability
- Structured logs: correlationId, projectId, executionId, taskId, node, status.
- Metrics: queue latency, container boot p50/p95, verification duration, success rate.
- Log routing: API → stdout; Worker → stdout; collected by Docker logging stack.

## 15. Security
- Inputs validated; outputs sanitized (redact tokens).
- Git/AI tokens via env; least privilege; never persisted.
- WS permissive profile relies on API gateway for authN/Z and payload limits.
- Idempotency optional; conflicts return 409.

## 16. Performance & SLAs
- /prep ≤2s; /implement ≤30s; /verify ≤60s.
- Container bootstrap: p50 ≤5s; p95 ≤10s; teardown ≤60s.
- WebSocket latency ≤500ms best-effort (no replay).
- Celery queue p95 time-to-start ≤5s; concurrency ≥4 workers recommended.

## 17. Deployment & Ops
- Docker Compose services: API, Worker, Redis, Postgres (Supabase stack).
- Compose files:
  - [docker-compose.yml](docker/docker-compose.yml)
  - [docker-compose.launchpad.yml](docker/docker-compose.launchpad.yml)
  - [docker-compose.supabase.yml](docker/docker-compose.supabase.yml)
- Apply Alembic migrations before run: alembic upgrade head.
- Verify services: use docker ps to confirm running.

## 18. Testing Strategy
- Unit: business logic and parsers (>80% coverage target).
- Integration: API endpoints and Celery task dispatch.
- E2E/Journey: autonomous task through VERIFY with mocked Git/Aider when needed.
- Run order: fundamentals → complex; avoid dependent tests before foundations.

## 19. Phase 2 Roadmap (Non-MVP)
- Expand GenAI workflow (Ollama prompt, GPT-5 Medium execution).
- WebSocket throttling + replay buffers; per-user routing.
- Strong idempotency required; concurrency scheduling enhancements.
- Advanced verification (tests, coverage, types).
- Improved isolation (per-task containers) if needed.

## 20. Open Decisions and Risks
- API gateway contract for WS auth passthrough and size limits.
- Default task_lists.md template content.
- Conflict handling on push under concurrent edits.
- Secret rotation policy.
- Monitoring dashboards and alerts.

## 21. References
- PRD Endpoints: [prd.md](ai_docs/context/core_docs/prd.md:293)
- Event-driven/DAG alignment: [Workflow.run()](app/core/workflow.py:105), [Workflow.__run()](app/core/workflow.py:119-135)
- Event persistence: [Event](app/database/event.py:13)
- Events API: [events_endpoint()](app/api/endpoint.py:43)
- Router include: [router.include_router](app/api/router.py:14)
- Celery worker: [process_incoming_event()](app/worker/tasks.py:19)
- Celery config: [celery_app](app/worker/config.py:39)

---
Document owner: DevTeam Runner Service
Version: 1.0.0-MVP