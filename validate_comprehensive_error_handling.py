"""
Comprehensive Error Handling Validation Script

This script validates all error handling implementations by running
comprehensive tests and checking system behavior under various
error conditions.
"""

import sys
import time
import json
import traceback
from typing import Dict, Any, List, Optional
from datetime import datetime

# Import all our error handling components for validation
try:
    from core.exceptions import (
        ClarityBaseException,
        DatabaseError,
        ServiceError,
        APIError,
        TaskContextTransformationError,
        InvalidTaskContextError,
        NodeDataError,
        StatusCalculationError,
        FieldExtractionError,
        RepositoryError
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
    
    print("✅ All error handling modules imported successfully")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


class ErrorHandlingValidator:
    """Validates comprehensive error handling implementation."""
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "summary": {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "errors": []
            }
        }
        self.logger = get_structured_logger(__name__)
    
    def run_test(self, test_name: str, test_func):
        """Run a single test and record results."""
        print(f"\n🧪 Running test: {test_name}")
        self.results["summary"]["total_tests"] += 1
        
        try:
            test_func()
            print(f"✅ {test_name} - PASSED")
            self.results["tests"][test_name] = {
                "status": "PASSED",
                "error": None
            }
            self.results["summary"]["passed"] += 1
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"❌ {test_name} - FAILED: {error_msg}")
            self.results["tests"][test_name] = {
                "status": "FAILED",
                "error": error_msg,
                "traceback": traceback.format_exc()
            }
            self.results["summary"]["failed"] += 1
            self.results["summary"]["errors"].append(f"{test_name}: {error_msg}")
    
    def test_custom_exceptions(self):
        """Test custom exception classes."""
        # Test base exception
        error = ClarityBaseException(
            message="Test error",
            error_code="TEST_001",
            correlation_id="test-123"
        )
        assert str(error) == "Test error"
        assert error.error_code == "TEST_001"
        assert error.correlation_id == "test-123"
        
        # Test database error
        db_error = DatabaseError(
            message="Database connection failed",
            correlation_id="test-123"
        )
        assert isinstance(db_error, ClarityBaseException)
        
        # Test service error
        service_error = ServiceError(
            message="Service unavailable",
            correlation_id="test-123"
        )
        assert isinstance(service_error, ClarityBaseException)
        
        # Test API error
        api_error = APIError(
            message="API request failed",
            correlation_id="test-123"
        )
        assert isinstance(api_error, ClarityBaseException)
        
        # Test transformation errors
        invalid_error = InvalidTaskContextError(
            message="Invalid task context",
            correlation_id="test-123"
        )
        assert isinstance(invalid_error, TaskContextTransformationError)
        
        node_error = NodeDataError(
            message="Invalid node data",
            correlation_id="test-123"
        )
        assert isinstance(node_error, TaskContextTransformationError)
        
        status_error = StatusCalculationError(
            message="Status calculation failed",
            correlation_id="test-123"
        )
        assert isinstance(status_error, TaskContextTransformationError)
        
        field_error = FieldExtractionError(
            message="Field extraction failed",
            correlation_id="test-123"
        )
        assert isinstance(field_error, TaskContextTransformationError)
        
        # Test backward compatibility
        repo_error = RepositoryError(
            message="Repository error",
            correlation_id="test-123"
        )
        assert isinstance(repo_error, DatabaseError)
    
    def test_structured_logging(self):
        """Test structured logging functionality."""
        # Test basic logger
        logger = get_structured_logger("test_module")
        assert logger is not None
        
        # Test transformation logger
        trans_logger = TransformationLogger(logger)
        assert trans_logger is not None
        
        # Test circuit breaker logger
        cb_logger = CircuitBreakerLogger("test_service", logger)
        assert cb_logger is not None
        
        # Test logging methods (should not raise exceptions)
        trans_logger.log_transformation_start("test-123", "exec-456")
        trans_logger.log_transformation_success("test-123", "exec-456", 100.0)
        trans_logger.log_transformation_error("test-123", "exec-456", Exception("Test error"))
        
        cb_logger.log_circuit_opened("test_service", 5, 3)
        cb_logger.log_circuit_closed("test_service", 2)
        cb_logger.log_circuit_half_open("test_service")
    
    def test_error_recovery(self):
        """Test error recovery mechanisms."""
        # Test retry strategy
        retry_strategy = RetryStrategy(max_retries=3, delay=0.1)
        assert retry_strategy.max_retries == 3
        assert retry_strategy.delay == 0.1
        
        # Test circuit breaker
        circuit_breaker = CircuitBreaker("test_service")
        assert circuit_breaker.name == "test_service"
        assert circuit_breaker.state == "closed"
        assert circuit_breaker.can_execute()
        
        # Test fallback provider
        fallback = FallbackProvider()
        assert fallback is not None
        
        # Test error recovery manager
        recovery_manager = ErrorRecoveryManager()
        assert recovery_manager is not None
        
        # Test retry decorator
        call_count = 0
        
        @with_retry("test_operation", max_retries=2, delay=0.1)
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary failure")
            return "success"
        
        result = test_function()
        assert result == "success"
        assert call_count == 2
    
    def test_performance_monitoring(self):
        """Test performance monitoring functionality."""
        # Test performance monitor
        monitor = PerformanceMonitor()
        assert monitor is not None
        
        # Test metric recording
        monitor.record_metric(
            name="test_metric",
            value=100.0,
            metric_type=MetricType.LATENCY,
            correlation_id="test-123"
        )
        
        # Test operation timing
        timer_key = monitor.start_operation_timer("test_operation", "test-123")
        time.sleep(0.05)  # Simulate work
        duration = monitor.end_operation_timer(
            timer_key,
            "test_operation",
            "test-123",
            "exec-456"
        )
        assert duration >= 50.0  # At least 50ms
        
        # Test transformation metrics
        monitor.record_transformation_metrics(
            phase=TransformationPhase.INPUT_VALIDATION,
            duration_ms=150.0,
            success=True,
            correlation_id="test-123",
            execution_id="exec-456"
        )
        
        # Test alert thresholds
        threshold = AlertThreshold(
            metric_name="test_alert_metric",
            threshold_value=100.0,
            threshold_type=ThresholdType.GREATER_THAN,
            severity=AlertSeverity.HIGH,
            min_samples=1,
            description="Test alert threshold"
        )
        monitor.add_threshold(threshold)
        
        # Test performance timer decorator
        @performance_timer("decorated_operation")
        def timed_function():
            time.sleep(0.02)
            return "completed"
        
        result = timed_function()
        assert result == "completed"
        
        # Test convenience functions
        record_api_latency("test_endpoint", 125.5, "test-123")
        record_transformation_performance(
            phase=TransformationPhase.DATA_EXTRACTION,
            duration_ms=200.0,
            success=True,
            correlation_id="test-123",
            execution_id="exec-456"
        )
    
    def test_transformation_function_error_handling(self):
        """Test transformation function error handling."""
        # Test None input
        try:
            project_status_from_task_context(None, "test-123", "exec-456")
            assert False, "Should have raised InvalidTaskContextError"
        except InvalidTaskContextError as e:
            assert "task_context cannot be None" in str(e)
            assert e.correlation_id == "test-123"
            assert e.execution_id == "exec-456"
        
        # Test non-dict input
        try:
            project_status_from_task_context("invalid", "test-123", "exec-456")
            assert False, "Should have raised InvalidTaskContextError"
        except InvalidTaskContextError as e:
            assert "must be a dictionary" in str(e)
        
        # Test empty dict
        try:
            project_status_from_task_context({}, "test-123", "exec-456")
            assert False, "Should have raised InvalidTaskContextError"
        except InvalidTaskContextError as e:
            assert "cannot be empty" in str(e)
        
        # Test missing nodes
        try:
            project_status_from_task_context({"edges": []}, "test-123", "exec-456")
            assert False, "Should have raised InvalidTaskContextError"
        except InvalidTaskContextError as e:
            assert "nodes" in str(e)
        
        # Test successful transformation
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
        assert result.total_nodes == 3
    
    def test_integration_scenarios(self):
        """Test integrated error handling scenarios."""
        # Test end-to-end error recovery
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
            operation_name="test_transformation",
            operation=transformation_with_intermittent_failure,
            correlation_id="test-123",
            retry_strategy=RetryStrategy(max_retries=3, delay=0.1),
            fallback_value=None
        )
        
        assert result is not None
        assert result.total_nodes == 2
        assert call_count == 2  # Should have succeeded on second attempt
        
        # Test performance monitoring integration
        monitor = get_performance_monitor()
        
        @performance_timer("integration_test")
        def operation_with_error(should_fail=False):
            if should_fail:
                raise ServiceError("Intentional failure")
            time.sleep(0.02)
            return "success"
        
        # Test successful operation
        result = operation_with_error(should_fail=False)
        assert result == "success"
        
        # Test failed operation
        try:
            operation_with_error(should_fail=True)
            assert False, "Should have raised ServiceError"
        except ServiceError:
            pass  # Expected
    
    def run_all_tests(self):
        """Run all validation tests."""
        print("🚀 Starting Comprehensive Error Handling Validation")
        print("=" * 60)
        
        # Run all tests
        self.run_test("Custom Exceptions", self.test_custom_exceptions)
        self.run_test("Structured Logging", self.test_structured_logging)
        self.run_test("Error Recovery", self.test_error_recovery)
        self.run_test("Performance Monitoring", self.test_performance_monitoring)
        self.run_test("Transformation Function Error Handling", self.test_transformation_function_error_handling)
        self.run_test("Integration Scenarios", self.test_integration_scenarios)
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        
        summary = self.results["summary"]
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed']} ✅")
        print(f"Failed: {summary['failed']} ❌")
        
        if summary["failed"] > 0:
            print("\n❌ FAILED TESTS:")
            for error in summary["errors"]:
                print(f"  - {error}")
        
        success_rate = (summary["passed"] / summary["total_tests"]) * 100
        print(f"\nSuccess Rate: {success_rate:.1f}%")
        
        if success_rate >= 90:
            print("🎉 VALIDATION PASSED - Comprehensive error handling is working correctly!")
            return True
        else:
            print("⚠️  VALIDATION FAILED - Some error handling components need attention")
            return False
    
    def save_results(self, filename: str = "error_handling_validation_results.json"):
        """Save validation results to file."""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"📄 Results saved to {filename}")


def main():
    """Main validation function."""
    validator = ErrorHandlingValidator()
    
    try:
        success = validator.run_all_tests()
        validator.save_results()
        
        if success:
            print("\n🎯 All error handling implementations validated successfully!")
            sys.exit(0)
        else:
            print("\n⚠️  Some validation tests failed. Check the results for details.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Validation failed with unexpected error: {e}")
        print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()