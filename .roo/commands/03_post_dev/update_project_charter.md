# Update Project Charter

READ the original project charter from `ai_docs/context/core_docs/project_charter.md`.
ANALYZE PRD, WBS, and ADD to understand what was actually built vs planned.
DETECT gaps between original business objectives and delivered solution.
ASK targeted questions based on evidence of change.
UPDATE the charter to reflect actual business outcomes.

Update project charter for:

$ARGUMENTS

## Intelligent Analysis Process

1. **Compare Vision to Reality**
   - Read original charter's vision and objectives
   - Analyze PRD for actual features implemented
   - Check WBS for scope changes and completed work
   - Identify divergence between planned and built

2. **Stakeholder Analysis**
   - Original charter stakeholders vs PRD personas
   - New user groups discovered during development
   - Changed priorities based on implementation

3. **Objective Achievement Detection**

   ```txt
   For each original objective:
   - Map to PRD requirements
   - Check WBS completion status
   - Identify partial or missed objectives
   - Find unexpected achievements
   ```

## Smart Consultation Based on Evidence

### When Vision Changed

If PRD shows different focus than charter:

- "Original vision was X, but PRD shows heavy focus on Y. What drove this pivot?"
- "Features A, B, C in PRD weren't in original objectives. What new opportunity emerged?"

### When Stakeholders Evolved

If PRD personas differ from charter stakeholders:

- "Charter focused on [stakeholder], but PRD shows [new persona]. When did this shift occur?"
- "The PRD user journeys suggest [stakeholder group] became primary. What validated this?"

### When Scope Changed

If WBS shows significant additions/removals:

- "WBS shows [major feature] was added mid-project. What business need drove this?"
- "Original objective X has no corresponding WBS tasks. Was this descoped? Why?"

### When Technology Impacted Business

If ADD shows architectural decisions affecting business:

- "ADD shows shift to [technology]. Did this enable new business capabilities?"
- "Architecture supports [scale/feature]. Does this change market positioning?"

## Evidence-Based Questions

Based on document analysis, ask specific questions like:

**Example 1**: Charter says "reduce support costs by 30%"

- PRD shows automation features
- Ask: "With the automation features built, what cost reduction is realistic?"

**Example 2**: Charter identifies "SMB market"

- PRD shows enterprise features
- Ask: "The features suggest enterprise focus. Has target market shifted?"

**Example 3**: Charter shows "6 month timeline"

- WBS history shows scope growth
- Ask: "Given scope expansion, what was the business impact of timeline change?"

## Update Format

```markdown
# Project Charter - [Project Name]
*Document Version: Final | Updated: [Date]*

## Executive Summary

**Original Vision**: [Preserved from original]

**Delivered Solution**: [What was actually built, based on PRD/ADD analysis]

**Key Evolution**: [Major pivots with business rationale]

## Business Objectives Assessment

### Objective 1: [Original from charter]
**Status**: [Based on PRD/WBS analysis]
**Evidence**: [Specific features/capabilities delivered]
**Business Impact**: [From developer consultation]

### Emerged Objectives [Detected from PRD/WBS]
1. **[Objective inferred from built features]**
   - Evidence: [Features/requirements that suggest this]
   - Business Driver: [From consultation]

## Stakeholder Outcomes

| Original Stakeholder | Status | Evidence | Impact |
|---------------------|---------|----------|---------|
| [From charter] | [Served/Modified/Replaced] | [PRD personas] | [Value delivered] |

## Market Position

**Original Target**: [From charter]
**Actual Focus**: [Based on PRD analysis]
**Rationale**: [From consultation]

## Success Metrics

Map original KPIs to actual capabilities:
- Metric 1: [Original] → [What's measurable with built solution]
- Metric 2: [Original] → [Adjusted based on reality]

## Risk Outcomes

Review original risks against built solution:
- Risk 1: [Mitigated/Materialized/Evolved]
- Evidence: [Architecture or features that address/reveal this]

## Strategic Impact

Based on delivered capabilities:
1. [Business opportunity from actual features]
2. [Market position from technology choices]
3. [Future potential from architecture]
```

## Critical Instructions

1. **Analyze first, ask second** - Base questions on document evidence
2. **Map objectives to features** - Connect charter goals to PRD/WBS deliverables  
3. **Infer from architecture** - ADD choices have business implications
4. **No assumptions** - Ask developer to confirm all inferences
5. **Focus on gaps** - What changed and why

## Where to Save

**ALWAYS update in place**: `ai_docs/context/core_docs/project_charter.md`

Remember: Use the actual build artifacts to ask intelligent questions about business outcomes. The charter update should reflect what was actually delivered and its business impact.
