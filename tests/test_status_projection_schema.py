"""
Unit Tests for Status Projection Schema

This module provides comprehensive unit tests for the status projection schema
validation, including field validation, state transition validation, and
error handling scenarios.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from schemas.status_projection_schema import (
    StatusProjection,
    ExecutionStatus,
    TaskTotals,
    ExecutionArtifacts,
    StatusProjectionError,
    project_status_from_task_context,
    validate_status_transition
)


class TestExecutionStatus:
    """Test ExecutionStatus enum values."""
    
    def test_execution_status_values(self):
        """Test that all expected status values are available."""
        assert ExecutionStatus.IDLE == "idle"
        assert ExecutionStatus.INITIALIZING == "initializing"
        assert ExecutionStatus.RUNNING == "running"
        assert ExecutionStatus.PAUSED == "paused"
        assert ExecutionStatus.COMPLETED == "completed"
        assert ExecutionStatus.ERROR == "error"


class TestTaskTotals:
    """Test TaskTotals model validation."""
    
    def test_valid_task_totals(self):
        """Test valid task totals creation."""
        totals = TaskTotals(completed=3, total=8)
        assert totals.completed == 3
        assert totals.total == 8
    
    def test_default_task_totals(self):
        """Test default task totals values."""
        totals = TaskTotals()
        assert totals.completed == 0
        assert totals.total == 0
    
    def test_completed_exceeds_total_validation(self):
        """Test validation when completed exceeds total."""
        with pytest.raises(ValidationError) as exc_info:
            TaskTotals(completed=10, total=5)
        
        assert "Completed tasks cannot exceed total tasks" in str(exc_info.value)
    
    def test_negative_values_validation(self):
        """Test validation of negative values."""
        with pytest.raises(ValidationError):
            TaskTotals(completed=-1, total=5)
        
        with pytest.raises(ValidationError):
            TaskTotals(completed=3, total=-1)


class TestExecutionArtifacts:
    """Test ExecutionArtifacts model validation."""
    
    def test_valid_execution_artifacts(self):
        """Test valid execution artifacts creation."""
        artifacts = ExecutionArtifacts(
            repo_path="/workspace/repos/test",
            branch="main",
            logs=["Started", "Processing"],
            files_modified=["src/app.py", "README.md"]
        )
        
        assert artifacts.repo_path == "/workspace/repos/test"
        assert artifacts.branch == "main"
        assert artifacts.logs == ["Started", "Processing"]
        assert artifacts.files_modified == ["src/app.py", "README.md"]
    
    def test_default_execution_artifacts(self):
        """Test default execution artifacts values."""
        artifacts = ExecutionArtifacts()
        assert artifacts.repo_path is None
        assert artifacts.branch is None
        assert artifacts.logs == []
        assert artifacts.files_modified == []
    
    def test_branch_validation(self):
        """Test branch name validation."""
        # Valid branch names
        valid_branches = ["main", "feature/test", "task/1-1-1", "dev_branch"]
        for branch in valid_branches:
            artifacts = ExecutionArtifacts(branch=branch)
            assert artifacts.branch == branch
        
        # Invalid branch names
        with pytest.raises(ValidationError):
            ExecutionArtifacts(branch="invalid@branch")
        
        # Empty branch should be None
        artifacts = ExecutionArtifacts(branch="")
        assert artifacts.branch is None


class TestStatusProjection:
    """Test StatusProjection model validation."""
    
    def test_valid_status_projection(self):
        """Test valid status projection creation."""
        projection = StatusProjection(
            execution_id="exec_12345",
            project_id="customer-123/project-abc",
            status=ExecutionStatus.RUNNING,
            progress=45.2,
            current_task="1.1.1",
            totals=TaskTotals(completed=3, total=8),
            customer_id="customer-123",
            branch="main",
            started_at=None
        )
        
        assert projection.execution_id == "exec_12345"
        assert projection.project_id == "customer-123/project-abc"
        assert projection.status == ExecutionStatus.RUNNING
        assert projection.progress == 45.2
        assert projection.current_task == "1.1.1"
        assert projection.totals.completed == 3
        assert projection.totals.total == 8
        assert projection.customer_id == "customer-123"
        assert projection.branch == "main"
    
    def test_minimal_status_projection(self):
        """Test minimal valid status projection."""
        projection = StatusProjection(
            execution_id="exec_minimal",
            project_id="test/project",
            status=ExecutionStatus.IDLE,
            progress=0.0,
            current_task=None,
            customer_id=None,
            branch=None,
            started_at=None
        )
        
        assert projection.execution_id == "exec_minimal"
        assert projection.project_id == "test/project"
        assert projection.status == ExecutionStatus.IDLE
        assert projection.progress == 0.0
        assert projection.current_task is None
        assert projection.customer_id is None
        assert projection.branch is None
    
    def test_execution_id_validation(self):
        """Test execution ID validation."""
        # Valid execution IDs
        valid_ids = ["exec_12345", "execution-abc", "exec_test_123"]
        for exec_id in valid_ids:
            projection = StatusProjection(
                execution_id=exec_id,
                project_id="test/project",
                status=ExecutionStatus.IDLE,
                progress=0.0,
                current_task=None,
                customer_id=None,
                branch=None,
                started_at=None
            )
            assert projection.execution_id == exec_id
        
        # Invalid execution IDs
        invalid_ids = ["", "  ", "exec@invalid", "exec with spaces"]
        for exec_id in invalid_ids:
            with pytest.raises(ValidationError):
                StatusProjection(
                    execution_id=exec_id,
                    project_id="test/project",
                    status=ExecutionStatus.IDLE,
                    progress=0.0,
                    current_task=None,
                    customer_id=None,
                    branch=None,
                    started_at=None
                )
    
    def test_project_id_validation(self):
        """Test project ID validation."""
        # Valid project IDs
        valid_ids = ["customer-123/project-abc", "test/project", "simple-project"]
        for project_id in valid_ids:
            projection = StatusProjection(
                execution_id="exec_test",
                project_id=project_id,
                status=ExecutionStatus.IDLE,
                progress=0.0
            )
            assert projection.project_id == project_id
        
        # Invalid project IDs
        invalid_ids = ["", "  ", "invalid@project", "customer/project/extra"]
        for project_id in invalid_ids:
            with pytest.raises(ValidationError):
                StatusProjection(
                    execution_id="exec_test",
                    project_id=project_id,
                    status=ExecutionStatus.IDLE,
                    progress=0.0
                )
    
    def test_progress_validation(self):
        """Test progress validation."""
        # Valid progress values
        valid_progress = [0.0, 25.5, 50.0, 100.0]
        for progress in valid_progress:
            projection = StatusProjection(
                execution_id="exec_test",
                project_id="test/project",
                status=ExecutionStatus.RUNNING,
                progress=progress
            )
            assert projection.progress == progress
        
        # Invalid progress values
        invalid_progress = [-1.0, 101.0, 150.0]
        for progress in invalid_progress:
            with pytest.raises(ValidationError):
                StatusProjection(
                    execution_id="exec_test",
                    project_id="test/project",
                    status=ExecutionStatus.RUNNING,
                    progress=progress
                )
    
    def test_current_task_validation(self):
        """Test current task validation."""
        # Valid task IDs
        valid_tasks = ["1.1.1", "2.3", "10.5.2"]
        for task_id in valid_tasks:
            projection = StatusProjection(
                execution_id="exec_test",
                project_id="test/project",
                status=ExecutionStatus.RUNNING,
                progress=50.0,
                current_task=task_id
            )
            assert projection.current_task == task_id
        
        # Invalid task IDs
        invalid_tasks = ["invalid", "1.a.1", "task-1"]
        for task_id in invalid_tasks:
            with pytest.raises(ValidationError):
                StatusProjection(
                    execution_id="exec_test",
                    project_id="test/project",
                    status=ExecutionStatus.RUNNING,
                    progress=50.0,
                    current_task=task_id
                )
    
    def test_status_consistency_validation(self):
        """Test status consistency validation."""
        # IDLE status should have 0% progress and no current task
        projection = StatusProjection(
            execution_id="exec_test",
            project_id="test/project",
            status=ExecutionStatus.IDLE,
            progress=0.0
        )
        assert projection.status == ExecutionStatus.IDLE
        
        # IDLE with progress should fail
        with pytest.raises(ValidationError) as exc_info:
            StatusProjection(
                execution_id="exec_test",
                project_id="test/project",
                status=ExecutionStatus.IDLE,
                progress=50.0
            )
        assert "IDLE status should have 0% progress" in str(exc_info.value)
        
        # IDLE with current task should fail
        with pytest.raises(ValidationError) as exc_info:
            StatusProjection(
                execution_id="exec_test",
                project_id="test/project",
                status=ExecutionStatus.IDLE,
                progress=0.0,
                current_task="1.1.1"
            )
        assert "IDLE status should not have a current task" in str(exc_info.value)
        
        # RUNNING without current task should fail
        with pytest.raises(ValidationError) as exc_info:
            StatusProjection(
                execution_id="exec_test",
                project_id="test/project",
                status=ExecutionStatus.RUNNING,
                progress=50.0
            )
        assert "RUNNING status requires a current task" in str(exc_info.value)
        
        # COMPLETED should have 100% progress
        with pytest.raises(ValidationError) as exc_info:
            StatusProjection(
                execution_id="exec_test",
                project_id="test/project",
                status=ExecutionStatus.COMPLETED,
                progress=50.0
            )
        assert "COMPLETED status requires 100% progress" in str(exc_info.value)
    
    def test_state_transition_validation(self):
        """Test state transition validation method."""
        projection = StatusProjection(
            execution_id="exec_test",
            project_id="test/project",
            status=ExecutionStatus.RUNNING,
            progress=50.0,
            current_task="1.1.1"
        )
        
        # Valid transitions from RUNNING
        assert projection.validate_state_transition(ExecutionStatus.RUNNING) == True  # Can pause
        assert projection.validate_state_transition(ExecutionStatus.PAUSED) == False  # Cannot go from PAUSED to RUNNING directly
        
        # Test IDLE to INITIALIZING
        idle_projection = StatusProjection(
            execution_id="exec_test",
            project_id="test/project",
            status=ExecutionStatus.INITIALIZING,
            progress=5.0
        )
        assert idle_projection.validate_state_transition(ExecutionStatus.IDLE) == True


class TestStatusProjectionError:
    """Test StatusProjectionError model."""
    
    def test_valid_error(self):
        """Test valid error creation."""
        error = StatusProjectionError(
            error_code="INVALID_STATE_TRANSITION",
            message="Cannot transition from COMPLETED to RUNNING",
            details={"from_status": "completed", "to_status": "running"},
            execution_id="exec_12345"
        )
        
        assert error.error_code == "INVALID_STATE_TRANSITION"
        assert error.message == "Cannot transition from COMPLETED to RUNNING"
        assert error.details is not None and error.details["from_status"] == "completed"
        assert error.execution_id == "exec_12345"


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_project_status_from_task_context(self):
        """Test projecting status from task context."""
        task_context = {
            "metadata": {
                "status": "prepared",
                "task_id": "1.1.1",
                "branch": "main",
                "started_at": "2025-01-14T18:25:00Z"
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
        assert projection.status == ExecutionStatus.RUNNING  # One node is running
        assert projection.current_task == "1.1.1"
        assert projection.customer_id == "customer-123"
        assert projection.branch == "main"
        assert projection.totals.total == 2
        assert projection.totals.completed == 1
    
    def test_project_status_completed_workflow(self):
        """Test projecting status for completed workflow."""
        task_context = {
            "metadata": {
                "status": "prepared",
                "task_id": "1.1.1"
            },
            "nodes": {
                "SelectNode": {"status": "completed"},
                "PrepNode": {"status": "completed"},
                "ImplementNode": {"status": "completed"}
            }
        }
        
        projection = project_status_from_task_context(
            task_context=task_context,
            execution_id="exec_12345",
            project_id="test/project"
        )
        
        assert projection.status == ExecutionStatus.COMPLETED
        assert projection.progress == 100.0
        assert projection.totals.completed == 3
        assert projection.totals.total == 3
    
    def test_validate_status_transition_function(self):
        """Test validate_status_transition utility function."""
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
        
        # Invalid status values
        assert validate_status_transition("invalid", "running") == False
        assert validate_status_transition("running", "invalid") == False


class TestIntegrationScenarios:
    """Test integration scenarios and edge cases."""
    
    def test_full_workflow_progression(self):
        """Test full workflow status progression."""
        # Start with IDLE
        projection = StatusProjection(
            execution_id="exec_workflow",
            project_id="test/workflow",
            status=ExecutionStatus.IDLE,
            progress=0.0
        )
        assert projection.status == ExecutionStatus.IDLE
        
        # Move to INITIALIZING
        projection.status = ExecutionStatus.INITIALIZING
        projection.progress = 5.0
        assert projection.status == ExecutionStatus.INITIALIZING
        
        # Move to RUNNING
        projection.status = ExecutionStatus.RUNNING
        projection.progress = 50.0
        projection.current_task = "1.1.1"
        assert projection.status == ExecutionStatus.RUNNING
        
        # Complete
        projection.status = ExecutionStatus.COMPLETED
        projection.progress = 100.0
        projection.totals = TaskTotals(completed=5, total=5)
        assert projection.status == ExecutionStatus.COMPLETED
    
    def test_error_scenarios(self):
        """Test various error scenarios."""
        # Test with error status
        projection = StatusProjection(
            execution_id="exec_error",
            project_id="test/error",
            status=ExecutionStatus.ERROR,
            progress=25.0,
            current_task="1.1.1"
        )
        assert projection.status == ExecutionStatus.ERROR
        
        # Error can have any progress/task state
        assert projection.progress == 25.0
        assert projection.current_task == "1.1.1"
    
    def test_performance_requirements(self):
        """Test that schema validation meets performance requirements."""
        import time
        
        # Test creation performance
        start_time = time.time()
        for i in range(100):
            projection = StatusProjection(
                execution_id=f"exec_{i}",
                project_id=f"test/project_{i}",
                status=ExecutionStatus.RUNNING,
                progress=float(i),
                current_task="1.1.1"
            )
        end_time = time.time()
        
        # Should complete 100 validations well under 2s requirement
        assert (end_time - start_time) < 1.0, "Schema validation should be fast"
    
    def test_json_serialization(self):
        """Test JSON serialization and deserialization."""
        projection = StatusProjection(
            execution_id="exec_json",
            project_id="test/json",
            status=ExecutionStatus.RUNNING,
            progress=75.0,
            current_task="2.1.1",
            totals=TaskTotals(completed=3, total=4),
            artifacts=ExecutionArtifacts(
                repo_path="/workspace/repos/test",
                branch="feature/test",
                logs=["Started", "Processing"],
                files_modified=["app.py"]
            )
        )
        
        # Test JSON export
        json_data = projection.dict()
        assert json_data["execution_id"] == "exec_json"
        assert json_data["status"] == "running"
        assert json_data["progress"] == 75.0
        
        # Test JSON import
        new_projection = StatusProjection(**json_data)
        assert new_projection.execution_id == projection.execution_id
        assert new_projection.status == projection.status
        assert new_projection.progress == projection.progress