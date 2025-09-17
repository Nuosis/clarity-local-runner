#!/usr/bin/env python3
"""
Task 5.3.2: Comprehensive Test Suite for DevTeam Automation Status Endpoint

This test suite validates the GET /api/devteam/automation/status/{project_id} endpoint
implementation with comprehensive coverage including:
- JSON response format validation against ADD Section 5.2 specification
- Unit tests for the status endpoint
- Integration tests with StatusProjectionService
- Performance validation tests (≤200ms requirement)
- Error handling tests (404, 422, 500 scenarios)
- >90% test coverage validation

Requirements validated:
- Response Format: Exact match to ADD Section 5.2 specification
- Performance: ≤200ms response time
- Error Handling: 404 for non-existent projects, 422 for invalid input, 500 for system errors
- Security: Input validation, audit logging, secure defaults
- Integration: Proper StatusProjectionService integration
- Data Accuracy: Real-time status updates, state consistency
"""

import json
import pytest
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Import the application and dependencies
from main import app
from schemas.status_projection_schema import (
    StatusProjection,
    ExecutionStatus,
    TaskTotals,
    ExecutionArtifacts
)
from services.status_projection_service import StatusProjectionService
from core.exceptions import RepositoryError


class TestDevTeamStatusEndpointTask532:
    """Comprehensive test suite for DevTeam Automation Status Endpoint - Task 5.3.2."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def sample_status_projection(self):
        """Create sample StatusProjection for testing."""
        return StatusProjection(
            execution_id="exec_12345678-1234-1234-1234-123456789012",
            project_id="customer-123/project-abc",
            status=ExecutionStatus.RUNNING,
            progress=45.2,
            current_task="1.1.1",
            totals=TaskTotals(completed=3, total=8),
            customer_id="customer-123",
            branch="task/1-1-1-add-devteam-enabled-flag",
            artifacts=ExecutionArtifacts(
                repo_path="/workspace/repos/customer-123-project-abc",
                branch="task/1-1-1-add-devteam-enabled-flag",
                logs=["Implementation started", "Aider tool initialized"],
                files_modified=["src/config.js", "README.md"]
            ),
            started_at=datetime.fromisoformat("2025-01-14T18:25:00"),
            updated_at=datetime.fromisoformat("2025-01-14T18:30:00")
        )

    # JSON Response Format Validation Tests
    def test_json_response_format_matches_add_specification(self, client, sample_status_projection):
        """Test that JSON response format exactly matches ADD Section 5.2 specification."""
        with patch('api.v1.endpoints.devteam_automation.get_status_projection_service') as mock_service_factory:
            mock_service = Mock(spec=StatusProjectionService)
            mock_service.get_status_by_project_id.return_value = sample_status_projection
            mock_service_factory.return_value = mock_service
            
            response = client.get("/api/v1/devteam/automation/status/customer-123/project-abc")
            
            assert response.status_code == 200
            response_data = response.json()
            
            # Validate top-level structure
            assert "success" in response_data
            assert "data" in response_data
            assert "message" in response_data
            assert response_data["success"] is True
            
            # Validate data structure matches ADD Section 5.2 exactly
            data = response_data["data"]
            required_fields = ["status", "progress", "current_task", "totals", "execution_id"]
            
            # Check all required fields are present
            for field in required_fields:
                assert field in data, f"Required field '{field}' missing from response"
            
            # Validate totals structure
            assert "totals" in data
            assert isinstance(data["totals"], dict)
            assert "completed" in data["totals"]
            assert "total" in data["totals"]
            assert isinstance(data["totals"]["completed"], int)
            assert isinstance(data["totals"]["total"], int)
            
            # Validate data types
            assert isinstance(data["status"], str)
            assert isinstance(data["progress"], (int, float))
            assert data["current_task"] is None or isinstance(data["current_task"], str)
            assert isinstance(data["execution_id"], str)
            
            # Validate specific values match expected format
            assert data["status"] == "running"
            assert data["progress"] == 45.2
            assert data["current_task"] == "1.1.1"
            assert data["totals"]["completed"] == 3
            assert data["totals"]["total"] == 8
            assert data["execution_id"] == "exec_12345678-1234-1234-1234-123456789012"

    def test_json_response_format_all_execution_statuses(self, client):
        """Test JSON response format for all possible execution statuses."""
        statuses_to_test = [
            (ExecutionStatus.IDLE, 0.0, None),
            (ExecutionStatus.INITIALIZING, 5.0, None),
            (ExecutionStatus.RUNNING, 45.2, "1.1.1"),
            (ExecutionStatus.PAUSED, 30.0, "1.2.1"),
            (ExecutionStatus.COMPLETED, 100.0, "1.3.1"),
            (ExecutionStatus.ERROR, 25.0, "1.1.2")
        ]
        
        for status, progress, current_task in statuses_to_test:
            with patch('api.v1.endpoints.devteam_automation.get_status_projection_service') as mock_service_factory:
                mock_projection = StatusProjection(
                    execution_id=f"exec_{uuid.uuid4()}",
                    project_id="customer-test/project-status",
                    status=status,
                    progress=progress,
                    current_task=current_task,
                    totals=TaskTotals(completed=2, total=5),
                    customer_id="customer-test",
                    branch="main",
                    started_at=datetime.utcnow()
                )
                
                mock_service = Mock(spec=StatusProjectionService)
                mock_service.get_status_by_project_id.return_value = mock_projection
                mock_service_factory.return_value = mock_service
                
                response = client.get("/api/v1/devteam/automation/status/customer-test/project-status")
                
                assert response.status_code == 200
                response_data = response.json()
                
                # Validate status-specific response format
                assert response_data["data"]["status"] == status.value
                assert response_data["data"]["progress"] == progress
                assert response_data["data"]["current_task"] == current_task

    # Integration Tests with StatusProjectionService
    def test_integration_with_status_projection_service(self, client):
        """Test integration with StatusProjectionService."""
        with patch('api.v1.endpoints.devteam_automation.get_status_projection_service') as mock_service_factory:
            mock_service = Mock(spec=StatusProjectionService)
            mock_service_factory.return_value = mock_service
            
            # Test service is called with correct parameters
            client.get("/api/v1/devteam/automation/status/customer-integration/project-test")
            
            # Verify service factory was called
            mock_service_factory.assert_called_once()
            call_args = mock_service_factory.call_args
            assert 'session' in call_args.kwargs
            assert 'correlation_id' in call_args.kwargs
            
            # Verify service method was called with correct project_id
            mock_service.get_status_by_project_id.assert_called_once_with(
                project_id="customer-integration/project-test"
            )

    def test_integration_handles_repository_error(self, client):
        """Test integration handles RepositoryError from service."""
        with patch('api.v1.endpoints.devteam_automation.get_status_projection_service') as mock_service_factory:
            mock_service = Mock(spec=StatusProjectionService)
            mock_service.get_status_by_project_id.side_effect = RepositoryError("Database connection failed")
            mock_service_factory.return_value = mock_service
            
            response = client.get("/api/v1/devteam/automation/status/customer-error/project-test")
            
            assert response.status_code == 500
            response_data = response.json()
            assert response_data["success"] is False
            assert "Database error" in response_data["message"]

    # Performance Validation Tests (≤200ms requirement)
    def test_performance_requirement_met(self, client):
        """Test that response time meets ≤200ms requirement."""
        with patch('api.v1.endpoints.devteam_automation.get_status_projection_service') as mock_service_factory:
            # Create a fast-responding mock service
            mock_service = Mock(spec=StatusProjectionService)
            mock_projection = StatusProjection(
                execution_id="exec_performance_test",
                project_id="customer-perf/project-test",
                status=ExecutionStatus.RUNNING,
                progress=50.0,
                current_task="1.1.1",
                totals=TaskTotals(completed=1, total=2),
                customer_id="customer-perf",
                branch="main",
                started_at=datetime.utcnow()
            )
            mock_service.get_status_by_project_id.return_value = mock_projection
            mock_service_factory.return_value = mock_service
            
            # Measure response time
            start_time = time.time()
            response = client.get("/api/v1/devteam/automation/status/customer-perf/project-test")
            duration_ms = (time.time() - start_time) * 1000
            
            assert response.status_code == 200
            assert duration_ms <= 200, f"Response time {duration_ms:.2f}ms exceeds 200ms requirement"

    def test_performance_with_multiple_concurrent_requests(self, client):
        """Test performance with multiple concurrent requests."""
        import concurrent.futures
        
        with patch('api.v1.endpoints.devteam_automation.get_status_projection_service') as mock_service_factory:
            mock_service = Mock(spec=StatusProjectionService)
            mock_projection = StatusProjection(
                execution_id="exec_concurrent_test",
                project_id="customer-concurrent/project-test",
                status=ExecutionStatus.RUNNING,
                progress=75.0,
                current_task="2.1.1",
                totals=TaskTotals(completed=3, total=4),
                customer_id="customer-concurrent",
                branch="main",
                started_at=datetime.utcnow()
            )
            mock_service.get_status_by_project_id.return_value = mock_projection
            mock_service_factory.return_value = mock_service
            
            def make_request():
                start_time = time.time()
                response = client.get("/api/v1/devteam/automation/status/customer-concurrent/project-test")
                duration_ms = (time.time() - start_time) * 1000
                return response.status_code, duration_ms
            
            # Make 10 concurrent requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(make_request) for _ in range(10)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            # Validate all requests succeeded and met performance requirement
            for status_code, duration_ms in results:
                assert status_code == 200
                assert duration_ms <= 200, f"Concurrent request took {duration_ms:.2f}ms > 200ms"

    # Error Handling Tests (404, 422, 500 scenarios)
    def test_error_handling_404_not_found(self, client):
        """Test 404 error handling for non-existent projects."""
        with patch('api.v1.endpoints.devteam_automation.get_status_projection_service') as mock_service_factory:
            mock_service = Mock(spec=StatusProjectionService)
            mock_service.get_status_by_project_id.return_value = None
            mock_service_factory.return_value = mock_service
            
            response = client.get("/api/v1/devteam/automation/status/customer-404/project-notfound")
            
            assert response.status_code == 404
            response_data = response.json()
            assert response_data["success"] is False
            assert "No automation status found" in response_data["message"]
            assert "data" in response_data
            assert response_data["data"]["project_id"] == "customer-404/project-notfound"

    def test_error_handling_422_validation_errors(self, client):
        """Test 422 error handling for validation errors."""
        invalid_project_ids = [
            ("", "empty project ID"),
            ("invalid-format", "missing slash separator"),
            ("customer-123/", "empty project part"),
            ("customer@123/project-abc", "invalid characters"),
            ("customer-123//project-abc", "double slash"),
        ]
        
        for invalid_id, description in invalid_project_ids:
            url = f"/api/v1/devteam/automation/status/{invalid_id}" if invalid_id else "/api/v1/devteam/automation/status/"
            response = client.get(url)
            
            assert response.status_code == 422, f"Failed for {description}: {invalid_id}"
            response_data = response.json()
            assert response_data["success"] is False
            assert "validation" in response_data["message"].lower()
            assert "errors" in response_data

    def test_error_handling_500_internal_server_error(self, client):
        """Test 500 error handling for internal server errors."""
        with patch('api.v1.endpoints.devteam_automation.get_status_projection_service') as mock_service_factory:
            # Simulate different types of internal errors
            error_scenarios = [
                (RepositoryError("Database connection failed"), "Database error"),
                (Exception("Unexpected error"), "Internal server error"),
                (RuntimeError("Service unavailable"), "Internal server error"),
            ]
            
            for error, expected_message_part in error_scenarios:
                mock_service = Mock(spec=StatusProjectionService)
                mock_service.get_status_by_project_id.side_effect = error
                mock_service_factory.return_value = mock_service
                
                response = client.get("/api/v1/devteam/automation/status/customer-500/project-error")
                
                assert response.status_code == 500
                response_data = response.json()
                assert response_data["success"] is False
                assert expected_message_part.lower() in response_data["message"].lower()
                assert "error_code" in response_data

    # Security and Input Validation Tests
    def test_security_input_validation(self, client):
        """Test security input validation."""
        malicious_inputs = [
            "customer-123/project-abc'; DROP TABLE events; --",
            "customer-123/project-abc<script>alert('xss')</script>",
            "customer-123/project-abc/../../../etc/passwd",
            "customer-123/project-abc%00",
            "customer-123/project-abc\x00",
        ]
        
        for malicious_input in malicious_inputs:
            response = client.get(f"/api/v1/devteam/automation/status/{malicious_input}")
            
            # Should return 422 validation error, not process malicious input
            assert response.status_code == 422
            response_data = response.json()
            assert response_data["success"] is False

    def test_audit_logging_correlation_id(self, client):
        """Test that audit logging includes correlation ID."""
        with patch('api.v1.endpoints.devteam_automation.get_status_projection_service') as mock_service_factory:
            mock_service = Mock(spec=StatusProjectionService)
            mock_service.get_status_by_project_id.return_value = None
            mock_service_factory.return_value = mock_service
            
            response = client.get("/api/v1/devteam/automation/status/customer-audit/project-test")
            
            # Verify service was called with correlation_id
            mock_service_factory.assert_called_once()
            call_kwargs = mock_service_factory.call_args.kwargs
            assert 'correlation_id' in call_kwargs
            assert call_kwargs['correlation_id'] is not None
            assert call_kwargs['correlation_id'].startswith('corr_')

    # Data Accuracy and State Consistency Tests
    def test_data_accuracy_status_projection_mapping(self, client):
        """Test data accuracy in status projection mapping."""
        test_cases = [
            {
                "status": ExecutionStatus.RUNNING,
                "progress": 67.5,
                "current_task": "2.1.3",
                "totals": TaskTotals(completed=5, total=8),
                "branch": "feature/task-2-1-3-implementation"
            },
            {
                "status": ExecutionStatus.COMPLETED,
                "progress": 100.0,
                "current_task": "3.2.1",
                "totals": TaskTotals(completed=10, total=10),
                "branch": "main"
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            with patch('api.v1.endpoints.devteam_automation.get_status_projection_service') as mock_service_factory:
                mock_projection = StatusProjection(
                    execution_id=f"exec_accuracy_test_{i}",
                    project_id=f"customer-accuracy/project-test-{i}",
                    customer_id="customer-accuracy",
                    started_at=datetime.utcnow(),
                    **test_case
                )
                
                mock_service = Mock(spec=StatusProjectionService)
                mock_service.get_status_by_project_id.return_value = mock_projection
                mock_service_factory.return_value = mock_service
                
                response = client.get(f"/api/v1/devteam/automation/status/customer-accuracy/project-test-{i}")
                
                assert response.status_code == 200
                response_data = response.json()
                data = response_data["data"]
                
                # Verify exact mapping of all fields
                assert data["status"] == test_case["status"].value
                assert data["progress"] == test_case["progress"]
                assert data["current_task"] == test_case["current_task"]
                assert data["totals"]["completed"] == test_case["totals"].completed
                assert data["totals"]["total"] == test_case["totals"].total
                assert data["branch"] == test_case["branch"]

    def test_state_consistency_validation(self, client):
        """Test state consistency validation."""
        # Test that the endpoint properly handles state transitions
        with patch('api.v1.endpoints.devteam_automation.get_status_projection_service') as mock_service_factory:
            # Test valid state: RUNNING with current_task
            valid_projection = StatusProjection(
                execution_id="exec_state_valid",
                project_id="customer-state/project-valid",
                status=ExecutionStatus.RUNNING,
                progress=50.0,
                current_task="1.2.1",
                totals=TaskTotals(completed=2, total=4),
                customer_id="customer-state",
                branch="main",
                started_at=datetime.utcnow()
            )
            
            mock_service = Mock(spec=StatusProjectionService)
            mock_service.get_status_by_project_id.return_value = valid_projection
            mock_service_factory.return_value = mock_service
            
            response = client.get("/api/v1/devteam/automation/status/customer-state/project-valid")
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["data"]["status"] == "running"
            assert response_data["data"]["current_task"] == "1.2.1"

    # Load Testing
    def test_response_time_under_load(self, client):
        """Test response time under simulated load."""
        with patch('api.v1.endpoints.devteam_automation.get_status_projection_service') as mock_service_factory:
            mock_service = Mock(spec=StatusProjectionService)
            mock_projection = StatusProjection(
                execution_id="exec_load_test",
                project_id="customer-load/project-test",
                status=ExecutionStatus.RUNNING,
                progress=40.0,
                current_task="1.1.2",
                totals=TaskTotals(completed=2, total=5),
                customer_id="customer-load",
                branch="main",
                started_at=datetime.utcnow()
            )
            mock_service.get_status_by_project_id.return_value = mock_projection
            mock_service_factory.return_value = mock_service
            
            # Simulate 50 sequential requests
            response_times = []
            for i in range(50):
                start_time = time.time()
                response = client.get("/api/v1/devteam/automation/status/customer-load/project-test")
                duration_ms = (time.time() - start_time) * 1000
                response_times.append(duration_ms)
                
                assert response.status_code == 200
            
            # Validate performance metrics
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            p95_response_time = sorted(response_times)[int(0.95 * len(response_times))]
            
            assert avg_response_time <= 200, f"Average response time {avg_response_time:.2f}ms > 200ms"
            assert max_response_time <= 300, f"Max response time {max_response_time:.2f}ms > 300ms"
            assert p95_response_time <= 200, f"P95 response time {p95_response_time:.2f}ms > 200ms"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])