#!/usr/bin/env python3
"""
Test script to verify worker logging with correlationId.

This script sends a test event to the API and monitors the worker logs
to verify that correlationId appears in structured logging fields.
"""

import requests
import json
import time
import uuid
from datetime import datetime

def send_test_event():
    """Send a test event to the API endpoint."""
    
    # Generate unique identifiers for tracing
    correlation_id = f"test_correlation_{uuid.uuid4().hex[:8]}"
    event_id = f"test_event_{uuid.uuid4().hex[:8]}"
    
    # Test event payload
    test_event = {
        "id": event_id,
        "type": "PLACEHOLDER",
        "project_id": "test-project/worker-logging",
        "data": {
            "test_field": "worker_logging_test",
            "timestamp": datetime.now().isoformat(),
            "purpose": "verify correlationId in worker logs"
        },
        "metadata": {
            "correlation_id": correlation_id,
            "source": "test_script",
            "user_id": "test_user_debug"
        }
    }
    
    print(f"🚀 Sending test event:")
    print(f"   Event ID: {event_id}")
    print(f"   Correlation ID: {correlation_id}")
    print(f"   Timestamp: {datetime.now().isoformat()}")
    
    try:
        # Send POST request to the events endpoint
        response = requests.post(
            "http://localhost:8090/process/events/",
            json=test_event,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"\n📡 API Response:")
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 202:
            response_data = response.json()
            print(f"   Response: {json.dumps(response_data, indent=2)}")
            print(f"\n✅ Event successfully dispatched!")
            print(f"   Task ID: {response_data.get('task_id', 'N/A')}")
            print(f"   Event ID: {response_data.get('event_id', 'N/A')}")
            print(f"   Correlation ID: {response_data.get('correlation_id', 'N/A')}")
            
            return {
                "success": True,
                "correlation_id": correlation_id,
                "event_id": event_id,
                "task_id": response_data.get('task_id'),
                "api_response": response_data
            }
        else:
            print(f"   Error: {response.text}")
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}",
                "correlation_id": correlation_id,
                "event_id": event_id
            }
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "correlation_id": correlation_id,
            "event_id": event_id
        }

def main():
    """Main test function."""
    print("=" * 60)
    print("🔍 WORKER LOGGING TEST - CorrelationId Verification")
    print("=" * 60)
    
    # Send test event
    result = send_test_event()
    
    if result["success"]:
        print(f"\n⏳ Waiting 3 seconds for worker processing...")
        time.sleep(3)
        
        print(f"\n📋 Test Summary:")
        print(f"   ✅ Event dispatched successfully")
        print(f"   🔗 Correlation ID: {result['correlation_id']}")
        print(f"   📦 Event ID: {result['event_id']}")
        print(f"   🏷️  Task ID: {result.get('task_id', 'N/A')}")
        
        print(f"\n🔍 Next Steps:")
        print(f"   1. Check worker logs: docker logs clarity-local_celery_worker --tail 20")
        print(f"   2. Look for correlation_id: {result['correlation_id']}")
        print(f"   3. Verify structured logging fields are present")
        
    else:
        print(f"\n❌ Test failed:")
        print(f"   Error: {result['error']}")
        print(f"   🔗 Correlation ID: {result['correlation_id']}")
        print(f"   📦 Event ID: {result['event_id']}")

if __name__ == "__main__":
    main()