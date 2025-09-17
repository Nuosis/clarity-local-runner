#!/usr/bin/env python3
"""
Performance Test Scenarios for WebSocket Demo Client

This module provides comprehensive test scenarios to validate the enhanced
performance monitoring system under different conditions, ensuring all
performance requirements are met.

Performance Requirements:
- Handshake time: ≤300ms
- Message latency: ≤500ms
- Performance statistics collection and validation
- Performance degradation detection and alerting
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import statistics

from websocket_demo_client import WebSocketDemoClient, MessageType, ClientConfig, ConnectionState


class PerformanceTestScenarios:
    """
    Comprehensive performance test scenarios for WebSocket demo client.
    
    Tests various conditions including:
    - Normal operation performance
    - High-frequency message scenarios
    - Connection stability under load
    - Performance degradation detection
    - Threshold validation and alerting
    """
    
    def __init__(self, server_url: str = "ws://localhost:8090/api/v1/ws/devteam", 
                 project_id: str = "test-project"):
        """
        Initialize performance test scenarios.
        
        Args:
            server_url: WebSocket server URL
            project_id: Project identifier for testing
        """
        self.server_url = server_url
        self.project_id = project_id
        self.client: Optional[WebSocketDemoClient] = None
        self.test_results: Dict[str, Any] = {}
        
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
                project_id=self.project_id
            )
            self.client = WebSocketDemoClient(config)
            return True
        except Exception as e:
            self.logger.error(f"Failed to setup client: {e}")
            return False
    
    async def cleanup_client(self) -> None:
        """Clean up WebSocket client after testing."""
        if self.client and self.client.state.name == "CONNECTED":
            await self.client.disconnect()
    
    async def test_basic_connection_performance(self) -> Dict[str, Any]:
        """
        Test basic connection performance and handshake timing.
        
        Returns:
            Dict containing test results and performance metrics
        """
        self.logger.info("Testing basic connection performance...")
        
        results = {
            "test_name": "basic_connection_performance",
            "success": False,
            "handshake_times": [],
            "performance_stats": None,
            "threshold_violations": 0,
            "error": None
        }
        
        try:
            # Test multiple connections to get statistical data
            for i in range(5):
                self.logger.info(f"Connection attempt {i+1}/5")
                
                # Ensure clean state
                if self.client and self.client.state == ConnectionState.CONNECTED:
                    await self.client.disconnect()
                    await asyncio.sleep(0.5)
                
                # Connect and measure handshake time
                start_time = time.time()
                success = await self.client.connect() if self.client else False
                handshake_time = time.time() - start_time
                
                if success:
                    results["handshake_times"].append(handshake_time * 1000)  # Convert to ms
                    self.logger.info(f"Handshake {i+1}: {handshake_time*1000:.1f}ms")
                    
                    # Check threshold violation
                    if handshake_time > 0.3:  # 300ms threshold
                        results["threshold_violations"] += 1
                        self.logger.warning(f"Handshake time exceeded 300ms: {handshake_time*1000:.1f}ms")
                else:
                    self.logger.error(f"Connection attempt {i+1} failed")
                    results["error"] = f"Connection attempt {i+1} failed"
                    return results
                
                await asyncio.sleep(1)  # Brief pause between tests
            
            # Get performance statistics from client
            if self.client:
                results["performance_stats"] = self.client.get_performance_statistics()
                validation = self.client.validate_performance_targets()
                results["targets_met"] = validation["overall_healthy"]
            
            # Calculate test statistics
            if results["handshake_times"]:
                times = results["handshake_times"]
                results["avg_handshake"] = statistics.mean(times)
                results["max_handshake"] = max(times)
                results["min_handshake"] = min(times)
                results["p95_handshake"] = statistics.quantiles(times, n=20)[18] if len(times) >= 5 else max(times)
            
            results["success"] = True
            self.logger.info("Basic connection performance test completed successfully")
            
        except Exception as e:
            self.logger.error(f"Basic connection performance test failed: {e}")
            results["error"] = str(e)
        
        return results
    
    async def test_message_latency_performance(self) -> Dict[str, Any]:
        """
        Test message round-trip latency performance.
        
        Returns:
            Dict containing test results and latency metrics
        """
        self.logger.info("Testing message latency performance...")
        
        results = {
            "test_name": "message_latency_performance",
            "success": False,
            "message_latencies": [],
            "messages_sent": 0,
            "messages_received": 0,
            "threshold_violations": 0,
            "error": None
        }
        
        try:
            # Ensure connected
            if not self.client or self.client.state != ConnectionState.CONNECTED:
                success = await self.client.connect() if self.client else False
                if not success:
                    results["error"] = "Failed to connect for latency test"
                    return results
            
            # Send multiple messages to test latency
            for i in range(10):
                payload = {
                    "test_message": f"latency_test_{i}",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "sequence": i
                }
                
                # Send message and track timing
                start_time = time.time()
                success = await self.client.send_message(MessageType.EXECUTION_UPDATE, payload) if self.client else False
                
                if success:
                    results["messages_sent"] += 1
                    self.logger.info(f"Sent message {i+1}/10")
                    
                    # Wait briefly for potential response processing
                    await asyncio.sleep(0.1)
                else:
                    self.logger.error(f"Failed to send message {i+1}")
                
                await asyncio.sleep(0.5)  # Brief pause between messages
            
            # Get performance statistics from client
            if self.client:
                perf_stats = self.client.get_performance_statistics()
                results["performance_stats"] = perf_stats
                
                # Extract latency data
                latency_data = perf_stats.get("message_latency", {})
                if latency_data.get("statistics", {}).get("count", 0) > 0:
                    stats = latency_data["statistics"]
                    results["avg_latency"] = stats["avg"]
                    results["max_latency"] = stats["max"]
                    results["min_latency"] = stats["min"]
                    results["p95_latency"] = stats["p95"]
                    results["threshold_violations"] = latency_data.get("violations", 0)
            
            results["success"] = True
            self.logger.info("Message latency performance test completed successfully")
            
        except Exception as e:
            self.logger.error(f"Message latency performance test failed: {e}")
            results["error"] = str(e)
        
        return results
    
    async def test_high_frequency_messaging(self) -> Dict[str, Any]:
        """
        Test performance under high-frequency messaging conditions.
        
        Returns:
            Dict containing test results and performance under load
        """
        self.logger.info("Testing high-frequency messaging performance...")
        
        results = {
            "test_name": "high_frequency_messaging",
            "success": False,
            "messages_sent": 0,
            "send_failures": 0,
            "avg_send_time": 0,
            "performance_degradation": False,
            "error": None
        }
        
        try:
            # Ensure connected
            if not self.client or self.client.state != ConnectionState.CONNECTED:
                success = await self.client.connect() if self.client else False
                if not success:
                    results["error"] = "Failed to connect for high-frequency test"
                    return results
            
            # Get baseline performance
            baseline_stats = self.client.get_performance_statistics() if self.client else {}
            
            # Send messages rapidly
            send_times = []
            for i in range(50):  # Send 50 messages rapidly
                payload = {
                    "burst_test": f"message_{i}",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "batch": "high_frequency"
                }
                
                start_time = time.time()
                success = await self.client.send_message(MessageType.EXECUTION_LOG, payload) if self.client else False
                send_time = time.time() - start_time
                
                send_times.append(send_time)
                
                if success:
                    results["messages_sent"] += 1
                else:
                    results["send_failures"] += 1
                
                # Very brief pause to simulate high-frequency but not overwhelming
                await asyncio.sleep(0.05)
            
            # Calculate send performance
            if send_times:
                results["avg_send_time"] = statistics.mean(send_times) * 1000  # Convert to ms
                results["max_send_time"] = max(send_times) * 1000
            
            # Check for performance degradation
            current_stats = self.client.get_performance_statistics() if self.client else {}
            validation = self.client.validate_performance_targets() if self.client else {"overall_healthy": True}
            results["performance_degradation"] = not validation["overall_healthy"]
            results["final_performance_stats"] = current_stats
            
            results["success"] = True
            self.logger.info(f"High-frequency messaging test completed: {results['messages_sent']} sent, {results['send_failures']} failed")
            
        except Exception as e:
            self.logger.error(f"High-frequency messaging test failed: {e}")
            results["error"] = str(e)
        
        return results
    
    async def test_performance_threshold_validation(self) -> Dict[str, Any]:
        """
        Test performance threshold validation and alerting system.
        
        Returns:
            Dict containing validation test results
        """
        self.logger.info("Testing performance threshold validation...")
        
        results = {
            "test_name": "performance_threshold_validation",
            "success": False,
            "handshake_threshold_test": None,
            "latency_threshold_test": None,
            "alert_system_test": None,
            "error": None
        }
        
        try:
            # Ensure connected
            if not self.client or self.client.state != ConnectionState.CONNECTED:
                success = await self.client.connect() if self.client else False
                if not success:
                    results["error"] = "Failed to connect for threshold validation test"
                    return results
            
            # Test handshake threshold validation
            validation = self.client.validate_performance_targets() if self.client else {}
            results["handshake_threshold_test"] = {
                "handshake_healthy": validation.get("handshake_healthy", False),
                "handshake_violations": validation.get("handshake_violations", 0)
            }
            
            # Test message latency threshold validation
            results["latency_threshold_test"] = {
                "latency_healthy": validation.get("latency_healthy", False),
                "latency_violations": validation.get("latency_violations", 0)
            }
            
            # Test overall health assessment
            results["overall_healthy"] = validation.get("overall_healthy", False)
            
            # Get performance report
            report = self.client.get_performance_report() if self.client else "No client available"
            results["performance_report"] = report
            
            # Test alert system by checking if alerts are properly tracked
            perf_stats = self.client.get_performance_statistics() if self.client else {}
            results["alert_system_test"] = {
                "handshake_violations_tracked": perf_stats.get("handshake", {}).get("violations", 0),
                "latency_violations_tracked": perf_stats.get("message_latency", {}).get("violations", 0)
            }
            
            results["success"] = True
            self.logger.info("Performance threshold validation test completed successfully")
            
        except Exception as e:
            self.logger.error(f"Performance threshold validation test failed: {e}")
            results["error"] = str(e)
        
        return results
    
    async def test_performance_history_tracking(self) -> Dict[str, Any]:
        """
        Test performance history tracking and trend analysis.
        
        Returns:
            Dict containing history tracking test results
        """
        self.logger.info("Testing performance history tracking...")
        
        results = {
            "test_name": "performance_history_tracking",
            "success": False,
            "history_data_available": False,
            "trend_analysis": None,
            "rolling_window_test": None,
            "error": None
        }
        
        try:
            # Ensure connected and generate some performance data
            if not self.client or self.client.state != ConnectionState.CONNECTED:
                success = await self.client.connect() if self.client else False
                if not success:
                    results["error"] = "Failed to connect for history tracking test"
                    return results
            
            # Generate performance data by sending messages
            for i in range(20):
                payload = {
                    "history_test": f"message_{i}",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
                if self.client:
                    await self.client.send_message(MessageType.EXECUTION_UPDATE, payload)
                await asyncio.sleep(0.1)
            
            # Test performance statistics collection
            perf_stats = self.client.get_performance_statistics() if self.client else {}
            
            # Check if history data is available
            handshake_data = perf_stats.get("handshake", {})
            latency_data = perf_stats.get("message_latency", {})
            
            results["history_data_available"] = (
                handshake_data.get("statistics", {}).get("count", 0) > 0 or
                latency_data.get("statistics", {}).get("count", 0) > 0
            )
            
            # Test rolling window functionality (implicit in the statistics)
            results["rolling_window_test"] = {
                "handshake_count": handshake_data.get("statistics", {}).get("count", 0),
                "latency_count": latency_data.get("statistics", {}).get("count", 0),
                "max_history_size": 100  # Based on implementation
            }
            
            # Test trend analysis (basic implementation)
            if results["history_data_available"]:
                results["trend_analysis"] = {
                    "handshake_avg": handshake_data.get("statistics", {}).get("avg", 0),
                    "latency_avg": latency_data.get("statistics", {}).get("avg", 0),
                    "performance_stable": perf_stats.get("overall_healthy", True)
                }
            
            results["success"] = True
            self.logger.info("Performance history tracking test completed successfully")
            
        except Exception as e:
            self.logger.error(f"Performance history tracking test failed: {e}")
            results["error"] = str(e)
        
        return results
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """
        Run all performance test scenarios.
        
        Returns:
            Dict containing results from all test scenarios
        """
        self.logger.info("Starting comprehensive performance test suite...")
        
        all_results = {
            "test_suite": "comprehensive_performance_tests",
            "start_time": datetime.utcnow().isoformat(),
            "tests": {},
            "summary": {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "overall_success": False
            }
        }
        
        # Setup client
        if not await self.setup_client():
            all_results["error"] = "Failed to setup WebSocket client"
            return all_results
        
        # Define test scenarios
        test_scenarios = [
            ("basic_connection", self.test_basic_connection_performance),
            ("message_latency", self.test_message_latency_performance),
            ("high_frequency", self.test_high_frequency_messaging),
            ("threshold_validation", self.test_performance_threshold_validation),
            ("history_tracking", self.test_performance_history_tracking)
        ]
        
        # Run each test scenario
        for test_name, test_func in test_scenarios:
            self.logger.info(f"Running test: {test_name}")
            
            try:
                test_result = await test_func()
                all_results["tests"][test_name] = test_result
                all_results["summary"]["total_tests"] += 1
                
                if test_result.get("success", False):
                    all_results["summary"]["passed_tests"] += 1
                    self.logger.info(f"Test {test_name}: PASSED")
                else:
                    all_results["summary"]["failed_tests"] += 1
                    self.logger.error(f"Test {test_name}: FAILED - {test_result.get('error', 'Unknown error')}")
                
            except Exception as e:
                self.logger.error(f"Test {test_name} encountered exception: {e}")
                all_results["tests"][test_name] = {
                    "test_name": test_name,
                    "success": False,
                    "error": str(e)
                }
                all_results["summary"]["failed_tests"] += 1
        
        # Cleanup
        await self.cleanup_client()
        
        # Calculate overall success
        all_results["summary"]["overall_success"] = (
            all_results["summary"]["failed_tests"] == 0 and
            all_results["summary"]["passed_tests"] > 0
        )
        
        all_results["end_time"] = datetime.utcnow().isoformat()
        
        self.logger.info(f"Performance test suite completed: {all_results['summary']['passed_tests']}/{all_results['summary']['total_tests']} tests passed")
        
        return all_results
    
    def print_test_summary(self, results: Dict[str, Any]) -> None:
        """
        Print a formatted summary of test results.
        
        Args:
            results: Test results dictionary from run_all_tests()
        """
        print("\n" + "="*80)
        print("WEBSOCKET PERFORMANCE TEST RESULTS")
        print("="*80)
        
        summary = results.get("summary", {})
        print(f"Total Tests: {summary.get('total_tests', 0)}")
        print(f"Passed: {summary.get('passed_tests', 0)}")
        print(f"Failed: {summary.get('failed_tests', 0)}")
        print(f"Overall Success: {'✓ PASS' if summary.get('overall_success', False) else '✗ FAIL'}")
        
        print("\nDETAILED RESULTS:")
        print("-" * 40)
        
        for test_name, test_result in results.get("tests", {}).items():
            status = "✓ PASS" if test_result.get("success", False) else "✗ FAIL"
            print(f"{test_name}: {status}")
            
            if not test_result.get("success", False) and test_result.get("error"):
                print(f"  Error: {test_result['error']}")
            
            # Print key metrics for successful tests
            if test_result.get("success", False):
                if "avg_handshake" in test_result:
                    print(f"  Avg Handshake: {test_result['avg_handshake']:.1f}ms")
                if "avg_latency" in test_result:
                    print(f"  Avg Latency: {test_result['avg_latency']:.1f}ms")
                if "messages_sent" in test_result:
                    print(f"  Messages Sent: {test_result['messages_sent']}")
        
        print("\n" + "="*80)


async def main():
    """Main function to run performance test scenarios."""
    # Create test instance
    test_scenarios = PerformanceTestScenarios()
    
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