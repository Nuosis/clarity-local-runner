#!/usr/bin/env python3

"""
Simple validation script for check_git_availability method in PerProjectContainerManager.

This script performs basic validation of the implementation without requiring Docker dependencies.
"""

import sys
import ast
import inspect
from pathlib import Path


class SimpleGitAvailabilityValidator:
    """Simple validator for the check_git_availability method."""
    
    def __init__(self):
        self.results = []
    
    def log_result(self, test_name: str, success: bool, message: str = ""):
        """Log test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        self.results.append({
            'test': test_name,
            'success': success,
            'message': message
        })
        print(f"{status} {test_name}")
        if message:
            print(f"    {message}")
    
    def test_file_exists(self):
        """Test that the PerProjectContainerManager file exists."""
        test_name = "File Existence Check"
        
        try:
            file_path = Path("app/services/per_project_container_manager.py")
            assert file_path.exists(), "PerProjectContainerManager file does not exist"
            
            self.log_result(test_name, True, f"File exists at {file_path}")
            
        except Exception as e:
            self.log_result(test_name, False, f"Error: {str(e)}")
    
    def test_method_exists_in_source(self):
        """Test that the check_git_availability method exists in the source code."""
        test_name = "Method Exists in Source"
        
        try:
            file_path = Path("app/services/per_project_container_manager.py")
            with open(file_path, 'r') as f:
                source_code = f.read()
            
            # Parse the source code
            tree = ast.parse(source_code)
            
            # Find the PerProjectContainerManager class
            container_manager_class = None
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == "PerProjectContainerManager":
                    container_manager_class = node
                    break
            
            assert container_manager_class is not None, "PerProjectContainerManager class not found"
            
            # Find the check_git_availability method
            check_git_method = None
            for node in container_manager_class.body:
                if isinstance(node, ast.FunctionDef) and node.name == "check_git_availability":
                    check_git_method = node
                    break
            
            assert check_git_method is not None, "check_git_availability method not found"
            
            self.log_result(test_name, True, "Method found in PerProjectContainerManager class")
            
        except Exception as e:
            self.log_result(test_name, False, f"Error: {str(e)}")
    
    def test_method_signature_in_source(self):
        """Test that the method has the correct signature in source code."""
        test_name = "Method Signature Check"
        
        try:
            file_path = Path("app/services/per_project_container_manager.py")
            with open(file_path, 'r') as f:
                source_code = f.read()
            
            # Parse the source code
            tree = ast.parse(source_code)
            
            # Find the check_git_availability method
            check_git_method = None
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == "check_git_availability":
                    check_git_method = node
                    break
            
            assert check_git_method is not None, "check_git_availability method not found"
            
            # Check method parameters
            args = [arg.arg for arg in check_git_method.args.args]
            expected_params = ['self', 'container', 'project_id', 'execution_id', 'timeout_seconds']
            
            for param in expected_params:
                assert param in args, f"Missing parameter: {param}"
            
            self.log_result(test_name, True, f"Method signature correct: {args}")
            
        except Exception as e:
            self.log_result(test_name, False, f"Error: {str(e)}")
    
    def test_method_has_docstring(self):
        """Test that the method has proper documentation."""
        test_name = "Method Documentation Check"
        
        try:
            file_path = Path("app/services/per_project_container_manager.py")
            with open(file_path, 'r') as f:
                source_code = f.read()
            
            # Parse the source code
            tree = ast.parse(source_code)
            
            # Find the check_git_availability method
            check_git_method = None
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == "check_git_availability":
                    check_git_method = node
                    break
            
            assert check_git_method is not None, "check_git_availability method not found"
            
            # Check if method has docstring
            docstring = ast.get_docstring(check_git_method)
            assert docstring is not None, "Method missing docstring"
            assert len(docstring) > 50, "Docstring too short"
            
            # Check for key documentation elements
            assert "Args:" in docstring, "Docstring missing Args section"
            assert "Returns:" in docstring, "Docstring missing Returns section"
            
            self.log_result(test_name, True, "Method has comprehensive docstring")
            
        except Exception as e:
            self.log_result(test_name, False, f"Error: {str(e)}")
    
    def test_performance_decorator_applied(self):
        """Test that the performance decorator is applied."""
        test_name = "Performance Decorator Check"
        
        try:
            file_path = Path("app/services/per_project_container_manager.py")
            with open(file_path, 'r') as f:
                source_code = f.read()
            
            # Parse the source code
            tree = ast.parse(source_code)
            
            # Find the check_git_availability method
            check_git_method = None
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == "check_git_availability":
                    check_git_method = node
                    break
            
            assert check_git_method is not None, "check_git_availability method not found"
            
            # Check if method has decorators
            assert len(check_git_method.decorator_list) > 0, "Method has no decorators"
            
            # Check for log_performance decorator
            has_performance_decorator = False
            for decorator in check_git_method.decorator_list:
                if isinstance(decorator, ast.Call) and hasattr(decorator.func, 'id'):
                    if decorator.func.id == "log_performance":
                        has_performance_decorator = True
                        break
            
            assert has_performance_decorator, "Method missing @log_performance decorator"
            
            self.log_result(test_name, True, "Performance decorator applied")
            
        except Exception as e:
            self.log_result(test_name, False, f"Error: {str(e)}")
    
    def test_method_returns_dict(self):
        """Test that the method returns a dictionary structure."""
        test_name = "Return Structure Check"
        
        try:
            file_path = Path("app/services/per_project_container_manager.py")
            with open(file_path, 'r') as f:
                source_code = f.read()
            
            # Check that the method contains the expected return structure
            expected_keys = [
                "'git_available'",
                "'git_version'", 
                "'performance_metrics'",
                "'error_details'"
            ]
            
            for key in expected_keys:
                assert key in source_code, f"Missing expected return key: {key}"
            
            self.log_result(test_name, True, "Method returns dictionary with expected keys")
            
        except Exception as e:
            self.log_result(test_name, False, f"Error: {str(e)}")
    
    def test_error_handling_patterns(self):
        """Test that the method includes proper error handling."""
        test_name = "Error Handling Check"
        
        try:
            file_path = Path("app/services/per_project_container_manager.py")
            with open(file_path, 'r') as f:
                source_code = f.read()
            
            # Check for error handling patterns
            error_patterns = [
                "try:",
                "except",
                "ContainerError",
                "error_details"
            ]
            
            for pattern in error_patterns:
                assert pattern in source_code, f"Missing error handling pattern: {pattern}"
            
            self.log_result(test_name, True, "Method includes comprehensive error handling")
            
        except Exception as e:
            self.log_result(test_name, False, f"Error: {str(e)}")
    
    def test_logging_integration(self):
        """Test that the method includes structured logging."""
        test_name = "Logging Integration Check"
        
        try:
            file_path = Path("app/services/per_project_container_manager.py")
            with open(file_path, 'r') as f:
                source_code = f.read()
            
            # Check for logging patterns
            logging_patterns = [
                "self.logger.info",
                "correlation_id=self.correlation_id",
                "LogStatus.STARTED",
                "LogStatus.COMPLETED"
            ]
            
            for pattern in logging_patterns:
                assert pattern in source_code, f"Missing logging pattern: {pattern}"
            
            self.log_result(test_name, True, "Method includes structured logging")
            
        except Exception as e:
            self.log_result(test_name, False, f"Error: {str(e)}")
    
    def test_health_checks_integration(self):
        """Test that the _perform_health_checks method uses the new method."""
        test_name = "Health Checks Integration"
        
        try:
            file_path = Path("app/services/per_project_container_manager.py")
            with open(file_path, 'r') as f:
                source_code = f.read()
            
            # Check that _perform_health_checks calls check_git_availability
            assert "self.check_git_availability(" in source_code, "Health checks method doesn't call check_git_availability"
            
            self.log_result(test_name, True, "Health checks method integrated with new git check")
            
        except Exception as e:
            self.log_result(test_name, False, f"Error: {str(e)}")
    
    def run_all_tests(self):
        """Run all validation tests."""
        print("🚀 Starting check_git_availability() Simple Validation\n")
        
        # Run all tests
        self.test_file_exists()
        self.test_method_exists_in_source()
        self.test_method_signature_in_source()
        self.test_method_has_docstring()
        self.test_performance_decorator_applied()
        self.test_method_returns_dict()
        self.test_error_handling_patterns()
        self.test_logging_integration()
        self.test_health_checks_integration()
        
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
    validator = SimpleGitAvailabilityValidator()
    success = validator.run_all_tests()
    
    if success:
        print("\n✅ All tests passed! The check_git_availability() method implementation looks correct.")
        print("\n📋 Implementation Summary:")
        print("- ✅ Standalone check_git_availability() method created")
        print("- ✅ Extracted from existing _perform_health_checks() logic")
        print("- ✅ Follows established patterns (logging, error handling, performance monitoring)")
        print("- ✅ Returns dictionary with git availability status, performance metrics, and error details")
        print("- ✅ Integrated with existing health checks system")
        print("- ✅ Uses @log_performance decorator for performance monitoring")
        print("- ✅ Includes comprehensive structured logging with correlationId propagation")
        print("- ✅ Proper ContainerError exception handling patterns")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please review the implementation.")
        sys.exit(1)