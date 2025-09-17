#!/usr/bin/env python3
"""
Task 7.8.1 Status Projection Update - Simple Validation Script

This script validates the core functionality of the status projection update implementation
with simplified testing that focuses on the essential requirements.
"""

import sys
import os

# Add the app directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_imports():
    """Test that all required modules can be imported."""
    print("--- Import Tests ---")
    try:
        from services.status_projection_service import StatusProjectionService, get_status_projection_service
        from services.aider_execution_service import AiderExecutionService
        from schemas.status_projection_schema import StatusProjection, ExecutionStatus
        from schemas.websocket_envelope import create_execution_update_envelope, create_completion_envelope
        print("✓ All required imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_method_existence():
    """Test that required methods exist."""
    print("\n--- Method Existence Tests ---")
    try:
        from services.status_projection_service import StatusProjectionService
        from services.aider_execution_service import AiderExecutionService
        
        # Check StatusProjectionService methods
        if hasattr(StatusProjectionService, 'update_status_projection_to_completed'):
            print("✓ StatusProjectionService.update_status_projection_to_completed exists")
        else:
            print("✗ StatusProjectionService.update_status_projection_to_completed missing")
            return False
            
        # Check AiderExecutionService integration
        if hasattr(AiderExecutionService, '_trigger_status_projection_completion'):
            print("✓ AiderExecutionService._trigger_status_projection_completion exists")
        else:
            print("✗ AiderExecutionService._trigger_status_projection_completion missing")
            return False
            
        return True
    except Exception as e:
        print(f"✗ Method existence test failed: {e}")
        return False

def test_websocket_envelopes():
    """Test WebSocket envelope creation."""
    print("\n--- WebSocket Envelope Tests ---")
    try:
        from schemas.websocket_envelope import create_execution_update_envelope, create_completion_envelope
        
        # Test execution update envelope
        update_envelope = create_execution_update_envelope(
            project_id="test-project",
            execution_id="test-execution-id",
            status="completed",
            progress=100.0,
            current_task="7.8.1",
            totals={"completed": 2, "total": 2},
            branch="main",
            updated_at="2023-01-01T00:00:00Z",
            event_type="completion"
        )
        
        if isinstance(update_envelope, dict):
            print("✓ Execution update envelope created successfully")
        else:
            print("✗ Execution update envelope creation failed")
            return False
        
        # Test completion envelope
        completion_envelope = create_completion_envelope(
            project_id="test-project",
            execution_id="test-execution-id",
            status="completed",
            final_result="success",
            duration_ms=1500.0,
            completed_tasks=2,
            total_tasks=2
        )
        
        if isinstance(completion_envelope, dict):
            print("✓ Completion envelope created successfully")
        else:
            print("✗ Completion envelope creation failed")
            return False
            
        return True
    except Exception as e:
        print(f"✗ WebSocket envelope test failed: {e}")
        return False

def test_status_projection_schema():
    """Test StatusProjection schema validation."""
    print("\n--- StatusProjection Schema Tests ---")
    try:
        from schemas.status_projection_schema import StatusProjection, ExecutionStatus, TaskTotals
        from datetime import datetime, timezone
        
        # Test creating a valid StatusProjection
        projection = StatusProjection(
            execution_id="test-execution-id",
            project_id="test-project",
            status=ExecutionStatus.COMPLETED,
            progress=100.0,
            current_task="7.8.1",
            totals=TaskTotals(completed=2, total=2),
            customer_id="test-customer",
            started_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            branch="main"
        )
        
        if projection.status == ExecutionStatus.COMPLETED:
            print("✓ StatusProjection schema validation successful")
            return True
        else:
            print("✗ StatusProjection schema validation failed")
            return False
            
    except Exception as e:
        print(f"✗ StatusProjection schema test failed: {e}")
        return False

def test_execution_status_enum():
    """Test ExecutionStatus enum functionality."""
    print("\n--- ExecutionStatus Enum Tests ---")
    try:
        from schemas.status_projection_schema import ExecutionStatus
        
        # Test enum values
        if ExecutionStatus.COMPLETED.value == "completed":
            print("✓ ExecutionStatus.COMPLETED has correct value")
        else:
            print("✗ ExecutionStatus.COMPLETED has incorrect value")
            return False
            
        if ExecutionStatus.RUNNING.value == "running":
            print("✓ ExecutionStatus.RUNNING has correct value")
        else:
            print("✗ ExecutionStatus.RUNNING has incorrect value")
            return False
            
        return True
    except Exception as e:
        print(f"✗ ExecutionStatus enum test failed: {e}")
        return False

def test_validation_functions():
    """Test status validation functions."""
    print("\n--- Validation Function Tests ---")
    try:
        from schemas.status_projection_schema import validate_status_transition
        
        # Test valid transitions
        if validate_status_transition("running", "completed"):
            print("✓ Valid transition (running → completed) accepted")
        else:
            print("✗ Valid transition (running → completed) rejected")
            return False
            
        # Test invalid transitions
        if not validate_status_transition("completed", "running"):
            print("✓ Invalid transition (completed → running) rejected")
        else:
            print("✗ Invalid transition (completed → running) accepted")
            return False
            
        return True
    except Exception as e:
        print(f"✗ Validation function test failed: {e}")
        return False

def run_validation():
    """Run all validation tests."""
    print("=" * 80)
    print("Task 7.8.1 Status Projection Update - Simple Validation")
    print("=" * 80)
    
    tests = [
        ("Import Tests", test_imports),
        ("Method Existence Tests", test_method_existence),
        ("WebSocket Envelope Tests", test_websocket_envelopes),
        ("StatusProjection Schema Tests", test_status_projection_schema),
        ("ExecutionStatus Enum Tests", test_execution_status_enum),
        ("Validation Function Tests", test_validation_functions),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{status:4} | {test_name}")
    
    print("-" * 80)
    print(f"Total: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 All validation tests passed! Core functionality is implemented correctly.")
        return True
    else:
        print(f"\n❌ {total - passed} validation tests failed. Please review the implementation.")
        return False

if __name__ == "__main__":
    success = run_validation()
    sys.exit(0 if success else 1)