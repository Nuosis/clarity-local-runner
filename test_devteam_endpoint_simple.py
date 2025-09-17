#!/usr/bin/env python3
"""
Simple test for DevTeam Automation Initialize Endpoint using urllib

This script validates the POST /api/v1/devteam/automation/initialize endpoint
without external dependencies.
"""

import json
import time
import uuid
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, Any


def test_devteam_endpoint():
    """Test the DevTeam automation initialize endpoint."""
    print("🧪 Testing DevTeam Automation Initialize Endpoint")
    print("=" * 60)
    
    # Test data
    payload = {
        "project_id": "customer-123/project-abc",
        "user_id": "user_test_123",
        "stop_point": "PREP"
    }
    
    # Convert to JSON
    data = json.dumps(payload).encode('utf-8')
    
    # Create request
    url = "http://localhost:8090/api/v1/devteam/automation/initialize"
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            'Content-Type': 'application/json',
            'Content-Length': str(len(data))
        },
        method='POST'
    )
    
    try:
        # Measure performance
        start_time = time.time()
        
        # Make request
        with urllib.request.urlopen(req, timeout=10) as response:
            duration_ms = (time.time() - start_time) * 1000
            
            # Read response
            response_data = json.loads(response.read().decode('utf-8'))
            status_code = response.getcode()
            
            print(f"✅ Request successful!")
            print(f"   - Status Code: {status_code}")
            print(f"   - Duration: {duration_ms:.2f}ms")
            print(f"   - Response: {json.dumps(response_data, indent=2)}")
            
            # Validate response
            if status_code == 202:
                if "data" in response_data:
                    data = response_data["data"]
                    if "execution_id" in data and "event_id" in data:
                        print("✅ Response format is correct!")
                        print(f"   - Execution ID: {data['execution_id']}")
                        print(f"   - Event ID: {data['event_id']}")
                        
                        # Check performance requirement
                        if duration_ms <= 200:
                            print("✅ Performance requirement met (≤200ms)")
                        else:
                            print(f"⚠️  Performance requirement not met: {duration_ms:.2f}ms > 200ms")
                        
                        return True
                    else:
                        print("❌ Response missing required fields (execution_id, event_id)")
                else:
                    print("❌ Response missing 'data' field")
            else:
                print(f"❌ Unexpected status code: {status_code} (expected 202)")
                
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error: {e.code} - {e.reason}")
        try:
            error_response = json.loads(e.read().decode('utf-8'))
            print(f"   Error details: {json.dumps(error_response, indent=2)}")
        except:
            print(f"   Raw error: {e.read().decode('utf-8')}")
    except urllib.error.URLError as e:
        print(f"❌ URL Error: {e.reason}")
        print("   Is the server running? Try: cd docker && ./start.sh")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
    
    return False


def test_health_endpoint():
    """Test the health endpoint to verify server is running."""
    print("🔍 Checking server health...")
    
    try:
        with urllib.request.urlopen("http://localhost:8090/health", timeout=5) as response:
            if response.getcode() == 200:
                print("✅ Server is healthy and running")
                return True
            else:
                print(f"⚠️  Server returned status: {response.getcode()}")
                return False
    except Exception as e:
        print(f"❌ Cannot connect to server: {str(e)}")
        print("   Please ensure the server is running with: cd docker && ./start.sh")
        return False


def main():
    """Main test function."""
    print("DevTeam Automation Initialize Endpoint Test")
    print("=" * 60)
    
    # Check server health first
    if not test_health_endpoint():
        return 1
    
    print()
    
    # Test the endpoint
    if test_devteam_endpoint():
        print("\n🎉 Test completed successfully!")
        return 0
    else:
        print("\n❌ Test failed!")
        return 1


if __name__ == "__main__":
    exit(main())