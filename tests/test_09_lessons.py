#!/usr/bin/env python3
"""
Lesson Management Endpoint Tests - Protected Endpoints
Tests all lesson management endpoints that require authentication.
"""

import os
import sys
import uuid
from datetime import date, datetime, timedelta

# Add the tests directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api_test_framework import APITestFramework, validate_api_response


def validate_lesson_response(response_data):
    """Validate lesson response structure."""
    if not validate_api_response(response_data):
        return False

    data = response_data.get("data", {})
    if not isinstance(data, dict):
        return False

    # Check for required lesson fields
    required_fields = [
        "id",
        "student_id",
        "teacher_id",
        "scheduled_at",
        "duration_minutes",
        "lesson_type",
        "status",
        "payment_status",
        "attendance_marked",
        "teacher_notes",
        "student_progress_notes",
        "timeslot_id",
        "semester_id",
        "created_at",
        "updated_at",
    ]

    for field in required_fields:
        if field not in data:
            return False

    return True


def validate_lesson_list_response(response_data):
    """Validate lesson list response structure."""
    if not validate_api_response(response_data):
        return False

    data = response_data.get("data", {})
    if not isinstance(data, dict):
        return False

    # Check for required list structure
    required_fields = ["lessons", "pagination"]
    for field in required_fields:
        if field not in data:
            return False

    # Validate lessons array
    lessons = data.get("lessons", [])
    if not isinstance(lessons, list):
        return False

    # If there are lessons, validate structure
    for lesson in lessons:
        if not isinstance(lesson, dict):
            return False
        lesson_fields = [
            "id",
            "student_id",
            "student_name",
            "teacher_id",
            "teacher_name",
            "scheduled_at",
            "duration_minutes",
            "lesson_type",
            "status",
            "payment_status",
            "attendance_marked",
            "timeslot_id",
            "semester_id",
            "created_at",
        ]
        for field in lesson_fields:
            if field not in lesson:
                return False

    # Validate pagination object
    pagination = data.get("pagination", {})
    if not isinstance(pagination, dict):
        return False

    pagination_fields = ["page", "limit", "total", "pages", "has_next", "has_prev"]
    for field in pagination_fields:
        if field not in pagination:
            return False

    return True


def validate_conflict_check_response(response_data):
    """Validate conflict check response structure."""
    if not validate_api_response(response_data):
        return False

    data = response_data.get("data", {})
    if not isinstance(data, dict):
        return False

    # Check for required conflict check fields
    required_fields = ["has_conflicts", "conflicts", "available", "suggested_times"]
    for field in required_fields:
        if field not in data:
            return False

    # Validate conflicts array
    conflicts = data.get("conflicts", [])
    if not isinstance(conflicts, list):
        return False

    # Validate suggested_times array
    suggested_times = data.get("suggested_times", [])
    if not isinstance(suggested_times, list):
        return False

    return True


def validate_schedule_response(response_data):
    """Validate schedule response structure."""
    if not validate_api_response(response_data):
        return False

    data = response_data.get("data", {})
    if not isinstance(data, dict):
        return False

    # Check for required schedule fields
    required_fields = ["view", "date_range", "schedule", "teachers"]
    for field in required_fields:
        if field not in data:
            return False

    # Validate date_range object
    date_range = data.get("date_range", {})
    if not isinstance(date_range, dict):
        return False

    date_range_fields = ["start", "end"]
    for field in date_range_fields:
        if field not in date_range:
            return False

    # Validate schedule and teachers arrays
    schedule = data.get("schedule", [])
    teachers = data.get("teachers", [])
    if not isinstance(schedule, list) or not isinstance(teachers, list):
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


def test_lesson_endpoints():
    """Test all lesson management endpoints."""
    framework = APITestFramework()

    print("📚 Testing Lesson Management Endpoints")
    print("=" * 60)

    # Authenticate first
    email = os.getenv("TEST_AUTH_EMAIL")
    password = os.getenv("TEST_AUTH_PASSWORD")

    if not email or not password:
        print(
            "❌ Authentication failed: TEST_AUTH_EMAIL and TEST_AUTH_PASSWORD environment variables not set"
        )
        print("❌ Authentication failed - skipping lesson tests")
        return framework

    if not framework.authenticate(email, password):
        print("❌ Authentication failed - skipping lesson tests")
        return framework

    # Test 1: List lessons (empty initially)
    framework.run_test(
        test_name="List Lessons (Empty)",
        method="GET",
        endpoint="/api/v1/lessons",
        expected_status=200,
        validate_response=validate_lesson_list_response,
    )

    # Test 2: List lessons with pagination
    framework.run_test(
        test_name="List Lessons (With Pagination)",
        method="GET",
        endpoint="/api/v1/lessons",
        params={"page": 1, "limit": 10},
        expected_status=200,
        validate_response=validate_lesson_list_response,
    )

    # Test 3: List lessons with filters
    framework.run_test(
        test_name="List Lessons (With Filters)",
        method="GET",
        endpoint="/api/v1/lessons",
        params={"student_id": 1, "teacher_id": 1, "status": "scheduled"},
        expected_status=200,
        validate_response=validate_lesson_list_response,
    )

    # Test 4: List lessons with date range
    today = date.today()
    next_week = today + timedelta(days=7)
    framework.run_test(
        test_name="List Lessons (Date Range)",
        method="GET",
        endpoint="/api/v1/lessons",
        params={
            "date_from": today.isoformat(),
            "date_to": next_week.isoformat(),
        },
        expected_status=200,
        validate_response=validate_lesson_list_response,
    )

    # Test 5: List lessons with notes included
    framework.run_test(
        test_name="List Lessons (Include Notes)",
        method="GET",
        endpoint="/api/v1/lessons",
        params={"include_notes": True},
        expected_status=200,
        validate_response=validate_lesson_list_response,
    )

    # Test 6: Create lesson (will fail without valid student/teacher IDs)
    future_time = datetime.now() + timedelta(days=1)
    create_lesson_data = {
        "student_id": 999,  # Non-existent student ID
        "teacher_id": 999,  # Non-existent teacher ID
        "scheduled_at": future_time.isoformat(),
        "duration_minutes": 30,
        "lesson_type": "regular",
        "timeslot_id": 1,
        "semester_id": 1,
        "teacher_notes": "Test lesson creation",
    }

    framework.run_test(
        test_name="Create Lesson (Invalid Student/Teacher)",
        method="POST",
        endpoint="/api/v1/lessons",
        request_data=create_lesson_data,
        expected_status=[400, 404],  # Not found expected
    )

    # Test 7: Create lesson with invalid data
    invalid_lesson_data = {
        "student_id": 1,
        "teacher_id": 1,
        "scheduled_at": "invalid_datetime",  # Invalid datetime
        "duration_minutes": -30,  # Invalid: negative duration
        "lesson_type": "invalid_type",  # Invalid lesson type
    }

    framework.run_test(
        test_name="Create Lesson (Invalid Data)",
        method="POST",
        endpoint="/api/v1/lessons",
        request_data=invalid_lesson_data,
        expected_status=422,  # Validation error expected
    )

    # Test 8: Get non-existent lesson
    fake_lesson_id = str(uuid.uuid4())
    framework.run_test(
        test_name="Get Non-existent Lesson",
        method="GET",
        endpoint=f"/api/v1/lessons/{fake_lesson_id}",
        expected_status=404,
    )

    # Test 9: Update non-existent lesson
    framework.run_test(
        test_name="Update Non-existent Lesson",
        method="PUT",
        endpoint=f"/api/v1/lessons/{fake_lesson_id}",
        request_data={"teacher_notes": "Updated notes"},
        expected_status=404,
    )

    # Test 10: Delete non-existent lesson
    framework.run_test(
        test_name="Delete Non-existent Lesson",
        method="DELETE",
        endpoint=f"/api/v1/lessons/{fake_lesson_id}",
        expected_status=404,
    )

    # Test 11: Cancel non-existent lesson
    framework.run_test(
        test_name="Cancel Non-existent Lesson",
        method="POST",
        endpoint=f"/api/v1/lessons/{fake_lesson_id}/cancel",
        request_data={
            "cancellation_reason": "Test cancellation",
            "notify_parent": True,
            "offer_makeup": False,
        },
        expected_status=404,
    )

    # Test 12: Complete non-existent lesson
    framework.run_test(
        test_name="Complete Non-existent Lesson",
        method="POST",
        endpoint=f"/api/v1/lessons/{fake_lesson_id}/complete",
        expected_status=404,
    )

    return framework


def test_lesson_conflict_checking():
    """Test lesson conflict checking endpoints."""
    framework = APITestFramework()

    print("\n⚠️ Testing Lesson Conflict Checking")
    print("=" * 60)

    # Authenticate first
    email = os.getenv("TEST_AUTH_EMAIL")
    password = os.getenv("TEST_AUTH_PASSWORD")

    if not email or not password:
        print(
            "❌ Authentication failed: TEST_AUTH_EMAIL and TEST_AUTH_PASSWORD environment variables not set"
        )
        print("❌ Authentication failed - skipping conflict tests")
        return framework

    if not framework.authenticate(email, password):
        print("❌ Authentication failed - skipping conflict tests")
        return framework

    # Test 1: Check conflicts for valid time slot
    future_time = datetime.now() + timedelta(days=1)
    conflict_check_data = {
        "teacher_id": 1,
        "scheduled_at": future_time.isoformat(),
        "duration_minutes": 30,
        "exclude_lesson_id": None,
    }

    framework.run_test(
        test_name="Check Conflicts (Valid Time)",
        method="POST",
        endpoint="/api/v1/lessons/check-conflicts",
        request_data=conflict_check_data,
        expected_status=200,
        validate_response=validate_conflict_check_response,
    )

    # Test 2: Check conflicts with invalid teacher ID
    invalid_conflict_data = {
        "teacher_id": 999,  # Non-existent teacher
        "scheduled_at": future_time.isoformat(),
        "duration_minutes": 30,
    }

    framework.run_test(
        test_name="Check Conflicts (Invalid Teacher)",
        method="POST",
        endpoint="/api/v1/lessons/check-conflicts",
        request_data=invalid_conflict_data,
        expected_status=200,  # Should still work, just return no conflicts
        validate_response=validate_conflict_check_response,
    )

    # Test 3: Check conflicts with invalid data
    invalid_conflict_data = {
        "teacher_id": 1,
        "scheduled_at": "invalid_datetime",  # Invalid datetime
        "duration_minutes": -30,  # Invalid duration
    }

    framework.run_test(
        test_name="Check Conflicts (Invalid Data)",
        method="POST",
        endpoint="/api/v1/lessons/check-conflicts",
        request_data=invalid_conflict_data,
        expected_status=422,  # Validation error expected
    )

    return framework


def test_lesson_schedule_view():
    """Test lesson schedule view endpoints."""
    framework = APITestFramework()

    print("\n📅 Testing Lesson Schedule View")
    print("=" * 60)

    # Authenticate first
    email = os.getenv("TEST_AUTH_EMAIL")
    password = os.getenv("TEST_AUTH_PASSWORD")

    if not email or not password:
        print(
            "❌ Authentication failed: TEST_AUTH_EMAIL and TEST_AUTH_PASSWORD environment variables not set"
        )
        print("❌ Authentication failed - skipping schedule tests")
        return framework

    if not framework.authenticate(email, password):
        print("❌ Authentication failed - skipping schedule tests")
        return framework

    # Test 1: Get week schedule view
    framework.run_test(
        test_name="Get Schedule View (Week)",
        method="GET",
        endpoint="/api/v1/lessons/schedule/view",
        params={"view": "week"},
        expected_status=200,
        validate_response=validate_schedule_response,
    )

    # Test 2: Get day schedule view
    today = date.today()
    framework.run_test(
        test_name="Get Schedule View (Day)",
        method="GET",
        endpoint="/api/v1/lessons/schedule/view",
        params={"view": "day", "schedule_date": today.isoformat()},
        expected_status=200,
        validate_response=validate_schedule_response,
    )

    # Test 3: Get month schedule view
    framework.run_test(
        test_name="Get Schedule View (Month)",
        method="GET",
        endpoint="/api/v1/lessons/schedule/view",
        params={"view": "month", "schedule_date": today.isoformat()},
        expected_status=200,
        validate_response=validate_schedule_response,
    )

    # Test 4: Get schedule view with teacher filter
    framework.run_test(
        test_name="Get Schedule View (Teacher Filter)",
        method="GET",
        endpoint="/api/v1/lessons/schedule/view",
        params={"view": "week", "teacher_id": 1},
        expected_status=200,
        validate_response=validate_schedule_response,
    )

    # Test 5: Get schedule view with student filter
    framework.run_test(
        test_name="Get Schedule View (Student Filter)",
        method="GET",
        endpoint="/api/v1/lessons/schedule/view",
        params={"view": "week", "student_id": 1},
        expected_status=200,
        validate_response=validate_schedule_response,
    )

    # Test 6: Get schedule view with invalid view type
    framework.run_test(
        test_name="Get Schedule View (Invalid View)",
        method="GET",
        endpoint="/api/v1/lessons/schedule/view",
        params={"view": "invalid_view"},
        expected_status=200,  # Should default to valid view
        validate_response=validate_schedule_response,
    )

    return framework


def test_lesson_validation_edge_cases():
    """Test edge cases and validation scenarios."""
    framework = APITestFramework()

    print("\n🔍 Testing Lesson Validation Edge Cases")
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
        endpoint="/api/v1/lessons",
        params={"page": 0, "limit": 10},
        expected_status=422,  # Validation error
    )

    framework.run_test(
        test_name="Invalid Pagination (Limit Too High)",
        method="GET",
        endpoint="/api/v1/lessons",
        params={"page": 1, "limit": 200},
        expected_status=422,  # Validation error
    )

    # Test 2: Invalid lesson type filter
    framework.run_test(
        test_name="Invalid Lesson Type Filter",
        method="GET",
        endpoint="/api/v1/lessons",
        params={"lesson_type": "invalid_type"},
        expected_status=422,  # Validation error
    )

    # Test 3: Invalid status filter
    framework.run_test(
        test_name="Invalid Status Filter",
        method="GET",
        endpoint="/api/v1/lessons",
        params={"status": "invalid_status"},
        expected_status=422,  # Validation error
    )

    # Test 4: Create lesson with past date
    past_time = datetime.now() - timedelta(days=1)
    past_lesson_data = {
        "student_id": 1,
        "teacher_id": 1,
        "scheduled_at": past_time.isoformat(),
        "duration_minutes": 30,
        "lesson_type": "regular",
    }

    framework.run_test(
        test_name="Create Lesson (Past Date)",
        method="POST",
        endpoint="/api/v1/lessons",
        request_data=past_lesson_data,
        expected_status=[400, 422],  # Validation error expected
    )

    # Test 5: Create lesson with invalid duration
    future_time = datetime.now() + timedelta(days=1)
    invalid_duration_data = {
        "student_id": 1,
        "teacher_id": 1,
        "scheduled_at": future_time.isoformat(),
        "duration_minutes": 0,  # Invalid: zero duration
        "lesson_type": "regular",
    }

    framework.run_test(
        test_name="Create Lesson (Invalid Duration)",
        method="POST",
        endpoint="/api/v1/lessons",
        request_data=invalid_duration_data,
        expected_status=422,  # Validation error expected
    )

    return framework


def test_lesson_endpoints_without_auth():
    """Test lesson endpoints without authentication."""
    framework = APITestFramework()

    print("\n🔒 Testing Lesson Endpoints Without Authentication")
    print("=" * 60)

    # Test 1: List lessons without auth
    framework.run_test(
        test_name="List Lessons (No Auth)",
        method="GET",
        endpoint="/api/v1/lessons",
        expected_status=401,
        require_auth=False,
    )

    # Test 2: Create lesson without auth
    framework.run_test(
        test_name="Create Lesson (No Auth)",
        method="POST",
        endpoint="/api/v1/lessons",
        request_data={"student_id": 1, "teacher_id": 1},
        expected_status=401,
        require_auth=False,
    )

    # Test 3: Get lesson without auth
    fake_id = str(uuid.uuid4())
    framework.run_test(
        test_name="Get Lesson (No Auth)",
        method="GET",
        endpoint=f"/api/v1/lessons/{fake_id}",
        expected_status=401,
        require_auth=False,
    )

    # Test 4: Check conflicts without auth
    framework.run_test(
        test_name="Check Conflicts (No Auth)",
        method="POST",
        endpoint="/api/v1/lessons/check-conflicts",
        request_data={"teacher_id": 1},
        expected_status=401,
        require_auth=False,
    )

    # Test 5: Get schedule view without auth
    framework.run_test(
        test_name="Get Schedule View (No Auth)",
        method="GET",
        endpoint="/api/v1/lessons/schedule/view",
        expected_status=401,
        require_auth=False,
    )

    return framework


if __name__ == "__main__":
    print("🚀 Cedar Heights Music Academy - Lesson Management Endpoint Tests")
    print("Testing lesson management endpoints with authentication...")

    # Run all lesson tests
    lesson_framework = test_lesson_endpoints()
    conflict_framework = test_lesson_conflict_checking()
    schedule_framework = test_lesson_schedule_view()
    validation_framework = test_lesson_validation_edge_cases()
    no_auth_framework = test_lesson_endpoints_without_auth()

    # Combine results
    all_results = (
        lesson_framework.results
        + conflict_framework.results
        + schedule_framework.results
        + validation_framework.results
        + no_auth_framework.results
    )
    lesson_framework.results = all_results

    # Print summary
    lesson_framework.print_summary()

    # Exit with appropriate code
    failed_tests = sum(1 for r in all_results if not r.success)
    sys.exit(0 if failed_tests == 0 else 1)
