# WebSocket Demo Client for Clarity Local Runner - Branch 6.4: Linear Reconnect & Payload Size Limits

This document provides comprehensive documentation and usage instructions for the WebSocket demo client, which connects to the Clarity Local Runner WebSocket devteam endpoint (`/ws/devteam`). This client implements linear reconnect logic following ADD Profile C specifications and enforces payload size limits at the gateway.

## Features

*   **JWT Authentication**: Uses `service_role_key` pattern for secure connection.
*   **Message Envelope Validation**: Ensures all messages adhere to the `{type, ts, projectId, payload}` format.
*   **Connection State Management**: Tracks `CONNECTING`, `CONNECTED`, `DISCONNECTED`, and `RECONNECTING` states.
*   **Linear Reconnect Logic**: Implements fixed 2-second reconnection intervals as per ADD Profile C.
*   **Client-side Payload Validation**: Enforces a 10KB message payload size limit, matching server constraints.
*   **Performance Monitoring**: Real-time tracking of handshake (≤300ms) and message latency (≤500ms) with threshold validation and alerting.
*   **Comprehensive Error Handling**: Provides graceful degradation and detailed error categorization.
*   **Event-Driven Architecture**: Customizable message, state change, error, and performance alert handlers.
*   **Structured Logging**: Integrates with existing project logging patterns, including `correlationId` tracking.
*   **Metrics Collection & Export**: Advanced logging and metrics system with JSON/CSV export capabilities for analysis.
*   **Interactive CLI**: A command-line interface for easy testing and demonstration.

## 1. Complete Usage Guide

### 1.1. Installation and Setup

To run the WebSocket demo client and its associated tools, ensure you have the following prerequisites and follow the setup instructions.

#### Prerequisites

*   **Python 3.9+**: The client is developed in Python.
*   **pip**: Python package installer.
*   **Clarity Local Runner**: The backend server must be running.

#### Setup Instructions

1.  **Clone the Repository (if not already done):**
    ```bash
    git clone [repository-url]
    cd Clarity-Local-Runner
    ```

2.  **Navigate to the `demo` directory:**
    ```bash
    cd demo
    ```

3.  **Install Python Dependencies:**
    It is recommended to use a virtual environment.
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```
    *(Note: A `requirements.txt` file is assumed to exist in the `demo` directory or project root, containing `websockets` and other necessary libraries.)*

4.  **Start the Clarity Local Runner Server:**
    The demo client connects to the Clarity Local Runner. Ensure it is running by navigating to the `docker` directory and executing the `start.sh` script.
    ```bash
    cd ../docker
    ./start.sh
    ```
    Verify server health:
    ```bash
    curl http://localhost:8090/health
    ```
    Expected output: `{"status":"ok"}`

### 1.2. Quick Start Guide

#### Basic Client Usage

The `websocket_demo_client.py` provides a simple example of how to connect, send messages, and handle events.

```python
import asyncio
from demo.websocket_demo_client import WebSocketDemoClient, ClientConfig, MessageType, ConnectionState
from typing import Dict, Any

async def main():
    # Configure client
    config = ClientConfig(
        project_id="my-demo-project",
        server_url="ws://localhost:8090"
    )
    
    client = WebSocketDemoClient(config)
    
    # Set up event handlers
    def on_message(message: Dict[str, Any]) -> None:
        print(f"📨 Received: {message['type']} - {message['payload']}")
    
    def on_state_change(state: ConnectionState) -> None:
        print(f"🔄 State: {state.value}")
    
    def on_error(error: Exception) -> None:
        print(f"❌ Error: {error}")
    
    client.on_message = on_message
    client.on_state_change = on_state_change
    client.on_error = on_error
    
    # Connect and send a test message
    print("🚀 Starting WebSocket demo client...")
    await client.connect()
    
    if client.state == ConnectionState.CONNECTED:
        await client.send_message(
            MessageType.EXECUTION_UPDATE,
            {"status": "running", "progress": 50.0}
        )
        print("Message sent successfully.")
    else:
        print("Failed to connect, cannot send message.")
        
    # Run for 10 seconds to receive messages and handle reconnects
    run_task = asyncio.create_task(client.run())
    await asyncio.sleep(10)
    
    # Stop client and print statistics
    await client.stop()
    stats = client.get_statistics()
    print(f"📊 Final statistics: {stats}")

# Run the example
if __name__ == "__main__":
    asyncio.run(main())
```

#### Running the Interactive CLI Demo

The `cli_demo.py` provides an interactive command-line interface for testing the WebSocket client.

1.  **Navigate to the `demo` directory:**
    ```bash
    cd demo
    ```
2.  **Run the CLI demo:**
    ```bash
    python cli_demo.py
    ```
    This will launch an interactive interface displaying connection status, performance metrics, and available commands.

### 1.3. Detailed CLI Command Reference

The interactive CLI (`cli_demo.py`) offers the following commands:

*   **`c` / `connect`**: Establishes a WebSocket connection to the server.
*   **`d` / `disconnect`**: Gracefully disconnects from the WebSocket server.
*   **`r` / `reconnect`**: Initiates a reconnect test by disconnecting and then attempting to reconnect. This validates the linear reconnect logic.
*   **`1` / `send-update`**: Sends an `execution-update` message with a sample payload.
*   **`2` / `send-log`**: Sends an `execution-log` message with a sample payload.
*   **`3` / `send-custom`**: Sends a custom message (using `execution-update` type with a custom payload).
*   **`s` / `stats`**: Displays detailed connection, message, reconnect, and performance statistics.
*   **`m` / `metrics`**: Toggles real-time metrics collection on or off. When active, it collects snapshots of client performance and reconnect data.
*   **`e` / `export`**: Exports collected metrics data to JSON and CSV files. This command is only available when metrics collection is active.
*   **`t` / `trends`**: Shows performance trends and analysis based on collected metrics. Requires a minimum number of snapshots to provide meaningful trends.
*   **`h` / `help`**: Displays a summary of available commands, performance targets, and connection states.
*   **`q` / `quit` / `exit`**: Exits the CLI application gracefully.

### 1.4. Configuration Options and Customization

The `ClientConfig` dataclass in [`demo/websocket_demo_client.py`](demo/websocket_demo_client.py:258) allows for extensive customization of the WebSocket client's behavior.

```python
@dataclass
class ClientConfig:
    server_url: str = "ws://localhost:8090"
    project_id: str = "demo-project"
    service_role_key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."  # Demo JWT
    reconnect_interval: float = 2.0  # ADD Profile C: Fixed 2-second intervals
    max_payload_size: int = 10240  # 10KB limit to match server
    connection_timeout: float = 10.0
    message_timeout: float = 5.0
    performance_thresholds: PerformanceThresholds = field(default_factory=PerformanceThresholds)
```

#### Key Configuration Parameters

*   **`server_url`** (`str`): The base URL of the WebSocket server (default: `ws://localhost:8090`). The full endpoint used is `server_url/api/v1/ws/devteam`.
*   **`project_id`** (`str`): A unique identifier for the project, used for message routing and correlation (default: `demo-project`). This is a required parameter for message envelopes.
*   **`service_role_key`** (`str`): A JWT token used for authenticating the WebSocket connection. A demo token is provided by default, but a valid token from your environment should be used in production.
*   **`reconnect_interval`** (`float`): The fixed interval in seconds between reconnection attempts (default: `2.0`). This adheres to ADD Profile C for linear reconnect.
*   **`max_payload_size`** (`int`): The maximum allowed size for a message payload in bytes (default: `10240` bytes, i.e., 10KB). Messages exceeding this limit will be rejected client-side.
*   **`connection_timeout`** (`float`): The maximum time in seconds to wait for the initial WebSocket connection to be established (default: `10.0`).
*   **`message_timeout`** (`float`): The maximum time in seconds to wait for a message to be received from the server before timing out (default: `5.0`).
*   **`performance_thresholds`** (`PerformanceThresholds`): An instance of `PerformanceThresholds` defining the maximum acceptable handshake and message latency times.
    *   `handshake_max_ms`: Maximum allowed handshake time in milliseconds (default: `300.0`).
    *   `message_latency_max_ms`: Maximum allowed message round-trip latency in milliseconds (default: `500.0`).

## 2. Technical Documentation

### 2.1. Architecture Overview and Design Patterns

The WebSocket demo client is designed with an event-driven, modular architecture to ensure robustness, maintainability, and clear separation of concerns.

*   **Client-Server Interaction**: The client communicates with the Clarity Local Runner's `/api/v1/ws/devteam` endpoint over WebSocket.
*   **Event-Driven Architecture**: The client exposes several callback handlers (`on_message`, `on_state_change`, `on_error`, `on_performance_alert`) allowing external components (like the CLI demo) to react to client events without tight coupling.
*   **State Management**: The `ConnectionState` enum (`DISCONNECTED`, `CONNECTING`, `CONNECTED`, `RECONNECTING`) provides a clear and consistent way to track the client's connection status, enabling robust logic for reconnection and error handling.
*   **Structured Logging**: Integrated with the project's structured logging system (`core.structured_logging`), ensuring all significant events, errors, and performance metrics are logged with contextual information like `projectId` and `correlationId`. This aids in debugging and operational monitoring.

### 2.2. Linear Reconnect Logic (ADD Profile C)

The client implements a linear reconnection strategy as specified in ADD Profile C.

*   **Fixed 2-Second Intervals**: When a connection is lost or fails to establish, the client enters the `RECONNECTING` state and attempts to re-establish the connection at fixed 2-second intervals. This prevents connection storms and provides predictable recovery behavior.
*   **`_reconnect_loop`**: This internal asynchronous loop continuously attempts to connect when the client is not in the `CONNECTED` state. It incorporates the `reconnect_interval` delay between attempts.
*   **State Transitions**: During a reconnect cycle, the client transitions from `DISCONNECTED` or `CONNECTED` (upon loss) to `RECONNECTING`, then to `CONNECTING` for each attempt, and finally back to `CONNECTED` upon success.
*   **Graceful Shutdown**: The reconnect loop respects the `running` flag, ensuring it terminates cleanly when the client is explicitly stopped.

### 2.3. Performance Monitoring and Metrics System

The client includes a robust performance monitoring system to track key metrics and ensure adherence to performance targets.

*   **Performance Targets**:
    *   **Handshake Time**: The time taken to establish a WebSocket connection should be **≤300ms**.
    *   **Message Latency**: The round-trip time for a message (send to receive acknowledgment) should be **≤500ms**.
*   **`PerformanceStats` Class**: This class (`demo/websocket_demo_client.py:151`) tracks historical handshake times and message latencies using `deque` for rolling windows. It also records threshold violations and calculates performance trends (`improving`, `degrading`, `stable`).
*   **`MetricsCollector` (`demo/metrics_collector.py`)**: A centralized system for collecting, aggregating, and exporting detailed metrics snapshots from the `WebSocketDemoClient`.
    *   **Real-time Collection**: Automatically collects snapshots of reconnect and performance metrics at a configurable `collection_interval`.
    *   **Aggregation**: Can aggregate metrics over specified time periods, providing summaries of reconnect success rates, average times, error distributions, and performance summaries.
    *   **Trend Analysis**: Provides insights into metric trends (e.g., `success_rate`, `handshake_time`, `message_latency`, `reconnect_time`) over time.
*   **Performance Alerts**: The client triggers `on_performance_alert` callbacks when handshake or message latency thresholds are exceeded, allowing for immediate notification and action.

### 2.4. Message Envelope Format and Validation

All messages exchanged with the WebSocket endpoint adhere to a standardized envelope format as defined in ADD Profile C.

#### Message Envelope Structure

```json
{
  "type": "execution-update",
  "ts": "2025-01-14T18:30:00.123Z",
  "projectId": "customer-123/project-abc",
  "payload": {
    "execution_id": "exec-456",
    "status": "running",
    "progress": 45.2
  }
}
```

#### Required Fields

*   **`type`** (`str`): The type of message, corresponding to the `MessageType` enum (e.g., `execution-update`, `execution-log`, `error`, `completion`).
*   **`ts`** (`str`): An ISO 8601 formatted timestamp (e.g., `2025-01-14T18:30:00.123Z`) indicating when the message was created. Must end with 'Z' for UTC.
*   **`projectId`** (`str`): A non-empty string identifying the project associated with the message.
*   **`payload`** (`dict`): A dictionary containing the actual message data. The content of the payload is specific to the `type` of message.

#### Client-Side Validation

The client performs rigorous validation on both outgoing and incoming messages:

*   **Envelope Format**: Ensures all required fields (`type`, `ts`, `projectId`, `payload`) are present and correctly structured.
*   **Message Type**: Validates that the `type` field matches one of the supported `MessageType` enum values.
*   **Timestamp Format**: Checks that the `ts` field is a valid ISO 8601 timestamp ending with 'Z'.
*   **Project ID**: Ensures `projectId` is a non-empty string.
*   **Payload Structure**: Verifies that `payload` is a dictionary.
*   **Payload Size**: Enforces the `max_payload_size` (10KB) limit. Messages exceeding this size are rejected before being sent.

### 2.5. Authentication and Security Considerations

Security is a critical aspect of the WebSocket client, particularly concerning authentication and data integrity.

*   **JWT Authentication**: The client uses a JSON Web Token (JWT) provided via the `service_role_key` in the `ClientConfig` for authentication. This token is sent in the `Authorization` header during the WebSocket handshake.
*   **Token Management Best Practices**:
    *   **Token Rotation**: In production environments, JWT tokens should be regularly rotated to minimize the impact of compromised tokens.
    *   **Secure Storage**: `service_role_key` should be stored securely (e.g., environment variables, secret management services) and never hardcoded in production code.
    *   **Token Validation**: The server is responsible for validating the JWT's signature, expiration, and permissions.
*   **Network Security**:
    *   **TLS/WSS**: Always use secure WebSocket connections (`wss://`) in production to encrypt data in transit and prevent eavesdropping. The `server_url` should reflect this.
    *   **Firewall Rules**: Restrict access to the WebSocket endpoint at the network level to authorized clients only.
    *   **Rate Limiting**: Implement client-side rate limiting if necessary to prevent abuse or accidental overload of the server.
*   **Data Validation**: Beyond envelope validation, ensure that the content within the `payload` is also validated and sanitized to prevent injection attacks or processing of malicious data.

## 3. Testing and Validation

The `demo` directory includes comprehensive test suites for both performance and reconnect functionality.

### 3.1. Test Suite Overview and Execution Instructions

To run the test suites, navigate to the `demo` directory and execute the respective Python scripts.

*   **Performance Test Scenarios**: [`demo/performance_test_scenarios.py`](demo/performance_test_scenarios.py)
*   **Reconnect Test Scenarios**: [`demo/reconnect_test_scenarios.py`](demo/reconnect_test_scenarios.py)

#### Running All Tests

```bash
cd demo
python performance_test_scenarios.py
python reconnect_test_scenarios.py
```

Each script will execute its defined test scenarios and print a summary of the results to the console.

#### Test Result Status

The `TestResult` enum (`PASS`, `FAIL`, `SKIP`, `ERROR`) is used to indicate the outcome of each test scenario.

### 3.2. Performance Test Scenarios and Validation

The [`demo/performance_test_scenarios.py`](demo/performance_test_scenarios.py) module validates the client's performance under various conditions against defined thresholds.

*   **`test_basic_connection_performance`**: Verifies initial connection handshake times.
    *   **Validation**: Handshake time ≤300ms.
*   **`test_message_latency_performance`**: Measures the round-trip latency for messages.
    *   **Validation**: Message latency ≤500ms.
*   **`test_high_frequency_messaging`**: Assesses client performance when sending a large number of messages rapidly.
    *   **Validation**: Checks for message send failures and overall performance degradation.
*   **`test_performance_threshold_validation`**: Explicitly tests if the client's internal performance validation and alerting system correctly identifies and reports threshold breaches.
*   **`test_performance_history_tracking`**: Verifies that performance history is correctly tracked and that basic trend analysis can be performed.

**Expected Outcomes**: All performance tests should ideally `PASS`, indicating that handshake and message latency targets are met, and the client remains stable under load.

### 3.3. Reconnect Test Scenarios and Expected Behavior

The [`demo/reconnect_test_scenarios.py`](demo/reconnect_test_scenarios.py) module rigorously tests the linear reconnect logic and connection stability.

*   **`test_basic_reconnect`**: Simulates a manual disconnect and validates that the client successfully reconnects using the linear 2-second interval.
    *   **Expected Behavior**: Client transitions to `RECONNECTING`, then `CONNECTING`, and finally `CONNECTED` within the expected time frame.
*   **`test_multiple_reconnects`**: Executes several disconnect/reconnect cycles to ensure stability and consistent behavior over time.
    *   **Expected Behavior**: Each cycle should result in a successful reconnection with linear timing, and overall success rate should be high (e.g., ≥80%).
*   **`test_server_unavailable`**: Tests the client's behavior when the target server is completely unreachable.
    *   **Expected Behavior**: Client should continuously attempt to reconnect at 2-second intervals, gracefully handling connection refused errors, and successfully recover when the server becomes available again.
*   **`test_network_interruption_simulation`**: Simulates a network interruption (e.g., by forcibly closing the WebSocket) and validates the client's ability to detect the interruption, initiate reconnects, and resume message delivery after recovery.
    *   **Expected Behavior**: Client detects disconnection, enters `RECONNECTING` state, and successfully re-establishes connection, allowing messages to be sent again.
*   **`test_reconnect_performance_validation`**: Combines reconnect cycles with performance checks to ensure that reconnects themselves do not introduce significant performance degradation.
    *   **Expected Behavior**: Handshake times after reconnects should remain within the ≤300ms target, and reconnect intervals should adhere to the 2-second linear timing.
*   **`test_state_consistency_validation`**: Verifies that the client's `ConnectionState` transitions are logical and that no invalid state changes occur during complex connection/reconnection sequences.
    *   **Expected Behavior**: State transitions follow a defined valid path (e.g., `DISCONNECTED` -> `CONNECTING` -> `CONNECTED`), and the client's state accurately reflects its actual connection status.

## 4. Troubleshooting and FAQ

### 4.1. Common Issues and Solutions

1.  **Connection Refused**
    ```
    Error: Connection failed: [Errno 61] Connection refused
    ```
    *   **Solution**: Ensure the Clarity Local Runner server is running. Use `docker ps` to verify container status.
    *   **Check**: Confirm the server health endpoint is accessible: `curl http://localhost:8090/health`.
2.  **Authentication Failed**
    ```
    Error: Authentication failed: 403 Forbidden
    ```
    *   **Solution**: Verify that the `service_role_key` in your `ClientConfig` is valid and has not expired.
    *   **Check**: Ensure you are using the correct JWT token from your `docker/.env` or equivalent secure storage.
3.  **Invalid Project ID**
    ```
    Error: Project ID must be a non-empty string
    ```
    *   **Solution**: Ensure the `project_id` in your `ClientConfig` is set and is a non-empty string.
    *   **Check**: Project ID format matches server expectations (e.g., `customer-123/project-abc`).
4.  **Message Too Large**
    ```
    Error: Message size 12000 bytes exceeds limit of 10240 bytes
    ```
    *   **Solution**: Reduce the size of your message payload or split large data into multiple smaller messages.
    *   **Check**: Use the client's `validate_payload_size()` method before sending to preemptively check size.
5.  **Reconnection Issues**
    ```
    State: reconnecting (attempt 5)
    ```
    *   **Solution**: Check network connectivity between the client and the server. Verify the server is operational and its WebSocket endpoint is accessible.
    *   **Check**: Review server logs (`docker logs clarity-local-api`) for any connection-related errors.

### 4.2. Performance Troubleshooting Guide

*   **Interpreting Performance Metrics**:
    *   **Handshake Time**: If consistently above 300ms, investigate network latency, server load, or authentication overhead.
    *   **Message Latency**: If consistently above 500ms, check network conditions, server processing time, or client-side message handling efficiency.
    *   **Violations**: High violation counts indicate frequent breaches of performance thresholds.
    *   **Trends**: A "degrading" trend suggests a worsening performance over time, requiring deeper investigation.
*   **Debugging Slow Handshakes/High Latency**:
    *   **Network Diagnostics**: Use tools like `ping`, `traceroute`, or network monitoring utilities to check connectivity and latency to the server.
    *   **Server Load**: Verify that the Clarity Local Runner server is not under heavy load, which could impact response times.
    *   **Client-side Processing**: Ensure your `on_message` handler is efficient and not introducing delays.
    *   **Logging**: Enable debug logging in the client to get more granular timing information.

### 4.3. Connection Issues and Debugging

*   **Debug Logging**: Enable debug logging in your Python script to get detailed client-side information.
    ```python
    import logging
    logging.basicConfig(level=logging.DEBUG)
    # Or for specific client logger:
    # logger = logging.getLogger('demo.websocket_demo_client')
    # logger.setLevel(logging.DEBUG)
    ```
*   **Server-Side Verification**: Always check the server logs for corresponding connection attempts and errors.
    ```bash
    docker logs clarity-local-api
    # To follow logs in real-time:
    docker logs -f clarity-local-api
    ```
    Look for messages related to WebSocket connections, authentication failures, or message processing errors.

### 4.4. Error Codes and Their Meanings

The client categorizes connection failures for better diagnostics:

*   **`connection_timeout`**: The client failed to establish a connection within the `connection_timeout` period.
*   **`invalid_uri`**: The provided `server_url` or constructed WebSocket URI is malformed.
*   **`authentication_failed`**: The server rejected the connection due to an invalid or expired JWT token (e.g., 401 Unauthorized, 403 Forbidden).
*   **`endpoint_not_found`**: The WebSocket endpoint (`/api/v1/ws/devteam`) was not found on the server (e.g., 404 Not Found).
*   **`connection_refused`**: The server actively refused the connection, often indicating the server is not running or the port is blocked.
*   **`connection_error`**: A general error occurred during the connection attempt that doesn't fit other specific categories.

## 5. API Reference

### 5.1. `WebSocketDemoClient` Class Documentation

The core of the demo client is the `WebSocketDemoClient` class (`demo/websocket_demo_client.py:270`).

#### Constructor

*   `__init__(self, config: ClientConfig)`: Initializes the client with the provided `ClientConfig`.

#### Key Methods

*   `async connect(self) -> bool`: Establishes a WebSocket connection. Returns `True` on success, `False` otherwise. Measures handshake time.
*   `async disconnect(self) -> None`: Gracefully closes the WebSocket connection.
*   `async send_message(self, message_type: MessageType, payload: Dict[str, Any]) -> bool`: Sends a message with the specified type and payload. Returns `True` if sent, `False` if not connected or validation fails. Tracks message latency.
*   `async run(self) -> None`: The main client loop that continuously receives messages and manages automatic reconnection.
*   `async stop(self) -> None`: Stops the client's operation and disconnects.
*   `get_statistics(self) -> Dict[str, Any]`: Returns current connection and message statistics (state, attempts, sent/received counts, uptime).
*   `get_performance_statistics(self) -> Dict[str, Any]`: Provides detailed performance metrics, including handshake and message latency statistics, thresholds, violations, and trends.
*   `validate_performance_targets(self) -> Dict[str, Any]`: Checks if current performance metrics meet the configured thresholds.
*   `get_performance_report(self) -> str`: Generates a human-readable comprehensive performance report.
*   `get_reconnect_metrics(self) -> Dict[str, Any]`: Returns detailed metrics related to reconnection attempts, success rates, error categories, and state transitions.
*   `create_message_envelope(self, message_type: MessageType, payload: Dict[str, Any], timestamp: Optional[str] = None) -> Dict[str, Any]`: Creates a standardized message envelope.
*   `validate_message_envelope(self, message: Dict[str, Any]) -> bool`: Validates the structure and content of a message envelope.
*   `validate_payload_size(self, message: Dict[str, Any]) -> bool`: Validates if the message payload size is within the configured limit.

#### Event Handlers (Callbacks)

These are optional callable attributes that can be set to react to client events:

*   `on_message: Optional[Callable[[Dict[str, Any]], None]]`: Called when a message is successfully received from the server.
*   `on_state_change: Optional[Callable[[ConnectionState], None]]`: Called when the client's connection state changes.
*   `on_error: Optional[Callable[[Exception], None]]`: Called when a significant error occurs within the client.
*   `on_performance_alert: Optional[Callable[[str, float, float], None]]`: Called when a performance metric (e.g., handshake time, message latency) exceeds its defined threshold.

### 5.2. `MetricsCollector` API Documentation

The `MetricsCollector` class (`demo/metrics_collector.py:61`) is responsible for gathering and analyzing performance and reconnect data.

#### Constructor

*   `__init__(self, max_snapshots: int = 1000, collection_interval: float = 5.0)`: Initializes the collector with a maximum number of snapshots and a collection interval.

#### Key Methods

*   `collect_snapshot(self, websocket_client) -> MetricsSnapshot`: Manually collects a snapshot of metrics from a `WebSocketDemoClient` instance.
*   `start_collection(self, websocket_client) -> None`: Starts an asynchronous loop to automatically collect metrics snapshots at `collection_interval`.
*   `async stop_collection(self) -> None`: Stops the automatic metrics collection loop.
*   `aggregate_metrics(self, start_time: Optional[float] = None, end_time: Optional[float] = None) -> MetricsAggregation`: Aggregates collected snapshots over a specified time range.
*   `export_to_json(self, filepath: str, include_snapshots: bool = True, include_aggregations: bool = True) -> None`: Exports collected metrics (snapshots and/or aggregations) to a JSON file.
*   `export_to_csv(self, filepath: str, data_type: str = "snapshots") -> None`: Exports collected metrics (either "snapshots" or "aggregations") to a CSV file.
*   `get_trend_analysis(self, metric_name: str, window_size: int = 10) -> Dict[str, Any]`: Analyzes trends for a specific metric (e.g., "success_rate", "handshake_time", "message_latency", "reconnect_time") using a moving average.
*   `get_dashboard_data(self) -> Dict[str, Any]`: Provides a summary of real-time metrics suitable for dashboard display.
*   `reset_metrics(self) -> None`: Clears all collected snapshots and aggregations.

### 5.3. Configuration Parameters and Options

Refer to [Section 1.4. Configuration Options and Customization](#1.4-configuration-options-and-customization) for a detailed reference of `ClientConfig` parameters.