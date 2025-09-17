#!/usr/bin/env python3
"""
Task 7.4.2 npm run build Implementation Validation Script (Simplified)

This script validates the implementation of npm run build functionality in AiderExecutionService
without requiring external dependencies. It performs static analysis and basic functionality checks.

Usage:
    python3 validate_task_7_4_2_npm_build_simplified.py
"""

import sys
import os
import time
import json
import inspect
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add the app directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def validate_npm_build_implementation():
    """Validate the npm build implementation."""
    print("🚀 Starting Task 7.4.2 npm run build Implementation Validation (Simplified)")
    print("=" * 80)
    
    results = {
        "validation_timestamp": datetime.now().isoformat(),
        "tests_run": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "errors": [],
        "warnings": [],
        "implementation_details": {}
    }
    
    try:
        # Test 1: Import AiderExecutionService
        print("📦 Testing imports...")
        try:
            from services.aider_execution_service import (
                AiderExecutionService,
                AiderExecutionContext,
                AiderExecutionResult,
                AiderExecutionError,
                get_aider_execution_service
            )
            results["tests_run"] += 1
            results["tests_passed"] += 1
            print("✅ Successfully imported AiderExecutionService and related classes")
        except ImportError as e:
            results["tests_run"] += 1
            results["tests_failed"] += 1
            results["errors"].append(f"Import failed: {e}")
            print(f"❌ Import failed: {e}")
            return results
        
        # Test 2: Create service instance
        print("\n🔧 Testing service initialization...")
        try:
            service = AiderExecutionService(correlation_id="test_npm_build_validation")
            results["tests_run"] += 1
            results["tests_passed"] += 1
            print("✅ Successfully created AiderExecutionService instance")
        except Exception as e:
            results["tests_run"] += 1
            results["tests_failed"] += 1
            results["errors"].append(f"Service initialization failed: {e}")
            print(f"❌ Service initialization failed: {e}")
            return results
        
        # Test 3: Check npm build constants
        print("\n📋 Testing npm build constants...")
        constants_tests = [
            ("NPM_BUILD_COMMAND", "npm run build"),
            ("BUILD_OUTPUT_DIRECTORIES", list)
        ]
        
        for const_name, expected in constants_tests:
            results["tests_run"] += 1
            if hasattr(service, const_name):
                const_value = getattr(service, const_name)
                if isinstance(expected, type):
                    if isinstance(const_value, expected):
                        results["tests_passed"] += 1
                        print(f"✅ {const_name} exists and is correct type: {type(const_value).__name__}")
                        results["implementation_details"][const_name] = str(const_value)
                    else:
                        results["tests_failed"] += 1
                        results["errors"].append(f"{const_name} has wrong type: expected {expected.__name__}, got {type(const_value).__name__}")
                        print(f"❌ {const_name} has wrong type: expected {expected.__name__}, got {type(const_value).__name__}")
                else:
                    if const_value == expected:
                        results["tests_passed"] += 1
                        print(f"✅ {const_name} has correct value: {const_value}")
                        results["implementation_details"][const_name] = const_value
                    else:
                        results["tests_failed"] += 1
                        results["errors"].append(f"{const_name} has wrong value: expected {expected}, got {const_value}")
                        print(f"❌ {const_name} has wrong value: expected {expected}, got {const_value}")
            else:
                results["tests_failed"] += 1
                results["errors"].append(f"Missing constant: {const_name}")
                print(f"❌ Missing constant: {const_name}")
        
        # Test 4: Check npm build methods
        print("\n🔍 Testing npm build methods...")
        required_methods = [
            "execute_npm_build",
            "_execute_npm_build_command", 
            "_capture_npm_build_artifacts"
        ]
        
        for method_name in required_methods:
            results["tests_run"] += 1
            if hasattr(service, method_name):
                method = getattr(service, method_name)
                if callable(method):
                    results["tests_passed"] += 1
                    print(f"✅ Method {method_name} exists and is callable")
                    
                    # Get method signature
                    try:
                        sig = inspect.signature(method)
                        params = list(sig.parameters.keys())
                        results["implementation_details"][f"{method_name}_signature"] = str(sig)
                        print(f"   📝 Signature: {method_name}{sig}")
                    except Exception as e:
                        results["warnings"].append(f"Could not inspect {method_name} signature: {e}")
                else:
                    results["tests_failed"] += 1
                    results["errors"].append(f"{method_name} exists but is not callable")
                    print(f"❌ {method_name} exists but is not callable")
            else:
                results["tests_failed"] += 1
                results["errors"].append(f"Missing method: {method_name}")
                print(f"❌ Missing method: {method_name}")
        
        # Test 5: Check BUILD_OUTPUT_DIRECTORIES content
        print("\n📁 Testing build output directories...")
        if hasattr(service, 'BUILD_OUTPUT_DIRECTORIES'):
            build_dirs = service.BUILD_OUTPUT_DIRECTORIES
            expected_dirs = ['dist', 'build', 'out', 'public', '.next', 'lib', 'es']
            
            results["tests_run"] += 1
            missing_dirs = [d for d in expected_dirs if d not in build_dirs]
            if not missing_dirs:
                results["tests_passed"] += 1
                print(f"✅ BUILD_OUTPUT_DIRECTORIES contains all expected directories: {build_dirs}")
            else:
                results["tests_failed"] += 1
                results["errors"].append(f"BUILD_OUTPUT_DIRECTORIES missing: {missing_dirs}")
                print(f"❌ BUILD_OUTPUT_DIRECTORIES missing: {missing_dirs}")
        
        # Test 6: Test execution context validation
        print("\n✅ Testing execution context validation...")
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
            
            results["tests_run"] += 1
            service._validate_execution_context(valid_context)
            results["tests_passed"] += 1
            print("✅ Valid execution context validation passed")
            
            # Test invalid context
            results["tests_run"] += 1
            try:
                invalid_context = AiderExecutionContext(
                    project_id="",  # Invalid empty project_id
                    execution_id="npm_build_exec_123"
                )
                service._validate_execution_context(invalid_context)
                results["tests_failed"] += 1
                results["errors"].append("Expected ValidationError for invalid context")
                print("❌ Expected ValidationError for invalid context")
            except Exception:
                results["tests_passed"] += 1
                print("✅ Invalid execution context properly rejected")
                
        except Exception as e:
            results["tests_run"] += 2
            results["tests_failed"] += 2
            results["errors"].append(f"Execution context validation failed: {e}")
            print(f"❌ Execution context validation failed: {e}")
        
        # Test 7: Check factory function
        print("\n🏭 Testing factory function...")
        try:
            results["tests_run"] += 1
            factory_service = get_aider_execution_service("npm_build_test_correlation")
            if isinstance(factory_service, AiderExecutionService):
                results["tests_passed"] += 1
                print("✅ Factory function works correctly")
            else:
                results["tests_failed"] += 1
                results["errors"].append(f"Factory function returned wrong type: {type(factory_service)}")
                print(f"❌ Factory function returned wrong type: {type(factory_service)}")
        except Exception as e:
            results["tests_run"] += 1
            results["tests_failed"] += 1
            results["errors"].append(f"Factory function failed: {e}")
            print(f"❌ Factory function failed: {e}")
        
        # Test 8: Check integration with npm ci patterns
        print("\n🔗 Testing integration patterns...")
        npm_ci_exists = hasattr(service, 'execute_npm_ci')
        npm_build_exists = hasattr(service, 'execute_npm_build')
        
        results["tests_run"] += 1
        if npm_ci_exists and npm_build_exists:
            results["tests_passed"] += 1
            print("✅ Both npm ci and npm build methods exist (consistent pattern)")
            
            # Check method signatures are similar
            try:
                ci_sig = inspect.signature(service.execute_npm_ci)
                build_sig = inspect.signature(service.execute_npm_build)
                
                ci_params = list(ci_sig.parameters.keys())
                build_params = list(build_sig.parameters.keys())
                
                results["tests_run"] += 1
                if (len(ci_params) >= 1 and len(build_params) >= 1 and
                    ci_params[0] == 'execution_context' and build_params[0] == 'execution_context'):
                    results["tests_passed"] += 1
                    print("✅ Method signatures follow consistent pattern")
                else:
                    results["tests_failed"] += 1
                    results["errors"].append(f"Inconsistent method signatures: ci={ci_params}, build={build_params}")
                    print(f"❌ Inconsistent method signatures: ci={ci_params}, build={build_params}")
            except Exception as e:
                results["tests_run"] += 1
                results["tests_failed"] += 1
                results["errors"].append(f"Could not compare method signatures: {e}")
                print(f"❌ Could not compare method signatures: {e}")
        else:
            results["tests_failed"] += 1
            results["errors"].append(f"Missing methods: npm_ci={npm_ci_exists}, npm_build={npm_build_exists}")
            print(f"❌ Missing methods: npm_ci={npm_ci_exists}, npm_build={npm_build_exists}")
        
    except Exception as e:
        results["errors"].append(f"Validation failed with unexpected error: {e}")
        print(f"💥 Validation failed with unexpected error: {e}")
    
    # Print summary
    print("\n" + "=" * 80)
    print("📊 VALIDATION SUMMARY")
    print("=" * 80)
    
    success_rate = (results["tests_passed"] / results["tests_run"] * 100) if results["tests_run"] > 0 else 0
    
    print(f"Total Tests: {results['tests_run']}")
    print(f"Passed: {results['tests_passed']}")
    print(f"Failed: {results['tests_failed']}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    if results["implementation_details"]:
        print("\n📋 Implementation Details:")
        for key, value in results["implementation_details"].items():
            print(f"  {key}: {value}")
    
    if results["errors"]:
        print("\n❌ Errors:")
        for error in results["errors"]:
            print(f"  • {error}")
    
    if results["warnings"]:
        print("\n⚠️  Warnings:")
        for warning in results["warnings"]:
            print(f"  • {warning}")
    
    # Overall result
    if results["tests_failed"] == 0:
        print(f"\n✅ ALL TESTS PASSED - npm run build implementation is valid!")
        exit_code = 0
    else:
        print(f"\n❌ {results['tests_failed']} TESTS FAILED - npm run build implementation needs fixes")
        exit_code = 1
    
    return results, exit_code


def main():
    """Main validation function."""
    try:
        results, exit_code = validate_npm_build_implementation()
        
        # Save results to file
        results_file = "task_7_4_2_npm_build_validation_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: {results_file}")
        
        # Exit with appropriate code
        sys.exit(exit_code)
        
    except Exception as e:
        print(f"\n💥 Validation script failed with error: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()