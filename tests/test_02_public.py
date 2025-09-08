#!/usr/bin/env python3
"""
Public Endpoint Tests - No Authentication Required
These tests verify public endpoints that don't require authentication.
"""

import os
import sys

# Add the tests directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api_test_framework import APITestFramework, validate_api_response


def validate_teachers_response(response_data):
    """Validate public teachers response."""
    if not validate_api_response(response_data):
        return False

    data = response_data.get("data", [])
    if not isinstance(data, list):
        return False

    # If there are teachers, validate structure
    for teacher in data:
        if not isinstance(teacher, dict):
            return False
        required_fields = ["id", "first_name", "last_name", "instruments"]
        for field in required_fields:
            if field not in teacher:
                return False

    return True


def validate_timeslots_response(response_data):
    """Validate public timeslots response."""
    if not validate_api_response(response_data):
        return False

    data = response_data.get("data", [])
    if not isinstance(data, list):
        return False

    # If there are timeslots, validate structure
    for slot in data:
        if not isinstance(slot, dict):
            return False
        required_fields = [
            "id",
            "teacher_id",
            "teacher_name",
            "day_of_week",
            "start_time",
            "end_time",
        ]
        for field in required_fields:
            if field not in slot:
                return False

    return True


def validate_pricing_response(response_data):
    """Validate public pricing response."""
    if not validate_api_response(response_data):
        return False

    data = response_data.get("data", {})
    if not isinstance(data, dict):
        return False

    # Check for pricing array
    if "pricing" not in data:
        return False

    pricing = data["pricing"]
    if not isinstance(pricing, list):
        return False

    # If there are pricing entries, validate structure
    for price in pricing:
        if not isinstance(price, dict):
            return False
        required_fields = ["instrument", "rate_per_lesson", "currency"]
        for field in required_fields:
            if field not in price:
                return False

    return True


def test_public_endpoints():
    """Test all public endpoints."""
    framework = APITestFramework()

    print("🌐 Testing Public Endpoints")
    print("=" * 50)

    # Test 1: Get public teachers
    framework.run_test(
        test_name="Get Public Teachers",
        method="GET",
        endpoint="/api/v1/public/teachers",
        expected_status=200,
        require_auth=False,
        validate_response=validate_teachers_response,
    )

    # Test 2: Get public teachers with instrument filter
    framework.run_test(
        test_name="Get Public Teachers (Piano Filter)",
        method="GET",
        endpoint="/api/v1/public/teachers",
        params={"instrument": "piano"},
        expected_status=200,
        require_auth=False,
        validate_response=validate_teachers_response,
    )

    # Test 3: Get public timeslots
    framework.run_test(
        test_name="Get Public Timeslots",
        method="GET",
        endpoint="/api/v1/public/timeslots",
        expected_status=200,
        require_auth=False,
        validate_response=validate_timeslots_response,
    )

    # Test 4: Get public timeslots with filters
    framework.run_test(
        test_name="Get Public Timeslots (Active Only)",
        method="GET",
        endpoint="/api/v1/public/timeslots",
        params={"active": True},
        expected_status=200,
        require_auth=False,
        validate_response=validate_timeslots_response,
    )

    # Test 5: Get public pricing
    framework.run_test(
        test_name="Get Public Pricing",
        method="GET",
        endpoint="/api/v1/public/pricing",
        expected_status=200,
        require_auth=False,
        validate_response=validate_pricing_response,
    )

    return framework


def test_public_edge_cases():
    """Test edge cases for public endpoints."""
    framework = APITestFramework()

    print("\n🔍 Testing Public Endpoint Edge Cases")
    print("=" * 50)

    # Test 1: Invalid instrument filter
    framework.run_test(
        test_name="Invalid Instrument Filter",
        method="GET",
        endpoint="/api/v1/public/teachers",
        params={"instrument": "invalid_instrument"},
        expected_status=200,  # Should return empty list, not error
        require_auth=False,
        validate_response=validate_teachers_response,
    )

    # Test 2: Invalid weekday filter
    framework.run_test(
        test_name="Invalid Weekday Filter",
        method="GET",
        endpoint="/api/v1/public/timeslots",
        params={"weekday": 99},  # Invalid weekday
        expected_status=200,  # Should return empty list, not error
        require_auth=False,
        validate_response=validate_timeslots_response,
    )

    # Test 3: Multiple filters
    framework.run_test(
        test_name="Multiple Timeslot Filters",
        method="GET",
        endpoint="/api/v1/public/timeslots",
        params={"active": True, "weekday": 1},  # Monday, active only
        expected_status=200,
        require_auth=False,
        validate_response=validate_timeslots_response,
    )

    return framework


if __name__ == "__main__":
    print("🚀 Cedar Heights Music Academy - Public Endpoint Tests")
    print("Testing public endpoints that don't require authentication...")

    # Run public endpoint tests
    public_framework = test_public_endpoints()
    edge_case_framework = test_public_edge_cases()

    # Combine results
    all_results = public_framework.results + edge_case_framework.results
    public_framework.results = all_results

    # Print summary
    public_framework.print_summary()

    # Exit with appropriate code
    failed_tests = sum(1 for r in all_results if not r.success)
    sys.exit(0 if failed_tests == 0 else 1)
