#!/usr/bin/env python3
"""
Task 8.1.2: API Performance Validation Test
Tests API response performance to ensure ≤200ms requirement is met.
"""

import time
import requests
import json
import statistics
from typing import List, Dict, Any

def test_api_performance():
    """Test API response performance for status endpoints."""
    
    # Test configuration
    base_url = "http://localhost:8090"
    health_endpoint = f"{base_url}/health"
    status_endpoint = f"{base_url}/api/v1/devteam-automation/status"
    
    # Performance requirements
    max_response_time_ms = 200
    num_tests = 10
    
    results = {
        "health_endpoint": {
            "url": health_endpoint,
            "response_times": [],
            "success_count": 0,
            "error_count": 0
        },
        "status_endpoint": {
            "url": status_endpoint,
            "response_times": [],
            "success_count": 0,
            "error_count": 0
        }
    }
    
    print("=" * 60)
    print("Task 8.1.2: API Performance Validation")
    print("=" * 60)
    print(f"Testing API response times (requirement: ≤{max_response_time_ms}ms)")
    print(f"Number of test iterations: {num_tests}")
    print()
    
    # Test health endpoint
    print("Testing Health Endpoint...")
    for i in range(num_tests):
        try:
            start_time = time.time()
            response = requests.get(health_endpoint, timeout=5)
            end_time = time.time()
            
            response_time_ms = (end_time - start_time) * 1000
            results["health_endpoint"]["response_times"].append(response_time_ms)
            
            if response.status_code == 200:
                results["health_endpoint"]["success_count"] += 1
                status = "✅" if response_time_ms <= max_response_time_ms else "⚠️"
                print(f"  Test {i+1}: {response_time_ms:.1f}ms {status}")
            else:
                results["health_endpoint"]["error_count"] += 1
                print(f"  Test {i+1}: HTTP {response.status_code} ❌")
                
        except Exception as e:
            results["health_endpoint"]["error_count"] += 1
            print(f"  Test {i+1}: Error - {str(e)} ❌")
    
    print()
    
    # Test status endpoint (with mock data since we need a valid project_id)
    print("Testing Status Endpoint...")
    test_project_id = "test-project-123"
    status_url = f"{status_endpoint}?project_id={test_project_id}"
    
    for i in range(num_tests):
        try:
            start_time = time.time()
            response = requests.get(status_url, timeout=5)
            end_time = time.time()
            
            response_time_ms = (end_time - start_time) * 1000
            results["status_endpoint"]["response_times"].append(response_time_ms)
            
            # Accept both 200 (found) and 404 (not found) as valid responses for performance testing
            if response.status_code in [200, 404]:
                results["status_endpoint"]["success_count"] += 1
                status = "✅" if response_time_ms <= max_response_time_ms else "⚠️"
                print(f"  Test {i+1}: {response_time_ms:.1f}ms (HTTP {response.status_code}) {status}")
            else:
                results["status_endpoint"]["error_count"] += 1
                print(f"  Test {i+1}: HTTP {response.status_code} ❌")
                
        except Exception as e:
            results["status_endpoint"]["error_count"] += 1
            print(f"  Test {i+1}: Error - {str(e)} ❌")
    
    print()
    print("=" * 60)
    print("PERFORMANCE ANALYSIS")
    print("=" * 60)
    
    # Analyze results
    overall_pass = True
    
    for endpoint_name, data in results.items():
        if data["response_times"]:
            avg_time = statistics.mean(data["response_times"])
            min_time = min(data["response_times"])
            max_time = max(data["response_times"])
            median_time = statistics.median(data["response_times"])
            
            # Check if performance requirement is met
            times_over_limit = [t for t in data["response_times"] if t > max_response_time_ms]
            performance_pass = len(times_over_limit) == 0
            
            if not performance_pass:
                overall_pass = False
            
            print(f"\n{endpoint_name.replace('_', ' ').title()}:")
            print(f"  URL: {data['url']}")
            print(f"  Successful requests: {data['success_count']}/{num_tests}")
            print(f"  Average response time: {avg_time:.1f}ms")
            print(f"  Median response time: {median_time:.1f}ms")
            print(f"  Min response time: {min_time:.1f}ms")
            print(f"  Max response time: {max_time:.1f}ms")
            print(f"  Times over {max_response_time_ms}ms limit: {len(times_over_limit)}")
            print(f"  Performance requirement met: {'✅ YES' if performance_pass else '❌ NO'}")
        else:
            print(f"\n{endpoint_name.replace('_', ' ').title()}:")
            print(f"  No successful responses recorded ❌")
            overall_pass = False
    
    print()
    print("=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    
    if overall_pass:
        print("✅ ALL PERFORMANCE REQUIREMENTS MET")
        print(f"✅ All API responses completed within {max_response_time_ms}ms requirement")
    else:
        print("⚠️  PERFORMANCE REQUIREMENTS NOT FULLY MET")
        print(f"⚠️  Some API responses exceeded {max_response_time_ms}ms requirement")
    
    print()
    print("Task 8.1.2 Performance Validation: COMPLETED")
    
    # Save results to file
    results_file = "task_8_1_2_performance_validation_results.json"
    with open(results_file, 'w') as f:
        json.dump({
            "test_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "performance_requirement_ms": max_response_time_ms,
            "num_test_iterations": num_tests,
            "overall_pass": overall_pass,
            "results": results
        }, f, indent=2)
    
    print(f"Detailed results saved to: {results_file}")
    
    return overall_pass

if __name__ == "__main__":
    test_api_performance()