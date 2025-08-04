# Generate Engineering Specification

READ the spec template in `ai_docs/context/specs_template.md`.
READ the project blueprint architecture in `ai_docs/context/genai_launchpad_workflow_architecture.md` to guide your implementation plan and ensure it aligns with the overall project structure.
USE your UNDERSTANDING of the spec template to create a specification for this request:

$ARGUMENTS

## Process

1. **Analyze the request thoroughly** to identify ALL ambiguities, unclear requirements, and implicit assumptions.

2. **Ask clarifying questions** - as many as needed to eliminate assumptions. Scale the number of questions with task complexity. Do not proceed until you have complete clarity.

3. **Ask follow-up questions** based on the answers received. New ambiguities often emerge from initial answers.

4. **Generate the specification** only when you can implement the feature without any further clarification.

5. Store the final specification in `ai_docs/specs/` with a descriptive filename based on the task.

## Critical Rules

- Never make assumptions about behavior, scope, or implementation details.
- If something could be interpreted multiple ways, ask which interpretation is correct.
- Continue asking questions across multiple rounds until achieving complete clarity.
- The final spec must be detailed enough that any developer could implement it without further questions.

## Escape Clause

If you're instructed to generate a specification without asking any more clarification questions (or if instructed to to so from the beginning), you can use your best judgment to fill in the gaps, but you must clearly document all assumptions made in the specification.
