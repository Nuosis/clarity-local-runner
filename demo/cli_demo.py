#!/usr/bin/env python3
"""
Interactive CLI Demo for WebSocket Client

This module provides an interactive command-line interface for the WebSocket demo client,
featuring real-time connection status display, performance monitoring, and comprehensive
testing capabilities for the Clarity Local Runner WebSocket endpoint.

Features:
- Interactive CLI with real-time status updates
- Connection management (connect, disconnect, reconnect testing)
- Message sending with different message types
- Performance monitoring (handshake time ≤300ms, latency ≤500ms)
- Statistics display (connection attempts, success rate, uptime, message counts)
- Non-blocking user input with concurrent WebSocket operations
- Color-coded output for better user experience
- Graceful exit handling with proper cleanup
- Enhanced metrics collection and export functionality
"""

import asyncio
import json
import signal
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from websocket_demo_client import ConnectionState

# Import metrics collector
from metrics_collector import MetricsCollector, create_metrics_collector

# Color codes for terminal output
class Colors:
    """ANSI color codes for terminal output."""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Status colors
    GREEN = '\033[92m'    # Connected/Success
    RED = '\033[91m'      # Disconnected/Error
    YELLOW = '\033[93m'   # Connecting/Warning
    BLUE = '\033[94m'     # Info
    CYAN = '\033[96m'     # Commands
    MAGENTA = '\033[95m'  # Performance metrics
    
    # Message type colors
    MSG_UPDATE = '\033[92m'    # execution-update (green)
    MSG_LOG = '\033[94m'       # execution-log (blue)
    MSG_ERROR = '\033[91m'     # error (red)
    MSG_COMPLETION = '\033[95m' # completion (magenta)


@dataclass
class EnhancedPerformanceDisplay:
    """Enhanced performance display for CLI with advanced metrics."""
    performance_alerts: List[Dict[str, Any]] = field(default_factory=list)
    max_alerts: int = 5
    
    def add_performance_alert(self, metric_type: str, actual_value: float, threshold: float) -> None:
        """Add a performance alert."""
        alert = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "metric_type": metric_type,
            "actual_value": actual_value,
            "threshold": threshold,
            "severity": "HIGH" if actual_value > threshold * 1.5 else "MEDIUM"
        }
        self.performance_alerts.append(alert)
        
        # Keep only recent alerts
        if len(self.performance_alerts) > self.max_alerts:
            self.performance_alerts.pop(0)
    
    def get_performance_status_with_trend(self, perf_stats: Dict[str, Any]) -> Dict[str, str]:
        """Get performance status with trend indicators and color coding."""
        handshake = perf_stats["handshake"]
        latency = perf_stats["message_latency"]
        
        # Handshake status
        if handshake["last_ms"] is None:
            handshake_status = f"{Colors.YELLOW}No data{Colors.RESET}"
        elif handshake["healthy"]:
            trend_icon = self._get_trend_icon(handshake["trend"])
            handshake_status = f"{Colors.GREEN}✓ {handshake['last_ms']:.1f}ms {trend_icon}{Colors.RESET}"
        else:
            trend_icon = self._get_trend_icon(handshake["trend"])
            handshake_status = f"{Colors.RED}✗ {handshake['last_ms']:.1f}ms {trend_icon}{Colors.RESET}"
        
        # Latency status
        if latency["last_ms"] is None:
            latency_status = f"{Colors.YELLOW}No data{Colors.RESET}"
        elif latency["healthy"]:
            trend_icon = self._get_trend_icon(latency["trend"])
            latency_status = f"{Colors.GREEN}✓ {latency['last_ms']:.1f}ms {trend_icon}{Colors.RESET}"
        else:
            trend_icon = self._get_trend_icon(latency["trend"])
            latency_status = f"{Colors.RED}✗ {latency['last_ms']:.1f}ms {trend_icon}{Colors.RESET}"
        
        return {
            "handshake": handshake_status,
            "latency": latency_status
        }
    
    def _get_trend_icon(self, trend: str) -> str:
        """Get trend icon based on trend direction."""
        if trend == "improving":
            return f"{Colors.GREEN}↗{Colors.RESET}"
        elif trend == "degrading":
            return f"{Colors.RED}↘{Colors.RESET}"
        else:
            return f"{Colors.BLUE}→{Colors.RESET}"
    
    def get_performance_summary(self, perf_stats: Dict[str, Any]) -> str:
        """Get a comprehensive performance summary."""
        handshake = perf_stats["handshake"]
        latency = perf_stats["message_latency"]
        
        summary = []
        
        # Overall health
        overall_healthy = handshake["healthy"] and latency["healthy"]
        health_status = f"{Colors.GREEN}HEALTHY{Colors.RESET}" if overall_healthy else f"{Colors.RED}DEGRADED{Colors.RESET}"
        summary.append(f"Overall: {health_status}")
        
        # Handshake details
        if handshake["statistics"]["avg"] > 0:
            stats = handshake["statistics"]
            summary.append(f"Handshake: avg={stats['avg']:.1f}ms, p95={stats['p95']:.1f}ms")
        
        # Latency details
        if latency["statistics"]["avg"] > 0:
            stats = latency["statistics"]
            summary.append(f"Latency: avg={stats['avg']:.1f}ms, p95={stats['p95']:.1f}ms")
        
        # Violations
        total_violations = handshake["violations"] + latency["violations"]
        if total_violations > 0:
            summary.append(f"{Colors.RED}Violations: {total_violations}{Colors.RESET}")
        
        return " | ".join(summary)


class CLIDemo:
    """
    Interactive CLI demo for WebSocket client.
    
    Provides a comprehensive interface for testing WebSocket connectivity,
    message handling, and performance monitoring with real-time updates.
    """
    
    def __init__(self):
        """Initialize CLI demo."""
        # Import here to avoid circular imports
        from websocket_demo_client import WebSocketDemoClient, ClientConfig, ConnectionState, MessageType
        
        self.WebSocketDemoClient = WebSocketDemoClient
        self.ClientConfig = ClientConfig
        self.ConnectionState = ConnectionState
        self.MessageType = MessageType
        
        # Initialize client with default config
        self.config = self.ClientConfig(project_id="cli-demo")
        self.client = self.WebSocketDemoClient(self.config)
        
        # Enhanced performance tracking
        self.performance_display = EnhancedPerformanceDisplay()
        
        # Metrics collector integration
        self.metrics_collector: Optional[MetricsCollector] = None
        self.metrics_enabled = False
        
        # CLI state
        self.running = True
        self.display_task: Optional[asyncio.Task] = None
        self.client_task: Optional[asyncio.Task] = None
        self.input_queue: asyncio.Queue = asyncio.Queue()
        
        # Message log for display
        self.message_log: List[Dict[str, Any]] = []
        self.max_log_entries = 10
        
        # Setup client event handlers
        self._setup_client_handlers()
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
    
    def _setup_client_handlers(self) -> None:
        """Setup WebSocket client event handlers."""
        self.client.on_message = self._handle_message
        self.client.on_state_change = self._handle_state_change
        self.client.on_error = self._handle_error
        self.client.on_performance_alert = self._handle_performance_alert
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            print(f"\n{Colors.YELLOW}Received signal {signum}, shutting down gracefully...{Colors.RESET}")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _handle_message(self, message: Dict[str, Any]) -> None:
        """Handle received WebSocket message."""
        # Add to message log
        log_entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "type": message.get("type", "unknown"),
            "payload": message.get("payload", {}),
            "direction": "received"
        }
        self.message_log.append(log_entry)
        
        # Keep log size manageable
        if len(self.message_log) > self.max_log_entries:
            self.message_log.pop(0)
    
    def _handle_state_change(self, state: 'ConnectionState') -> None:
        """Handle connection state changes."""
        # State changes are now handled by the enhanced client
        pass
    
    def _handle_error(self, error: Exception) -> None:
        """Handle WebSocket errors."""
        log_entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "type": "error",
            "payload": {"error": str(error)},
            "direction": "system"
        }
        self.message_log.append(log_entry)
        
        if len(self.message_log) > self.max_log_entries:
            self.message_log.pop(0)
    
    def _handle_performance_alert(self, metric_type: str, actual_value: float, threshold: float) -> None:
        """Handle performance alerts from the WebSocket client."""
        self.performance_display.add_performance_alert(metric_type, actual_value, threshold)
        
        # Add alert to message log for display
        log_entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "type": "performance_alert",
            "payload": {
                "metric_type": metric_type,
                "actual_value": f"{actual_value:.1f}ms",
                "threshold": f"{threshold:.1f}ms"
            },
            "direction": "system"
        }
        self.message_log.append(log_entry)
        
        if len(self.message_log) > self.max_log_entries:
            self.message_log.pop(0)
    
    def _get_state_color(self, state: 'ConnectionState') -> str:
        """Get color code for connection state."""
        state_colors = {
            self.ConnectionState.CONNECTED: Colors.GREEN,
            self.ConnectionState.CONNECTING: Colors.YELLOW,
            self.ConnectionState.RECONNECTING: Colors.YELLOW,
            self.ConnectionState.DISCONNECTED: Colors.RED
        }
        return state_colors.get(state, Colors.RESET)
    
    def _get_message_color(self, msg_type: str) -> str:
        """Get color code for message type."""
        type_colors = {
            "execution-update": Colors.MSG_UPDATE,
            "execution-log": Colors.MSG_LOG,
            "error": Colors.MSG_ERROR,
            "completion": Colors.MSG_COMPLETION,
            "system": Colors.YELLOW
        }
        return type_colors.get(msg_type, Colors.BLUE)
    
    def _clear_screen(self) -> None:
        """Clear terminal screen."""
        print("\033[2J\033[H", end="")
    
    def _display_header(self) -> None:
        """Display CLI header."""
        print(f"{Colors.BOLD}{Colors.CYAN}╔══════════════════════════════════════════════════════════════════════════════╗{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}║                    WebSocket Demo Client - Interactive CLI                   ║{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}╚══════════════════════════════════════════════════════════════════════════════╝{Colors.RESET}")
        print()
    
    def _display_connection_status(self) -> None:
        """Display current connection status."""
        state = self.client.state
        state_color = self._get_state_color(state)
        
        print(f"{Colors.BOLD}Connection Status:{Colors.RESET}")
        print(f"  State: {state_color}{state.value.upper()}{Colors.RESET}")
        print(f"  Server: {Colors.BLUE}{self.config.server_url}/api/v1/ws/devteam{Colors.RESET}")
        print(f"  Project ID: {Colors.BLUE}{self.config.project_id}{Colors.RESET}")
        print()
    
    def _display_performance_metrics(self) -> None:
        """Display enhanced performance metrics."""
        try:
            perf_stats = self.client.get_performance_statistics()
            status = self.performance_display.get_performance_status_with_trend(perf_stats)
            
            print(f"{Colors.BOLD}Performance Metrics:{Colors.RESET}")
            print(f"  Handshake Time: {status['handshake']}")
            print(f"  Message Latency: {status['latency']}")
            
            # Show performance summary
            summary = self.performance_display.get_performance_summary(perf_stats)
            print(f"  Summary: {summary}")
            
            # Show recent alerts
            if self.performance_display.performance_alerts:
                print(f"  {Colors.RED}Recent Alerts:{Colors.RESET}")
                for alert in self.performance_display.performance_alerts[-2:]:  # Show last 2 alerts
                    severity_color = Colors.RED if alert["severity"] == "HIGH" else Colors.YELLOW
                    print(f"    {alert['timestamp']} {severity_color}{alert['metric_type']}: {alert['actual_value']:.1f}ms > {alert['threshold']:.1f}ms{Colors.RESET}")
            
            print()
        except Exception as e:
            print(f"{Colors.BOLD}Performance Metrics:{Colors.RESET}")
            print(f"  {Colors.YELLOW}Performance data unavailable: {e}{Colors.RESET}")
            print()
    
    def _display_statistics(self) -> None:
        """Display connection and message statistics with enhanced reconnect metrics."""
        stats = self.client.get_statistics()
        success_rate = 0.0
        if stats["connection_attempts"] > 0:
            # Approximate success rate based on current state
            success_rate = (1.0 if self.client.state == self.ConnectionState.CONNECTED else 0.0) * 100
        
        print(f"{Colors.BOLD}Statistics:{Colors.RESET}")
        print(f"  Connection Attempts: {Colors.BLUE}{stats['connection_attempts']}{Colors.RESET}")
        print(f"  Success Rate: {Colors.GREEN if success_rate > 0 else Colors.RED}{success_rate:.1f}%{Colors.RESET}")
        print(f"  Messages Sent: {Colors.BLUE}{stats['messages_sent']}{Colors.RESET}")
        print(f"  Messages Received: {Colors.BLUE}{stats['messages_received']}{Colors.RESET}")
        print(f"  Uptime: {Colors.BLUE}{stats['uptime_seconds']:.1f}s{Colors.RESET}")
        
        # Enhanced reconnect metrics
        try:
            reconnect_metrics = self.client.get_reconnect_metrics()
            print(f"  Reconnect Attempts: {Colors.BLUE}{reconnect_metrics['reconnect_attempts']}{Colors.RESET}")
            print(f"  Reconnect Success Rate: {Colors.GREEN if reconnect_metrics['success_rate_percent'] > 0 else Colors.RED}{reconnect_metrics['success_rate_percent']:.1f}%{Colors.RESET}")
            if reconnect_metrics['average_reconnect_time_s'] > 0:
                print(f"  Avg Reconnect Time: {Colors.BLUE}{reconnect_metrics['average_reconnect_time_s']:.2f}s{Colors.RESET}")
        except Exception:
            pass  # Gracefully handle if reconnect metrics aren't available
        
        # Metrics collection status
        if self.metrics_enabled and self.metrics_collector:
            print(f"  Metrics Collection: {Colors.GREEN}ACTIVE{Colors.RESET} ({len(self.metrics_collector.snapshots)} snapshots)")
        else:
            print(f"  Metrics Collection: {Colors.YELLOW}DISABLED{Colors.RESET}")
        
        print()
    
    def _display_message_log(self) -> None:
        """Display recent message log."""
        print(f"{Colors.BOLD}Recent Messages:{Colors.RESET}")
        if not self.message_log:
            print(f"  {Colors.YELLOW}No messages yet{Colors.RESET}")
        else:
            for msg in self.message_log[-5:]:  # Show last 5 messages
                msg_color = self._get_message_color(msg["type"])
                direction = "←" if msg["direction"] == "received" else "→" if msg["direction"] == "sent" else "•"
                print(f"  {msg['timestamp']} {direction} {msg_color}{msg['type']}{Colors.RESET}")
        print()
    
    def _display_commands(self) -> None:
        """Display available commands."""
        print(f"{Colors.BOLD}Available Commands:{Colors.RESET}")
        commands = [
            ("c", "connect", "Connect to WebSocket server"),
            ("d", "disconnect", "Disconnect from server"),
            ("r", "reconnect", "Test reconnect (disconnect then reconnect)"),
            ("1", "send-update", "Send execution-update message"),
            ("2", "send-log", "Send execution-log message"),
            ("3", "send-custom", "Send custom message"),
            ("s", "stats", "Show detailed statistics"),
            ("m", "metrics", "Toggle metrics collection"),
            ("e", "export", "Export metrics (JSON/CSV)"),
            ("t", "trends", "Show performance trends"),
            ("h", "help", "Show this help"),
            ("q", "quit", "Exit the application")
        ]
        
        for short, long, desc in commands:
            print(f"  {Colors.CYAN}{short}{Colors.RESET}/{Colors.CYAN}{long}{Colors.RESET} - {desc}")
        print()
    
    def _display_prompt(self) -> None:
        """Display command prompt."""
        state_color = self._get_state_color(self.client.state)
        print(f"{state_color}[{self.client.state.value}]{Colors.RESET} Enter command: ", end="", flush=True)
    
    async def _display_loop(self) -> None:
        """Main display loop for real-time updates."""
        while self.running:
            self._clear_screen()
            self._display_header()
            self._display_connection_status()
            self._display_performance_metrics()
            self._display_statistics()
            self._display_message_log()
            self._display_commands()
            self._display_prompt()
            
            await asyncio.sleep(1.0)  # Update every second
    
    async def _input_loop(self) -> None:
        """Handle user input in a non-blocking way."""
        loop = asyncio.get_event_loop()
        
        while self.running:
            try:
                # Read input in a non-blocking way
                command = await loop.run_in_executor(None, input)
                await self.input_queue.put(command.strip().lower())
            except EOFError:
                # Handle Ctrl+D
                self.running = False
                break
            except Exception as e:
                print(f"{Colors.RED}Input error: {e}{Colors.RESET}")
    
    async def _process_commands(self) -> None:
        """Process user commands from the input queue."""
        while self.running:
            try:
                # Wait for command with timeout
                command = await asyncio.wait_for(self.input_queue.get(), timeout=0.1)
                await self._handle_command(command)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"{Colors.RED}Command processing error: {e}{Colors.RESET}")
    
    async def _handle_command(self, command: str) -> None:
        """Handle individual commands."""
        if command in ['c', 'connect']:
            await self._cmd_connect()
        elif command in ['d', 'disconnect']:
            await self._cmd_disconnect()
        elif command in ['r', 'reconnect']:
            await self._cmd_reconnect()
        elif command in ['1', 'send-update']:
            await self._cmd_send_update()
        elif command in ['2', 'send-log']:
            await self._cmd_send_log()
        elif command in ['3', 'send-custom']:
            await self._cmd_send_custom()
        elif command in ['s', 'stats']:
            await self._cmd_show_stats()
        elif command in ['m', 'metrics']:
            await self._cmd_toggle_metrics()
        elif command in ['e', 'export']:
            await self._cmd_export_metrics()
        elif command in ['t', 'trends']:
            await self._cmd_show_trends()
        elif command in ['h', 'help']:
            await self._cmd_help()
        elif command in ['q', 'quit', 'exit']:
            self.running = False
        else:
            if command:  # Don't show error for empty commands
                print(f"{Colors.RED}Unknown command: {command}. Type 'h' for help.{Colors.RESET}")
    
    async def _cmd_connect(self) -> None:
        """Handle connect command."""
        if self.client.state == self.ConnectionState.CONNECTED:
            print(f"{Colors.YELLOW}Already connected{Colors.RESET}")
            return
        
        success = await self.client.connect()
        
        if success:
            print(f"{Colors.GREEN}Connected successfully{Colors.RESET}")
        else:
            print(f"{Colors.RED}Connection failed{Colors.RESET}")
    
    async def _cmd_disconnect(self) -> None:
        """Handle disconnect command."""
        if self.client.state == self.ConnectionState.DISCONNECTED:
            print(f"{Colors.YELLOW}Already disconnected{Colors.RESET}")
            return
        
        await self.client.disconnect()
        print(f"{Colors.YELLOW}Disconnected{Colors.RESET}")
    
    async def _cmd_reconnect(self) -> None:
        """Handle reconnect test command."""
        print(f"{Colors.YELLOW}Testing reconnect logic...{Colors.RESET}")
        
        # Disconnect first
        await self.client.disconnect()
        await asyncio.sleep(1)
        
        # Reconnect
        success = await self.client.connect()
        
        if success:
            print(f"{Colors.GREEN}Reconnect test successful{Colors.RESET}")
        else:
            print(f"{Colors.RED}Reconnect test failed{Colors.RESET}")
    
    async def _cmd_send_update(self) -> None:
        """Send execution-update message."""
        if self.client.state != self.ConnectionState.CONNECTED:
            print(f"{Colors.RED}Not connected{Colors.RESET}")
            return
        
        payload = {
            "status": "running",
            "progress": 75.5,
            "current_task": "Processing data",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        success = await self.client.send_message(self.MessageType.EXECUTION_UPDATE, payload)
        
        if success:
            # Add to message log
            log_entry = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "type": "execution-update",
                "payload": payload,
                "direction": "sent"
            }
            self.message_log.append(log_entry)
            print(f"{Colors.GREEN}Execution update sent{Colors.RESET}")
        else:
            print(f"{Colors.RED}Failed to send message{Colors.RESET}")
    
    async def _cmd_send_log(self) -> None:
        """Send execution-log message."""
        if self.client.state != self.ConnectionState.CONNECTED:
            print(f"{Colors.RED}Not connected{Colors.RESET}")
            return
        
        payload = {
            "level": "info",
            "message": "CLI demo log message",
            "component": "cli-demo",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        success = await self.client.send_message(self.MessageType.EXECUTION_LOG, payload)
        
        if success:
            # Add to message log
            log_entry = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "type": "execution-log",
                "payload": payload,
                "direction": "sent"
            }
            self.message_log.append(log_entry)
            print(f"{Colors.GREEN}Execution log sent{Colors.RESET}")
        else:
            print(f"{Colors.RED}Failed to send message{Colors.RESET}")
    
    async def _cmd_send_custom(self) -> None:
        """Send custom message."""
        if self.client.state != self.ConnectionState.CONNECTED:
            print(f"{Colors.RED}Not connected{Colors.RESET}")
            return
        
        payload = {
            "custom_field": "demo_value",
            "number": 42,
            "nested": {
                "data": "test",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }
        
        success = await self.client.send_message(self.MessageType.EXECUTION_UPDATE, payload)
        
        if success:
            # Add to message log
            log_entry = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "type": "custom",
                "payload": payload,
                "direction": "sent"
            }
            self.message_log.append(log_entry)
            print(f"{Colors.GREEN}Custom message sent{Colors.RESET}")
        else:
            print(f"{Colors.RED}Failed to send message{Colors.RESET}")
    
    async def _cmd_show_stats(self) -> None:
        """Show detailed statistics and performance metrics."""
        stats = self.client.get_statistics()
        
        print(f"\n{Colors.BOLD}Detailed Statistics:{Colors.RESET}")
        print(f"  Connection State: {self._get_state_color(self.client.state)}{stats['state']}{Colors.RESET}")
        print(f"  Server URL: {Colors.BLUE}{stats['server_url']}{Colors.RESET}")
        print(f"  Project ID: {Colors.BLUE}{stats['project_id']}{Colors.RESET}")
        print(f"  Connection Attempts: {Colors.BLUE}{stats['connection_attempts']}{Colors.RESET}")
        print(f"  Messages Sent: {Colors.BLUE}{stats['messages_sent']}{Colors.RESET}")
        print(f"  Messages Received: {Colors.BLUE}{stats['messages_received']}{Colors.RESET}")
        print(f"  Uptime: {Colors.BLUE}{stats['uptime_seconds']:.2f} seconds{Colors.RESET}")
        
        # Enhanced reconnect statistics
        try:
            reconnect_metrics = self.client.get_reconnect_metrics()
            print(f"\n{Colors.BOLD}Reconnect Statistics:{Colors.RESET}")
            print(f"  Total Attempts: {Colors.BLUE}{reconnect_metrics['reconnect_attempts']}{Colors.RESET}")
            print(f"  Successful: {Colors.GREEN}{reconnect_metrics['successful_reconnects']}{Colors.RESET}")
            print(f"  Failed: {Colors.RED}{reconnect_metrics['failed_reconnects']}{Colors.RESET}")
            print(f"  Success Rate: {Colors.GREEN if reconnect_metrics['success_rate_percent'] > 0 else Colors.RED}{reconnect_metrics['success_rate_percent']:.1f}%{Colors.RESET}")
            if reconnect_metrics['average_reconnect_time_s'] > 0:
                print(f"  Average Time: {Colors.BLUE}{reconnect_metrics['average_reconnect_time_s']:.2f}s{Colors.RESET}")
            
            # Error categories
            if reconnect_metrics['error_categories']:
                print(f"  Error Categories:")
                for error_type, count in reconnect_metrics['error_categories'].items():
                    print(f"    {error_type}: {Colors.RED}{count}{Colors.RESET}")
        except Exception as e:
            print(f"  {Colors.YELLOW}Reconnect data unavailable: {e}{Colors.RESET}")
        
        # Show enhanced performance statistics
        try:
            perf_stats = self.client.get_performance_statistics()
            validation = self.client.validate_performance_targets()
            
            print(f"\n{Colors.BOLD}Performance Statistics:{Colors.RESET}")
            print(f"  Overall Health: {'✓ HEALTHY' if validation['overall_healthy'] else '✗ DEGRADED'}")
            
            # Handshake performance
            handshake = perf_stats["handshake"]
            if handshake["statistics"]["avg"] > 0:
                stats_h = handshake["statistics"]
                print(f"  Handshake: avg={stats_h['avg']:.1f}ms, p95={stats_h['p95']:.1f}ms, violations={handshake['violations']}")
            
            # Latency performance
            latency = perf_stats["message_latency"]
            if latency["statistics"]["avg"] > 0:
                stats_l = latency["statistics"]
                print(f"  Latency: avg={stats_l['avg']:.1f}ms, p95={stats_l['p95']:.1f}ms, violations={latency['violations']}")
            
            # Performance report
            print(f"\n{Colors.BOLD}Performance Report:{Colors.RESET}")
            report = self.client.get_performance_report()
            for line in report.split('\n'):
                if line.strip():
                    print(f"  {line}")
                    
        except Exception as e:
            print(f"  {Colors.YELLOW}Performance data unavailable: {e}{Colors.RESET}")
        
        # Metrics collection status
        if self.metrics_enabled and self.metrics_collector:
            print(f"\n{Colors.BOLD}Metrics Collection:{Colors.RESET}")
            print(f"  Status: {Colors.GREEN}ACTIVE{Colors.RESET}")
            print(f"  Snapshots: {Colors.BLUE}{len(self.metrics_collector.snapshots)}{Colors.RESET}")
            print(f"  Collection Interval: {Colors.BLUE}{self.metrics_collector.collection_interval}s{Colors.RESET}")
            print(f"  Aggregations: {Colors.BLUE}{len(self.metrics_collector.aggregations)}{Colors.RESET}")
        
        print()
    
    async def _cmd_toggle_metrics(self) -> None:
        """Toggle metrics collection on/off."""
        if not self.metrics_enabled:
            # Start metrics collection
            try:
                self.metrics_collector = create_metrics_collector(
                    max_snapshots=1000,
                    collection_interval=2.0  # Collect every 2 seconds
                )
                self.metrics_collector.start_collection(self.client)
                self.metrics_enabled = True
                print(f"{Colors.GREEN}Metrics collection started{Colors.RESET}")
            except Exception as e:
                print(f"{Colors.RED}Failed to start metrics collection: {e}{Colors.RESET}")
        else:
            # Stop metrics collection
            try:
                if self.metrics_collector:
                    await self.metrics_collector.stop_collection()
                self.metrics_enabled = False
                print(f"{Colors.YELLOW}Metrics collection stopped{Colors.RESET}")
            except Exception as e:
                print(f"{Colors.RED}Failed to stop metrics collection: {e}{Colors.RESET}")
    
    async def _cmd_export_metrics(self) -> None:
        """Export metrics to JSON or CSV format."""
        if not self.metrics_enabled or not self.metrics_collector:
            print(f"{Colors.RED}Metrics collection is not active. Use 'm' to start collection first.{Colors.RESET}")
            return
        
        if len(self.metrics_collector.snapshots) == 0:
            print(f"{Colors.YELLOW}No metrics data to export yet.{Colors.RESET}")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # Export to JSON
            json_file = f"websocket_metrics_{timestamp}.json"
            self.metrics_collector.export_to_json(json_file)
            print(f"{Colors.GREEN}Metrics exported to JSON: {json_file}{Colors.RESET}")
            
            # Export to CSV
            csv_file = f"websocket_metrics_{timestamp}.csv"
            self.metrics_collector.export_to_csv(csv_file, "snapshots")
            print(f"{Colors.GREEN}Metrics exported to CSV: {csv_file}{Colors.RESET}")
            
            # Show export summary
            print(f"  Snapshots exported: {Colors.BLUE}{len(self.metrics_collector.snapshots)}{Colors.RESET}")
            print(f"  Aggregations exported: {Colors.BLUE}{len(self.metrics_collector.aggregations)}{Colors.RESET}")
            
        except Exception as e:
            print(f"{Colors.RED}Export failed: {e}{Colors.RESET}")
    
    async def _cmd_show_trends(self) -> None:
        """Show performance trends and analysis."""
        if not self.metrics_enabled or not self.metrics_collector:
            print(f"{Colors.RED}Metrics collection is not active. Use 'm' to start collection first.{Colors.RESET}")
            return
        
        if len(self.metrics_collector.snapshots) < 5:
            print(f"{Colors.YELLOW}Need at least 5 snapshots for trend analysis. Current: {len(self.metrics_collector.snapshots)}{Colors.RESET}")
            return
        
        try:
            print(f"\n{Colors.BOLD}Performance Trends Analysis:{Colors.RESET}")
            
            # Success rate trend
            success_trend = self.metrics_collector.get_trend_analysis("success_rate")
            trend_color = Colors.GREEN if success_trend["trend"] == "increasing" else Colors.RED if success_trend["trend"] == "decreasing" else Colors.BLUE
            print(f"  Success Rate: {trend_color}{success_trend['trend'].upper()}{Colors.RESET} (current: {success_trend['current_value']:.1f}%)")
            
            # Handshake time trend
            handshake_trend = self.metrics_collector.get_trend_analysis("handshake_time")
            trend_color = Colors.RED if handshake_trend["trend"] == "increasing" else Colors.GREEN if handshake_trend["trend"] == "decreasing" else Colors.BLUE
            print(f"  Handshake Time: {trend_color}{handshake_trend['trend'].upper()}{Colors.RESET} (current: {handshake_trend['current_value']:.1f}ms)")
            
            # Message latency trend
            latency_trend = self.metrics_collector.get_trend_analysis("message_latency")
            trend_color = Colors.RED if latency_trend["trend"] == "increasing" else Colors.GREEN if latency_trend["trend"] == "decreasing" else Colors.BLUE
            print(f"  Message Latency: {trend_color}{latency_trend['trend'].upper()}{Colors.RESET} (current: {latency_trend['current_value']:.1f}ms)")
            
            # Reconnect time trend
            reconnect_trend = self.metrics_collector.get_trend_analysis("reconnect_time")
            trend_color = Colors.RED if reconnect_trend["trend"] == "increasing" else Colors.GREEN if reconnect_trend["trend"] == "decreasing" else Colors.BLUE
            print(f"  Reconnect Time: {trend_color}{reconnect_trend['trend'].upper()}{Colors.RESET} (current: {reconnect_trend['current_value']:.2f}s)")
            
            # Dashboard data
            dashboard = self.metrics_collector.get_dashboard_data()
            if dashboard["status"] == "active":
                print(f"\n{Colors.BOLD}Real-time Dashboard:{Colors.RESET}")
                print(f"  Connection State: {self._get_state_color(self.client.state)}{dashboard['connection_state']}{Colors.RESET}")
                print(f"  Total Snapshots: {Colors.BLUE}{dashboard['collection_info']['total_snapshots']}{Colors.RESET}")
                print(f"  Collection Active: {Colors.GREEN if dashboard['collection_info']['collecting'] else Colors.RED}{dashboard['collection_info']['collecting']}{Colors.RESET}")
                
                # Performance health
                perf = dashboard["performance_summary"]
                handshake_status = f"{Colors.GREEN}HEALTHY{Colors.RESET}" if perf["handshake_healthy"] else f"{Colors.RED}DEGRADED{Colors.RESET}"
                latency_status = f"{Colors.GREEN}HEALTHY{Colors.RESET}" if perf["latency_healthy"] else f"{Colors.RED}DEGRADED{Colors.RESET}"
                print(f"  Handshake Health: {handshake_status} ({perf['handshake_last_ms']:.1f}ms)")
                print(f"  Latency Health: {latency_status} ({perf['latency_last_ms']:.1f}ms)")
            
        except Exception as e:
            print(f"{Colors.RED}Trend analysis failed: {e}{Colors.RESET}")
        
        print()
    
    async def _cmd_help(self) -> None:
        """Show help information."""
        print(f"\n{Colors.BOLD}WebSocket Demo CLI Help:{Colors.RESET}")
        print(f"This interactive CLI demonstrates WebSocket connectivity to the Clarity Local Runner.")
        print(f"")
        print(f"{Colors.BOLD}Performance Targets:{Colors.RESET}")
        print(f"  • Handshake Time: ≤300ms")
        print(f"  • Message Latency: ≤500ms")
        print(f"")
        print(f"{Colors.BOLD}Connection States:{Colors.RESET}")
        print(f"  • {Colors.GREEN}CONNECTED{Colors.RESET} - Active WebSocket connection")
        print(f"  • {Colors.YELLOW}CONNECTING{Colors.RESET} - Establishing connection")
        print(f"  • {Colors.YELLOW}RECONNECTING{Colors.RESET} - Attempting to reconnect")
        print(f"  • {Colors.RED}DISCONNECTED{Colors.RESET} - No connection")
        print(f"")
        print(f"{Colors.BOLD}Message Types:{Colors.RESET}")
        print(f"  • {Colors.MSG_UPDATE}execution-update{Colors.RESET} - Status and progress updates")
        print(f"  • {Colors.MSG_LOG}execution-log{Colors.RESET} - Log messages")
        print(f"  • {Colors.MSG_ERROR}error{Colors.RESET} - Error messages")
        print(f"  • {Colors.MSG_COMPLETION}completion{Colors.RESET} - Task completion")
        print(f"")
        print(f"{Colors.BOLD}Metrics Commands:{Colors.RESET}")
        print(f"  • {Colors.CYAN}m{Colors.RESET} - Toggle metrics collection on/off")
        print(f"  • {Colors.CYAN}e{Colors.RESET} - Export metrics to JSON and CSV files")
        print(f"  • {Colors.CYAN}t{Colors.RESET} - Show performance trends and analysis")
        print(f"")
        print(f"Press any key to continue...")
        await asyncio.sleep(2)
    
    async def run(self) -> None:
        """Run the interactive CLI demo."""
        print(f"{Colors.BOLD}{Colors.GREEN}Starting WebSocket Demo CLI...{Colors.RESET}")
        print(f"Server: {Colors.BLUE}{self.config.server_url}/api/v1/ws/devteam{Colors.RESET}")
        print(f"Project ID: {Colors.BLUE}{self.config.project_id}{Colors.RESET}")
        print(f"Press {Colors.CYAN}Ctrl+C{Colors.RESET} to exit gracefully")
        print()
        
        try:
            # Start all concurrent tasks
            tasks = [
                asyncio.create_task(self._display_loop()),
                asyncio.create_task(self._input_loop()),
                asyncio.create_task(self._process_commands())
            ]
            
            # Start client if needed
            if self.client.state == self.ConnectionState.DISCONNECTED:
                self.client_task = asyncio.create_task(self.client.run())
                tasks.append(self.client_task)
            
            # Wait for any task to complete (usually means shutdown)
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Interrupted by user{Colors.RESET}")
        
        finally:
            await self._cleanup()
    
    async def _cleanup(self) -> None:
        """Cleanup resources and disconnect."""
        print(f"{Colors.YELLOW}Cleaning up...{Colors.RESET}")
        
        # Stop metrics collection
        if self.metrics_enabled and self.metrics_collector:
            try:
                await self.metrics_collector.stop_collection()
            except Exception as e:
                print(f"{Colors.RED}Error stopping metrics collection: {e}{Colors.RESET}")
        
        # Stop client
        if self.client:
            await self.client.stop()
        
        # Cancel display task
        if self.display_task and not self.display_task.done():
            self.display_task.cancel()
            try:
                await self.display_task
            except asyncio.CancelledError:
                pass
        
        # Cancel client task
        if self.client_task and not self.client_task.done():
            self.client_task.cancel()
            try:
                await self.client_task
            except asyncio.CancelledError:
                pass
        
        print(f"{Colors.GREEN}Cleanup complete. Goodbye!{Colors.RESET}")


async def main():
    """Main entry point for the CLI demo."""
    try:
        demo = CLIDemo()
        await demo.run()
    except Exception as e:
        print(f"{Colors.RED}Fatal error: {e}{Colors.RESET}")
        sys.exit(1)


if __name__ == "__main__":
    # Ensure we're running in an asyncio event loop
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Interrupted{Colors.RESET}")
        sys.exit(0)
            print(f"  Aggregations: {Colors.BLUE}{len(self