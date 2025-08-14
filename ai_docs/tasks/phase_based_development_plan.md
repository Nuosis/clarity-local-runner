# SEWP Chatbot - Phase-Based Development Plan

## Executive Summary
This document outlines a structured, phase-based approach to implementing the SEWP Chatbot system. The project will deliver a RAG-based chatbot that provides evidence-backed answers from GitHub repository documentation with automatic reindexing capabilities.

**Total Duration**: 6-8 weeks  
**Team Size**: 2-3 developers  
**Methodology**: Agile with 1-week sprints  

---

## Phase 1: Foundation & Infrastructure (Week 1)
**Goal**: Establish core infrastructure, database schemas, and development environment

### Deliverables
1. **Database Setup**
   - [ ] PostgreSQL with pgvector extension configured
   - [ ] Supabase integration complete
   - [ ] Schema `sewp_context` created with required tables:
     - Documents table
     - PassageChunks table
     - EmbeddingVectors table
     - Events table
     - QARecords table
   - [ ] Alembic migrations configured and tested

2. **Development Environment**
   - [ ] Docker compose configuration for local development
   - [ ] Environment variables and secrets management (.env setup)
   - [ ] GitHub repository access configured with token
   - [ ] OpenAI API key configured for embeddings

3. **Core API Framework**
   - [ ] FastAPI application structure
   - [ ] Basic `/health` endpoint
   - [ ] Event ingestion endpoint `/events` 
   - [ ] M2M authentication middleware (X-SEWP-Secret header)
   - [ ] Celery worker configuration
   - [ ] Redis/RabbitMQ message broker setup

### Success Criteria
- Docker compose brings up all services successfully
- Database migrations run without errors
- Health endpoint returns 200 OK
- Basic event can be posted and stored

### Risk Mitigation
- Use existing GenAI Launchpad patterns to accelerate setup
- Leverage docker compose templates from existing codebase

---

## Phase 2: Document Ingestion Pipeline (Week 2)
**Goal**: Implement complete document processing and embedding pipeline

### Deliverables
1. **Ingest Workflow Implementation**
   - [ ] Gate node - input validation and sanitization
   - [ ] Type router node - handle init/rebase/reindex modes
   - [ ] Compiler node - document discovery and metadata extraction
   - [ ] Processor node - Docling integration for parsing
   - [ ] Save node - chunking, embedding, and storage

2. **Document Processing**
   - [ ] Docling library integration for .md/.txt/.pdf parsing
   - [ ] Heading preservation and metadata extraction
   - [ ] Code block handling (preserve as plain text)
   - [ ] File exclusion rules (skip code files)

3. **Embedding Pipeline**
   - [ ] OpenAI text-embedding-3-small integration
   - [ ] 800-token chunking with 15% overlap
   - [ ] Metadata preservation (path, headings, offsets, commit SHA)
   - [ ] Idempotent upsert logic to pgvector

4. **CLI Tool**
   - [ ] Command-line interface for manual ingestion
   - [ ] Progress reporting and summary statistics
   - [ ] Dry-run mode for testing

### Success Criteria
- Successfully ingest `ai_docs/context/` directory
- Verify embeddings stored with correct metadata
- Reindex operation only processes changed files
- CLI tool provides clear feedback

### Testing Checkpoints
- Unit tests for chunking algorithm
- Integration test for Docling parsing
- End-to-end test of complete ingestion

---

## Phase 3: Retrieval & Search Implementation (Week 3)
**Goal**: Build robust multi-modal search capabilities

### Deliverables
1. **Search Infrastructure**
   - [ ] Keyword search using PostgreSQL full-text search
   - [ ] Semantic search using pgvector similarity
   - [ ] Concurrent search execution node
   - [ ] Result ranking and deduplication

2. **Retrieval Components**
   - [ ] Prepare node - query analysis and parameter extraction
   - [ ] Keyword search node - phrase and ILIKE queries
   - [ ] Semantic search node - vector similarity with top_k
   - [ ] Search aggregation and scoring

3. **Passage Management**
   - [ ] Passage extraction with context windows
   - [ ] Metadata enrichment (headings, paths, offsets)
   - [ ] Citation payload generation

### Success Criteria
- Keyword search returns relevant passages
- Semantic search achieves >90% relevance
- Combined search outperforms individual methods
- Retrieval latency <500ms for top_k=6

### Performance Benchmarks
- Test with 1000+ document corpus
- Measure p95 latency
- Validate retrieval accuracy

---

## Phase 4: Answer Generation & Synthesis (Week 4)
**Goal**: Implement intelligent answer composition with citations

### Deliverables
1. **Answer Workflow**
   - [ ] Gate node - request validation and auth
   - [ ] Prepare node - query understanding (AgentNode)
   - [ ] Search node - concurrent retrieval (ConcurrentNode)
   - [ ] Synthesis node - answer generation (AgentNode)

2. **Answer Generation**
   - [ ] LLM integration for answer composition
   - [ ] Inline citation formatting
   - [ ] Context-aware response generation
   - [ ] Handling of insufficient information cases

3. **Citation System**
   - [ ] Citation extraction from passages
   - [ ] Inline citation markers in answers
   - [ ] Citation payload with full metadata
   - [ ] Link generation to source documents

### Success Criteria
- Answers include relevant citations
- Each assertion backed by evidence
- Clear indication when information insufficient
- Response time <3s p95

### Quality Metrics
- Citation coverage per assertion
- Answer relevance scoring
- User satisfaction tracking

---

## Phase 5: Verification & Quality Assurance (Week 5)
**Goal**: Ensure answer accuracy and citation completeness

### Deliverables
1. **Verification Sub-workflow**
   - [ ] Extract assertions node - identify factual claims
   - [ ] Citation mapping node - link assertions to evidence
   - [ ] Verification gate - ensure citation coverage
   - [ ] Loop-back mechanism for incomplete citations

2. **Quality Controls**
   - [ ] Assertion extraction algorithm
   - [ ] Citation validation logic
   - [ ] Deduction/induction annotation
   - [ ] Suspect assertion flagging

3. **Feedback System**
   - [ ] Thumbs up/down capture
   - [ ] Insufficient flag handling
   - [ ] QA record logging
   - [ ] Metrics aggregation

### Success Criteria
- 95% of assertions have citations
- Uncited assertions properly flagged
- Feedback captured in database
- Verification adds <500ms latency

### Acceptance Tests
- Test with known Q&A pairs
- Validate citation accuracy
- Measure false positive/negative rates

---

## Phase 6: Production Readiness (Week 6)
**Goal**: Harden system for production deployment

### Deliverables
1. **Security Hardening**
   - [ ] Constant-time secret comparison
   - [ ] Input sanitization across all nodes
   - [ ] Rate limiting implementation
   - [ ] Audit logging

2. **Operational Excellence**
   - [ ] Comprehensive error handling
   - [ ] Retry logic with exponential backoff
   - [ ] Circuit breakers for external services
   - [ ] Health checks for all components

3. **Monitoring & Observability**
   - [ ] Structured logging implementation
   - [ ] Metrics collection (Prometheus-ready)
   - [ ] Distributed tracing setup
   - [ ] Alert configurations

4. **Documentation**
   - [ ] API documentation (OpenAPI/Swagger)
   - [ ] Deployment guide
   - [ ] Operations runbook
   - [ ] Troubleshooting guide

### Success Criteria
- Pass security audit
- 99.5% uptime in staging
- All alerts configured and tested
- Documentation reviewed and approved

### Pre-Production Checklist
- Load testing completed
- Disaster recovery tested
- Rollback procedures verified
- Monitoring dashboards operational

---

## Phase 7: GitHub Integration (Week 7-8)
**Goal**: Automate document reindexing via GitHub webhooks

### Deliverables
1. **GitHub App Setup**
   - [ ] GitHub App registration
   - [ ] Webhook configuration
   - [ ] Authentication setup
   - [ ] Permission scoping

2. **Webhook Handler**
   - [ ] `/webhook` endpoint implementation
   - [ ] Push event processing
   - [ ] Commit diff analysis
   - [ ] Incremental reindex triggering

3. **Automation Pipeline**
   - [ ] Change detection logic
   - [ ] Selective document reprocessing
   - [ ] Commit SHA tracking
   - [ ] Rollback capabilities

### Success Criteria
- Webhook receives GitHub events
- Only changed files reindexed
- <5 minute reindex latency
- Zero duplicate processing

### Integration Tests
- Test with various commit types
- Validate incremental updates
- Ensure idempotency

---

## Risk Management

### Technical Risks
1. **PDF Parsing Complexity**
   - Mitigation: Focus on Markdown/text first, simplified PDF extraction as fallback
   
2. **Embedding Cost/Latency**
   - Mitigation: Implement caching, batch processing, consider alternative models

3. **Citation Accuracy**
   - Mitigation: Smaller chunks, increased overlap, passage validation

4. **Scalability Concerns**
   - Mitigation: Horizontal scaling ready, connection pooling, query optimization

### Schedule Risks
1. **Compressed Timeline**
   - Mitigation: Strict scope control, reuse existing patterns, parallel development

2. **Integration Delays**
   - Mitigation: Early API mocking, contract-first development

---

## Resource Allocation

### Team Structure
- **Lead Developer**: Architecture, workflows, integration
- **Backend Developer**: Database, search, embeddings
- **DevOps Engineer** (part-time): Infrastructure, deployment, monitoring

### Key Dependencies
- OpenAI API access
- GitHub repository access
- Supabase instance
- Docker/Kubernetes infrastructure

---

## Success Metrics

### Technical KPIs
- Answer accuracy: ≥95% (citation coverage)
- Response latency: p95 ≤3s
- System availability: ≥99.5%
- Ingestion throughput: 500 pages in 10 minutes

### Business KPIs
- User satisfaction: ≥90% thumbs up
- Insufficient rate: ≤10%
- Adoption rate: 50% of target users in first month
- Query volume: 100+ queries/day after launch

---

## Go-Live Criteria

### MVP Launch (End of Week 6)
- [ ] Core workflows operational
- [ ] Manual ingestion complete
- [ ] Answer generation with citations working
- [ ] Basic monitoring in place
- [ ] Security controls implemented

### Full Production (End of Week 8)
- [ ] GitHub automation active
- [ ] Complete observability suite
- [ ] Performance targets met
- [ ] Documentation complete
- [ ] User training conducted

---

## Post-Launch Roadmap

### Month 2
- Admin UI for monitoring
- Advanced analytics dashboard
- Multi-repo support
- Custom embedding models

### Month 3
- Conversation memory
- Multi-turn dialogue
- Source code understanding
- API rate limiting tiers

### Future Enhancements
- Real-time collaboration features
- Integration with other tools (Slack, Teams)
- Custom knowledge graphs
- Fine-tuned language models

---

## Appendix: Technical Stack

### Core Technologies
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Database**: PostgreSQL with pgvector
- **Queue**: Celery with Redis/RabbitMQ
- **Container**: Docker, Docker Compose
- **Cloud**: Supabase for managed PostgreSQL

### Key Libraries
- **Document Processing**: Docling
- **Embeddings**: OpenAI API (text-embedding-3-small)
- **LLM**: OpenAI GPT-4 or similar
- **Validation**: Pydantic
- **ORM**: SQLAlchemy
- **Migrations**: Alembic

### Development Tools
- **Testing**: pytest, pytest-asyncio
- **Linting**: ruff, mypy
- **Documentation**: Sphinx, OpenAPI
- **Monitoring**: Prometheus, Grafana
- **Logging**: structlog

---

*Document Version: 1.0*  
*Last Updated: 2025-01-13*  
*Status: READY FOR REVIEW*