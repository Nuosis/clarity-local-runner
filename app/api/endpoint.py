import json
from http import HTTPStatus
from typing import Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette.responses import Response

from worker.config import celery_app
from database.event import Event
from database.repository import GenericRepository
from database.session import db_session

from schemas.event_schema import EventRequest
from core.exceptions import ValidationError
from fastapi import HTTPException
from pydantic import ValidationError as PydanticValidationError
from workflows.workflow_registry import WorkflowRegistry

# Configure structured logging - uses comprehensive logging infrastructure from Branch 8.1
# Provides JSON format, secret redaction, and required fields (correlationId, projectId, executionId)
from core.structured_logging import get_structured_logger, LogStatus
logger = get_structured_logger(__name__)

"""
Event Submission Endpoint Module

This module defines the primary FastAPI endpoint for event ingestion.
It implements the initial handling of incoming events by:
1. Validating the incoming event data
2. Persisting the event to the database
3. Queuing an asynchronous processing task
4. Returning an acceptance response

The endpoint follows the "accept-and-delegate" pattern where:
- Events are immediately accepted if valid
- Processing is handled asynchronously via Celery
- A 202 Accepted response indicates successful queueing

This pattern ensures high availability and responsiveness of the API
while allowing for potentially long-running processing operations.
"""

router = APIRouter()


@router.post("/", dependencies=[])
def handle_event(
    data: EventRequest,
    session: Session = Depends(db_session),
) -> Response:
    """Handles incoming event submissions with comprehensive validation.

    This endpoint receives events, validates them against the EventRequest schema,
    stores them in the database, and queues them for asynchronous processing.
    It implements a non-blocking pattern to ensure API responsiveness.

    Args:
        data: The event data, validated against EventRequest schema with:
            - Comprehensive field validation and constraints
            - Input sanitization and security checks
            - Type safety with meaningful error messages
            - Support for DevTeam automation and other event types
        session: Database session injected by FastAPI dependency

    Returns:
        Response: 202 Accepted response with task ID

    Raises:
        HTTPException: 422 for validation errors with detailed field-level feedback
        HTTPException: 500 for internal server errors

    Note:
        The endpoint returns immediately after queueing the task.
        Use the task ID in the response to check processing status.
        Validation processing is optimized to meet ≤200ms requirement.
    """
    try:
        # Store event in database
        repository = GenericRepository(
            session=session,
            model=Event,
        )
        raw_event = data.model_dump(mode="json")
        event = Event(data=raw_event, workflow_type=get_workflow_type(raw_event))
        repository.create(obj=event)

        # Extract correlationId from metadata or generate from task_id
        correlation_id = None
        if data.metadata and data.metadata.correlation_id:
            correlation_id = data.metadata.correlation_id
        
        # Log event persistence with structured fields using established patterns
        # Includes correlationId, projectId, and executionId for distributed tracing
        logger.info(
            "Event persisted successfully",
            correlation_id=correlation_id,
            project_id=data.project_id,
            execution_id=str(event.id),  # Use event ID as execution ID for traceability
            status=LogStatus.COMPLETED,
            event_id=str(event.id),
            event_type=data.type.value if hasattr(data.type, 'value') else str(data.type),
            workflow_type=event.workflow_type
        )

        # Queue processing task with enhanced error handling
        try:
            task_id = celery_app.send_task(
                "process_incoming_event",
                args=[str(event.id)],
                # Pass correlationId as task metadata for worker access
                headers={
                    "correlation_id": correlation_id or str(event.id),
                    "event_id": str(event.id),
                    "project_id": data.project_id,
                    "event_type": data.type.value if hasattr(data.type, 'value') else str(data.type)
                }
            )
            
            # Use task_id as correlationId if not provided in metadata
            if not correlation_id:
                correlation_id = str(task_id)
            
            # Log successful task dispatch with structured fields
            # CorrelationId propagated from request headers to Celery task for end-to-end tracing
            logger.info(
                "Celery task dispatched successfully",
                correlation_id=correlation_id,
                project_id=data.project_id,
                execution_id=str(event.id),
                task_id=str(task_id),
                status=LogStatus.COMPLETED,
                event_id=str(event.id),
                event_type=data.type.value if hasattr(data.type, 'value') else str(data.type),
                workflow_type=event.workflow_type
            )
            
        except Exception as celery_error:
            # Log Celery dispatch failure with structured fields
            # Secret redaction automatically applied by StructuredLogger infrastructure
            logger.error(
                "Failed to dispatch Celery task",
                correlation_id=correlation_id,
                project_id=data.project_id,
                execution_id=str(event.id),
                status=LogStatus.FAILED,
                event_id=str(event.id),
                error=celery_error,
                error_type=type(celery_error).__name__
            )
            
            # Still return 202 as event is persisted, but log the dispatch failure
            # This implements graceful degradation - the event is stored and can be retried
            task_id = None

        # Return acceptance response with enhanced metadata including correlationId
        response_data = {
            "message": f"Event accepted and queued for processing",
            "event_id": str(event.id),
            "task_id": str(task_id) if task_id else None,
            "correlation_id": correlation_id,
            "status": "accepted",
            "event_type": data.type.value if hasattr(data.type, 'value') else str(data.type)
        }
        
        return Response(
            content=json.dumps(response_data),
            status_code=HTTPStatus.ACCEPTED,
            media_type="application/json"
        )
        
    except PydanticValidationError as e:
        # This should not happen as FastAPI handles validation before reaching here
        # But included for completeness
        error_details = []
        for error in e.errors():
            error_details.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"]
            })
        
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Request validation failed",
                "errors": error_details,
                "error_code": "VALIDATION_ERROR"
            }
        )
    
    except Exception as e:
        # Initialize variables for error logging to avoid unbound variable issues
        correlation_id_for_log = None
        execution_id_for_log = None
        
        # Extract correlation_id if available
        if data and data.metadata and data.metadata.correlation_id:
            correlation_id_for_log = data.metadata.correlation_id
        
        # Extract execution_id if event was created
        try:
            # Use globals() to safely check for event variable
            if 'event' in globals() or 'event' in locals():
                event_var = locals().get('event') or globals().get('event')
                if event_var and hasattr(event_var, 'id'):
                    execution_id_for_log = str(event_var.id)
        except:
            pass
        
        # Log the error for debugging with structured fields
        # Automatic secret redaction ensures sensitive data in event_data is protected
        logger.error(
            "Error processing event",
            correlation_id=correlation_id_for_log,
            project_id=data.project_id if data else None,
            execution_id=execution_id_for_log,
            status=LogStatus.FAILED,
            error=e,
            error_type=type(e).__name__,
            event_data=data.model_dump(mode="json") if data else None
        )
        
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Internal server error occurred while processing event",
                "error_code": "INTERNAL_ERROR"
            }
        )


def get_workflow_type(data: Dict) -> str:
    """
    Determine the workflow type based on the event data.
    
    This function maps event types to their corresponding workflow registry entries.
    It ensures that events are routed to the correct workflow implementation.
    
    Args:
        data: The event data dictionary containing the event type
        
    Returns:
        The workflow registry name corresponding to the event type
    """
    event_type = data.get('type')
    
    # Map event types to workflow registry entries
    if event_type == 'DEVTEAM_AUTOMATION':
        return WorkflowRegistry.DEVTEAM_AUTOMATION.name
    elif event_type == 'PLACEHOLDER':
        return WorkflowRegistry.PLACEHOLDER.name
    else:
        # Default to PLACEHOLDER for unknown event types
        return WorkflowRegistry.PLACEHOLDER.name
