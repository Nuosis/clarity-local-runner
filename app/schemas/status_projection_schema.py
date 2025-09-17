"""
Status Projection Schema Module

This module defines Pydantic schemas for status projection data structures that
project execution state from Event.task_context. The schemas provide comprehensive
validation for DevTeam automation workflow status tracking and state transitions.

The status projection models support the DevTeam automation API endpoints with
robust field validation, state transition validation, and meaningful error messages.
"""

import logging
import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator, root_validator, ValidationError

from core.exceptions import (
    TaskContextTransformationError,
    InvalidTaskContextError,
    NodeDataError,
    StatusCalculationError,
    FieldExtractionError
)
from core.structured_logging import (
    get_transformation_logger,
    TransformationPhase,
    log_performance
)

# Configure logger for status projection
logger = logging.getLogger(__name__)
transformation_logger = get_transformation_logger(__name__)


class ExecutionStatus(str, Enum):
    """Valid execution status values for DevTeam automation workflows."""
    
    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    COMPLETED = "completed"
    ERROR = "error"


class TaskTotals(BaseModel):
    """Task completion totals for progress tracking."""
    
    completed: int = Field(
        default=0,
        ge=0,
        description="Number of completed tasks"
    )
    
    total: int = Field(
        default=0,
        ge=0,
        description="Total number of tasks"
    )
    
    @validator('total')
    def validate_total_count(cls, v, values):
        """Validate total count against completed."""
        completed = values.get('completed', 0)
        if completed > v:
            raise ValueError("Completed tasks cannot exceed total tasks")
        return v
    
    class Config:
        """Pydantic configuration."""
        
        schema_extra = {
            "example": {
                "completed": 3,
                "total": 8
            }
        }


class ExecutionArtifacts(BaseModel):
    """Execution artifacts and metadata."""
    
    repo_path: Optional[str] = Field(
        default=None,
        description="Repository path in the workspace"
    )
    
    branch: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Current working branch"
    )
    
    logs: List[str] = Field(
        default_factory=list,
        description="Execution log entries"
    )
    
    files_modified: List[str] = Field(
        default_factory=list,
        description="List of files modified during execution"
    )
    
    @validator('branch')
    def validate_branch_format(cls, v):
        """Validate branch name format."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
            
            # Basic branch name validation
            import re
            if not re.match(r"^[a-zA-Z0-9_/-]+$", v):
                raise ValueError("Branch name must contain only alphanumeric characters, underscores, hyphens, and forward slashes")
        
        return v
    
    class Config:
        """Pydantic configuration."""
        
        schema_extra = {
            "example": {
                "repo_path": "/workspace/repos/customer-123-project-abc",
                "branch": "task/1-1-1-add-devteam-enabled-flag",
                "logs": ["Implementation started", "Aider tool initialized"],
                "files_modified": ["src/config.js", "README.md"]
            }
        }


class StatusProjection(BaseModel):
    """
    Status projection schema for DevTeam automation execution state.
    
    This schema projects execution state from Event.task_context following
    the ADD Section 13 format: {customerId?, projectId, status, progress, 
    currentTask, branch, artifacts}.
    
    Supports state transitions: idle→initializing→running→paused→running→completed|error
    """
    
    # Core required fields
    execution_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique execution identifier"
    )
    
    project_id: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Project identifier (e.g., 'customer-123/project-abc')"
    )
    
    status: ExecutionStatus = Field(
        ...,
        description="Current execution status"
    )
    
    progress: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Execution progress percentage (0.0-100.0)"
    )
    
    current_task: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Current task identifier (e.g., '1.1.1')"
    )
    
    totals: TaskTotals = Field(
        default_factory=TaskTotals,
        description="Task completion totals"
    )
    
    # Optional fields
    customer_id: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Customer identifier (optional)"
    )
    
    branch: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        description="Current working branch"
    )
    
    artifacts: ExecutionArtifacts = Field(
        default_factory=ExecutionArtifacts,
        description="Execution artifacts and metadata"
    )
    
    # Timestamps
    started_at: Optional[datetime] = Field(
        None,
        description="Execution start timestamp"
    )
    
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )
    
    @validator('execution_id')
    def validate_execution_id_format(cls, v):
        """Validate execution ID format."""
        if not v or not v.strip():
            raise ValueError("Execution ID cannot be empty")
        
        v = v.strip()
        
        # Validate regex pattern
        import re
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Execution ID must contain only alphanumeric characters, underscores, and hyphens")
        
        return v
    
    @validator('project_id')
    def validate_project_id_format(cls, v):
        """Validate project ID format."""
        if not v or not v.strip():
            raise ValueError("Project ID cannot be empty")
        
        v = v.strip()
        
        # Validate regex pattern
        import re
        if not re.match(r"^[a-zA-Z0-9_/-]+$", v):
            raise ValueError("Project ID must contain only alphanumeric characters, underscores, hyphens, and forward slashes")
        
        # Validate format: customer-id/project-id
        if '/' in v:
            parts = v.split('/')
            if len(parts) != 2 or not all(part.strip() for part in parts):
                raise ValueError("Project ID must be in format 'customer-id/project-id'")
        
        return v
    
    @validator('current_task')
    def validate_current_task_format(cls, v):
        """Validate current task ID format."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
            
            # Validate task ID format (e.g., '1.1.1', '2.3')
            import re
            if not re.match(r"^[0-9]+(\.[0-9]+)*$", v):
                raise ValueError("Task ID must be in format like '1.1.1' or '2.3'")
        
        return v
    
    @validator('customer_id')
    def validate_customer_id_format(cls, v):
        """Validate customer ID format if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
            
            # Basic security validation
            import re
            if not re.match(r"^[a-zA-Z0-9_-]+$", v):
                raise ValueError("Customer ID must contain only alphanumeric characters, underscores, and hyphens")
        
        return v
    
    @validator('branch')
    def validate_branch_format(cls, v):
        """Validate branch name format."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
            
            # Basic branch name validation
            import re
            if not re.match(r"^[a-zA-Z0-9_/-]+$", v):
                raise ValueError("Branch name must contain only alphanumeric characters, underscores, hyphens, and forward slashes")
        
        return v
    
    @root_validator(pre=True)
    def validate_status_consistency(cls, values):
        """Validate status consistency and state transitions."""
        status = values.get('status')
        progress = values.get('progress', 0.0)
        current_task = values.get('current_task')
        totals = values.get('totals', TaskTotals())
        
        # Status-specific validations
        if status == ExecutionStatus.IDLE:
            if progress > 0.0:
                raise ValueError("IDLE status should have 0% progress")
            if current_task is not None:
                raise ValueError("IDLE status should not have a current task")
        
        elif status == ExecutionStatus.INITIALIZING:
            if progress > 10.0:
                raise ValueError("INITIALIZING status should have minimal progress (≤10%)")
        
        elif status == ExecutionStatus.RUNNING:
            if current_task is None:
                raise ValueError("RUNNING status requires a current task")
            if progress >= 100.0:
                raise ValueError("RUNNING status should not have 100% progress")
        
        elif status == ExecutionStatus.COMPLETED:
            if progress < 100.0:
                raise ValueError("COMPLETED status requires 100% progress")
            if totals.completed < totals.total and totals.total > 0:
                raise ValueError("COMPLETED status requires all tasks to be completed")
        
        elif status == ExecutionStatus.ERROR:
            # Error status can have any progress/task state
            pass
        
        elif status == ExecutionStatus.PAUSED:
            if current_task is None:
                raise ValueError("PAUSED status requires a current task")
        
        elif status == ExecutionStatus.STOPPING:
            if current_task is None:
                raise ValueError("STOPPING status requires a current task")
        
        elif status == ExecutionStatus.STOPPED:
            # STOPPED status can have any progress/task state
            pass
        
        return values
    
    def validate_state_transition(self, from_status: ExecutionStatus) -> bool:
        """
        Validate state transition according to ADD Section 17.
        
        Valid transitions: idle→initializing→running→paused→running→completed|error
        Error can be reached from any state.
        """
        valid_transitions = {
            ExecutionStatus.IDLE: [ExecutionStatus.INITIALIZING, ExecutionStatus.ERROR],
            ExecutionStatus.INITIALIZING: [ExecutionStatus.RUNNING, ExecutionStatus.ERROR],
            ExecutionStatus.RUNNING: [ExecutionStatus.PAUSED, ExecutionStatus.STOPPING, ExecutionStatus.COMPLETED, ExecutionStatus.ERROR],
            ExecutionStatus.PAUSED: [ExecutionStatus.RUNNING, ExecutionStatus.ERROR],
            ExecutionStatus.STOPPING: [ExecutionStatus.STOPPED, ExecutionStatus.ERROR],
            ExecutionStatus.STOPPED: [ExecutionStatus.ERROR],  # Can only transition to error for cleanup
            ExecutionStatus.COMPLETED: [ExecutionStatus.ERROR],  # Can only transition to error for cleanup
            ExecutionStatus.ERROR: []  # Terminal state
        }
        
        return self.status in valid_transitions.get(from_status, [])
    
    class Config:
        """Pydantic configuration."""
        
        # Performance optimizations
        validate_assignment = True
        use_enum_values = True
        allow_population_by_field_name = True
        
        # JSON encoding configuration
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }
        
        # Schema configuration
        schema_extra = {
            "example": {
                "execution_id": "exec_12345678-1234-1234-1234-123456789012",
                "project_id": "customer-123/project-abc",
                "status": "running",
                "progress": 45.2,
                "current_task": "1.1.1",
                "totals": {
                    "completed": 3,
                    "total": 8
                },
                "customer_id": "customer-123",
                "branch": "task/1-1-1-add-devteam-enabled-flag",
                "artifacts": {
                    "repo_path": "/workspace/repos/customer-123-project-abc",
                    "branch": "task/1-1-1-add-devteam-enabled-flag",
                    "logs": ["Implementation started", "Aider tool initialized"],
                    "files_modified": ["src/config.js"]
                },
                "started_at": "2025-01-14T18:25:00Z",
                "updated_at": "2025-01-14T18:30:00Z"
            }
        }


class StatusProjectionError(BaseModel):
    """Error response schema for status projection operations."""
    
    error_code: str = Field(
        ...,
        description="Error code for programmatic handling"
    )
    
    message: str = Field(
        ...,
        description="Human-readable error message"
    )
    
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details"
    )
    
    execution_id: Optional[str] = Field(
        None,
        description="Execution ID if available"
    )
    
    class Config:
        """Pydantic configuration."""
        
        schema_extra = {
            "example": {
                "error_code": "INVALID_STATE_TRANSITION",
                "message": "Cannot transition from COMPLETED to RUNNING status",
                "details": {
                    "from_status": "completed",
                    "to_status": "running",
                    "valid_transitions": ["error"]
                },
                "execution_id": "exec_12345678-1234-1234-1234-123456789012"
            }
        }


# Helper functions for robust field extraction
def _safe_get_field_with_fallbacks(data: Any, *field_names: str, default: Any = None) -> Any:
    """
    Safely extract field value with multiple fallback field names.
    
    Handles both snake_case and camelCase field naming conventions.
    
    Args:
        data: Data structure to extract from (must be dict-like)
        *field_names: Field names to try in order (e.g., 'task_id', 'taskId')
        default: Default value if no field found
        
    Returns:
        Field value or default
    """
    if not isinstance(data, dict):
        return default
        
    for field_name in field_names:
        if field_name in data:
            return data[field_name]
    
    return default


def _safe_get_node_status(node: Any) -> Optional[str]:
    """
    Safely extract status from a node, handling various node structures.
    
    Supports:
    - Direct status field: {'status': 'completed'}
    - Nested event_data: {'event_data': {'status': 'completed'}}
    - Non-dictionary nodes (returns None)
    
    Args:
        node: Node data structure
        
    Returns:
        Status string or None if not found/invalid
    """
    if not isinstance(node, dict):
        return None
    
    # Try direct status field first
    status = node.get('status')
    if status is not None:
        return str(status) if status else None
    
    # Try nested event_data structure
    event_data = node.get('event_data')
    if isinstance(event_data, dict):
        nested_status = event_data.get('status')
        if nested_status is not None:
            return str(nested_status) if nested_status else None
    
    return None


def _validate_status_value(status_value: Any) -> ExecutionStatus:
    """
    Validate and convert status value to ExecutionStatus enum.
    
    Args:
        status_value: Status value to validate
        
    Returns:
        Valid ExecutionStatus enum value, defaults to IDLE for invalid values
    """
    if status_value is None:
        return ExecutionStatus.IDLE
    
    try:
        # Convert to string and normalize
        status_str = str(status_value).lower().strip()
        
        # Try direct enum conversion
        for status_enum in ExecutionStatus:
            if status_enum.value == status_str:
                return status_enum
        
        # Fallback to IDLE for invalid values
        logger.warning(f"Invalid status value '{status_value}', defaulting to IDLE")
        return ExecutionStatus.IDLE
        
    except (ValueError, TypeError) as e:
        logger.warning(f"Error validating status value '{status_value}': {e}, defaulting to IDLE")
        return ExecutionStatus.IDLE


def _process_nodes_single_pass(nodes: Any) -> tuple[int, int, ExecutionStatus, Optional[str]]:
    """
    Process nodes in a single pass for performance optimization.
    
    Args:
        nodes: Nodes data structure
        
    Returns:
        Tuple of (completed_count, total_count, derived_status, error_details)
    """
    if not isinstance(nodes, dict):
        logger.warning(f"Nodes is not a dictionary: {type(nodes)}, treating as empty")
        return 0, 0, ExecutionStatus.IDLE, None
    
    if not nodes:
        return 0, 0, ExecutionStatus.IDLE, None
    
    completed_count = 0
    total_count = len(nodes)
    has_error = False
    has_running = False
    error_details = None
    
    for node_name, node_data in nodes.items():
        status = _safe_get_node_status(node_data)
        
        if status == 'error':
            has_error = True
            error_details = f"Node '{node_name}' has error status"
        elif status == 'completed':
            completed_count += 1
        elif status == 'running':
            has_running = True
    
    # Determine overall status
    if has_error:
        derived_status = ExecutionStatus.ERROR
    elif completed_count == total_count:
        derived_status = ExecutionStatus.COMPLETED
    elif has_running or completed_count > 0:
        derived_status = ExecutionStatus.RUNNING
    else:
        derived_status = ExecutionStatus.IDLE
    
    return completed_count, total_count, derived_status, error_details


# Enhanced utility functions for status projection with comprehensive error handling
@log_performance(
    transformation_logger.logger,
    "task_context_transformation",
    phase=TransformationPhase.VALIDATION,
    performance_thresholds={'warning': 100, 'critical': 500, 'emergency': 1000}
)
def project_status_from_task_context(
    task_context: Dict[str, Any],
    execution_id: str,
    project_id: str,
    correlation_id: Optional[str] = None
) -> StatusProjection:
    """
    Project status from Event.task_context following ADD Section 13 format.
    
    Enhanced with comprehensive error handling, structured logging, and performance monitoring.
    This function robustly handles all known task_context schema variations including:
    - Field naming inconsistencies (snake_case vs camelCase)
    - Non-dictionary metadata and node values
    - Nested event_data structures in nodes
    - Missing optional fields
    - Invalid status enum values
    
    The function uses defensive programming patterns, comprehensive error handling,
    and structured logging to ensure it never crashes and always returns a valid StatusProjection.
    
    Args:
        task_context: The task_context from Event model (any structure)
        execution_id: Unique execution identifier
        project_id: Project identifier
        correlation_id: Optional correlation ID for distributed tracing
        
    Returns:
        StatusProjection instance with projected state
        
    Raises:
        TaskContextTransformationError: For critical transformation failures
        InvalidTaskContextError: For invalid task_context structure
        NodeDataError: For malformed node data
        StatusCalculationError: For status calculation failures
        FieldExtractionError: For field extraction failures
    """
    # Generate correlation ID if not provided
    if not correlation_id:
        correlation_id = str(uuid.uuid4())
    
    # Set transformation context for logging
    transformation_logger.set_transformation_context(
        correlation_id=correlation_id,
        execution_id=execution_id,
        task_context_size=len(str(task_context)) if task_context else 0
    )
    
    start_time = time.time()
    
    try:
        # Phase 1: Input Validation
        transformation_logger.log_transformation_start(
            TransformationPhase.VALIDATION,
            input_data_summary={
                "has_task_context": task_context is not None,
                "task_context_type": type(task_context).__name__,
                "execution_id": execution_id,
                "project_id": project_id
            }
        )
        
        # Validate input parameters
        if not execution_id or not isinstance(execution_id, str):
            raise InvalidTaskContextError(
                "execution_id must be a non-empty string",
                context={"execution_id": execution_id, "type": type(execution_id).__name__}
            )
        
        if not project_id or not isinstance(project_id, str):
            raise InvalidTaskContextError(
                "project_id must be a non-empty string",
                context={"project_id": project_id, "type": type(project_id).__name__}
            )
        
        # Validate task_context structure
        if task_context is None:
            raise InvalidTaskContextError(
                "task_context cannot be None",
                context={"task_context": None}
            )
        
        if not isinstance(task_context, dict):
            raise InvalidTaskContextError(
                f"task_context must be a dictionary, got {type(task_context).__name__}",
                context={"task_context_type": type(task_context).__name__}
            )
        
        validation_duration = (time.time() - start_time) * 1000
        transformation_logger.log_transformation_success(
            TransformationPhase.VALIDATION,
            validation_duration,
            output_summary={"validation_passed": True}
        )
        
        # Phase 2: Field Extraction
        extraction_start = time.time()
        transformation_logger.log_transformation_start(
            TransformationPhase.EXTRACTION,
            input_data_summary={
                "task_context_keys": list(task_context.keys()) if isinstance(task_context, dict) else []
            }
        )
        
        try:
            # Extract and validate metadata with comprehensive error handling
            metadata = task_context.get('metadata', {})
            if not isinstance(metadata, dict):
                transformation_logger.log_degraded_operation(
                    TransformationPhase.EXTRACTION,
                    f"Metadata is not a dictionary: {type(metadata)}",
                    "using_empty_dict",
                    "Metadata fields will be unavailable"
                )
                metadata = {}
            
            # Extract and validate nodes with comprehensive error handling
            nodes = task_context.get('nodes', {})
            if not isinstance(nodes, dict):
                transformation_logger.log_degraded_operation(
                    TransformationPhase.EXTRACTION,
                    f"Nodes is not a dictionary: {type(nodes)}",
                    "using_empty_dict",
                    "Node processing will be skipped"
                )
                nodes = {}
            
            extraction_duration = (time.time() - extraction_start) * 1000
            transformation_logger.log_transformation_success(
                TransformationPhase.EXTRACTION,
                extraction_duration,
                output_summary={
                    "metadata_keys": list(metadata.keys()) if metadata else [],
                    "nodes_count": len(nodes) if nodes else 0
                }
            )
            
        except Exception as e:
            extraction_duration = (time.time() - extraction_start) * 1000
            transformation_logger.log_transformation_error(
                TransformationPhase.EXTRACTION,
                e,
                extraction_duration,
                error_context={
                    "task_context_keys": list(task_context.keys()) if isinstance(task_context, dict) else None,
                    "metadata_type": type(task_context.get('metadata')).__name__ if 'metadata' in task_context else None,
                    "nodes_type": type(task_context.get('nodes')).__name__ if 'nodes' in task_context else None
                }
            )
            raise FieldExtractionError(
                f"Failed to extract fields from task_context: {str(e)}",
                context={
                    "task_context_keys": list(task_context.keys()) if isinstance(task_context, dict) else None,
                    "error": str(e)
                }
            ) from e
        
        # Phase 3: Status Calculation
        calculation_start = time.time()
        transformation_logger.log_transformation_start(
            TransformationPhase.CALCULATION,
            input_data_summary={
                "nodes_count": len(nodes) if nodes else 0,
                "metadata_status": metadata.get('status') if metadata else None
            }
        )
        
        try:
            # Process nodes in single pass for performance with error handling
            completed_nodes, total_nodes, derived_status, error_details = _process_nodes_single_pass(nodes)
            
            # Override status based on metadata if needed
            metadata_status = _safe_get_field_with_fallbacks(metadata, 'status')
            if metadata_status == 'prepared' and derived_status == ExecutionStatus.IDLE:
                derived_status = ExecutionStatus.INITIALIZING
            
            # Validate final status
            status = _validate_status_value(derived_status.value)
            
            # Calculate progress with error handling
            try:
                progress = (completed_nodes / total_nodes) * 100.0 if total_nodes > 0 else 0.0
                if progress < 0 or progress > 100:
                    transformation_logger.log_degraded_operation(
                        TransformationPhase.CALCULATION,
                        f"Invalid progress value: {progress}",
                        "clamping_to_valid_range",
                        "Progress will be clamped to 0-100 range"
                    )
                    progress = max(0.0, min(100.0, progress))
            except (ZeroDivisionError, TypeError, ValueError) as e:
                transformation_logger.log_degraded_operation(
                    TransformationPhase.CALCULATION,
                    f"Progress calculation failed: {str(e)}",
                    "defaulting_to_zero",
                    "Progress will be set to 0"
                )
                progress = 0.0
            
            calculation_duration = (time.time() - calculation_start) * 1000
            transformation_logger.log_transformation_success(
                TransformationPhase.CALCULATION,
                calculation_duration,
                output_summary={
                    "completed_nodes": completed_nodes,
                    "total_nodes": total_nodes,
                    "derived_status": status.value,
                    "progress": progress
                },
                performance_metrics={
                    "nodes_processed": total_nodes,
                    "processing_rate_nodes_per_ms": total_nodes / calculation_duration if calculation_duration > 0 else 0
                }
            )
            
        except Exception as e:
            calculation_duration = (time.time() - calculation_start) * 1000
            transformation_logger.log_transformation_error(
                TransformationPhase.CALCULATION,
                e,
                calculation_duration,
                error_context={
                    "nodes_count": len(nodes) if nodes else 0,
                    "metadata_status": metadata.get('status') if metadata else None
                }
            )
            raise StatusCalculationError(
                f"Failed to calculate status from nodes: {str(e)}",
                context={
                    "nodes_count": len(nodes) if nodes else 0,
                    "error": str(e)
                }
            ) from e
        
        # Phase 4: Serialization
        serialization_start = time.time()
        transformation_logger.log_transformation_start(
            TransformationPhase.SERIALIZATION,
            input_data_summary={
                "status": status.value,
                "progress": progress,
                "has_metadata": bool(metadata)
            }
        )
        
        try:
            # Extract additional fields with comprehensive error handling
            current_task = _safe_get_field_with_fallbacks(metadata, 'task_id', 'taskId')
            
            # Clear current_task if status is IDLE (business rule validation)
            if status == ExecutionStatus.IDLE:
                current_task = None
            
            # Extract customer ID from project ID with error handling
            customer_id = None
            try:
                if isinstance(project_id, str) and '/' in project_id:
                    customer_id = project_id.split('/')[0]
            except Exception as e:
                transformation_logger.log_degraded_operation(
                    TransformationPhase.SERIALIZATION,
                    f"Error extracting customer_id from project_id '{project_id}': {str(e)}",
                    "setting_to_none",
                    "Customer ID will be None"
                )
            
            # Extract branch information with fallbacks
            branch = _safe_get_field_with_fallbacks(metadata, 'branch')
            
            # Build artifacts with comprehensive error handling
            try:
                artifacts = ExecutionArtifacts(
                    repo_path=_safe_get_field_with_fallbacks(metadata, 'repo_path', 'repoPath'),
                    branch=branch,
                    logs=_safe_get_field_with_fallbacks(metadata, 'logs', default=[]),
                    files_modified=_safe_get_field_with_fallbacks(metadata, 'files_modified', 'filesModified', default=[])
                )
            except ValidationError as e:
                transformation_logger.log_degraded_operation(
                    TransformationPhase.SERIALIZATION,
                    f"Error creating ExecutionArtifacts: {str(e)}",
                    "using_defaults",
                    "Artifacts will have default values"
                )
                artifacts = ExecutionArtifacts()
            
            # Build totals with validation and error handling
            try:
                totals = TaskTotals(
                    completed=max(0, completed_nodes),
                    total=max(0, total_nodes)
                )
            except ValidationError as e:
                transformation_logger.log_degraded_operation(
                    TransformationPhase.SERIALIZATION,
                    f"Error creating TaskTotals: {str(e)}",
                    "using_defaults",
                    "Task totals will have default values"
                )
                totals = TaskTotals()
            
            # Extract timestamps with comprehensive error handling
            started_at = _safe_get_field_with_fallbacks(metadata, 'started_at', 'startedAt')
            if started_at and not isinstance(started_at, datetime):
                try:
                    if isinstance(started_at, str):
                        from dateutil.parser import parse
                        started_at = parse(started_at)
                    else:
                        started_at = None
                except Exception as e:
                    transformation_logger.log_degraded_operation(
                        TransformationPhase.SERIALIZATION,
                        f"Error parsing started_at timestamp '{started_at}': {str(e)}",
                        "setting_to_none",
                        "Started timestamp will be None"
                    )
                    started_at = None
            
            serialization_duration = (time.time() - serialization_start) * 1000
            transformation_logger.log_transformation_success(
                TransformationPhase.SERIALIZATION,
                serialization_duration,
                output_summary={
                    "current_task": current_task,
                    "customer_id": customer_id,
                    "branch": branch,
                    "has_artifacts": artifacts is not None,
                    "has_started_at": started_at is not None
                }
            )
            
        except Exception as e:
            serialization_duration = (time.time() - serialization_start) * 1000
            transformation_logger.log_transformation_error(
                TransformationPhase.SERIALIZATION,
                e,
                serialization_duration,
                error_context={
                    "metadata_keys": list(metadata.keys()) if metadata else [],
                    "project_id": project_id
                }
            )
            raise FieldExtractionError(
                f"Failed to serialize StatusProjection fields: {str(e)}",
                context={
                    "metadata_keys": list(metadata.keys()) if metadata else [],
                    "error": str(e)
                }
            ) from e
        
        # Phase 5: Final StatusProjection Creation
        creation_start = time.time()
        try:
            # Log any error details for debugging
            if error_details:
                transformation_logger.logger.info(
                    "Status projection detected node errors",
                    correlation_id=correlation_id,
                    execution_id=execution_id,
                    error_details=error_details
                )
            
            # Create and validate final StatusProjection
            status_projection = StatusProjection(
                execution_id=execution_id,
                project_id=project_id,
                status=status,
                progress=progress,
                current_task=current_task,
                totals=totals,
                customer_id=customer_id,
                branch=branch,
                artifacts=artifacts,
                started_at=started_at,
                updated_at=datetime.utcnow()
            )
            
            total_duration = (time.time() - start_time) * 1000
            transformation_logger.log_transformation_success(
                TransformationPhase.PERSISTENCE,
                total_duration,
                output_summary={
                    "execution_id": execution_id,
                    "project_id": project_id,
                    "status": status.value,
                    "progress": progress
                },
                performance_metrics={
                    "total_duration_ms": total_duration,
                    "phases_completed": 5
                }
            )
            
            return status_projection
            
        except ValidationError as e:
            creation_duration = (time.time() - creation_start) * 1000
            transformation_logger.log_transformation_error(
                TransformationPhase.PERSISTENCE,
                e,
                creation_duration,
                error_context={
                    "execution_id": execution_id,
                    "project_id": project_id,
                    "status": status.value if status else None,
                    "validation_errors": e.errors() if hasattr(e, 'errors') else str(e)
                }
            )
            raise TaskContextTransformationError(
                f"Failed to create valid StatusProjection: {str(e)}",
                context={
                    "execution_id": execution_id,
                    "project_id": project_id,
                    "validation_errors": e.errors() if hasattr(e, 'errors') else str(e)
                }
            ) from e
        
    except (InvalidTaskContextError, NodeDataError, StatusCalculationError, FieldExtractionError, TaskContextTransformationError):
        # Re-raise our custom exceptions
        raise
        
    except Exception as e:
        # Ultimate fallback for unexpected errors
        total_duration = (time.time() - start_time) * 1000
        transformation_logger.log_transformation_error(
            TransformationPhase.VALIDATION,  # Use validation phase as fallback
            e,
            total_duration,
            error_context={
                "execution_id": execution_id,
                "project_id": project_id,
                "task_context_type": type(task_context).__name__ if task_context else None,
                "unexpected_error": True
            }
        )
        
        # For backward compatibility, return a minimal valid StatusProjection instead of raising
        transformation_logger.log_degraded_operation(
            TransformationPhase.PERSISTENCE,
            f"Unexpected error in transformation: {str(e)}",
            "returning_error_status_projection",
            "System will continue with minimal error state"
        )
        
        return StatusProjection(
            execution_id=execution_id,
            project_id=project_id,
            status=ExecutionStatus.ERROR,
            progress=0.0,
            current_task=None,
            totals=TaskTotals(),
            customer_id=None,
            branch=None,
            artifacts=ExecutionArtifacts(),
            started_at=None,
            updated_at=datetime.utcnow()
        )


def validate_status_transition(from_status: str, to_status: str) -> bool:
    """
    Validate status transition according to ADD Section 17.
    
    Args:
        from_status: Current status
        to_status: Target status
        
    Returns:
        True if transition is valid, False otherwise
    """
    try:
        from_enum = ExecutionStatus(from_status)
        to_enum = ExecutionStatus(to_status)
        
        # Define valid transitions directly to avoid validation issues
        valid_transitions = {
            ExecutionStatus.IDLE: [ExecutionStatus.INITIALIZING, ExecutionStatus.ERROR],
            ExecutionStatus.INITIALIZING: [ExecutionStatus.RUNNING, ExecutionStatus.ERROR],
            ExecutionStatus.RUNNING: [ExecutionStatus.PAUSED, ExecutionStatus.STOPPING, ExecutionStatus.COMPLETED, ExecutionStatus.ERROR],
            ExecutionStatus.PAUSED: [ExecutionStatus.RUNNING, ExecutionStatus.ERROR],
            ExecutionStatus.STOPPING: [ExecutionStatus.STOPPED, ExecutionStatus.ERROR],
            ExecutionStatus.STOPPED: [ExecutionStatus.ERROR],  # Can only transition to error for cleanup
            ExecutionStatus.COMPLETED: [ExecutionStatus.ERROR],  # Can only transition to error for cleanup
            ExecutionStatus.ERROR: []  # Terminal state
        }
        
        return to_enum in valid_transitions.get(from_enum, [])
    except (ValueError, TypeError):
        return False