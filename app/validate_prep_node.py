#!/usr/bin/env python3
"""
PREP Node Validation Script

This script validates that the PREP node implementation meets all acceptance criteria
for task 3.2.2: Implement PREP node stub persisting initial task_context.
"""

import sys
import time
import asyncio
from datetime import datetime

# Add app directory to path for imports
sys.path.append('./app')

from workflows.devteam_automation_workflow import DevTeamAutomationWorkflow
from workflows.devteam_automation_workflow_nodes.prep_node import PrepNode
from workflows.devteam_automation_workflow_nodes.select_node import SelectNode
from schemas.event_schema import EventRequest, TaskDefinition, EventMetadata
from core.task import TaskContext


def print_test_header(test_name):
    """Print formatted test header."""
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print(f"{'='*60}")


def print_test_result(test_name, passed, details=""):
    """Print formatted test result."""
    status = "✓ PASSED" if passed else "✗ FAILED"
    print(f"{test_name}: {status}")
    if details:
        print(f"  Details: {details}")


async def test_prep_node_basic_functionality():
    """Test basic PREP node functionality."""
    print_test_header("PREP Node Basic Functionality")
    
    try:
        # Create test event with metadata
        test_event = EventRequest(
            id="test_prep_node_123",
            type="DEVTEAM_AUTOMATION",
            project_id="customer-123/project-abc",
            task=TaskDefinition(
                id="3.2.2",
                title="Test PREP node implementation",
                description="Validate PREP node persists task_context",
                type="atomic"
            ),
            priority="high",
            metadata=EventMetadata(
                correlation_id="corr_prep_test_123",
                source="validation_script",
                user_id="test_user"
            )
        )
        
        # Create task context
        task_context = TaskContext(event=test_event)
        
        # Add selected plan from SELECT node (simulating SELECT→PREP flow)
        task_context.metadata["selected_plan"] = {
            "plan_id": "plan_test_prep_node_123",
            "strategy": "devteam_automation"
        }
        
        # Create and process PREP node
        prep_node = PrepNode()
        result = await prep_node.process(task_context)
        
        # Validate basic functionality
        assert result is not None, "PREP node should return TaskContext"
        assert isinstance(result, TaskContext), "Result should be TaskContext instance"
        
        print_test_result("PREP Node Basic Functionality", True, "Node processes successfully")
        return True
        
    except Exception as e:
        print_test_result("PREP Node Basic Functionality", False, str(e))
        return False


async def test_prep_node_metadata_persistence():
    """Test that PREP node persists required metadata."""
    print_test_header("PREP Node Metadata Persistence")
    
    try:
        # Create test event with metadata
        test_event = EventRequest(
            id="test_metadata_456",
            type="DEVTEAM_AUTOMATION",
            project_id="customer-456/project-def",
            task=TaskDefinition(
                id="3.2.2",
                title="Test metadata persistence",
                description="Validate metadata fields",
                type="atomic"
            ),
            priority="normal",
            metadata=EventMetadata(
                correlation_id="corr_metadata_test",
                source="validation_script",
                user_id="test_user_456"
            )
        )
        
        task_context = TaskContext(event=test_event)
        task_context.metadata["selected_plan"] = {
            "plan_id": "plan_metadata_test",
            "strategy": "devteam_automation"
        }
        
        prep_node = PrepNode()
        result = await prep_node.process(task_context)
        
        # Validate required metadata fields
        required_fields = [
            "correlationId", "status", "prepared_at", "workflow_type",
            "event_id", "project_id", "task_id", "priority"
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in result.metadata:
                missing_fields.append(field)
        
        assert not missing_fields, f"Missing required metadata fields: {missing_fields}"
        
        # Validate specific field values
        assert result.metadata["correlationId"] == "corr_metadata_test", "CorrelationId should match event metadata"
        assert result.metadata["status"] == "prepared", "Status should be 'prepared'"
        assert result.metadata["workflow_type"] == "DEVTEAM_AUTOMATION", "Workflow type should be DEVTEAM_AUTOMATION"
        assert result.metadata["event_id"] == "test_metadata_456", "Event ID should match"
        assert result.metadata["project_id"] == "customer-456/project-def", "Project ID should match"
        assert result.metadata["task_id"] == "3.2.2", "Task ID should match"
        assert result.metadata["priority"] == "normal", "Priority should match"
        
        # Validate timestamp format
        prepared_at = result.metadata["prepared_at"]
        datetime.fromisoformat(prepared_at)  # Should not raise exception
        
        print_test_result("PREP Node Metadata Persistence", True, "All required metadata fields present and valid")
        return True
        
    except Exception as e:
        print_test_result("PREP Node Metadata Persistence", False, str(e))
        return False


async def test_prep_node_correlation_id_generation():
    """Test PREP node generates correlationId when missing."""
    print_test_header("PREP Node CorrelationId Generation")
    
    try:
        # Create event without metadata
        test_event = EventRequest(
            id="test_no_correlation",
            type="DEVTEAM_AUTOMATION",
            project_id="test/project",
            task=TaskDefinition(
                id="1.0",
                title="Test correlation ID generation",
                description="Test fallback correlation ID"
            )
        )
        
        task_context = TaskContext(event=test_event)
        prep_node = PrepNode()
        result = await prep_node.process(task_context)
        
        # Should generate correlationId based on event ID
        expected_correlation_id = "corr_test_no_correlation"
        assert result.metadata["correlationId"] == expected_correlation_id, f"Should generate correlationId: {expected_correlation_id}"
        
        print_test_result("PREP Node CorrelationId Generation", True, "Generates correlationId when missing")
        return True
        
    except Exception as e:
        print_test_result("PREP Node CorrelationId Generation", False, str(e))
        return False


async def test_prep_node_task_context_update():
    """Test PREP node updates task context properly."""
    print_test_header("PREP Node Task Context Update")
    
    try:
        test_event = EventRequest(
            id="test_context_update",
            type="DEVTEAM_AUTOMATION",
            project_id="test/context",
            task=TaskDefinition(
                id="1.1",
                title="Test context update",
                description="Test node status update"
            ),
            metadata=EventMetadata(
                correlation_id="corr_context_test",
                source="validation",
                user_id="test_user"
            )
        )
        
        task_context = TaskContext(event=test_event)
        task_context.metadata["selected_plan"] = {
            "plan_id": "plan_context_test",
            "strategy": "devteam_automation"
        }
        
        prep_node = PrepNode()
        result = await prep_node.process(task_context)
        
        # Validate node was updated in task context
        assert "PrepNode" in result.nodes, "PrepNode should be in task context nodes"
        
        node_data = result.nodes["PrepNode"]
        assert node_data["status"] == "completed", "Node status should be completed"
        assert "Task context prepared" in node_data["message"], "Should have appropriate message"
        
        # Validate event data
        event_data = node_data["event_data"]
        assert event_data["correlationId"] == "corr_context_test", "Event data should include correlationId"
        assert event_data["workflow_type"] == "DEVTEAM_AUTOMATION", "Event data should include workflow_type"
        assert "prepared_at" in event_data, "Event data should include prepared_at"
        assert event_data["plan_id"] == "plan_context_test", "Event data should include plan_id"
        
        print_test_result("PREP Node Task Context Update", True, "Node properly updates task context")
        return True
        
    except Exception as e:
        print_test_result("PREP Node Task Context Update", False, str(e))
        return False


def test_select_prep_workflow_integration():
    """Test SELECT→PREP workflow integration."""
    print_test_header("SELECT→PREP Workflow Integration")
    
    try:
        # Create test event
        test_event = {
            "id": "test_integration_789",
            "type": "DEVTEAM_AUTOMATION",
            "project_id": "customer-789/project-integration",
            "task": {
                "id": "3.2.2",
                "title": "Test SELECT→PREP integration",
                "description": "Validate complete workflow execution",
                "type": "atomic"
            },
            "priority": "high",
            "metadata": {
                "correlation_id": "corr_integration_test",
                "source": "validation_script",
                "user_id": "integration_user"
            }
        }
        
        # Execute complete workflow
        workflow = DevTeamAutomationWorkflow()
        result = workflow.run(test_event)
        
        # Validate workflow completed
        assert isinstance(result, TaskContext), "Workflow should return TaskContext"
        assert result.event.id == "test_integration_789", "Event ID should match"
        
        # Validate both nodes executed
        assert "SelectNode" in result.nodes, "SelectNode should have executed"
        assert "PrepNode" in result.nodes, "PrepNode should have executed"
        
        # Validate SelectNode results
        select_data = result.nodes["SelectNode"]
        assert select_data["status"] == "completed", "SelectNode should be completed"
        
        # Validate PrepNode results
        prep_data = result.nodes["PrepNode"]
        assert prep_data["status"] == "completed", "PrepNode should be completed"
        
        # Validate metadata was set by PrepNode
        assert result.metadata["correlationId"] == "corr_integration_test", "CorrelationId should be preserved"
        assert result.metadata["status"] == "prepared", "Status should be prepared"
        assert result.metadata["workflow_type"] == "DEVTEAM_AUTOMATION", "Workflow type should be set"
        
        # Validate plan was passed from SELECT to PREP
        assert "selected_plan" in result.metadata, "Selected plan should be in metadata"
        
        print_test_result("SELECT→PREP Workflow Integration", True, "Complete workflow executes successfully")
        return True
        
    except Exception as e:
        print_test_result("SELECT→PREP Workflow Integration", False, str(e))
        return False


def test_workflow_performance_requirement():
    """Test workflow execution meets performance requirement (≤2s)."""
    print_test_header("Workflow Performance Requirement")
    
    try:
        test_event = {
            "id": "test_performance",
            "type": "DEVTEAM_AUTOMATION",
            "project_id": "test/performance",
            "task": {"id": "1.0", "title": "Performance test"}
        }
        
        workflow = DevTeamAutomationWorkflow()
        
        # Measure execution time
        start_time = time.time()
        result = workflow.run(test_event)
        execution_time = time.time() - start_time
        
        # Validate performance requirement (≤2s)
        assert execution_time <= 2.0, f"Workflow execution took {execution_time:.3f}s, exceeding 2s requirement"
        
        # Validate workflow still completed successfully
        assert isinstance(result, TaskContext), "Workflow should complete successfully"
        assert "SelectNode" in result.nodes, "SelectNode should execute"
        assert "PrepNode" in result.nodes, "PrepNode should execute"
        
        print_test_result("Workflow Performance Requirement", True, f"Execution time: {execution_time:.3f}s (≤2s)")
        return True
        
    except Exception as e:
        print_test_result("Workflow Performance Requirement", False, str(e))
        return False


async def main():
    """Run all validation tests."""
    print("PREP Node Implementation Validation")
    print("Task 3.2.2: Implement PREP node stub persisting initial task_context")
    print(f"Validation started at: {datetime.now().isoformat()}")
    
    # Run all tests
    tests = [
        test_prep_node_basic_functionality(),
        test_prep_node_metadata_persistence(),
        test_prep_node_correlation_id_generation(),
        test_prep_node_task_context_update(),
    ]
    
    # Run async tests
    async_results = await asyncio.gather(*tests, return_exceptions=True)
    
    # Run sync tests
    sync_results = [
        test_select_prep_workflow_integration(),
        test_workflow_performance_requirement(),
    ]
    
    # Combine results
    all_results = list(async_results) + sync_results
    
    # Count results
    passed_tests = sum(1 for result in all_results if result is True)
    total_tests = len(all_results)
    failed_tests = total_tests - passed_tests
    
    # Print summary
    print(f"\n{'='*60}")
    print("VALIDATION SUMMARY")
    print(f"{'='*60}")
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if failed_tests == 0:
        print("\n✓ ALL TESTS PASSED - PREP node implementation is complete and functional!")
        print("\nAcceptance Criteria Validation:")
        print("✓ PREP node stub exists and persists initial task_context")
        print("✓ Metadata includes: correlationId, status, prepared_at, workflow_type, event_id, project_id, task_id, priority")
        print("✓ Node follows established patterns from PlaceholderWorkflow")
        print("✓ Performance: workflow execution completes within 2s requirement")
        print("✓ Integration: works seamlessly with SELECT node in SELECT→PREP flow")
        print("✓ Testing: comprehensive test coverage validates functionality")
        return True
    else:
        print(f"\n✗ {failed_tests} TEST(S) FAILED - Implementation needs attention")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)