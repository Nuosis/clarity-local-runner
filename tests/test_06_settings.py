#!/usr/bin/env python3
"""
System Settings Endpoint Tests - Protected Endpoints
Tests all system settings management endpoints that require authentication.
"""

import os
import sys
import uuid

# Add the tests directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api_test_framework import APITestFramework, validate_api_response


def validate_settings_list_response(response_data):
    """Validate settings list response structure."""
    if not validate_api_response(response_data):
        return False

    data = response_data.get("data")
    if not isinstance(data, list):
        return False

    # If there are settings, validate structure
    for setting in data:
        if not isinstance(setting, dict):
            return False
        required_fields = [
            "id",
            "setting_key",
            "setting_value",
            "setting_type",
            "description",
            "is_public",
            "category",
            "created_at",
            "updated_at",
        ]
        for field in required_fields:
            if field not in setting:
                return False

    return True


def validate_setting_response(response_data):
    """Validate single setting response structure."""
    if not validate_api_response(response_data):
        return False

    data = response_data.get("data", {})
    if not isinstance(data, dict):
        return False

    # Check for required setting fields
    required_fields = [
        "id",
        "setting_key",
        "setting_value",
        "setting_type",
        "description",
        "is_public",
        "category",
        "created_at",
        "updated_at",
    ]

    for field in required_fields:
        if field not in data:
            return False

    return True


def validate_delete_response(response_data):
    """Validate delete response structure."""
    if not validate_api_response(response_data):
        return False

    data = response_data.get("data", {})
    if not isinstance(data, dict):
        return False

    required_fields = ["id", "setting_key", "deleted"]
    for field in required_fields:
        if field not in data:
            return False

    return data.get("deleted") is True


def test_settings_endpoints():
    """Test all system settings management endpoints."""
    framework = APITestFramework()

    print("⚙️ Testing System Settings Management Endpoints")
    print("=" * 60)

    # Authenticate first
    email = os.getenv("TEST_AUTH_EMAIL")
    password = os.getenv("TEST_AUTH_PASSWORD")

    if not email or not password:
        print(
            "❌ Authentication failed: TEST_AUTH_EMAIL and TEST_AUTH_PASSWORD environment variables not set"
        )
        print("❌ Authentication failed - skipping settings tests")
        return framework

    if not framework.authenticate(email, password):
        print("❌ Authentication failed - skipping settings tests")
        return framework

    # Test 1: List settings (empty initially)
    framework.run_test(
        test_name="List Settings (Empty)",
        method="GET",
        endpoint="/api/v1/settings",
        expected_status=200,
        validate_response=validate_settings_list_response,
    )

    # Test 2: List settings with category filter
    framework.run_test(
        test_name="List Settings (Category Filter)",
        method="GET",
        endpoint="/api/v1/settings",
        params={"category": "general"},
        expected_status=200,
        validate_response=validate_settings_list_response,
    )

    # Test 3: List settings with public filter
    framework.run_test(
        test_name="List Settings (Public Only)",
        method="GET",
        endpoint="/api/v1/settings",
        params={"is_public": True},
        expected_status=200,
        validate_response=validate_settings_list_response,
    )

    # Test 4: Update non-existent setting
    fake_setting_id = 999999
    framework.run_test(
        test_name="Update Non-existent Setting",
        method="PUT",
        endpoint=f"/api/v1/settings/{fake_setting_id}",
        request_data={"setting_value": "new_value"},
        expected_status=404,
    )

    # Test 5: Delete non-existent setting
    framework.run_test(
        test_name="Delete Non-existent Setting",
        method="DELETE",
        endpoint=f"/api/v1/settings/{fake_setting_id}",
        expected_status=404,
    )

    return framework


def test_settings_validation_edge_cases():
    """Test edge cases and validation scenarios."""
    framework = APITestFramework()

    print("\n🔍 Testing Settings Validation Edge Cases")
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

    # Test 1: Invalid category filter
    framework.run_test(
        test_name="Invalid Category Filter",
        method="GET",
        endpoint="/api/v1/settings",
        params={"category": "invalid_category_that_does_not_exist"},
        expected_status=200,  # Should return empty list, not error
        validate_response=validate_settings_list_response,
    )

    # Test 2: Multiple filters
    framework.run_test(
        test_name="Multiple Filters",
        method="GET",
        endpoint="/api/v1/settings",
        params={"category": "general", "is_public": False},
        expected_status=200,
        validate_response=validate_settings_list_response,
    )

    # Test 3: Update setting with empty data
    fake_setting_id = 999999
    framework.run_test(
        test_name="Update Setting (Empty Data)",
        method="PUT",
        endpoint=f"/api/v1/settings/{fake_setting_id}",
        request_data={},
        expected_status=404,  # Setting not found (but would be valid if setting existed)
    )

    # Test 4: Update setting with null values
    framework.run_test(
        test_name="Update Setting (Null Values)",
        method="PUT",
        endpoint=f"/api/v1/settings/{fake_setting_id}",
        request_data={"setting_value": None, "description": None},
        expected_status=404,  # Setting not found
    )

    return framework


def test_settings_endpoints_without_auth():
    """Test settings endpoints without authentication."""
    framework = APITestFramework()

    print("\n🔒 Testing Settings Endpoints Without Authentication")
    print("=" * 60)

    # Test 1: List settings without auth (should work for public settings)
    framework.run_test(
        test_name="List Settings (No Auth)",
        method="GET",
        endpoint="/api/v1/settings",
        expected_status=401,  # Requires authentication
        require_auth=False,
    )

    # Test 2: Update setting without auth
    fake_id = 999999
    framework.run_test(
        test_name="Update Setting (No Auth)",
        method="PUT",
        endpoint=f"/api/v1/settings/{fake_id}",
        request_data={"setting_value": "test"},
        expected_status=401,
        require_auth=False,
    )

    # Test 3: Delete setting without auth
    framework.run_test(
        test_name="Delete Setting (No Auth)",
        method="DELETE",
        endpoint=f"/api/v1/settings/{fake_id}",
        expected_status=401,
        require_auth=False,
    )

    return framework


def test_settings_non_admin_access():
    """Test settings endpoints with non-admin user."""
    framework = APITestFramework()

    print("\n👤 Testing Settings Endpoints with Non-Admin User")
    print("=" * 60)

    # Try to authenticate with non-admin credentials if available
    teacher_email = os.getenv("TEST_TEACHER_EMAIL", "teacher@cedarheights.com")
    teacher_password = os.getenv("TEST_TEACHER_PASSWORD", "teacher123")

    # Note: This might fail if teacher credentials don't exist
    if framework.authenticate(teacher_email, teacher_password):
        # Test 1: List settings as non-admin (should only see public settings)
        framework.run_test(
            test_name="List Settings (Non-Admin)",
            method="GET",
            endpoint="/api/v1/settings",
            expected_status=200,
            validate_response=validate_settings_list_response,
        )

        # Test 2: Try to update setting as non-admin (should fail)
        fake_id = 999999
        framework.run_test(
            test_name="Update Setting (Non-Admin)",
            method="PUT",
            endpoint=f"/api/v1/settings/{fake_id}",
            request_data={"setting_value": "test"},
            expected_status=403,  # Forbidden - requires admin
        )

        # Test 3: Try to delete setting as non-admin (should fail)
        framework.run_test(
            test_name="Delete Setting (Non-Admin)",
            method="DELETE",
            endpoint=f"/api/v1/settings/{fake_id}",
            expected_status=403,  # Forbidden - requires admin
        )
    else:
        print("⚠️  Non-admin credentials not available, skipping non-admin tests")

    return framework


if __name__ == "__main__":
    print("🚀 Cedar Heights Music Academy - System Settings Endpoint Tests")
    print("Testing system settings management endpoints with authentication...")

    # Run all settings tests
    main_framework = test_settings_endpoints()
    validation_framework = test_settings_validation_edge_cases()
    no_auth_framework = test_settings_endpoints_without_auth()
    non_admin_framework = test_settings_non_admin_access()

    # Combine results
    all_results = (
        main_framework.results
        + validation_framework.results
        + no_auth_framework.results
        + non_admin_framework.results
    )
    main_framework.results = all_results

    # Print summary
    main_framework.print_summary()

    # Exit with appropriate code
    failed_tests = sum(1 for r in all_results if not r.success)
    sys.exit(0 if failed_tests == 0 else 1)
