"""
WebSocket Demo Client for Clarity Local Runner

This module provides a demonstration WebSocket client that connects to the
/ws/devteam endpoint with linear reconnect logic following ADD Profile C.

Features:
- JWT authentication using service_role_key pattern
- Message envelope validation for {type, ts, projectId, payload} format
- Connection state management (connecting, connected, disconnected, reconnecting)
- Client-side payload size validation (10KB limit)
- Linear reconnect with fixed 2-second intervals (ADD Profile C)
- Comprehensive error handling and structured logging
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from collections import deque
import statistics

import websockets
from websockets.exceptions import ConnectionClosed, InvalidURI

# Import structured logging from the project
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from core.structured_logging import get_structured_logger, LogStatus


class ConnectionState(str, Enum):
    """WebSocket connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"


class MessageType(str, Enum):
    """Supported WebSocket message types per ADD Section 6."""
    EXECUTION_UPDATE = "execution-update"
    EXECUTION_LOG = "execution-log"
    ERROR = "error"
    COMPLETION = "completion"
    CONNECTION_ESTABLISHED = "connection-established"
    MESSAGE_RECEIVED = "message-received"


@dataclass
class PerformanceThresholds:
    """Performance thresholds for monitoring."""
    handshake_max_ms: float = 300.0  # ≤300ms handshake target
    message_latency_max_ms: float = 500.0  # ≤500ms message latency target


@dataclass
class ReconnectMetrics:
    """Comprehensive reconnect metrics tracking."""
    # Reconnect attempt tracking
    reconnect_attempts: int = 0
    successful_reconnects: int = 0
    failed_reconnects: int = 0
    reconnect_times: deque = field(default_factory=lambda: deque(maxlen=100))
    
    # State transition tracking
    state_transitions: List[Dict[str, Any]] = field(default_factory=list)
    time_in_states: Dict[str, float] = field(default_factory=dict)
    last_state_change_time: Optional[float] = None
    
    # Error categorization
    error_categories: Dict[str, int] = field(default_factory=dict)
    connection_failures: List[Dict[str, Any]] = field(default_factory=list)
    
    # Performance during reconnects
    handshake_times_during_reconnect: deque = field(default_factory=lambda: deque(maxlen=50))
    message_latency_after_reconnect: deque = field(default_factory=lambda: deque(maxlen=50))
    
    def add_reconnect_attempt(self, success: bool, duration: float, error_type: Optional[str] = None) -> None:
        """Add a reconnect attempt with detailed tracking."""
        self.reconnect_attempts += 1
        if success:
            self.successful_reconnects += 1
            self.reconnect_times.append(duration)
        else:
            self.failed_reconnects += 1
            if error_type:
                self.error_categories[error_type] = self.error_categories.get(error_type, 0) + 1
    
    def add_state_transition(self, from_state: str, to_state: str, timestamp: float, correlation_id: str) -> None:
        """Add state transition with correlation tracking."""
        transition = {
            "from_state": from_state,
            "to_state": to_state,
            "timestamp": timestamp,
            "correlation_id": correlation_id
        }
        self.state_transitions.append(transition)
        
        # Track time in previous state
        if self.last_state_change_time is not None:
            time_in_previous_state = timestamp - self.last_state_change_time
            self.time_in_states[from_state] = self.time_in_states.get(from_state, 0) + time_in_previous_state
        
        self.last_state_change_time = timestamp
    
    def add_connection_failure(self, error_type: str, error_message: str, correlation_id: str) -> None:
        """Add connection failure details."""
        failure = {
            "timestamp": time.time(),
            "error_type": error_type,
            "error_message": error_message,
            "correlation_id": correlation_id
        }
        self.connection_failures.append(failure)
        
        # Keep only recent failures
        if len(self.connection_failures) > 50:
            self.connection_failures.pop(0)
    
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
    
    def get_error_distribution(self) -> Dict[str, float]:
        """Get error distribution as percentages."""
        if not self.error_categories:
            return {}
        
        total_errors = sum(self.error_categories.values())
        return {
            error_type: (count / total_errors) * 100.0
            for error_type, count in self.error_categories.items()
        }


@dataclass
class PerformanceStats:
    """Performance statistics tracking."""
    handshake_times: deque = field(default_factory=lambda: deque(maxlen=100))
    message_latencies: deque = field(default_factory=lambda: deque(maxlen=100))
    pending_messages: Dict[str, float] = field(default_factory=dict)
    
    # Current metrics
    last_handshake_time: Optional[float] = None
    last_message_latency: Optional[float] = None
    
    # Threshold violations
    handshake_violations: int = 0
    latency_violations: int = 0
    
    # Performance trends
    handshake_trend: str = "stable"  # improving, degrading, stable
    latency_trend: str = "stable"
    
    def add_handshake_time(self, duration_ms: float, threshold: float = 300.0) -> None:
        """Add handshake time measurement."""
        self.handshake_times.append(duration_ms)
        self.last_handshake_time = duration_ms
        
        if duration_ms > threshold:
            self.handshake_violations += 1
        
        # Update trend
        if len(self.handshake_times) >= 5:
            recent = list(self.handshake_times)[-5:]
            older = list(self.handshake_times)[-10:-5] if len(self.handshake_times) >= 10 else recent
            
            recent_avg = sum(recent) / len(recent)
            older_avg = sum(older) / len(older)
            
            if recent_avg < older_avg * 0.9:
                self.handshake_trend = "improving"
            elif recent_avg > older_avg * 1.1:
                self.handshake_trend = "degrading"
            else:
                self.handshake_trend = "stable"
    
    def add_message_latency(self, latency_ms: float, threshold: float = 500.0) -> None:
        """Add message latency measurement."""
        self.message_latencies.append(latency_ms)
        self.last_message_latency = latency_ms
        
        if latency_ms > threshold:
            self.latency_violations += 1
        
        # Update trend
        if len(self.message_latencies) >= 5:
            recent = list(self.message_latencies)[-5:]
            older = list(self.message_latencies)[-10:-5] if len(self.message_latencies) >= 10 else recent
            
            recent_avg = sum(recent) / len(recent)
            older_avg = sum(older) / len(older)
            
            if recent_avg < older_avg * 0.9:
                self.latency_trend = "improving"
            elif recent_avg > older_avg * 1.1:
                self.latency_trend = "degrading"
            else:
                self.latency_trend = "stable"
    
    def get_handshake_statistics(self) -> Dict[str, float]:
        """Get handshake performance statistics."""
        if not self.handshake_times:
            return {"min": 0, "max": 0, "avg": 0, "p95": 0, "p99": 0}
        
        times = list(self.handshake_times)
        return {
            "min": min(times),
            "max": max(times),
            "avg": statistics.mean(times),
            "p95": statistics.quantiles(times, n=20)[18] if len(times) >= 20 else max(times),
            "p99": statistics.quantiles(times, n=100)[98] if len(times) >= 100 else max(times)
        }
    
    def get_latency_statistics(self) -> Dict[str, float]:
        """Get message latency statistics."""
        if not self.message_latencies:
            return {"min": 0, "max": 0, "avg": 0, "p95": 0, "p99": 0}
        
        latencies = list(self.message_latencies)
        return {
            "min": min(latencies),
            "max": max(latencies),
            "avg": statistics.mean(latencies),
            "p95": statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies),
            "p99": statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies)
        }
    
    def is_handshake_healthy(self, threshold: float = 300.0) -> bool:
        """Check if handshake performance is healthy."""
        if not self.last_handshake_time:
            return True
        return self.last_handshake_time <= threshold
    
    def is_latency_healthy(self, threshold: float = 500.0) -> bool:
        """Check if message latency is healthy."""
        if not self.last_message_latency:
            return True
        return self.last_message_latency <= threshold


@dataclass
class ClientConfig:
    """Configuration for WebSocket demo client."""
    server_url: str = "ws://localhost:8090"
    project_id: str = "demo-project"
    service_role_key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyAgCiAgICAicm9sZSI6ICJzZXJ2aWNlX3JvbGUiLAogICAgImlzcyI6ICJzdXBhYmFzZS1kZW1vIiwKICAgICJpYXQiOiAxNjQxNzY5MjAwLAogICAgImV4cCI6IDE3OTk1MzU2MDAKfQ.DaYlNEoUrrEn2Ig7tqibS-PHK5vgusbcbo7X36XVt4Q"
    reconnect_interval: float = 2.0  # ADD Profile C: Linear reconnect with fixed 2-second intervals
    max_payload_size: int = 10240  # 10KB limit to match server
    connection_timeout: float = 10.0
    message_timeout: float = 5.0
    performance_thresholds: PerformanceThresholds = field(default_factory=PerformanceThresholds)


class WebSocketDemoClient:
    """
    WebSocket demo client with linear reconnect logic for Clarity Local Runner.
    
    This client demonstrates proper connection management, authentication,
    message envelope validation, and reconnection handling following ADD Profile C.
    
    Example usage:
        config = ClientConfig(project_id="my-project")
        client = WebSocketDemoClient(config)
        
        # Set up message handlers
        client.on_message = lambda msg: print(f"Received: {msg}")
        client.on_state_change = lambda state: print(f"State: {state}")
        
        # Connect and run
        await client.connect()
        await client.run()
    """
    
    def __init__(self, config: ClientConfig):
        """
        Initialize WebSocket demo client.
        
        Args:
            config: Client configuration settings
        """
        self.config = config
        self.state = ConnectionState.DISCONNECTED
        self.websocket: Optional[Any] = None
        self.running = False
        self.reconnect_task: Optional[asyncio.Task] = None
        
        # Correlation ID for distributed tracing
        self.correlation_id = str(uuid.uuid4())
        
        # Event handlers
        self.on_message: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_state_change: Optional[Callable[[ConnectionState], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        self.on_performance_alert: Optional[Callable[[str, float, float], None]] = None
        
        # Statistics
        self.connection_attempts = 0
        self.messages_sent = 0
        self.messages_received = 0
        self.last_connection_time: Optional[float] = None
        
        # Performance monitoring
        self.performance_stats = PerformanceStats()
        self.handshake_start_time: Optional[float] = None
        
        # Enhanced reconnect metrics
        self.reconnect_metrics = ReconnectMetrics()
        
        # Setup structured logging
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.structured_logger = get_structured_logger(f"{__name__}.{self.__class__.__name__}")
        self.structured_logger.set_context(
            projectId=self.config.project_id,
            correlationId=self.correlation_id,
            node="websocket_demo_client"
        )
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Setup structured logging for the client."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _trigger_performance_alert(self, metric_type: str, actual_value: float, threshold: float) -> None:
        """
        Trigger performance alert when thresholds are exceeded.
        
        Args:
            metric_type: Type of metric (handshake, latency)
            actual_value: Actual measured value
            threshold: Threshold that was exceeded
        """
        alert_msg = f"Performance alert: {metric_type} {actual_value:.1f}ms exceeds threshold {threshold:.1f}ms"
        self.logger.warning(alert_msg)
        
        if self.on_performance_alert:
            try:
                self.on_performance_alert(metric_type, actual_value, threshold)
            except Exception as e:
                self.logger.error(f"Error in performance alert handler: {e}")
    
    def _generate_message_id(self) -> str:
        """Generate unique message ID for latency tracking."""
        return f"msg_{int(time.time() * 1000)}_{self.messages_sent}"
    
    def _set_state(self, new_state: ConnectionState) -> None:
        """
        Update connection state and notify handlers with structured logging.
        
        Args:
            new_state: New connection state
        """
        if self.state != new_state:
            old_state = self.state
            self.state = new_state
            current_time = time.time()
            
            # Traditional logging
            self.logger.info(f"State changed: {old_state} -> {new_state}")
            
            # Structured logging for state transitions
            self.structured_logger.info(
                f"WebSocket state transition: {old_state.value} -> {new_state.value}",
                status=LogStatus.IN_PROGRESS,
                from_state=old_state.value,
                to_state=new_state.value,
                transition_timestamp=current_time,
                connection_attempts=self.connection_attempts
            )
            
            # Track metrics
            self.reconnect_metrics.add_state_transition(
                old_state.value,
                new_state.value,
                current_time,
                self.correlation_id
            )
            
            if self.on_state_change:
                try:
                    self.on_state_change(new_state)
                except Exception as e:
                    self.logger.error(f"Error in state change handler: {e}")
                    self.structured_logger.error(
                        "State change handler failed",
                        status=LogStatus.FAILED,
                        error=e,
                        handler_type="state_change"
                    )
    
    def _build_websocket_uri(self) -> str:
        """
        Build WebSocket URI with project ID parameter.
        
        Returns:
            Complete WebSocket URI
        """
        base_uri = f"{self.config.server_url}/api/v1/ws/devteam"
        return f"{base_uri}?projectId={self.config.project_id}"
    
    def _build_auth_headers(self) -> Dict[str, str]:
        """
        Build authentication headers using JWT service role key.
        
        Returns:
            Headers dictionary with Authorization header
        """
        return {
            "Authorization": f"Bearer {self.config.service_role_key}"
        }
    
    def validate_message_envelope(self, message: Dict[str, Any]) -> bool:
        """
        Validate message follows ADD Profile C envelope format: {type, ts, projectId, payload}.
        
        Args:
            message: Message dictionary to validate
            
        Returns:
            True if message is valid, False otherwise
        """
        try:
            # Check required fields
            required_fields = ["type", "ts", "projectId", "payload"]
            for field in required_fields:
                if field not in message:
                    self.logger.error(f"Message missing required field: {field}")
                    return False
            
            # Validate message type
            if message["type"] not in [t.value for t in MessageType]:
                self.logger.error(f"Invalid message type: {message['type']}")
                return False
            
            # Validate timestamp format (should end with 'Z')
            if not message["ts"].endswith('Z'):
                self.logger.error(f"Invalid timestamp format: {message['ts']}")
                return False
            
            # Validate project ID
            if not isinstance(message["projectId"], str) or not message["projectId"].strip():
                self.logger.error(f"Invalid project ID: {message['projectId']}")
                return False
            
            # Validate payload is a dictionary
            if not isinstance(message["payload"], dict):
                self.logger.error(f"Payload must be a dictionary, got: {type(message['payload'])}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating message envelope: {e}")
            return False
    
    def validate_payload_size(self, message: Dict[str, Any]) -> bool:
        """
        Validate message payload size is within 10KB limit.
        
        Args:
            message: Message dictionary to validate
            
        Returns:
            True if payload size is valid, False otherwise
        """
        try:
            message_json = json.dumps(message)
            message_size = len(message_json.encode('utf-8'))
            
            if message_size > self.config.max_payload_size:
                self.logger.error(
                    f"Message size {message_size} bytes exceeds limit of {self.config.max_payload_size} bytes"
                )
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating payload size: {e}")
            return False
    
    def create_message_envelope(
        self,
        message_type: MessageType,
        payload: Dict[str, Any],
        timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a standardized message envelope following ADD Profile C format.
        
        Args:
            message_type: Type of message being created
            payload: Message payload data
            timestamp: Optional timestamp (defaults to current UTC time)
            
        Returns:
            Dict containing the standardized envelope
            
        Raises:
            ValueError: If payload is invalid or message size exceeds limit
        """
        if payload is None:
            raise ValueError("Payload cannot be None")
        
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat() + "Z"
        elif not timestamp.endswith('Z'):
            timestamp = timestamp + "Z"
        
        envelope = {
            "type": message_type.value,
            "ts": timestamp,
            "projectId": self.config.project_id,
            "payload": payload
        }
        
        # Validate envelope
        if not self.validate_message_envelope(envelope):
            raise ValueError("Created envelope failed validation")
        
        if not self.validate_payload_size(envelope):
            raise ValueError("Message size exceeds 10KB limit")
        
        return envelope
    
    async def connect(self) -> bool:
        """
        Establish WebSocket connection with authentication and measure handshake time.
        Enhanced with structured logging and comprehensive metrics collection.
        
        Returns:
            True if connection successful, False otherwise
        """
        if self.state in [ConnectionState.CONNECTING, ConnectionState.CONNECTED]:
            self.logger.warning("Already connected or connecting")
            self.structured_logger.warn(
                "Connection attempt while already connected or connecting",
                status=LogStatus.SKIPPED,
                current_state=self.state.value,
                connection_attempts=self.connection_attempts
            )
            return self.state == ConnectionState.CONNECTED
        
        self._set_state(ConnectionState.CONNECTING)
        self.connection_attempts += 1
        
        # Generate new correlation ID for this connection attempt
        connection_correlation_id = str(uuid.uuid4())
        
        # Start handshake timing
        self.handshake_start_time = time.time()
        connect_start_time = time.time()
        
        # Structured logging for connection attempt start
        self.structured_logger.info(
            "Starting WebSocket connection attempt",
            status=LogStatus.STARTED,
            connection_attempt=self.connection_attempts,
            connection_correlation_id=connection_correlation_id,
            server_url=self.config.server_url,
            reconnect_interval=self.config.reconnect_interval
        )
        
        try:
            uri = self._build_websocket_uri()
            headers = self._build_auth_headers()
            
            self.logger.info(f"Connecting to {uri} (attempt {self.connection_attempts})")
            
            # Connect with timeout
            self.websocket = await asyncio.wait_for(
                websockets.connect(uri, additional_headers=headers),
                timeout=self.config.connection_timeout
            )
            
            # Calculate handshake time
            handshake_duration = (time.time() - self.handshake_start_time) * 1000  # Convert to ms
            connect_duration = time.time() - connect_start_time
            
            self.performance_stats.add_handshake_time(
                handshake_duration,
                self.config.performance_thresholds.handshake_max_ms
            )
            
            # Track reconnect metrics
            self.reconnect_metrics.add_reconnect_attempt(True, connect_duration)
            if self.connection_attempts > 1:  # This is a reconnect
                self.reconnect_metrics.handshake_times_during_reconnect.append(handshake_duration)
            
            self._set_state(ConnectionState.CONNECTED)
            self.last_connection_time = time.time()
            
            # Structured logging for successful connection
            self.structured_logger.info(
                "WebSocket connection established successfully",
                status=LogStatus.COMPLETED,
                connection_attempt=self.connection_attempts,
                connection_correlation_id=connection_correlation_id,
                handshake_duration_ms=handshake_duration,
                connect_duration_s=connect_duration,
                is_reconnect=self.connection_attempts > 1,
                total_reconnect_attempts=self.reconnect_metrics.reconnect_attempts
            )
            
            # Check for performance alerts
            if handshake_duration > self.config.performance_thresholds.handshake_max_ms:
                self._trigger_performance_alert(
                    "handshake",
                    handshake_duration,
                    self.config.performance_thresholds.handshake_max_ms
                )
                
                self.structured_logger.warn(
                    "Handshake performance threshold exceeded",
                    status=LogStatus.COMPLETED,
                    handshake_duration_ms=handshake_duration,
                    threshold_ms=self.config.performance_thresholds.handshake_max_ms,
                    performance_violation=True
                )
            
            self.logger.info(f"Successfully connected to {uri} (handshake: {handshake_duration:.1f}ms)")
            return True
            
        except asyncio.TimeoutError as e:
            connect_duration = time.time() - connect_start_time
            error_type = "connection_timeout"
            
            self.logger.error(f"Connection timeout after {self.config.connection_timeout}s")
            self.reconnect_metrics.add_reconnect_attempt(False, connect_duration, error_type)
            self.reconnect_metrics.add_connection_failure(error_type, str(e), connection_correlation_id)
            
            self.structured_logger.error(
                "WebSocket connection timeout",
                status=LogStatus.FAILED,
                connection_attempt=self.connection_attempts,
                connection_correlation_id=connection_correlation_id,
                timeout_s=self.config.connection_timeout,
                connect_duration_s=connect_duration,
                error_type=error_type,
                error=e
            )
            
            self._set_state(ConnectionState.DISCONNECTED)
            return False
            
        except InvalidURI as e:
            connect_duration = time.time() - connect_start_time
            error_type = "invalid_uri"
            
            self.logger.error(f"Invalid WebSocket URI: {e}")
            self.reconnect_metrics.add_reconnect_attempt(False, connect_duration, error_type)
            self.reconnect_metrics.add_connection_failure(error_type, str(e), connection_correlation_id)
            
            self.structured_logger.error(
                "Invalid WebSocket URI",
                status=LogStatus.FAILED,
                connection_attempt=self.connection_attempts,
                connection_correlation_id=connection_correlation_id,
                uri=self._build_websocket_uri(),
                error_type=error_type,
                error=e
            )
            
            self._set_state(ConnectionState.DISCONNECTED)
            return False
            
        except Exception as e:
            connect_duration = time.time() - connect_start_time
            error_msg = str(e)
            
            # Categorize error types
            if "403" in error_msg or "401" in error_msg:
                error_type = "authentication_failed"
                self.logger.error(f"Authentication failed: {e}")
            elif "404" in error_msg:
                error_type = "endpoint_not_found"
                self.logger.error(f"Endpoint not found: {e}")
            elif "ConnectionRefused" in str(type(e)):
                error_type = "connection_refused"
                self.logger.error(f"Connection refused: {e}")
            else:
                error_type = "connection_error"
                self.logger.error(f"Connection failed: {e}")
            
            self.reconnect_metrics.add_reconnect_attempt(False, connect_duration, error_type)
            self.reconnect_metrics.add_connection_failure(error_type, error_msg, connection_correlation_id)
            
            self.structured_logger.error(
                "WebSocket connection failed",
                status=LogStatus.FAILED,
                connection_attempt=self.connection_attempts,
                connection_correlation_id=connection_correlation_id,
                connect_duration_s=connect_duration,
                error_type=error_type,
                error_message=error_msg,
                error=e
            )
            
            self._set_state(ConnectionState.DISCONNECTED)
            
            if self.on_error:
                try:
                    self.on_error(e)
                except Exception as handler_error:
                    self.logger.error(f"Error in error handler: {handler_error}")
                    self.structured_logger.error(
                        "Error handler failed",
                        status=LogStatus.FAILED,
                        handler_type="error_handler",
                        error=handler_error
                    )
            return False
    
    async def disconnect(self) -> None:
        """Gracefully disconnect from WebSocket server."""
        if self.websocket and not self.websocket.closed:
            try:
                await self.websocket.close()
                self.logger.info("WebSocket connection closed gracefully")
            except Exception as e:
                self.logger.error(f"Error closing WebSocket connection: {e}")
        
        self.websocket = None
        self._set_state(ConnectionState.DISCONNECTED)
    
    async def send_message(self, message_type: MessageType, payload: Dict[str, Any]) -> bool:
        """
        Send a message through the WebSocket connection with latency tracking.
        
        Args:
            message_type: Type of message to send
            payload: Message payload data
            
        Returns:
            True if message sent successfully, False otherwise
        """
        if self.state != ConnectionState.CONNECTED or not self.websocket:
            self.logger.error("Cannot send message: not connected")
            return False
        
        try:
            # Generate message ID for latency tracking
            message_id = self._generate_message_id()
            
            # Add message ID to payload for round-trip tracking
            enhanced_payload = payload.copy()
            enhanced_payload["_message_id"] = message_id
            
            # Create and validate envelope
            envelope = self.create_message_envelope(message_type, enhanced_payload)
            message_json = json.dumps(envelope)
            
            # Record send time for latency measurement
            send_time = time.time()
            self.performance_stats.pending_messages[message_id] = send_time
            
            # Send message
            await self.websocket.send(message_json)
            self.messages_sent += 1
            
            self.logger.debug(f"Sent message: {message_type.value} (ID: {message_id})")
            return True
            
        except ValueError as e:
            self.logger.error(f"Message validation failed: {e}")
            return False
            
        except ConnectionClosed:
            self.logger.error("Connection closed while sending message")
            self._set_state(ConnectionState.DISCONNECTED)
            return False
            
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            return False
    
    async def _handle_received_message(self, message_data: str) -> None:
        """
        Handle received WebSocket message with latency tracking.
        
        Args:
            message_data: Raw message data from WebSocket
        """
        try:
            message = json.loads(message_data)
            self.messages_received += 1
            
            # Check for message ID to calculate latency
            payload = message.get("payload", {})
            message_id = payload.get("_message_id")
            
            if message_id and message_id in self.performance_stats.pending_messages:
                # Calculate round-trip latency
                send_time = self.performance_stats.pending_messages.pop(message_id)
                latency_ms = (time.time() - send_time) * 1000
                
                self.performance_stats.add_message_latency(
                    latency_ms,
                    self.config.performance_thresholds.message_latency_max_ms
                )
                
                # Check for performance alerts
                if latency_ms > self.config.performance_thresholds.message_latency_max_ms:
                    self._trigger_performance_alert(
                        "message_latency",
                        latency_ms,
                        self.config.performance_thresholds.message_latency_max_ms
                    )
                
                self.logger.debug(f"Message latency: {latency_ms:.1f}ms (ID: {message_id})")
            
            # Validate message envelope
            if not self.validate_message_envelope(message):
                self.logger.error("Received invalid message envelope")
                return
            
            self.logger.debug(f"Received message: {message.get('type', 'unknown')}")
            
            # Call message handler if set
            if self.on_message:
                try:
                    self.on_message(message)
                except Exception as e:
                    self.logger.error(f"Error in message handler: {e}")
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse received message as JSON: {e}")
        except Exception as e:
            self.logger.error(f"Error handling received message: {e}")
    
    async def _reconnect_loop(self) -> None:
        """
        Linear reconnect loop with fixed 2-second intervals (ADD Profile C).
        Enhanced with structured logging and comprehensive metrics tracking.
        """
        reconnect_loop_id = str(uuid.uuid4())
        reconnect_start_time = time.time()
        
        self.structured_logger.info(
            "Starting reconnect loop",
            status=LogStatus.STARTED,
            reconnect_loop_id=reconnect_loop_id,
            reconnect_interval_s=self.config.reconnect_interval,
            current_attempts=self.reconnect_metrics.reconnect_attempts,
            success_rate=self.reconnect_metrics.get_success_rate()
        )
        
        while self.running and self.state != ConnectionState.CONNECTED:
            self._set_state(ConnectionState.RECONNECTING)
            
            # Log reconnect attempt with structured logging
            self.structured_logger.info(
                f"Waiting {self.config.reconnect_interval}s before reconnect attempt",
                status=LogStatus.IN_PROGRESS,
                reconnect_loop_id=reconnect_loop_id,
                wait_time_s=self.config.reconnect_interval,
                total_attempts=self.connection_attempts,
                failed_attempts=self.reconnect_metrics.failed_reconnects
            )
            
            self.logger.info(f"Attempting reconnection in {self.config.reconnect_interval}s...")
            await asyncio.sleep(self.config.reconnect_interval)
            
            if not self.running:
                self.structured_logger.info(
                    "Reconnect loop stopped - client shutting down",
                    status=LogStatus.COMPLETED,
                    reconnect_loop_id=reconnect_loop_id,
                    reason="client_shutdown"
                )
                break
            
            # Attempt reconnection
            reconnect_attempt_start = time.time()
            success = await self.connect()
            reconnect_attempt_duration = time.time() - reconnect_attempt_start
            
            if success:
                total_reconnect_time = time.time() - reconnect_start_time
                
                self.structured_logger.info(
                    "Reconnect loop completed successfully",
                    status=LogStatus.COMPLETED,
                    reconnect_loop_id=reconnect_loop_id,
                    total_reconnect_time_s=total_reconnect_time,
                    final_attempt_duration_s=reconnect_attempt_duration,
                    total_attempts=self.connection_attempts,
                    success_rate=self.reconnect_metrics.get_success_rate()
                )
                break
            else:
                self.structured_logger.warn(
                    "Reconnect attempt failed, continuing loop",
                    status=LogStatus.FAILED,
                    reconnect_loop_id=reconnect_loop_id,
                    attempt_duration_s=reconnect_attempt_duration,
                    total_attempts=self.connection_attempts,
                    failed_attempts=self.reconnect_metrics.failed_reconnects
                )
    
    async def run(self) -> None:
        """
        Main client run loop with automatic reconnection.
        
        This method handles the main message receiving loop and manages
        reconnection attempts using linear reconnect with fixed intervals.
        """
        self.running = True
        
        try:
            while self.running:
                # Ensure we're connected
                if self.state != ConnectionState.CONNECTED:
                    if not await self.connect():
                        # Start reconnection loop
                        await self._reconnect_loop()
                        continue
                
                # Message receiving loop
                try:
                    if self.websocket:
                        message = await asyncio.wait_for(
                            self.websocket.recv(),
                            timeout=self.config.message_timeout
                        )
                        await self._handle_received_message(message)
                
                except asyncio.TimeoutError:
                    # Timeout is normal, continue loop
                    continue
                    
                except ConnectionClosed:
                    self.logger.warning("WebSocket connection closed")
                    self._set_state(ConnectionState.DISCONNECTED)
                    continue
                    
                except Exception as e:
                    self.logger.error(f"Error in message loop: {e}")
                    self._set_state(ConnectionState.DISCONNECTED)
                    continue
        
        finally:
            await self.disconnect()
            self.running = False
    
    async def stop(self) -> None:
        """Stop the client and disconnect."""
        self.logger.info("Stopping WebSocket client...")
        self.running = False
        
        if self.reconnect_task and not self.reconnect_task.done():
            self.reconnect_task.cancel()
            try:
                await self.reconnect_task
            except asyncio.CancelledError:
                pass
        
        await self.disconnect()
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get client connection and message statistics.
        
        Returns:
            Dictionary containing client statistics
        """
        return {
            "state": self.state.value,
            "connection_attempts": self.connection_attempts,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "last_connection_time": self.last_connection_time,
            "uptime_seconds": time.time() - self.last_connection_time if self.last_connection_time else 0,
            "project_id": self.config.project_id,
            "server_url": self.config.server_url
        }
    
    def get_performance_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive performance statistics.
        
        Returns:
            Dictionary containing performance metrics and statistics
        """
        handshake_stats = self.performance_stats.get_handshake_statistics()
        latency_stats = self.performance_stats.get_latency_statistics()
        
        return {
            "handshake": {
                "last_ms": self.performance_stats.last_handshake_time,
                "statistics": handshake_stats,
                "threshold_ms": self.config.performance_thresholds.handshake_max_ms,
                "violations": self.performance_stats.handshake_violations,
                "trend": self.performance_stats.handshake_trend,
                "healthy": self.performance_stats.is_handshake_healthy(
                    self.config.performance_thresholds.handshake_max_ms
                )
            },
            "message_latency": {
                "last_ms": self.performance_stats.last_message_latency,
                "statistics": latency_stats,
                "threshold_ms": self.config.performance_thresholds.message_latency_max_ms,
                "violations": self.performance_stats.latency_violations,
                "trend": self.performance_stats.latency_trend,
                "healthy": self.performance_stats.is_latency_healthy(
                    self.config.performance_thresholds.message_latency_max_ms
                )
            },
            "pending_messages": len(self.performance_stats.pending_messages),
            "sample_counts": {
                "handshake_samples": len(self.performance_stats.handshake_times),
                "latency_samples": len(self.performance_stats.message_latencies)
            }
        }
    
    def validate_performance_targets(self) -> Dict[str, Any]:
        """
        Validate current performance against targets.
        
        Returns:
            Dictionary containing validation results
        """
        handshake_healthy = self.performance_stats.is_handshake_healthy(
            self.config.performance_thresholds.handshake_max_ms
        )
        latency_healthy = self.performance_stats.is_latency_healthy(
            self.config.performance_thresholds.message_latency_max_ms
        )
        
        overall_healthy = handshake_healthy and latency_healthy
        
        return {
            "overall_healthy": overall_healthy,
            "handshake_target_met": handshake_healthy,
            "latency_target_met": latency_healthy,
            "handshake_threshold_ms": self.config.performance_thresholds.handshake_max_ms,
            "latency_threshold_ms": self.config.performance_thresholds.message_latency_max_ms,
            "last_handshake_ms": self.performance_stats.last_handshake_time,
            "last_latency_ms": self.performance_stats.last_message_latency,
            "violation_counts": {
                "handshake": self.performance_stats.handshake_violations,
                "latency": self.performance_stats.latency_violations
            }
        }
    
    def get_performance_report(self) -> str:
        """
        Generate a comprehensive performance report.
        
        Returns:
            Formatted performance report string
        """
        perf_stats = self.get_performance_statistics()
        validation = self.validate_performance_targets()
        
        report = []
        report.append("=== WebSocket Performance Report ===")
        report.append(f"Overall Health: {'✓ HEALTHY' if validation['overall_healthy'] else '✗ DEGRADED'}")
        report.append("")
        
        # Handshake performance
        handshake = perf_stats["handshake"]
        report.append("Handshake Performance:")
        report.append(f"  Target: ≤{handshake['threshold_ms']:.0f}ms")
        report.append(f"  Last: {handshake['last_ms']:.1f}ms" if handshake['last_ms'] else "  Last: N/A")
        report.append(f"  Status: {'✓ HEALTHY' if handshake['healthy'] else '✗ EXCEEDED'}")
        report.append(f"  Trend: {handshake['trend'].upper()}")
        report.append(f"  Violations: {handshake['violations']}")
        
        if handshake['statistics']['avg'] > 0:
            stats = handshake['statistics']
            report.append(f"  Statistics: min={stats['min']:.1f}ms, avg={stats['avg']:.1f}ms, max={stats['max']:.1f}ms")
            report.append(f"  Percentiles: p95={stats['p95']:.1f}ms, p99={stats['p99']:.1f}ms")
        
        report.append("")
        
        # Message latency performance
        latency = perf_stats["message_latency"]
        report.append("Message Latency Performance:")
        report.append(f"  Target: ≤{latency['threshold_ms']:.0f}ms")
        report.append(f"  Last: {latency['last_ms']:.1f}ms" if latency['last_ms'] else "  Last: N/A")
        report.append(f"  Status: {'✓ HEALTHY' if latency['healthy'] else '✗ EXCEEDED'}")
        report.append(f"  Trend: {latency['trend'].upper()}")
        report.append(f"  Violations: {latency['violations']}")
        
        if latency['statistics']['avg'] > 0:
            stats = latency['statistics']
            report.append(f"  Statistics: min={stats['min']:.1f}ms, avg={stats['avg']:.1f}ms, max={stats['max']:.1f}ms")
            report.append(f"  Percentiles: p95={stats['p95']:.1f}ms, p99={stats['p99']:.1f}ms")
        
        report.append("")
        report.append(f"Sample Counts: {perf_stats['sample_counts']['handshake_samples']} handshake, {perf_stats['sample_counts']['latency_samples']} latency")
        report.append(f"Pending Messages: {perf_stats['pending_messages']}")
        
        return "\n".join(report)
    
    def reset_performance_statistics(self) -> None:
        """Reset all performance statistics."""
        self.performance_stats = PerformanceStats()
        self.logger.info("Performance statistics reset")
    
    def get_performance_history(self, metric_type: str = "both", count: int = 10) -> Dict[str, List[float]]:
        """
        Get recent performance history.
        
        Args:
            metric_type: Type of metrics to return ("handshake", "latency", or "both")
            count: Number of recent measurements to return
            
        Returns:
            Dictionary containing recent performance measurements
        """
        history = {}
        
        if metric_type in ["handshake", "both"]:
            recent_handshake = list(self.performance_stats.handshake_times)[-count:]
            history["handshake_times_ms"] = recent_handshake
        
        if metric_type in ["latency", "both"]:
            recent_latency = list(self.performance_stats.message_latencies)[-count:]
            history["message_latencies_ms"] = recent_latency
        
        return history
    
    def get_reconnect_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive reconnect metrics and statistics.
        
        Returns:
            Dictionary containing detailed reconnect metrics
        """
        return {
            "reconnect_attempts": self.reconnect_metrics.reconnect_attempts,
            "successful_reconnects": self.reconnect_metrics.successful_reconnects,
            "failed_reconnects": self.reconnect_metrics.failed_reconnects,
            "success_rate_percent": self.reconnect_metrics.get_success_rate(),
            "average_reconnect_time_s": self.reconnect_metrics.get_average_reconnect_time(),
            "reconnect_times_s": list(self.reconnect_metrics.reconnect_times),
            "error_distribution": self.reconnect_metrics.get_error_distribution(),
            "error_categories": dict(self.reconnect_metrics.error_categories),
            "state_transitions": self.reconnect_metrics.state_transitions[-20:],  # Last 20 transitions
            "time_in_states_s": dict(self.reconnect_metrics.time_in_states),
            "recent_connection_failures": self.reconnect_metrics.connection_failures[-10:],  # Last 10 failures
            "handshake_times_during_reconnect_ms": list(self.reconnect_metrics.handshake_times_during_reconnect),
            "message_latency_after_reconnect_ms": list(self.reconnect_metrics.message_latency_after_reconnect),
            "correlation_id": self.correlation_id
        }
    
    def get_reconnect_statistics_summary(self) -> Dict[str, Any]:
        """
        Get a summary of reconnect statistics for quick overview.
        
        Returns:
            Dictionary containing key reconnect statistics
        """
        metrics = self.get_reconnect_metrics()
        
        # Calculate additional statistics
        recent_failures = len([f for f in self.reconnect_metrics.connection_failures
                              if time.time() - f["timestamp"] < 300])  # Last 5 minutes
        
        most_common_error = None
        if self.reconnect_metrics.error_categories:
            most_common_error = max(self.reconnect_metrics.error_categories.items(),
                                  key=lambda x: x[1])[0]
        
        return {
            "overall_health": "healthy" if metrics["success_rate_percent"] >= 80 else "degraded",
            "success_rate_percent": metrics["success_rate_percent"],
            "total_attempts": metrics["reconnect_attempts"],
            "recent_failures_5min": recent_failures,
            "average_reconnect_time_s": metrics["average_reconnect_time_s"],
            "most_common_error": most_common_error,
            "current_state": self.state.value,
            "connection_attempts": self.connection_attempts,
            "uptime_s": time.time() - self.last_connection_time if self.last_connection_time else 0
        }
    
    def reset_reconnect_metrics(self) -> None:
        """Reset all reconnect metrics and statistics."""
        self.reconnect_metrics = ReconnectMetrics()
        self.structured_logger.info(
            "Reconnect metrics reset",
            status=LogStatus.COMPLETED,
            reset_timestamp=time.time()
        )
        self.logger.info("Reconnect metrics reset")


# Example usage and testing functions
async def example_usage():
    """Example of how to use the WebSocket demo client."""
    # Configure client
    config = ClientConfig(
        project_id="demo-example",
        server_url="ws://localhost:8090"
    )
    
    client = WebSocketDemoClient(config)
    
    # Set up event handlers
    def on_message(message: Dict[str, Any]) -> None:
        print(f"📨 Received: {message['type']} - {message['payload']}")
    
    def on_state_change(state: ConnectionState) -> None:
        print(f"🔄 State changed to: {state}")
    
    def on_error(error: Exception) -> None:
        print(f"❌ Error: {error}")
    
    client.on_message = on_message
    client.on_state_change = on_state_change
    client.on_error = on_error
    
    try:
        # Connect and run
        print("🚀 Starting WebSocket demo client...")
        await client.connect()
        
        # Send a test message
        await client.send_message(
            MessageType.EXECUTION_UPDATE,
            {"status": "running", "progress": 50.0}
        )
        
        # Run for a short time
        run_task = asyncio.create_task(client.run())
        await asyncio.sleep(10)  # Run for 10 seconds
        
        # Stop client
        await client.stop()
        
        # Print statistics
        stats = client.get_statistics()
        print(f"📊 Final statistics: {stats}")
        
    except KeyboardInterrupt:
        print("🛑 Interrupted by user")
        await client.stop()


if __name__ == "__main__":
    # Run example usage
    asyncio.run(example_usage())