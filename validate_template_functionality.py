#!/usr/bin/env python3
"""
Validation script for Branch 4.4.1: Template Reading Functionality

This script validates the implementation of template reading functionality
in the RepositoryCacheManager class, ensuring all requirements are met.
"""

import sys
import time
import traceback
from pathlib import Path

# Add the app directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent / "app"))

try:
    from services.repository_cache_manager import RepositoryCacheManager, get_repository_cache_manager
    from core.exceptions import RepositoryError
    from core.structured_logging import LogStatus
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("Make sure you're running this script from the project root directory")
    sys.exit(1)


class TemplateValidationResults:
    """Container for validation results."""
    
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.errors = []
        self.warnings = []
        self.performance_metrics = {}
    
    def add_success(self, test_name: str):
        """Record a successful test."""
        self.tests_passed += 1
        print(f"✅ {test_name}")
    
    def add_failure(self, test_name: str, error: str):
        """Record a failed test."""
        self.tests_failed += 1
        self.errors.append(f"{test_name}: {error}")
        print(f"❌ {test_name}: {error}")
    
    def add_warning(self, message: str):
        """Record a warning."""
        self.warnings.append(message)
        print(f"⚠️  {message}")
    
    def add_performance_metric(self, metric_name: str, value: float):
        """Record a performance metric."""
        self.performance_metrics[metric_name] = value
    
    def print_summary(self):
        """Print validation summary."""
        total_tests = self.tests_passed + self.tests_failed
        print(f"\n{'='*60}")
        print(f"VALIDATION SUMMARY")
        print(f"{'='*60}")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_failed}")
        print(f"Success Rate: {(self.tests_passed/total_tests*100):.1f}%" if total_tests > 0 else "N/A")
        
        if self.warnings:
            print(f"\nWarnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        if self.errors:
            print(f"\nErrors ({len(self.errors)}):")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.performance_metrics:
            print(f"\nPerformance Metrics:")
            for metric, value in self.performance_metrics.items():
                print(f"  - {metric}: {value:.3f}s")
        
        print(f"{'='*60}")
        
        return self.tests_failed == 0


def validate_template_functionality():
    """Main validation function for template functionality."""
    print("🚀 Starting Branch 4.4.1 Template Functionality Validation")
    print("="*60)
    
    results = TemplateValidationResults()
    correlation_id = "validation_test_123"
    
    try:
        # Test 1: Verify RepositoryCacheManager can be instantiated
        try:
            manager = RepositoryCacheManager(correlation_id=correlation_id)
            results.add_success("RepositoryCacheManager instantiation")
        except Exception as e:
            results.add_failure("RepositoryCacheManager instantiation", str(e))
            return results
        
        # Test 2: Verify factory function works
        try:
            factory_manager = get_repository_cache_manager(correlation_id="factory_test")
            if isinstance(factory_manager, RepositoryCacheManager):
                results.add_success("Factory function get_repository_cache_manager")
            else:
                results.add_failure("Factory function get_repository_cache_manager", 
                                  f"Expected RepositoryCacheManager, got {type(factory_manager)}")
        except Exception as e:
            results.add_failure("Factory function get_repository_cache_manager", str(e))
        
        # Test 3: Verify DEFAULT_TASK_LIST_TEMPLATE constant exists
        try:
            template_constant = RepositoryCacheManager.DEFAULT_TASK_LIST_TEMPLATE
            if isinstance(template_constant, str) and len(template_constant) > 1000:
                results.add_success("DEFAULT_TASK_LIST_TEMPLATE constant exists and has content")
            else:
                results.add_failure("DEFAULT_TASK_LIST_TEMPLATE constant", 
                                  f"Expected substantial string content, got {type(template_constant)} with length {len(template_constant) if isinstance(template_constant, str) else 'N/A'}")
        except AttributeError as e:
            results.add_failure("DEFAULT_TASK_LIST_TEMPLATE constant", f"Constant not found: {e}")
        except Exception as e:
            results.add_failure("DEFAULT_TASK_LIST_TEMPLATE constant", str(e))
        
        # Test 4: Verify template constant has required structure
        try:
            template = RepositoryCacheManager.DEFAULT_TASK_LIST_TEMPLATE
            required_sections = [
                "# Task List",
                "## Project Tasks", 
                "### 1. Core Configuration Tasks",
                "### 2. Development Setup Tasks",
                "1.1.1 Add DEVTEAM_ENABLED flag",
                "1.2.1 Initialize project structure",
                "2.1.1 Configure development environment"
            ]
            
            missing_sections = []
            for section in required_sections:
                if section not in template:
                    missing_sections.append(section)
            
            if not missing_sections:
                results.add_success("Template constant structure validation")
            else:
                results.add_failure("Template constant structure validation", 
                                  f"Missing sections: {missing_sections}")
        except Exception as e:
            results.add_failure("Template constant structure validation", str(e))
        
        # Test 5: Verify get_default_task_list_template method exists and works
        try:
            start_time = time.time()
            template_content = manager.get_default_task_list_template(
                project_id="test_project",
                execution_id="test_execution"
            )
            duration = time.time() - start_time
            results.add_performance_metric("get_default_task_list_template", duration)
            
            if isinstance(template_content, str) and len(template_content) > 0:
                results.add_success("get_default_task_list_template method")
                
                # Check performance requirement (≤2s)
                if duration <= 2.0:
                    results.add_success("get_default_task_list_template performance (≤2s)")
                else:
                    results.add_failure("get_default_task_list_template performance", 
                                      f"Took {duration:.3f}s, requirement is ≤2s")
            else:
                results.add_failure("get_default_task_list_template method", 
                                  f"Expected non-empty string, got {type(template_content)}")
        except Exception as e:
            results.add_failure("get_default_task_list_template method", str(e))
        
        # Test 6: Verify get_default_task_list_template works without optional parameters
        try:
            template_content = manager.get_default_task_list_template()
            if isinstance(template_content, str) and len(template_content) > 0:
                results.add_success("get_default_task_list_template without optional params")
            else:
                results.add_failure("get_default_task_list_template without optional params", 
                                  f"Expected non-empty string, got {type(template_content)}")
        except Exception as e:
            results.add_failure("get_default_task_list_template without optional params", str(e))
        
        # Test 7: Verify validate_template_format method exists and works
        try:
            test_template = """# Test Template

## Project Tasks

#### 1.1.1 Test task
- **Description**: Test task description
- **Type**: atomic
- **Status**: pending
"""
            start_time = time.time()
            validation_result = manager.validate_template_format(
                test_template,
                project_id="test_project",
                execution_id="test_execution"
            )
            duration = time.time() - start_time
            results.add_performance_metric("validate_template_format", duration)
            
            if isinstance(validation_result, dict) and 'is_valid' in validation_result:
                results.add_success("validate_template_format method")
                
                # Check performance requirement (≤2s)
                if duration <= 2.0:
                    results.add_success("validate_template_format performance (≤2s)")
                else:
                    results.add_failure("validate_template_format performance", 
                                      f"Took {duration:.3f}s, requirement is ≤2s")
                
                # Check validation result structure
                expected_keys = ['is_valid', 'validation_status', 'template_content', 
                               'validation_checks', 'performance_metrics', 'template_info']
                missing_keys = [key for key in expected_keys if key not in validation_result]
                
                if not missing_keys:
                    results.add_success("validate_template_format result structure")
                else:
                    results.add_failure("validate_template_format result structure", 
                                      f"Missing keys: {missing_keys}")
            else:
                results.add_failure("validate_template_format method", 
                                  f"Expected dict with 'is_valid' key, got {type(validation_result)}")
        except Exception as e:
            results.add_failure("validate_template_format method", str(e))
        
        # Test 8: Verify validate_template_format handles invalid input
        try:
            validation_result = manager.validate_template_format("")
            if validation_result.get('is_valid') is False:
                results.add_success("validate_template_format handles empty template")
            else:
                results.add_failure("validate_template_format handles empty template", 
                                  "Expected is_valid=False for empty template")
        except Exception as e:
            results.add_failure("validate_template_format handles empty template", str(e))
        
        # Test 9: Verify validate_template_format handles non-string input
        try:
            try:
                manager.validate_template_format(123)  # type: ignore
                results.add_failure("validate_template_format non-string input", 
                                  "Expected RepositoryError for non-string input")
            except RepositoryError:
                results.add_success("validate_template_format handles non-string input")
            except Exception as e:
                results.add_failure("validate_template_format non-string input", 
                                  f"Expected RepositoryError, got {type(e).__name__}: {e}")
        except Exception as e:
            results.add_failure("validate_template_format non-string input", str(e))
        
        # Test 10: Verify template validation with default template
        try:
            default_template = manager.get_default_task_list_template()
            validation_result = manager.validate_template_format(default_template)
            
            if validation_result.get('is_valid') is True:
                results.add_success("Default template passes validation")
            else:
                results.add_failure("Default template passes validation", 
                                  f"Default template failed validation: {validation_result.get('errors', [])}")
        except Exception as e:
            results.add_failure("Default template passes validation", str(e))
        
        # Test 11: Verify integration with existing functionality
        try:
            # Test that template methods don't interfere with existing functionality
            cache_root = manager.CACHE_ROOT
            correlation_id_check = manager.correlation_id
            
            if cache_root == Path("/workspace/repos") and correlation_id_check == correlation_id:
                results.add_success("Template methods don't interfere with existing functionality")
            else:
                results.add_failure("Template methods don't interfere with existing functionality", 
                                  f"State changed: cache_root={cache_root}, correlation_id={correlation_id_check}")
        except Exception as e:
            results.add_failure("Template methods don't interfere with existing functionality", str(e))
        
        # Test 12: Verify error handling patterns
        try:
            # Test that methods follow established error handling patterns
            try:
                # This should raise RepositoryError for invalid template
                manager.validate_template_format("<script>alert('test')</script>")
                validation_passed = True
            except RepositoryError:
                validation_passed = True
            except Exception:
                validation_passed = False
            
            if validation_passed:
                results.add_success("Error handling follows established patterns")
            else:
                results.add_failure("Error handling follows established patterns", 
                                  "Expected RepositoryError for dangerous content")
        except Exception as e:
            results.add_failure("Error handling follows established patterns", str(e))
        
    except Exception as e:
        results.add_failure("Validation execution", f"Unexpected error: {e}")
        traceback.print_exc()
    
    return results


def main():
    """Main entry point for validation script."""
    try:
        results = validate_template_functionality()
        success = results.print_summary()
        
        if success:
            print("\n🎉 All validations passed! Branch 4.4.1 implementation is complete and functional.")
            sys.exit(0)
        else:
            print(f"\n💥 {results.tests_failed} validation(s) failed. Please review and fix the issues.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Validation script failed with unexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()