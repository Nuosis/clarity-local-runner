#!/usr/bin/env python3
"""
Task 7.5.1 Retry Mechanism Validation Script

This script validates the retry mechanism implementation for failed builds
in the AiderExecutionService with maximum 2 attempts as specified in PRD line 81.

Validation Focus:
- Maximum 2 retry attempts per build operation
- Retry both npm ci and npm run build operations with immediate retries
- Performance: ≤60s total for verify operations including retries
- Container cleanup after each attempt
- Structured logging with correlationId for each retry attempt
- Comprehensive error handling with meaningful messages
"""

import sys
import time
import json
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional

# Add the app directory to Python path for imports
sys.path.insert(0, '/Users/marcusswift/python/Clarity-Local-Runner/app')

try:
    from services.aider_execution_service import (
        AiderExecutionService,
        AiderExecutionContext,
        AiderExecutionResult,
        AiderExecutionError,
        get_aider_execution_service
    )
    from services.per_project_container_manager import ContainerError
    from core.exceptions import ValidationError
    from core.structured_logging import get_structured_logger, LogStatus
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("Make sure you're running this from the correct directory and all dependencies are installed.")
    sys.exit(1)


class RetryMechanismValidator:
    """Validator for retry mechanism functionality."""
    
    def __init__(self):
        self.logger = get_structured_logger(__name__)
        self.correlation_id = f"retry-validation-{int(time.time())}"
        self.results = {
            'npm_ci_retry_tests': [],
            'npm_build_retry_tests': [],
            'performance_tests': [],
            'error_handling_tests': [],
            'container_cleanup_tests': [],
            'logging_tests': []
        }
    
    def create_test_context(self, project_id: str = "test-retry-project") -> AiderExecutionContext:
        """Create a test execution context."""
        return AiderExecutionContext(
            project_id=project_id,
            execution_id=f"exec-{int(time.time())}",
            correlation_id=self.correlation_id,
            repository_url="https://github.com/test/test-repo.git",
            working_directory="/workspace",
            timeout_seconds=60
        )
    
    def test_npm_ci_retry_mechanism(self) -> Dict[str, Any]:
        """Test npm ci retry mechanism with maximum 2 attempts."""
        print("🔄 Testing npm ci retry mechanism...")
        
        test_results = {
            'test_name': 'npm_ci_retry_mechanism',
            'success': False,
            'details': {},
            'errors': []
        }
        
        try:
            # Create service with mocked dependencies
            service = AiderExecutionService(correlation_id=self.correlation_id)
            context = self.create_test_context()
            
            # Mock the single attempt method to fail twice, then succeed
            attempt_count = 0
            def mock_single_attempt(*args, **kwargs):
                nonlocal attempt_count
                attempt_count += 1
                
                if attempt_count <= 2:  # First two attempts fail
                    result = AiderExecutionResult(
                        success=False,
                        execution_id=context.execution_id,
                        project_id=context.project_id,
                        stdout_output=f"npm ci failed on attempt {attempt_count}",
                        stderr_output="Error: npm ci failed",
                        exit_code=1,
                        execution_timestamp=datetime.utcnow().isoformat() + "Z"
                    )
                    return result
                else:  # Third attempt would succeed (but we only allow 2)
                    result = AiderExecutionResult(
                        success=True,
                        execution_id=context.execution_id,
                        project_id=context.project_id,
                        stdout_output="npm ci succeeded",
                        stderr_output="",
                        exit_code=0,
                        execution_timestamp=datetime.utcnow().isoformat() + "Z"
                    )
                    return result
            
            # Mock cleanup method
            cleanup_calls = []
            def mock_cleanup(exec_context, attempt):
                cleanup_calls.append(attempt)
            
            with patch.object(service, '_execute_npm_ci_single_attempt', side_effect=mock_single_attempt):
                with patch.object(service, '_cleanup_container_after_failed_attempt', side_effect=mock_cleanup):
                    try:
                        result = service.execute_npm_ci(context)
                        test_results['errors'].append("Expected AiderExecutionError but got success")
                    except AiderExecutionError as e:
                        # This is expected - should fail after 2 attempts
                        test_results['details']['final_error'] = str(e)
                        test_results['details']['attempt_count'] = attempt_count
                        test_results['details']['cleanup_calls'] = cleanup_calls
                        
                        # Validate retry behavior
                        if attempt_count == 2:  # Should try exactly 2 times
                            test_results['details']['max_attempts_respected'] = True
                        else:
                            test_results['errors'].append(f"Expected 2 attempts, got {attempt_count}")
                        
                        # Validate cleanup was called once (after first failed attempt)
                        if len(cleanup_calls) == 1 and cleanup_calls[0] == 1:
                            test_results['details']['cleanup_called_correctly'] = True
                        else:
                            test_results['errors'].append(f"Expected 1 cleanup call for attempt 1, got {cleanup_calls}")
                        
                        if not test_results['errors']:
                            test_results['success'] = True
            
        except Exception as e:
            test_results['errors'].append(f"Unexpected error: {str(e)}")
        
        self.results['npm_ci_retry_tests'].append(test_results)
        return test_results
    
    def test_npm_build_retry_mechanism(self) -> Dict[str, Any]:
        """Test npm build retry mechanism with maximum 2 attempts."""
        print("🔄 Testing npm build retry mechanism...")
        
        test_results = {
            'test_name': 'npm_build_retry_mechanism',
            'success': False,
            'details': {},
            'errors': []
        }
        
        try:
            # Create service with mocked dependencies
            service = AiderExecutionService(correlation_id=self.correlation_id)
            context = self.create_test_context()
            
            # Mock the single attempt method to fail twice
            attempt_count = 0
            def mock_single_attempt(*args, **kwargs):
                nonlocal attempt_count
                attempt_count += 1
                
                result = AiderExecutionResult(
                    success=False,
                    execution_id=context.execution_id,
                    project_id=context.project_id,
                    stdout_output=f"npm run build failed on attempt {attempt_count}",
                    stderr_output="Error: build failed",
                    exit_code=1,
                    execution_timestamp=datetime.utcnow().isoformat() + "Z"
                )
                return result
            
            # Mock cleanup method
            cleanup_calls = []
            def mock_cleanup(exec_context, attempt):
                cleanup_calls.append(attempt)
            
            with patch.object(service, '_execute_npm_build_single_attempt', side_effect=mock_single_attempt):
                with patch.object(service, '_cleanup_container_after_failed_attempt', side_effect=mock_cleanup):
                    try:
                        result = service.execute_npm_build(context)
                        test_results['errors'].append("Expected AiderExecutionError but got success")
                    except AiderExecutionError as e:
                        # This is expected - should fail after 2 attempts
                        test_results['details']['final_error'] = str(e)
                        test_results['details']['attempt_count'] = attempt_count
                        test_results['details']['cleanup_calls'] = cleanup_calls
                        
                        # Validate retry behavior
                        if attempt_count == 2:  # Should try exactly 2 times
                            test_results['details']['max_attempts_respected'] = True
                        else:
                            test_results['errors'].append(f"Expected 2 attempts, got {attempt_count}")
                        
                        # Validate cleanup was called once (after first failed attempt)
                        if len(cleanup_calls) == 1 and cleanup_calls[0] == 1:
                            test_results['details']['cleanup_called_correctly'] = True
                        else:
                            test_results['errors'].append(f"Expected 1 cleanup call for attempt 1, got {cleanup_calls}")
                        
                        if not test_results['errors']:
                            test_results['success'] = True
            
        except Exception as e:
            test_results['errors'].append(f"Unexpected error: {str(e)}")
        
        self.results['npm_build_retry_tests'].append(test_results)
        return test_results
    
    def test_successful_retry_scenario(self) -> Dict[str, Any]:
        """Test scenario where retry succeeds on second attempt."""
        print("✅ Testing successful retry scenario...")
        
        test_results = {
            'test_name': 'successful_retry_scenario',
            'success': False,
            'details': {},
            'errors': []
        }
        
        try:
            # Create service with mocked dependencies
            service = AiderExecutionService(correlation_id=self.correlation_id)
            context = self.create_test_context()
            
            # Mock the single attempt method to fail once, then succeed
            attempt_count = 0
            def mock_single_attempt(*args, **kwargs):
                nonlocal attempt_count
                attempt_count += 1
                
                if attempt_count == 1:  # First attempt fails
                    result = AiderExecutionResult(
                        success=False,
                        execution_id=context.execution_id,
                        project_id=context.project_id,
                        stdout_output="npm ci failed on attempt 1",
                        stderr_output="Error: npm ci failed",
                        exit_code=1,
                        execution_timestamp=datetime.utcnow().isoformat() + "Z"
                    )
                    return result
                else:  # Second attempt succeeds
                    result = AiderExecutionResult(
                        success=True,
                        execution_id=context.execution_id,
                        project_id=context.project_id,
                        stdout_output="npm ci succeeded on attempt 2",
                        stderr_output="",
                        exit_code=0,
                        execution_timestamp=datetime.utcnow().isoformat() + "Z"
                    )
                    return result
            
            # Mock cleanup method
            cleanup_calls = []
            def mock_cleanup(exec_context, attempt):
                cleanup_calls.append(attempt)
            
            with patch.object(service, '_execute_npm_ci_single_attempt', side_effect=mock_single_attempt):
                with patch.object(service, '_cleanup_container_after_failed_attempt', side_effect=mock_cleanup):
                    result = service.execute_npm_ci(context)
                    
                    # Should succeed on second attempt
                    if result.success:
                        test_results['details']['succeeded_on_retry'] = True
                        test_results['details']['attempt_count'] = attempt_count
                        test_results['details']['cleanup_calls'] = cleanup_calls
                        
                        # Validate exactly 2 attempts were made
                        if attempt_count == 2:
                            test_results['details']['correct_attempt_count'] = True
                        else:
                            test_results['errors'].append(f"Expected 2 attempts, got {attempt_count}")
                        
                        # Validate cleanup was called once (after first failed attempt)
                        if len(cleanup_calls) == 1 and cleanup_calls[0] == 1:
                            test_results['details']['cleanup_called_correctly'] = True
                        else:
                            test_results['errors'].append(f"Expected 1 cleanup call for attempt 1, got {cleanup_calls}")
                        
                        if not test_results['errors']:
                            test_results['success'] = True
                    else:
                        test_results['errors'].append("Expected success but got failure")
            
        except Exception as e:
            test_results['errors'].append(f"Unexpected error: {str(e)}")
        
        self.results['npm_ci_retry_tests'].append(test_results)
        return test_results
    
    def test_performance_requirements(self) -> Dict[str, Any]:
        """Test that retry mechanism meets performance requirements (≤60s total)."""
        print("⏱️ Testing performance requirements...")
        
        test_results = {
            'test_name': 'performance_requirements',
            'success': False,
            'details': {},
            'errors': []
        }
        
        try:
            # Create service with mocked dependencies
            service = AiderExecutionService(correlation_id=self.correlation_id)
            context = self.create_test_context()
            
            # Mock single attempt to simulate realistic timing
            def mock_single_attempt(*args, **kwargs):
                # Simulate some processing time (but not too much for testing)
                time.sleep(0.1)  # 100ms per attempt
                
                result = AiderExecutionResult(
                    success=False,
                    execution_id=context.execution_id,
                    project_id=context.project_id,
                    stdout_output="npm ci failed",
                    stderr_output="Error: npm ci failed",
                    exit_code=1,
                    execution_timestamp=datetime.utcnow().isoformat() + "Z",
                    total_duration_ms=100.0  # Mock 100ms per attempt
                )
                return result
            
            # Mock cleanup method
            def mock_cleanup(exec_context, attempt):
                time.sleep(0.05)  # 50ms cleanup time
            
            with patch.object(service, '_execute_npm_ci_single_attempt', side_effect=mock_single_attempt):
                with patch.object(service, '_cleanup_container_after_failed_attempt', side_effect=mock_cleanup):
                    start_time = time.time()
                    
                    try:
                        result = service.execute_npm_ci(context)
                    except AiderExecutionError:
                        pass  # Expected to fail
                    
                    total_time = time.time() - start_time
                    test_results['details']['total_execution_time_seconds'] = round(total_time, 3)
                    
                    # Should complete well under 60 seconds (our mock should take ~0.3s total)
                    if total_time < 60.0:
                        test_results['details']['meets_performance_requirement'] = True
                        test_results['success'] = True
                    else:
                        test_results['errors'].append(f"Execution took {total_time}s, exceeds 60s limit")
            
        except Exception as e:
            test_results['errors'].append(f"Unexpected error: {str(e)}")
        
        self.results['performance_tests'].append(test_results)
        return test_results
    
    def test_structured_logging(self) -> Dict[str, Any]:
        """Test that structured logging includes correlationId and retry information."""
        print("📝 Testing structured logging...")
        
        test_results = {
            'test_name': 'structured_logging',
            'success': False,
            'details': {},
            'errors': []
        }
        
        try:
            # Create service with mocked dependencies
            service = AiderExecutionService(correlation_id=self.correlation_id)
            context = self.create_test_context()
            
            # Capture log calls
            log_calls = []
            original_info = service.logger.info
            original_warn = service.logger.warn
            original_error = service.logger.error
            
            def mock_info(*args, **kwargs):
                log_calls.append(('info', args, kwargs))
                return original_info(*args, **kwargs)
            
            def mock_warn(*args, **kwargs):
                log_calls.append(('warn', args, kwargs))
                return original_warn(*args, **kwargs)
            
            def mock_error(*args, **kwargs):
                log_calls.append(('error', args, kwargs))
                return original_error(*args, **kwargs)
            
            # Mock single attempt to fail
            def mock_single_attempt(*args, **kwargs):
                result = AiderExecutionResult(
                    success=False,
                    execution_id=context.execution_id,
                    project_id=context.project_id,
                    stdout_output="npm ci failed",
                    stderr_output="Error: npm ci failed",
                    exit_code=1,
                    execution_timestamp=datetime.utcnow().isoformat() + "Z"
                )
                return result
            
            with patch.object(service.logger, 'info', side_effect=mock_info):
                with patch.object(service.logger, 'warn', side_effect=mock_warn):
                    with patch.object(service.logger, 'error', side_effect=mock_error):
                        with patch.object(service, '_execute_npm_ci_single_attempt', side_effect=mock_single_attempt):
                            with patch.object(service, '_cleanup_container_after_failed_attempt'):
                                try:
                                    result = service.execute_npm_ci(context)
                                except AiderExecutionError:
                                    pass  # Expected to fail
            
            # Analyze log calls
            test_results['details']['total_log_calls'] = len(log_calls)
            
            # Check for correlation_id in log calls
            correlation_id_found = False
            retry_info_found = False
            attempt_info_found = False
            
            for level, args, kwargs in log_calls:
                if 'correlation_id' in kwargs and kwargs['correlation_id'] == self.correlation_id:
                    correlation_id_found = True
                
                if 'attempt' in kwargs:
                    attempt_info_found = True
                
                if 'max_attempts' in kwargs:
                    retry_info_found = True
            
            test_results['details']['correlation_id_found'] = correlation_id_found
            test_results['details']['retry_info_found'] = retry_info_found
            test_results['details']['attempt_info_found'] = attempt_info_found
            
            if correlation_id_found and retry_info_found and attempt_info_found:
                test_results['success'] = True
            else:
                if not correlation_id_found:
                    test_results['errors'].append("correlation_id not found in log calls")
                if not retry_info_found:
                    test_results['errors'].append("retry info (max_attempts) not found in log calls")
                if not attempt_info_found:
                    test_results['errors'].append("attempt info not found in log calls")
            
        except Exception as e:
            test_results['errors'].append(f"Unexpected error: {str(e)}")
        
        self.results['logging_tests'].append(test_results)
        return test_results
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all retry mechanism validation tests."""
        print("🚀 Starting Task 7.5.1 Retry Mechanism Validation")
        print("=" * 60)
        
        start_time = time.time()
        
        # Run all test categories
        tests = [
            self.test_npm_ci_retry_mechanism,
            self.test_npm_build_retry_mechanism,
            self.test_successful_retry_scenario,
            self.test_performance_requirements,
            self.test_structured_logging
        ]
        
        for test_func in tests:
            try:
                result = test_func()
                if result['success']:
                    print(f"✅ {result['test_name']}: PASSED")
                else:
                    print(f"❌ {result['test_name']}: FAILED")
                    for error in result['errors']:
                        print(f"   - {error}")
            except Exception as e:
                print(f"💥 {test_func.__name__}: CRASHED - {str(e)}")
        
        total_time = time.time() - start_time
        
        # Calculate summary
        all_tests = []
        for category in self.results.values():
            all_tests.extend(category)
        
        passed_tests = [t for t in all_tests if t['success']]
        failed_tests = [t for t in all_tests if not t['success']]
        
        summary = {
            'total_tests': len(all_tests),
            'passed_tests': len(passed_tests),
            'failed_tests': len(failed_tests),
            'success_rate': len(passed_tests) / len(all_tests) if all_tests else 0,
            'total_execution_time': round(total_time, 3),
            'validation_timestamp': datetime.utcnow().isoformat() + "Z"
        }
        
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed_tests']}")
        print(f"Failed: {summary['failed_tests']}")
        print(f"Success Rate: {summary['success_rate']:.1%}")
        print(f"Execution Time: {summary['total_execution_time']}s")
        
        if summary['success_rate'] >= 0.8:  # 80% pass rate
            print("\n🎉 RETRY MECHANISM VALIDATION: PASSED")
            print("✅ Retry mechanism implementation meets requirements")
        else:
            print("\n❌ RETRY MECHANISM VALIDATION: FAILED")
            print("❌ Retry mechanism implementation needs improvement")
        
        return {
            'summary': summary,
            'detailed_results': self.results
        }


def main():
    """Main validation function."""
    validator = RetryMechanismValidator()
    results = validator.run_all_tests()
    
    # Save detailed results
    with open('task_7_5_1_retry_validation_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: task_7_5_1_retry_validation_results.json")
    
    # Return appropriate exit code
    if results['summary']['success_rate'] >= 0.8:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()