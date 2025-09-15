# DevTeam Runner Service — Work Breakdown Structure (MVP)

Status: Approved. Pure phase-based (fundamentals → complex). Capacity: 10h/week. Env: local-dev only. Scope: Adopt ADD MVP exactly; include Pause/Resume/Stop in Phase 5.

Constraints:
- Python/FastAPI; Docker Compose; Celery+Redis; Supabase Postgres
- Build-only verification; stop-on-error; optional idempotency (Profile B)
- No task_lists.md to be created now; WBS only

Complexity legend: L=Low, M=Medium, H=High

Phases (sequential)

1) Foundations & Ops Validation (L)
Objectives:
- Bring up Compose stack; apply Alembic; verify /health
Deliverables:
- docker ps shows services; Alembic applied; GET /health OK
Key anchors:
- [docker-compose.yml](docker/docker-compose.yml)
- [env.py](app/alembic/env.py)
- [alembic.ini](app/alembic.ini)
- [health.py](app/api/v1/endpoints/health.py)
Tasks:
- Compose up/down scripts verified
- Run alembic upgrade head
- Validate dependency tools available in containers (git, node, aider)

2) Events → Worker Wire-up (M)
Objectives:
- Ingest events, persist, enqueue Celery; worker consumes
Deliverables:
- POST /events returns 202; Event row stored; Celery task executed
Key anchors:
- [router.include_router](app/api/router.py:14)
- [events_endpoint()](app/api/endpoint.py:43)
- [celery_app.send_task](app/api/endpoint.py:72)
- [process_incoming_event()](app/worker/tasks.py:19)
- [celery_app](app/worker/config.py:39)
- [Event](app/database/repository.py)
Tasks:
- Mount events router; validate request schema; persist Event
- Dispatch Celery task with correlationId
- Confirm worker consumes and logs structured event

3) Workflow Engine Integration (M)
Objectives:
- Execute minimal DEVTEAM_AUTOMATION DAG; persist task_context
Deliverables:
- Workflow.run executes; task_context written
Key anchors:
- [Workflow.run()](app/core/workflow.py:105)
- [Workflow.__run()](app/core/workflow.py:119)
- [workflow_registry.py](app/workflows/workflow_registry.py)
Tasks:
- Register DEVTEAM_AUTOMATION workflow
- Implement minimal nodes to prove SELECT→PREP skeleton

4) Repository Initialization Workflow (M)
Objectives:
- Repo cache/clone/fetch; create defaults only where allowed; start/reuse per-project container; health check
Deliverables:
- Repository context (paths, branch); container healthy
References:
- [add.md](ai_docs/context/core_docs/add.md)
Tasks:
- Implement repo cache and clone; fetch if present
- Ensure default template is only referenced (no task_lists.md creation now)
- Start/reuse per-project container; run healthcheck (git --version && node --version)

5) DevTeam Automation API (Profile B) (M)
Objectives:
- Initialize/status plus Pause/Resume/Stop endpoints
Deliverables:
- 202 Accepted for initialize with {executionId,eventId}; status projection JSON; transitions enforced (running↔paused; stop only from running)
References:
- [prd.md](ai_docs/context/core_docs/prd.md:293)
- [add.md](ai_docs/context/core_docs/add.md:55)
Key anchors:
- [events_endpoint()](app/api/endpoint.py:43)
Tasks:
- POST /api/devteam/automation/initialize
- GET /api/devteam/automation/status/{projectId}
- POST /api/devteam/automation/pause/{projectId}
- POST /api/devteam/automation/resume/{projectId}
- POST /api/devteam/automation/stop/{projectId}
- Optional Idempotency-Key support (TTL 6h)

6) WebSocket /ws/devteam (Profile C) (M)
Objectives:
- Real-time execution-update/log frames; projectId-only routing; permissive profile
Deliverables:
- Demo client receives frames; reconnect works; no replay
References:
- [add.md](ai_docs/context/core_docs/add.md:96)
Tasks:
- Implement WS endpoint /ws/devteam
- Envelope {type, ts, projectId, payload}
- Linear reconnect; payload size limits at gateway (not in service)

7) Execute Code Change + Verify (combined) (H)
Objectives:
- Deterministic prompt; Aider-driven changes; build-only verify (npm ci; npm run build)
Deliverables:
- Changes applied; build passes or failure path recorded with artifacts
References:
- [add.md](ai_docs/context/core_docs/add.md:131)
Tasks:
- Generate prompt; run Aider; capture diff/stdout/artifacts
- Run build-only verify; retries ≤2; stop-on-error on build failures
- On success: merge/push; update status projection

8) Persistence & Observability Polish (M)
Objectives:
- Structured logs; minimal metrics; status consistency; DB write SLA notes
Deliverables:
- Logs include correlationId, projectId, executionId; basic metrics recorded
References:
- [add.md](ai_docs/context/core_docs/add.md:150)
- [add.md](ai_docs/context/core_docs/add.md:156)
Tasks:
- Ensure task_context schema stable; status projection matches API
- Add structured logging fields across API and Worker
- Record queue latency and verification duration (minimal)

9) Local Scripts for Build/Run (L)
Objectives:
- One-command local bootstrap; local CI steps
Deliverables:
- Scripts for build, test, alembic upgrade, compose up/down
Key anchors:
- [start.sh](docker/start.sh)
- [Dockerfile.api](docker/Dockerfile.api)
- [docker-compose.yml](docker/docker-compose.yml)
Tasks:
- Create/validate shell targets for build/test/migrate/run
- Document rollback procedure

Dependencies and sequencing
- 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9

User stories and acceptance criteria

Story A: Initialize Automation
As a developer, I can start autonomous execution for a project so that tasks run without manual steps.
Acceptance:
- Given valid payload, When POST /api/devteam/automation/initialize, Then 202 with {executionId,eventId}
- And Event persisted; And Celery task enqueued and consumed

Story B: Pause/Resume/Stop
As a developer, I can pause/resume/stop an execution to control automation safely.
Acceptance:
- Given status running, When POST /api/devteam/automation/pause/{projectId}, Then status=paused
- Given paused, When POST /api/devteam/automation/resume/{projectId}, Then status=running
- Given running, When POST /api/devteam/automation/stop/{projectId}, Then status=stopped
- Invalid transitions return 409

Story C: Real-time updates
As a developer, I see progress and logs in real-time.
Acceptance:
- When connected to /ws/devteam, Then receive execution-update/log frames within ≤500ms best-effort

Story D: Execute Code Change + Verify
As a developer, I can apply code changes and verify build success.
Acceptance:
- When Aider completes, Then artifacts (diff, stdout, filesModified) saved
- And build-only verify runs (npm ci; npm run build); failures stop pipeline

Testing strategy
- Unit (≥80%): parsers, workflow nodes, automation state transitions
- Integration: POST /events → Celery → Workflow.run path; API endpoints
- E2E/Journey: Initialize → Execute+Verify through WS updates (mock Git/Aider as needed)
- Run order: fundamentals → complex; avoid dependent tests before foundations

CI/CD approach (local scripts only)
- Build: docker compose build; type/lint if configured
- Test: run unit/integration suites
- Migrate: alembic upgrade head
- Run: docker compose up -d api worker redis db
- Stop: docker compose down -v (when needed)
- Anchors: [start.sh](docker/start.sh), [docker-compose.yml](docker/docker-compose.yml), [alembic.ini](app/alembic.ini)

Quality gates
- Lint/type clean; tests ≥80% unit coverage on core logic
- No secrets in logs; redact tokens
- Build-only verify mandatory for Execute phase completion

Risks and mitigations
- Git/Aider instability → retries + clear error artifacts; manual fallback
- WebSocket instability → linear reconnect; gateway limits
- Merge/push conflicts → stop-on-error; document manual resolution path

Progress tracking
- Status endpoint returns projection; WS frames for live updates
- Manual checklist per phase; evidence links in commits

Change log
- 2025-09-14: Initial WBS created (phases approved; Verify merged into Execute)