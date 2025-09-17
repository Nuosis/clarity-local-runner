#!/usr/bin/env python3
"""
Task Context Schema Stabilization Test Suite
Task 8.1.1: Review and Stabilize task_context Schema

This comprehensive test suite validates:
1. Schema variation handling (snake_case, camelCase, nested event_data)
2. Edge cases for malformed task_context data
3. Performance testing with realistic data volumes
4. Backward compatibility
5. Error handling and graceful degradation
"""

import sys
import time
import traceback
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass

# Add app directory to path for imports
sys.path.append('app')

try:
    from schemas.status_projection_schema import (
        project_status_from_task_context, 
        ExecutionStatus,
        StatusProjection,
        _safe_get_field_with_fallbacks,
        _safe_get_node_status,
        _validate_status_value,
        _process_nodes_single_pass
    )
    from core.exceptions import (
        TaskContextTransformationError,
        InvalidTaskContextError,
        NodeDataError,
        StatusCalculationError,
        FieldExtractionError
    )
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the correct directory with app/ available")
    sys.exit(1)


@dataclass
class TestResult:
    """Test result data structure."""
    name: str
    passed: bool
    duration_ms: float
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class TaskContextSchemaStabilizationTest:
    """Comprehensive test suite for task context schema stabilization."""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.start_time = time.time()
    
    def run_test(self, test_name: str, test_func) -> TestResult:
        """Run a single test and capture results."""
        print(f"\n🧪 Testing: {test_name}")
        start_time = time.time()
        
        try:
            result = test_func()
            duration_ms = (time.time() - start_time) * 1000
            
            if result is True:
                print(f"   ✅ PASSED ({duration_ms:.1f}ms)")
                test_result = TestResult(test_name, True, duration_ms)
            else:
                print(f"   ❌ FAILED: {result}")
                test_result = TestResult(test_name, False, duration_ms, str(result))
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"   ❌ FAILED: {error_msg} ({duration_ms:.1f}ms)")
            test_result = TestResult(test_name, False, duration_ms, error_msg)
            
        self.results.append(test_result)
        return test_result
    
    def test_snake_case_field_handling(self) -> bool:
        """Test snake_case field naming convention."""
        task_context = {
            'metadata': {
                'task_id': '1.1.1',
                'project_id': 'customer-123/project-abc',
                'repo_path': '/workspace/test',
                'files_modified': ['file1.py', 'file2.js'],
                'started_at': '2025-01-17T12:30:00Z'
            },
            'nodes': {
                'select': {'status': 'completed'},
                'prep': {'status': 'running'},
                'implement': {'status': 'idle'}
            }
        }
        
        result = project_status_from_task_context(
            task_context, "test-exec-snake", "customer-123/project-abc"
        )
        
        # Verify correct field extraction
        assert result.current_task == '1.1.1'
        assert result.project_id == 'customer-123/project-abc'
        assert result.customer_id == 'customer-123'
        assert result.artifacts.repo_path == '/workspace/test'
        assert result.artifacts.files_modified == ['file1.py', 'file2.js']
        assert result.status == ExecutionStatus.RUNNING
        assert result.totals.total == 3
        assert result.totals.completed == 1
        
        return True
    
    def test_camel_case_field_handling(self) -> bool:
        """Test camelCase field naming convention."""
        task_context = {
            'metadata': {
                'taskId': '2.1.1',
                'projectId': 'customer-456/project-xyz',
                'repoPath': '/workspace/camel-test',
                'filesModified': ['camel1.py', 'camel2.js'],
                'startedAt': '2025-01-17T12:30:00Z'
            },
            'nodes': {
                'select': {'status': 'completed'},
                'prep': {'status': 'completed'},
                'implement': {'status': 'running'}
            }
        }
        
        result = project_status_from_task_context(
            task_context, "test-exec-camel", "customer-456/project-xyz"
        )
        
        # Verify correct field extraction with camelCase
        assert result.current_task == '2.1.1'
        assert result.project_id == 'customer-456/project-xyz'
        assert result.customer_id == 'customer-456'
        assert result.artifacts.repo_path == '/workspace/camel-test'
        assert result.artifacts.files_modified == ['camel1.py', 'camel2.js']
        assert result.status == ExecutionStatus.RUNNING
        
        return True
    
    def test_nested_event_data_handling(self) -> bool:
        """Test nested event_data structure handling."""
        task_context = {
            'metadata': {
                'task_id': '3.1.1',
                'project_id': 'customer-789/project-nested'
            },
            'nodes': {
                'select': {
                    'event_data': {'status': 'completed', 'timestamp': '2025-01-17T12:35:00Z'}
                },
                'prep': {
                    'event_data': {'status': 'running', 'progress': 50}
                },
                'implement': {
                    'status': 'idle'  # Direct status (should also work)
                }
            }
        }
        
        result = project_status_from_task_context(
            task_context, "test-exec-nested", "customer-789/project-nested"
        )
        
        # Verify nested event_data extraction
        assert result.current_task == '3.1.1'
        assert result.status == ExecutionStatus.RUNNING
        assert result.totals.total == 3
        assert result.totals.completed == 1
        
        return True
    
    def test_mixed_schema_variations(self) -> bool:
        """Test mixed schema variations in single task_context."""
        task_context = {
            'metadata': {
                'taskId': '4.1.1',  # camelCase
                'project_id': 'customer-mixed/project-test',  # snake_case
                'repoPath': '/workspace/mixed',  # camelCase
                'files_modified': ['mixed.py']  # snake_case
            },
            'nodes': {
                'select': {'status': 'completed'},  # Direct status
                'prep': {'event_data': {'status': 'running'}},  # Nested status
                'implement': {'status': 'error'},  # Direct status
                'deploy': {'event_data': {'status': 'idle'}}  # Nested status
            }
        }
        
        result = project_status_from_task_context(
            task_context, "test-exec-mixed", "customer-mixed/project-test"
        )
        
        # Verify mixed schema handling
        assert result.current_task == '4.1.1'
        assert result.project_id == 'customer-mixed/project-test'
        assert result.artifacts.repo_path == '/workspace/mixed'
        assert result.artifacts.files_modified == ['mixed.py']
        assert result.status == ExecutionStatus.ERROR  # Should detect error node
        assert result.totals.total == 4
        
        return True
    
    def test_malformed_task_context_none(self) -> Union[bool, str]:
        """Test handling of None task_context."""
        try:
            project_status_from_task_context(None, "test-exec", "test/project")  # type: ignore
            return "Should have raised InvalidTaskContextError"
        except InvalidTaskContextError as e:
            assert "task_context cannot be None" in str(e)
            return True
        except Exception as e:
            return f"Wrong exception type: {type(e).__name__}: {e}"
    
    def test_malformed_task_context_non_dict(self) -> Union[bool, str]:
        """Test handling of non-dictionary task_context."""
        try:
            project_status_from_task_context("invalid_string", "test-exec", "test/project")  # type: ignore
            return "Should have raised InvalidTaskContextError"
        except InvalidTaskContextError as e:
            assert "must be a dictionary" in str(e)
            return True
        except Exception as e:
            return f"Wrong exception type: {type(e).__name__}: {e}"
    
    def test_malformed_metadata_non_dict(self) -> bool:
        """Test handling of non-dictionary metadata."""
        task_context = {
            'metadata': 'invalid_metadata',  # String instead of dict
            'nodes': {
                'select': {'status': 'completed'}
            }
        }
        
        # Should handle gracefully with degraded operation
        result = project_status_from_task_context(
            task_context, "test-exec-bad-meta", "test/project"
        )
        
        # Should still work but with limited metadata
        assert result.current_task is None  # No task_id available
        assert result.status == ExecutionStatus.COMPLETED
        
        return True
    
    def test_malformed_nodes_non_dict(self) -> bool:
        """Test handling of non-dictionary nodes."""
        task_context = {
            'metadata': {'task_id': '5.1.1'},
            'nodes': 'invalid_nodes'  # String instead of dict
        }
        
        # Should handle gracefully
        result = project_status_from_task_context(
            task_context, "test-exec-bad-nodes", "test/project"
        )
        
        # Should default to IDLE with no nodes
        assert result.status == ExecutionStatus.IDLE
        assert result.totals.total == 0
        assert result.totals.completed == 0
        
        return True
    
    def test_invalid_node_structures(self) -> bool:
        """Test handling of various invalid node structures."""
        task_context = {
            'metadata': {'task_id': '6.1.1'},
            'nodes': {
                'valid_node': {'status': 'completed'},
                'string_node': 'invalid',  # String instead of dict
                'none_node': None,  # None value
                'empty_node': {},  # Empty dict
                'number_node': 42,  # Number instead of dict
                'list_node': ['invalid'],  # List instead of dict
                'no_status_node': {'other_field': 'value'}  # Dict without status
            }
        }
        
        result = project_status_from_task_context(
            task_context, "test-exec-invalid-nodes", "test/project"
        )
        
        # Should only count valid nodes
        assert result.totals.total == 7  # All nodes counted
        assert result.totals.completed == 1  # Only valid_node completed
        assert result.status == ExecutionStatus.RUNNING  # Has some progress
        
        return True
    
    def test_invalid_status_values(self) -> bool:
        """Test handling of invalid status values."""
        task_context = {
            'metadata': {'task_id': '7.1.1'},
            'nodes': {
                'valid_status': {'status': 'completed'},
                'invalid_string': {'status': 'invalid_status'},
                'number_status': {'status': 123},
                'none_status': {'status': None},
                'empty_status': {'status': ''},
                'bool_status': {'status': True}
            }
        }
        
        result = project_status_from_task_context(
            task_context, "test-exec-invalid-status", "test/project"
        )
        
        # Should handle invalid statuses gracefully
        assert result.totals.total == 6
        assert result.totals.completed == 1  # Only valid_status
        
        return True
    
    def test_empty_structures(self) -> bool:
        """Test handling of empty metadata and nodes."""
        task_context = {
            'metadata': {},
            'nodes': {}
        }
        
        result = project_status_from_task_context(
            task_context, "test-exec-empty", "test/project"
        )
        
        # Should handle empty structures
        assert result.current_task is None
        assert result.status == ExecutionStatus.IDLE
        assert result.totals.total == 0
        assert result.totals.completed == 0
        assert result.progress == 0.0
        
        return True
    
    def test_performance_large_dataset(self) -> bool:
        """Test performance with large dataset (1000 nodes)."""
        # Create large dataset
        large_nodes = {}
        for i in range(1000):
            status = 'completed' if i < 800 else 'running' if i < 950 else 'error'
            large_nodes[f'task_{i:04d}'] = {'status': status}
        
        task_context = {
            'metadata': {
                'task_id': '8.1.1',
                'project_id': 'performance/test'
            },
            'nodes': large_nodes
        }
        
        start_time = time.time()
        result = project_status_from_task_context(
            task_context, "test-exec-perf", "performance/test"
        )
        duration_ms = (time.time() - start_time) * 1000
        
        # Verify correctness
        assert result.totals.total == 1000
        assert result.totals.completed == 800
        assert result.status == ExecutionStatus.ERROR  # Has error nodes
        
        # Verify performance (should be well under 2s requirement)
        assert duration_ms < 2000, f"Performance requirement not met: {duration_ms:.1f}ms"
        
        print(f"   📊 Performance: {duration_ms:.1f}ms for 1000 nodes")
        return True
    
    def test_utility_functions(self) -> bool:
        """Test utility functions directly."""
        # Test _safe_get_field_with_fallbacks
        data = {'snake_case': 'value1', 'camelCase': 'value2'}
        
        # Should get snake_case first
        result = _safe_get_field_with_fallbacks(data, 'snake_case', 'camelCase')
        assert result == 'value1'
        
        # Should fallback to camelCase
        result = _safe_get_field_with_fallbacks(data, 'missing', 'camelCase')
        assert result == 'value2'
        
        # Should return default
        result = _safe_get_field_with_fallbacks(data, 'missing1', 'missing2', default='default')
        assert result == 'default'
        
        # Test _safe_get_node_status
        node_direct = {'status': 'completed'}
        assert _safe_get_node_status(node_direct) == 'completed'
        
        node_nested = {'event_data': {'status': 'running'}}
        assert _safe_get_node_status(node_nested) == 'running'
        
        node_invalid = 'not_a_dict'
        assert _safe_get_node_status(node_invalid) is None
        
        # Test _validate_status_value
        assert _validate_status_value('completed') == ExecutionStatus.COMPLETED
        assert _validate_status_value('invalid') == ExecutionStatus.IDLE
        assert _validate_status_value(None) == ExecutionStatus.IDLE
        
        return True
    
    def test_backward_compatibility(self) -> bool:
        """Test backward compatibility with older schema formats."""
        # Old format that might exist in production
        old_task_context = {
            'metadata': {
                'taskId': '9.1.1',  # Old camelCase
                'projectId': 'legacy/project',
                'status': 'prepared'  # Old status field
            },
            'nodes': {
                'node1': {'status': 'completed'},
                'node2': {'status': 'in_progress'}  # Old status value
            }
        }
        
        result = project_status_from_task_context(
            old_task_context, "test-exec-legacy", "legacy/project"
        )
        
        # Should handle old format correctly
        assert result.current_task == '9.1.1'
        assert result.project_id == 'legacy/project'
        assert result.status == ExecutionStatus.RUNNING  # Should derive from nodes
        
        return True
    
    def test_error_recovery_and_logging(self) -> bool:
        """Test error recovery and structured logging."""
        # This should trigger degraded operations but not crash
        problematic_context = {
            'metadata': {
                'task_id': '10.1.1',
                'invalid_timestamp': 'not-a-timestamp',
                'malformed_list': 'should-be-list'
            },
            'nodes': {
                'good_node': {'status': 'completed'},
                'bad_node': {'status': 'invalid_status'},
                'weird_node': {'event_data': {'nested': {'too': {'deep': 'status'}}}}
            }
        }
        
        result = project_status_from_task_context(
            problematic_context, "test-exec-recovery", "test/recovery"
        )
        
        # Should recover gracefully
        assert result is not None
        assert result.current_task == '10.1.1'
        assert result.totals.total == 3
        
        return True
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return summary."""
        print("🚀 Task Context Schema Stabilization Test Suite")
        print("=" * 60)
        print("Task 8.1.1: Review and Stabilize task_context Schema")
        print("=" * 60)
        
        # Schema variation tests
        self.run_test("Snake_case field handling", self.test_snake_case_field_handling)
        self.run_test("CamelCase field handling", self.test_camel_case_field_handling)
        self.run_test("Nested event_data handling", self.test_nested_event_data_handling)
        self.run_test("Mixed schema variations", self.test_mixed_schema_variations)
        
        # Edge case tests
        self.run_test("Malformed task_context (None)", self.test_malformed_task_context_none)
        self.run_test("Malformed task_context (non-dict)", self.test_malformed_task_context_non_dict)
        self.run_test("Malformed metadata (non-dict)", self.test_malformed_metadata_non_dict)
        self.run_test("Malformed nodes (non-dict)", self.test_malformed_nodes_non_dict)
        self.run_test("Invalid node structures", self.test_invalid_node_structures)
        self.run_test("Invalid status values", self.test_invalid_status_values)
        self.run_test("Empty structures", self.test_empty_structures)
        
        # Performance tests
        self.run_test("Performance with large dataset", self.test_performance_large_dataset)
        
        # Utility and compatibility tests
        self.run_test("Utility functions", self.test_utility_functions)
        self.run_test("Backward compatibility", self.test_backward_compatibility)
        self.run_test("Error recovery and logging", self.test_error_recovery_and_logging)
        
        # Generate summary
        total_duration = (time.time() - self.start_time) * 1000
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        
        print("\n" + "=" * 60)
        print("📊 Test Results Summary")
        print("=" * 60)
        
        print(f"✅ Passed: {passed}/{total} ({passed/total*100:.1f}%)")
        print(f"⏱️  Total Duration: {total_duration:.1f}ms")
        
        # Show failed tests
        failed_tests = [r for r in self.results if not r.passed]
        if failed_tests:
            print(f"\n❌ Failed Tests ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"   • {test.name}: {test.error}")
        
        # Performance summary
        perf_tests = [r for r in self.results if 'performance' in r.name.lower()]
        if perf_tests:
            print(f"\n📈 Performance Summary:")
            for test in perf_tests:
                print(f"   • {test.name}: {test.duration_ms:.1f}ms")
        
        success = passed == total
        if success:
            print("\n🎉 All tests passed! Task context schema is stable and robust.")
        else:
            print(f"\n⚠️  {total - passed} tests failed. Schema needs attention.")
        
        return {
            'success': success,
            'passed': passed,
            'total': total,
            'duration_ms': total_duration,
            'failed_tests': [{'name': t.name, 'error': t.error} for t in failed_tests],
            'results': self.results
        }


def main():
    """Main test execution."""
    test_suite = TaskContextSchemaStabilizationTest()
    summary = test_suite.run_all_tests()
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"task_8_1_1_schema_stabilization_results_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        # Convert results to serializable format
        serializable_results = []
        for result in summary['results']:
            serializable_results.append({
                'name': result.name,
                'passed': result.passed,
                'duration_ms': result.duration_ms,
                'error': result.error,
                'details': result.details
            })
        
        summary['results'] = serializable_results
        json.dump(summary, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: {results_file}")
    
    return 0 if summary['success'] else 1


if __name__ == "__main__":
    sys.exit(main())