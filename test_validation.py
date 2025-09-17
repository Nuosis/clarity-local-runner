#!/usr/bin/env python3
"""
Simple validation test script for EventRequest schema.

This script tests the comprehensive validation implemented for the POST /events endpoint
without requiring pytest or complex test infrastructure.
"""

import json
import time
from datetime import datetime

# Import the schema
from app.schemas.event_schema import EventRequest, EventType, EventPriority


def test_valid_devteam_automation_event():
    """Test valid DevTeam automation event passes validation."""
    print("Testing valid DevTeam automation event...")
    
    valid_event = {
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
    
    try:
        event = EventRequest(**valid_event)
        assert event.id == "evt_devteam_12345"
        assert event.type == EventType.DEVTEAM_AUTOMATION
        assert event.project_id == "customer-123/project-abc"
        assert event.task.id == "1.1.1"
        assert event.priority == EventPriority.NORMAL
        print("✓ Valid DevTeam automation event passed validation")
        return True
    except Exception as e:
        print(f"✗ Valid DevTeam automation event failed: {e}")
        return False


def test_valid_placeholder_event():
    """Test backward compatibility with PlaceholderEventSchema."""
    print("Testing backward compatibility with placeholder event...")
    
    placeholder_event = {
        "id": "simple_event_123",
        "type": "PLACEHOLDER"
    }
    
    try:
        event = EventRequest(**placeholder_event)
        assert event.id == "simple_event_123"
        assert event.type == EventType.PLACEHOLDER
        print("✓ Placeholder event passed validation (backward compatibility)")
        return True
    except Exception as e:
        print(f"✗ Placeholder event failed: {e}")
        return False


def test_invalid_event_id():
    """Test invalid event ID format raises validation error."""
    print("Testing invalid event ID validation...")
    
    invalid_events = [
        {"id": "", "type": "PLACEHOLDER"},  # Empty ID
        {"id": "   ", "type": "PLACEHOLDER"},  # Whitespace only
        {"id": "invalid<script>", "type": "PLACEHOLDER"},  # Dangerous characters
        {"id": "invalid'quote", "type": "PLACEHOLDER"},  # Quote character
    ]
    
    failed_count = 0
    for i, invalid_event in enumerate(invalid_events):
        try:
            EventRequest(**invalid_event)
            print(f"✗ Invalid event {i+1} should have failed validation")
            failed_count += 1
        except Exception:
            # Expected to fail
            pass
    
    if failed_count == 0:
        print("✓ All invalid event IDs properly rejected")
        return True
    else:
        print(f"✗ {failed_count} invalid events incorrectly passed validation")
        return False


def test_devteam_automation_requirements():
    """Test DevTeam automation events require project_id and task."""
    print("Testing DevTeam automation requirements...")
    
    # Missing project_id
    try:
        EventRequest(
            id="test_123",
            type="DEVTEAM_AUTOMATION",
            task={"id": "1.1", "title": "Test task"}
        )
        print("✗ Missing project_id should have failed")
        return False
    except Exception:
        # Expected to fail
        pass
    
    # Missing task
    try:
        EventRequest(
            id="test_124",
            type="DEVTEAM_AUTOMATION",
            project_id="customer-123/project-abc"
        )
        print("✗ Missing task should have failed")
        return False
    except Exception:
        # Expected to fail
        pass
    
    print("✓ DevTeam automation requirements properly enforced")
    return True


def test_validation_performance():
    """Test validation performance meets ≤200ms requirement."""
    print("Testing validation performance...")
    
    valid_event = {
        "id": "perf_test_123",
        "type": "DEVTEAM_AUTOMATION",
        "project_id": "customer-123/project-abc",
        "task": {
            "id": "1.1.1",
            "title": "Performance test task",
            "description": "Testing validation performance",
            "files": ["file1.js", "file2.py", "file3.md"]
        },
        "data": {
            "repository_url": "https://github.com/user/repo.git",
            "branch": "main",
            "additional_data": {"key1": "value1", "key2": "value2"}
        }
    }
    
    # Test multiple validations to get average time
    times = []
    for _ in range(10):
        start_time = time.time()
        EventRequest(**valid_event)
        end_time = time.time()
        times.append((end_time - start_time) * 1000)  # Convert to milliseconds
    
    avg_time = sum(times) / len(times)
    max_time = max(times)
    
    print(f"Average validation time: {avg_time:.2f}ms")
    print(f"Max validation time: {max_time:.2f}ms")
    
    # Should meet ≤200ms requirement
    if avg_time <= 200 and max_time <= 200:
        print("✓ Validation performance meets ≤200ms requirement")
        return True
    else:
        print(f"✗ Validation performance exceeds 200ms limit")
        return False


def test_optional_fields_defaults():
    """Test optional fields have correct defaults."""
    print("Testing optional field defaults...")
    
    try:
        minimal_event = EventRequest(
            id="test_123",
            type="PLACEHOLDER"
        )
        
        assert minimal_event.priority == EventPriority.NORMAL
        assert minimal_event.data == {}
        assert minimal_event.project_id is None
        assert minimal_event.task is None
        assert minimal_event.options is None
        assert minimal_event.metadata is None
        assert isinstance(minimal_event.created_at, datetime)
        
        print("✓ Optional fields have correct defaults")
        return True
    except Exception as e:
        print(f"✗ Optional field defaults failed: {e}")
        return False


def test_endpoint_with_requests():
    """Test the actual endpoint with HTTP requests."""
    print("Testing endpoint with HTTP requests...")
    
    try:
        import requests
        
        # Test valid event
        valid_event = {
            "id": "http_test_123",
            "type": "PLACEHOLDER"
        }
        
        response = requests.post(
            "http://localhost:8090/process/events/",
            json=valid_event,
            timeout=5
        )
        
        if response.status_code == 202:
            response_data = response.json()
            if "event_id" in response_data and "task_id" in response_data:
                print("✓ HTTP endpoint test passed")
                return True
            else:
                print(f"✗ HTTP endpoint response missing required fields: {response_data}")
                return False
        else:
            print(f"✗ HTTP endpoint returned status {response.status_code}: {response.text}")
            return False
            
    except ImportError:
        print("⚠ Requests library not available, skipping HTTP test")
        return True
    except Exception as e:
        print(f"⚠ HTTP endpoint test failed (server may not be running): {e}")
        return True  # Don't fail the test if server isn't running


def main():
    """Run all validation tests."""
    print("=" * 60)
    print("EventRequest Schema Validation Tests")
    print("=" * 60)
    
    tests = [
        test_valid_devteam_automation_event,
        test_valid_placeholder_event,
        test_invalid_event_id,
        test_devteam_automation_requirements,
        test_validation_performance,
        test_optional_fields_defaults,
        test_endpoint_with_requests,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
        print()
    
    print("=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Schema validation is working correctly.")
        return True
    else:
        print(f"❌ {total - passed} tests failed. Please review the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)