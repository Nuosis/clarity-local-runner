#!/usr/bin/env python3
"""
Student Endpoint Tests - Protected Endpoints
Tests all student management endpoints that require authentication.
"""

import os
import sys
import uuid
from datetime import date, timedelta

# Add the tests directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api_test_framework import APITestFramework, validate_api_response


def validate_student_response(response_data):
    """Validate student response structure."""
    if not validate_api_response(response_data):
        return False

    data = response_data.get("data", {})
    if not isinstance(data, dict):
        return False

    # Check for required student fields
    required_fields = [
        "id",
        "first_name",
        "last_name",
        "date_of_birth",
        "instrument",
        "skill_level",
        "lesson_rate",
        "enrollment_date",
        "is_active",
        "created_at",
        "updated_at",
    ]

    for field in required_fields:
        if field not in data:
            return False

    return True


def validate_student_list_response(response_data):
    """Validate student list response structure."""
    if not validate_api_response(response_data):
        return False

    data = response_data.get("data", {})
    if not isinstance(data, dict):
        return False

    # Check for pagination structure
    if "pagination" not in data:
        return False

    pagination = data["pagination"]
    required_pagination_fields = [
        "page",
        "limit",
        "total",
        "pages",
        "has_next",
        "has_prev",
    ]
    for field in required_pagination_fields:
        if field not in pagination:
            return False

    # Check students array
    if "students" not in data:
        return False

    students = data["students"]
    if not isinstance(students, list):
        return False

    # If there are students, validate structure
    for student in students:
        if not isinstance(student, dict):
            return False
        required_fields = ["id", "first_name", "last_name", "instrument", "skill_level"]
        for field in required_fields:
            if field not in student:
                return False

    return True


def validate_delete_response(response_data):
    """Validate delete response structure."""
    if not validate_api_response(response_data):
        return False

    data = response_data.get("data", {})
    if not isinstance(data, dict):
        return False

    required_fields = ["id", "deleted"]
    for field in required_fields:
        if field not in data:
            return False

    return data.get("deleted") is True


def test_student_endpoints():
    """Test all student management endpoints."""
    framework = APITestFramework()

    print("👨‍🎓 Testing Student Management Endpoints")
    print("=" * 60)

    # Authenticate first
    email = os.getenv("TEST_AUTH_EMAIL")
    password = os.getenv("TEST_AUTH_PASSWORD")

    if not email or not password:
        print(
            "❌ Authentication failed: TEST_AUTH_EMAIL and TEST_AUTH_PASSWORD environment variables not set"
        )
        print("❌ Authentication failed - skipping student tests")
        return framework

    if not framework.authenticate(email, password):
        print("❌ Authentication failed - skipping student tests")
        return framework

    # Test 1: List students (empty initially)
    framework.run_test(
        test_name="List Students (Empty)",
        method="GET",
        endpoint="/api/v1/students",
        expected_status=200,
        validate_response=validate_student_list_response,
    )

    # Test 2: List students with pagination
    framework.run_test(
        test_name="List Students (With Pagination)",
        method="GET",
        endpoint="/api/v1/students",
        params={"page": 1, "limit": 10},
        expected_status=200,
        validate_response=validate_student_list_response,
    )

    # Test 3: List students with filters
    framework.run_test(
        test_name="List Students (With Instrument Filter)",
        method="GET",
        endpoint="/api/v1/students",
        params={"instrument": "piano", "is_active": True},
        expected_status=200,
        validate_response=validate_student_list_response,
    )

    # Test 4: List students with search
    framework.run_test(
        test_name="List Students (With Search)",
        method="GET",
        endpoint="/api/v1/students",
        params={"search": "test"},
        expected_status=200,
        validate_response=validate_student_list_response,
    )

    # Test 5: Create student (will fail without valid parent_id)
    create_student_data = {
        "first_name": "Emma",
        "last_name": "Johnson",
        "email": "emma.johnson@example.com",
        "date_of_birth": (
            date.today() - timedelta(days=365 * 8)
        ).isoformat(),  # 8 years old
        "instrument": "piano",
        "skill_level": "beginner",
        "lesson_rate": 125.00,
        "enrollment_date": date.today().isoformat(),
        "parent_id": 999,  # Non-existent parent ID
        "notes": "Enthusiastic beginner student",
    }

    framework.run_test(
        test_name="Create Student (Invalid Parent ID)",
        method="POST",
        endpoint="/api/v1/students",
        request_data=create_student_data,
        expected_status=422,  # Validation error expected
    )

    # Test 6: Create student with invalid data
    invalid_student_data = {
        "first_name": "",  # Invalid: empty name
        "last_name": "Johnson",
        "date_of_birth": date.today().isoformat(),  # Invalid: too young
        "instrument": "piano",
        "skill_level": "beginner",
        "lesson_rate": -50.00,  # Invalid: negative rate
        "enrollment_date": date.today().isoformat(),
        "parent_id": 1,
    }

    framework.run_test(
        test_name="Create Student (Invalid Data)",
        method="POST",
        endpoint="/api/v1/students",
        request_data=invalid_student_data,
        expected_status=422,  # Validation error expected
    )

    # Test 7: Get non-existent student
    fake_student_id = str(uuid.uuid4())
    framework.run_test(
        test_name="Get Non-existent Student",
        method="GET",
        endpoint=f"/api/v1/students/{fake_student_id}",
        expected_status=404,
    )

    # Test 8: Update non-existent student
    framework.run_test(
        test_name="Update Non-existent Student",
        method="PUT",
        endpoint=f"/api/v1/students/{fake_student_id}",
        request_data={"skill_level": "intermediate"},
        expected_status=404,
    )

    # Test 9: Delete non-existent student
    framework.run_test(
        test_name="Delete Non-existent Student",
        method="DELETE",
        endpoint=f"/api/v1/students/{fake_student_id}",
        expected_status=404,
    )

    # Test 10: Activate non-existent student
    framework.run_test(
        test_name="Activate Non-existent Student",
        method="POST",
        endpoint=f"/api/v1/students/{fake_student_id}/activate",
        expected_status=404,
    )

    # Test 11: Get lessons for non-existent student
    framework.run_test(
        test_name="Get Lessons for Non-existent Student",
        method="GET",
        endpoint=f"/api/v1/students/{fake_student_id}/lessons",
        expected_status=404,
    )

    return framework


def test_student_validation_edge_cases():
    """Test edge cases and validation scenarios."""
    framework = APITestFramework()

    print("\n🔍 Testing Student Validation Edge Cases")
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

    # Test 1: Invalid pagination parameters
    framework.run_test(
        test_name="Invalid Pagination (Page 0)",
        method="GET",
        endpoint="/api/v1/students",
        params={"page": 0, "limit": 10},
        expected_status=422,  # Validation error
    )

    framework.run_test(
        test_name="Invalid Pagination (Limit Too High)",
        method="GET",
        endpoint="/api/v1/students",
        params={"page": 1, "limit": 200},
        expected_status=422,  # Validation error
    )

    # Test 2: Invalid search parameters
    framework.run_test(
        test_name="Invalid Search (Too Long)",
        method="GET",
        endpoint="/api/v1/students",
        params={"search": "a" * 101},  # Too long
        expected_status=422,  # Validation error
    )

    # Test 3: Invalid instrument filter
    framework.run_test(
        test_name="Invalid Instrument Filter",
        method="GET",
        endpoint="/api/v1/students",
        params={"instrument": "invalid_instrument"},
        expected_status=422,  # Validation error
    )

    # Test 4: Student creation with duplicate email (if any exist)
    duplicate_email_data = {
        "first_name": "Test",
        "last_name": "Student",
        "email": "duplicate@example.com",
        "date_of_birth": (date.today() - timedelta(days=365 * 10)).isoformat(),
        "instrument": "piano",
        "skill_level": "beginner",
        "lesson_rate": 100.00,
        "enrollment_date": date.today().isoformat(),
        "parent_id": 1,
    }

    # First attempt (might succeed if no existing student)
    framework.run_test(
        test_name="Create Student (First Attempt)",
        method="POST",
        endpoint="/api/v1/students",
        request_data=duplicate_email_data,
        expected_status=[201, 422],  # Either created or validation error
    )

    # Second attempt (should fail if first succeeded)
    framework.run_test(
        test_name="Create Student (Duplicate Email)",
        method="POST",
        endpoint="/api/v1/students",
        request_data=duplicate_email_data,
        expected_status=422,  # Validation error expected
    )

    # Test 5: Age validation edge cases
    too_young_data = duplicate_email_data.copy()
    too_young_data["email"] = "tooyoung@example.com"
    too_young_data["date_of_birth"] = (
        date.today() - timedelta(days=365 * 3)
    ).isoformat()  # 3 years old

    framework.run_test(
        test_name="Create Student (Too Young)",
        method="POST",
        endpoint="/api/v1/students",
        request_data=too_young_data,
        expected_status=422,  # Validation error
    )

    return framework


def test_student_endpoints_without_auth():
    """Test student endpoints without authentication."""
    framework = APITestFramework()

    print("\n🔒 Testing Student Endpoints Without Authentication")
    print("=" * 60)

    # Test 1: List students without auth
    framework.run_test(
        test_name="List Students (No Auth)",
        method="GET",
        endpoint="/api/v1/students",
        expected_status=401,
        require_auth=False,
    )

    # Test 2: Create student without auth
    framework.run_test(
        test_name="Create Student (No Auth)",
        method="POST",
        endpoint="/api/v1/students",
        request_data={"first_name": "Test"},
        expected_status=401,
        require_auth=False,
    )

    # Test 3: Get student without auth
    fake_id = str(uuid.uuid4())
    framework.run_test(
        test_name="Get Student (No Auth)",
        method="GET",
        endpoint=f"/api/v1/students/{fake_id}",
        expected_status=401,
        require_auth=False,
    )

    return framework


if __name__ == "__main__":
    print("🚀 Cedar Heights Music Academy - Student Endpoint Tests")
    print("Testing student management endpoints with authentication...")

    # Run all student tests
    main_framework = test_student_endpoints()
    validation_framework = test_student_validation_edge_cases()
    no_auth_framework = test_student_endpoints_without_auth()

    # Combine results
    all_results = (
        main_framework.results
        + validation_framework.results
        + no_auth_framework.results
    )
    main_framework.results = all_results

    # Print summary
    main_framework.print_summary()

    # Exit with appropriate code
    failed_tests = sum(1 for r in all_results if not r.success)
    sys.exit(0 if failed_tests == 0 else 1)
