# Update Architecture Design Document

READ the current ADD from `ai_docs/context/core_docs/add.md`.
ANALYZE the codebase to detect architectural patterns and changes.
ENGAGE in targeted consultation to understand architectural decisions.
UPDATE the ADD to reflect actual implementation without assumptions.

Update architecture documentation based on:

$ARGUMENTS

## Automated Architecture Detection

1. **Scan Project Structure**

   ```bash
   # Detect new services/modules
   find app -type d -name "*service*" -o -name "*module*" | sort
   
   # Find configuration files revealing architecture
   find . -name "docker-compose*.yml" -o -name "*.dockerfile" -o -name "k8s/*.yaml"
   
   # Detect API definitions
   find app -name "*router*.py" -o -name "*endpoint*.py" -o -name "*api*.py"
   ```

2. **Analyze Dependencies**

   ```bash
   # Check for new architectural dependencies
   grep -E "redis|kafka|rabbitmq|celery|fastapi|django" requirements.txt
   
   # Database technologies
   grep -E "sqlalchemy|pymongo|psycopg|redis" requirements.txt
   
   # External service integrations
   grep -E "boto3|stripe|twilio|sendgrid" requirements.txt
   ```

3. **Detect Design Patterns**

   ```bash
   # Repository pattern
   find app -name "*repository*.py" | head -10
   
   # Event-driven patterns
   grep -r "publish\|subscribe\|emit\|on_event" --include="*.py" | head -10
   
   # Caching implementations
   grep -r "@cache\|redis\|memcache" --include="*.py" | head -10
   ```

## Interactive Architecture Consultation

Based on code analysis, ask specific questions:

### Service Architecture

- "I found new directories X, Y, Z. Are these separate services or modules?"
- "Service A imports from Service B frequently. Is this a direct dependency or should there be a message queue?"
- "No API gateway detected. How are you handling cross-service authentication?"

### Technology Stack Evolution

- "Redis appears in requirements but wasn't in original ADD. What role does it serve?"
- "I see Celery workers. What async tasks are being processed?"
- "Database migrations show 15 new tables. What drove this data model expansion?"

### Integration Patterns

- "Found 3 webhook endpoints. Which external services are integrated?"
- "OAuth implementation detected. Which providers are supported?"
- "Message queue configuration found. What communication patterns use this?"

### Performance & Scale

- "Connection pooling code found. What load are you designing for?"
- "Caching decorators on 20+ methods. What performance issues did you encounter?"
- "Rate limiting middleware detected. What are the thresholds?"

### Security Architecture

- "JWT implementation differs from ADD. What changed in auth strategy?"
- "Found encryption utilities. What data requires encryption?"
- "CORS configuration is permissive. Is this intentional?"

## Code-Based Evidence Gathering

### Directory Structure Analysis

```python
# Example detection logic
new_services = set(current_dirs) - set(add_documented_dirs)
if new_services:
    ask("These services aren't in the ADD: {new_services}. What do they do?")
```

### Configuration Analysis

- Docker Compose files reveal service topology
- Environment variables hint at external dependencies
- CI/CD files show deployment architecture

### Import Graph Analysis

- Circular imports suggest architectural issues
- Deep import chains indicate tight coupling
- Missing abstractions between layers

## Update Documentation Format

```markdown
## System Architecture - Updated [Date]

### Service Topology [EVOLVED]
**Original Design**: Monolithic API service
**Current Implementation**: 
- API Gateway (FastAPI)
- Auth Service (separate container)
- Worker Service (Celery + Redis)
- Database Service (PostgreSQL + Redis cache)

**Evolution Rationale**:
- Auth extracted due to [User's explanation]
- Workers added for [User's explanation]
- Evidence: docker-compose.yml shows 4 services

### Technology Stack Changes
| Component | Original | Current | Reason |
|-----------|----------|---------|---------|
| Cache | None | Redis | Found in requirements.txt, used in user_service.py:45 |
| Queue | None | Celery | Found worker definitions in app/tasks/ |
| Auth | JWT local | Auth0 | OAuth configuration in config.py |

### Architectural Patterns Discovered
1. **Repository Pattern** 
   - Evidence: app/repositories/ directory with 5 repository classes
   - Not in original ADD
   - Ask: "What drove the repository pattern adoption?"

2. **Event-Driven Updates**
   - Evidence: event_publisher.py and 10 event handlers
   - Ask: "What events flow through the system?"
```

## Critical Questions Framework

### Before Making Changes

1. "This pattern appears throughout the code. Is it an architectural decision?"
2. "The implementation differs from the ADD here. Was this intentional?"
3. "I found X but the ADD mentions Y. Which is correct?"

### Validation Questions

1. "Does this architectural change affect system boundaries?"
2. "Are there deployment implications I should document?"
3. "What operational insights led to this design?"

## Where to Save Updates

**ALWAYS update in place**: `ai_docs/context/core_docs/add.md`

- Preserve original design with strikethrough
- Add implementation notes with evidence
- Include decision rationale from developer

## Key Instructions

1. **Evidence-based updates** - Link changes to specific files/code
2. **Ask don't assume** - Verify interpretations with developer
3. **Preserve history** - Show evolution, not just final state
4. **Focus on architecture** - Not implementation details
5. **Document the WHY** - Rationale matters more than what

Remember: The ADD should help new developers understand both the system's structure and why it evolved this way.
