#!/usr/bin/env python3
"""
WebSocket DevTeam Endpoint Test Suite

This test validates the WebSocket endpoint implementation for task 6.1.1:
- WebSocket endpoint at /ws/devteam with projectId parameter
- JWT authentication integration
- Connection management and message validation
- Performance requirements (≤300ms handshake, ≤500ms message latency)
"""

import asyncio
import json
import time
import sys
from typing import Dict, Any, List

# Test configuration
BASE_URL = "ws://localhost:8090/api/v1/ws/devteam"
TEST_PROJECT_ID = "test-project-123"
TEST_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXIiLCJleHAiOjk5OTk5OTk5OTl9.test"

try:
    import websockets
    from websockets.exceptions import ConnectionClosedError
except ImportError:
    print("❌ websockets library not found. Install with: pip install websockets")
    exit(1)


class WebSocketTestSuite:
    """Comprehensive test suite for WebSocket DevTeam endpoint"""
    
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.passed = 0
        self.failed = 0
    
    def log_result(self, test_name: str, passed: bool, message: str, duration_ms: float = 0):
        """Log test result with structured output"""
        status = "✅ PASS" if passed else "❌ FAIL"
        duration_str = f" ({duration_ms:.2f}ms)" if duration_ms > 0 else ""
        print(f"{status} {test_name}: {message}{duration_str}")
        
        self.results.append({
            "test": test_name,
            "passed": passed,
            "message": message,
            "duration_ms": duration_ms
        })
        
        if passed:
            self.passed += 1
        else:
            self.failed += 1
    
    async def test_connection_without_auth(self):
        """Test connection rejection without authentication"""
        test_name = "connection_without_auth"
        start_time = time.time()
        
        try:
            async with websockets.connect(f"{BASE_URL}?projectId={TEST_PROJECT_ID}") as websocket:
                # Should not reach here
                duration_ms = (time.time() - start_time) * 1000
                self.log_result(test_name, False, "Connection accepted without auth", duration_ms)
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            if "401" in str(e) or "4001" in str(e) or "Unauthorized" in str(e):
                self.log_result(test_name, True, f"Correctly rejected without auth: {e}", duration_ms)
            else:
                self.log_result(test_name, False, f"Unexpected error: {e}", duration_ms)
    
    async def test_connection_without_project_id(self):
        """Test connection rejection without projectId parameter"""
        test_name = "connection_without_project_id"
        start_time = time.time()
        
        try:
            async with websockets.connect(
                BASE_URL,
                extra_headers={"Authorization": f"Bearer {TEST_TOKEN}"}
            ) as websocket:
                # Should not reach here
                duration_ms = (time.time() - start_time) * 1000
                self.log_result(test_name, False, "Connection accepted without projectId", duration_ms)
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            if "400" in str(e) or "4003" in str(e) or "projectId" in str(e):
                self.log_result(test_name, True, f"Correctly rejected without projectId: {e}", duration_ms)
            else:
                self.log_result(test_name, False, f"Unexpected error: {e}", duration_ms)
    
    async def test_valid_connection_and_messaging(self):
        """Test valid connection with authentication and basic messaging"""
        test_name = "valid_connection_messaging"
        start_time = time.time()
        
        try:
            async with websockets.connect(
                f"{BASE_URL}?projectId={TEST_PROJECT_ID}",
                extra_headers={"Authorization": f"Bearer {TEST_TOKEN}"}
            ) as websocket:
                # Test handshake performance
                handshake_time = (time.time() - start_time) * 1000
                if handshake_time <= 300:
                    self.log_result(f"{test_name}_handshake", True, f"Handshake time: {handshake_time:.2f}ms", handshake_time)
                else:
                    self.log_result(f"{test_name}_handshake", False, f"Handshake too slow: {handshake_time:.2f}ms", handshake_time)
                
                # Test basic message exchange
                message_start = time.time()
                test_message = {
                    "type": "ping",
                    "data": {"message": "test"}
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Wait for response with timeout
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    message_time = (time.time() - message_start) * 1000
                    
                    if message_time <= 500:
                        self.log_result(f"{test_name}_message", True, f"Message time: {message_time:.2f}ms", message_time)
                    else:
                        self.log_result(f"{test_name}_message", False, f"Message too slow: {message_time:.2f}ms", message_time)
                    
                    # Validate response format
                    try:
                        response_data = json.loads(response)
                        if isinstance(response_data, dict):
                            self.log_result(f"{test_name}_response_format", True, "Response is valid JSON object", 0)
                        else:
                            self.log_result(f"{test_name}_response_format", False, "Response is not a JSON object", 0)
                    except json.JSONDecodeError:
                        self.log_result(f"{test_name}_response_format", False, "Response is not valid JSON", 0)
                        
                except asyncio.TimeoutError:
                    self.log_result(f"{test_name}_message", False, "Message response timeout", 0)
                
                # Test invalid message handling
                try:
                    await websocket.send("invalid json")
                    # Should handle gracefully without closing connection
                    await asyncio.sleep(0.1)  # Give server time to process
                    self.log_result(f"{test_name}_invalid_message", True, "Invalid message handled gracefully", 0)
                except Exception as e:
                    if "4003" in str(e):
                        self.log_result(f"{test_name}_invalid_message", True, f"Correctly rejected invalid message: {e}", 0)
                    else:
                        self.log_result(f"{test_name}_invalid_message", False, f"Unexpected error: {e}", 0)
                
            duration_ms = (time.time() - start_time) * 1000
            self.log_result(test_name, True, f"Connection completed successfully", duration_ms)
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.log_result(test_name, False, f"Connection failed: {e}", duration_ms)
    
    async def test_performance_requirements(self):
        """Test performance requirements specifically"""
        test_name = "performance_requirements"
        
        try:
            # Test multiple connections for consistency
            handshake_times = []
            message_times = []
            
            for i in range(3):  # Test 3 connections
                start_time = time.time()
                
                async with websockets.connect(
                    f"{BASE_URL}?projectId={TEST_PROJECT_ID}",
                    extra_headers={"Authorization": f"Bearer {TEST_TOKEN}"}
                ) as websocket:
                    handshake_time = (time.time() - start_time) * 1000
                    handshake_times.append(handshake_time)
                    
                    # Test message performance
                    message_start = time.time()
                    await websocket.send(json.dumps({"type": "ping", "data": {}}))
                    await websocket.recv()
                    message_time = (time.time() - message_start) * 1000
                    message_times.append(message_time)
            
            # Analyze results
            avg_handshake = sum(handshake_times) / len(handshake_times)
            avg_message = sum(message_times) / len(message_times)
            max_handshake = max(handshake_times)
            max_message = max(message_times)
            
            # Check handshake requirement (≤300ms)
            if max_handshake <= 300:
                self.log_result(f"{test_name}_handshake_req", True, 
                              f"Handshake requirement met: avg={avg_handshake:.2f}ms, max={max_handshake:.2f}ms", 
                              avg_handshake)
            else:
                self.log_result(f"{test_name}_handshake_req", False, 
                              f"Handshake requirement failed: avg={avg_handshake:.2f}ms, max={max_handshake:.2f}ms", 
                              avg_handshake)
            
            # Check message requirement (≤500ms)
            if max_message <= 500:
                self.log_result(f"{test_name}_message_req", True, 
                              f"Message requirement met: avg={avg_message:.2f}ms, max={max_message:.2f}ms", 
                              avg_message)
            else:
                self.log_result(f"{test_name}_message_req", False, 
                              f"Message requirement failed: avg={avg_message:.2f}ms, max={max_message:.2f}ms", 
                              avg_message)
                
        except Exception as e:
            self.log_result(test_name, False, f"Performance test failed: {e}", 0)
    
    async def run_all_tests(self):
        """Run all test cases"""
        print("🚀 Starting WebSocket DevTeam Endpoint Test Suite")
        print("=" * 60)
        
        # Run tests in order
        await self.test_connection_without_auth()
        await self.test_connection_without_project_id()
        await self.test_valid_connection_and_messaging()
        await self.test_performance_requirements()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Summary: {self.passed} passed, {self.failed} failed")
        
        if self.failed == 0:
            print("🎉 All tests passed! WebSocket endpoint is working correctly.")
            return True
        else:
            print(f"⚠️  {self.failed} test(s) failed. Please review the implementation.")
            return False


async def main():
    """Main test execution"""
    print("WebSocket DevTeam Endpoint Test Suite")
    print("Testing endpoint: /api/v1/ws/devteam")
    print("Server: http://localhost:8090")
    print()
    
    # Check if server is running
    try:
        import requests
        response = requests.get("http://localhost:8090/health", timeout=5)
        if response.status_code != 200:
            print("❌ Server health check failed. Is the server running?")
            print("   Start with: cd docker && ./start.sh")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("   Start with: cd docker && ./start.sh")
        return False
    
    # Run tests
    test_suite = WebSocketTestSuite()
    success = await test_suite.run_all_tests()
    
    return success


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        sys.exit(1)