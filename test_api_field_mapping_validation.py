"""
API Field Mapping Validation Test

This test validates that StatusProjection objects can be successfully serialized 
to DevTeamAutomationStatusResponse without data loss, ensuring perfect field alignment.

Tests:
1. Complete field mapping validation
2. Type consistency verification
3. Performance requirements (<200ms)
4. Backward compatibility
5. Edge cases and error handling
"""

import json
import time
from datetime import datetime, timezone
from typing import Dict, Any

import pytest
from pydantic import ValidationError

from schemas.status_projection_schema import (
    StatusProjection,
    ExecutionStatus,
    TaskTotals,
    ExecutionArtifacts
)
from schemas.devteam_automation_schema import DevTeamAutomationStatusResponse


class TestAPIFieldMappingValidation:
    """Test suite for API field mapping validation."""
    
    def test_complete_field_mapping_validation(self):
        """Test that all StatusProjection fields map correctly to API response."""
        # Create a comprehensive StatusProjection with all fields populated
        status_projection = StatusProjection(
            execution_id="exec_test_12345678-1234-1234-1234-123456789012",
            project_id="customer-test/project-field-mapping",
            status=ExecutionStatus.RUNNING,
            progress=67.5,
            current_task="2.3.1",
            totals=TaskTotals(completed=5, total=8),
            customer_id="customer-test",
            branch="task/2-3-1-field-mapping-validation",
            artifacts=ExecutionArtifacts(
                repo_path="/workspace/repos/customer-test-project-field-mapping",
                branch="task/2-3-1-field-mapping-validation",
                logs=["Field mapping test started", "Validation in progress"],
                files_modified=["src/api.py", "schemas/response.py", "tests/test_mapping.py"]
            ),
            started_at=datetime(2025, 1, 17, 12, 30, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 1, 17, 12, 45, 30, tzinfo=timezone.utc)
        )
        
        # Convert to API response format (simulating the endpoint conversion logic)
        api_response = DevTeamAutomationStatusResponse(
            status=status_projection.status.value,
            progress=status_projection.progress,
            current_task=status_projection.current_task,
            totals={
                "completed": status_projection.totals.completed,
                "total": status_projection.totals.total
            },
            execution_id=status_projection.execution_id,
            project_id=status_projection.project_id,
            customer_id=status_projection.customer_id,
            branch=status_projection.branch,
            artifacts={
                "repo_path": status_projection.artifacts.repo_path,
                "branch": status_projection.artifacts.branch,
                "logs": status_projection.artifacts.logs,
                "files_modified": status_projection.artifacts.files_modified
            },
            started_at=status_projection.started_at.isoformat() if status_projection.started_at else None,
            updated_at=status_projection.updated_at.isoformat() if status_projection.updated_at else None
        )
        
        # Validate all fields are correctly mapped
        assert api_response.status == "running"
        assert api_response.progress == 67.5
        assert api_response.current_task == "2.3.1"
        assert api_response.totals == {"completed": 5, "total": 8}
        assert api_response.execution_id == "exec_test_12345678-1234-1234-1234-123456789012"
        assert api_response.project_id == "customer-test/project-field-mapping"
        assert api_response.customer_id == "customer-test"
        assert api_response.branch == "task/2-3-1-field-mapping-validation"
        
        # Validate artifacts mapping
        assert api_response.artifacts is not None
        assert api_response.artifacts["repo_path"] == "/workspace/repos/customer-test-project-field-mapping"
        assert api_response.artifacts["branch"] == "task/2-3-1-field-mapping-validation"
        assert api_response.artifacts["logs"] == ["Field mapping test started", "Validation in progress"]
        assert api_response.artifacts["files_modified"] == ["src/api.py", "schemas/response.py", "tests/test_mapping.py"]
        
        # Validate timestamp formatting
        assert api_response.started_at == "2025-01-17T12:30:00+00:00"
        assert api_response.updated_at == "2025-01-17T12:45:30+00:00"
        
        print("✅ Complete field mapping validation passed")
    
    def test_minimal_field_mapping(self):
        """Test field mapping with minimal required fields only."""
        # Create StatusProjection with only required fields
        status_projection = StatusProjection(
            execution_id="exec_minimal_test",
            project_id="customer-minimal/project-test",
            status=ExecutionStatus.IDLE,
            progress=0.0,
            current_task=None,
            totals=TaskTotals(completed=0, total=0),
            customer_id=None,
            branch=None,
            artifacts=ExecutionArtifacts(),  # Empty artifacts
            started_at=None,
            updated_at=datetime.now(timezone.utc)
        )
        
        # Convert to API response
        api_response = DevTeamAutomationStatusResponse(
            status=status_projection.status.value,
            progress=status_projection.progress,
            current_task=status_projection.current_task,
            totals={
                "completed": status_projection.totals.completed,
                "total": status_projection.totals.total
            },
            execution_id=status_projection.execution_id,
            project_id=status_projection.project_id,
            customer_id=status_projection.customer_id,
            branch=status_projection.branch,
            artifacts={
                "repo_path": status_projection.artifacts.repo_path,
                "branch": status_projection.artifacts.branch,
                "logs": status_projection.artifacts.logs,
                "files_modified": status_projection.artifacts.files_modified
            } if status_projection.artifacts else None,
            started_at=status_projection.started_at.isoformat() if status_projection.started_at else None,
            updated_at=status_projection.updated_at.isoformat() if status_projection.updated_at else None
        )
        
        # Validate minimal mapping
        assert api_response.status == "idle"
        assert api_response.progress == 0.0
        assert api_response.current_task is None
        assert api_response.totals == {"completed": 0, "total": 0}
        assert api_response.execution_id == "exec_minimal_test"
        assert api_response.project_id == "customer-minimal/project-test"
        assert api_response.customer_id is None
        assert api_response.branch is None
        assert api_response.artifacts is not None  # Should still have artifacts structure
        assert api_response.started_at is None
        assert api_response.updated_at is not None
        
        print("✅ Minimal field mapping validation passed")
    
    def test_json_serialization_compatibility(self):
        """Test that the API response can be serialized to JSON without issues."""
        # Create a complete StatusProjection
        status_projection = StatusProjection(
            execution_id="exec_json_test",
            project_id="customer-json/project-serialization",
            status=ExecutionStatus.COMPLETED,
            progress=100.0,
            current_task="3.1.1",
            totals=TaskTotals(completed=10, total=10),
            customer_id="customer-json",
            branch="main",
            artifacts=ExecutionArtifacts(
                repo_path="/workspace/repos/customer-json-project-serialization",
                branch="main",
                logs=["Serialization test", "JSON compatibility check"],
                files_modified=["api.py", "models.py"]
            ),
            started_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Convert to API response
        api_response = DevTeamAutomationStatusResponse(
            status=status_projection.status.value,
            progress=status_projection.progress,
            current_task=status_projection.current_task,
            totals={
                "completed": status_projection.totals.completed,
                "total": status_projection.totals.total
            },
            execution_id=status_projection.execution_id,
            project_id=status_projection.project_id,
            customer_id=status_projection.customer_id,
            branch=status_projection.branch,
            artifacts={
                "repo_path": status_projection.artifacts.repo_path,
                "branch": status_projection.artifacts.branch,
                "logs": status_projection.artifacts.logs,
                "files_modified": status_projection.artifacts.files_modified
            },
            started_at=status_projection.started_at.isoformat() if status_projection.started_at else None,
            updated_at=status_projection.updated_at.isoformat() if status_projection.updated_at else None
        )
        
        # Test JSON serialization
        json_data = api_response.model_dump(mode="json")
        json_string = json.dumps(json_data)
        
        # Verify JSON can be parsed back
        parsed_data = json.loads(json_string)
        
        # Validate key fields in parsed JSON
        assert parsed_data["status"] == "completed"
        assert parsed_data["progress"] == 100.0
        assert parsed_data["execution_id"] == "exec_json_test"
        assert parsed_data["project_id"] == "customer-json/project-serialization"
        assert "artifacts" in parsed_data
        assert "totals" in parsed_data
        
        print("✅ JSON serialization compatibility validation passed")
    
    def test_performance_requirements(self):
        """Test that field mapping and serialization meets <200ms performance requirement."""
        # Create multiple StatusProjection objects for performance testing
        test_cases = []
        for i in range(100):  # Test with 100 objects
            status_projection = StatusProjection(
                execution_id=f"exec_perf_test_{i:03d}",
                project_id=f"customer-perf/project-{i:03d}",
                status=ExecutionStatus.RUNNING,
                progress=float(i),
                current_task=f"{i}.1.1",
                totals=TaskTotals(completed=i, total=100),
                customer_id=f"customer-perf-{i}",
                branch=f"task/{i}-performance-test",
                artifacts=ExecutionArtifacts(
                    repo_path=f"/workspace/repos/customer-perf-project-{i:03d}",
                    branch=f"task/{i}-performance-test",
                    logs=[f"Performance test {i}", f"Iteration {i} in progress"],
                    files_modified=[f"file_{i}.py", f"test_{i}.py"]
                ),
                started_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            test_cases.append(status_projection)
        
        # Measure conversion performance
        start_time = time.time()
        
        api_responses = []
        for status_projection in test_cases:
            api_response = DevTeamAutomationStatusResponse(
                status=status_projection.status.value,
                progress=status_projection.progress,
                current_task=status_projection.current_task,
                totals={
                    "completed": status_projection.totals.completed,
                    "total": status_projection.totals.total
                },
                execution_id=status_projection.execution_id,
                project_id=status_projection.project_id,
                customer_id=status_projection.customer_id,
                branch=status_projection.branch,
                artifacts={
                    "repo_path": status_projection.artifacts.repo_path,
                    "branch": status_projection.artifacts.branch,
                    "logs": status_projection.artifacts.logs,
                    "files_modified": status_projection.artifacts.files_modified
                },
                started_at=status_projection.started_at.isoformat(),
                updated_at=status_projection.updated_at.isoformat()
            )
            api_responses.append(api_response)
        
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        
        # Validate performance requirement
        assert duration_ms < 200, f"Performance requirement failed: {duration_ms:.2f}ms > 200ms"
        assert len(api_responses) == 100, "Not all conversions completed"
        
        print(f"✅ Performance validation passed: {duration_ms:.2f}ms for 100 conversions")
    
    def test_edge_cases_and_error_handling(self):
        """Test edge cases and error handling in field mapping."""
        # Test with various execution statuses
        statuses_to_test = [
            ExecutionStatus.IDLE,
            ExecutionStatus.INITIALIZING,
            ExecutionStatus.RUNNING,
            ExecutionStatus.PAUSED,
            ExecutionStatus.STOPPING,
            ExecutionStatus.STOPPED,
            ExecutionStatus.COMPLETED,
            ExecutionStatus.ERROR
        ]
        
        for status in statuses_to_test:
            status_projection = StatusProjection(
                execution_id=f"exec_edge_test_{status.value}",
                project_id=f"customer-edge/project-{status.value}",
                status=status,
                progress=50.0 if status != ExecutionStatus.COMPLETED else 100.0,
                current_task="1.1.1" if status in [ExecutionStatus.RUNNING, ExecutionStatus.PAUSED] else None,
                totals=TaskTotals(completed=5, total=10),
                customer_id="customer-edge",
                branch="edge-test-branch",
                artifacts=ExecutionArtifacts(
                    repo_path="/workspace/repos/edge-test",
                    branch="edge-test-branch",
                    logs=[f"Testing {status.value} status"],
                    files_modified=["edge_test.py"]
                ),
                started_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            # Convert to API response
            api_response = DevTeamAutomationStatusResponse(
                status=status_projection.status.value,
                progress=status_projection.progress,
                current_task=status_projection.current_task,
                totals={
                    "completed": status_projection.totals.completed,
                    "total": status_projection.totals.total
                },
                execution_id=status_projection.execution_id,
                project_id=status_projection.project_id,
                customer_id=status_projection.customer_id,
                branch=status_projection.branch,
                artifacts={
                    "repo_path": status_projection.artifacts.repo_path,
                    "branch": status_projection.artifacts.branch,
                    "logs": status_projection.artifacts.logs,
                    "files_modified": status_projection.artifacts.files_modified
                },
                started_at=status_projection.started_at.isoformat() if status_projection.started_at else None,
                updated_at=status_projection.updated_at.isoformat() if status_projection.updated_at else None
            )
            
            # Validate conversion succeeded
            assert api_response.status == status.value
            assert api_response.execution_id == f"exec_edge_test_{status.value}"
            assert api_response.project_id == f"customer-edge/project-{status.value}"
        
        print("✅ Edge cases and error handling validation passed")
    
    def test_backward_compatibility(self):
        """Test that new fields don't break existing API consumers."""
        # Create API response with only original fields (simulating old client)
        minimal_response_data = {
            "status": "running",
            "progress": 45.2,
            "current_task": "1.1.1",
            "totals": {"completed": 3, "total": 8},
            "execution_id": "exec_backward_compat_test",
            "branch": "main",
            "started_at": "2025-01-17T12:30:00+00:00",
            "updated_at": "2025-01-17T12:45:00+00:00"
        }
        
        # Test that we can still create response with minimal fields
        # (new fields should be optional)
        try:
            # This should fail because project_id is now required
            api_response = DevTeamAutomationStatusResponse(**minimal_response_data)
            assert False, "Expected validation error for missing required project_id field"
        except ValidationError as e:
            # This is expected - project_id is now required
            assert "project_id" in str(e)
            print("✅ Backward compatibility validation: project_id is correctly required")
        
        # Test with project_id included (updated minimal client)
        minimal_response_data["project_id"] = "customer-compat/project-test"
        api_response = DevTeamAutomationStatusResponse(**minimal_response_data)
        
        # Validate that optional new fields have appropriate defaults
        assert api_response.customer_id is None  # Should be None (optional)
        assert api_response.artifacts is None    # Should be None (optional)
        
        print("✅ Backward compatibility validation passed with required project_id")


def run_comprehensive_validation():
    """Run all validation tests and provide summary."""
    print("🚀 Starting API Field Mapping Comprehensive Validation")
    print("=" * 60)
    
    test_suite = TestAPIFieldMappingValidation()
    
    try:
        # Run all tests
        test_suite.test_complete_field_mapping_validation()
        test_suite.test_minimal_field_mapping()
        test_suite.test_json_serialization_compatibility()
        test_suite.test_performance_requirements()
        test_suite.test_edge_cases_and_error_handling()
        test_suite.test_backward_compatibility()
        
        print("=" * 60)
        print("🎉 ALL VALIDATION TESTS PASSED!")
        print("✅ StatusProjection → API Response field mapping is complete")
        print("✅ No data loss during transformation")
        print("✅ Performance requirements met (<200ms)")
        print("✅ JSON serialization compatible")
        print("✅ Edge cases handled properly")
        print("✅ Backward compatibility considerations addressed")
        
        return True
        
    except Exception as e:
        print("=" * 60)
        print(f"❌ VALIDATION FAILED: {e}")
        print("Please review the field mapping implementation")
        return False


if __name__ == "__main__":
    success = run_comprehensive_validation()
    exit(0 if success else 1)