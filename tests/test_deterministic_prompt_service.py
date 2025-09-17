"""
Unit Tests for Deterministic Prompt Service

This module provides comprehensive unit tests for the DeterministicPromptService
with >80% coverage, validating all core functionality including prompt generation,
validation, error handling, and performance requirements.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from services.deterministic_prompt_service import (
    DeterministicPromptService,
    PromptContext,
    get_deterministic_prompt_service
)
from core.exceptions import ValidationError, ExternalServiceError


class TestPromptContext:
    """Test cases for PromptContext dataclass."""
    
    def test_prompt_context_creation_minimal(self):
        """Test creating PromptContext with minimal required fields."""
        context = PromptContext(
            task_id="test_task_123",
            project_id="customer-123/project-abc",
            execution_id="exec_12345"
        )
        
        assert context.task_id == "test_task_123"
        assert context.project_id == "customer-123/project-abc"
        assert context.execution_id == "exec_12345"
        assert context.correlation_id is None
        assert context.task_description is None
        assert context.files_to_modify is None
    
    def test_prompt_context_creation_full(self):
        """Test creating PromptContext with all fields."""
        context = PromptContext(
            task_id="test_task_123",
            project_id="customer-123/project-abc",
            execution_id="exec_12345",
            correlation_id="corr_12345",
            task_description="Add DEVTEAM_ENABLED flag",
            task_type="atomic",
            task_priority="high",
            current_node="PrepNode",
            workflow_status="in_progress",
            repository_url="https://github.com/test/repo.git",
            repository_path="/workspace/repos/test_repo",
            repository_branch="main",
            files_to_modify=["src/config.js", "tests/config.test.js"],
            user_id="user_123",
            timestamp="2025-01-14T18:25:00Z",
            metadata={"custom_field": "custom_value"}
        )
        
        assert context.task_id == "test_task_123"
        assert context.project_id == "customer-123/project-abc"
        assert context.execution_id == "exec_12345"
        assert context.correlation_id == "corr_12345"
        assert context.task_description == "Add DEVTEAM_ENABLED flag"
        assert context.task_type == "atomic"
        assert context.task_priority == "high"
        assert context.current_node == "PrepNode"
        assert context.workflow_status == "in_progress"
        assert context.repository_url == "https://github.com/test/repo.git"
        assert context.repository_path == "/workspace/repos/test_repo"
        assert context.repository_branch == "main"
        assert context.files_to_modify == ["src/config.js", "tests/config.test.js"]
        assert context.user_id == "user_123"
        assert context.timestamp == "2025-01-14T18:25:00Z"
        assert context.metadata == {"custom_field": "custom_value"}


class TestDeterministicPromptService:
    """Test cases for DeterministicPromptService."""
    
    @pytest.fixture
    def service(self):
        """Create a DeterministicPromptService instance for testing."""
        return DeterministicPromptService(correlation_id="test_corr_123")
    
    @pytest.fixture
    def valid_prompt_context(self):
        """Create a valid PromptContext for testing."""
        return PromptContext(
            task_id="test_task_123",
            project_id="customer-123/project-abc",
            execution_id="exec_12345",
            correlation_id="corr_12345",
            task_description="Add DEVTEAM_ENABLED flag to src/config.js",
            task_type="atomic",
            task_priority="medium",
            current_node="PrepNode",
            workflow_status="in_progress",
            repository_url="https://github.com/test/repo.git",
            repository_branch="main",
            files_to_modify=["src/config.js"],
            user_id="user_123",
            metadata={"test_key": "test_value"}
        )
    
    def test_service_initialization(self, service):
        """Test service initialization with correlation ID."""
        assert service.correlation_id == "test_corr_123"
        assert service.logger is not None
        assert service.prompt_manager is not None
        assert service.repository_manager is not None
    
    def test_service_initialization_without_correlation_id(self):
        """Test service initialization without correlation ID."""
        service = DeterministicPromptService()
        assert service.correlation_id is None
        assert service.logger is not None
        assert service.prompt_manager is not None
        assert service.repository_manager is not None
    
    @patch('services.deterministic_prompt_service.PromptManager')
    @patch('services.deterministic_prompt_service.get_repository_cache_manager')
    def test_generate_prompt_success(self, mock_repo_manager, mock_prompt_manager, service, valid_prompt_context):
        """Test successful prompt generation."""
        # Mock dependencies
        mock_prompt_manager_instance = Mock()
        mock_prompt_manager.return_value = mock_prompt_manager_instance
        mock_prompt_manager_instance.get_prompt.return_value = "Generated prompt content"
        
        mock_repo_manager_instance = Mock()
        mock_repo_manager.return_value = mock_repo_manager_instance
        mock_repo_manager_instance.get_repository_cache_info.return_value = {
            'cache_path': '/workspace/repos/test_repo',
            'size_bytes': 1024,
            'file_count': 10,
            'last_modified': '2025-01-14T18:00:00Z',
            'is_valid': True
        }
        
        # Replace service dependencies
        service.prompt_manager = mock_prompt_manager_instance
        service.repository_manager = mock_repo_manager_instance
        
        # Generate prompt
        result = service.generate_prompt(valid_prompt_context)
        
        # Verify result structure
        assert result['success'] is True
        assert result['prompt'] == "Generated prompt content"
        assert result['template_name'] == "aider_code_change"
        assert 'context_hash' in result
        assert 'generation_timestamp' in result
        assert 'performance_metrics' in result
        assert result['validation_status'] == 'valid'
        assert 'repository_context' in result
        
        # Verify performance metrics
        assert 'total_duration_ms' in result['performance_metrics']
        assert 'template_generation_duration_ms' in result['performance_metrics']
        assert 'context_preparation_duration_ms' in result['performance_metrics']
        assert 'prompt_length' in result['performance_metrics']
        assert 'template_variables_count' in result['performance_metrics']
        
        # Verify repository context
        repo_context = result['repository_context']
        assert repo_context['repository_url'] == valid_prompt_context.repository_url
        assert repo_context['repository_path'] == '/workspace/repos/test_repo'
        assert repo_context['repository_branch'] == 'main'
        assert repo_context['repository_size_bytes'] == 1024
        assert repo_context['file_count'] == 10
        assert repo_context['is_valid'] is True
    
    def test_generate_prompt_performance_requirement(self, service, valid_prompt_context):
        """Test that prompt generation meets ≤2s performance requirement."""
        # Mock dependencies to return quickly
        with patch.object(service, 'prompt_manager') as mock_prompt_manager, \
             patch.object(service, 'repository_manager') as mock_repo_manager:
            
            mock_prompt_manager.get_prompt.return_value = "Test prompt"
            mock_repo_manager.get_repository_cache_info.return_value = None
            
            start_time = time.time()
            result = service.generate_prompt(valid_prompt_context)
            duration = time.time() - start_time
            
            # Verify performance requirement
            assert duration <= 2.0, f"Prompt generation took {duration:.3f}s, exceeds 2s requirement"
            assert result['performance_metrics']['total_duration_ms'] <= 2000
    
    def test_validate_prompt_context_valid(self, service, valid_prompt_context):
        """Test validation of valid prompt context."""
        # Should not raise any exception
        service._validate_prompt_context(valid_prompt_context)
    
    def test_validate_prompt_context_invalid_type(self, service):
        """Test validation with invalid context type."""
        with pytest.raises(ValidationError) as exc_info:
            service._validate_prompt_context("invalid_context")
        
        assert "prompt_context must be a PromptContext instance" in str(exc_info.value)
    
    def test_validate_prompt_context_missing_required_fields(self, service):
        """Test validation with missing required fields."""
        context = PromptContext(
            task_id="",  # Empty task_id
            project_id="customer-123/project-abc",
            execution_id=""  # Empty execution_id
        )
        
        with pytest.raises(ValidationError) as exc_info:
            service._validate_prompt_context(context)
        
        error_message = str(exc_info.value)
        assert "Missing required fields" in error_message
        assert "task_id" in error_message
        assert "execution_id" in error_message
    
    def test_validate_prompt_context_invalid_characters(self, service):
        """Test validation with invalid characters in fields."""
        context = PromptContext(
            task_id="test<script>alert('xss')</script>",  # Invalid characters
            project_id="customer-123/project-abc",
            execution_id="exec_12345"
        )
        
        with pytest.raises(ValidationError) as exc_info:
            service._validate_prompt_context(context)
        
        assert "task_id contains invalid characters" in str(exc_info.value)
    
    def test_validate_template_name_valid(self, service):
        """Test validation of valid template name."""
        # Should not raise any exception
        service._validate_template_name("aider_code_change")
        service._validate_template_name("test_template_123")
        service._validate_template_name("simple-template")
    
    def test_validate_template_name_empty(self, service):
        """Test validation with empty template name."""
        with pytest.raises(ValidationError) as exc_info:
            service._validate_template_name("")
        
        assert "template_name cannot be empty" in str(exc_info.value)
    
    def test_validate_template_name_path_traversal(self, service):
        """Test validation with path traversal attempts."""
        invalid_names = [
            "../template",
            "template/../other",
            "template/subdir",
            "template\\windows",
            "template..evil"
        ]
        
        for invalid_name in invalid_names:
            with pytest.raises(ValidationError) as exc_info:
                service._validate_template_name(invalid_name)
            
            error_message = str(exc_info.value)
            assert ("contains invalid characters" in error_message or 
                   "contains path traversal characters" in error_message)
    
    def test_generate_context_hash_deterministic(self, service):
        """Test that context hash generation is deterministic."""
        context1 = PromptContext(
            task_id="test_task_123",
            project_id="customer-123/project-abc",
            execution_id="exec_12345",
            task_description="Test description",
            files_to_modify=["file1.js", "file2.js"]
        )
        
        context2 = PromptContext(
            task_id="test_task_123",
            project_id="customer-123/project-abc",
            execution_id="exec_12345",
            task_description="Test description",
            files_to_modify=["file2.js", "file1.js"]  # Different order
        )
        
        hash1 = service._generate_context_hash(context1)
        hash2 = service._generate_context_hash(context2)
        
        # Hashes should be the same (files are sorted)
        assert hash1 == hash2
        assert len(hash1) == 16  # Should be 16 character hex string
    
    def test_generate_context_hash_different_contexts(self, service):
        """Test that different contexts generate different hashes."""
        context1 = PromptContext(
            task_id="test_task_123",
            project_id="customer-123/project-abc",
            execution_id="exec_12345"
        )
        
        context2 = PromptContext(
            task_id="test_task_456",  # Different task_id
            project_id="customer-123/project-abc",
            execution_id="exec_12345"
        )
        
        hash1 = service._generate_context_hash(context1)
        hash2 = service._generate_context_hash(context2)
        
        assert hash1 != hash2
    
    @patch('services.deterministic_prompt_service.get_repository_cache_manager')
    def test_get_repository_context_with_cache(self, mock_repo_manager, service, valid_prompt_context):
        """Test getting repository context when cache exists."""
        mock_repo_manager_instance = Mock()
        mock_repo_manager.return_value = mock_repo_manager_instance
        mock_repo_manager_instance.get_repository_cache_info.return_value = {
            'cache_path': '/workspace/repos/test_repo',
            'size_bytes': 2048,
            'file_count': 15,
            'last_modified': '2025-01-14T18:00:00Z',
            'is_valid': True
        }
        
        service.repository_manager = mock_repo_manager_instance
        
        result = service._get_repository_context(valid_prompt_context)
        
        assert result is not None
        assert result['repository_url'] == valid_prompt_context.repository_url
        assert result['repository_path'] == '/workspace/repos/test_repo'
        assert result['repository_branch'] == 'main'
        assert result['repository_size_bytes'] == 2048
        assert result['file_count'] == 15
        assert result['is_valid'] is True
    
    @patch('services.deterministic_prompt_service.get_repository_cache_manager')
    def test_get_repository_context_no_cache(self, mock_repo_manager, service, valid_prompt_context):
        """Test getting repository context when no cache exists."""
        mock_repo_manager_instance = Mock()
        mock_repo_manager.return_value = mock_repo_manager_instance
        mock_repo_manager_instance.get_repository_cache_info.return_value = None
        
        service.repository_manager = mock_repo_manager_instance
        
        result = service._get_repository_context(valid_prompt_context)
        
        assert result is not None
        assert result['repository_url'] == valid_prompt_context.repository_url
        assert result['repository_path'] is None
        assert result['repository_branch'] == 'main'
        assert result['repository_size_bytes'] == 0
        assert result['file_count'] == 0
        assert result['is_valid'] is False
    
    def test_get_repository_context_no_url(self, service):
        """Test getting repository context when no repository URL is provided."""
        context = PromptContext(
            task_id="test_task_123",
            project_id="customer-123/project-abc",
            execution_id="exec_12345"
            # No repository_url
        )
        
        result = service._get_repository_context(context)
        assert result is None
    
    def test_prepare_template_variables_full_context(self, service, valid_prompt_context):
        """Test preparing template variables with full context."""
        repository_context = {
            'repository_url': 'https://github.com/test/repo.git',
            'repository_path': '/workspace/repos/test_repo',
            'repository_branch': 'main',
            'repository_size_bytes': 1024,
            'file_count': 10,
            'last_updated': '2025-01-14T18:00:00Z',
            'is_valid': True
        }
        
        variables = service._prepare_template_variables(valid_prompt_context, repository_context)
        
        # Verify basic fields
        assert variables['task_id'] == valid_prompt_context.task_id
        assert variables['project_id'] == valid_prompt_context.project_id
        assert variables['execution_id'] == valid_prompt_context.execution_id
        assert variables['task_description'] == valid_prompt_context.task_description
        assert variables['task_type'] == valid_prompt_context.task_type
        assert variables['task_priority'] == valid_prompt_context.task_priority
        assert variables['files_to_modify'] == valid_prompt_context.files_to_modify
        assert variables['files_count'] == 1
        assert variables['user_id'] == valid_prompt_context.user_id
        assert variables['metadata'] == valid_prompt_context.metadata
        
        # Verify repository fields
        assert variables['repository_url'] == repository_context['repository_url']
        assert variables['repository_path'] == repository_context['repository_path']
        assert variables['repository_branch'] == repository_context['repository_branch']
        assert variables['repository_size_bytes'] == repository_context['repository_size_bytes']
        assert variables['repository_file_count'] == repository_context['file_count']
        assert variables['repository_is_valid'] == repository_context['is_valid']
        
        # Verify generated fields
        assert 'correlation_id' in variables
        assert 'generation_timestamp' in variables
    
    def test_prepare_template_variables_minimal_context(self, service):
        """Test preparing template variables with minimal context."""
        context = PromptContext(
            task_id="test_task_123",
            project_id="customer-123/project-abc",
            execution_id="exec_12345"
        )
        
        variables = service._prepare_template_variables(context, None)
        
        # Verify defaults are applied
        assert variables['task_description'] == 'No description provided'
        assert variables['task_type'] == 'atomic'
        assert variables['task_priority'] == 'medium'
        assert variables['current_node'] == 'unknown'
        assert variables['workflow_status'] == 'in_progress'
        assert variables['files_to_modify'] == []
        assert variables['files_count'] == 0
        assert variables['user_id'] == 'system'
        assert variables['metadata'] == {}
        
        # Verify repository defaults
        assert variables['repository_url'] is None
        assert variables['repository_path'] is None
        assert variables['repository_branch'] == 'main'
        assert variables['repository_size_bytes'] == 0
        assert variables['repository_file_count'] == 0
        assert variables['repository_is_valid'] is False
    
    def test_validate_generated_prompt_valid(self, service):
        """Test validation of valid generated prompt."""
        prompt = "This is a valid prompt with sufficient content to pass validation checks."
        
        result = service._validate_generated_prompt(prompt)
        
        assert result['status'] == 'valid'
        assert result['issues'] == []
        assert result['prompt_length'] == len(prompt)
        assert result['line_count'] == 1
    
    def test_validate_generated_prompt_empty(self, service):
        """Test validation of empty prompt."""
        result = service._validate_generated_prompt("")
        
        assert result['status'] == 'invalid'
        assert 'Generated prompt is empty' in result['issues']
    
    def test_validate_generated_prompt_too_short(self, service):
        """Test validation of very short prompt."""
        result = service._validate_generated_prompt("Short")
        
        assert result['status'] == 'warning'
        assert 'Generated prompt is very short' in result['issues']
    
    def test_validate_generated_prompt_too_long(self, service):
        """Test validation of very long prompt."""
        long_prompt = "x" * 60000  # Exceeds 50000 character limit
        
        result = service._validate_generated_prompt(long_prompt)
        
        assert result['status'] == 'warning'
        assert 'Generated prompt is very long' in result['issues']
    
    def test_validate_generated_prompt_dangerous_content(self, service):
        """Test validation of prompt with dangerous content."""
        dangerous_prompts = [
            "This contains <script>alert('xss')</script> content",
            "This contains javascript:void(0) content",
            "This contains \x00 null character"
        ]
        
        for dangerous_prompt in dangerous_prompts:
            result = service._validate_generated_prompt(dangerous_prompt)
            
            assert result['status'] == 'invalid'
            assert 'Generated prompt contains potentially dangerous content' in result['issues']
    
    @patch('services.deterministic_prompt_service.PromptManager')
    def test_generate_prompt_template_error(self, mock_prompt_manager, service, valid_prompt_context):
        """Test handling of template generation errors."""
        mock_prompt_manager_instance = Mock()
        mock_prompt_manager.return_value = mock_prompt_manager_instance
        mock_prompt_manager_instance.get_prompt.side_effect = Exception("Template error")
        
        service.prompt_manager = mock_prompt_manager_instance
        
        with pytest.raises(ExternalServiceError) as exc_info:
            service.generate_prompt(valid_prompt_context)
        
        assert "Failed to generate prompt from template" in str(exc_info.value)
        assert exc_info.value.service == "prompt_manager"
    
    @patch('services.deterministic_prompt_service.PromptManager')
    def test_generate_prompt_unexpected_error(self, mock_prompt_manager, service, valid_prompt_context):
        """Test handling of unexpected errors during prompt generation."""
        mock_prompt_manager_instance = Mock()
        mock_prompt_manager.return_value = mock_prompt_manager_instance
        
        # Mock an unexpected error in context hash generation
        with patch.object(service, '_generate_context_hash', side_effect=Exception("Unexpected error")):
            with pytest.raises(ExternalServiceError) as exc_info:
                service.generate_prompt(valid_prompt_context)
            
            assert "Prompt generation failed" in str(exc_info.value)
            assert exc_info.value.service == "deterministic_prompt_service"


class TestFactoryFunction:
    """Test cases for factory function."""
    
    def test_get_deterministic_prompt_service_with_correlation_id(self):
        """Test factory function with correlation ID."""
        service = get_deterministic_prompt_service("test_corr_123")
        
        assert isinstance(service, DeterministicPromptService)
        assert service.correlation_id == "test_corr_123"
    
    def test_get_deterministic_prompt_service_without_correlation_id(self):
        """Test factory function without correlation ID."""
        service = get_deterministic_prompt_service()
        
        assert isinstance(service, DeterministicPromptService)
        assert service.correlation_id is None


class TestIntegrationScenarios:
    """Integration test scenarios for realistic usage patterns."""
    
    @pytest.fixture
    def service(self):
        """Create service for integration tests."""
        return DeterministicPromptService(correlation_id="integration_test")
    
    def test_devteam_automation_workflow_integration(self, service):
        """Test integration with DevTeam automation workflow context."""
        # Simulate context from DevTeam automation workflow
        context = PromptContext(
            task_id="1.1.1",
            project_id="customer-123/project-abc",
            execution_id="exec_devteam_12345",
            correlation_id="corr_devteam_12345",
            task_description="Add DEVTEAM_ENABLED flag to src/config.js with default false and JSDoc documentation",
            task_type="atomic",
            task_priority="medium",
            current_node="PrepNode",
            workflow_status="prepared",
            repository_url="https://github.com/customer-123/project-abc.git",
            repository_branch="main",
            files_to_modify=["src/config.js"],
            user_id="user_123",
            metadata={
                "workflow_type": "DEVTEAM_AUTOMATION",
                "plan_id": "plan_devteam_12345",
                "strategy": "devteam_automation"
            }
        )
        
        # Mock dependencies for integration test
        with patch.object(service, 'prompt_manager') as mock_prompt_manager, \
             patch.object(service, 'repository_manager') as mock_repo_manager:
            
            mock_prompt_manager.get_prompt.return_value = """
# Code Change Instructions for Aider

## Task Context
- **Task ID**: 1.1.1
- **Project ID**: customer-123/project-abc
- **Description**: Add DEVTEAM_ENABLED flag to src/config.js with default false and JSDoc documentation

## Implementation Guidelines
- Follow SOLID principles and established design patterns
- Write self-documenting code with clear variable and function names
- Add appropriate comments for complex logic
"""
            
            mock_repo_manager.get_repository_cache_info.return_value = {
                'cache_path': '/workspace/repos/customer-123_project-abc_abc123',
                'size_bytes': 5120,
                'file_count': 25,
                'last_modified': '2025-01-14T18:00:00Z',
                'is_valid': True
            }
            
            result = service.generate_prompt(context)
            
            # Verify integration result
            assert result['success'] is True
            assert result['template_name'] == "aider_code_change"
            assert 'Code Change Instructions for Aider' in result['prompt']
            assert result['validation_status'] == 'valid'
            
            # Verify repository context integration
            repo_context = result['repository_context']
            assert repo_context['repository_url'] == context.repository_url
            assert repo_context['is_valid'] is True
            
            # Verify performance meets requirements
            assert result['performance_metrics']['total_duration_ms'] <= 2000
    
    def test_deterministic_behavior_across_calls(self, service):
        """Test that multiple calls with same context produce identical results."""
        context = PromptContext(
            task_id="deterministic_test",
            project_id="test-project/deterministic",
            execution_id="exec_deterministic_123",
            task_description="Test deterministic behavior",
            files_to_modify=["test.js"]
        )
        
        # Mock dependencies to return consistent results
        with patch.object(service, 'prompt_manager') as mock_prompt_manager, \
             patch.object(service, 'repository_manager') as mock_repo_manager:
            
            mock_prompt_manager.get_prompt.return_value = "Consistent prompt content"
            mock_repo_manager.get_repository_cache_info.return_value = None
            
            # Generate prompt multiple times
            result1 = service.generate_prompt(context)
            result2 = service.generate_prompt(context)
            
            # Verify deterministic behavior
            assert result1['context_hash'] == result2['context_hash']
            assert result1['prompt'] == result2['prompt']
            assert result1['template_name'] == result2['template_name']
            
            # Note: generation_timestamp will be different, which is expected
            # as it represents when the prompt was generated