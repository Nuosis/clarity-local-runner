
# WBS Consultation Scratchpad — DevTeam Runner Service

- Reviewed core docs: project_charter, prd, add (MVP-ready baseline)
- MVP profiles: Containers=C; WebSocket=C; Automation API=B; Verify/TaskList/Concurrency=B
- Architecture: FastAPI API, Celery worker, Workflow engine, per-project container, WS streaming, Supabase Postgres, Redis
- Key anchors: router.include_router, events_endpoint(), celery_app.send_task, process_incoming_event(), Workflow.run(), Workflow.__run(), Event, env.py, celery_app
- Data flow: POST /events → persist Event → enqueue Celery → Workflow runs → WS emits updates → status via GET
- APIs: Core Runner + DevTeam Automation (initialize/status/pause/resume/stop, repo validate, tasks read/update, errors, inject, executions)
- Non-functional targets: /prep ≤2s; /implement ≤30s; /verify ≤60s; WS ≤500ms; Celery start p95 ≤5s; per-project concurrency=1; global=5
- Deployment: Docker Compose (api, worker, redis, postgres); apply Alembic; verify via docker ps
- Testing: Unit &gt;80% coverage; Integration; E2E/Journey; run fundamentals → complex
- Constraints: Python/FastAPI; Aider integration; build-only verify; stop-on-error; optional idempotency; env-scoped secrets
- Risks/open decisions: WS gateway contract, default task_lists.md template, push conflicts, secret rotation, monitoring

Planning scope for WBS phase:
- WBS + user stories + acceptance criteria
- Complexity-based estimates; dependencies &amp; sequencing
- Sprint plan; CI/CD approach; QA gates
- Risk mitigations; progress tracking plan

Next questions (to unblock planning):
- Developer capacity (hours/week) and sprint length?
- Target repositories to automate first (URLs) and tech stacks?
- CI provider and environments (dev/stage/prod)?
- Any must-have non-MVP items for first release?
- WebSocket gateway details (auth passthrough, size limits)?
- Default task_lists.md template expectations?
- Additional compliance/logging requirements?
- Cadence: Continuous Kanban; Capacity: 10h/week
- Preference: Phase-based WBS (fundamental → complex), sequential build
- Proposed Phases (draft):
  1) Foundations & Ops: Docker Compose sanity, Alembic run, health checks, logging/metrics, basic Kanban/WIP
  2) Repository Init Workflow: repo cache/clone/fetch, task_lists.md template + lenient parser, branch creation, container health
  3) DevTeam Automation API (MVP scope): initialize/status/pause/resume/stop, optional idempotency, status projection
  4) WebSocket /ws/devteam (permissive): routing by projectId, envelope, reconnect, no replay
  5) Execute Code Change (MVP): deterministic prompt, Aider integration, artifacts capture
  6) Verify (build-only): npm ci + build; skip tests; error handling + retries
  7) Persistence & Observability polish: task_context shaping, metrics, structured logs
  8) CI/CD & Delivery: pipeline, migrations gate, container build/push, deploy scripts
- MVP scope: Adopt ADD MVP exactly — Containers=C, WebSocket=C, Automation API=B (optional idempotency), Verify/TaskList/Concurrency=B (from [add.md](ai_docs/context/core_docs/add.md))
- Kanban removed — adopt pure phase-based sequential plan

Proposed Phases (sequential, fundamentals → complex):
1) Foundations & Ops Validation
   - Compose stack up; apply Alembic; verify health
   - Exit: docker ps shows services; /health OK; migrations applied
   - Anchors: [env.py](app/alembic/env.py:11), [docker-compose.yml](docker/docker-compose.yml), [health.py](app/api/v1/endpoints/health.py:1)
2) Event Ingestion & Worker Wire-up
   - Ensure Events API mount and handler persist Event; Celery dispatch
   - Exit: POST /events → 202; Celery receives task; Event row written
   - Anchors: [router.include_router](app/api/router.py:14), [events_endpoint()](app/api/endpoint.py:43), [process_incoming_event()](app/worker/tasks.py:19), [celery_app](app/worker/config.py:39), [Event](app/database/repository.py:1)
3) Workflow Engine Integration (DEVTEAM_AUTOMATION)
   - Register/run DEVTEAM_AUTOMATION via workflow engine; task_context projection
   - Exit: Workflow.run executes a simple DAG and persists task_context
   - Anchors: [Workflow.run()](app/core/workflow.py:105), [WorkflowRegistry](app/workflows/workflow_registry.py:1)
4) Repository Initialization Workflow
   - Repo cache/clone/fetch, create default task_lists.md if missing (lenient), start/reuse per-project container, health checks
   - Exit: repo ready, branch context returned, container healthy
   - Anchors: [ADD §8](ai_docs/context/core_docs/add.md:115)
5) DevTeam Automation API (MVP Profile B)
   - Endpoints: initialize, status (pause/resume/stop queued later if needed)
   - Exit: initialize returns executionId/eventId; status reflects task_context
   - Anchors: [PRD API](ai_docs/context/core_docs/prd.md:293)
6) WebSocket Service (Profile C)
   - WS /ws/devteam with projectId-only routing, envelope {type, ts, projectId, payload}
   - Exit: execution-update/log frames visible in client
   - Anchors: [ADD §6](ai_docs/context/core_docs/add.md:96)
7) Execute Code Change (MVP)
   - Deterministic prompt template; invoke Aider; capture artifacts/diff
   - Exit: modified files produced; artifacts persisted to task_context
   - Anchors: [ADD §10](ai_docs/context/core_docs/add.md:131)
8) Verify (Build-only, Profile B)
   - npm ci; npm run build; retries; skip tests; proceed on verifySkipped as spec
   - Exit: verification result persisted; stop-on-error enforced on failures
   - Anchors: [ADD §11](ai_docs/context/core_docs/add.md:139)
9) Persistence & Observability Polish
   - Status projection model, structured logs, minimal metrics
   - Exit: status endpoints consistent; logs include correlationId/projectId
   - Anchors: [ADD §13-14](ai_docs/context/core_docs/add.md:150)
10) CI/CD & Delivery
   - Pipeline: build, lint, tests, alembic upgrade, image push, deploy scripts
   - Exit: one-command deploy; rollback plan documented
   - Anchors: [docker/](docker/docker-compose.yml), [alembic.ini](app/alembic.ini)
- Phases approved; Verify merged into Execute Code Change (pure phase-based)
- Instruction: Do NOT create task_lists.md now — produce WBS in core_docs only

Phase-based WBS — Draft (fundamentals → complex; Verify merged into Execute)
1) Foundations & Ops Validation (L)
   - Bring up Compose stack [docker-compose.yml](docker/docker-compose.yml); verify services with docker ps
   - Apply Alembic migrations [env.py](app/alembic/env.py:11), [alembic.ini](app/alembic.ini)
   - Health endpoint returns OK [health.py](app/api/v1/endpoints/health.py:1)
   - Deliverables: runbook notes; proof logs; command snippets
   - Deps: none
2) Events → Worker Wire-up (M)
   - API mounts events router [router.include_router](app/api/router.py:14)
   - Persist Event; enqueue Celery [events_endpoint()](app/api/endpoint.py:43), [celery_app.send_task](app/api/endpoint.py:72)
   - Worker consumes task [process_incoming_event()](app/worker/tasks.py:19), Celery config [celery_app](app/worker/config.py:39)
   - Deliverables: POST /events → 202; Event row stored
   - Deps: phase 1
3) Workflow Engine Integration (M)
   - Execute minimal DEVTEAM_AUTOMATION DAG [Workflow.run()](app/core/workflow.py:105), parse schema [Workflow.__run()](app/core/workflow.py:119)
   - Persist task_context; project status projection shape
   - Deliverables: sample DAG execution recorded in DB
   - Deps: phase 2
4) Repository Initialization Workflow (M)
   - Repo cache/clone/fetch; create defaults only where spec allows (explicitly skip task_lists.md creation per instruction)
   - Start/reuse per-project container; healthcheck policy (Profile C) — ref ADD §8 [add.md](ai_docs/context/core_docs/add.md:115)
   - Deliverables: repository context (paths, branch); container healthy
   - Deps: phase 3
5) DevTeam Automation API (Profile B) (M)
   - Implement initialize/status (pause/resume/stop optional later) — PRD §API [prd.md](ai_docs/context/core_docs/prd.md:293)
   - Optional Idempotency-Key handling per Profile B
   - Deliverables: executionId/eventId on init; status projection JSON
   - Deps: phase 4
6) WebSocket /ws/devteam (Profile C) (M)
   - Endpoint /ws/devteam; route by projectId; envelope {type, ts, projectId, payload} — ADD §6 [add.md](ai_docs/context/core_docs/add.md:96)
   - Emit execution-update/log frames
   - Deliverables: demo client receives frames
   - Deps: phase 5
7) Execute Code Change + Verify (combined) (H)
   - Deterministic prompt template (MVP) → invoke Aider; capture artifacts/diff
   - Build-only verify: npm ci; npm run build; stop-on-error; retries — ADD §10–11 [add.md](ai_docs/context/core_docs/add.md:131)
   - Deliverables: code changes applied; build passes or error path logged
   - Deps: phases 4–6
8) Persistence & Observability Polish (M)
   - Structured logs (correlationId, projectId) — ADD §14 [add.md](ai_docs/context/core_docs/add.md:156)
   - Minimal metrics; status consistency checks; DB write SLA notes — ADD §13 [add.md](ai_docs/context/core_docs/add.md:150)
   - Deliverables: logging fields present; basic metrics recorded
   - Deps: 5–7
9) Local Scripts for Build/Run (CI/CD local) (L)
   - Local scripts: build, test, alembic upgrade, compose up/down [start.sh](docker/start.sh), [Dockerfile.api](docker/Dockerfile.api)
   - Deliverables: one-command local bootstrap; rollback notes
   - Deps: 1–8