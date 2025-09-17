#!/usr/bin/env python3
"""
Test script for enhanced project_status_from_task_context function.

This script validates that the function gracefully handles all identified
schema variations and edge cases without crashing.
"""

import sys
import traceback
from datetime import datetime
from typing import Dict, Any

# Import the enhanced function
sys.path.append('app')
from schemas.status_projection_schema import project_status_from_task_context, ExecutionStatus


def test_scenario(name: str, task_context: Any, execution_id: str = "test-exec", project_id: str = "test/project") -> bool:
    """Test a specific scenario and return success status."""
    print(f"\n🧪 Testing: {name}")
    print(f"   Input: {task_context}")
    
    try:
        result = project_status_from_task_context(task_context, execution_id, project_id)
        print(f"   ✅ Success: status={result.status.value}, progress={result.progress:.1f}%, totals={result.totals.completed}/{result.totals.total}")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all test scenarios."""
    print("🚀 Testing Enhanced project_status_from_task_context Function")
    print("=" * 60)
    
    test_results = []
    
    # Test 1: Non-dictionary node values
    test_results.append(test_scenario(
        "Non-dictionary node values",
        {
            'metadata': {'task_id': '1.1.1'},
            'nodes': {
                'select': 'completed',  # String instead of dict
                'prep': None,           # None instead of dict
                'analyze': 42,          # Number instead of dict
            }
        }
    ))
    
    # Test 2: Field naming inconsistencies (camelCase)
    test_results.append(test_scenario(
        "CamelCase field naming",
        {
            'metadata': {
                'projectId': 'customer-123/project-abc',  # camelCase
                'taskId': '2.1.1',                        # camelCase
                'repoPath': '/workspace/test',             # camelCase
                'filesModified': ['file1.js', 'file2.py'] # camelCase
            },
            'nodes': {
                'task1': {'status': 'running'},
                'task2': {'status': 'completed'}
            }
        }
    ))
    
    # Test 3: Nested event_data structure
    test_results.append(test_scenario(
        "Nested event_data structure",
        {
            'metadata': {'task_id': '3.1.1'},
            'nodes': {
                'select': {
                    'event_data': {'status': 'completed'}
                },
                'prep': {
                    'event_data': {'status': 'running'}
                }
            }
        }
    ))
    
    # Test 4: Non-dictionary metadata
    test_results.append(test_scenario(
        "Non-dictionary metadata",
        {
            'metadata': 'invalid_string',  # String instead of dict
            'nodes': {
                'task1': {'status': 'completed'}
            }
        }
    ))
    
    # Test 5: Mixed node structures
    test_results.append(test_scenario(
        "Mixed node structures",
        {
            'metadata': {'task_id': '4.1.1'},
            'nodes': {
                'direct_status': {'status': 'completed'},
                'nested_status': {'event_data': {'status': 'running'}},
                'invalid_node': 'not_a_dict',
                'empty_node': {},
                'null_node': None
            }
        }
    ))
    
    # Test 6: Invalid status values
    test_results.append(test_scenario(
        "Invalid status values",
        {
            'metadata': {'task_id': '5.1.1'},
            'nodes': {
                'task1': {'status': 'invalid_status'},
                'task2': {'status': 123},  # Number status
                'task3': {'status': None}, # None status
                'task4': {'status': ''},   # Empty status
            }
        }
    ))
    
    # Test 7: Completely malformed task_context
    test_results.append(test_scenario(
        "Completely malformed task_context",
        "not_a_dictionary"  # String instead of dict
    ))
    
    # Test 8: Empty structures
    test_results.append(test_scenario(
        "Empty structures",
        {
            'metadata': {},
            'nodes': {}
        }
    ))
    
    # Test 9: Missing keys
    test_results.append(test_scenario(
        "Missing keys",
        {}  # No metadata or nodes
    ))
    
    # Test 10: Complex valid scenario with all features
    test_results.append(test_scenario(
        "Complex valid scenario",
        {
            'metadata': {
                'task_id': '6.1.1',
                'status': 'prepared',
                'branch': 'feature/test-branch',
                'repo_path': '/workspace/test-repo',
                'logs': ['Started execution', 'Processing...'],
                'files_modified': ['src/main.py', 'tests/test_main.py'],
                'started_at': '2025-01-14T18:25:00Z'
            },
            'nodes': {
                'select': {'status': 'completed'},
                'prep': {'event_data': {'status': 'running'}},
                'analyze': {'status': 'idle'},
                'implement': {'event_data': {'status': 'error'}}
            }
        }
    ))
    
    # Test 11: Deeply nested invalid structures
    test_results.append(test_scenario(
        "Deeply nested invalid structures",
        {
            'metadata': {
                'task_id': '7.1.1',
                'nested': {
                    'deeply': {
                        'invalid': 'structure'
                    }
                }
            },
            'nodes': {
                'task1': {
                    'event_data': {
                        'nested': {
                            'status': 'completed'  # Too deeply nested
                        }
                    }
                }
            }
        }
    ))
    
    # Test 12: Large dataset performance test
    large_nodes = {}
    for i in range(100):
        large_nodes[f'task_{i}'] = {
            'status': 'completed' if i < 80 else 'running' if i < 95 else 'error'
        }
    
    test_results.append(test_scenario(
        "Large dataset (100 nodes)",
        {
            'metadata': {'task_id': '8.1.1'},
            'nodes': large_nodes
        }
    ))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"✅ Passed: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed! The enhanced function handles all edge cases gracefully.")
        return True
    else:
        print(f"❌ {total - passed} tests failed. Function needs further improvements.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)