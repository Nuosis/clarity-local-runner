# Update Work Breakdown Structure

READ the WBS document from `ai_docs/context/core_docs/wbs.md`.
ANALYZE recent git commits to detect work done vs planned tasks.
CHECK `ai_docs/specs/` for new or modified specifications that impact tasks.
UPDATE the WBS with evidence-based changes reflecting actual project state.

Update WBS based on:

$ARGUMENTS

Identify if user specifies a commit count or time range in the arguments.
Default: Analyze last 2 days of commits if no commit count specified.

## Process

1. **Read Current WBS**
   - Use the Read tool to examine `ai_docs/context/core_docs/wbs.md`
   - Note existing tasks, complexity ratings, and completion status

2. **Analyze Recent Commits**

   ```bash
   # If user specifies: "last 20 commits"
   git log --oneline -20
   
   # Default: last 2 days
   git log --since="2 days ago" --oneline
   
   # Show which files changed most (complexity indicators)
   git log --since="2 days ago" --name-only --pretty=format: | \
     sort | uniq -c | sort -nr | head -10
   ```

3. **Detect Unplanned Work**

   ```bash
   # Find recent TODOs
   git grep -n "TODO\|FIXME\|HACK" | head -20
   
   # New files not in WBS
   git ls-files --others --exclude-standard | grep -E "\.(py|ts|tsx)$"
   
   # Files created recently
   find app -type f -name "*.py" -mtime -2
   ```

4. **Match Work to Tasks**
   - Read WBS task list
   - Map commit messages to task descriptions
   - Identify work without corresponding WBS items

5. **Interactive Clarification**
   When ambiguity exists, ask specific questions:
   - "I found 5 commits related to 'caching' but no WBS task. Was this planned work?"
   - "Task X shows no commits for 3 days. Is it blocked or deprioritised?"
   - "These 3 new files suggest feature Y. Should I add this as a new task?"

## Key Signals to Detect

### Task Completion

- Commits with "feat:", "implement", "complete" + task keywords
- Test files created for the feature
- No TODOs remaining in related files

### Increased Complexity

- Same file modified in 5+ commits → More complex than expected
- New dependencies added → Integration complexity
- Error handling commits → Edge cases discovered

### Unplanned Tasks

- New modules without WBS entry
- "fix:" commits for non-existent tasks
- Refactoring commits indicating tech debt

## Update Format

```markdown
## WBS Updates - Based on last 20 commits

### Completed Tasks
- [x] Implement CustomerSupportWorkflow
  - Evidence: Commits a1b2c3, d4e5f6 - created workflow + 3 nodes
  - Complexity: Medium (expected) → High (actual) - custom routing logic added

### In Progress
- [~] Add AgentNode for analysis (70% complete)
  - Evidence: analyze_node.py created, needs prompt refinement
  - Discovered: Need separate validation node (not in original WBS)

### New Tasks Discovered
- [ ] Create ValidationNode for input sanitization
  - Evidence: TODO in analyze_node.py:45
  - Complexity: Low
  
- [ ] Add error recovery for API timeouts  
  - Evidence: 3 timeout-related commits in last 2 days
  - Complexity: Medium

### Complexity Adjustments
- Database integration: Low → Medium
  - Evidence: 8 commits for connection pooling issues
  - Added subtasks: connection retry logic, pool management
```

Always use the actual format in the WBS document, maintaining consistency with existing entries.

## Where to Save Updates

**ALWAYS update the existing WBS**: `ai_docs/context/core_docs/wbs.md`

- NEVER create new versions or duplicate files
- Maintain change log and decision history within the document

## Change Log Format

Add a dedicated section in the WBS:

```markdown
## Change History

### 2025-07-23 Update
**Evidence Source**: Last 20 commits
**Key Changes**:
- Marked "Implement CustomerSupportWorkflow" as complete (commits: a1b2c3, d4e5f6)
- Increased complexity of "Database Integration" from Low to Medium (8 fix commits)
- Added new task: "Implement retry logic" (discovered via TODOs in connection.py:45-52)

**Decisions Made**:
- User decided to split "API Integration" into 3 subtasks for better tracking
- Deferred "Performance Optimization" to next sprint due to current priorities
- Removed "Legacy System Migration" task as no longer needed
```

## Focus on Evidence

Every change must have evidence:

- Specific commit SHAs
- File paths created/modified  
- TODO/FIXME line numbers
- Error messages encountered

## Development Insights Section

Also maintain a section for patterns and learnings:

```markdown
## Development Insights

### Patterns Observed
- Database tasks consistently take 2x initial complexity estimate
- New API integrations always require error handling subtasks
- Test coverage gaps discovered when implementing error paths

### Technical Decisions
- Chose async pattern for all external API calls (better error handling)
- Standardized on Pydantic for all data validation (type safety)
- Using repository pattern for database access (easier testing)
```

## Critical Instructions

1. **ASK before assuming**: If task descriptions are unclear or you need more context, ASK THE USER
2. **NEVER invent tasks**: Only document work that has evidence in commits or code  
3. **NO assumptions about future work**: Only update based on what actually happened
4. **Update in place**: Always modify the existing WBS file, never create versions
5. **Capture decisions**: Record WHY changes were made, not just what changed
6. **Track patterns**: Note recurring issues or consistent estimation errors

## Value as Central Development Tool

This WBS update process serves as:

- **Progress Tracker**: Evidence-based completion status
- **Decision Log**: Why plans changed and what was learned
- **Knowledge Base**: Patterns and insights for future work
- **Context Bridge**: Critical information for new Claude Code sessions

Remember: Task complexity matters more than time estimates when working with AI assistance.
