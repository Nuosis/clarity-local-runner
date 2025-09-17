"""
Unit tests for DevTeam Automation Pause Endpoint - Task 5.4.1

This module provides comprehensive unit tests for the POST /api/devteam/automation/pause/{projectId}
endpoint, validating state transition logic (running→paused), error handling, and performance requirements.

Test Coverage:
- Valid pause operations (running→paused)
- Invalid state transitions (409 Conflict)
- Project not found scenarios (404 Not Found)
- Input validation (422 Validation Error)
- Repository errors (500 Internal Server Error)
- Performance requirements (≤200ms)
- Structured logging validation
- Response format compliance
"""

import asyncio
import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException

from api.v1.endpoints.devteam_automation import pause_devteam_automation
from schemas.devteam_automation_schema import (
    DevTeamAutomationPauseResponse,
    DevTeamPauseSuccessResponse
)
from schemas.status_projection_schema import (
    StatusProjection,
    ExecutionStatus,
    TaskTotals
)
from core.exceptions import RepositoryError


class TestDevTeamPauseEndpoint:
    """Unit tests for DevTeam automation pause endpoint."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.test_project_id = "customer-123/project-abc"
        self.test_execution_id = "exec_12345678-1234-1234-1234-123456789012"
        self.mock_session = Mock()
        
        # Create mock status projection for running state
        self.mock_running_projection = StatusProjection(
            execution_id=self.test_execution_id,
            project_id=self.test_project_id,
            status=ExecutionStatus.RUNNING,
            progress=45.2,
            current_task="1.1.1",
            totals=TaskTotals(completed=3, total=8),
            customer_id="customer-123",
            branch="task/1-1-1-add-devteam-enabled-flag",
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Create mock status projection for completed state
        self.mock_completed_projection = StatusProjection(
            execution_id=self.test_execution_id,
            project_id=self.test_project_id,
            status=ExecutionStatus.COMPLETED,
            progress=100.0,
            current_task="1.1.1",
            totals=TaskTotals(completed=8, total=8),
            customer_id="customer-123",
            branch="task/1-1-1-add-devteam-enabled-flag",
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    @pytest.mark.asyncio
    async def test_pause_automation_success_running_to_paused(self, mock_get_service):
        """Test successful pause operation from running to paused state."""
        # Arrange
        mock_service = Mock()
        mock_service.get_status_by_project_id.return_value = self.mock_running_projection
        mock_get_service.return_value = mock_service
        
        start_time = time.time()
        
        # Act
        result = await pause_devteam_automation(
            project_id=self.test_project_id,
            session=self.mock_session
        )
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Assert
        assert result.success is True
        assert result.message == "DevTeam automation paused successfully"
        
        # Validate response data
        assert result.data is not None
        assert result.data.project_id == self.test_project_id
        assert result.data.execution_id == self.test_execution_id
        assert result.data.previous_status == "running"
        assert result.data.current_status == "paused"
        assert result.data.paused_at is not None
        
        # Validate performance requirement
        assert duration_ms <= 200, f"Response time {duration_ms}ms exceeds 200ms requirement"
        
        # Verify service calls
        mock_get_service.assert_called_once()
        mock_service.get_status_by_project_id.assert_called_once_with(
            project_id=self.test_project_id
        )
    
    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    @pytest.mark.asyncio
    async def test_pause_automation_project_not_found(self, mock_get_service):
        """Test pause operation when project is not found (404)."""
        # Arrange
        mock_service = Mock()
        mock_service.get_status_by_project_id.return_value = None
        mock_get_service.return_value = mock_service
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await pause_devteam_automation(
                project_id=self.test_project_id,
                session=self.mock_session
            )
        
        # Validate 404 response
        assert exc_info.value.status_code == 404
        detail = exc_info.value.detail
        assert detail["success"] is False
        assert "No automation status found for project" in detail["data"]["message"]
        assert detail["data"]["project_id"] == self.test_project_id
    
    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    @pytest.mark.asyncio
    async def test_pause_automation_invalid_state_transition_completed(self, mock_get_service):
        """Test pause operation with invalid state transition from completed (409)."""
        # Arrange
        mock_service = Mock()
        mock_service.get_status_by_project_id.return_value = self.mock_completed_projection
        mock_get_service.return_value = mock_service
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await pause_devteam_automation(
                project_id=self.test_project_id,
                session=self.mock_session
            )
        
        # Validate 409 response
        assert exc_info.value.status_code == 409
        detail = exc_info.value.detail
        assert detail["success"] is False
        assert "Invalid state transition" in detail["data"]["message"]
        assert detail["data"]["current_status"] == "completed"
        assert detail["data"]["requested_transition"] == "completed→paused"
        assert "error" in detail["data"]["valid_transitions"]
    
    @pytest.mark.asyncio
    async def test_pause_automation_invalid_project_id_empty(self):
        """Test pause operation with empty project ID (422)."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await pause_devteam_automation(
                project_id="",
                session=self.mock_session
            )
        
        # Validate 422 response
        assert exc_info.value.status_code == 422
        detail = exc_info.value.detail
        assert detail["success"] is False
        assert detail["error_code"] == "VALIDATION_ERROR"
        assert "Project ID cannot be empty" in detail["errors"][0]["message"]
    
    @pytest.mark.asyncio
    async def test_pause_automation_invalid_project_id_format(self):
        """Test pause operation with invalid project ID format (422)."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await pause_devteam_automation(
                project_id="invalid@project#id",
                session=self.mock_session
            )
        
        # Validate 422 response
        assert exc_info.value.status_code == 422
        detail = exc_info.value.detail
        assert detail["success"] is False
        assert detail["error_code"] == "VALIDATION_ERROR"
        assert "must contain only alphanumeric characters" in detail["errors"][0]["message"]
    
    @pytest.mark.asyncio
    async def test_pause_automation_invalid_project_id_malformed_slash(self):
        """Test pause operation with malformed project ID with slash (422)."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await pause_devteam_automation(
                project_id="customer-123/",
                session=self.mock_session
            )
        
        # Validate 422 response
        assert exc_info.value.status_code == 422
        detail = exc_info.value.detail
        assert detail["success"] is False
        assert detail["error_code"] == "VALIDATION_ERROR"
        assert "must be in format 'customer-id/project-id'" in detail["errors"][0]["message"]
    
    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    @pytest.mark.asyncio
    async def test_pause_automation_repository_error(self, mock_get_service):
        """Test pause operation with repository error (500)."""
        # Arrange
        mock_service = Mock()
        mock_service.get_status_by_project_id.side_effect = RepositoryError("Database connection failed")
        mock_get_service.return_value = mock_service
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await pause_devteam_automation(
                project_id=self.test_project_id,
                session=self.mock_session
            )
        
        # Validate 500 response
        assert exc_info.value.status_code == 500
        detail = exc_info.value.detail
        assert detail["success"] is False
        assert detail["error_code"] == "REPOSITORY_ERROR"
        assert "Database error occurred" in detail["message"]
    
    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    @pytest.mark.asyncio
    async def test_pause_automation_unexpected_error(self, mock_get_service):
        """Test pause operation with unexpected error (500)."""
        # Arrange
        mock_get_service.side_effect = Exception("Unexpected error")
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await pause_devteam_automation(
                project_id=self.test_project_id,
                session=self.mock_session
            )
        
        # Validate 500 response
        assert exc_info.value.status_code == 500
        detail = exc_info.value.detail
        assert detail["success"] is False
        assert detail["error_code"] == "INTERNAL_ERROR"
        assert "Internal server error occurred" in detail["message"]
    
    @pytest.mark.parametrize("invalid_status,expected_transitions", [
        (ExecutionStatus.IDLE, ["initializing", "error"]),
        (ExecutionStatus.INITIALIZING, ["running", "error"]),
        (ExecutionStatus.PAUSED, ["running", "error"]),
        (ExecutionStatus.ERROR, []),
    ])
    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    @pytest.mark.asyncio
    async def test_pause_automation_invalid_state_transitions(self, mock_get_service, invalid_status, expected_transitions):
        """Test pause operation with various invalid state transitions."""
        # Arrange
        mock_projection = StatusProjection(
            execution_id=self.test_execution_id,
            project_id=self.test_project_id,
            status=invalid_status,
            progress=25.0,
            current_task="1.1.1" if invalid_status != ExecutionStatus.IDLE else None,
            totals=TaskTotals(completed=2, total=8),
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        mock_service = Mock()
        mock_service.get_status_by_project_id.return_value = mock_projection
        mock_get_service.return_value = mock_service
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await pause_devteam_automation(
                project_id=self.test_project_id,
                session=self.mock_session
            )
        
        # Validate 409 response
        assert exc_info.value.status_code == 409
        detail = exc_info.value.detail
        assert detail["success"] is False
        assert detail["data"]["current_status"] == invalid_status.value
        assert detail["data"]["requested_transition"] == f"{invalid_status.value}→paused"
        assert detail["data"]["valid_transitions"] == expected_transitions
    
    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    @pytest.mark.asyncio
    async def test_pause_automation_performance_requirement(self, mock_get_service):
        """Test that pause operation meets performance requirement (≤200ms)."""
        # Arrange
        mock_service = Mock()
        mock_service.get_status_by_project_id.return_value = self.mock_running_projection
        mock_get_service.return_value = mock_service
        
        # Act - Measure performance
        start_time = time.time()
        result = await pause_devteam_automation(
            project_id=self.test_project_id,
            session=self.mock_session
        )
        duration_ms = (time.time() - start_time) * 1000
        
        # Assert
        assert result.success is True
        assert duration_ms <= 200, f"Response time {duration_ms}ms exceeds 200ms requirement"
    
    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    @pytest.mark.asyncio
    async def test_pause_automation_response_format_compliance(self, mock_get_service):
        """Test that pause operation returns compliant response format."""
        # Arrange
        mock_service = Mock()
        mock_service.get_status_by_project_id.return_value = self.mock_running_projection
        mock_get_service.return_value = mock_service
        
        # Act
        result = await pause_devteam_automation(
            project_id=self.test_project_id,
            session=self.mock_session
        )
        
        # Assert response structure
        assert hasattr(result, 'success')
        assert hasattr(result, 'data')
        assert hasattr(result, 'message')
        
        # Assert data structure
        assert hasattr(result.data, 'project_id')
        assert hasattr(result.data, 'execution_id')
        assert hasattr(result.data, 'previous_status')
        assert hasattr(result.data, 'current_status')
        assert hasattr(result.data, 'paused_at')
        
        # Validate data types
        assert result.data is not None
        assert isinstance(result.data.project_id, str)
        assert isinstance(result.data.execution_id, str)
        assert isinstance(result.data.previous_status, str)
        assert isinstance(result.data.current_status, str)
        assert isinstance(result.data.paused_at, str)
        
        # Validate ISO timestamp format
        datetime.fromisoformat(result.data.paused_at.replace('Z', '+00:00'))
    
    @patch('api.v1.endpoints.devteam_automation.logger')
    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    @pytest.mark.asyncio
    async def test_pause_automation_structured_logging(self, mock_get_service, mock_logger):
        """Test that pause operation includes proper structured logging."""
        # Arrange
        mock_service = Mock()
        mock_service.get_status_by_project_id.return_value = self.mock_running_projection
        mock_get_service.return_value = mock_service
        
        # Act
        await pause_devteam_automation(
            project_id=self.test_project_id,
            session=self.mock_session
        )
        
        # Assert logging calls
        assert mock_logger.info.call_count >= 2  # Start and success logs
        
        # Verify start log
        start_call = mock_logger.info.call_args_list[0]
        start_extra = start_call[1]['extra']
        assert 'correlation_id' in start_extra
        assert start_extra['project_id'] == self.test_project_id
        assert start_extra['operation'] == 'devteam_automation_pause'
        
        # Verify success log
        success_call = mock_logger.info.call_args_list[-1]
        success_extra = success_call[1]['extra']
        assert 'correlation_id' in success_extra
        assert success_extra['project_id'] == self.test_project_id
        assert success_extra['execution_id'] == self.test_execution_id
        assert success_extra['previous_status'] == 'running'
        assert success_extra['current_status'] == 'paused'
        assert success_extra['response_status'] == '200_ok'
        assert 'duration_ms' in success_extra
        assert 'performance_target_met' in success_extra
    
    @patch('api.v1.endpoints.devteam_automation.logger')
    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    @pytest.mark.asyncio
    async def test_pause_automation_error_logging(self, mock_get_service, mock_logger):
        """Test that pause operation includes proper error logging."""
        # Arrange
        mock_service = Mock()
        mock_service.get_status_by_project_id.return_value = self.mock_completed_projection
        mock_get_service.return_value = mock_service
        
        # Act & Assert
        with pytest.raises(HTTPException):
            await pause_devteam_automation(
                project_id=self.test_project_id,
                session=self.mock_session
            )
        
        # Verify warning log for invalid state transition
        assert mock_logger.warning.call_count >= 1
        warning_call = mock_logger.warning.call_args_list[0]
        warning_extra = warning_call[1]['extra']
        assert 'correlation_id' in warning_extra
        assert warning_extra['project_id'] == self.test_project_id
        assert warning_extra['current_status'] == 'completed'
        assert warning_extra['requested_transition'] == 'completed→paused'
        assert warning_extra['response_status'] == '409_conflict'
        assert 'duration_ms' in warning_extra


class TestDevTeamPauseEndpointIntegration:
    """Integration tests for DevTeam automation pause endpoint."""
    
    def setup_method(self):
        """Set up integration test fixtures."""
        self.test_project_id = "customer-integration/project-test"
        self.test_execution_id = "exec_integration_test"
    
    @pytest.mark.asyncio
    async def test_pause_automation_end_to_end_flow(self):
        """Test complete pause automation flow with mocked dependencies."""
        # This test would require actual database setup and is more suitable
        # for integration test suite. For now, we focus on unit tests.
        pass


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])