import asyncio
import logging
import time
from contextlib import contextmanager

from core.structured_logging import get_structured_logger, LogStatus
from core.performance_monitoring import record_queue_latency
from database.event import Event
from database.repository import GenericRepository
from database.session import db_session
from worker.config import celery_app
from workflows.workflow_registry import WorkflowRegistry
from schemas.event_schema import EventRequest
from services.execution_update_service import send_execution_update
from services.execution_log_service import get_execution_log_service, LogEntryType
from pydantic import ValidationError as PydanticValidationError

# Configure structured logging
logger = get_structured_logger(__name__)

"""
Workflow Task Processing Module

This module handles asynchronous processing of workflow events using Celery.
It manages the lifecycle of event processing from database retrieval through
workflow execution and result storage.
"""


@celery_app.task(name="process_incoming_event", bind=True)
def process_incoming_event(self, event_id: str):
    """Processes an incoming event through its designated workflow.

    This Celery task handles the asynchronous processing of events by:
    1. Logging task receipt with correlationId and event type for audit trail
    2. Validating event schema before processing
    3. Retrieving the event from the database
    4. Determining the appropriate workflow
    5. Executing the workflow
    6. Storing the results

    Args:
        self: Celery task instance (bound task)
        event_id: Unique identifier of the event to process
    """
    # Extract correlationId and other metadata from task headers
    task_headers = getattr(self.request, 'headers', {})
    correlation_id = task_headers.get('correlation_id', event_id)
    project_id = task_headers.get('project_id')
    event_type = task_headers.get('event_type')
    enqueue_time = task_headers.get('enqueue_time')
    
    # Generate execution ID from event_id for traceability
    execution_id = f"exec_{event_id}"
    
    # Record queue latency metric if enqueue time is available
    if enqueue_time:
        try:
            consume_time = time.time()
            record_queue_latency(
                enqueue_time=float(enqueue_time),
                consume_time=consume_time,
                correlation_id=correlation_id,
                execution_id=execution_id,
                event_id=event_id,
                task_id=str(self.request.id)
            )
        except (ValueError, TypeError) as e:
            # Log error but don't fail the task
            logger.warn(
                "Failed to record queue latency metric",
                correlation_id=correlation_id,
                execution_id=execution_id,
                event_id=event_id,
                error_message=str(e),
                enqueue_time=enqueue_time
            )
    
    # Initialize execution log service for real-time log broadcasting
    log_service = get_execution_log_service(correlation_id=correlation_id)
    
    # Log task receipt with correlationId and event type for audit trail
    logger.info(
        "Task received for processing",
        correlation_id=correlation_id,
        project_id=project_id,
        execution_id=execution_id,
        task_id=str(self.request.id),
        node="task_receipt",
        status=LogStatus.STARTED,
        event_id=event_id,
        event_type=event_type,
        message_type="task_receipt"
    )
    
    # Send execution log for task receipt
    if project_id:
        try:
            asyncio.run(log_service.send_task_receipt_log(
                project_id=project_id,
                execution_id=execution_id,
                task_id=str(self.request.id),
                event_id=event_id,
                event_type=event_type or "unknown"
            ))
        except Exception as log_error:
            logger.warn(
                "Failed to send task receipt execution log",
                correlation_id=correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                error_message=str(log_error)
            )
    
    # Log task start with structured fields
    logger.info(
        "Starting event processing",
        correlation_id=correlation_id,
        project_id=project_id,
        execution_id=execution_id,
        task_id=str(self.request.id),
        node="process_incoming_event",
        status=LogStatus.STARTED,
        event_id=event_id,
        event_type=event_type
    )
    
    try:
        with contextmanager(db_session)() as session:
            # Initialize repository for database operations
            repository = GenericRepository(session=session, model=Event)

            # Retrieve event from database
            db_event = repository.get(id=event_id)
            if db_event is None:
                error_msg = f"Event with id {event_id} not found"
                logger.error(
                    "Event not found in database",
                    correlation_id=correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    task_id=str(self.request.id),
                    node="database_retrieval",
                    status=LogStatus.FAILED,
                    event_id=event_id,
                    error_message=error_msg
                )
                raise ValueError(error_msg)

            # Log event retrieval success
            logger.info(
                "Event retrieved from database",
                correlation_id=correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                task_id=str(self.request.id),
                node="database_retrieval",
                status=LogStatus.COMPLETED,
                event_id=event_id,
                workflow_type=str(db_event.workflow_type)
            )

            # Validate event schema before processing with meaningful error messages
            try:
                # Ensure db_event.data is a dictionary before validation
                if not isinstance(db_event.data, dict):
                    raise ValueError(f"Event data must be a dictionary, got {type(db_event.data)}")
                
                validated_event = EventRequest.parse_obj(db_event.data)
                logger.info(
                    "Event schema validation successful",
                    correlation_id=correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    task_id=str(self.request.id),
                    node="schema_validation",
                    status=LogStatus.COMPLETED,
                    event_id=event_id,
                    event_type=event_type
                )
            except PydanticValidationError as validation_error:
                # Create meaningful error messages for validation failures
                error_details = []
                for error in validation_error.errors():
                    error_details.append({
                        "field": ".".join(str(loc) for loc in error["loc"]),
                        "message": error["msg"],
                        "type": error["type"],
                        "input": str(error.get("input", ""))[:100]  # Limit input length for logging
                    })
                
                error_msg = f"Event schema validation failed: {len(error_details)} validation errors"
                logger.error(
                    "Event schema validation failed",
                    correlation_id=correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    task_id=str(self.request.id),
                    node="schema_validation",
                    status=LogStatus.FAILED,
                    event_id=event_id,
                    event_type=event_type,
                    error_message=error_msg,
                    validation_errors=error_details
                )
                raise ValueError(f"{error_msg}: {error_details}")
            except Exception as schema_error:
                error_msg = f"Unexpected error during schema validation: {str(schema_error)}"
                logger.error(
                    "Unexpected schema validation error",
                    correlation_id=correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    task_id=str(self.request.id),
                    node="schema_validation",
                    status=LogStatus.FAILED,
                    event_id=event_id,
                    event_type=event_type,
                    error_message=error_msg,
                    error=schema_error
                )
                raise ValueError(error_msg)

            # Execute workflow and store results
            try:
                workflow_class = WorkflowRegistry[str(db_event.workflow_type)].value
                workflow = workflow_class()
                
                # Send initial execution update before workflow starts
                if project_id:
                    try:
                        # Create initial task context for status projection
                        initial_task_context = {
                            'metadata': {
                                'correlationId': correlation_id,
                                'taskId': str(self.request.id),
                                'executionId': execution_id,
                                'project_id': project_id,
                                'status': 'initializing'
                            },
                            'nodes': {}
                        }
                        
                        # Send initial execution update
                        asyncio.run(send_execution_update(
                            project_id=project_id,
                            task_context=initial_task_context,
                            execution_id=execution_id,
                            event_type="workflow_started",
                            correlation_id=correlation_id
                        ))
                        
                        # Send workflow start execution log
                        asyncio.run(log_service.send_workflow_start_log(
                            project_id=project_id,
                            execution_id=execution_id,
                            workflow_type=str(db_event.workflow_type),
                            task_id=str(self.request.id)
                        ))
                    except Exception as update_error:
                        logger.warn(
                            "Failed to send initial execution update or log",
                            correlation_id=correlation_id,
                            project_id=project_id,
                            execution_id=execution_id,
                            error_message=str(update_error)
                        )
                
                # Execute the workflow
                task_context = workflow.run(db_event.data).model_dump(mode="json")
                
                # Ensure correlationId is included in task_context metadata
                if 'metadata' not in task_context:
                    task_context['metadata'] = {}
                task_context['metadata']['correlationId'] = correlation_id
                task_context['metadata']['taskId'] = str(self.request.id)
                task_context['metadata']['executionId'] = execution_id
                task_context['metadata']['project_id'] = project_id
                
                # Update the database event with task context
                setattr(db_event, 'task_context', task_context)

                # Update event with processing results
                repository.update(obj=db_event)
                
                # Send completion execution update
                if project_id:
                    try:
                        asyncio.run(send_execution_update(
                            project_id=project_id,
                            task_context=task_context,
                            execution_id=execution_id,
                            event_type="workflow_completed",
                            correlation_id=correlation_id
                        ))
                        
                        # Send workflow completion execution log
                        asyncio.run(log_service.send_workflow_complete_log(
                            project_id=project_id,
                            execution_id=execution_id,
                            workflow_type=str(db_event.workflow_type),
                            task_id=str(self.request.id)
                        ))
                    except Exception as update_error:
                        logger.warn(
                            "Failed to send completion execution update or log",
                            correlation_id=correlation_id,
                            project_id=project_id,
                            execution_id=execution_id,
                            error_message=str(update_error)
                        )
                
                # Log successful completion
                logger.info(
                    "Event processing completed successfully",
                    correlation_id=correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    task_id=str(self.request.id),
                    node="workflow_execution",
                    status=LogStatus.COMPLETED,
                    event_id=event_id,
                    workflow_type=str(db_event.workflow_type)
                )
                
            except Exception as workflow_error:
                # Send error execution update
                if project_id:
                    try:
                        # Create error task context for status projection
                        error_task_context = {
                            'metadata': {
                                'correlationId': correlation_id,
                                'taskId': str(self.request.id),
                                'executionId': execution_id,
                                'project_id': project_id,
                                'status': 'error',
                                'error_message': str(workflow_error)
                            },
                            'nodes': {}
                        }
                        
                        asyncio.run(send_execution_update(
                            project_id=project_id,
                            task_context=error_task_context,
                            execution_id=execution_id,
                            event_type="workflow_error",
                            correlation_id=correlation_id
                        ))
                        
                        # Send workflow error execution log
                        asyncio.run(log_service.send_workflow_error_log(
                            project_id=project_id,
                            execution_id=execution_id,
                            workflow_type=str(db_event.workflow_type),
                            error_message=str(workflow_error),
                            task_id=str(self.request.id)
                        ))
                    except Exception as update_error:
                        logger.warn(
                            "Failed to send error execution update or log",
                            correlation_id=correlation_id,
                            project_id=project_id,
                            execution_id=execution_id,
                            error_message=str(update_error)
                        )
                
                # Log workflow execution failure
                logger.error(
                    "Workflow execution failed",
                    correlation_id=correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    task_id=str(self.request.id),
                    node="workflow_execution",
                    status=LogStatus.FAILED,
                    event_id=event_id,
                    workflow_type=str(db_event.workflow_type),
                    error=workflow_error
                )
                raise
                
    except Exception as e:
        # Log general task failure
        logger.error(
            "Event processing failed",
            correlation_id=correlation_id,
            project_id=project_id,
            execution_id=execution_id,
            task_id=str(self.request.id),
            node="process_incoming_event",
            status=LogStatus.FAILED,
            event_id=event_id,
            error=e
        )
        raise
