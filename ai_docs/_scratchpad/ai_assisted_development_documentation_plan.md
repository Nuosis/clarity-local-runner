# AI-Assisted Development Documentation Plan - REVISED

## Context for New Session

This plan outlines creating a comprehensive guide for **Spec-Driven Development with AI** - a methodology where specifications guide AI tools to build exactly what's intended, minimizing assumptions and maximizing developer control.

### Core Philosophy

Based on extensive refinement of AI commands, the key principles are:

1. **Evidence-Based Intelligence** - AI analyzes actual artifacts (code, docs, commits) before asking questions
2. **No Assumptions** - AI must ask specific questions rather than guess intent
3. **Iterative Refinement** - Documents evolve through targeted consultation, not regeneration
4. **Context Preservation** - Changes tracked in-place with clear rationale
5. **Developer Efficiency** - Focus on what matters, skip the obvious

### Current State Analysis

#### Documentation Hierarchy

- **Core Documents** (`ai_docs/context/core_docs/`):
  - `project_charter.md` - Business vision and objectives
  - `prd.md` - Detailed requirements and user stories  
  - `add.md` - System architecture and design
  - `wbs.md` - Task breakdown with complexity ratings

- **CLAUDE.md System**:
  - Distributed documentation for AI context
  - Focus on non-obvious insights and gotchas
  - Key patterns and architectural decisions

- **AI Commands** (`ai_docs/commands/`):
  - Pre-dev: Charter → PRD → ADD → WBS flow
  - Dev: Task specs, tests, updates
  - Post-dev: Retrospective updates

### Key Insights from Command Refinement

#### 1. Update Commands Are Intelligent

Each update command now:

- Analyzes existing documents for evidence
- Detects gaps and changes programmatically
- Asks specific, evidence-based questions
- Updates in-place with clear change tracking

Examples:

- **update_wbs.md**: Analyzes git commits to detect work drift
- **update_prd.md**: Maps WBS changes to requirement evolution
- **update_add.md**: Scans codebase for architectural patterns
- **update_project_charter.md**: Cross-references all docs for business impact

#### 2. Generation Commands Use Consultation

Pre-dev commands follow pattern:

- Extract requirements through targeted questions
- Use scratchpad for context persistence
- Build comprehensive understanding before generation
- Only generate when explicitly instructed

#### 3. Focus on Developer Reality

Commands now:

- Use bash/grep/find for analysis (no Python scripts)
- Focus on complexity not time estimates
- Track decisions and rationale
- Integrate with actual developer workflow

## Detailed Implementation Plan

### 1. Main Guide: `ai_docs/AI_ASSISTED_DEVELOPMENT_GUIDE.md`

#### Structure

**I. Introduction to Spec-Driven Development**:

- What problem does this solve?
- How AI amplifies developer capability
- The specification cascade: Charter → PRD → ADD → WBS → Tasks
- Why evidence-based updates matter

**II. The Developer's Control System**:

- How specifications minimize AI assumptions
- The power of targeted questions
- Evidence-based decision making
- Maintaining project coherence

**III. Starting a New Project (Greenfield)**:

A. Business Foundation Phase

1. Project Charter - Setting Vision
   - The consultation process
   - Business focus (not technical)
   - Success metrics that matter
   - Output: `ai_docs/context/core_docs/project_charter.md`

2. Product Requirements - What to Build
   - User personas and journeys
   - Functional/non-functional requirements
   - Acceptance criteria
   - Output: `ai_docs/context/core_docs/prd.md`

3. Architecture Design - How to Build
   - System topology decisions
   - Technology selection rationale
   - Scalability and security
   - Output: `ai_docs/context/core_docs/add.md`

4. Work Breakdown - Tasks and Complexity
   - Task decomposition
   - Complexity ratings (Low/Medium/High)
   - Dependencies and sequencing
   - Output: `ai_docs/context/core_docs/wbs.md`

B. Development Phase

1. Task Specifications
   - Converting WBS items to detailed specs
   - Implementation constraints
   - Success criteria

2. Writing Code with Specs
   - Spec → Implementation workflow
   - Following conventions (CLAUDE.md)
   - Test-driven approach

3. Continuous Updates
   - Using update_wbs to track progress
   - Evidence-based status changes
   - Decision documentation

**IV. Working with Existing Projects (Brownfield)**:

A. Understanding the Codebase

1. CLAUDE.md Navigation
   - Reading order and priorities
   - Extracting key insights
   - Understanding conventions

2. Analyzing Current State
   - Where are the core docs?
   - What's the architecture?
   - What patterns exist?

B. Making Changes

1. Targeted Specifications
   - Spec for specific features
   - Working within constraints
   - Maintaining consistency

2. Intelligent Updates
   - Let update commands analyze first
   - Answer targeted questions
   - Track evolution

**V. The Update Cycle**:

A. During Development

1. WBS Updates
   - Git analysis for task drift
   - Complexity adjustments
   - New task discovery

2. PRD Evolution
   - Requirements clarification
   - Scope refinement
   - User feedback integration

B. Major Milestones

1. Architecture Updates
   - Codebase analysis
   - Pattern detection
   - Design evolution

2. Charter Reflection
   - Business outcome assessment
   - Strategic impact
   - Executive communication

**VI. Power Techniques**:

A. Evidence-Based Workflow

1. Let AI Analyze First
   - Code structure detection
   - Dependency analysis
   - Pattern recognition

2. Targeted Consultation
   - Specific questions based on evidence
   - No generic questionnaires
   - Focus on decisions

B. Context Management

1. CLAUDE.md Integration
   - When to read vs reference
   - Keeping context focused
   - Update triggers

2. Document Evolution
   - In-place updates
   - Change tracking
   - Rationale capture

### 2. Quick Start Guide: `ai_docs/QUICK_START.md`

#### Decision Tree

```txt
Starting Fresh?
└─> /project_charter → /prd → /architecture_design → /wbs

Have a Project?
├─> New Feature: Read core docs → /task_spec → implement
├─> Major Change: /update_prd → /update_wbs → implement
└─> Maintenance: Read CLAUDE.md → make changes

At Milestone?
├─> Development Complete: /update_add
├─> Sprint End: /update_wbs → /update_prd
└─> Project End: /update_project_charter
```

#### Essential Patterns

**Pattern 1: Greenfield MVP**:

```txt
1. /project_charter - Define business vision
2. /prd - Detail requirements
3. /architecture_design - Design system
4. /wbs - Break down work
5. Loop: /task_spec → implement → /update_wbs
```

**Pattern 2: Feature Addition**:

```txt
1. Read prd.md and wbs.md
2. /task_spec for new feature
3. Implement with specs
4. /update_wbs with results
5. /update_prd if scope changed
```

**Pattern 3: Architecture Evolution**:

```txt
1. Implement changes
2. /update_add - Analyzes and asks questions
3. Document decisions
4. Update CLAUDE.md if needed
```

### 3. CLAUDE.md Integration: `ai_docs/CLAUDE_MD_USAGE.md`

#### When CLAUDE.md Matters

- **Before coding**: Read relevant CLAUDE.md files
- **During updates**: Reference for conventions
- **After changes**: Update with new insights

#### Writing Effective CLAUDE.md

Focus on:

- Non-obvious behaviors
- Critical gotchas
- Architectural decisions
- Integration patterns

Skip:

- Obvious code structure
- Generic descriptions
- Implementation details

#### The Synergy

- **Specs** define WHAT to build
- **CLAUDE.md** explains HOW things work
- **Updates** track WHY things changed
- Together: Complete context for AI

### 4. Command Integration

All commands now follow intelligent patterns:

**Generation Commands**:

- Iterative consultation
- Comprehensive understanding
- Explicit generation trigger

**Update Commands**:

- Automated analysis
- Evidence-based questions
- In-place modification
- Decision tracking

**Key Commands**:

- `/project_charter` - Business vision
- `/prd` - Requirements
- `/architecture_design` - System design
- `/wbs` - Task breakdown
- `/task_spec` - Implementation details
- `/update_wbs` - Track progress
- `/update_prd` - Evolve requirements
- `/update_add` - Architecture reality
- `/update_project_charter` - Business outcomes

## Implementation Priorities

1. **Main Guide** - Comprehensive spec-driven methodology
2. **Quick Start** - Decision trees and patterns
3. **CLAUDE.md Guide** - Integration best practices
4. **Command Setup** - .claude/commands/ structure
5. **Examples** - Real workflow demonstrations

## Success Metrics

A guide succeeds when:

- Developers control AI output through specifications
- No critical decisions made by assumption
- Evolution tracked with clear rationale
- Projects maintain coherence from vision to implementation
- AI amplifies capability without adding chaos

## The Spirit

This isn't about generating more documentation - it's about using specifications to maintain control over AI-assisted development. Every command should help developers:

1. **Specify precisely** what they want
2. **Guide intelligently** how it's built
3. **Track systematically** how it evolves
4. **Communicate clearly** why it changed

The result: AI becomes a powerful amplifier of developer intent, not a source of random assumptions.
