MVP READY
# SEWP Chatbot — Project Charter

## Executive summary
- Vision: Chatbot answering from GitHub repo docs via Retrieval-Augmented Generation (RAG) with automatic reindexing when docs change.
- Primary value: Evidence-backed, up-to-date answers to planning questions (“How will SEWP …?”, “Have we thought about …?”) for SEWP staff and leadership.
- Repo: Nuosis/SEWP (GitHub). Access via token/secret in environment.
- MVP: 1‑day build focused on single‑pass CLI ingest and a /chat endpoint with citations; logging kept minimal; evaluation node stubbed.

## Objectives and success criteria
- Objectives
  - Provide authoritative answers grounded in the SEWP documentation.
  - Enable quick pilot usage by staff/leadership with minimal setup.
- KPIs
  - Usefulness ≥ 90% (track thumbs up/down and “insufficient” rate per answer).
  - Accuracy ≥ 95% based on citation coverage at the assertion level.
- Instrumentation
  - Track per-answer thumbs up/down and “insufficient” label.
  - Final workflow node evaluates each assertion: assertions must cite a retrieved passage; uncited assertions are counted inaccurate; valid deduction/induction annotated, otherwise flagged “suspect”.

## Stakeholders
- Stakeholder roles provided: Developer, Owner, MCA, COO, Admin, Sales, Practitioner.
- Responsibility mapping: intentionally deferred for MVP; will capture as RACI in a later iteration.

## Users and high‑level use cases
- Primary users: SEWP staff and leadership.
- Core use cases:
  - Ask planning/architecture/process questions and receive evidence-backed answers with inline citations.
  - Mark answers as “insufficient” when the corpus does not support an answer.
  - View minimal logs of questions/answers for review (future admin view).

## Scope
- In scope (Day 1 MVP):
  - Ingest documents under [ai_docs/context/](ai_docs/context/).
  - Allowed file types: .md, .txt, .pdf. Exclude code files.
  - /chat endpoint with top_k retrieval and inline citations.
  - Minimal logging and evaluation node stub that records required citations without strict scoring.
- Out of scope (Day 1):
  - GitHub webhook automation (planned for subsequent iteration).
  - Full accuracy scoring, admin UI, and complex dashboards.

## Architecture overview
- Foundation: GenAI Launchpad workflow architecture; see [ai_docs/context/guides/genai_launchpad_workflow_architecture.md](ai_docs/context/guides/genai_launchpad_workflow_architecture.md).
- Major components:
  - API service: [app/api/router.py](app/api/router.py).
  - Worker and tasks: [app/worker/tasks.py](app/worker/tasks.py).
  - Workflow engine and schema: [app/core/workflow.py](app/core/workflow.py), [app/core/schema.py](app/core/schema.py).
  - Node base/agent patterns: [app/core/nodes/base.py](app/core/nodes/base.py), [app/core/nodes/agent.py](app/core/nodes/agent.py).
- Execution model:
  - Day 1: CLI ingest writes embeddings to pgvector; /chat performs retrieval and answer composition with inline citations.
  - Later: Event-driven ingestion via GitHub App webhook to /webhook, enqueueing reindex tasks to the worker.

## Data ingestion and parsing (Docling)
- Library: Docling (pip package: “docling”) for .md/.txt/.pdf.
- Behavior:
  - Preserve headings as metadata; include basic images/tables (as available).
  - Keep fenced/indented code blocks as plain text within chunks.
  - Exclude source code files from ingestion.
- CLI ingest: Single-pass ingest over [ai_docs/context/](ai_docs/context/) with idempotent upsert semantics.

## Embeddings and vector store
- Vector store: Supabase Postgres with pgvector, schema: sewp_context.
- Embeddings: OpenAI text-embedding-3-small.
- Chunking: 800-token chunks with 15% overlap.
- Stored metadata per chunk: file path, heading chain, commit SHA, passage start/end offsets, content type (md/txt/pdf).

## Retrieval and answer generation
- Default retrieval: top_k = 6.
- Inline citations enabled with payload: file path, heading chain, commit SHA, start/end offsets; passage_size ≈ 1200 chars.
- Answer composer requirements:
  - Each assertion should reference at least one citation from retrieved passages.
  - Deductions/inductions must be explicitly annotated; otherwise assertions are marked “suspect”.

## Interfaces and endpoints
- Day 1 MVP:
  - CLI: one-shot ingest for [ai_docs/context/](ai_docs/context/).
  - HTTP: /chat, /health.
- Future endpoints (post-MVP):
  - /webhook for GitHub App push events (default branch) to drive incremental reindex.
  - /feedback or equivalent to capture thumbs up/down and insufficient labels.
- Auth (M2M):
  - Header: X-SEWP-Secret; env var: SEWP_M2M_SECRET; constant-time comparison; 401 on mismatch.

## Data governance and compliance
- Classification: Internal-only; no sensitive PII expected.
- Repo access scope: Read-only to documentation paths (TBD exact path constraints beyond [ai_docs/context/](ai_docs/context/)).
- Retention: TBD for logs/Q&A and embeddings (proposed: logs/Q&A 90 days; embeddings indefinite).
- Encryption: TLS in transit; Supabase encryption at rest assumed.

## Timeline and milestones
- 1‑day MVP deliverables:
  - Ingestion CLI processes [ai_docs/context/](ai_docs/context/) into sewp_context.pgvector with Docling parsing.
  - /chat returns answers with inline citations and retrieved passage payloads; top_k=6.
  - Minimal logging of questions/answers plus “insufficient” flag; evaluation node stub records citation requirements.
  - Health check endpoint available; env-based M2M protection applied where required.
- Acceptance tests:
  - Ask three representative planning questions; answers include at least one inline citation per assertion and link back to the correct passage.
  - “Insufficient” flow marks the record and is visible in logs.
  - Ingest is repeatable without duplicating vectors (upsert semantics).

## Risks and mitigations
- PDF parsing variability (Docling): mitigate by focusing on Markdown/TXT first; fall back to simplified text extraction if needed.
- Citation precision: ensure chunk-level offsets and heading chains are stored; consider smaller overlap tuning if hallucinations rise.
- Embedding vendor dependency/cost: start with text-embedding-3-small; leave model configurable via env.
- Compressed timeline: constrain scope (no webhook Day 1) and use existing GenAI Launchpad patterns to accelerate.
- Security of secrets: use container-mounted .env; never commit secrets; apply constant-time compare for M2M header.

## Open TBDs
- Exact repo access scope beyond [ai_docs/context/](ai_docs/context/).
- Retention windows for logs/Q&A and embeddings.
- Responsibility mapping for stakeholders (RACI).
- Competitive landscape and differentiation summary.
- Detailed deployment profile reference (noted as “already in code base”).

## Next steps
- Finalize retention windows and repo scope constraints; update configs.
- Implement CLI ingest command and DB migrations for sewp_context schema and pgvector tables.
- Implement /chat endpoint response format with inline citations and assertion structure.
- Wire minimal logging and evaluation stub; expose /health.
- Prepare follow-on iteration to add GitHub App webhook and incremental reindex.