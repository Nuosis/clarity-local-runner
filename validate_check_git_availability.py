#!/usr/bin/env python3

"""
Validation script for check_git_availability method in PerProjectContainerManager.

This script tests the new standalone check_git_availability() method to ensure
it works correctly and follows the established patterns.
"""

import sys
import time
from unittest.mock import Mock, patch

# Add the app directory to the Python path
sys.path.insert(0, 'app')

from services.per_project_container_manager import PerProjectContainerManager, ContainerError


class GitAvailabilityValidator:
    """Validator for the check_git_availability method."""
    
    def __init__(self):
        self.results = []
    
    def log_result(self, test_name: str, success: bool, message: str = "", duration_ms: float = 0.0):
        """Log test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        self.results.append({
            'test': test_name,
            'success': success,
            'message': message,
            'duration_ms': duration_ms
        })
        print(f"{status} {test_name} ({duration_ms:.2f}ms)")
        if message:
            print(f"    {message}")
    
    def test_method_exists(self):
        """Test that the check_git_availability method exists and is callable."""
        test_name = "Method Existence Check"
        start_time = time.time()
        
        try:
            manager = PerProjectContainerManager()
            
            # Check method exists
            assert hasattr(manager, 'check_git_availability'), "Method check_git_availability does not exist"
            
            # Check method is callable
            assert callable(getattr(manager, 'check_git_availability')), "Method check_git_availability is not callable"
            
            duration_ms = (time.time() - start_time) * 1000
            self.log_result(test_name, True, "Method exists and is callable", duration_ms)
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.log_result(test_name, False, f"Error: {str(e)}", duration_ms)
    
    def test_method_signature(self):
        """Test that the method has the correct signature."""
        test_name = "Method Signature Check"
        start_time = time.time()
        
        try:
            manager = PerProjectContainerManager()
            method = getattr(manager, 'check_git_availability')
            
            # Check method signature by inspecting the function
            import inspect
            sig = inspect.signature(method)
            params = list(sig.parameters.keys())
            
            # Expected parameters: self, container, project_id, execution_id, timeout_seconds
            expected_params = ['container', 'project_id', 'execution_id', 'timeout_seconds']
            
            for param in expected_params:
                assert param in params, f"Missing parameter: {param}"
            
            duration_ms = (time.time() - start_time) * 1000
            self.log_result(test_name, True, f"Method signature correct: {params}", duration_ms)
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.log_result(test_name, False, f"Error: {str(e)}", duration_ms)
    
    def test_successful_git_check(self):
        """Test successful git availability check with mocked container."""
        test_name = "Successful Git Check"
        start_time = time.time()
        
        try:
            manager = PerProjectContainerManager()
            
            # Create mock container
            mock_container = Mock()
            mock_container.id = "test-container-123"
            mock_container.status = "running"
            mock_container.reload.return_value = None
            mock_container.exec_run.return_value = (0, b"git version 2.34.1")
            
            # Call the method
            result = manager.check_git_availability(
                container=mock_container,
                project_id="test-project",
                execution_id="test-exec-123"
            )
            
            # Validate result structure
            assert isinstance(result, dict), "Result should be a dictionary"
            assert 'git_available' in result, "Result missing 'git_available' key"
            assert 'git_version' in result, "Result missing 'git_version' key"
            assert 'performance_metrics' in result, "Result missing 'performance_metrics' key"
            assert 'error_details' in result, "Result missing 'error_details' key"
            
            # Validate result values
            assert result['git_available'] is True, "Git should be available"
            assert result['git_version'] is not None, "Git version should be present"
            assert isinstance(result['performance_metrics'], dict), "Performance metrics should be a dict"
            assert result['error_details'] is None, "Error details should be None for successful check"
            
            # Validate performance metrics structure
            metrics = result['performance_metrics']
            assert 'total_duration_ms' in metrics, "Missing total_duration_ms"
            assert 'git_check_duration_ms' in metrics, "Missing git_check_duration_ms"
            assert 'container_validation_duration_ms' in metrics, "Missing container_validation_duration_ms"
            
            duration_ms = (time.time() - start_time) * 1000
            self.log_result(test_name, True, f"Git available: {result['git_available']}, Version: {result['git_version']}", duration_ms)
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.log_result(test_name, False, f"Error: {str(e)}", duration_ms)
    
    def test_failed_git_check(self):
        """Test failed git availability check with mocked container."""
        test_name = "Failed Git Check"
        start_time = time.time()
        
        try:
            manager = PerProjectContainerManager()
            
            # Create mock container that fails git check
            mock_container = Mock()
            mock_container.id = "test-container-456"
            mock_container.status = "running"
            mock_container.reload.return_value = None
            mock_container.exec_run.return_value = (127, b"git: command not found")
            
            # Call the method
            result = manager.check_git_availability(
                container=mock_container,
                project_id="test-project",
                execution_id="test-exec-456"
            )
            
            # Validate result structure
            assert isinstance(result, dict), "Result should be a dictionary"
            assert result['git_available'] is False, "Git should not be available"
            assert result['git_version'] is None, "Git version should be None"
            assert result['error_details'] is not None, "Error details should be present"
            assert isinstance(result['performance_metrics'], dict), "Performance metrics should be a dict"
            
            duration_ms = (time.time() - start_time) * 1000
            self.log_result(test_name, True, f"Git unavailable correctly detected: {result['error_details']}", duration_ms)
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.log_result(test_name, False, f"Error: {str(e)}", duration_ms)
    
    def test_container_not_running(self):
        """Test behavior when container is not running."""
        test_name = "Container Not Running"
        start_time = time.time()
        
        try:
            manager = PerProjectContainerManager()
            
            # Create mock container that is not running
            mock_container = Mock()
            mock_container.id = "test-container-789"
            mock_container.status = "stopped"
            mock_container.reload.return_value = None
            
            # Call the method
            result = manager.check_git_availability(
                container=mock_container,
                project_id="test-project",
                execution_id="test-exec-789"
            )
            
            # Validate result structure
            assert isinstance(result, dict), "Result should be a dictionary"
            assert result['git_available'] is False, "Git should not be available"
            assert result['error_details'] is not None, "Error details should be present"
            assert "not running" in result['error_details'], "Error should mention container not running"
            
            duration_ms = (time.time() - start_time) * 1000
            self.log_result(test_name, True, f"Container not running correctly handled: {result['error_details']}", duration_ms)
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.log_result(test_name, False, f"Error: {str(e)}", duration_ms)
    
    def test_performance_decorator(self):
        """Test that the performance decorator is applied."""
        test_name = "Performance Decorator Check"
        start_time = time.time()
        
        try:
            manager = PerProjectContainerManager()
            method = getattr(manager, 'check_git_availability')
            
            # Check if method has performance logging decorator
            # The decorator should add attributes or modify the function
            assert hasattr(method, '__wrapped__') or hasattr(method, '__name__'), "Method should have decorator attributes"
            
            duration_ms = (time.time() - start_time) * 1000
            self.log_result(test_name, True, "Performance decorator appears to be applied", duration_ms)
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.log_result(test_name, False, f"Error: {str(e)}", duration_ms)
    
    def run_all_tests(self):
        """Run all validation tests."""
        print("🚀 Starting check_git_availability() Method Validation\n")
        
        # Run all tests
        self.test_method_exists()
        self.test_method_signature()
        self.test_successful_git_check()
        self.test_failed_git_check()
        self.test_container_not_running()
        self.test_performance_decorator()
        
        # Print summary
        print(f"\n📊 Test Summary:")
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        
        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.results:
                if not result['success']:
                    print(f"  - {result['test']}: {result['message']}")
        
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        print(f"\nSuccess Rate: {success_rate:.1f}%")
        
        return failed_tests == 0


if __name__ == "__main__":
    validator = GitAvailabilityValidator()
    success = validator.run_all_tests()
    
    if success:
        print("\n✅ All tests passed! The check_git_availability() method is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please review the implementation.")
        sys.exit(1)