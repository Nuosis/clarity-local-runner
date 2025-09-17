"""
Simple unit tests for DevTeam Automation Pause Endpoint - Task 5.4.1

This module provides focused unit tests for the POST /api/devteam/automation/pause/{projectId}
endpoint, validating core functionality without complex type checking issues.
"""

import asyncio
import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch
from fastapi import HTTPException

from api.v1.endpoints.devteam_automation import pause_devteam_automation
from schemas.status_projection_schema import (
    StatusProjection,
    ExecutionStatus,
    TaskTotals
)
from core.exceptions import RepositoryError


class TestDevTeamPauseEndpointSimple:
    """Simple unit tests for DevTeam automation pause endpoint."""
    
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
        assert exc_info.value.detail.get("success") is False
        assert "No automation status found for project" in str(exc_info.value.detail)
    
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
        assert exc_info.value.detail.get("success") is False
        assert "Invalid state transition" in str(exc_info.value.detail)
    
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
        assert exc_info.value.detail.get("success") is False
        assert "VALIDATION_ERROR" in str(exc_info.value.detail)
    
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
        assert exc_info.value.detail.get("success") is False
        assert "VALIDATION_ERROR" in str(exc_info.value.detail)
    
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
        assert exc_info.value.detail.get("success") is False
        assert "REPOSITORY_ERROR" in str(exc_info.value.detail)
    
    @pytest.mark.parametrize("invalid_status", [
        ExecutionStatus.IDLE,
        ExecutionStatus.INITIALIZING,
        ExecutionStatus.PAUSED,
        ExecutionStatus.ERROR,
    ])
    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    @pytest.mark.asyncio
    async def test_pause_automation_invalid_state_transitions(self, mock_get_service, invalid_status):
        """Test pause operation with various invalid state transitions."""
        # Arrange - Set appropriate progress values for each status
        if invalid_status == ExecutionStatus.IDLE:
            progress = 0.0
            current_task = None
        elif invalid_status == ExecutionStatus.INITIALIZING:
            progress = 5.0  # ≤10% for initializing
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
            await pause_devteam_automation(
                project_id=self.test_project_id,
                session=self.mock_session
            )
        
        # Validate 409 response
        assert exc_info.value.status_code == 409
        assert exc_info.value.detail.get("success") is False
        assert invalid_status.value in str(exc_info.value.detail)
    
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
        assert result.data is not None
        assert hasattr(result.data, 'project_id')
        assert hasattr(result.data, 'execution_id')
        assert hasattr(result.data, 'previous_status')
        assert hasattr(result.data, 'current_status')
        assert hasattr(result.data, 'paused_at')
        
        # Validate data types
        assert isinstance(result.data.project_id, str)
        assert isinstance(result.data.execution_id, str)
        assert isinstance(result.data.previous_status, str)
        assert isinstance(result.data.current_status, str)
        assert isinstance(result.data.paused_at, str)
        
        # Validate ISO timestamp format
        datetime.fromisoformat(result.data.paused_at.replace('Z', '+00:00'))


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])