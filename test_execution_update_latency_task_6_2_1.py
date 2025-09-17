#!/usr/bin/env python3
"""
Test Execution Update Latency for Task 6.2.1

This test validates that execution-update frames are sent with ≤500ms latency
as required by the PRD Section 140-151 and ADD Section 6.

Test Coverage:
- WebSocket connection establishment
- Execution update message delivery latency
- Message envelope format validation
- Performance target validation (≤500ms)
- Integration with workflow execution pipeline
"""

import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any

import pytest
import websockets
from websockets.exceptions import ConnectionClosed

from services.execution_update_service import send_execution_update
from schemas.status_projection_schema import project_status_from_task_context


class ExecutionUpdateLatencyTest:
    """Test class for validating execution update latency requirements."""
    
    def __init__(self):
        self.websocket_url = "ws://localhost:8090/api/v1/ws/devteam"
        self.received_messages = []
        self.latency_measurements = []
        
    async def connect_websocket(self, project_id: str, token: str = "test-token"):
        """
        Connect to WebSocket endpoint with authentication.
        
        Args:
            project_id: Project identifier for routing
            token: JWT token for authentication
            
        Returns:
            WebSocket connection
        """
        uri = f"{self.websocket_url}?project_id={project_id}&token={token}"
        
        try:
            websocket = await websockets.connect(uri)
            print(f"✓ WebSocket connected to {uri}")
            return websocket
        except Exception as e:
            print(f"✗ Failed to connect to WebSocket: {e}")
            raise
    
    async def listen_for_messages(self, websocket, timeout: float = 10.0):
        """
        Listen for WebSocket messages with timeout.
        
        Args:
            websocket: WebSocket connection
            timeout: Maximum time to wait for messages
        """
        try:
            async with asyncio.timeout(timeout):
                async for message in websocket:
                    received_time = time.time()
                    try:
                        message_data = json.loads(message)
                        message_data['_received_at'] = received_time
                        self.received_messages.append(message_data)
                        
                        print(f"✓ Received message: {message_data.get('type', 'unknown')}")
                        
                        # Stop listening after receiving execution-update
                        if message_data.get('type') == 'execution-update':
                            break
                            
                    except json.JSONDecodeError as e:
                        print(f"✗ Failed to parse message: {e}")
                        
        except asyncio.TimeoutError:
            print(f"✗ Timeout waiting for messages after {timeout}s")
        except ConnectionClosed:
            print("✓ WebSocket connection closed")
    
    def create_test_task_context(self, project_id: str, execution_id: str) -> Dict[str, Any]:
        """
        Create test task context for execution updates.
        
        Args:
            project_id: Project identifier
            execution_id: Execution identifier
            
        Returns:
            Test task context dictionary
        """
        return {
            'metadata': {
                'correlationId': f"test_{uuid.uuid4()}",
                'taskId': f"task_{uuid.uuid4()}",
                'executionId': execution_id,
                'project_id': project_id,
                'status': 'running',
                'prepared_at': datetime.utcnow().isoformat(),
                'workflow_type': 'DEVTEAM_AUTOMATION'
            },
            'nodes': {
                'SelectNode': {
                    'status': 'completed',
                    'message': 'Fixed plan selected for DevTeam automation workflow'
                },
                'PrepNode': {
                    'status': 'running',
                    'message': 'Task context prepared with basic metadata'
                }
            }
        }
    
    async def test_execution_update_latency(self) -> bool:
        """
        Test execution update latency requirement (≤500ms).
        
        Returns:
            True if latency requirement is met, False otherwise
        """
        project_id = f"test-project-{uuid.uuid4()}"
        execution_id = f"exec_{uuid.uuid4()}"
        
        print(f"\n🧪 Testing execution update latency for project: {project_id}")
        
        try:
            # Connect to WebSocket
            websocket = await self.connect_websocket(project_id)
            
            # Start listening for messages in background
            listen_task = asyncio.create_task(
                self.listen_for_messages(websocket, timeout=5.0)
            )
            
            # Wait a moment for connection to stabilize
            await asyncio.sleep(0.1)
            
            # Create test task context
            task_context = self.create_test_task_context(project_id, execution_id)
            
            # Record start time and send execution update
            start_time = time.time()
            
            await send_execution_update(
                project_id=project_id,
                task_context=task_context,
                execution_id=execution_id,
                event_type="test_latency",
                correlation_id=task_context['metadata']['correlationId']
            )
            
            # Wait for message to be received
            await listen_task
            
            # Close WebSocket
            await websocket.close()
            
            # Analyze latency
            return self.analyze_latency_results(start_time)
            
        except Exception as e:
            print(f"✗ Test failed with error: {e}")
            return False
    
    def analyze_latency_results(self, start_time: float) -> bool:
        """
        Analyze latency measurement results.
        
        Args:
            start_time: Time when execution update was sent
            
        Returns:
            True if latency requirement is met, False otherwise
        """
        if not self.received_messages:
            print("✗ No messages received")
            return False
        
        # Find execution-update message
        execution_update_msg = None
        for msg in self.received_messages:
            if msg.get('type') == 'execution-update':
                execution_update_msg = msg
                break
        
        if not execution_update_msg:
            print("✗ No execution-update message received")
            return False
        
        # Calculate latency
        received_time = execution_update_msg.get('_received_at', 0)
        latency_ms = (received_time - start_time) * 1000
        
        print(f"📊 Execution update latency: {latency_ms:.2f}ms")
        
        # Validate latency requirement (≤500ms)
        latency_requirement_met = latency_ms <= 500
        
        if latency_requirement_met:
            print(f"✅ Latency requirement met: {latency_ms:.2f}ms ≤ 500ms")
        else:
            print(f"❌ Latency requirement NOT met: {latency_ms:.2f}ms > 500ms")
        
        # Validate message format
        format_valid = self.validate_message_format(execution_update_msg)
        
        return latency_requirement_met and format_valid
    
    def validate_message_format(self, message: Dict[str, Any]) -> bool:
        """
        Validate execution-update message format.
        
        Args:
            message: Received message to validate
            
        Returns:
            True if format is valid, False otherwise
        """
        print("\n📋 Validating message format...")
        
        # Check envelope format: { type, ts, project_id, payload }
        required_fields = ['type', 'ts', 'project_id', 'payload']
        
        for field in required_fields:
            if field not in message:
                print(f"✗ Missing required field: {field}")
                return False
        
        # Validate message type
        if message['type'] != 'execution-update':
            print(f"✗ Invalid message type: {message['type']}")
            return False
        
        # Validate payload structure
        payload = message.get('payload', {})
        required_payload_fields = ['execution_id', 'status', 'progress', 'event_type']
        
        for field in required_payload_fields:
            if field not in payload:
                print(f"✗ Missing required payload field: {field}")
                return False
        
        print("✅ Message format validation passed")
        return True
    
    async def run_comprehensive_test(self) -> bool:
        """
        Run comprehensive execution update latency test.
        
        Returns:
            True if all tests pass, False otherwise
        """
        print("🚀 Starting Execution Update Latency Test (Task 6.2.1)")
        print("=" * 60)
        
        try:
            # Test execution update latency
            latency_test_passed = await self.test_execution_update_latency()
            
            print("\n" + "=" * 60)
            if latency_test_passed:
                print("🎉 All tests PASSED - Execution update latency ≤500ms requirement met")
                return True
            else:
                print("💥 Tests FAILED - Execution update latency requirement not met")
                return False
                
        except Exception as e:
            print(f"\n💥 Test suite failed with error: {e}")
            return False


async def main():
    """Main test execution function."""
    test = ExecutionUpdateLatencyTest()
    success = await test.run_comprehensive_test()
    
    if success:
        print("\n✅ Task 6.2.1 - Execution Update Latency Test: PASSED")
        exit(0)
    else:
        print("\n❌ Task 6.2.1 - Execution Update Latency Test: FAILED")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())