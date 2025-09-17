"""
Unit Tests for AiderExecutionService

This module provides comprehensive unit tests for the AiderExecutionService,
covering all major functionality including container integration, Aider execution,
artifact capture, error handling, and performance validation.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from services.aider_execution_service import (
    AiderExecutionService,
    AiderExecutionContext,
    AiderExecutionResult,
    AiderExecutionError,
    get_aider_execution_service
)
from services.deterministic_prompt_service import PromptContext
from services.per_project_container_manager import ContainerError
from core.exceptions import ValidationError


class TestAiderExecutionService:
    """Test suite for AiderExecutionService class."""
    
    @pytest.fixture
    def service(self):
        """Create an AiderExecutionService instance for testing."""
        return AiderExecutionService(correlation_id="test_corr_123")
    
    @pytest.fixture
    def valid_execution_context(self):
        """Create a valid AiderExecutionContext for testing."""
        return AiderExecutionContext(
            project_id="test-project",
            execution_id="exec_123",
            correlation_id="corr_123",
            repository_url="https://github.com/test/repo.git",
            repository_branch="main",
            model="gpt-4",
            files_to_modify=["test.py"],
            timeout_seconds=1800,
            user_id="test_user"
        )
    
    @pytest.fixture
    def valid_prompt_context(self):
        """Create a valid PromptContext for testing."""
        return PromptContext(
            task_id="task_123",
            project_id="test-project",
            execution_id="exec_123",
            correlation_id="corr_123",
            task_description="Test task description",
            repository_url="https://github.com/test/repo.git",
            repository_branch="main",
            files_to_modify=["test.py"]
        )
    
    @pytest.fixture
    def mock_container(self):
        """Create a mock Docker container for testing."""
        container = Mock()
        container.id = "container_123"
        container.exec_run.return_value = (0, b"Success output")
        return container
    
    def test_service_initialization(self, service):
        """Test AiderExecutionService initialization."""
        assert service is not None
        assert service.correlation_id == "test_corr_123"
        assert service.prompt_service is not None
        assert service.container_manager is not None
        assert service.logger is not None
    
    def test_service_initialization_without_correlation_id(self):
        """Test AiderExecutionService initialization without correlation ID."""
        service = AiderExecutionService()
        assert service is not None
        assert service.correlation_id is None
        assert service.prompt_service is not None
        assert service.container_manager is not None
    
    def test_validate_execution_context_valid(self, service, valid_execution_context):
        """Test validation of valid execution context."""
        # Should not raise any exception
        service._validate_execution_context(valid_execution_context)
    
    def test_validate_execution_context_invalid_type(self, service):
        """Test validation with invalid context type."""
        with pytest.raises(ValidationError) as exc_info:
            service._validate_execution_context("invalid_context")
        
        assert "execution_context must be an AiderExecutionContext instance" in str(exc_info.value)
    
    def test_validate_execution_context_missing_required_fields(self, service):
        """Test validation with missing required fields."""
        context = AiderExecutionContext(
            project_id="",  # Empty project_id
            execution_id="exec_123"
        )
        
        with pytest.raises(ValidationError) as exc_info:
            service._validate_execution_context(context)
        
        assert "Missing required fields" in str(exc_info.value)
        assert "project_id" in str(exc_info.value)
    
    def test_validate_execution_context_invalid_project_id(self, service):
        """Test validation with invalid project ID characters."""
        context = AiderExecutionContext(
            project_id="test<>project",  # Invalid characters
            execution_id="exec_123"
        )
        
        with pytest.raises(ValidationError) as exc_info:
            service._validate_execution_context(context)
        
        assert "project_id contains invalid characters" in str(exc_info.value)
    
    def test_validate_execution_context_invalid_timeout(self, service):
        """Test validation with invalid timeout."""
        context = AiderExecutionContext(
            project_id="test-project",
            execution_id="exec_123",
            timeout_seconds=0  # Invalid timeout
        )
        
        with pytest.raises(ValidationError) as exc_info:
            service._validate_execution_context(context)
        
        assert "timeout_seconds must be between 1 and 3600 seconds" in str(exc_info.value)
    
    def test_validate_execution_context_invalid_model(self, service):
        """Test validation with invalid model name."""
        context = AiderExecutionContext(
            project_id="test-project",
            execution_id="exec_123",
            model="gpt<>4"  # Invalid characters
        )
        
        with pytest.raises(ValidationError) as exc_info:
            service._validate_execution_context(context)
        
        assert "model contains invalid characters" in str(exc_info.value)
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_setup_container_success(self, mock_get_container_manager, service, valid_execution_context):
        """Test successful container setup."""
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        # Mock container manager response
        mock_container_manager.start_or_reuse_container.return_value = {
            'success': True,
            'container_id': 'container_123',
            'container_status': 'started'
        }
        
        # Mock Docker client
        mock_container = Mock()
        mock_container.id = 'container_123'
        mock_docker_client = Mock()
        mock_docker_client.containers.get.return_value = mock_container
        mock_container_manager.docker_client = mock_docker_client
        
        result = service._setup_container(valid_execution_context)
        
        assert result['container_id'] == 'container_123'
        assert result['container_status'] == 'started'
        assert result['container'] == mock_container
        
        mock_container_manager.start_or_reuse_container.assert_called_once_with(
            project_id=valid_execution_context.project_id,
            execution_id=valid_execution_context.execution_id,
            timeout_seconds=30
        )
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_setup_container_failure(self, mock_get_container_manager, service, valid_execution_context):
        """Test container setup failure."""
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        # Mock container manager failure
        mock_container_manager.start_or_reuse_container.return_value = {
            'success': False,
            'container_id': None,
            'container_status': 'failed'
        }
        
        with pytest.raises(ContainerError) as exc_info:
            service._setup_container(valid_execution_context)
        
        assert "Failed to setup container for Aider execution" in str(exc_info.value)
    
    def test_ensure_aider_installed_already_installed(self, service, mock_container, valid_execution_context):
        """Test Aider installation when already installed."""
        # Mock Aider version check success
        mock_container.exec_run.return_value = (0, b"aider 0.35.0")
        
        # Should not raise any exception
        service._ensure_aider_installed(mock_container, valid_execution_context)
        
        # Should only call version check, not installation
        mock_container.exec_run.assert_called_once_with(service.AIDER_VERSION_COMMAND)
    
    def test_ensure_aider_installed_needs_installation(self, service, mock_container, valid_execution_context):
        """Test Aider installation when not installed."""
        # Mock version check failure, then successful installation and verification
        mock_container.exec_run.side_effect = [
            (1, b"command not found"),  # Version check fails
            (0, b"Successfully installed aider-chat"),  # Installation succeeds
            (0, b"aider 0.35.0")  # Verification succeeds
        ]
        
        service._ensure_aider_installed(mock_container, valid_execution_context)
        
        # Should call version check, install, and verify
        assert mock_container.exec_run.call_count == 3
        calls = mock_container.exec_run.call_args_list
        assert calls[0][0][0] == service.AIDER_VERSION_COMMAND
        assert calls[1][0][0] == service.AIDER_INSTALL_COMMAND
        assert calls[2][0][0] == service.AIDER_VERSION_COMMAND
    
    def test_ensure_aider_installed_installation_failure(self, service, mock_container, valid_execution_context):
        """Test Aider installation failure."""
        # Mock version check failure, then installation failure
        mock_container.exec_run.side_effect = [
            (1, b"command not found"),  # Version check fails
            (1, b"Installation failed")  # Installation fails
        ]
        
        with pytest.raises(AiderExecutionError) as exc_info:
            service._ensure_aider_installed(mock_container, valid_execution_context)
        
        assert "Failed to install Aider" in str(exc_info.value)
        assert exc_info.value.exit_code == 1
    
    def test_setup_repository_success(self, service, mock_container, valid_execution_context):
        """Test successful repository setup."""
        # Mock successful git clone
        mock_container.exec_run.return_value = (0, b"Cloning into 'repo'...")
        
        service._setup_repository(mock_container, valid_execution_context)
        
        expected_command = f"cd {valid_execution_context.working_directory} && git clone -b {valid_execution_context.repository_branch} {valid_execution_context.repository_url} repo"
        mock_container.exec_run.assert_called_once_with(expected_command)
    
    def test_setup_repository_no_url(self, service, mock_container):
        """Test repository setup with no repository URL."""
        context = AiderExecutionContext(
            project_id="test-project",
            execution_id="exec_123",
            repository_url=None  # No repository URL
        )
        
        # Should return without doing anything
        service._setup_repository(mock_container, context)
        
        # Should not call exec_run
        mock_container.exec_run.assert_not_called()
    
    def test_setup_repository_clone_failure(self, service, mock_container, valid_execution_context):
        """Test repository setup clone failure."""
        # Mock git clone failure
        mock_container.exec_run.return_value = (128, b"fatal: repository not found")
        
        with pytest.raises(AiderExecutionError) as exc_info:
            service._setup_repository(mock_container, valid_execution_context)
        
        assert "Failed to clone repository" in str(exc_info.value)
        assert exc_info.value.exit_code == 128
    
    def test_execute_aider_command_success(self, service, mock_container, valid_execution_context):
        """Test successful Aider command execution."""
        # Mock successful Aider execution
        mock_container.exec_run.return_value = (0, b"Aider execution completed successfully")
        
        result = service._execute_aider_command(mock_container, valid_execution_context)
        
        assert result['exit_code'] == 0
        assert result['stdout'] == "Aider execution completed successfully"
        assert result['stderr'] == ""
        assert "aider --model gpt-4" in result['command']
    
    def test_execute_aider_command_with_prompt(self, service, mock_container, valid_execution_context):
        """Test Aider command execution with prompt."""
        # Mock successful prompt file write and Aider execution
        mock_container.exec_run.side_effect = [
            (0, b""),  # Prompt file write
            (0, b"Aider execution with prompt completed")  # Aider execution
        ]
        
        prompt = "Test prompt for Aider"
        result = service._execute_aider_command(mock_container, valid_execution_context, prompt)
        
        assert result['exit_code'] == 0
        assert result['stdout'] == "Aider execution with prompt completed"
        assert "--message-file aider_prompt.txt" in result['command']
        
        # Should call exec_run twice (write prompt file, execute aider)
        assert mock_container.exec_run.call_count == 2
    
    def test_execute_aider_command_with_files(self, service, mock_container, valid_execution_context):
        """Test Aider command execution with specific files."""
        # Mock successful Aider execution
        mock_container.exec_run.return_value = (0, b"Aider execution with files completed")
        
        result = service._execute_aider_command(mock_container, valid_execution_context)
        
        assert result['exit_code'] == 0
        assert '"test.py"' in result['command']
    
    def test_execute_aider_command_failure(self, service, mock_container, valid_execution_context):
        """Test Aider command execution failure."""
        # Mock Aider execution failure
        mock_container.exec_run.return_value = (1, b"Aider execution failed")
        
        result = service._execute_aider_command(mock_container, valid_execution_context)
        
        assert result['exit_code'] == 1
        assert result['stdout'] == "Aider execution failed"
    
    def test_capture_execution_artifacts_success(self, service, mock_container, valid_execution_context):
        """Test successful execution artifact capture."""
        execution_result = {
            'exit_code': 0,
            'stdout': 'Modified test.py\nCreated new_file.py\ncommit abc123def456',
            'stderr': ''
        }
        
        # Mock artifact capture commands
        mock_container.exec_run.side_effect = [
            (0, b"aider 0.35.0"),  # Version check
            (0, b"diff --git a/test.py b/test.py\n+added line"),  # Git diff
            (0, b"abc123def456789")  # Git commit hash
        ]
        
        artifacts = service._capture_execution_artifacts(mock_container, valid_execution_context, execution_result)
        
        assert artifacts['aider_version'] == "aider 0.35.0"
        assert artifacts['diff_output'] == "diff --git a/test.py b/test.py\n+added line"
        assert artifacts['commit_hash'] == "abc123def456789"
        assert "test.py" in artifacts['files_modified']
        assert "new_file.py" in artifacts['files_modified']
    
    def test_capture_execution_artifacts_no_repository(self, service, mock_container):
        """Test artifact capture without repository."""
        context = AiderExecutionContext(
            project_id="test-project",
            execution_id="exec_123",
            repository_url=None  # No repository
        )
        
        execution_result = {
            'exit_code': 0,
            'stdout': 'Modified test.py',
            'stderr': ''
        }
        
        # Mock version check only
        mock_container.exec_run.return_value = (0, b"aider 0.35.0")
        
        artifacts = service._capture_execution_artifacts(mock_container, context, execution_result)
        
        assert artifacts['aider_version'] == "aider 0.35.0"
        assert artifacts['diff_output'] is None
        assert artifacts['commit_hash'] is None
        assert "test.py" in artifacts['files_modified']
    
    @patch('services.aider_execution_service.get_deterministic_prompt_service')
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_execute_aider_full_success(self, mock_get_container_manager, mock_get_prompt_service, 
                                       service, valid_execution_context, valid_prompt_context):
        """Test full Aider execution success."""
        # Mock prompt service
        mock_prompt_service = Mock()
        mock_get_prompt_service.return_value = mock_prompt_service
        service.prompt_service = mock_prompt_service
        
        mock_prompt_service.generate_prompt.return_value = {
            'success': True,
            'prompt': 'Generated test prompt'
        }
        
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        mock_container_manager.start_or_reuse_container.return_value = {
            'success': True,
            'container_id': 'container_123',
            'container_status': 'started'
        }
        
        # Mock container
        mock_container = Mock()
        mock_container.id = 'container_123'
        mock_docker_client = Mock()
        mock_docker_client.containers.get.return_value = mock_container
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock container operations
        mock_container.exec_run.side_effect = [
            (0, b"aider 0.35.0"),  # Aider version check
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b""),  # Prompt file write
            (0, b"Modified test.py\nAider execution completed"),  # Aider execution
            (0, b"aider 0.35.0"),  # Version for artifacts
            (0, b"diff --git a/test.py"),  # Git diff
            (0, b"abc123def456")  # Git commit hash
        ]
        
        result = service.execute_aider(valid_execution_context, valid_prompt_context, use_generated_prompt=True)
        
        assert result.success is True
        assert result.exit_code == 0
        assert result.project_id == valid_execution_context.project_id
        assert result.execution_id == valid_execution_context.execution_id
        assert result.container_id == 'container_123'
        assert "test.py" in result.files_modified
        assert result.total_duration_ms > 0
        assert result.aider_execution_duration_ms > 0
        assert result.container_setup_duration_ms > 0
        assert result.artifact_capture_duration_ms > 0
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_execute_aider_container_setup_failure(self, mock_get_container_manager, 
                                                   service, valid_execution_context):
        """Test Aider execution with container setup failure."""
        # Mock container manager failure
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        mock_container_manager.start_or_reuse_container.side_effect = ContainerError(
            "Container setup failed", project_id=valid_execution_context.project_id
        )
        
        with pytest.raises(ContainerError):
            service.execute_aider(valid_execution_context)
    
    def test_execute_aider_validation_failure(self, service):
        """Test Aider execution with validation failure."""
        invalid_context = AiderExecutionContext(
            project_id="",  # Invalid empty project_id
            execution_id="exec_123"
        )
        
        with pytest.raises(ValidationError):
            service.execute_aider(invalid_context)
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_execute_aider_performance_requirement(self, mock_get_container_manager, 
                                                  service, valid_execution_context):
        """Test that Aider execution meets performance requirements (≤30s)."""
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        mock_container_manager.start_or_reuse_container.return_value = {
            'success': True,
            'container_id': 'container_123',
            'container_status': 'started'
        }
        
        # Mock container
        mock_container = Mock()
        mock_container.id = 'container_123'
        mock_docker_client = Mock()
        mock_docker_client.containers.get.return_value = mock_container
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock fast container operations
        mock_container.exec_run.side_effect = [
            (0, b"aider 0.35.0"),  # Aider version check
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"Aider execution completed"),  # Aider execution
            (0, b"aider 0.35.0"),  # Version for artifacts
        ]
        
        start_time = time.time()
        result = service.execute_aider(valid_execution_context, use_generated_prompt=False)
        execution_time = time.time() - start_time
        
        # Verify performance requirement (≤30s)
        assert execution_time <= 30.0, f"Execution took {execution_time:.2f}s, exceeds 30s requirement"
        assert result.total_duration_ms <= 30000, f"Total duration {result.total_duration_ms}ms exceeds 30s requirement"
        assert result.success is True
    
    def test_get_aider_execution_service_factory(self):
        """Test factory function for AiderExecutionService."""
        service = get_aider_execution_service()
        assert isinstance(service, AiderExecutionService)
        assert service.correlation_id is None
        
        service_with_correlation = get_aider_execution_service("test_correlation")
        assert isinstance(service_with_correlation, AiderExecutionService)
        assert service_with_correlation.correlation_id == "test_correlation"


class TestAiderExecutionContext:
    """Test suite for AiderExecutionContext dataclass."""
    
    def test_context_creation_minimal(self):
        """Test creation of AiderExecutionContext with minimal fields."""
        context = AiderExecutionContext(
            project_id="test-project",
            execution_id="exec_123"
        )
        
        assert context.project_id == "test-project"
        assert context.execution_id == "exec_123"
        assert context.correlation_id is None
        assert context.repository_branch == "main"  # Default value
        assert context.model == "gpt-4"  # Default value
        assert context.timeout_seconds == 1800  # Default value
        assert context.working_directory == "/workspace"  # Default value
    
    def test_context_creation_full(self):
        """Test creation of AiderExecutionContext with all fields."""
        context = AiderExecutionContext(
            project_id="test-project",
            execution_id="exec_123",
            correlation_id="corr_123",
            repository_url="https://github.com/test/repo.git",
            repository_path="/local/repo",
            repository_branch="feature-branch",
            model="gpt-3.5-turbo",
            aider_args=["--no-auto-commits"],
            files_to_modify=["file1.py", "file2.py"],
            timeout_seconds=3600,
            working_directory="/custom/workspace",
            user_id="user_123",
            metadata={"key": "value"}
        )
        
        assert context.project_id == "test-project"
        assert context.execution_id == "exec_123"
        assert context.correlation_id == "corr_123"
        assert context.repository_url == "https://github.com/test/repo.git"
        assert context.repository_path == "/local/repo"
        assert context.repository_branch == "feature-branch"
        assert context.model == "gpt-3.5-turbo"
        assert context.aider_args == ["--no-auto-commits"]
        assert context.files_to_modify == ["file1.py", "file2.py"]
        assert context.timeout_seconds == 3600
        assert context.working_directory == "/custom/workspace"
        assert context.user_id == "user_123"
        assert context.metadata == {"key": "value"}


class TestAiderExecutionResult:
    """Test suite for AiderExecutionResult dataclass."""
    
    def test_result_creation_minimal(self):
        """Test creation of AiderExecutionResult with minimal fields."""
        result = AiderExecutionResult(
            success=True,
            execution_id="exec_123",
            project_id="test-project",
            stdout_output="Success output",
            stderr_output="",
            exit_code=0
        )
        
        assert result.success is True
        assert result.execution_id == "exec_123"
        assert result.project_id == "test-project"
        assert result.stdout_output == "Success output"
        assert result.stderr_output == ""
        assert result.exit_code == 0
        assert result.total_duration_ms == 0.0  # Default value
    
    def test_result_creation_full(self):
        """Test creation of AiderExecutionResult with all fields."""
        result = AiderExecutionResult(
            success=True,
            execution_id="exec_123",
            project_id="test-project",
            stdout_output="Success output",
            stderr_output="Warning output",
            exit_code=0,
            diff_output="diff --git a/test.py",
            files_modified=["test.py", "new_file.py"],
            commit_hash="abc123def456",
            total_duration_ms=5000.0,
            aider_execution_duration_ms=3000.0,
            container_setup_duration_ms=1000.0,
            artifact_capture_duration_ms=1000.0,
            error_message=None,
            error_type=None,
            aider_version="aider 0.35.0",
            container_id="container_123",
            execution_timestamp="2025-01-01T00:00:00Z"
        )
        
        assert result.success is True
        assert result.diff_output == "diff --git a/test.py"
        assert result.files_modified == ["test.py", "new_file.py"]
        assert result.commit_hash == "abc123def456"
        assert result.total_duration_ms == 5000.0
        assert result.aider_execution_duration_ms == 3000.0
        assert result.container_setup_duration_ms == 1000.0
        assert result.artifact_capture_duration_ms == 1000.0
        assert result.aider_version == "aider 0.35.0"
        assert result.container_id == "container_123"
        assert result.execution_timestamp == "2025-01-01T00:00:00Z"


class TestAiderExecutionError:
    """Test suite for AiderExecutionError exception."""
    
    def test_error_creation_minimal(self):
        """Test creation of AiderExecutionError with minimal fields."""
        error = AiderExecutionError("Test error message")
        
        assert str(error) == "Test error message"
        assert error.project_id is None
        assert error.execution_id is None
        assert error.exit_code is None
    
    def test_error_creation_full(self):
        """Test creation of AiderExecutionError with all fields."""
        error = AiderExecutionError(
            "Test error message",
            project_id="test-project",
            execution_id="exec_123",
            exit_code=1
        )
        
        assert str(error) == "Test error message"
        assert error.project_id == "test-project"
        assert error.execution_id == "exec_123"
        assert error.exit_code == 1


class TestNpmCiExecution:
    """Test suite for npm ci execution functionality."""
    
    @pytest.fixture
    def service(self):
        """Create an AiderExecutionService instance for testing."""
        return AiderExecutionService(correlation_id="test_npm_corr_123")
    
    @pytest.fixture
    def valid_execution_context(self):
        """Create a valid AiderExecutionContext for npm ci testing."""
        return AiderExecutionContext(
            project_id="test-npm-project",
            execution_id="npm_exec_123",
            correlation_id="npm_corr_123",
            repository_url="https://github.com/test/npm-repo.git",
            repository_branch="main",
            timeout_seconds=1800,
            user_id="test_user"
        )
    
    @pytest.fixture
    def mock_container(self):
        """Create a mock Docker container for npm testing."""
        container = Mock()
        container.id = "npm_container_123"
        container.exec_run.return_value = (0, b"npm ci completed successfully")
        return container
    
    def test_ensure_npm_available_success(self, service, mock_container, valid_execution_context):
        """Test npm availability check when npm is available."""
        # Mock npm version check success
        mock_container.exec_run.return_value = (0, b"8.19.2")
        
        # Should not raise any exception
        service._ensure_npm_available(mock_container, valid_execution_context)
        
        # Should call npm version check
        mock_container.exec_run.assert_called_once_with(service.NPM_VERSION_COMMAND)
    
    def test_ensure_npm_available_failure(self, service, mock_container, valid_execution_context):
        """Test npm availability check when npm is not available."""
        # Mock npm version check failure
        mock_container.exec_run.return_value = (127, b"npm: command not found")
        
        with pytest.raises(AiderExecutionError) as exc_info:
            service._ensure_npm_available(mock_container, valid_execution_context)
        
        assert "npm is not available in container" in str(exc_info.value)
        assert exc_info.value.exit_code == 127
    
    def test_ensure_npm_available_exception(self, service, mock_container, valid_execution_context):
        """Test npm availability check with execution exception."""
        # Mock execution exception
        mock_container.exec_run.side_effect = Exception("Container execution failed")
        
        with pytest.raises(AiderExecutionError) as exc_info:
            service._ensure_npm_available(mock_container, valid_execution_context)
        
        assert "Failed to check npm availability" in str(exc_info.value)
    
    def test_execute_npm_ci_command_success(self, service, mock_container, valid_execution_context):
        """Test successful npm ci command execution."""
        # Mock package.json exists and npm ci succeeds
        mock_container.exec_run.side_effect = [
            (0, b""),  # package.json exists
            (0, b"added 150 packages in 5s\nnpm ci completed successfully")  # npm ci success
        ]
        
        result = service._execute_npm_ci_command(mock_container, valid_execution_context)
        
        assert result['exit_code'] == 0
        assert result['stdout'] == "added 150 packages in 5s\nnpm ci completed successfully"
        assert result['stderr'] == ""
        assert result['skipped'] is False
        assert "npm ci" in result['command']
        
        # Should call package.json check and npm ci
        assert mock_container.exec_run.call_count == 2
    
    def test_execute_npm_ci_command_no_package_json(self, service, mock_container, valid_execution_context):
        """Test npm ci command when package.json doesn't exist."""
        # Mock package.json doesn't exist
        mock_container.exec_run.return_value = (1, b"test: No such file or directory")
        
        result = service._execute_npm_ci_command(mock_container, valid_execution_context)
        
        assert result['exit_code'] == 0  # Success but skipped
        assert result['stdout'] == "No package.json found, npm ci skipped"
        assert result['stderr'] == ""
        assert result['skipped'] is True
        
        # Should only call package.json check
        mock_container.exec_run.assert_called_once()
    
    def test_execute_npm_ci_command_with_custom_directory(self, service, mock_container, valid_execution_context):
        """Test npm ci command with custom working directory."""
        custom_dir = "/custom/workspace"
        
        # Mock package.json exists and npm ci succeeds
        mock_container.exec_run.side_effect = [
            (0, b""),  # package.json exists
            (0, b"npm ci completed in custom directory")  # npm ci success
        ]
        
        result = service._execute_npm_ci_command(mock_container, valid_execution_context, custom_dir)
        
        assert result['exit_code'] == 0
        assert result['skipped'] is False
        
        # Verify custom directory was used
        calls = mock_container.exec_run.call_args_list
        assert custom_dir in calls[0][0][0]  # package.json check
        assert custom_dir in calls[1][0][0]  # npm ci command
    
    def test_execute_npm_ci_command_failure(self, service, mock_container, valid_execution_context):
        """Test npm ci command execution failure."""
        # Mock package.json exists but npm ci fails
        mock_container.exec_run.side_effect = [
            (0, b""),  # package.json exists
            (1, b"npm ERR! peer dep missing: react@^18.0.0")  # npm ci fails
        ]
        
        result = service._execute_npm_ci_command(mock_container, valid_execution_context)
        
        assert result['exit_code'] == 1
        assert "npm ERR!" in result['stdout']
        assert result['skipped'] is False
    
    def test_execute_npm_ci_command_exception(self, service, mock_container, valid_execution_context):
        """Test npm ci command with execution exception."""
        # Mock execution exception
        mock_container.exec_run.side_effect = Exception("Container execution failed")
        
        with pytest.raises(AiderExecutionError) as exc_info:
            service._execute_npm_ci_command(mock_container, valid_execution_context)
        
        assert "npm ci command execution failed" in str(exc_info.value)
    
    def test_capture_npm_artifacts_success(self, service, mock_container, valid_execution_context):
        """Test successful npm artifact capture."""
        execution_result = {
            'exit_code': 0,
            'stdout': 'added 150 packages in 5s',
            'stderr': '',
            'skipped': False
        }
        
        # Mock artifact capture commands
        mock_container.exec_run.side_effect = [
            (0, b"8.19.2"),  # npm version
            (0, b""),  # package-lock.json exists
            (0, b"")   # node_modules exists
        ]
        
        artifacts = service._capture_npm_artifacts(mock_container, valid_execution_context, execution_result)
        
        assert artifacts['npm_version'] == "8.19.2"
        assert artifacts['package_lock_exists'] is True
        assert artifacts['node_modules_created'] is True
        assert artifacts['files_modified'] == ['node_modules/']
    
    def test_capture_npm_artifacts_skipped(self, service, mock_container, valid_execution_context):
        """Test npm artifact capture when npm ci was skipped."""
        execution_result = {
            'exit_code': 0,
            'stdout': 'No package.json found, npm ci skipped',
            'stderr': '',
            'skipped': True
        }
        
        # Mock artifact capture commands
        mock_container.exec_run.side_effect = [
            (0, b"8.19.2"),  # npm version
            (1, b""),  # package-lock.json doesn't exist
            (1, b"")   # node_modules doesn't exist
        ]
        
        artifacts = service._capture_npm_artifacts(mock_container, valid_execution_context, execution_result)
        
        assert artifacts['npm_version'] == "8.19.2"
        assert artifacts['package_lock_exists'] is False
        assert artifacts['node_modules_created'] is False
        assert artifacts['files_modified'] == []  # No files modified when skipped
    
    def test_capture_npm_artifacts_with_custom_directory(self, service, mock_container, valid_execution_context):
        """Test npm artifact capture with custom working directory."""
        custom_dir = "/custom/workspace"
        execution_result = {
            'exit_code': 0,
            'stdout': 'npm ci completed',
            'stderr': '',
            'skipped': False
        }
        
        # Mock artifact capture commands
        mock_container.exec_run.side_effect = [
            (0, b"8.19.2"),  # npm version
            (0, b""),  # package-lock.json exists
            (0, b"")   # node_modules exists
        ]
        
        artifacts = service._capture_npm_artifacts(mock_container, valid_execution_context, execution_result, custom_dir)
        
        assert artifacts['npm_version'] == "8.19.2"
        
        # Verify custom directory was used in commands
        calls = mock_container.exec_run.call_args_list
        assert custom_dir in calls[1][0][0]  # package-lock.json check
        assert custom_dir in calls[2][0][0]  # node_modules check
    
    def test_capture_npm_artifacts_exception_handling(self, service, mock_container, valid_execution_context):
        """Test npm artifact capture with exceptions (should not fail)."""
        execution_result = {
            'exit_code': 0,
            'stdout': 'npm ci completed',
            'stderr': '',
            'skipped': False
        }
        
        # Mock execution exception for some commands
        mock_container.exec_run.side_effect = [
            (0, b"8.19.2"),  # npm version succeeds
            Exception("Command failed"),  # package-lock.json check fails
            Exception("Command failed")   # node_modules check fails
        ]
        
        # Should not raise exception, just log warnings
        artifacts = service._capture_npm_artifacts(mock_container, valid_execution_context, execution_result)
        
        assert artifacts['npm_version'] == "8.19.2"
        assert artifacts['package_lock_exists'] is False  # Default when exception
        assert artifacts['node_modules_created'] is False  # Default when exception
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_execute_npm_ci_full_success(self, mock_get_container_manager, service, valid_execution_context):
        """Test full npm ci execution success."""
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        mock_container_manager.start_or_reuse_container.return_value = {
            'success': True,
            'container_id': 'npm_container_123',
            'container_status': 'started'
        }
        
        # Mock container
        mock_container = Mock()
        mock_container.id = 'npm_container_123'
        mock_docker_client = Mock()
        mock_docker_client.containers.get.return_value = mock_container
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock container operations
        mock_container.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"8.19.2"),  # npm version check
            (0, b""),  # package.json exists
            (0, b"added 150 packages in 5s\nnpm ci completed"),  # npm ci execution
            (0, b"8.19.2"),  # npm version for artifacts
            (0, b""),  # package-lock.json exists
            (0, b"")   # node_modules exists
        ]
        
        result = service.execute_npm_ci(valid_execution_context)
        
        assert result.success is True
        assert result.exit_code == 0
        assert result.project_id == valid_execution_context.project_id
        assert result.execution_id == valid_execution_context.execution_id
        assert result.container_id == 'npm_container_123'
        assert result.files_modified == ['node_modules/']
        assert result.total_duration_ms > 0
        assert result.aider_execution_duration_ms > 0  # Reused for npm duration
        assert result.container_setup_duration_ms > 0
        assert result.artifact_capture_duration_ms > 0
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_execute_npm_ci_no_repository(self, mock_get_container_manager, service):
        """Test npm ci execution without repository URL."""
        context = AiderExecutionContext(
            project_id="test-npm-project",
            execution_id="npm_exec_123",
            repository_url=None  # No repository URL
        )
        
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        mock_container_manager.start_or_reuse_container.return_value = {
            'success': True,
            'container_id': 'npm_container_123',
            'container_status': 'started'
        }
        
        # Mock container
        mock_container = Mock()
        mock_container.id = 'npm_container_123'
        mock_docker_client = Mock()
        mock_docker_client.containers.get.return_value = mock_container
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock container operations (no git clone)
        mock_container.exec_run.side_effect = [
            (0, b"8.19.2"),  # npm version check
            (0, b""),  # package.json exists
            (0, b"npm ci completed"),  # npm ci execution
            (0, b"8.19.2"),  # npm version for artifacts
            (0, b""),  # package-lock.json exists
            (0, b"")   # node_modules exists
        ]
        
        result = service.execute_npm_ci(context)
        
        assert result.success is True
        assert result.exit_code == 0
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_execute_npm_ci_npm_unavailable(self, mock_get_container_manager, service, valid_execution_context):
        """Test npm ci execution when npm is not available."""
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        mock_container_manager.start_or_reuse_container.return_value = {
            'success': True,
            'container_id': 'npm_container_123',
            'container_status': 'started'
        }
        
        # Mock container
        mock_container = Mock()
        mock_container.id = 'npm_container_123'
        mock_docker_client = Mock()
        mock_docker_client.containers.get.return_value = mock_container
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock container operations
        mock_container.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (127, b"npm: command not found")  # npm not available
        ]
        
        with pytest.raises(AiderExecutionError) as exc_info:
            service.execute_npm_ci(valid_execution_context)
        
        assert "npm is not available in container" in str(exc_info.value)
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_execute_npm_ci_container_setup_failure(self, mock_get_container_manager, service, valid_execution_context):
        """Test npm ci execution with container setup failure."""
        # Mock container manager failure
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        mock_container_manager.start_or_reuse_container.side_effect = ContainerError(
            "Container setup failed", project_id=valid_execution_context.project_id
        )
        
        with pytest.raises(ContainerError):
            service.execute_npm_ci(valid_execution_context)
    
    def test_execute_npm_ci_validation_failure(self, service):
        """Test npm ci execution with validation failure."""
        invalid_context = AiderExecutionContext(
            project_id="",  # Invalid empty project_id
            execution_id="npm_exec_123"
        )
        
        with pytest.raises(ValidationError):
            service.execute_npm_ci(invalid_context)
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_execute_npm_ci_performance_requirement(self, mock_get_container_manager, service, valid_execution_context):
        """Test that npm ci execution meets performance requirements (≤60s)."""
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        mock_container_manager.start_or_reuse_container.return_value = {
            'success': True,
            'container_id': 'npm_container_123',
            'container_status': 'started'
        }
        
        # Mock container
        mock_container = Mock()
        mock_container.id = 'npm_container_123'
        mock_docker_client = Mock()
        mock_docker_client.containers.get.return_value = mock_container
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock fast container operations
        mock_container.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"8.19.2"),  # npm version check
            (0, b""),  # package.json exists
            (0, b"npm ci completed"),  # npm ci execution
            (0, b"8.19.2"),  # npm version for artifacts
        ]
        
        start_time = time.time()
        result = service.execute_npm_ci(valid_execution_context)
        execution_time = time.time() - start_time
        
        # Verify performance requirement (≤60s)
        assert execution_time <= 60.0, f"Execution took {execution_time:.2f}s, exceeds 60s requirement"
        assert result.total_duration_ms <= 60000, f"Total duration {result.total_duration_ms}ms exceeds 60s requirement"
        assert result.success is True
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_execute_npm_ci_with_working_directory_override(self, mock_get_container_manager, service, valid_execution_context):
        """Test npm ci execution with working directory override."""
        custom_working_dir = "/custom/project/path"
        
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        mock_container_manager.start_or_reuse_container.return_value = {
            'success': True,
            'container_id': 'npm_container_123',
            'container_status': 'started'
        }
        
        # Mock container
        mock_container = Mock()
        mock_container.id = 'npm_container_123'
        mock_docker_client = Mock()
        mock_docker_client.containers.get.return_value = mock_container
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock container operations
        mock_container.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"8.19.2"),  # npm version check
            (0, b""),  # package.json exists
            (0, b"npm ci completed"),  # npm ci execution
            (0, b"8.19.2"),  # npm version for artifacts
            (0, b""),  # package-lock.json exists
            (0, b"")   # node_modules exists
        ]
        
        result = service.execute_npm_ci(valid_execution_context, custom_working_dir)
        
        assert result.success is True
        assert result.exit_code == 0
        
        # Verify custom working directory was used in npm commands
        calls = mock_container.exec_run.call_args_list
        npm_related_calls = [call for call in calls if 'npm' in str(call) or 'package' in str(call) or 'node_modules' in str(call)]
        
        # At least some calls should use the custom directory
        custom_dir_used = any(custom_working_dir in str(call) for call in npm_related_calls)
        assert custom_dir_used, "Custom working directory should be used in npm-related commands"


class TestNpmBuildExecution:
    """Test suite for npm run build execution functionality."""
    
    @pytest.fixture
    def service(self):
        """Create an AiderExecutionService instance for testing."""
        return AiderExecutionService(correlation_id="test_npm_build_corr_123")
    
    @pytest.fixture
    def valid_execution_context(self):
        """Create a valid AiderExecutionContext for npm build testing."""
        return AiderExecutionContext(
            project_id="test-npm-build-project",
            execution_id="npm_build_exec_123",
            correlation_id="npm_build_corr_123",
            repository_url="https://github.com/test/npm-build-repo.git",
            repository_branch="main",
            timeout_seconds=1800,
            user_id="test_user"
        )
    
    @pytest.fixture
    def mock_container(self):
        """Create a mock Docker container for npm build testing."""
        container = Mock()
        container.id = "npm_build_container_123"
        container.exec_run.return_value = (0, b"npm run build completed successfully")
        return container
    
    def test_execute_npm_build_command_success(self, service, mock_container, valid_execution_context):
        """Test successful npm run build command execution."""
        # Mock package.json exists with build script and npm build succeeds
        mock_container.exec_run.side_effect = [
            (0, b""),  # package.json exists
            (0, b'{"scripts": {"build": "webpack --mode production"}}'),  # package.json content with build script
            (0, b"webpack compiled successfully\nnpm run build completed")  # npm build success
        ]
        
        result = service._execute_npm_build_command(mock_container, valid_execution_context)
        
        assert result['exit_code'] == 0
        assert result['stdout'] == "webpack compiled successfully\nnpm run build completed"
        assert result['stderr'] == ""
        assert result['skipped'] is False
        assert "npm run build" in result['command']
        
        # Should call package.json check, content read, and npm build
        assert mock_container.exec_run.call_count == 3
    
    def test_execute_npm_build_command_no_package_json(self, service, mock_container, valid_execution_context):
        """Test npm build command when package.json doesn't exist."""
        # Mock package.json doesn't exist
        mock_container.exec_run.return_value = (1, b"test: No such file or directory")
        
        result = service._execute_npm_build_command(mock_container, valid_execution_context)
        
        assert result['exit_code'] == 0  # Success but skipped
        assert result['stdout'] == "No package.json found, npm build skipped"
        assert result['stderr'] == ""
        assert result['skipped'] is True
        assert result['skip_reason'] == "no_package_json"
        
        # Should only call package.json check
        mock_container.exec_run.assert_called_once()
    
    def test_execute_npm_build_command_no_build_script(self, service, mock_container, valid_execution_context):
        """Test npm build command when build script doesn't exist in package.json."""
        # Mock package.json exists but no build script
        mock_container.exec_run.side_effect = [
            (0, b""),  # package.json exists
            (0, b'{"scripts": {"test": "jest", "start": "node server.js"}}')  # package.json without build script
        ]
        
        result = service._execute_npm_build_command(mock_container, valid_execution_context)
        
        assert result['exit_code'] == 0  # Success but skipped
        assert result['stdout'] == "No build script found in package.json, npm build skipped"
        assert result['stderr'] == ""
        assert result['skipped'] is True
        assert result['skip_reason'] == "no_build_script"
        
        # Should call package.json check and content read
        assert mock_container.exec_run.call_count == 2
    
    def test_execute_npm_build_command_custom_build_script(self, service, mock_container, valid_execution_context):
        """Test npm build command with custom build script name."""
        # Mock package.json exists with custom build script
        mock_container.exec_run.side_effect = [
            (0, b""),  # package.json exists
            (0, b'{"scripts": {"build:prod": "webpack --mode production"}}'),  # package.json with custom build script
            (0, b"webpack compiled successfully")  # npm build success
        ]
        
        result = service._execute_npm_build_command(mock_container, valid_execution_context, build_script="build:prod")
        
        assert result['exit_code'] == 0
        assert result['skipped'] is False
        assert "npm run build:prod" in result['command']
    
    def test_execute_npm_build_command_with_custom_directory(self, service, mock_container, valid_execution_context):
        """Test npm build command with custom working directory."""
        custom_dir = "/custom/workspace"
        
        # Mock package.json exists with build script and npm build succeeds
        mock_container.exec_run.side_effect = [
            (0, b""),  # package.json exists
            (0, b'{"scripts": {"build": "webpack --mode production"}}'),  # package.json content
            (0, b"npm build completed in custom directory")  # npm build success
        ]
        
        result = service._execute_npm_build_command(mock_container, valid_execution_context, custom_dir)
        
        assert result['exit_code'] == 0
        assert result['skipped'] is False
        
        # Verify custom directory was used
        calls = mock_container.exec_run.call_args_list
        assert custom_dir in calls[0][0][0]  # package.json check
        assert custom_dir in calls[1][0][0]  # package.json content read
        assert custom_dir in calls[2][0][0]  # npm build command
    
    def test_execute_npm_build_command_failure(self, service, mock_container, valid_execution_context):
        """Test npm build command execution failure."""
        # Mock package.json exists with build script but npm build fails
        mock_container.exec_run.side_effect = [
            (0, b""),  # package.json exists
            (0, b'{"scripts": {"build": "webpack --mode production"}}'),  # package.json content
            (1, b"webpack compilation failed\nERROR in ./src/index.js")  # npm build fails
        ]
        
        result = service._execute_npm_build_command(mock_container, valid_execution_context)
        
        assert result['exit_code'] == 1
        assert "webpack compilation failed" in result['stdout']
        assert result['skipped'] is False
    
    def test_execute_npm_build_command_invalid_package_json(self, service, mock_container, valid_execution_context):
        """Test npm build command with invalid package.json content."""
        # Mock package.json exists but contains invalid JSON
        mock_container.exec_run.side_effect = [
            (0, b""),  # package.json exists
            (0, b'{"scripts": {"build": "webpack"')  # Invalid JSON (missing closing brace)
        ]
        
        result = service._execute_npm_build_command(mock_container, valid_execution_context)
        
        assert result['exit_code'] == 0  # Success but skipped
        assert result['stdout'] == "Invalid package.json format, npm build skipped"
        assert result['skipped'] is True
        assert result['skip_reason'] == "invalid_package_json"
    
    def test_execute_npm_build_command_exception(self, service, mock_container, valid_execution_context):
        """Test npm build command with execution exception."""
        # Mock execution exception
        mock_container.exec_run.side_effect = Exception("Container execution failed")
        
        with pytest.raises(AiderExecutionError) as exc_info:
            service._execute_npm_build_command(mock_container, valid_execution_context)
        
        assert "npm build command execution failed" in str(exc_info.value)
    
    def test_capture_npm_build_artifacts_success(self, service, mock_container, valid_execution_context):
        """Test successful npm build artifact capture."""
        execution_result = {
            'exit_code': 0,
            'stdout': 'webpack compiled successfully\nBuild completed',
            'stderr': '',
            'skipped': False
        }
        
        # Mock artifact capture commands
        mock_container.exec_run.side_effect = [
            (0, b"8.19.2"),  # npm version
            (0, b""),  # dist directory exists
            (0, b"index.html\nmain.js\nstyle.css"),  # dist directory contents
            (1, b""),  # build directory doesn't exist
            (1, b""),  # out directory doesn't exist
            (1, b""),  # public directory doesn't exist
            (1, b""),  # .next directory doesn't exist
            (1, b""),  # lib directory doesn't exist
            (1, b"")   # es directory doesn't exist
        ]
        
        artifacts = service._capture_npm_build_artifacts(mock_container, valid_execution_context, execution_result)
        
        assert artifacts['npm_version'] == "8.19.2"
        assert artifacts['build_output_directories'] == ['dist']
        assert artifacts['build_artifacts'] == ['dist/index.html', 'dist/main.js', 'dist/style.css']
        assert artifacts['files_modified'] == ['dist/']
    
    def test_capture_npm_build_artifacts_multiple_directories(self, service, mock_container, valid_execution_context):
        """Test npm build artifact capture with multiple build output directories."""
        execution_result = {
            'exit_code': 0,
            'stdout': 'Build completed',
            'stderr': '',
            'skipped': False
        }
        
        # Mock artifact capture commands - multiple directories exist
        mock_container.exec_run.side_effect = [
            (0, b"8.19.2"),  # npm version
            (0, b""),  # dist directory exists
            (0, b"index.html"),  # dist directory contents
            (0, b""),  # build directory exists
            (0, b"static/js/main.js"),  # build directory contents
            (1, b""),  # out directory doesn't exist
            (1, b""),  # public directory doesn't exist
            (1, b""),  # .next directory doesn't exist
            (1, b""),  # lib directory doesn't exist
            (1, b"")   # es directory doesn't exist
        ]
        
        artifacts = service._capture_npm_build_artifacts(mock_container, valid_execution_context, execution_result)
        
        assert artifacts['npm_version'] == "8.19.2"
        assert set(artifacts['build_output_directories']) == {'dist', 'build'}
        assert set(artifacts['build_artifacts']) == {'dist/index.html', 'build/static/js/main.js'}
        assert set(artifacts['files_modified']) == {'dist/', 'build/'}
    
    def test_capture_npm_build_artifacts_skipped(self, service, mock_container, valid_execution_context):
        """Test npm build artifact capture when npm build was skipped."""
        execution_result = {
            'exit_code': 0,
            'stdout': 'No package.json found, npm build skipped',
            'stderr': '',
            'skipped': True
        }
        
        # Mock artifact capture commands
        mock_container.exec_run.side_effect = [
            (0, b"8.19.2"),  # npm version
        ]
        
        artifacts = service._capture_npm_build_artifacts(mock_container, valid_execution_context, execution_result)
        
        assert artifacts['npm_version'] == "8.19.2"
        assert artifacts['build_output_directories'] == []
        assert artifacts['build_artifacts'] == []
        assert artifacts['files_modified'] == []  # No files modified when skipped
    
    def test_capture_npm_build_artifacts_with_custom_directory(self, service, mock_container, valid_execution_context):
        """Test npm build artifact capture with custom working directory."""
        custom_dir = "/custom/workspace"
        execution_result = {
            'exit_code': 0,
            'stdout': 'npm build completed',
            'stderr': '',
            'skipped': False
        }
        
        # Mock artifact capture commands
        mock_container.exec_run.side_effect = [
            (0, b"8.19.2"),  # npm version
            (0, b""),  # dist directory exists
            (0, b"index.html"),  # dist directory contents
            (1, b""),  # build directory doesn't exist
            (1, b""),  # out directory doesn't exist
            (1, b""),  # public directory doesn't exist
            (1, b""),  # .next directory doesn't exist
            (1, b""),  # lib directory doesn't exist
            (1, b"")   # es directory doesn't exist
        ]
        
        artifacts = service._capture_npm_build_artifacts(mock_container, valid_execution_context, execution_result, custom_dir)
        
        assert artifacts['npm_version'] == "8.19.2"
        assert artifacts['build_output_directories'] == ['dist']
        
        # Verify custom directory was used in commands
        calls = mock_container.exec_run.call_args_list
        build_dir_calls = [call for call in calls[1:] if 'test -d' in str(call)]
        assert all(custom_dir in str(call) for call in build_dir_calls)
    
    def test_capture_npm_build_artifacts_exception_handling(self, service, mock_container, valid_execution_context):
        """Test npm build artifact capture with exceptions (should not fail)."""
        execution_result = {
            'exit_code': 0,
            'stdout': 'npm build completed',
            'stderr': '',
            'skipped': False
        }
        
        # Mock execution exception for some commands
        mock_container.exec_run.side_effect = [
            (0, b"8.19.2"),  # npm version succeeds
            Exception("Command failed"),  # dist directory check fails
            Exception("Command failed")   # build directory check fails
        ]
        
        # Should not raise exception, just log warnings
        artifacts = service._capture_npm_build_artifacts(mock_container, valid_execution_context, execution_result)
        
        assert artifacts['npm_version'] == "8.19.2"
        assert artifacts['build_output_directories'] == []  # Default when exception
        assert artifacts['build_artifacts'] == []  # Default when exception
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_execute_npm_build_full_success(self, mock_get_container_manager, service, valid_execution_context):
        """Test full npm build execution success."""
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        mock_container_manager.start_or_reuse_container.return_value = {
            'success': True,
            'container_id': 'npm_build_container_123',
            'container_status': 'started'
        }
        
        # Mock container
        mock_container = Mock()
        mock_container.id = 'npm_build_container_123'
        mock_docker_client = Mock()
        mock_docker_client.containers.get.return_value = mock_container
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock container operations
        mock_container.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"8.19.2"),  # npm version check
            (0, b""),  # package.json exists
            (0, b'{"scripts": {"build": "webpack --mode production"}}'),  # package.json content
            (0, b"webpack compiled successfully\nnpm build completed"),  # npm build execution
            (0, b"8.19.2"),  # npm version for artifacts
            (0, b""),  # dist directory exists
            (0, b"index.html\nmain.js"),  # dist directory contents
            (1, b""),  # build directory doesn't exist
            (1, b""),  # out directory doesn't exist
            (1, b""),  # public directory doesn't exist
            (1, b""),  # .next directory doesn't exist
            (1, b""),  # lib directory doesn't exist
            (1, b"")   # es directory doesn't exist
        ]
        
        result = service.execute_npm_build(valid_execution_context)
        
        assert result.success is True
        assert result.exit_code == 0
        assert result.project_id == valid_execution_context.project_id
        assert result.execution_id == valid_execution_context.execution_id
        assert result.container_id == 'npm_build_container_123'
        assert result.files_modified == ['dist/']
        assert result.total_duration_ms > 0
        assert result.aider_execution_duration_ms > 0  # Reused for npm duration
        assert result.container_setup_duration_ms > 0
        assert result.artifact_capture_duration_ms > 0
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_execute_npm_build_no_repository(self, mock_get_container_manager, service):
        """Test npm build execution without repository URL."""
        context = AiderExecutionContext(
            project_id="test-npm-build-project",
            execution_id="npm_build_exec_123",
            repository_url=None  # No repository URL
        )
        
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        mock_container_manager.start_or_reuse_container.return_value = {
            'success': True,
            'container_id': 'npm_build_container_123',
            'container_status': 'started'
        }
        
        # Mock container
        mock_container = Mock()
        mock_container.id = 'npm_build_container_123'
        mock_docker_client = Mock()
        mock_docker_client.containers.get.return_value = mock_container
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock container operations (no git clone)
        mock_container.exec_run.side_effect = [
            (0, b"8.19.2"),  # npm version check
            (0, b""),  # package.json exists
            (0, b'{"scripts": {"build": "webpack"}}'),  # package.json content
            (0, b"npm build completed"),  # npm build execution
            (0, b"8.19.2"),  # npm version for artifacts
            (0, b""),  # dist directory exists
            (0, b"index.html"),  # dist directory contents
            (1, b""),  # build directory doesn't exist
            (1, b""),  # out directory doesn't exist
            (1, b""),  # public directory doesn't exist
            (1, b""),  # .next directory doesn't exist
            (1, b""),  # lib directory doesn't exist
            (1, b"")   # es directory doesn't exist
        ]
        
        result = service.execute_npm_build(context)
        
        assert result.success is True
        assert result.exit_code == 0
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_execute_npm_build_npm_unavailable(self, mock_get_container_manager, service, valid_execution_context):
        """Test npm build execution when npm is not available."""
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        mock_container_manager.start_or_reuse_container.return_value = {
            'success': True,
            'container_id': 'npm_build_container_123',
            'container_status': 'started'
        }
        
        # Mock container
        mock_container = Mock()
        mock_container.id = 'npm_build_container_123'
        mock_docker_client = Mock()
        mock_docker_client.containers.get.return_value = mock_container
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock container operations
        mock_container.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (127, b"npm: command not found")  # npm not available
        ]
        
        with pytest.raises(AiderExecutionError) as exc_info:
            service.execute_npm_build(valid_execution_context)
        
        assert "npm is not available in container" in str(exc_info.value)
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_execute_npm_build_container_setup_failure(self, mock_get_container_manager, service, valid_execution_context):
        """Test npm build execution with container setup failure."""
        # Mock container manager failure
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        mock_container_manager.start_or_reuse_container.side_effect = ContainerError(
            "Container setup failed", project_id=valid_execution_context.project_id
        )
        
        with pytest.raises(ContainerError):
            service.execute_npm_build(valid_execution_context)
    
    def test_execute_npm_build_validation_failure(self, service):
        """Test npm build execution with validation failure."""
        invalid_context = AiderExecutionContext(
            project_id="",  # Invalid empty project_id
            execution_id="npm_build_exec_123"
        )
        
        with pytest.raises(ValidationError):
            service.execute_npm_build(invalid_context)
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_execute_npm_build_performance_requirement(self, mock_get_container_manager, service, valid_execution_context):
        """Test that npm build execution meets performance requirements (≤60s)."""
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        mock_container_manager.start_or_reuse_container.return_value = {
            'success': True,
            'container_id': 'npm_build_container_123',
            'container_status': 'started'
        }
        
        # Mock container
        mock_container = Mock()
        mock_container.id = 'npm_build_container_123'
        mock_docker_client = Mock()
        mock_docker_client.containers.get.return_value = mock_container
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock fast container operations
        mock_container.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"8.19.2"),  # npm version check
            (0, b""),  # package.json exists
            (0, b'{"scripts": {"build": "webpack"}}'),  # package.json content
            (0, b"npm build completed"),  # npm build execution
            (0, b"8.19.2"),  # npm version for artifacts
        ]
        
        start_time = time.time()
        result = service.execute_npm_build(valid_execution_context)
        execution_time = time.time() - start_time
        
        # Verify performance requirement (≤60s)
        assert execution_time <= 60.0, f"Execution took {execution_time:.2f}s, exceeds 60s requirement"
        assert result.total_duration_ms <= 60000, f"Total duration {result.total_duration_ms}ms exceeds 60s requirement"
        assert result.success is True
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_execute_npm_build_with_working_directory_override(self, mock_get_container_manager, service, valid_execution_context):
        """Test npm build execution with working directory override."""
        custom_working_dir = "/custom/project/path"
        
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        mock_container_manager.start_or_reuse_container.return_value = {
            'success': True,
            'container_id': 'npm_build_container_123',
            'container_status': 'started'
        }
        
        # Mock container
        mock_container = Mock()
        mock_container.id = 'npm_build_container_123'
        mock_docker_client = Mock()
        mock_docker_client.containers.get.return_value = mock_container
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock container operations
        mock_container.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"8.19.2"),  # npm version check
            (0, b""),  # package.json exists
            (0, b'{"scripts": {"build": "webpack"}}'),  # package.json content
            (0, b"npm build completed"),  # npm build execution
            (0, b"8.19.2"),  # npm version for artifacts
            (0, b""),  # dist directory exists
            (0, b"index.html"),  # dist directory contents
            (1, b""),  # build directory doesn't exist
            (1, b""),  # out directory doesn't exist
            (1, b""),  # public directory doesn't exist
            (1, b""),  # .next directory doesn't exist
            (1, b""),  # lib directory doesn't exist
            (1, b"")   # es directory doesn't exist
        ]
        
        result = service.execute_npm_build(valid_execution_context, custom_working_dir)
        
        assert result.success is True
        assert result.exit_code == 0
        
        # Verify custom working directory was used in npm commands
        calls = mock_container.exec_run.call_args_list
        npm_related_calls = [call for call in calls if 'npm' in str(call) or 'package' in str(call) or 'test -d' in str(call)]
        
        # At least some calls should use the custom directory
        custom_dir_used = any(custom_working_dir in str(call) for call in npm_related_calls)
        assert custom_dir_used, "Custom working directory should be used in npm-related commands"
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_execute_npm_build_with_custom_build_script(self, mock_get_container_manager, service, valid_execution_context):
        """Test npm build execution with custom build script name."""
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        mock_container_manager.start_or_reuse_container.return_value = {
            'success': True,
            'container_id': 'npm_build_container_123',
            'container_status': 'started'
        }
        
        # Mock container
        mock_container = Mock()
        mock_container.id = 'npm_build_container_123'
        mock_docker_client = Mock()
        mock_docker_client.containers.get.return_value = mock_container
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock container operations
        mock_container.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"8.19.2"),  # npm version check
            (0, b""),  # package.json exists
            (0, b'{"scripts": {"build:prod": "webpack --mode production"}}'),  # package.json with custom script
            (0, b"webpack compiled successfully"),  # npm build execution
            (0, b"8.19.2"),  # npm version for artifacts
            (0, b""),  # dist directory exists
            (0, b"index.html"),  # dist directory contents
            (1, b""),  # build directory doesn't exist
            (1, b""),  # out directory doesn't exist
            (1, b""),  # public directory doesn't exist
            (1, b""),  # .next directory doesn't exist
            (1, b""),  # lib directory doesn't exist
            (1, b"")   # es directory doesn't exist
        ]
        
        result = service.execute_npm_build(valid_execution_context, build_script="build:prod")
        
        assert result.success is True
        assert result.exit_code == 0
        
        # Verify custom build script was used
        calls = mock_container.exec_run.call_args_list
        npm_build_calls = [call for call in calls if 'npm run' in str(call)]
        assert any('build:prod' in str(call) for call in npm_build_calls)


class TestGitMergeExecution:
    """Test suite for git merge execution functionality."""
    
    @pytest.fixture
    def service(self):
        """Create an AiderExecutionService instance for testing."""
        return AiderExecutionService(correlation_id="test_git_merge_corr_123")
    
    @pytest.fixture
    def valid_execution_context(self):
        """Create a valid AiderExecutionContext for git merge testing."""
        return AiderExecutionContext(
            project_id="test-git-merge-project",
            execution_id="git_merge_exec_123",
            correlation_id="git_merge_corr_123",
            repository_url="https://github.com/test/git-merge-repo.git",
            repository_branch="main",
            timeout_seconds=1800,
            user_id="test_user"
        )
    
    @pytest.fixture
    def mock_container(self):
        """Create a mock Docker container for git merge testing."""
        container = Mock()
        container.id = "git_merge_container_123"
        container.exec_run.return_value = (0, b"git merge completed successfully")
        return container
    
    def test_validate_branch_names_success(self, service, valid_execution_context):
        """Test successful branch name validation."""
        # Should not raise any exception
        service._validate_branch_names("feature/task-123", "main", valid_execution_context)
        service._validate_branch_names("task/456-feature-branch", "develop", valid_execution_context)
        service._validate_branch_names("hotfix/bug-fix", "release/v1.0", valid_execution_context)
    
    def test_validate_branch_names_invalid_source(self, service, valid_execution_context):
        """Test branch name validation with invalid source branch."""
        with pytest.raises(ValidationError) as exc_info:
            service._validate_branch_names("", "main", valid_execution_context)
        
        assert "Source branch name is required" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            service._validate_branch_names("feature<>branch", "main", valid_execution_context)
        
        assert "Source branch name contains invalid characters" in str(exc_info.value)
    
    def test_validate_branch_names_invalid_target(self, service, valid_execution_context):
        """Test branch name validation with invalid target branch."""
        with pytest.raises(ValidationError) as exc_info:
            service._validate_branch_names("feature/task-123", "", valid_execution_context)
        
        assert "Target branch name is required" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            service._validate_branch_names("feature/task-123", "main<>branch", valid_execution_context)
        
        assert "Target branch name contains invalid characters" in str(exc_info.value)
    
    def test_validate_branch_names_same_branches(self, service, valid_execution_context):
        """Test branch name validation with same source and target branches."""
        with pytest.raises(ValidationError) as exc_info:
            service._validate_branch_names("main", "main", valid_execution_context)
        
        assert "Source and target branches cannot be the same" in str(exc_info.value)
    
    def test_detect_merge_conflicts_exit_code_1(self, service):
        """Test merge conflict detection via exit code 1."""
        assert service._detect_merge_conflicts("Some merge output", 1) is True
    
    def test_detect_merge_conflicts_conflict_markers(self, service):
        """Test merge conflict detection via conflict markers in output."""
        conflict_outputs = [
            "CONFLICT (content): Merge conflict in file.txt",
            "Automatic merge failed; fix conflicts and then commit the result.",
            "<<<<<<< HEAD\nconflict content\n=======\nother content\n>>>>>>> branch",
            "fix conflicts and then commit"
        ]
        
        for output in conflict_outputs:
            assert service._detect_merge_conflicts(output, 0) is True
    
    def test_detect_merge_conflicts_no_conflicts(self, service):
        """Test merge conflict detection with no conflicts."""
        clean_outputs = [
            "Merge made by the 'recursive' strategy.",
            "Fast-forward merge completed",
            "Already up to date."
        ]
        
        for output in clean_outputs:
            assert service._detect_merge_conflicts(output, 0) is False
    
    def test_execute_git_merge_command_success(self, service, mock_container, valid_execution_context):
        """Test successful git merge command execution."""
        # Mock git checkout and merge success
        mock_container.exec_run.side_effect = [
            (0, b"Switched to branch 'main'"),  # git checkout
            (0, b"Merge made by the 'recursive' strategy.\n 1 file changed, 5 insertions(+)")  # git merge
        ]
        
        result = service._execute_git_merge_command(
            mock_container,
            valid_execution_context,
            "feature/task-123",
            "main"
        )
        
        assert result['exit_code'] == 0
        assert result['stdout'] == "Merge made by the 'recursive' strategy.\n 1 file changed, 5 insertions(+)"
        assert result['stderr'] == ""
        assert result['has_conflicts'] is False
        assert result['source_branch'] == "feature/task-123"
        assert result['target_branch'] == "main"
        
        # Should call git checkout and git merge
        assert mock_container.exec_run.call_count == 2
    
    def test_execute_git_merge_command_with_conflicts(self, service, mock_container, valid_execution_context):
        """Test git merge command execution with conflicts."""
        # Mock git checkout success and merge with conflicts
        mock_container.exec_run.side_effect = [
            (0, b"Switched to branch 'main'"),  # git checkout
            (1, b"CONFLICT (content): Merge conflict in file.txt\nAutomatic merge failed; fix conflicts and then commit the result.")  # git merge with conflicts
        ]
        
        result = service._execute_git_merge_command(
            mock_container,
            valid_execution_context,
            "feature/task-123",
            "main"
        )
        
        assert result['exit_code'] == 1
        assert "CONFLICT" in result['stdout']
        assert result['has_conflicts'] is True
        assert result['source_branch'] == "feature/task-123"
        assert result['target_branch'] == "main"
    
    def test_execute_git_merge_command_checkout_failure(self, service, mock_container, valid_execution_context):
        """Test git merge command with checkout failure."""
        # Mock git checkout failure
        mock_container.exec_run.return_value = (128, b"error: pathspec 'nonexistent-branch' did not match any file(s) known to git")
        
        with pytest.raises(AiderExecutionError) as exc_info:
            service._execute_git_merge_command(
                mock_container,
                valid_execution_context,
                "feature/task-123",
                "nonexistent-branch"
            )
        
        assert "Failed to checkout target branch" in str(exc_info.value)
        assert exc_info.value.exit_code == 128
    
    def test_execute_git_merge_command_with_custom_directory(self, service, mock_container, valid_execution_context):
        """Test git merge command with custom working directory."""
        custom_dir = "/custom/workspace"
        
        # Mock git checkout and merge success
        mock_container.exec_run.side_effect = [
            (0, b"Switched to branch 'main'"),  # git checkout
            (0, b"Merge completed in custom directory")  # git merge
        ]
        
        result = service._execute_git_merge_command(
            mock_container,
            valid_execution_context,
            "feature/task-123",
            "main",
            custom_dir
        )
        
        assert result['exit_code'] == 0
        assert result['has_conflicts'] is False
        
        # Verify custom directory was used
        calls = mock_container.exec_run.call_args_list
        assert custom_dir in calls[0][0][0]  # git checkout command
        assert custom_dir in calls[1][0][0]  # git merge command
    
    def test_execute_git_merge_command_exception(self, service, mock_container, valid_execution_context):
        """Test git merge command with execution exception."""
        # Mock execution exception
        mock_container.exec_run.side_effect = Exception("Container execution failed")
        
        with pytest.raises(AiderExecutionError) as exc_info:
            service._execute_git_merge_command(
                mock_container,
                valid_execution_context,
                "feature/task-123",
                "main"
            )
        
        assert "Git merge command execution failed" in str(exc_info.value)
    
    def test_capture_git_merge_artifacts_success(self, service, mock_container, valid_execution_context):
        """Test successful git merge artifact capture."""
        execution_result = {
            'exit_code': 0,
            'stdout': 'Merge made by recursive strategy',
            'stderr': '',
            'has_conflicts': False,
            'source_branch': 'feature/task-123',
            'target_branch': 'main'
        }
        
        # Mock artifact capture commands
        mock_container.exec_run.side_effect = [
            (0, b"abc123def456789"),  # git log commit hash
            (0, b"commit abc123def456789\nAuthor: Test User\nDate: 2025-01-01\n\nfile1.py\nfile2.js")  # git show
        ]
        
        artifacts = service._capture_git_merge_artifacts(
            mock_container,
            valid_execution_context,
            execution_result
        )
        
        assert artifacts['commit_hash'] == "abc123def456789"
        assert artifacts['diff_output'] == "commit abc123def456789\nAuthor: Test User\nDate: 2025-01-01\n\nfile1.py\nfile2.js"
        assert "file1.py" in artifacts['files_modified']
        assert "file2.js" in artifacts['files_modified']
        assert artifacts['has_conflicts'] is False
        assert artifacts['source_branch'] == 'feature/task-123'
        assert artifacts['target_branch'] == 'main'
        assert artifacts['merge_conflicts'] == []
    
    def test_capture_git_merge_artifacts_with_conflicts(self, service, mock_container, valid_execution_context):
        """Test git merge artifact capture with conflicts."""
        execution_result = {
            'exit_code': 1,
            'stdout': 'CONFLICT (content): Merge conflict in file.txt',
            'stderr': '',
            'has_conflicts': True,
            'source_branch': 'feature/task-123',
            'target_branch': 'main'
        }
        
        # Mock git status for conflict files
        mock_container.exec_run.return_value = (0, b"UU file1.txt\nAA file2.py\nDD file3.js")
        
        artifacts = service._capture_git_merge_artifacts(
            mock_container,
            valid_execution_context,
            execution_result
        )
        
        assert artifacts['commit_hash'] is None  # No commit hash for failed merge
        assert artifacts['has_conflicts'] is True
        assert artifacts['merge_conflicts'] == ['file1.txt', 'file2.py', 'file3.js']
        assert artifacts['source_branch'] == 'feature/task-123'
        assert artifacts['target_branch'] == 'main'
    
    def test_capture_git_merge_artifacts_with_custom_directory(self, service, mock_container, valid_execution_context):
        """Test git merge artifact capture with custom working directory."""
        custom_dir = "/custom/workspace"
        execution_result = {
            'exit_code': 0,
            'stdout': 'Merge completed',
            'stderr': '',
            'has_conflicts': False,
            'source_branch': 'feature/task-123',
            'target_branch': 'main'
        }
        
        # Mock artifact capture commands
        mock_container.exec_run.side_effect = [
            (0, b"abc123def456789"),  # git log commit hash
            (0, b"file1.py\nfile2.js")  # git show
        ]
        
        artifacts = service._capture_git_merge_artifacts(
            mock_container,
            valid_execution_context,
            execution_result,
            custom_dir
        )
        
        assert artifacts['commit_hash'] == "abc123def456789"
        
        # Verify custom directory was used in commands
        calls = mock_container.exec_run.call_args_list
        assert all(custom_dir in str(call) for call in calls)
    
    def test_capture_git_merge_artifacts_exception_handling(self, service, mock_container, valid_execution_context):
        """Test git merge artifact capture with exceptions (should not fail)."""
        execution_result = {
            'exit_code': 0,
            'stdout': 'Merge completed',
            'stderr': '',
            'has_conflicts': False,
            'source_branch': 'feature/task-123',
            'target_branch': 'main'
        }
        
        # Mock execution exception for some commands
        mock_container.exec_run.side_effect = Exception("Command failed")
        
        # Should not raise exception, just log warnings
        artifacts = service._capture_git_merge_artifacts(
            mock_container,
            valid_execution_context,
            execution_result
        )
        
        assert artifacts['commit_hash'] is None  # Default when exception
        assert artifacts['diff_output'] is None  # Default when exception
        assert artifacts['has_conflicts'] is False
        assert artifacts['source_branch'] == 'feature/task-123'
        assert artifacts['target_branch'] == 'main'
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_execute_git_merge_full_success(self, mock_get_container_manager, service, valid_execution_context):
        """Test full git merge execution success."""
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        mock_container_manager.start_or_reuse_container.return_value = {
            'success': True,
            'container_id': 'git_merge_container_123',
            'container_status': 'started'
        }
        
        # Mock container
        mock_container = Mock()
        mock_container.id = 'git_merge_container_123'
        mock_docker_client = Mock()
        mock_docker_client.containers.get.return_value = mock_container
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock container operations
        mock_container.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"Switched to branch 'main'"),  # Git checkout
            (0, b"Merge made by the 'recursive' strategy.\n 1 file changed, 5 insertions(+)"),  # Git merge
            (0, b"abc123def456789"),  # Git log commit hash
            (0, b"file1.py\nfile2.js")  # Git show files
        ]
        
        result = service.execute_git_merge(
            valid_execution_context,
            "feature/task-123",
            "main"
        )
        
        assert result.success is True
        assert result.exit_code == 0
        assert result.project_id == valid_execution_context.project_id
        assert result.execution_id == valid_execution_context.execution_id
        assert result.container_id == 'git_merge_container_123'
        assert result.commit_hash == "abc123def456789"
        assert "file1.py" in result.files_modified
        assert "file2.js" in result.files_modified
        assert result.total_duration_ms > 0
        assert result.aider_execution_duration_ms > 0  # Reused for merge duration
        assert result.container_setup_duration_ms > 0
        assert result.artifact_capture_duration_ms > 0
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_execute_git_merge_with_conflicts(self, mock_get_container_manager, service, valid_execution_context):
        """Test git merge execution with conflicts."""
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        mock_container_manager.start_or_reuse_container.return_value = {
            'success': True,
            'container_id': 'git_merge_container_123',
            'container_status': 'started'
        }
        
        # Mock container
        mock_container = Mock()
        mock_container.id = 'git_merge_container_123'
        mock_docker_client = Mock()
        mock_docker_client.containers.get.return_value = mock_container
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock container operations with conflicts
        mock_container.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"Switched to branch 'main'"),  # Git checkout
            (1, b"CONFLICT (content): Merge conflict in file.txt\nAutomatic merge failed; fix conflicts and then commit the result."),  # Git merge with conflicts
            (0, b"UU file.txt")  # Git status for conflicts
        ]
        
        result = service.execute_git_merge(
            valid_execution_context,
            "feature/task-123",
            "main"
        )
        
        assert result.success is False
        assert result.exit_code == 1
        assert result.commit_hash is None  # No commit hash for failed merge
        assert result.files_modified == []  # No files modified due to conflicts
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_execute_git_merge_no_repository(self, mock_get_container_manager, service):
        """Test git merge execution without repository URL."""
        context = AiderExecutionContext(
            project_id="test-git-merge-project",
            execution_id="git_merge_exec_123",
            repository_url=None  # No repository URL
        )
        
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        mock_container_manager.start_or_reuse_container.return_value = {
            'success': True,
            'container_id': 'git_merge_container_123',
            'container_status': 'started'
        }
        
        # Mock container
        mock_container = Mock()
        mock_container.id = 'git_merge_container_123'
        mock_docker_client = Mock()
        mock_docker_client.containers.get.return_value = mock_container
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock container operations (no git clone)
        mock_container.exec_run.side_effect = [
            (0, b"Switched to branch 'main'"),  # Git checkout
            (0, b"Merge completed"),  # Git merge
            (0, b"abc123def456789"),  # Git log commit hash
            (0, b"file1.py")  # Git show files
        ]
        
        result = service.execute_git_merge(context, "feature/task-123", "main")
        
        assert result.success is True
        assert result.exit_code == 0
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_execute_git_merge_container_setup_failure(self, mock_get_container_manager, service, valid_execution_context):
        """Test git merge execution with container setup failure."""
        # Mock container manager failure
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        mock_container_manager.start_or_reuse_container.side_effect = ContainerError(
            "Container setup failed", project_id=valid_execution_context.project_id
        )
        
        with pytest.raises(ContainerError):
            service.execute_git_merge(valid_execution_context, "feature/task-123", "main")
    
    def test_execute_git_merge_validation_failure(self, service):
        """Test git merge execution with validation failure."""
        invalid_context = AiderExecutionContext(
            project_id="",  # Invalid empty project_id
            execution_id="git_merge_exec_123"
        )
        
        with pytest.raises(ValidationError):
            service.execute_git_merge(invalid_context, "feature/task-123", "main")
    
    def test_execute_git_merge_branch_validation_failure(self, service, valid_execution_context):
        """Test git merge execution with branch validation failure."""
        with pytest.raises(ValidationError):
            service.execute_git_merge(valid_execution_context, "", "main")  # Empty source branch
        
        with pytest.raises(ValidationError):
            service.execute_git_merge(valid_execution_context, "main", "main")  # Same branches
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_execute_git_merge_performance_requirement(self, mock_get_container_manager, service, valid_execution_context):
        """Test that git merge execution meets performance requirements (≤60s)."""
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        mock_container_manager.start_or_reuse_container.return_value = {
            'success': True,
            'container_id': 'git_merge_container_123',
            'container_status': 'started'
        }
        
        # Mock container
        mock_container = Mock()
        mock_container.id = 'git_merge_container_123'
        mock_docker_client = Mock()
        mock_docker_client.containers.get.return_value = mock_container
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock fast container operations
        mock_container.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"Switched to branch 'main'"),  # Git checkout
            (0, b"Merge completed"),  # Git merge
            (0, b"abc123def456789"),  # Git log commit hash
        ]
        
        start_time = time.time()
        result = service.execute_git_merge(valid_execution_context, "feature/task-123", "main")
        execution_time = time.time() - start_time
        
        # Verify performance requirement (≤60s)
        assert execution_time <= 60.0, f"Execution took {execution_time:.2f}s, exceeds 60s requirement"
        assert result.total_duration_ms <= 60000, f"Total duration {result.total_duration_ms}ms exceeds 60s requirement"
        assert result.success is True
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_execute_git_merge_with_working_directory_override(self, mock_get_container_manager, service, valid_execution_context):
        """Test git merge execution with working directory override."""
        custom_working_dir = "/custom/project/path"
        
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        mock_container_manager.start_or_reuse_container.return_value = {
            'success': True,
            'container_id': 'git_merge_container_123',
            'container_status': 'started'
        }
        
        # Mock container
        mock_container = Mock()
        mock_container.id = 'git_merge_container_123'
        mock_docker_client = Mock()
        mock_docker_client.containers.get.return_value = mock_container
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock container operations
        mock_container.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"Switched to branch 'main'"),  # Git checkout
            (0, b"Merge completed"),  # Git merge
            (0, b"abc123def456789"),  # Git log commit hash
            (0, b"file1.py")  # Git show files
        ]
        
        result = service.execute_git_merge(
            valid_execution_context,
            "feature/task-123",
            "main",
            custom_working_dir
        )
        
        assert result.success is True
        assert result.exit_code == 0
        
        # Verify custom working directory was used in git commands
        calls = mock_container.exec_run.call_args_list
        git_related_calls = [call for call in calls if 'git' in str(call)]
        
        # At least some calls should use the custom directory
        custom_dir_used = any(custom_working_dir in str(call) for call in git_related_calls)
        assert custom_dir_used, "Custom working directory should be used in git-related commands"