"""
Status Projection Service Module for Clarity Local Runner

This module provides comprehensive status projection read model operations with:
- Read operations for status projection data from Event.task_context
- Integration with StatusProjection schema from Task 5.2.1
- Performance-optimized database operations (≤2s requirement)
- Structured logging with correlationId propagation
- Comprehensive error handling with meaningful messages
- Repository pattern integration for database operations

Primary Responsibility: Status projection read model operations
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, String

from core.structured_logging import get_structured_logger, get_transformation_logger, LogStatus, log_performance, TransformationPhase, TransformationLogger
from core.exceptions import (
    RepositoryError,
    DatabaseError,
    ServiceError,
    ValidationError as ClarityValidationError,
    TaskContextTransformationError,
    InvalidTaskContextError,
    StatusCalculationError,
    FieldExtractionError
)
from database.repository import GenericRepository
from database.event import Event
from database.session import db_session
from schemas.status_projection_schema import (
    StatusProjection,
    ExecutionStatus,
    StatusProjectionError,
    project_status_from_task_context,
    validate_status_transition
)
from schemas.websocket_envelope import create_execution_update_envelope, create_completion_envelope
from api.v1.endpoints.websocket import broadcast_to_project


class StatusProjectionService:
    """
    Status projection read model service with comprehensive query operations.
    
    This service provides read operations for status projection data, integrating
    with the existing database layer and the StatusProjection schema from Task 5.2.1.
    It follows established patterns for logging, error handling, and performance optimization.
    """
    
    def __init__(self, session: Session, correlation_id: Optional[str] = None):
        """
        Initialize status projection service.
        
        Args:
            session: Database session for operations
            correlation_id: Optional correlation ID for distributed tracing
        """
        self.session = session
        self.repository = GenericRepository(session, Event)
        self.logger = get_structured_logger(__name__)
        self.transformation_logger = get_transformation_logger(__name__)
        self.correlation_id = correlation_id or f"sps_{int(time.time() * 1000)}"
        
        # Set persistent context for logging
        self.logger.set_context(correlationId=self.correlation_id)
        
        # Initialize transformation logger context
        self.transformation_logger.set_transformation_context(
            correlation_id=self.correlation_id,
            execution_id="service_operation",
            task_context_size=0
        )
    
    @log_performance(get_structured_logger(__name__), "get_status_by_project_id")
    def get_status_by_project_id(
        self,
        project_id: str,
        execution_id: Optional[str] = None
    ) -> Optional[StatusProjection]:
        """
        Get status projection by project ID.
        
        Args:
            project_id: Project identifier to get status for
            execution_id: Optional execution identifier for logging
            
        Returns:
            StatusProjection instance if found, None otherwise
            
        Raises:
            RepositoryError: If database operation fails or validation errors occur
        """
        start_time = time.time()
        
        try:
            # Enhanced input validation with custom exceptions
            if not project_id:
                raise ClarityValidationError(
                    "Project ID is required",
                    context={"field": "project_id", "value": project_id}
                )
            
            if not isinstance(project_id, str):
                raise ClarityValidationError(
                    "Project ID must be a string",
                    context={"field": "project_id", "type": type(project_id).__name__}
                )
            
            if not project_id.strip():
                raise ClarityValidationError(
                    "Project ID cannot be empty or whitespace",
                    context={"field": "project_id", "value": project_id}
                )
            
            # Validate project ID format for security
            import re
            if not re.match(r'^[a-zA-Z0-9_/-]+$', project_id.strip()):
                raise ClarityValidationError(
                    "Project ID contains invalid characters",
                    context={
                        "field": "project_id",
                        "value": project_id,
                        "allowed_pattern": "alphanumeric, underscores, hyphens, forward slashes"
                    }
                )
            
            self.logger.info(
                "Getting status projection by project ID",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.STARTED
            )
            
            # Query for the most recent event for this project
            # Look for events with task_context containing project information
            query = self.session.query(Event).filter(
                Event.task_context.isnot(None)
            ).order_by(desc(Event.updated_at))
            
            # Find events that match the project_id in task_context
            matching_event = None
            for event in query.limit(100):  # Limit search to recent events for performance
                task_context = event.task_context or {}
                metadata = task_context.get('metadata', {})
                
                # Check if this event matches our project_id
                event_project_id = metadata.get('project_id')
                if event_project_id == project_id:
                    matching_event = event
                    break
            
            if not matching_event:
                self.logger.info(
                    "No status projection found for project ID",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    status=LogStatus.COMPLETED,
                    duration_ms=round((time.time() - start_time) * 1000, 2)
                )
                return None
            
            # Generate execution_id from event ID if not provided
            event_execution_id = str(matching_event.id)
            
            # Project status from task_context using utility from Task 5.2.1 with enhanced error handling
            try:
                self.transformation_logger.log_transformation_start(
                    TransformationPhase.EXTRACTION,
                    input_data_summary={
                        "event_id": event_execution_id,
                        "project_id": project_id,
                        "has_task_context": matching_event.task_context is not None
                    }
                )
                
                # Convert SQLAlchemy column to dict with validation
                task_context_raw = matching_event.task_context
                if isinstance(task_context_raw, dict):
                    task_context_dict = task_context_raw
                else:
                    task_context_dict = {}
                
                # Check if task context is empty or invalid
                is_empty = False
                try:
                    # Safely check if task_context_dict is empty
                    if isinstance(task_context_dict, dict):
                        is_empty = len(task_context_dict) == 0
                    else:
                        is_empty = True
                except Exception:
                    # Handle SQLAlchemy column edge cases
                    is_empty = True
                
                if is_empty:
                    raise InvalidTaskContextError(
                        "Event has empty or invalid task_context",
                        context={
                            "event_id": event_execution_id,
                            "project_id": project_id,
                            "task_context_type": type(matching_event.task_context).__name__
                        }
                    )
                
                status_projection = project_status_from_task_context(
                    task_context=task_context_dict,
                    execution_id=event_execution_id,
                    project_id=project_id
                )
                
                transformation_duration = (time.time() - start_time) * 1000
                self.transformation_logger.log_transformation_success(
                    TransformationPhase.EXTRACTION,
                    transformation_duration,
                    output_summary={
                        "status": status_projection.status.value if hasattr(status_projection.status, 'value') else str(status_projection.status),
                        "progress": status_projection.progress,
                        "current_task": status_projection.current_task
                    }
                )
                
            except (TaskContextTransformationError, InvalidTaskContextError, StatusCalculationError, FieldExtractionError) as te:
                transformation_duration = (time.time() - start_time) * 1000
                self.transformation_logger.log_transformation_error(
                    TransformationPhase.EXTRACTION,
                    te,
                    transformation_duration,
                    error_context=getattr(te, 'context', {})
                )
                raise ServiceError(
                    f"Failed to transform task context to status projection: {str(te)}",
                    context={
                        "event_id": event_execution_id,
                        "project_id": project_id,
                        "transformation_error": str(te)
                    }
                )
            except Exception as e:
                transformation_duration = (time.time() - start_time) * 1000
                self.transformation_logger.log_transformation_error(
                    TransformationPhase.EXTRACTION,
                    e,
                    transformation_duration
                )
                raise ServiceError(
                    f"Unexpected error during status projection transformation: {str(e)}",
                    context={
                        "event_id": event_execution_id,
                        "project_id": project_id,
                        "error_type": type(e).__name__
                    }
                )

            # Handle status value properly - could be enum or string
            projection_status = status_projection.status.value if hasattr(status_projection.status, 'value') else str(status_projection.status)

            self.logger.info(
                "Status projection retrieved successfully by project ID",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.COMPLETED,
                event_id=str(matching_event.id),
                projection_status=projection_status,
                progress=status_projection.progress,
                duration_ms=round((time.time() - start_time) * 1000, 2)
            )
            
            return status_projection
            
        except RepositoryError:
            raise
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(
                "Failed to get status projection by project ID",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.FAILED,
                duration_ms=round(duration_ms, 2),
                error=e
            )
            raise RepositoryError(
                f"Failed to get status projection by project ID: {str(e)}"
            )
    
    @log_performance(get_structured_logger(__name__), "get_status_by_execution_id")
    def get_status_by_execution_id(
        self,
        execution_id: str,
        project_id: Optional[str] = None
    ) -> Optional[StatusProjection]:
        """
        Get status projection by execution ID.
        
        Args:
            execution_id: Execution identifier to get status for
            project_id: Optional project identifier for logging
            
        Returns:
            StatusProjection instance if found, None otherwise
            
        Raises:
            RepositoryError: If database operation fails or validation errors occur
        """
        start_time = time.time()
        
        try:
            if not execution_id or not isinstance(execution_id, str):
                raise RepositoryError(
                    "Execution ID must be a non-empty string"
                )
            
            self.logger.info(
                "Getting status projection by execution ID",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.STARTED
            )
            
            # Try to find event by ID (assuming execution_id maps to event.id)
            try:
                event = self.repository.get(execution_id)
            except Exception:
                # If direct lookup fails, search by string representation
                event = self.session.query(Event).filter(
                    Event.id.cast(String) == execution_id
                ).first()
            
            if not event or event.task_context is None:
                self.logger.info(
                    "No status projection found for execution ID",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    status=LogStatus.COMPLETED,
                    duration_ms=round((time.time() - start_time) * 1000, 2)
                )
                return None
            
            # Extract project_id from task_context if not provided
            task_context = event.task_context or {}
            metadata = task_context.get('metadata', {})
            derived_project_id = project_id or metadata.get('project_id', 'unknown')
            
            # Project status from task_context using utility from Task 5.2.1
            # Convert SQLAlchemy column to dict
            task_context_dict = event.task_context if isinstance(event.task_context, dict) else {}
            status_projection = project_status_from_task_context(
                task_context=task_context_dict,
                execution_id=execution_id,
                project_id=derived_project_id
            )
            
            self.logger.info(
                "Status projection retrieved successfully by execution ID",
                correlation_id=self.correlation_id,
                project_id=derived_project_id,
                execution_id=execution_id,
                status=LogStatus.COMPLETED,
                event_id=str(event.id),
                projection_status=status_projection.status.value if hasattr(status_projection.status, 'value') else str(status_projection.status),
                progress=status_projection.progress,
                duration_ms=round((time.time() - start_time) * 1000, 2)
            )
            
            return status_projection
            
        except RepositoryError:
            raise
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(
                "Failed to get status projection by execution ID",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.FAILED,
                duration_ms=round(duration_ms, 2),
                error=e
            )
            raise RepositoryError(
                f"Failed to get status projection by execution ID: {str(e)}"
            )
    
    @log_performance(get_structured_logger(__name__), "list_active_executions")
    def list_active_executions(
        self,
        limit: int = 50,
        project_id: Optional[str] = None
    ) -> List[StatusProjection]:
        """
        List active executions with status projections.
        
        Args:
            limit: Maximum number of executions to return (default: 50)
            project_id: Optional project identifier for filtering
            
        Returns:
            List of StatusProjection instances for active executions
            
        Raises:
            RepositoryError: If database operation fails or validation errors occur
        """
        start_time = time.time()
        
        try:
            if limit <= 0 or limit > 1000:
                raise RepositoryError(
                    "Limit must be between 1 and 1000"
                )
            
            self.logger.info(
                "Listing active executions",
                correlation_id=self.correlation_id,
                project_id=project_id,
                status=LogStatus.STARTED,
                limit=limit
            )
            
            # Query for recent events with task_context
            query = self.session.query(Event).filter(
                Event.task_context.isnot(None)
            ).order_by(desc(Event.updated_at)).limit(limit * 2)  # Get more to filter
            
            active_projections = []
            processed_projects = set()
            
            for event in query:
                task_context = event.task_context or {}
                metadata = task_context.get('metadata', {})
                event_project_id = metadata.get('project_id')
                
                # Skip if no project_id in task_context
                if not event_project_id:
                    continue
                
                # Filter by project_id if specified
                if project_id and event_project_id != project_id:
                    continue
                
                # Skip if we already processed this project (get most recent only)
                if event_project_id in processed_projects:
                    continue
                
                try:
                    # Project status from task_context using utility from Task 5.2.1
                    # Convert SQLAlchemy column to dict
                    task_context_dict = event.task_context if isinstance(event.task_context, dict) else {}
                    status_projection = project_status_from_task_context(
                        task_context=task_context_dict,
                        execution_id=str(event.id),
                        project_id=event_project_id
                    )
                    
                    # Only include active executions (not completed or error)
                    if status_projection.status in [
                        ExecutionStatus.INITIALIZING,
                        ExecutionStatus.RUNNING,
                        ExecutionStatus.PAUSED
                    ]:
                        active_projections.append(status_projection)
                        processed_projects.add(event_project_id)
                        
                        # Stop if we have enough active executions
                        if len(active_projections) >= limit:
                            break
                            
                except Exception as e:
                    # Log but continue processing other events
                    self.logger.warn(
                        "Failed to project status for event",
                        correlation_id=self.correlation_id,
                        project_id=project_id,
                        event_id=str(event.id),
                        error=str(e)
                    )
                    continue
            
            self.logger.info(
                "Active executions listed successfully",
                correlation_id=self.correlation_id,
                project_id=project_id,
                status=LogStatus.COMPLETED,
                active_executions_count=len(active_projections),
                events_processed=query.count(),
                duration_ms=round((time.time() - start_time) * 1000, 2)
            )
            
            return active_projections
            
        except RepositoryError:
            raise
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(
                "Failed to list active executions",
                correlation_id=self.correlation_id,
                project_id=project_id,
                status=LogStatus.FAILED,
                duration_ms=round(duration_ms, 2),
                error=e
            )
            raise RepositoryError(
                f"Failed to list active executions: {str(e)}"
            )
    
    @log_performance(get_structured_logger(__name__), "project_status_from_event_task_context")
    def project_status_from_event_task_context(
        self,
        event_id: str,
        project_id: Optional[str] = None
    ) -> Optional[StatusProjection]:
        """
        Project status from Event.task_context using the utility from Task 5.2.1.
        
        This method provides a service-layer wrapper around the utility function
        for projecting status from Event.task_context data.
        
        Args:
            event_id: Event ID to get task_context from
            project_id: Optional project identifier for validation
            
        Returns:
            StatusProjection instance if successful, None if event not found
            
        Raises:
            RepositoryError: If database operation fails or validation errors occur
        """
        start_time = time.time()
        
        try:
            if not event_id or not isinstance(event_id, str):
                raise RepositoryError(
                    "Event ID must be a non-empty string"
                )
            
            self.logger.info(
                "Projecting status from event task context",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=event_id,
                status=LogStatus.STARTED
            )
            
            # Get event by ID
            try:
                event = self.repository.get(event_id)
            except Exception:
                # If direct lookup fails, search by string representation
                event = self.session.query(Event).filter(
                    Event.id.cast(String) == event_id
                ).first()
            
            if not event:
                self.logger.info(
                    "Event not found for status projection",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    execution_id=event_id,
                    status=LogStatus.COMPLETED,
                    duration_ms=round((time.time() - start_time) * 1000, 2)
                )
                return None
            
            if event.task_context is None:
                self.logger.warn(
                    "Event has no task_context for status projection",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    execution_id=event_id,
                    event_id=str(event.id)
                )
                return None
            
            # Extract project_id from task_context if not provided
            task_context = event.task_context or {}
            metadata = task_context.get('metadata', {})
            derived_project_id = project_id or metadata.get('project_id', 'unknown')
            
            # Validate project_id matches if both provided
            if project_id and metadata.get('project_id') and project_id != metadata.get('project_id'):
                raise RepositoryError(
                    f"Project ID mismatch: provided {project_id}, found {metadata.get('project_id')}"
                )
            
            # Project status from task_context using utility from Task 5.2.1
            # Convert SQLAlchemy column to dict
            task_context_dict = event.task_context if isinstance(event.task_context, dict) else {}
            status_projection = project_status_from_task_context(
                task_context=task_context_dict,
                execution_id=event_id,
                project_id=derived_project_id
            )
            
            self.logger.info(
                "Status projected successfully from event task context",
                correlation_id=self.correlation_id,
                project_id=derived_project_id,
                execution_id=event_id,
                status=LogStatus.COMPLETED,
                event_id=str(event.id),
                projection_status=status_projection.status.value if hasattr(status_projection.status, 'value') else str(status_projection.status),
                progress=status_projection.progress,
                current_task=status_projection.current_task,
                duration_ms=round((time.time() - start_time) * 1000, 2)
            )
            
            return status_projection
            
        except RepositoryError:
            raise
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(
                "Failed to project status from event task context",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=event_id,
                status=LogStatus.FAILED,
                duration_ms=round(duration_ms, 2),
                error=e
            )
            raise RepositoryError(
                f"Failed to project status from event task context: {str(e)}"
            )
    
    def get_execution_history(
        self,
        project_id: str,
        limit: int = 10
    ) -> List[StatusProjection]:
        """
        Get execution history for a project.
        
        Args:
            project_id: Project identifier to get history for
            limit: Maximum number of historical executions to return
            
        Returns:
            List of StatusProjection instances ordered by most recent first
            
        Raises:
            RepositoryError: If database operation fails or validation errors occur
        """
        start_time = time.time()
        
        try:
            if not project_id or not isinstance(project_id, str):
                raise RepositoryError(
                    "Project ID must be a non-empty string"
                )
            
            if limit <= 0 or limit > 100:
                raise RepositoryError(
                    "Limit must be between 1 and 100"
                )
            
            self.logger.info(
                "Getting execution history for project",
                correlation_id=self.correlation_id,
                project_id=project_id,
                status=LogStatus.STARTED,
                limit=limit
            )
            
            # Query for events with task_context for this project
            query = self.session.query(Event).filter(
                Event.task_context.isnot(None)
            ).order_by(desc(Event.updated_at)).limit(limit * 3)  # Get more to filter
            
            history_projections = []
            
            for event in query:
                task_context = event.task_context or {}
                metadata = task_context.get('metadata', {})
                event_project_id = metadata.get('project_id')
                
                # Skip if not matching project
                if event_project_id != project_id:
                    continue
                
                try:
                    # Project status from task_context using utility from Task 5.2.1
                    # Convert SQLAlchemy column to dict
                    task_context_dict = event.task_context if isinstance(event.task_context, dict) else {}
                    status_projection = project_status_from_task_context(
                        task_context=task_context_dict,
                        execution_id=str(event.id),
                        project_id=project_id
                    )
                    
                    history_projections.append(status_projection)
                    
                    # Stop if we have enough history
                    if len(history_projections) >= limit:
                        break
                        
                except Exception as e:
                    # Log but continue processing other events
                    self.logger.warn(
                        "Failed to project status for historical event",
                        correlation_id=self.correlation_id,
                        project_id=project_id,
                        event_id=str(event.id),
                        error=str(e)
                    )
                    continue
            
            self.logger.info(
                "Execution history retrieved successfully",
                correlation_id=self.correlation_id,
                project_id=project_id,
                status=LogStatus.COMPLETED,
                history_count=len(history_projections),
                duration_ms=round((time.time() - start_time) * 1000, 2)
            )
            
            return history_projections
            
        except RepositoryError:
            raise
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(
                "Failed to get execution history",
                correlation_id=self.correlation_id,
                project_id=project_id,
                status=LogStatus.FAILED,
                duration_ms=round(duration_ms, 2),
                error=e
            )
            raise RepositoryError(
                f"Failed to get execution history: {str(e)}"
            )
    
    @log_performance(get_structured_logger(__name__), "update_status_projection_to_completed")
    def update_status_projection_to_completed(
        self,
        execution_id: str,
        project_id: str,
        completion_metadata: Optional[Dict[str, Any]] = None
    ) -> StatusProjection:
        """
        Update status projection to completed state after successful git push operation.
        
        This method updates the Event.task_context to mark all workflow nodes as completed,
        sets progress to 100%, and broadcasts the completion status via WebSocket.
        
        Args:
            execution_id: Execution identifier to update
            project_id: Project identifier for validation and WebSocket routing
            completion_metadata: Optional metadata about the completion (commit hash, etc.)
            
        Returns:
            Updated StatusProjection instance
            
        Raises:
            RepositoryError: If database operation fails or validation errors occur
        """
        start_time = time.time()
        
        try:
            # Validate input parameters
            self._validate_update_parameters(execution_id, project_id)
            
            self.logger.info(
                "Starting status projection update to completed",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.STARTED,
                has_completion_metadata=completion_metadata is not None
            )
            
            # Get the current event and validate it exists
            event = self._get_event_for_update(execution_id, project_id)
            
            # Get current status projection for state transition validation
            current_projection = self._get_current_status_projection(event, execution_id, project_id)
            
            # Validate state transition to completed
            self._validate_completion_transition(current_projection)
            
            # Update task_context to completion state
            current_task_context = event.task_context if isinstance(event.task_context, dict) else {}
            updated_task_context = self._update_task_context_to_completed(
                current_task_context,
                completion_metadata
            )
            
            # Update the event in database using session operations
            self.session.query(Event).filter(Event.id == event.id).update({
                'task_context': updated_task_context,
                'updated_at': datetime.utcnow()
            })
            self.session.commit()
            
            # Get updated event
            updated_event = self.session.query(Event).filter(Event.id == event.id).first()
            
            # Generate updated status projection
            updated_projection = project_status_from_task_context(
                task_context=updated_task_context,
                execution_id=execution_id,
                project_id=project_id
            )
            
            # Calculate total duration
            total_duration = (time.time() - start_time) * 1000
            
            # Broadcast completion status via WebSocket (async operation)
            self._broadcast_completion_status(updated_projection, total_duration)
            
            self.logger.info(
                "Status projection updated to completed successfully",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.COMPLETED,
                final_progress=updated_projection.progress,
                completed_tasks=updated_projection.totals.completed,
                total_tasks=updated_projection.totals.total,
                duration_ms=round(total_duration, 2),
                performance_target_met=total_duration <= 2000  # ≤2s requirement
            )
            
            return updated_projection
            
        except RepositoryError:
            raise
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(
                "Failed to update status projection to completed",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.FAILED,
                duration_ms=round(duration_ms, 2),
                error=e
            )
            raise RepositoryError(
                f"Failed to update status projection to completed: {str(e)}"
            )
    
    def _validate_update_parameters(self, execution_id: str, project_id: str) -> None:
        """
        Validate parameters for status projection update.
        
        Args:
            execution_id: Execution identifier to validate
            project_id: Project identifier to validate
            
        Raises:
            RepositoryError: If validation fails
        """
        if not execution_id or not isinstance(execution_id, str) or not execution_id.strip():
            raise RepositoryError("Execution ID must be a non-empty string")
        
        if not project_id or not isinstance(project_id, str) or not project_id.strip():
            raise RepositoryError("Project ID must be a non-empty string")
        
        # Validate project ID format for security
        import re
        if not re.match(r'^[a-zA-Z0-9_/-]+$', project_id):
            raise RepositoryError(
                "Project ID contains invalid characters. Must contain only alphanumeric characters, underscores, hyphens, and forward slashes"
            )
    
    def _get_event_for_update(self, execution_id: str, project_id: str) -> Event:
        """
        Get event for status update with validation.
        
        Args:
            execution_id: Execution identifier
            project_id: Project identifier for validation
            
        Returns:
            Event instance
            
        Raises:
            RepositoryError: If event not found or invalid
        """
        try:
            event = self.repository.get(execution_id)
        except Exception:
            # If direct lookup fails, search by string representation
            event = self.session.query(Event).filter(
                Event.id.cast(String) == execution_id
            ).first()
        
        if not event:
            raise RepositoryError(
                f"Event not found for execution ID: {execution_id}"
            )
        
        # Check if task_context is None or empty (handle SQLAlchemy column properly)
        task_context_value = event.task_context
        if task_context_value is None:
            raise RepositoryError(
                f"Event has no task_context for execution ID: {execution_id}"
            )
        
        # Convert to dict and check if empty
        if isinstance(task_context_value, dict) and len(task_context_value) == 0:
            raise RepositoryError(
                f"Event has empty task_context for execution ID: {execution_id}"
            )
        
        # Validate project ID matches
        task_context = event.task_context or {}
        metadata = task_context.get('metadata', {})
        event_project_id = metadata.get('project_id')
        
        if event_project_id and event_project_id != project_id:
            raise RepositoryError(
                f"Project ID mismatch: expected {project_id}, found {event_project_id}"
            )
        
        return event
    
    def _get_current_status_projection(self, event: Event, execution_id: str, project_id: str) -> StatusProjection:
        """
        Get current status projection for state validation.
        
        Args:
            event: Event instance
            execution_id: Execution identifier
            project_id: Project identifier
            
        Returns:
            Current StatusProjection
        """
        task_context_dict = event.task_context if isinstance(event.task_context, dict) else {}
        return project_status_from_task_context(
            task_context=task_context_dict,
            execution_id=execution_id,
            project_id=project_id
        )
    
    def _validate_completion_transition(self, current_projection: StatusProjection) -> None:
        """
        Validate that transition to completed status is valid.
        
        Args:
            current_projection: Current status projection
            
        Raises:
            RepositoryError: If transition is invalid
        """
        current_status = current_projection.status
        
        # Check if already completed (idempotent operation)
        if current_status == ExecutionStatus.COMPLETED:
            self.logger.info(
                "Status projection already completed - idempotent operation",
                correlation_id=self.correlation_id,
                project_id=current_projection.project_id,
                execution_id=current_projection.execution_id,
                current_status=current_status.value
            )
            return
        
        # Validate state transition using existing utility
        if not validate_status_transition(current_status.value, ExecutionStatus.COMPLETED.value):
            raise RepositoryError(
                f"Invalid state transition from {current_status.value} to {ExecutionStatus.COMPLETED.value}. "
                f"Valid transitions from {current_status.value} are defined in ADD Profile B."
            )
    
    def _update_task_context_to_completed(
        self,
        task_context: Dict[str, Any],
        completion_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update task_context to reflect completion state.
        
        Args:
            task_context: Current task context
            completion_metadata: Optional completion metadata
            
        Returns:
            Updated task context dictionary
        """
        # Create a deep copy to avoid modifying the original
        import copy
        updated_context = copy.deepcopy(task_context)
        
        # Update metadata
        metadata = updated_context.setdefault('metadata', {})
        metadata['status'] = 'completed'
        metadata['completed_at'] = datetime.utcnow().isoformat() + "Z"
        
        # Add completion metadata if provided
        if completion_metadata:
            metadata.update(completion_metadata)
        
        # Update all nodes to completed status
        nodes = updated_context.setdefault('nodes', {})
        for node_id, node_data in nodes.items():
            if isinstance(node_data, dict):
                node_data['status'] = 'completed'
                if 'completed_at' not in node_data:
                    node_data['completed_at'] = datetime.utcnow().isoformat() + "Z"
        
        return updated_context
    
    def _broadcast_completion_status(self, projection: StatusProjection, duration_ms: float) -> None:
        """
        Broadcast completion status via WebSocket.
        
        Args:
            projection: Updated status projection
            duration_ms: Operation duration for performance monitoring
        """
        try:
            # Create execution update envelope for completion
            update_envelope = create_execution_update_envelope(
                project_id=projection.project_id,
                execution_id=projection.execution_id,
                status=projection.status.value,
                progress=projection.progress,
                current_task=projection.current_task or "",
                totals={
                    "completed": projection.totals.completed,
                    "total": projection.totals.total
                },
                branch=projection.branch,
                updated_at=projection.updated_at.isoformat() + "Z" if projection.updated_at else None,
                event_type="completion"
            )
            
            # Create completion envelope
            completion_envelope = create_completion_envelope(
                project_id=projection.project_id,
                execution_id=projection.execution_id,
                status=projection.status.value,
                final_result="success",
                duration_ms=duration_ms,
                completed_tasks=projection.totals.completed,
                total_tasks=projection.totals.total
            )
            
            # Broadcast both messages (fire-and-forget for performance)
            import asyncio
            
            async def broadcast_messages():
                broadcast_start = time.time()
                
                # Broadcast execution update
                await broadcast_to_project(update_envelope, projection.project_id)
                
                # Broadcast completion
                await broadcast_to_project(completion_envelope, projection.project_id)
                
                broadcast_duration = (time.time() - broadcast_start) * 1000
                
                self.logger.info(
                    "WebSocket completion status broadcast completed",
                    correlation_id=self.correlation_id,
                    project_id=projection.project_id,
                    execution_id=projection.execution_id,
                    broadcast_duration_ms=round(broadcast_duration, 2),
                    performance_target_met=broadcast_duration <= 500  # ≤500ms requirement
                )
            
            # Schedule async broadcast (non-blocking)
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(broadcast_messages())
            except RuntimeError:
                # If no event loop is running, create a new one
                asyncio.create_task(broadcast_messages())
                
        except Exception as e:
            # Log error but don't fail the main operation
            self.logger.warn(
                "Failed to broadcast completion status via WebSocket",
                correlation_id=self.correlation_id,
                project_id=projection.project_id,
                execution_id=projection.execution_id,
                error=str(e)
            )


def get_status_projection_service(
    session: Session,
    correlation_id: Optional[str] = None
) -> StatusProjectionService:
    """
    Factory function to get a status projection service instance.
    
    Args:
        session: Database session for operations
        correlation_id: Optional correlation ID for distributed tracing
        
    Returns:
        StatusProjectionService instance
    """
    return StatusProjectionService(session=session, correlation_id=correlation_id)