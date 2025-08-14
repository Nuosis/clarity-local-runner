MVP READY
# SEWP Chatbot — Product Requirements Document (PRD)

## Personas (<=3)
- SEWP Staff (Practitioner): Needs quick, evidence-backed answers to planning/process questions drawn from the SEWP repo corpus.
- SEWP Leadership: Needs concise, cited summaries to support decisions with clear provenance.
- Developer/Admin: Operates ingestion and monitors logs; maintains workflow health; triages “insufficient” feedback.

## Primary workflows (GenAI Launchpad model)
1) Ingest Workflow (event-triggered)
2) Answer Workflow (event-triggered; includes “insufficient” feedback as a step within this workflow)

Notes
- Workflows are triggered via the event endpoint in the API, stored in the events table, and processed asynchronously by Celery workers with the workflow registry.
- Current endpoint path in code is /events via [router = APIRouter()](app/api/router.py:12) and [router.include_router()](app/api/router.py:14); the handler is [endpoint.handle_event()](app/api/endpoint.py:39). The Celery task is [tasks.process_incoming_event()](app/worker/tasks.py:18). Events are stored using model [database.event.Event](app/database/event.py:21) and workflows are resolved via [workflows.workflow_registry.WorkflowRegistry](app/workflows/workflow_registry.py:6).

## Functional requirements by workflow (MoSCoW)

- Workflow 1: Ingest (event-triggered)
  - Must: Accept an ingest event via POST /events (current) with a type indicating init, rebase (full reset), or reindex (changed files only).
  - Must: Gate (basic guardrail) — protect against prompt/AI injection or malformed parameters.
  - Must: Router (Type) — determine ingest mode: init, rebase, or reindex based on event payload.
  - Must: Compiler (Base) — compile list of document paths under ai_docs/context/ with inclusion rules (.md, .txt, .pdf) and exclusions (code files); retain metadata plan to orient location in documents (e.g., source path, headings, byte offsets; optionally page/paragraph if available from parser).
  - Must: Processor (Base) — run Docling over selected paths to extract plain text with headings preserved; keep fenced/indented code blocks as plain text inside chunks.
  - Must: Save (Base) — chunk (≈800 tokens, 15% overlap), embed (OpenAI text-embedding-3-small), and upsert to Supabase Postgres pgvector (schema sewp_context) with metadata: file path, heading chain, commit SHA, start/end offsets, content_type (md/txt/pdf).
  - Must: Idempotent upsert semantics; reindex processes only changed files.
  - Should: CLI mode may invoke same workflow locally with summary counts and durations.
  - Could: Dry-run option that lists files and forecasted chunks.

- Workflow 2: Answer (event-triggered)
  - Must: Gate (Basic) — sanitize input; enforce M2M auth via header X-SEWP-Secret, constant-time compare; reject on mismatch.
  - Must: Prepare (Agentic) — derive keyword phrases and retrieval parameters (e.g., top_k=6, section weighting) from the question/context.
  - Must: Search (Concurrent) — run:
    - Keyword Search (Base) — phrase/keyword search over stored plain text (Postgres), scoped by file path/heading chain.
    - Semantic Search (Base) — vector similarity search over pgvector (top_k=6 default), retrieve passage payloads with start/end offsets.
  - Must: Synthesis (Agentic) — compose answer using retrieved passages; attach inline citations with payload {path, heading_chain, commit_sha, start, end, passage_text}.
  - Must: Verify (Workflow) — perform verification sub-workflow to ensure every assertion is supported by at least one citation. Steps:
    - Extract Assertions (Agentic) — identify assertions of fact as an array.
    - Citation (Agentic) — supply at least one citation per assertion from retrieved results; annotate valid deduction/induction explicitly; otherwise mark “suspect”.
    - Gate (Agentic) — ensure all assertions have citations; if missing, loop back to Citation for unresolved assertions.
  - Must: Log Q/A record including thumbs_up, insufficient flag, assertions, and citations.
  - Should: Allow top_k override in request payload within safe bounds.
  - Could: Emit triage event upon “insufficient” to queue follow-up actions.

## Non-functional requirements (targets)
- Accuracy: ≥95% assertions contain at least one valid citation; uncited assertions counted as inaccurate by the verify sub-workflow.
- Usefulness: ≥90% thumbs-up or non-insufficient rate.
- Latency: Answer workflow p95 ≤ 3s on corpus ≤ 1k docs and top_k=6.
- Ingestion throughput: 500 Markdown pages ≤ 10 minutes on a standard dev machine.
- Availability: API uptime ≥ 99.5% during pilot.
- Security: M2M header X-SEWP-Secret, constant-time compare; no secrets in VCS; TLS in transit; Supabase encryption at rest assumed.
- Compliance: Internal-only data; no sensitive PII expected.

## Core data objects (<=5) with key attributes
- Event: id, workflow_type, data(json), created_at, updated_at
- Document: id, path, content_type, commit_sha, heading_chain[]
- PassageChunk: id, document_id, start_offset, end_offset, heading_chain, text
- EmbeddingVector: id, chunk_id, vector, model, created_at
- QARecord: id, question, answer_text, assertions[], citations[], thumbs_up:boolean, insufficient:boolean, created_at

## Interface contracts (representative)
- POST /events → Accept event (202). Current implementation: [endpoint.handle_event()](app/api/endpoint.py:39)
  - Accepts JSON conforming to the workflow’s event schema; persists Event; enqueues Celery job [tasks.process_incoming_event()](app/worker/tasks.py:18).
- Workflow execution:
  - Worker loads Event by id, resolves workflow via [WorkflowRegistry](app/workflows/workflow_registry.py:6), and executes [Workflow.run()](app/core/workflow.py:105) which validates against event_schema and orchestrates nodes.

## Acceptance criteria

- Ingest Workflow
  - Given a corpus under ai_docs/context/ with .md/.txt/.pdf and no code files,
  - And an ingest event of type init, rebase, or reindex is POSTed to /events,
  - When the workflow runs, Then files are parsed with Docling, chunked (≈800 tokens, 15% overlap), embedded (text-embedding-3-small),
    and upserted into sewp_context.pgvector with metadata {path, heading_chain, commit_sha, start, end, content_type} and no duplicate vectors on re-run.

- Answer Workflow (includes “insufficient” within the same workflow)
  - Given embeddings exist and the service is healthy,
  - When an answer event is POSTed to /events with a question and optional top_k,
  - Then Prepare derives keyword phrases and retrieval params,
  - And Search concurrently executes keyword (Postgres) and semantic (pgvector) retrieval,
  - And Synthesis composes an answer with inline citations including {path, heading_chain, commit_sha, start, end, passage_text},
  - And Verify ensures every assertion has ≥1 citation; uncited assertions are marked inaccurate and the answer is flagged accordingly,
  - And the stored QARecord includes thumbs_up/down and an “insufficient” flag that can be set post-response, within the Answer workflow’s logging step.

## Implementation notes and mapping to code
- Event ingestion: [endpoint.handle_event()](app/api/endpoint.py:39) persists Event and enqueues Celery job; storage model: [database.event.Event](app/database/event.py:21).
- Worker: [tasks.process_incoming_event()](app/worker/tasks.py:18) resolves workflow via [WorkflowRegistry](app/workflows/workflow_registry.py:6) and executes via [core.workflow.Workflow](app/core/workflow.py:24).
- Node patterns available:
  - Base Node: [core.nodes.base.Node](app/core/nodes/base.py:14)
  - Router: [core.nodes.router.BaseRouter](app/core/nodes/router.py:16) with [RouterNode](app/core/nodes/router.py:50)
  - Concurrent: [core.nodes.concurrent.ConcurrentNode](app/core/nodes/concurrent.py:9)
  - Agentic: [core.nodes.agent.AgentNode](app/core/nodes/agent.py:102)
- Placeholder workflow exists: [workflows.placeholder_workflow.PlaceholderWorkflow](app/workflows/placeholder_workflow.py:7) with start node [initial_node.InitialNode](app/workflows/placeholder_workflow_nodes/initial_node.py:5).

## Out-of-scope (MVP)
- Full admin UI and dashboards.
- Automated GitHub webhook configuration (may be added as alias to /events later).
- Advanced scoring beyond assertion/citation coverage.