# Transformation Rules Guide

This document describes the transformation rules and the 5-phase pipeline used by the DevTeam Runner Service to convert raw `task_context` data into a standardized `StatusProjection` object. This process ensures consistency, robustness, and backward compatibility across various `task_context` schema variations.

## 1. Overview of the Transformation Pipeline

The `project_status_from_task_context` function, located in [`app/schemas/status_projection_schema.py`](app/schemas/status_projection_schema.py), orchestrates the transformation process through a series of five distinct phases. Each phase has specific responsibilities, error handling, and logging mechanisms.

The 5-phase pipeline is as follows:

1.  **INPUT_VALIDATION**: Validate `task_context` structure and types.
2.  **DATA_EXTRACTION**: Extract fields with fallback mechanisms, handling naming conventions and nested structures.
3.  **BUSINESS_LOGIC**: Calculate overall status, progress, and derived fields.
4.  **OUTPUT_GENERATION**: Create the `StatusProjection` object.
5.  **FINALIZATION**: Performance logging and correlation tracking.

## 2. Detailed Transformation Phases and Rules

### 2.1. Phase 1: INPUT_VALIDATION

This initial phase ensures that the incoming `task_context` is in a usable format before any processing begins.

*   **Purpose:** To validate the basic structure and types of the `task_context` and essential identifiers.
*   **Validation Rules:**
    *   `execution_id` must be a non-empty string.
    *   `project_id` must be a non-empty string.
    *   `task_context` itself must not be `None`.
    *   `task_context` must be a dictionary.
*   **Error Handling:** Raises `InvalidTaskContextError` for any validation failures in this phase.
*   **Logging:** Logs the start and success of the validation phase, including input data summary.

### 2.2. Phase 2: DATA_EXTRACTION

This phase focuses on safely extracting raw data from the `task_context`, accommodating various schema variations.

*   **Purpose:** To extract `metadata` and `nodes` dictionaries from the `task_context` and handle potential malformed structures gracefully.
*   **Extraction Logic:**
    *   **Metadata Extraction:** Attempts to retrieve the `metadata` dictionary from `task_context.get('metadata', {})`. If `metadata` is not a dictionary, a degraded operation is logged, and an empty dictionary is used as a fallback.
    *   **Nodes Extraction:** Attempts to retrieve the `nodes` dictionary from `task_context.get('nodes', {})`. If `nodes` is not a dictionary, a degraded operation is logged, and an empty dictionary is used as a fallback.
    *   **Field Fallback Mechanisms (`_safe_get_field_with_fallbacks`):** This utility function is used extensively to extract fields from `metadata` and `nodes`, supporting both `snake_case` and `camelCase` naming conventions. It tries multiple field names in a specified order (e.g., `task_id`, then `taskId`) and returns a default value if none are found.
        ```python
        # Example from _safe_get_field_with_fallbacks
        def _safe_get_field_with_fallbacks(data: Any, *field_names: str, default: Any = None) -> Any:
            if not isinstance(data, dict):
                return default
            for field_name in field_names:
                if field_name in data:
                    return data[field_name]
            return default
        ```
    *   **Node Status Extraction (`_safe_get_node_status`):** This utility handles different node structures:
        *   Direct `status` field: `{"status": "completed"}`
        *   Nested `event_data`: `{"event_data": {"status": "completed"}}`
        It returns `None` if the status cannot be reliably extracted.
        ```python
        # Example from _safe_get_node_status
        def _safe_get_node_status(node: Any) -> Optional[str]:
            if not isinstance(node, dict):
                return None
            status = node.get('status')
            if status is not None:
                return str(status) if status else None
            event_data = node.get('event_data')
            if isinstance(event_data, dict):
                nested_status = event_data.get('status')
                if nested_status is not None:
                    return str(nested_status) if nested_status else None
            return None
        ```
*   **Error Handling:** Raises `FieldExtractionError` if critical fields cannot be extracted. Logs degraded operations for non-critical issues.
*   **Logging:** Logs the start and success of the extraction phase, including summaries of extracted metadata keys and node counts.

### 2.3. Phase 3: BUSINESS_LOGIC (Status Calculation)

This phase applies business rules to determine the overall execution status and progress based on the extracted node data.

*   **Purpose:** To calculate the `status`, `progress`, and `TaskTotals` for the `StatusProjection`.
*   **Status Calculation Rules (`_process_nodes_single_pass`):**
    *   Iterates through all `nodes` to count `completed` nodes and detect `error` or `running` statuses.
    *   **Overall Status Derivation:**
        *   If any node has an `error` status, the overall status is `ERROR`.
        *   If all nodes are `completed`, the overall status is `COMPLETED`.
        *   If any node is `running` or at least one node is `completed` (and not all are completed), the overall status is `RUNNING`.
        *   Otherwise, the status defaults to `IDLE`.
    *   **Metadata Status Override:** If `metadata.status` is "prepared" and the derived status is `IDLE`, the status is overridden to `INITIALIZING`.
    *   **Status Enum Validation (`_validate_status_value`):** Ensures that the derived status is a valid `ExecutionStatus` enum member. Invalid values default to `IDLE` with a warning log.
*   **Progress Calculation Methodology:**
    *   `progress = (completed_nodes / total_nodes) * 100.0`.
    *   Handles `ZeroDivisionError` by setting progress to `0.0` if `total_nodes` is zero.
    *   Clamps progress to the `0.0-100.0` range if an invalid value is calculated, logging a degraded operation.
*   **Customer ID Extraction from `project_id` patterns:**
    *   If `project_id` is in the format "customer-id/project-id", the part before the first `/` is extracted as `customer_id`.
    *   Gracefully handles cases where `project_id` is not a string or does not contain `/`.
*   **Error Handling:** Raises `StatusCalculationError` for critical calculation failures. Logs degraded operations for issues like invalid progress values.
*   **Logging:** Logs the start and success of the calculation phase, including completed/total nodes, derived status, and progress. Performance metrics related to node processing are also logged.

### 2.4. Phase 4: OUTPUT_GENERATION (Serialization)

This phase assembles the extracted and calculated data into the final `StatusProjection` object.

*   **Purpose:** To construct `ExecutionArtifacts`, `TaskTotals`, and parse timestamps, then create the `StatusProjection` instance.
*   **Field Composition:**
    *   `current_task`: Extracted from `metadata.task_id` or `metadata.taskId`.
    *   `customer_id`: Derived from `project_id` (e.g., "customer-123" from "customer-123/project-abc").
    *   `branch`: Extracted from `metadata.branch`.
    *   `artifacts`: Composed using `ExecutionArtifacts` schema, extracting `repo_path`, `branch`, `logs`, and `files_modified` from `metadata` with fallbacks.
    *   `totals`: Composed using `TaskTotals` schema, using `completed_nodes` and `total_nodes` from the calculation phase.
    *   `started_at`: Extracted from `metadata.started_at` or `metadata.startedAt` and parsed into a `datetime` object. Handles various string formats and `None` values.
*   **Type Conversion Rules and Validation:** Pydantic models (`StatusProjection`, `TaskTotals`, `ExecutionArtifacts`) automatically handle type conversion and enforce validation rules defined in [`app/schemas/status_projection_schema.py`](app/schemas/status_projection_schema.py).
*   **Default Value Handling:** Missing optional fields are assigned default values (e.g., empty lists for `logs` and `files_modified`, `None` for `branch` if not found).
*   **Error Handling:** Raises `FieldExtractionError` if critical fields for `StatusProjection` cannot be serialized. Logs degraded operations if sub-schemas like `ExecutionArtifacts` or `TaskTotals` fail Pydantic validation, using default instances instead.
*   **Logging:** Logs the start and success of the serialization phase, including summaries of extracted fields.

### 2.5. Phase 5: FINALIZATION (Persistence/Creation)

The final phase involves creating the `StatusProjection` object and logging the overall transformation outcome.

*   **Purpose:** To instantiate the `StatusProjection` Pydantic model and log the complete transformation process.
*   **Process:**
    *   Instantiates `StatusProjection` with all gathered and calculated fields.
    *   Logs any detected node-specific errors.
    *   Logs the total duration of the transformation.
*   **Error Handling:** Raises `TaskContextTransformationError` if the final `StatusProjection` object fails Pydantic validation. Includes detailed validation errors in the exception context.
    *   **Ultimate Fallback:** In case of any unexpected `Exception` during the entire transformation, a minimal `StatusProjection` with `ExecutionStatus.ERROR` is returned to ensure the system never crashes, logging a degraded operation. This ensures backward compatibility and system resilience.
*   **Logging:** Logs the success of the final phase, including the overall execution ID, project ID, status, and total duration. Performance metrics for the entire transformation are also recorded.

## 3. Example Transformation Flow

Consider a `task_context` with a `camelCase` metadata field and a nested `event_data` node:

```json
{
  "metadata": {
    "taskId": "1.2.3",
    "projectId": "customer-456/project-xyz",
    "repoPath": "/workspace/repos/project-xyz",
    "startedAt": "2025-01-17T10:00:00Z"
  },
  "nodes": {
    "fetch": {"status": "completed"},
    "analyze": {"event_data": {"status": "running"}},
    "report": {"status": "idle"}
  }
}
```

**Transformation Steps:**

1.  **INPUT_VALIDATION:** `task_context`, `execution_id`, `project_id` are validated.
2.  **DATA_EXTRACTION:**
    *   `metadata` and `nodes` dictionaries are extracted.
    *   `metadata.taskId` is recognized and mapped.
    *   `nodes.analyze.event_data.status` is correctly extracted.
3.  **BUSINESS_LOGIC:**
    *   `completed_nodes = 1` (fetch)
    *   `total_nodes = 3`
    *   `derived_status = RUNNING` (due to 'analyze' node)
    *   `progress = (1/3) * 100 = 33.33`
    *   `customer_id = "customer-456"` (from `projectId`)
4.  **OUTPUT_GENERATION:**
    *   `current_task = "1.2.3"`
    *   `branch = None` (not in `metadata`)
    *   `artifacts = ExecutionArtifacts(repo_path="/workspace/repos/project-xyz", ...)`
    *   `totals = TaskTotals(completed=1, total=3)`
    *   `started_at = datetime.fromisoformat("2025-01-17T10:00:00Z")`
5.  **FINALIZATION:** A `StatusProjection` object is successfully created and returned.

This robust pipeline ensures that the system can reliably process diverse `task_context` inputs and maintain a consistent view of execution status.