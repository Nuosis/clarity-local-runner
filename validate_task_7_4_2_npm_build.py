#!/usr/bin/env python3
"""
Task 7.4.2 npm run build Implementation Validation Script

This script validates the implementation of npm run build functionality in AiderExecutionService.
It tests the core functionality, error handling, performance requirements, and integration patterns.

Usage:
    python validate_task_7_4_2_npm_build.py

Requirements:
    - Docker environment running
    - AiderExecutionService implementation with npm build functionality
    - Test dependencies available
"""

import sys
import os
import time
import json
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add the app directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

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
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("Make sure you're running this script from the project root directory")
    sys.exit(1)


class NpmBuildValidationResult:
    """Container for validation test results."""
    
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.errors = []
        self.warnings = []
        self.performance_metrics = {}
        self.start_time = time.time()
        self.end_time = None
    
    def add_test_result(self, test_name: str, passed: bool, error: Optional[str] = None, warning: Optional[str] = None):
        """Add a test result."""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
            print(f"✅ {test_name}")
        else:
            self.tests_failed += 1
            print(f"❌ {test_name}")
            if error:
                self.errors.append(f"{test_name}: {error}")
                print(f"   Error: {error}")
        
        if warning:
            self.warnings.append(f"{test_name}: {warning}")
            print(f"   ⚠️  Warning: {warning}")
    
    def add_performance_metric(self, metric_name: str, value: float, unit: str = "ms"):
        """Add a performance metric."""
        self.performance_metrics[metric_name] = {"value": value, "unit": unit}
    
    def finalize(self):
        """Finalize the validation results."""
        self.end_time = time.time()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get validation summary."""
        total_time = (self.end_time or time.time()) - self.start_time
        return {
            "validation_timestamp": datetime.now().isoformat(),
            "total_tests": self.tests_run,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "success_rate": (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0,
            "total_validation_time_seconds": round(total_time, 2),
            "performance_metrics": self.performance_metrics,
            "errors": self.errors,
            "warnings": self.warnings
        }


class NpmBuildValidator:
    """Validator for npm build functionality."""
    
    def __init__(self):
        self.result = NpmBuildValidationResult()
        self.service: Optional[AiderExecutionService] = None
    
    def setup(self) -> bool:
        """Set up the validator."""
        try:
            self.service = AiderExecutionService(correlation_id="npm_build_validation_123")
            return True
        except Exception as e:
            self.result.add_test_result("Service Setup", False, str(e))
            return False
    
    def test_service_initialization(self):
        """Test AiderExecutionService initialization with npm build constants."""
        try:
            # Test service has npm build constants
            has_npm_build_command = hasattr(self.service, 'NPM_BUILD_COMMAND')
            has_build_output_dirs = hasattr(self.service, 'BUILD_OUTPUT_DIRECTORIES')
            has_execute_npm_build = hasattr(self.service, 'execute_npm_build')
            has_execute_npm_build_command = hasattr(self.service, '_execute_npm_build_command')
            has_capture_npm_build_artifacts = hasattr(self.service, '_capture_npm_build_artifacts')
            
            if not all([has_npm_build_command, has_build_output_dirs, has_execute_npm_build, 
                       has_execute_npm_build_command, has_capture_npm_build_artifacts]):
                missing = []
                if not has_npm_build_command: missing.append('NPM_BUILD_COMMAND')
                if not has_build_output_dirs: missing.append('BUILD_OUTPUT_DIRECTORIES')
                if not has_execute_npm_build: missing.append('execute_npm_build')
                if not has_execute_npm_build_command: missing.append('_execute_npm_build_command')
                if not has_capture_npm_build_artifacts: missing.append('_capture_npm_build_artifacts')
                
                self.result.add_test_result(
                    "Service Initialization - npm build methods/constants",
                    False,
                    f"Missing npm build components: {', '.join(missing)}"
                )
                return
            
            # Test npm build command constant
            if self.service.NPM_BUILD_COMMAND != "npm run build":
                self.result.add_test_result(
                    "Service Initialization - NPM_BUILD_COMMAND",
                    False,
                    f"Expected 'npm run build', got '{self.service.NPM_BUILD_COMMAND}'"
                )
                return
            
            # Test build output directories constant
            expected_dirs = ['dist', 'build', 'out', 'public', '.next', 'lib', 'es']
            if not isinstance(self.service.BUILD_OUTPUT_DIRECTORIES, list):
                self.result.add_test_result(
                    "Service Initialization - BUILD_OUTPUT_DIRECTORIES",
                    False,
                    f"Expected list, got {type(self.service.BUILD_OUTPUT_DIRECTORIES)}"
                )
                return
            
            missing_dirs = [d for d in expected_dirs if d not in self.service.BUILD_OUTPUT_DIRECTORIES]
            if missing_dirs:
                self.result.add_test_result(
                    "Service Initialization - BUILD_OUTPUT_DIRECTORIES",
                    False,
                    f"Missing expected directories: {missing_dirs}"
                )
                return
            
            self.result.add_test_result("Service Initialization - npm build functionality", True)
            
        except Exception as e:
            self.result.add_test_result("Service Initialization", False, str(e))
    
    def test_execution_context_validation(self):
        """Test execution context validation for npm build."""
        try:
            # Test valid context
            valid_context = AiderExecutionContext(
                project_id="test-npm-build-project",
                execution_id="npm_build_exec_123",
                correlation_id="npm_build_corr_123",
                repository_url="https://github.com/test/npm-build-repo.git",
                repository_branch="main",
                timeout_seconds=1800,
                user_id="test_user"
            )
            
            # This should not raise an exception
            self.service._validate_execution_context(valid_context)
            self.result.add_test_result("Execution Context Validation - Valid Context", True)
            
            # Test invalid context (empty project_id)
            invalid_context = AiderExecutionContext(
                project_id="",  # Invalid empty project_id
                execution_id="npm_build_exec_123"
            )
            
            try:
                self.service._validate_execution_context(invalid_context)
                self.result.add_test_result(
                    "Execution Context Validation - Invalid Context",
                    False,
                    "Expected ValidationError for empty project_id"
                )
            except ValidationError:
                self.result.add_test_result("Execution Context Validation - Invalid Context", True)
            except Exception as e:
                self.result.add_test_result(
                    "Execution Context Validation - Invalid Context",
                    False,
                    f"Expected ValidationError, got {type(e).__name__}: {e}"
                )
            
        except Exception as e:
            self.result.add_test_result("Execution Context Validation", False, str(e))
    
    def test_npm_build_command_logic(self):
        """Test npm build command execution logic (mocked)."""
        try:
            from unittest.mock import Mock, patch
            
            # Create mock container
            mock_container = Mock()
            mock_container.id = "test_container_123"
            
            # Create test context
            context = AiderExecutionContext(
                project_id="test-npm-build-project",
                execution_id="npm_build_exec_123"
            )
            
            # Test 1: Successful npm build execution
            mock_container.exec_run.side_effect = [
                (0, b""),  # package.json exists
                (0, b'{"scripts": {"build": "webpack --mode production"}}'),  # package.json content
                (0, b"webpack compiled successfully\nnpm build completed")  # npm build success
            ]
            
            result = self.service._execute_npm_build_command(mock_container, context)
            
            if (result['exit_code'] == 0 and 
                result['skipped'] is False and 
                "npm run build" in result['command'] and
                "webpack compiled successfully" in result['stdout']):
                self.result.add_test_result("npm build Command Logic - Success Case", True)
            else:
                self.result.add_test_result(
                    "npm build Command Logic - Success Case",
                    False,
                    f"Unexpected result: {result}"
                )
            
            # Test 2: No package.json
            mock_container.exec_run.side_effect = [
                (1, b"test: No such file or directory")  # package.json doesn't exist
            ]
            
            result = self.service._execute_npm_build_command(mock_container, context)
            
            if (result['exit_code'] == 0 and 
                result['skipped'] is True and 
                result['skip_reason'] == "no_package_json" and
                "No package.json found" in result['stdout']):
                self.result.add_test_result("npm build Command Logic - No package.json", True)
            else:
                self.result.add_test_result(
                    "npm build Command Logic - No package.json",
                    False,
                    f"Unexpected result: {result}"
                )
            
            # Test 3: No build script
            mock_container.exec_run.side_effect = [
                (0, b""),  # package.json exists
                (0, b'{"scripts": {"test": "jest", "start": "node server.js"}}')  # no build script
            ]
            
            result = self.service._execute_npm_build_command(mock_container, context)
            
            if (result['exit_code'] == 0 and 
                result['skipped'] is True and 
                result['skip_reason'] == "no_build_script" and
                "No build script found" in result['stdout']):
                self.result.add_test_result("npm build Command Logic - No build script", True)
            else:
                self.result.add_test_result(
                    "npm build Command Logic - No build script",
                    False,
                    f"Unexpected result: {result}"
                )
            
            # Test 4: Build failure
            mock_container.exec_run.side_effect = [
                (0, b""),  # package.json exists
                (0, b'{"scripts": {"build": "webpack --mode production"}}'),  # package.json content
                (1, b"webpack compilation failed\nERROR in ./src/index.js")  # npm build fails
            ]
            
            result = self.service._execute_npm_build_command(mock_container, context)
            
            if (result['exit_code'] == 1 and 
                result['skipped'] is False and
                "webpack compilation failed" in result['stdout']):
                self.result.add_test_result("npm build Command Logic - Build failure", True)
            else:
                self.result.add_test_result(
                    "npm build Command Logic - Build failure",
                    False,
                    f"Unexpected result: {result}"
                )
            
        except Exception as e:
            self.result.add_test_result("npm build Command Logic", False, str(e))
    
    def test_build_artifact_capture(self):
        """Test build artifact capture logic (mocked)."""
        try:
            from unittest.mock import Mock
            
            # Create mock container
            mock_container = Mock()
            mock_container.id = "test_container_123"
            
            # Create test context
            context = AiderExecutionContext(
                project_id="test-npm-build-project",
                execution_id="npm_build_exec_123"
            )
            
            # Test successful artifact capture with multiple build directories
            execution_result = {
                'exit_code': 0,
                'stdout': 'webpack compiled successfully\nBuild completed',
                'stderr': '',
                'skipped': False
            }
            
            mock_container.exec_run.side_effect = [
                (0, b"8.19.2"),  # npm version
                (0, b""),  # dist directory exists
                (0, b"index.html\nmain.js\nstyle.css"),  # dist directory contents
                (0, b""),  # build directory exists
                (0, b"static/js/main.js"),  # build directory contents
                (1, b""),  # out directory doesn't exist
                (1, b""),  # public directory doesn't exist
                (1, b""),  # .next directory doesn't exist
                (1, b""),  # lib directory doesn't exist
                (1, b"")   # es directory doesn't exist
            ]
            
            artifacts = self.service._capture_npm_build_artifacts(mock_container, context, execution_result)
            
            expected_dirs = {'dist', 'build'}
            expected_artifacts = {'dist/index.html', 'dist/main.js', 'dist/style.css', 'build/static/js/main.js'}
            expected_files_modified = {'dist/', 'build/'}
            
            if (artifacts['npm_version'] == "8.19.2" and
                set(artifacts['build_output_directories']) == expected_dirs and
                set(artifacts['build_artifacts']) == expected_artifacts and
                set(artifacts['files_modified']) == expected_files_modified):
                self.result.add_test_result("Build Artifact Capture - Multiple directories", True)
            else:
                self.result.add_test_result(
                    "Build Artifact Capture - Multiple directories",
                    False,
                    f"Unexpected artifacts: {artifacts}"
                )
            
            # Test skipped build artifact capture
            execution_result_skipped = {
                'exit_code': 0,
                'stdout': 'No package.json found, npm build skipped',
                'stderr': '',
                'skipped': True
            }
            
            mock_container.exec_run.side_effect = [
                (0, b"8.19.2"),  # npm version
            ]
            
            artifacts = self.service._capture_npm_build_artifacts(mock_container, context, execution_result_skipped)
            
            if (artifacts['npm_version'] == "8.19.2" and
                artifacts['build_output_directories'] == [] and
                artifacts['build_artifacts'] == [] and
                artifacts['files_modified'] == []):
                self.result.add_test_result("Build Artifact Capture - Skipped build", True)
            else:
                self.result.add_test_result(
                    "Build Artifact Capture - Skipped build",
                    False,
                    f"Unexpected artifacts for skipped build: {artifacts}"
                )
            
        except Exception as e:
            self.result.add_test_result("Build Artifact Capture", False, str(e))
    
    def test_error_handling(self):
        """Test error handling in npm build functionality."""
        try:
            from unittest.mock import Mock
            
            # Create mock container
            mock_container = Mock()
            mock_container.id = "test_container_123"
            
            # Create test context
            context = AiderExecutionContext(
                project_id="test-npm-build-project",
                execution_id="npm_build_exec_123"
            )
            
            # Test 1: Container execution exception
            mock_container.exec_run.side_effect = Exception("Container execution failed")
            
            try:
                self.service._execute_npm_build_command(mock_container, context)
                self.result.add_test_result(
                    "Error Handling - Container execution exception",
                    False,
                    "Expected AiderExecutionError"
                )
            except AiderExecutionError as e:
                if "npm build command execution failed" in str(e):
                    self.result.add_test_result("Error Handling - Container execution exception", True)
                else:
                    self.result.add_test_result(
                        "Error Handling - Container execution exception",
                        False,
                        f"Unexpected error message: {e}"
                    )
            except Exception as e:
                self.result.add_test_result(
                    "Error Handling - Container execution exception",
                    False,
                    f"Expected AiderExecutionError, got {type(e).__name__}: {e}"
                )
            
            # Test 2: Invalid package.json handling
            mock_container.exec_run.side_effect = [
                (0, b""),  # package.json exists
                (0, b'{"scripts": {"build": "webpack"')  # Invalid JSON (missing closing brace)
            ]
            
            result = self.service._execute_npm_build_command(mock_container, context)
            
            if (result['exit_code'] == 0 and 
                result['skipped'] is True and 
                result['skip_reason'] == "invalid_package_json" and
                "Invalid package.json format" in result['stdout']):
                self.result.add_test_result("Error Handling - Invalid package.json", True)
            else:
                self.result.add_test_result(
                    "Error Handling - Invalid package.json",
                    False,
                    f"Unexpected result: {result}"
                )
            
        except Exception as e:
            self.result.add_test_result("Error Handling", False, str(e))
    
    def test_performance_requirements(self):
        """Test performance requirements for npm build functionality."""
        try:
            from unittest.mock import Mock, patch
            
            # Test that the service can handle the performance requirements
            # This is a basic test since we can't do real performance testing without containers
            
            start_time = time.time()
            
            # Create test context
            context = AiderExecutionContext(
                project_id="test-npm-build-project",
                execution_id="npm_build_exec_123"
            )
            
            # Mock container operations to simulate fast execution
            mock_container = Mock()
            mock_container.id = "test_container_123"
            mock_container.exec_run.side_effect = [
                (0, b""),  # package.json exists
                (0, b'{"scripts": {"build": "webpack"}}'),  # package.json content
                (0, b"npm build completed")  # npm build execution
            ]
            
            # Execute npm build command
            result = self.service._execute_npm_build_command(mock_container, context)
            
            execution_time = time.time() - start_time
            
            # Performance requirement: should complete quickly (mocked operations)
            if execution_time < 1.0:  # Mocked operations should be very fast
                self.result.add_test_result("Performance Requirements - Command execution speed", True)
                self.result.add_performance_metric("npm_build_command_execution_time", execution_time * 1000, "ms")
            else:
                self.result.add_test_result(
                    "Performance Requirements - Command execution speed",
                    False,
                    f"Execution took {execution_time:.2f}s, expected < 1.0s for mocked operations"
                )
            
            # Test that the service has proper timeout handling
            if hasattr(context, 'timeout_seconds') and context.timeout_seconds == 1800:
                self.result.add_test_result("Performance Requirements - Timeout configuration", True)
            else:
                self.result.add_test_result(
                    "Performance Requirements - Timeout configuration",
                    False,
                    f"Expected timeout_seconds=1800, got {getattr(context, 'timeout_seconds', 'None')}"
                )
            
        except Exception as e:
            self.result.add_test_result("Performance Requirements", False, str(e))
    
    def test_integration_patterns(self):
        """Test integration with existing patterns and services."""
        try:
            # Test factory function
            factory_service = get_aider_execution_service("npm_build_test_correlation")
            
            if (isinstance(factory_service, AiderExecutionService) and
                factory_service.correlation_id == "npm_build_test_correlation"):
                self.result.add_test_result("Integration Patterns - Factory function", True)
            else:
                self.result.add_test_result(
                    "Integration Patterns - Factory function",
                    False,
                    f"Factory function returned unexpected service: {factory_service}"
                )
            
            # Test that npm build methods follow the same pattern as npm ci
            npm_ci_method = hasattr(self.service, 'execute_npm_ci')
            npm_build_method = hasattr(self.service, 'execute_npm_build')
            
            if npm_ci_method and npm_build_method:
                self.result.add_test_result("Integration Patterns - Consistent method naming", True)
            else:
                self.result.add_test_result(
                    "Integration Patterns - Consistent method naming",
                    False,
                    f"npm ci method exists: {npm_ci_method}, npm build method exists: {npm_build_method}"
                )
            
            # Test that both methods have similar signatures
            import inspect
            
            if npm_ci_method and npm_build_method:
                ci_sig = inspect.signature(self.service.execute_npm_ci)
                build_sig = inspect.signature(self.service.execute_npm_build)
                
                # Both should have execution_context as first parameter and optional working_directory
                ci_params = list(ci_sig.parameters.keys())
                build_params = list(build_sig.parameters.keys())
                
                if (len(ci_params) >= 1 and len(build_params) >= 1 and
                    ci_params[0] == 'execution_context' and build_params[0] == 'execution_context'):
                    self.result.add_test_result("Integration Patterns - Consistent method signatures", True)
                else:
                    self.result.add_test_result(
                        "Integration Patterns - Consistent method signatures",
                        False,
                        f"npm ci params: {ci_params}, npm build params: {build_params}"
                    )
            
        except Exception as e:
            self.result.add_test_result("Integration Patterns", False, str(e))
    
    def run_validation(self) -> Dict[str, Any]:
        """Run all validation tests."""
        print("🚀 Starting Task 7.4.2 npm run build Implementation Validation")
        print("=" * 70)
        
        if not self.setup():
            print("❌ Setup failed, cannot continue validation")
            return self.result.get_summary()
        
        # Run all validation tests
        self.test_service_initialization()
        self.test_execution_context_validation()
        self.test_npm_build_command_logic()
        self.test_build_artifact_capture()
        self.test_error_handling()
        self.test_performance_requirements()
        self.test_integration_patterns()
        
        # Finalize results
        self.result.finalize()
        
        # Print summary
        print("\n" + "=" * 70)
        print("📊 VALIDATION SUMMARY")
        print("=" * 70)
        
        summary = self.result.get_summary()
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['tests_passed']}")
        print(f"Failed: {summary['tests_failed']}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print(f"Validation Time: {summary['total_validation_time_seconds']}s")
        
        if summary['performance_metrics']:
            print("\n📈 Performance Metrics:")
            for metric, data in summary['performance_metrics'].items():
                print(f"  {metric}: {data['value']:.2f} {data['unit']}")
        
        if summary['errors']:
            print("\n❌ Errors:")
            for error in summary['errors']:
                print(f"  • {error}")
        
        if summary['warnings']:
            print("\n⚠️  Warnings:")
            for warning in summary['warnings']:
                print(f"  • {warning}")
        
        # Overall result
        if summary['tests_failed'] == 0:
            print(f"\n✅ ALL TESTS PASSED - npm run build implementation is valid!")
        else:
            print(f"\n❌ {summary['tests_failed']} TESTS FAILED - npm run build implementation needs fixes")
        
        return summary


def main():
    """Main validation function."""
    try:
        validator = NpmBuildValidator()
        summary = validator.run_validation()
        
        # Save results to file
        results_file = "task_7_4_2_npm_build_validation_results.json"
        with open(results_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: {results_file}")
        
        # Exit with appropriate code
        sys.exit(0 if summary['tests_failed'] == 0 else 1)
        
    except Exception as e:
        print(f"\n💥 Validation script failed with error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()