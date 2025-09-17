"""
WebSocket Message Envelope Schema

This module provides standardized envelope schemas and utilities for all WebSocket frames
following the ADD Section 6 specification: { type, ts, projectId, payload }

All WebSocket messages must use this standardized envelope format to ensure consistency
across execution-update, execution-log, error, and completion message types.
"""

from datetime import datetime
from typing import Dict, Any, Literal, Union, Optional
from enum import Enum

from pydantic import BaseModel, Field, validator


class MessageType(str, Enum):
    """Supported WebSocket message types per ADD Section 6."""
    EXECUTION_UPDATE = "execution-update"
    EXECUTION_LOG = "execution-log"
    ERROR = "error"
    COMPLETION = "completion"
    CONNECTION_ESTABLISHED = "connection-established"
    MESSAGE_RECEIVED = "message-received"


class WebSocketEnvelope(BaseModel):
    """
    Standardized WebSocket message envelope following ADD Section 6 specification.
    
    Format: { type, ts, projectId, payload }
    
    This schema ensures all WebSocket frames use consistent field naming and structure
    across all services and message types.
    """
    
    type: MessageType = Field(..., description="Message type identifier")
    ts: str = Field(..., description="Timestamp in ISO format with Z suffix")
    projectId: str = Field(..., description="Project identifier for routing")
    payload: Dict[str, Any] = Field(..., description="Message payload data")
    
    @validator('ts')
    def validate_timestamp_format(cls, v):
        """Ensure timestamp is in ISO format with Z suffix."""
        if not v.endswith('Z'):
            raise ValueError("Timestamp must end with 'Z' suffix")
        try:
            # Validate ISO format
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("Timestamp must be in valid ISO format")
        return v
    
    @validator('projectId')
    def validate_project_id(cls, v):
        """Ensure project ID is non-empty string."""
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError("Project ID must be a non-empty string")
        return v.strip()
    
    class Config:
        schema_extra = {
            "example": {
                "type": "execution-update",
                "ts": "2025-01-14T18:30:00.123Z",
                "projectId": "customer-123/project-abc",
                "payload": {
                    "execution_id": "exec-456",
                    "status": "running",
                    "progress": 45.2,
                    "current_task": "1.1.1"
                }
            }
        }


# Specialized envelope examples for documentation purposes
EXECUTION_UPDATE_EXAMPLE = {
    "type": "execution-update",
    "ts": "2025-01-14T18:30:00.123Z",
    "projectId": "customer-123/project-abc",
    "payload": {
        "execution_id": "exec-456",
        "status": "running",
        "progress": 45.2,
        "current_task": "1.1.1",
        "totals": {
            "completed": 3,
            "total": 8
        },
        "branch": "main",
        "updated_at": "2025-01-14T18:30:00.123Z",
        "event_type": "status_change"
    }
}

EXECUTION_LOG_EXAMPLE = {
    "type": "execution-log",
    "ts": "2025-01-14T18:30:00.123Z",
    "projectId": "customer-123/project-abc",
    "payload": {
        "execution_id": "exec-456",
        "log_entry_type": "node_start",
        "level": "INFO",
        "message": "Starting node: prep_node",
        "timestamp": "2025-01-14T18:30:00.123Z",
        "node_name": "prep_node",
        "task_id": "task-789"
    }
}

ERROR_EXAMPLE = {
    "type": "error",
    "ts": "2025-01-14T18:30:00.123Z",
    "projectId": "customer-123/project-abc",
    "payload": {
        "error_code": "VALIDATION_ERROR",
        "message": "Invalid message format",
        "details": "Missing required field: type"
    }
}

COMPLETION_EXAMPLE = {
    "type": "completion",
    "ts": "2025-01-14T18:30:00.123Z",
    "projectId": "customer-123/project-abc",
    "payload": {
        "execution_id": "exec-456",
        "status": "completed",
        "final_result": "success",
        "duration_ms": 45230.5,
        "completed_tasks": 8,
        "total_tasks": 8
    }
}


def create_envelope(
    message_type: MessageType,
    project_id: str,
    payload: Dict[str, Any],
    timestamp: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized WebSocket envelope.
    
    This utility function ensures all WebSocket messages follow the consistent
    envelope format: { type, ts, projectId, payload }
    
    Args:
        message_type: Type of message being created
        project_id: Project identifier for routing
        payload: Message payload data
        timestamp: Optional timestamp (defaults to current UTC time)
        
    Returns:
        Dict containing the standardized envelope
        
    Raises:
        ValueError: If project_id is invalid or payload is None
    """
    if not project_id or not isinstance(project_id, str) or not project_id.strip():
        raise ValueError("Project ID must be a non-empty string")
    
    if payload is None:
        raise ValueError("Payload cannot be None")
    
    if timestamp is None:
        timestamp = datetime.utcnow().isoformat() + "Z"
    elif not timestamp.endswith('Z'):
        timestamp = timestamp + "Z"
    
    envelope = {
        "type": message_type.value if isinstance(message_type, MessageType) else message_type,
        "ts": timestamp,
        "projectId": project_id.strip(),
        "payload": payload
    }
    
    # Validate the envelope using Pydantic
    WebSocketEnvelope(**envelope)
    
    return envelope


def create_execution_update_envelope(
    project_id: str,
    execution_id: str,
    status: str,
    progress: float,
    current_task: str,
    totals: Dict[str, int],
    branch: Optional[str] = None,
    updated_at: Optional[str] = None,
    event_type: str = "status_change",
    timestamp: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized execution-update envelope.
    
    Args:
        project_id: Project identifier for routing
        execution_id: Unique execution identifier
        status: Current execution status
        progress: Progress percentage (0-100)
        current_task: Current task identifier
        totals: Dictionary with 'completed' and 'total' counts
        branch: Optional branch name
        updated_at: Optional update timestamp
        event_type: Type of event triggering the update
        timestamp: Optional envelope timestamp
        
    Returns:
        Dict containing the standardized execution-update envelope
    """
    payload = {
        "execution_id": execution_id,
        "status": status,
        "progress": progress,
        "current_task": current_task,
        "totals": totals,
        "branch": branch,
        "updated_at": updated_at,
        "event_type": event_type
    }
    
    return create_envelope(MessageType.EXECUTION_UPDATE, project_id, payload, timestamp)


def create_execution_log_envelope(
    project_id: str,
    execution_id: str,
    log_entry_type: str,
    level: str,
    message: str,
    node_name: Optional[str] = None,
    task_id: Optional[str] = None,
    additional_data: Optional[Dict[str, Any]] = None,
    timestamp: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized execution-log envelope.
    
    Args:
        project_id: Project identifier for routing
        execution_id: Unique execution identifier
        log_entry_type: Type of log entry
        level: Log level (DEBUG, INFO, WARN, ERROR)
        message: Log message content
        node_name: Optional workflow node name
        task_id: Optional task identifier
        additional_data: Optional additional data
        timestamp: Optional envelope timestamp
        
    Returns:
        Dict containing the standardized execution-log envelope
    """
    payload = {
        "execution_id": execution_id,
        "log_entry_type": log_entry_type,
        "level": level,
        "message": message,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "node_name": node_name,
        "task_id": task_id
    }
    
    # Add additional data if provided
    if additional_data:
        payload.update(additional_data)
    
    return create_envelope(MessageType.EXECUTION_LOG, project_id, payload, timestamp)


def create_error_envelope(
    project_id: str,
    error_code: str,
    message: str,
    details: Optional[str] = None,
    timestamp: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized error envelope.
    
    Args:
        project_id: Project identifier for routing
        error_code: Error code identifier
        message: Error message
        details: Optional error details
        timestamp: Optional envelope timestamp
        
    Returns:
        Dict containing the standardized error envelope
    """
    payload = {
        "error_code": error_code,
        "message": message,
        "details": details
    }
    
    return create_envelope(MessageType.ERROR, project_id, payload, timestamp)


def create_completion_envelope(
    project_id: str,
    execution_id: str,
    status: str,
    final_result: str,
    duration_ms: Optional[float] = None,
    completed_tasks: Optional[int] = None,
    total_tasks: Optional[int] = None,
    timestamp: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized completion envelope.
    
    Args:
        project_id: Project identifier for routing
        execution_id: Unique execution identifier
        status: Final execution status
        final_result: Final result description
        duration_ms: Optional execution duration in milliseconds
        completed_tasks: Optional number of completed tasks
        total_tasks: Optional total number of tasks
        timestamp: Optional envelope timestamp
        
    Returns:
        Dict containing the standardized completion envelope
    """
    payload = {
        "execution_id": execution_id,
        "status": status,
        "final_result": final_result,
        "duration_ms": duration_ms,
        "completed_tasks": completed_tasks,
        "total_tasks": total_tasks
    }
    
    return create_envelope(MessageType.COMPLETION, project_id, payload, timestamp)