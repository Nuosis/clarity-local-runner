"""
Unit Tests for Verification Duration Metrics (Task 8.3.2)

This module tests the verification duration metric implementation that measures
time for build/test verification operations, ensuring:
- Performance overhead ≤1ms
- Integration with existing structured logging patterns
- Proper error handling and edge cases
- Metric emission and threshold validation
"""

import time
import unittest
from unittest.mock import Mock, patch, MagicMock
import pytest
from typing import Dict, Any

from core.performance_monitoring import (
    record_verification_duration,
    get_performance_monitor,
    MetricType,
    AlertSeverity,
    AlertThreshold,
    ThresholdType
)
from core.structured_logging import get_structured_logger


class TestVerificationDurationMetrics(unittest.TestCase):
    """Test suite for verification duration metrics implementation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.performance_monitor = get_performance_monitor()
        self.logger = get_structured_logger(__name__)
        
        # Clear any existing metrics for clean tests
        if hasattr(self.performance_monitor, 'metrics'):
            self.performance_monitor.metrics.clear()
        if hasattr(self.performance_monitor, 'active_alerts'):
            self.performance_monitor.active_alerts.clear()
    
    def test_record_verification_duration_basic_functionality(self):
        """Test basic verification duration recording functionality."""
        # Arrange
        start_time = time.time() - 5.0  # 5 seconds ago
        end_time = time.time()
        verification_type = "npm_ci"
        success = True
        correlation_id = "test_corr_123"
        execution_id = "exec_test_456"
        project_id = "project_789"
        
        # Act
        record_verification_duration(
            start_time=start_time,
            end_time=end_time,
            verification_type=verification_type,
            success=success,
            correlation_id=correlation_id,
            execution_id=execution_id,
            project_id=project_id
        )
        
        # Assert
        self.assertIn("verification_duration", self.performance_monitor.metrics)
        
        # Verify metric was recorded with correct type
        metric_window = self.performance_monitor.metrics["verification_duration"]
        values = metric_window.get_values_in_window()
        self.assertEqual(len(values), 1)
        
        # Verify duration is approximately 5000ms (allow for small timing variations)
        recorded_duration = values[0]
        self.assertGreater(recorded_duration, 4800)  # At least 4.8 seconds
        self.assertLess(recorded_duration, 5200)     # At most 5.2 seconds
    
    def test_record_verification_duration_with_tags(self):
        """Test verification duration recording includes proper tags."""
        # Arrange
        start_time = time.time() - 2.0
        end_time = time.time()
        verification_type = "npm_build"
        success = False
        project_id = "project_with_tags"
        operation_details = {
            "build_script": "build",
            "attempt": "1",
            "working_directory": "/workspace/repo"
        }
        
        # Act
        with patch.object(self.performance_monitor, 'record_metric') as mock_record:
            record_verification_duration(
                start_time=start_time,
                end_time=end_time,
                verification_type=verification_type,
                success=success,
                project_id=project_id,
                operation_details=operation_details
            )
            
            # Assert
            mock_record.assert_called_once()
            call_args = mock_record.call_args
            
            # Verify metric name and type
            self.assertEqual(call_args[1]['name'], "verification_duration")
            self.assertEqual(call_args[1]['metric_type'], MetricType.VERIFICATION_DURATION)
            
            # Verify tags are included
            tags = call_args[1]['tags']
            self.assertEqual(tags['verification_type'], verification_type)
            self.assertEqual(tags['success'], str(success))
            self.assertEqual(tags['project_id'], project_id)
            self.assertEqual(tags['build_script'], "build")
            self.assertEqual(tags['attempt'], "1")
            self.assertEqual(tags['working_directory'], "/workspace/repo")
    
    def test_record_verification_duration_performance_overhead(self):
        """Test that verification duration recording has ≤1ms overhead."""
        # Arrange
        start_time = time.time() - 1.0
        end_time = time.time()
        verification_type = "git_merge"
        success = True
        
        # Act - measure the overhead of recording the metric
        overhead_start = time.time()
        record_verification_duration(
            start_time=start_time,
            end_time=end_time,
            verification_type=verification_type,
            success=success
        )
        overhead_end = time.time()
        
        # Assert - overhead should be ≤1ms
        overhead_ms = (overhead_end - overhead_start) * 1000
        self.assertLessEqual(overhead_ms, 1.0, 
                           f"Verification duration recording overhead {overhead_ms:.3f}ms exceeds 1ms requirement")
    
    def test_record_verification_duration_multiple_measurements(self):
        """Test recording multiple verification duration measurements."""
        # Arrange
        base_time = time.time()
        measurements = [
            (base_time - 10.0, base_time - 8.0, "npm_ci", True),      # 2 seconds
            (base_time - 7.0, base_time - 2.0, "npm_build", True),   # 5 seconds
            (base_time - 1.5, base_time, "git_merge", False),        # 1.5 seconds
        ]
        
        # Act
        for start_time, end_time, verification_type, success in measurements:
            record_verification_duration(
                start_time=start_time,
                end_time=end_time,
                verification_type=verification_type,
                success=success,
                correlation_id=f"corr_{verification_type}"
            )
        
        # Assert
        metric_window = self.performance_monitor.metrics["verification_duration"]
        values = metric_window.get_values_in_window()
        self.assertEqual(len(values), 3)
        
        # Verify statistics
        stats = metric_window.get_statistics()
        self.assertEqual(stats["count"], 3)
        self.assertGreater(stats["mean"], 0)
        self.assertGreater(stats["max"], stats["min"])
    
    def test_verification_duration_threshold_alert(self):
        """Test that verification duration threshold alerts are triggered correctly."""
        # Arrange - set up a low threshold for testing
        test_threshold = AlertThreshold(
            metric_name="verification_duration",
            threshold_value=1000.0,  # 1 second threshold
            threshold_type=ThresholdType.GREATER_THAN,
            severity=AlertSeverity.HIGH,
            min_samples=1,  # Trigger on first sample
            description="Test verification duration threshold"
        )
        self.performance_monitor.add_threshold(test_threshold)
        
        # Act - record a duration that exceeds the threshold
        start_time = time.time() - 3.0  # 3 seconds ago
        end_time = time.time()
        
        record_verification_duration(
            start_time=start_time,
            end_time=end_time,
            verification_type="npm_ci",
            success=True,
            correlation_id="test_alert_corr"
        )
        
        # Assert - check that alert was triggered
        active_alerts = self.performance_monitor.get_active_alerts()
        verification_duration_alerts = [
            alert for alert in active_alerts 
            if alert.metric_name == "verification_duration"
        ]
        self.assertGreater(len(verification_duration_alerts), 0, 
                          "Expected verification duration alert to be triggered")
        
        alert = verification_duration_alerts[0]
        self.assertEqual(alert.severity, AlertSeverity.HIGH)
        self.assertGreater(alert.current_value, 1000.0)
    
    def test_verification_duration_integration_with_structured_logging(self):
        """Test integration with existing structured logging patterns."""
        # Arrange
        correlation_id = "struct_log_test_123"
        execution_id = "exec_struct_456"
        
        # Act
        with patch.object(self.logger, 'debug') as mock_debug:
            # The performance monitor should log the metric
            record_verification_duration(
                start_time=time.time() - 2.0,
                end_time=time.time(),
                verification_type="npm_build",
                success=True,
                correlation_id=correlation_id,
                execution_id=execution_id
            )
            
            # The performance monitoring system logs metrics internally
            # We verify the metric was recorded properly
            self.assertIn("verification_duration", self.performance_monitor.metrics)
    
    def test_verification_duration_edge_cases(self):
        """Test edge cases for verification duration recording."""
        # Test case 1: Zero duration (end_time == start_time)
        current_time = time.time()
        record_verification_duration(
            start_time=current_time,
            end_time=current_time,
            verification_type="git_merge",
            success=True
        )
        
        values = self.performance_monitor.metrics["verification_duration"].get_values_in_window()
        self.assertGreaterEqual(values[-1], 0)  # Should be 0 or very small positive
        
        # Test case 2: Very small duration
        record_verification_duration(
            start_time=current_time,
            end_time=current_time + 0.001,  # 1ms
            verification_type="npm_ci",
            success=True
        )
        
        values = self.performance_monitor.metrics["verification_duration"].get_values_in_window()
        self.assertGreater(len(values), 1)
    
    def test_verification_duration_error_handling(self):
        """Test error handling in verification duration recording."""
        # Test case 1: Invalid start_time (future time)
        future_time = time.time() + 100
        current_time = time.time()
        
        # Should not raise exception, but may log warning
        record_verification_duration(
            start_time=future_time,
            end_time=current_time,
            verification_type="npm_build",
            success=False
        )
        
        # Verify metric was still recorded (negative duration)
        values = self.performance_monitor.metrics["verification_duration"].get_values_in_window()
        self.assertGreater(len(values), 0)
    
    def test_verification_duration_metric_type_enum(self):
        """Test that VERIFICATION_DURATION metric type is properly defined."""
        # Assert
        self.assertTrue(hasattr(MetricType, 'VERIFICATION_DURATION'))
        self.assertEqual(MetricType.VERIFICATION_DURATION.value, "verification_duration")
    
    def test_default_verification_duration_threshold(self):
        """Test that default verification duration threshold is configured."""
        # Check if default threshold exists
        thresholds = self.performance_monitor.thresholds
        self.assertIn("verification_duration", thresholds)
        
        threshold = thresholds["verification_duration"]
        self.assertEqual(threshold.metric_name, "verification_duration")
        self.assertEqual(threshold.threshold_type, ThresholdType.GREATER_THAN)
        self.assertEqual(threshold.severity, AlertSeverity.HIGH)
        self.assertEqual(threshold.threshold_value, 30000.0)  # 30 seconds
    
    def test_verification_duration_statistics(self):
        """Test statistical calculations for verification duration metrics."""
        # Arrange - record several measurements with known durations
        base_time = time.time()
        durations_ms = [1000, 2000, 3000, 4000, 5000]  # Known durations in ms
        
        for i, duration_ms in enumerate(durations_ms):
            start_time = base_time - (duration_ms / 1000)
            end_time = base_time
            record_verification_duration(
                start_time=start_time,
                end_time=end_time,
                verification_type="npm_ci",
                success=True,
                correlation_id=f"stats_test_{i}"
            )
            base_time += 0.001  # Slight time progression
        
        # Act
        stats = self.performance_monitor.get_metric_statistics("verification_duration")
        
        # Assert
        self.assertIsNotNone(stats, "Verification duration statistics should not be None")
        if stats is not None:  # Additional safety check for type checker
            self.assertEqual(stats["count"], 5)
            self.assertAlmostEqual(stats["mean"], 3000, delta=100)  # Should be around 3000ms
            self.assertAlmostEqual(stats["min"], 1000, delta=50)    # Should be around 1000ms
            self.assertAlmostEqual(stats["max"], 5000, delta=50)    # Should be around 5000ms
    
    def test_verification_duration_different_types(self):
        """Test verification duration recording for different verification types."""
        # Arrange
        verification_types = ["npm_ci", "npm_build", "git_merge", "custom_verification"]
        base_time = time.time()
        
        # Act
        for i, verification_type in enumerate(verification_types):
            record_verification_duration(
                start_time=base_time - 1.0,
                end_time=base_time,
                verification_type=verification_type,
                success=i % 2 == 0,  # Alternate success/failure
                project_id=f"project_{i}",
                operation_details={"type_specific_detail": f"detail_{i}"}
            )
        
        # Assert
        metric_window = self.performance_monitor.metrics["verification_duration"]
        values = metric_window.get_values_in_window()
        self.assertEqual(len(values), len(verification_types))
    
    def test_verification_duration_with_operation_details_filtering(self):
        """Test that operation details are properly filtered for string values."""
        # Arrange
        operation_details = {
            "string_detail": "valid_string",
            "int_detail": 123,  # Should be filtered out
            "bool_detail": True,  # Should be filtered out
            "none_detail": None,  # Should be filtered out
            "another_string": "another_valid_string"
        }
        
        # Act
        with patch.object(self.performance_monitor, 'record_metric') as mock_record:
            record_verification_duration(
                start_time=time.time() - 1.0,
                end_time=time.time(),
                verification_type="npm_ci",
                success=True,
                operation_details=operation_details
            )
            
            # Assert
            call_args = mock_record.call_args
            tags = call_args[1]['tags']
            
            # Should include string values
            self.assertEqual(tags['string_detail'], "valid_string")
            self.assertEqual(tags['another_string'], "another_valid_string")
            
            # Should not include non-string values
            self.assertNotIn('int_detail', tags)
            self.assertNotIn('bool_detail', tags)
            self.assertNotIn('none_detail', tags)


class TestVerificationDurationIntegration(unittest.TestCase):
    """Integration tests for verification duration metrics with AiderExecutionService."""
    
    @patch('services.aider_execution_service.record_verification_duration')
    def test_aider_execution_service_npm_ci_integration(self, mock_record_duration):
        """Test that AiderExecutionService properly calls verification duration recording for npm ci."""
        from services.aider_execution_service import AiderExecutionService, AiderExecutionContext
        
        # Arrange
        service = AiderExecutionService("test_correlation_123")
        context = AiderExecutionContext(
            project_id="test_project",
            execution_id="test_execution"
        )
        
        # Mock the container setup and npm execution
        with patch.object(service, '_setup_container') as mock_setup, \
             patch.object(service, '_execute_npm_ci_command') as mock_npm_cmd, \
             patch.object(service, '_capture_npm_artifacts') as mock_artifacts:
            
            mock_setup.return_value = {'container': Mock(), 'container_id': 'test_container'}
            mock_npm_cmd.return_value = {'exit_code': 0, 'stdout': 'success', 'stderr': ''}
            mock_artifacts.return_value = {'files_modified': []}
            
            # Act
            try:
                service._execute_npm_ci_single_attempt(context, "/workspace", 1)
            except Exception:
                pass  # Expected due to mocked dependencies
            
            # Assert - verify verification duration was recorded
            mock_record_duration.assert_called()
            call_args = mock_record_duration.call_args
            self.assertEqual(call_args[1]['verification_type'], "npm_ci")
            self.assertEqual(call_args[1]['success'], True)
            self.assertEqual(call_args[1]['project_id'], "test_project")
            self.assertEqual(call_args[1]['execution_id'], "test_execution")


if __name__ == '__main__':
    unittest.main()