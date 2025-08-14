# Prompt Template Specification Guide

This guide provides a comprehensive template for creating high-quality, structured prompts for LLMs. Follow this specification to ensure consistency, clarity, and effectiveness in prompt design.

## Overview

Every prompt should consist of two main functions:

1. `get_instructions()` - Defines the system instructions and behavioral guidelines
2. `get_task()` - Provides the specific task context and input data

## Template Components

### 1. Role Component

**Purpose**: Establishes the AI's specialized identity and expertise domain.

**Template**:

```xml
<role>
You are a [SPECIALIST_TITLE] for [DOMAIN/ORGANIZATION]. Your expertise lies in [CORE_EXPERTISE_AREA].
</role>
```

**Guidelines**:

- Be specific about the role's specialization
- Include the domain or organizational context
- Clearly state the area of expertise
- Use professional, authoritative language

**Generic Example**:

```xml
<role>
You are a Document Classification Specialist for technical documentation systems. Your expertise lies in categorizing and organizing complex technical content based on semantic analysis and structural patterns.
</role>
```

### 2. Purpose Component

**Purpose**: Articulates the AI's mission, analytical framework, and deliverables.

**Template**:

```xml
<purpose>
[MAIN_OBJECTIVE_STATEMENT_PARAGRAPH]
 
[ANALYTICAL_FRAMEWORK_DESCRIPTION]:
 
1. [PRIMARY_ANALYSIS_CATEGORY]:
* [SPECIFIC_CAPABILITY_OR_CONSIDERATION]
* [ANOTHER_CAPABILITY_WITH_DETAILS]
* [EDGE_CASE_OR_SPECIAL_HANDLING]
* [VALIDATION_OR_QUALITY_CHECK]
 
2. [SECONDARY_ANALYSIS_CATEGORY]:
* [DETAILED_ANALYTICAL_ASPECT]
* [CONTEXTUAL_CONSIDERATION]
* [DECISION_CRITERIA]
* [OUTPUT_REQUIREMENT]
 
You provide:
* [PRIMARY_DELIVERABLE_WITH_FORMAT_SPECIFICATION]
* [SECONDARY_DELIVERABLE_WITH_CONSTRAINTS]
</purpose>
```

**Guidelines**:

- Start with a clear mission statement
- Organize capabilities into logical categories
- Use numbered lists for major categories
- Use bullet points for specific capabilities
- End with concrete deliverables
- Be explicit about output formats and constraints

### 3. Task Description Component

**Purpose**: Provides a step-by-step process for completing the analysis or generation task.

**Template**:

```xml
<task_description>
[PROCESS_OVERVIEW_SENTENCE]:
 
1. [FIRST_MAJOR_STEP_NAME]:
* [DETAILED_ACTION_OR_ANALYSIS_REQUIREMENT]
* [SPECIFIC_CONSIDERATION_OR_CHECK]
* [DATA_PROCESSING_OR_EVALUATION_STEP]
* [QUALITY_ASSURANCE_CHECKPOINT]
 
2. [SECOND_MAJOR_STEP_NAME]:
* [CONTEXTUAL_ANALYSIS_REQUIREMENT]
* [DECISION_FRAMEWORK_APPLICATION]
* [VALIDATION_OR_VERIFICATION_STEP]
* [OUTPUT_PREPARATION_CONSIDERATION]
 
[Continue with additional numbered steps as needed]
</task_description>
```

**Guidelines**:

- Start with a process overview
- Break down into clear, numbered steps
- Each step should have 3-5 specific sub-tasks
- Progress logically from input to output
- Include validation and quality checks
- Make each step actionable and measurable

### 4. Criteria/Strategy Component (Optional)

**Purpose**: Provides classification criteria, taxonomies, or strategic frameworks the AI must consider.

**Template**:

```xml
<[CRITERIA_TYPE]>
[CRITERIA_OVERVIEW_AND_PURPOSE]
 
[POSITIVE_CRITERIA_CATEGORY]:
* [SPECIFIC_INCLUSION_CRITERION]
* [ANOTHER_INCLUSION_CRITERION]
* [CONTEXTUAL_INCLUSION_RULE]
 
[NEGATIVE_CRITERIA_CATEGORY]:
* [SPECIFIC_EXCLUSION_CRITERION]
* [ANOTHER_EXCLUSION_CRITERION]
* [CONTEXTUAL_EXCLUSION_RULE]
 
[SPECIAL_CONSIDERATIONS]:
* [DOMAIN_SPECIFIC_EXCEPTION]
* [EDGE_CASE_HANDLING_RULE]
* [DISAMBIGUATION_GUIDELINE]
</[CRITERIA_TYPE]>
```

**Guidelines**:

- Use descriptive tag names (e.g., `<classification_criteria>`, `<validation_rules>`)
- Clearly separate positive and negative criteria
- Include special considerations for edge cases
- Make criteria specific and testable
- Consider domain-specific requirements

### 5. Examples Component

**Purpose**: Demonstrates expected behavior through comprehensive examples covering various scenarios.

**Template**:

```xml
<examples>
<example label="[DESCRIPTIVE_SCENARIO_TYPE]">
[OPTIONAL_CONTEXT_FIELDS]
<request>
[INPUT_DATA_OR_USER_QUERY]
</request>
<response>
[EXPECTED_OUTPUT_STRUCTURE]
</response>
</example>
</examples>
```

**Guidelines**:

- Use descriptive labels that indicate the scenario type
- Include both typical and edge cases
- Show examples with and without optional context
- Demonstrate proper output formatting
- Cover success and failure scenarios
- Progress from simple to complex examples

**Example Structure Guide**:

```xml
<examples>
<!-- Simple positive case -->
<example label="basic valid input">
<request>[SIMPLE_VALID_INPUT]</request>
<response>[EXPECTED_POSITIVE_OUTPUT]</response>
</example>
 
<!-- Edge case with context -->
<example label="edge case with context">
<optional_context>[CONTEXTUAL_INFORMATION]</optional_context>
<request>[EDGE_CASE_INPUT]</request>
<response>[APPROPRIATE_EDGE_CASE_OUTPUT]</response>
</example>
 
<!-- Negative case -->
<example label="invalid input scenario">
<request>[INVALID_INPUT]</request>
<response>[EXPECTED_REJECTION_OUTPUT]</response>
</example>
</examples>
```

### 6. Output Format Component

**Purpose**: Defines strict formatting requirements and validation rules for AI responses.

**Template**:

```xml
<output_format>
Your response must strictly follow this format:
---------------------------------------------------
<response>
<field_1>[FIELD_1_CONTENT - INCLUDE CATEGORICAL OPTIONS IF APPLICABLE]</field_1>
<field_2>[FIELD_2_CONTENT - INCLUDE CATEGORICAL OPTIONS IF APPLICABLE]</field_2>
<!-- Add more fields as necessary -->
</response>
---------------------------------------------------
 
<format_rules>
1. [FIELD_NAME] Rules:
   * [SPECIFIC_FORMAT_REQUIREMENT]
   * [CONTENT_CONSTRAINT]
   * [VALIDATION_RULE]
   * [STYLE_GUIDELINE]
 
2. [ANOTHER_FIELD_NAME] Rules:
   * [FORMAT_SPECIFICATION]
   * [CONTENT_REQUIREMENT]
   * [LENGTH_CONSTRAINT]
   * [QUALITY_STANDARD]
</format_rules>
</output_format>
```

**Guidelines**:

- Use clear visual separators
- Define each output field precisely
- Specify format, content, and length constraints
- Include validation rules
- Make requirements unambiguous
- Consider both structure and content quality

### 7. Task Input Component

**Purpose**: Structures the runtime task with specific inputs, contextual information, and operational constraints.

**Template**:

```xml
<task>
This is the input data you need to analyse:
 
[INPUT_DATA_SECTIONS]
<[input_type]>
{{variable_name}}
</[input_type]>
 
<immediate_task>
[CLEAR_CONCISE_TASK_STATEMENT]
</immediate_task>
 
[OPTIONAL_ANALYTICAL_FRAMEWORK]
<[framework_name]>
[ANALYTICAL_STEPS_OR_CONSIDERATIONS]
</[framework_name]>
 
<guardrails>
1. [FORMAT_COMPLIANCE_GUARDRAIL]
2. [QUALITY_ASSURANCE_GUARDRAIL]
3. [SCOPE_LIMITATION_GUARDRAIL]
4. [SAFETY_OR_ETHICAL_GUARDRAIL]
</guardrails>
</task>
```

**Guidelines**:

- Clearly present all input data
- State the immediate task concisely
- Include analytical frameworks when helpful
- Always include guardrails for quality control
- Use numbered guardrails for clarity
- Focus guardrails on output quality and safety

## Variable System

### Variable Types

1. **Runtime Variables**: `{{variable_name}}`
   - Replaced at execution time
   - Use for dynamic content like queries, contexts, etc.

2. **Template Placeholders**: `[PLACEHOLDER_NAME]`
   - Used in this specification for template guidance
   - Should be replaced when implementing actual prompts

## Best Practices

### Structure and Organization

1. Maintain consistent XML structure throughout
2. Use clear, descriptive tag names
3. Progress logically from general to specific
4. Keep related information grouped together

### Clarity and Precision

1. Use unambiguous language
2. Define all technical terms
3. Specify exact requirements, not approximations
4. Include measurable criteria where possible

### Completeness

1. Cover both positive and negative cases
2. Include edge cases in examples
3. Specify behavior for unexpected inputs
4. Define clear failure modes

### Output Quality

1. Enforce strict output formatting
2. Include validation rules
3. Specify length constraints where appropriate
4. Require justifications for decisions

### Flexibility

1. Use optional components where appropriate
2. Allow for domain-specific customization
3. Support both simple and complex use cases
4. Enable progressive enhancement

## Common Patterns

### Binary Classification Pattern

```xml
<output_format>
<response>
<decision>{true/false}</decision>
<justification>{CONCISE_EXPLANATION}</justification>
</response>
</output_format>
```

### Multi-Option Classification Pattern

```xml
<output_format>
<response>
<category>{CATEGORY_NAME - ONE OF: [OPTION_1, OPTION_2, OPTION_3]}</category>
<reasoning>{BRIEF_EXPLANATION}</reasoning>
</response>
</output_format>
```

## Quality Checklist

Before finalizing a prompt template, ensure:

- [ ] Role is clearly defined with specific expertise
- [ ] Purpose includes numbered capability categories
- [ ] Task description has actionable steps
- [ ] Examples cover typical and edge cases
- [ ] Output format is unambiguous
- [ ] Format rules are comprehensive
- [ ] Guardrails ensure quality and safety
- [ ] All variables are properly marked
- [ ] XML structure is consistent
- [ ] Language is clear and professional
