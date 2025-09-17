"""
Comprehensive Error Handling Test Suite

This test suite validates all error handling implementations across the
transformation pipeline including:
- Custom exception classes
- Structured logging
- Transformation function error handling
- API endpoint error handling
- Service layer error handling
- Error recovery mechanisms
- Performance monitoring
- Circuit breaker patterns
- Fallback mechanisms

The tests are organized by component and error scenario to ensure
complete coverage of all error handling paths.
"""

import pytest
import time
import asyncio
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional
import json

# Import our error handling components
from core.exceptions import (
    ClarityBaseException,
    ClarityValidationError,
    DatabaseError,
    ServiceError,
    APIError,
    TaskContextTransformationError,
    InvalidTaskContextError,
    NodeDataError,
    StatusCalculationError,
    FieldExtractionError,
    RepositoryError  # Backward compatibility alias
)

from core.structured_logging import (
    get_structured_logger,
    TransformationLogger,
    CircuitBreakerLogger,
    TransformationPhase,
    PerformanceThreshold
)

from core.error_recovery import (
    ErrorRecoveryManager,
    CircuitBreaker,
    FallbackProvider,
    RetryStrategy,
    RecoveryContext,
    with_retry
)

from core.performance_monitoring import (
    PerformanceMonitor,
    AlertSeverity,
    MetricType,
    ThresholdType,
    AlertThreshold,
    PerformanceAlert,
    get_performance_monitor,
    performance_timer,
    record_api_latency,
    record_transformation_performance
)

from schemas.status_projection_schema import project_status_from_task_context
from services.status_projection_service import StatusProjectionService


class TestCustomExceptions:
    """Test custom exception classes and their behavior."""
    
    def test_clarity_base_exception(self):
        """Test base exception functionality."""
        error = ClarityBaseException(
            message="Test error",
            error_code="TEST_001",
            correlation_id="test-123",
            execution_id="exec-456"
        )
        
        assert str(error) == "Test error"
        assert error.error_code == "TEST_001"
        assert error.correlation_id == "test-123"
        assert error.execution_id == "exec-456"
        assert error.timestamp is not None
        assert isinstance(error.context, dict)
    
    def test_validation_error(self):
        """Test validation error with field details."""
        error = ClarityValidationError(
            message="Validation failed",
            field_name="test_field",
            field_value="invalid_value",
            validation_rule="required"
        )
        
        assert error.field_name == "test_field"
        assert error.field_value == "invalid_value"
        assert error.validation_rule == "required"
        assert "test_field" in str(error)
    
    def test_database_error(self):
        """Test database error with query details."""
        error = DatabaseError(
            message="Database connection failed",
            query="SELECT * FROM test",
            table_name="test_table",
            operation="SELECT"
        )
        
        assert error.query == "SELECT * FROM test"
        assert error.table_name == "test_table"
        assert error.operation == "SELECT"
    
    def test_service_error(self):
        """Test service error with service details."""
        error = ServiceError(
            message="Service unavailable",
            service_name="test_service",
            endpoint="http://test.com/api",
            status_code=503
        )
        
        assert error.service_name == "test_service"
        assert error.endpoint == "http://test.com/api"
        assert error.status_code == 503
    
    def test_api_error(self):
        """Test API error with request details."""
        error = APIError(
            message="API request failed",
            endpoint="/api/test",
            method="POST",
            status_code=400,
            response_body={"error": "Bad request"}
        )
        
        assert error.endpoint == "/api/test"
        assert error.method == "POST"
        assert error.status_code == 400
        assert error.response_body == {"error": "Bad request"}
    
    def test_transformation_errors(self):
        """Test transformation-specific errors."""
        # Test InvalidTaskContextError
        invalid_error = InvalidTaskContextError(
            message="Invalid task context",
            context_type="dict",
            expected_keys=["nodes", "edges"]
        )
        assert invalid_error.context_type == "dict"
        assert invalid_error.expected_keys == ["nodes", "edges"]
        
        # Test NodeDataError
        node_error = NodeDataError(
            message="Invalid node data",
            node_id="node_123",
            node_type="test_node",
            validation_errors=["missing required field"]
        )
        assert node_error.node_id == "node_123"
        assert node_error.node_type == "test_node"
        assert node_error.validation_errors == ["missing required field"]
        
        # Test StatusCalculationError
        status_error = StatusCalculationError(
            message="Status calculation failed",
            calculation_type="completion_percentage",
            input_values={"completed": 5, "total": 10}
        )
        assert status_error.calculation_type == "completion_percentage"
        assert status_error.input_values == {"completed": 5, "total": 10}
        
        # Test FieldExtractionError
        field_error = FieldExtractionError(
            message="Field extraction failed",
            field_path="nodes.0.status",
            source_data={"nodes": [{}]}
        )
        assert field_error.field_path == "nodes.0.status"
        assert field_error.source_data == {"nodes": [{}]}
    
    def test_backward_compatibility(self):
        """Test backward compatibility aliases."""
        # RepositoryError should be an alias for DatabaseError
        error = RepositoryError(
            message="Repository error",
            repository_url="https://github.com/test/repo"
        )
        
        assert isinstance(error, DatabaseError)
        assert hasattr(error, 'repository_url')


class TestStructuredLogging:
    """Test structured logging functionality."""
    
    def test_get_structured_logger(self):
        """Test structured logger creation."""
        logger = get_structured_logger("test_module")
        assert logger is not None
        assert logger.name == "test_module"
    
    def test_transformation_logger(self):
        """Test transformation-specific logging."""
        logger = TransformationLogger("test_transformation")
        
        # Test phase logging
        logger.log_phase_start(
            TransformationPhase.INPUT_VALIDATION,
            correlation_id="test-123",
            execution_id="exec-456"
        )
        
        logger.log_phase_success(
            TransformationPhase.INPUT_VALIDATION,
            duration_ms=100.5,
            correlation_id="test-123",
            execution_id="exec-456"
        )
        
        logger.log_phase_error(
            TransformationPhase.INPUT_VALIDATION,
            Exception("Test error"),
            duration_ms=50.0,
            correlation_id="test-123",
            execution_id="exec-456"
        )
        
        # Test performance threshold logging
        logger.log_performance_threshold_exceeded(
            PerformanceThreshold.TRANSFORMATION_LATENCY,
            current_value=2500.0,
            threshold_value=2000.0,
            correlation_id="test-123"
        )
    
    def test_circuit_breaker_logger(self):
        """Test circuit breaker logging."""
        logger = CircuitBreakerLogger("test_service")
        
        logger.log_circuit_opened("test_service", failure_count=5)
        logger.log_circuit_closed("test_service")
        logger.log_circuit_half_open("test_service")
        logger.log_call_success("test_service", duration_ms=100.0)
        logger.log_call_failure("test_service", Exception("Test error"))


class TestErrorRecovery:
    """Test error recovery mechanisms."""
    
    def test_retry_strategy(self):
        """Test retry strategy implementations."""
        # Test exponential backoff
        exponential = RetryStrategy.exponential_backoff(
            max_retries=3,
            base_delay=1.0,
            max_delay=10.0
        )
        
        delays = [exponential.get_delay(attempt) for attempt in range(4)]
        assert delays[0] == 1.0  # First retry
        assert delays[1] == 2.0  # Second retry
        assert delays[2] == 4.0  # Third retry
        assert delays[3] == 8.0  # Fourth retry (capped at max_delay if configured)
        
        # Test linear backoff
        linear = RetryStrategy.linear_backoff(max_retries=3, delay=2.0)
        delays = [linear.get_delay(attempt) for attempt in range(4)]
        assert all(delay == 2.0 for delay in delays)
        
        # Test fixed delay
        fixed = RetryStrategy.fixed_delay(max_retries=3, delay=1.5)
        delays = [fixed.get_delay(attempt) for attempt in range(4)]
        assert all(delay == 1.5 for delay in delays)
    
    def test_circuit_breaker(self):
        """Test circuit breaker functionality."""
        circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=1.0,
            success_threshold=2
        )
        
        # Initially closed
        assert circuit_breaker.state == "closed"
        assert circuit_breaker.can_execute()
        
        # Record failures to open circuit
        for _ in range(3):
            circuit_breaker.record_failure()
        
        assert circuit_breaker.state == "open"
        assert not circuit_breaker.can_execute()
        
        # Wait for recovery timeout
        time.sleep(1.1)
        assert circuit_breaker.state == "half_open"
        assert circuit_breaker.can_execute()
        
        # Record successes to close circuit
        for _ in range(2):
            circuit_breaker.record_success()
        
        assert circuit_breaker.state == "closed"
    
    def test_fallback_provider(self):
        """Test fallback mechanisms."""
        fallback = FallbackProvider()
        
        # Test default value fallback
        result = fallback.get_default_value("string", "default_string")
        assert result == "default_string"
        
        result = fallback.get_default_value("int", 42)
        assert result == 42
        
        # Test cached value fallback
        fallback.cache_value("test_key", "cached_value")
        result = fallback.get_cached_value("test_key")
        assert result == "cached_value"
        
        # Test degraded service response
        degraded = fallback.get_degraded_service_response("test_service")
        assert "service" in degraded
        assert degraded["available"] is False
    
    def test_error_recovery_manager(self):
        """Test error recovery manager."""
        recovery_manager = ErrorRecoveryManager()
        
        # Test retry with success
        call_count = 0
        def successful_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary failure")
            return "success"
        
        result = recovery_manager.execute_with_recovery(
            successful_function,
            retry_strategy=RetryStrategy.fixed_delay(max_retries=3, delay=0.1),
            fallback_value="fallback"
        )
        
        assert result == "success"
        assert call_count == 2
        
        # Test retry with fallback
        def failing_function():
            raise Exception("Permanent failure")
        
        result = recovery_manager.execute_with_recovery(
            failing_function,
            retry_strategy=RetryStrategy.fixed_delay(max_retries=2, delay=0.1),
            fallback_value="fallback_used"
        )
        
        assert result == "fallback_used"
    
    def test_with_retry_decorator(self):
        """Test retry decorator."""
        call_count = 0
        
        @with_retry(max_retries=3, delay=0.1)
        def decorated_function(should_fail: bool = True):
            nonlocal call_count
            call_count += 1
            if should_fail and call_count < 3:
                raise Exception("Temporary failure")
            return f"success_attempt_{call_count}"
        
        # Test successful retry
        call_count = 0
        result = decorated_function(should_fail=True)
        assert result == "success_attempt_3"
        assert call_count == 3
        
        # Test immediate success
        call_count = 0
        result = decorated_function(should_fail=False)
        assert result == "success_attempt_1"
        assert call_count == 1


class TestPerformanceMonitoring:
    """Test performance monitoring and alerting."""
    
    def test_performance_monitor_initialization(self):
        """Test performance monitor setup."""
        monitor = PerformanceMonitor()
        
        # Check default thresholds are set
        assert "transformation_latency" in monitor.thresholds
        assert "api_response_time" in monitor.thresholds
        assert "error_rate" in monitor.thresholds
        assert "memory_usage" in monitor.thresholds
        assert "cpu_usage" in monitor.thresholds
    
    def test_metric_recording(self):
        """Test metric recording and statistics."""
        monitor = PerformanceMonitor()
        
        # Record some metrics
        for i in range(5):
            monitor.record_metric(
                name="test_metric",
                value=float(i * 10),
                metric_type=MetricType.LATENCY,
                correlation_id="test-123"
            )
        
        # Get statistics
        stats = monitor.get_metric_statistics("test_metric")
        assert stats is not None
        assert stats["count"] == 5
        assert stats["mean"] == 20.0  # (0+10+20+30+40)/5
        assert stats["min"] == 0.0
        assert stats["max"] == 40.0
    
    def test_operation_timing(self):
        """Test operation timing functionality."""
        monitor = PerformanceMonitor()
        
        # Test timer operations
        timer_key = monitor.start_operation_timer("test_operation", "test-123")
        time.sleep(0.1)  # Simulate work
        duration = monitor.end_operation_timer(
            timer_key,
            "test_operation",
            "test-123",
            "exec-456"
        )
        
        assert duration >= 100.0  # At least 100ms
        
        # Check metric was recorded
        stats = monitor.get_metric_statistics("test_operation_latency")
        assert stats is not None
        assert stats["count"] == 1
    
    def test_transformation_metrics(self):
        """Test transformation-specific metrics."""
        monitor = PerformanceMonitor()
        
        monitor.record_transformation_metrics(
            phase=TransformationPhase.INPUT_VALIDATION,
            duration_ms=150.0,
            success=True,
            correlation_id="test-123",
            execution_id="exec-456",
            input_size=1000,
            output_size=800
        )
        
        # Check metrics were recorded
        duration_stats = monitor.get_metric_statistics("transformation_input_validation_duration")
        assert duration_stats is not None
        assert duration_stats["count"] == 1
        assert duration_stats["mean"] == 150.0
        
        success_stats = monitor.get_metric_statistics("transformation_input_validation_success_rate")
        assert success_stats is not None
        assert success_stats["mean"] == 1.0  # 100% success
        
        throughput_stats = monitor.get_metric_statistics("transformation_input_validation_throughput")
        assert throughput_stats is not None
        assert throughput_stats["mean"] > 0  # Should have calculated throughput
    
    def test_alert_thresholds(self):
        """Test alert threshold configuration and triggering."""
        monitor = PerformanceMonitor()
        
        # Add custom threshold
        threshold = AlertThreshold(
            metric_name="test_alert_metric",
            threshold_value=100.0,
            threshold_type=ThresholdType.GREATER_THAN,
            severity=AlertSeverity.HIGH,
            min_samples=1,
            description="Test alert threshold"
        )
        monitor.add_threshold(threshold)
        
        # Record metric that should trigger alert
        monitor.record_metric(
            name="test_alert_metric",
            value=150.0,
            metric_type=MetricType.LATENCY,
            correlation_id="test-123"
        )
        
        # Check alert was triggered
        active_alerts = monitor.get_active_alerts()
        assert len(active_alerts) > 0
        
        alert = active_alerts[0]
        assert alert.metric_name == "test_alert_metric"
        assert alert.current_value == 150.0
        assert alert.threshold_value == 100.0
        assert alert.severity == AlertSeverity.HIGH
    
    def test_performance_timer_decorator(self):
        """Test performance timer decorator."""
        call_count = 0
        
        @performance_timer("decorated_operation")
        def timed_function(correlation_id=None, execution_id=None):
            nonlocal call_count
            call_count += 1
            time.sleep(0.05)  # Simulate work
            return "completed"
        
        result = timed_function(correlation_id="test-123", execution_id="exec-456")
        assert result == "completed"
        assert call_count == 1
        
        # Check metrics were recorded
        monitor = get_performance_monitor()
        latency_stats = monitor.get_metric_statistics("decorated_operation_latency")
        assert latency_stats is not None
        assert latency_stats["count"] >= 1
        
        success_stats = monitor.get_metric_statistics("decorated_operation_success_rate")
        assert success_stats is not None
        assert success_stats["mean"] == 1.0  # 100% success
    
    def test_convenience_functions(self):
        """Test convenience functions for common monitoring patterns."""
        # Test API latency recording
        record_api_latency("test_endpoint", 125.5, "test-123")
        
        monitor = get_performance_monitor()
        stats = monitor.get_metric_statistics("api_test_endpoint_latency")
        assert stats is not None
        assert stats["mean"] == 125.5
        
        # Test transformation performance recording
        record_transformation_performance(
            phase=TransformationPhase.DATA_EXTRACTION,
            duration_ms=200.0,
            success=True,
            correlation_id="test-123",
            execution_id="exec-456",
            input_size=500
        )
        
        duration_stats = monitor.get_metric_statistics("transformation_data_extraction_duration")
        assert duration_stats is not None
        assert duration_stats["mean"] == 200.0


class TestTransformationFunctionErrorHandling:
    """Test error handling in the transformation function."""
    
    def test_invalid_task_context_handling(self):
        """Test handling of invalid task context."""
        # Test None input
        with pytest.raises(InvalidTaskContextError) as exc_info:
            project_status_from_task_context(None, "test-123", "exec-456")
        
        assert "task_context cannot be None" in str(exc_info.value)
        assert exc_info.value.correlation_id == "test-123"
        assert exc_info.value.execution_id == "exec-456"
        
        # Test non-dict input
        with pytest.raises(InvalidTaskContextError) as exc_info:
            project_status_from_task_context("invalid", "test-123", "exec-456")
        
        assert "must be a dictionary" in str(exc_info.value)
        
        # Test empty dict
        with pytest.raises(InvalidTaskContextError) as exc_info:
            project_status_from_task_context({}, "test-123", "exec-456")
        
        assert "cannot be empty" in str(exc_info.value)
    
    def test_missing_nodes_handling(self):
        """Test handling of missing nodes in task context."""
        task_context = {"edges": []}
        
        with pytest.raises(InvalidTaskContextError) as exc_info:
            project_status_from_task_context(task_context, "test-123", "exec-456")
        
        assert "nodes" in str(exc_info.value)
        assert exc_info.value.expected_keys == ["nodes"]
    
    def test_invalid_node_data_handling(self):
        """Test handling of invalid node data."""
        # Test non-dict node
        task_context = {
            "nodes": ["invalid_node"]
        }
        
        with pytest.raises(NodeDataError) as exc_info:
            project_status_from_task_context(task_context, "test-123", "exec-456")
        
        assert "must be a dictionary" in str(exc_info.value)
        
        # Test node without required fields
        task_context = {
            "nodes": [{"invalid": "node"}]
        }
        
        with pytest.raises(FieldExtractionError) as exc_info:
            project_status_from_task_context(task_context, "test-123", "exec-456")
        
        assert "status" in str(exc_info.value) or "id" in str(exc_info.value)
    
    def test_successful_transformation_with_logging(self):
        """Test successful transformation with proper logging."""
        task_context = {
            "nodes": [
                {"id": "node1", "status": "completed", "type": "task"},
                {"id": "node2", "status": "in_progress", "type": "task"},
                {"id": "node3", "status": "pending", "type": "task"}
            ]
        }
        
        result = project_status_from_task_context(task_context, "test-123", "exec-456")
        
        assert result is not None
        assert hasattr(result, 'total_nodes')
        assert hasattr(result, 'completed_nodes')
        assert hasattr(result, 'in_progress_nodes')
        assert hasattr(result, 'pending_nodes')
        assert hasattr(result, 'completion_percentage')
        
        assert result.total_nodes == 3
        assert result.completed_nodes == 1
        assert result.in_progress_nodes == 1
        assert result.pending_nodes == 1
        assert result.completion_percentage == 33.33


class TestServiceLayerErrorHandling:
    """Test error handling in service layer."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return Mock()
    
    def test_status_projection_service_error_handling(self, mock_db_session):
        """Test StatusProjectionService error handling."""
        service = StatusProjectionService(mock_db_session)
        
        # Test database error handling
        mock_db_session.execute.side_effect = Exception("Database connection failed")
        
        with pytest.raises(DatabaseError) as exc_info:
            service.get_status_projection("test-execution-123")
        
        assert "Database operation failed" in str(exc_info.value)
        assert exc_info.value.operation == "SELECT"
        
        # Test validation error handling
        with pytest.raises(ClarityValidationError) as exc_info:
            service.create_status_projection(None, "test-123", "exec-456")
        
        assert "task_context cannot be None" in str(exc_info.value)
    
    def test_service_recovery_mechanisms(self, mock_db_session):
        """Test service layer recovery mechanisms."""
        service = StatusProjectionService(mock_db_session)
        
        # Mock intermittent failure followed by success
        call_count = 0
        def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary database error")
            return Mock(fetchone=Mock(return_value=None))
        
        mock_db_session.execute.side_effect = mock_execute
        
        # This should succeed after retries
        result = service.get_status_projection("test-execution-123")
        assert call_count == 3  # Should have retried twice


class TestIntegrationScenarios:
    """Test integrated error handling scenarios."""
    
    def test_end_to_end_error_recovery(self):
        """Test end-to-end error recovery scenario."""
        # Simulate a complete transformation pipeline with errors
        task_context = {
            "nodes": [
                {"id": "node1", "status": "completed", "type": "task"},
                {"id": "node2", "status": "in_progress", "type": "task"}
            ]
        }
        
        # Test with error recovery
        recovery_manager = ErrorRecoveryManager()
        
        call_count = 0
        def transformation_with_intermittent_failure():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ServiceError("Temporary service failure")
            return project_status_from_task_context(task_context, "test-123", "exec-456")
        
        result = recovery_manager.execute_with_recovery(
            transformation_with_intermittent_failure,
            retry_strategy=RetryStrategy.fixed_delay(max_retries=3, delay=0.1),
            fallback_value=None
        )
        
        assert result is not None
        assert result.total_nodes == 2
        assert call_count == 2  # Should have succeeded on second attempt
    
    def test_performance_monitoring_integration(self):
        """Test performance monitoring integration with error handling."""
        monitor = get_performance_monitor()
        
        # Test performance monitoring with errors
        @performance_timer("integration_test")
        def operation_with_error(should_fail=False):
            if should_fail:
                raise ServiceError("Intentional failure")
            time.sleep(0.05)
            return "success"
        
        # Test successful operation
        result = operation_with_error(should_fail=False)
        assert result == "success"
        
        # Test failed operation
        with pytest.raises(ServiceError):
            operation_with_error(should_fail=True)
        
        # Check metrics were recorded for both success and failure
        latency_stats = monitor.get_metric_statistics("integration_test_latency")
        assert latency_stats is not None
        assert latency_stats["count"] >= 2  # At least 2 calls
        
        success_stats = monitor.get_metric_statistics("integration_test_success_rate")
        assert success_stats is not None
        # Should have both success (1.0) and failure (0.0) recorded
    
    def test_circuit_breaker_integration(self):
        """Test circuit breaker integration with service calls."""
        circuit_breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.1,
            success_threshold=1
        )
        
        call_count = 0
        def unreliable_service():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise ServiceError("Service failure")
            return "success"
        
        # First two calls should fail and open circuit
        for _ in range(2):
            if circuit_breaker.can_execute():
                try:
                    unreliable_service()
                    circuit_breaker.record_success()
                except ServiceError:
                    circuit_breaker.record_failure()
        
        assert circuit_breaker.state == "open"
        assert not circuit_breaker.can_execute()
        
        # Wait for recovery timeout
        time.sleep(0.15)
        assert circuit_breaker.state == "half_open"
        assert circuit_breaker.can_execute()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])