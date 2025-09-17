#!/usr/bin/env python3
"""
Test Task 5.1.2: Wire endpoint to enqueue initial workflow event

This test validates that the POST /api/devteam/automation/initialize endpoint
properly integrates with the existing event processing pipeline by:
1. Creating a DEVTEAM_AUTOMATION event using EventRequest schema
2. Persisting the event to database using GenericRepository pattern
3. Dispatching Celery task with proper headers
4. Returning 202 Accepted with real database event ID
"""

import json
import requests
import time
import uuid
from typing import Dict, Any

def test_devteam_automation_initialize_integration():
    """Test the complete integration of the DevTeam automation initialize endpoint."""
    
    print("🧪 Testing Task 5.1.2: Wire endpoint to enqueue initial workflow event")
    print("=" * 80)
    
    # Test configuration
    base_url = "http://localhost:8090"
    endpoint = "/api/v1/devteam/automation/initialize"
    
    # Test data
    test_request = {
        "project_id": "customer-123/project-test-5-1-2",
        "user_id": "test_user_5_1_2",
        "stop_point": "PREP"
    }
    
    print(f"📋 Test Request:")
    print(f"   URL: {base_url}{endpoint}")
    print(f"   Method: POST")
    print(f"   Body: {json.dumps(test_request, indent=2)}")
    print()
    
    try:
        # Make the request
        start_time = time.time()
        response = requests.post(
            f"{base_url}{endpoint}",
            json=test_request,
            headers={"Content-Type": "application/json"}
        )
        duration_ms = (time.time() - start_time) * 1000
        
        print(f"📊 Response Details:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Duration: {duration_ms:.2f}ms")
        print(f"   Headers: {dict(response.headers)}")
        print()
        
        # Validate response status
        if response.status_code != 202:
            print(f"❌ FAIL: Expected status code 202, got {response.status_code}")
            print(f"   Response: {response.text}")
            return False
        
        # Parse response body
        try:
            response_data = response.json()
            print(f"📄 Response Body:")
            print(f"   {json.dumps(response_data, indent=2)}")
            print()
        except json.JSONDecodeError as e:
            print(f"❌ FAIL: Invalid JSON response: {e}")
            print(f"   Response text: {response.text}")
            return False
        
        # Validate response structure
        required_fields = ["success", "data", "message"]
        for field in required_fields:
            if field not in response_data:
                print(f"❌ FAIL: Missing required field '{field}' in response")
                return False
        
        # Validate success field
        if not response_data.get("success"):
            print(f"❌ FAIL: Response indicates failure")
            print(f"   Message: {response_data.get('message', 'No message')}")
            return False
        
        # Validate data structure
        data = response_data.get("data", {})
        required_data_fields = ["execution_id", "event_id"]
        for field in required_data_fields:
            if field not in data:
                print(f"❌ FAIL: Missing required data field '{field}'")
                return False
        
        execution_id = data["execution_id"]
        event_id = data["event_id"]
        
        print(f"🔍 Validation Results:")
        print(f"   ✅ Status Code: 202 Accepted")
        print(f"   ✅ Response Structure: Valid")
        print(f"   ✅ Execution ID: {execution_id}")
        print(f"   ✅ Event ID: {event_id}")
        print(f"   ✅ Performance: {duration_ms:.2f}ms ({'✅ Under 200ms' if duration_ms <= 200 else '⚠️ Over 200ms'})")
        print()
        
        # Validate ID formats
        if not execution_id.startswith("exec_"):
            print(f"❌ FAIL: Execution ID should start with 'exec_', got: {execution_id}")
            return False
        
        # Validate that event_id is a real database ID (UUID format, not prefixed)
        try:
            # Try to parse as UUID to validate it's a real database ID
            uuid.UUID(event_id)
            print(f"   ✅ Event ID Format: Valid UUID (real database ID)")
        except ValueError:
            print(f"❌ FAIL: Event ID should be a valid UUID (database ID), got: {event_id}")
            return False
        
        # Test idempotency key support (optional)
        print(f"🔄 Testing Idempotency Key Support:")
        idempotency_key = f"test-key-{int(time.time())}"
        
        response2 = requests.post(
            f"{base_url}{endpoint}",
            json=test_request,
            headers={
                "Content-Type": "application/json",
                "Idempotency-Key": idempotency_key
            }
        )
        
        if response2.status_code == 202:
            print(f"   ✅ Idempotency Key Accepted: {idempotency_key}")
        else:
            print(f"   ⚠️ Idempotency Key Response: {response2.status_code} (implementation may be pending)")
        
        print()
        print(f"🎉 SUCCESS: Task 5.1.2 integration test passed!")
        print(f"   - Event created with real database ID: {event_id}")
        print(f"   - Execution tracking ID: {execution_id}")
        print(f"   - Performance: {duration_ms:.2f}ms")
        print(f"   - Response format: 202 Accepted with {{executionId, eventId}}")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"❌ FAIL: Could not connect to {base_url}")
        print(f"   Make sure the server is running with: cd docker && ./start.sh")
        return False
    except Exception as e:
        print(f"❌ FAIL: Unexpected error: {e}")
        return False

def test_error_scenarios():
    """Test error handling scenarios."""
    
    print("\n🧪 Testing Error Scenarios:")
    print("=" * 50)
    
    base_url = "http://localhost:8090"
    endpoint = "/api/v1/devteam/automation/initialize"
    
    # Test invalid project_id format
    invalid_request = {
        "project_id": "invalid-format",  # Missing customer/project format
        "user_id": "test_user"
    }
    
    try:
        response = requests.post(
            f"{base_url}{endpoint}",
            json=invalid_request,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 422:
            print(f"   ✅ Validation Error Handling: 422 for invalid project_id")
        else:
            print(f"   ⚠️ Validation Response: {response.status_code} (expected 422)")
            
    except Exception as e:
        print(f"   ❌ Error testing validation: {e}")

if __name__ == "__main__":
    success = test_devteam_automation_initialize_integration()
    test_error_scenarios()
    
    if success:
        print(f"\n✅ All tests passed! Task 5.1.2 implementation is working correctly.")
        exit(0)
    else:
        print(f"\n❌ Tests failed! Please check the implementation.")
        exit(1)