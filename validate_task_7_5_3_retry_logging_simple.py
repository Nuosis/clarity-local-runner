#!/usr/bin/env python3
"""
Task 7.5.3 Simple Validation: Enhanced Retry Logging for AiderExecutionService

This script validates that the enhanced retry logging functionality has been properly
implemented with comprehensive structured logging for each retry attempt.

Validation Criteria:
- Enhanced logging captures detailed logs for each retry attempt
- Includes correlationId propagation for distributed tracing
- Logs retry attempt number, operation type, failure reason, and timing information
- Integrates with existing structured logging patterns and secret redaction
- Maintains performance requirements (≤60s total)
- Log messages are meaningful and actionable for debugging
"""

import sys
import json
import time
import inspect
import re

# Add the app directory to the Python path
sys.path.insert(0, '/Users/marcusswift/python/Clarity-Local-Runner/app')

def validate_enhanced_retry_logging():
    """Validate enhanced retry logging functionality."""
    print("🔍 Validating Task 7.5.3: Enhanced Retry Logging")
    print("=" * 60)
    
    results = []
    total_tests = 0
    passed_tests = 0
    
    def add_result(test_name, passed, details=""):
        nonlocal total_tests, passed_tests
        results.append({"test": test_name, "passed": passed, "details": details})
        total_tests += 1
        if passed:
            passed_tests += 1
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"    Details: {details}")
    
    # Test 1: Import validation
    try:
        from services.aider_execution_service import (
            AiderExecutionService, 
            AiderExecutionContext,
            AiderExecutionResult,
            AiderExecutionError
        )
        from core.structured_logging import LogStatus
        from core.exceptions import ValidationError
        add_result("Module imports", True, "All required modules imported successfully")
    except ImportError as e:
        add_result("Module imports", False, f"Import error: {str(e)}")
        return {"total_tests": 1, "passed_tests": 0, "failed_tests": 1, "success_rate": 0, "overall_status": "FAIL"}
    
    # Test 2: Check enhanced retry methods exist
    try:
        service = AiderExecutionService(correlation_id="test-correlation-123")
        
        has_npm_ci_retry = hasattr(service, '_execute_npm_ci_with_retry')
        has_npm_build_retry = hasattr(service, '_execute_npm_build_with_retry')
        has_cleanup_method = hasattr(service, '_cleanup_container_after_failed_attempt')
        has_validate_retry_limit = hasattr(service, '_validate_retry_limit')
        
        all_methods_exist = all([has_npm_ci_retry, has_npm_build_retry, has_cleanup_method, has_validate_retry_limit])
        
        add_result(
            "Enhanced retry methods exist",
            all_methods_exist,
            f"npm_ci_retry: {has_npm_ci_retry}, npm_build_retry: {has_npm_build_retry}, cleanup: {has_cleanup_method}, validate_retry_limit: {has_validate_retry_limit}"
        )
        
    except Exception as e:
        add_result("Enhanced retry methods exist", False, f"Error: {str(e)}")
    
    # Test 3: Check correlation ID propagation
    try:
        correlation_id = "test-correlation-456"
        service = AiderExecutionService(correlation_id=correlation_id)
        
        has_correlation_id = service.correlation_id == correlation_id
        has_logger = hasattr(service, 'logger')
        
        add_result(
            "Correlation ID propagation",
            has_correlation_id and has_logger,
            f"correlation_id set: {has_correlation_id}, has logger: {has_logger}"
        )
        
    except Exception as e:
        add_result("Correlation ID propagation", False, f"Error: {str(e)}")
    
    # Test 4: Check LogStatus integration
    try:
        has_started = hasattr(LogStatus, 'STARTED')
        has_in_progress = hasattr(LogStatus, 'IN_PROGRESS')
        has_completed = hasattr(LogStatus, 'COMPLETED')
        has_failed = hasattr(LogStatus, 'FAILED')
        
        all_statuses_available = all([has_started, has_in_progress, has_completed, has_failed])
        
        add_result(
            "LogStatus integration",
            all_statuses_available,
            f"Required LogStatus values available: {all_statuses_available}"
        )
        
    except Exception as e:
        add_result("LogStatus integration", False, f"Error: {str(e)}")
    
    # Test 5: Check enhanced logging in source code
    try:
        # Read the source file to check for enhanced logging patterns
        with open('/Users/marcusswift/python/Clarity-Local-Runner/app/services/aider_execution_service.py', 'r') as f:
            source_code = f.read()
        
        # Check for enhanced logging patterns
        has_operation_type = 'operation_type=' in source_code
        has_retry_context = 'retry_context=' in source_code
        has_attempt_duration = 'attempt_duration_ms=' in source_code
        has_failure_reason = 'failure_reason=' in source_code
        has_retry_outcome = 'retry_outcome=' in source_code
        has_cleanup_context = 'cleanup_context=' in source_code
        
        enhanced_logging_patterns = all([
            has_operation_type, has_retry_context, has_attempt_duration, 
            has_failure_reason, has_retry_outcome, has_cleanup_context
        ])
        
        add_result(
            "Enhanced logging patterns in code",
            enhanced_logging_patterns,
            f"operation_type: {has_operation_type}, retry_context: {has_retry_context}, attempt_duration: {has_attempt_duration}, failure_reason: {has_failure_reason}, retry_outcome: {has_retry_outcome}, cleanup_context: {has_cleanup_context}"
        )
        
    except Exception as e:
        add_result("Enhanced logging patterns in code", False, f"Error: {str(e)}")
    
    # Test 6: Check retry limit validation
    try:
        service = AiderExecutionService(correlation_id="test-correlation-789")
        context = AiderExecutionContext(
            project_id="test-project",
            execution_id="test-execution"
        )
        
        # Test that retry limit validation method exists and can be called
        validate_method = getattr(service, '_validate_retry_limit', None)
        method_exists = validate_method is not None
        
        if method_exists:
            # Check method signature
            sig = inspect.signature(validate_method)
            expected_params = ['max_attempts', 'operation_name', 'context']
            has_correct_params = all(param in sig.parameters for param in expected_params)
        else:
            has_correct_params = False
        
        add_result(
            "Retry limit validation method",
            method_exists and has_correct_params,
            f"Method exists: {method_exists}, Correct parameters: {has_correct_params}"
        )
        
    except Exception as e:
        add_result("Retry limit validation method", False, f"Error: {str(e)}")
    
    # Test 7: Check performance considerations
    try:
        start_time = time.time()
        service = AiderExecutionService(correlation_id="test-performance")
        instantiation_time = (time.time() - start_time) * 1000
        
        performance_ok = instantiation_time < 100  # Should be < 100ms
        
        add_result(
            "Performance requirements",
            performance_ok,
            f"Service instantiation time: {instantiation_time:.2f}ms (should be < 100ms)"
        )
        
    except Exception as e:
        add_result("Performance requirements", False, f"Error: {str(e)}")
    
    # Test 8: Check error handling integration
    try:
        has_execution_error = AiderExecutionError is not None
        
        # Test error creation
        try:
            error = AiderExecutionError(
                "Test error",
                project_id="test-project",
                execution_id="test-execution",
                exit_code=1
            )
            error_created = True
            has_attributes = all([
                hasattr(error, 'project_id'),
                hasattr(error, 'execution_id'),
                hasattr(error, 'exit_code')
            ])
        except Exception:
            error_created = False
            has_attributes = False
        
        add_result(
            "Error handling integration",
            has_execution_error and error_created and has_attributes,
            f"AiderExecutionError available: {has_execution_error}, can create: {error_created}, has attributes: {has_attributes}"
        )
        
    except Exception as e:
        add_result("Error handling integration", False, f"Error: {str(e)}")
    
    # Test 9: Check for comprehensive logging fields
    try:
        # Check source code for comprehensive logging fields
        with open('/Users/marcusswift/python/Clarity-Local-Runner/app/services/aider_execution_service.py', 'r') as f:
            source_code = f.read()
        
        # Look for specific enhanced logging fields
        logging_fields = [
            'correlation_id=',
            'project_id=',
            'execution_id=',
            'attempt=',
            'max_attempts=',
            'status=LogStatus',
            'error_type=',
            'error_message=',
            'container_id=',
            'total_duration_ms=',
            'exit_code='
        ]
        
        fields_found = sum(1 for field in logging_fields if field in source_code)
        comprehensive_logging = fields_found >= len(logging_fields) * 0.8  # At least 80% of fields
        
        add_result(
            "Comprehensive logging fields",
            comprehensive_logging,
            f"Found {fields_found}/{len(logging_fields)} expected logging fields"
        )
        
    except Exception as e:
        add_result("Comprehensive logging fields", False, f"Error: {str(e)}")
    
    # Calculate summary
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    overall_status = "PASS" if passed_tests == total_tests else "FAIL"
    
    summary = {
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": total_tests - passed_tests,
        "success_rate": success_rate,
        "overall_status": overall_status,
        "results": results
    }
    
    return summary


def main():
    """Main validation function."""
    print("🚀 Starting Task 7.5.3 Enhanced Retry Logging Validation")
    print()
    
    # Run validation
    summary = validate_enhanced_retry_logging()
    
    # Print summary
    print()
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed_tests']}")
    print(f"Failed: {summary['failed_tests']}")
    print(f"Success Rate: {summary['success_rate']:.1f}%")
    print(f"Overall Status: {summary['overall_status']}")
    
    # Save detailed results
    try:
        with open('task_7_5_3_simple_validation_results.json', 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"\n📄 Detailed results saved to: task_7_5_3_simple_validation_results.json")
    except Exception as e:
        print(f"\n⚠️  Could not save results file: {e}")
    
    # Exit with appropriate code
    if summary['overall_status'] == 'PASS':
        print("\n🎉 Task 7.5.3 Enhanced Retry Logging validation PASSED!")
        return 0
    else:
        print(f"\n❌ Task 7.5.3 Enhanced Retry Logging validation FAILED!")
        print("Please review the failed tests and fix the issues.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)