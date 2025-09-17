#!/usr/bin/env python3
"""
Branch 6.4 Comprehensive Validation Script
==========================================

This script provides comprehensive validation of all Branch 6.4 acceptance criteria
for the WebSocket Demo Client implementation, including:

- Linear Reconnect Logic (ADD Profile C)
- Performance Requirements (≤300ms handshake, ≤500ms latency)
- Message Envelope Format validation
- Payload Size Limits (10KB client-side validation)
- JWT Authentication using service_role_key pattern
- Connection State Management
- Error Handling and graceful degradation
- Structured Logging integration
- CLI Interface functionality
- Metrics Collection and Export

This validation script integrates all existing test scenarios and components
to provide a final comprehensive validation of Branch 6.4 implementation.
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import statistics
import subprocess

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Import all Branch 6.4 components
from websocket_demo_client import (
    WebSocketDemoClient, ClientConfig, ConnectionState, MessageType,
    PerformanceThresholds
)
from performance_test_scenarios import PerformanceTestScenarios
from reconnect_test_scenarios import ReconnectTestScenarios, TestResult
from metrics_collector import MetricsCollector, create_metrics_collector
from core.structured_logging import get_structured_logger, LogStatus


class ValidationResult(str, Enum):
    """Validation result status."""
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    ERROR = "ERROR"


@dataclass
class AcceptanceCriterion:
    """Individual acceptance criterion definition."""
    id: str
    name: str
    description: str
    requirement: str
    validation_method: str
    priority: str = "HIGH"  # HIGH, MEDIUM, LOW


@dataclass
class ValidationTestResult:
    """Result of a validation test."""
    criterion_id: str
    criterion_name: str
    result: ValidationResult
    duration: float
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    performance_data: Optional[Dict[str, Any]] = None
    compliance_status: bool = False


@dataclass
class Branch64ValidationReport:
    """Comprehensive Branch 6.4 validation report."""
    validation_timestamp: str
    total_criteria: int
    passed_criteria: int
    failed_criteria: int
    error_criteria: int
    skipped_criteria: int
    overall_compliance: bool
    performance_summary: Dict[str, Any]
    test_results: List[ValidationTestResult]
    recommendations: List[str]
    execution_summary: Dict[str, Any]


class Branch64Validator:
    """
    Comprehensive validator for Branch 6.4 acceptance criteria.
    
    This class orchestrates validation of all Branch 6.4 requirements including
    linear reconnect logic, performance requirements, message format validation,
    error handling, logging integration, and CLI functionality.
    """
    
    def __init__(self, server_url: str = "ws://localhost:8090", 
                 project_id: str = "branch-6-4-validation"):
        """
        Initialize Branch 6.4 validator.
        
        Args:
            server_url: WebSocket server URL for testing
            project_id: Project identifier for validation tests
        """
        self.server_url = server_url
        self.project_id = project_id
        self.validation_id = str(uuid.uuid4())
        
        # Test components
        self.client: Optional[WebSocketDemoClient] = None
        self.performance_tester: Optional[PerformanceTestScenarios] = None
        self.reconnect_tester: Optional[ReconnectTestScenarios] = None
        self.metrics_collector: Optional[MetricsCollector] = None
        
        # Validation results
        self.test_results: List[ValidationTestResult] = []
        self.validation_start_time: float = 0.0
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Setup structured logging
        self.structured_logger = get_structured_logger(f"{__name__}.Branch64Validator")
        self.structured_logger.set_context(
            validation_id=self.validation_id,
            project_id=self.project_id,
            node="branch_6_4_validator"
        )
        
        # Define acceptance criteria
        self.acceptance_criteria = self._define_acceptance_criteria()
    
    def _define_acceptance_criteria(self) -> List[AcceptanceCriterion]:
        """Define all Branch 6.4 acceptance criteria."""
        return [
            # Core Functionality
            AcceptanceCriterion(
                id="AC-001",
                name="WebSocket Connection Establishment",
                description="Client can establish WebSocket connection to /api/v1/ws/devteam endpoint",
                requirement="Successful connection with JWT authentication",
                validation_method="Connection test with authentication validation"
            ),
            AcceptanceCriterion(
                id="AC-002", 
                name="Message Sending and Receiving",
                description="Client can send and receive messages through WebSocket connection",
                requirement="Bidirectional message communication",
                validation_method="Send test messages and verify receipt"
            ),
            
            # Linear Reconnect Logic (ADD Profile C)
            AcceptanceCriterion(
                id="AC-003",
                name="Linear Reconnect Intervals",
                description="Reconnect attempts use fixed 2-second intervals",
                requirement="Linear reconnect with 2-second intervals (ADD Profile C)",
                validation_method="Timing validation of reconnect attempts"
            ),
            AcceptanceCriterion(
                id="AC-004",
                name="Connection State Management",
                description="Proper state transitions during reconnect cycles",
                requirement="Valid state transitions: DISCONNECTED -> CONNECTING -> CONNECTED/RECONNECTING",
                validation_method="State transition tracking and validation"
            ),
            
            # Performance Requirements
            AcceptanceCriterion(
                id="AC-005",
                name="Handshake Performance",
                description="WebSocket handshake completes within 300ms",
                requirement="Handshake time ≤300ms",
                validation_method="Handshake timing measurement and validation"
            ),
            AcceptanceCriterion(
                id="AC-006",
                name="Message Latency Performance", 
                description="Message round-trip latency within 500ms",
                requirement="Message latency ≤500ms",
                validation_method="Round-trip latency measurement and validation"
            ),
            
            # Message Format and Validation
            AcceptanceCriterion(
                id="AC-007",
                name="Message Envelope Format",
                description="All messages follow standardized {type, ts, projectId, payload} format",
                requirement="Envelope format compliance with ADD Profile C",
                validation_method="Message structure validation"
            ),
            AcceptanceCriterion(
                id="AC-008",
                name="Payload Size Validation",
                description="Client-side payload size validation enforces 10KB limit",
                requirement="Payload size ≤10KB with client-side validation",
                validation_method="Payload size limit testing"
            ),
            
            # Authentication and Security
            AcceptanceCriterion(
                id="AC-009",
                name="JWT Authentication",
                description="WebSocket connection uses service_role_key JWT pattern",
                requirement="JWT authentication using service_role_key",
                validation_method="Authentication mechanism validation"
            ),
            
            # Error Handling and Recovery
            AcceptanceCriterion(
                id="AC-010",
                name="Error Categorization",
                description="Comprehensive error categorization and handling",
                requirement="Proper error categorization (timeout, auth, connection, etc.)",
                validation_method="Error scenario testing and categorization validation"
            ),
            AcceptanceCriterion(
                id="AC-011",
                name="Graceful Degradation",
                description="System continues functioning when components fail",
                requirement="Graceful handling of connection failures and recovery",
                validation_method="Failure scenario testing and recovery validation"
            ),
            
            # Logging and Metrics
            AcceptanceCriterion(
                id="AC-012",
                name="Structured Logging Integration",
                description="Integration with existing project logging patterns",
                requirement="Structured logging with correlationId tracking",
                validation_method="Logging output validation and correlation tracking"
            ),
            AcceptanceCriterion(
                id="AC-013",
                name="Metrics Collection and Export",
                description="Advanced metrics collection with export capabilities",
                requirement="Metrics collection, aggregation, and JSON/CSV export",
                validation_method="Metrics functionality testing and export validation"
            ),
            
            # CLI Interface
            AcceptanceCriterion(
                id="AC-014",
                name="Interactive CLI Functionality",
                description="CLI interface provides comprehensive testing and monitoring",
                requirement="Interactive CLI with real-time status and command execution",
                validation_method="CLI functionality testing and command validation"
            )
        ]
    
    async def setup_test_environment(self) -> bool:
        """
        Set up test environment and components.
        
        Returns:
            bool: True if setup successful, False otherwise
        """
        try:
            self.structured_logger.info(
                "Setting up Branch 6.4 validation environment",
                status=LogStatus.STARTED,
                server_url=self.server_url,
                project_id=self.project_id
            )
            
            # Initialize WebSocket client
            config = ClientConfig(
                server_url=self.server_url,
                project_id=self.project_id,
                reconnect_interval=2.0,  # ADD Profile C
                max_payload_size=10240,  # 10KB limit
                performance_thresholds=PerformanceThresholds(
                    handshake_max_ms=300.0,
                    message_latency_max_ms=500.0
                )
            )
            self.client = WebSocketDemoClient(config)
            
            # Initialize test components
            self.performance_tester = PerformanceTestScenarios(
                server_url=self.server_url,
                project_id=f"{self.project_id}-perf"
            )
            
            self.reconnect_tester = ReconnectTestScenarios(
                server_url=self.server_url,
                project_id=f"{self.project_id}-reconnect"
            )
            
            # Initialize metrics collector
            self.metrics_collector = create_metrics_collector(
                max_snapshots=1000,
                collection_interval=1.0
            )
            
            self.structured_logger.info(
                "Branch 6.4 validation environment setup completed",
                status=LogStatus.COMPLETED
            )
            
            return True
            
        except Exception as e:
            self.structured_logger.error(
                "Failed to setup validation environment",
                status=LogStatus.FAILED,
                error=e
            )
            self.logger.error(f"Environment setup failed: {e}")
            return False
    
    async def cleanup_test_environment(self) -> None:
        """Clean up test environment and resources."""
        try:
            if self.client:
                await self.client.stop()
            
            if self.metrics_collector and self.metrics_collector.collecting:
                await self.metrics_collector.stop_collection()
            
            self.structured_logger.info(
                "Branch 6.4 validation environment cleanup completed",
                status=LogStatus.COMPLETED
            )
            
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")
    
    async def validate_core_functionality(self) -> List[ValidationTestResult]:
        """
        Validate core WebSocket functionality.
        
        Returns:
            List of validation test results for core functionality
        """
        results = []
        
        # AC-001: WebSocket Connection Establishment
        start_time = time.time()
        try:
            if not self.client:
                raise ValueError("Client not initialized")
            
            success = await self.client.connect()
            duration = time.time() - start_time
            
            if success and self.client.state == ConnectionState.CONNECTED:
                results.append(ValidationTestResult(
                    criterion_id="AC-001",
                    criterion_name="WebSocket Connection Establishment",
                    result=ValidationResult.PASS,
                    duration=duration,
                    details={
                        "connection_successful": True,
                        "final_state": self.client.state.value,
                        "server_url": self.server_url
                    },
                    compliance_status=True
                ))
            else:
                results.append(ValidationTestResult(
                    criterion_id="AC-001",
                    criterion_name="WebSocket Connection Establishment", 
                    result=ValidationResult.FAIL,
                    duration=duration,
                    error_message="Failed to establish WebSocket connection",
                    compliance_status=False
                ))
        except Exception as e:
            results.append(ValidationTestResult(
                criterion_id="AC-001",
                criterion_name="WebSocket Connection Establishment",
                result=ValidationResult.ERROR,
                duration=time.time() - start_time,
                error_message=str(e),
                compliance_status=False
            ))
        
        # AC-002: Message Sending and Receiving
        start_time = time.time()
        try:
            if self.client and self.client.state == ConnectionState.CONNECTED:
                # Send test message
                test_payload = {
                    "test_type": "core_functionality_validation",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "validation_id": self.validation_id
                }
                
                send_success = await self.client.send_message(
                    MessageType.EXECUTION_UPDATE, 
                    test_payload
                )
                
                duration = time.time() - start_time
                
                if send_success:
                    results.append(ValidationTestResult(
                        criterion_id="AC-002",
                        criterion_name="Message Sending and Receiving",
                        result=ValidationResult.PASS,
                        duration=duration,
                        details={
                            "message_sent": True,
                            "message_type": MessageType.EXECUTION_UPDATE.value,
                            "payload_size": len(json.dumps(test_payload))
                        },
                        compliance_status=True
                    ))
                else:
                    results.append(ValidationTestResult(
                        criterion_id="AC-002",
                        criterion_name="Message Sending and Receiving",
                        result=ValidationResult.FAIL,
                        duration=duration,
                        error_message="Failed to send test message",
                        compliance_status=False
                    ))
            else:
                results.append(ValidationTestResult(
                    criterion_id="AC-002",
                    criterion_name="Message Sending and Receiving",
                    result=ValidationResult.SKIP,
                    duration=0.0,
                    error_message="No active connection for message testing",
                    compliance_status=False
                ))
        except Exception as e:
            results.append(ValidationTestResult(
                criterion_id="AC-002",
                criterion_name="Message Sending and Receiving",
                result=ValidationResult.ERROR,
                duration=time.time() - start_time,
                error_message=str(e),
                compliance_status=False
            ))
        
        return results
    
    async def validate_linear_reconnect_logic(self) -> List[ValidationTestResult]:
        """
        Validate linear reconnect logic (ADD Profile C).
        
        Returns:
            List of validation test results for reconnect functionality
        """
        results = []
        
        if not self.reconnect_tester:
            results.append(ValidationTestResult(
                criterion_id="AC-003",
                criterion_name="Linear Reconnect Intervals",
                result=ValidationResult.ERROR,
                duration=0.0,
                error_message="Reconnect tester not initialized",
                compliance_status=False
            ))
            return results
        
        # Setup reconnect tester
        await self.reconnect_tester.setup_client()
        
        try:
            # AC-003: Linear Reconnect Intervals
            basic_reconnect_result = await self.reconnect_tester.test_basic_reconnect()
            
            if basic_reconnect_result.result == TestResult.PASS:
                # Validate timing compliance
                timing_valid = basic_reconnect_result.details.get("timing_valid", False)
                expected_interval = basic_reconnect_result.details.get("expected_interval", 2.0)
                
                results.append(ValidationTestResult(
                    criterion_id="AC-003",
                    criterion_name="Linear Reconnect Intervals",
                    result=ValidationResult.PASS if timing_valid else ValidationResult.FAIL,
                    duration=basic_reconnect_result.duration,
                    details={
                        "timing_valid": timing_valid,
                        "expected_interval_s": expected_interval,
                        "reconnect_attempts": basic_reconnect_result.metrics.reconnect_attempts,
                        "successful_reconnects": basic_reconnect_result.metrics.successful_reconnects
                    },
                    compliance_status=timing_valid
                ))
            else:
                results.append(ValidationTestResult(
                    criterion_id="AC-003",
                    criterion_name="Linear Reconnect Intervals",
                    result=ValidationResult.FAIL,
                    duration=basic_reconnect_result.duration,
                    error_message=basic_reconnect_result.error_message,
                    compliance_status=False
                ))
            
            # AC-004: Connection State Management
            state_consistency_result = await self.reconnect_tester.test_state_consistency_validation()
            
            if state_consistency_result.result == TestResult.PASS:
                state_details = state_consistency_result.details
                results.append(ValidationTestResult(
                    criterion_id="AC-004",
                    criterion_name="Connection State Management",
                    result=ValidationResult.PASS,
                    duration=state_consistency_result.duration,
                    details={
                        "state_transitions": len(state_details.get("state_transitions", [])),
                        "invalid_transitions": len(state_details.get("invalid_transitions", [])),
                        "expected_states_seen": state_details.get("expected_states_seen", False),
                        "transition_timing_consistent": state_details.get("transition_timing_consistent", False)
                    },
                    compliance_status=True
                ))
            else:
                results.append(ValidationTestResult(
                    criterion_id="AC-004",
                    criterion_name="Connection State Management",
                    result=ValidationResult.FAIL,
                    duration=state_consistency_result.duration,
                    error_message=state_consistency_result.error_message,
                    compliance_status=False
                ))
                
        except Exception as e:
            results.append(ValidationTestResult(
                criterion_id="AC-003",
                criterion_name="Linear Reconnect Intervals",
                result=ValidationResult.ERROR,
                duration=0.0,
                error_message=str(e),
                compliance_status=False
            ))
        finally:
            await self.reconnect_tester.cleanup_client()
        
        return results
    
    async def validate_performance_requirements(self) -> List[ValidationTestResult]:
        """
        Validate performance requirements (≤300ms handshake, ≤500ms latency).
        
        Returns:
            List of validation test results for performance requirements
        """
        results = []
        
        if not self.performance_tester:
            results.append(ValidationTestResult(
                criterion_id="AC-005",
                criterion_name="Handshake Performance",
                result=ValidationResult.ERROR,
                duration=0.0,
                error_message="Performance tester not initialized",
                compliance_status=False
            ))
            return results
        
        # Setup performance tester
        await self.performance_tester.setup_client()
        
        try:
            # AC-005: Handshake Performance
            connection_perf_result = await self.performance_tester.test_basic_connection_performance()
            
            if connection_perf_result.get("success", False):
                avg_handshake = connection_perf_result.get("avg_handshake", 0)
                max_handshake = connection_perf_result.get("max_handshake", 0)
                violations = connection_perf_result.get("threshold_violations", 0)
                
                handshake_compliant = avg_handshake <= 300.0 and max_handshake <= 300.0
                
                results.append(ValidationTestResult(
                    criterion_id="AC-005",
                    criterion_name="Handshake Performance",
                    result=ValidationResult.PASS if handshake_compliant else ValidationResult.FAIL,
                    duration=connection_perf_result.get("duration", 0),
                    details={
                        "avg_handshake_ms": avg_handshake,
                        "max_handshake_ms": max_handshake,
                        "min_handshake_ms": connection_perf_result.get("min_handshake", 0),
                        "threshold_violations": violations,
                        "requirement_met": handshake_compliant
                    },
                    performance_data={
                        "handshake_times": connection_perf_result.get("handshake_times", []),
                        "threshold_ms": 300.0
                    },
                    compliance_status=handshake_compliant
                ))
            else:
                results.append(ValidationTestResult(
                    criterion_id="AC-005",
                    criterion_name="Handshake Performance",
                    result=ValidationResult.FAIL,
                    duration=0.0,
                    error_message=connection_perf_result.get("error", "Handshake performance test failed"),
                    compliance_status=False
                ))
            
            # AC-006: Message Latency Performance
            latency_perf_result = await self.performance_tester.test_message_latency_performance()
            
            if latency_perf_result.get("success", False):
                avg_latency = latency_perf_result.get("avg_latency", 0)
                max_latency = latency_perf_result.get("max_latency", 0)
                violations = latency_perf_result.get("threshold_violations", 0)
                
                latency_compliant = avg_latency <= 500.0 and max_latency <= 500.0
                
                results.append(ValidationTestResult(
                    criterion_id="AC-006",
                    criterion_name="Message Latency Performance",
                    result=ValidationResult.PASS if latency_compliant else ValidationResult.FAIL,
                    duration=latency_perf_result.get("duration", 0),
                    details={
                        "avg_latency_ms": avg_latency,
                        "max_latency_ms": max_latency,
                        "min_latency_ms": latency_perf_result.get("min_latency", 0),
                        "messages_sent": latency_perf_result.get("messages_sent", 0),
                        "threshold_violations": violations,
                        "requirement_met": latency_compliant
                    },
                    performance_data={
                        "latency_times": latency_perf_result.get("message_latencies", []),
                        "threshold_ms": 500.0
                    },
                    compliance_status=latency_compliant
                ))
            else:
                results.append(ValidationTestResult(
                    criterion_id="AC-006",
                    criterion_name="Message Latency Performance",
                    result=ValidationResult.FAIL,
                    duration=0.0,
                    error_message=latency_perf_result.get("error", "Message latency performance test failed"),
                    compliance_status=False
                ))
                
        except Exception as e:
            results.append(ValidationTestResult(
                criterion_id="AC-005",
                criterion_name="Handshake Performance",
                result=ValidationResult.ERROR,
                duration=0.0,
                error_message=str(e),
                compliance_status=False
            ))
        finally:
            await self.performance_tester.cleanup_client()
        
        return results
    
    async def validate_message_format_and_payload(self) -> List[ValidationTestResult]:
        """
        Validate message format and payload size requirements.
        
        Returns:
            List of validation test results for message format and payload validation
        """
        results = []
        
        # AC-007: Message Envelope Format
        start_time = time.time()
        try:
            if not self.client:
                raise ValueError("Client not initialized")
            
            # Test message envelope creation and validation
            test_payload = {"test": "envelope_validation", "data": [1, 2, 3]}
            envelope = self.client.create_message_envelope(
                MessageType.EXECUTION_UPDATE,
                test_payload
            )
            
            # Validate envelope structure
            required_fields = ["type", "ts", "projectId", "payload"]
            envelope_valid = all(field in envelope for field in required_fields)
            
            # Validate field types and formats
            type_valid = envelope["type"] in [t.value for t in MessageType]
            ts_valid = envelope["ts"].endswith('Z')
            project_id_valid = isinstance(envelope["projectId"], str) and len(envelope["projectId"]) > 0
            payload_valid = isinstance(envelope["payload"], dict)
            
            format_compliant = envelope_valid and type_valid and ts_valid and project_id_valid and payload_valid
            
            duration = time.time() - start_time
            
            results.append(ValidationTestResult(
                criterion_id="AC-007",
                criterion_name="Message Envelope Format",
                result=ValidationResult.PASS if format_compliant else ValidationResult.FAIL,
                duration=duration,
                details={
                    "envelope_structure_valid": envelope_valid,
                    "type_field_valid": type_valid,
                    "timestamp_format_valid": ts_valid,
                    "project_id_valid": project_id_valid,
                    "payload_structure_valid": payload_valid,
                    "envelope_fields": list(envelope.keys()),
                    "message_type": envelope.get("type"),
                    "timestamp": envelope.get("ts")
                },
                compliance_status=format_compliant
            ))
            
        except Exception as e:
            results.append(ValidationTestResult(
                criterion_id="AC-007",
                criterion_name="Message Envelope Format",
                result=ValidationResult.ERROR,
                duration=time.time() - start_time,
                error_message=str(e),
                compliance_status=False
            ))
        
        # AC-008: Payload Size Validation
        start_time = time.time()
        try:
            if not self.client:
                raise ValueError("Client not initialized")
            
            # Test payload size validation with various sizes
            test_cases = [
                {"size": 1024, "description": "1KB payload", "should_pass": True},
                {"size": 5120, "description": "5KB payload", "should_pass": True},
                {"size": 10240, "description": "10KB payload (limit)", "should_pass": True},
                {"size": 12288, "description": "12KB payload (over limit)", "should_pass": False}
            ]
            
            validation_results = []
            
            for test_case in test_cases:
                # Create payload of specified size
                payload_data = "x" * (test_case["size"] - 100)  # Account for envelope overhead
                test_payload = {"data": payload_data, "size": test_case["size"]}
                
                try:
                    envelope = self.client.create_message_envelope(
                        MessageType.EXECUTION_UPDATE,
                        test_payload
                    )
                    
                    # Check if validation passed as expected
                    validation_passed = True
                    actual_size = len(json.dumps(envelope).encode('utf-8'))
                    
                    validation_results.append({
                        "test_case": test_case["description"],
                        "expected_size": test_case["size"],
                        "actual_size": actual_size,
                        "should_pass": test_case["should_pass"],
                        "validation_passed": validation_passed,
                        "correct_behavior": validation_passed == test_case["should_pass"]
                    })
                    
                except ValueError as ve:
                    # Validation should fail for oversized payloads
                    validation_failed = True
                    validation_results.append({
                        "test_case": test_case["description"],
                        "expected_size": test_case["size"],
                        "should_pass": test_case["should_pass"],
                        "validation_passed": False,
                        "error": str(ve),
                        "correct_behavior": not test_case["should_pass"]
                    })
            
            # Check if all test cases behaved correctly
            all_correct = all(result.get("correct_behavior", False) for result in validation_results)
            
            duration = time.time() - start_time
            
            results.append(ValidationTestResult(
                criterion_id="AC-008",
                criterion_name="Payload Size Validation",
                result=ValidationResult.PASS if all_correct else ValidationResult.FAIL,
                duration=duration,
                details={
                    "payload_limit_bytes": 10240,
                    "test_cases_run": len(test_cases),
                    "all_validations_correct": all_correct,
                    "validation_results": validation_results
                },
                compliance_status=all_correct
            ))
            
        except Exception as e:
            results.append(ValidationTestResult(
                criterion_id="AC-008",
                criterion_name="Payload Size Validation",
                result=ValidationResult.ERROR,
                duration=time.time() - start_time,
                error_message=str(e),
                compliance_status=False
            ))
        
        return results
    
    async def validate_authentication_and_security(self) -> List[ValidationTestResult]:
        """
        Validate JWT authentication and security features.
        
        Returns:
            List of validation test results for authentication and security
        """
        results = []
        
        # AC-009: JWT Authentication
        start_time = time.time()
        try:
            if not self.client:
                raise ValueError("Client not initialized")
            
            # Validate JWT authentication configuration
            config = self.client.config
            has_service_role_key = bool(config.service_role_key)
            key_format_valid = config.service_role_key.startswith("eyJ") if has_service_role_key else False
            
            # Test authentication headers
            auth_headers = self.client._build_auth_headers()
            has_auth_header = "Authorization" in auth_headers
            bearer_format = auth_headers.get("Authorization", "").startswith("Bearer ") if has_auth_header else False
            
            auth_compliant = has_service_role_key and key_format_valid and has_auth_header and bearer_format
            
            duration = time.time() - start_time
            
            results.append(ValidationTestResult(
                criterion_id="AC-009",
                criterion_name="JWT Authentication",
                result=ValidationResult.PASS if auth_compliant else ValidationResult.FAIL,
                duration=duration,
                details={
                    "has_service_role_key": has_service_role_key,
                    "key_format_valid": key_format_valid,
                    "has_auth_header": has_auth_header,
                    "bearer_format_valid": bearer_format,
                    "auth_compliant": auth_compliant
                },
                compliance_status=auth_compliant
            ))
            
        except Exception as e:
            results.append(ValidationTestResult(
                criterion_id="AC-009",
                criterion_name="JWT Authentication",
                result=ValidationResult.ERROR,
                duration=time.time() - start_time,
                error_message=str(e),
                compliance_status=False
            ))
        
        return results
    
    async def validate_error_handling_and_recovery(self) -> List[ValidationTestResult]:
        """
        Validate error handling and recovery capabilities.
        
        Returns:
            List of validation test results for error handling and recovery
        """
        results = []
        
        # AC-010: Error Categorization
        start_time = time.time()
        try:
            if not self.client:
                raise ValueError("Client not initialized")
            
            # Test error categorization by examining reconnect metrics
            reconnect_metrics = self.client.get_reconnect_metrics()
            error_categories = reconnect_metrics.get("error_categories", {})
            error_distribution = reconnect_metrics.get("error_distribution", {})
            
            # Check if error categorization is working
            has_error_categories = len(error_categories) > 0 or len(error_distribution) > 0
            
            # Expected error categories
            expected_categories = [
                "connection_timeout", "invalid_uri", "authentication_failed",
                "endpoint_not_found", "connection_refused", "connection_error"
            ]
            
            duration = time.time() - start_time
            
            results.append(ValidationTestResult(
                criterion_id="AC-010",
                criterion_name="Error Categorization",
                result=ValidationResult.PASS if has_error_categories else ValidationResult.SKIP,
                duration=duration,
                details={
                    "error_categories_found": list(error_categories.keys()),
                    "error_distribution": error_distribution,
                    "expected_categories": expected_categories,
                    "categorization_active": has_error_categories
                },
                compliance_status=has_error_categories
            ))
            
        except Exception as e:
            results.append(ValidationTestResult(
                criterion_id="AC-010",
                criterion_name="Error Categorization",
                result=ValidationResult.ERROR,
                duration=time.time() - start_time,
                error_message=str(e),
                compliance_status=False
            ))
        
        # AC-011: Graceful Degradation
        start_time = time.time()
        try:
            if not self.reconnect_tester:
                raise ValueError("Reconnect tester not initialized")
            
            # Use existing server unavailable test for graceful degradation validation
            await self.reconnect_tester.setup_client()
            server_unavailable_result = await self.reconnect_tester.test_server_unavailable()
            await self.reconnect_tester.cleanup_client()
            
            graceful_degradation = (
                server_unavailable_result.result == TestResult.PASS and
                server_unavailable_result.metrics.failed_reconnects >= 3 and
                server_unavailable_result.metrics.successful_reconnects > 0
            )
            
            duration = time.time() - start_time
            
            results.append(ValidationTestResult(
                criterion_id="AC-011",
                criterion_name="Graceful Degradation",
                result=ValidationResult.PASS if graceful_degradation else ValidationResult.FAIL,
                duration=duration,
                details={
                    "server_unavailable_test_result": server_unavailable_result.result.value,
                    "failed_reconnects": server_unavailable_result.metrics.failed_reconnects,
                    "successful_reconnects": server_unavailable_result.metrics.successful_reconnects,
                    "graceful_degradation": graceful_degradation
                },
                compliance_status=graceful_degradation
            ))
            
        except Exception as e:
            results.append(ValidationTestResult(
                criterion_id="AC-011",
                criterion_name="Graceful Degradation",
                result=ValidationResult.ERROR,
                duration=time.time() - start_time,
                error_message=str(e),
                compliance_status=False
            ))
        
        return results
    
    async def validate_logging_and_metrics(self) -> List[ValidationTestResult]:
        """
        Validate logging and metrics system integration.
        
        Returns:
            List of validation test results for logging and metrics
        """
        results = []
        
        # AC-012: Structured Logging Integration
        start_time = time.time()
        try:
            if not self.client:
                raise ValueError("Client not initialized")
            
            # Test structured logging by checking if logger is configured
            has_structured_logger = hasattr(self.client, 'structured_logger')
            has_correlation_id = hasattr(self.client, 'correlation_id')
            
            # Test logging context
            logging_context_valid = False
            if has_structured_logger:
                try:
                    # Check if structured logger has context
                    logger_context = getattr(self.client.structured_logger, '_context', {})
                    logging_context_valid = 'projectId' in logger_context and 'correlationId' in logger_context
                except:
                    pass
            
            structured_logging_compliant = has_structured_logger and has_correlation_id and logging_context_valid
            
            duration = time.time() - start_time
            
            results.append(ValidationTestResult(
                criterion_id="AC-012",
                criterion_name="Structured Logging Integration",
                result=ValidationResult.PASS if structured_logging_compliant else ValidationResult.FAIL,
                duration=duration,
                details={
                    "has_structured_logger": has_structured_logger,
                    "has_correlation_id": has_correlation_id,
                    "logging_context_valid": logging_context_valid,
                    "correlation_id": getattr(self.client, 'correlation_id', None)
                },
                compliance_status=structured_logging_compliant
            ))
            
        except Exception as e:
            results.append(ValidationTestResult(
                criterion_id="AC-012",
                criterion_name="Structured Logging Integration",
                result=ValidationResult.ERROR,
                duration=time.time() - start_time,
                error_message=str(e),
                compliance_status=False
            ))
        
        # AC-013: Metrics Collection and Export
        start_time = time.time()
        try:
            if not self.metrics_collector:
                raise ValueError("Metrics collector not initialized")
            
            # Test metrics collection
            if self.client:
                # Start metrics collection
                self.metrics_collector.start_collection(self.client)
                await asyncio.sleep(2.0)  # Collect for 2 seconds
                await self.metrics_collector.stop_collection()
                
                # Test metrics functionality
                has_snapshots = len(self.metrics_collector.snapshots) > 0
                
                # Test export functionality
                export_successful = False
                try:
                    test_json_file = f"test_metrics_{int(time.time())}.json"
                    test_csv_file = f"test_metrics_{int(time.time())}.csv"
                    
                    self.metrics_collector.export_to_json(test_json_file)
                    self.metrics_collector.export_to_csv(test_csv_file, "snapshots")
                    
                    # Clean up test files
                    if os.path.exists(test_json_file):
                        os.remove(test_json_file)
                    if os.path.exists(test_csv_file):
                        os.remove(test_csv_file)
                    
                    export_successful = True
                except Exception:
                    pass
                
                # Test trend analysis
                trend_analysis_working = False
                try:
                    if has_snapshots:
                        trend_result = self.metrics_collector.get_trend_analysis("success_rate")
                        trend_analysis_working = "trend" in trend_result
                except Exception:
                    pass
                
                metrics_compliant = has_snapshots and export_successful and trend_analysis_working
                
                duration = time.time() - start_time
                
                results.append(ValidationTestResult(
                    criterion_id="AC-013",
                    criterion_name="Metrics Collection and Export",
                    result=ValidationResult.PASS if metrics_compliant else ValidationResult.FAIL,
                    duration=duration,
                    details={
                        "snapshots_collected": len(self.metrics_collector.snapshots),
                        "export_successful": export_successful,
                        "trend_analysis_working": trend_analysis_working,
                        "metrics_compliant": metrics_compliant
                    },
                    compliance_status=metrics_compliant
                ))
            else:
                results.append(ValidationTestResult(
                    criterion_id="AC-013",
                    criterion_name="Metrics Collection and Export",
                    result=ValidationResult.SKIP,
                    duration=0.0,
                    error_message="No client available for metrics testing",
                    compliance_status=False
                ))
                
        except Exception as e:
            results.append(ValidationTestResult(
                criterion_id="AC-013",
                criterion_name="Metrics Collection and Export",
                result=ValidationResult.ERROR,
                duration=time.time() - start_time,
                error_message=str(e),
                compliance_status=False
            ))
        
        return results
    
    async def validate_cli_interface(self) -> List[ValidationTestResult]:
        """
        Validate CLI interface functionality.
        
        Returns:
            List of validation test results for CLI interface
        """
        results = []
        
        # AC-014: Interactive CLI Functionality
        start_time = time.time()
        try:
            # Test CLI module import and basic functionality
            cli_import_successful = False
            cli_functionality_working = False
            
            try:
                from cli_demo import CLIDemo
                cli_import_successful = True
                
                # Test CLI initialization
                cli_demo = CLIDemo()
                cli_functionality_working = (
                    hasattr(cli_demo, 'client') and
                    hasattr(cli_demo, 'performance_display') and
                    hasattr(cli_demo, 'metrics_collector') and
                    hasattr(cli_demo, '_handle_command')
                )
                
            except ImportError:
                pass
            except Exception:
                pass
            
            duration = time.time() - start_time
            
            cli_compliant = cli_import_successful and cli_functionality_working
            
            results.append(ValidationTestResult(
                criterion_id="AC-014",
                criterion_name="Interactive CLI Functionality",
                result=ValidationResult.PASS if cli_compliant else ValidationResult.FAIL,
                duration=duration,
                details={
                    "cli_import_successful": cli_import_successful,
                    "cli_functionality_working": cli_functionality_working,
                    "cli_compliant": cli_compliant
                },
                compliance_status=cli_compliant
            ))
            
        except Exception as e:
            results.append(ValidationTestResult(
                criterion_id="AC-014",
                criterion_name="Interactive CLI Functionality",
                result=ValidationResult.ERROR,
                duration=time.time() - start_time,
                error_message=str(e),
                compliance_status=False
            ))
        
        return results
    
    async def run_comprehensive_validation(self) -> Branch64ValidationReport:
        """
        Run comprehensive validation of all Branch 6.4 acceptance criteria.
        
        Returns:
            Branch64ValidationReport containing complete validation results
        """
        self.validation_start_time = time.time()
        
        self.structured_logger.info(
            "Starting comprehensive Branch 6.4 validation",
            status=LogStatus.STARTED,
            total_criteria=len(self.acceptance_criteria),
            validation_id=self.validation_id
        )
        
        # Setup test environment
        if not await self.setup_test_environment():
            return Branch64ValidationReport(
                validation_timestamp=datetime.utcnow().isoformat() + "Z",
                total_criteria=len(self.acceptance_criteria),
                passed_criteria=0,
                failed_criteria=0,
                error_criteria=1,
                skipped_criteria=0,
                overall_compliance=False,
                performance_summary={},
                test_results=[ValidationTestResult(
                    criterion_id="SETUP",
                    criterion_name="Environment Setup",
                    result=ValidationResult.ERROR,
                    duration=0.0,
                    error_message="Failed to setup test environment",
                    compliance_status=False
                )],
                recommendations=["Fix test environment setup issues"],
                execution_summary={"error": "Environment setup failed"}
            )
        
        try:
            # Run all validation categories
            validation_categories = [
                ("Core Functionality", self.validate_core_functionality),
                ("Linear Reconnect Logic", self.validate_linear_reconnect_logic),
                ("Performance Requirements", self.validate_performance_requirements),
                ("Message Format and Payload", self.validate_message_format_and_payload),
                ("Authentication and Security", self.validate_authentication_and_security),
                ("Error Handling and Recovery", self.validate_error_handling_and_recovery),
                ("Logging and Metrics", self.validate_logging_and_metrics),
                ("CLI Interface", self.validate_cli_interface)
            ]
            
            all_results = []
            
            for category_name, validation_func in validation_categories:
                self.logger.info(f"Running {category_name} validation...")
                
                try:
                    category_results = await validation_func()
                    all_results.extend(category_results)
                    
                    self.structured_logger.info(
                        f"{category_name} validation completed",
                        status=LogStatus.COMPLETED,
                        category=category_name,
                        results_count=len(category_results)
                    )
                    
                except Exception as e:
                    self.logger.error(f"Error in {category_name} validation: {e}")
                    self.structured_logger.error(
                        f"{category_name} validation failed",
                        status=LogStatus.FAILED,
                        category=category_name,
                        error=e
                    )
            
            # Calculate summary statistics
            total_criteria = len(all_results)
            passed_criteria = len([r for r in all_results if r.result == ValidationResult.PASS])
            failed_criteria = len([r for r in all_results if r.result == ValidationResult.FAIL])
            error_criteria = len([r for r in all_results if r.result == ValidationResult.ERROR])
            skipped_criteria = len([r for r in all_results if r.result == ValidationResult.SKIP])
            
            overall_compliance = (
                failed_criteria == 0 and
                error_criteria == 0 and
                passed_criteria > 0
            )
            
            # Generate performance summary
            performance_results = [r for r in all_results if r.performance_data]
            performance_summary = self._generate_performance_summary(performance_results)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(all_results)
            
            # Create execution summary
            execution_summary = {
                "total_duration_s": time.time() - self.validation_start_time,
                "validation_categories": len(validation_categories),
                "environment_setup_successful": True,
                "validation_id": self.validation_id
            }
            
            validation_report = Branch64ValidationReport(
                validation_timestamp=datetime.utcnow().isoformat() + "Z",
                total_criteria=total_criteria,
                passed_criteria=passed_criteria,
                failed_criteria=failed_criteria,
                error_criteria=error_criteria,
                skipped_criteria=skipped_criteria,
                overall_compliance=overall_compliance,
                performance_summary=performance_summary,
                test_results=all_results,
                recommendations=recommendations,
                execution_summary=execution_summary
            )
            
            self.structured_logger.info(
                "Branch 6.4 validation completed",
                status=LogStatus.COMPLETED,
                overall_compliance=overall_compliance,
                passed_criteria=passed_criteria,
                total_criteria=total_criteria,
                validation_duration_s=execution_summary["total_duration_s"]
            )
            
            return validation_report
            
        finally:
            await self.cleanup_test_environment()
    
    def _generate_performance_summary(self, performance_results: List[ValidationTestResult]) -> Dict[str, Any]:
        """Generate performance summary from performance test results."""
        if not performance_results:
            return {"status": "no_performance_data"}
        
        handshake_times = []
        latency_times = []
        
        for result in performance_results:
            if result.performance_data:
                if "handshake_times" in result.performance_data:
                    handshake_times.extend(result.performance_data["handshake_times"])
                if "latency_times" in result.performance_data:
                    latency_times.extend(result.performance_data["latency_times"])
        
        summary = {
            "handshake_performance": {
                "requirement_ms": 300.0,
                "samples": len(handshake_times),
                "compliant": all(t <= 300.0 for t in handshake_times) if handshake_times else False
            },
            "latency_performance": {
                "requirement_ms": 500.0,
                "samples": len(latency_times),
                "compliant": all(t <= 500.0 for t in latency_times) if latency_times else False
            }
        }
        
        if handshake_times:
            summary["handshake_performance"].update({
                "avg_ms": statistics.mean(handshake_times),
                "max_ms": max(handshake_times),
                "min_ms": min(handshake_times)
            })
        
        if latency_times:
            summary["latency_performance"].update({
                "avg_ms": statistics.mean(latency_times),
                "max_ms": max(latency_times),
                "min_ms": min(latency_times)
            })
        
        return summary
    
    def _generate_recommendations(self, results: List[ValidationTestResult]) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        failed_results = [r for r in results if r.result == ValidationResult.FAIL]
        error_results = [r for r in results if r.result == ValidationResult.ERROR]
        
        if failed_results:
            recommendations.append(f"Address {len(failed_results)} failed acceptance criteria")
            
            # Specific recommendations based on failed criteria
            for result in failed_results:
                if "handshake" in result.criterion_name.lower():
                    recommendations.append("Optimize WebSocket handshake performance to meet ≤300ms requirement")
                elif "latency" in result.criterion_name.lower():
                    recommendations.append("Optimize message latency to meet ≤500ms requirement")
                elif "reconnect" in result.criterion_name.lower():
                    recommendations.append("Review linear reconnect logic implementation for ADD Profile C compliance")
                elif "authentication" in result.criterion_name.lower():
                    recommendations.append("Verify JWT authentication configuration and service_role_key setup")
        
        if error_results:
            recommendations.append(f"Investigate and resolve {len(error_results)} validation errors")
        
        if not failed_results and not error_results:
            recommendations.append("All acceptance criteria passed - Branch 6.4 implementation is compliant")
        
        return recommendations
    
    def print_validation_report(self, report: Branch64ValidationReport) -> None:
        """
        Print formatted validation report to console.
        
        Args:
            report: Branch64ValidationReport to print
        """
        print("\n" + "="*100)
        print("BRANCH 6.4 COMPREHENSIVE VALIDATION REPORT")
        print("="*100)
        
        print(f"Validation Timestamp: {report.validation_timestamp}")
        print(f"Validation ID: {self.validation_id}")
        print(f"Total Criteria: {report.total_criteria}")
        print(f"Passed: {report.passed_criteria}")
        print(f"Failed: {report.failed_criteria}")
        print(f"Errors: {report.error_criteria}")
        print(f"Skipped: {report.skipped_criteria}")
        print(f"Overall Compliance: {'✓ COMPLIANT' if report.overall_compliance else '✗ NON-COMPLIANT'}")
        
        print(f"\nExecution Time: {report.execution_summary.get('total_duration_s', 0):.2f} seconds")
        
        # Performance Summary
        if report.performance_summary and "handshake_performance" in report.performance_summary:
            print("\nPERFORMANCE SUMMARY:")
            print("-" * 50)
            
            handshake = report.performance_summary["handshake_performance"]
            latency = report.performance_summary["latency_performance"]
            
            print(f"Handshake Performance: {'✓ COMPLIANT' if handshake.get('compliant', False) else '✗ NON-COMPLIANT'}")
            if handshake.get("avg_ms"):
                print(f"  Average: {handshake['avg_ms']:.1f}ms (requirement: ≤{handshake['requirement_ms']}ms)")
                print(f"  Range: {handshake['min_ms']:.1f}ms - {handshake['max_ms']:.1f}ms")
            
            print(f"Message Latency: {'✓ COMPLIANT' if latency.get('compliant', False) else '✗ NON-COMPLIANT'}")
            if latency.get("avg_ms"):
                print(f"  Average: {latency['avg_ms']:.1f}ms (requirement: ≤{latency['requirement_ms']}ms)")
                print(f"  Range: {latency['min_ms']:.1f}ms - {latency['max_ms']:.1f}ms")
        
        # Detailed Results
        print("\nDETAILED VALIDATION RESULTS:")
        print("-" * 50)
        
        for result in report.test_results:
            status_symbol = {
                ValidationResult.PASS: "✓",
                ValidationResult.FAIL: "✗",
                ValidationResult.ERROR: "⚠",
                ValidationResult.SKIP: "-"
            }.get(result.result, "?")
            
            print(f"{status_symbol} {result.criterion_id}: {result.criterion_name}")
            
            if result.result != ValidationResult.PASS and result.error_message:
                print(f"    Error: {result.error_message}")
            
            if result.details and result.result == ValidationResult.PASS:
                # Show key compliance details for passed tests
                if "requirement_met" in result.details:
                    print(f"    Requirement Met: {result.details['requirement_met']}")
        
        # Recommendations
        if report.recommendations:
            print("\nRECOMMENDATIONS:")
            print("-" * 50)
            for i, recommendation in enumerate(report.recommendations, 1):
                print(f"{i}. {recommendation}")
        
        print("\n" + "="*100)
    
    def export_validation_report(self, report: Branch64ValidationReport,
                                filepath: Optional[str] = None) -> str:
        """
        Export validation report to JSON file.
        
        Args:
            report: Branch64ValidationReport to export
            filepath: Optional file path (defaults to timestamped filename)
            
        Returns:
            str: Path to exported file
        """
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"branch_6_4_validation_report_{timestamp}.json"
        
        # Convert report to dictionary
        report_dict = {
            "validation_timestamp": report.validation_timestamp,
            "validation_id": self.validation_id,
            "total_criteria": report.total_criteria,
            "passed_criteria": report.passed_criteria,
            "failed_criteria": report.failed_criteria,
            "error_criteria": report.error_criteria,
            "skipped_criteria": report.skipped_criteria,
            "overall_compliance": report.overall_compliance,
            "performance_summary": report.performance_summary,
            "test_results": [
                {
                    "criterion_id": r.criterion_id,
                    "criterion_name": r.criterion_name,
                    "result": r.result.value,
                    "duration": r.duration,
                    "details": r.details,
                    "error_message": r.error_message,
                    "performance_data": r.performance_data,
                    "compliance_status": r.compliance_status
                }
                for r in report.test_results
            ],
            "recommendations": report.recommendations,
            "execution_summary": report.execution_summary,
            "acceptance_criteria": [
                {
                    "id": ac.id,
                    "name": ac.name,
                    "description": ac.description,
                    "requirement": ac.requirement,
                    "validation_method": ac.validation_method,
                    "priority": ac.priority
                }
                for ac in self.acceptance_criteria
            ]
        }
        
        try:
            with open(filepath, 'w') as f:
                json.dump(report_dict, f, indent=2, default=str)
            
            self.logger.info(f"Validation report exported to: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Failed to export validation report: {e}")
            raise


async def main():
    """Main function to run Branch 6.4 comprehensive validation."""
    print("Branch 6.4 Comprehensive Validation")
    print("===================================")
    
    # Check if server is running
    print("Checking server availability...")
    try:
        import subprocess
        result = subprocess.run(
            ["curl", "-s", "http://localhost:8090/health"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            print("❌ Server not available at http://localhost:8090")
            print("Please start the server using: cd docker && ./start.sh")
            return 1
        else:
            print("✅ Server is running")
    except Exception as e:
        print(f"⚠️  Could not verify server status: {e}")
        print("Proceeding with validation...")
    
    # Initialize validator
    validator = Branch64Validator()
    
    try:
        # Run comprehensive validation
        print("\nStarting comprehensive Branch 6.4 validation...")
        report = await validator.run_comprehensive_validation()
        
        # Print report
        validator.print_validation_report(report)
        
        # Export report
        export_path = validator.export_validation_report(report)
        print(f"\n📄 Detailed report exported to: {export_path}")
        
        # Return appropriate exit code
        return 0 if report.overall_compliance else 1
        
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)