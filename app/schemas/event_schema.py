"""
Event Request Schema Module

This module defines comprehensive Pydantic schemas for event validation in the
Clarity Local Runner workflow orchestration system. It provides robust input
validation, type safety, and meaningful error messages for the POST /events endpoint.

The EventRequest schema supports the DevTeam automation workflow and other event
types with comprehensive field validation and constraints.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator, root_validator, constr


class EventType(str, Enum):
    """Supported event types for workflow processing."""
    
    DEVTEAM_AUTOMATION = "DEVTEAM_AUTOMATION"
    PLACEHOLDER = "PLACEHOLDER"
    PAYMENT = "PAYMENT"
    ENROLLMENT = "ENROLLMENT"
    SUBSCRIPTION_PAYMENT = "SUBSCRIPTION_PAYMENT"
    CUSTOMER_CARE = "CUSTOMER_CARE"


class EventPriority(str, Enum):
    """Event processing priority levels."""
    
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class TaskDefinition(BaseModel):
    """Task definition for DevTeam automation events."""
    
    id: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Task identifier (e.g., '1.1.1', '2.3')"
    )
    
    @validator('id')
    def validate_task_id_format(cls, v):
        """Validate task ID format."""
        import re
        if not re.match(r"^[0-9]+(\.[0-9]+)*$", v):
            raise ValueError("Task ID must be in format like '1.1.1' or '2.3'")
        return v
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Task title"
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Detailed task description"
    )
    type: str = Field(
        default="atomic",
        description="Task type (atomic, composite, etc.)"
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="List of task IDs this task depends on"
    )
    files: List[str] = Field(
        default_factory=list,
        description="List of files this task affects"
    )


class EventOptions(BaseModel):
    """Optional configuration for event processing."""
    
    stop_point: Optional[str] = Field(
        None,
        description="Optional stop point for debugging/testing"
    )
    idempotency_key: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Idempotency key for duplicate prevention"
    )
    timeout_seconds: Optional[int] = Field(
        None,
        ge=1,
        le=3600,
        description="Processing timeout in seconds (1-3600)"
    )
    retry_count: Optional[int] = Field(
        None,
        ge=0,
        le=5,
        description="Number of retry attempts (0-5)"
    )


class EventMetadata(BaseModel):
    """Event metadata for tracking and correlation."""
    
    correlation_id: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Correlation ID for request tracking"
    )
    source: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Event source system or component"
    )
    user_id: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="User ID who initiated the event"
    )
    session_id: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Session ID for the request"
    )
    client_timestamp: Optional[datetime] = Field(
        None,
        description="Client-side timestamp when event was created"
    )


class EventRequest(BaseModel):
    """
    Comprehensive event request schema for POST /events endpoint.
    
    This schema provides robust validation for all incoming events with:
    - Type safety with proper field validation and constraints
    - Input sanitization and validation for all user inputs
    - Support for required fields for event processing
    - Meaningful error messages with actionable feedback
    - Performance-optimized validation (≤200ms processing time)
    
    Example:
        {
            "id": "evt_12345",
            "type": "DEVTEAM_AUTOMATION",
            "project_id": "customer-123/project-abc",
            "task": {
                "id": "1.1.1",
                "title": "Add DEVTEAM_ENABLED flag to src/config.js"
            },
            "priority": "normal",
            "data": {
                "repository_url": "https://github.com/user/repo.git",
                "branch": "main"
            }
        }
    """
    
    # Required core fields
    id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique event identifier (alphanumeric, underscore, hyphen only)"
    )
    
    type: EventType = Field(
        ...,
        description="Event type for workflow routing"
    )
    
    # Optional but commonly used fields
    project_id: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        description="Project identifier (e.g., 'customer-123/project-abc')"
    )
    
    task: Optional[TaskDefinition] = Field(
        None,
        description="Task definition for DevTeam automation events"
    )
    
    priority: EventPriority = Field(
        default=EventPriority.NORMAL,
        description="Event processing priority"
    )
    
    # Flexible data payload
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Event-specific data payload"
    )
    
    # Optional configuration and metadata
    options: Optional[EventOptions] = Field(
        None,
        description="Optional processing configuration"
    )
    
    metadata: Optional[EventMetadata] = Field(
        None,
        description="Optional event metadata for tracking"
    )
    
    # Timestamps
    created_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description="Event creation timestamp"
    )
    
    @validator('id')
    def validate_id_format(cls, v):
        """Validate event ID format and sanitize input."""
        if not v or not v.strip():
            raise ValueError("Event ID cannot be empty or whitespace only")
        
        # Sanitize by removing extra whitespace
        v = v.strip()
        
        # Validate regex pattern
        import re
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Event ID must contain only alphanumeric characters, underscores, and hyphens")
        
        # Additional security check for common injection patterns
        dangerous_patterns = ['<', '>', '"', "'", '&', ';', '|', '`']
        if any(pattern in v for pattern in dangerous_patterns):
            raise ValueError("Event ID contains invalid characters")
        
        return v
    
    @validator('project_id')
    def validate_project_id(cls, v):
        """Validate project ID format if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Project ID cannot be empty if provided")
            
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
    
    @validator('data')
    def validate_data_payload(cls, v):
        """Validate and sanitize data payload."""
        if not isinstance(v, dict):
            raise ValueError("Data payload must be a dictionary")
        
        # Check payload size to prevent DoS attacks
        import json
        payload_size = len(json.dumps(v))
        if payload_size > 1024 * 1024:  # 1MB limit
            raise ValueError("Data payload exceeds maximum size of 1MB")
        
        return v
    
    @root_validator(pre=True)
    def validate_event_consistency(cls, values):
        """Validate event consistency and required fields based on type."""
        event_type = values.get('type')
        task = values.get('task')
        project_id = values.get('project_id')
        data = values.get('data', {})
        
        # DevTeam automation events require specific fields
        if event_type == EventType.DEVTEAM_AUTOMATION:
            if not project_id:
                raise ValueError("DevTeam automation events require project_id")
            
            if not task:
                raise ValueError("DevTeam automation events require task definition")
            
            # Validate repository URL if provided in data
            repo_url = data.get('repository_url')
            if repo_url and not isinstance(repo_url, str):
                raise ValueError("Repository URL must be a string")
        
        # Placeholder events (backward compatibility)
        elif event_type == EventType.PLACEHOLDER:
            # Ensure backward compatibility with existing PlaceholderEventSchema
            if 'id' not in values or 'type' not in values:
                raise ValueError("Placeholder events require id and type fields")
        
        return values
    
    class Config:
        """Pydantic configuration for optimal performance and validation."""
        
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
                "id": "evt_devteam_12345",
                "type": "DEVTEAM_AUTOMATION",
                "project_id": "customer-123/project-abc",
                "task": {
                    "id": "1.1.1",
                    "title": "Add DEVTEAM_ENABLED flag to src/config.js",
                    "description": "Add DEVTEAM_ENABLED flag with default false and JSDoc",
                    "type": "atomic",
                    "dependencies": [],
                    "files": ["src/config.js"]
                },
                "priority": "normal",
                "data": {
                    "repository_url": "https://github.com/user/repo.git",
                    "branch": "main"
                },
                "options": {
                    "idempotency_key": "unique-key-12345",
                    "timeout_seconds": 300
                },
                "metadata": {
                    "correlation_id": "req_12345",
                    "source": "devteam_ui",
                    "user_id": "user_123"
                }
            }
        }


# Backward compatibility alias
PlaceholderEventSchema = EventRequest