# DevTeam Runner Service - Architecture Design Consult Scratchpad

Timestamp: 2025-09-14T23:01:43Z

Inputs reviewed:
- [ai_docs/context/core_docs/project_charter.md](ai_docs/context/core_docs/project_charter.md)
- [ai_docs/context/core_docs/prd.md](ai_docs/context/core_docs/prd.md)
- [ai_docs/context/core_docs/devTeam_integration_patterns.md](ai_docs/context/core_docs/devTeam_integration_patterns.md)
- [ai_docs/context/core_docs/devTeam_autonomous_execution_workflows.md](ai_docs/context/core_docs/devTeam_autonomous_execution_workflows.md)

Highlighted significance (per user):
- Docker Container Orchestration
- WebSocket Communication Infrastructure
- API Extensions and Endpoints
- DevTeam Automation API

Workflows owned by this service:
- Repository Initialization Workflow
- Task Execution State Machine
- Execute Code Change Workflow (GenAI Launchpad)
- All other GenAI workflows (Phase 2+ readiness)

MVP constraints:
- Python/FastAPI, Docker, Celery+Redis, Supabase Postgres, Aider tool
- Stop-on-error semantics; Aider-only tool in Phase 1
- Real-time WS updates with ≤500ms latency
- Event-driven via POST /events → Celery → [app/core/workflow.py](app/core/workflow.py)

Non-functional targets (key):
- Prep ≤2s, Implement ≤30s, Verify ≤60s
- Container bootstrap p50 ≤5s / p95 ≤10s; teardown ≤60s
- 5+ concurrent customer executions

Open decisions/questions to confirm

Container Orchestration:
- Base image(s) per repo type (default Node:18-alpine for JS)? Need Python variants?
- Per-execution quotas: defaults 1 vCPU / 2GiB RAM (configurable)? Enforcement method?
- Workspace volumes: named Docker volumes vs bind-mount; retention TTL (≥24h) and cleanup cadence?
- Git credentials: secret injection (PAT) mechanism and scope (least-privilege)?
- Network egress policy: restrict to Git + AI endpoints? DNS/proxy considerations?
- Health checks + restart/backoff policy details for per-task containers

WebSocket Infrastructure:
- AuthN/Z source: JWT from frontend; project/user scoping model?
- Routing model: projectId + executionId multiplexed on single connection?
- Message contracts finalized: execution-update, execution-log, error, completion; schema versions?
- Backpressure/throttling thresholds and batching window for bursty logs

DevTeam Automation + Core Runner API:
- Idempotency-Key storage, TTL, and replay response semantics
- Status model for GET /automation/status/{projectId}: fields and progress calculation
- Pause/Resume/Stop allowed states; race handling and eventual consistency
- Task Injection guardrails: conflict resolution when concurrent edits to task_lists.md

Workflow specifics:
- Repo init: default task_lists.md template content and validation rules
- State machine: idempotent transitions, retry counters, correlation IDs
- Execute Code Change: verification steps for JS repos; test detection policy
- Error policy: when to inject error-resolution task vs escalate to human review

Multi-customer execution:
- Concurrency limits per account/user; fair scheduling policy
- Isolation of working directories; naming convention; disk quota + cleanup policy

Observability:
- Structured logging fields: correlationId, projectId, executionId, taskId, node
- Metrics: queue latency, container boot time (p50/p95), verification duration, success rates

Security:
- Secret management strategy for Git/AI tokens; rotation approach
- WS message size limits and schema enforcement

Next steps (after confirmations):
- Lock container manager design + limits
- Finalize WS message schemas + routing/auth
- Draft precise endpoint specs for Automation API + idempotency behaviors
- Map workflows to DAG engine nodes and persistence fields
Update 2025-09-14T23:06:17Z — Container Orchestration MVP decided

Decision: Profile C (bootstrap-optimized shared)
- Per-project long-lived container reused across tasks
- Quotas: 1 vCPU, 1 GiB RAM
- Storage: single named Docker volume per project; TTL 7d; daily cleanup job
- Secrets: env scoped per project; not persisted to volume
- Network: open egress
- Lifecycle: healthcheck + always restart; workflow-level backoff unchanged

Implications:
- Faster p50 boot; weaker isolation accepted; enforce per-project concurrency limits
- VerifyNode timeouts sized for shared container
- Document deviation from per-task isolation noted in [prd.md](ai_docs/context/core_docs/prd.md:141)

Next decisions to lock:
- WebSocket authN/Z and routing (projectId + executionId), message schemas, throttling
- DevTeam Automation API idempotency semantics and status model (see [api endpoints](ai_docs/context/core_docs/prd.md:293))
- task_lists.md validation rules and default template
Update 2025-09-14T23:23:27Z — Task list, Verify, Concurrency decided

Decision: Profile B (lenient + build-only + round-robin)
- task_lists.md: lenient parse; warn on missing fields; auto-fill defaults
- Verify: npm ci; npm run build only (skip tests)
- Concurrency: per-project=1, global=5, round-robin across projects

Implications:
- Minimal process overhead; faster verify path; acceptable for MVP stop-on-error
- Requires npm scripts; if missing, mark verify skipped with warning and continue to next task
- Queue fairness across projects; matches shared container choice