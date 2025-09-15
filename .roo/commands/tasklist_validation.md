You are given the refined `ai_docs/tasks/tasks_list.md` after atomicity verification, plus reference documents:
- PRD: `ai_docs/context/core_docs/prd.md`
- Architecture (ADD): `ai_docs/context/core_docs/add.md`

Your job is to enforce **validation, verification, and documentation** for every Phase, Task, and Subtask — and to **replace generic verification** lines with a **concrete, enumerated list of acceptance criteria** extracted from the reference documents.

---

## What to Add (Idempotent)
At the end of **every Phase, Task, and Subtask**, ensure these appear **once** (no duplicates):
1. `Validate outputs of Task X.Y[.Z]`
2. `Verify correctness of Task X.Y[.Z] against acceptance criteria` **followed by** a list of **actual acceptance criteria** formatted as:
   - `<criterion 1: …>`
   - `<criterion 2: …>`
   - …
3. `Document results of Task X.Y[.Z] in task_outcomes.md`

If items 1–3 already exist:
- **Do not duplicate** them.
- For item 2, if it is present but **does not enumerate criteria**, **augment it in place** by appending the enumerated `<criterion …>` lines.
- If item 2 already has enumerated criteria, **update** the list to reflect the current PRD/ADD (add missing, remove obsolete).

**DO NOT CREATE A NEW FILE — modify `ai_docs/tasks/tasks_list.md` in place.**

---

## How to Extract Acceptance Criteria
1. **Scan PRD (primary) and ADD (secondary)** for acceptance/success criteria and explicit targets relevant to the current node’s scope and wording.
   - Examples from PRD (illustrative, not exhaustive):
     - Performance: `<200ms` quick APIs, `<2s` workflow APIs
     - Reliability/Uptime: `99.9%` uptime
     - Testing: `>90%` coverage (MVP), `>85%` technical metric elsewhere
     - Security/Compliance: PIPEDA compliance validated, security audit “no critical vulnerabilities,” RLS policies in Supabase
     - Delivery/Operations: Monitoring & alerting operational, Docker deployment on Hetzner, OpenAPI docs present
   - ADD provides architectural constraints and patterns to reference when relevant (e.g., workflow-driven orchestration, Pydantic type safety end-to-end, Redis/Celery event-driven ops).

2. **Map by relevance**:
   - If the node is about **API endpoints** → include API performance and type-safety criteria.
   - If about **workflows (enrollment, payments, scheduling)** → include workflow time targets, error handling/retry, business outcomes (e.g., payment reconciliation accuracy).
   - If about **security/auth/data** → include RLS, security audit, PIPEDA, auth validation.
   - If about **testing** → include coverage thresholds and pass/fail gates relevant to the scope.
   - If about **deployment/ops** → include Dockerization, monitoring/alerting, uptime.

3. **Be explicit and atomic**:
   - Each `<criterion …>` is a single measurable statement (one metric or pass/fail gate).
   - Prefer direct wording from PRD/ADD; if you must paraphrase, keep it precise and verifiable.

4. **No Type I / Type II Errors**:
   - **Type I (false positive):** Do not invent criteria not supported by PRD/ADD.
   - **Type II (false negative):** Do not omit applicable criteria when the node clearly relates to them.

---

## Numbering & Style
- Preserve hierarchical numbering (e.g., `2.1.3.A`, `2.1.3.B`, `2.1.3.C`).
- Keep the Markdown tree structure intact.

---

## Example Transformation (replace generic verification with enumerated criteria)

**Before**
2.1.3.A Validate outputs of Task 2.1.3
2.1.3.B Verify correctness of Task 2.1.3 against acceptance criteria from prd.md and add.md
2.1.3.C Document results of Task 2.1.3 in task_outcomes.md

**After**
2.1.3.A Validate outputs of Task 2.1.3
2.1.3.B Verify correctness of Task 2.1.3 against acceptance criteria
	•	<criterion 1: Quick API endpoints respond in <200ms at p95>  [source: PRD]>
	•	<criterion 2: Workflow-backed operations complete in <2s at p95>  [source: PRD]>
	•	<criterion 3: Type-safety enforced with end-to-end Pydantic validation; zero runtime type errors in happy-path flows>  [source: PRD/ADD]>
	•	<criterion 4: Security audit returns no critical vulnerabilities; Supabase RLS policies enforced on student/lesson/payment tables>  [source: PRD/ADD]>
	•	<criterion 5: Monitoring & alerting operational for API and workflows; error tracking enabled>  [source: PRD]>
	•	<criterion 6: PIPEDA compliance validated for stored and processed personal data>  [source: PRD]>
	•	<criterion 7: Test coverage meets or exceeds project threshold (>90% for MVP scope)>  [source: PRD]>
	•	<criterion 8: Payment reconciliation accuracy 100% for relevant payment tasks>  [source: PRD]>
2.1.3.C Document results of Task 2.1.3 in task_outcomes.md
*(Note: The concrete set chosen per node must match the node’s scope. For example, if 2.1.3 is purely about “Lesson Scheduling API,” include API performance, workflow timing (if invoked), validation/type-safety, monitoring, and security—omit payments criteria unless the node touches billing.)*


## Example Transformation (add validation criteria to an atomic task)

**Before**
2.1.3.1 Create a new file Lesson_Scheduling_API.py and implement the endpoint POST /schedule_lesson

**After**
2.1.3.1 Create a new file Lesson_Scheduling_API.py and implement the endpoint POST /schedule_lesson
2.1.3.1.A Validate outputs of Task 2.1.3.1
2.1.3.1.B Verify correctness of Task 2.1.3.1 against acceptance criteria
    • <criterion 1: Quick API endpoints respond in <200ms at p95> [source: PRD]>
    • <criterion 2: Workflow-backed operations complete in <2s at p95> [source: PRD]>
    • <criterion 3: Type-safety enforced with end-to-end Pydantic validation; zero runtime type errors in happy-path flows> [source: PRD/ADD]>
    • <criterion 4: Monitoring & alerting operational for the Lesson Scheduling API endpoint; error tracking enabled> [source: PRD]>
    • <criterion 5: PIPEDA compliance validated for stored and processed personal data> [source: PRD]>
2.1.3.1.C Document results of Task 2.1.3.1 in task_outcomes.md