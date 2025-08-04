# CLAUDE.md Integration Guide

## Understanding CLAUDE.md Files

CLAUDE.md files serve as distributed documentation throughout your codebase, providing AI tools with essential context about how your code actually works. Unlike traditional documentation that often becomes stale, CLAUDE.md files focus on non-obvious behaviors and critical insights that directly impact development.

These files complement your specification documents by bridging the gap between what you planned to build and how it actually works. While specifications define intent, CLAUDE.md captures implementation reality.

## The Role of CLAUDE.md in Spec-Driven Development

### Specifications Define the What, CLAUDE.md Explains the How

Your core specifications tell AI what to build. The Project Charter establishes business objectives. The PRD details requirements. The Architecture Design outlines system structure. The WBS organizes tasks. These documents define intent and constraints.

CLAUDE.md files explain how things actually work in practice. They document that workflow nodes are instantiated fresh on each execution, which means state cannot persist in instance variables. They explain that routers use a two-phase execution pattern where process() is never called. These implementation details matter when generating code but don't belong in specifications.

### Context Without Clutter

Traditional documentation often includes obvious information that anyone can understand by reading code. CLAUDE.md takes the opposite approach. It documents only what's non-obvious, surprising, or critical to understand.

For example, a CLAUDE.md file won't document that a UserService class handles user operations. That's obvious from the name and code structure. It will document that the UserService caches user objects for 5 minutes using Redis, and that cache invalidation happens through an event system rather than direct calls. These non-obvious behaviors prevent bugs and guide proper usage.

### Living Documentation

CLAUDE.md files live alongside code and evolve with it. When you discover a gotcha during development, you add it to the nearest CLAUDE.md. When you make an architectural decision that affects how components interact, you document it. When you find that a seemingly simple operation has complex edge cases, you capture that knowledge.

This approach keeps documentation relevant and useful. Future developers (including AI tools) learn from your discoveries without repeating your mistakes.

## When to Read CLAUDE.md Files

### Before Starting Work in a Directory

Always read the CLAUDE.md file in any directory where you'll be working. These files contain critical context that prevents errors and guides proper implementation. Reading takes minutes but saves hours of debugging.

For example, before implementing a new workflow node, read `app/core/nodes/CLAUDE.md`. You'll learn about the execution model, state management constraints, and integration patterns. This knowledge shapes how you design your node.

### During Specification Creation

When creating task specifications, CLAUDE.md files provide implementation context that shapes requirements. If CLAUDE.md documents that all API endpoints require rate limiting, your specification should account for this constraint. If it explains that database connections use a specific pooling strategy, your specification should align with this pattern.

### When Debugging Integration Issues

CLAUDE.md files often document integration gotchas that cause subtle bugs. If your new feature doesn't work as expected, check CLAUDE.md files in related directories. You might discover that the authentication system has special token refresh requirements, or that the message queue requires specific acknowledgment patterns.

## How to Reference CLAUDE.md During Updates

### Extracting Patterns for Consistency

When update commands analyze your codebase, they should consider patterns documented in CLAUDE.md files. These patterns represent deliberate decisions that new code should follow.

For example, if CLAUDE.md documents that all service classes use dependency injection through constructors, the update commands should detect when new services deviate from this pattern. This helps maintain architectural consistency.

### Understanding Architectural Evolution

CLAUDE.md files often explain why certain architectural decisions were made. When `/update_add` detects architectural changes, these explanations provide context for understanding whether changes are intentional improvements or accidental deviations.

### Preserving Institutional Knowledge

During major updates, CLAUDE.md files preserve knowledge that might otherwise be lost. They explain why certain approaches were abandoned, what alternatives were considered, and what constraints shaped decisions. This historical context informs future changes.

## Writing Effective CLAUDE.md Content

### Focus on Non-Obvious Behaviors

Document behaviors that surprised you, caused bugs, or required deep investigation to understand. If you spent an hour figuring out why something didn't work as expected, document your discovery for the next developer.

Good examples include:

- Execution order dependencies that aren't obvious from code structure
- Side effects that occur through event systems or callbacks  
- Performance characteristics that affect usage patterns
- Integration requirements with external systems

### Document Critical Gotchas

Some behaviors can cause serious problems if not understood. Document these prominently in CLAUDE.md files. Examples include:

- Operations that appear safe but aren't thread-safe
- Methods that modify state in unexpected ways
- Caching behaviors that affect data consistency
- Error conditions that require special handling

### Explain Architectural Decisions

When code follows non-standard patterns for good reasons, document why. This prevents future developers from "fixing" code that works correctly but looks unusual.

For example: "This service uses synchronous calls instead of our standard async pattern because the downstream system cannot handle concurrent requests. Attempting to make this async will cause rate limiting errors."

### Keep It Concise and Specific

Each insight should be actionable and specific. Instead of "This module is complex," write "The validation logic uses a chain of responsibility pattern. Each validator must call next() or validation stops. See line 145 for the chain setup."

Include line numbers when referencing specific code sections. This creates a direct link between documentation and implementation.

## What to Skip in CLAUDE.md

### Obvious Code Structure

Don't document what's clear from reading code. Skip descriptions like "This class handles user authentication" or "This method returns a list of products." The code itself communicates this information.

### Generic Best Practices

CLAUDE.md isn't the place for generic programming advice. Don't include reminders to write tests, handle errors, or follow SOLID principles. Focus on project-specific insights.

### Implementation Details That Change Frequently

Avoid documenting details that change with normal refactoring. Don't list every method in a class or every field in a data structure. Document the patterns and constraints, not the specific implementation.

## The CLAUDE.md Hierarchy

### Root CLAUDE.md

The root CLAUDE.md provides project-wide context. It documents global conventions, architectural patterns, and critical project-specific knowledge. This includes:

- Import style conventions specific to your project
- Global error handling patterns
- Project-specific naming conventions
- Key architectural decisions that affect the entire codebase

### Module-Level CLAUDE.md

Each major module or directory can have its own CLAUDE.md. These files document module-specific patterns and gotchas. They explain how components within the module interact and what constraints apply.

For example, `app/core/CLAUDE.md` documents workflow execution patterns that apply to all workflows. It explains the DAG execution model, node instantiation behavior, and error propagation rules.

### Feature-Level CLAUDE.md

Sometimes specific features need their own documentation. Complex features with non-obvious interactions benefit from dedicated CLAUDE.md files that explain the full context.

## Maintaining CLAUDE.md Files

### Update Immediately When You Discover Insights

The best time to update CLAUDE.md is when knowledge is fresh. If you just spent time debugging an issue, document the insight immediately. If you made an architectural decision after careful consideration, capture the reasoning now.

### Review During Major Updates

When running update commands for architecture or requirements, review relevant CLAUDE.md files. They might need updates to reflect evolved understanding or changed patterns.

### Keep Content Focused

Periodically review CLAUDE.md files to remove outdated information. If documented gotchas have been fixed, remove them. If patterns have changed, update the documentation. Keep only information that remains valuable.

## Integration with AI Commands

### Generation Commands Read Context

When AI generates code, it reads relevant CLAUDE.md files to understand project patterns. This ensures generated code follows established conventions and avoids known gotchas.

### Update Commands Detect Deviations

Update commands can detect when new code deviates from patterns documented in CLAUDE.md. This helps maintain consistency and catch potential issues early.

### Specifications Reference Constraints

When creating specifications, reference constraints documented in CLAUDE.md. If CLAUDE.md explains that all database queries must use prepared statements, specifications should include this requirement.

## Example CLAUDE.md Patterns

### Documenting Non-Obvious Execution Models

```markdown
## Workflow Execution Model

Nodes are instantiated fresh on each workflow execution (see workflow.py:146). This means:
- You CANNOT store state in node instance variables between executions
- Each execution gets a clean node instance
- Use TaskContext for passing data between nodes
```

### Explaining Integration Gotchas

```markdown
## Redis Connection Management

The Redis client uses connection pooling with these constraints:
- Max connections: 50 (see config.py:23)
- Connections timeout after 300s idle
- CRITICAL: Always use context manager to ensure connection return
- Bulk operations must be chunked to avoid timeout (max 1000 items)
```

### Documenting Architectural Decisions

```markdown
## Why We Don't Use GraphQL

Despite initial plans for GraphQL, we use REST because:
1. Our mobile client has limited GraphQL support
2. Caching is simpler with REST endpoints
3. Team expertise is stronger with REST

This decision is reversible if mobile constraints change.
```

## Best Practices Summary

CLAUDE.md files work best when they focus on non-obvious, critical insights that directly impact development. They should complement specifications by documenting implementation reality. Keep them concise, specific, and actionable.

Read CLAUDE.md files before working in new areas. Update them immediately when you discover important insights. Reference them during specification creation and updates. Together with your specification documents, they provide complete context for effective AI-assisted development.

The goal is not comprehensive documentation but targeted insights that prevent errors and guide proper implementation. When used effectively, CLAUDE.md files become a valuable knowledge repository that makes your codebase more maintainable and AI-friendly.
