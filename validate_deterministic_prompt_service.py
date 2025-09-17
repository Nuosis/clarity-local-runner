#!/usr/bin/env python3
"""
Validation script for DeterministicPromptService (Task 7.1.1)

This script validates that the deterministic prompt service:
1. Loads and runs without syntax errors
2. Generates consistent prompts from same inputs
3. Meets performance requirements (≤2s)
4. Integrates properly with existing codebase
5. Handles edge cases and errors gracefully
"""

import sys
import time
import traceback
from pathlib import Path

# Add app directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent / "app"))

def test_imports():
    """Test that all required modules can be imported without errors."""
    print("Testing imports...")
    try:
        from services.deterministic_prompt_service import DeterministicPromptService, PromptContext
        from services.prompt_loader import PromptManager
        from services.repository_cache_manager import get_repository_cache_manager
        from core.exceptions import ValidationError, ExternalServiceError
        print("✓ All imports successful")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        traceback.print_exc()
        return False

def test_prompt_context_creation():
    """Test PromptContext dataclass creation and validation."""
    print("\nTesting PromptContext creation...")
    try:
        from services.deterministic_prompt_service import PromptContext
        
        # Test valid context
        context = PromptContext(
            task_id="test_task_123",
            project_id="test_project",
            execution_id="exec_123",
            correlation_id="corr_123",
            task_description="Test task description",
            task_type="atomic",
            task_priority="medium",
            current_node="TestNode",
            workflow_status="in_progress",
            repository_url="https://github.com/test/repo.git",
            repository_branch="main",
            files_to_modify=["test.py"],
            user_id="test_user",
            metadata={"test": "value"}
        )
        
        assert context.task_id == "test_task_123"
        assert context.project_id == "test_project"
        assert context.task_description == "Test task description"
        assert context.metadata == {"test": "value"}
        
        print("✓ PromptContext creation successful")
        return True
    except Exception as e:
        print(f"✗ PromptContext creation failed: {e}")
        traceback.print_exc()
        return False

def test_service_initialization():
    """Test DeterministicPromptService initialization."""
    print("\nTesting service initialization...")
    try:
        from services.deterministic_prompt_service import DeterministicPromptService
        
        service = DeterministicPromptService()
        assert service is not None
        
        print("✓ Service initialization successful")
        return True
    except Exception as e:
        print(f"✗ Service initialization failed: {e}")
        traceback.print_exc()
        return False

def test_prompt_generation():
    """Test basic prompt generation functionality."""
    print("\nTesting prompt generation...")
    try:
        from services.deterministic_prompt_service import DeterministicPromptService, PromptContext
        
        service = DeterministicPromptService()
        
        context = PromptContext(
            task_id="test_task_123",
            project_id="test_project",
            execution_id="exec_123",
            correlation_id="corr_123",
            task_description="Add logging to authentication module",
            task_type="atomic",
            task_priority="high",
            current_node="PrepNode",
            workflow_status="in_progress",
            repository_url="https://github.com/test/repo.git",
            repository_branch="main",
            files_to_modify=["auth.py", "logging.py"],
            user_id="test_user",
            metadata={"workflow_type": "DEVTEAM_AUTOMATION"}
        )
        
        # Test prompt generation
        start_time = time.time()
        prompt = service.generate_prompt(context)
        generation_time = time.time() - start_time
        
        # Validate prompt content
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "test_task_123" in prompt
        assert "Add logging to authentication module" in prompt
        assert "auth.py" in prompt
        
        # Validate performance requirement (≤2s)
        assert generation_time <= 2.0, f"Generation took {generation_time:.2f}s, exceeds 2s limit"
        
        print(f"✓ Prompt generation successful ({generation_time:.3f}s)")
        print(f"  Prompt length: {len(prompt)} characters")
        return True
    except Exception as e:
        print(f"✗ Prompt generation failed: {e}")
        traceback.print_exc()
        return False

def test_deterministic_behavior():
    """Test that the service generates consistent prompts from same inputs."""
    print("\nTesting deterministic behavior...")
    try:
        from services.deterministic_prompt_service import DeterministicPromptService, PromptContext
        
        service = DeterministicPromptService()
        
        context = PromptContext(
            task_id="deterministic_test",
            project_id="test_project",
            execution_id="exec_det",
            correlation_id="corr_det",
            task_description="Test deterministic generation",
            task_type="atomic",
            task_priority="medium",
            current_node="TestNode",
            workflow_status="in_progress",
            repository_url="https://github.com/test/repo.git",
            repository_branch="main",
            files_to_modify=["test.py"],
            user_id="test_user",
            metadata={"test": "deterministic"}
        )
        
        # Generate prompt multiple times
        prompt1 = service.generate_prompt(context)
        prompt2 = service.generate_prompt(context)
        prompt3 = service.generate_prompt(context)
        
        # Verify all prompts are identical
        assert prompt1 == prompt2 == prompt3, "Prompts are not deterministic"
        
        print("✓ Deterministic behavior verified")
        return True
    except Exception as e:
        print(f"✗ Deterministic behavior test failed: {e}")
        traceback.print_exc()
        return False

def test_error_handling():
    """Test error handling for invalid inputs."""
    print("\nTesting error handling...")
    try:
        from services.deterministic_prompt_service import DeterministicPromptService, PromptContext
        from core.exceptions import ValidationError
        
        service = DeterministicPromptService()
        
        # Test with None context
        try:
            service.generate_prompt(None)
            print("✗ Should have raised ValidationError for None context")
            return False
        except ValidationError:
            print("✓ Correctly handled None context")
        
        # Test with invalid context (missing required fields)
        try:
            invalid_context = PromptContext(
                task_id="",  # Empty task_id should be invalid
                project_id="test_project",
                execution_id="exec_123",
                correlation_id="corr_123",
                task_description="Test task",
                task_type="atomic",
                task_priority="medium",
                current_node="TestNode",
                workflow_status="in_progress",
                repository_url="https://github.com/test/repo.git",
                repository_branch="main",
                files_to_modify=["test.py"],
                user_id="test_user",
                metadata={}
            )
            service.generate_prompt(invalid_context)
            print("✗ Should have raised ValidationError for empty task_id")
            return False
        except ValidationError:
            print("✓ Correctly handled invalid context")
        
        print("✓ Error handling tests passed")
        return True
    except Exception as e:
        print(f"✗ Error handling test failed: {e}")
        traceback.print_exc()
        return False

def test_template_integration():
    """Test integration with Jinja2 template."""
    print("\nTesting template integration...")
    try:
        from pathlib import Path
        
        # Check that template file exists
        template_path = Path("app/prompts/aider_code_change.j2")
        assert template_path.exists(), f"Template file not found: {template_path}"
        
        # Read template content
        template_content = template_path.read_text()
        assert len(template_content) > 0, "Template file is empty"
        assert "{{ task_id }}" in template_content, "Template missing task_id variable"
        assert "{{ task_description }}" in template_content, "Template missing task_description variable"
        
        print("✓ Template integration verified")
        return True
    except Exception as e:
        print(f"✗ Template integration test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all validation tests."""
    print("=" * 60)
    print("DETERMINISTIC PROMPT SERVICE VALIDATION")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_prompt_context_creation,
        test_service_initialization,
        test_template_integration,
        test_prompt_generation,
        test_deterministic_behavior,
        test_error_handling,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"VALIDATION RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED - DeterministicPromptService is ready!")
        return 0
    else:
        print("❌ SOME TESTS FAILED - Please review and fix issues")
        return 1

if __name__ == "__main__":
    sys.exit(main())