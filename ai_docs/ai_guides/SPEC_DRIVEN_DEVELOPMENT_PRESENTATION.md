# Spec-Driven Development with GenAI Launchpad

---SLIDE 1: Title Slide---

# Spec-Driven Development

## Building AI-Powered Applications with Precision

Using GenAI Launchpad as Your Foundation

---SLIDE 2: The Problem---

# Why Spec-Driven Development?

## The Challenge with AI Tools

AI makes assumptions about what you want to build. Without clear specifications, you get:

- Features you didn't ask for
- Architecture that doesn't match your vision  
- Code that technically works but misses the mark
- Endless rounds of "that's not what I meant"

## The Solution

Specifications provide constraints that guide AI to build exactly what you intend.

---SLIDE 3: What is Spec-Driven Development?---

# The Specification Cascade

## A Natural Flow from Vision to Implementation

```
Project Charter → PRD → Architecture Design → WBS → Task Specs
```

Each document builds on the previous one:

- **Charter**: Why are we building this?
- **PRD**: What are we building?
- **Architecture**: How will we build it?
- **WBS**: What tasks need to be done?
- **Task Specs**: Implementation details

---SLIDE 4: GenAI Launchpad Overview---

# GenAI Launchpad Template

## Your Starting Point for AI-Powered Applications

GenAI Launchpad provides:

- Event-driven workflow orchestration system
- DAG-based workflow execution engine
- Multi-provider AI support (OpenAI, Anthropic, Gemini, etc.)
- Type-safe implementation with Pydantic
- Complete documentation structure

Clone it and build your own AI application on top.

---SLIDE 5: Project Structure---

# Understanding the Structure

## Key Directories in GenAI Launchpad

```
genai-launchpad/
├── app/                    # Application code
│   ├── core/              # Workflow engine
│   ├── workflows/         # Your custom workflows
│   └── CLAUDE.md         # Application insights
├── ai_docs/               # AI documentation
│   ├── commands/         # AI command library
│   ├── context/          # Project specifications
│   └── ai_guides/        # This documentation
└── docker/               # Container setup
```

---SLIDE 6: The Command Flow---

# Building a New Project

## The Five Essential Commands

1. `/project_charter` - Define business vision
2. `/prd` - Detail product requirements  
3. `/architecture_design` - Design system architecture
4. `/wbs` - Break down work into tasks
5. `/task_spec` - Create implementation specs

Each command engages you in intelligent consultation to extract requirements without overwhelming you.

---SLIDE 7: Starting with Project Charter---

# Step 1: Project Charter

## Setting Your Business Vision

```bash
/project_charter "AI-powered customer support automation"
```

The AI will ask about:

- Target market and customer needs
- Business objectives and success metrics
- Stakeholders and their interests
- Resource constraints and timeline
- Risk assessment

Output: `ai_docs/context/core_docs/project_charter.md`

---SLIDE 8: Defining Requirements---

# Step 2: Product Requirements

## What Will You Build?

```bash
/prd "Based on the project charter"
```

The consultation covers:

- User personas and their goals
- User journeys through the system
- Functional requirements (features)
- Non-functional requirements (performance, security)
- Acceptance criteria for success

Output: `ai_docs/context/core_docs/prd.md`

---SLIDE 9: Architecture Design---

# Step 3: System Architecture

## How Will You Build It?

```bash
/architecture_design "Design system based on PRD"
```

Key decisions:

- System topology (monolith vs microservices)
- Technology stack selection
- Data flow and storage strategies
- Integration patterns
- Security architecture

Output: `ai_docs/context/core_docs/add.md`

---SLIDE 10: Work Breakdown---

# Step 4: Task Organization

## Breaking Down the Work

```bash
/wbs "Create work breakdown from architecture"
```

Creates tasks with:

- Complexity ratings (Low/Medium/High)
- Dependencies between tasks
- Logical grouping and sequencing
- No time estimates (complexity matters more)

Output: `ai_docs/context/core_docs/wbs.md`

---SLIDE 11: Implementation Workflow---

# Development Loop

## From Tasks to Code

For each task in your WBS:

1. Create detailed specification:

   ```bash
   /task_spec "Implement user authentication feature"
   ```

2. Use specification to generate code with AI

3. Track progress:

   ```bash
   /update_wbs "Update based on last 10 commits"
   ```

---SLIDE 12: Understanding CLAUDE.md---

# CLAUDE.md Files

## Distributed Documentation for AI Context

CLAUDE.md files capture non-obvious insights:

- Critical implementation details
- Architectural decisions and gotchas
- Integration patterns
- Performance characteristics

Example locations:

- `/CLAUDE.md` - Project-wide conventions
- `/app/core/CLAUDE.md` - Workflow engine insights
- `/app/workflows/your_workflow/CLAUDE.md` - Feature-specific notes

---SLIDE 13: CLAUDE.md Best Practices---

# Writing Effective CLAUDE.md

## Focus on What's Not Obvious

✅ **DO Document:**

- "Nodes are instantiated fresh each execution - no state in instance variables"
- "Router process() method is never called - only route()"
- "Database connections timeout after 300s - always use context manager"

❌ **DON'T Document:**

- "UserService handles user operations"
- "This method returns a list"
- Generic best practices

---SLIDE 14: Implementing a Workflow---

# Building on GenAI Launchpad

## Creating Your First Workflow

1. Define your event schema in `app/schemas/`
2. Create workflow class in `app/workflows/`
3. Implement nodes in `app/workflows/your_workflow_nodes/`
4. Register in `WorkflowRegistry`
5. Test with POST to `http://localhost:8080/events/`

Each step guided by specifications and CLAUDE.md insights.

---SLIDE 15: ---

# Keeping Documentation Current

## Intelligence Built Into Updates

```bash
# Analyzes git commits to detect drift
/update_wbs "last 20 commits"

# Maps WBS changes to requirement evolution  
/update_prd "based on WBS complexity changes"

# Scans codebase for architectural patterns
/update_add "document architecture evolution"
```

No generic forms - just targeted questions based on evidence.

---SLIDE 16: ---

# Example: WBS Update

## What Actually Happens

```bash
/update_wbs "last 10 commits"
```

The command:

1. Analyzes your commits
2. Detects work not in WBS
3. Finds complexity increases
4. Asks specific questions:
   - "Found 5 commits for caching - was this planned?"
   - "Database task has 8 fix commits - increase complexity?"

---SLIDE 17: Development Best Practices---

# Best Practices

## Working with Spec-Driven Development

1. **Start with clear business objectives** - Charter matters
2. **Let specifications guide implementation** - Don't code first
3. **Update regularly** - Every few days, not at sprint end
4. **Document surprises in CLAUDE.md** - Help future you
5. **Trust the process** - Specifications prevent assumptions

---SLIDE 18: Quick Reference---

# Command Quick Reference

## Your Daily Commands

**Starting a project:**

- `/project_charter` → `/prd` → `/architecture_design` → `/wbs`

**During development:**

- `/task_spec [feature]` - Before implementing
- `/update_wbs` - Track progress (every few days)

**At milestones:**

- `/update_add` - Document architecture reality
- `/update_prd` - If requirements evolved

---SLIDE 19: Getting Started---

# Your Next Steps

## Start Building with GenAI Launchpad

1. Clone the GenAI Launchpad repository
2. Run `/project_charter` to define your vision
3. Follow the specification cascade
4. Build your workflows on the proven foundation
5. Keep documentation current with updates

Remember: You control the AI through specifications. The AI amplifies your capability through implementation speed.

---SLIDE 20: Resources---

# Resources and Documentation

## Everything You Need

- **Main Guide**: `ai_docs/ai_guides/AI_ASSISTED_DEVELOPMENT_GUIDE.md`
- **Quick Start**: `ai_docs/ai_guides/QUICK_START.md`  
- **CLAUDE.md Guide**: `ai_docs/ai_guides/CLAUDE_MD_USAGE.md`
- **Command Reference**: `ai_docs/commands/`

## Support

- Check existing CLAUDE.md files for insights
- Use update commands to analyze unclear code
- Let specifications guide your implementation

---SLIDE 21: Thank You---

# Questions?

## Remember the Core Principle

Specifications are your tool for maintaining control over AI-assisted development.

When you specify precisely what you want, AI can build it exactly as intended.

Start with GenAI Launchpad. Build with confidence.
