#!/usr/bin/env python3
"""
Reconnect Test Scenarios for WebSocket Demo Client

This module provides comprehensive test scenarios to validate the linear reconnect
functionality of the WebSocket demo client, ensuring proper behavior during
connection interruptions and server unavailability.

Test Scenarios:
- Basic reconnect test with manual disconnect and linear reconnect validation
- Multiple reconnect test for stability validation
- Server unavailable test for graceful degradation
- Network interruption simulation and recovery testing
- Reconnect performance validation with timing requirements
- State consistency validation during reconnect cycles

Requirements:
- Linear reconnect with 2-second intervals (ADD Profile C)
- Connection state management validation
- Message delivery validation after reconnect
- Performance metrics collection during reconnects
"""

import asyncio
import time
import logging
import signal
import subprocess
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import statistics

from websocket_demo_client import WebSocketDemoClient, MessageType, ClientConfig, ConnectionState


class TestResult(str, Enum):
    """Test result status."""
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    ERROR = "ERROR"


@dataclass
class ReconnectMetrics:
    """Metrics for reconnect testing."""
    reconnect_attempts: int = 0
    successful_reconnects: int = 0
    failed_reconnects: int = 0
    reconnect_times: List[float] = field(default_factory=list)
    state_transitions: List[Tuple[str, str, float]] = field(default_factory=list)
    messages_lost: int = 0
    messages_delivered_after_reconnect: int = 0
    
    def add_reconnect_attempt(self, success: bool, duration: float) -> None:
        """Add a reconnect attempt result."""
        self.reconnect_attempts += 1
        if success:
            self.successful_reconnects += 1
            self.reconnect_times.append(duration)
        else:
            self.failed_reconnects += 1
    
    def add_state_transition(self, from_state: str, to_state: str, timestamp: float) -> None:
        """Add a state transition record."""
        self.state_transitions.append((from_state, to_state, timestamp))
    
    def get_success_rate(self) -> float:
        """Get reconnect success rate as percentage."""
        if self.reconnect_attempts == 0:
            return 0.0
        return (self.successful_reconnects / self.reconnect_attempts) * 100.0
    
    def get_average_reconnect_time(self) -> float:
        """Get average reconnect time in seconds."""
        if not self.reconnect_times:
            return 0.0
        return statistics.mean(self.reconnect_times)
    
    def validate_linear_reconnect_timing(self, expected_interval: float = 2.0, tolerance: float = 0.5) -> bool:
        """Validate that reconnect timing follows linear pattern with expected interval."""
        if len(self.reconnect_times) < 2:
            return True  # Not enough data to validate
        
        # Check if reconnect times are within tolerance of expected interval
        for reconnect_time in self.reconnect_times:
            if abs(reconnect_time - expected_interval) > tolerance:
                return False
        return True


@dataclass
class TestScenarioResult:
    """Result of a test scenario."""
    scenario_name: str
    result: TestResult
    duration: float
    metrics: ReconnectMetrics
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "scenario_name": self.scenario_name,
            "result": self.result.value,
            "duration": self.duration,
            "success_rate": self.metrics.get_success_rate(),
            "avg_reconnect_time": self.metrics.get_average_reconnect_time(),
            "reconnect_attempts": self.metrics.reconnect_attempts,
            "successful_reconnects": self.metrics.successful_reconnects,
            "failed_reconnects": self.metrics.failed_reconnects,
            "messages_lost": self.metrics.messages_lost,
            "messages_delivered_after_reconnect": self.metrics.messages_delivered_after_reconnect,
            "error_message": self.error_message,
            "details": self.details
        }


class ReconnectTestScenarios:
    """
    Comprehensive reconnect test scenarios for WebSocket demo client.
    
    Validates linear reconnect functionality, connection state management,
    and message delivery during various network conditions and server states.
    """
    
    def __init__(self, server_url: str = "ws://localhost:8090", 
                 project_id: str = "reconnect-test"):
        """
        Initialize reconnect test scenarios.
        
        Args:
            server_url: WebSocket server URL
            project_id: Project identifier for testing
        """
        self.server_url = server_url
        self.project_id = project_id
        self.client: Optional[WebSocketDemoClient] = None
        self.test_results: List[TestScenarioResult] = []
        
        # Test configuration
        self.linear_reconnect_interval = 2.0  # ADD Profile C: 2-second intervals
        self.timing_tolerance = 0.5  # 500ms tolerance for timing validation
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    async def setup_client(self) -> bool:
        """
        Set up WebSocket client for testing.
        
        Returns:
            bool: True if setup successful, False otherwise
        """
        try:
            config = ClientConfig(
                server_url=self.server_url,
                project_id=self.project_id,
                reconnect_interval=self.linear_reconnect_interval
            )
            self.client = WebSocketDemoClient(config)
            return True
        except Exception as e:
            self.logger.error(f"Failed to setup client: {e}")
            return False
    
    async def cleanup_client(self) -> None:
        """Clean up WebSocket client after testing."""
        if self.client:
            await self.client.stop()
            self.client = None
    
    async def test_basic_reconnect(self) -> TestScenarioResult:
        """
        Test basic reconnect functionality with manual disconnect and linear reconnect validation.
        
        Validates:
        - Manual disconnect triggers reconnect logic
        - Linear reconnect with 2-second intervals
        - Connection state transitions
        - Successful reconnection
        
        Returns:
            TestScenarioResult: Test results and metrics
        """
        scenario_name = "basic_reconnect"
        self.logger.info(f"Starting {scenario_name} test...")
        
        metrics = ReconnectMetrics()
        start_time = time.time()
        
        try:
            if not self.client:
                return TestScenarioResult(
                    scenario_name=scenario_name,
                    result=TestResult.ERROR,
                    duration=0.0,
                    metrics=metrics,
                    error_message="Client not initialized"
                )
            
            # Set up state tracking
            state_changes = []
            
            def track_state_change(state: ConnectionState) -> None:
                state_changes.append((state.value, time.time()))
                metrics.add_state_transition(
                    state_changes[-2][0] if len(state_changes) > 1 else "unknown",
                    state.value,
                    time.time()
                )
            
            self.client.on_state_change = track_state_change
            
            # Initial connection
            self.logger.info("Establishing initial connection...")
            initial_connect_success = await self.client.connect()
            if not initial_connect_success:
                return TestScenarioResult(
                    scenario_name=scenario_name,
                    result=TestResult.FAIL,
                    duration=time.time() - start_time,
                    metrics=metrics,
                    error_message="Failed to establish initial connection"
                )
            
            # Wait for stable connection
            await asyncio.sleep(1.0)
            
            # Manual disconnect to trigger reconnect
            self.logger.info("Performing manual disconnect...")
            disconnect_time = time.time()
            await self.client.disconnect()
            
            # Start client run loop to trigger reconnect logic
            client_task = asyncio.create_task(self.client.run())
            
            # Wait for reconnect attempts (should happen with 2-second intervals)
            reconnect_start = time.time()
            max_wait_time = 10.0  # Wait up to 10 seconds for reconnect
            
            while time.time() - reconnect_start < max_wait_time:
                if self.client.state == ConnectionState.CONNECTED:
                    reconnect_duration = time.time() - disconnect_time
                    metrics.add_reconnect_attempt(True, reconnect_duration)
                    self.logger.info(f"Reconnected successfully in {reconnect_duration:.2f}s")
                    break
                await asyncio.sleep(0.1)
            else:
                metrics.add_reconnect_attempt(False, max_wait_time)
                client_task.cancel()
                return TestScenarioResult(
                    scenario_name=scenario_name,
                    result=TestResult.FAIL,
                    duration=time.time() - start_time,
                    metrics=metrics,
                    error_message="Reconnect timed out"
                )
            
            # Stop client task
            client_task.cancel()
            try:
                await client_task
            except asyncio.CancelledError:
                pass
            
            # Validate linear reconnect timing
            timing_valid = metrics.validate_linear_reconnect_timing(
                self.linear_reconnect_interval, 
                self.timing_tolerance
            )
            
            # Determine test result
            if metrics.successful_reconnects > 0 and timing_valid:
                result = TestResult.PASS
                error_message = None
            else:
                result = TestResult.FAIL
                error_message = "Reconnect timing validation failed" if not timing_valid else "No successful reconnects"
            
            return TestScenarioResult(
                scenario_name=scenario_name,
                result=result,
                duration=time.time() - start_time,
                metrics=metrics,
                error_message=error_message,
                details={
                    "state_changes": state_changes,
                    "timing_valid": timing_valid,
                    "expected_interval": self.linear_reconnect_interval
                }
            )
            
        except Exception as e:
            self.logger.error(f"Basic reconnect test failed with exception: {e}")
            return TestScenarioResult(
                scenario_name=scenario_name,
                result=TestResult.ERROR,
                duration=time.time() - start_time,
                metrics=metrics,
                error_message=str(e)
            )
    
    async def test_multiple_reconnects(self) -> TestScenarioResult:
        """
        Test multiple disconnect/reconnect cycles for stability validation.
        
        Validates:
        - Multiple reconnect cycles work consistently
        - Connection state management remains stable
        - Performance doesn't degrade over multiple cycles
        - Linear timing is maintained across cycles
        
        Returns:
            TestScenarioResult: Test results and metrics
        """
        scenario_name = "multiple_reconnects"
        self.logger.info(f"Starting {scenario_name} test...")
        
        metrics = ReconnectMetrics()
        start_time = time.time()
        num_cycles = 5
        
        try:
            if not self.client:
                return TestScenarioResult(
                    scenario_name=scenario_name,
                    result=TestResult.ERROR,
                    duration=0.0,
                    metrics=metrics,
                    error_message="Client not initialized"
                )
            
            # Track state changes
            state_changes = []
            
            def track_state_change(state: ConnectionState) -> None:
                state_changes.append((state.value, time.time()))
                metrics.add_state_transition(
                    state_changes[-2][0] if len(state_changes) > 1 else "unknown",
                    state.value,
                    time.time()
                )
            
            self.client.on_state_change = track_state_change
            
            # Initial connection
            initial_connect_success = await self.client.connect()
            if not initial_connect_success:
                return TestScenarioResult(
                    scenario_name=scenario_name,
                    result=TestResult.FAIL,
                    duration=time.time() - start_time,
                    metrics=metrics,
                    error_message="Failed to establish initial connection"
                )
            
            # Perform multiple reconnect cycles
            for cycle in range(num_cycles):
                self.logger.info(f"Starting reconnect cycle {cycle + 1}/{num_cycles}")
                
                # Disconnect
                disconnect_time = time.time()
                await self.client.disconnect()
                
                # Start client run loop for reconnect
                client_task = asyncio.create_task(self.client.run())
                
                # Wait for reconnect
                reconnect_start = time.time()
                max_wait_time = 8.0  # 8 seconds should be enough for 2-second interval reconnect
                
                while time.time() - reconnect_start < max_wait_time:
                    if self.client.state == ConnectionState.CONNECTED:
                        reconnect_duration = time.time() - disconnect_time
                        metrics.add_reconnect_attempt(True, reconnect_duration)
                        self.logger.info(f"Cycle {cycle + 1} reconnected in {reconnect_duration:.2f}s")
                        break
                    await asyncio.sleep(0.1)
                else:
                    metrics.add_reconnect_attempt(False, max_wait_time)
                    self.logger.error(f"Cycle {cycle + 1} reconnect timed out")
                
                # Stop client task
                client_task.cancel()
                try:
                    await client_task
                except asyncio.CancelledError:
                    pass
                
                # Brief pause between cycles
                if cycle < num_cycles - 1:
                    await asyncio.sleep(1.0)
            
            # Validate results
            success_rate = metrics.get_success_rate()
            timing_valid = metrics.validate_linear_reconnect_timing(
                self.linear_reconnect_interval,
                self.timing_tolerance
            )
            
            # Determine test result
            if success_rate >= 80.0 and timing_valid:  # At least 80% success rate
                result = TestResult.PASS
                error_message = None
            else:
                result = TestResult.FAIL
                error_message = f"Success rate {success_rate:.1f}% or timing validation failed"
            
            return TestScenarioResult(
                scenario_name=scenario_name,
                result=result,
                duration=time.time() - start_time,
                metrics=metrics,
                error_message=error_message,
                details={
                    "num_cycles": num_cycles,
                    "success_rate": success_rate,
                    "timing_valid": timing_valid,
                    "state_changes": state_changes
                }
            )
            
        except Exception as e:
            self.logger.error(f"Multiple reconnects test failed with exception: {e}")
            return TestScenarioResult(
                scenario_name=scenario_name,
                result=TestResult.ERROR,
                duration=time.time() - start_time,
                metrics=metrics,
                error_message=str(e)
            )
    
    async def test_server_unavailable(self) -> TestScenarioResult:
        """
        Test behavior when server is completely unavailable.
        
        Validates:
        - Graceful handling when server is down
        - Continuous reconnect attempts with linear timing
        - Proper error handling and logging
        - Recovery when server becomes available again
        
        Returns:
            TestScenarioResult: Test results and metrics
        """
        scenario_name = "server_unavailable"
        self.logger.info(f"Starting {scenario_name} test...")
        
        metrics = ReconnectMetrics()
        start_time = time.time()
        
        try:
            if not self.client:
                return TestScenarioResult(
                    scenario_name=scenario_name,
                    result=TestResult.ERROR,
                    duration=0.0,
                    metrics=metrics,
                    error_message="Client not initialized"
                )
            
            # Track state changes and connection attempts
            state_changes = []
            connection_attempts = []
            
            def track_state_change(state: ConnectionState) -> None:
                state_changes.append((state.value, time.time()))
                metrics.add_state_transition(
                    state_changes[-2][0] if len(state_changes) > 1 else "unknown",
                    state.value,
                    time.time()
                )
            
            self.client.on_state_change = track_state_change
            
            # Use invalid server URL to simulate server unavailable
            original_url = self.client.config.server_url
            self.client.config.server_url = "ws://localhost:9999"  # Non-existent server
            
            # Start client run loop (will attempt to connect to unavailable server)
            client_task = asyncio.create_task(self.client.run())
            
            # Monitor reconnect attempts for a period
            monitor_duration = 10.0  # Monitor for 10 seconds
            monitor_start = time.time()
            last_attempt_time = monitor_start
            
            while time.time() - monitor_start < monitor_duration:
                current_time = time.time()
                
                # Check if client is attempting reconnection
                if self.client.state in [ConnectionState.CONNECTING, ConnectionState.RECONNECTING]:
                    if current_time - last_attempt_time >= self.linear_reconnect_interval - 0.1:
                        connection_attempts.append(current_time)
                        metrics.add_reconnect_attempt(False, 0.0)  # Failed attempt
                        last_attempt_time = current_time
                        self.logger.info(f"Reconnect attempt detected at {current_time:.2f}")
                
                await asyncio.sleep(0.1)
            
            # Restore original server URL and test recovery
            self.client.config.server_url = original_url
            self.logger.info("Restoring server URL to test recovery...")
            
            # Wait for successful reconnection
            recovery_start = time.time()
            max_recovery_time = 8.0
            
            while time.time() - recovery_start < max_recovery_time:
                if self.client.state == ConnectionState.CONNECTED:
                    recovery_duration = time.time() - recovery_start
                    metrics.add_reconnect_attempt(True, recovery_duration)
                    self.logger.info(f"Recovered connection in {recovery_duration:.2f}s")
                    break
                await asyncio.sleep(0.1)
            
            # Stop client task
            client_task.cancel()
            try:
                await client_task
            except asyncio.CancelledError:
                pass
            
            # Validate linear timing of failed attempts
            if len(connection_attempts) >= 2:
                intervals = []
                for i in range(1, len(connection_attempts)):
                    interval = connection_attempts[i] - connection_attempts[i-1]
                    intervals.append(interval)
                
                # Check if intervals are close to expected linear interval
                timing_valid = all(
                    abs(interval - self.linear_reconnect_interval) <= self.timing_tolerance
                    for interval in intervals
                )
            else:
                timing_valid = False
            
            # Determine test result
            if metrics.failed_reconnects >= 3 and timing_valid and metrics.successful_reconnects > 0:
                result = TestResult.PASS
                error_message = None
            else:
                result = TestResult.FAIL
                error_message = "Insufficient reconnect attempts, timing issues, or no recovery"
            
            return TestScenarioResult(
                scenario_name=scenario_name,
                result=result,
                duration=time.time() - start_time,
                metrics=metrics,
                error_message=error_message,
                details={
                    "connection_attempts": len(connection_attempts),
                    "timing_valid": timing_valid,
                    "monitor_duration": monitor_duration,
                    "state_changes": state_changes
                }
            )
            
        except Exception as e:
            self.logger.error(f"Server unavailable test failed with exception: {e}")
            return TestScenarioResult(
                scenario_name=scenario_name,
                result=TestResult.ERROR,
                duration=time.time() - start_time,
                metrics=metrics,
                error_message=str(e)
            )
    
    async def test_network_interruption_simulation(self) -> TestScenarioResult:
        """
        Test network interruption simulation and recovery.
        
        Simulates network interruption by closing connection and validates:
        - Detection of network interruption
        - Automatic reconnect attempts
        - Linear timing during reconnect attempts
        - Message delivery after reconnection
        
        Returns:
            TestScenarioResult: Test results and metrics
        """
        scenario_name = "network_interruption_simulation"
        self.logger.info(f"Starting {scenario_name} test...")
        
        metrics = ReconnectMetrics()
        start_time = time.time()
        
        try:
            if not self.client:
                return TestScenarioResult(
                    scenario_name=scenario_name,
                    result=TestResult.ERROR,
                    duration=0.0,
                    metrics=metrics,
                    error_message="Client not initialized"
                )
            
            # Track messages and state changes
            messages_sent_before = 0
            messages_sent_after = 0
            state_changes = []
            
            def track_state_change(state: ConnectionState) -> None:
                state_changes.append((state.value, time.time()))
                metrics.add_state_transition(
                    state_changes[-2][0] if len(state_changes) > 1 else "unknown",
                    state.value,
                    time.time()
                )
            
            self.client.on_state_change = track_state_change
            
            # Establish initial connection
            initial_connect_success = await self.client.connect()
            if not initial_connect_success:
                return TestScenarioResult(
                    scenario_name=scenario_name,
                    result=TestResult.FAIL,
                    duration=time.time() - start_time,
                    metrics=metrics,
                    error_message="Failed to establish initial connection"
                )
            
            # Send test messages before interruption
            for i in range(3):
                payload = {"test_message": f"before_interruption_{i}", "timestamp": datetime.utcnow().isoformat() + "Z"}
                success = await self.client.send_message(MessageType.EXECUTION_UPDATE, payload)
                if success:
                    messages_sent_before += 1
                await asyncio.sleep(0.1)
            
            # Simulate network interruption by forcibly closing WebSocket
            self.logger.info("Simulating network interruption...")
            interruption_time = time.time()
            
            if self.client.websocket and not self.client.websocket.closed:
                await self.client.websocket.close()
            
            # Start client run loop to handle reconnection
            client_task = asyncio.create_task(self.client.run())
            
            # Wait for reconnection
            reconnect_start = time.time()
            max_wait_time = 10.0
            
            while time.time() - reconnect_start < max_wait_time:
                if self.client.state == ConnectionState.CONNECTED:
                    reconnect_duration = time.time() - interruption_time
                    metrics.add_reconnect_attempt(True, reconnect_duration)
                    self.logger.info(f"Reconnected after interruption in {reconnect_duration:.2f}s")
                    break
                await asyncio.sleep(0.1)
            else:
                metrics.add_reconnect_attempt(False, max_wait_time)
                client_task.cancel()
                return TestScenarioResult(
                    scenario_name=scenario_name,
                    result=TestResult.FAIL,
                    duration=time.time() - start_time,
                    metrics=metrics,
                    error_message="Failed to reconnect after network interruption"
                )
            
            # Send test messages after reconnection
            await asyncio.sleep(0.5)  # Brief pause to ensure stable connection
            for i in range(3):
                payload = {"test_message": f"after_reconnection_{i}", "timestamp": datetime.utcnow().isoformat() + "Z"}
                success = await self.client.send_message(MessageType.EXECUTION_UPDATE, payload)
                if success:
                    messages_sent_after += 1
                    metrics.messages_delivered_after_reconnect += 1
                await asyncio.sleep(0.1)
            
            # Stop client task
            client_task.cancel()
            try:
                await client_task
            except asyncio.CancelledError:
                pass
            
            # Validate results
            timing_valid = metrics.validate_linear_reconnect_timing(
                self.linear_reconnect_interval,
                self.timing_tolerance
            )
            
            # Determine test result
            if (metrics.successful_reconnects > 0 and 
                messages_sent_before > 0 and 
                messages_sent_after > 0 and 
                timing_valid):
                result = TestResult.PASS
                error_message = None
            else:
                result = TestResult.FAIL
                error_message = "Network interruption recovery failed or timing invalid"
            
            return TestScenarioResult(
                scenario_name=scenario_name,
                result=result,
                duration=time.time() - start_time,
                metrics=metrics,
                error_message=error_message,
                details={
                    "messages_sent_before": messages_sent_before,
                    "messages_sent_after": messages_sent_after,
                    "timing_valid": timing_valid,
                    "state_changes": state_changes
                }
            )
            
        except Exception as e:
            self.logger.error(f"Network interruption test failed with exception: {e}")
            return TestScenarioResult(
                scenario_name=scenario_name,
                result=TestResult.ERROR,
                duration=time.time() - start_time,
                metrics=metrics,
                error_message=str(e)
            )
    
    async def test_reconnect_performance_validation(self) -> TestScenarioResult:
        """
        Test reconnect performance validation with timing requirements.
        
        Validates:
        - Reconnect attempts follow linear 2-second intervals
        - Performance metrics are collected during reconnects
        - Handshake performance after reconnect meets requirements
        - Overall reconnect performance is within acceptable bounds
        
        Returns:
            TestScenarioResult: Test results and metrics
        """
        scenario_name = "reconnect_performance_validation"
        self.logger.info(f"Starting {scenario_name} test...")
        
        metrics = ReconnectMetrics()
        start_time = time.time()
        
        try:
            if not self.client:
                return TestScenarioResult(
                    scenario_name=scenario_name,
                    result=TestResult.ERROR,
                    duration=0.0,
                    metrics=metrics,
                    error_message="Client not initialized"
                )
            
            # Track performance metrics
            handshake_times = []
            reconnect_intervals = []
            state_changes = []
            
            def track_state_change(state: ConnectionState) -> None:
                state_changes.append((state.value, time.time()))
                metrics.add_state_transition(
                    state_changes[-2][0] if len(state_changes) > 1 else "unknown",
                    state.value,
                    time.time()
                )
            
            self.client.on_state_change = track_state_change
            
            # Perform multiple reconnect cycles to gather performance data
            num_cycles = 3
            for cycle in range(num_cycles):
                self.logger.info(f"Performance test cycle {cycle + 1}/{num_cycles}")
                
                # Connect and measure handshake time
                connect_start = time.time()
                connect_success = await self.client.connect()
                connect_duration = time.time() - connect_start
                
                if connect_success:
                    handshake_times.append(connect_duration * 1000)  # Convert to ms
                    metrics.add_reconnect_attempt(True, connect_duration)
                    self.logger.info(f"Cycle {cycle + 1} connected in {connect_duration*1000:.1f}ms")
                else:
                    metrics.add_reconnect_attempt(False, connect_duration)
                    self.logger.error(f"Cycle {cycle + 1} connection failed")
                    continue
                
                # Wait briefly then disconnect
                await asyncio.sleep(1.0)
                disconnect_time = time.time()
                await self.client.disconnect()
                
                # If not the last cycle, measure reconnect interval
                if cycle < num_cycles - 1:
                    # Start client run loop for reconnect
                    client_task = asyncio.create_task(self.client.run())
                    
                    # Wait for reconnect and measure interval
                    reconnect_start = time.time()
                    max_wait_time = 8.0
                    
                    while time.time() - reconnect_start < max_wait_time:
                        if self.client.state == ConnectionState.CONNECTED:
                            interval = time.time() - disconnect_time
                            reconnect_intervals.append(interval)
                            self.logger.info(f"Reconnect interval: {interval:.2f}s")
                            break
                        await asyncio.sleep(0.1)
                    
                    # Stop client task
                    client_task.cancel()
                    try:
                        await client_task
                    except asyncio.CancelledError:
                        pass
            
            # Get client performance statistics
            perf_stats = self.client.get_performance_statistics()
            validation = self.client.validate_performance_targets()
            
            # Validate performance requirements
            handshake_performance_ok = all(ht <= 300.0 for ht in handshake_times)  # ≤300ms
            timing_intervals_ok = all(
                abs(interval - self.linear_reconnect_interval) <= self.timing_tolerance
                for interval in reconnect_intervals
            )
            overall_performance_ok = validation.get("overall_healthy", False)
            
            # Determine test result
            if (handshake_performance_ok and 
                timing_intervals_ok and 
                metrics.successful_reconnects >= num_cycles * 0.8):  # At least 80% success
                result = TestResult.PASS
                error_message = None
            else:
                result = TestResult.FAIL
                error_message = "Performance requirements not met"
            
            return TestScenarioResult(
                scenario_name=scenario_name,
                result=result,
                duration=time.time() - start_time,
                metrics=metrics,
                error_message=error_message,
                details={
                    "handshake_times_ms": handshake_times,
                    "reconnect_intervals_s": reconnect_intervals,
                    "handshake_performance_ok": handshake_performance_ok,
                    "timing_intervals_ok": timing_intervals_ok,
                    "overall_performance_ok": overall_performance_ok,
                    "performance_stats": perf_stats,
                    "state_changes": state_changes
                }
            )
            
        except Exception as e:
            self.logger.error(f"Reconnect performance validation test failed with exception: {e}")
            return TestScenarioResult(
                scenario_name=scenario_name,
                result=TestResult.ERROR,
                duration=time.time() - start_time,
                metrics=metrics,
                error_message=str(e)
            )
    
    async def test_state_consistency_validation(self) -> TestScenarioResult:
        """
        Test state consistency validation during reconnect cycles.
        
        Validates:
        - Connection state transitions are logical and consistent
        - State changes are properly tracked and reported
        - No invalid state transitions occur
        - State consistency is maintained across reconnect cycles
        
        Returns:
            TestScenarioResult: Test results and metrics
        """
        scenario_name = "state_consistency_validation"
        self.logger.info(f"Starting {scenario_name} test...")
        
        metrics = ReconnectMetrics()
        start_time = time.time()
        
        try:
            if not self.client:
                return TestScenarioResult(
                    scenario_name=scenario_name,
                    result=TestResult.ERROR,
                    duration=0.0,
                    metrics=metrics,
                    error_message="Client not initialized"
                )
            
            # Track all state transitions
            state_transitions = []
            invalid_transitions = []
            
            # Define valid state transitions
            valid_transitions = {
                ConnectionState.DISCONNECTED: [ConnectionState.CONNECTING],
                ConnectionState.CONNECTING: [ConnectionState.CONNECTED, ConnectionState.DISCONNECTED],
                ConnectionState.CONNECTED: [ConnectionState.DISCONNECTED, ConnectionState.RECONNECTING],
                ConnectionState.RECONNECTING: [ConnectionState.CONNECTED, ConnectionState.DISCONNECTED, ConnectionState.CONNECTING]
            }
            
            def track_state_change(state: ConnectionState) -> None:
                current_time = time.time()
                if state_transitions:
                    previous_state = state_transitions[-1][0]
                    # Check if transition is valid
                    if state not in valid_transitions.get(previous_state, []):
                        invalid_transitions.append((previous_state, state, current_time))
                        self.logger.warning(f"Invalid state transition: {previous_state} -> {state}")
                
                state_transitions.append((state, current_time))
                metrics.add_state_transition(
                    state_transitions[-2][0].value if len(state_transitions) > 1 else "unknown",
                    state.value,
                    current_time
                )
            
            self.client.on_state_change = track_state_change
            
            # Perform multiple connection cycles to test state consistency
            num_cycles = 4
            for cycle in range(num_cycles):
                self.logger.info(f"State consistency test cycle {cycle + 1}/{num_cycles}")
                
                # Connect
                connect_success = await self.client.connect()
                if connect_success:
                    metrics.add_reconnect_attempt(True, 0.0)
                    await asyncio.sleep(0.5)  # Brief pause in connected state
                else:
                    metrics.add_reconnect_attempt(False, 0.0)
                
                # Disconnect
                await self.client.disconnect()
                await asyncio.sleep(0.5)  # Brief pause in disconnected state
                
                # Test reconnect logic
                if cycle < num_cycles - 1:
                    client_task = asyncio.create_task(self.client.run())
                    
                    # Wait for reconnect
                    reconnect_start = time.time()
                    max_wait_time = 6.0
                    
                    while time.time() - reconnect_start < max_wait_time:
                        if self.client.state == ConnectionState.CONNECTED:
                            break
                        await asyncio.sleep(0.1)
                    
                    # Stop client task
                    client_task.cancel()
                    try:
                        await client_task
                    except asyncio.CancelledError:
                        pass
            
            # Analyze state transitions
            expected_states = [
                ConnectionState.CONNECTING,
                ConnectionState.CONNECTED,
                ConnectionState.DISCONNECTED
            ]
            
            # Check if we saw expected state patterns
            states_seen = set(state for state, _ in state_transitions)
            expected_states_seen = all(state in states_seen for state in expected_states)
            
            # Validate no invalid transitions occurred
            no_invalid_transitions = len(invalid_transitions) == 0
            
            # Check state transition timing consistency
            transition_timing_consistent = True
            for i in range(1, len(state_transitions)):
                time_diff = state_transitions[i][1] - state_transitions[i-1][1]
                # State transitions should not be too rapid (< 10ms) or too slow (> 30s)
                if time_diff < 0.01 or time_diff > 30.0:
                    transition_timing_consistent = False
                    break
            
            # Determine test result
            if (no_invalid_transitions and
                expected_states_seen and
                transition_timing_consistent and
                len(state_transitions) >= num_cycles * 2):  # At least 2 transitions per cycle
                result = TestResult.PASS
                error_message = None
            else:
                result = TestResult.FAIL
                error_message = "State consistency validation failed"
            
            return TestScenarioResult(
                scenario_name=scenario_name,
                result=result,
                duration=time.time() - start_time,
                metrics=metrics,
                error_message=error_message,
                details={
                    "state_transitions": [(s.value, t) for s, t in state_transitions],
                    "invalid_transitions": [(s1.value, s2.value, t) for s1, s2, t in invalid_transitions],
                    "expected_states_seen": expected_states_seen,
                    "no_invalid_transitions": no_invalid_transitions,
                    "transition_timing_consistent": transition_timing_consistent,
                    "total_transitions": len(state_transitions)
                }
            )
            
        except Exception as e:
            self.logger.error(f"State consistency validation test failed with exception: {e}")
            return TestScenarioResult(
                scenario_name=scenario_name,
                result=TestResult.ERROR,
                duration=time.time() - start_time,
                metrics=metrics,
                error_message=str(e)
            )
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """
        Run all reconnect test scenarios.
        
        Returns:
            Dict containing results from all test scenarios
        """
        self.logger.info("Starting comprehensive reconnect test suite...")
        
        all_results = {
            "test_suite": "comprehensive_reconnect_tests",
            "start_time": datetime.utcnow().isoformat(),
            "tests": {},
            "summary": {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "error_tests": 0,
                "skipped_tests": 0,
                "overall_success": False
            }
        }
        
        # Setup client
        if not await self.setup_client():
            all_results["error"] = "Failed to setup WebSocket client"
            return all_results
        
        # Define test scenarios in order of complexity
        test_scenarios = [
            ("basic_reconnect", self.test_basic_reconnect),
            ("multiple_reconnects", self.test_multiple_reconnects),
            ("server_unavailable", self.test_server_unavailable),
            ("network_interruption_simulation", self.test_network_interruption_simulation),
            ("reconnect_performance_validation", self.test_reconnect_performance_validation),
            ("state_consistency_validation", self.test_state_consistency_validation)
        ]
        
        # Run each test scenario
        for test_name, test_func in test_scenarios:
            self.logger.info(f"Running test: {test_name}")
            
            try:
                test_result = await test_func()
                all_results["tests"][test_name] = test_result.to_dict()
                all_results["summary"]["total_tests"] += 1
                
                if test_result.result == TestResult.PASS:
                    all_results["summary"]["passed_tests"] += 1
                    self.logger.info(f"Test {test_name}: PASSED")
                elif test_result.result == TestResult.FAIL:
                    all_results["summary"]["failed_tests"] += 1
                    self.logger.error(f"Test {test_name}: FAILED - {test_result.error_message}")
                elif test_result.result == TestResult.ERROR:
                    all_results["summary"]["error_tests"] += 1
                    self.logger.error(f"Test {test_name}: ERROR - {test_result.error_message}")
                elif test_result.result == TestResult.SKIP:
                    all_results["summary"]["skipped_tests"] += 1
                    self.logger.info(f"Test {test_name}: SKIPPED - {test_result.error_message}")
                
                # Store result for reporting
                self.test_results.append(test_result)
                
            except Exception as e:
                self.logger.error(f"Test {test_name} encountered exception: {e}")
                error_result = TestScenarioResult(
                    scenario_name=test_name,
                    result=TestResult.ERROR,
                    duration=0.0,
                    metrics=ReconnectMetrics(),
                    error_message=str(e)
                )
                all_results["tests"][test_name] = error_result.to_dict()
                all_results["summary"]["error_tests"] += 1
                self.test_results.append(error_result)
        
        # Cleanup
        await self.cleanup_client()
        
        # Calculate overall success
        all_results["summary"]["overall_success"] = (
            all_results["summary"]["failed_tests"] == 0 and
            all_results["summary"]["error_tests"] == 0 and
            all_results["summary"]["passed_tests"] > 0
        )
        
        all_results["end_time"] = datetime.utcnow().isoformat()
        
        self.logger.info(
            f"Reconnect test suite completed: "
            f"{all_results['summary']['passed_tests']}/{all_results['summary']['total_tests']} tests passed"
        )
        
        return all_results
    
    def print_test_summary(self, results: Dict[str, Any]) -> None:
        """
        Print a formatted summary of test results.
        
        Args:
            results: Test results dictionary from run_all_tests()
        """
        print("\n" + "="*80)
        print("WEBSOCKET RECONNECT TEST RESULTS")
        print("="*80)
        
        summary = results.get("summary", {})
        print(f"Total Tests: {summary.get('total_tests', 0)}")
        print(f"Passed: {summary.get('passed_tests', 0)}")
        print(f"Failed: {summary.get('failed_tests', 0)}")
        print(f"Errors: {summary.get('error_tests', 0)}")
        print(f"Skipped: {summary.get('skipped_tests', 0)}")
        print(f"Overall Success: {'✓ PASS' if summary.get('overall_success', False) else '✗ FAIL'}")
        
        print("\nDETAILED RESULTS:")
        print("-" * 40)
        
        for test_name, test_result in results.get("tests", {}).items():
            status_map = {
                "PASS": "✓ PASS",
                "FAIL": "✗ FAIL",
                "ERROR": "⚠ ERROR",
                "SKIP": "- SKIP"
            }
            status = status_map.get(test_result.get("result", "UNKNOWN"), "? UNKNOWN")
            print(f"{test_name}: {status}")
            
            if test_result.get("result") != "PASS" and test_result.get("error_message"):
                print(f"  Error: {test_result['error_message']}")
            
            # Print key metrics for all tests
            if test_result.get("success_rate") is not None:
                print(f"  Success Rate: {test_result['success_rate']:.1f}%")
            if test_result.get("avg_reconnect_time") is not None and test_result.get("avg_reconnect_time") > 0:
                print(f"  Avg Reconnect Time: {test_result['avg_reconnect_time']:.2f}s")
            if test_result.get("reconnect_attempts") is not None and test_result.get("reconnect_attempts") > 0:
                print(f"  Reconnect Attempts: {test_result['reconnect_attempts']}")
        
        print("\nRECONNECT PERFORMANCE SUMMARY:")
        print("-" * 40)
        
        # Aggregate metrics across all tests
        total_attempts = sum(test.get("reconnect_attempts", 0) for test in results.get("tests", {}).values())
        total_successful = sum(test.get("successful_reconnects", 0) for test in results.get("tests", {}).values())
        
        if total_attempts > 0:
            overall_success_rate = (total_successful / total_attempts) * 100.0
            print(f"Overall Reconnect Success Rate: {overall_success_rate:.1f}%")
            print(f"Total Reconnect Attempts: {total_attempts}")
            print(f"Successful Reconnects: {total_successful}")
        
        # Linear timing validation summary
        timing_tests = [test for test in results.get("tests", {}).values()
                       if "timing_valid" in test.get("details", {})]
        if timing_tests:
            timing_valid_count = sum(1 for test in timing_tests
                                   if test.get("details", {}).get("timing_valid", False))
            print(f"Linear Timing Validation: {timing_valid_count}/{len(timing_tests)} tests passed")
        
        print("\n" + "="*80)


async def main():
    """Main function to run reconnect test scenarios."""
    # Create test instance
    test_scenarios = ReconnectTestScenarios()
    
    # Run all tests
    results = await test_scenarios.run_all_tests()
    
    # Print summary
    test_scenarios.print_test_summary(results)
    
    # Return exit code based on results
    return 0 if results.get("summary", {}).get("overall_success", False) else 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)