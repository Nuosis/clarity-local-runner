#!/usr/bin/env python3
"""
Task 7.6.1 Git Merge Validation Script (Simplified)
Tests the execute_git_merge() functionality in AiderExecutionService
"""

import sys
import os
import json
import time
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock, patch

# Add the app directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    from services.aider_execution_service import AiderExecutionService
    from services.per_project_container_manager import PerProjectContainerManager
    from core.structured_logging import LogStatus
    print("✅ Successfully imported required modules")
except ImportError as e:
    print(f"❌ Failed to import required modules: {e}")
    sys.exit(1)

class GitMergeValidator:
    """Validates git merge functionality in AiderExecutionService"""
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.utcnow().isoformat(),
            "task": "7.6.1 - Git Merge Implementation",
            "tests": {},
            "summary": {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "performance_metrics": {}
            }
        }
        
    def log_test_result(self, test_name: str, success: bool, details: Dict[str, Any]):
        """Log test result"""
        self.results["tests"][test_name] = {
            "success": success,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.results["summary"]["total_tests"] += 1
        if success:
            self.results["summary"]["passed"] += 1
            print(f"✅ {test_name}")
        else:
            self.results["summary"]["failed"] += 1
            print(f"❌ {test_name}: {details.get('error', 'Unknown error')}")
    
    def test_service_initialization(self) -> bool:
        """Test AiderExecutionService can be initialized"""
        try:
            # Initialize service (it gets its own dependencies)
            service = AiderExecutionService(correlation_id="test-correlation-id")
            
            # Verify service has required attributes
            assert hasattr(service, 'execute_git_merge'), "Service missing execute_git_merge method"
            assert hasattr(service, '_validate_branch_names'), "Service missing _validate_branch_names method"
            assert hasattr(service, '_execute_git_merge_command'), "Service missing _execute_git_merge_command method"
            assert hasattr(service, '_detect_merge_conflicts'), "Service missing _detect_merge_conflicts method"
            assert hasattr(service, '_capture_git_merge_artifacts'), "Service missing _capture_git_merge_artifacts method"
            
            self.log_test_result("service_initialization", True, {
                "service_type": type(service).__name__,
                "methods_found": [
                    "execute_git_merge",
                    "_validate_branch_names", 
                    "_execute_git_merge_command",
                    "_detect_merge_conflicts",
                    "_capture_git_merge_artifacts"
                ]
            })
            return True
            
        except Exception as e:
            self.log_test_result("service_initialization", False, {"error": str(e)})
            return False
    
    def test_branch_validation(self) -> bool:
        """Test branch name validation"""
        try:
            service = AiderExecutionService(correlation_id="test-correlation-id")
            
            # Test valid branch names
            valid_branches = [
                ("main", "task/123-feature-branch"),
                ("main", "task/456-bug-fix"),
                ("develop", "feature/new-feature")
            ]
            
            for target, source in valid_branches:
                try:
                    service._validate_branch_names(source, target, Mock())
                except Exception as e:
                    raise AssertionError(f"Valid branches {target}, {source} failed validation: {e}")
            
            # Test invalid branch names
            invalid_branches = [
                ("", "task/123-feature"),  # Empty target
                ("main", ""),  # Empty source
                ("main", "../malicious"),  # Path traversal
                ("main", "task/123; rm -rf /"),  # Command injection
            ]
            
            for target, source in invalid_branches:
                try:
                    service._validate_branch_names(source, target, Mock())
                    raise AssertionError(f"Invalid branches {target}, {source} should have failed validation")
                except ValueError:
                    pass  # Expected validation error
            
            self.log_test_result("branch_validation", True, {
                "valid_branches_tested": len(valid_branches),
                "invalid_branches_tested": len(invalid_branches)
            })
            return True
            
        except Exception as e:
            self.log_test_result("branch_validation", False, {"error": str(e)})
            return False
    
    def test_conflict_detection(self) -> bool:
        """Test merge conflict detection"""
        try:
            service = AiderExecutionService(correlation_id="test-correlation-id")
            
            # Test successful merge (exit code 0)
            success_result = service._detect_merge_conflicts("Merge made by the 'recursive' strategy.", 0)
            assert success_result is False
            
            # Test merge conflict (exit code 1)
            conflict_output = """Auto-merging file1.txt
CONFLICT (content): Merge conflict in file1.txt
Auto-merging file2.py
CONFLICT (content): Merge conflict in file2.py
Automatic merge failed; fix conflicts and then commit the result."""
            
            conflict_result = service._detect_merge_conflicts(conflict_output, 1)
            assert conflict_result is True
            
            # Test other error (exit code 128)
            error_result = service._detect_merge_conflicts("fatal: not a git repository", 128)
            assert error_result is False
            
            self.log_test_result("conflict_detection", True, {
                "success_case": success_result,
                "conflict_case": conflict_result,
                "error_case": error_result
            })
            return True
            
        except Exception as e:
            self.log_test_result("conflict_detection", False, {"error": str(e)})
            return False
    
    def test_git_merge_command_execution(self) -> bool:
        """Test git merge command execution with mocked container"""
        try:
            # Create mock container and container manager
            mock_container = Mock()
            mock_container_manager = Mock(spec=PerProjectContainerManager)
            mock_container_manager.get_container.return_value = mock_container
            
            # Mock successful git checkout
            checkout_result = Mock()
            checkout_result.exit_code = 0
            checkout_result.output = b"Switched to branch 'main'"
            
            # Mock successful git merge
            merge_result = Mock()
            merge_result.exit_code = 0
            merge_result.output = b"Merge made by the 'recursive' strategy.\n file1.txt | 2 +-\n 1 file changed, 1 insertion(+), 1 deletion(-)"
            
            # Configure container.exec_run to return different results based on command
            def mock_exec_run(cmd, **kwargs):
                if "git checkout" in cmd:
                    return checkout_result
                elif "git merge" in cmd:
                    return merge_result
                else:
                    result = Mock()
                    result.exit_code = 0
                    result.output = b"mock output"
                    return result
            
            mock_container.exec_run = mock_exec_run
            
            # Initialize service
            service = AiderExecutionService(correlation_id="test-correlation-id")
            
            # Execute git merge command
            result = service._execute_git_merge_command(
                mock_container,
                Mock(),  # context
                "task/123-feature",  # source_branch
                "main",  # target_branch
                None  # working_directory
            )
            
            # Verify results
            assert result["exit_code"] == 0
            assert result["stdout"] is not None
            assert result["source_branch"] == "task/123-feature"
            assert result["target_branch"] == "main"
            
            self.log_test_result("git_merge_command_execution", True, {
                "exit_code": result["exit_code"],
                "stdout_length": len(result["stdout"]),
                "source_branch": result["source_branch"],
                "target_branch": result["target_branch"]
            })
            return True
            
        except Exception as e:
            self.log_test_result("git_merge_command_execution", False, {"error": str(e)})
            return False
    
    def test_artifact_capture(self) -> bool:
        """Test artifact capture functionality"""
        try:
            # Create mock container and container manager
            mock_container = Mock()
            mock_container_manager = Mock(spec=PerProjectContainerManager)
            mock_container_manager.get_container.return_value = mock_container
            
            # Mock git log command for commit hash
            log_result = Mock()
            log_result.exit_code = 0
            log_result.output = b"abc123def456789"
            
            # Mock git diff command for files modified
            diff_result = Mock()
            diff_result.exit_code = 0
            diff_result.output = b"file1.txt\nfile2.py\nREADME.md"
            
            def mock_exec_run(cmd, **kwargs):
                if "git log -1 --format=%H" in cmd:
                    return log_result
                elif "git diff --name-only" in cmd:
                    return diff_result
                else:
                    result = Mock()
                    result.exit_code = 0
                    result.output = b"mock output"
                    return result
            
            mock_container.exec_run = mock_exec_run
            
            # Initialize service
            service = AiderExecutionService(correlation_id="test-correlation-id")
            
            # Mock execution result
            mock_execution_result = {
                "exit_code": 0,
                "stdout": "Merge successful",
                "source_branch": "task/123-feature",
                "target_branch": "main",
                "has_conflicts": False
            }
            
            # Capture artifacts
            artifacts = service._capture_git_merge_artifacts(
                mock_container,
                Mock(),  # context
                mock_execution_result,
                None  # working_directory
            )
            
            # Verify artifacts
            assert artifacts["commit_hash"] == "abc123def456789"
            assert artifacts["files_modified"] == ["file1.txt", "file2.py", "README.md"]
            assert "target_branch" in artifacts
            assert "source_branch" in artifacts
            
            self.log_test_result("artifact_capture", True, {
                "commit_hash": artifacts["commit_hash"],
                "files_modified_count": len(artifacts["files_modified"]),
                "target_branch": artifacts["target_branch"],
                "source_branch": artifacts["source_branch"]
            })
            return True
            
        except Exception as e:
            self.log_test_result("artifact_capture", False, {"error": str(e)})
            return False
    
    def test_full_integration(self) -> bool:
        """Test full git merge integration"""
        try:
            start_time = time.time()
            
            # Create comprehensive mocks
            mock_container = Mock()
            mock_container_manager = Mock(spec=PerProjectContainerManager)
            mock_container_manager.get_container.return_value = mock_container
            
            # Mock all git commands
            def mock_exec_run(cmd, **kwargs):
                result = Mock()
                result.exit_code = 0
                
                if "git checkout" in cmd:
                    result.output = b"Switched to branch 'main'"
                elif "git merge" in cmd:
                    result.output = b"Merge made by the 'recursive' strategy.\n file1.txt | 2 +-\n 1 file changed, 1 insertion(+), 1 deletion(-)"
                elif "git log -1 --format=%H" in cmd:
                    result.output = b"abc123def456789"
                elif "git diff --name-only" in cmd:
                    result.output = b"file1.txt\nfile2.py"
                else:
                    result.output = b"mock output"
                
                return result
            
            mock_container.exec_run = mock_exec_run
            
            # Initialize service
            service = AiderExecutionService(correlation_id="test-correlation-id")
            
            # Create mock execution context
            from services.aider_execution_service import AiderExecutionContext
            mock_context = AiderExecutionContext(
                project_id="test-project",
                execution_id="test-execution",
                repository_url="https://github.com/test/repo.git"
            )
            
            # Execute full git merge
            with patch.object(service, '_log_performance') as mock_log_perf:
                result = service.execute_git_merge(
                    mock_context,
                    "task/123-feature",  # source_branch
                    "main",  # target_branch
                    None  # working_directory
                )
            
            execution_time = time.time() - start_time
            
            # Verify results
            success = (
                result.success is True and
                result.exit_code == 0 and
                result.commit_hash == "abc123def456789" and
                result.files_modified is not None and
                len(result.files_modified) > 0 and
                result.total_duration_ms > 0
            )
            
            # Check performance requirement (≤60s)
            performance_ok = execution_time < 60.0
            
            self.results["summary"]["performance_metrics"]["full_integration_time_ms"] = execution_time * 1000
            
            self.log_test_result("full_integration", success and performance_ok, {
                "execution_time_ms": execution_time * 1000,
                "performance_requirement_met": performance_ok,
                "result_success": result.success,
                "exit_code": result.exit_code,
                "commit_hash": result.commit_hash,
                "files_modified_count": len(result.files_modified) if result.files_modified else 0,
                "total_duration_ms": result.total_duration_ms
            })
            return success and performance_ok
            
        except Exception as e:
            self.log_test_result("full_integration", False, {"error": str(e)})
            return False
    
    def test_error_handling(self) -> bool:
        """Test error handling scenarios"""
        try:
            service = AiderExecutionService(correlation_id="test-correlation-id")
            
            # Create invalid execution context
            from services.aider_execution_service import AiderExecutionContext
            invalid_context = AiderExecutionContext(
                project_id="",  # Invalid empty project_id
                execution_id="test-execution"
            )
            
            # Test invalid execution context
            try:
                result = service.execute_git_merge(
                    invalid_context,
                    "task/123-feature",
                    "main"
                )
                assert False, "Should have raised ValidationError for invalid context"
            except Exception as e:
                assert "ValidationError" in str(type(e)) or "ValueError" in str(type(e))
            
            # Test invalid branch names
            valid_context = AiderExecutionContext(
                project_id="test-project",
                execution_id="test-execution"
            )
            
            try:
                result = service.execute_git_merge(
                    valid_context,
                    "",  # Invalid empty source branch
                    "main"
                )
                assert False, "Should have raised ValidationError for empty source branch"
            except Exception as e:
                assert "ValidationError" in str(type(e)) or "ValueError" in str(type(e))
            
            self.log_test_result("error_handling", True, {
                "validation_error_handled": True,
                "branch_validation_handled": True
            })
            return True
            
        except Exception as e:
            self.log_test_result("error_handling", False, {"error": str(e)})
            return False
    
    def run_all_tests(self) -> bool:
        """Run all validation tests"""
        print("🚀 Starting Task 7.6.1 Git Merge Validation")
        print("=" * 60)
        
        tests = [
            self.test_service_initialization,
            self.test_branch_validation,
            self.test_conflict_detection,
            self.test_git_merge_command_execution,
            self.test_artifact_capture,
            self.test_full_integration,
            self.test_error_handling
        ]
        
        all_passed = True
        for test in tests:
            if not test():
                all_passed = False
        
        # Calculate success rate
        total = self.results["summary"]["total_tests"]
        passed = self.results["summary"]["passed"]
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print("\n" + "=" * 60)
        print(f"📊 VALIDATION SUMMARY")
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {self.results['summary']['failed']}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if all_passed:
            print("✅ All tests passed! Git merge functionality is working correctly.")
        else:
            print("❌ Some tests failed. Please review the results above.")
        
        return all_passed
    
    def save_results(self, filename: str = "task_7_6_1_git_merge_validation_results.json"):
        """Save validation results to JSON file"""
        try:
            with open(filename, 'w') as f:
                json.dump(self.results, f, indent=2)
            print(f"📄 Results saved to {filename}")
        except Exception as e:
            print(f"❌ Failed to save results: {e}")

def main():
    """Main validation function"""
    validator = GitMergeValidator()
    
    try:
        success = validator.run_all_tests()
        validator.save_results()
        
        if success:
            print("\n🎉 Task 7.6.1 validation completed successfully!")
            print("Git merge functionality is ready for production use.")
            return 0
        else:
            print("\n⚠️  Task 7.6.1 validation completed with issues.")
            print("Please review the failed tests and fix any issues.")
            return 1
            
    except Exception as e:
        print(f"\n💥 Validation failed with error: {e}")
        validator.save_results()
        return 1

if __name__ == "__main__":
    sys.exit(main())