# API Field Mapping Reference

## Overview

This document provides a comprehensive guide to the field mapping between `task_context`, `StatusProjection`, and the DevTeam Automation API response. The mapping ensures consistent data transformation across the system's workflow processing pipeline.

## Field Mapping Principles

1. **Naming Conventions**
   - Internal representation uses `snake_case`
   - API response supports both `snake_case` and `camelCase`
   - Fallback mechanisms handle variations in field naming

2. **Transformation Strategy**
   - Utility function `_safe_get_field_with_fallbacks()` handles field extraction
   - Supports multiple input formats and naming conventions
   - Provides default values and type conversions

## Detailed Field Mapping

### Core Fields

| task_context Field | StatusProjection Field | API Response Field | Type | Description |
|-------------------|------------------------|-------------------|------|-------------|
| `metadata.task_id` | `execution_id` | `executionId` | `str` | Unique identifier for the execution |
| `metadata.project_id` | `project_id` | `projectId` | `str` | Fully qualified project identifier |
| `metadata.branch` | `branch` | `branch` | `str` | Current git branch |

### Status and Progress Fields

| task_context Field | StatusProjection Field | API Response Field | Type | Description |
|-------------------|------------------------|-------------------|------|-------------|
| `nodes.*.status` | `status` | `status` | `ExecutionStatus` | Current execution status |
| Calculated | `progress` | `progress` | `float` | Percentage of completion |
| Calculated | `current_task` | `currentTask` | `str` | Current active task identifier |

### Metadata and Artifacts

| task_context Field | StatusProjection Field | API Response Field | Type | Description |
|-------------------|------------------------|-------------------|------|-------------|
| `metadata.repo_path` | `artifacts.repo_path` | `artifacts.repoPath` | `str` | Repository filesystem path |
| `metadata.logs` | `artifacts.logs` | `artifacts.logs` | `List[str]` | Execution logs |
| `metadata.files_modified` | `artifacts.files_modified` | `artifacts.filesModified` | `List[str]` | Modified files during execution |

### Temporal Fields

| task_context Field | StatusProjection Field | API Response Field | Type | Description |
|-------------------|------------------------|-------------------|------|-------------|
| `metadata.started_at` | `started_at` | `startedAt` | `datetime` | Execution start timestamp |
| Calculated | `updated_at` | `updatedAt` | `datetime` | Last update timestamp |

### Totals and Aggregates

| task_context Field | StatusProjection Field | API Response Field | Type | Description |
|-------------------|------------------------|-------------------|------|-------------|
| Calculated | `totals.completed` | `totals.completed` | `int` | Number of completed tasks |
| Calculated | `totals.total` | `totals.total` | `int` | Total number of tasks |

## Transformation Examples

### Standard Workflow Transformation

```python
# Input task_context
task_context = {
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
        "select": {"status": "completed"},
        "prep": {"status": "running"}
    }
}

# Resulting StatusProjection
status_projection = StatusProjection(
    execution_id="1.1.1",
    project_id="customer-123/project-abc",
    status=ExecutionStatus.RUNNING,
    progress=50.0,
    current_task="prep",
    branch="main",
    artifacts=ExecutionArtifacts(
        repo_path="/workspace/repos/...",
        logs=["Implementation started"],
        files_modified=["src/api.py"]
    ),
    started_at=datetime(2025, 1, 17, 12, 30, 0, tzinfo=timezone.utc)
)
```

## Handling Schema Variations

1. **CamelCase Input**
   ```json
   {
     "metadata": {
       "taskId": "1.1.1",
       "projectId": "customer-123/project-abc"
     }
   }
   ```

2. **Nested Event Data**
   ```json
   {
     "metadata": {...},
     "nodes": {
       "select": {
         "event_data": {"status": "completed"}
       }
     }
   }
   ```

The transformation utility handles these variations seamlessly, extracting and mapping fields consistently.

## Performance Considerations

- Field mapping is optimized for low-latency transformations
- Minimal computational overhead
- Supports batch processing and high-throughput scenarios

## Backward Compatibility

- Maintains consistent mapping across different schema versions
- Graceful handling of missing or partial input data
- Provides default values to ensure API response integrity

## Best Practices

1. Always use the `project_status_from_task_context()` utility for transformations
2. Validate input data before transformation
3. Handle potential exceptions during mapping
4. Log any mapping inconsistencies for further investigation