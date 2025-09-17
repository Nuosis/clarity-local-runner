"""
Core Exception Classes for Clarity Local Runner

This module defines comprehensive custom exception classes for different failure scenarios
throughout the task_context processing pipeline, providing clear error categorization
and structured error information for debugging and monitoring.

The exception hierarchy follows the principle of specific error types for different
failure scenarios while maintaining backward compatibility with existing error handling.
"""

import time
from typing import Any, Dict, List, Optional, Union
from datetime import datetime


class ClarityBaseException(Exception):
    """
    Base exception class for all Clarity Local Runner exceptions.
    
    Provides common functionality for error tracking, correlation IDs,
    and structured error information.
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        correlation_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize base exception with structured error information.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code for programmatic handling
            correlation_id: Correlation ID for distributed tracing
            execution_id: Execution ID if available
            context: Additional context information for debugging
            cause: Original exception that caused this error (if any)
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__.upper()
        self.correlation_id = correlation_id
        self.execution_id = execution_id
        self.context = context or {}
        self.cause = cause
        self.timestamp = datetime.utcnow()
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for structured logging and API responses.
        
        Returns:
            Dictionary representation of the exception
        """
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "correlation_id": self.correlation_id,
            "execution_id": self.execution_id,
            "context": self.context,
            "timestamp": self.timestamp.isoformat() + "Z",
            "cause": str(self.cause) if self.cause else None
        }
    
    def __str__(self) -> str:
        """String representation with error code and correlation ID."""
        parts = [f"[{self.error_code}]", self.message]
        if self.correlation_id:
            parts.append(f"(correlation_id: {self.correlation_id})")
        return " ".join(parts)


# Task Context Transformation Exceptions

class TaskContextTransformationError(ClarityBaseException):
    """
    Base exception for task context transformation failures.
    
    This is the parent class for all transformation-related errors,
    providing common functionality for transformation error scenarios.
    """
    
    def __init__(
        self,
        message: str,
        task_context: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize transformation error with task context information.
        
        Args:
            message: Error message
            task_context: The task_context that caused the error
            **kwargs: Additional arguments passed to base class
        """
        # Add task context information to context
        context = kwargs.get('context', {})
        if task_context is not None:
            context.update({
                "task_context_type": type(task_context).__name__,
                "task_context_keys": list(task_context.keys()) if isinstance(task_context, dict) else None,
                "task_context_size": len(str(task_context)) if task_context else 0
            })
        kwargs['context'] = context
        
        super().__init__(message, **kwargs)
        self.task_context = task_context


class InvalidTaskContextError(TaskContextTransformationError):
    """
    Raised when task_context structure is invalid or malformed.
    
    This exception is raised when the task_context is not a dictionary,
    is None when required, or has an invalid structure that prevents processing.
    """
    
    def __init__(
        self,
        message: str = "Task context structure is invalid",
        task_context: Optional[Any] = None,
        expected_type: str = "dict",
        **kwargs
    ):
        """
        Initialize invalid task context error.
        
        Args:
            message: Error message
            task_context: The invalid task_context
            expected_type: Expected type for the task_context
            **kwargs: Additional arguments
        """
        context = kwargs.get('context', {})
        context.update({
            "expected_type": expected_type,
            "actual_type": type(task_context).__name__ if task_context is not None else "None",
            "is_none": task_context is None,
            "is_empty": not bool(task_context) if task_context is not None else True
        })
        kwargs['context'] = context
        kwargs['error_code'] = kwargs.get('error_code', 'INVALID_TASK_CONTEXT')
        
        super().__init__(message, task_context=task_context, **kwargs)


class NodeDataError(TaskContextTransformationError):
    """
    Raised when node data is malformed or contains invalid values.
    
    This exception is raised when individual nodes in the task_context
    have invalid structures, missing required fields, or malformed data.
    """
    
    def __init__(
        self,
        message: str = "Node data is malformed",
        node_id: Optional[str] = None,
        node_data: Optional[Any] = None,
        **kwargs
    ):
        """
        Initialize node data error.
        
        Args:
            message: Error message
            node_id: ID of the problematic node
            node_data: The malformed node data
            **kwargs: Additional arguments
        """
        context = kwargs.get('context', {})
        context.update({
            "node_id": node_id,
            "node_data_type": type(node_data).__name__ if node_data is not None else "None",
            "node_data_keys": list(node_data.keys()) if isinstance(node_data, dict) else None
        })
        kwargs['context'] = context
        kwargs['error_code'] = kwargs.get('error_code', 'NODE_DATA_ERROR')
        
        super().__init__(message, **kwargs)
        self.node_id = node_id
        self.node_data = node_data


class StatusCalculationError(TaskContextTransformationError):
    """
    Raised when status calculation fails due to invalid enum values or logic errors.
    
    This exception is raised when the status calculation logic encounters
    invalid status values, conflicting states, or other calculation errors.
    """
    
    def __init__(
        self,
        message: str = "Status calculation failed",
        invalid_status: Optional[str] = None,
        valid_statuses: Optional[List[str]] = None,
        **kwargs
    ):
        """
        Initialize status calculation error.
        
        Args:
            message: Error message
            invalid_status: The invalid status value that caused the error
            valid_statuses: List of valid status values
            **kwargs: Additional arguments
        """
        context = kwargs.get('context', {})
        context.update({
            "invalid_status": invalid_status,
            "valid_statuses": valid_statuses,
            "status_type": type(invalid_status).__name__ if invalid_status is not None else "None"
        })
        kwargs['context'] = context
        kwargs['error_code'] = kwargs.get('error_code', 'STATUS_CALCULATION_ERROR')
        
        super().__init__(message, **kwargs)
        self.invalid_status = invalid_status
        self.valid_statuses = valid_statuses


class FieldExtractionError(TaskContextTransformationError):
    """
    Raised when required field extraction fails from task_context or metadata.
    
    This exception is raised when required fields cannot be extracted from
    the task_context, metadata, or node data structures.
    """
    
    def __init__(
        self,
        message: str = "Required field extraction failed",
        field_name: Optional[str] = None,
        attempted_fields: Optional[List[str]] = None,
        source_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize field extraction error.
        
        Args:
            message: Error message
            field_name: Name of the field that failed to extract
            attempted_fields: List of field names that were attempted
            source_data: The source data structure where extraction was attempted
            **kwargs: Additional arguments
        """
        context = kwargs.get('context', {})
        context.update({
            "field_name": field_name,
            "attempted_fields": attempted_fields,
            "source_data_keys": list(source_data.keys()) if isinstance(source_data, dict) else None,
            "source_data_type": type(source_data).__name__ if source_data is not None else "None"
        })
        kwargs['context'] = context
        kwargs['error_code'] = kwargs.get('error_code', 'FIELD_EXTRACTION_ERROR')
        
        super().__init__(message, **kwargs)
        self.field_name = field_name
        self.attempted_fields = attempted_fields
        self.source_data = source_data


class SchemaValidationError(TaskContextTransformationError):
    """
    Raised when StatusProjection schema validation fails.
    
    This exception is raised when the generated StatusProjection object
    fails Pydantic validation due to constraint violations or invalid data.
    """
    
    def __init__(
        self,
        message: str = "Schema validation failed",
        validation_errors: Optional[List[Dict[str, Any]]] = None,
        field_errors: Optional[Dict[str, str]] = None,
        **kwargs
    ):
        """
        Initialize schema validation error.
        
        Args:
            message: Error message
            validation_errors: List of Pydantic validation errors
            field_errors: Dictionary of field-specific errors
            **kwargs: Additional arguments
        """
        context = kwargs.get('context', {})
        context.update({
            "validation_errors": validation_errors,
            "field_errors": field_errors,
            "error_count": len(validation_errors) if validation_errors else 0
        })
        kwargs['context'] = context
        kwargs['error_code'] = kwargs.get('error_code', 'SCHEMA_VALIDATION_ERROR')
        
        super().__init__(message, **kwargs)
        self.validation_errors = validation_errors
        self.field_errors = field_errors


# API and Service Layer Exceptions

class APIError(ClarityBaseException):
    """
    Base exception for API-related errors.
    
    This is the parent class for all API endpoint errors,
    providing common functionality for HTTP error responses.
    """
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize API error with HTTP status code.
        
        Args:
            message: Error message
            status_code: HTTP status code
            error_code: Machine-readable error code
            **kwargs: Additional arguments
        """
        context = kwargs.get('context', {})
        context.update({
            "status_code": status_code,
            "http_method": context.get('http_method'),
            "endpoint": context.get('endpoint'),
            "request_id": context.get('request_id')
        })
        kwargs['context'] = context
        
        super().__init__(message, error_code=error_code, **kwargs)
        self.status_code = status_code


class ValidationError(APIError):
    """
    Raised when API request validation fails.
    
    This exception is raised when incoming API requests fail validation,
    including parameter validation, schema validation, or business rule validation.
    """
    
    def __init__(
        self,
        message: str = "Request validation failed",
        field_errors: Optional[Dict[str, str]] = None,
        **kwargs
    ):
        """
        Initialize validation error.
        
        Args:
            message: Error message
            field_errors: Dictionary of field-specific validation errors
            **kwargs: Additional arguments
        """
        context = kwargs.get('context', {})
        context.update({
            "field_errors": field_errors,
            "validation_type": "request_validation"
        })
        kwargs['context'] = context
        kwargs['status_code'] = kwargs.get('status_code', 422)
        kwargs['error_code'] = kwargs.get('error_code', 'VALIDATION_ERROR')
        
        super().__init__(message, **kwargs)
        self.field_errors = field_errors


class ResourceNotFoundError(APIError):
    """
    Raised when requested resources are not found.
    
    This exception is raised when API endpoints cannot find the requested
    resources such as projects, executions, or status projections.
    """
    
    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize resource not found error.
        
        Args:
            message: Error message
            resource_type: Type of resource that was not found
            resource_id: ID of the resource that was not found
            **kwargs: Additional arguments
        """
        context = kwargs.get('context', {})
        context.update({
            "resource_type": resource_type,
            "resource_id": resource_id
        })
        kwargs['context'] = context
        kwargs['status_code'] = kwargs.get('status_code', 404)
        kwargs['error_code'] = kwargs.get('error_code', 'RESOURCE_NOT_FOUND')
        
        super().__init__(message, **kwargs)
        self.resource_type = resource_type
        self.resource_id = resource_id


class StateTransitionError(APIError):
    """
    Raised when invalid state transitions are attempted.
    
    This exception is raised when API endpoints attempt invalid state transitions
    such as pausing a completed automation or resuming a non-paused automation.
    """
    
    def __init__(
        self,
        message: str = "Invalid state transition",
        current_state: Optional[str] = None,
        requested_state: Optional[str] = None,
        valid_transitions: Optional[List[str]] = None,
        **kwargs
    ):
        """
        Initialize state transition error.
        
        Args:
            message: Error message
            current_state: Current state of the resource
            requested_state: Requested target state
            valid_transitions: List of valid transitions from current state
            **kwargs: Additional arguments
        """
        context = kwargs.get('context', {})
        context.update({
            "current_state": current_state,
            "requested_state": requested_state,
            "valid_transitions": valid_transitions,
            "transition": f"{current_state}→{requested_state}" if current_state and requested_state else None
        })
        kwargs['context'] = context
        kwargs['status_code'] = kwargs.get('status_code', 409)
        kwargs['error_code'] = kwargs.get('error_code', 'STATE_TRANSITION_ERROR')
        
        super().__init__(message, **kwargs)
        self.current_state = current_state
        self.requested_state = requested_state
        self.valid_transitions = valid_transitions


class ServiceError(ClarityBaseException):
    """
    Base exception for service layer errors.
    
    This is the parent class for all service layer errors,
    providing common functionality for service operation failures.
    """
    
    def __init__(
        self,
        message: str,
        service_name: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize service error.
        
        Args:
            message: Error message
            service_name: Name of the service that encountered the error
            operation: Operation that was being performed
            **kwargs: Additional arguments
        """
        context = kwargs.get('context', {})
        context.update({
            "service_name": service_name,
            "operation": operation
        })
        kwargs['context'] = context
        
        super().__init__(message, **kwargs)
        self.service_name = service_name
        self.operation = operation


class DatabaseError(ServiceError):
    """
    Raised when database operations fail.
    
    This exception is raised when database queries, connections,
    or transactions fail in the service layer.
    """
    
    def __init__(
        self,
        message: str = "Database operation failed",
        query_type: Optional[str] = None,
        table_name: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize database error.
        
        Args:
            message: Error message
            query_type: Type of database query (SELECT, INSERT, UPDATE, DELETE)
            table_name: Name of the database table involved
            **kwargs: Additional arguments
        """
        context = kwargs.get('context', {})
        context.update({
            "query_type": query_type,
            "table_name": table_name,
            "database_operation": True
        })
        kwargs['context'] = context
        kwargs['error_code'] = kwargs.get('error_code', 'DATABASE_ERROR')
        
        super().__init__(message, **kwargs)
        self.query_type = query_type
        self.table_name = table_name


class CacheError(ServiceError):
    """
    Raised when cache operations fail.
    
    This exception is raised when Redis or other cache operations
    fail in the service layer.
    """
    
    def __init__(
        self,
        message: str = "Cache operation failed",
        cache_key: Optional[str] = None,
        operation_type: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize cache error.
        
        Args:
            message: Error message
            cache_key: Cache key that was being accessed
            operation_type: Type of cache operation (GET, SET, DELETE)
            **kwargs: Additional arguments
        """
        context = kwargs.get('context', {})
        context.update({
            "cache_key": cache_key,
            "operation_type": operation_type,
            "cache_operation": True
        })
        kwargs['context'] = context
        kwargs['error_code'] = kwargs.get('error_code', 'CACHE_ERROR')
        
        super().__init__(message, **kwargs)
        self.cache_key = cache_key
        self.operation_type = operation_type


class ExternalServiceError(ServiceError):
    """
    Raised when external service communication fails.
    
    This exception is raised when communication with external services
    such as Git repositories, webhooks, or third-party APIs fails.
    """
    
    def __init__(
        self,
        message: str = "External service communication failed",
        service_url: Optional[str] = None,
        response_code: Optional[int] = None,
        timeout: Optional[float] = None,
        **kwargs
    ):
        """
        Initialize external service error.
        
        Args:
            message: Error message
            service_url: URL of the external service
            response_code: HTTP response code from the service
            timeout: Timeout value if the error was due to timeout
            **kwargs: Additional arguments
        """
        context = kwargs.get('context', {})
        context.update({
            "service_url": service_url,
            "response_code": response_code,
            "timeout": timeout,
            "external_service": True
        })
        kwargs['context'] = context
        kwargs['error_code'] = kwargs.get('error_code', 'EXTERNAL_SERVICE_ERROR')
        
        super().__init__(message, **kwargs)
        self.service_url = service_url
        self.response_code = response_code
        self.timeout = timeout


# Performance and Monitoring Exceptions

class PerformanceError(ClarityBaseException):
    """
    Raised when performance thresholds are exceeded.
    
    This exception is raised when operations exceed performance
    thresholds such as execution time, memory usage, or throughput limits.
    """
    
    def __init__(
        self,
        message: str = "Performance threshold exceeded",
        metric_name: Optional[str] = None,
        actual_value: Optional[Union[int, float]] = None,
        threshold_value: Optional[Union[int, float]] = None,
        unit: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize performance error.
        
        Args:
            message: Error message
            metric_name: Name of the performance metric
            actual_value: Actual measured value
            threshold_value: Threshold value that was exceeded
            unit: Unit of measurement (ms, MB, requests/sec, etc.)
            **kwargs: Additional arguments
        """
        context = kwargs.get('context', {})
        context.update({
            "metric_name": metric_name,
            "actual_value": actual_value,
            "threshold_value": threshold_value,
            "unit": unit,
            "performance_violation": True,
            "exceeded_by": actual_value - threshold_value if actual_value and threshold_value else None
        })
        kwargs['context'] = context
        kwargs['error_code'] = kwargs.get('error_code', 'PERFORMANCE_ERROR')
        
        super().__init__(message, **kwargs)
        self.metric_name = metric_name
        self.actual_value = actual_value
        self.threshold_value = threshold_value
        self.unit = unit


class CircuitBreakerError(ClarityBaseException):
    """
    Raised when circuit breaker is open and requests are being rejected.
    
    This exception is raised when the circuit breaker pattern is active
    and requests to failing services are being rejected to prevent cascading failures.
    """
    
    def __init__(
        self,
        message: str = "Circuit breaker is open",
        service_name: Optional[str] = None,
        failure_count: Optional[int] = None,
        failure_threshold: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize circuit breaker error.
        
        Args:
            message: Error message
            service_name: Name of the service with open circuit breaker
            failure_count: Current failure count
            failure_threshold: Failure threshold that triggered the circuit breaker
            **kwargs: Additional arguments
        """
        context = kwargs.get('context', {})
        context.update({
            "service_name": service_name,
            "failure_count": failure_count,
            "failure_threshold": failure_threshold,
            "circuit_breaker_open": True
        })
        kwargs['context'] = context
        kwargs['error_code'] = kwargs.get('error_code', 'CIRCUIT_BREAKER_OPEN')
        
        super().__init__(message, **kwargs)
        self.service_name = service_name
        self.failure_count = failure_count
        self.failure_threshold = failure_threshold


# Utility Functions

def create_error_context(
    correlation_id: Optional[str] = None,
    execution_id: Optional[str] = None,
    project_id: Optional[str] = None,
    operation: Optional[str] = None,
    **additional_context
) -> Dict[str, Any]:
    """
    Create standardized error context dictionary.
    
    Args:
        correlation_id: Correlation ID for distributed tracing
        execution_id: Execution ID if available
        project_id: Project ID if available
        operation: Operation being performed
        **additional_context: Additional context fields
        
    Returns:
        Dictionary with standardized error context
    """
    context = {
        "correlation_id": correlation_id,
        "execution_id": execution_id,
        "project_id": project_id,
        "operation": operation,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    # Add additional context fields
    context.update(additional_context)
    
    # Remove None values
    return {k: v for k, v in context.items() if v is not None}


def wrap_exception(
    original_exception: Exception,
    wrapper_class: type = ClarityBaseException,
    message: Optional[str] = None,
    **kwargs
) -> ClarityBaseException:
    """
    Wrap an existing exception in a Clarity exception class.
    
    Args:
        original_exception: The original exception to wrap
        wrapper_class: The Clarity exception class to wrap with
        message: Optional custom message (uses original message if not provided)
        **kwargs: Additional arguments for the wrapper exception
        
    Returns:
        Wrapped exception instance
    """
    if message is None:
        message = str(original_exception)
    
    kwargs['cause'] = original_exception
    
    return wrapper_class(message, **kwargs)


# Backward compatibility aliases for existing code
RepositoryError = DatabaseError
