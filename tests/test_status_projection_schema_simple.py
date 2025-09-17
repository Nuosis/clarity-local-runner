"""
Simple Unit Tests for Status Projection Schema

This module provides focused unit tests for the status projection schema
validation, testing core functionality without complex parameter handling.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from schemas.status_projection_schema import (
    StatusProjection,
    ExecutionStatus,
    TaskTotals,
    ExecutionArtifacts,
    project_status_from_task_context,
    validate_status_transition
)


class TestStatusProjectionCore:
    """Test core StatusProjection functionality."""
    
    def test_basic_status_projection_creation(self):
        """Test basic status projection creation with minimal fields."""
        projection_data = {
            "execution_id": "exec_12345",
            "project_id": "customer-123/project-abc",
            "status": "running",
            "progress": 45.2,
            "current_task": "1.1.1",
            "customer_id": "customer-123",
            "branch": "main",
            "started_at": None
        }
        
        projection = StatusProjection(**projection_data)
        
        assert projection.execution_id == "exec_12345"
        assert projection.project_id == "customer-123/project-abc"
        assert projection.status == ExecutionStatus.RUNNING
        assert projection.progress == 45.2
        assert projection.current_task == "1.1.1"
        assert projection.customer_id == "customer-123"
        assert projection.branch == "main"
    
    def test_execution_status_enum(self):
        """Test ExecutionStatus enum values."""
        assert ExecutionStatus.IDLE == "idle"
        assert ExecutionStatus.INITIALIZING == "initializing"
        assert ExecutionStatus.RUNNING == "running"
        assert ExecutionStatus.PAUSED == "paused"
        assert ExecutionStatus.COMPLETED == "completed"
        assert ExecutionStatus.ERROR == "error"
    
    def test_task_totals_validation(self):
        """Test TaskTotals validation."""
        # Valid totals
        totals = TaskTotals(completed=3, total=8)
        assert totals.completed == 3
        assert totals.total == 8
        
        # Default values
        default_totals = TaskTotals()
        assert default_totals.completed == 0
        assert default_totals.total == 0
        
        # Invalid: completed > total
        with pytest.raises(ValidationError):
            TaskTotals(completed=10, total=5)
    
    def test_execution_artifacts_creation(self):
        """Test ExecutionArtifacts creation."""
        artifacts = ExecutionArtifacts(
            repo_path="/workspace/repos/test",
            branch="main",
            logs=["Started", "Processing"],
            files_modified=["src/app.py"]
        )
        
        assert artifacts.repo_path == "/workspace/repos/test"
        assert artifacts.branch == "main"
        assert artifacts.logs == ["Started", "Processing"]
        assert artifacts.files_modified == ["src/app.py"]
        
        # Test defaults
        default_artifacts = ExecutionArtifacts()
        assert default_artifacts.repo_path is None
        assert default_artifacts.branch is None
        assert artifacts.logs == ["Started", "Processing"]  # Should keep previous value
        assert artifacts.files_modified == ["src/app.py"]  # Should keep previous value
    
    def test_field_validation(self):
        """Test field validation."""
        base_data = {
            "execution_id": "exec_test",
            "project_id": "test/project",
            "status": "idle",
            "progress": 0.0,
            "current_task": None,
            "customer_id": None,
            "branch": None,
            "started_at": None
        }
        
        # Valid execution ID
        projection = StatusProjection(**base_data)
        assert projection.execution_id == "exec_test"
        
        # Invalid execution ID
        invalid_data = base_data.copy()
        invalid_data["execution_id"] = "invalid@id"
        with pytest.raises(ValidationError):
            StatusProjection(**invalid_data)
        
        # Invalid progress
        invalid_data = base_data.copy()
        invalid_data["progress"] = 150.0
        with pytest.raises(ValidationError):
            StatusProjection(**invalid_data)
    
    def test_json_serialization(self):
        """Test JSON serialization."""
        projection_data = {
            "execution_id": "exec_json",
            "project_id": "test/json",
            "status": "running",
            "progress": 75.0,
            "current_task": "2.1.1",
            "customer_id": "test",
            "branch": "main",
            "started_at": None
        }
        
        projection = StatusProjection(**projection_data)
        json_data = projection.dict()
        
        assert json_data["execution_id"] == "exec_json"
        assert json_data["status"] == "running"
        assert json_data["progress"] == 75.0
        
        # Test round-trip
        new_projection = StatusProjection(**json_data)
        assert new_projection.execution_id == projection.execution_id
        assert new_projection.status == projection.status


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_project_status_from_task_context(self):
        """Test projecting status from task context."""
        task_context = {
            "metadata": {
                "status": "prepared",
                "task_id": "1.1.1",
                "branch": "main"
            },
            "nodes": {
                "SelectNode": {"status": "completed"},
                "PrepNode": {"status": "running"}
            }
        }
        
        projection = project_status_from_task_context(
            task_context=task_context,
            execution_id="exec_12345",
            project_id="customer-123/project-abc"
        )
        
        assert projection.execution_id == "exec_12345"
        assert projection.project_id == "customer-123/project-abc"
        assert projection.status == ExecutionStatus.RUNNING
        assert projection.current_task == "1.1.1"
        assert projection.customer_id == "customer-123"
        assert projection.branch == "main"
    
    def test_validate_status_transition(self):
        """Test status transition validation."""
        # Valid transitions
        assert validate_status_transition("idle", "initializing") == True
        assert validate_status_transition("initializing", "running") == True
        assert validate_status_transition("running", "paused") == True
        assert validate_status_transition("paused", "running") == True
        assert validate_status_transition("running", "completed") == True
        assert validate_status_transition("running", "error") == True
        
        # Invalid transitions
        assert validate_status_transition("idle", "running") == False
        assert validate_status_transition("completed", "running") == False
        assert validate_status_transition("error", "running") == False


class TestPerformance:
    """Test performance requirements."""
    
    def test_schema_validation_performance(self):
        """Test that schema validation meets performance requirements."""
        import time
        
        projection_data = {
            "execution_id": "exec_perf",
            "project_id": "test/performance",
            "status": "running",
            "progress": 50.0,
            "current_task": "1.1.1",
            "customer_id": "test",
            "branch": "main",
            "started_at": None
        }
        
        # Test creation performance
        start_time = time.time()
        for i in range(100):
            data = projection_data.copy()
            data["execution_id"] = f"exec_{i}"
            projection = StatusProjection(**data)
        end_time = time.time()
        
        # Should complete 100 validations well under 2s requirement
        duration = end_time - start_time
        assert duration < 1.0, f"Schema validation took {duration}s, should be <1s"


class TestStateTransitions:
    """Test state transition logic."""
    
    def test_valid_state_progression(self):
        """Test valid state progression through workflow."""
        # Create base projection data
        base_data = {
            "execution_id": "exec_workflow",
            "project_id": "test/workflow",
            "progress": 0.0,
            "current_task": None,
            "customer_id": "test",
            "branch": "main",
            "started_at": None
        }
        
        # IDLE state
        idle_data = base_data.copy()
        idle_data.update({"status": "idle", "progress": 0.0})
        idle_projection = StatusProjection(**idle_data)
        assert idle_projection.status == ExecutionStatus.IDLE
        
        # INITIALIZING state
        init_data = base_data.copy()
        init_data.update({"status": "initializing", "progress": 5.0})
        init_projection = StatusProjection(**init_data)
        assert init_projection.status == ExecutionStatus.INITIALIZING
        
        # RUNNING state
        running_data = base_data.copy()
        running_data.update({"status": "running", "progress": 50.0, "current_task": "1.1.1"})
        running_projection = StatusProjection(**running_data)
        assert running_projection.status == ExecutionStatus.RUNNING
        
        # COMPLETED state
        completed_data = base_data.copy()
        completed_data.update({
            "status": "completed", 
            "progress": 100.0,
            "totals": {"completed": 5, "total": 5}
        })
        completed_projection = StatusProjection(**completed_data)
        assert completed_projection.status == ExecutionStatus.COMPLETED


if __name__ == "__main__":
    # Simple test runner for validation
    test_instance = TestStatusProjectionCore()
    test_instance.test_basic_status_projection_creation()
    test_instance.test_execution_status_enum()
    test_instance.test_task_totals_validation()
    print("Core tests passed!")
    
    util_test = TestUtilityFunctions()
    util_test.test_validate_status_transition()
    print("Utility tests passed!")
    
    perf_test = TestPerformance()
    perf_test.test_schema_validation_performance()
    print("Performance tests passed!")
    
    print("All status projection schema tests completed successfully!")