#!/usr/bin/env python3
"""
Health Endpoint Tests - Most Basic Tests
These tests verify the API is running and basic endpoints are accessible.
"""

import os
import sys

# Add the tests directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api_test_framework import (
    APITestFramework,
    validate_api_response,
    validate_health_response,
)


def test_health_endpoints():
    """Test all health check endpoints."""
    framework = APITestFramework()

    print("🏥 Testing Health Endpoints")
    print("=" * 50)

    # Test 1: Basic health check
    framework.run_test(
        test_name="Basic Health Check",
        method="GET",
        endpoint="/health",
        expected_status=200,
        require_auth=False,
        validate_response=validate_health_response,
    )

    # Test 2: Detailed health check
    framework.run_test(
        test_name="Detailed Health Check",
        method="GET",
        endpoint="/health/detailed",
        expected_status=200,
        require_auth=False,
        validate_response=validate_health_response,
    )

    # Test 3: Readiness probe
    framework.run_test(
        test_name="Readiness Probe",
        method="GET",
        endpoint="/health/ready",
        expected_status=200,
        require_auth=False,
        validate_response=validate_api_response,
    )

    # Test 4: Liveness probe
    framework.run_test(
        test_name="Liveness Probe",
        method="GET",
        endpoint="/health/live",
        expected_status=200,
        require_auth=False,
        validate_response=validate_api_response,
    )

    # Test 5: Root endpoint
    framework.run_test(
        test_name="Root Endpoint",
        method="GET",
        endpoint="/",
        expected_status=200,
        require_auth=False,
    )

    return framework


def test_auth_health():
    """Test authentication service health."""
    framework = APITestFramework()

    print("\n🔐 Testing Auth Service Health")
    print("=" * 50)

    # Test auth health endpoint
    framework.run_test(
        test_name="Auth Service Health",
        method="GET",
        endpoint="/auth/health",
        expected_status=200,
        require_auth=False,
        validate_response=lambda r: r.get("status") == "healthy",
    )

    return framework


if __name__ == "__main__":
    print("🚀 Cedar Heights Music Academy - Health Tests")
    print("Testing basic health endpoints to verify API is running...")

    # Run health tests
    health_framework = test_health_endpoints()
    auth_health_framework = test_auth_health()

    # Combine results
    all_results = health_framework.results + auth_health_framework.results
    health_framework.results = all_results

    # Print summary
    health_framework.print_summary()

    # Exit with appropriate code
    failed_tests = sum(1 for r in all_results if not r.success)
    sys.exit(0 if failed_tests == 0 else 1)
