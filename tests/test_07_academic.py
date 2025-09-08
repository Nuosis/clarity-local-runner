#!/usr/bin/env python3
"""
Academic Calendar Endpoint Tests - Protected Endpoints
Tests all academic calendar management endpoints that require authentication.
"""

import os
import sys
from datetime import date, timedelta

# Add the tests directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api_test_framework import APITestFramework, validate_api_response


def validate_academic_years_response(response_data):
    """Validate academic years list response structure."""
    if not validate_api_response(response_data):
        return False

    data = response_data.get("data")
    if not isinstance(data, list):
        return False

    # If there are academic years, validate structure
    for year in data:
        if not isinstance(year, dict):
            return False
        required_fields = [
            "id",
            "name",
            "start_date",
            "end_date",
            "is_current",
            "created_at",
        ]
        for field in required_fields:
            if field not in year:
                return False

    return True


def validate_academic_year_response(response_data):
    """Validate single academic year response structure."""
    if not validate_api_response(response_data):
        return False

    data = response_data.get("data", {})
    if not isinstance(data, dict):
        return False

    # Check for required academic year fields
    required_fields = [
        "id",
        "name",
        "start_date",
        "end_date",
        "is_current",
        "created_at",
    ]

    for field in required_fields:
        if field not in data:
            return False

    return True


def validate_semesters_response(response_data):
    """Validate semesters list response structure."""
    if not validate_api_response(response_data):
        return False

    data = response_data.get("data")
    if not isinstance(data, list):
        return False

    # If there are semesters, validate structure
    for semester in data:
        if not isinstance(semester, dict):
            return False
        required_fields = [
            "id",
            "academic_year_id",
            "name",
            "start_date",
            "end_date",
            "is_current",
            "makeup_weeks",
            "created_at",
        ]
        for field in required_fields:
            if field not in semester:
                return False

        # Validate makeup_weeks structure
        makeup_weeks = semester.get("makeup_weeks", [])
        if not isinstance(makeup_weeks, list):
            return False

        for week in makeup_weeks:
            if not isinstance(week, dict):
                return False
            week_fields = ["id", "name", "start_date", "end_date", "is_active"]
            for field in week_fields:
                if field not in week:
                    return False

    return True


def test_academic_years_endpoints():
    """Test academic years management endpoints."""
    framework = APITestFramework()

    print("📅 Testing Academic Years Management Endpoints")
    print("=" * 60)

    # Authenticate first
    email = os.getenv("TEST_AUTH_EMAIL")
    password = os.getenv("TEST_AUTH_PASSWORD")

    if not email or not password:
        print(
            "❌ Authentication failed: TEST_AUTH_EMAIL and TEST_AUTH_PASSWORD environment variables not set"
        )
        print("❌ Authentication failed - skipping academic years tests")
        return framework

    if not framework.authenticate(email, password):
        print("❌ Authentication failed - skipping academic years tests")
        return framework

    # Test 1: List academic years (empty initially)
    framework.run_test(
        test_name="List Academic Years (Empty)",
        method="GET",
        endpoint="/api/v1/academic/years",
        expected_status=200,
        validate_response=validate_academic_years_response,
    )

    # Test 2: Create academic year with valid data
    current_year = date.today().year
    create_year_data = {
        "name": f"Academic Year {current_year}-{current_year + 1}",
        "start_date": f"{current_year}-09-01",
        "end_date": f"{current_year + 1}-06-30",
        "is_current": True,
    }

    framework.run_test(
        test_name="Create Academic Year (Valid Data)",
        method="POST",
        endpoint="/api/v1/academic/years",
        request_data=create_year_data,
        expected_status=200,
        validate_response=validate_academic_year_response,
    )

    # Test 3: Create academic year with invalid data
    invalid_year_data = {
        "name": "",  # Invalid: empty name
        "start_date": f"{current_year + 1}-09-01",  # Invalid: start after end
        "end_date": f"{current_year}-06-30",
        "is_current": False,
    }

    framework.run_test(
        test_name="Create Academic Year (Invalid Data)",
        method="POST",
        endpoint="/api/v1/academic/years",
        request_data=invalid_year_data,
        expected_status=[400, 422],  # Validation error expected
    )

    # Test 4: Create academic year with missing required fields
    incomplete_year_data = {
        "name": "Incomplete Year",
        # Missing start_date and end_date
    }

    framework.run_test(
        test_name="Create Academic Year (Missing Fields)",
        method="POST",
        endpoint="/api/v1/academic/years",
        request_data=incomplete_year_data,
        expected_status=422,  # Validation error expected
    )

    return framework


def test_semesters_endpoints():
    """Test semesters management endpoints."""
    framework = APITestFramework()

    print("\n📚 Testing Semesters Management Endpoints")
    print("=" * 60)

    # Authenticate first
    email = os.getenv("TEST_AUTH_EMAIL")
    password = os.getenv("TEST_AUTH_PASSWORD")

    if not email or not password:
        print(
            "❌ Authentication failed: TEST_AUTH_EMAIL and TEST_AUTH_PASSWORD environment variables not set"
        )
        print("❌ Authentication failed - skipping semesters tests")
        return framework

    if not framework.authenticate(email, password):
        print("❌ Authentication failed - skipping semesters tests")
        return framework

    # Test 1: List semesters (empty initially)
    framework.run_test(
        test_name="List Semesters (Empty)",
        method="GET",
        endpoint="/api/v1/academic/semesters",
        expected_status=200,
        validate_response=validate_semesters_response,
    )

    # Test 2: List semesters with academic year filter
    framework.run_test(
        test_name="List Semesters (Academic Year Filter)",
        method="GET",
        endpoint="/api/v1/academic/semesters",
        params={"academic_year_id": 1},
        expected_status=200,
        validate_response=validate_semesters_response,
    )

    # Test 3: List semesters with current filter
    framework.run_test(
        test_name="List Semesters (Current Only)",
        method="GET",
        endpoint="/api/v1/academic/semesters",
        params={"is_current": True},
        expected_status=200,
        validate_response=validate_semesters_response,
    )

    # Test 4: List semesters with multiple filters
    framework.run_test(
        test_name="List Semesters (Multiple Filters)",
        method="GET",
        endpoint="/api/v1/academic/semesters",
        params={"academic_year_id": 1, "is_current": False},
        expected_status=200,
        validate_response=validate_semesters_response,
    )

    # Test 5: Create semester (will fail without valid academic year)
    current_year = date.today().year
    create_semester_data = {
        "academic_year_id": 999,  # Non-existent academic year
        "name": f"Fall {current_year}",
        "start_date": f"{current_year}-09-01",
        "end_date": f"{current_year}-12-15",
        "is_current": True,
    }

    framework.run_test(
        test_name="Create Semester (Invalid Academic Year)",
        method="POST",
        endpoint="/api/v1/academic/semesters",
        request_data=create_semester_data,
        expected_status=[400, 422],  # Validation error expected
    )

    return framework


def test_academic_validation_edge_cases():
    """Test edge cases and validation scenarios."""
    framework = APITestFramework()

    print("\n🔍 Testing Academic Calendar Validation Edge Cases")
    print("=" * 60)

    # Authenticate first
    email = os.getenv("TEST_AUTH_EMAIL")
    password = os.getenv("TEST_AUTH_PASSWORD")

    if not email or not password:
        print(
            "❌ Authentication failed: TEST_AUTH_EMAIL and TEST_AUTH_PASSWORD environment variables not set"
        )
        print("❌ Authentication failed - skipping validation tests")
        return framework

    if not framework.authenticate(email, password):
        print("❌ Authentication failed - skipping validation tests")
        return framework

    # Test 1: Create academic year with dates in wrong order
    current_year = date.today().year
    wrong_order_data = {
        "name": "Wrong Order Year",
        "start_date": f"{current_year}-12-31",  # Start after end
        "end_date": f"{current_year}-01-01",
        "is_current": False,
    }

    framework.run_test(
        test_name="Create Academic Year (Wrong Date Order)",
        method="POST",
        endpoint="/api/v1/academic/years",
        request_data=wrong_order_data,
        expected_status=[400, 422],  # Validation error expected
    )

    # Test 2: Create academic year with very long name
    long_name_data = {
        "name": "A" * 256,  # Very long name
        "start_date": f"{current_year}-09-01",
        "end_date": f"{current_year + 1}-06-30",
        "is_current": False,
    }

    framework.run_test(
        test_name="Create Academic Year (Long Name)",
        method="POST",
        endpoint="/api/v1/academic/years",
        request_data=long_name_data,
        expected_status=[400, 422],  # Validation error expected
    )

    # Test 3: Create semester with invalid date range
    invalid_semester_data = {
        "academic_year_id": 1,
        "name": "Invalid Semester",
        "start_date": f"{current_year}-12-31",  # Start after end
        "end_date": f"{current_year}-09-01",
        "is_current": False,
    }

    framework.run_test(
        test_name="Create Semester (Invalid Date Range)",
        method="POST",
        endpoint="/api/v1/academic/semesters",
        request_data=invalid_semester_data,
        expected_status=[400, 422],  # Validation error expected
    )

    # Test 4: List semesters with invalid academic year ID
    framework.run_test(
        test_name="List Semesters (Invalid Academic Year ID)",
        method="GET",
        endpoint="/api/v1/academic/semesters",
        params={"academic_year_id": -1},
        expected_status=200,  # Should return empty list, not error
        validate_response=validate_semesters_response,
    )

    return framework


def test_academic_endpoints_without_auth():
    """Test academic endpoints without authentication."""
    framework = APITestFramework()

    print("\n🔒 Testing Academic Endpoints Without Authentication")
    print("=" * 60)

    # Test 1: List academic years without auth
    framework.run_test(
        test_name="List Academic Years (No Auth)",
        method="GET",
        endpoint="/api/v1/academic/years",
        expected_status=401,
        require_auth=False,
    )

    # Test 2: Create academic year without auth
    framework.run_test(
        test_name="Create Academic Year (No Auth)",
        method="POST",
        endpoint="/api/v1/academic/years",
        request_data={"name": "Test Year"},
        expected_status=401,
        require_auth=False,
    )

    # Test 3: List semesters without auth
    framework.run_test(
        test_name="List Semesters (No Auth)",
        method="GET",
        endpoint="/api/v1/academic/semesters",
        expected_status=401,
        require_auth=False,
    )

    # Test 4: Create semester without auth
    framework.run_test(
        test_name="Create Semester (No Auth)",
        method="POST",
        endpoint="/api/v1/academic/semesters",
        request_data={"name": "Test Semester"},
        expected_status=401,
        require_auth=False,
    )

    return framework


def test_academic_non_admin_access():
    """Test academic endpoints with non-admin user."""
    framework = APITestFramework()

    print("\n👤 Testing Academic Endpoints with Non-Admin User")
    print("=" * 60)

    # Try to authenticate with non-admin credentials if available
    teacher_email = os.getenv("TEST_TEACHER_EMAIL", "teacher@cedarheights.com")
    teacher_password = os.getenv("TEST_TEACHER_PASSWORD", "teacher123")

    # Note: This might fail if teacher credentials don't exist
    if framework.authenticate(teacher_email, teacher_password):
        # Test 1: List academic years as non-admin (should work - read access)
        framework.run_test(
            test_name="List Academic Years (Non-Admin)",
            method="GET",
            endpoint="/api/v1/academic/years",
            expected_status=200,
            validate_response=validate_academic_years_response,
        )

        # Test 2: Try to create academic year as non-admin (should fail)
        framework.run_test(
            test_name="Create Academic Year (Non-Admin)",
            method="POST",
            endpoint="/api/v1/academic/years",
            request_data={"name": "Test Year"},
            expected_status=403,  # Forbidden - requires admin
        )

        # Test 3: List semesters as non-admin (should work - read access)
        framework.run_test(
            test_name="List Semesters (Non-Admin)",
            method="GET",
            endpoint="/api/v1/academic/semesters",
            expected_status=200,
            validate_response=validate_semesters_response,
        )

        # Test 4: Try to create semester as non-admin (should fail)
        framework.run_test(
            test_name="Create Semester (Non-Admin)",
            method="POST",
            endpoint="/api/v1/academic/semesters",
            request_data={"name": "Test Semester"},
            expected_status=403,  # Forbidden - requires admin
        )
    else:
        print("⚠️  Non-admin credentials not available, skipping non-admin tests")

    return framework


if __name__ == "__main__":
    print("🚀 Cedar Heights Music Academy - Academic Calendar Endpoint Tests")
    print("Testing academic calendar management endpoints with authentication...")

    # Run all academic tests
    years_framework = test_academic_years_endpoints()
    semesters_framework = test_semesters_endpoints()
    validation_framework = test_academic_validation_edge_cases()
    no_auth_framework = test_academic_endpoints_without_auth()
    non_admin_framework = test_academic_non_admin_access()

    # Combine results
    all_results = (
        years_framework.results
        + semesters_framework.results
        + validation_framework.results
        + no_auth_framework.results
        + non_admin_framework.results
    )
    years_framework.results = all_results

    # Print summary
    years_framework.print_summary()

    # Exit with appropriate code
    failed_tests = sum(1 for r in all_results if not r.success)
    sys.exit(0 if failed_tests == 0 else 1)
