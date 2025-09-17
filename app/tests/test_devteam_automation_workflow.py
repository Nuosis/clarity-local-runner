"""
DevTeam Automation Workflow Test Suite

This module provides comprehensive testing for the DevTeam Automation workflow,
including unit tests for individual nodes, integration tests for the complete
workflow, and performance validation to ensure the 2s execution requirement.

Test Coverage:
- SelectNode functionality and plan generation
- PrepNode metadata setting and task context preparation
- Complete workflow execution (SELECT→PREP pattern)
- Performance validation (≤2s execution time)
- Error handling and edge cases
- Integration with existing EventRequest schema
"""

import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch

from workflows.devteam_automation_workflow import DevTeamAutomationWorkflow
from workflows.devteam_automation_workflow_nodes.select_node import SelectNode
from workflows.devteam_automation_workflow_nodes.prep_node import PrepNode
from schemas.event_schema import EventRequest, TaskDefinition, EventMetadata
from core.task import TaskContext


class TestSelectNode:
    """Test suite for SelectNode functionality."""
    
    @pytest.fixture
    def select_node(self):
        """Create a SelectNode instance for testing."""
        return SelectNode()
    
    @pytest.fixture
    def sample_event(self):
        """Create a sample DEVTEAM_AUTOMATION event for testing."""
        return EventRequest(
            id="test_event_123",
            type="DEVTEAM_AUTOMATION",
            project_id="customer-123/project-abc",
            task=TaskDefinition(
                id="1.1.1",
                title="Add DEVTEAM_ENABLED flag to src/config.js",
                description="Add DEVTEAM_ENABLED flag with default false and JSDoc",
                type="atomic",
                dependencies=[],
                files=["src/config.js"]
            ),
            priority="normal"
        )
    
    @pytest.fixture
    def task_context(self, sample_event):
        """Create a TaskContext with sample event."""
        return TaskContext(event=sample_event)
    
    async def test_select_node_creates_fixed_plan(self, select_node, task_context):
        """Test that SelectNode creates a fixed plan object."""
        result = await select_node.process(task_context)
        
        # Verify plan was created and stored
        assert "selected_plan" in result.metadata
        plan = result.metadata["selected_plan"]
        
        # Verify plan structure
        assert plan["plan_id"] == f"plan_{task_context.event.id}"
        assert plan["strategy"] == "devteam_automation"
        assert len(plan["phases"]) == 2
        assert plan["estimated_duration"] == "2s"
        assert plan["priority"] == "normal"
        
        # Verify phases structure
        phases = plan["phases"]
        assert phases[0]["phase"] == "preparation"
        assert phases[1]["phase"] == "execution"
    
    async def test_select_node_updates_task_context(self, select_node, task_context):
        """Test that SelectNode properly updates task context."""
        result = await select_node.process(task_context)
        
        # Verify node was updated in task context
        assert "SelectNode" in result.nodes
        node_data = result.nodes["SelectNode"]
        
        assert node_data["status"] == "completed"
        assert "Fixed plan selected" in node_data["message"]
        assert node_data["event_data"]["strategy"] == "devteam_automation"
        assert node_data["event_data"]["phases_count"] == 2
    
    async def test_select_node_handles_different_priorities(self, select_node):
        """Test SelectNode handles different event priorities."""
        high_priority_event = EventRequest(
            id="high_priority_event",
            type="DEVTEAM_AUTOMATION",
            project_id="customer-123/project-abc",
            task=TaskDefinition(
                id="1.1.1",
                title="High priority task",
                description="High priority task description"
            ),
            priority="high"
        )
        
        task_context = TaskContext(event=high_priority_event)
        result = await select_node.process(task_context)
        
        plan = result.metadata["selected_plan"]
        assert plan["priority"] == "high"


class TestPrepNode:
    """Test suite for PrepNode functionality."""
    
    @pytest.fixture
    def prep_node(self):
        """Create a PrepNode instance for testing."""
        return PrepNode()
    
    @pytest.fixture
    def sample_event_with_metadata(self):
        """Create a sample event with metadata for testing."""
        return EventRequest(
            id="test_event_456",
            type="DEVTEAM_AUTOMATION",
            project_id="customer-456/project-def",
            task=TaskDefinition(
                id="2.1.3",
                title="Update database schema",
                description="Update database schema for new features",
                type="atomic"
            ),
            priority="high",
            metadata=EventMetadata(
                correlation_id="corr_test_123",
                source="devteam_ui",
                user_id="user_456"
            )
        )
    
    @pytest.fixture
    def task_context_with_plan(self, sample_event_with_metadata):
        """Create a TaskContext with event and selected plan."""
        context = TaskContext(event=sample_event_with_metadata)
        context.metadata["selected_plan"] = {
            "plan_id": "plan_test_event_456",
            "strategy": "devteam_automation"
        }
        return context
    
    async def test_prep_node_sets_basic_metadata(self, prep_node, task_context_with_plan):
        """Test that PrepNode sets basic task context metadata."""
        result = await prep_node.process(task_context_with_plan)
        
        # Verify basic metadata was set
        metadata = result.metadata
        assert metadata["correlationId"] == "corr_test_123"
        assert metadata["status"] == "prepared"
        assert metadata["workflow_type"] == "DEVTEAM_AUTOMATION"
        assert metadata["event_id"] == "test_event_456"
        assert metadata["project_id"] == "customer-456/project-def"
        assert metadata["task_id"] == "2.1.3"
        assert metadata["priority"] == "high"
        assert "prepared_at" in metadata
        
        # Verify timestamp format
        prepared_at = datetime.fromisoformat(metadata["prepared_at"])
        assert isinstance(prepared_at, datetime)
    
    async def test_prep_node_generates_correlation_id_when_missing(self, prep_node):
        """Test PrepNode generates correlationId when not provided."""
        event_without_metadata = EventRequest(
            id="no_metadata_event",
            type="DEVTEAM_AUTOMATION",
            project_id="test/project",
            task=TaskDefinition(
                id="1.1",
                title="Test task",
                description="Test task description"
            )
        )
        
        task_context = TaskContext(event=event_without_metadata)
        result = await prep_node.process(task_context)
        
        # Should generate correlationId based on event ID
        assert result.metadata["correlationId"] == "corr_no_metadata_event"
    
    async def test_prep_node_updates_task_context(self, prep_node, task_context_with_plan):
        """Test that PrepNode properly updates task context."""
        result = await prep_node.process(task_context_with_plan)
        
        # Verify node was updated in task context
        assert "PrepNode" in result.nodes
        node_data = result.nodes["PrepNode"]
        
        assert node_data["status"] == "completed"
        assert "Task context prepared" in node_data["message"]
        assert node_data["event_data"]["correlationId"] == "corr_test_123"
        assert node_data["event_data"]["workflow_type"] == "DEVTEAM_AUTOMATION"
        assert node_data["event_data"]["plan_id"] == "plan_test_event_456"


class TestDevTeamAutomationWorkflow:
    """Test suite for complete DevTeam Automation workflow."""
    
    @pytest.fixture
    def workflow(self):
        """Create a DevTeamAutomationWorkflow instance for testing."""
        return DevTeamAutomationWorkflow()
    
    @pytest.fixture
    def sample_devteam_event(self):
        """Create a comprehensive DEVTEAM_AUTOMATION event for testing."""
        return {
            "id": "evt_devteam_789",
            "type": "DEVTEAM_AUTOMATION",
            "project_id": "customer-789/project-ghi",
            "task": {
                "id": "3.2.1",
                "title": "Implement user authentication",
                "description": "Add JWT-based authentication system",
                "type": "atomic",
                "dependencies": ["3.1.1", "3.1.2"],
                "files": ["src/auth.js", "src/middleware.js"]
            },
            "priority": "high",
            "data": {
                "repository_url": "https://github.com/user/repo.git",
                "branch": "feature/auth"
            },
            "metadata": {
                "correlation_id": "corr_workflow_test",
                "source": "devteam_automation",
                "user_id": "dev_user_123"
            }
        }
    
    def test_workflow_execution_completes_successfully(self, workflow, sample_devteam_event):
        """Test that the complete workflow executes successfully."""
        result = workflow.run(sample_devteam_event)
        
        # Verify workflow completed
        assert isinstance(result, TaskContext)
        assert result.event.id == "evt_devteam_789"
        assert result.event.type == "DEVTEAM_AUTOMATION"
        
        # Verify both nodes executed
        assert "SelectNode" in result.nodes
        assert "PrepNode" in result.nodes
        
        # Verify SelectNode results
        select_data = result.nodes["SelectNode"]
        assert select_data["status"] == "completed"
        
        # Verify PrepNode results
        prep_data = result.nodes["PrepNode"]
        assert prep_data["status"] == "completed"
        
        # Verify metadata was set by PrepNode
        assert result.metadata["correlationId"] == "corr_workflow_test"
        assert result.metadata["status"] == "prepared"
        assert result.metadata["workflow_type"] == "DEVTEAM_AUTOMATION"
    
    def test_workflow_execution_performance_requirement(self, workflow, sample_devteam_event):
        """Test that workflow execution completes within 2s requirement."""
        start_time = time.time()
        result = workflow.run(sample_devteam_event)
        execution_time = time.time() - start_time
        
        # Verify performance requirement (≤2s)
        assert execution_time <= 2.0, f"Workflow execution took {execution_time:.3f}s, exceeding 2s requirement"
        
        # Verify workflow still completed successfully
        assert isinstance(result, TaskContext)
        assert "SelectNode" in result.nodes
        assert "PrepNode" in result.nodes
    
    def test_workflow_handles_minimal_event(self, workflow):
        """Test workflow handles minimal DEVTEAM_AUTOMATION event."""
        minimal_event = {
            "id": "minimal_event",
            "type": "DEVTEAM_AUTOMATION",
            "project_id": "test/minimal",
            "task": {
                "id": "1.0",
                "title": "Minimal task"
            }
        }
        
        result = workflow.run(minimal_event)
        
        # Should still complete successfully
        assert isinstance(result, TaskContext)
        assert "SelectNode" in result.nodes
        assert "PrepNode" in result.nodes
        assert result.metadata["correlationId"].startswith("corr_")
    
    def test_workflow_schema_validation(self, workflow):
        """Test that workflow properly validates event schema."""
        # This should work with valid DEVTEAM_AUTOMATION event
        valid_event = {
            "id": "valid_event",
            "type": "DEVTEAM_AUTOMATION",
            "project_id": "customer/project",
            "task": {"id": "1.1", "title": "Valid task"}
        }
        
        result = workflow.run(valid_event)
        assert isinstance(result, TaskContext)
    
    async def test_workflow_async_execution(self, workflow, sample_devteam_event):
        """Test that workflow can be executed asynchronously."""
        result = await workflow.run_async(sample_devteam_event)
        
        # Verify async execution works the same as sync
        assert isinstance(result, TaskContext)
        assert "SelectNode" in result.nodes
        assert "PrepNode" in result.nodes


class TestWorkflowIntegration:
    """Integration tests for DevTeam Automation workflow with existing systems."""
    
    def test_workflow_registry_integration(self):
        """Test that workflow is properly registered in WorkflowRegistry."""
        from workflows.workflow_registry import WorkflowRegistry
        
        # Verify DEVTEAM_AUTOMATION is registered
        assert hasattr(WorkflowRegistry, 'DEVTEAM_AUTOMATION')
        
        # Verify it points to the correct workflow class
        workflow_class = WorkflowRegistry.DEVTEAM_AUTOMATION.value
        assert workflow_class == DevTeamAutomationWorkflow
        
        # Verify workflow can be instantiated from registry
        workflow_instance = workflow_class()
        assert isinstance(workflow_instance, DevTeamAutomationWorkflow)
    
    def test_event_schema_compatibility(self):
        """Test that workflow is compatible with existing EventRequest schema."""
        # Test with schema example from event_schema.py
        schema_example = {
            "id": "evt_devteam_12345",
            "type": "DEVTEAM_AUTOMATION",
            "project_id": "customer-123/project-abc",
            "task": {
                "id": "1.1.1",
                "title": "Add DEVTEAM_ENABLED flag to src/config.js",
                "description": "Add DEVTEAM_ENABLED flag with default false and JSDoc",
                "type": "atomic",
                "dependencies": [],
                "files": ["src/config.js"]
            },
            "priority": "normal",
            "data": {
                "repository_url": "https://github.com/user/repo.git",
                "branch": "main"
            },
            "options": {
                "idempotency_key": "unique-key-12345",
                "timeout_seconds": 300
            },
            "metadata": {
                "correlation_id": "req_12345",
                "source": "devteam_ui",
                "user_id": "user_123"
            }
        }
        
        workflow = DevTeamAutomationWorkflow()
        result = workflow.run(schema_example)
        
        # Should execute successfully with full schema
        assert isinstance(result, TaskContext)
        assert result.metadata["correlationId"] == "req_12345"


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_workflow_handles_missing_optional_fields(self):
        """Test workflow handles events with missing optional fields gracefully."""
        minimal_event = {
            "id": "minimal_test",
            "type": "DEVTEAM_AUTOMATION",
            "project_id": "test/project",
            "task": {"id": "1.0", "title": "Test"}
            # Missing: priority, data, metadata, options
        }
        
        workflow = DevTeamAutomationWorkflow()
        result = workflow.run(minimal_event)
        
        # Should complete successfully
        assert isinstance(result, TaskContext)
        assert result.metadata["priority"] == "normal"  # Default priority
    
    def test_nodes_handle_missing_task_attributes(self):
        """Test nodes handle events with missing task attributes."""
        event_missing_task_attrs = {
            "id": "missing_attrs",
            "type": "DEVTEAM_AUTOMATION",
            "project_id": "test/project",
            "task": {"id": "1.0", "title": "Test"}
            # Missing: task.description, task.type, etc.
        }
        
        workflow = DevTeamAutomationWorkflow()
        result = workflow.run(event_missing_task_attrs)
        
        # Should still complete
        assert isinstance(result, TaskContext)
        assert result.metadata["task_id"] == "1.0"


if __name__ == "__main__":
    # Run performance test directly
    workflow = DevTeamAutomationWorkflow()
    test_event = {
        "id": "perf_test",
        "type": "DEVTEAM_AUTOMATION",
        "project_id": "test/performance",
        "task": {"id": "1.0", "title": "Performance test"}
    }
    
    start = time.time()
    result = workflow.run(test_event)
    duration = time.time() - start
    
    print(f"Workflow execution time: {duration:.3f}s")
    print(f"Performance requirement (≤2s): {'✓ PASSED' if duration <= 2.0 else '✗ FAILED'}")
    print(f"Nodes executed: {list(result.nodes.keys())}")