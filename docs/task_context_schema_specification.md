# Task Context Schema Specification

This document details the various schema formats supported by the `task_context` processing system within the DevTeam Runner Service. The system is designed to be backward-compatible, handling different historical and current `task_context` structures to ensure seamless operation.

## 1. Overview

The `task_context` is a flexible JSON object embedded within an `Event` that captures the state and progress of an automation workflow. The status projection service transforms this raw `task_context` into a standardized `StatusProjection` object for consistent API responses and internal state management.

## 2. Core Structure

All `task_context` variations generally adhere to a core structure comprising `metadata` and `nodes`:

```json
{
  "metadata": {
    // Key-value pairs describing the overall task
  },
  "nodes": {
    // Key-value pairs representing individual workflow steps/nodes
  }
}
```

## 3. Supported Schema Variations

The system supports several variations in `task_context` structure and field naming. The transformation logic includes robust fallback mechanisms to handle these differences.

### 3.1. Standard DevTeam Workflow Format

This is the most common and recommended format, using `snake_case` for field names and direct status reporting within nodes.

**Example:**

```json
{
  "metadata": {
    "task_id": "1.1.1",
    "project_id": "customer-123/project-abc",
    "branch": "main",
    "repo_path": "/workspace/repos/...",
    "logs": ["Implementation started"],
    "files_modified": ["src/api.py"],
    "started_at": "2025-01-17T12:30:00+00:00"
  },
  "nodes": {
    "select": {"status": "completed", "started_at": "2025-01-17T12:30:00+00:00", "completed_at": "2025-01-17T12:35:00+00:00"},
    "prep": {"status": "running", "started_at": "2025-01-17T12:35:00+00:00"},
    "implement": {"status": "idle"}
  }
}
```

**Field Specifications:**

*   **`metadata` (object, required):** Contains high-level information about the execution.
    *   **`task_id` (string, required):** Unique identifier for the current task (e.g., "1.1.1").
    *   **`project_id` (string, required):** Identifier for the project (e.g., "customer-123/project-abc"). Used to derive `customer_id`.
    *   **`branch` (string, optional):** The Git branch associated with the execution.
    *   **`repo_path` (string, optional):** Absolute path to the repository in the workspace.
    *   **`logs` (array of strings, optional):** A list of log entries related to the execution.
    *   **`files_modified` (array of strings, optional):** A list of files modified during the execution.
    *   **`started_at` (string, optional):** ISO 8601 timestamp when the execution started.
    *   **`status` (string, optional):** Overall status of the execution (e.g., "prepared"). If present, can influence the derived `StatusProjection` status.
    *   **`completed_at` (string, optional):** ISO 8601 timestamp when the execution completed.
*   **`nodes` (object, required):** Contains the status of individual workflow nodes.
    *   Each key represents a node identifier (e.g., "select", "prep", "implement").
    *   Each value is an object containing:
        *   **`status` (string, required):** The status of the individual node (e.g., "idle", "running", "completed", "error").
        *   **`started_at` (string, optional):** ISO 8601 timestamp when the node started.
        *   **`completed_at` (string, optional):** ISO 8601 timestamp when the node completed.

### 3.2. CamelCase Variation

This variation uses `camelCase` for field names within the `metadata` section. The transformation logic automatically maps these to their `snake_case` equivalents.

**Example:**

```json
{
  "metadata": {
    "taskId": "1.1.1",
    "projectId": "customer-123/project-abc",
    "startedAt": "2025-01-17T12:30:00+00:00"
  },
  "nodes": {
    "select": {"status": "completed"}
  }
}
```

**Key Differences:**

*   `metadata.taskId` maps to `StatusProjection.current_task` (derived from `task_id`).
*   `metadata.projectId` maps to `StatusProjection.project_id`.
*   `metadata.repoPath` maps to `StatusProjection.artifacts.repo_path`.
*   `metadata.filesModified` maps to `StatusProjection.artifacts.files_modified`.
*   `metadata.startedAt` maps to `StatusProjection.started_at`.

### 3.3. Nested `event_data` Variation

In some older or specific `task_context` formats, the node status might be nested within an `event_data` object. The transformation function is designed to extract the status correctly from this structure.

**Example:**

```json
{
  "metadata": {
    "task_id": "1.1.1",
    "project_id": "customer-123/project-abc"
  },
  "nodes": {
    "select": {
      "event_data": {"status": "completed", "timestamp": "2025-01-17T12:35:00+00:00"}
    }
  }
}
```

**Key Differences:**

*   The `status` field for a node is found at `nodes.<node_id>.event_data.status`.
*   Other fields like `started_at` or `completed_at` might also be nested within `event_data` or directly under the node. The transformation prioritizes direct fields, then falls back to `event_data`.

## 4. Field Naming Conventions

The system primarily uses `snake_case` for internal `StatusProjection` fields and API responses. However, the `_safe_get_field_with_fallbacks` utility in [`app/schemas/status_projection_schema.py`](app/schemas/status_projection_schema.py) ensures that both `snake_case` and `camelCase` variations from the raw `task_context` are correctly extracted.

**Examples of handled conventions:**

*   `task_id` (snake_case) / `taskId` (camelCase)
*   `project_id` (snake_case) / `projectId` (camelCase)
*   `repo_path` (snake_case) / `repoPath` (camelCase)
*   `files_modified` (snake_case) / `filesModified` (camelCase)
*   `started_at` (snake_case) / `startedAt` (camelCase)

## 5. Required vs. Optional Fields

The `StatusProjection` schema defines which fields are strictly required and which are optional. The transformation process attempts to extract all fields, providing default values or `None` for missing optional fields to ensure a valid `StatusProjection` object is always produced.

**Required fields for `StatusProjection`:**

*   `execution_id`
*   `project_id`
*   `status`
*   `progress`
*   `totals`

**Optional fields for `StatusProjection`:**

*   `current_task`
*   `customer_id`
*   `branch`
*   `artifacts`
*   `started_at`
*   `updated_at`

## 6. Metadata Field Specifications and Extraction Rules

The `metadata` block in `task_context` is crucial for extracting high-level execution details.

*   **`task_id` / `taskId`:** Extracted as `current_task` in `StatusProjection`.
*   **`project_id` / `projectId`:** Extracted as `project_id` in `StatusProjection`. Also used to derive `customer_id` (the part before the first `/`).
*   **`branch`:** Extracted as `branch` in `StatusProjection` and `ExecutionArtifacts`.
*   **`repo_path` / `repoPath`:** Extracted as `artifacts.repo_path`.
*   **`logs`:** Extracted as `artifacts.logs`. Defaults to an empty list if not present.
*   **`files_modified` / `filesModified`:** Extracted as `artifacts.files_modified`. Defaults to an empty list if not present.
*   **`started_at` / `startedAt`:** Extracted as `started_at` in `StatusProjection`. Timestamps are parsed into `datetime` objects.
*   **`status`:** If present in `metadata`, it can influence the overall `StatusProjection.status`, especially for initial states like "prepared" mapping to `INITIALIZING`.

The extraction logic prioritizes robustness, using `_safe_get_field_with_fallbacks` to handle various naming conventions and gracefully manage missing fields.