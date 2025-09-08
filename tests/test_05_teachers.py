#!/usr/bin/env python3
"""
Teacher Endpoint Tests - Protected Endpoints
Tests all teacher management endpoints that require authentication.
"""

import os
import sys
import uuid
from decimal import Decimal

# Add the tests directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api_test_framework import APITestFramework, validate_api_response


def validate_teacher_response(response_data):
    """Validate teacher response structure."""
    if not validate_api_response(response_data):
        return False

    data = response_data.get("data", {})
    if not isinstance(data, dict):
        return False

    # Check for required teacher fields
    required_fields = [
        "id",
        "user_id",
        "first_name",
        "last_name",
        "email",
        "instruments",
        "hourly_rate",
        "max_students",
        "current_students",
        "is_available",
        "created_at",
        "updated_at",
    ]

    for field in required_fields:
        if field not in data:
            return False

    # Validate instruments is a list
    if not isinstance(data.get("instruments"), list):
        return False

    return True


def validate_teacher_list_response(response_data):
    """Validate teacher list response structure."""
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

    # Check teachers array
    if "teachers" not in data:
        return False

    teachers = data["teachers"]
    if not isinstance(teachers, list):
        return False

    # If there are teachers, validate structure
    for teacher in teachers:
        if not isinstance(teacher, dict):
            return False
        required_fields = [
            "id",
            "first_name",
            "last_name",
            "instruments",
            "hourly_rate",
        ]
        for field in required_fields:
            if field not in teacher:
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


def validate_lessons_response(response_data):
    """Validate lessons response structure."""
    if not validate_api_response(response_data):
        return False

    data = response_data.get("data")
    if not isinstance(data, list):
        return False

    # For now, lessons are empty (TODO in implementation)
    return True


def validate_students_response(response_data):
    """Validate students response structure."""
    if not validate_api_response(response_data):
        return False

    data = response_data.get("data")
    if not isinstance(data, list):
        return False

    # For now, students are empty (TODO in implementation)
    return True


def test_teacher_endpoints():
    """Test all teacher management endpoints."""
    framework = APITestFramework()

    print("👨‍🏫 Testing Teacher Management Endpoints")
    print("=" * 60)

    # Authenticate first
    email = os.getenv("TEST_AUTH_EMAIL", "admin@cedarheights.com")
    password = os.getenv("TEST_AUTH_PASSWORD", "admin123")

    if not framework.authenticate(email, password):
        print("❌ Authentication failed - skipping teacher tests")
        return framework

    # Test 1: List teachers (empty initially)
    framework.run_test(
        test_name="List Teachers (Empty)",
        method="GET",
        endpoint="/api/v1/teachers",
        expected_status=200,
        validate_response=validate_teacher_list_response,
    )

    # Test 2: List teachers with pagination
    framework.run_test(
        test_name="List Teachers (With Pagination)",
        method="GET",
        endpoint="/api/v1/teachers",
        params={"page": 1, "limit": 10},
        expected_status=200,
        validate_response=validate_teacher_list_response,
    )

    # Test 3: List teachers with filters
    framework.run_test(
        test_name="List Teachers (With Instrument Filter)",
        method="GET",
        endpoint="/api/v1/teachers",
        params={"instrument": "piano", "is_active": True},
        expected_status=200,
        validate_response=validate_teacher_list_response,
    )

    # Test 4: List teachers with search
    framework.run_test(
        test_name="List Teachers (With Search)",
        method="GET",
        endpoint="/api/v1/teachers",
        params={"search": "test"},
        expected_status=200,
        validate_response=validate_teacher_list_response,
    )

    # Test 5: Create teacher (will fail without valid user_id)
    create_teacher_data = {
        "user_id": 999,  # Non-existent user ID
        "instruments": ["piano", "guitar"],
        "hourly_rate": 125.00,
        "max_students": 30,
        "is_available": True,
        "bio": "Experienced music teacher with 15 years of teaching experience",
        "photo_url": "https://example.com/photos/teacher.jpg",
    }

    framework.run_test(
        test_name="Create Teacher (Invalid User ID)",
        method="POST",
        endpoint="/api/v1/teachers",
        request_data=create_teacher_data,
        expected_status=422,  # Validation error expected
    )

    # Test 6: Create teacher with invalid data
    invalid_teacher_data = {
        "user_id": 1,
        "instruments": [],  # Invalid: empty instruments
        "hourly_rate": -50.00,  # Invalid: negative rate
        "max_students": 0,  # Invalid: zero max students
        "bio": "a" * 1001,  # Invalid: bio too long
    }

    framework.run_test(
        test_name="Create Teacher (Invalid Data)",
        method="POST",
        endpoint="/api/v1/teachers",
        request_data=invalid_teacher_data,
        expected_status=422,  # Validation error expected
    )

    # Test 7: Get non-existent teacher
    fake_teacher_id = str(uuid.uuid4())
    framework.run_test(
        test_name="Get Non-existent Teacher",
        method="GET",
        endpoint=f"/api/v1/teachers/{fake_teacher_id}",
        expected_status=404,
    )

    # Test 8: Update non-existent teacher
    framework.run_test(
        test_name="Update Non-existent Teacher",
        method="PUT",
        endpoint=f"/api/v1/teachers/{fake_teacher_id}",
        request_data={"hourly_rate": 150.00},
        expected_status=404,
    )

    # Test 9: Delete non-existent teacher
    framework.run_test(
        test_name="Delete Non-existent Teacher",
        method="DELETE",
        endpoint=f"/api/v1/teachers/{fake_teacher_id}",
        expected_status=404,
    )

    # Test 10: Activate non-existent teacher
    framework.run_test(
        test_name="Activate Non-existent Teacher",
        method="POST",
        endpoint=f"/api/v1/teachers/{fake_teacher_id}/activate",
        expected_status=404,
    )

    # Test 11: Update availability for non-existent teacher
    availability_data = {
        "start_time": "09:00:00",
        "end_time": "10:00:00",
        "is_active": True,
    }

    framework.run_test(
        test_name="Update Availability (Non-existent Teacher)",
        method="PUT",
        endpoint=f"/api/v1/teachers/{fake_teacher_id}/availability",
        request_data=availability_data,
        expected_status=404,
    )

    # Test 12: Get students for non-existent teacher
    framework.run_test(
        test_name="Get Students for Non-existent Teacher",
        method="GET",
        endpoint=f"/api/v1/teachers/{fake_teacher_id}/students",
        expected_status=404,
    )

    # Test 13: Get lessons for non-existent teacher
    framework.run_test(
        test_name="Get Lessons for Non-existent Teacher",
        method="GET",
        endpoint=f"/api/v1/teachers/{fake_teacher_id}/lessons",
        expected_status=404,
    )

    return framework


def test_teacher_validation_edge_cases():
    """Test edge cases and validation scenarios."""
    framework = APITestFramework()

    print("\n🔍 Testing Teacher Validation Edge Cases")
    print("=" * 60)

    # Authenticate first
    email = os.getenv("TEST_AUTH_EMAIL", "admin@cedarheights.com")
    password = os.getenv("TEST_AUTH_PASSWORD", "admin123")

    if not framework.authenticate(email, password):
        print("❌ Authentication failed - skipping validation tests")
        return framework

    # Test 1: Invalid pagination parameters
    framework.run_test(
        test_name="Invalid Pagination (Page 0)",
        method="GET",
        endpoint="/api/v1/teachers",
        params={"page": 0, "limit": 10},
        expected_status=422,  # Validation error
    )

    framework.run_test(
        test_name="Invalid Pagination (Limit Too High)",
        method="GET",
        endpoint="/api/v1/teachers",
        params={"page": 1, "limit": 200},
        expected_status=422,  # Validation error
    )

    # Test 2: Invalid search parameters
    framework.run_test(
        test_name="Invalid Search (Too Long)",
        method="GET",
        endpoint="/api/v1/teachers",
        params={"search": "a" * 101},  # Too long
        expected_status=422,  # Validation error
    )

    # Test 3: Invalid instrument filter
    framework.run_test(
        test_name="Invalid Instrument Filter",
        method="GET",
        endpoint="/api/v1/teachers",
        params={"instrument": "invalid_instrument"},
        expected_status=422,  # Validation error
    )

    # Test 4: Teacher creation with duplicate instruments
    duplicate_instruments_data = {
        "user_id": 1,
        "instruments": ["piano", "piano"],  # Duplicate instruments
        "hourly_rate": 100.00,
        "max_students": 20,
    }

    framework.run_test(
        test_name="Create Teacher (Duplicate Instruments)",
        method="POST",
        endpoint="/api/v1/teachers",
        request_data=duplicate_instruments_data,
        expected_status=422,  # Validation error
    )

    # Test 5: Teacher creation with invalid max_students
    invalid_max_students_data = {
        "user_id": 1,
        "instruments": ["piano"],
        "hourly_rate": 100.00,
        "max_students": 101,  # Too high
    }

    framework.run_test(
        test_name="Create Teacher (Max Students Too High)",
        method="POST",
        endpoint="/api/v1/teachers",
        request_data=invalid_max_students_data,
        expected_status=422,  # Validation error
    )

    # Test 6: Teacher update with duplicate instruments
    update_duplicate_instruments = {
        "instruments": ["guitar", "guitar"]  # Duplicate instruments
    }

    fake_teacher_id = str(uuid.uuid4())
    framework.run_test(
        test_name="Update Teacher (Duplicate Instruments)",
        method="PUT",
        endpoint=f"/api/v1/teachers/{fake_teacher_id}",
        request_data=update_duplicate_instruments,
        expected_status=404,  # Teacher not found (but would be 422 if teacher existed)
    )

    # Test 7: Invalid availability slot data
    invalid_availability_data = {
        "start_time": "10:00:00",
        "end_time": "09:00:00",  # End time before start time
        "is_active": True,
    }

    framework.run_test(
        test_name="Update Availability (Invalid Time Range)",
        method="PUT",
        endpoint=f"/api/v1/teachers/{fake_teacher_id}/availability",
        request_data=invalid_availability_data,
        expected_status=404,  # Teacher not found (but would be 422 if teacher existed)
    )

    return framework


def test_teacher_endpoints_without_auth():
    """Test teacher endpoints without authentication."""
    framework = APITestFramework()

    print("\n🔒 Testing Teacher Endpoints Without Authentication")
    print("=" * 60)

    # Test 1: List teachers without auth
    framework.run_test(
        test_name="List Teachers (No Auth)",
        method="GET",
        endpoint="/api/v1/teachers",
        expected_status=401,
        require_auth=False,
    )

    # Test 2: Create teacher without auth
    framework.run_test(
        test_name="Create Teacher (No Auth)",
        method="POST",
        endpoint="/api/v1/teachers",
        request_data={"user_id": 1, "instruments": ["piano"]},
        expected_status=401,
        require_auth=False,
    )

    # Test 3: Get teacher without auth
    fake_id = str(uuid.uuid4())
    framework.run_test(
        test_name="Get Teacher (No Auth)",
        method="GET",
        endpoint=f"/api/v1/teachers/{fake_id}",
        expected_status=401,
        require_auth=False,
    )

    # Test 4: Update teacher without auth
    framework.run_test(
        test_name="Update Teacher (No Auth)",
        method="PUT",
        endpoint=f"/api/v1/teachers/{fake_id}",
        request_data={"hourly_rate": 150.00},
        expected_status=401,
        require_auth=False,
    )

    # Test 5: Delete teacher without auth
    framework.run_test(
        test_name="Delete Teacher (No Auth)",
        method="DELETE",
        endpoint=f"/api/v1/teachers/{fake_id}",
        expected_status=401,
        require_auth=False,
    )

    # Test 6: Activate teacher without auth
    framework.run_test(
        test_name="Activate Teacher (No Auth)",
        method="POST",
        endpoint=f"/api/v1/teachers/{fake_id}/activate",
        expected_status=401,
        require_auth=False,
    )

    # Test 7: Update availability without auth
    framework.run_test(
        test_name="Update Availability (No Auth)",
        method="PUT",
        endpoint=f"/api/v1/teachers/{fake_id}/availability",
        request_data={"start_time": "09:00:00", "end_time": "10:00:00"},
        expected_status=401,
        require_auth=False,
    )

    # Test 8: Get teacher students without auth
    framework.run_test(
        test_name="Get Teacher Students (No Auth)",
        method="GET",
        endpoint=f"/api/v1/teachers/{fake_id}/students",
        expected_status=401,
        require_auth=False,
    )

    # Test 9: Get teacher lessons without auth
    framework.run_test(
        test_name="Get Teacher Lessons (No Auth)",
        method="GET",
        endpoint=f"/api/v1/teachers/{fake_id}/lessons",
        expected_status=401,
        require_auth=False,
    )

    return framework


if __name__ == "__main__":
    print("🚀 Cedar Heights Music Academy - Teacher Endpoint Tests")
    print("Testing teacher management endpoints with authentication...")

    # Run all teacher tests
    main_framework = test_teacher_endpoints()
    validation_framework = test_teacher_validation_edge_cases()
    no_auth_framework = test_teacher_endpoints_without_auth()

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
