MVP READY
# SEWP Chatbot — Architecture Design (ADD)

This ADD reflects the current code and expands it to the required event-driven workflow model using the provided node patterns and mermaid diagrams.

## System overview and current code mapping
- Event ingress (API)
  - Endpoint: POST /events via [router = APIRouter()](app/api/router.py:12) and [router.include_router()](app/api/router.py:14)
  - Handler: [endpoint.handle_event()](app/api/endpoint.py:39) persists to [database.event.Event](app/database/event.py:21), then enqueues [tasks.process_incoming_event()](app/worker/tasks.py:18)
- Asynchronous processing
  - Worker task loads Event by id, resolves workflow via [workflows.workflow_registry.WorkflowRegistry](app/workflows/workflow_registry.py:6), executes [core.workflow.Workflow.run()](app/core/workflow.py:105)
  - Workflow orchestrator and schema: [core.workflow.Workflow](app/core/workflow.py:24), [core.schema.WorkflowSchema](app/core/schema.py:46), [core.schema.NodeConfig](app/core/schema.py:16), [core.validate.WorkflowValidator](app/core/validate.py:16)
- Node patterns available
  - Base Node: [core.nodes.base.Node](app/core/nodes/base.py:14)
  - Router: [core.nodes.router.BaseRouter](app/core/nodes/router.py:16), rule units [core.nodes.router.RouterNode](app/core/nodes/router.py:50)
  - Concurrent: [core.nodes.concurrent.ConcurrentNode](app/core/nodes/concurrent.py:9)
  - Agentic: [core.nodes.agent.AgentNode](app/core/nodes/agent.py:102)
- Placeholder scaffold (to replace with real workflows)
  - [workflows.placeholder_workflow.PlaceholderWorkflow](app/workflows/placeholder_workflow.py:7)
  - [workflows.placeholder_workflow_nodes.initial_node.InitialNode](app/workflows/placeholder_workflow_nodes/initial_node.py:5)

Note: The user-described “/webhook” concept maps to the existing /events endpoint today; an alias route can be added later.

## Data and storage
- Vector store: Supabase Postgres with pgvector under schema sewp_context (see docker compose and DB bootstrap)
- Event table: [database.event.Event](app/database/event.py:21) stores incoming event data and resulting task_context
- Logged Q/A: stored in Event.task_context initially; future normalized tables may be added

## Security
- M2M header: X-SEWP-Secret (see Project Charter)
- Perform constant-time compare in protected endpoints; never commit secrets; container-mounted .env

## Performance and targets
- Retrieval top_k=6; chunk size ≈ 800 tokens with 15% overlap
- /chat p95 ≤ 3s for corpus ≤ 1k docs
- Ingest 500 Markdown pages ≤ 10 minutes on a standard dev machine

---

# Workflows

All workflows are triggered by POST /events and processed asynchronously by Celery. Each workflow is defined as a DAG of nodes using [WorkflowSchema](app/core/schema.py:46) and executed by [Workflow.run()](app/core/workflow.py:105).

## Ingest Workflow

High-level steps
1) gate (basic) — protects against injection/malformed params
2) type router — decides init, rebase (full reset), or reindex (changes only)
3) compiler (base) — compiles list of document paths under ai_docs/context/, determines metadata plan (file path, heading chain, commit sha, start/end offsets; optionally page or paragraph numbers if parser provides)
4) processor (base) — runs Docling to extract text with headings; retains fenced/indented code blocks as plain text
5) save (base) — chunks, embeds, and upserts into sewp_context.pgvector with required metadata; idempotent reindex

Mermaid
```mermaid
flowchart TD
  G[gate (basic)] --> R{type router}
  R -- init --> C1[compiler (base)]
  R -- rebase --> C2[compiler (base)]
  R -- reindex --> C3[compiler (base)]
  C1 --> P[processor (base)]
  C2 --> P
  C3 --> P
  P --> S[save (base)]
```

Node type mapping
- gate: Base Node → subclass [core.nodes.base.Node](app/core/nodes/base.py:14)
- type router: Router → subclass [core.nodes.router.BaseRouter](app/core/nodes/router.py:16) with route rules via [core.nodes.router.RouterNode](app/core/nodes/router.py:50)
- compiler: Base Node
- processor: Base Node (uses Docling library)
- save: Base Node (chunks, embeds, upserts pgvector)

Implementation plan (modules to add)
- app/workflows/ingest_workflow.py with WorkflowSchema start=GateNode
- app/workflows/ingest_nodes/
  - gate.py, type_router.py, compiler.py, processor.py, save.py (all subclasses of Node except type_router which subclasses BaseRouter)
- app/schemas/ingest_event.py (pydantic event model)

Event payload (representative)
```json
{
  "type": "INGEST",
  "mode": "reindex", 
  "paths": ["ai_docs/context/"],
  "commit_sha": "abc123"
}
```

## Answer Workflow

High-level steps
1) gate (basic) — sanitize inputs; enforce M2M header
2) prepare (agentic) — derive keyword phrases and retrieval params (e.g., top_k=6)
3) search (concurrent) — executes:
   - keyword search (base) — Postgres phrase/ILIKE search over stored plain text, scoped by file/heading
   - semantic search (base) — pgvector similarity search returning top_k chunks and passage payloads (path, heading_chain, commit_sha, start/end, passage_text)
4) synthesis (agentic) — compose answer with inline citations referencing retrieved passages
5) verify (workflow) — sub-workflow ensuring every assertion has at least one citation; loops until citations are complete or flags as insufficient/suspect

Mermaid
```mermaid
flowchart TD
  GA[gate (basic)] --> PR[prepare (agentic)]
  PR --> SC{search (concurrent)}
  SC --> KW[keyword search (base)]
  SC --> SEM[semantic search (base)]
  KW --> SY[synthesis (agentic)]
  SEM --> SY
  SY --> V[verify (workflow)]
```

Verify sub-workflow
- extract assertions (agentic)
- citation (agentic) — map assertions to citations with explicit deduction/induction annotation
- gate (agentic) — if any assertion lacks citation, loop back to citation; else finalize

Mermaid
```mermaid
flowchart TD
  E[extract assertions (agentic)] --> C[citation (agentic)]
  C --> G{gate (agentic)}
  G -- all cited --> OK[complete]
  G -- missing --> C
```

Node type mapping
- gate: Base Node
- prepare: Agentic → subclass [core.nodes.agent.AgentNode](app/core/nodes/agent.py:102)
- search: Concurrent → subclass [core.nodes.concurrent.ConcurrentNode](app/core/nodes/concurrent.py:9)
- keyword search: Base Node
- semantic search: Base Node
- synthesis: Agentic → subclass [core.nodes.agent.AgentNode](app/core/nodes/agent.py:102)
- verify: Workflow (composite) — implemented either as nested Workflow execution or as a sequence of AgentNode/Base nodes within the same workflow section

Implementation plan (modules to add)
- app/workflows/answer_workflow.py with WorkflowSchema start=GateNode
- app/workflows/answer_nodes/
  - gate.py, prepare.py(AgentNode), search.py(ConcurrentNode), keyword_search.py, semantic_search.py, synthesis.py(AgentNode)
- app/workflows/verify_nodes/
  - extract_assertions.py(AgentNode), citation.py(AgentNode), gate.py(AgentNode or Base with explicit checks)
- app/schemas/answer_event.py (pydantic event model)

Event payload (representative)
```json
{
  "type": "ANSWER",
  "question": "How will SEWP handle ingestion?",
  "top_k": 6
}
```

## Interfaces and contracts

Ingress
- POST /events
  - Accepts JSON validated to the workflow’s event schema (pydantic)
  - Stores Event via [endpoint.handle_event()](app/api/endpoint.py:39)
  - Enqueues Celery task [tasks.process_incoming_event()](app/worker/tasks.py:18)

Execution
- Worker resolves workflow via [WorkflowRegistry](app/workflows/workflow_registry.py:6)
- Runs [Workflow.run()](app/core/workflow.py:105), which:
  - Validates event against schema
  - Iterates nodes; handles routers via [BaseRouter.route()](app/core/nodes/router.py:31)
  - Supports concurrent nodes via [ConcurrentNode.execute_nodes_concurrently()](app/core/nodes/concurrent.py:20)

Outputs
- task_context: [core.task.TaskContext](app/core/task.py:11) with:
  - event (parsed), nodes[results by node], metadata, should_stop
  - For Answer workflow, assertions and citations recorded in nodes/Synthesis + Verify phases
- Event.task_context updated and persisted by worker

## Data persistence details

Vector store rows (per chunk)
- path, content_type (md/txt/pdf), heading_chain, commit_sha, start_offset, end_offset, text, embedding vector, model name, created_at

Q/A record (initially inside Event.task_context)
- question, answer_text, assertions[], citations[] {path, heading_chain, commit_sha, start, end, passage}, thumbs_up, insufficient, created_at

## Deployment
- Local/dev with Docker compose; API + Celery worker + Supabase. Files include docker-compose, Dockerfiles, and Supabase bootstrap in repo.
- Health: GET /health (to be added to API router)

## Future extensions
- Add /webhook as an alias to /events (or a specific dispatcher) for GitHub App push events
- Incremental reindex logic keyed by commit diff
- Normalize Q/A into dedicated tables for analytics

