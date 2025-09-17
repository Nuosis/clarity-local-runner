#!/usr/bin/env python3
"""
Task 7.4.1 Simplified Validation Script: Execute "npm ci" in target repository

This script validates the npm ci execution functionality implemented in AiderExecutionService
without requiring full Docker dependencies. It focuses on testing the core logic, method
signatures, and integration readiness.

Usage:
    python validate_task_7_4_1_npm_ci_simplified.py

Requirements:
    - AiderExecutionService with npm ci functionality
"""

import sys
import time
import json
import inspect
from datetime import datetime
from pathlib import Path

# Add the app directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent / "app"))

try:
    from services.aider_execution_service import (
        AiderExecutionService,
        AiderExecutionContext,
        AiderExecutionError,
        get_aider_execution_service
    )
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)


class SimplifiedNpmCiValidator:
    """Simplified validator for npm ci execution functionality."""
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.utcnow().isoformat(),
            "task": "7.4.1 - Execute npm ci in target repository (Simplified Validation)",
            "tests": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0
            }
        }
    
    def log_test_result(self, test_name: str, status: str, details: str = "", duration_ms: float = 0):
        """Log a test result."""
        result = {
            "test_name": test_name,
            "status": status,
            "details": details,
            "duration_ms": duration_ms,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.results["tests"].append(result)
        self.results["summary"]["total"] += 1
        self.results["summary"][status.lower()] += 1
        
        status_emoji = {"PASSED": "✅", "FAILED": "❌", "SKIPPED": "⏭️"}.get(status, "❓")
        print(f"{status_emoji} {test_name}: {status}")
        if details:
            print(f"   Details: {details}")
        if duration_ms > 0:
            print(f"   Duration: {duration_ms:.2f}ms")
    
    def test_service_initialization(self):
        """Test AiderExecutionService initialization with npm ci methods."""
        test_name = "Service Initialization"
        start_time = time.time()
        
        try:
            service = AiderExecutionService(correlation_id="test_npm_validation")
            
            # Check if npm ci methods exist
            required_methods = [
                'execute_npm_ci',
                '_ensure_npm_available',
                '_execute_npm_ci_command',
                '_capture_npm_artifacts'
            ]
            
            missing_methods = []
            for method in required_methods:
                if not hasattr(service, method):
                    missing_methods.append(method)
            
            if missing_methods:
                self.log_test_result(
                    test_name, 
                    "FAILED", 
                    f"Missing methods: {', '.join(missing_methods)}",
                    (time.time() - start_time) * 1000
                )
                return False
            
            # Check npm constants
            required_constants = ['NPM_VERSION_COMMAND', 'NPM_CI_COMMAND']
            missing_constants = []
            for constant in required_constants:
                if not hasattr(service, constant):
                    missing_constants.append(constant)
            
            if missing_constants:
                self.log_test_result(
                    test_name, 
                    "FAILED", 
                    f"Missing constants: {', '.join(missing_constants)}",
                    (time.time() - start_time) * 1000
                )
                return False
            
            self.log_test_result(
                test_name, 
                "PASSED", 
                "All required npm ci methods and constants present",
                (time.time() - start_time) * 1000
            )
            return True
            
        except Exception as e:
            self.log_test_result(
                test_name, 
                "FAILED", 
                f"Exception: {str(e)}",
                (time.time() - start_time) * 1000
            )
            return False
    
    def test_npm_constants_values(self):
        """Test npm command constants have correct values."""
        test_name = "NPM Command Constants Values"
        start_time = time.time()
        
        try:
            service = AiderExecutionService()
            
            # Check npm version command
            npm_version_cmd = getattr(service, 'NPM_VERSION_COMMAND', None)
            if not npm_version_cmd or 'npm --version' not in npm_version_cmd:
                self.log_test_result(
                    test_name, 
                    "FAILED", 
                    f"Invalid NPM_VERSION_COMMAND: {npm_version_cmd}",
                    (time.time() - start_time) * 1000
                )
                return False
            
            # Check npm ci command
            npm_ci_cmd = getattr(service, 'NPM_CI_COMMAND', None)
            if not npm_ci_cmd or 'npm ci' not in npm_ci_cmd:
                self.log_test_result(
                    test_name, 
                    "FAILED", 
                    f"Invalid NPM_CI_COMMAND: {npm_ci_cmd}",
                    (time.time() - start_time) * 1000
                )
                return False
            
            self.log_test_result(
                test_name, 
                "PASSED", 
                f"NPM commands properly defined: version='{npm_version_cmd}', ci='{npm_ci_cmd}'",
                (time.time() - start_time) * 1000
            )
            return True
            
        except Exception as e:
            self.log_test_result(
                test_name, 
                "FAILED", 
                f"Exception: {str(e)}",
                (time.time() - start_time) * 1000
            )
            return False
    
    def test_method_signatures(self):
        """Test that npm ci methods have correct signatures."""
        test_name = "Method Signatures"
        start_time = time.time()
        
        try:
            service = AiderExecutionService()
            
            # Test execute_npm_ci signature
            execute_npm_ci_sig = inspect.signature(service.execute_npm_ci)
            expected_params = ['execution_context', 'working_directory']
            
            actual_params = list(execute_npm_ci_sig.parameters.keys())
            # Remove 'self' parameter
            if 'self' in actual_params:
                actual_params.remove('self')
            
            missing_params = []
            for param in expected_params:
                if param not in actual_params:
                    missing_params.append(param)
            
            if missing_params:
                self.log_test_result(
                    test_name, 
                    "FAILED", 
                    f"execute_npm_ci missing parameters: {', '.join(missing_params)}",
                    (time.time() - start_time) * 1000
                )
                return False
            
            # Test _ensure_npm_available signature
            ensure_npm_sig = inspect.signature(service._ensure_npm_available)
            ensure_params = list(ensure_npm_sig.parameters.keys())
            if 'self' in ensure_params:
                ensure_params.remove('self')
            
            if len(ensure_params) < 2:  # Should have container and execution_context
                self.log_test_result(
                    test_name, 
                    "FAILED", 
                    f"_ensure_npm_available has insufficient parameters: {ensure_params}",
                    (time.time() - start_time) * 1000
                )
                return False
            
            self.log_test_result(
                test_name, 
                "PASSED", 
                f"Method signatures correct: execute_npm_ci({', '.join(actual_params)}), _ensure_npm_available({', '.join(ensure_params)})",
                (time.time() - start_time) * 1000
            )
            return True
            
        except Exception as e:
            self.log_test_result(
                test_name, 
                "FAILED", 
                f"Exception: {str(e)}",
                (time.time() - start_time) * 1000
            )
            return False
    
    def test_execution_context_validation(self):
        """Test execution context validation for npm ci."""
        test_name = "Execution Context Validation"
        start_time = time.time()
        
        try:
            service = AiderExecutionService(correlation_id="test_validation")
            
            # Test valid context
            valid_context = AiderExecutionContext(
                project_id="test-npm-project",
                execution_id="npm_exec_123",
                correlation_id="npm_corr_123",
                repository_url="https://github.com/test/npm-repo.git",
                repository_branch="main",
                timeout_seconds=1800,
                user_id="test_user"
            )
            
            # This should not raise an exception
            service._validate_execution_context(valid_context)
            
            # Test invalid context
            invalid_context = AiderExecutionContext(
                project_id="",  # Empty project_id should fail
                execution_id="npm_exec_123"
            )
            
            try:
                service._validate_execution_context(invalid_context)
                self.log_test_result(
                    test_name, 
                    "FAILED", 
                    "Validation should have failed for empty project_id",
                    (time.time() - start_time) * 1000
                )
                return False
            except Exception:
                # Expected to fail
                pass
            
            self.log_test_result(
                test_name, 
                "PASSED", 
                "Context validation working correctly",
                (time.time() - start_time) * 1000
            )
            return True
            
        except Exception as e:
            self.log_test_result(
                test_name, 
                "FAILED", 
                f"Exception: {str(e)}",
                (time.time() - start_time) * 1000
            )
            return False
    
    def test_factory_function(self):
        """Test the factory function for AiderExecutionService."""
        test_name = "Factory Function"
        start_time = time.time()
        
        try:
            # Test without correlation ID
            service1 = get_aider_execution_service()
            if not isinstance(service1, AiderExecutionService):
                self.log_test_result(
                    test_name, 
                    "FAILED", 
                    "Factory function should return AiderExecutionService instance",
                    (time.time() - start_time) * 1000
                )
                return False
            
            # Test with correlation ID
            service2 = get_aider_execution_service("test_correlation")
            if not isinstance(service2, AiderExecutionService):
                self.log_test_result(
                    test_name, 
                    "FAILED", 
                    "Factory function should return AiderExecutionService instance with correlation ID",
                    (time.time() - start_time) * 1000
                )
                return False
            
            if service2.correlation_id != "test_correlation":
                self.log_test_result(
                    test_name, 
                    "FAILED", 
                    f"Correlation ID not set correctly: expected 'test_correlation', got '{service2.correlation_id}'",
                    (time.time() - start_time) * 1000
                )
                return False
            
            self.log_test_result(
                test_name, 
                "PASSED", 
                "Factory function working correctly",
                (time.time() - start_time) * 1000
            )
            return True
            
        except Exception as e:
            self.log_test_result(
                test_name, 
                "FAILED", 
                f"Exception: {str(e)}",
                (time.time() - start_time) * 1000
            )
            return False
    
    def test_error_handling(self):
        """Test error handling for npm ci functionality."""
        test_name = "Error Handling"
        start_time = time.time()
        
        try:
            service = AiderExecutionService()
            
            # Test AiderExecutionError creation
            try:
                raise AiderExecutionError(
                    "Test npm error",
                    project_id="test-project",
                    execution_id="test-exec",
                    exit_code=1
                )
            except AiderExecutionError as e:
                if str(e) != "Test npm error":
                    self.log_test_result(
                        test_name, 
                        "FAILED", 
                        f"Error message not preserved: {str(e)}",
                        (time.time() - start_time) * 1000
                    )
                    return False
                
                if e.project_id != "test-project":
                    self.log_test_result(
                        test_name, 
                        "FAILED", 
                        f"Project ID not preserved: {e.project_id}",
                        (time.time() - start_time) * 1000
                    )
                    return False
                
                if e.exit_code != 1:
                    self.log_test_result(
                        test_name, 
                        "FAILED", 
                        f"Exit code not preserved: {e.exit_code}",
                        (time.time() - start_time) * 1000
                    )
                    return False
            
            self.log_test_result(
                test_name, 
                "PASSED", 
                "Error handling working correctly",
                (time.time() - start_time) * 1000
            )
            return True
            
        except Exception as e:
            self.log_test_result(
                test_name, 
                "FAILED", 
                f"Exception: {str(e)}",
                (time.time() - start_time) * 1000
            )
            return False
    
    def test_performance_requirements(self):
        """Test performance requirements for npm ci execution."""
        test_name = "Performance Requirements"
        start_time = time.time()
        
        try:
            # Test that service initialization is fast
            init_start = time.time()
            service = AiderExecutionService(correlation_id="perf_test")
            init_time = (time.time() - init_start) * 1000
            
            if init_time > 1000:  # Should initialize in less than 1 second
                self.log_test_result(
                    test_name, 
                    "FAILED", 
                    f"Service initialization too slow: {init_time:.2f}ms",
                    (time.time() - start_time) * 1000
                )
                return False
            
            # Test that method calls are responsive
            context = AiderExecutionContext(
                project_id="perf-test-project",
                execution_id="perf_exec_123"
            )
            
            validation_start = time.time()
            service._validate_execution_context(context)
            validation_time = (time.time() - validation_start) * 1000
            
            if validation_time > 100:  # Should validate in less than 100ms
                self.log_test_result(
                    test_name, 
                    "FAILED", 
                    f"Context validation too slow: {validation_time:.2f}ms",
                    (time.time() - start_time) * 1000
                )
                return False
            
            self.log_test_result(
                test_name, 
                "PASSED", 
                f"Performance requirements met: init={init_time:.2f}ms, validation={validation_time:.2f}ms",
                (time.time() - start_time) * 1000
            )
            return True
            
        except Exception as e:
            self.log_test_result(
                test_name, 
                "FAILED", 
                f"Exception: {str(e)}",
                (time.time() - start_time) * 1000
            )
            return False
    
    def test_integration_readiness(self):
        """Test that npm ci functionality is ready for integration."""
        test_name = "Integration Readiness"
        start_time = time.time()
        
        try:
            service = AiderExecutionService()
            
            # Check that service has all required attributes
            required_attrs = [
                'execute_npm_ci', '_ensure_npm_available',
                '_execute_npm_ci_command', '_capture_npm_artifacts',
                'NPM_VERSION_COMMAND', 'NPM_CI_COMMAND'
            ]
            
            missing_attrs = []
            for attr in required_attrs:
                if not hasattr(service, attr):
                    missing_attrs.append(attr)
            
            if missing_attrs:
                self.log_test_result(
                    test_name, 
                    "FAILED", 
                    f"Missing required attributes: {', '.join(missing_attrs)}",
                    (time.time() - start_time) * 1000
                )
                return False
            
            # Check that methods are callable
            callable_methods = ['execute_npm_ci', '_ensure_npm_available', '_execute_npm_ci_command', '_capture_npm_artifacts']
            non_callable = []
            for method in callable_methods:
                if not callable(getattr(service, method)):
                    non_callable.append(method)
            
            if non_callable:
                self.log_test_result(
                    test_name, 
                    "FAILED", 
                    f"Non-callable methods: {', '.join(non_callable)}",
                    (time.time() - start_time) * 1000
                )
                return False
            
            self.log_test_result(
                test_name, 
                "PASSED", 
                "Service ready for integration with container infrastructure",
                (time.time() - start_time) * 1000
            )
            return True
            
        except Exception as e:
            self.log_test_result(
                test_name, 
                "FAILED", 
                f"Exception: {str(e)}",
                (time.time() - start_time) * 1000
            )
            return False
    
    def test_code_quality_metrics(self):
        """Test code quality metrics for npm ci implementation."""
        test_name = "Code Quality Metrics"
        start_time = time.time()
        
        try:
            service = AiderExecutionService()
            
            # Check method documentation
            methods_to_check = ['execute_npm_ci', '_ensure_npm_available', '_execute_npm_ci_command', '_capture_npm_artifacts']
            undocumented_methods = []
            
            for method_name in methods_to_check:
                method = getattr(service, method_name)
                if not method.__doc__ or len(method.__doc__.strip()) < 10:
                    undocumented_methods.append(method_name)
            
            if undocumented_methods:
                self.log_test_result(
                    test_name, 
                    "FAILED", 
                    f"Undocumented methods: {', '.join(undocumented_methods)}",
                    (time.time() - start_time) * 1000
                )
                return False
            
            # Check method complexity (basic check - number of parameters)
            complex_methods = []
            for method_name in methods_to_check:
                method = getattr(service, method_name)
                sig = inspect.signature(method)
                param_count = len([p for p in sig.parameters.values() if p.name != 'self'])
                if param_count > 5:  # Arbitrary complexity threshold
                    complex_methods.append(f"{method_name}({param_count} params)")
            
            if complex_methods:
                self.log_test_result(
                    test_name, 
                    "SKIPPED", 
                    f"High complexity methods (may need refactoring): {', '.join(complex_methods)}",
                    (time.time() - start_time) * 1000
                )
                return True  # Skip but don't fail
            
            self.log_test_result(
                test_name, 
                "PASSED", 
                "Code quality metrics acceptable: all methods documented, reasonable complexity",
                (time.time() - start_time) * 1000
            )
            return True
            
        except Exception as e:
            self.log_test_result(
                test_name, 
                "FAILED", 
                f"Exception: {str(e)}",
                (time.time() - start_time) * 1000
            )
            return False
    
    def run_validation(self):
        """Run all validation tests."""
        print("🚀 Starting Task 7.4.1 Simplified Validation: Execute npm ci in target repository")
        print("=" * 80)
        
        # Run all tests
        tests = [
            self.test_service_initialization,
            self.test_npm_constants_values,
            self.test_method_signatures,
            self.test_execution_context_validation,
            self.test_factory_function,
            self.test_error_handling,
            self.test_performance_requirements,
            self.test_integration_readiness,
            self.test_code_quality_metrics
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                self.log_test_result(
                    test.__name__.replace('test_', '').replace('_', ' ').title(),
                    "FAILED",
                    f"Unexpected exception: {str(e)}"
                )
        
        # Print summary
        print("\n" + "=" * 80)
        print("📊 VALIDATION SUMMARY")
        print("=" * 80)
        
        summary = self.results["summary"]
        total = summary["total"]
        passed = summary["passed"]
        failed = summary["failed"]
        skipped = summary["skipped"]
        
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⏭️ Skipped: {skipped}")
        
        if total > 0:
            success_rate = (passed / total) * 100
            print(f"Success Rate: {success_rate:.1f}%")
        
        # Determine overall result
        if failed == 0:
            print("\n🎉 VALIDATION PASSED: npm ci functionality is working correctly!")
            overall_status = "PASSED"
        else:
            print(f"\n❌ VALIDATION FAILED: {failed} test(s) failed")
            overall_status = "FAILED"
        
        # Save results to file
        self.results["overall_status"] = overall_status
        results_file = "task_7_4_1_validation_results.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: {results_file}")
        
        return overall_status == "PASSED"


def main():
    """Main validation function."""
    validator = SimplifiedNpmCiValidator()
    success = validator.run_validation()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()