"""
Execution Log Service Module

This module provides real-time execution log broadcasting via WebSocket connections.
It captures structured log entries from workflow execution and sends execution-log frames 
with ≤500ms latency to connected clients following the established message envelope format.

Primary Responsibility: Real-time execution log broadcasting with performance optimization
"""

import asyncio
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from core.structured_logging import get_structured_logger, LogStatus, LogLevel
from schemas.websocket_envelope import create_execution_log_envelope
from api.v1.endpoints.websocket import broadcast_to_project


class LogEntryType(Enum):
    """Types of log entries that can be broadcast."""
    TASK_RECEIPT = "task_receipt"
    NODE_START = "node_start"
    NODE_COMPLETE = "node_complete"
    NODE_ERROR = "node_error"
    WORKFLOW_START = "workflow_start"
    WORKFLOW_COMPLETE = "workflow_complete"
    WORKFLOW_ERROR = "workflow_error"
    OPERATION_LOG = "operation_log"
    DEBUG_LOG = "debug_log"
    INFO_LOG = "info_log"
    WARN_LOG = "warn_log"
    ERROR_LOG = "error_log"


class ExecutionLogService:
    """
    Service for broadcasting real-time execution logs via WebSocket.
    
    This service captures structured log entries from workflow execution and broadcasts
    execution-log messages to connected WebSocket clients with ≤500ms latency.
    It integrates with the existing WebSocket infrastructure and follows the
    established message envelope format.
    """
    
    def __init__(self, correlation_id: Optional[str] = None):
        """
        Initialize execution log service.
        
        Args:
            correlation_id: Optional correlation ID for distributed tracing
        """
        self.logger = get_structured_logger(__name__)
        self.correlation_id = correlation_id
        
        # Set persistent context for logging
        if correlation_id:
            self.logger.set_context(correlationId=correlation_id)
    
    async def send_execution_log(
        self,
        project_id: str,
        execution_id: str,
        log_entry_type: LogEntryType,
        message: str,
        level: LogLevel = LogLevel.INFO,
        node_name: Optional[str] = None,
        task_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Send execution-log frame to WebSocket connections for a project.
        
        This method captures structured log entries and broadcasts execution-log
        messages to all WebSocket connections for the specified project with ≤500ms latency.
        
        Args:
            project_id: Project identifier for routing messages
            execution_id: Unique execution identifier
            log_entry_type: Type of log entry being broadcast
            message: Log message content
            level: Log level (DEBUG, INFO, WARN, ERROR)
            node_name: Optional name of the workflow node
            task_id: Optional task identifier
            additional_data: Optional additional data to include in the log entry
        """
        start_time = time.time()
        
        try:
            if not project_id or not isinstance(project_id, str):
                self.logger.error(
                    "Invalid project_id for execution log",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    error_message="Project ID must be a non-empty string"
                )
                return
            
            self.logger.debug(
                "Sending execution log",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                log_entry_type=log_entry_type.value,
                level=level.value,
                status=LogStatus.STARTED
            )
            
            # Build execution-log message using standardized envelope utility
            execution_log_message = create_execution_log_envelope(
                project_id=project_id,
                execution_id=execution_id,
                log_entry_type=log_entry_type.value,
                level=level.value,
                message=message,
                node_name=node_name,
                task_id=task_id,
                additional_data=additional_data
            )
            
            # Broadcast to all WebSocket connections for this project
            await broadcast_to_project(execution_log_message, project_id)
            
            # Calculate and log performance metrics
            duration_ms = (time.time() - start_time) * 1000
            performance_target_met = duration_ms <= 500
            
            self.logger.debug(
                "Execution log sent successfully",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                log_entry_type=log_entry_type.value,
                level=level.value,
                status=LogStatus.COMPLETED,
                duration_ms=round(duration_ms, 2),
                performance_target_met=performance_target_met
            )
            
            # Log performance warning if target not met
            if not performance_target_met:
                self.logger.warn(
                    "Execution log latency exceeded 500ms target",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    duration_ms=round(duration_ms, 2),
                    target_ms=500
                )
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(
                "Failed to send execution log",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                log_entry_type=log_entry_type.value if log_entry_type else "unknown",
                level=level.value if level else "unknown",
                status=LogStatus.FAILED,
                duration_ms=round(duration_ms, 2),
                error_message=str(e),
                exc_info=True
            )
    
    async def send_task_receipt_log(
        self,
        project_id: str,
        execution_id: str,
        task_id: str,
        event_id: str,
        event_type: str
    ) -> None:
        """
        Send execution-log for task receipt events.
        
        Args:
            project_id: Project identifier for routing messages
            execution_id: Unique execution identifier
            task_id: Task identifier
            event_id: Event identifier
            event_type: Type of event being processed
        """
        await self.send_execution_log(
            project_id=project_id,
            execution_id=execution_id,
            log_entry_type=LogEntryType.TASK_RECEIPT,
            message=f"Task received for processing: {event_type}",
            level=LogLevel.INFO,
            task_id=task_id,
            additional_data={
                "event_id": event_id,
                "event_type": event_type
            }
        )
    
    async def send_node_start_log(
        self,
        project_id: str,
        execution_id: str,
        node_name: str,
        task_id: Optional[str] = None
    ) -> None:
        """
        Send execution-log for node start events.
        
        Args:
            project_id: Project identifier for routing messages
            execution_id: Unique execution identifier
            node_name: Name of the node starting
            task_id: Optional task identifier
        """
        await self.send_execution_log(
            project_id=project_id,
            execution_id=execution_id,
            log_entry_type=LogEntryType.NODE_START,
            message=f"Starting node: {node_name}",
            level=LogLevel.INFO,
            node_name=node_name,
            task_id=task_id
        )
    
    async def send_node_complete_log(
        self,
        project_id: str,
        execution_id: str,
        node_name: str,
        task_id: Optional[str] = None,
        duration_ms: Optional[float] = None
    ) -> None:
        """
        Send execution-log for node completion events.
        
        Args:
            project_id: Project identifier for routing messages
            execution_id: Unique execution identifier
            node_name: Name of the node that completed
            task_id: Optional task identifier
            duration_ms: Optional duration in milliseconds
        """
        additional_data = {}
        if duration_ms is not None:
            additional_data["duration_ms"] = round(duration_ms, 2)
            
        await self.send_execution_log(
            project_id=project_id,
            execution_id=execution_id,
            log_entry_type=LogEntryType.NODE_COMPLETE,
            message=f"Finished node: {node_name}",
            level=LogLevel.INFO,
            node_name=node_name,
            task_id=task_id,
            additional_data=additional_data
        )
    
    async def send_node_error_log(
        self,
        project_id: str,
        execution_id: str,
        node_name: str,
        error_message: str,
        task_id: Optional[str] = None
    ) -> None:
        """
        Send execution-log for node error events.
        
        Args:
            project_id: Project identifier for routing messages
            execution_id: Unique execution identifier
            node_name: Name of the node that errored
            error_message: Error message
            task_id: Optional task identifier
        """
        await self.send_execution_log(
            project_id=project_id,
            execution_id=execution_id,
            log_entry_type=LogEntryType.NODE_ERROR,
            message=f"Error in node {node_name}: {error_message}",
            level=LogLevel.ERROR,
            node_name=node_name,
            task_id=task_id,
            additional_data={
                "error_message": error_message
            }
        )
    
    async def send_workflow_start_log(
        self,
        project_id: str,
        execution_id: str,
        workflow_type: str,
        task_id: Optional[str] = None
    ) -> None:
        """
        Send execution-log for workflow start events.
        
        Args:
            project_id: Project identifier for routing messages
            execution_id: Unique execution identifier
            workflow_type: Type of workflow starting
            task_id: Optional task identifier
        """
        await self.send_execution_log(
            project_id=project_id,
            execution_id=execution_id,
            log_entry_type=LogEntryType.WORKFLOW_START,
            message=f"Starting workflow: {workflow_type}",
            level=LogLevel.INFO,
            task_id=task_id,
            additional_data={
                "workflow_type": workflow_type
            }
        )
    
    async def send_workflow_complete_log(
        self,
        project_id: str,
        execution_id: str,
        workflow_type: str,
        task_id: Optional[str] = None,
        duration_ms: Optional[float] = None
    ) -> None:
        """
        Send execution-log for workflow completion events.
        
        Args:
            project_id: Project identifier for routing messages
            execution_id: Unique execution identifier
            workflow_type: Type of workflow that completed
            task_id: Optional task identifier
            duration_ms: Optional duration in milliseconds
        """
        additional_data = {"workflow_type": workflow_type}
        if duration_ms is not None:
            additional_data["duration_ms"] = round(duration_ms, 2)
            
        await self.send_execution_log(
            project_id=project_id,
            execution_id=execution_id,
            log_entry_type=LogEntryType.WORKFLOW_COMPLETE,
            message=f"Workflow completed: {workflow_type}",
            level=LogLevel.INFO,
            task_id=task_id,
            additional_data=additional_data
        )
    
    async def send_workflow_error_log(
        self,
        project_id: str,
        execution_id: str,
        workflow_type: str,
        error_message: str,
        task_id: Optional[str] = None
    ) -> None:
        """
        Send execution-log for workflow error events.
        
        Args:
            project_id: Project identifier for routing messages
            execution_id: Unique execution identifier
            workflow_type: Type of workflow that errored
            error_message: Error message
            task_id: Optional task identifier
        """
        await self.send_execution_log(
            project_id=project_id,
            execution_id=execution_id,
            log_entry_type=LogEntryType.WORKFLOW_ERROR,
            message=f"Workflow error in {workflow_type}: {error_message}",
            level=LogLevel.ERROR,
            task_id=task_id,
            additional_data={
                "workflow_type": workflow_type,
                "error_message": error_message
            }
        )
    
    async def send_operation_log(
        self,
        project_id: str,
        execution_id: str,
        operation: str,
        message: str,
        level: LogLevel = LogLevel.INFO,
        node_name: Optional[str] = None,
        task_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Send execution-log for general operation events.
        
        Args:
            project_id: Project identifier for routing messages
            execution_id: Unique execution identifier
            operation: Name of the operation
            message: Log message
            level: Log level
            node_name: Optional name of the workflow node
            task_id: Optional task identifier
            additional_data: Optional additional data
        """
        log_data = {"operation": operation}
        if additional_data:
            log_data.update(additional_data)
            
        await self.send_execution_log(
            project_id=project_id,
            execution_id=execution_id,
            log_entry_type=LogEntryType.OPERATION_LOG,
            message=message,
            level=level,
            node_name=node_name,
            task_id=task_id,
            additional_data=log_data
        )


def get_execution_log_service(correlation_id: Optional[str] = None) -> ExecutionLogService:
    """
    Factory function to get an execution log service instance.
    
    Args:
        correlation_id: Optional correlation ID for distributed tracing
        
    Returns:
        ExecutionLogService instance
    """
    return ExecutionLogService(correlation_id=correlation_id)


# Utility function for easy integration
async def send_execution_log(
    project_id: str,
    execution_id: str,
    log_entry_type: LogEntryType,
    message: str,
    level: LogLevel = LogLevel.INFO,
    node_name: Optional[str] = None,
    task_id: Optional[str] = None,
    additional_data: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None
) -> None:
    """
    Utility function to send execution logs without service instantiation.
    
    Args:
        project_id: Project identifier for routing messages
        execution_id: Unique execution identifier
        log_entry_type: Type of log entry being broadcast
        message: Log message content
        level: Log level (DEBUG, INFO, WARN, ERROR)
        node_name: Optional name of the workflow node
        task_id: Optional task identifier
        additional_data: Optional additional data to include
        correlation_id: Optional correlation ID for distributed tracing
    """
    service = get_execution_log_service(correlation_id=correlation_id)
    await service.send_execution_log(
        project_id=project_id,
        execution_id=execution_id,
        log_entry_type=log_entry_type,
        message=message,
        level=level,
        node_name=node_name,
        task_id=task_id,
        additional_data=additional_data
    )