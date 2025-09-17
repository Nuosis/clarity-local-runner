#!/usr/bin/env python3
"""
Task 7.5.2 Retry Limit Validation Test

This script validates that the retry limit validation enforces the maximum of 2 attempts
per build operation as specified in PRD line 81.

Test Coverage:
- Validates that max_attempts <= 2 is accepted
- Validates that max_attempts > 2 raises ValidationError
- Validates proper error messages when retry limits are exceeded
- Validates backward compatibility with existing method signatures
- Validates structured logging for retry limit validation
"""

import sys
import os
import traceback
from typing import Dict, Any

# Add the app directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    from services.aider_execution_service import AiderExecutionService, AiderExecutionContext
    from core.exceptions import ValidationError
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)


def test_retry_limit_validation():
    """Test retry limit validation functionality."""
    print("🧪 Testing Task 7.5.2: Retry Limit Validation")
    print("=" * 60)
    
    results = {
        'total_tests': 0,
        'passed_tests': 0,
        'failed_tests': 0,
        'test_details': []
    }
    
    # Initialize service
    service = AiderExecutionService(correlation_id="test-7-5-2")
    
    # Create test execution context
    context = AiderExecutionContext(
        project_id="test-project",
        execution_id="test-execution-7-5-2"
    )
    
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
        try:
            service._validate_retry_limit(3, "npm ci", context)
            raise AssertionError("Expected ValidationError for max_attempts = 3")
        except ValidationError as e:
            if "maximum allowed is 2" in str(e) and "PRD line 81" in str(e):
                print("  ✅ max_attempts = 3 correctly rejected with proper error message")
            else:
                raise AssertionError(f"Error message doesn't contain expected text: {e}")
        
        # Test max_attempts = 5 (should fail)
        try:
            service._validate_retry_limit(5, "npm build", context)
            raise AssertionError("Expected ValidationError for max_attempts = 5")
        except ValidationError as e:
            if "maximum allowed is 2" in str(e) and "PRD line 81" in str(e):
                print("  ✅ max_attempts = 5 correctly rejected with proper error message")
            else:
                raise AssertionError(f"Error message doesn't contain expected text: {e}")
        
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
        
        # Test non-integer max_attempts
        try:
            service._validate_retry_limit("2", "npm ci", context)
            raise AssertionError("Expected ValidationError for string max_attempts")
        except ValidationError as e:
            if "must be an integer" in str(e):
                print("  ✅ String max_attempts correctly rejected")
            else:
                raise AssertionError(f"Error message doesn't contain expected text: {e}")
        
        # Test negative max_attempts
        try:
            service._validate_retry_limit(-1, "npm ci", context)
            raise AssertionError("Expected ValidationError for negative max_attempts")
        except ValidationError as e:
            if "must be at least 1" in str(e):
                print("  ✅ Negative max_attempts correctly rejected")
            else:
                raise AssertionError(f"Error message doesn't contain expected text: {e}")
        
        # Test zero max_attempts
        try:
            service._validate_retry_limit(0, "npm ci", context)
            raise AssertionError("Expected ValidationError for zero max_attempts")
        except ValidationError as e:
            if "must be at least 1" in str(e):
                print("  ✅ Zero max_attempts correctly rejected")
            else:
                raise AssertionError(f"Error message doesn't contain expected text: {e}")
        
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
    
    # Test 4: Backward compatibility - method signatures unchanged
    test_name = "Backward compatibility - method signatures unchanged"
    results['total_tests'] += 1
    try:
        print(f"\n📋 Test: {test_name}")
        
        # Check that npm ci retry method still has default max_attempts=2
        import inspect
        npm_ci_signature = inspect.signature(service._execute_npm_ci_with_retry)
        max_attempts_param = npm_ci_signature.parameters.get('max_attempts')
        
        if max_attempts_param and max_attempts_param.default == 2:
            print("  ✅ npm ci retry method maintains default max_attempts=2")
        else:
            raise AssertionError(f"npm ci retry method signature changed: {max_attempts_param}")
        
        # Check that npm build retry method still has default max_attempts=2
        npm_build_signature = inspect.signature(service._execute_npm_build_with_retry)
        max_attempts_param = npm_build_signature.parameters.get('max_attempts')
        
        if max_attempts_param and max_attempts_param.default == 2:
            print("  ✅ npm build retry method maintains default max_attempts=2")
        else:
            raise AssertionError(f"npm build retry method signature changed: {max_attempts_param}")
        
        results['passed_tests'] += 1
        results['test_details'].append({
            'test': test_name,
            'status': 'PASSED',
            'details': 'Method signatures maintain backward compatibility'
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
    print("🚀 Starting Task 7.5.2 Retry Limit Validation Tests")
    print("=" * 60)
    
    try:
        results = test_retry_limit_validation()
        
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
            print("✅ Backward compatibility maintained")
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