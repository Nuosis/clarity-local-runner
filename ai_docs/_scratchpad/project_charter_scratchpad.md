
## SEWP Chatbot — Project Charter Scratchpad (2025-08-12)

- Vision: Chatbot answering from GitHub repo docs via RAG; reindex on doc changes via GitHub webhook. Repo: Nuosis/SEWP; .env token/secret.
- Users/use-cases: SEWP staff &amp; leadership; planning Qs (“How will SEWP…”, “Have we thought about …”); all Qs tracked; answers can be marked “insufficient”.
- Tech baseline: GenAI Launchpad; Supabase backend; Alembic migrations; Dockling for read/chunk/vectorize (to implement).
- KPIs (90d): usefulness ≥90%; accuracy ≥95% (measurement method TBD).
- Constraints: conform with GenAI; rapid MVP in 1–3 days.

Open decisions/assumptions:
- Corpus scope: included paths, exclusions; file types (md/mdx/pdf/code comments?).
- Vector store: Supabase Postgres + pgvector? schema naming/permissions.
- Embeddings: provider/model; chunk size/overlap; metadata (path, commit sha, headings).
- Webhook: GitHub App vs PAT; events (push, PR); secret management; incremental reindex.
- Interface: API-first vs minimal UI; auth (org-only); role permissions.
- Feedback loop: “insufficient” labeling UX; storage; triage (issue creation?).
- Accuracy measurement: gold Q/A set; sampling; acceptance thresholds.
- Deployment: envs (dev/prod), hosting target.
- Security: secret storage; repo access scope; PII not expected.

Proposed MVP (1–3 days):
- Ingest selected repo paths; chunk+embed; store in Supabase pgvector.
- /chat endpoint with top-k citations; log Q/A; mark “insufficient”.
- GitHub webhook to reindex changed files only.
- Minimal admin/reporting (query log + export).
- Decision: Ingestion scope — include [ai_docs/context/](ai_docs/context/); extensions: .md, .txt, .pdf; exclude code files.
- Pending: Choose parsing lib (Docling vs Unstructured) and PDF handling specifics.
- Decision: Parsing/ingestion — Docling (pip: docling) for .md/.txt/.pdf; keep headings as metadata; include basic images/tables where available.
- Pending: Markdown fenced code blocks — strip or keep? (recommend strip in MVP to reduce noise)
- Decision: Vector store — Supabase Postgres + pgvector; schema: sewp_context.
- Decision: Markdown code blocks — keep as plain text in chunks (no syntax-highlighting metadata).
- Decision: Embeddings/chunking — OpenAI text-embedding-3-small; chunk_size=800 tokens; overlap=15%.
- Decision: Webhook/infra — GitHub App; event: push on default branch; incremental reindex (changed files only); secrets in container .env (mounted).
- Decision: API/auth — API-only EDA: /webhook → store in event table → enqueue worker → execute workflow → persist to event.result; all endpoints protected via M2M shared secret (in container .env). Pending: header name and env var key for the shared secret.
- Decision: M2M auth details — Header: X-SEWP-Secret; Env var: SEWP_M2M_SECRET; constant-time compare; 401 on mismatch; applied to all protected endpoints.
- Decision: Accuracy evaluation — Final workflow node validates each answer’s assertions against retrieved passages; each assertion must include citation (source doc + line/paragraph). Uncited assertions counted as inaccurate. Valid deduction/induction annotated; otherwise flagged “suspect”.
- Decision: Usefulness metric — Track thumbs up/down and “insufficient” rate per answer.
- Stakeholders (list provided): Developer, Owner, MCA, COO, Admin, Sales, Practitioner. Pending: map each to responsibility (sponsor, decision-maker, eng owner, data owner, security reviewer, pilot users, etc.).
- Decision: Timeline — 1‑day MVP: single‑pass CLI ingest + /chat with citations; no webhook; minimal logging; eval node stub (records citations; no strict scoring).
- Decision: Retrieval — top_k=6 with inline citations; payload = file path, heading chain, commit SHA, passage start/end offsets; passage_size≈1200 chars.
- Decision: Data governance — Internal-only; no sensitive PII.
- Pending: Repo scope confirmation (read-only to [ai_docs/context/](ai_docs/context/:1)?), retention windows for logs/Q&amp;A and embeddings, and encryption notes (TLS in transit; Supabase at-rest assumed).