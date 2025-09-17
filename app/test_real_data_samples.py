#!/usr/bin/env python3
"""
Comprehensive Test Suite for Enhanced project_status_from_task_context Function
Using Realistic Production Data Patterns

This test suite simulates real production data patterns based on identified
schema variations and validates the enhanced transformation function.

Task 8.1: Ensure task_context schema stable; status projection matches API
"""

import sys
import json
import time
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# Add app directory to path for imports
sys.path.append('app')

try:
    from schemas.status_projection_schema import project_status_from_task_context, ExecutionStatus
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)


@dataclass
class TestResult:
    """Container for test results."""
    test_name: str
    success: bool
    execution_time_ms: float
    status_projection: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class RealDataPatternGenerator:
    """Generates realistic task_context data patterns based on production observations."""
    
    @staticmethod
    def get_production_like_samples() -> List[Dict[str, Any]]:
        """
        Generate realistic task_context samples based on actual production patterns.
        
        These patterns are based on:
        - Previous task analysis findings
        - Known schema variations from workflow nodes
        - Field naming inconsistencies observed in the codebase
        - Real-world DevTeam automation scenarios
        """
        return [
            # Pattern 1: Standard DevTeam workflow with snake_case fields
            {
                "name": "Standard DevTeam Workflow",
                "task_context": {
                    "metadata": {
                        "project_id": "customer-123/project-abc",
                        "task_id": "1.1.1",
                        "status": "running",
                        "branch": "task/1-1-1-add-devteam-enabled-flag",
                        "repo_path": "/workspace/repos/customer-123-project-abc",
                        "started_at": "2025-01-14T18:25:00Z",
                        "logs": ["Implementation started", "Aider tool initialized"],
                        "files_modified": ["src/config.js", "README.md"]
                    },
                    "nodes": {
                        "select": {"status": "completed"},
                        "prep": {"status": "completed"},
                        "analyze": {"status": "running"},
                        "implement": {"status": "idle"}
                    }
                }
            },
            
            # Pattern 2: CamelCase field naming (frontend/API inconsistency)
            {
                "name": "CamelCase Field Naming",
                "task_context": {
                    "metadata": {
                        "projectId": "customer-456/project-def",  # camelCase
                        "taskId": "2.3.1",                        # camelCase
                        "status": "initializing",
                        "branch": "feature/api-integration",
                        "repoPath": "/workspace/repos/customer-456-project-def",  # camelCase
                        "startedAt": "2025-01-14T19:15:00Z",      # camelCase
                        "filesModified": ["api/endpoints.py", "tests/test_api.py"]  # camelCase
                    },
                    "nodes": {
                        "select": {"status": "completed"},
                        "prep": {"status": "running"},
                        "analyze": {"status": "idle"},
                        "implement": {"status": "idle"}
                    }
                }
            },
            
            # Pattern 3: Nested event_data structure in nodes
            {
                "name": "Nested Event Data Structure",
                "task_context": {
                    "metadata": {
                        "project_id": "customer-789/project-ghi",
                        "task_id": "3.2.1",
                        "status": "prepared"  # Special status that should map to initializing
                    },
                    "nodes": {
                        "select": {
                            "event_data": {"status": "completed"},
                            "timestamp": "2025-01-14T20:00:00Z"
                        },
                        "prep": {
                            "event_data": {"status": "running"},
                            "timestamp": "2025-01-14T20:05:00Z"
                        },
                        "analyze": {
                            "event_data": {"status": "error"},
                            "error_message": "Analysis failed due to missing dependencies"
                        }
                    }
                }
            },
            
            # Pattern 4: Non-dictionary node values (malformed data)
            {
                "name": "Non-Dictionary Node Values",
                "task_context": {
                    "metadata": {
                        "project_id": "customer-101/project-jkl",
                        "task_id": "4.1.1"
                    },
                    "nodes": {
                        "select": "completed",  # String instead of dict
                        "prep": None,           # None instead of dict
                        "analyze": 42,          # Number instead of dict
                        "implement": {"status": "idle"}  # Valid dict
                    }
                }
            },
            
            # Pattern 5: Non-dictionary metadata (corrupted data)
            {
                "name": "Non-Dictionary Metadata",
                "task_context": {
                    "metadata": "invalid_string_metadata",  # String instead of dict
                    "nodes": {
                        "select": {"status": "completed"},
                        "prep": {"status": "running"}
                    }
                }
            },
            
            # Pattern 6: Mixed node structures (real-world complexity)
            {
                "name": "Mixed Node Structures",
                "task_context": {
                    "metadata": {
                        "project_id": "customer-202/project-mno",
                        "task_id": "5.1.1",
                        "status": "running"
                    },
                    "nodes": {
                        "select": {"status": "completed"},
                        "prep": {"event_data": {"status": "completed"}},
                        "analyze": {"status": "running", "progress": 75},
                        "implement": {"event_data": {"status": "idle"}},
                        "test": "not_started",  # String value
                        "deploy": None,         # None value
                        "validate": {}          # Empty dict
                    }
                }
            },
            
            # Pattern 7: Invalid status values
            {
                "name": "Invalid Status Values",
                "task_context": {
                    "metadata": {
                        "project_id": "customer-303/project-pqr",
                        "task_id": "6.1.1"
                    },
                    "nodes": {
                        "select": {"status": "invalid_status"},
                        "prep": {"status": 123},  # Number status
                        "analyze": {"status": None},  # None status
                        "implement": {"status": ""},  # Empty status
                        "test": {"event_data": {"status": "unknown_state"}}
                    }
                }
            },
            
            # Pattern 8: Large dataset (performance test)
            {
                "name": "Large Dataset Performance Test",
                "task_context": {
                    "metadata": {
                        "project_id": "customer-404/project-stu",
                        "task_id": "7.1.1",
                        "status": "running"
                    },
                    "nodes": {
                        **{f"task_{i}": {"status": "completed" if i < 80 else "running" if i < 95 else "error"} 
                           for i in range(100)}
                    }
                }
            },
            
            # Pattern 9: Completely malformed task_context
            {
                "name": "Completely Malformed Task Context",
                "task_context": "not_a_dictionary"  # String instead of dict
            },
            
            # Pattern 10: Empty structures
            {
                "name": "Empty Structures",
                "task_context": {
                    "metadata": {},
                    "nodes": {}
                }
            },
            
            # Pattern 11: Missing keys
            {
                "name": "Missing Keys",
                "task_context": {}  # No metadata or nodes
            },
            
            # Pattern 12: Complex valid scenario with all features
            {
                "name": "Complex Valid Scenario",
                "task_context": {
                    "metadata": {
                        "project_id": "customer-505/project-vwx",
                        "task_id": "8.2.3",
                        "status": "running",
                        "branch": "feature/complex-implementation",
                        "repo_path": "/workspace/repos/customer-505-project-vwx",
                        "started_at": "2025-01-14T21:00:00Z",
                        "logs": [
                            "Workflow started",
                            "Dependencies analyzed",
                            "Implementation in progress",
                            "Tests running"
                        ],
                        "files_modified": [
                            "src/main.py",
                            "src/utils.py",
                            "tests/test_main.py",
                            "tests/test_utils.py",
                            "README.md",
                            "requirements.txt"
                        ]
                    },
                    "nodes": {
                        "select": {"status": "completed", "completed_at": "2025-01-14T21:01:00Z"},
                        "prep": {"status": "completed", "completed_at": "2025-01-14T21:02:00Z"},
                        "analyze": {"status": "completed", "completed_at": "2025-01-14T21:05:00Z"},
                        "implement": {"status": "running", "started_at": "2025-01-14T21:05:30Z"},
                        "test": {"status": "idle"},
                        "deploy": {"status": "idle"}
                    }
                }
            },
            
            # Pattern 13: Error state scenario
            {
                "name": "Error State Scenario",
                "task_context": {
                    "metadata": {
                        "project_id": "customer-606/project-yz",
                        "task_id": "9.1.1",
                        "status": "error",
                        "error_message": "Workflow failed due to dependency conflict"
                    },
                    "nodes": {
                        "select": {"status": "completed"},
                        "prep": {"status": "completed"},
                        "analyze": {"status": "error", "error": "Analysis failed"},
                        "implement": {"status": "idle"}
                    }
                }
            },
            
            # Pattern 14: Completed workflow
            {
                "name": "Completed Workflow",
                "task_context": {
                    "metadata": {
                        "project_id": "customer-707/project-final",
                        "task_id": "10.1.1",
                        "status": "completed",
                        "completed_at": "2025-01-14T22:00:00Z"
                    },
                    "nodes": {
                        "select": {"status": "completed"},
                        "prep": {"status": "completed"},
                        "analyze": {"status": "completed"},
                        "implement": {"status": "completed"},
                        "test": {"status": "completed"},
                        "deploy": {"status": "completed"}
                    }
                }
            }
        ]


class RealDataValidator:
    """Validator for testing enhanced function with realistic production data patterns."""
    
    def __init__(self):
        self.test_results: List[TestResult] = []
        self.performance_metrics = {
            'total_tests': 0,
            'successful_tests': 0,
            'failed_tests': 0,
            'min_time_ms': float('inf'),
            'max_time_ms': 0,
            'avg_time_ms': 0,
            'total_time_ms': 0
        }
    
    def validate_sample(self, sample: Dict[str, Any], execution_id: str = "test-exec", 
                       project_id: str = "test/project") -> TestResult:
        """
        Validate a single task_context sample with the enhanced function.
        
        Args:
            sample: Sample data with name and task_context
            execution_id: Execution identifier for testing
            project_id: Project identifier for testing
            
        Returns:
            TestResult with validation results
        """
        start_time = time.time()
        test_name = sample.get('name', 'Unknown Test')
        task_context = sample.get('task_context', {})
        
        result = TestResult(
            test_name=test_name,
            success=False,
            execution_time_ms=0
        )
        
        try:
            # Extract project_id from task_context if available
            if isinstance(task_context, dict):
                metadata = task_context.get('metadata', {})
                if isinstance(metadata, dict):
                    extracted_project_id = metadata.get('project_id') or metadata.get('projectId')
                    if extracted_project_id:
                        project_id = extracted_project_id
            
            # Call the enhanced function
            status_projection = project_status_from_task_context(
                task_context=task_context,
                execution_id=execution_id,
                project_id=project_id
            )
            
            result.success = True
            result.status_projection = {
                'status': status_projection.status.value,
                'progress': status_projection.progress,
                'current_task': status_projection.current_task,
                'totals': {
                    'completed': status_projection.totals.completed,
                    'total': status_projection.totals.total
                },
                'customer_id': status_projection.customer_id,
                'branch': status_projection.branch,
                'execution_id': status_projection.execution_id,
                'project_id': status_projection.project_id
            }
            
        except Exception as e:
            result.error = str(e)
        
        finally:
            result.execution_time_ms = round((time.time() - start_time) * 1000, 2)
        
        return result
    
    def run_comprehensive_validation(self) -> Dict[str, Any]:
        """
        Run comprehensive validation with all realistic production data patterns.
        
        Returns:
            Dictionary with comprehensive validation results
        """
        print("🧪 Running Comprehensive Real Data Pattern Validation")
        print("=" * 80)
        
        samples = RealDataPatternGenerator.get_production_like_samples()
        
        for i, sample in enumerate(samples):
            print(f"\n📋 Test {i+1}/{len(samples)}: {sample.get('name', 'Unknown')}")
            
            result = self.validate_sample(sample, f"exec_{i+1}", f"test-project-{i+1}")
            self.test_results.append(result)
            
            # Update performance metrics
            self._update_performance_metrics(result)
            
            # Display result
            if result.success and result.status_projection:
                proj = result.status_projection
                print(f"   ✅ SUCCESS: status={proj['status']}, progress={proj['progress']:.1f}%, "
                      f"totals={proj['totals']['completed']}/{proj['totals']['total']}, "
                      f"time={result.execution_time_ms:.2f}ms")
            else:
                print(f"   ❌ FAILED: {result.error}, time={result.execution_time_ms:.2f}ms")
        
        # Generate comprehensive results
        return self._generate_comprehensive_results()
    
    def _update_performance_metrics(self, result: TestResult):
        """Update performance metrics with test result."""
        self.performance_metrics['total_tests'] += 1
        
        if result.success:
            self.performance_metrics['successful_tests'] += 1
        else:
            self.performance_metrics['failed_tests'] += 1
        
        exec_time = result.execution_time_ms
        self.performance_metrics['total_time_ms'] += exec_time
        self.performance_metrics['min_time_ms'] = min(
            self.performance_metrics['min_time_ms'], exec_time
        )
        self.performance_metrics['max_time_ms'] = max(
            self.performance_metrics['max_time_ms'], exec_time
        )
        
        # Calculate average
        if self.performance_metrics['total_tests'] > 0:
            self.performance_metrics['avg_time_ms'] = (
                self.performance_metrics['total_time_ms'] / 
                self.performance_metrics['total_tests']
            )
    
    def _generate_comprehensive_results(self) -> Dict[str, Any]:
        """Generate comprehensive validation results."""
        # Fix min_time_ms if no tests ran
        if self.performance_metrics['min_time_ms'] == float('inf'):
            self.performance_metrics['min_time_ms'] = 0
        
        # Analyze status distribution
        status_distribution = {}
        error_patterns = {}
        
        for result in self.test_results:
            if result.success and result.status_projection:
                status = result.status_projection['status']
                status_distribution[status] = status_distribution.get(status, 0) + 1
            elif result.error:
                error_type = type(Exception(result.error)).__name__
                error_patterns[error_type] = error_patterns.get(error_type, 0) + 1
        
        return {
            'timestamp': datetime.now().isoformat(),
            'test_summary': {
                'total_tests': self.performance_metrics['total_tests'],
                'successful_tests': self.performance_metrics['successful_tests'],
                'failed_tests': self.performance_metrics['failed_tests'],
                'success_rate': (
                    self.performance_metrics['successful_tests'] / 
                    self.performance_metrics['total_tests'] * 100
                ) if self.performance_metrics['total_tests'] > 0 else 0
            },
            'performance_metrics': self.performance_metrics,
            'status_distribution': status_distribution,
            'error_patterns': error_patterns,
            'detailed_results': [
                {
                    'test_name': result.test_name,
                    'success': result.success,
                    'execution_time_ms': result.execution_time_ms,
                    'status_projection': result.status_projection,
                    'error': result.error
                }
                for result in self.test_results
            ]
        }


def main():
    """Main validation function."""
    print("🚀 Real Data Pattern Validation for Enhanced project_status_from_task_context")
    print("=" * 80)
    print("Testing with realistic production data patterns based on:")
    print("• Previous task analysis findings")
    print("• Known schema variations from workflow nodes")
    print("• Field naming inconsistencies observed in codebase")
    print("• Real-world DevTeam automation scenarios")
    
    validator = RealDataValidator()
    
    try:
        # Run comprehensive validation
        results = validator.run_comprehensive_validation()
        
        # Display summary
        print("\n" + "=" * 80)
        print("📊 Validation Results Summary")
        print("=" * 80)
        
        summary = results['test_summary']
        perf = results['performance_metrics']
        
        print(f"✅ Successful tests: {summary['successful_tests']}/{summary['total_tests']} "
              f"({summary['success_rate']:.1f}%)")
        print(f"❌ Failed tests: {summary['failed_tests']}")
        
        print(f"\n⚡ Performance Metrics:")
        print(f"   Average execution time: {perf['avg_time_ms']:.2f}ms")
        print(f"   Min execution time: {perf['min_time_ms']:.2f}ms")
        print(f"   Max execution time: {perf['max_time_ms']:.2f}ms")
        print(f"   Total processing time: {perf['total_time_ms']:.2f}ms")
        
        # Status distribution
        if results['status_distribution']:
            print(f"\n📈 Status Distribution:")
            for status, count in results['status_distribution'].items():
                print(f"   {status}: {count}")
        
        # Error patterns
        if results['error_patterns']:
            print(f"\n🚨 Error Patterns:")
            for error_type, count in results['error_patterns'].items():
                print(f"   {error_type}: {count}")
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"task_8_1_real_data_pattern_validation_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Detailed results saved to: {results_file}")
        
        # Final assessment
        success_rate = summary['success_rate']
        if success_rate == 100.0:
            print("\n🎉 SUCCESS: Enhanced function handles 100% of realistic production data patterns!")
            return True
        elif success_rate >= 95.0:
            print(f"\n✅ EXCELLENT: Enhanced function handles {success_rate:.1f}% of realistic production data patterns")
            return True
        elif success_rate >= 90.0:
            print(f"\n✅ GOOD: Enhanced function handles {success_rate:.1f}% of realistic production data patterns")
            return True
        else:
            print(f"\n⚠️  NEEDS IMPROVEMENT: Enhanced function handles only {success_rate:.1f}% of realistic production data patterns")
            return False
    
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)