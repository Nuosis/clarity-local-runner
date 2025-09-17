"""
Execution Update Service Module

This module provides real-time execution update broadcasting via WebSocket connections.
It monitors workflow status changes and sends execution-update frames with ≤500ms latency
to connected clients following the established message envelope format.

Primary Responsibility: Real-time execution status broadcasting with performance optimization
"""

import asyncio
import time
from datetime import datetime
from typing import Optional, Dict, Any

from core.structured_logging import get_structured_logger, LogStatus
from schemas.status_projection_schema import project_status_from_task_context, ExecutionStatus
from schemas.websocket_envelope import create_execution_update_envelope
from api.v1.endpoints.websocket import broadcast_to_project


class ExecutionUpdateService:
    """
    Service for broadcasting real-time execution updates via WebSocket.
    
    This service monitors workflow execution status changes and broadcasts
    execution-update messages to connected WebSocket clients with ≤500ms latency.
    It integrates with the existing WebSocket infrastructure and follows the
    established message envelope format.
    """
    
    def __init__(self, correlation_id: Optional[str] = None):
        """
        Initialize execution update service.
        
        Args:
            correlation_id: Optional correlation ID for distributed tracing
        """
        self.logger = get_structured_logger(__name__)
        self.correlation_id = correlation_id
        
        # Set persistent context for logging
        if correlation_id:
            self.logger.set_context(correlationId=correlation_id)
    
    async def send_execution_update(
        self,
        project_id: str,
        task_context: Dict[str, Any],
        execution_id: str,
        event_type: str = "status_change"
    ) -> None:
        """
        Send execution-update frame to WebSocket connections for a project.
        
        This method projects status from task_context and broadcasts execution-update
        messages to all WebSocket connections for the specified project with ≤500ms latency.
        
        Args:
            project_id: Project identifier for routing messages
            task_context: Task context containing workflow execution state
            execution_id: Unique execution identifier
            event_type: Type of event triggering the update (default: "status_change")
        """
        start_time = time.time()
        
        try:
            if not project_id or not isinstance(project_id, str):
                self.logger.error(
                    "Invalid project_id for execution update",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    error_message="Project ID must be a non-empty string"
                )
                return
            
            self.logger.info(
                "Sending execution update",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                event_type=event_type,
                status=LogStatus.STARTED
            )
            
            # Project status from task_context using utility from Task 5.2.1
            try:
                status_projection = project_status_from_task_context(
                    task_context=task_context,
                    execution_id=execution_id,
                    project_id=project_id
                )
            except Exception as e:
                self.logger.error(
                    "Failed to project status from task context",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    error_message=str(e)
                )
                return
            
            # Build execution-update message using standardized envelope utility
            execution_update_message = create_execution_update_envelope(
                project_id=project_id,
                execution_id=execution_id,
                status=status_projection.status.value if hasattr(status_projection.status, 'value') else str(status_projection.status),
                progress=status_projection.progress,
                current_task=status_projection.current_task or "unknown",
                totals={
                    "completed": status_projection.totals.completed,
                    "total": status_projection.totals.total
                },
                branch=status_projection.branch,
                updated_at=status_projection.updated_at.isoformat() + "Z" if status_projection.updated_at else None,
                event_type=event_type
            )
            
            # Broadcast to all WebSocket connections for this project
            await broadcast_to_project(execution_update_message, project_id)
            
            # Calculate and log performance metrics
            duration_ms = (time.time() - start_time) * 1000
            performance_target_met = duration_ms <= 500
            
            self.logger.info(
                "Execution update sent successfully",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                event_type=event_type,
                status=LogStatus.COMPLETED,
                duration_ms=round(duration_ms, 2),
                performance_target_met=performance_target_met,
                projection_status=status_projection.status.value if hasattr(status_projection.status, 'value') else str(status_projection.status),
                progress=status_projection.progress
            )
            
            # Log performance warning if target not met
            if not performance_target_met:
                self.logger.warn(
                    "Execution update latency exceeded 500ms target",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    duration_ms=round(duration_ms, 2),
                    target_ms=500
                )
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(
                "Failed to send execution update",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                event_type=event_type,
                status=LogStatus.FAILED,
                duration_ms=round(duration_ms, 2),
                error_message=str(e),
                exc_info=True
            )
    
    async def send_node_status_update(
        self,
        project_id: str,
        task_context: Dict[str, Any],
        execution_id: str,
        node_name: str,
        node_status: str
    ) -> None:
        """
        Send execution-update for node status changes.
        
        This method sends targeted updates when individual workflow nodes
        change status, providing granular progress tracking.
        
        Args:
            project_id: Project identifier for routing messages
            task_context: Task context containing workflow execution state
            execution_id: Unique execution identifier
            node_name: Name of the node that changed status
            node_status: New status of the node
        """
        await self.send_execution_update(
            project_id=project_id,
            task_context=task_context,
            execution_id=execution_id,
            event_type=f"node_{node_status}"
        )
        
        self.logger.info(
            "Node status update sent",
            correlation_id=self.correlation_id,
            project_id=project_id,
            execution_id=execution_id,
            node_name=node_name,
            node_status=node_status
        )
    
    async def send_workflow_completion_update(
        self,
        project_id: str,
        task_context: Dict[str, Any],
        execution_id: str,
        completion_status: str
    ) -> None:
        """
        Send execution-update for workflow completion.
        
        This method sends updates when workflows complete, either successfully
        or with errors, providing final status information.
        
        Args:
            project_id: Project identifier for routing messages
            task_context: Task context containing workflow execution state
            execution_id: Unique execution identifier
            completion_status: Final completion status (completed, error, stopped)
        """
        await self.send_execution_update(
            project_id=project_id,
            task_context=task_context,
            execution_id=execution_id,
            event_type=f"workflow_{completion_status}"
        )
        
        self.logger.info(
            "Workflow completion update sent",
            correlation_id=self.correlation_id,
            project_id=project_id,
            execution_id=execution_id,
            completion_status=completion_status
        )


def get_execution_update_service(correlation_id: Optional[str] = None) -> ExecutionUpdateService:
    """
    Factory function to get an execution update service instance.
    
    Args:
        correlation_id: Optional correlation ID for distributed tracing
        
    Returns:
        ExecutionUpdateService instance
    """
    return ExecutionUpdateService(correlation_id=correlation_id)


# Utility function for easy integration
async def send_execution_update(
    project_id: str,
    task_context: Dict[str, Any],
    execution_id: str,
    event_type: str = "status_change",
    correlation_id: Optional[str] = None
) -> None:
    """
    Utility function to send execution updates without service instantiation.
    
    Args:
        project_id: Project identifier for routing messages
        task_context: Task context containing workflow execution state
        execution_id: Unique execution identifier
        event_type: Type of event triggering the update
        correlation_id: Optional correlation ID for distributed tracing
    """
    service = get_execution_update_service(correlation_id=correlation_id)
    await service.send_execution_update(
        project_id=project_id,
        task_context=task_context,
        execution_id=execution_id,
        event_type=event_type
    )