#!/usr/bin/env python3
"""
Authentication Endpoint Tests
- Exercises /auth endpoints using the existing APITestFramework
- Runs gracefully with or without real credentials configured
  - Set TEST_AUTH_EMAIL and TEST_AUTH_PASSWORD env vars to run authenticated flows
"""

import os
import sys

# Add the tests directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api_test_framework import APITestFramework  # noqa: E402


def validate_auth_success(resp: dict) -> bool:
    return (
        isinstance(resp, dict)
        and resp.get("success") is True
        and isinstance(resp.get("token"), str)
    )


def validate_auth_failure(resp: dict) -> bool:
    return isinstance(resp, dict) and resp.get("success") is False


def validate_user_context(resp: dict) -> bool:
    # /auth/me returns a plain user context object (not wrapped)
    required = ["user_id", "email", "role", "permissions", "authenticated"]
    return isinstance(resp, dict) and all(k in resp for k in required)


def validate_permissions(resp: dict) -> bool:
    # /auth/permissions returns context-like info
    required = ["user_id", "email", "role", "permissions", "authenticated"]
    return isinstance(resp, dict) and all(k in resp for k in required)


def validate_verify_token_valid(resp: dict) -> bool:
    required = ["valid", "user_id", "email", "role", "permissions"]
    return (
        isinstance(resp, dict)
        and resp.get("valid") is True
        and all(k in resp for k in required)
    )


def validate_verify_token_invalid(resp: dict) -> bool:
    return isinstance(resp, dict) and resp.get("valid") is False


def test_auth_endpoints():
    framework = APITestFramework()

    print("🔐 Testing Authentication Endpoints")
    print("=" * 50)

    # 1) Auth Health (public)
    framework.run_test(
        test_name="Auth Health",
        method="GET",
        endpoint="/auth/health",
        expected_status=200,
        require_auth=False,
        validate_response=lambda r: isinstance(r, dict)
        and r.get("status") == "healthy",
    )

    # 2) Login - invalid credentials (always safe)
    framework.run_test(
        test_name="Login (Invalid Credentials)",
        method="POST",
        endpoint="/auth/login",
        expected_status=200,
        require_auth=False,
        request_data={
            "email": os.getenv("TEST_INVALID_EMAIL", "nobody+test@example.com"),
            "password": os.getenv("TEST_INVALID_PASSWORD", "definitely_wrong_password"),
        },
        validate_response=validate_auth_failure,
    )

    # 3) Verify Token - missing header (expect 401)
    framework.run_test(
        test_name="Verify Token (Missing Header)",
        method="POST",
        endpoint="/auth/verify-token",
        expected_status=401,
        require_auth=False,  # ensure no Authorization header
    )

    # 4) Refresh - invalid refresh token (expect success=False 200)
    framework.run_test(
        test_name="Refresh (Invalid Refresh Token)",
        method="POST",
        endpoint="/auth/refresh",
        expected_status=200,
        require_auth=False,
        request_data={
            "refresh_token": os.getenv(
                "TEST_INVALID_REFRESH_TOKEN", "invalid_refresh_token"
            )
        },
        validate_response=validate_auth_failure,
    )

    # If creds provided, run authenticated flow
    email = os.getenv("TEST_AUTH_EMAIL")
    password = os.getenv("TEST_AUTH_PASSWORD")

    authed = False
    if email and password:
        authed = framework.authenticate(email, password)

    if authed:
        # 5) /auth/me
        framework.run_test(
            test_name="Get Current User (/auth/me)",
            method="GET",
            endpoint="/auth/me",
            expected_status=200,
            require_auth=True,
            validate_response=validate_user_context,
        )

        # 6) /auth/verify-token (valid)
        framework.run_test(
            test_name="Verify Token (Valid)",
            method="POST",
            endpoint="/auth/verify-token",
            expected_status=200,
            require_auth=True,
            validate_response=validate_verify_token_valid,
        )

        # 7) /auth/permissions
        framework.run_test(
            test_name="Get User Permissions",
            method="GET",
            endpoint="/auth/permissions",
            expected_status=200,
            require_auth=True,
            validate_response=validate_permissions,
        )

        # 8) /auth/logout
        framework.run_test(
            test_name="Logout",
            method="POST",
            endpoint="/auth/logout",
            expected_status=200,
            require_auth=True,
        )

        # 9) /auth/verify-token (explicit invalid token)
        temp = APITestFramework()
        temp.session.headers.update({"Authorization": "Bearer invalid_token"})
        temp.run_test(
            test_name="Verify Token (Explicit Invalid)",
            method="POST",
            endpoint="/auth/verify-token",
            expected_status=200,
            require_auth=True,
            validate_response=validate_verify_token_invalid,
        )

        # Merge results
        framework.results.extend(temp.results)
    else:
        print(
            "⚠️  TEST_AUTH_EMAIL/TEST_AUTH_PASSWORD not set or authentication failed; skipping authenticated flows."
        )

    return framework


if __name__ == "__main__":
    print("🚀 Cedar Heights Music Academy - Authentication Tests")
    framework = test_auth_endpoints()
    framework.print_summary()
    failed = sum(1 for r in framework.results if not r.success)
    sys.exit(0 if failed == 0 else 1)
