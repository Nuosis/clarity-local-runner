"""
DevTeam Automation API Schemas

This module defines Pydantic schemas for the DevTeam Automation API endpoints,
specifically for the POST /api/devteam/automation/initialize endpoint.

The schemas provide comprehensive validation for:
- Request validation with projectId, userId, and optional stopPoint
- Response format with executionId and eventId
- Idempotency key support with TTL handling
- Error responses for validation and conflict scenarios
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field, validator
from schemas.common import APIResponse


class DevTeamAutomationInitializeRequest(BaseModel):
    """
    Request schema for POST /api/devteam/automation/initialize endpoint.
    
    This schema validates the incoming request for initializing DevTeam automation
    with comprehensive field validation and security checks.
    """
    
    project_id: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Project identifier (e.g., 'customer-123/project-abc')"
    )
    
    user_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User ID who is initializing the automation"
    )
    
    stop_point: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Optional stop point for debugging/testing (e.g., 'SELECT', 'PREP')"
    )
    
    @validator('project_id')
    def validate_project_id(cls, v):
        """Validate project ID format."""
        if not v or not v.strip():
            raise ValueError("Project ID cannot be empty")
        
        v = v.strip()
        
        # Validate regex pattern for security
        import re
        if not re.match(r"^[a-zA-Z0-9_/-]+$", v):
            raise ValueError("Project ID must contain only alphanumeric characters, underscores, hyphens, and forward slashes")
        
        # Validate format: customer-id/project-id
        if '/' in v:
            parts = v.split('/')
            if len(parts) != 2 or not all(part.strip() for part in parts):
                raise ValueError("Project ID must be in format 'customer-id/project-id'")
        
        return v
    
    @validator('user_id')
    def validate_user_id(cls, v):
        """Validate user ID format."""
        if not v or not v.strip():
            raise ValueError("User ID cannot be empty")
        
        v = v.strip()
        
        # Basic security validation
        import re
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("User ID must contain only alphanumeric characters, underscores, and hyphens")
        
        return v
    
    @validator('stop_point')
    def validate_stop_point(cls, v):
        """Validate stop point if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
            
            # Validate against known workflow nodes
            valid_stop_points = ['SELECT', 'PREP', 'IMPLEMENT', 'VERIFY']
            if v.upper() not in valid_stop_points:
                raise ValueError(f"Stop point must be one of: {', '.join(valid_stop_points)}")
            
            return v.upper()
        
        return v
    
    class Config:
        """Pydantic configuration."""
        
        schema_extra = {
            "example": {
                "project_id": "customer-123/project-abc",
                "user_id": "user_123",
                "stop_point": "PREP"
            }
        }


class DevTeamAutomationInitializeResponse(BaseModel):
    """
    Response schema for successful DevTeam automation initialization.
    
    Returns 202 Accepted with executionId and eventId as specified in the requirements.
    """
    
    execution_id: str = Field(
        ...,
        description="Unique execution identifier for tracking automation progress"
    )
    
    event_id: str = Field(
        ...,
        description="Event identifier for the created automation event"
    )
    
    class Config:
        """Pydantic configuration."""
        
        schema_extra = {
            "example": {
                "execution_id": "exec_12345678-1234-1234-1234-123456789012",
                "event_id": "evt_devteam_12345678-1234-1234-1234-123456789012"
            }
        }


class DevTeamAutomationConflictResponse(BaseModel):
    """
    Response schema for 409 Conflict when idempotency key is replayed.
    
    Provides location header information for status endpoint.
    """
    
    message: str = Field(
        ...,
        description="Conflict message explaining the idempotency replay"
    )
    
    location: str = Field(
        ...,
        description="Location URL for checking automation status"
    )
    
    existing_execution_id: str = Field(
        ...,
        description="Execution ID of the existing automation"
    )
    
    class Config:
        """Pydantic configuration."""
        
        schema_extra = {
            "example": {
                "message": "Automation already initialized for this project with the same idempotency key",
                "location": "/api/devteam/automation/status/customer-123/project-abc",
                "existing_execution_id": "exec_12345678-1234-1234-1234-123456789012"
            }
        }


class DevTeamAutomationStatusResponse(BaseModel):
    """
    Response schema for GET /api/devteam/automation/status/{project_id} endpoint.
    
    Returns the current automation status and progress for a project following
    the ADD Section 5.2 format: {status, progress, currentTask, totals, executionId}.
    
    Updated to include all StatusProjection fields for complete field mapping alignment.
    """
    
    status: str = Field(
        ...,
        description="Current execution status (idle, initializing, running, paused, completed, error)"
    )
    
    progress: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Execution progress percentage (0.0-100.0)"
    )
    
    current_task: Optional[str] = Field(
        None,
        description="Current task identifier (e.g., '1.1.1')"
    )
    
    totals: Dict[str, int] = Field(
        ...,
        description="Task completion totals {completed: int, total: int}"
    )
    
    execution_id: str = Field(
        ...,
        description="Unique execution identifier"
    )
    
    # Required field from StatusProjection - added for complete field mapping
    project_id: str = Field(
        ...,
        description="Project identifier (e.g., 'customer-123/project-abc')"
    )
    
    # Optional fields for enhanced status information
    customer_id: Optional[str] = Field(
        None,
        description="Customer identifier extracted from project_id"
    )
    
    branch: Optional[str] = Field(
        None,
        description="Current working branch"
    )
    
    artifacts: Optional[Dict[str, Any]] = Field(
        None,
        description="Execution artifacts and metadata (repo_path, logs, files_modified)"
    )
    
    started_at: Optional[str] = Field(
        None,
        description="Execution start timestamp (ISO format)"
    )
    
    updated_at: Optional[str] = Field(
        None,
        description="Last update timestamp (ISO format)"
    )
    
    class Config:
        """Pydantic configuration."""
        
        schema_extra = {
            "example": {
                "status": "running",
                "progress": 45.2,
                "current_task": "1.1.1",
                "totals": {
                    "completed": 3,
                    "total": 8
                },
                "execution_id": "exec_12345678-1234-1234-1234-123456789012",
                "project_id": "customer-123/project-abc",
                "customer_id": "customer-123",
                "branch": "task/1-1-1-add-devteam-enabled-flag",
                "artifacts": {
                    "repo_path": "/workspace/repos/customer-123-project-abc",
                    "branch": "task/1-1-1-add-devteam-enabled-flag",
                    "logs": ["Implementation started", "Aider tool initialized"],
                    "files_modified": ["src/config.js", "README.md"]
                },
                "started_at": "2025-01-14T18:25:00Z",
                "updated_at": "2025-01-14T18:30:00Z"
            }
        }


class DevTeamAutomationStatusNotFoundResponse(BaseModel):
    """
    Response schema for 404 Not Found when project status is not available.
    """
    
    message: str = Field(
        ...,
        description="Error message explaining why status was not found"
    )
    
    project_id: str = Field(
        ...,
        description="Project ID that was requested"
    )
    
    class Config:
        """Pydantic configuration."""
        
        schema_extra = {
            "example": {
                "message": "No automation status found for project",
                "project_id": "customer-123/project-abc"
            }
        }


class DevTeamAutomationPauseResponse(BaseModel):
    """
    Response schema for successful DevTeam automation pause operation.
    
    Returns 200 OK with status transition confirmation.
    """
    
    project_id: str = Field(
        ...,
        description="Project identifier that was paused"
    )
    
    execution_id: str = Field(
        ...,
        description="Execution identifier for the paused automation"
    )
    
    previous_status: str = Field(
        ...,
        description="Previous execution status before pause"
    )
    
    current_status: str = Field(
        ...,
        description="Current execution status after pause (should be 'paused')"
    )
    
    paused_at: str = Field(
        ...,
        description="Timestamp when the automation was paused (ISO format)"
    )
    
    class Config:
        """Pydantic configuration."""
        
        schema_extra = {
            "example": {
                "project_id": "customer-123/project-abc",
                "execution_id": "exec_12345678-1234-1234-1234-123456789012",
                "previous_status": "running",
                "current_status": "paused",
                "paused_at": "2025-01-14T18:35:00Z"
            }
        }


class DevTeamAutomationResumeResponse(BaseModel):
    """
    Response schema for successful DevTeam automation resume operation.
    
    Returns 200 OK with status transition confirmation.
    """
    
    project_id: str = Field(
        ...,
        description="Project identifier that was resumed"
    )
    
    execution_id: str = Field(
        ...,
        description="Execution identifier for the resumed automation"
    )
    
    previous_status: str = Field(
        ...,
        description="Previous execution status before resume"
    )
    
    current_status: str = Field(
        ...,
        description="Current execution status after resume (should be 'running')"
    )
    
    resumed_at: str = Field(
        ...,
        description="Timestamp when the automation was resumed (ISO format)"
    )
    
    class Config:
        """Pydantic configuration."""
        
        schema_extra = {
            "example": {
                "project_id": "customer-123/project-abc",
                "execution_id": "exec_12345678-1234-1234-1234-123456789012",
                "previous_status": "paused",
                "current_status": "running",
                "resumed_at": "2025-01-14T18:40:00Z"
            }
        }


class DevTeamAutomationStopResponse(BaseModel):
    """
    Response schema for successful DevTeam automation stop operation.
    
    Returns 200 OK with status transition confirmation.
    """
    
    project_id: str = Field(
        ...,
        description="Project identifier that was stopped"
    )
    
    execution_id: str = Field(
        ...,
        description="Execution identifier for the stopped automation"
    )
    
    previous_status: str = Field(
        ...,
        description="Previous execution status before stop"
    )
    
    current_status: str = Field(
        ...,
        description="Current execution status after stop (should be 'stopping')"
    )
    
    stopped_at: str = Field(
        ...,
        description="Timestamp when the automation was stopped (ISO format)"
    )
    
    class Config:
        """Pydantic configuration."""
        
        schema_extra = {
            "example": {
                "project_id": "customer-123/project-abc",
                "execution_id": "exec_12345678-1234-1234-1234-123456789012",
                "previous_status": "running",
                "current_status": "stopping",
                "stopped_at": "2025-01-14T18:45:00Z"
            }
        }


class DevTeamAutomationStateTransitionErrorResponse(BaseModel):
    """
    Response schema for 409 Conflict when state transition is invalid.
    """
    
    message: str = Field(
        ...,
        description="Error message explaining the invalid state transition"
    )
    
    project_id: str = Field(
        ...,
        description="Project ID that was requested"
    )
    
    current_status: str = Field(
        ...,
        description="Current execution status"
    )
    
    requested_transition: str = Field(
        ...,
        description="The requested state transition that failed"
    )
    
    valid_transitions: list = Field(
        ...,
        description="List of valid state transitions from current status"
    )
    
    class Config:
        """Pydantic configuration."""
        
        schema_extra = {
            "example": {
                "message": "Invalid state transition: cannot pause automation that is not running",
                "project_id": "customer-123/project-abc",
                "current_status": "completed",
                "requested_transition": "completed→paused",
                "valid_transitions": ["error"]
            }
        }


# Type aliases for API responses
DevTeamInitializeSuccessResponse = APIResponse[DevTeamAutomationInitializeResponse]
DevTeamInitializeConflictResponse = APIResponse[DevTeamAutomationConflictResponse]
DevTeamStatusSuccessResponse = APIResponse[DevTeamAutomationStatusResponse]
DevTeamStatusNotFoundResponse = APIResponse[DevTeamAutomationStatusNotFoundResponse]
DevTeamPauseSuccessResponse = APIResponse[DevTeamAutomationPauseResponse]
DevTeamPauseConflictResponse = APIResponse[DevTeamAutomationStateTransitionErrorResponse]
DevTeamResumeSuccessResponse = APIResponse[DevTeamAutomationResumeResponse]
DevTeamResumeConflictResponse = APIResponse[DevTeamAutomationStateTransitionErrorResponse]
DevTeamStopSuccessResponse = APIResponse[DevTeamAutomationStopResponse]
DevTeamStopConflictResponse = APIResponse[DevTeamAutomationStateTransitionErrorResponse]