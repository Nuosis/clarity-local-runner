"""
Integration Tests for Deterministic Prompt Service

This module provides integration tests that validate prompt generation with real
task context from workflow nodes and repository information, ensuring proper
integration with the existing DevTeam automation workflow system.
"""

import pytest
import time
from unittest.mock import Mock, patch
from datetime import datetime

from services.deterministic_prompt_service import (
    DeterministicPromptService,
    PromptContext,
    get_deterministic_prompt_service
)
from core.task import TaskContext
from schemas.event_schema import EventRequest
from workflows.devteam_automation_workflow import DevTeamAutomationWorkflow
from workflows.devteam_automation_workflow_nodes.select_node import SelectNode
from workflows.devteam_automation_workflow_nodes.prep_node import PrepNode


class TestWorkflowIntegration:
    """Integration tests with DevTeam automation workflow."""
    
    @pytest.fixture
    def mock_event_data(self):
        """Create mock event data for DevTeam automation."""
        return {
            "id": "evt_devteam_12345",
            "type": "DEVTEAM_AUTOMATION",
            "project_id": "customer-123/project-abc",
            "user_id": "user_123",
            "task": {
                "id": "1.1.1",
                "description": "Add DEVTEAM_ENABLED flag to src/config.js with default false and JSDoc documentation",
                "type": "atomic",
                "priority": "medium",
                "files": ["src/config.js"]
            },
            "repository": {
                "url": "https://github.com/customer-123/project-abc.git",
                "branch": "main"
            },
            "metadata": {
                "correlation_id": "corr_devteam_12345",
                "workflow_type": "DEVTEAM_AUTOMATION"
            }
        }
    
    @pytest.fixture
    def workflow_task_context(self, mock_event_data):
        """Create TaskContext as it would appear after workflow processing."""
        # Simulate the TaskContext after SelectNode and PrepNode processing
        event = EventRequest(**mock_event_data)
        task_context = TaskContext(event=event)
        
        # Simulate SelectNode results
        task_context.metadata["selected_plan"] = {
            "plan_id": f"plan_{event.id}",
            "strategy": "devteam_automation",
            "phases": [
                {"phase": "preparation", "description": "Prepare task context and validate requirements"},
                {"phase": "execution", "description": "Execute DevTeam automation task"}
            ],
            "estimated_duration": "2s",
            "priority": "medium"
        }
        
        # Simulate PrepNode results
        task_context.metadata.update({
            "correlationId": "corr_devteam_12345",
            "status": "prepared",
            "prepared_at": "2025-01-14T18:25:00.000Z",
            "workflow_type": "DEVTEAM_AUTOMATION",
            "event_id": event.id,
            "project_id": event.project_id,
            "task_id": event.task.id if hasattr(event, 'task') and event.task else None,
            "priority": getattr(event, 'priority', 'normal')
        })
        
        # Simulate node processing results
        task_context.nodes = {
            "SelectNode": {
                "status": "completed",
                "message": "Fixed plan selected for DevTeam automation workflow",
                "event_data": {
                    "plan_id": f"plan_{event.id}",
                    "strategy": "devteam_automation",
                    "phases_count": 2
                }
            },
            "PrepNode": {
                "status": "completed",
                "message": "Task context prepared with basic metadata for DevTeam automation",
                "event_data": {
                    "correlationId": "corr_devteam_12345",
                    "workflow_type": "DEVTEAM_AUTOMATION",
                    "prepared_at": "2025-01-14T18:25:00.000Z",
                    "plan_id": f"plan_{event.id}"
                }
            }
        }
        
        return task_context
    
    def test_prompt_context_from_workflow_task_context(self, workflow_task_context):
        """Test creating PromptContext from workflow TaskContext."""
        # Extract information from workflow TaskContext to create PromptContext
        event = workflow_task_context.event
        metadata = workflow_task_context.metadata
        
        # Extract task information safely
        task_id = event.task.id if hasattr(event, 'task') and event.task else event.id
        task_description = event.task.description if hasattr(event, 'task') and event.task else None
        task_type = event.task.type if hasattr(event, 'task') and event.task else "atomic"
        task_priority = event.task.priority if hasattr(event, 'task') and event.task else metadata.get("priority", "medium")
        repository_url = event.repository.url if hasattr(event, 'repository') and event.repository else None
        repository_branch = event.repository.branch if hasattr(event, 'repository') and event.repository else "main"
        files_to_modify = event.task.files if hasattr(event, 'task') and event.task and hasattr(event.task, 'files') else None
        
        prompt_context = PromptContext(
            task_id=metadata.get("task_id", task_id),
            project_id=event.project_id,
            execution_id=f"exec_{event.id}",
            correlation_id=metadata.get("correlationId"),
            task_description=task_description,
            task_type=task_type,
            task_priority=task_priority,
            current_node="PrepNode",
            workflow_status=metadata.get("status", "in_progress"),
            repository_url=repository_url,
            repository_branch=repository_branch,
            files_to_modify=files_to_modify,
            user_id=event.user_id,
            metadata={
                "workflow_type": metadata.get("workflow_type"),
                "selected_plan": metadata.get("selected_plan"),
                "prepared_at": metadata.get("prepared_at")
            }
        )
        
        # Verify PromptContext creation
        assert prompt_context.task_id == "1.1.1"
        assert prompt_context.project_id == "customer-123/project-abc"
        assert prompt_context.execution_id == "exec_evt_devteam_12345"
        assert prompt_context.correlation_id == "corr_devteam_12345"
        assert prompt_context.task_description == "Add DEVTEAM_ENABLED flag to src/config.js with default false and JSDoc documentation"
        assert prompt_context.task_type == "atomic"
        assert prompt_context.task_priority == "medium"
        assert prompt_context.current_node == "PrepNode"
        assert prompt_context.workflow_status == "prepared"
        assert prompt_context.repository_url == "https://github.com/customer-123/project-abc.git"
        assert prompt_context.repository_branch == "main"
        assert prompt_context.files_to_modify == ["src/config.js"]
        assert prompt_context.user_id == "user_123"
        if prompt_context.metadata:
            assert prompt_context.metadata["workflow_type"] == "DEVTEAM_AUTOMATION"
    
    @patch('services.deterministic_prompt_service.PromptManager')
    @patch('services.deterministic_prompt_service.get_repository_cache_manager')
    def test_end_to_end_prompt_generation_from_workflow(
        self, 
        mock_repo_manager, 
        mock_prompt_manager, 
        workflow_task_context
    ):
        """Test end-to-end prompt generation from workflow TaskContext."""
        # Setup mocks
        mock_prompt_manager_instance = Mock()
        mock_prompt_manager.return_value = mock_prompt_manager_instance
        mock_prompt_manager_instance.get_prompt.return_value = """# Code Change Instructions for Aider

## Task Context
- **Task ID**: {{ task_id }}
- **Project ID**: {{ project_id }}
- **Description**: {{ task_description }}

## Repository Context
- **Repository**: {{ repository_url }}
- **Branch**: {{ repository_branch }}
- **Files to Modify**: {{ files_to_modify|join(', ') }}

## Implementation Guidelines
- Follow SOLID principles and established design patterns
- Write self-documenting code with clear variable and function names
- Add appropriate comments for complex logic
"""
        
        mock_repo_manager_instance = Mock()
        mock_repo_manager.return_value = mock_repo_manager_instance
        mock_repo_manager_instance.get_repository_cache_info.return_value = {
            'cache_path': '/workspace/repos/customer-123_project-abc_abc123',
            'size_bytes': 10240,
            'file_count': 50,
            'last_modified': '2025-01-14T18:00:00Z',
            'is_valid': True
        }
        
        # Create service and PromptContext from workflow
        service = DeterministicPromptService(correlation_id="integration_test")
        service.prompt_manager = mock_prompt_manager_instance
        service.repository_manager = mock_repo_manager_instance
        
        event = workflow_task_context.event
        metadata = workflow_task_context.metadata
        
        prompt_context = PromptContext(
            task_id=metadata.get("task_id", event.task.id),
            project_id=event.project_id,
            execution_id=f"exec_{event.id}",
            correlation_id=metadata.get("correlationId"),
            task_description=event.task.description,
            task_type=event.task.type,
            task_priority=event.task.priority,
            current_node="PrepNode",
            workflow_status=metadata.get("status"),
            repository_url=event.repository.url,
            repository_branch=event.repository.branch,
            files_to_modify=event.task.files,
            user_id=event.user_id,
            metadata={
                "workflow_type": metadata.get("workflow_type"),
                "selected_plan": metadata.get("selected_plan")
            }
        )
        
        # Generate prompt
        result = service.generate_prompt(prompt_context)
        
        # Verify integration result
        assert result['success'] is True
        assert result['template_name'] == "aider_code_change"
        assert 'Code Change Instructions for Aider' in result['prompt']
        assert result['validation_status'] == 'valid'
        
        # Verify context hash is deterministic
        assert len(result['context_hash']) == 16
        
        # Verify repository context integration
        repo_context = result['repository_context']
        assert repo_context['repository_url'] == "https://github.com/customer-123/project-abc.git"
        assert repo_context['repository_branch'] == "main"
        assert repo_context['is_valid'] is True
        
        # Verify performance requirements
        assert result['performance_metrics']['total_duration_ms'] <= 2000
        
        # Verify template was called with correct variables
        mock_prompt_manager_instance.get_prompt.assert_called_once()
        call_args = mock_prompt_manager_instance.get_prompt.call_args
        template_vars = call_args[1]  # kwargs
        
        assert template_vars['task_id'] == "1.1.1"
        assert template_vars['project_id'] == "customer-123/project-abc"
        assert template_vars['task_description'] == "Add DEVTEAM_ENABLED flag to src/config.js with default false and JSDoc documentation"
        assert template_vars['files_to_modify'] == ["src/config.js"]
        assert template_vars['repository_url'] == "https://github.com/customer-123/project-abc.git"


class TestRepositoryIntegration:
    """Integration tests with repository cache manager."""
    
    @pytest.fixture
    def service(self):
        """Create service for repository integration tests."""
        return DeterministicPromptService(correlation_id="repo_integration_test")
    
    @pytest.fixture
    def prompt_context_with_repo(self):
        """Create PromptContext with repository information."""
        return PromptContext(
            task_id="repo_test_123",
            project_id="test-org/test-repo",
            execution_id="exec_repo_123",
            correlation_id="corr_repo_123",
            task_description="Test repository integration",
            repository_url="https://github.com/test-org/test-repo.git",
            repository_branch="feature/test-branch",
            files_to_modify=["src/main.js", "tests/main.test.js"]
        )
    
    @patch('services.deterministic_prompt_service.PromptManager')
    def test_repository_context_with_valid_cache(
        self, 
        mock_prompt_manager, 
        service, 
        prompt_context_with_repo
    ):
        """Test repository context integration with valid cache."""
        # Mock prompt manager
        mock_prompt_manager_instance = Mock()
        mock_prompt_manager.return_value = mock_prompt_manager_instance
        mock_prompt_manager_instance.get_prompt.return_value = "Test prompt with repo context"
        
        # Mock repository manager with valid cache
        with patch.object(service, 'repository_manager') as mock_repo_manager:
            mock_repo_manager.get_repository_cache_info.return_value = {
                'cache_path': '/workspace/repos/test-org_test-repo_def456',
                'size_bytes': 15360,
                'file_count': 75,
                'last_modified': '2025-01-14T17:30:00Z',
                'is_valid': True
            }
            
            service.prompt_manager = mock_prompt_manager_instance
            
            result = service.generate_prompt(prompt_context_with_repo)
            
            # Verify repository context
            repo_context = result['repository_context']
            assert repo_context is not None
            assert repo_context['repository_url'] == "https://github.com/test-org/test-repo.git"
            assert repo_context['repository_path'] == '/workspace/repos/test-org_test-repo_def456'
            assert repo_context['repository_branch'] == 'feature/test-branch'
            assert repo_context['repository_size_bytes'] == 15360
            assert repo_context['file_count'] == 75
            assert repo_context['is_valid'] is True
            
            # Verify repository manager was called correctly
            mock_repo_manager.get_repository_cache_info.assert_called_once_with(
                repository_url="https://github.com/test-org/test-repo.git",
                project_id="test-org/test-repo",
                execution_id="exec_repo_123"
            )
    
    @patch('services.deterministic_prompt_service.PromptManager')
    def test_repository_context_with_no_cache(
        self, 
        mock_prompt_manager, 
        service, 
        prompt_context_with_repo
    ):
        """Test repository context integration with no cache."""
        # Mock prompt manager
        mock_prompt_manager_instance = Mock()
        mock_prompt_manager.return_value = mock_prompt_manager_instance
        mock_prompt_manager_instance.get_prompt.return_value = "Test prompt without repo cache"
        
        # Mock repository manager with no cache
        with patch.object(service, 'repository_manager') as mock_repo_manager:
            mock_repo_manager.get_repository_cache_info.return_value = None
            
            service.prompt_manager = mock_prompt_manager_instance
            
            result = service.generate_prompt(prompt_context_with_repo)
            
            # Verify repository context defaults
            repo_context = result['repository_context']
            assert repo_context is not None
            assert repo_context['repository_url'] == "https://github.com/test-org/test-repo.git"
            assert repo_context['repository_path'] is None
            assert repo_context['repository_branch'] == 'feature/test-branch'
            assert repo_context['repository_size_bytes'] == 0
            assert repo_context['file_count'] == 0
            assert repo_context['is_valid'] is False
    
    @patch('services.deterministic_prompt_service.PromptManager')
    def test_repository_context_error_handling(
        self, 
        mock_prompt_manager, 
        service, 
        prompt_context_with_repo
    ):
        """Test repository context error handling."""
        # Mock prompt manager
        mock_prompt_manager_instance = Mock()
        mock_prompt_manager.return_value = mock_prompt_manager_instance
        mock_prompt_manager_instance.get_prompt.return_value = "Test prompt with repo error"
        
        # Mock repository manager to raise exception
        with patch.object(service, 'repository_manager') as mock_repo_manager:
            mock_repo_manager.get_repository_cache_info.side_effect = Exception("Repository error")
            
            service.prompt_manager = mock_prompt_manager_instance
            
            result = service.generate_prompt(prompt_context_with_repo)
            
            # Should still succeed with None repository context
            assert result['success'] is True
            assert result['repository_context'] is None


class TestPerformanceIntegration:
    """Integration tests for performance requirements."""
    
    @pytest.fixture
    def service(self):
        """Create service for performance tests."""
        return DeterministicPromptService(correlation_id="perf_test")
    
    @pytest.fixture
    def large_prompt_context(self):
        """Create PromptContext with large data for performance testing."""
        return PromptContext(
            task_id="perf_test_123",
            project_id="performance/test-project",
            execution_id="exec_perf_123",
            correlation_id="corr_perf_123",
            task_description="Performance test with large context data " * 50,  # Large description
            task_type="composite",
            task_priority="high",
            current_node="PrepNode",
            workflow_status="in_progress",
            repository_url="https://github.com/performance/test-project.git",
            repository_branch="main",
            files_to_modify=[f"src/file_{i}.js" for i in range(100)],  # Many files
            user_id="perf_user_123",
            metadata={
                "large_data": {f"key_{i}": f"value_{i}" * 100 for i in range(50)}  # Large metadata
            }
        )
    
    @patch('services.deterministic_prompt_service.PromptManager')
    @patch('services.deterministic_prompt_service.get_repository_cache_manager')
    def test_performance_with_large_context(
        self, 
        mock_repo_manager, 
        mock_prompt_manager, 
        service, 
        large_prompt_context
    ):
        """Test performance with large context data."""
        # Mock dependencies
        mock_prompt_manager_instance = Mock()
        mock_prompt_manager.return_value = mock_prompt_manager_instance
        mock_prompt_manager_instance.get_prompt.return_value = "Large context prompt " * 1000
        
        mock_repo_manager_instance = Mock()
        mock_repo_manager.return_value = mock_repo_manager_instance
        mock_repo_manager_instance.get_repository_cache_info.return_value = {
            'cache_path': '/workspace/repos/performance_test-project_ghi789',
            'size_bytes': 1048576,  # 1MB
            'file_count': 1000,
            'last_modified': '2025-01-14T18:00:00Z',
            'is_valid': True
        }
        
        service.prompt_manager = mock_prompt_manager_instance
        service.repository_manager = mock_repo_manager_instance
        
        # Measure performance
        start_time = time.time()
        result = service.generate_prompt(large_prompt_context)
        duration = time.time() - start_time
        
        # Verify performance requirement
        assert duration <= 2.0, f"Large context processing took {duration:.3f}s, exceeds 2s requirement"
        assert result['success'] is True
        assert result['performance_metrics']['total_duration_ms'] <= 2000
        
        # Verify large context was handled correctly
        assert result['context_hash'] is not None
        assert len(result['context_hash']) == 16
        assert result['repository_context']['file_count'] == 1000
    
    @patch('services.deterministic_prompt_service.PromptManager')
    def test_performance_multiple_sequential_calls(self, mock_prompt_manager, service):
        """Test performance of multiple sequential prompt generations."""
        # Mock prompt manager
        mock_prompt_manager_instance = Mock()
        mock_prompt_manager.return_value = mock_prompt_manager_instance
        mock_prompt_manager_instance.get_prompt.return_value = "Sequential test prompt"
        
        service.prompt_manager = mock_prompt_manager_instance
        
        # Create multiple contexts
        contexts = [
            PromptContext(
                task_id=f"seq_test_{i}",
                project_id="sequential/test-project",
                execution_id=f"exec_seq_{i}",
                task_description=f"Sequential test {i}"
            )
            for i in range(10)
        ]
        
        # Measure total time for sequential calls
        start_time = time.time()
        results = []
        
        for context in contexts:
            result = service.generate_prompt(context)
            results.append(result)
        
        total_duration = time.time() - start_time
        
        # Verify all calls succeeded
        assert len(results) == 10
        assert all(result['success'] for result in results)
        
        # Verify average performance per call
        avg_duration_per_call = total_duration / 10
        assert avg_duration_per_call <= 2.0, f"Average duration per call {avg_duration_per_call:.3f}s exceeds 2s requirement"
        
        # Verify each individual call met performance requirement
        for result in results:
            assert result['performance_metrics']['total_duration_ms'] <= 2000


class TestTemplateIntegration:
    """Integration tests with template system."""
    
    @pytest.fixture
    def service(self):
        """Create service for template integration tests."""
        return DeterministicPromptService(correlation_id="template_test")
    
    @pytest.fixture
    def template_context(self):
        """Create context for template testing."""
        return PromptContext(
            task_id="template_test_123",
            project_id="template/test-project",
            execution_id="exec_template_123",
            correlation_id="corr_template_123",
            task_description="Test template integration with all variables",
            task_type="atomic",
            task_priority="high",
            current_node="PrepNode",
            workflow_status="prepared",
            repository_url="https://github.com/template/test-project.git",
            repository_branch="develop",
            files_to_modify=["src/component.js", "tests/component.test.js"],
            user_id="template_user",
            metadata={
                "workflow_type": "DEVTEAM_AUTOMATION",
                "custom_field": "custom_value"
            }
        )
    
    def test_template_variable_preparation(self, service, template_context):
        """Test that all template variables are prepared correctly."""
        repository_context = {
            'repository_url': 'https://github.com/template/test-project.git',
            'repository_path': '/workspace/repos/template_test-project_jkl012',
            'repository_branch': 'develop',
            'repository_size_bytes': 5120,
            'file_count': 25,
            'last_updated': '2025-01-14T18:00:00Z',
            'is_valid': True
        }
        
        variables = service._prepare_template_variables(template_context, repository_context)
        
        # Verify all expected variables are present
        expected_vars = [
            'task_id', 'project_id', 'execution_id', 'correlation_id', 'generation_timestamp',
            'task_description', 'task_type', 'task_priority', 'current_node', 'workflow_status',
            'files_to_modify', 'files_count', 'user_id', 'metadata',
            'repository_url', 'repository_path', 'repository_branch', 'repository_size_bytes',
            'repository_file_count', 'repository_last_updated', 'repository_is_valid'
        ]
        
        for var in expected_vars:
            assert var in variables, f"Expected variable '{var}' not found in template variables"
        
        # Verify variable values
        assert variables['task_id'] == "template_test_123"
        assert variables['project_id'] == "template/test-project"
        assert variables['task_description'] == "Test template integration with all variables"
        assert variables['task_type'] == "atomic"
        assert variables['task_priority'] == "high"
        assert variables['files_count'] == 2
        assert variables['repository_branch'] == "develop"
        assert variables['repository_is_valid'] is True
    
    @patch('services.deterministic_prompt_service.get_repository_cache_manager')
    def test_real_template_rendering(self, mock_repo_manager, service, template_context):
        """Test rendering with the actual Jinja2 template."""
        # Mock repository manager
        mock_repo_manager_instance = Mock()
        mock_repo_manager.return_value = mock_repo_manager_instance
        mock_repo_manager_instance.get_repository_cache_info.return_value = {
            'cache_path': '/workspace/repos/template_test-project_jkl012',
            'size_bytes': 5120,
            'file_count': 25,
            'last_modified': '2025-01-14T18:00:00Z',
            'is_valid': True
        }
        
        service.repository_manager = mock_repo_manager_instance
        
        # Use real PromptManager (not mocked) to test actual template rendering
        result = service.generate_prompt(template_context)
        
        # Verify successful rendering
        assert result['success'] is True
        assert result['template_name'] == "aider_code_change"
        
        # Verify template content includes expected sections
        prompt = result['prompt']
        assert "# Code Change Instructions for Aider" in prompt
        assert "## Task Context" in prompt
        assert "## Repository Context" in prompt
        assert "## Files to Modify" in prompt
        assert "## Aider Instructions" in prompt
        
        # Verify specific values were rendered
        assert "template_test_123" in prompt  # task_id
        assert "template/test-project" in prompt  # project_id
        assert "Test template integration with all variables" in prompt  # task_description
        assert "atomic" in prompt  # task_type
        assert "HIGH PRIORITY" in prompt  # high priority
        assert "src/component.js" in prompt  # files
        assert "tests/component.test.js" in prompt  # files
        assert "https://github.com/template/test-project.git" in prompt  # repository_url
        assert "develop" in prompt  # repository_branch