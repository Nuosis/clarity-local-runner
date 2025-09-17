#!/usr/bin/env python3
"""
Task 7.6.1 Git Merge Validation Script

This script validates the git merge functionality implemented in AiderExecutionService,
testing various merge scenarios including clean merges, conflicts, and error conditions.

Usage:
    python validate_task_7_6_1_git_merge.py

Requirements:
    - Docker environment running
    - AiderExecutionService implementation complete
    - Test repository access (mocked for validation)
"""

import sys
import time
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, MagicMock

# Add the app directory to the Python path for imports
sys.path.insert(0, 'app')

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
    print("✅ Successfully imported required modules")
except ImportError as e:
    print(f"❌ Failed to import required modules: {e}")
    sys.exit(1)


class GitMergeValidationResult:
    """Container for validation test results."""
    
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_results = []
        self.start_time = time.time()
        self.performance_metrics = {}
    
    def add_test_result(self, test_name: str, passed: bool, details: str = "", duration_ms: float = 0):
        """Add a test result."""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
            status = "✅ PASS"
        else:
            self.tests_failed += 1
            status = "❌ FAIL"
        
        result = {
            "test_name": test_name,
            "status": status,
            "passed": passed,
            "details": details,
            "duration_ms": round(duration_ms, 2)
        }
        self.test_results.append(result)
        print(f"{status}: {test_name}")
        if details:
            print(f"    Details: {details}")
        if duration_ms > 0:
            print(f"    Duration: {duration_ms:.2f}ms")
    
    def add_performance_metric(self, metric_name: str, value: float, unit: str = "ms"):
        """Add a performance metric."""
        self.performance_metrics[metric_name] = {
            "value": round(value, 2),
            "unit": unit
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get validation summary."""
        total_duration = (time.time() - self.start_time) * 1000
        return {
            "validation_summary": {
                "total_tests": self.tests_run,
                "tests_passed": self.tests_passed,
                "tests_failed": self.tests_failed,
                "success_rate": round((self.tests_passed / self.tests_run) * 100, 2) if self.tests_run > 0 else 0,
                "total_duration_ms": round(total_duration, 2)
            },
            "performance_metrics": self.performance_metrics,
            "test_results": self.test_results,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }


class GitMergeValidator:
    """Validator for git merge functionality."""
    
    def __init__(self):
        self.result = GitMergeValidationResult()
        self.service = None
    
    def run_validation(self) -> GitMergeValidationResult:
        """Run all validation tests."""
        print("🚀 Starting Task 7.6.1 Git Merge Validation")
        print("=" * 60)
        
        try:
            # Test 1: Service Initialization
            self._test_service_initialization()
            
            # Test 2: Branch Name Validation
            self._test_branch_name_validation()
            
            # Test 3: Conflict Detection Logic
            self._test_conflict_detection()
            
            # Test 4: Git Merge Command Execution
            self._test_git_merge_command_execution()
            
            # Test 5: Artifact Capture
            self._test_artifact_capture()
            
            # Test 6: Full Integration Test
            self._test_full_integration()
            
            # Test 7: Error Handling
            self._test_error_handling()
            
            # Test 8: Performance Requirements
            self._test_performance_requirements()
            
            # Test 9: Edge Cases
            self._test_edge_cases()
            
        except Exception as e:
            self.result.add_test_result(
                "Validation Framework",
                False,
                f"Validation framework error: {str(e)}"
            )
        
        print("\n" + "=" * 60)
        print("🏁 Validation Complete")
        
        summary = self.result.get_summary()
        print(f"📊 Results: {summary['validation_summary']['tests_passed']}/{summary['validation_summary']['total_tests']} tests passed")
        print(f"⏱️  Total Duration: {summary['validation_summary']['total_duration_ms']:.2f}ms")
        
        return self.result
    
    def _test_service_initialization(self):
        """Test AiderExecutionService initialization with git merge methods."""
        try:
            # Test service creation
            self.service = AiderExecutionService(correlation_id="git_merge_validation")
            
            # Check if execute_git_merge method exists
            if hasattr(self.service, 'execute_git_merge'):
                self.result.add_test_result("Service Initialization - execute_git_merge method exists", True)
            else:
                self.result.add_test_result("Service Initialization - execute_git_merge method exists", False, "Method not found")
                return
            
            # Check supporting methods
            supporting_methods = [
                '_validate_branch_names',
                '_execute_git_merge_command',
                '_detect_merge_conflicts',
                '_capture_git_merge_artifacts'
            ]
            
            for method_name in supporting_methods:
                if hasattr(self.service, method_name):
                    self.result.add_test_result(f"Service Initialization - {method_name} method exists", True)
                else:
                    self.result.add_test_result(f"Service Initialization - {method_name} method exists", False, "Method not found")
            
            # Check git command constants
            git_constants = [
                'GIT_CHECKOUT_COMMAND',
                'GIT_MERGE_COMMAND',
                'GIT_STATUS_COMMAND',
                'GIT_LOG_COMMAND'
            ]
            
            for constant_name in git_constants:
                if hasattr(self.service, constant_name):
                    self.result.add_test_result(f"Service Initialization - {constant_name} constant exists", True)
                else:
                    self.result.add_test_result(f"Service Initialization - {constant_name} constant exists", False, "Constant not found")
            
        except Exception as e:
            self.result.add_test_result("Service Initialization", False, f"Error: {str(e)}")
    
    def _test_branch_name_validation(self):
        """Test branch name validation logic."""
        if not self.service:
            self.result.add_test_result("Branch Name Validation", False, "Service not initialized")
            return
        
        try:
            context = AiderExecutionContext(
                project_id="test-project",
                execution_id="test-exec-123"
            )
            
            # Test valid branch names
            valid_cases = [
                ("feature/task-123", "main"),
                ("hotfix/bug-fix", "develop"),
                ("task/456-feature-branch", "release/v1.0")
            ]
            
            for source, target in valid_cases:
                try:
                    self.service._validate_branch_names(source, target, context)
                    self.result.add_test_result(f"Branch Validation - Valid: {source} -> {target}", True)
                except Exception as e:
                    self.result.add_test_result(f"Branch Validation - Valid: {source} -> {target}", False, str(e))
            
            # Test invalid branch names
            invalid_cases = [
                ("", "main", "Empty source branch"),
                ("feature/task-123", "", "Empty target branch"),
                ("main", "main", "Same source and target"),
                ("feature<>branch", "main", "Invalid characters in source"),
                ("feature/task-123", "main<>branch", "Invalid characters in target")
            ]
            
            for source, target, description in invalid_cases:
                try:
                    self.service._validate_branch_names(source, target, context)
                    self.result.add_test_result(f"Branch Validation - Invalid: {description}", False, "Should have raised ValidationError")
                except ValidationError:
                    self.result.add_test_result(f"Branch Validation - Invalid: {description}", True)
                except Exception as e:
                    self.result.add_test_result(f"Branch Validation - Invalid: {description}", False, f"Wrong exception type: {str(e)}")
            
        except Exception as e:
            self.result.add_test_result("Branch Name Validation", False, f"Error: {str(e)}")
    
    def _test_conflict_detection(self):
        """Test merge conflict detection logic."""
        if not self.service:
            self.result.add_test_result("Conflict Detection", False, "Service not initialized")
            return
        
        try:
            # Test conflict detection via exit code
            conflict_detected = self.service._detect_merge_conflicts("Some output", 1)
            self.result.add_test_result("Conflict Detection - Exit code 1", conflict_detected)
            
            # Test conflict detection via output markers
            conflict_outputs = [
                "CONFLICT (content): Merge conflict in file.txt",
                "Automatic merge failed; fix conflicts and then commit the result.",
                "<<<<<<< HEAD\nconflict content\n=======\nother content\n>>>>>>> branch"
            ]
            
            for output in conflict_outputs:
                conflict_detected = self.service._detect_merge_conflicts(output, 0)
                self.result.add_test_result(f"Conflict Detection - Output marker", conflict_detected)
            
            # Test no conflicts
            clean_outputs = [
                "Merge made by the 'recursive' strategy.",
                "Fast-forward merge completed",
                "Already up to date."
            ]
            
            for output in clean_outputs:
                conflict_detected = self.service._detect_merge_conflicts(output, 0)
                self.result.add_test_result(f"Conflict Detection - Clean merge", not conflict_detected)
            
        except Exception as e:
            self.result.add_test_result("Conflict Detection", False, f"Error: {str(e)}")
    
    def _test_git_merge_command_execution(self):
        """Test git merge command execution logic."""
        if not self.service:
            self.result.add_test_result("Git Merge Command Execution", False, "Service not initialized")
            return
        
        try:
            context = AiderExecutionContext(
                project_id="test-project",
                execution_id="test-exec-123",
                repository_url="https://github.com/test/repo.git"
            )
            
            # Mock container for testing
            mock_container = Mock()
            
            # Test successful merge
            mock_container.exec_run.side_effect = [
                (0, b"Switched to branch 'main'"),  # git checkout
                (0, b"Merge made by the 'recursive' strategy.\n 1 file changed, 5 insertions(+)")  # git merge
            ]
            
            result = self.service._execute_git_merge_command(
                mock_container, context, "feature/task-123", "main"
            )
            
            success = (
                result['exit_code'] == 0 and
                result['has_conflicts'] is False and
                result['source_branch'] == "feature/task-123" and
                result['target_branch'] == "main"
            )
            self.result.add_test_result("Git Merge Command - Successful merge", success)
            
            # Test merge with conflicts
            mock_container.exec_run.side_effect = [
                (0, b"Switched to branch 'main'"),  # git checkout
                (1, b"CONFLICT (content): Merge conflict in file.txt\nAutomatic merge failed")  # git merge with conflicts
            ]
            
            result = self.service._execute_git_merge_command(
                mock_container, context, "feature/task-123", "main"
            )
            
            success = (
                result['exit_code'] == 1 and
                result['has_conflicts'] is True and
                "CONFLICT" in result['stdout']
            )
            self.result.add_test_result("Git Merge Command - Merge with conflicts", success)
            
            # Test checkout failure
            mock_container.exec_run.return_value = (128, b"error: pathspec 'nonexistent-branch' did not match any file(s)")
            
            try:
                self.service._execute_git_merge_command(
                    mock_container, context, "feature/task-123", "nonexistent-branch"
                )
                self.result.add_test_result("Git Merge Command - Checkout failure", False, "Should have raised AiderExecutionError")
            except AiderExecutionError as e:
                success = "Failed to checkout target branch" in str(e)
                self.result.add_test_result("Git Merge Command - Checkout failure", success)
            
        except Exception as e:
            self.result.add_test_result("Git Merge Command Execution", False, f"Error: {str(e)}")
    
    def _test_artifact_capture(self):
        """Test artifact capture functionality."""
        if not self.service:
            self.result.add_test_result("Artifact Capture", False, "Service not initialized")
            return
        
        try:
            context = AiderExecutionContext(
                project_id="test-project",
                execution_id="test-exec-123",
                repository_url="https://github.com/test/repo.git"
            )
            
            # Mock container for testing
            mock_container = Mock()
            
            # Test successful merge artifact capture
            execution_result = {
                'exit_code': 0,
                'stdout': 'Merge made by recursive strategy',
                'stderr': '',
                'has_conflicts': False,
                'source_branch': 'feature/task-123',
                'target_branch': 'main'
            }
            
            mock_container.exec_run.side_effect = [
                (0, b"abc123def456789"),  # git log commit hash
                (0, b"commit abc123def456789\nAuthor: Test User\n\nfile1.py\nfile2.js")  # git show
            ]
            
            artifacts = self.service._capture_git_merge_artifacts(
                mock_container, context, execution_result
            )
            
            success = (
                artifacts['commit_hash'] == "abc123def456789" and
                artifacts['has_conflicts'] is False and
                artifacts['source_branch'] == 'feature/task-123' and
                artifacts['target_branch'] == 'main' and
                len(artifacts['files_modified']) > 0
            )
            self.result.add_test_result("Artifact Capture - Successful merge", success)
            
            # Test conflict artifact capture
            execution_result['exit_code'] = 1
            execution_result['has_conflicts'] = True
            
            mock_container.exec_run.return_value = (0, b"UU file1.txt\nAA file2.py")
            
            artifacts = self.service._capture_git_merge_artifacts(
                mock_container, context, execution_result
            )
            
            success = (
                artifacts['has_conflicts'] is True and
                len(artifacts['merge_conflicts']) > 0 and
                'file1.txt' in artifacts['merge_conflicts']
            )
            self.result.add_test_result("Artifact Capture - Merge conflicts", success)
            
        except Exception as e:
            self.result.add_test_result("Artifact Capture", False, f"Error: {str(e)}")
    
    def _test_full_integration(self):
        """Test full git merge integration."""
        if not self.service:
            self.result.add_test_result("Full Integration", False, "Service not initialized")
            return
        
        try:
            context = AiderExecutionContext(
                project_id="test-integration-project",
                execution_id="integration-exec-123",
                repository_url="https://github.com/test/integration-repo.git"
            )
            
            # Mock the container manager and container
            with patch('services.aider_execution_service.get_per_project_container_manager') as mock_get_manager:
                mock_container_manager = Mock()
                mock_get_manager.return_value = mock_container_manager
                self.service.container_manager = mock_container_manager
                
                mock_container_manager.start_or_reuse_container.return_value = {
                    'success': True,
                    'container_id': 'integration_container_123',
                    'container_status': 'started'
                }
                
                mock_container = Mock()
                mock_container.id = 'integration_container_123'
                mock_docker_client = Mock()
                mock_docker_client.containers.get.return_value = mock_container
                mock_container_manager.docker_client = mock_docker_client
                
                # Mock successful integration flow
                mock_container.exec_run.side_effect = [
                    (0, b"Cloning into 'repo'..."),  # Git clone
                    (0, b"Switched to branch 'main'"),  # Git checkout
                    (0, b"Merge made by the 'recursive' strategy.\n 2 files changed, 10 insertions(+)"),  # Git merge
                    (0, b"abc123def456789"),  # Git log commit hash
                    (0, b"file1.py\nfile2.js\nfile3.md")  # Git show files
                ]
                
                start_time = time.time()
                result = self.service.execute_git_merge(context, "feature/integration-test", "main")
                duration = (time.time() - start_time) * 1000
                
                success = (
                    result.success is True and
                    result.exit_code == 0 and
                    result.commit_hash == "abc123def456789" and
                    result.files_modified is not None and
                    len(result.files_modified) > 0 and
                    result.total_duration_ms > 0
                )
                
                self.result.add_test_result("Full Integration - Successful merge", success, f"Duration: {duration:.2f}ms", duration)
                self.result.add_performance_metric("full_integration_duration", duration)
        
        except Exception as e:
            self.result.add_test_result("Full Integration", False, f"Error: {str(e)}")
    
    def _test_error_handling(self):
        """Test error handling scenarios."""
        if not self.service:
            self.result.add_test_result("Error Handling", False, "Service not initialized")
            return
        
        try:
            # Test validation error
            invalid_context = AiderExecutionContext(
                project_id="",  # Invalid empty project_id
                execution_id="test-exec-123"
            )
            
            try:
                self.service.execute_git_merge(invalid_context, "feature/test", "main")
                self.result.add_test_result("Error Handling - Validation error", False, "Should have raised ValidationError")
            except ValidationError:
                self.result.add_test_result("Error Handling - Validation error", True)
            except Exception as e:
                self.result.add_test_result("Error Handling - Validation error", False, f"Wrong exception type: {str(e)}")
            
            # Test branch validation error
            valid_context = AiderExecutionContext(
                project_id="test-project",
                execution_id="test-exec-123"
            )
            
            try:
                self.service.execute_git_merge(valid_context, "", "main")  # Empty source branch
                self.result.add_test_result("Error Handling - Branch validation error", False, "Should have raised ValidationError")
            except ValidationError:
                self.result.add_test_result("Error Handling - Branch validation error", True)
            except Exception as e:
                self.result.add_test_result("Error Handling - Branch validation error", False, f"Wrong exception type: {str(e)}")
            
            # Test container error
            with patch('services.aider_execution_service.get_per_project_container_manager') as mock_get_manager:
                mock_container_manager = Mock()
                mock_get_manager.return_value = mock_container_manager
                self.service.container_manager = mock_container_manager
                
                mock_container_manager.start_or_reuse_container.side_effect = ContainerError(
                    "Container setup failed", project_id=valid_context.project_id
                )
                
                try:
                    self.service.execute_git_merge(valid_context, "feature/test", "main")
                    self.result.add_test_result("Error Handling - Container error", False, "Should have raised ContainerError")
                except ContainerError:
                    self.result.add_test_result("Error Handling - Container error", True)
                except Exception as e:
                    self.result.add_test_result("Error Handling - Container error", False, f"Wrong exception type: {str(e)}")
        
        except Exception as e:
            self.result.add_test_result("Error Handling", False, f"Error: {str(e)}")
    
    def _test_performance_requirements(self):
        """Test performance requirements (≤60s target)."""
        if not self.service:
            self.result.add_test_result("Performance Requirements", False, "Service not initialized")
            return
        
        try:
            context = AiderExecutionContext(
                project_id="test-performance-project",
                execution_id="performance-exec-123",
                repository_url="https://github.com/test/performance-repo.git"
            )
            
            with patch('services.aider_execution_service.get_per_project_container_manager') as mock_get_manager:
                mock_container_manager = Mock()
                mock_get_manager.return_value = mock_container_manager
                self.service.container_manager = mock_container_manager
                
                mock_container_manager.start_or_reuse_container.return_value = {
                    'success': True,
                    'container_id': 'performance_container_123',
                    'container_status': 'started'
                }
                
                mock_container = Mock()
                mock_container.id = 'performance_container_123'
                mock_docker_client = Mock()
                mock_docker_client.containers.get.return_value = mock_container
                mock_container_manager.docker_client = mock_docker_client
                
                # Mock fast operations
                mock_container.exec_run.side_effect = [
                    (0, b"Cloning into 'repo'..."),  # Git clone
                    (0, b"Switched to branch 'main'"),  # Git checkout
                    (0, b"Merge completed"),  # Git merge
                    (0, b"abc123def456789"),  # Git log commit hash
                ]
                
                start_time = time.time()
                result = self.service.execute_git_merge(context, "feature/performance-test", "main")
                execution_time = time.time() - start_time
                
                # Performance requirement: ≤60s
                performance_met = execution_time <= 60.0 and result.total_duration_ms <= 60000
                
                self.result.add_test_result(
                    "Performance Requirements - ≤60s target",
                    performance_met,
                    f"Execution time: {execution_time:.2f}s, Total duration: {result.total_duration_ms:.2f}ms"
                )
                
                self.result.add_performance_metric("git_merge_execution_time", execution_time * 1000)
                self.result.add_performance_metric("git_merge_total_duration", result.total_duration_ms)
        
        except Exception as e:
            self.result.add_test_result("Performance Requirements", False, f"Error: {str(e)}")
    
    def _test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        if not self.service:
            self.result.add_test_result("Edge Cases", False, "Service not initialized")
            return
        
        try:
            # Test with no repository URL
            context_no_repo = AiderExecutionContext(
                project_id="test-no-repo-project",
                execution_id="no-repo-exec-123",
                repository_url=None
            )
            
            with patch('services.aider_execution_service.get_per_project_container_manager') as mock_get_manager:
                mock_container_manager = Mock()
                mock_get_manager.return_value = mock_container_manager
                self.service.container_manager = mock_container_manager
                
                mock_container_manager.start_or_reuse_container.return_value = {
                    'success': True,
                    'container_id': 'no_repo_container_123',
                    'container_status': 'started'
                }
                
                mock_container = Mock()
                mock_container.id = 'no_repo_container_123'
                mock_docker_client = Mock()
                mock_docker_client.containers.get.return_value = mock_container
                mock_container_manager.docker_client = mock_docker_client
                
                # Mock operations without git clone
                mock_container.exec_run.side_effect = [
                    (0, b"Switched to branch 'main'"),  # Git checkout
                    (0, b"Merge completed"),  # Git merge
                    (0, b"abc123def456789"),  # Git log commit hash
                    (0, b"file1.py")  # Git show files
                ]
                
                result = self.service.execute_git_merge(context_no_repo, "feature/test", "main")
                
                success = result.success is True and result.exit_code == 0
                self.result.add_test_result("Edge Cases - No repository URL", success)
            
            # Test with custom working directory
            context_custom_dir = AiderExecutionContext(
                project_id="test-custom-dir-project",
                execution_id="custom-dir-exec-123",
                repository_url="https://github.com/test/custom-dir-repo.git"
            )
            
            with patch('services.aider_execution_service.get_per_project_container_manager') as mock_get_manager:
                mock_container_manager = Mock()
                mock_get_manager.return_value = mock_container_manager
                self.service.container_manager = mock_container_manager
                
                mock_container_manager.start_or_reuse_container.return_value = {
                    'success': True,
                    'container_id': 'custom_dir_container_123',
                    'container_status': 'started'
                }
                
                mock_container = Mock()
                mock_container.id = 'custom_dir_container_123'
                mock_docker_client = Mock()
                mock_docker_client.containers.get.return_value = mock_container
                mock_container_manager.docker_client = mock_docker_client
                
                mock_container.exec_run.side_effect = [
                    (0, b"Cloning into 'repo'..."),  # Git clone
                    (0, b"Switched to branch 'main'"),  # Git checkout
                    (0, b"Merge completed"),  # Git merge
                    (0, b"abc123def456789"),  # Git log commit hash
                    (0, b"file1.py")  # Git show files
                ]
                
                custom_working_dir = "/custom/project/path"
                result = self.service.execute_git_merge(
                    context_custom_dir, 
                    "feature/test", 
                    "main",
                    custom_working_dir
                )
                
                success = result.success is True and result.exit_code == 0
                self.result.add_test_result("Edge Cases - Custom working directory", success)
        
        except Exception as e:
            self.result.add_test_result("Edge Cases", False, f"Error: {str(e)}")


def main():
    """Main validation function."""
    validator = GitMergeValidator()
    result = validator.run_validation()
    
    # Save results to file
    results_file = "task_7_6_1_git_merge_validation_results.json"
    with open(results_file, 'w') as f:
        json.dump(result.get_summary(), f, indent=2)
    
    print(f"\n📄 Detailed results saved to: {results_file}")
    
    # Return appropriate exit code
    if result.tests_failed == 0:
        print("🎉 All tests passed!")
        return 0
    else:
        print(f"⚠️  {result.tests_failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())