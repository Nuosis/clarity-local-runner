# Generate LLM Prompt

READ the prompt template specification in `ai_docs/context/prompt_template.md`.
UNDERSTAND the XML-based structure and best practices for creating high-quality, reusable prompts.

Your task is to create a structured prompt for the following use case:

$ARGUMENTS

## Process

1. **Analyze the Requirements**
   - What specific task should the LLM perform?
   - What inputs will it receive?
   - What outputs are expected?
   - What constraints or guardrails are needed?

2. **Define the Role Component**
   - What expertise should the LLM embody?
   - What domain knowledge is required?
   - What professional perspective should it take?

3. **Structure the Purpose**
   - Main objective statement
   - Analytical framework with numbered categories
   - Specific capabilities and deliverables

4. **Design the Task Flow**
   - Break down into clear, numbered steps
   - Include validation and quality checks
   - Make each step actionable and measurable

5. **Create Comprehensive Examples**
   - Basic positive cases
   - Edge cases with context
   - Invalid input scenarios
   - Progress from simple to complex

6. **Define Output Format**
   - Strict formatting requirements
   - Field-by-field specifications
   - Validation rules and constraints

7. **Add Guardrails**
   - Format compliance rules
   - Quality assurance checks
   - Scope limitations
   - Safety considerations

## Output Requirements

Generate a complete prompt following the XML template structure that:

- Uses clear `<role>`, `<purpose>`, `<task_description>` tags
- Includes relevant `<examples>` covering various scenarios
- Specifies exact `<output_format>` with validation rules
- Contains appropriate `<guardrails>` for quality control
- Uses `{{variable_name}}` placeholders for runtime values

## Save Location

Once generated, save the prompt to:

- Default: `app/prompts/<descriptive_name>.j2`
- Or as specified by the user

Include frontmatter metadata:

```yaml
---
description: [Brief description of what this prompt does]
author: [Author name or "AI-Generated"]
version: 1.0.0
tags: [relevant, tags, for, categorization]
---
```

Remember: The goal is to create a reusable, well-structured prompt that minimizes ambiguity and maximizes output quality.
