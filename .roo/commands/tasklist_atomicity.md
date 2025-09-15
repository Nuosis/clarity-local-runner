You are given a generated tasklist file: `ai_docs/tasks/tasks_list.md`.  
This tasklist is derived from reference documents:  
- Project Charter (`ai_docs/context/core_docs/project_charter.md`)  
- Project Requirements (`ai_docs/context/core_docs/prd.md`)  
- Project Architecture (`ai_docs/context/core_docs/add.md`)  
- Work Breakdown Structure (`ai_docs/context/core_docs/wbs.md`)  

Your job is to **verify and refine atomicity** of every task in `tasks_list.md`.

---

## Rules

1. **Atomicity Check**
   - Review every leaf node (lowest-level numbered item).
   - Ensure each represents a single coherent action with one clear output.
   - If any task contains multiple actions (e.g., "Run tests and verify results"), split it into separate atomic actions.

2. **Reference Integrity**
   - Compare each task against the reference documents above.
   - Ensure there are no **Type I errors** (false positives: tasks not supported by references).
   - Ensure there are no **Type II errors** (false negatives: missing required tasks from references).

3. **Dependencies**
   - Preserve all existing `Dependencies:` notes at the Phase, Task, and Subtask levels.
   - If dependencies are missing or unclear, infer them logically from the reference documents.

4. **Output**
   - Maintain hierarchical numbering (`1.2.3.4`).
   - Preserve Markdown tree structure.
   - **DO NOT CREATE A NEW FILE — modify `ai_docs/tasks/tasks_list.md` in place.**

---

## Example Transformation

**Before**
3.1.2.2 Implement Stripe test environment integration testing

**After**
3.1.2.2.1 Configure Stripe test environment
3.1.2.2.2 Run integration tests against Stripe test environment