"""
Test module for structured logging implementation.

This module tests the comprehensive structured logging capabilities including:
- JSON format output for machine parsing
- Secret/token redaction for security
- Required fields: correlationId, projectId, executionId, taskId, node, status
- Performance impact validation
- Audit trail maintenance
"""

import json
import logging
import pytest
import time
from io import StringIO
from unittest.mock import patch, MagicMock
from datetime import datetime

from core.structured_logging import (
    get_structured_logger, 
    LogLevel, 
    LogStatus, 
    SecretRedactor,
    StructuredLogger
)


class TestSecretRedactor:
    """Test cases for secret redaction functionality."""
    
    def test_redact_api_keys(self):
        """Test redaction of API keys and tokens."""
        test_data = {
            "api_key": "sk-1234567890abcdef",
            "token": "ghp_abcdefghijklmnop",
            "secret": "super_secret_value",
            "password": "my_password123"
        }
        
        redacted = SecretRedactor.redact_secrets(test_data)
        
        assert redacted["api_key"] == "[REDACTED]"
        assert redacted["token"] == "[REDACTED]"
        assert redacted["secret"] == "[REDACTED]"
        assert redacted["password"] == "[REDACTED]"
    
    def test_redact_jwt_tokens(self):
        """Test redaction of JWT tokens."""
        jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        
        redacted = SecretRedactor.redact_secrets(jwt_token)
        
        assert redacted == "[JWT_TOKEN_REDACTED]"
    
    def test_redact_bearer_tokens(self):
        """Test redaction of Bearer tokens."""
        auth_header = "Bearer abc123def456"
        
        redacted = SecretRedactor.redact_secrets(auth_header)
        
        assert redacted == "Bearer [REDACTED]"
    
    def test_redact_database_urls(self):
        """Test redaction of database URLs with credentials."""
        db_url = "postgresql://user:password@localhost:5432/dbname"
        
        redacted = SecretRedactor.redact_secrets(db_url)
        
        assert "user" not in redacted
        assert "password" not in redacted
        assert "[USER]:[PASSWORD]" in redacted
    
    def test_preserve_non_sensitive_data(self):
        """Test that non-sensitive data is preserved."""
        test_data = {
            "user_id": "12345",
            "event_type": "test_event",
            "timestamp": "2025-01-01T00:00:00Z",
            "message": "This is a test message"
        }
        
        redacted = SecretRedactor.redact_secrets(test_data)
        
        assert redacted == test_data


class TestStructuredLogger:
    """Test cases for structured logger functionality."""
    
    @pytest.fixture
    def logger(self):
        """Create a structured logger for testing."""
        return get_structured_logger("test_logger")
    
    @pytest.fixture
    def log_capture(self):
        """Capture log output for testing."""
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.DEBUG)
        
        # Get the root logger and add our handler
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.DEBUG)
        
        yield log_stream
        
        # Clean up
        root_logger.removeHandler(handler)
    
    def test_structured_log_format(self, logger, log_capture):
        """Test that logs are output in JSON format."""
        correlation_id = "test_correlation_123"
        project_id = "test_project"
        execution_id = "exec_456"
        task_id = "task_789"
        
        logger.info(
            "Test message",
            correlation_id=correlation_id,
            project_id=project_id,
            execution_id=execution_id,
            task_id=task_id,
            node="test_node",
            status=LogStatus.COMPLETED
        )
        
        log_output = log_capture.getvalue()
        
        # Should be valid JSON
        log_entry = json.loads(log_output.strip())
        
        # Verify required fields
        assert log_entry["correlationId"] == correlation_id
        assert log_entry["projectId"] == project_id
        assert log_entry["executionId"] == execution_id
        assert log_entry["taskId"] == task_id
        assert log_entry["node"] == "test_node"
        assert log_entry["status"] == LogStatus.COMPLETED.value
        assert log_entry["level"] == "INFO"
        assert log_entry["message"] == "Test message"
        assert "timestamp" in log_entry
    
    def test_log_levels(self, logger, log_capture):
        """Test all log levels work correctly."""
        test_message = "Test message"
        
        # Test DEBUG level
        logger.debug(test_message, correlation_id="debug_test")
        debug_output = log_capture.getvalue()
        debug_entry = json.loads(debug_output.strip().split('\n')[0])
        assert debug_entry["level"] == "DEBUG"
        
        # Clear the buffer
        log_capture.truncate(0)
        log_capture.seek(0)
        
        # Test INFO level
        logger.info(test_message, correlation_id="info_test")
        info_output = log_capture.getvalue()
        info_entry = json.loads(info_output.strip())
        assert info_entry["level"] == "INFO"
        
        # Clear the buffer
        log_capture.truncate(0)
        log_capture.seek(0)
        
        # Test WARN level
        logger.warn(test_message, correlation_id="warn_test")
        warn_output = log_capture.getvalue()
        warn_entry = json.loads(warn_output.strip())
        assert warn_entry["level"] == "WARN"
        
        # Clear the buffer
        log_capture.truncate(0)
        log_capture.seek(0)
        
        # Test ERROR level
        test_error = ValueError("Test error")
        logger.error(test_message, correlation_id="error_test", error=test_error)
        error_output = log_capture.getvalue()
        error_entry = json.loads(error_output.strip())
        assert error_entry["level"] == "ERROR"
        assert error_entry["error_type"] == "ValueError"
        assert error_entry["error_message"] == "Test error"
    
    def test_secret_redaction_in_logs(self, logger, log_capture):
        """Test that secrets are redacted from log entries."""
        logger.info(
            "Processing authentication",
            correlation_id="secret_test",
            api_key="sk-1234567890abcdef",
            password="secret_password",
            jwt_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.signature"
        )
        
        log_output = log_capture.getvalue()
        log_entry = json.loads(log_output.strip())
        
        # Verify secrets are redacted
        assert log_entry["api_key"] == "[REDACTED]"
        assert log_entry["password"] == "[REDACTED]"
        assert log_entry["jwt_token"] == "[JWT_TOKEN_REDACTED]"
        
        # Verify correlation_id is preserved
        assert log_entry["correlationId"] == "secret_test"
    
    def test_context_persistence(self, logger, log_capture):
        """Test that context fields persist across log calls."""
        # Set persistent context
        logger.set_context(
            correlation_id="persistent_test",
            project_id="persistent_project"
        )
        
        # Log without specifying context fields
        logger.info("First message", task_id="task_1")
        logger.info("Second message", task_id="task_2")
        
        log_output = log_capture.getvalue()
        log_lines = log_output.strip().split('\n')
        
        # Both log entries should have persistent context
        first_entry = json.loads(log_lines[0])
        second_entry = json.loads(log_lines[1])
        
        assert first_entry["correlationId"] == "persistent_test"
        assert first_entry["projectId"] == "persistent_project"
        assert first_entry["taskId"] == "task_1"
        
        assert second_entry["correlationId"] == "persistent_test"
        assert second_entry["projectId"] == "persistent_project"
        assert second_entry["taskId"] == "task_2"
        
        # Clear context
        logger.clear_context()
    
    def test_performance_impact(self, logger):
        """Test that logging overhead meets performance SLAs."""
        # Test logging performance with large number of entries
        start_time = time.time()
        
        for i in range(1000):
            logger.info(
                f"Performance test message {i}",
                correlation_id=f"perf_test_{i}",
                project_id="performance_project",
                execution_id=f"exec_{i}",
                task_id=f"task_{i}",
                node="performance_test",
                status=LogStatus.COMPLETED,
                iteration=i
            )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete 1000 log entries in under 1 second
        assert duration < 1.0, f"Logging took {duration:.3f}s, exceeds 1s SLA"
        
        # Average time per log entry should be under 1ms
        avg_time_per_log = (duration / 1000) * 1000  # Convert to milliseconds
        assert avg_time_per_log < 1.0, f"Average time per log: {avg_time_per_log:.3f}ms"


class TestWorkerTaskLogging:
    """Test structured logging integration with worker tasks."""
    
    @patch('app.worker.tasks.contextmanager')
    @patch('app.worker.tasks.GenericRepository')
    @patch('app.worker.tasks.WorkflowRegistry')
    def test_worker_structured_logging(self, mock_registry, mock_repo, mock_contextmanager, log_capture):
        """Test that worker task uses structured logging correctly."""
        from worker.tasks import process_incoming_event
        
        # Mock task request
        mock_task_request = MagicMock()
        mock_task_request.id = "task_123"
        mock_task_request.headers = {
            "correlation_id": "worker_test_456",
            "project_id": "test_project_789",
            "event_type": "test_event"
        }
        
        # Mock database session and event
        mock_session = MagicMock()
        mock_contextmanager.return_value.__enter__.return_value = mock_session
        
        mock_event = MagicMock()
        mock_event.id = "event_123"
        mock_event.workflow_type = "test_workflow"
        mock_event.data = {"test": "data"}
        
        mock_repo_instance = MagicMock()
        mock_repo_instance.get.return_value = mock_event
        mock_repo.return_value = mock_repo_instance
        
        # Mock workflow execution
        mock_workflow_class = MagicMock()
        mock_workflow = MagicMock()
        mock_workflow.run.return_value = MagicMock()
        mock_workflow.run.return_value.model_dump.return_value = {"result": "success"}
        mock_workflow_class.return_value = mock_workflow
        mock_registry.__getitem__.return_value.value = mock_workflow_class
        
        # Create task instance with mocked request
        mock_self = MagicMock()
        mock_self.request = mock_task_request
        
        # Execute task
        process_incoming_event(mock_self, "event_123")
        
        # Verify structured logging was used
        log_output = log_capture.getvalue()
        log_lines = [line for line in log_output.strip().split('\n') if line]
        
        # Should have multiple structured log entries
        assert len(log_lines) >= 3  # Start, retrieval, completion
        
        # Verify each log entry is valid JSON with required fields
        for log_line in log_lines:
            log_entry = json.loads(log_line)
            
            # Required fields should be present
            assert "timestamp" in log_entry
            assert "level" in log_entry
            assert "message" in log_entry
            assert "correlationId" in log_entry
            assert "projectId" in log_entry
            assert "executionId" in log_entry
            assert "taskId" in log_entry
            assert "node" in log_entry
            assert "status" in log_entry
            
            # Verify values
            assert log_entry["correlationId"] == "worker_test_456"
            assert log_entry["projectId"] == "test_project_789"
            assert log_entry["taskId"] == "task_123"
            assert log_entry["executionId"] == "exec_event_123"


def test_audit_trail_completeness():
    """Test that audit trail captures all required information."""
    logger = get_structured_logger("audit_test")
    
    # Simulate a complete workflow execution
    correlation_id = "audit_test_123"
    project_id = "audit_project"
    execution_id = "exec_audit_456"
    task_id = "task_audit_789"
    
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        # Start
        logger.info(
            "Workflow started",
            correlation_id=correlation_id,
            project_id=project_id,
            execution_id=execution_id,
            task_id=task_id,
            node="workflow_start",
            status=LogStatus.STARTED
        )
        
        # Processing
        logger.info(
            "Processing data",
            correlation_id=correlation_id,
            project_id=project_id,
            execution_id=execution_id,
            task_id=task_id,
            node="data_processing",
            status=LogStatus.IN_PROGRESS
        )
        
        # Completion
        logger.info(
            "Workflow completed",
            correlation_id=correlation_id,
            project_id=project_id,
            execution_id=execution_id,
            task_id=task_id,
            node="workflow_completion",
            status=LogStatus.COMPLETED
        )
        
        log_output = mock_stdout.getvalue()
        log_lines = [line for line in log_output.strip().split('\n') if line]
        
        # Should have complete audit trail
        assert len(log_lines) == 3
        
        # Verify audit trail continuity
        for log_line in log_lines:
            log_entry = json.loads(log_line)
            assert log_entry["correlationId"] == correlation_id
            assert log_entry["projectId"] == project_id
            assert log_entry["executionId"] == execution_id
            assert log_entry["taskId"] == task_id
        
        # Verify status progression
        statuses = [json.loads(line)["status"] for line in log_lines]
        assert statuses == ["started", "in_progress", "completed"]


if __name__ == "__main__":
    pytest.main([__file__])