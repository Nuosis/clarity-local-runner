#!/usr/bin/env python3
"""
Technical Validation Script for Status Projection Schema

This script validates that the status projection schema implementation:
1. Loads without import errors
2. Creates valid schema instances
3. Performs field validation correctly
4. Handles state transitions properly
5. Integrates with existing Event.task_context patterns
6. Meets performance requirements

Usage:
    python validate_status_projection_schema.py
"""

import sys
import time
import traceback
from datetime import datetime
from typing import Dict, Any


def validate_imports():
    """Validate that all schema imports work correctly."""
    print("🔍 Validating imports...")
    
    try:
        from schemas.status_projection_schema import (
            StatusProjection,
            ExecutionStatus,
            TaskTotals,
            ExecutionArtifacts,
            project_status_from_task_context,
            validate_status_transition
        )
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"❌ Unexpected error during import: {e}")
        traceback.print_exc()
        return False


def validate_basic_schema_creation():
    """Validate basic schema creation and field access."""
    print("\n🔍 Validating basic schema creation...")
    
    try:
        from schemas.status_projection_schema import StatusProjection, ExecutionStatus
        
        # Test minimal valid projection
        projection_data = {
            "execution_id": "exec_validation_001",
            "project_id": "customer-123/project-validation",
            "status": "running",
            "progress": 42.5,
            "current_task": "1.2.1",
            "customer_id": "customer-123",
            "branch": "main",
            "started_at": None
        }
        
        projection = StatusProjection(**projection_data)
        
        # Validate field access
        assert projection.execution_id == "exec_validation_001"
        assert projection.project_id == "customer-123/project-validation"
        assert projection.status == ExecutionStatus.RUNNING
        assert projection.progress == 42.5
        assert projection.current_task == "1.2.1"
        assert projection.customer_id == "customer-123"
        assert projection.branch == "main"
        
        print("✅ Basic schema creation successful")
        return True
        
    except Exception as e:
        print(f"❌ Schema creation failed: {e}")
        traceback.print_exc()
        return False


def validate_field_validation():
    """Validate field validation rules."""
    print("\n🔍 Validating field validation...")
    
    try:
        from schemas.status_projection_schema import StatusProjection
        from pydantic import ValidationError
        
        base_data = {
            "execution_id": "exec_valid",
            "project_id": "test/project",
            "status": "idle",
            "progress": 0.0,
            "current_task": None,
            "customer_id": None,
            "branch": None,
            "started_at": None
        }
        
        # Test valid data
        projection = StatusProjection(**base_data)
        assert projection.execution_id == "exec_valid"
        
        # Test invalid execution_id
        try:
            invalid_data = base_data.copy()
            invalid_data["execution_id"] = "invalid@id!"
            StatusProjection(**invalid_data)
            print("❌ Should have failed validation for invalid execution_id")
            return False
        except ValidationError:
            pass  # Expected
        
        # Test invalid progress
        try:
            invalid_data = base_data.copy()
            invalid_data["progress"] = 150.0
            StatusProjection(**invalid_data)
            print("❌ Should have failed validation for invalid progress")
            return False
        except ValidationError:
            pass  # Expected
        
        print("✅ Field validation working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Field validation test failed: {e}")
        traceback.print_exc()
        return False


def validate_state_transitions():
    """Validate state transition logic."""
    print("\n🔍 Validating state transitions...")
    
    try:
        from schemas.status_projection_schema import validate_status_transition
        
        # Test valid transitions
        valid_transitions = [
            ("idle", "initializing"),
            ("initializing", "running"),
            ("running", "paused"),
            ("paused", "running"),
            ("running", "completed"),
            ("running", "error")
        ]
        
        for from_status, to_status in valid_transitions:
            if not validate_status_transition(from_status, to_status):
                print(f"❌ Valid transition {from_status} -> {to_status} failed")
                return False
        
        # Test invalid transitions
        invalid_transitions = [
            ("idle", "running"),
            ("completed", "running"),
            ("error", "running"),
            ("idle", "completed")
        ]
        
        for from_status, to_status in invalid_transitions:
            if validate_status_transition(from_status, to_status):
                print(f"❌ Invalid transition {from_status} -> {to_status} should have failed")
                return False
        
        print("✅ State transitions working correctly")
        return True
        
    except Exception as e:
        print(f"❌ State transition validation failed: {e}")
        traceback.print_exc()
        return False


def validate_task_context_projection():
    """Validate projection from task context."""
    print("\n🔍 Validating task context projection...")
    
    try:
        from schemas.status_projection_schema import project_status_from_task_context
        
        # Test task context similar to existing patterns
        task_context = {
            "metadata": {
                "status": "prepared",
                "task_id": "1.1.1",
                "branch": "main",
                "customer_id": "customer-123"
            },
            "nodes": {
                "SelectNode": {"status": "completed"},
                "PrepNode": {"status": "running"}
            }
        }
        
        projection = project_status_from_task_context(
            task_context=task_context,
            execution_id="exec_context_test",
            project_id="customer-123/project-context"
        )
        
        assert projection.execution_id == "exec_context_test"
        assert projection.project_id == "customer-123/project-context"
        assert projection.current_task == "1.1.1"
        assert projection.customer_id == "customer-123"
        assert projection.branch == "main"
        
        print("✅ Task context projection working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Task context projection failed: {e}")
        traceback.print_exc()
        return False


def validate_performance():
    """Validate performance requirements."""
    print("\n🔍 Validating performance...")
    
    try:
        from schemas.status_projection_schema import StatusProjection
        
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
        
        # Test creation performance (should be well under 2s for 1000 instances)
        start_time = time.time()
        for i in range(1000):
            data = projection_data.copy()
            data["execution_id"] = f"exec_perf_{i}"
            projection = StatusProjection(**data)
        end_time = time.time()
        
        duration = end_time - start_time
        print(f"📊 Created 1000 projections in {duration:.3f}s")
        
        if duration > 2.0:
            print(f"❌ Performance requirement not met: {duration}s > 2s")
            return False
        
        print("✅ Performance requirements met")
        return True
        
    except Exception as e:
        print(f"❌ Performance validation failed: {e}")
        traceback.print_exc()
        return False


def validate_json_serialization():
    """Validate JSON serialization/deserialization."""
    print("\n🔍 Validating JSON serialization...")
    
    try:
        from schemas.status_projection_schema import StatusProjection, TaskTotals, ExecutionArtifacts
        
        # Create complex projection with all fields
        projection_data = {
            "execution_id": "exec_json_test",
            "project_id": "customer-456/project-json",
            "status": "running",
            "progress": 67.8,
            "current_task": "2.1.3",
            "customer_id": "customer-456",
            "branch": "feature/json-test",
            "started_at": datetime.now(),
            "totals": TaskTotals(completed=3, total=8),
            "artifacts": ExecutionArtifacts(
                repo_path="/workspace/repos/test",
                branch="feature/json-test",
                logs=["Started", "Processing", "Almost done"],
                files_modified=["src/app.py", "tests/test_app.py"]
            )
        }
        
        projection = StatusProjection(**projection_data)
        
        # Test JSON serialization
        json_data = projection.dict()
        assert json_data["execution_id"] == "exec_json_test"
        assert json_data["status"] == "running"
        assert json_data["progress"] == 67.8
        
        # Test round-trip
        new_projection = StatusProjection(**json_data)
        assert new_projection.execution_id == projection.execution_id
        assert new_projection.status == projection.status
        assert new_projection.progress == projection.progress
        
        print("✅ JSON serialization working correctly")
        return True
        
    except Exception as e:
        print(f"❌ JSON serialization failed: {e}")
        traceback.print_exc()
        return False


def run_simple_tests():
    """Run simple unit tests to verify functionality."""
    print("\n🔍 Running simple unit tests...")
    
    try:
        # Import and run the simple test file
        import subprocess
        import os
        
        # Change to app directory for proper imports
        original_dir = os.getcwd()
        if not os.path.exists("app"):
            print("❌ App directory not found, running from current directory")
        else:
            os.chdir("app")
        
        try:
            # Run the simple test file directly
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                "../tests/test_status_projection_schema_simple.py", 
                "-v", "--tb=short"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✅ Simple unit tests passed")
                print(f"📊 Test output:\n{result.stdout}")
                return True
            else:
                print(f"❌ Simple unit tests failed")
                print(f"📊 Test output:\n{result.stdout}")
                print(f"📊 Test errors:\n{result.stderr}")
                return False
                
        finally:
            os.chdir(original_dir)
            
    except Exception as e:
        print(f"❌ Simple unit tests execution failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Main validation function."""
    print("🚀 Starting Status Projection Schema Technical Validation")
    print("=" * 60)
    
    validation_results = []
    
    # Run all validation tests
    validation_tests = [
        ("Import Validation", validate_imports),
        ("Basic Schema Creation", validate_basic_schema_creation),
        ("Field Validation", validate_field_validation),
        ("State Transitions", validate_state_transitions),
        ("Task Context Projection", validate_task_context_projection),
        ("Performance", validate_performance),
        ("JSON Serialization", validate_json_serialization),
        ("Simple Unit Tests", run_simple_tests)
    ]
    
    for test_name, test_func in validation_tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            validation_results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            validation_results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("📊 VALIDATION SUMMARY")
    print("="*60)
    
    passed = 0
    total = len(validation_results)
    
    for test_name, result in validation_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n📈 Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 ALL VALIDATIONS PASSED!")
        print("✅ Status projection schema is technically validated and ready for use")
        return True
    else:
        print(f"\n⚠️  {total-passed} validation(s) failed")
        print("❌ Status projection schema requires fixes before deployment")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)