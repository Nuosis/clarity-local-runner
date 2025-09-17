#!/usr/bin/env python3
"""
WebSocket Connection Routing Test Suite - Task 6.1.2
Tests the enhanced WebSocket routing functionality with ADD Profile C message envelope format.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any, List

import websockets
import requests


class WebSocketRoutingTester:
    """Comprehensive tester for WebSocket connection routing by projectId functionality."""
    
    def __init__(self, base_url: str = "http://localhost:8090"):
        self.base_url = base_url
        self.ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://")
        
        # Supabase tokens from environment (these are the demo tokens from docker/.env)
        self.anon_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyAgCiAgICAicm9sZSI6ICJhbm9uIiwKICAgICJpc3MiOiAic3VwYWJhc2UtZGVtbyIsCiAgICAiaWF0IjogMTY0MTc2OTIwMCwKICAgICJleHAiOiAxNzk5NTM1NjAwCn0.dc_X5iR_VP_qT0zsiyj_I_OZ2T9FtRU2BBNWN8Bu4GE"
        self.service_role_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyAgCiAgICAicm9sZSI6ICJzZXJ2aWNlX3JvbGUiLAogICAgImlzcyI6ICJzdXBhYmFzZS1kZW1vIiwKICAgICJpYXQiOiAxNjQxNzY5MjAwLAogICAgImV4cCI6IDE3OTk1MzU2MDAKfQ.DaYlNEoUrrEn2Ig7tqibS-PHK5vgusbcbo7X36XVt4Q"
        
        self.results = []

    def log_result(self, test_name: str, success: bool, message: str, duration_ms: float = 0):
        """Log test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        duration_str = f" ({duration_ms:.2f}ms)" if duration_ms > 0 else ""
        print(f"{status} {test_name}: {message}{duration_str}")
        self.results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "duration_ms": duration_ms
        })

    def create_add_profile_c_message(self, msg_type: str, project_id: str, payload: dict) -> dict:
        """Create a message following ADD Profile C envelope format: { type, ts, projectId, payload }"""
        return {
            "type": msg_type,
            "ts": datetime.utcnow().isoformat() + "Z",
            "projectId": project_id,
            "payload": payload
        }

    async def test_add_profile_c_envelope_validation(self) -> bool:
        """Test that messages must follow ADD Profile C envelope format."""
        start_time = time.time()
        try:
            uri = f"{self.ws_url}/api/v1/ws/devteam?projectId=test-envelope-validation"
            headers = {"Authorization": f"Bearer {self.service_role_key}"}
            
            async with websockets.connect(uri, additional_headers=headers) as websocket:
                # Wait for welcome message
                welcome = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                
                # Test 1: Missing required fields
                invalid_message = {"type": "execution-update"}  # Missing ts, projectId, payload
                await websocket.send(json.dumps(invalid_message))
                
                error_response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                error_data = json.loads(error_response)
                
                if (error_data.get("type") == "error" and 
                    "missing required fields" in error_data.get("payload", {}).get("details", "").lower()):
                    
                    # Test 2: Invalid message type
                    invalid_type_message = self.create_add_profile_c_message(
                        "invalid-type", "test-envelope-validation", {"test": "data"}
                    )
                    await websocket.send(json.dumps(invalid_type_message))
                    
                    error_response2 = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    error_data2 = json.loads(error_response2)
                    
                    if (error_data2.get("type") == "error" and 
                        "invalid message type" in error_data2.get("payload", {}).get("details", "").lower()):
                        
                        self.log_result("add_profile_c_envelope_validation", True, 
                                      "Envelope validation working correctly", 
                                      (time.time() - start_time) * 1000)
                        return True
                
                self.log_result("add_profile_c_envelope_validation", False, 
                              "Envelope validation not working as expected", 
                              (time.time() - start_time) * 1000)
                return False
                
        except Exception as e:
            self.log_result("add_profile_c_envelope_validation", False, f"Test error: {str(e)}", 
                          (time.time() - start_time) * 1000)
            return False

    async def test_four_event_types_support(self) -> bool:
        """Test support for the four required event types: execution-update, execution-log, error, completion."""
        start_time = time.time()
        try:
            uri = f"{self.ws_url}/api/v1/ws/devteam?projectId=test-event-types"
            headers = {"Authorization": f"Bearer {self.service_role_key}"}
            
            async with websockets.connect(uri, additional_headers=headers) as websocket:
                # Wait for welcome message
                welcome = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                
                event_types = [
                    ("execution-update", {"status": "running", "progress": 50.0}),
                    ("execution-log", {"level": "INFO", "message": "Test log entry"}),
                    ("error", {"error_code": "TEST_ERROR", "message": "Test error"}),
                    ("completion", {"status": "completed", "duration_seconds": 120.5})
                ]
                
                successful_types = 0
                
                for event_type, payload in event_types:
                    message = self.create_add_profile_c_message(event_type, "test-event-types", payload)
                    await websocket.send(json.dumps(message))
                    
                    # Should receive acknowledgment
                    ack_response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    ack_data = json.loads(ack_response)
                    
                    if (ack_data.get("type") == "message-acknowledged" and 
                        ack_data.get("payload", {}).get("original_type") == event_type):
                        successful_types += 1
                
                if successful_types == 4:
                    self.log_result("four_event_types_support", True, 
                                  "All four event types supported correctly", 
                                  (time.time() - start_time) * 1000)
                    return True
                else:
                    self.log_result("four_event_types_support", False, 
                                  f"Only {successful_types}/4 event types working", 
                                  (time.time() - start_time) * 1000)
                    return False
                
        except Exception as e:
            self.log_result("four_event_types_support", False, f"Test error: {str(e)}", 
                          (time.time() - start_time) * 1000)
            return False

    async def test_project_id_routing(self) -> bool:
        """Test that messages are routed only to connections for the specific projectId."""
        start_time = time.time()
        try:
            # Create connections for two different projects
            project_a = "test-routing-project-a"
            project_b = "test-routing-project-b"
            
            uri_a = f"{self.ws_url}/api/v1/ws/devteam?projectId={project_a}"
            uri_b = f"{self.ws_url}/api/v1/ws/devteam?projectId={project_b}"
            headers = {"Authorization": f"Bearer {self.service_role_key}"}
            
            async with websockets.connect(uri_a, additional_headers=headers) as ws_a, \
                       websockets.connect(uri_b, additional_headers=headers) as ws_b:
                
                # Wait for welcome messages
                await asyncio.wait_for(ws_a.recv(), timeout=2.0)
                await asyncio.wait_for(ws_b.recv(), timeout=2.0)
                
                # Send message from project A
                message_a = self.create_add_profile_c_message(
                    "execution-update", project_a, {"status": "running", "progress": 25.0}
                )
                await ws_a.send(json.dumps(message_a))
                
                # Project A should receive acknowledgment and broadcast
                ack_a = await asyncio.wait_for(ws_a.recv(), timeout=2.0)
                broadcast_a = await asyncio.wait_for(ws_a.recv(), timeout=2.0)
                
                # Project B should NOT receive the broadcast (only project A should)
                try:
                    # This should timeout since project B shouldn't receive project A's message
                    unexpected_b = await asyncio.wait_for(ws_b.recv(), timeout=1.0)
                    self.log_result("project_id_routing", False, 
                                  "Project B received message intended for Project A", 
                                  (time.time() - start_time) * 1000)
                    return False
                except asyncio.TimeoutError:
                    # This is expected - project B should not receive project A's message
                    pass
                
                # Verify project A received its own message
                ack_data = json.loads(ack_a)
                broadcast_data = json.loads(broadcast_a)
                
                if (ack_data.get("type") == "message-acknowledged" and 
                    broadcast_data.get("projectId") == project_a):
                    
                    self.log_result("project_id_routing", True, 
                                  "Messages correctly routed by projectId", 
                                  (time.time() - start_time) * 1000)
                    return True
                else:
                    self.log_result("project_id_routing", False, 
                                  "Message routing not working correctly", 
                                  (time.time() - start_time) * 1000)
                    return False
                
        except Exception as e:
            self.log_result("project_id_routing", False, f"Test error: {str(e)}", 
                          (time.time() - start_time) * 1000)
            return False

    async def test_message_broadcasting_to_multiple_connections(self) -> bool:
        """Test that messages are broadcast to all connections for the same projectId."""
        start_time = time.time()
        try:
            project_id = "test-broadcast-multiple"
            uri = f"{self.ws_url}/api/v1/ws/devteam?projectId={project_id}"
            headers = {"Authorization": f"Bearer {self.service_role_key}"}
            
            # Create multiple connections for the same project
            async with websockets.connect(uri, additional_headers=headers) as ws1, \
                       websockets.connect(uri, additional_headers=headers) as ws2, \
                       websockets.connect(uri, additional_headers=headers) as ws3:
                
                # Wait for welcome messages
                await asyncio.wait_for(ws1.recv(), timeout=2.0)
                await asyncio.wait_for(ws2.recv(), timeout=2.0)
                await asyncio.wait_for(ws3.recv(), timeout=2.0)
                
                # Send message from first connection
                message = self.create_add_profile_c_message(
                    "execution-log", project_id, {"level": "INFO", "message": "Broadcast test"}
                )
                await ws1.send(json.dumps(message))
                
                # All connections should receive the broadcast
                responses = []
                for ws in [ws1, ws2, ws3]:
                    # Skip acknowledgment message for sender
                    if ws == ws1:
                        ack = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    
                    # All should receive the broadcast
                    broadcast = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    responses.append(json.loads(broadcast))
                
                # Verify all received the same broadcast message
                if (len(responses) == 3 and 
                    all(r.get("type") == "execution-log" and r.get("projectId") == project_id 
                        for r in responses)):
                    
                    self.log_result("message_broadcasting_multiple_connections", True, 
                                  "Messages broadcast to all connections for projectId", 
                                  (time.time() - start_time) * 1000)
                    return True
                else:
                    self.log_result("message_broadcasting_multiple_connections", False, 
                                  "Broadcasting not working correctly", 
                                  (time.time() - start_time) * 1000)
                    return False
                
        except Exception as e:
            self.log_result("message_broadcasting_multiple_connections", False, f"Test error: {str(e)}", 
                          (time.time() - start_time) * 1000)
            return False

    async def test_message_size_limits(self) -> bool:
        """Test that message size limits are enforced."""
        start_time = time.time()
        try:
            uri = f"{self.ws_url}/api/v1/ws/devteam?projectId=test-size-limits"
            headers = {"Authorization": f"Bearer {self.service_role_key}"}
            
            async with websockets.connect(uri, additional_headers=headers) as websocket:
                # Wait for welcome message
                welcome = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                
                # Create a message that exceeds the 10KB limit
                large_payload = {"data": "x" * 12000}  # 12KB of data
                large_message = self.create_add_profile_c_message(
                    "execution-log", "test-size-limits", large_payload
                )
                
                await websocket.send(json.dumps(large_message))
                
                # Should receive error about message size
                error_response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                error_data = json.loads(error_response)
                
                if (error_data.get("type") == "error" and 
                    "MESSAGE_TOO_LARGE" in error_data.get("payload", {}).get("error_code", "")):
                    
                    self.log_result("message_size_limits", True, 
                                  "Message size limits enforced correctly", 
                                  (time.time() - start_time) * 1000)
                    return True
                else:
                    self.log_result("message_size_limits", False, 
                                  "Message size limits not working", 
                                  (time.time() - start_time) * 1000)
                    return False
                
        except Exception as e:
            self.log_result("message_size_limits", False, f"Test error: {str(e)}", 
                          (time.time() - start_time) * 1000)
            return False

    async def test_latency_requirements(self) -> bool:
        """Test that ≤500ms latency requirement is met for message delivery."""
        start_time = time.time()
        try:
            project_id = "test-latency-requirements"
            uri = f"{self.ws_url}/api/v1/ws/devteam?projectId={project_id}"
            headers = {"Authorization": f"Bearer {self.service_role_key}"}
            
            latency_measurements = []
            
            async with websockets.connect(uri, additional_headers=headers) as websocket:
                # Wait for welcome message
                welcome = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                
                # Test multiple messages to get average latency
                for i in range(5):
                    message_start = time.time()
                    
                    message = self.create_add_profile_c_message(
                        "execution-update", project_id, {"status": "running", "progress": i * 20}
                    )
                    await websocket.send(json.dumps(message))
                    
                    # Receive acknowledgment
                    ack_response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    ack_data = json.loads(ack_response)
                    
                    # Get broadcast duration from acknowledgment
                    broadcast_duration = ack_data.get("payload", {}).get("broadcast_duration_ms", 0)
                    latency_measurements.append(broadcast_duration)
                    
                    # Also receive the broadcast
                    broadcast_response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                
                # Calculate average latency
                avg_latency = sum(latency_measurements) / len(latency_measurements)
                max_latency = max(latency_measurements)
                
                if avg_latency <= 500 and max_latency <= 500:
                    self.log_result("latency_requirements", True, 
                                  f"Latency requirement met - Avg: {avg_latency:.2f}ms, Max: {max_latency:.2f}ms", 
                                  (time.time() - start_time) * 1000)
                    return True
                else:
                    self.log_result("latency_requirements", False, 
                                  f"Latency requirement failed - Avg: {avg_latency:.2f}ms, Max: {max_latency:.2f}ms", 
                                  (time.time() - start_time) * 1000)
                    return False
                
        except Exception as e:
            self.log_result("latency_requirements", False, f"Test error: {str(e)}", 
                          (time.time() - start_time) * 1000)
            return False

    async def test_project_id_mismatch_validation(self) -> bool:
        """Test that messages with projectId mismatch are rejected."""
        start_time = time.time()
        try:
            connection_project = "test-mismatch-connection"
            message_project = "test-mismatch-message"
            
            uri = f"{self.ws_url}/api/v1/ws/devteam?projectId={connection_project}"
            headers = {"Authorization": f"Bearer {self.service_role_key}"}
            
            async with websockets.connect(uri, additional_headers=headers) as websocket:
                # Wait for welcome message
                welcome = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                
                # Send message with different projectId than connection
                message = self.create_add_profile_c_message(
                    "execution-update", message_project, {"status": "running"}
                )
                await websocket.send(json.dumps(message))
                
                # Should receive error about projectId mismatch
                error_response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                error_data = json.loads(error_response)
                
                if (error_data.get("type") == "error" and 
                    "does not match connection projectId" in error_data.get("payload", {}).get("details", "")):
                    
                    self.log_result("project_id_mismatch_validation", True, 
                                  "ProjectId mismatch validation working correctly", 
                                  (time.time() - start_time) * 1000)
                    return True
                else:
                    self.log_result("project_id_mismatch_validation", False, 
                                  "ProjectId mismatch validation not working", 
                                  (time.time() - start_time) * 1000)
                    return False
                
        except Exception as e:
            self.log_result("project_id_mismatch_validation", False, f"Test error: {str(e)}", 
                          (time.time() - start_time) * 1000)
            return False

    def check_server_health(self) -> bool:
        """Check if the server is running and healthy."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ Server is healthy at {self.base_url}")
                return True
            else:
                print(f"❌ Server health check failed: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Server health check failed: {str(e)}")
            return False

    async def run_all_tests(self):
        """Run all WebSocket routing tests."""
        print("🚀 Starting WebSocket Connection Routing Test Suite - Task 6.1.2")
        print("=" * 80)
        print(f"Testing endpoint: /api/v1/ws/devteam")
        print(f"Server: {self.base_url}")
        print(f"Focus: ADD Profile C envelope format and projectId routing")
        print()
        
        # Check server health first
        if not self.check_server_health():
            print("❌ Server is not healthy. Please start the server and try again.")
            return
        
        print()
        
        # Run tests
        tests = [
            ("add_profile_c_envelope_validation", self.test_add_profile_c_envelope_validation),
            ("four_event_types_support", self.test_four_event_types_support),
            ("project_id_routing", self.test_project_id_routing),
            ("message_broadcasting_multiple_connections", self.test_message_broadcasting_to_multiple_connections),
            ("message_size_limits", self.test_message_size_limits),
            ("latency_requirements", self.test_latency_requirements),
            ("project_id_mismatch_validation", self.test_project_id_mismatch_validation),
        ]
        
        for test_name, test_func in tests:
            try:
                await test_func()
            except Exception as e:
                self.log_result(test_name, False, f"Test error: {str(e)}")
        
        # Summary
        print()
        print("=" * 80)
        passed = sum(1 for r in self.results if r["success"])
        total = len(self.results)
        
        print(f"📊 Test Summary: {passed} passed, {total - passed} failed")
        
        if passed == total:
            print("🎉 All tests passed! WebSocket connection routing is working correctly.")
            print("✅ Task 6.1.2 implementation validated successfully!")
        else:
            print("⚠️  Some tests failed. Please review the implementation.")
            
        return passed == total


async def main():
    """Main test runner."""
    tester = WebSocketRoutingTester()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))