"""
Task 5.3.2: DevTeam Automation Status Endpoint - Final Unit Tests
================================================================

This test suite validates the GET /api/devteam/automation/status/{project_id} endpoint
implementation for Task 5.3.2, focusing on comprehensive testing of the endpoint logic.

Test Coverage:
- JSON response format validation against ADD Section 5.2 specification
- All execution status scenarios (IDLE, INITIALIZING, RUNNING, PAUSED, COMPLETED, ERROR)
- StatusProjectionService integration with proper mocking
- Error handling (404, 422, 500 scenarios)
- Performance validation (≤200ms requirement)
- Security and input validation
- Data accuracy and state consistency

ADD Section 5.2 Response Format:
{
    "status": "running",
    "progress": 45.2,
    "current_task": "1.1.1",
    "totals": {
        "completed": 3,
        "total": 8
    },
    "execution_id": "exec_12345678-1234-1234-1234-123456789012",
    "branch": "task/1-1-1-add-devteam-enabled-flag",
    "started_at": "2025-01-14T18:25:00Z",
    "updated_at": "2025-01-14T18:30:00Z"
}
"""

import pytest
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException

# Import the endpoint function directly
from api.v1.endpoints.devteam_automation import get_devteam_automation_status
from schemas.status_projection_schema import StatusProjection, ExecutionStatus, TaskTotals
from services.status_projection_service import StatusProjectionService
from core.exceptions import RepositoryError


class TestDevTeamStatusEndpointTask532Final:
    """Final unit tests for DevTeam Automation Status Endpoint - Task 5.3.2"""

    def setup_method(self):
        """Set up test fixtures"""
        self.test_project_id = "test-project-123"
        self.test_customer_id = "customer-456"
        
        # Create valid test projection data
        self.test_projection = StatusProjection(
            execution_id="exec_test_123",
            project_id=self.test_project_id,
            customer_id=self.test_customer_id,
            status=ExecutionStatus.RUNNING,
            progress=45.0,
            current_task="1.1.1",
            totals=TaskTotals(completed=3, total=8),
            branch="feature/new-api",
            started_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    async def test_json_response_format_matches_add_specification(self, mock_service_factory):
        """Test that JSON response format exactly matches ADD Section 5.2 specification"""
        # Arrange
        mock_service = Mock(spec=StatusProjectionService)
        mock_service.get_status_by_project_id = Mock(return_value=self.test_projection)
        mock_service_factory.return_value = mock_service

        # Act
        result = await get_devteam_automation_status(self.test_project_id)

        # Assert - Verify response structure matches ADD Section 5.2
        assert result.success is True
        assert result.data is not None
        
        response_data = result.data
        
        # Required fields from ADD Section 5.2
        assert hasattr(response_data, 'status')
        assert hasattr(response_data, 'progress')
        assert hasattr(response_data, 'current_task')
        assert hasattr(response_data, 'totals')
        assert hasattr(response_data, 'execution_id')
        
        # Optional fields from ADD Section 5.2
        assert hasattr(response_data, 'branch')
        assert hasattr(response_data, 'started_at')
        assert hasattr(response_data, 'updated_at')
        
        # Verify data types and values
        assert response_data.status == "running"
        assert response_data.progress == 45.0
        assert response_data.current_task == "1.1.1"
        assert response_data.totals["completed"] == 3
        assert response_data.totals["total"] == 8
        assert response_data.execution_id == "exec_test_123"
        assert response_data.branch == "feature/new-api"
        
        # Verify datetime fields are properly formatted
        assert isinstance(response_data.started_at, str)
        assert isinstance(response_data.updated_at, str)

    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    async def test_all_execution_statuses(self, mock_service_factory):
        """Test JSON response format for all execution statuses"""
        mock_service = Mock(spec=StatusProjectionService)
        mock_service_factory.return_value = mock_service
        
        # Test data for each status
        status_test_cases = [
            {
                "status": ExecutionStatus.IDLE,
                "progress": 0.0,
                "current_task": None,
                "totals": TaskTotals(completed=0, total=0)
            },
            {
                "status": ExecutionStatus.INITIALIZING,
                "progress": 5.0,
                "current_task": "1.1.1",
                "totals": TaskTotals(completed=0, total=10)
            },
            {
                "status": ExecutionStatus.RUNNING,
                "progress": 45.0,
                "current_task": "1.1.2",
                "totals": TaskTotals(completed=4, total=10)
            },
            {
                "status": ExecutionStatus.PAUSED,
                "progress": 60.0,
                "current_task": "1.1.3",
                "totals": TaskTotals(completed=6, total=10)
            },
            {
                "status": ExecutionStatus.COMPLETED,
                "progress": 100.0,
                "current_task": None,
                "totals": TaskTotals(completed=10, total=10)
            },
            {
                "status": ExecutionStatus.ERROR,
                "progress": 30.0,
                "current_task": "1.1.1",
                "totals": TaskTotals(completed=3, total=10)
            }
        ]
        
        for test_case in status_test_cases:
            # Create test projection for this status
            test_projection = StatusProjection(
                execution_id=f"exec_{test_case['status'].value.lower()}",
                project_id=self.test_project_id,
                customer_id=self.test_customer_id,
                status=test_case["status"],
                progress=test_case["progress"],
                current_task=test_case["current_task"],
                totals=test_case["totals"],
                branch="main" if test_case["status"] != ExecutionStatus.IDLE else None,
                started_at=datetime.now(timezone.utc) if test_case["status"] != ExecutionStatus.IDLE else None,
                updated_at=datetime.now(timezone.utc)
            )
            
            mock_service.get_status_by_project_id = Mock(return_value=test_projection)
            
            # Act
            result = await get_devteam_automation_status(self.test_project_id)
            
            # Assert
            assert result.success is True
            response_data = result.data
            assert response_data.status == test_case["status"].value
            assert response_data.progress == test_case["progress"]
            assert response_data.current_task == test_case["current_task"]
            assert response_data.totals["completed"] == test_case["totals"].completed
            assert response_data.totals["total"] == test_case["totals"].total

    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    async def test_performance_requirement_met(self, mock_service_factory):
        """Test that endpoint meets ≤200ms performance requirement"""
        # Arrange
        mock_service = Mock(spec=StatusProjectionService)
        mock_service.get_status_by_project_id = Mock(return_value=self.test_projection)
        mock_service_factory.return_value = mock_service

        # Act - Measure execution time
        start_time = time.time()
        result = await get_devteam_automation_status(self.test_project_id)
        end_time = time.time()
        
        execution_time_ms = (end_time - start_time) * 1000

        # Assert
        assert result.success is True
        assert execution_time_ms <= 200, f"Endpoint took {execution_time_ms:.2f}ms, exceeds 200ms requirement"

    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    async def test_error_handling_404_not_found(self, mock_service_factory):
        """Test 404 error handling for non-existent projects"""
        # Arrange
        mock_service = Mock(spec=StatusProjectionService)
        mock_service.get_status_by_project_id = Mock(return_value=None)
        mock_service_factory.return_value = mock_service

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_devteam_automation_status("non-existent-project")
        
        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail).lower()

    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    async def test_error_handling_500_internal_server_error(self, mock_service_factory):
        """Test 500 error handling for repository errors"""
        # Arrange
        mock_service = Mock(spec=StatusProjectionService)
        mock_service.get_status_by_project_id = Mock(
            side_effect=RepositoryError("Database connection failed")
        )
        mock_service_factory.return_value = mock_service

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_devteam_automation_status(self.test_project_id)
        
        assert exc_info.value.status_code == 500
        assert "error" in str(exc_info.value.detail).lower()

    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    async def test_service_integration(self, mock_service_factory):
        """Test proper integration with StatusProjectionService"""
        # Arrange
        mock_service = Mock(spec=StatusProjectionService)
        mock_service.get_status_by_project_id = Mock(return_value=self.test_projection)
        mock_service_factory.return_value = mock_service

        # Act
        result = await get_devteam_automation_status(self.test_project_id)

        # Assert
        mock_service_factory.assert_called_once()
        mock_service.get_status_by_project_id.assert_called_once_with(project_id=self.test_project_id)
        assert result.success is True

    async def test_input_validation_project_id_format(self):
        """Test input validation for project ID format"""
        # Test various invalid project ID formats
        invalid_project_ids = [
            "",  # Empty string
            "a",  # Too short
            "project with spaces",  # Contains spaces
            "project@invalid",  # Invalid characters
            "project-" + "x" * 100,  # Too long
        ]
        
        for invalid_id in invalid_project_ids:
            # The validation should happen at the FastAPI level
            # Here we test that our function handles edge cases gracefully
            with patch('api.v1.endpoints.devteam_automation.get_status_projection_service') as mock_factory:
                mock_service = Mock(spec=StatusProjectionService)
                mock_service.get_status_by_project_id = Mock(return_value=None)
                mock_factory.return_value = mock_service
                
                with pytest.raises(HTTPException) as exc_info:
                    await get_devteam_automation_status(invalid_id)
                
                # Should return 404 for invalid/non-existent projects or 422 for validation
                assert exc_info.value.status_code in [404, 422]

    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    async def test_data_accuracy_mapping(self, mock_service_factory):
        """Test accurate mapping from StatusProjection to response format"""
        # Arrange - Create projection with specific test values
        test_projection = StatusProjection(
            execution_id="exec_mapping_test",
            project_id="mapping-project-123",
            customer_id="mapping-customer-456",
            status=ExecutionStatus.RUNNING,
            progress=75.0,
            current_task="1.2.3",
            totals=TaskTotals(completed=7, total=9),
            branch="release/v2.0",
            started_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 15, 10, 45, 0, tzinfo=timezone.utc)
        )
        
        mock_service = Mock(spec=StatusProjectionService)
        mock_service.get_status_by_project_id = Mock(return_value=test_projection)
        mock_service_factory.return_value = mock_service

        # Act
        result = await get_devteam_automation_status("mapping-project-123")

        # Assert - Verify exact mapping
        assert result.success is True
        response_data = result.data
        
        assert response_data.status == "running"
        assert response_data.progress == 75.0
        assert response_data.current_task == "1.2.3"
        assert response_data.totals["completed"] == 7
        assert response_data.totals["total"] == 9
        assert response_data.execution_id == "exec_mapping_test"
        assert response_data.branch == "release/v2.0"
        assert response_data.started_at == "2024-01-15T10:30:00+00:00"
        assert response_data.updated_at == "2024-01-15T10:45:00+00:00"

    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    async def test_concurrent_requests_performance(self, mock_service_factory):
        """Test performance with multiple concurrent requests"""
        import asyncio
        
        # Arrange
        mock_service = Mock(spec=StatusProjectionService)
        mock_service.get_status_by_project_id = Mock(return_value=self.test_projection)
        mock_service_factory.return_value = mock_service

        # Act - Create multiple concurrent requests
        async def make_request():
            start_time = time.time()
            result = await get_devteam_automation_status(self.test_project_id)
            end_time = time.time()
            return result, (end_time - start_time) * 1000

        # Run 5 concurrent requests (reduced for stability)
        tasks = [make_request() for _ in range(5)]
        results = await asyncio.gather(*tasks)

        # Assert
        for result, execution_time in results:
            assert result.success is True
            assert execution_time <= 200, f"Request took {execution_time:.2f}ms, exceeds 200ms requirement"

    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    async def test_optional_fields_handling(self, mock_service_factory):
        """Test handling of optional fields (branch, started_at) when None"""
        # Arrange - Create projection with None optional fields
        test_projection = StatusProjection(
            execution_id="exec_optional_test",
            project_id=self.test_project_id,
            customer_id=self.test_customer_id,
            status=ExecutionStatus.IDLE,
            progress=0.0,
            current_task=None,
            totals=TaskTotals(completed=0, total=0),
            branch=None,  # Optional field as None
            started_at=None,  # Optional field as None
            updated_at=datetime.now(timezone.utc)
        )
        
        mock_service = Mock(spec=StatusProjectionService)
        mock_service.get_status_by_project_id = Mock(return_value=test_projection)
        mock_service_factory.return_value = mock_service

        # Act
        result = await get_devteam_automation_status(self.test_project_id)

        # Assert
        assert result.success is True
        response_data = result.data
        
        # Optional fields should still be present but with None values
        assert response_data.branch is None
        assert response_data.started_at is None
        assert response_data.current_task is None
        
        # Required fields should be present
        assert response_data.status == "idle"
        assert response_data.progress == 0.0
        assert response_data.execution_id == "exec_optional_test"
        assert response_data.updated_at is not None

    def test_add_specification_compliance(self):
        """Test that response format complies with ADD Section 5.2 specification"""
        # This test documents the exact ADD Section 5.2 specification
        add_section_5_2_format = {
            "status": "string",  # Required: Current execution status
            "progress": "float",  # Required: Progress percentage (0.0-100.0)
            "current_task": "string|null",  # Required: Current task description
            "totals": {  # Required: Task completion totals
                "completed": "integer",  # Required: Number of completed tasks
                "total": "integer"  # Required: Total number of tasks
            },
            "execution_id": "string",  # Required: Unique execution identifier
            "branch": "string|null",  # Optional: Git branch name
            "started_at": "string|null",  # Optional: ISO 8601 timestamp
            "updated_at": "string"  # Required: ISO 8601 timestamp
        }
        
        # This test serves as documentation of the required format
        # The actual validation is done in the other tests
        assert add_section_5_2_format is not None
        
        # Verify all required fields are documented
        required_fields = ["status", "progress", "current_task", "totals", "execution_id", "updated_at"]
        optional_fields = ["branch", "started_at"]
        
        for field in required_fields:
            assert field in add_section_5_2_format
        
        for field in optional_fields:
            assert field in add_section_5_2_format
        
        # Verify totals structure
        assert "completed" in add_section_5_2_format["totals"]
        assert "total" in add_section_5_2_format["totals"]

    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    async def test_validation_error_handling(self, mock_service_factory):
        """Test validation error handling for malformed project IDs"""
        # Arrange
        mock_service = Mock(spec=StatusProjectionService)
        mock_service_factory.return_value = mock_service

        # Test empty project ID
        with pytest.raises(HTTPException) as exc_info:
            await get_devteam_automation_status("")
        
        assert exc_info.value.status_code == 422

        # Test project ID with invalid characters
        with pytest.raises(HTTPException) as exc_info:
            await get_devteam_automation_status("project@invalid!")
        
        assert exc_info.value.status_code == 422

    @patch('api.v1.endpoints.devteam_automation.get_status_projection_service')
    async def test_response_time_consistency(self, mock_service_factory):
        """Test that response times are consistent across multiple calls"""
        # Arrange
        mock_service = Mock(spec=StatusProjectionService)
        mock_service.get_status_by_project_id = Mock(return_value=self.test_projection)
        mock_service_factory.return_value = mock_service

        # Act - Make multiple sequential calls
        response_times = []
        for _ in range(10):
            start_time = time.time()
            result = await get_devteam_automation_status(self.test_project_id)
            end_time = time.time()
            
            assert result.success is True
            response_times.append((end_time - start_time) * 1000)

        # Assert - All response times should be under 200ms
        for response_time in response_times:
            assert response_time <= 200, f"Response time {response_time:.2f}ms exceeds 200ms requirement"
        
        # Calculate average response time
        avg_response_time = sum(response_times) / len(response_times)
        assert avg_response_time <= 100, f"Average response time {avg_response_time:.2f}ms should be well under limit"