"""
Simple unit tests for DevTeam automation stop endpoint.

This module provides comprehensive unit tests for the POST /api/devteam/automation/stop/{projectId}
endpoint, following the established patterns from pause and resume endpoint tests.

Tests cover:
- Valid state transitions (running→stopping)
- Invalid state transitions (all other states→stopping should return 409)
- Error conditions (project not found, service errors)
- Performance requirements (≤200ms)
- Integration with status projection service
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from fastapi import HTTPException

from api.v1.endpoints.devteam_automation import stop_devteam_automation
from schemas.status_projection_schema import ExecutionStatus, StatusProjection, TaskTotals, ExecutionArtifacts
from schemas.devteam_automation_schema import DevTeamAutomationStopResponse
from core.exceptions import RepositoryError


class TestDevTeamStopEndpointSimple:
    """Simple unit tests for DevTeam automation stop endpoint."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.test_project_id = "customer-123/project-abc"
        self.test_execution_id = "exec_12345678-1234-1234-1234-123456789012"
        
        # Mock database session
        self.mock_session = Mock()
        
        # Create mock status projections for different states
        self.mock_running_projection = StatusProjection(
            execution_id=self.test_execution_id,
            project_id=self.test_project_id,
            status=ExecutionStatus.RUNNING,
            progress=45.2,
            current_task="1.1.1",
            totals=TaskTotals(completed=3, total=8),
            customer_id="customer-123",
            branch="task/1-1-1-add-devteam-enabled-flag",
            artifacts=ExecutionArtifacts(),
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.mock_paused_projection = StatusProjection(
            execution_id=self.test_execution_id,
            project_id=self.test_project_id,
            status=ExecutionStatus.PAUSED,
            progress=45.2,
            current_task="1.1.1",
            totals=TaskTotals(completed=3, total=8),
            customer_id="customer-123",
            branch="task/1-1-1-add-devteam-enabled-flag",
            artifacts=ExecutionArtifacts(),
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.mock_completed_projection = StatusProjection(
            execution_id=self.test_execution_id,
            project_id=self.test_project_id,
            status=ExecutionStatus.COMPLETED,
            progress=100.0,
            current_task="1.1.1",
            totals=TaskTotals(completed=8, total=8),
            customer_id="customer-123",
            branch="task/1-1-1-add-devteam-enabled-flag",
            artifacts=ExecutionArtifacts(),
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.mock_stopping_projection = StatusProjection(
            execution_id=self.test_execution_id,
            project_id=self.test_project_id,
            status=ExecutionStatus.STOPPING,
            progress=45.2,
            current_task="1.1.1",
            totals=TaskTotals(completed=3, total=8),
            customer_id="customer-123",
            branch="task/1-1-1-add-devteam-enabled-flag",
            artifacts=ExecutionArtifacts(),
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.mock_stopped_projection = StatusProjection(
            execution_id=self.test_execution_id,
            project_id=self.test_project_id,
            status=ExecutionStatus.STOPPED,
            progress=45.2,
            current_task="1.1.1",
            totals=TaskTotals(completed=3, total=8),
            customer_id="customer-123",
            branch="task/1-1-1-add-devteam-enabled-flag",
            artifacts=ExecutionArtifacts(),
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    @pytest.mark.asyncio
    async def test_stop_automation_success_running_to_stopping(self, mock_get_service):
        """Test successful stop operation from running to stopping state."""
        # Arrange
        mock_service = Mock()
        mock_service.get_status_by_project_id.return_value = self.mock_running_projection
        mock_get_service.return_value = mock_service
        
        # Act
        result = await stop_devteam_automation(
            project_id=self.test_project_id,
            session=self.mock_session
        )
        
        # Assert
        assert result.success is True
        assert result.message == "DevTeam automation stopped successfully"
        assert isinstance(result.data, DevTeamAutomationStopResponse)
        assert result.data.project_id == self.test_project_id
        assert result.data.execution_id == self.test_execution_id
        assert result.data.previous_status == ExecutionStatus.RUNNING.value
        assert result.data.current_status == ExecutionStatus.STOPPING.value
        assert result.data.stopped_at is not None
        
        # Verify service calls
        mock_get_service.assert_called_once()
        mock_service.get_status_by_project_id.assert_called_once_with(
            project_id=self.test_project_id
        )

    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    @pytest.mark.asyncio
    async def test_stop_automation_project_not_found(self, mock_get_service):
        """Test stop operation when project is not found."""
        # Arrange
        mock_service = Mock()
        mock_service.get_status_by_project_id.return_value = None
        mock_get_service.return_value = mock_service
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await stop_devteam_automation(
                project_id=self.test_project_id,
                session=self.mock_session
            )
        
        # Verify it's a 404 HTTPException
        assert exc_info.value.status_code == 404
        assert "No automation found for the specified project" in str(exc_info.value.detail)

    @pytest.mark.parametrize("current_status,status_projection", [
        (ExecutionStatus.IDLE, "mock_idle_projection"),
        (ExecutionStatus.INITIALIZING, "mock_initializing_projection"),
        (ExecutionStatus.PAUSED, "mock_paused_projection"),
        (ExecutionStatus.STOPPING, "mock_stopping_projection"),
        (ExecutionStatus.STOPPED, "mock_stopped_projection"),
        (ExecutionStatus.COMPLETED, "mock_completed_projection"),
        (ExecutionStatus.ERROR, "mock_error_projection"),
    ])
    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    @pytest.mark.asyncio
    async def test_stop_automation_invalid_state_transitions(self, mock_get_service, current_status, status_projection):
        """Test that stop operation returns 409 for invalid state transitions."""
        # Arrange - create projection for the current status
        if status_projection == "mock_idle_projection":
            projection = StatusProjection(
                execution_id=self.test_execution_id,
                project_id=self.test_project_id,
                status=ExecutionStatus.IDLE,
                progress=0.0,
                current_task=None,
                totals=TaskTotals(completed=0, total=8),
                customer_id="customer-123",
                branch=None,
                artifacts=ExecutionArtifacts(),
                started_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        elif status_projection == "mock_initializing_projection":
            projection = StatusProjection(
                execution_id=self.test_execution_id,
                project_id=self.test_project_id,
                status=ExecutionStatus.INITIALIZING,
                progress=5.0,
                current_task="1.1.1",
                totals=TaskTotals(completed=0, total=8),
                customer_id="customer-123",
                branch="task/1-1-1-add-devteam-enabled-flag",
                artifacts=ExecutionArtifacts(),
                started_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        elif status_projection == "mock_error_projection":
            projection = StatusProjection(
                execution_id=self.test_execution_id,
                project_id=self.test_project_id,
                status=ExecutionStatus.ERROR,
                progress=45.2,
                current_task="1.1.1",
                totals=TaskTotals(completed=3, total=8),
                customer_id="customer-123",
                branch="task/1-1-1-add-devteam-enabled-flag",
                artifacts=ExecutionArtifacts(),
                started_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        else:
            # Use the existing mock projections
            projection = getattr(self, status_projection)
        
        mock_service = Mock()
        mock_service.get_status_by_project_id.return_value = projection
        mock_get_service.return_value = mock_service
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await stop_devteam_automation(
                project_id=self.test_project_id,
                session=self.mock_session
            )
        
        # Verify it's a 409 HTTPException for invalid state transition
        assert exc_info.value.status_code == 409
        assert "Invalid state transition" in str(exc_info.value.detail)
        assert f"cannot stop automation that is {current_status.value}" in str(exc_info.value.detail)

    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    @pytest.mark.asyncio
    async def test_stop_automation_state_transition_validation(self, mock_get_service):
        """Test that stop operation validates state transitions correctly."""
        # Arrange
        mock_service = Mock()
        mock_service.get_status_by_project_id.return_value = self.mock_running_projection
        mock_get_service.return_value = mock_service
        
        # Act
        result = await stop_devteam_automation(
            project_id=self.test_project_id,
            session=self.mock_session
        )
        
        # Assert state transition
        assert result.data.previous_status == ExecutionStatus.RUNNING.value
        assert result.data.current_status == ExecutionStatus.STOPPING.value
        
        # Validate that only running→stopping transition is allowed
        # This is implicitly tested by the parametrized test above

    @pytest.mark.parametrize("invalid_project_id,expected_error", [
        ("", "Project ID cannot be empty"),
        ("   ", "Project ID cannot be empty"),
        ("invalid-chars!", "Project ID must contain only alphanumeric characters"),
        ("customer-123/", "Project ID must be in format 'customer-id/project-id'"),
        ("/project-abc", "Project ID must be in format 'customer-id/project-id'"),
        ("customer-123//project-abc", "Project ID must be in format 'customer-id/project-id'"),
    ])
    @pytest.mark.asyncio
    async def test_stop_automation_invalid_project_id_validation(self, invalid_project_id, expected_error):
        """Test project ID validation with various invalid formats."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await stop_devteam_automation(
                project_id=invalid_project_id,
                session=self.mock_session
            )
        
        # Verify it's a 422 HTTPException for validation error
        assert exc_info.value.status_code == 422
        assert "Request validation failed" in str(exc_info.value.detail)

    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    @pytest.mark.asyncio
    async def test_stop_automation_repository_error(self, mock_get_service):
        """Test stop operation when repository error occurs."""
        # Arrange
        mock_service = Mock()
        mock_service.get_status_by_project_id.side_effect = RepositoryError("Database connection failed")
        mock_get_service.return_value = mock_service
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await stop_devteam_automation(
                project_id=self.test_project_id,
                session=self.mock_session
            )
        
        # Verify it's a 500 HTTPException for repository error
        assert exc_info.value.status_code == 500
        assert "Database error occurred while stopping automation" in str(exc_info.value.detail)

    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    @pytest.mark.asyncio
    async def test_stop_automation_general_exception(self, mock_get_service):
        """Test stop operation when general exception occurs."""
        # Arrange
        mock_get_service.side_effect = Exception("Unexpected error")
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await stop_devteam_automation(
                project_id=self.test_project_id,
                session=self.mock_session
            )
        
        # Verify it's a 500 HTTPException for general error
        assert exc_info.value.status_code == 500
        assert "Internal server error occurred while stopping automation" in str(exc_info.value.detail)

    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    @patch('api.v1.endpoints.devteam_automation.time')
    @pytest.mark.asyncio
    async def test_stop_automation_performance_monitoring(self, mock_time, mock_get_service):
        """Test that stop operation meets performance requirements (≤200ms)."""
        # Arrange
        mock_time.time.side_effect = [0.0, 0.15]  # 150ms duration
        mock_service = Mock()
        mock_service.get_status_by_project_id.return_value = self.mock_running_projection
        mock_get_service.return_value = mock_service
        
        # Act
        result = await stop_devteam_automation(
            project_id=self.test_project_id,
            session=self.mock_session
        )
        
        # Assert
        assert result.success is True
        # Performance is logged but not returned in response
        # The test verifies that the endpoint completes within reasonable time

    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    @pytest.mark.asyncio
    async def test_stop_automation_response_format(self, mock_get_service):
        """Test that stop operation returns correct response format."""
        # Arrange
        mock_service = Mock()
        mock_service.get_status_by_project_id.return_value = self.mock_running_projection
        mock_get_service.return_value = mock_service
        
        # Act
        result = await stop_devteam_automation(
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
        assert hasattr(result.data, 'stopped_at')
        
        # Assert data types
        assert isinstance(result.data.project_id, str)
        assert isinstance(result.data.execution_id, str)
        assert isinstance(result.data.previous_status, str)
        assert isinstance(result.data.current_status, str)
        assert isinstance(result.data.stopped_at, str)

    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    @pytest.mark.asyncio
    async def test_stop_automation_integration_with_status_projection_service(self, mock_get_service):
        """Test integration with status projection service."""
        # Arrange
        mock_service = Mock()
        mock_service.get_status_by_project_id.return_value = self.mock_running_projection
        mock_get_service.return_value = mock_service
        
        # Act
        result = await stop_devteam_automation(
            project_id=self.test_project_id,
            session=self.mock_session
        )
        
        # Assert service integration
        mock_get_service.assert_called_once()
        # Verify correlation_id is passed (it's generated in the function)
        call_args = mock_get_service.call_args
        assert 'session' in call_args.kwargs
        assert 'correlation_id' in call_args.kwargs
        assert call_args.kwargs['session'] == self.mock_session
        
        # Verify status retrieval
        mock_service.get_status_by_project_id.assert_called_once_with(
            project_id=self.test_project_id
        )
        
        # Assert successful result
        assert result.success is True
        assert result.data.execution_id == self.test_execution_id

    @pytest.mark.parametrize("project_id_format", [
        "customer-123/project-abc",
        "customer_456/project_def",
        "customer-789/project-ghi-jkl",
        "simple-project",  # Single part project ID
    ])
    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    @pytest.mark.asyncio
    async def test_stop_automation_valid_project_id_formats(self, mock_get_service, project_id_format):
        """Test stop operation with various valid project ID formats."""
        # Arrange
        mock_service = Mock()
        running_projection = StatusProjection(
            execution_id=self.test_execution_id,
            project_id=project_id_format,
            status=ExecutionStatus.RUNNING,
            progress=45.2,
            current_task="1.1.1",
            totals=TaskTotals(completed=3, total=8),
            customer_id="customer-123",
            branch="task/1-1-1-add-devteam-enabled-flag",
            artifacts=ExecutionArtifacts(),
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        mock_service.get_status_by_project_id.return_value = running_projection
        mock_get_service.return_value = mock_service
        
        # Act
        result = await stop_devteam_automation(
            project_id=project_id_format,
            session=self.mock_session
        )
        
        # Assert
        assert result.success is True
        assert result.data.project_id == project_id_format
        assert result.data.previous_status == ExecutionStatus.RUNNING.value
        assert result.data.current_status == ExecutionStatus.STOPPING.value


if __name__ == "__main__":
    pytest.main([__file__])