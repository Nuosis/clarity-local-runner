"""
Error Recovery Strategies and Fallback Mechanisms

This module provides comprehensive error recovery patterns including:
- Exponential backoff retry logic with jitter
- Circuit breaker pattern for external dependencies
- Graceful degradation strategies
- Fallback value providers
- Recovery context management
- Performance monitoring integration

The module follows established resilience patterns and integrates with our
custom exception hierarchy and structured logging framework.
"""

import asyncio
import random
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
from dataclasses import dataclass, field
from functools import wraps

from core.structured_logging import get_structured_logger, get_transformation_logger, TransformationPhase
from core.exceptions import (
    ClarityBaseException,
    DatabaseError,
    ServiceError,
    APIError,
    TaskContextTransformationError,
    InvalidTaskContextError,
    StatusCalculationError,
    FieldExtractionError
)

# Type variables for generic retry functions
T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])

# Configure logging
logger = get_structured_logger(__name__)
transformation_logger = get_transformation_logger(__name__)


class RetryStrategy(Enum):
    """Retry strategy types."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    IMMEDIATE = "immediate"


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class FallbackStrategy(Enum):
    """Fallback strategy types."""
    DEFAULT_VALUE = "default_value"
    CACHED_VALUE = "cached_value"
    DEGRADED_SERVICE = "degraded_service"
    EMPTY_RESPONSE = "empty_response"
    RETRY_LATER = "retry_later"


@dataclass
class RetryConfig:
    """Configuration for retry operations."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    retryable_exceptions: tuple = (
        DatabaseError,
        ServiceError,
        APIError,
        ConnectionError,
        TimeoutError
    )
    non_retryable_exceptions: tuple = (
        InvalidTaskContextError,
        StatusCalculationError,
        FieldExtractionError
    )


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    success_threshold: int = 3
    timeout: float = 30.0


@dataclass
class FallbackConfig:
    """Configuration for fallback mechanisms."""
    strategy: FallbackStrategy = FallbackStrategy.DEFAULT_VALUE
    default_value: Any = None
    cache_ttl: float = 300.0  # 5 minutes
    enable_degraded_mode: bool = True


@dataclass
class RecoveryContext:
    """Context information for error recovery operations."""
    operation_name: str
    correlation_id: str
    execution_id: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    attempt_count: int = 0
    last_error: Optional[Exception] = None
    recovery_metadata: Dict[str, Any] = field(default_factory=dict)


class CircuitBreaker:
    """
    Circuit breaker implementation for external service calls.
    
    Provides automatic failure detection and recovery testing to prevent
    cascading failures and improve system resilience.
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.next_attempt_time: Optional[float] = None
        
        # Logging context
        self.logger = get_structured_logger(f"{__name__}.CircuitBreaker.{name}")
    
    def can_execute(self) -> bool:
        """Check if the circuit breaker allows execution."""
        current_time = time.time()
        
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if (self.next_attempt_time and 
                current_time >= self.next_attempt_time):
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                self.logger.info(
                    "Circuit breaker transitioning to half-open",
                    circuit_breaker=self.name,
                    state=self.state.value,
                    current_time=current_time,
                    next_attempt_time=self.next_attempt_time
                )
                return True
            return False
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return True
        
        return False
    
    def record_success(self):
        """Record a successful operation."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                self.last_failure_time = None
                self.next_attempt_time = None
                
                self.logger.info(
                    "Circuit breaker recovered to closed state",
                    circuit_breaker=self.name,
                    state=self.state.value,
                    success_count=self.success_count
                )
        elif self.state == CircuitBreakerState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    def record_failure(self, error: Exception):
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitBreakerState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                self.next_attempt_time = (
                    self.last_failure_time + self.config.recovery_timeout
                )
                
                self.logger.warn(
                    "Circuit breaker opened due to failures",
                    circuit_breaker=self.name,
                    state=self.state.value,
                    failure_count=self.failure_count,
                    failure_threshold=self.config.failure_threshold,
                    error=str(error),
                    next_attempt_time=self.next_attempt_time
                )
        elif self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            self.next_attempt_time = (
                self.last_failure_time + self.config.recovery_timeout
            )
            
            self.logger.warn(
                "Circuit breaker returned to open state after half-open failure",
                circuit_breaker=self.name,
                state=self.state.value,
                error=str(error),
                next_attempt_time=self.next_attempt_time
            )


class FallbackProvider:
    """
    Provides fallback values and degraded service responses.
    
    Implements various fallback strategies to maintain system functionality
    even when primary operations fail.
    """
    
    def __init__(self, config: FallbackConfig):
        self.config = config
        self.cache: Dict[str, tuple] = {}  # key -> (value, timestamp)
        self.logger = get_structured_logger(f"{__name__}.FallbackProvider")
    
    def get_fallback(
        self,
        operation_name: str,
        context: RecoveryContext,
        error: Exception
    ) -> Any:
        """Get fallback value based on configured strategy."""
        
        self.logger.info(
            "Providing fallback value",
            operation=operation_name,
            strategy=self.config.strategy.value,
            correlation_id=context.correlation_id,
            error_type=type(error).__name__
        )
        
        if self.config.strategy == FallbackStrategy.DEFAULT_VALUE:
            return self._get_default_value(operation_name, context)
        elif self.config.strategy == FallbackStrategy.CACHED_VALUE:
            return self._get_cached_value(operation_name, context)
        elif self.config.strategy == FallbackStrategy.DEGRADED_SERVICE:
            return self._get_degraded_response(operation_name, context)
        elif self.config.strategy == FallbackStrategy.EMPTY_RESPONSE:
            return self._get_empty_response(operation_name, context)
        elif self.config.strategy == FallbackStrategy.RETRY_LATER:
            return self._get_retry_later_response(operation_name, context, error)
        else:
            return self.config.default_value
    
    def cache_value(self, key: str, value: Any):
        """Cache a value for fallback use."""
        self.cache[key] = (value, time.time())
        
        # Clean old cache entries
        self._cleanup_cache()
    
    def _get_default_value(self, operation_name: str, context: RecoveryContext) -> Any:
        """Get configured default value."""
        return self.config.default_value
    
    def _get_cached_value(self, operation_name: str, context: RecoveryContext) -> Any:
        """Get cached value if available and not expired."""
        cache_key = f"{operation_name}:{context.execution_id or 'default'}"
        
        if cache_key in self.cache:
            value, timestamp = self.cache[cache_key]
            if time.time() - timestamp <= self.config.cache_ttl:
                self.logger.info(
                    "Using cached fallback value",
                    operation=operation_name,
                    cache_key=cache_key,
                    cache_age=time.time() - timestamp
                )
                return value
        
        # Fall back to default if no valid cache
        return self.config.default_value
    
    def _get_degraded_response(self, operation_name: str, context: RecoveryContext) -> Any:
        """Get degraded service response."""
        if not self.config.enable_degraded_mode:
            return self.config.default_value
        
        # Return minimal response structure based on operation
        if "status" in operation_name.lower():
            return {
                "status": "degraded",
                "message": "Service operating in degraded mode",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        
        return self.config.default_value
    
    def _get_empty_response(self, operation_name: str, context: RecoveryContext) -> Any:
        """Get empty response appropriate for the operation."""
        if "list" in operation_name.lower():
            return []
        elif "dict" in operation_name.lower() or "status" in operation_name.lower():
            return {}
        else:
            return None
    
    def _get_retry_later_response(
        self,
        operation_name: str,
        context: RecoveryContext,
        error: Exception
    ) -> Any:
        """Get retry later response with error details."""
        return {
            "status": "retry_later",
            "message": "Operation temporarily unavailable, please retry later",
            "error": str(error),
            "retry_after": 60,  # seconds
            "correlation_id": context.correlation_id
        }
    
    def _cleanup_cache(self):
        """Remove expired cache entries."""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if current_time - timestamp > self.config.cache_ttl
        ]
        
        for key in expired_keys:
            del self.cache[key]


class ErrorRecoveryManager:
    """
    Main error recovery manager that coordinates retry logic, circuit breakers,
    and fallback mechanisms.
    """
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.fallback_providers: Dict[str, FallbackProvider] = {}
        self.logger = get_structured_logger(f"{__name__}.ErrorRecoveryManager")
    
    def get_circuit_breaker(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        if name not in self.circuit_breakers:
            config = config or CircuitBreakerConfig()
            self.circuit_breakers[name] = CircuitBreaker(name, config)
        
        return self.circuit_breakers[name]
    
    def get_fallback_provider(
        self,
        name: str,
        config: Optional[FallbackConfig] = None
    ) -> FallbackProvider:
        """Get or create a fallback provider."""
        if name not in self.fallback_providers:
            config = config or FallbackConfig()
            self.fallback_providers[name] = FallbackProvider(config)
        
        return self.fallback_providers[name]
    
    def execute_with_recovery(
        self,
        func: Callable[..., T],
        *args,
        operation_name: str,
        correlation_id: str,
        execution_id: Optional[str] = None,
        retry_config: Optional[RetryConfig] = None,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        fallback_config: Optional[FallbackConfig] = None,
        **kwargs
    ) -> T:
        """
        Execute function with comprehensive error recovery.
        
        Combines retry logic, circuit breaker pattern, and fallback mechanisms
        to provide maximum resilience.
        """
        context = RecoveryContext(
            operation_name=operation_name,
            correlation_id=correlation_id,
            execution_id=execution_id
        )
        
        retry_config = retry_config or RetryConfig()
        circuit_breaker = None
        fallback_provider = None
        
        # Set up circuit breaker if configured
        if circuit_breaker_config:
            circuit_breaker = self.get_circuit_breaker(
                f"{operation_name}_cb",
                circuit_breaker_config
            )
        
        # Set up fallback provider if configured
        if fallback_config:
            fallback_provider = self.get_fallback_provider(
                f"{operation_name}_fallback",
                fallback_config
            )
        
        # Execute with retry logic
        return self._execute_with_retry(
            func,
            args,
            kwargs,
            context,
            retry_config,
            circuit_breaker,
            fallback_provider
        )
    
    def _execute_with_retry(
        self,
        func: Callable[..., T],
        args: tuple,
        kwargs: dict,
        context: RecoveryContext,
        retry_config: RetryConfig,
        circuit_breaker: Optional[CircuitBreaker],
        fallback_provider: Optional[FallbackProvider]
    ) -> T:
        """Execute function with retry logic."""
        
        for attempt in range(retry_config.max_attempts):
            context.attempt_count = attempt + 1
            
            try:
                # Check circuit breaker
                if circuit_breaker and not circuit_breaker.can_execute():
                    raise ServiceError(
                        f"Circuit breaker open for {context.operation_name}",
                        context={
                            "circuit_breaker_state": circuit_breaker.state.value,
                            "operation": context.operation_name
                        }
                    )
                
                # Log attempt
                self.logger.info(
                    "Executing operation with recovery",
                    operation=context.operation_name,
                    correlation_id=context.correlation_id,
                    execution_id=context.execution_id,
                    attempt=context.attempt_count,
                    max_attempts=retry_config.max_attempts
                )
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Record success
                if circuit_breaker:
                    circuit_breaker.record_success()
                
                # Cache successful result for fallback
                if fallback_provider:
                    cache_key = f"{context.operation_name}:{context.execution_id or 'default'}"
                    fallback_provider.cache_value(cache_key, result)
                
                self.logger.info(
                    "Operation completed successfully",
                    operation=context.operation_name,
                    correlation_id=context.correlation_id,
                    execution_id=context.execution_id,
                    attempt=context.attempt_count,
                    duration_ms=round((time.time() - context.start_time) * 1000, 2)
                )
                
                return result
                
            except Exception as error:
                context.last_error = error
                
                # Record failure in circuit breaker
                if circuit_breaker:
                    circuit_breaker.record_failure(error)
                
                # Check if error is retryable
                is_retryable = (
                    isinstance(error, retry_config.retryable_exceptions) and
                    not isinstance(error, retry_config.non_retryable_exceptions)
                )
                
                # Log error
                self.logger.warn(
                    "Operation attempt failed",
                    operation=context.operation_name,
                    correlation_id=context.correlation_id,
                    execution_id=context.execution_id,
                    attempt=context.attempt_count,
                    max_attempts=retry_config.max_attempts,
                    error=str(error),
                    error_type=type(error).__name__,
                    is_retryable=is_retryable
                )
                
                # If not retryable or last attempt, try fallback
                if not is_retryable or attempt == retry_config.max_attempts - 1:
                    if fallback_provider:
                        try:
                            fallback_result = fallback_provider.get_fallback(
                                context.operation_name,
                                context,
                                error
                            )
                            
                            self.logger.info(
                                "Using fallback value after operation failure",
                                operation=context.operation_name,
                                correlation_id=context.correlation_id,
                                execution_id=context.execution_id,
                                fallback_strategy=fallback_provider.config.strategy.value
                            )
                            
                            return fallback_result
                            
                        except Exception as fallback_error:
                            self.logger.error(
                                "Fallback mechanism also failed",
                                operation=context.operation_name,
                                correlation_id=context.correlation_id,
                                execution_id=context.execution_id,
                                original_error=str(error),
                                fallback_error=str(fallback_error)
                            )
                    
                    # No fallback available, re-raise original error
                    raise error
                
                # Calculate delay for next attempt
                if attempt < retry_config.max_attempts - 1:
                    delay = self._calculate_delay(
                        attempt,
                        retry_config.base_delay,
                        retry_config.max_delay,
                        retry_config.exponential_base,
                        retry_config.strategy,
                        retry_config.jitter
                    )
                    
                    self.logger.info(
                        "Retrying operation after delay",
                        operation=context.operation_name,
                        correlation_id=context.correlation_id,
                        execution_id=context.execution_id,
                        delay_seconds=delay,
                        next_attempt=attempt + 2
                    )
                    
                    time.sleep(delay)
        
        # Should not reach here, but handle gracefully
        raise context.last_error or ServiceError("All retry attempts exhausted")
    
    def _calculate_delay(
        self,
        attempt: int,
        base_delay: float,
        max_delay: float,
        exponential_base: float,
        strategy: RetryStrategy,
        jitter: bool
    ) -> float:
        """Calculate delay for next retry attempt."""
        
        if strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = base_delay * (exponential_base ** attempt)
        elif strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = base_delay * (attempt + 1)
        elif strategy == RetryStrategy.FIXED_DELAY:
            delay = base_delay
        else:  # IMMEDIATE
            delay = 0
        
        # Apply maximum delay limit
        delay = min(delay, max_delay)
        
        # Add jitter to prevent thundering herd
        if jitter and delay > 0:
            jitter_amount = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_amount, jitter_amount)
            delay = max(0, delay)  # Ensure non-negative
        
        return delay


# Global error recovery manager instance
_error_recovery_manager = ErrorRecoveryManager()


def with_retry(
    operation_name: str,
    retry_config: Optional[RetryConfig] = None,
    circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
    fallback_config: Optional[FallbackConfig] = None
):
    """
    Decorator for adding error recovery to functions.
    
    Usage:
        @with_retry("database_query", retry_config=RetryConfig(max_attempts=5))
        def query_database():
            # Function implementation
            pass
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract correlation_id and execution_id from kwargs if available
            correlation_id = kwargs.pop('correlation_id', f"retry_{int(time.time() * 1000)}")
            execution_id = kwargs.pop('execution_id', None)
            
            return _error_recovery_manager.execute_with_recovery(
                func,
                *args,
                operation_name=operation_name,
                correlation_id=correlation_id,
                execution_id=execution_id,
                retry_config=retry_config,
                circuit_breaker_config=circuit_breaker_config,
                fallback_config=fallback_config,
                **kwargs
            )
        
        return wrapper
    return decorator


def get_error_recovery_manager() -> ErrorRecoveryManager:
    """Get the global error recovery manager instance."""
    return _error_recovery_manager


# Convenience functions for common recovery patterns
def create_database_retry_config() -> RetryConfig:
    """Create retry configuration optimized for database operations."""
    return RetryConfig(
        max_attempts=3,
        base_delay=0.5,
        max_delay=10.0,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        retryable_exceptions=(DatabaseError, ConnectionError, TimeoutError)
    )


def create_api_retry_config() -> RetryConfig:
    """Create retry configuration optimized for API calls."""
    return RetryConfig(
        max_attempts=5,
        base_delay=1.0,
        max_delay=30.0,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        retryable_exceptions=(APIError, ServiceError, ConnectionError, TimeoutError)
    )


def create_transformation_fallback_config() -> FallbackConfig:
    """Create fallback configuration for transformation operations."""
    return FallbackConfig(
        strategy=FallbackStrategy.DEFAULT_VALUE,
        default_value=None,
        enable_degraded_mode=True
    )