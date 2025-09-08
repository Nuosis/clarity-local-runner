#!/usr/bin/env python3
"""
API Test Runner - Cedar Heights Music Academy
Executes API tests from most basic to most complex.
"""

import os
import subprocess
import sys
import time
from typing import List, Tuple

# Add the tests directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api_test_framework import APITestFramework


def check_server_health() -> bool:
    """Check if the API server is running and healthy."""
    print("🔍 Checking server health...")

    framework = APITestFramework()
    try:
        response = framework.make_request(
            method="GET", endpoint="/health", require_auth=False
        )

        if response.status_code == 200:
            print("✅ Server is healthy and ready for testing")
            return True
        else:
            print(f"❌ Server health check failed with status {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Server health check failed: {str(e)}")
        print(
            "💡 Make sure the server is running with: cd docker && docker-compose up api"
        )
        return False


def run_test_file(test_file: str) -> Tuple[bool, int, int]:
    """Run a single test file and return success status and test counts."""
    print(f"\n{'=' * 60}")
    print(f"🧪 Running {test_file}")
    print(f"{'=' * 60}")

    try:
        # Run the test file
        result = subprocess.run(
            [sys.executable, test_file],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=False,  # Let output stream to console
            text=True,
        )

        success = result.returncode == 0

        if success:
            print(f"✅ {test_file} completed successfully")
        else:
            print(f"❌ {test_file} failed with exit code {result.returncode}")

        return success, 0, 0  # We'll get actual counts from the test output

    except Exception as e:
        print(f"❌ Failed to run {test_file}: {str(e)}")
        return False, 0, 1


def main():
    """Main test runner function."""
    print("🚀 Cedar Heights Music Academy - API Test Suite")
    print("=" * 60)
    print("Running tests from most basic to most complex...")

    # Check if server is running
    if not check_server_health():
        print("\n❌ Cannot proceed with tests - server is not healthy")
        sys.exit(1)

    # Define test files in order from basic to complex
    test_files = [
        "test_01_health.py",  # Most basic - health checks
        "test_02_public.py",  # Public endpoints (no auth)
        "test_03_auth.py",  # Authentication endpoints (public + optional authenticated flows)
        "test_04_students.py",  # Student management endpoints (protected)
        "test_05_teachers.py",  # Teacher management endpoints (protected)
        "test_06_settings.py",  # System settings endpoints (protected)
        "test_07_academic.py",  # Academic calendar endpoints (protected)
        "test_08_payments.py",  # Payment management endpoints (protected)
        "test_09_lessons.py",  # Lesson management endpoints (protected)
    ]

    # Track overall results
    total_files = len(test_files)
    passed_files = 0
    failed_files = 0

    start_time = time.time()

    # Run each test file
    for test_file in test_files:
        test_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), test_file)

        if not os.path.exists(test_path):
            print(f"⚠️  Test file {test_file} not found, skipping...")
            continue

        success, passed, failed = run_test_file(test_path)

        if success:
            passed_files += 1
        else:
            failed_files += 1

        # Small delay between test files
        time.sleep(1)

    # Print final summary
    total_time = time.time() - start_time

    print(f"\n" + "=" * 60)
    print(f"📊 FINAL TEST SUMMARY")
    print(f"=" * 60)
    print(f"Total Test Files: {total_files}")
    print(f"✅ Passed Files: {passed_files}")
    print(f"❌ Failed Files: {failed_files}")
    print(f"⏱️  Total Time: {total_time:.1f}s")
    print(f"Success Rate: {(passed_files / total_files) * 100:.1f}%")

    if failed_files > 0:
        print(
            f"\n❌ {failed_files} test file(s) failed. Check the output above for details."
        )
        print("💡 Common issues:")
        print("   • Server not running (run: cd docker && docker-compose up api)")
        print("   • Database not seeded with test data")
        print("   • Authentication credentials not configured")
    else:
        print(f"\n🎉 All test files passed successfully!")

    print(f"=" * 60)

    # Exit with appropriate code
    sys.exit(0 if failed_files == 0 else 1)


if __name__ == "__main__":
    main()
