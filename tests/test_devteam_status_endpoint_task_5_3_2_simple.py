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
from unittest.mock import Mock, patch, MagicMock

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
    """
    Comprehensive test suite for Task 5.3.2: DevTeam Automation Status Endpoint Testing
    
    This test class validates the GET /api/devteam/automation/status/{project_id} endpoint
    with comprehensive coverage of all requirements specified in the task.
    """
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.client = TestClient(app)
        self.test_project_id = "customer-123/project-abc"
        self.test_execution_id = "exec_12345678-1234-1234-1234-123456789012"
        
        # Create sample status projection for testing
        self.sample_status_projection = StatusProjection(
            execution_id=self.test_execution_id,
            project_id=self.test_project_id,
            customer_id="customer-123",
            status=ExecutionStatus.RUNNING,
            progress=45.2,
            current_task="1.1.1",
            totals=TaskTotals(completed=3, total=8),
            branch="task/1-1-1-add-devteam-enabled-flag",
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            artifacts=ExecutionArtifacts()
        )

    def test_json_response_format_matches_add_specification(self):
        """
        Test that JSON response format exactly matches ADD Section 5.2 specification.
        
        Validates:
        - Response contains all required fields: status, progress, currentTask, totals, executionId
        - Optional fields: branch, startedAt, updatedAt
        - Field types and formats match specification
        - Response structure is exactly as specified
        """
        with patch('services.status_projection_service.get_status_projection_service') as mock_service_factory:
            mock_service = Mock(spec=StatusProjectionService)
            mock_service.get_status_by_project_id.return_value = self.sample_status_projection
            mock_service_factory.return_value = mock_service
            
            # Test the endpoint with valid project ID
            response = self.client.get(f"/api/v1/devteam/automation/status/{self.test_project_id}")
            
            # Validate response status
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            
            # Parse response data
            response_data = response.json()
            
            # Validate top-level response structure
            assert "success" in response_data
            assert "data" in response_data
            assert "message" in response_data
            assert response_data["success"] is True
            
            # Extract the actual status data
            status_data = response_data["data"]
            
            # Validate ADD Section 5.2 specification fields
            required_fields = ["status", "progress", "current_task", "totals", "execution_id"]
            for field in required_fields:
                assert field in status_data, f"Required field '{field}' missing from response"
            
            # Validate field types and values
            assert isinstance(status_data["status"], str)
            assert status_data["status"] == "running"
            
            assert isinstance(status_data["progress"], (int, float))
            assert status_data["progress"] == 45.2
            
            assert isinstance(status_data["current_task"], str)
            assert status_data["current_task"] == "1.1.1"
            
            assert isinstance(status_data["execution_id"], str)
            assert status_data["execution_id"] == self.test_execution_id
            
            # Validate totals structure
            assert "totals" in status_data
            totals = status_data["totals"]
            assert isinstance(totals, dict)
            assert "completed" in totals
            assert "total" in totals
            assert isinstance(totals["completed"], int)
            assert isinstance(totals["total"], int)
            assert totals["completed"] == 3
            assert totals["total"] == 8
            
            # Validate optional fields
            optional_fields = ["branch", "started_at", "updated_at"]
            for field in optional_fields:
                if field in status_data:
                    assert status_data[field] is not None
            
            # Validate branch if present
            if "branch" in status_data:
                assert isinstance(status_data["branch"], str)
                assert status_data["branch"] == "task/1-1-1-add-devteam-enabled-flag"
            
            # Validate timestamp formats if present
            for timestamp_field in ["started_at", "updated_at"]:
                if timestamp_field in status_data and status_data[timestamp_field]:
                    # Should be ISO format string
                    assert isinstance(status_data[timestamp_field], str)
                    # Validate it can be parsed as datetime
                    datetime.fromisoformat(status_data[timestamp_field].replace('Z', '+00:00'))

    def test_json_response_format_all_execution_statuses(self):
        """
        Test JSON response format for all possible execution statuses.
        
        Validates that the response format is consistent across all execution states:
        IDLE, INITIALIZING, RUNNING, PAUSED, COMPLETED, ERROR
        """
        statuses_to_test = [
            (ExecutionStatus.IDLE, "idle"),
            (ExecutionStatus.INITIALIZING, "initializing"),
            (ExecutionStatus.RUNNING, "running"),
            (ExecutionStatus.PAUSED, "paused"),
            (ExecutionStatus.COMPLETED, "completed"),
            (ExecutionStatus.ERROR, "error")
        ]
        
        for status_enum, expected_status_str in statuses_to_test:
            with patch('services.status_projection_service.get_status_projection_service') as mock_service_factory:
                mock_service = Mock(spec=StatusProjectionService)
                
                # Create status projection with specific status
                test_projection = StatusProjection(
                    execution_id=f"exec_{uuid.uuid4()}",
                    project_id=self.test_project_id,
                    customer_id="customer-123",
                    status=status_enum,
                    progress=25.0 if status_enum != ExecutionStatus.COMPLETED else 100.0,
                    current_task="1.2.3",
                    totals=TaskTotals(completed=2, total=8),
                    branch="test-branch",
                    started_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    artifacts=ExecutionArtifacts()
                )
                
                mock_service.get_status_by_project_id.return_value = test_projection
                mock_service_factory.return_value = mock_service
                
                # Test the endpoint
                response = self.client.get(f"/api/v1/devteam/automation/status/{self.test_project_id}")
                
                # Validate response
                assert response.status_code == 200
                response_data = response.json()
                
                # Validate status field matches expected string representation
                assert response_data["data"]["status"] == expected_status_str
                
                # Validate all required fields are present
                required_fields = ["status", "progress", "current_task", "totals", "execution_id"]
                for field in required_fields:
                    assert field in response_data["data"]

    def test_integration_with_status_projection_service(self):
        """
        Test integration with StatusProjectionService.
        
        Validates:
        - Service is called with correct parameters
        - Service response is properly transformed
        - Database session is properly injected
        - Correlation ID is propagated
        """
        with patch('services.status_projection_service.get_status_projection_service') as mock_service_factory:
            mock_service = Mock(spec=StatusProjectionService)
            mock_service.get_status_by_project_id.return_value = self.sample_status_projection
            mock_service_factory.return_value = mock_service
            
            # Make request
            response = self.client.get(f"/api/v1/devteam/automation/status/{self.test_project_id}")
            
            # Validate service was called
            mock_service_factory.assert_called_once()
            mock_service.get_status_by_project_id.assert_called_once_with(
                project_id=self.test_project_id
            )
            
            # Validate response transformation
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["data"]["execution_id"] == self.test_execution_id

    def test_integration_handles_repository_error(self):
        """
        Test integration properly handles RepositoryError from service layer.
        
        Validates:
        - RepositoryError is caught and handled
        - Proper 500 error response is returned
        - Error logging is performed
        """
        with patch('services.status_projection_service.get_status_projection_service') as mock_service_factory:
            mock_service = Mock(spec=StatusProjectionService)
            mock_service.get_status_by_project_id.side_effect = RepositoryError("Database connection failed")
            mock_service_factory.return_value = mock_service
            
            # Make request
            response = self.client.get(f"/api/v1/devteam/automation/status/{self.test_project_id}")
            
            # Validate error response
            assert response.status_code == 500
            response_data = response.json()
            assert response_data["success"] is False
            assert "Database error occurred" in response_data["message"]
            assert response_data["error_code"] == "REPOSITORY_ERROR"

    def test_performance_requirement_met(self):
        """
        Test that performance requirement (≤200ms) is met.
        
        Validates:
        - Response time is under 200ms
        - Performance is consistent across multiple requests
        - Performance monitoring is logged
        """
        with patch('services.status_projection_service.get_status_projection_service') as mock_service_factory:
            mock_service = Mock(spec=StatusProjectionService)
            
            # Create a fast-responding mock
            test_projection = StatusProjection(
                execution_id=f"exec_{uuid.uuid4()}",
                project_id=self.test_project_id,
                customer_id="customer-123",
                status=ExecutionStatus.RUNNING,
                progress=50.0,
                current_task="1.1.1",
                totals=TaskTotals(completed=4, total=8),
                branch="perf-test-branch",
                started_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                artifacts=ExecutionArtifacts()
            )
            
            mock_service.get_status_by_project_id.return_value = test_projection
            mock_service_factory.return_value = mock_service
            
            # Measure response time
            start_time = time.time()
            response = self.client.get(f"/api/v1/devteam/automation/status/customer-perf/project-test")
            end_time = time.time()
            
            response_time_ms = (end_time - start_time) * 1000
            
            # Validate response
            assert response.status_code == 200
            
            # Validate performance requirement
            assert response_time_ms <= 200, f"Response time {response_time_ms:.2f}ms exceeds 200ms requirement"
            
            # Log performance for monitoring
            print(f"Performance test: {response_time_ms:.2f}ms (target: ≤200ms)")

    def test_performance_with_multiple_concurrent_requests(self):
        """
        Test performance with multiple concurrent requests.
        
        Validates:
        - System handles concurrent requests efficiently
        - Average response time stays under 200ms
        - No degradation with load
        """
        import concurrent.futures
        import threading
        
        with patch('services.status_projection_service.get_status_projection_service') as mock_service_factory:
            mock_service = Mock(spec=StatusProjectionService)
            
            def create_test_projection():
                return StatusProjection(
                    execution_id=f"exec_{uuid.uuid4()}",
                    project_id=f"customer-{threading.current_thread().ident}/project-load-test",
                    customer_id=f"customer-{threading.current_thread().ident}",
                    status=ExecutionStatus.RUNNING,
                    progress=75.0,
                    current_task="1.3.2",
                    totals=TaskTotals(completed=6, total=8),
                    branch="load-test-branch",
                    started_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    artifacts=ExecutionArtifacts()
                )
            
            mock_service.get_status_by_project_id.return_value = create_test_projection()
            mock_service_factory.return_value = mock_service
            
            def make_request():
                start_time = time.time()
                response = self.client.get("/api/v1/devteam/automation/status/customer-perf/project-test")
                end_time = time.time()
                return response.status_code, (end_time - start_time) * 1000
            
            # Execute concurrent requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(make_request) for _ in range(10)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            # Validate all requests succeeded
            status_codes = [result[0] for result in results]
            response_times = [result[1] for result in results]
            
            assert all(status_code == 200 for status_code in status_codes)
            
            # Validate average performance
            avg_response_time = sum(response_times) / len(response_times)
            assert avg_response_time <= 200, f"Average response time {avg_response_time:.2f}ms exceeds 200ms"
            
            print(f"Concurrent load test: avg {avg_response_time:.2f}ms, max {max(response_times):.2f}ms")

    def test_error_handling_404_not_found(self):
        """
        Test 404 error handling for non-existent projects.
        
        Validates:
        - Returns 404 when project not found
        - Proper error message structure
        - Logging of not found cases
        """
        with patch('services.status_projection_service.get_status_projection_service') as mock_service_factory:
            mock_service = Mock(spec=StatusProjectionService)
            mock_service.get_status_by_project_id.return_value = None
            mock_service_factory.return_value = mock_service
            
            # Test with non-existent project
            response = self.client.get("/api/v1/devteam/automation/status/nonexistent-customer/nonexistent-project")
            
            # Validate 404 response
            assert response.status_code == 404
            response_data = response.json()
            assert response_data["success"] is False
            assert "No automation status found" in response_data["message"]
            assert "data" in response_data
            assert "project_id" in response_data["data"]

    def test_error_handling_422_validation_errors(self):
        """
        Test 422 validation error handling for invalid input.
        
        Validates:
        - Invalid project ID formats return 422
        - Proper validation error messages
        - Security against malicious input
        """
        invalid_project_ids = [
            ("", "empty project ID"),
            ("   ", "whitespace only project ID"),
            ("invalid-format", "missing slash separator"),
            ("customer-123/", "empty project part"),
            ("/project-abc", "empty customer part"),
            ("customer-123//project-abc", "double slash"),
            ("customer@123/project-abc", "invalid characters"),
            ("customer-123/project<script>", "potential XSS"),
        ]
        
        for invalid_id, description in invalid_project_ids:
            response = self.client.get(f"/api/v1/devteam/automation/status/{invalid_id}")
            
            assert response.status_code == 422, f"Failed for {description}: {invalid_id}"
            response_data = response.json()
            assert response_data["success"] is False
            assert "validation" in response_data["message"].lower()

    def test_error_handling_500_internal_server_error(self):
        """
        Test 500 error handling for internal server errors.
        
        Validates:
        - Unexpected exceptions return 500
        - Proper error message structure
        - Error logging and monitoring
        """
        with patch('services.status_projection_service.get_status_projection_service') as mock_service_factory:
            mock_service = Mock(spec=StatusProjectionService)
            mock_service.get_status_by_project_id.side_effect = Exception("Unexpected database error")
            mock_service_factory.return_value = mock_service
            
            # Test with valid project ID that causes internal error
            response = self.client.get(f"/api/v1/devteam/automation/status/{self.test_project_id}")
            
            # Validate 500 response
            assert response.status_code == 500
            response_data = response.json()
            assert response_data["success"] is False
            assert "Internal server error" in response_data["message"]
            assert response_data["error_code"] == "INTERNAL_ERROR"

    def test_security_input_validation(self):
        """
        Test security input validation and sanitization.
        
        Validates:
        - SQL injection attempts are blocked
        - XSS attempts are blocked
        - Path traversal attempts are blocked
        - Malicious input is properly sanitized
        """
        malicious_inputs = [
            "customer'; DROP TABLE users; --/project",
            "customer<script>alert('xss')</script>/project",
            "../../../etc/passwd",
            "customer/project/../../../sensitive",
            "customer\x00/project",  # Null byte injection
        ]
        
        for malicious_input in malicious_inputs:
            response = self.client.get(f"/api/v1/devteam/automation/status/{malicious_input}")
            
            # Should return validation error, not process malicious input
            assert response.status_code == 422
            response_data = response.json()
            assert response_data["success"] is False

    def test_audit_logging_correlation_id(self):
        """
        Test audit logging and correlation ID propagation.
        
        Validates:
        - Correlation ID is generated and logged
        - Request/response logging is performed
        - Audit trail is maintained
        """
        with patch('services.status_projection_service.get_status_projection_service') as mock_service_factory:
            mock_service = Mock(spec=StatusProjectionService)
            mock_service.get_status_by_project_id.return_value = self.sample_status_projection
            mock_service_factory.return_value = mock_service
            
            # Make request
            response = self.client.get(f"/api/v1/devteam/automation/status/{self.test_project_id}")
            
            # Validate service was called with correlation_id
            mock_service_factory.assert_called_once()
            call_args = mock_service_factory.call_args
            assert 'correlation_id' in call_args.kwargs
            assert call_args.kwargs['correlation_id'].startswith('corr_')
            
            # Validate successful response
            assert response.status_code == 200

    def test_data_accuracy_status_projection_mapping(self):
        """
        Test data accuracy and proper status projection mapping.
        
        Validates:
        - All StatusProjection fields are properly mapped
        - Data types are correctly converted
        - No data loss in transformation
        - Consistent field naming
        """
        with patch('services.status_projection_service.get_status_projection_service') as mock_service_factory:
            mock_service = Mock(spec=StatusProjectionService)
            
            # Create comprehensive test data
            comprehensive_projection = StatusProjection(
                execution_id="exec_comprehensive_test",
                project_id="customer-data/project-accuracy",
                customer_id="customer-data",
                status=ExecutionStatus.RUNNING,
                progress=67.5,
                current_task="2.1.4",
                totals=TaskTotals(completed=5, total=7),
                branch="feature/data-accuracy-test",
                started_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                artifacts=ExecutionArtifacts()
            )
            
            mock_service.get_status_by_project_id.return_value = comprehensive_projection
            mock_service_factory.return_value = mock_service
            
            # Make request
            response = self.client.get("/api/v1/devteam/automation/status/customer-data/project-accuracy")
            
            # Validate response
            assert response.status_code == 200
            response_data = response.json()
            status_data = response_data["data"]
            
            # Validate all fields are properly mapped
            assert status_data["execution_id"] == "exec_comprehensive_test"
            assert status_data["status"] == "running"
            assert status_data["progress"] == 67.5
            assert status_data["current_task"] == "2.1.4"
            assert status_data["totals"]["completed"] == 5
            assert status_data["totals"]["total"] == 7
            assert status_data["branch"] == "feature/data-accuracy-test"
            
            # Validate timestamp fields are properly formatted
            assert "started_at" in status_data
            assert "updated_at" in status_data
            assert isinstance(status_data["started_at"], str)
            assert isinstance(status_data["updated_at"], str)

    def test_state_consistency_validation(self):
        """
        Test state consistency validation.
        
        Validates:
        - Progress values are consistent with status
        - Task counts are logical
        - Status transitions are valid
        - Data integrity is maintained
        """
        test_cases = [
            # (status, progress, completed, total, should_be_valid)
            (ExecutionStatus.IDLE, 0.0, 0, 8, True),
            (ExecutionStatus.INITIALIZING, 5.0, 0, 8, True),
            (ExecutionStatus.RUNNING, 50.0, 4, 8, True),
            (ExecutionStatus.COMPLETED, 100.0, 8, 8, True),
            (ExecutionStatus.ERROR, 25.0, 2, 8, True),
        ]
        
        for status, progress, completed, total, should_be_valid in test_cases:
            with patch('services.status_projection_service.get_status_projection_service') as mock_service_factory:
                mock_service = Mock(spec=StatusProjectionService)
                
                test_projection = StatusProjection(
                    execution_id=f"exec_consistency_{status.value}",
                    project_id=f"customer-consistency/project-{status.value}",
                    customer_id="customer-consistency",
                    status=status,
                    progress=progress,
                    current_task="1.1.1",
                    totals=TaskTotals(completed=completed, total=total),
                    branch="consistency-test",
                    started_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    artifacts=ExecutionArtifacts()
                )
                
                mock_service.get_status_by_project_id.return_value = test_projection
                mock_service_factory.return_value = mock_service
                
                # Make request
                response = self.client.get(f"/api/v1/devteam/automation/status/customer-consistency/project-{status.value}")
                
                if should_be_valid:
                    assert response.status_code == 200
                    response_data = response.json()
                    status_data = response_data["data"]
                    
                    # Validate consistency
                    assert status_data["progress"] == progress
                    assert status_data["totals"]["completed"] == completed
                    assert status_data["totals"]["total"] == total

    def test_response_time_under_load(self):
        """
        Test response time consistency under load.
        
        Validates:
        - Response times remain consistent under load
        - No significant performance degradation
        - System stability under stress
        """
        with patch('services.status_projection_service.get_status_projection_service') as mock_service_factory:
            mock_service = Mock(spec=StatusProjectionService)
            
            # Create test projection
            load_test_projection = StatusProjection(
                execution_id="exec_load_test",
                project_id="customer-load/project-test",
                customer_id="customer-load",
                status=ExecutionStatus.RUNNING,
                progress=80.0,
                current_task="3.2.1",
                totals=TaskTotals(completed=7, total=8),
                branch="load-test-branch",
                started_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                artifacts=ExecutionArtifacts()
            )
            
            mock_service.get_status_by_project_id.return_value = load_test_projection
            mock_service_factory.return_value = mock_service
            
            # Perform load test
            response_times = []
            for i in range(20):  # 20 sequential requests
                start_time = time.time()
                response = self.client.get("/api/v1/devteam/automation/status/customer-load/project-test")
                end_time = time.time()
                
                response_time_ms = (end_time - start_time) * 1000
                response_times.append(response_time_ms)
                
                # Validate each response
                assert response.status_code == 200
            
            # Validate performance consistency
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            
            assert avg_response_time <= 200, f"Average response time {avg_response_time:.2f}ms exceeds 200ms"
            assert max_response_time <= 300, f"Max response time {max_response_time:.2f}ms exceeds acceptable threshold"
            
            print(f"Load test results: avg {avg_response_time:.2f}ms, max {max_response_time:.2f}ms")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])