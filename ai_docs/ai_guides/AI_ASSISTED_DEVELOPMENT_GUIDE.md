# AI-Assisted Development Guide

## Introduction to Spec-Driven Development

### The Problem We're Solving

When developers use AI tools like Claude Code, they often encounter a fundamental challenge. The AI makes assumptions about what you want, implements features you didn't ask for, or misunderstands your requirements. This happens because traditional AI interactions lack structure and clear specifications. The result is frustration, wasted time, and code that doesn't match your vision.

Spec-Driven Development solves this problem by establishing a clear hierarchy of specifications that guide AI tools to build exactly what you intend. Instead of hoping the AI understands your vague requests, you create precise specifications that leave no room for misinterpretation.

### How AI Amplifies Developer Capability

Think of AI as an incredibly capable junior developer who can write code at superhuman speed but needs clear direction. When you provide that direction through specifications, AI becomes a powerful amplifier of your intent. You focus on what needs to be built and why, while AI handles the implementation details under your guidance.

The key insight is that AI works best when it has constraints. Specifications provide those constraints in a structured, predictable way.

### The Specification Cascade

Spec-Driven Development follows a natural cascade from high-level business vision to detailed implementation tasks:

```txt
Project Charter → Product Requirements → Architecture Design → Work Breakdown → Task Specifications
```

Each document builds on the previous one, creating a comprehensive blueprint for your project. The Charter establishes why you're building something. The PRD defines what you're building. The Architecture Design determines how you'll build it. The Work Breakdown Structure organizes the work. Task Specifications provide implementation details.

This cascade ensures that every line of code traces back to a business objective, and every business objective translates into concrete tasks.

### Why Evidence-Based Updates Matter

Projects evolve during development. Requirements change, technical realities emerge, and better solutions present themselves. Traditional documentation becomes stale and disconnected from reality.

Our approach uses intelligent update commands that analyze your actual code and development artifacts to detect changes. These commands ask specific questions based on evidence, not generic questionnaires. The result is documentation that evolves with your project while maintaining a clear history of decisions and changes.

## The Developer's Control System

### How Specifications Minimize AI Assumptions

Without specifications, AI must guess at your intent. It might assume you want a REST API when you need GraphQL. It might implement complex authentication when you just need a simple API key. These assumptions compound, leading to code that technically works but doesn't match your vision.

Specifications eliminate guesswork. When you specify that users authenticate via OAuth with Google, the AI won't implement a custom JWT system. When you define specific error handling requirements, the AI won't create generic try-catch blocks. Every specification becomes a constraint that guides AI toward your intended solution.

### The Power of Targeted Questions

Our AI commands don't just ask "What do you want to build?" They engage in intelligent consultation, asking specific questions that help clarify requirements without overwhelming you. For example, when creating a project charter, the AI might ask:

"You mentioned serving small businesses. What specific pain points are you addressing for this market?"

This targeted approach extracts meaningful requirements while respecting your time. Each question builds on previous answers, creating a comprehensive understanding of your project.

### Evidence-Based Decision Making

Traditional development often relies on assumptions and gut feelings. Our update commands analyze your actual code, commits, and documentation to provide evidence for decisions. When the update_wbs command detects that a task took significantly more commits than expected, it asks about the complexity increase rather than assuming the estimate was wrong.

This evidence-based approach ensures that your documentation reflects reality, not wishful thinking.

### Maintaining Project Coherence

As projects grow, they often lose coherence. Features drift from original objectives. Architecture evolves without updating documentation. Team members work from outdated assumptions.

Spec-Driven Development maintains coherence through systematic updates. Your Project Charter remains aligned with what you actually built. Your architecture documentation reflects real implementation. Your task breakdown shows actual complexity. This coherence makes it easier to onboard team members, make decisions, and plan future work.

## Starting a New Project (Greenfield)

### Business Foundation Phase

#### Project Charter: Setting Vision

The Project Charter is your north star. It establishes the business vision, identifies stakeholders, and defines success metrics. This isn't a technical document. It focuses entirely on business outcomes and strategic objectives.

To create a Project Charter, use the `/project_charter` command. The AI will engage you in a consultation that explores your business vision, market understanding, and success criteria. This isn't a form to fill out. It's an intelligent conversation that helps clarify your thinking.

The consultation covers essential topics like target market, competitive landscape, resource constraints, and risk assessment. The AI asks follow-up questions to dive deeper into areas that need clarification. For example, if you mention cost reduction as an objective, it might ask about specific cost categories and reduction targets.

The resulting document lives in `ai_docs/context/core_docs/project_charter.md`. It becomes the business foundation for all subsequent specifications.

#### Product Requirements: What to Build

With your business vision clear, the Product Requirements Document (PRD) defines what you'll build to achieve that vision. The PRD translates business objectives into specific features, user stories, and acceptance criteria.

Use the `/prd` command to start the PRD consultation. The AI builds on insights from your Project Charter, asking about user personas, user journeys, functional requirements, and non-functional requirements. This process ensures that every requirement traces back to a business objective.

The PRD consultation explores edge cases, error scenarios, and data requirements that developers often overlook. It helps you think through the full user experience, not just the happy path. The result is a comprehensive requirements document that guides implementation without constraining creativity.

Your PRD lives in `ai_docs/context/core_docs/prd.md` and becomes the definitive source for what your system should do.

#### Architecture Design: How to Build

The Architecture Design Document (ADD) translates requirements into technical architecture. This is where you make decisions about system topology, technology stack, data flow, and integration patterns.

The `/architecture_design` command initiates a technical consultation that explores different architectural approaches. The AI helps you think through trade-offs between centralized and distributed systems, synchronous and asynchronous communication, and build versus buy decisions.

This consultation goes deep into technical details while maintaining focus on business requirements. If your PRD requires sub-second response times, the architecture consultation explores caching strategies, database optimization, and CDN usage. If you need to integrate with external systems, it discusses API patterns, error handling, and data synchronization.

The ADD in `ai_docs/context/core_docs/add.md` becomes your technical blueprint, ensuring all developers understand the system architecture.

#### Work Breakdown: Tasks and Complexity

The Work Breakdown Structure (WBS) transforms your architecture into actionable tasks. This isn't just a todo list. It's a structured decomposition of work with complexity ratings, dependencies, and sequencing.

Use `/wbs` to create your initial task breakdown. The AI analyzes your PRD and ADD to suggest logical task groupings and sequences. It focuses on complexity rather than time estimates, recognizing that AI-assisted development changes traditional estimation models.

Each task receives a complexity rating of Low, Medium, or High. These ratings help you plan sprints, allocate resources, and identify risks. The WBS also captures dependencies between tasks, ensuring you build features in the right order.

Your WBS in `ai_docs/context/core_docs/wbs.md` becomes a living document that tracks project progress.

### Development Phase

#### Task Specifications

With your WBS defined, you need detailed specifications for each task. Task specifications provide implementation-level details that guide AI code generation without constraining implementation choices.

The `/task_spec` command creates specifications from WBS items. It extracts context from your PRD and ADD, then asks specific questions about implementation constraints, success criteria, and integration requirements. This ensures that whoever implements the task (human or AI) has clear guidance.

Task specifications live in `ai_docs/specs/` and follow a consistent template that includes context, requirements, constraints, success criteria, and examples.

#### Writing Code with Specs

When you're ready to implement, specifications guide AI code generation. Instead of asking AI to "build a user authentication system," you provide the detailed specification that defines exactly what authentication means for your project.

This specification-driven approach produces code that matches your requirements on the first try. The AI doesn't guess whether you want JWT or session-based authentication because your specification makes it clear. It doesn't assume you need email verification because your specification explicitly states whether you do.

Following the conventions documented in CLAUDE.md files ensures your generated code fits naturally into the existing codebase. The AI reads these files to understand naming patterns, import styles, and architectural patterns specific to your project.

#### Continuous Updates

Development reveals new requirements, technical constraints, and better solutions. The `/update_wbs` command helps track these changes systematically. It analyzes your git commits to detect work that doesn't match WBS tasks, complexity increases, and new dependencies.

This isn't a manual status update. The command examines actual development artifacts and asks targeted questions. If it detects multiple commits fixing issues in a "Low" complexity task, it might ask whether the complexity should be increased. If it finds new files without corresponding WBS tasks, it asks about the additional work.

These updates maintain accurate project status while building a history of decisions and changes. Your WBS becomes a living document that reflects reality, not just initial plans.

## Working with Existing Projects (Brownfield)

### Gathering Essential Documentation

When joining an existing project, you need the same specifications that guide new development, but the approach differs. Most existing projects weren't built with spec-driven development, so you'll need to gather or create documentation strategically.

#### Project Charter

A Project Charter is helpful but not essential for brownfield development. If your client or product management has one, request it to understand the business vision. However, don't create one yourself unless you're wearing the product owner hat. Your focus should be on implementation, not defining business strategy.

#### Product Requirements Document (Essential)

You absolutely need a PRD to understand what you're building or modifying. Request this from:

- Product Management (primary source)
- Client stakeholders
- Senior engineers on the team

Without a PRD, you're coding blind. If stakeholders can't provide one, escalate this gap. As an engineer, you shouldn't write the PRD unless you're explicitly wearing the product owner hat. The PRD defines what users need, which requires product expertise and stakeholder alignment.

#### Architecture Design Document (Essential)

Understanding system architecture is critical before making changes. Request the ADD from:

- Engineering Lead or Architect
- Senior engineers familiar with the system
- Client technical contacts

If no ADD exists, you can generate one using the `/update_add` command. This analyzes the existing codebase to detect architectural patterns, then asks you targeted questions about design decisions. This reverse-engineering approach documents the current system for future developers.

#### Work Breakdown Structure (Essential)

You need to understand planned work and dependencies. Request the WBS from:

- Engineering Lead
- Project Management
- Team members working on related features

If no WBS exists, generate one using the `/wbs` command based on the PRD and your understanding of required work. This helps organize your implementation approach.

#### Implementation Plan (Essential)

Even if the team provides high-level plans through Jira or other project management tools, create your own detailed implementation plan using spec-driven development. The `/task_spec` command helps you:

- Break down Jira tickets into detailed specifications
- Clarify ambiguous requirements
- Define success criteria
- Document implementation constraints

This detailed planning ensures AI generates code that matches requirements, not assumptions.

### Understanding the Existing Codebase

#### Reading Existing Documentation

Start by looking for any existing documentation:

```bash
# Find documentation files
find . -type f -name "*.md" | grep -E "(README|DESIGN|ARCHITECTURE|API)"

# Check for CLAUDE.md files (if the project uses them)
find . -name "CLAUDE.md" -type f

# Look for wiki or docs directories
ls -la docs/ wiki/ documentation/ 2>/dev/null
```

#### Analyzing Code Structure

Without documentation, analyze the codebase systematically:

```bash
# Understand project structure
tree -d -L 3 -I 'node_modules|__pycache__|.git'

# Find main entry points
find . -name "main.*" -o -name "app.*" -o -name "index.*" | grep -v node_modules

# Identify key services or modules
find . -type d -name "*service*" -o -name "*controller*" -o -name "*model*"
```

#### Creating Missing Documentation

For critical missing documentation, use intelligent update commands:

```bash
# Generate architecture documentation from code
/update_add "Analyze existing system architecture"

# Create WBS from existing code structure
/wbs "Create task breakdown for planned feature additions"
```

These commands analyze the codebase and ask specific questions to help document what exists.

### Making Changes

#### Targeted Specifications

When adding features to existing projects, you don't need to specify the entire system. Create targeted specifications for just the new functionality while respecting existing patterns and constraints.

The `/task_spec` command works perfectly for incremental development. It extracts context from existing documentation and code, then helps you specify new features that integrate smoothly. This ensures new code follows established patterns while meeting new requirements.

#### Intelligent Updates

After implementing changes, update commands help maintain documentation accuracy. The `/update_prd` command detects when implemented features differ from documented requirements and asks about the changes. The `/update_add` command identifies new architectural patterns and asks about their purpose.

These updates happen through targeted questions based on evidence, not generic forms. If the update command detects a new caching layer, it asks specifically about caching strategy and invalidation patterns. If it finds new API endpoints, it asks about their purpose and authentication requirements.

## The Update Cycle

### During Development

#### WBS Updates

The `/update_wbs` command should run regularly during development. By default, it analyzes the last two days of commits, though you can specify a different range. This frequent analysis catches drift between planned and actual work before it becomes a problem.

The command detects several patterns that indicate WBS updates are needed. Multiple commits to the same file suggest increased complexity. New files without WBS tasks indicate unplanned work. TODO comments reveal discovered requirements. Each pattern triggers specific questions to understand what changed and why.

Regular WBS updates provide accurate project status, reveal hidden complexity, and document decisions. They transform the WBS from a static plan into a dynamic project management tool.

#### PRD Evolution

Requirements evolve as you build and learn. The `/update_prd` command helps track this evolution systematically. It analyzes WBS changes to identify requirement impacts, then asks targeted questions about requirement modifications.

For example, if WBS tasks related to authentication increased in complexity, the update command might ask whether authentication requirements need clarification. If new tasks appeared for error handling, it might ask about reliability requirements. This approach ensures requirements stay aligned with implementation reality.

### Major Milestones

#### Architecture Updates

At major milestones, the `/update_add` command documents how architecture evolved during implementation. It analyzes the codebase to detect architectural patterns, technology choices, and integration approaches, then asks about the rationale behind changes.

This isn't about documenting every class and function. It focuses on significant architectural decisions that future developers need to understand. If you switched from REST to GraphQL, the command detects this and asks why. If you added a caching layer, it asks about performance requirements that drove this decision.

#### Charter Reflection

When projects reach completion or major milestones, the `/update_project_charter` command helps assess business outcomes. It analyzes all documentation to understand what was built versus what was planned, then asks about business impact.

This reflection focuses on outcomes executives care about. Did you achieve the cost reduction targets? How did users respond to the solution? What market opportunities emerged? The updated charter becomes a historical record that informs future projects.

## Power Techniques

### Evidence-Based Workflow

#### Let AI Analyze First

The most powerful aspect of our update commands is their ability to analyze before asking questions. Instead of presenting generic questionnaires, they examine your actual code and documentation to ask relevant questions.

This analysis uses standard tools like grep, find, and git to detect patterns. The commands look for new directories that might indicate new services. They check dependencies to identify technology choices. They analyze commit patterns to understand development velocity. All this analysis happens automatically, focusing your attention on decisions that matter.

#### Targeted Consultation

Based on analysis results, update commands ask specific questions that matter for your project. If analysis reveals a new Redis dependency, the command asks about caching strategy, not whether you're using caching. If it detects new error handling patterns, it asks about reliability requirements, not whether errors should be handled.

This targeted approach respects your time while gathering essential information. Every question has a purpose based on evidence from your project.

### Context Management

#### CLAUDE.md Integration

CLAUDE.md files provide persistent context about how your code actually works. They complement specifications by documenting implementation insights that emerge during development. While specifications define what to build, CLAUDE.md explains how it actually works.

Keep CLAUDE.md files focused on non-obvious behaviors and critical insights. Don't document what someone can understand by reading the code. Do document why certain patterns exist, what gotchas to avoid, and how components integrate.

#### Document Evolution

All core documents evolve through in-place updates that preserve history. When requirements change, the PRD shows both original and updated requirements with explanations. When architecture evolves, the ADD documents both planned and actual architecture with rationale.

This evolutionary approach maintains context while reflecting reality. Future developers can understand not just the current state, but how and why it evolved. This historical context proves invaluable for making future decisions.

## Conclusion

Spec-Driven Development transforms AI from an unpredictable assistant into a powerful amplifier of developer intent. By creating clear specifications, maintaining them through intelligent updates, and preserving decision history, you maintain control while leveraging AI's implementation speed.

The methodology works because it respects both human creativity and AI capability. Humans excel at understanding business needs, making architectural decisions, and evaluating trade-offs. AI excels at implementing specifications, analyzing code patterns, and maintaining consistency. Spec-Driven Development combines these strengths systematically.

Start with a clear business vision in your Project Charter. Define requirements comprehensively in your PRD. Design architecture thoughtfully in your ADD. Break down work systematically in your WBS. Specify tasks precisely for implementation. Update intelligently as you learn. The result is software that matches your vision, built efficiently with AI assistance.
