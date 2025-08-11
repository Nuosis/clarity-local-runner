# Update Product Requirements Document

READ the current PRD from `ai_docs/context/core_docs/prd.md`.
ANALYZE the WBS change history in `ai_docs/context/core_docs/wbs.md`.
ENGAGE in iterative consultation to understand requirement evolution.
UPDATE the PRD based on actual project learnings without assumptions.

Update PRD based on:

$ARGUMENTS

## Process

1. **Analyze WBS Evolution**
   - Read WBS change history section
   - Note completed tasks and their outcomes
   - Identify new tasks that suggest requirement changes
   - Review complexity adjustments and their reasons

2. **Map WBS Changes to PRD Requirements**
   - Which completed tasks fulfill which requirements?
   - What new tasks indicate missing requirements?
   - Which complexity increases suggest underspecified requirements?
   - What removed tasks indicate obsolete requirements?

3. **Interactive Requirement Consultation**

   Based on WBS analysis, ask specific questions aligned with PRD sections:

   **For Functional Requirements:**
   - "Task X is complete. Does the implementation fully satisfy functional requirement Y?"
   - "The implementation required 3 additional subtasks. What functional requirements were underspecified?"

   **For Non-Functional Requirements:**
   - "I see retry logic was added. What reliability/performance requirement does this address?"
   - "Database tasks increased in complexity. What scalability requirements emerged?"

   **For User Journey Changes:**
   - "This new workflow wasn't in the original user journeys. Which persona needs this?"
   - "Has the user's interaction model changed based on implementation feedback?"

   **For Data Requirements:**
   - "New data models were added. What business rules or relationships were discovered?"
   - "Data migration tasks appeared. Were data lifecycle requirements missed?"

   **For Edge Cases:**
   - "Multiple error handling tasks added. What edge cases were discovered?"
   - "Should these become formal error scenarios in the PRD?"

4. **Document Requirement Evolution**

## Question Framework

### Discovery Questions

- "What user feedback has influenced these changes?"
- "Have any business objectives shifted based on development insights?"
- "What technical constraints were discovered during implementation?"

### Validation Questions

- "This pattern appears multiple times. Should it become a formal requirement?"
- "Does this change affect your success criteria?"
- "Are there downstream requirements impacted by this change?"

### Context Questions

- "What drove this decision?"
- "Is this a temporary workaround or permanent requirement change?"
- "Who are the stakeholders affected by this change?"

## Update Format

```markdown
### 3.2 Authentication Requirements

**Original**: Users shall authenticate via email/password
<!-- Updated 2025-07-23: Based on enterprise customer feedback -->
**Current**: Users shall authenticate via email/password OR SSO integration
- **Rationale**: Enterprise customers require SAML/OAuth integration
- **WBS Evidence**: Added 3 SSO-related tasks, increased auth complexity to High
- **Impact**: Affects user management, session handling, and security requirements
```

## Change Documentation

Every PRD update must include:

1. **Date stamp** of the change
2. **WBS evidence** that triggered the update
3. **Business rationale** (not technical reasons)
4. **Stakeholder impact** assessment

## Critical Instructions

1. **NEVER assume requirements** - Always ask for clarification
2. **Link to WBS evidence** - Every change needs WBS backing
3. **Focus on the WHY** - Business reasons, not technical details
4. **Maintain requirement integrity** - Don't break existing dependencies
5. **Ask before removing** - Never delete requirements without confirmation

## Requirement Health Checks

After updates, verify each PRD section:

**Functional Requirements**:

- Still specific and testable?
- User stories still valid?
- Dependencies updated?

**Non-Functional Requirements**:

- Performance metrics still achievable?
- Security requirements adequate?
- Scalability needs addressed?

**User Personas & Journeys**:

- Do personas still reflect actual users?
- Are journeys aligned with implementation?

**Acceptance Criteria**:

- Still measurable and verifiable?
- Do they cover discovered edge cases?

**Data Requirements**:

- Models complete with discovered relationships?
- Business rules accurately captured?

## Where to Save Updates

**ALWAYS update in place**: `ai_docs/context/core_docs/prd.md`

- Use inline comments for change tracking
- Preserve historical context where valuable
- Never create PRD versions

Remember: The PRD captures WHAT and WHY, while the WBS captures HOW. Keep the PRD focused on business requirements, not implementation details.
