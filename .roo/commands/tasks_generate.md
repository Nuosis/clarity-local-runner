You are given a Work Breakdown Structure (WBS) document.  {{doc}}
Your job is to expand it into a **treed tasklist** where every branch continues until it produces **atomic tasks** — each being a single coherent action with one clear output.

---

## Rules for Expansion

1. **Hierarchical Numbering**  
   - Use `1.2.3.4` style numbering for every node (Phase → Task → Subtask → Atomic Action).  
   - Preserve the WBS structure, but extend numbering down to the atomic level.  

2. **Atomic Definition**  
   - An atomic task is a **singular, indivisible action** that can be performed by one developer without further decomposition.  
   - Examples of valid atomic tasks:  
     - `Create X component in a new file New_Component.JSX`  
     - `Create a comprehensive unit test for awesome_service.py`  
     - `Ensure project builds and if not report error`  
     - `Produce issue_resolving.md file by calling error_solving MCP and printing the prompt it provides`  
     - `Test hypothesis 1 in new_error_solving.md`  

3. **Multi-Pass Refinement**  
   - Perform **multiple passes** through the WBS {{doc}} to guarantee that *all tasks are captured*.  
   - Perform **multiple passes** through the task_list.md (`ai_docs/tasks/tasks_list.md`) to guarantee that *all leaf nodes* are atomic.  
   - If any item contains more than one action, break it down further.  

4. **Dependencies**  
   - At the **Phase, Task, and Subtask levels**, include a note:  
     - `Dependencies: [list]`  
   - Use information from the WBS where available, or infer dependencies based on logical sequencing.  

5. **Validation, Verification, and Documentation**  
   - At the end of every **Task (the parent grouping of atomic actions)**, add three atomic subtasks:  
     - `Validate outputs of Task X.Y`  
     - `Verify correctness of Task X.Y against acceptance criteria`  
     - `Document results of Task X.Y in task_outcomes.md`  

6. **Output Format**  
   - Produce the tasklist as a **Markdown tree** with hierarchical numbering.  
   - Each Phase, Task, and Subtask should clearly show dependencies.  
   - Each atomic action should be a **single coherent instruction**.  

---

## Output Example
Phase 1: Setup (Dependencies: None)

1.1 Project Initialization (Dependencies: None)
1.1.1 Create repo clarity_project on GitHub
1.1.2 Initialize project with uv init in local environment
1.1.3 Configure .gitignore for Python and Node
1.1.4 Commit initial files to main branch

1.1.A Validate outputs of Task 1.1
1.1.B Verify correctness of Task 1.1 against <acceptance_criteria1>
1.1.B Verify correctness of Task 1.1 against <acceptance_criteria2>
1.1.C Document results of Task 1.1 in task_outcomes.md

Store results in `ai_docs/tasks/tasks_list.md` and `ai_docs/tasks/task_outcomes.md`