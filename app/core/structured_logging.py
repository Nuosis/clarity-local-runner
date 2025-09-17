"""
Structured Logging Module for Clarity Local Runner

This module provides comprehensive structured logging capabilities with:
- JSON format for machine parsing
- Secret/token redaction for security
- Required fields: correlationId, projectId, executionId, taskId, node, status
- Performance-optimized logging with minimal overhead
- Audit trail maintenance for all worker operations
"""

import json
import logging
import re
import time
import traceback
from datetime import datetime
from typing import Any, Dict, Optional, Union, List
from enum import Enum
from functools import wraps

try:
    from pydantic import BaseModel
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseModel = None


class LogLevel(Enum):
    """Structured logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class LogStatus(Enum):
    """Standard status values for structured logging."""
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"
    DEGRADED = "degraded"
    RECOVERED = "recovered"
    CIRCUIT_OPEN = "circuit_open"
    CIRCUIT_CLOSED = "circuit_closed"


class TransformationPhase(Enum):
    """Phases of task context transformation for detailed logging."""
    VALIDATION = "validation"
    EXTRACTION = "extraction"
    CALCULATION = "calculation"
    SERIALIZATION = "serialization"
    PERSISTENCE = "persistence"


class PerformanceThreshold(Enum):
    """Performance threshold levels for monitoring."""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Pydantic models and other complex objects."""
    
    def default(self, o):
        """Convert non-serializable objects to serializable format."""
        # Handle Pydantic models
        if PYDANTIC_AVAILABLE and BaseModel and isinstance(o, BaseModel):
            return o.dict()
        
        # Handle datetime objects
        if isinstance(o, datetime):
            return o.isoformat()
        
        # Handle Enum objects
        if isinstance(o, Enum):
            return o.value
        
        # Handle sets
        if isinstance(o, set):
            return list(o)
        
        # For any other non-serializable object, convert to string
        try:
            return str(o)
        except Exception:
            return f"<non-serializable: {type(o).__name__}>"


class SecretRedactor:
    """Utility class for redacting sensitive information from log outputs."""
    
    # Patterns for common secrets and tokens
    SECRET_PATTERNS = [
        # JWT tokens
        (re.compile(r'eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*'), '[JWT_TOKEN_REDACTED]'),
        # Bearer tokens
        (re.compile(r'Bearer\s+[A-Za-z0-9_-]+', re.IGNORECASE), 'Bearer [REDACTED]'),
        # Database URLs with credentials
        (re.compile(r'(postgresql|mysql|mongodb)://([^:]+):([^@]+)@', re.IGNORECASE), r'\1://[USER]:[PASSWORD]@'),
    ]
    
    # Sensitive field names that should be redacted
    SENSITIVE_FIELDS = {
        'api_key', 'apikey', 'api-key',
        'token', 'access_token', 'refresh_token', 'auth_token',
        'secret', 'client_secret', 'app_secret',
        'password', 'pwd', 'pass',
        'key', 'private_key', 'public_key',
        'auth', 'authorization',
        'credential', 'credentials'
    }
    
    @classmethod
    def redact_secrets(cls, data: Union[str, Dict[str, Any]]) -> Union[str, Dict[str, Any]]:
        """
        Redact sensitive information from strings or dictionaries.
        
        Args:
            data: String or dictionary that may contain sensitive information
            
        Returns:
            Data with sensitive information redacted
        """
        if isinstance(data, dict):
            return cls._redact_dict(data)
        elif isinstance(data, str):
            return cls._redact_string(data)
        else:
            return data
    
    @classmethod
    def _redact_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Redact secrets from dictionary values."""
        redacted = {}
        for key, value in data.items():
            # Check if the key itself indicates sensitive data
            if key.lower().replace('_', '').replace('-', '') in cls.SENSITIVE_FIELDS:
                redacted[key] = '[REDACTED]'
            elif isinstance(value, dict):
                redacted[key] = cls._redact_dict(value)
            elif isinstance(value, str):
                redacted[key] = cls._redact_string(value)
            elif isinstance(value, list):
                redacted[key] = [cls.redact_secrets(item) for item in value]
            else:
                redacted[key] = value
        return redacted
    
    @classmethod
    def _redact_string(cls, text: str) -> str:
        """Redact secrets from string content."""
        for pattern, replacement in cls.SECRET_PATTERNS:
            text = pattern.sub(replacement, text)
        return text


class StructuredLogger:
    """
    High-performance structured logger with JSON output and secret redaction.
    
    This logger provides consistent structured logging across the application
    with minimal performance overhead and comprehensive audit trail capabilities.
    """
    
    def __init__(self, name: str):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name (typically __name__)
        """
        self.logger = logging.getLogger(name)
        self._base_fields = {}
    
    def set_context(self, **kwargs):
        """
        Set persistent context fields for this logger instance.
        
        Args:
            **kwargs: Context fields to persist across log calls
        """
        self._base_fields.update(kwargs)
    
    def clear_context(self):
        """Clear all persistent context fields."""
        self._base_fields.clear()
    
    def _create_log_entry(
        self,
        level: LogLevel,
        message: str,
        correlation_id: Optional[str] = None,
        project_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        task_id: Optional[str] = None,
        node: Optional[str] = None,
        status: Optional[Union[LogStatus, str]] = None,
        **extra_fields
    ) -> Dict[str, Any]:
        """
        Create a structured log entry with all required fields.
        
        Args:
            level: Log level
            message: Log message
            correlation_id: Correlation ID for distributed tracing
            project_id: Project identifier
            execution_id: Execution identifier
            task_id: Task identifier
            node: Current workflow node
            status: Operation status
            **extra_fields: Additional fields to include
            
        Returns:
            Structured log entry dictionary
        """
        # Start with base fields
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level.value,
            "message": message,
            "logger": self.logger.name,
        }
        
        # Add persistent context fields
        log_entry.update(self._base_fields)
        
        # Add required structured fields
        if correlation_id:
            log_entry["correlationId"] = correlation_id
        if project_id:
            log_entry["projectId"] = project_id
        if execution_id:
            log_entry["executionId"] = execution_id
        if task_id:
            log_entry["taskId"] = task_id
        if node:
            log_entry["node"] = node
        if status:
            log_entry["status"] = status.value if isinstance(status, LogStatus) else status
        
        # Add extra fields
        log_entry.update(extra_fields)
        
        # Redact secrets from the entire log entry
        redacted_entry = SecretRedactor.redact_secrets(log_entry)
        
        # Ensure we always return a dictionary
        if isinstance(redacted_entry, dict):
            return redacted_entry
        else:
            # This should never happen, but provide a fallback
            return log_entry
    
    def _log(self, level: LogLevel, log_entry: Dict[str, Any]):
        """
        Output structured log entry as JSON.
        
        Args:
            level: Log level
            log_entry: Structured log entry
        """
        # Convert to JSON string for machine parsing using custom encoder
        try:
            json_message = json.dumps(log_entry, separators=(',', ':'), cls=CustomJSONEncoder)
        except Exception as e:
            # Fallback: create a safe log entry if JSON serialization fails
            safe_entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": level.value,
                "message": f"JSON serialization failed: {str(e)}",
                "logger": self.logger.name,
                "original_message": str(log_entry.get('message', 'Unknown')),
                "serialization_error": str(e)
            }
            json_message = json.dumps(safe_entry, separators=(',', ':'))
        
        # Map our LogLevel to Python logging levels
        python_level = getattr(logging, level.value)
        
        # Log with minimal overhead
        self.logger.log(python_level, json_message)
    
    def debug(
        self,
        message: str,
        correlation_id: Optional[str] = None,
        project_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        task_id: Optional[str] = None,
        node: Optional[str] = None,
        status: Optional[Union[LogStatus, str]] = None,
        **extra_fields
    ):
        """Log DEBUG level message."""
        if self.logger.isEnabledFor(logging.DEBUG):
            log_entry = self._create_log_entry(
                LogLevel.DEBUG, message, correlation_id, project_id,
                execution_id, task_id, node, status, **extra_fields
            )
            self._log(LogLevel.DEBUG, log_entry)
    
    def info(
        self,
        message: str,
        correlation_id: Optional[str] = None,
        project_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        task_id: Optional[str] = None,
        node: Optional[str] = None,
        status: Optional[Union[LogStatus, str]] = None,
        **extra_fields
    ):
        """Log INFO level message."""
        if self.logger.isEnabledFor(logging.INFO):
            log_entry = self._create_log_entry(
                LogLevel.INFO, message, correlation_id, project_id,
                execution_id, task_id, node, status, **extra_fields
            )
            self._log(LogLevel.INFO, log_entry)
    
    def warn(
        self,
        message: str,
        correlation_id: Optional[str] = None,
        project_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        task_id: Optional[str] = None,
        node: Optional[str] = None,
        status: Optional[Union[LogStatus, str]] = None,
        **extra_fields
    ):
        """Log WARN level message."""
        if self.logger.isEnabledFor(logging.WARNING):
            log_entry = self._create_log_entry(
                LogLevel.WARN, message, correlation_id, project_id,
                execution_id, task_id, node, status, **extra_fields
            )
            self._log(LogLevel.WARN, log_entry)
    
    def error(
        self,
        message: str,
        correlation_id: Optional[str] = None,
        project_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        task_id: Optional[str] = None,
        node: Optional[str] = None,
        status: Optional[Union[LogStatus, str]] = None,
        error: Optional[Exception] = None,
        **extra_fields
    ):
        """Log ERROR level message."""
        if self.logger.isEnabledFor(logging.ERROR):
            if error:
                extra_fields.update({
                    "error_type": type(error).__name__,
                    "error_message": str(error)
                })
            
            log_entry = self._create_log_entry(
                LogLevel.ERROR, message, correlation_id, project_id,
                execution_id, task_id, node, status, **extra_fields
            )
            self._log(LogLevel.ERROR, log_entry)


def get_structured_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name)


class TransformationLogger:
    """
    Specialized logger for task context transformation operations.
    
    Provides detailed logging for transformation phases, error recovery,
    and performance monitoring specific to schema transformation.
    """
    
    def __init__(self, base_logger: StructuredLogger):
        """
        Initialize transformation logger.
        
        Args:
            base_logger: Base structured logger instance
        """
        self.logger = base_logger
        self._transformation_context = {}
    
    def set_transformation_context(
        self,
        correlation_id: str,
        execution_id: str,
        task_context_size: Optional[int] = None,
        **kwargs
    ):
        """
        Set transformation-specific context.
        
        Args:
            correlation_id: Correlation ID for distributed tracing
            execution_id: Execution identifier
            task_context_size: Size of task_context data
            **kwargs: Additional context fields
        """
        self._transformation_context = {
            "correlation_id": correlation_id,
            "execution_id": execution_id,
            "task_context_size": task_context_size,
            **kwargs
        }
    
    def log_transformation_start(
        self,
        phase: TransformationPhase,
        input_data_summary: Optional[Dict[str, Any]] = None
    ):
        """
        Log the start of a transformation phase.
        
        Args:
            phase: Transformation phase being started
            input_data_summary: Summary of input data (redacted)
        """
        extra_fields = {
            "transformation_phase": phase.value,
            "status": LogStatus.STARTED.value,
            **self._transformation_context
        }
        
        if input_data_summary:
            extra_fields["input_summary"] = input_data_summary
        
        self.logger.info(
            f"Transformation {phase.value} started",
            **extra_fields
        )
    
    def log_transformation_success(
        self,
        phase: TransformationPhase,
        duration_ms: float,
        output_summary: Optional[Dict[str, Any]] = None,
        performance_metrics: Optional[Dict[str, Any]] = None
    ):
        """
        Log successful completion of a transformation phase.
        
        Args:
            phase: Transformation phase completed
            duration_ms: Duration in milliseconds
            output_summary: Summary of output data
            performance_metrics: Performance metrics
        """
        extra_fields = {
            "transformation_phase": phase.value,
            "status": LogStatus.COMPLETED.value,
            "duration_ms": round(duration_ms, 2),
            "performance_threshold": self._get_performance_threshold(duration_ms),
            **self._transformation_context
        }
        
        if output_summary:
            extra_fields["output_summary"] = output_summary
        
        if performance_metrics:
            extra_fields["performance_metrics"] = performance_metrics
        
        self.logger.info(
            f"Transformation {phase.value} completed successfully",
            **extra_fields
        )
    
    def log_transformation_error(
        self,
        phase: TransformationPhase,
        error: Exception,
        duration_ms: float,
        error_context: Optional[Dict[str, Any]] = None,
        recovery_attempted: bool = False
    ):
        """
        Log transformation error with detailed context.
        
        Args:
            phase: Transformation phase that failed
            error: Exception that occurred
            duration_ms: Duration before failure
            error_context: Additional error context
            recovery_attempted: Whether recovery was attempted
        """
        extra_fields = {
            "transformation_phase": phase.value,
            "status": LogStatus.FAILED.value,
            "duration_ms": round(duration_ms, 2),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "recovery_attempted": recovery_attempted,
            **self._transformation_context
        }
        
        if error_context:
            extra_fields["error_context"] = error_context
        
        # Add stack trace for debugging
        if hasattr(error, '__traceback__') and error.__traceback__:
            extra_fields["stack_trace"] = traceback.format_exception(
                type(error), error, error.__traceback__
            )
        
        self.logger.error(
            f"Transformation {phase.value} failed: {str(error)}",
            **extra_fields
        )
    
    def log_recovery_attempt(
        self,
        phase: TransformationPhase,
        recovery_strategy: str,
        attempt_number: int,
        max_attempts: int
    ):
        """
        Log error recovery attempt.
        
        Args:
            phase: Transformation phase being recovered
            recovery_strategy: Recovery strategy being used
            attempt_number: Current attempt number
            max_attempts: Maximum attempts allowed
        """
        extra_fields = {
            "transformation_phase": phase.value,
            "status": LogStatus.RETRYING.value,
            "recovery_strategy": recovery_strategy,
            "attempt_number": attempt_number,
            "max_attempts": max_attempts,
            **self._transformation_context
        }
        
        self.logger.warn(
            f"Attempting recovery for {phase.value} using {recovery_strategy} "
            f"(attempt {attempt_number}/{max_attempts})",
            **extra_fields
        )
    
    def log_recovery_success(
        self,
        phase: TransformationPhase,
        recovery_strategy: str,
        total_attempts: int,
        total_duration_ms: float
    ):
        """
        Log successful error recovery.
        
        Args:
            phase: Transformation phase that was recovered
            recovery_strategy: Recovery strategy that succeeded
            total_attempts: Total attempts made
            total_duration_ms: Total duration including retries
        """
        extra_fields = {
            "transformation_phase": phase.value,
            "status": LogStatus.RECOVERED.value,
            "recovery_strategy": recovery_strategy,
            "total_attempts": total_attempts,
            "total_duration_ms": round(total_duration_ms, 2),
            **self._transformation_context
        }
        
        self.logger.info(
            f"Successfully recovered {phase.value} using {recovery_strategy} "
            f"after {total_attempts} attempts",
            **extra_fields
        )
    
    def log_degraded_operation(
        self,
        phase: TransformationPhase,
        degradation_reason: str,
        fallback_strategy: str,
        impact_assessment: Optional[str] = None
    ):
        """
        Log degraded operation with fallback.
        
        Args:
            phase: Transformation phase running in degraded mode
            degradation_reason: Reason for degradation
            fallback_strategy: Fallback strategy being used
            impact_assessment: Assessment of impact on functionality
        """
        extra_fields = {
            "transformation_phase": phase.value,
            "status": LogStatus.DEGRADED.value,
            "degradation_reason": degradation_reason,
            "fallback_strategy": fallback_strategy,
            **self._transformation_context
        }
        
        if impact_assessment:
            extra_fields["impact_assessment"] = impact_assessment
        
        self.logger.warn(
            f"Operating {phase.value} in degraded mode: {degradation_reason}",
            **extra_fields
        )
    
    def _get_performance_threshold(self, duration_ms: float) -> str:
        """
        Determine performance threshold based on duration.
        
        Args:
            duration_ms: Duration in milliseconds
            
        Returns:
            Performance threshold level
        """
        if duration_ms < 100:
            return PerformanceThreshold.NORMAL.value
        elif duration_ms < 500:
            return PerformanceThreshold.WARNING.value
        elif duration_ms < 2000:
            return PerformanceThreshold.CRITICAL.value
        else:
            return PerformanceThreshold.EMERGENCY.value


class CircuitBreakerLogger:
    """
    Logger for circuit breaker pattern implementation.
    
    Provides structured logging for circuit breaker state changes
    and failure tracking.
    """
    
    def __init__(self, base_logger: StructuredLogger, service_name: str):
        """
        Initialize circuit breaker logger.
        
        Args:
            base_logger: Base structured logger instance
            service_name: Name of the service being protected
        """
        self.logger = base_logger
        self.service_name = service_name
    
    def log_circuit_opened(
        self,
        failure_count: int,
        failure_threshold: int,
        correlation_id: Optional[str] = None
    ):
        """
        Log circuit breaker opening.
        
        Args:
            failure_count: Number of failures that triggered opening
            failure_threshold: Threshold that was exceeded
            correlation_id: Optional correlation ID
        """
        extra_fields = {
            "service_name": self.service_name,
            "status": LogStatus.CIRCUIT_OPEN.value,
            "failure_count": failure_count,
            "failure_threshold": failure_threshold
        }
        
        if correlation_id:
            extra_fields["correlation_id"] = correlation_id
        
        self.logger.error(
            f"Circuit breaker opened for {self.service_name} "
            f"after {failure_count} failures",
            **extra_fields
        )
    
    def log_circuit_closed(
        self,
        success_count: int,
        correlation_id: Optional[str] = None
    ):
        """
        Log circuit breaker closing.
        
        Args:
            success_count: Number of successful operations
            correlation_id: Optional correlation ID
        """
        extra_fields = {
            "service_name": self.service_name,
            "status": LogStatus.CIRCUIT_CLOSED.value,
            "success_count": success_count
        }
        
        if correlation_id:
            extra_fields["correlation_id"] = correlation_id
        
        self.logger.info(
            f"Circuit breaker closed for {self.service_name} "
            f"after {success_count} successful operations",
            **extra_fields
        )
    
    def log_circuit_half_open(self, correlation_id: Optional[str] = None):
        """
        Log circuit breaker entering half-open state.
        
        Args:
            correlation_id: Optional correlation ID
        """
        extra_fields = {
            "service_name": self.service_name,
            "status": "half_open"
        }
        
        if correlation_id:
            extra_fields["correlation_id"] = correlation_id
        
        self.logger.info(
            f"Circuit breaker for {self.service_name} entering half-open state",
            **extra_fields
        )


def log_performance(
    logger: StructuredLogger,
    operation: str,
    phase: Optional[TransformationPhase] = None,
    performance_thresholds: Optional[Dict[str, float]] = None
):
    """
    Enhanced decorator to log operation performance metrics with thresholds.
    
    Args:
        logger: StructuredLogger instance
        operation: Operation name for logging
        phase: Optional transformation phase
        performance_thresholds: Optional performance thresholds in ms
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            correlation_id = kwargs.get('correlation_id')
            execution_id = kwargs.get('execution_id')
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                # Determine performance threshold
                threshold = PerformanceThreshold.NORMAL
                if performance_thresholds:
                    if duration_ms > performance_thresholds.get('emergency', 2000):
                        threshold = PerformanceThreshold.EMERGENCY
                    elif duration_ms > performance_thresholds.get('critical', 1000):
                        threshold = PerformanceThreshold.CRITICAL
                    elif duration_ms > performance_thresholds.get('warning', 500):
                        threshold = PerformanceThreshold.WARNING
                
                extra_fields = {
                    "status": LogStatus.COMPLETED.value,
                    "duration_ms": round(duration_ms, 2),
                    "performance_threshold": threshold.value
                }
                
                if phase:
                    extra_fields["transformation_phase"] = phase.value
                if correlation_id:
                    extra_fields["correlation_id"] = correlation_id
                if execution_id:
                    extra_fields["execution_id"] = execution_id
                
                # Log at appropriate level based on performance
                if threshold == PerformanceThreshold.EMERGENCY:
                    logger.error(f"{operation} completed with emergency-level latency", **extra_fields)
                elif threshold == PerformanceThreshold.CRITICAL:
                    logger.warn(f"{operation} completed with critical latency", **extra_fields)
                elif threshold == PerformanceThreshold.WARNING:
                    logger.warn(f"{operation} completed with warning-level latency", **extra_fields)
                else:
                    logger.debug(f"{operation} completed", **extra_fields)
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                extra_fields = {
                    "status": LogStatus.FAILED.value,
                    "duration_ms": round(duration_ms, 2),
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
                
                if phase:
                    extra_fields["transformation_phase"] = phase.value
                if correlation_id:
                    extra_fields["correlation_id"] = correlation_id
                if execution_id:
                    extra_fields["execution_id"] = execution_id
                
                logger.error(f"{operation} failed", **extra_fields)
                raise
                
        return wrapper
    return decorator


def get_transformation_logger(name: str) -> TransformationLogger:
    """
    Get a transformation-specific logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        TransformationLogger instance
    """
    base_logger = get_structured_logger(name)
    return TransformationLogger(base_logger)


def get_circuit_breaker_logger(name: str, service_name: str) -> CircuitBreakerLogger:
    """
    Get a circuit breaker logger instance.
    
    Args:
        name: Logger name (typically __name__)
        service_name: Name of the service being protected
        
    Returns:
        CircuitBreakerLogger instance
    """
    base_logger = get_structured_logger(name)
    return CircuitBreakerLogger(base_logger, service_name)