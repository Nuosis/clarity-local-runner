"""
Branch 8.2 Structured Logging Validation Tests

This test suite validates the implementation of Branch 8.2 requirements:
- Task 8.2.1: Add correlationId, projectId, executionId fields to logs across API and Worker
- Task 8.2.2: Logs redact tokens/secrets across all components

Tests cover:
1. API endpoint structured logging with required fields
2. Secret redaction functionality across different data types
3. Performance requirements and error handling scenarios
4. LogStatus enum usage and field validation
"""

import json
import pytest
import time
from unittest.mock import MagicMock, patch
from io import StringIO
import logging

from api.endpoint import handle_event
from schemas.event_schema import EventRequest
from core.structured_logging import get_structured_logger, LogStatus, SecretRedactor


class TestAPIEndpointStructuredLogging:
    """Test structured logging implementation in API endpoint."""

    @pytest.fixture
    def log_capture(self):
        """Capture log output for testing."""
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.INFO)
        
        # Get the logger used by the API endpoint
        logger = logging.getLogger('api.endpoint')
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        yield log_capture
        
        # Cleanup
        logger.removeHandler(handler)

    @pytest.fixture
    def mock_event_data(self):
        """Mock event data for testing."""
        return {
            "id": "evt_test_123",
            "type": "DEVTEAM_AUTOMATION",
            "project_id": "test_project_456",
            "metadata": {
                "correlation_id": "api_test_correlation_789"
            },
            "task": {
                "id": "1.1.1",
                "title": "Test API structured logging"
            }
        }

    @patch('api.endpoint.celery_app.send_task')
    @patch('api.endpoint.GenericRepository')
    def test_api_structured_logging_success(self, mock_repo, mock_celery, log_capture, mock_event_data):
        """Test that API endpoint uses structured logging with required fields on success."""
        # Mock database operations
        mock_repo_instance = MagicMock()
        mock_event = MagicMock()
        mock_event.id = 123  # Use integer ID that will be converted to string
        mock_event.workflow_type = "DEVTEAM_AUTOMATION"
        mock_repo_instance.create.return_value = mock_event
        mock_repo.return_value = mock_repo_instance

        # Mock Celery task dispatch
        mock_task_id = "celery_task_456"
        mock_celery.return_value = mock_task_id

        # Create EventRequest
        event_request = EventRequest.model_validate(mock_event_data)

        # Mock database session
        with patch('api.endpoint.db_session') as mock_session:
            mock_session.return_value = MagicMock()

            # Call the endpoint
            response = handle_event(event_request, mock_session.return_value)

            # Verify response
            assert response.status_code == 202
            if isinstance(response.body, bytes):
                response_body = response.body.decode('utf-8')
            elif hasattr(response.body, 'tobytes'):
                response_body = response.body.tobytes().decode('utf-8')
            else:
                response_body = str(response.body)
            response_data = json.loads(response_body)
            assert response_data["status"] == "accepted"
            assert response_data["correlation_id"] == "api_test_correlation_789"

        # Verify structured logging
        log_output = log_capture.getvalue()
        log_lines = [line for line in log_output.strip().split('\n') if line]

        # Should have at least 2 log entries (persistence and task dispatch)
        assert len(log_lines) >= 2

        # Verify event persistence log entry
        persistence_log = json.loads(log_lines[0])
        assert persistence_log["message"] == "Event persisted successfully"
        assert persistence_log["correlationId"] == "api_test_correlation_789"
        assert persistence_log["projectId"] == "test_project_456"
        assert persistence_log["executionId"] == "123"  # Should match mock_event.id
        assert persistence_log["status"] == "completed"

        # Verify task dispatch log entry
        dispatch_log = json.loads(log_lines[1])
        assert dispatch_log["message"] == "Celery task dispatched successfully"
        assert dispatch_log["correlationId"] == "api_test_correlation_789"
        assert dispatch_log["projectId"] == "test_project_456"
        assert dispatch_log["executionId"] == "123"
        assert dispatch_log["taskId"] == "celery_task_456"
        assert dispatch_log["status"] == "completed"

    @patch('api.endpoint.celery_app.send_task')
    @patch('api.endpoint.GenericRepository')
    def test_api_structured_logging_celery_failure(self, mock_repo, mock_celery, log_capture, mock_event_data):
        """Test structured logging when Celery task dispatch fails."""
        # Mock database operations
        mock_repo_instance = MagicMock()
        mock_event = MagicMock()
        mock_event.id = 456  # Use integer ID
        mock_event.workflow_type = "DEVTEAM_AUTOMATION"
        mock_repo_instance.create.return_value = mock_event
        mock_repo.return_value = mock_repo_instance

        # Mock Celery task dispatch failure
        celery_error = Exception("Celery connection failed")
        mock_celery.side_effect = celery_error

        # Create EventRequest
        event_request = EventRequest.model_validate(mock_event_data)

        # Mock database session
        with patch('api.endpoint.db_session') as mock_session:
            mock_session.return_value = MagicMock()

            # Call the endpoint - should still return 202 (graceful degradation)
            response = handle_event(event_request, mock_session.return_value)

            # Verify response (graceful degradation)
            assert response.status_code == 202
            if isinstance(response.body, bytes):
                response_body = response.body.decode('utf-8')
            elif hasattr(response.body, 'tobytes'):
                response_body = response.body.tobytes().decode('utf-8')
            else:
                response_body = str(response.body)
            response_data = json.loads(response_body)
            assert response_data["status"] == "accepted"
            assert response_data["task_id"] is None

        # Verify structured logging includes error
        log_output = log_capture.getvalue()
        log_lines = [line for line in log_output.strip().split('\n') if line]

        # Should have persistence success and Celery failure logs
        assert len(log_lines) >= 2

        # Find Celery failure log
        celery_error_log = None
        for line in log_lines:
            log_entry = json.loads(line)
            if "Failed to dispatch Celery task" in log_entry.get("message", ""):
                celery_error_log = log_entry
                break

        assert celery_error_log is not None
        assert celery_error_log["correlationId"] == "api_test_correlation_789"
        assert celery_error_log["projectId"] == "test_project_456"
        assert celery_error_log["executionId"] == "456"
        assert celery_error_log["status"] == "failed"
        assert celery_error_log["error_type"] == "Exception"
        assert celery_error_log["error_message"] == "Celery connection failed"

    @patch('api.endpoint.celery_app.send_task')
    @patch('api.endpoint.GenericRepository')
    def test_api_structured_logging_general_error(self, mock_repo, mock_celery, log_capture, mock_event_data):
        """Test structured logging for general errors."""
        # Mock database operation failure
        db_error = Exception("Database connection failed")
        mock_repo.side_effect = db_error

        # Create EventRequest
        event_request = EventRequest.model_validate(mock_event_data)

        # Mock database session
        with patch('api.endpoint.db_session') as mock_session:
            mock_session.return_value = MagicMock()

            # Call the endpoint - should raise HTTPException
            with pytest.raises(Exception):
                handle_event(event_request, mock_session.return_value)

        # Verify error logging
        log_output = log_capture.getvalue()
        log_lines = [line for line in log_output.strip().split('\n') if line]

        assert len(log_lines) >= 1
        error_log = json.loads(log_lines[0])

        assert error_log["message"] == "Error processing event"
        assert error_log["correlationId"] == "api_test_correlation_789"
        assert error_log["projectId"] == "test_project_456"
        assert error_log["status"] == "failed"
        assert error_log["error_type"] == "Exception"
        assert error_log["error_message"] == "Database connection failed"

    @patch('api.endpoint.celery_app.send_task')
    @patch('api.endpoint.GenericRepository')
    def test_correlation_id_fallback(self, mock_repo, mock_celery, log_capture):
        """Test correlation ID fallback when not provided in metadata."""
        # Event data without correlation_id
        event_data_no_correlation = {
            "id": "evt_no_correlation_123",
            "type": "DEVTEAM_AUTOMATION",
            "project_id": "test_project_no_corr",
            "metadata": {},  # No correlation_id
            "task": {
                "id": "1.1.1",
                "title": "Test correlation ID fallback"
            }
        }

        # Mock database operations
        mock_repo_instance = MagicMock()
        mock_event = MagicMock()
        mock_event.id = 789
        mock_event.workflow_type = "DEVTEAM_AUTOMATION"
        mock_repo_instance.create.return_value = mock_event
        mock_repo.return_value = mock_repo_instance

        # Mock Celery task dispatch
        mock_task_id = "fallback_task_123"
        mock_celery.return_value = mock_task_id

        # Create EventRequest
        event_request = EventRequest.model_validate(event_data_no_correlation)

        # Mock database session
        with patch('api.endpoint.db_session') as mock_session:
            mock_session.return_value = MagicMock()

            # Call the endpoint
            response = handle_event(event_request, mock_session.return_value)

            # Verify response
            assert response.status_code == 202

        # Verify structured logging uses task_id as correlation_id
        log_output = log_capture.getvalue()
        log_lines = [line for line in log_output.strip().split('\n') if line]

        # Find task dispatch log
        dispatch_log = None
        for line in log_lines:
            log_entry = json.loads(line)
            if "Celery task dispatched successfully" in log_entry.get("message", ""):
                dispatch_log = log_entry
                break

        assert dispatch_log is not None
        assert dispatch_log["correlationId"] == "fallback_task_123"  # Should use task_id as fallback

    def test_log_status_enum_usage(self, log_capture):
        """Test that LogStatus enum values are used correctly."""
        logger = get_structured_logger("test_log_status")

        # Test all LogStatus enum values
        test_cases = [
            (LogStatus.STARTED, "started"),
            (LogStatus.IN_PROGRESS, "in_progress"),
            (LogStatus.COMPLETED, "completed"),
            (LogStatus.FAILED, "failed"),
            (LogStatus.RETRYING, "retrying")
        ]

        for status_enum, expected_value in test_cases:
            logger.info(
                f"Testing {status_enum.name}",
                correlation_id="status_test_123",
                project_id="status_project",
                execution_id="status_exec_456",
                status=status_enum
            )

        log_output = log_capture.getvalue()
        log_lines = [line for line in log_output.strip().split('\n') if line]

        assert len(log_lines) == len(test_cases)

        for i, (status_enum, expected_value) in enumerate(test_cases):
            log_entry = json.loads(log_lines[i])
            assert log_entry["status"] == expected_value
            assert log_entry["correlationId"] == "status_test_123"
            assert log_entry["projectId"] == "status_project"
            assert log_entry["executionId"] == "status_exec_456"


class TestSecretRedactionInAPI:
    """Test secret redaction functionality in API logging."""

    @pytest.fixture
    def log_capture(self):
        """Capture log output for testing."""
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.INFO)
        
        # Get a test logger
        logger = logging.getLogger('test_secret_redaction')
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        yield log_capture
        
        # Cleanup
        logger.removeHandler(handler)

    def test_jwt_token_redaction(self, log_capture):
        """Test that JWT tokens are redacted in API logs."""
        logger = get_structured_logger("test_api_secret_redaction")

        # Sample JWT token
        jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"

        logger.info(
            "Processing authentication request",
            correlation_id="jwt_test_123",
            project_id="jwt_project",
            execution_id="exec_jwt_456",
            status=LogStatus.COMPLETED,
            authorization_header=f"Bearer {jwt_token}",
            jwt_token=jwt_token
        )

        log_output = log_capture.getvalue()
        log_entry = json.loads(log_output.strip())

        # Verify JWT token is redacted
        assert log_entry["jwt_token"] == "[JWT_TOKEN_REDACTED]"
        assert "[JWT_TOKEN_REDACTED]" in log_entry["authorization_header"]

    def test_bearer_token_redaction(self, log_capture):
        """Test that Bearer tokens are redacted in API logs."""
        logger = get_structured_logger("test_api_bearer_redaction")

        logger.info(
            "API request with Bearer token",
            correlation_id="bearer_test_123",
            project_id="bearer_project",
            execution_id="exec_bearer_456",
            status=LogStatus.COMPLETED,
            auth_header="Bearer sk-1234567890abcdef",
            request_headers={"Authorization": "Bearer ghp_abcdefghijklmnop"}
        )

        log_output = log_capture.getvalue()
        log_entry = json.loads(log_output.strip())

        # Verify Bearer tokens are redacted
        assert log_entry["auth_header"] == "Bearer [REDACTED]"
        assert log_entry["request_headers"]["Authorization"] == "[REDACTED]"

    def test_sensitive_field_redaction(self, log_capture):
        """Test that sensitive fields are redacted in API logs."""
        logger = get_structured_logger("test_api_sensitive_redaction")

        sensitive_data = {
            "api_key": "sk-1234567890abcdef",
            "password": "super_secret_password",
            "token": "access_token_456",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQ...",
            "user_id": "user_123",  # Should NOT be redacted
            "event_type": "API_REQUEST"  # Should NOT be redacted
        }

        logger.info(
            "Processing request with sensitive data",
            correlation_id="sensitive_test_123",
            project_id="sensitive_project",
            execution_id="exec_sensitive_456",
            status=LogStatus.COMPLETED,
            **sensitive_data
        )

        log_output = log_capture.getvalue()
        log_entry = json.loads(log_output.strip())

        # Verify sensitive fields are redacted
        assert log_entry["api_key"] == "[REDACTED]"
        assert log_entry["password"] == "[REDACTED]"
        assert log_entry["token"] == "[REDACTED]"
        assert log_entry["private_key"] == "[REDACTED]"

        # Verify non-sensitive fields are NOT redacted
        assert log_entry["user_id"] == "user_123"
        assert log_entry["event_type"] == "API_REQUEST"

    def test_database_url_redaction(self, log_capture):
        """Test that database URLs with credentials are redacted."""
        logger = get_structured_logger("test_db_url_redaction")

        logger.error(
            "Database connection failed",
            correlation_id="db_test_123",
            project_id="db_project",
            execution_id="exec_db_456",
            status=LogStatus.FAILED,
            error_message="Connection failed to postgresql://admin:secret123@localhost:5432/mydb"
        )

        log_output = log_capture.getvalue()
        log_entry = json.loads(log_output.strip())

        # Verify database URL credentials are redacted
        assert "postgresql://[USER]:[PASSWORD]@localhost:5432/mydb" in log_entry["error_message"]
        assert "admin" not in log_entry["error_message"]
        assert "secret123" not in log_entry["error_message"]

    @patch('api.endpoint.celery_app.send_task')
    @patch('api.endpoint.GenericRepository')
    def test_api_error_with_secret_redaction(self, mock_repo, mock_celery, log_capture):
        """Test that secrets in error scenarios are properly redacted."""
        # Mock event data with sensitive information
        event_data_with_secrets = {
            "id": "evt_secret_error_123",
            "type": "DEVTEAM_AUTOMATION",
            "project_id": "secret_project_456",
            "metadata": {
                "correlation_id": "secret_error_correlation_789"
            },
            "task": {
                "id": "1.1.1",
                "title": "Task with secrets",
                "config": {
                    "database_url": "postgresql://user:pass@localhost/db"
                }
            }
        }

        # Mock database operation failure
        db_error = Exception("Database error with credentials: postgresql://admin:secret@db/app")
        mock_repo.side_effect = db_error

        # Create EventRequest
        event_request = EventRequest.model_validate(event_data_with_secrets)

        # Mock database session
        with patch('api.endpoint.db_session') as mock_session:
            mock_session.return_value = MagicMock()

            # Call the endpoint - should raise HTTPException
            with pytest.raises(Exception):
                handle_event(event_request, mock_session.return_value)

        # Verify error logging with secret redaction
        log_output = log_capture.getvalue()
        log_lines = [line for line in log_output.strip().split('\n') if line]

        error_log = json.loads(log_lines[0])

        # Verify database URL in error message is redacted
        assert "postgresql://[USER]:[PASSWORD]@db/app" in error_log["error_message"]
        assert "admin" not in error_log["error_message"]
        assert "secret" not in error_log["error_message"]

        # Verify event_data structure is present (Pydantic transforms the data)
        assert "event_data" in error_log
        assert error_log["event_data"]["project_id"] == "secret_project_456"


class TestAPIPerformanceRequirements:
    """Test performance requirements for API structured logging."""

    @pytest.fixture
    def log_capture(self):
        """Capture log output for testing."""
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.INFO)
        
        logger = logging.getLogger('test_performance')
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        yield log_capture
        
        logger.removeHandler(handler)

    def test_logging_performance_impact(self, log_capture):
        """Test that structured logging has minimal performance impact."""
        logger = get_structured_logger("test_performance_logging")

        # Measure time for multiple log operations
        start_time = time.time()
        
        for i in range(100):
            logger.info(
                f"Performance test log entry {i}",
                correlation_id=f"perf_test_{i}",
                project_id="performance_project",
                execution_id=f"exec_{i}",
                status=LogStatus.COMPLETED,
                iteration=i,
                test_data={"key": f"value_{i}"}
            )
        
        end_time = time.time()
        total_duration = (end_time - start_time) * 1000  # Convert to milliseconds

        # Verify performance requirement: 100 log entries should complete in < 100ms
        assert total_duration < 100, f"Logging took {total_duration}ms, expected < 100ms"

        # Verify all log entries were created
        log_output = log_capture.getvalue()
        log_lines = [line for line in log_output.strip().split('\n') if line]
        assert len(log_lines) == 100

    def test_secret_redaction_performance(self, log_capture):
        """Test that secret redaction doesn't significantly impact performance."""
        logger = get_structured_logger("test_redaction_performance")

        # Test data with various secrets
        test_data_with_secrets = {
            "api_key": "sk-1234567890abcdef",
            "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
            "database_url": "postgresql://user:password@localhost:5432/db",
            "bearer_token": "Bearer ghp_abcdefghijklmnop",
            "normal_field": "this should not be redacted"
        }

        # Measure time for secret redaction
        start_time = time.time()
        
        for i in range(50):
            logger.info(
                f"Secret redaction test {i}",
                correlation_id=f"redaction_test_{i}",
                project_id="redaction_project",
                execution_id=f"exec_redaction_{i}",
                status=LogStatus.COMPLETED,
                **test_data_with_secrets
            )
        
        end_time = time.time()
        total_duration = (end_time - start_time) * 1000

        # Verify performance: 50 log entries with secret redaction should complete in < 100ms
        assert total_duration < 100, f"Secret redaction took {total_duration}ms, expected < 100ms"

        # Verify secrets were redacted
        log_output = log_capture.getvalue()
        log_lines = [line for line in log_output.strip().split('\n') if line]
        
        # Check first log entry for proper redaction
        first_log = json.loads(log_lines[0])
        assert first_log["api_key"] == "[REDACTED]"
        assert first_log["jwt_token"] == "[JWT_TOKEN_REDACTED]"
        assert "postgresql://[USER]:[PASSWORD]@localhost:5432/db" in first_log["database_url"]
        assert first_log["bearer_token"] == "Bearer [REDACTED]"
        assert first_log["normal_field"] == "this should not be redacted"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])