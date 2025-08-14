MVP READY
# SEWP Chatbot — Work Breakdown Structure (WBS)

## MVP scope checklist
- Event-driven workflows via POST /events; events persisted and processed by Celery
- Ingest workflow: Docling parse .md/.txt/.pdf; chunk+embed; upsert to pgvector with metadata
- Answer workflow: keyword+semantic retrieval; synthesis with inline citations; verify assertions have citations
- Minimal logging of Q/A with thumbs_up and insufficient flag
- M2M secret header (X-SEWP-Secret) enforced on protected endpoints
- Health endpoint available

## Task groups by component/service
- API and Endpoint
  - Define/confirm POST /events in [api/router.py](app/api/router.py:12) and [api/endpoint.handle_event()](app/api/endpoint.py:39)
  - Add /health with simple OK
  - Add constant-time check for X-SEWP-Secret
- Database and Migrations
  - Event table migration in SQLAlchemy/Alembic matches [database.event.Event](app/database/event.py:21)
  - Create sewp_context schema and pgvector tables for chunks and embeddings
- Worker and Registry
  - Ensure Celery config/tasks wired; see [worker.tasks.process_incoming_event()](app/worker/tasks.py:18)
  - Extend [workflows.workflow_registry.WorkflowRegistry](app/workflows/workflow_registry.py:6) with INGEST and ANSWER workflows
- Ingest Workflow
  - Implement nodes: gate, type_router, compiler, processor, save
  - Wire [core.schema.WorkflowSchema](app/core/schema.py:46) and [core.workflow.Workflow](app/core/workflow.py:24)
- Answer Workflow
  - Implement nodes: gate, prepare, search(concurrent), keyword_search, semantic_search, synthesis
  - Implement verify sub-workflow: extract_assertions, citation, gate
- Retrieval and Storage
  - Implement pgvector similarity search and Postgres keyword search
  - Define metadata and persistence contract
- Security and Ops
  - Secrets via .env; docker-compose for local dev; logging baseline

## Dependencies and sequencing
1) DB migrations (events table, sewp_context schema, pgvector) → 2) API /events + worker wiring → 3) Ingest workflow nodes → 4) Docling integration → 5) Answer workflow nodes → 6) Verify sub-workflow → 7) Health + security hardening → 8) Acceptance tests

## Estimates and owners
- DB migrations and Supabase pgvector bootstrap — S (0.5d) — Owner: Developer
- API /events + Celery wiring — S (0.5d) — Owner: Developer
- Ingest nodes (gate/router/compiler/processor/save) — M (1d) — Owner: Developer
- Docling integration and chunk/embed/upsert — M (1d) — Owner: Developer
- Answer nodes (gate/prepare/search/keyword/semantic/synthesis) — M (1.5d) — Owner: Developer
- Verify sub-workflow (extract/citation/gate) — M (1d) — Owner: Developer
- Security (X-SEWP-Secret), Health endpoint, logging — S (0.5d) — Owner: Developer
- Acceptance tests and PRD conformance checks — S (0.5d) — Owner: Developer
Note: Calendar time compressed via parallelization where feasible.

## Sprint 1 plan (1 week) with Definition of Done
- Day 1–2: DB migrations, API /events, Celery wiring; DoD: POST /events stores Event and enqueues task; health endpoint returns 200
- Day 3: Ingest workflow nodes + Docling; DoD: ingest event “init” processes ai_docs/context/ with upsert to pgvector (idempotent)
- Day 4–5: Answer workflow nodes; DoD: answer event returns assertions with inline citations; verify loop enforces ≥1 citation per assertion
- Day 6–7: Hardening (security, logging), acceptance tests; DoD: KPIs and NFRs measurable, logs capture insufficient flags, PRD acceptance criteria pass

## Test strategy + CI/CD
- Unit tests: node-level tests for compiler, keyword_search, semantic_search, verify gate
- Integration tests: end-to-end ingest over sample corpus; /events happy path through worker to stored task_context
- E2E tests: question→answer with citations; insufficient labeling path
- CI: run tests and linters on PR; container build; optional docker compose up check
- Observability: log per-answer verdicts and missing-citation flags