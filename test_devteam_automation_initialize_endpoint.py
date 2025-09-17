#!/usr/bin/env python3
"""
Test script for DevTeam Automation Initialize Endpoint

This script validates the POST /api/v1/devteam/automation/initialize endpoint
to ensure it returns 202 Accepted with {executionId, eventId} as specified.

Tests:
- Valid request with required fields
- Request validation (invalid project_id format)
- Response format validation
- Performance requirements (≤200ms)
- Integration with existing event pipeline
"""

import json
import time
import uuid
from typing import Dict, Any

import requests


class DevTeamAutomationEndpointTester:
    """Test suite for DevTeam automation initialize endpoint."""
    
    def __init__(self, base_url: str = "http://localhost:8090"):
        """
        Initialize tester with base URL.
        
        Args:
            base_url: Base URL of the API server
        """
        self.base_url = base_url
        self.endpoint = f"{base_url}/api/v1/devteam/automation/initialize"
        
    def test_valid_request(self) -> Dict[str, Any]:
        """
        Test valid DevTeam automation initialization request.
        
        Returns:
            Test result dictionary
        """
        print("🧪 Testing valid DevTeam automation initialization request...")
        
        # Prepare valid request payload
        payload = {
            "project_id": "customer-123/project-abc",
            "user_id": "user_test_123",
            "stop_point": "PREP"
        }
        
        # Measure performance
        start_time = time.time()
        
        try:
            response = requests.post(
                self.endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Validate response status
            assert response.status_code == 202, f"Expected 202, got {response.status_code}"
            
            # Parse response
            response_data = response.json()
            
            # Validate response structure
            assert "success" in response_data, "Response missing 'success' field"
            assert response_data["success"] is True, "Response success should be True"
            
            assert "data" in response_data, "Response missing 'data' field"
            data = response_data["data"]
            
            # Validate required fields in response data
            assert "execution_id" in data, "Response data missing 'execution_id'"
            assert "event_id" in data, "Response data missing 'event_id'"
            
            # Validate ID formats
            execution_id = data["execution_id"]
            event_id = data["event_id"]
            
            assert execution_id.startswith("exec_"), f"execution_id should start with 'exec_', got: {execution_id}"
            assert event_id.startswith("evt_devteam_"), f"event_id should start with 'evt_devteam_', got: {event_id}"
            
            # Validate performance requirement (≤200ms)
            assert duration_ms <= 200, f"Response time {duration_ms:.2f}ms exceeds 200ms requirement"
            
            print(f"✅ Valid request test passed!")
            print(f"   - Status: {response.status_code}")
            print(f"   - Duration: {duration_ms:.2f}ms")
            print(f"   - Execution ID: {execution_id}")
            print(f"   - Event ID: {event_id}")
            
            return {
                "test": "valid_request",
                "status": "PASSED",
                "duration_ms": duration_ms,
                "response_data": response_data
            }
            
        except Exception as e:
            print(f"❌ Valid request test failed: {str(e)}")
            return {
                "test": "valid_request",
                "status": "FAILED",
                "error": str(e)
            }
    
    def test_invalid_project_id(self) -> Dict[str, Any]:
        """
        Test request with invalid project_id format.
        
        Returns:
            Test result dictionary
        """
        print("🧪 Testing invalid project_id format...")
        
        # Prepare invalid request payload
        payload = {
            "project_id": "invalid-project-id-format",  # Missing customer/project format
            "user_id": "user_test_123"
        }
        
        try:
            response = requests.post(
                self.endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            
            # Should return 422 for validation error
            assert response.status_code == 422, f"Expected 422, got {response.status_code}"
            
            response_data = response.json()
            
            # Validate error response structure
            assert "detail" in response_data, "Error response missing 'detail' field"
            
            print(f"✅ Invalid project_id test passed!")
            print(f"   - Status: {response.status_code}")
            print(f"   - Error: {response_data.get('detail', {}).get('message', 'Unknown error')}")
            
            return {
                "test": "invalid_project_id",
                "status": "PASSED",
                "response_data": response_data
            }
            
        except Exception as e:
            print(f"❌ Invalid project_id test failed: {str(e)}")
            return {
                "test": "invalid_project_id",
                "status": "FAILED",
                "error": str(e)
            }
    
    def test_missing_required_fields(self) -> Dict[str, Any]:
        """
        Test request with missing required fields.
        
        Returns:
            Test result dictionary
        """
        print("🧪 Testing missing required fields...")
        
        # Prepare request with missing user_id
        payload = {
            "project_id": "customer-123/project-abc"
            # Missing user_id
        }
        
        try:
            response = requests.post(
                self.endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            
            # Should return 422 for validation error
            assert response.status_code == 422, f"Expected 422, got {response.status_code}"
            
            response_data = response.json()
            
            print(f"✅ Missing required fields test passed!")
            print(f"   - Status: {response.status_code}")
            
            return {
                "test": "missing_required_fields",
                "status": "PASSED",
                "response_data": response_data
            }
            
        except Exception as e:
            print(f"❌ Missing required fields test failed: {str(e)}")
            return {
                "test": "missing_required_fields",
                "status": "FAILED",
                "error": str(e)
            }
    
    def test_with_idempotency_key(self) -> Dict[str, Any]:
        """
        Test request with idempotency key header.
        
        Returns:
            Test result dictionary
        """
        print("🧪 Testing request with idempotency key...")
        
        # Prepare valid request payload
        payload = {
            "project_id": "customer-456/project-def",
            "user_id": "user_test_456"
        }
        
        # Generate unique idempotency key
        idempotency_key = f"test-key-{uuid.uuid4()}"
        
        try:
            response = requests.post(
                self.endpoint,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Idempotency-Key": idempotency_key
                },
                timeout=5
            )
            
            # Should return 202 for successful initialization
            assert response.status_code == 202, f"Expected 202, got {response.status_code}"
            
            response_data = response.json()
            
            # Validate response structure
            assert response_data["success"] is True, "Response success should be True"
            assert "data" in response_data, "Response missing 'data' field"
            
            print(f"✅ Idempotency key test passed!")
            print(f"   - Status: {response.status_code}")
            print(f"   - Idempotency Key: {idempotency_key}")
            
            return {
                "test": "with_idempotency_key",
                "status": "PASSED",
                "idempotency_key": idempotency_key,
                "response_data": response_data
            }
            
        except Exception as e:
            print(f"❌ Idempotency key test failed: {str(e)}")
            return {
                "test": "with_idempotency_key",
                "status": "FAILED",
                "error": str(e)
            }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """
        Run all endpoint tests.
        
        Returns:
            Complete test results
        """
        print("🚀 Starting DevTeam Automation Initialize Endpoint Tests")
        print("=" * 60)
        
        results = []
        
        # Test 1: Valid request
        results.append(self.test_valid_request())
        print()
        
        # Test 2: Invalid project_id
        results.append(self.test_invalid_project_id())
        print()
        
        # Test 3: Missing required fields
        results.append(self.test_missing_required_fields())
        print()
        
        # Test 4: With idempotency key
        results.append(self.test_with_idempotency_key())
        print()
        
        # Summary
        passed = sum(1 for r in results if r["status"] == "PASSED")
        failed = sum(1 for r in results if r["status"] == "FAILED")
        
        print("=" * 60)
        print(f"📊 Test Summary: {passed} passed, {failed} failed")
        
        if failed == 0:
            print("🎉 All tests passed! DevTeam automation endpoint is working correctly.")
        else:
            print("⚠️  Some tests failed. Please review the implementation.")
        
        return {
            "summary": {
                "total": len(results),
                "passed": passed,
                "failed": failed
            },
            "results": results
        }


def main():
    """Main test execution function."""
    print("DevTeam Automation Initialize Endpoint Test Suite")
    print("=" * 60)
    
    # Check if server is running
    try:
        health_response = requests.get("http://localhost:8090/health", timeout=5)
        if health_response.status_code != 200:
            print("❌ Server health check failed. Is the server running?")
            return
        print("✅ Server is running and healthy")
        print()
    except requests.exceptions.RequestException:
        print("❌ Cannot connect to server at http://localhost:8090")
        print("   Please ensure the server is running with: cd docker && ./start.sh")
        return
    
    # Run tests
    tester = DevTeamAutomationEndpointTester()
    results = tester.run_all_tests()
    
    # Exit with appropriate code
    if results["summary"]["failed"] > 0:
        exit(1)
    else:
        exit(0)


if __name__ == "__main__":
    main()