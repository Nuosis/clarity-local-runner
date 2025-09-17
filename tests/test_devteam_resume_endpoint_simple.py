"""
Simple unit tests for DevTeam Automation Resume Endpoint - Task 5.5.1

This module provides focused unit tests for the POST /api/devteam/automation/resume/{projectId}
endpoint, validating core functionality including paused→running state transitions.
"""

import asyncio
import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch
from fastapi import HTTPException

from api.v1.endpoints.devteam_automation import resume_devteam_automation
from schemas.status_projection_schema import (
    StatusProjection,
    ExecutionStatus,
    TaskTotals
)
from core.exceptions import RepositoryError


class TestDevTeamResumeEndpointSimple:
    """Simple unit tests for DevTeam automation resume endpoint."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.test_project_id = "customer-123/project-abc"
        self.test_execution_id = "exec_12345678-1234-1234-1234-123456789012"
        self.mock_session = Mock()
        
        # Create mock status projection for paused state
        self.mock_paused_projection = StatusProjection(
            execution_id=self.test_execution_id,
            project_id=self.test_project_id,
            status=ExecutionStatus.PAUSED,
            progress=45.2,
            current_task="1.1.1",
            totals=TaskTotals(completed=3, total=8),
            customer_id="customer-123",
            branch="task/1-1-1-add-devteam-enabled-flag",
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
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
    async def test_resume_automation_success_paused_to_running(self, mock_get_service):
        """Test successful resume operation from paused to running state."""
        # Arrange
        mock_service = Mock()
        mock_service.get_status_by_project_id.return_value = self.mock_paused_projection
        mock_get_service.return_value = mock_service
        
        start_time = time.time()
        
        # Act
        result = await resume_devteam_automation(
            project_id=self.test_project_id,
            session=self.mock_session
        )
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Assert
        assert result.success is True
        assert result.message == "DevTeam automation resumed successfully"
        assert result.data is not None
        assert result.data.project_id == self.test_project_id
        assert result.data.execution_id == self.test_execution_id
        assert result.data.previous_status == "paused"
        assert result.data.current_status == "running"
        assert result.data.resumed_at is not None
        
        # Validate performance requirement
        assert duration_ms <= 200, f"Response time {duration_ms}ms exceeds 200ms requirement"
        
        # Verify service calls
        mock_get_service.assert_called_once()
        mock_service.get_status_by_project_id.assert_called_once_with(
            project_id=self.test_project_id
        )
    
    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    @pytest.mark.asyncio
    async def test_resume_automation_project_not_found(self, mock_get_service):
        """Test resume operation when project is not found (404)."""
        # Arrange
        mock_service = Mock()
        mock_service.get_status_by_project_id.return_value = None
        mock_get_service.return_value = mock_service
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await resume_devteam_automation(
                project_id=self.test_project_id,
                session=self.mock_session
            )
        
        # Validate 404 response
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail.get("success") is False
        assert "No automation status found for project" in str(exc_info.value.detail)
    
    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    @pytest.mark.asyncio
    async def test_resume_automation_invalid_state_transition_running(self, mock_get_service):
        """Test resume operation with invalid state transition from running (409)."""
        # Arrange
        mock_service = Mock()
        mock_service.get_status_by_project_id.return_value = self.mock_running_projection
        mock_get_service.return_value = mock_service
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await resume_devteam_automation(
                project_id=self.test_project_id,
                session=self.mock_session
            )
        
        # Validate 409 response
        assert exc_info.value.status_code == 409
        assert exc_info.value.detail.get("success") is False
        assert "Invalid state transition" in str(exc_info.value.detail)
        assert "cannot resume automation that is running" in str(exc_info.value.detail)
    
    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    @pytest.mark.asyncio
    async def test_resume_automation_invalid_state_transition_completed(self, mock_get_service):
        """Test resume operation with invalid state transition from completed (409)."""
        # Arrange
        mock_service = Mock()
        mock_service.get_status_by_project_id.return_value = self.mock_completed_projection
        mock_get_service.return_value = mock_service
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await resume_devteam_automation(
                project_id=self.test_project_id,
                session=self.mock_session
            )
        
        # Validate 409 response
        assert exc_info.value.status_code == 409
        assert exc_info.value.detail.get("success") is False
        assert "Invalid state transition" in str(exc_info.value.detail)
        assert "cannot resume automation that is completed" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_resume_automation_invalid_project_id_empty(self):
        """Test resume operation with empty project ID (422)."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await resume_devteam_automation(
                project_id="",
                session=self.mock_session
            )
        
        # Validate 422 response
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail.get("success") is False
        assert "VALIDATION_ERROR" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_resume_automation_invalid_project_id_format(self):
        """Test resume operation with invalid project ID format (422)."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await resume_devteam_automation(
                project_id="invalid@project#id",
                session=self.mock_session
            )
        
        # Validate 422 response
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail.get("success") is False
        assert "VALIDATION_ERROR" in str(exc_info.value.detail)
    
    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    @pytest.mark.asyncio
    async def test_resume_automation_repository_error(self, mock_get_service):
        """Test resume operation with repository error (500)."""
        # Arrange
        mock_service = Mock()
        mock_service.get_status_by_project_id.side_effect = RepositoryError("Database connection failed")
        mock_get_service.return_value = mock_service
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await resume_devteam_automation(
                project_id=self.test_project_id,
                session=self.mock_session
            )
        
        # Validate 500 response
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail.get("success") is False
        assert "REPOSITORY_ERROR" in str(exc_info.value.detail)
    
    @pytest.mark.parametrize("invalid_status", [
        ExecutionStatus.IDLE,
        ExecutionStatus.INITIALIZING,
        ExecutionStatus.RUNNING,
        ExecutionStatus.COMPLETED,
        ExecutionStatus.ERROR,
    ])
    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    @pytest.mark.asyncio
    async def test_resume_automation_invalid_state_transitions(self, mock_get_service, invalid_status):
        """Test resume operation with various invalid state transitions."""
        # Arrange - Set appropriate progress values for each status
        if invalid_status == ExecutionStatus.IDLE:
            progress = 0.0
            current_task = None
        elif invalid_status == ExecutionStatus.INITIALIZING:
            progress = 5.0  # ≤10% for initializing
            current_task = "1.1.1"
        elif invalid_status == ExecutionStatus.COMPLETED:
            progress = 100.0
            current_task = "1.1.1"
        else:
            progress = 25.0
            current_task = "1.1.1"
            
        mock_projection = StatusProjection(
            execution_id=self.test_execution_id,
            project_id=self.test_project_id,
            status=invalid_status,
            progress=progress,
            current_task=current_task,
            totals=TaskTotals(completed=2, total=8),
            customer_id="customer-123",
            branch="task/1-1-1-add-devteam-enabled-flag",
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        mock_service = Mock()
        mock_service.get_status_by_project_id.return_value = mock_projection
        mock_get_service.return_value = mock_service
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await resume_devteam_automation(
                project_id=self.test_project_id,
                session=self.mock_session
            )
        
        # Validate 409 response
        assert exc_info.value.status_code == 409
        assert exc_info.value.detail.get("success") is False
        assert invalid_status.value in str(exc_info.value.detail)
    
    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    @pytest.mark.asyncio
    async def test_resume_automation_performance_requirement(self, mock_get_service):
        """Test that resume operation meets performance requirement (≤200ms)."""
        # Arrange
        mock_service = Mock()
        mock_service.get_status_by_project_id.return_value = self.mock_paused_projection
        mock_get_service.return_value = mock_service
        
        # Act - Measure performance
        start_time = time.time()
        result = await resume_devteam_automation(
            project_id=self.test_project_id,
            session=self.mock_session
        )
        duration_ms = (time.time() - start_time) * 1000
        
        # Assert
        assert result.success is True
        assert duration_ms <= 200, f"Response time {duration_ms}ms exceeds 200ms requirement"
    
    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    @pytest.mark.asyncio
    async def test_resume_automation_response_format_compliance(self, mock_get_service):
        """Test that resume operation returns compliant response format."""
        # Arrange
        mock_service = Mock()
        mock_service.get_status_by_project_id.return_value = self.mock_paused_projection
        mock_get_service.return_value = mock_service
        
        # Act
        result = await resume_devteam_automation(
            project_id=self.test_project_id,
            session=self.mock_session
        )
        
        # Assert response structure
        assert hasattr(result, 'success')
        assert hasattr(result, 'data')
        assert hasattr(result, 'message')
        
        # Assert data structure
        assert result.data is not None
        assert hasattr(result.data, 'project_id')
        assert hasattr(result.data, 'execution_id')
        assert hasattr(result.data, 'previous_status')
        assert hasattr(result.data, 'current_status')
        assert hasattr(result.data, 'resumed_at')
        
        # Validate data types
        assert isinstance(result.data.project_id, str)
        assert isinstance(result.data.execution_id, str)
        assert isinstance(result.data.previous_status, str)
        assert isinstance(result.data.current_status, str)
        assert isinstance(result.data.resumed_at, str)
        
        # Validate ISO timestamp format
        datetime.fromisoformat(result.data.resumed_at.replace('Z', '+00:00'))
    
    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    @pytest.mark.asyncio
    async def test_resume_automation_state_transition_validation(self, mock_get_service):
        """Test that resume operation validates state transitions correctly."""
        # Arrange
        mock_service = Mock()
        mock_service.get_status_by_project_id.return_value = self.mock_paused_projection
        mock_get_service.return_value = mock_service
        
        # Act
        result = await resume_devteam_automation(
            project_id=self.test_project_id,
            session=self.mock_session
        )
        
        # Assert state transition
        assert result.data.previous_status == ExecutionStatus.PAUSED.value
        assert result.data.current_status == ExecutionStatus.RUNNING.value
        
        # Validate that only paused→running transition is allowed
        # This is implicitly tested by the parametrized test above
    
    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    @pytest.mark.asyncio
    async def test_resume_automation_correlation_id_generation(self, mock_get_service):
        """Test that resume operation generates correlation IDs for logging."""
        # Arrange
        mock_service = Mock()
        mock_service.get_status_by_project_id.return_value = self.mock_paused_projection
        mock_get_service.return_value = mock_service
        
        # Act
        result = await resume_devteam_automation(
            project_id=self.test_project_id,
            session=self.mock_session
        )
        
        # Assert - The correlation ID is used internally for logging
        # We can't directly test it without mocking the logger, but we can
        # verify the service was called with the session and correlation_id
        mock_get_service.assert_called_once()
        call_args = mock_get_service.call_args
        assert 'session' in call_args.kwargs
        assert 'correlation_id' in call_args.kwargs
        assert call_args.kwargs['correlation_id'].startswith('corr_')
    
    @pytest.mark.asyncio
    async def test_resume_automation_project_id_validation_whitespace(self):
        """Test resume operation with whitespace-only project ID (422)."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await resume_devteam_automation(
                project_id="   ",
                session=self.mock_session
            )
        
        # Validate 422 response
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail.get("success") is False
        assert "VALIDATION_ERROR" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_resume_automation_project_id_validation_malformed_slash(self):
        """Test resume operation with malformed project ID containing slash (422)."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await resume_devteam_automation(
                project_id="customer-123/",  # Missing project part
                session=self.mock_session
            )
        
        # Validate 422 response
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail.get("success") is False
        assert "VALIDATION_ERROR" in str(exc_info.value.detail)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])