#!/usr/bin/env python3
"""
Task 7.5.2 Retry Limit Validation Simple Test

This script validates that the retry limit validation enforces the maximum of 2 attempts
per build operation as specified in PRD line 81.

Simplified test that focuses on the core validation logic.
"""

import sys
import os
import traceback

# Add the app directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_retry_limit_validation_simple():
    """Test retry limit validation functionality with minimal dependencies."""
    print("🧪 Testing Task 7.5.2: Retry Limit Validation (Simple)")
    print("=" * 60)
    
    results = {
        'total_tests': 0,
        'passed_tests': 0,
        'failed_tests': 0,
        'test_details': []
    }
    
    try:
        # Import only what we need
        from services.aider_execution_service import AiderExecutionService, AiderExecutionContext
        from core.exceptions import ValidationError
        
        # Initialize service
        service = AiderExecutionService(correlation_id="test-7-5-2-simple")
        
        # Create test execution context
        context = AiderExecutionContext(
            project_id="test-project",
            execution_id="test-execution-7-5-2-simple"
        )
        
        print("✅ Successfully imported required modules")
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return {
            'total_tests': 1,
            'passed_tests': 0,
            'failed_tests': 1,
            'test_details': [{'test': 'Import test', 'status': 'FAILED', 'error': str(e)}]
        }
    
    # Test 1: Valid retry limits (1 and 2 attempts)
    test_name = "Valid retry limits (1 and 2 attempts)"
    results['total_tests'] += 1
    try:
        print(f"\n📋 Test: {test_name}")
        
        # Test max_attempts = 1
        service._validate_retry_limit(1, "npm ci", context)
        print("  ✅ max_attempts = 1 accepted")
        
        # Test max_attempts = 2
        service._validate_retry_limit(2, "npm ci", context)
        print("  ✅ max_attempts = 2 accepted")
        
        # Test max_attempts = 2 for npm build
        service._validate_retry_limit(2, "npm build", context)
        print("  ✅ max_attempts = 2 accepted for npm build")
        
        results['passed_tests'] += 1
        results['test_details'].append({
            'test': test_name,
            'status': 'PASSED',
            'details': 'All valid retry limits accepted'
        })
        print(f"  ✅ {test_name}: PASSED")
        
    except Exception as e:
        results['failed_tests'] += 1
        results['test_details'].append({
            'test': test_name,
            'status': 'FAILED',
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        print(f"  ❌ {test_name}: FAILED - {e}")
    
    # Test 2: Invalid retry limits (> 2 attempts)
    test_name = "Invalid retry limits (> 2 attempts)"
    results['total_tests'] += 1
    try:
        print(f"\n📋 Test: {test_name}")
        
        # Test max_attempts = 3 (should fail)
        validation_error_caught = False
        try:
            service._validate_retry_limit(3, "npm ci", context)
        except ValidationError as e:
            validation_error_caught = True
            if "maximum allowed is 2" in str(e) and "PRD line 81" in str(e):
                print("  ✅ max_attempts = 3 correctly rejected with proper error message")
            else:
                raise AssertionError(f"Error message doesn't contain expected text: {e}")
        
        if not validation_error_caught:
            raise AssertionError("Expected ValidationError for max_attempts = 3")
        
        # Test max_attempts = 5 (should fail)
        validation_error_caught = False
        try:
            service._validate_retry_limit(5, "npm build", context)
        except ValidationError as e:
            validation_error_caught = True
            if "maximum allowed is 2" in str(e) and "PRD line 81" in str(e):
                print("  ✅ max_attempts = 5 correctly rejected with proper error message")
            else:
                raise AssertionError(f"Error message doesn't contain expected text: {e}")
        
        if not validation_error_caught:
            raise AssertionError("Expected ValidationError for max_attempts = 5")
        
        results['passed_tests'] += 1
        results['test_details'].append({
            'test': test_name,
            'status': 'PASSED',
            'details': 'Invalid retry limits correctly rejected with proper error messages'
        })
        print(f"  ✅ {test_name}: PASSED")
        
    except Exception as e:
        results['failed_tests'] += 1
        results['test_details'].append({
            'test': test_name,
            'status': 'FAILED',
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        print(f"  ❌ {test_name}: FAILED - {e}")
    
    # Test 3: Invalid input types
    test_name = "Invalid input types"
    results['total_tests'] += 1
    try:
        print(f"\n📋 Test: {test_name}")
        
        # Test zero max_attempts
        validation_error_caught = False
        try:
            service._validate_retry_limit(0, "npm ci", context)
        except ValidationError as e:
            validation_error_caught = True
            if "must be at least 1" in str(e):
                print("  ✅ Zero max_attempts correctly rejected")
            else:
                raise AssertionError(f"Error message doesn't contain expected text: {e}")
        
        if not validation_error_caught:
            raise AssertionError("Expected ValidationError for zero max_attempts")
        
        results['passed_tests'] += 1
        results['test_details'].append({
            'test': test_name,
            'status': 'PASSED',
            'details': 'Invalid input types correctly rejected with proper error messages'
        })
        print(f"  ✅ {test_name}: PASSED")
        
    except Exception as e:
        results['failed_tests'] += 1
        results['test_details'].append({
            'test': test_name,
            'status': 'FAILED',
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        print(f"  ❌ {test_name}: FAILED - {e}")
    
    return results


def main():
    """Main test execution function."""
    print("🚀 Starting Task 7.5.2 Retry Limit Validation Simple Tests")
    print("=" * 60)
    
    try:
        results = test_retry_limit_validation_simple()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {results['total_tests']}")
        print(f"Passed: {results['passed_tests']}")
        print(f"Failed: {results['failed_tests']}")
        print(f"Success Rate: {(results['passed_tests']/results['total_tests']*100):.1f}%")
        
        # Print detailed results
        print("\n📋 DETAILED RESULTS:")
        for detail in results['test_details']:
            status_icon = "✅" if detail['status'] == 'PASSED' else "❌"
            print(f"{status_icon} {detail['test']}: {detail['status']}")
            if detail['status'] == 'FAILED':
                print(f"   Error: {detail['error']}")
        
        # Determine overall result
        if results['failed_tests'] == 0:
            print(f"\n🎉 ALL TESTS PASSED! Task 7.5.2 retry limit validation is working correctly.")
            print("✅ Retry limit validation enforces maximum 2 attempts per PRD line 81")
            print("✅ Proper error messages when retry limits are exceeded")
            print("✅ Input validation handles edge cases")
            return True
        else:
            print(f"\n❌ {results['failed_tests']} test(s) failed. Please review the implementation.")
            return False
            
    except Exception as e:
        print(f"\n💥 Test execution failed with error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)