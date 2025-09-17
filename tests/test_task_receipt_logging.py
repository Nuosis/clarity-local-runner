"""
Test module for task receipt logging implementation (Task 2.3.B).

This module tests the task receipt logging functionality including:
- Task receipt logging with correlationId and event type for audit trail
- Event schema validation before processing with meaningful error messages
- All required audit trail fields (correlationId, projectId, executionId, taskId, eventType)
- JSON format for machine parsing
- Performance requirements
"""

import json
import logging
import pytest
import time
from io import StringIO
from unittest.mock import patch, MagicMock
from datetime import datetime

from core.structured_logging import get_structured_logger, LogStatus
from worker.tasks import process_incoming_event
from schemas.event_schema import EventRequest
from pydantic import ValidationError as PydanticValidationError


class TestTaskReceiptLogging:
    """Test cases for task receipt logging functionality."""
    
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
    
    @patch('app.worker.tasks.contextmanager')
    @patch('app.worker.tasks.GenericRepository')
    @patch('app.worker.tasks.WorkflowRegistry')
    def test_task_receipt_logging_with_correlation_id(self, mock_registry, mock_repo, mock_contextmanager, log_capture):
        """Test that task receipt is logged with correlationId and event type."""
        # Mock task request with headers
        mock_task_request = MagicMock()
        mock_task_request.id = "task_receipt_123"
        mock_task_request.headers = {
            "correlation_id": "receipt_test_456",
            "project_id": "test_project_789",
            "event_type": "DEVTEAM_AUTOMATION"
        }
        
        # Mock database session and event
        mock_session = MagicMock()
        mock_contextmanager.return_value.__enter__.return_value = mock_session
        
        mock_event = MagicMock()
        mock_event.id = "event_receipt_123"
        mock_event.workflow_type = "test_workflow"
        mock_event.data = {
            "id": "evt_test_123",
            "type": "DEVTEAM_AUTOMATION",
            "project_id": "test_project_789",
            "task": {
                "id": "1.1.1",
                "title": "Test task"
            }
        }
        
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
        process_incoming_event(mock_self, "event_receipt_123")
        
        # Verify task receipt logging
        log_output = log_capture.getvalue()
        log_lines = [line for line in log_output.strip().split('\n') if line]
        
        # Should have task receipt log entry as first entry
        assert len(log_lines) >= 1
        
        # Parse first log entry (task receipt)
        first_log_entry = json.loads(log_lines[0])
        
        # Verify task receipt log entry
        assert first_log_entry["message"] == "Task received for processing"
        assert first_log_entry["correlationId"] == "receipt_test_456"
        assert first_log_entry["projectId"] == "test_project_789"
        assert first_log_entry["executionId"] == "exec_event_receipt_123"
        assert first_log_entry["taskId"] == "task_receipt_123"
        assert first_log_entry["node"] == "task_receipt"
        assert first_log_entry["status"] == "started"
        assert first_log_entry["event_id"] == "event_receipt_123"
        assert first_log_entry["event_type"] == "DEVTEAM_AUTOMATION"
        assert first_log_entry["message_type"] == "task_receipt"
        assert first_log_entry["level"] == "INFO"
        assert "timestamp" in first_log_entry
    
    @patch('app.worker.tasks.contextmanager')
    @patch('app.worker.tasks.GenericRepository')
    def test_event_schema_validation_success(self, mock_repo, mock_contextmanager, log_capture):
        """Test successful event schema validation logging."""
        # Mock task request
        mock_task_request = MagicMock()
        mock_task_request.id = "validation_task_123"
        mock_task_request.headers = {
            "correlation_id": "validation_test_456",
            "project_id": "validation_project",
            "event_type": "DEVTEAM_AUTOMATION"
        }
        
        # Mock database session and valid event
        mock_session = MagicMock()
        mock_contextmanager.return_value.__enter__.return_value = mock_session
        
        mock_event = MagicMock()
        mock_event.id = "valid_event_123"
        mock_event.workflow_type = "test_workflow"
        mock_event.data = {
            "id": "evt_valid_123",
            "type": "DEVTEAM_AUTOMATION",
            "project_id": "validation_project",
            "task": {
                "id": "1.1.1",
                "title": "Valid test task"
            }
        }
        
        mock_repo_instance = MagicMock()
        mock_repo_instance.get.return_value = mock_event
        mock_repo.return_value = mock_repo_instance
        
        # Create task instance
        mock_self = MagicMock()
        mock_self.request = mock_task_request
        
        # Mock workflow execution to avoid full execution
        with patch('app.worker.tasks.WorkflowRegistry') as mock_registry:
            mock_workflow_class = MagicMock()
            mock_workflow = MagicMock()
            mock_workflow.run.return_value = MagicMock()
            mock_workflow.run.return_value.model_dump.return_value = {"result": "success"}
            mock_workflow_class.return_value = mock_workflow
            mock_registry.__getitem__.return_value.value = mock_workflow_class
            
            # Execute task
            process_incoming_event(mock_self, "valid_event_123")
        
        # Verify schema validation success logging
        log_output = log_capture.getvalue()
        log_lines = [line for line in log_output.strip().split('\n') if line]
        
        # Find schema validation success log
        validation_log = None
        for line in log_lines:
            log_entry = json.loads(line)
            if log_entry.get("node") == "schema_validation" and log_entry.get("status") == "completed":
                validation_log = log_entry
                break
        
        assert validation_log is not None
        assert validation_log["message"] == "Event schema validation successful"
        assert validation_log["correlationId"] == "validation_test_456"
        assert validation_log["projectId"] == "validation_project"
        assert validation_log["node"] == "schema_validation"
        assert validation_log["status"] == "completed"
    
    @patch('app.worker.tasks.contextmanager')
    @patch('app.worker.tasks.GenericRepository')
    def test_event_schema_validation_failure(self, mock_repo, mock_contextmanager, log_capture):
        """Test event schema validation failure with meaningful error messages."""
        # Mock task request
        mock_task_request = MagicMock()
        mock_task_request.id = "invalid_task_123"
        mock_task_request.headers = {
            "correlation_id": "invalid_test_456",
            "project_id": "invalid_project",
            "event_type": "DEVTEAM_AUTOMATION"
        }
        
        # Mock database session and invalid event
        mock_session = MagicMock()
        mock_contextmanager.return_value.__enter__.return_value = mock_session
        
        mock_event = MagicMock()
        mock_event.id = "invalid_event_123"
        mock_event.workflow_type = "test_workflow"
        # Invalid event data - missing required fields
        mock_event.data = {
            "id": "evt_invalid_123",
            "type": "DEVTEAM_AUTOMATION"
            # Missing project_id and task fields required for DEVTEAM_AUTOMATION
        }
        
        mock_repo_instance = MagicMock()
        mock_repo_instance.get.return_value = mock_event
        mock_repo.return_value = mock_repo_instance
        
        # Create task instance
        mock_self = MagicMock()
        mock_self.request = mock_task_request
        
        # Execute task - should fail validation
        with pytest.raises(ValueError) as exc_info:
            process_incoming_event(mock_self, "invalid_event_123")
        
        # Verify error message contains validation details
        assert "Event schema validation failed" in str(exc_info.value)
        
        # Verify schema validation failure logging
        log_output = log_capture.getvalue()
        log_lines = [line for line in log_output.strip().split('\n') if line]
        
        # Find schema validation failure log
        validation_error_log = None
        for line in log_lines:
            log_entry = json.loads(line)
            if log_entry.get("node") == "schema_validation" and log_entry.get("status") == "failed":
                validation_error_log = log_entry
                break
        
        assert validation_error_log is not None
        assert validation_error_log["message"] == "Event schema validation failed"
        assert validation_error_log["correlationId"] == "invalid_test_456"
        assert validation_error_log["projectId"] == "invalid_project"
        assert validation_error_log["node"] == "schema_validation"
        assert validation_error_log["status"] == "failed"
        assert "validation_errors" in validation_error_log
        assert len(validation_error_log["validation_errors"]) > 0
        
        # Verify meaningful error details
        error_details = validation_error_log["validation_errors"]
        assert any("project_id" in error["field"] for error in error_details)
        assert any("task" in error["field"] for error in error_details)
    
    def test_audit_trail_completeness(self, log_capture):
        """Test that all required audit trail fields are included."""
        logger = get_structured_logger("audit_test")
        
        # Test task receipt logging with all required fields
        correlation_id = "audit_test_123"
        project_id = "audit_project"
        execution_id = "exec_audit_456"
        task_id = "task_audit_789"
        event_type = "DEVTEAM_AUTOMATION"
        
        logger.info(
            "Task received for processing",
            correlation_id=correlation_id,
            project_id=project_id,
            execution_id=execution_id,
            task_id=task_id,
            node="task_receipt",
            status=LogStatus.STARTED,
            event_id="event_audit_123",
            event_type=event_type,
            message_type="task_receipt"
        )
        
        log_output = log_capture.getvalue()
        log_entry = json.loads(log_output.strip())
        
        # Verify all required audit trail fields
        required_fields = [
            "correlationId", "projectId", "executionId", "taskId", 
            "eventType", "timestamp", "level", "message", "node", "status"
        ]
        
        for field in required_fields:
            assert field in log_entry, f"Required field {field} missing from audit trail"
        
        # Verify field values
        assert log_entry["correlationId"] == correlation_id
        assert log_entry["projectId"] == project_id
        assert log_entry["executionId"] == execution_id
        assert log_entry["taskId"] == task_id
        assert log_entry["event_type"] == event_type
        assert log_entry["message_type"] == "task_receipt"
    
    def test_json_format_machine_readable(self, log_capture):
        """Test that log entries are in JSON format for machine parsing."""
        logger = get_structured_logger("json_test")
        
        logger.info(
            "Task received for processing",
            correlation_id="json_test_123",
            project_id="json_project",
            execution_id="exec_json_456",
            task_id="task_json_789",
            node="task_receipt",
            status=LogStatus.STARTED,
            event_id="event_json_123",
            event_type="DEVTEAM_AUTOMATION",
            message_type="task_receipt"
        )
        
        log_output = log_capture.getvalue().strip()
        
        # Should be valid JSON
        log_entry = json.loads(log_output)
        
        # Verify JSON structure
        assert isinstance(log_entry, dict)
        assert "timestamp" in log_entry
        assert "level" in log_entry
        assert "message" in log_entry
        
        # Verify timestamp is ISO format
        timestamp = log_entry["timestamp"]
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))  # Should not raise exception
    
    def test_performance_requirements(self):
        """Test that task receipt logging meets performance requirements."""
        logger = get_structured_logger("performance_test")
        
        # Test logging performance
        start_time = time.time()
        
        for i in range(100):
            logger.info(
                "Task received for processing",
                correlation_id=f"perf_test_{i}",
                project_id="performance_project",
                execution_id=f"exec_perf_{i}",
                task_id=f"task_perf_{i}",
                node="task_receipt",
                status=LogStatus.STARTED,
                event_id=f"event_perf_{i}",
                event_type="DEVTEAM_AUTOMATION",
                message_type="task_receipt"
            )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete 100 log entries quickly
        assert duration < 0.1, f"Logging took {duration:.3f}s, exceeds performance requirement"
        
        # Average time per log entry should be under 1ms
        avg_time_per_log = (duration / 100) * 1000  # Convert to milliseconds
        assert avg_time_per_log < 1.0, f"Average time per log: {avg_time_per_log:.3f}ms"
    
    @patch('app.worker.tasks.contextmanager')
    @patch('app.worker.tasks.GenericRepository')
    def test_correlation_id_fallback(self, mock_repo, mock_contextmanager, log_capture):
        """Test that event_id is used as correlationId when not provided."""
        # Mock task request without correlation_id
        mock_task_request = MagicMock()
        mock_task_request.id = "fallback_task_123"
        mock_task_request.headers = {
            "project_id": "fallback_project",
            "event_type": "PLACEHOLDER"
        }
        
        # Mock database session and event
        mock_session = MagicMock()
        mock_contextmanager.return_value.__enter__.return_value = mock_session
        
        mock_event = MagicMock()
        mock_event.id = "fallback_event_123"
        mock_event.workflow_type = "test_workflow"
        mock_event.data = {
            "id": "evt_fallback_123",
            "type": "PLACEHOLDER"
        }
        
        mock_repo_instance = MagicMock()
        mock_repo_instance.get.return_value = mock_event
        mock_repo.return_value = mock_repo_instance
        
        # Create task instance
        mock_self = MagicMock()
        mock_self.request = mock_task_request
        
        # Mock workflow execution
        with patch('app.worker.tasks.WorkflowRegistry') as mock_registry:
            mock_workflow_class = MagicMock()
            mock_workflow = MagicMock()
            mock_workflow.run.return_value = MagicMock()
            mock_workflow.run.return_value.model_dump.return_value = {"result": "success"}
            mock_workflow_class.return_value = mock_workflow
            mock_registry.__getitem__.return_value.value = mock_workflow_class
            
            # Execute task
            process_incoming_event(mock_self, "fallback_event_123")
        
        # Verify correlation_id fallback
        log_output = log_capture.getvalue()
        log_lines = [line for line in log_output.strip().split('\n') if line]
        
        # Parse first log entry (task receipt)
        first_log_entry = json.loads(log_lines[0])
        
        # Should use event_id as correlation_id when not provided
        assert first_log_entry["correlationId"] == "fallback_event_123"


if __name__ == "__main__":
    pytest.main([__file__])