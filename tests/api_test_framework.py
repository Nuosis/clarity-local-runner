#!/usr/bin/env python3
"""
Quick and Dirty API Test Framework for Cedar Heights Music Academy API

This framework provides simple API testing capabilities with authentication handling.
Tests are organized from basic to complex and can be run individually or as a suite.
"""

import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

import requests


@dataclass
class TestResult:
    """Test result data structure."""

    name: str
    endpoint: str
    method: str
    status_code: int
    expected_status: int
    response_time_ms: float
    success: bool
    error_message: Optional[str] = None
    response_data: Optional[Dict] = None


class APITestFramework:
    """Simple API testing framework with authentication support."""

    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.auth_token: Optional[str] = None
        self.session = requests.Session()
        self.results: List[TestResult] = []

        # Set default headers
        self.session.headers.update(
            {"Content-Type": "application/json", "Accept": "application/json"}
        )

    def authenticate(self, email: str, password: str) -> bool:
        """Authenticate and store JWT token for subsequent requests."""
        try:
            login_data = {"email": email, "password": password}
            response = self.session.post(
                urljoin(self.base_url, "/auth/login"), json=login_data, timeout=10
            )

            if response.status_code == 200:
                auth_response = response.json()
                if auth_response.get("success") and auth_response.get("token"):
                    self.auth_token = auth_response["token"]
                    self.session.headers.update(
                        {"Authorization": f"Bearer {self.auth_token}"}
                    )
                    print(f"✅ Authentication successful")
                    return True
                else:
                    print(
                        f"❌ Authentication failed: {auth_response.get('error', 'Unknown error')}"
                    )
                    return False
            else:
                print(f"❌ Authentication failed with status {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Authentication error: {str(e)}")
            return False

    def load_request_data(self, file_path: str) -> Optional[Dict]:
        """Load JSON request data from file."""
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Failed to load request data from {file_path}: {str(e)}")
            return None

    def make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        require_auth: bool = True,
    ) -> requests.Response:
        """Make HTTP request with optional authentication."""
        url = urljoin(self.base_url, endpoint)

        # Remove auth header for public endpoints
        headers = self.session.headers.copy()
        if not require_auth and "Authorization" in headers:
            del headers["Authorization"]

        kwargs = {"timeout": 30, "headers": headers}

        if data:
            kwargs["json"] = data
        if params:
            kwargs["params"] = params

        return getattr(self.session, method.lower())(url, **kwargs)

    def run_test(
        self,
        test_name: str,
        method: str,
        endpoint: str,
        expected_status: int = 200,
        request_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        require_auth: bool = True,
        validate_response: Optional[callable] = None,
    ) -> TestResult:
        """Run a single API test."""
        print(f"\n🧪 Running test: {test_name}")
        print(f"   {method.upper()} {endpoint}")

        start_time = time.time()
        error_message = None
        response_data = None

        try:
            response = self.make_request(
                method=method,
                endpoint=endpoint,
                data=request_data,
                params=params,
                require_auth=require_auth,
            )

            response_time_ms = (time.time() - start_time) * 1000

            # Try to parse JSON response
            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text}

            # Check status code
            status_success = response.status_code == expected_status

            # Run custom validation if provided
            validation_success = True
            if validate_response and response_data:
                try:
                    validation_success = validate_response(response_data)
                    if not validation_success:
                        error_message = "Custom validation failed"
                except Exception as e:
                    validation_success = False
                    error_message = f"Validation error: {str(e)}"

            success = status_success and validation_success

            if not status_success:
                error_message = (
                    f"Expected status {expected_status}, got {response.status_code}"
                )

            result = TestResult(
                name=test_name,
                endpoint=endpoint,
                method=method.upper(),
                status_code=response.status_code,
                expected_status=expected_status,
                response_time_ms=response_time_ms,
                success=success,
                error_message=error_message,
                response_data=response_data,
            )

            # Print result
            status_icon = "✅" if success else "❌"
            print(
                f"   {status_icon} Status: {response.status_code} ({response_time_ms:.1f}ms)"
            )

            if not success and error_message:
                print(f"   ❌ Error: {error_message}")

            if response_data and isinstance(response_data, dict):
                if response_data.get("message"):
                    print(f"   📝 Message: {response_data['message']}")
                if not success and response_data.get("error"):
                    print(f"   🚨 API Error: {response_data['error']}")

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            error_message = f"Request failed: {str(e)}"

            result = TestResult(
                name=test_name,
                endpoint=endpoint,
                method=method.upper(),
                status_code=0,
                expected_status=expected_status,
                response_time_ms=response_time_ms,
                success=False,
                error_message=error_message,
            )

            print(f"   ❌ Request failed: {str(e)}")

        self.results.append(result)
        return result

    def print_summary(self):
        """Print test results summary."""
        if not self.results:
            print("\n📊 No tests were run.")
            return

        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - passed_tests
        avg_response_time = sum(r.response_time_ms for r in self.results) / total_tests

        print(f"\n" + "=" * 60)
        print(f"📊 TEST SUMMARY")
        print(f"=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⏱️  Average Response Time: {avg_response_time:.1f}ms")
        print(f"Success Rate: {(passed_tests / total_tests) * 100:.1f}%")

        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.results:
                if not result.success:
                    print(f"   • {result.name} - {result.error_message}")

        print(f"=" * 60)


def validate_api_response(response_data: Dict) -> bool:
    """Validate standard API response format."""
    if not isinstance(response_data, dict):
        return False

    # Check for required fields in APIResponse format
    required_fields = ["success"]
    for field in required_fields:
        if field not in response_data:
            return False

    return True


def validate_health_response(response_data: Dict) -> bool:
    """Validate health check response."""
    if not validate_api_response(response_data):
        return False

    data = response_data.get("data", {})
    if not isinstance(data, dict):
        return False

    # Check for health-specific fields
    required_fields = ["status", "timestamp", "version"]
    for field in required_fields:
        if field not in data:
            return False

    return data.get("status") in ["healthy", "unhealthy"]


def validate_list_response(response_data: Dict) -> bool:
    """Validate paginated list response."""
    if not validate_api_response(response_data):
        return False

    data = response_data.get("data", {})
    if not isinstance(data, dict):
        return False

    # Check for pagination metadata
    if "pagination" not in data:
        return False

    pagination = data["pagination"]
    required_fields = ["page", "limit", "total", "pages"]
    for field in required_fields:
        if field not in pagination:
            return False

    return True


if __name__ == "__main__":
    print("🚀 Cedar Heights Music Academy - API Test Framework")
    print("This framework provides utilities for testing the API endpoints.")
    print("Import this module to use the APITestFramework class in your tests.")
