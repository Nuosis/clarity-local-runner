#!/usr/bin/env python3
"""
SELECT Node Validation Script

This script validates that the SELECT node implementation returns a fixed plan object
as required for task 3.2.1. It tests the core functionality without requiring pytest.
"""

import sys
import asyncio
import time
from datetime import datetime

# Add the app directory to the Python path
sys.path.insert(0, 'app')

from workflows.devteam_automation_workflow_nodes.select_node import SelectNode
from workflows.devteam_automation_workflow import DevTeamAutomationWorkflow
from schemas.event_schema import EventRequest, TaskDefinition, EventMetadata
from core.task import TaskContext


def create_sample_event():
    """Create a sample DEVTEAM_AUTOMATION event for testing."""
    return EventRequest(
        id="test_event_123",
        type="DEVTEAM_AUTOMATION",
        project_id="customer-123/project-abc",
        task=TaskDefinition(
            id="3.2.1",
            title="Implement SELECT node stub returning fixed plan",
            description="Add SELECT node that returns fixed plan object with required structure",
            type="atomic",
            dependencies=[],
            files=["app/workflows/devteam_automation_workflow_nodes/select_node.py"]
        ),
        priority="normal",
        metadata=EventMetadata(
            correlation_id="corr_test_123",
            source="validation_script",
            user_id="validator"
        )
    )


async def test_select_node_functionality():
    """Test SELECT node core functionality."""
    print("🔍 Testing SELECT Node Functionality...")
    
    # Create SelectNode instance
    select_node = SelectNode()
    
    # Create sample event and task context
    sample_event = create_sample_event()
    task_context = TaskContext(event=sample_event)
    
    # Test node processing
    start_time = time.time()
    result = await select_node.process(task_context)
    processing_time = time.time() - start_time
    
    # Validate results
    success = True
    errors = []
    
    # Check that plan was created and stored
    if "selected_plan" not in result.metadata:
        success = False
        errors.append("❌ No 'selected_plan' found in task_context.metadata")
    else:
        plan = result.metadata["selected_plan"]
        print(f"✅ Plan created: {plan}")
        
        # Validate plan structure
        required_fields = ["plan_id", "strategy", "phases", "estimated_duration", "priority"]
        for field in required_fields:
            if field not in plan:
                success = False
                errors.append(f"❌ Missing required field '{field}' in plan")
        
        # Validate specific values
        if plan.get("plan_id") != f"plan_{sample_event.id}":
            success = False
            errors.append(f"❌ Incorrect plan_id: expected 'plan_{sample_event.id}', got '{plan.get('plan_id')}'")
        
        if plan.get("strategy") != "devteam_automation":
            success = False
            errors.append(f"❌ Incorrect strategy: expected 'devteam_automation', got '{plan.get('strategy')}'")
        
        if len(plan.get("phases", [])) != 2:
            success = False
            errors.append(f"❌ Incorrect phases count: expected 2, got {len(plan.get('phases', []))}")
        
        if plan.get("estimated_duration") != "2s":
            success = False
            errors.append(f"❌ Incorrect estimated_duration: expected '2s', got '{plan.get('estimated_duration')}'")
        
        if plan.get("priority") != "normal":
            success = False
            errors.append(f"❌ Incorrect priority: expected 'normal', got '{plan.get('priority')}'")
    
    # Check node status update
    if "SelectNode" not in result.nodes:
        success = False
        errors.append("❌ SelectNode not found in task_context.nodes")
    else:
        node_data = result.nodes["SelectNode"]
        if node_data.get("status") != "completed":
            success = False
            errors.append(f"❌ Incorrect node status: expected 'completed', got '{node_data.get('status')}'")
    
    # Performance check
    if processing_time > 0.1:  # Should be very fast for a stub
        errors.append(f"⚠️  Processing time {processing_time:.3f}s seems slow for a stub implementation")
    
    print(f"⏱️  Processing time: {processing_time:.3f}s")
    
    if success:
        print("✅ SELECT Node validation PASSED")
    else:
        print("❌ SELECT Node validation FAILED")
        for error in errors:
            print(f"   {error}")
    
    return success


def test_workflow_integration():
    """Test that SELECT node integrates properly with the workflow."""
    print("\n🔗 Testing Workflow Integration...")
    
    # Create workflow instance
    workflow = DevTeamAutomationWorkflow()
    
    # Create sample event
    sample_event = {
        "id": "workflow_test_456",
        "type": "DEVTEAM_AUTOMATION",
        "project_id": "customer-456/project-def",
        "task": {
            "id": "3.2.1",
            "title": "Workflow integration test",
            "description": "Test SELECT node integration with workflow"
        },
        "priority": "high"
    }
    
    # Test workflow execution
    start_time = time.time()
    result = workflow.run(sample_event)
    execution_time = time.time() - start_time
    
    success = True
    errors = []
    
    # Validate workflow completed
    if not isinstance(result, TaskContext):
        success = False
        errors.append("❌ Workflow did not return TaskContext")
    else:
        # Check that SelectNode executed
        if "SelectNode" not in result.nodes:
            success = False
            errors.append("❌ SelectNode not executed in workflow")
        
        # Check that plan was created
        if "selected_plan" not in result.metadata:
            success = False
            errors.append("❌ No plan created by workflow")
        else:
            plan = result.metadata["selected_plan"]
            if plan.get("strategy") != "devteam_automation":
                success = False
                errors.append(f"❌ Incorrect strategy in workflow: got '{plan.get('strategy')}'")
    
    # Performance check (should complete within 2s requirement)
    if execution_time > 2.0:
        success = False
        errors.append(f"❌ Workflow execution time {execution_time:.3f}s exceeds 2s requirement")
    
    print(f"⏱️  Workflow execution time: {execution_time:.3f}s")
    
    if success:
        print("✅ Workflow integration validation PASSED")
    else:
        print("❌ Workflow integration validation FAILED")
        for error in errors:
            print(f"   {error}")
    
    return success


def test_workflow_registry():
    """Test that workflow is properly registered."""
    print("\n📋 Testing Workflow Registry...")
    
    try:
        from workflows.workflow_registry import WorkflowRegistry
        
        success = True
        errors = []
        
        # Check DEVTEAM_AUTOMATION is registered
        if not hasattr(WorkflowRegistry, 'DEVTEAM_AUTOMATION'):
            success = False
            errors.append("❌ DEVTEAM_AUTOMATION not found in WorkflowRegistry")
        else:
            workflow_class = WorkflowRegistry.DEVTEAM_AUTOMATION.value
            if workflow_class != DevTeamAutomationWorkflow:
                success = False
                errors.append("❌ DEVTEAM_AUTOMATION points to wrong workflow class")
            
            # Test instantiation
            try:
                workflow_instance = workflow_class()
                if not isinstance(workflow_instance, DevTeamAutomationWorkflow):
                    success = False
                    errors.append("❌ Cannot instantiate workflow from registry")
            except Exception as e:
                success = False
                errors.append(f"❌ Error instantiating workflow: {e}")
        
        if success:
            print("✅ Workflow registry validation PASSED")
        else:
            print("❌ Workflow registry validation FAILED")
            for error in errors:
                print(f"   {error}")
        
        return success
        
    except ImportError as e:
        print(f"❌ Cannot import WorkflowRegistry: {e}")
        return False


async def main():
    """Run all validation tests."""
    print("🚀 SELECT Node Implementation Validation")
    print("=" * 50)
    
    # Run all tests
    test_results = []
    
    # Test 1: SELECT node functionality
    test_results.append(await test_select_node_functionality())
    
    # Test 2: Workflow integration
    test_results.append(test_workflow_integration())
    
    # Test 3: Registry integration
    test_results.append(test_workflow_registry())
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 VALIDATION SUMMARY")
    print("=" * 50)
    
    passed = sum(test_results)
    total = len(test_results)
    
    if passed == total:
        print(f"🎉 ALL TESTS PASSED ({passed}/{total})")
        print("\n✅ Task 3.2.1 Implementation Status: COMPLETE")
        print("   - SELECT node stub exists and returns fixed plan object")
        print("   - Plan object contains all required fields")
        print("   - Node follows established patterns from workflow framework")
        print("   - Performance meets 2s workflow execution requirement")
        print("   - Integration with workflow registry works correctly")
        return True
    else:
        print(f"❌ SOME TESTS FAILED ({passed}/{total})")
        print("\n🔧 Task 3.2.1 Implementation Status: NEEDS ATTENTION")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)