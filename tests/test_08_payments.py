#!/usr/bin/env python3
"""
Payment Management Endpoint Tests - Protected Endpoints
Tests all payment management endpoints that require authentication.
"""

import os
import sys
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

# Add the tests directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api_test_framework import APITestFramework, validate_api_response


def validate_payment_response(response_data):
    """Validate payment response structure."""
    if not validate_api_response(response_data):
        return False

    data = response_data.get("data", {})
    if not isinstance(data, dict):
        return False

    # Check for required payment fields
    required_fields = [
        "id",
        "student",
        "stripe_payment_intent_id",
        "amount",
        "currency",
        "payment_method",
        "billing_cycle",
        "description",
        "status",
        "payment_date",
        "failure_reason",
        "metadata",
        "created_at",
        "updated_at",
    ]

    for field in required_fields:
        if field not in data:
            return False

    # Validate student object
    student = data.get("student")
    if student and isinstance(student, dict):
        student_fields = ["id", "first_name", "last_name"]
        for field in student_fields:
            if field not in student:
                return False

    return True


def validate_payment_list_response(response_data):
    """Validate payment list response structure."""
    if not validate_api_response(response_data):
        return False

    data = response_data.get("data", {})
    if not isinstance(data, dict):
        return False

    # Check for required list structure
    required_fields = ["payments", "summary", "pagination"]
    for field in required_fields:
        if field not in data:
            return False

    # Validate payments array
    payments = data.get("payments", [])
    if not isinstance(payments, list):
        return False

    # If there are payments, validate structure
    for payment in payments:
        if not isinstance(payment, dict):
            return False
        payment_fields = [
            "id",
            "student_id",
            "student_name",
            "lesson_id",
            "stripe_payment_intent_id",
            "amount",
            "currency",
            "status",
            "payment_method",
            "payment_date",
            "billing_cycle",
            "description",
            "created_at",
        ]
        for field in payment_fields:
            if field not in payment:
                return False

    # Validate summary object
    summary = data.get("summary", {})
    if not isinstance(summary, dict):
        return False

    summary_fields = [
        "total_amount",
        "successful_payments",
        "failed_payments",
        "pending_payments",
        "refunded_amount",
    ]
    for field in summary_fields:
        if field not in summary:
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


def validate_subscription_response(response_data):
    """Validate subscription response structure."""
    if not validate_api_response(response_data):
        return False

    data = response_data.get("data", {})
    if not isinstance(data, dict):
        return False

    # Check for required subscription fields
    required_fields = [
        "id",
        "student_id",
        "student_name",
        "stripe_subscription_id",
        "stripe_customer_id",
        "billing_cycle",
        "amount",
        "currency",
        "status",
        "current_period_start",
        "current_period_end",
        "created_at",
        "updated_at",
    ]

    for field in required_fields:
        if field not in data:
            return False

    return True


def validate_subscription_list_response(response_data):
    """Validate subscription list response structure."""
    if not validate_api_response(response_data):
        return False

    data = response_data.get("data", {})
    if not isinstance(data, dict):
        return False

    # Check for required list structure
    required_fields = ["subscriptions", "pagination"]
    for field in required_fields:
        if field not in data:
            return False

    # Validate subscriptions array
    subscriptions = data.get("subscriptions", [])
    if not isinstance(subscriptions, list):
        return False

    return True


def validate_workflow_response(response_data):
    """Validate workflow response structure."""
    if not validate_api_response(response_data):
        return False

    data = response_data.get("data", {})
    if not isinstance(data, dict):
        return False

    # Check for required workflow fields
    required_fields = ["workflow_id", "status", "execution_time", "results"]
    for field in required_fields:
        if field not in data:
            return False

    return True


def test_payment_endpoints():
    """Test all payment management endpoints."""
    framework = APITestFramework()

    print("💳 Testing Payment Management Endpoints")
    print("=" * 60)

    # Authenticate first
    email = os.getenv("TEST_AUTH_EMAIL")
    password = os.getenv("TEST_AUTH_PASSWORD")

    if not email or not password:
        print(
            "❌ Authentication failed: TEST_AUTH_EMAIL and TEST_AUTH_PASSWORD environment variables not set"
        )
        print("❌ Authentication failed - skipping payment tests")
        return framework

    if not framework.authenticate(email, password):
        print("❌ Authentication failed - skipping payment tests")
        return framework

    # Test 1: List payments (empty initially)
    framework.run_test(
        test_name="List Payments (Empty)",
        method="GET",
        endpoint="/api/v1/payments",
        expected_status=200,
        validate_response=validate_payment_list_response,
    )

    # Test 2: List payments with pagination
    framework.run_test(
        test_name="List Payments (With Pagination)",
        method="GET",
        endpoint="/api/v1/payments",
        params={"page": 1, "limit": 10},
        expected_status=200,
        validate_response=validate_payment_list_response,
    )

    # Test 3: List payments with filters
    framework.run_test(
        test_name="List Payments (With Filters)",
        method="GET",
        endpoint="/api/v1/payments",
        params={"student_id": 1, "status": "succeeded"},
        expected_status=200,
        validate_response=validate_payment_list_response,
    )

    # Test 4: List payments with date range
    today = date.today()
    last_month = today - timedelta(days=30)
    framework.run_test(
        test_name="List Payments (Date Range)",
        method="GET",
        endpoint="/api/v1/payments",
        params={
            "date_from": last_month.isoformat(),
            "date_to": today.isoformat(),
        },
        expected_status=200,
        validate_response=validate_payment_list_response,
    )

    # Test 5: Create payment (will fail without valid student_id)
    create_payment_data = {
        "student_id": 999,  # Non-existent student ID
        "lesson_id": None,
        "amount": 125.00,
        "currency": "CAD",
        "payment_method": "card",
        "billing_cycle": "monthly",
        "description": "Piano lesson - Test payment",
        "payment_date": datetime.now().isoformat(),
    }

    framework.run_test(
        test_name="Create Payment (Invalid Student ID)",
        method="POST",
        endpoint="/api/v1/payments",
        request_data=create_payment_data,
        expected_status=400,  # Bad request expected
    )

    # Test 6: Create payment with invalid data
    invalid_payment_data = {
        "student_id": 1,
        "amount": -50.00,  # Invalid: negative amount
        "currency": "INVALID",  # Invalid currency
        "payment_method": "invalid_method",
        "billing_cycle": "invalid_cycle",
        "description": "",
    }

    framework.run_test(
        test_name="Create Payment (Invalid Data)",
        method="POST",
        endpoint="/api/v1/payments",
        request_data=invalid_payment_data,
        expected_status=422,  # Validation error expected
    )

    # Test 7: Get non-existent payment
    fake_payment_id = 999999
    framework.run_test(
        test_name="Get Non-existent Payment",
        method="GET",
        endpoint=f"/api/v1/payments/{fake_payment_id}",
        expected_status=404,
    )

    # Test 8: Update non-existent payment
    framework.run_test(
        test_name="Update Non-existent Payment",
        method="PATCH",
        endpoint=f"/api/v1/payments/{fake_payment_id}",
        request_data={"status": "succeeded"},
        expected_status=404,
    )

    # Test 9: Delete non-existent payment
    framework.run_test(
        test_name="Delete Non-existent Payment",
        method="DELETE",
        endpoint=f"/api/v1/payments/{fake_payment_id}",
        expected_status=404,
    )

    return framework


def test_subscription_endpoints():
    """Test subscription management endpoints."""
    framework = APITestFramework()

    print("\n🔄 Testing Subscription Management Endpoints")
    print("=" * 60)

    # Authenticate first
    email = os.getenv("TEST_AUTH_EMAIL")
    password = os.getenv("TEST_AUTH_PASSWORD")

    if not email or not password:
        print(
            "❌ Authentication failed: TEST_AUTH_EMAIL and TEST_AUTH_PASSWORD environment variables not set"
        )
        print("❌ Authentication failed - skipping subscription tests")
        return framework

    if not framework.authenticate(email, password):
        print("❌ Authentication failed - skipping subscription tests")
        return framework

    # Test 1: List subscriptions (empty initially)
    framework.run_test(
        test_name="List Subscriptions (Empty)",
        method="GET",
        endpoint="/api/v1/payments/subscriptions",
        expected_status=200,
        validate_response=validate_subscription_list_response,
    )

    # Test 2: List subscriptions with pagination
    framework.run_test(
        test_name="List Subscriptions (With Pagination)",
        method="GET",
        endpoint="/api/v1/payments/subscriptions",
        params={"page": 1, "limit": 10},
        expected_status=200,
        validate_response=validate_subscription_list_response,
    )

    # Test 3: List subscriptions with filters
    framework.run_test(
        test_name="List Subscriptions (With Filters)",
        method="GET",
        endpoint="/api/v1/payments/subscriptions",
        params={"student_id": 1, "status": "active"},
        expected_status=200,
        validate_response=validate_subscription_list_response,
    )

    # Test 4: Create subscription (will fail without valid student_id)
    create_subscription_data = {
        "student_id": 999,  # Non-existent student ID
        "stripe_customer_id": "cus_test_123",
        "billing_cycle": "monthly",
        "amount": 125.00,
        "currency": "CAD",
    }

    framework.run_test(
        test_name="Create Subscription (Invalid Student ID)",
        method="POST",
        endpoint="/api/v1/payments/subscriptions",
        request_data=create_subscription_data,
        expected_status=404,  # Student not found
    )

    # Test 5: Create subscription with invalid data
    invalid_subscription_data = {
        "student_id": 1,
        "amount": -50.00,  # Invalid: negative amount
        "currency": "INVALID",  # Invalid currency
        "billing_cycle": "invalid_cycle",
    }

    framework.run_test(
        test_name="Create Subscription (Invalid Data)",
        method="POST",
        endpoint="/api/v1/payments/subscriptions",
        request_data=invalid_subscription_data,
        expected_status=422,  # Validation error expected
    )

    return framework


def test_workflow_endpoints():
    """Test payment workflow endpoints."""
    framework = APITestFramework()

    print("\n⚙️ Testing Payment Workflow Endpoints")
    print("=" * 60)

    # Authenticate first
    email = os.getenv("TEST_AUTH_EMAIL")
    password = os.getenv("TEST_AUTH_PASSWORD")

    if not email or not password:
        print(
            "❌ Authentication failed: TEST_AUTH_EMAIL and TEST_AUTH_PASSWORD environment variables not set"
        )
        print("❌ Authentication failed - skipping workflow tests")
        return framework

    if not framework.authenticate(email, password):
        print("❌ Authentication failed - skipping workflow tests")
        return framework

    # Test 1: Process payment workflow
    workflow_request_data = {
        "student_id": 1,
        "amount": 125.00,
        "currency": "CAD",
        "payment_method": "card",
        "description": "Test workflow payment",
    }

    framework.run_test(
        test_name="Process Payment Workflow",
        method="POST",
        endpoint="/api/v1/payments/workflows/process",
        request_data=workflow_request_data,
        expected_status=200,
        validate_response=validate_workflow_response,
    )

    # Test 2: Get workflow status
    fake_workflow_id = "wf_test_123"
    framework.run_test(
        test_name="Get Workflow Status",
        method="GET",
        endpoint=f"/api/v1/payments/workflows/{fake_workflow_id}/status",
        expected_status=200,
        validate_response=validate_workflow_response,
    )

    # Test 3: Process workflow with invalid data
    invalid_workflow_data = {
        "student_id": 999,  # Non-existent student
        "amount": -50.00,  # Invalid amount
        "currency": "INVALID",
    }

    framework.run_test(
        test_name="Process Workflow (Invalid Data)",
        method="POST",
        endpoint="/api/v1/payments/workflows/process",
        request_data=invalid_workflow_data,
        expected_status=[400, 422],  # Validation error expected
    )

    return framework


def test_payment_validation_edge_cases():
    """Test edge cases and validation scenarios."""
    framework = APITestFramework()

    print("\n🔍 Testing Payment Validation Edge Cases")
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
        endpoint="/api/v1/payments",
        params={"page": 0, "limit": 10},
        expected_status=422,  # Validation error
    )

    framework.run_test(
        test_name="Invalid Pagination (Limit Too High)",
        method="GET",
        endpoint="/api/v1/payments",
        params={"page": 1, "limit": 200},
        expected_status=422,  # Validation error
    )

    # Test 2: Invalid date range
    framework.run_test(
        test_name="Invalid Date Range",
        method="GET",
        endpoint="/api/v1/payments",
        params={
            "date_from": "2024-12-31",  # Future start date
            "date_to": "2024-01-01",  # Past end date
        },
        expected_status=200,  # Should return empty list, not error
        validate_response=validate_payment_list_response,
    )

    # Test 3: Invalid status filter
    framework.run_test(
        test_name="Invalid Status Filter",
        method="GET",
        endpoint="/api/v1/payments",
        params={"status": "invalid_status"},
        expected_status=422,  # Validation error
    )

    # Test 4: Create payment with missing required fields
    incomplete_payment_data = {
        "student_id": 1,
        # Missing amount, currency, etc.
    }

    framework.run_test(
        test_name="Create Payment (Missing Fields)",
        method="POST",
        endpoint="/api/v1/payments",
        request_data=incomplete_payment_data,
        expected_status=422,  # Validation error
    )

    return framework


def test_payment_endpoints_without_auth():
    """Test payment endpoints without authentication."""
    framework = APITestFramework()

    print("\n🔒 Testing Payment Endpoints Without Authentication")
    print("=" * 60)

    # Test 1: List payments without auth
    framework.run_test(
        test_name="List Payments (No Auth)",
        method="GET",
        endpoint="/api/v1/payments",
        expected_status=401,
        require_auth=False,
    )

    # Test 2: Create payment without auth
    framework.run_test(
        test_name="Create Payment (No Auth)",
        method="POST",
        endpoint="/api/v1/payments",
        request_data={"student_id": 1, "amount": 100.00},
        expected_status=401,
        require_auth=False,
    )

    # Test 3: Get payment without auth
    fake_id = 999999
    framework.run_test(
        test_name="Get Payment (No Auth)",
        method="GET",
        endpoint=f"/api/v1/payments/{fake_id}",
        expected_status=401,
        require_auth=False,
    )

    # Test 4: List subscriptions without auth
    framework.run_test(
        test_name="List Subscriptions (No Auth)",
        method="GET",
        endpoint="/api/v1/payments/subscriptions",
        expected_status=401,
        require_auth=False,
    )

    # Test 5: Process workflow without auth
    framework.run_test(
        test_name="Process Workflow (No Auth)",
        method="POST",
        endpoint="/api/v1/payments/workflows/process",
        request_data={"student_id": 1, "amount": 100.00},
        expected_status=401,
        require_auth=False,
    )

    return framework


if __name__ == "__main__":
    print("🚀 Cedar Heights Music Academy - Payment Management Endpoint Tests")
    print("Testing payment management endpoints with authentication...")

    # Run all payment tests
    payment_framework = test_payment_endpoints()
    subscription_framework = test_subscription_endpoints()
    workflow_framework = test_workflow_endpoints()
    validation_framework = test_payment_validation_edge_cases()
    no_auth_framework = test_payment_endpoints_without_auth()

    # Combine results
    all_results = (
        payment_framework.results
        + subscription_framework.results
        + workflow_framework.results
        + validation_framework.results
        + no_auth_framework.results
    )
    payment_framework.results = all_results

    # Print summary
    payment_framework.print_summary()

    # Exit with appropriate code
    failed_tests = sum(1 for r in all_results if not r.success)
    sys.exit(0 if failed_tests == 0 else 1)
