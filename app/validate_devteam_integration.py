#!/usr/bin/env python3
"""
DEVTEAM_AUTOMATION Workflow Integration Validation Script

This script validates the end-to-end integration of the DEVTEAM_AUTOMATION workflow
without requiring pytest. It tests all the key acceptance criteria for task 3.1.2.
"""

import sys
import time
import json
from datetime import datetime

# Add app directory to path for imports
sys.path.insert(0, './app')

def test_workflow_registry_resolution():
    """Test that WorkflowRegistry['DEVTEAM_AUTOMATION'] resolves correctly."""
    print("🔍 Testing WorkflowRegistry['DEVTEAM_AUTOMATION'] resolution...")
    
    try:
        from workflows.workflow_registry import WorkflowRegistry
        from workflows.devteam_automation_workflow import DevTeamAutomationWorkflow
        
        # Test registry resolution by name
        workflow_class = WorkflowRegistry["DEVTEAM_AUTOMATION"].value
        assert workflow_class == DevTeamAutomationWorkflow, "Registry resolution by name failed"
        
        # Test registry resolution by enum
        workflow_class_enum = WorkflowRegistry.DEVTEAM_AUTOMATION.value
        assert workflow_class_enum == DevTeamAutomationWorkflow, "Registry resolution by enum failed"
        
        # Test workflow instantiation
        workflow_instance = workflow_class()
        assert isinstance(workflow_instance, DevTeamAutomationWorkflow), "Workflow instantiation failed"
        
        # Test workflow name consistency
        assert WorkflowRegistry.DEVTEAM_AUTOMATION.name == "DEVTEAM_AUTOMATION", "Workflow name inconsistent"
        
        print("✅ WorkflowRegistry['DEVTEAM_AUTOMATION'] resolution validated")
        return True
        
    except Exception as e:
        print(f"❌ WorkflowRegistry resolution failed: {e}")
        return False

def test_workflow_type_determination():
    """Test that get_workflow_type properly routes DEVTEAM_AUTOMATION events."""
    print("🔍 Testing workflow type determination...")
    
    try:
        from api.endpoint import get_workflow_type
        
        # Test DEVTEAM_AUTOMATION routing
        devteam_type = get_workflow_type({"type": "DEVTEAM_AUTOMATION"})
        assert devteam_type == "DEVTEAM_AUTOMATION", f"Expected DEVTEAM_AUTOMATION, got {devteam_type}"
        
        # Test PLACEHOLDER routing (backward compatibility)
        placeholder_type = get_workflow_type({"type": "PLACEHOLDER"})
        assert placeholder_type == "PLACEHOLDER", f"Expected PLACEHOLDER, got {placeholder_type}"
        
        # Test unknown type fallback
        unknown_type = get_workflow_type({"type": "UNKNOWN"})
        assert unknown_type == "PLACEHOLDER", f"Expected PLACEHOLDER fallback, got {unknown_type}"
        
        print("✅ Workflow type determination validated")
        return True
        
    except Exception as e:
        print(f"❌ Workflow type determination failed: {e}")
        return False

def test_performance_requirement():
    """Test that workflow execution completes within 2s requirement."""
    print("🔍 Testing performance requirement (≤2s execution)...")
    
    try:
        from workflows.devteam_automation_workflow import DevTeamAutomationWorkflow
        
        # Create realistic DEVTEAM_AUTOMATION event payload
        devteam_event = {
            "id": "evt_performance_test",
            "type": "DEVTEAM_AUTOMATION",
            "project_id": "customer-test/project-performance",
            "task": {
                "id": "3.1.2",
                "title": "Performance test task",
                "description": "Test workflow execution performance",
                "type": "atomic"
            },
            "priority": "high",
            "metadata": {
                "correlation_id": "corr_performance_test",
                "source": "validation_script"
            }
        }
        
        workflow = DevTeamAutomationWorkflow()
        
        # Measure workflow execution time
        start_time = time.time()
        result = workflow.run(devteam_event)
        execution_time = time.time() - start_time
        
        # Verify performance requirement
        assert execution_time <= 2.0, f"Workflow execution took {execution_time:.3f}s, exceeding 2s requirement"
        
        # Verify workflow completed successfully
        assert result is not None, "Workflow result is None"
        assert "SelectNode" in result.nodes, "SelectNode not found in result"
        assert "PrepNode" in result.nodes, "PrepNode not found in result"
        assert result.metadata["correlationId"] == "corr_performance_test", "CorrelationId not preserved"
        assert result.metadata["workflow_type"] == "DEVTEAM_AUTOMATION", "Workflow type not set correctly"
        
        print(f"✅ Performance requirement validated: {execution_time:.3f}s (≤2s)")
        return True
        
    except Exception as e:
        print(f"❌ Performance requirement test failed: {e}")
        return False

def test_event_schema_compatibility():
    """Test integration with existing EventRequest schema."""
    print("🔍 Testing EventRequest schema compatibility...")
    
    try:
        from schemas.event_schema import EventRequest
        
        # Test with comprehensive DEVTEAM_AUTOMATION event
        comprehensive_event = {
            "id": "evt_schema_test",
            "type": "DEVTEAM_AUTOMATION",
            "project_id": "customer-schema/project-test",
            "task": {
                "id": "1.1.1",
                "title": "Schema compatibility test",
                "description": "Test EventRequest schema with DEVTEAM_AUTOMATION",
                "type": "atomic",
                "dependencies": [],
                "files": ["test.py"]
            },
            "priority": "normal",
            "data": {
                "repository_url": "https://github.com/test/repo.git",
                "branch": "main"
            },
            "options": {
                "idempotency_key": "schema_test_key",
                "timeout_seconds": 300
            },
            "metadata": {
                "correlation_id": "corr_schema_test",
                "source": "validation_script",
                "user_id": "test_user"
            }
        }
        
        # Validate event against schema
        validated_event = EventRequest.parse_obj(comprehensive_event)
        assert validated_event.type == "DEVTEAM_AUTOMATION", "Event type validation failed"
        assert validated_event.task is not None, "Task is None"
        assert validated_event.task.id == "1.1.1", "Task ID validation failed"
        assert validated_event.metadata is not None, "Metadata is None"
        assert validated_event.metadata.correlation_id == "corr_schema_test", "CorrelationId validation failed"
        
        # Test with minimal event
        minimal_event = {
            "id": "evt_minimal_test",
            "type": "DEVTEAM_AUTOMATION",
            "project_id": "test/minimal",
            "task": {
                "id": "1.0",
                "title": "Minimal test"
            }
        }
        
        validated_minimal = EventRequest.parse_obj(minimal_event)
        assert validated_minimal.type == "DEVTEAM_AUTOMATION", "Minimal event type validation failed"
        
        print("✅ EventRequest schema compatibility validated")
        return True
        
    except Exception as e:
        print(f"❌ EventRequest schema compatibility test failed: {e}")
        return False

def test_workflow_execution_with_realistic_payload():
    """Test workflow execution with realistic DEVTEAM_AUTOMATION payloads."""
    print("🔍 Testing workflow execution with realistic payloads...")
    
    try:
        from workflows.devteam_automation_workflow import DevTeamAutomationWorkflow
        
        # Test with full-featured payload
        full_payload = {
            "id": "evt_realistic_full",
            "type": "DEVTEAM_AUTOMATION",
            "project_id": "customer-realistic/project-full",
            "task": {
                "id": "3.1.2",
                "title": "Ensure workflow can be resolved by name/id and validate end-to-end integration",
                "description": "Complete end-to-end integration validation with comprehensive test coverage",
                "type": "atomic",
                "dependencies": ["3.1.1"],
                "files": ["tests/test_integration.py"]
            },
            "priority": "high",
            "data": {
                "repository_url": "https://github.com/customer/project.git",
                "branch": "feature/integration",
                "environment": "test"
            },
            "metadata": {
                "correlation_id": "corr_realistic_full",
                "source": "integration_test",
                "user_id": "test_user_realistic"
            }
        }
        
        workflow = DevTeamAutomationWorkflow()
        result = workflow.run(full_payload)
        
        # Verify workflow execution
        assert result is not None, "Workflow result is None"
        assert "SelectNode" in result.nodes, "SelectNode not executed"
        assert "PrepNode" in result.nodes, "PrepNode not executed"
        assert result.nodes["SelectNode"]["status"] == "completed", "SelectNode not completed"
        assert result.nodes["PrepNode"]["status"] == "completed", "PrepNode not completed"
        
        # Verify metadata propagation
        assert result.metadata["correlationId"] == "corr_realistic_full", "CorrelationId not propagated"
        assert result.metadata["workflow_type"] == "DEVTEAM_AUTOMATION", "Workflow type not set"
        assert result.metadata["task_id"] == "3.1.2", "Task ID not propagated"
        assert result.metadata["priority"] == "high", "Priority not propagated"
        
        # Test with minimal payload
        minimal_payload = {
            "id": "evt_realistic_minimal",
            "type": "DEVTEAM_AUTOMATION",
            "project_id": "test/minimal",
            "task": {
                "id": "1.0",
                "title": "Minimal realistic test"
            }
        }
        
        result_minimal = workflow.run(minimal_payload)
        assert result_minimal is not None, "Minimal workflow result is None"
        assert "SelectNode" in result_minimal.nodes, "SelectNode not executed for minimal payload"
        assert "PrepNode" in result_minimal.nodes, "PrepNode not executed for minimal payload"
        
        print("✅ Workflow execution with realistic payloads validated")
        return True
        
    except Exception as e:
        print(f"❌ Workflow execution with realistic payloads failed: {e}")
        return False

def test_correlation_id_propagation():
    """Test correlationId propagation through workflow execution."""
    print("🔍 Testing correlationId propagation...")
    
    try:
        from workflows.devteam_automation_workflow import DevTeamAutomationWorkflow
        
        # Test with provided correlationId
        event_with_correlation = {
            "id": "evt_correlation_test",
            "type": "DEVTEAM_AUTOMATION",
            "project_id": "test/correlation",
            "task": {
                "id": "1.0",
                "title": "Correlation test"
            },
            "metadata": {
                "correlation_id": "corr_explicit_test_123"
            }
        }
        
        workflow = DevTeamAutomationWorkflow()
        result = workflow.run(event_with_correlation)
        
        # Verify correlationId propagation
        assert result.metadata["correlationId"] == "corr_explicit_test_123", "Explicit correlationId not propagated"
        
        # Test without provided correlationId (should generate one)
        event_without_correlation = {
            "id": "evt_no_correlation",
            "type": "DEVTEAM_AUTOMATION",
            "project_id": "test/no-correlation",
            "task": {
                "id": "1.0",
                "title": "No correlation test"
            }
        }
        
        result_no_corr = workflow.run(event_without_correlation)
        
        # Should generate correlationId based on event ID
        expected_correlation = "corr_evt_no_correlation"
        assert result_no_corr.metadata["correlationId"] == expected_correlation, f"Generated correlationId incorrect: {result_no_corr.metadata['correlationId']}"
        
        print("✅ CorrelationId propagation validated")
        return True
        
    except Exception as e:
        print(f"❌ CorrelationId propagation test failed: {e}")
        return False

def main():
    """Run all validation tests."""
    print("🚀 Starting DEVTEAM_AUTOMATION Workflow Integration Validation")
    print("=" * 70)
    
    tests = [
        test_workflow_registry_resolution,
        test_workflow_type_determination,
        test_performance_requirement,
        test_event_schema_compatibility,
        test_workflow_execution_with_realistic_payload,
        test_correlation_id_propagation
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            failed += 1
        print()
    
    print("=" * 70)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All DEVTEAM_AUTOMATION integration tests passed!")
        print("✅ End-to-end integration validation successful")
        return 0
    else:
        print("⚠️  Some tests failed. Please review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())