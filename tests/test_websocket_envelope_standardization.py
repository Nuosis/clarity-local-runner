"""
Test suite for WebSocket envelope standardization (Task 6.3.1).

This test validates that all WebSocket frames use the standardized envelope format:
{ type, ts, projectId, payload } as specified in ADD Section 6.

Tests cover:
- Envelope utility functions
- Message type validation
- Field naming consistency (projectId vs project_id)
- Timestamp formatting (ISO format with Z suffix)
- Service integration with envelope utilities
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
import json

from schemas.websocket_envelope import (
    WebSocketEnvelope,
    MessageType,
    create_envelope,
    create_execution_update_envelope,
    create_execution_log_envelope,
    create_error_envelope,
    create_completion_envelope
)
from services.execution_update_service import ExecutionUpdateService
from services.execution_log_service import ExecutionLogService, LogEntryType
from core.structured_logging import LogLevel


class TestWebSocketEnvelopeUtility:
    """Test the centralized envelope utility functions."""
    
    def test_message_type_enum_values(self):
        """Test that MessageType enum has all required values."""
        assert MessageType.EXECUTION_UPDATE == "execution-update"
        assert MessageType.EXECUTION_LOG == "execution-log"
        assert MessageType.ERROR == "error"
        assert MessageType.COMPLETION == "completion"
    
    def test_create_envelope_basic(self):
        """Test basic envelope creation with required fields."""
        project_id = "test-project-123"
        message_type = MessageType.EXECUTION_UPDATE
        payload = {"status": "running", "progress": 50}
        
        envelope = create_envelope(
            message_type=message_type,
            project_id=project_id,
            payload=payload
        )
        
        # Validate envelope structure
        assert envelope["type"] == "execution-update"
        assert envelope["projectId"] == project_id  # Must be projectId, not project_id
        assert envelope["payload"] == payload
        
        # Validate timestamp format (ISO with Z suffix)
        assert "ts" in envelope
        assert envelope["ts"].endswith("Z")
        
        # Validate timestamp is valid ISO format
        datetime.fromisoformat(envelope["ts"].replace("Z", "+00:00"))
    
    def test_create_envelope_field_naming_consistency(self):
        """Test that envelope always uses 'projectId' field name."""
        project_id = "test-project-456"
        
        envelope = create_envelope(
            message_type=MessageType.EXECUTION_LOG,
            project_id=project_id,
            payload={"message": "test log"}
        )
        
        # Critical: Must use projectId, not project_id
        assert "projectId" in envelope
        assert "project_id" not in envelope
        assert envelope["projectId"] == project_id
    
    def test_create_execution_update_envelope(self):
        """Test execution update envelope creation."""
        project_id = "test-project-789"
        execution_id = "exec-123"
        status = "running"
        progress = 75.0
        current_task = "processing data"
        totals = {"completed": 3, "total": 8}
        
        envelope = create_execution_update_envelope(
            project_id=project_id,
            execution_id=execution_id,
            status=status,
            progress=progress,
            current_task=current_task,
            totals=totals
        )
        
        # Validate envelope structure
        assert envelope["type"] == "execution-update"
        assert envelope["projectId"] == project_id
        assert envelope["payload"]["execution_id"] == execution_id
        assert envelope["payload"]["status"] == status
        assert envelope["payload"]["progress"] == progress
        assert envelope["payload"]["current_task"] == current_task
        assert envelope["payload"]["totals"] == totals
        
        # Validate timestamp
        assert envelope["ts"].endswith("Z")
    
    def test_create_execution_log_envelope(self):
        """Test execution log envelope creation."""
        project_id = "test-project-abc"
        execution_id = "exec-456"
        log_entry_type = "node_start"
        level = "INFO"
        message = "Test log message"
        
        envelope = create_execution_log_envelope(
            project_id=project_id,
            execution_id=execution_id,
            log_entry_type=log_entry_type,
            level=level,
            message=message
        )
        
        # Validate envelope structure
        assert envelope["type"] == "execution-log"
        assert envelope["projectId"] == project_id
        assert envelope["payload"]["execution_id"] == execution_id
        assert envelope["payload"]["log_entry_type"] == log_entry_type
        assert envelope["payload"]["level"] == level
        assert envelope["payload"]["message"] == message
        assert envelope["payload"]["timestamp"].endswith("Z")  # Auto-generated timestamp
        
        # Validate envelope timestamp
        assert envelope["ts"].endswith("Z")
    
    def test_create_error_envelope(self):
        """Test error envelope creation."""
        project_id = "test-project-def"
        error_code = "VALIDATION_ERROR"
        message = "Invalid input"
        details = "Field 'name' is required"
        
        envelope = create_error_envelope(
            project_id=project_id,
            error_code=error_code,
            message=message,
            details=details
        )
        
        # Validate envelope structure
        assert envelope["type"] == "error"
        assert envelope["projectId"] == project_id
        assert envelope["payload"]["error_code"] == error_code
        assert envelope["payload"]["message"] == message
        assert envelope["payload"]["details"] == details
        
        # Validate timestamp
        assert envelope["ts"].endswith("Z")
    
    def test_create_completion_envelope(self):
        """Test completion envelope creation."""
        project_id = "test-project-ghi"
        execution_id = "exec-789"
        status = "completed"
        final_result = "success"
        
        envelope = create_completion_envelope(
            project_id=project_id,
            execution_id=execution_id,
            status=status,
            final_result=final_result
        )
        
        # Validate envelope structure
        assert envelope["type"] == "completion"
        assert envelope["projectId"] == project_id
        assert envelope["payload"]["execution_id"] == execution_id
        assert envelope["payload"]["status"] == status
        assert envelope["payload"]["final_result"] == final_result
        
        # Validate timestamp
        assert envelope["ts"].endswith("Z")
    
    def test_envelope_json_serializable(self):
        """Test that envelopes are JSON serializable."""
        envelope = create_envelope(
            message_type=MessageType.EXECUTION_UPDATE,
            project_id="test-project",
            payload={"status": "running"}
        )
        
        # Should not raise exception
        json_str = json.dumps(envelope)
        
        # Should be able to parse back
        parsed = json.loads(json_str)
        assert parsed["type"] == "execution-update"
        assert parsed["projectId"] == "test-project"


class TestServiceIntegration:
    """Test that services use the standardized envelope utilities."""
    
    @patch('api.v1.endpoints.websocket.broadcast_to_project')
    @pytest.mark.asyncio
    async def test_execution_update_service_uses_standard_envelope(self, mock_broadcast):
        """Test ExecutionUpdateService uses standardized envelope."""
        mock_broadcast.return_value = None
        
        service = ExecutionUpdateService()
        project_id = "test-project-service"
        execution_id = "exec-service-123"
        task_context = {
            "status": "running",
            "progress": 60.0,
            "current_task": "analyzing code",
            "totals": {"completed": 2, "total": 5}
        }
        
        # Call the service method
        await service.send_execution_update(
            project_id=project_id,
            task_context=task_context,
            execution_id=execution_id
        )
        
        # Verify broadcast_to_project was called
        mock_broadcast.assert_called_once()
        
        # Get the message that was sent
        call_args = mock_broadcast.call_args
        sent_message = call_args[0][0]
        sent_project_id = call_args[0][1]
        
        # Validate project ID
        assert sent_project_id == project_id
        
        # Validate message uses standard envelope format
        assert sent_message["type"] == "execution-update"
        assert sent_message["projectId"] == project_id  # Must be projectId
        assert "project_id" not in sent_message  # Must not have project_id
        assert sent_message["payload"]["execution_id"] == execution_id
        assert sent_message["ts"].endswith("Z")
    
    @patch('api.v1.endpoints.websocket.broadcast_to_project')
    @pytest.mark.asyncio
    async def test_execution_log_service_uses_standard_envelope(self, mock_broadcast):
        """Test ExecutionLogService uses standardized envelope."""
        mock_broadcast.return_value = None
        
        service = ExecutionLogService()
        project_id = "test-project-log"
        execution_id = "exec-log-456"
        log_entry_type = LogEntryType.ERROR_LOG
        level = LogLevel.ERROR
        message = "Test error message"
        
        # Call the service method
        await service.send_execution_log(
            project_id=project_id,
            execution_id=execution_id,
            log_entry_type=log_entry_type,
            message=message,
            level=level
        )
        
        # Verify broadcast_to_project was called
        mock_broadcast.assert_called_once()
        
        # Get the message that was sent
        call_args = mock_broadcast.call_args
        sent_message = call_args[0][0]
        sent_project_id = call_args[0][1]
        
        # Validate project ID
        assert sent_project_id == project_id
        
        # Validate message uses standard envelope format
        assert sent_message["type"] == "execution-log"
        assert sent_message["projectId"] == project_id  # Must be projectId
        assert "project_id" not in sent_message  # Must not have project_id
        assert sent_message["payload"]["execution_id"] == execution_id
        assert sent_message["payload"]["log_entry_type"] == log_entry_type.value
        assert sent_message["payload"]["level"] == level.value
        assert sent_message["payload"]["message"] == message
        assert sent_message["ts"].endswith("Z")


class TestEnvelopeValidation:
    """Test envelope validation and error handling."""
    
    def test_envelope_with_empty_current_task(self):
        """Test envelope handles empty current_task gracefully."""
        envelope = create_execution_update_envelope(
            project_id="test-project",
            execution_id="exec-test",
            status="running",
            progress=50.0,
            current_task="",
            totals={"completed": 1, "total": 2}
        )
        
        # Should handle empty string gracefully
        assert envelope["payload"]["current_task"] == ""
    
    def test_envelope_with_empty_payload(self):
        """Test envelope with empty payload."""
        envelope = create_envelope(
            message_type=MessageType.ERROR,
            project_id="test-project",
            payload={}
        )
        
        assert envelope["type"] == "error"
        assert envelope["projectId"] == "test-project"
        assert envelope["payload"] == {}
    
    def test_timestamp_format_consistency(self):
        """Test that all envelope types use consistent timestamp format."""
        project_id = "test-project"
        execution_id = "exec-test"
        
        # Test different envelope types
        envelopes = [
            create_execution_update_envelope(
                project_id, execution_id, "running", 50.0, "task1", {"completed": 1, "total": 2}
            ),
            create_execution_log_envelope(
                project_id, execution_id, "info_log", "INFO", "test"
            ),
            create_error_envelope(project_id, "ERROR", "test error"),
            create_completion_envelope(project_id, execution_id, "completed", "success")
        ]
        
        for envelope in envelopes:
            # All should have timestamp ending with Z
            assert envelope["ts"].endswith("Z")
            
            # All should be valid ISO format
            datetime.fromisoformat(envelope["ts"].replace("Z", "+00:00"))
    
    def test_field_naming_consistency_across_types(self):
        """Test that all envelope types use consistent field naming."""
        project_id = "test-project"
        execution_id = "exec-test"
        
        # Test different envelope types
        envelopes = [
            create_execution_update_envelope(
                project_id, execution_id, "running", 50.0, "task1", {"completed": 1, "total": 2}
            ),
            create_execution_log_envelope(
                project_id, execution_id, "info_log", "INFO", "test"
            ),
            create_error_envelope(project_id, "ERROR", "test error"),
            create_completion_envelope(project_id, execution_id, "completed", "success")
        ]
        
        for envelope in envelopes:
            # All must use projectId, not project_id
            assert "projectId" in envelope
            assert "project_id" not in envelope
            assert envelope["projectId"] == project_id
            
            # All must have required fields
            assert "type" in envelope
            assert "ts" in envelope
            assert "payload" in envelope


class TestPerformanceRequirements:
    """Test that envelope creation meets performance requirements."""
    
    def test_envelope_creation_performance(self):
        """Test that envelope creation is fast (contributes to ≤500ms requirement)."""
        import time
        
        project_id = "test-project"
        payload = {"status": "running", "progress": 50}
        
        # Measure envelope creation time
        start_time = time.time()
        
        # Create multiple envelopes to test performance
        envelope = None
        for _ in range(1000):
            envelope = create_envelope(
                message_type=MessageType.EXECUTION_UPDATE,
                project_id=project_id,
                payload=payload
            )
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should be very fast (well under the 500ms WebSocket latency requirement)
        # 1000 envelope creations should take less than 100ms
        assert total_time < 0.1, f"Envelope creation too slow: {total_time}s for 1000 envelopes"
        
        # Validate last envelope is correct
        assert envelope is not None
        assert envelope["type"] == "execution-update"
        assert envelope["projectId"] == project_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])