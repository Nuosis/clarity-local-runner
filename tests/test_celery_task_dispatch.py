"""
Test module for Celery task dispatch functionality.

This module tests the integration between the POST /events endpoint and Celery worker
task dispatch, ensuring correlationId is properly passed and handled.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from database.event import Event
from schemas.event_schema import EventRequest, EventType
from worker.tasks import process_incoming_event


class TestCeleryTaskDispatch:
    """Test cases for Celery task dispatch with correlationId."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def sample_event_data(self):
        """Sample event data for testing."""
        return {
            "id": "test_event_123",
            "type": "PLACEHOLDER",
            "project_id": "test-project/test-repo",
            "data": {
                "test_field": "test_value"
            },
            "metadata": {
                "correlation_id": "test_correlation_123",
                "source": "test_suite",
                "user_id": "test_user"
            }
        }

    @patch('app.api.endpoint.celery_app.send_task')
    @patch('app.api.endpoint.GenericRepository')
    def test_celery_task_dispatch_with_correlation_id(self, mock_repo, mock_send_task, client, sample_event_data):
        """Test that Celery task is dispatched with correlationId in headers."""
        # Mock database operations
        mock_event = Mock()
        mock_event.id = "event_uuid_123"
        mock_event.workflow_type = "PLACEHOLDER"
        
        mock_repo_instance = Mock()
        mock_repo_instance.create.return_value = mock_event
        mock_repo.return_value = mock_repo_instance
        
        # Mock Celery task dispatch
        mock_task_id = "task_uuid_456"
        mock_send_task.return_value = mock_task_id
        
        # Make request
        response = client.post("/process/events/", json=sample_event_data)
        
        # Verify response
        assert response.status_code == 202
        response_data = response.json()
        assert response_data["status"] == "accepted"
        assert response_data["event_id"] == str(mock_event.id)
        assert response_data["task_id"] == str(mock_task_id)
        assert response_data["correlation_id"] == "test_correlation_123"
        
        # Verify Celery task was dispatched with correct parameters
        mock_send_task.assert_called_once_with(
            "process_incoming_event",
            args=[str(mock_event.id)],
            headers={
                "correlation_id": "test_correlation_123",
                "event_id": str(mock_event.id),
                "project_id": "test-project/test-repo",
                "event_type": "PLACEHOLDER"
            }
        )

    @patch('app.api.endpoint.celery_app.send_task')
    @patch('app.api.endpoint.GenericRepository')
    def test_celery_task_dispatch_without_correlation_id(self, mock_repo, mock_send_task, client):
        """Test that task_id is used as correlationId when not provided."""
        # Sample data without correlation_id
        event_data = {
            "id": "test_event_456",
            "type": "PLACEHOLDER",
            "data": {"test": "value"}
        }
        
        # Mock database operations
        mock_event = Mock()
        mock_event.id = "event_uuid_456"
        mock_event.workflow_type = "PLACEHOLDER"
        
        mock_repo_instance = Mock()
        mock_repo_instance.create.return_value = mock_event
        mock_repo.return_value = mock_repo_instance
        
        # Mock Celery task dispatch
        mock_task_id = "task_uuid_789"
        mock_send_task.return_value = mock_task_id
        
        # Make request
        response = client.post("/process/events/", json=event_data)
        
        # Verify response
        assert response.status_code == 202
        response_data = response.json()
        assert response_data["correlation_id"] == str(mock_task_id)
        
        # Verify Celery task was dispatched with event_id as correlation_id initially
        mock_send_task.assert_called_once_with(
            "process_incoming_event",
            args=[str(mock_event.id)],
            headers={
                "correlation_id": str(mock_event.id),
                "event_id": str(mock_event.id),
                "project_id": None,
                "event_type": "PLACEHOLDER"
            }
        )

    @patch('app.api.endpoint.celery_app.send_task')
    @patch('app.api.endpoint.GenericRepository')
    def test_celery_task_dispatch_failure_graceful_degradation(self, mock_repo, mock_send_task, client, sample_event_data):
        """Test graceful degradation when Celery task dispatch fails."""
        # Mock database operations
        mock_event = Mock()
        mock_event.id = "event_uuid_789"
        mock_event.workflow_type = "PLACEHOLDER"
        
        mock_repo_instance = Mock()
        mock_repo_instance.create.return_value = mock_event
        mock_repo.return_value = mock_repo_instance
        
        # Mock Celery task dispatch failure
        mock_send_task.side_effect = Exception("Redis connection failed")
        
        # Make request
        response = client.post("/process/events/", json=sample_event_data)
        
        # Verify response - should still return 202 (graceful degradation)
        assert response.status_code == 202
        response_data = response.json()
        assert response_data["status"] == "accepted"
        assert response_data["event_id"] == str(mock_event.id)
        assert response_data["task_id"] is None  # Task dispatch failed
        assert response_data["correlation_id"] == "test_correlation_123"
        
        # Verify event was still persisted
        mock_repo_instance.create.assert_called_once()

    @patch('app.worker.tasks.contextmanager')
    @patch('app.worker.tasks.GenericRepository')
    @patch('app.worker.tasks.WorkflowRegistry')
    def test_worker_task_processes_correlation_id(self, mock_registry, mock_repo, mock_contextmanager):
        """Test that worker task properly processes correlationId from headers."""
        # Mock task request with headers
        mock_task_request = Mock()
        mock_task_request.id = "task_123"
        mock_task_request.headers = {
            "correlation_id": "test_correlation_456",
            "event_id": "event_123",
            "project_id": "test-project",
            "event_type": "PLACEHOLDER"
        }
        
        # Mock database session and event
        mock_session = Mock()
        mock_contextmanager.return_value.__enter__.return_value = mock_session
        
        mock_event = Mock()
        mock_event.id = "event_123"
        mock_event.workflow_type = "PLACEHOLDER"
        mock_event.data = {"test": "data"}
        
        mock_repo_instance = Mock()
        mock_repo_instance.get.return_value = mock_event
        mock_repo.return_value = mock_repo_instance
        
        # Mock workflow execution
        mock_workflow_class = Mock()
        mock_workflow = Mock()
        mock_workflow_class.return_value = mock_workflow
        
        mock_result = Mock()
        mock_result.model_dump.return_value = {"result": "success"}
        mock_workflow.run.return_value = mock_result
        
        mock_registry.__getitem__.return_value.value = mock_workflow_class
        
        # Create task instance with mocked request
        task_instance = Mock()
        task_instance.request = mock_task_request
        
        # Execute task
        process_incoming_event(task_instance, "event_123")
        
        # Verify workflow was executed
        mock_workflow.run.assert_called_once_with({"test": "data"})
        
        # Verify task_context was updated with correlationId
        expected_task_context = {
            "result": "success",
            "metadata": {
                "correlationId": "test_correlation_456",
                "taskId": "task_123"
            }
        }
        assert mock_event.task_context == expected_task_context
        
        # Verify event was updated in database
        mock_repo_instance.update.assert_called_once_with(obj=mock_event)

    def test_event_request_schema_supports_correlation_id(self):
        """Test that EventRequest schema properly handles correlationId in metadata."""
        event_data = {
            "id": "test_event",
            "type": "PLACEHOLDER",
            "metadata": {
                "correlation_id": "test_correlation_789",
                "source": "test",
                "user_id": "user123"
            }
        }
        
        # Validate schema
        event_request = EventRequest(**event_data)
        
        assert event_request.metadata.correlation_id == "test_correlation_789"
        assert event_request.metadata.source == "test"
        assert event_request.metadata.user_id == "user123"

    @patch('app.api.endpoint.logger')
    @patch('app.api.endpoint.celery_app.send_task')
    @patch('app.api.endpoint.GenericRepository')
    def test_structured_logging_with_correlation_id(self, mock_repo, mock_send_task, mock_logger, client, sample_event_data):
        """Test that structured logging includes correlationId."""
        # Mock database operations
        mock_event = Mock()
        mock_event.id = "event_uuid_logging"
        mock_event.workflow_type = "PLACEHOLDER"
        
        mock_repo_instance = Mock()
        mock_repo_instance.create.return_value = mock_event
        mock_repo.return_value = mock_repo_instance
        
        # Mock Celery task dispatch
        mock_task_id = "task_uuid_logging"
        mock_send_task.return_value = mock_task_id
        
        # Make request
        response = client.post("/process/events/", json=sample_event_data)
        
        # Verify structured logging was called with correlationId
        assert mock_logger.info.call_count >= 2  # At least persistence and dispatch logs
        
        # Check that correlationId appears in log calls
        log_calls = mock_logger.info.call_args_list
        correlation_id_found = False
        
        for call in log_calls:
            if len(call) > 1 and 'extra' in call[1]:
                extra_data = call[1]['extra']
                if 'correlation_id' in extra_data and extra_data['correlation_id'] == "test_correlation_123":
                    correlation_id_found = True
                    break
        
        assert correlation_id_found, "correlationId not found in structured logging"


if __name__ == "__main__":
    pytest.main([__file__])