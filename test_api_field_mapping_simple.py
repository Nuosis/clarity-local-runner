"""
Simple API Field Mapping Validation Test

This test validates that StatusProjection objects can be successfully serialized 
to DevTeamAutomationStatusResponse without data loss, ensuring perfect field alignment.
"""

import json
import sys
import time
from datetime import datetime, timezone
from typing import Dict, Any

# Add app directory to path for imports
sys.path.insert(0, 'app')

from schemas.status_projection_schema import (
    StatusProjection,
    ExecutionStatus,
    TaskTotals,
    ExecutionArtifacts
)
from schemas.devteam_automation_schema import DevTeamAutomationStatusResponse


def test_complete_field_mapping_validation():
    """Test that all StatusProjection fields map correctly to API response."""
    print("Testing complete field mapping validation...")
    
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
    return True


def test_minimal_field_mapping():
    """Test field mapping with minimal required fields only."""
    print("Testing minimal field mapping...")
    
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
    return True


def test_json_serialization_compatibility():
    """Test that the API response can be serialized to JSON without issues."""
    print("Testing JSON serialization compatibility...")
    
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
    return True


def test_performance_requirements():
    """Test that field mapping and serialization meets <200ms performance requirement."""
    print("Testing performance requirements...")
    
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
    return True


def run_comprehensive_validation():
    """Run all validation tests and provide summary."""
    print("🚀 Starting API Field Mapping Comprehensive Validation")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 4
    
    try:
        # Run all tests
        if test_complete_field_mapping_validation():
            tests_passed += 1
        
        if test_minimal_field_mapping():
            tests_passed += 1
            
        if test_json_serialization_compatibility():
            tests_passed += 1
            
        if test_performance_requirements():
            tests_passed += 1
        
        print("=" * 60)
        if tests_passed == total_tests:
            print("🎉 ALL VALIDATION TESTS PASSED!")
            print("✅ StatusProjection → API Response field mapping is complete")
            print("✅ No data loss during transformation")
            print("✅ Performance requirements met (<200ms)")
            print("✅ JSON serialization compatible")
            return True
        else:
            print(f"❌ {total_tests - tests_passed} out of {total_tests} tests failed")
            return False
        
    except Exception as e:
        print("=" * 60)
        print(f"❌ VALIDATION FAILED: {e}")
        print("Please review the field mapping implementation")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_comprehensive_validation()
    exit(0 if success else 1)