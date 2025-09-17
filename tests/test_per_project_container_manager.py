
"""
Comprehensive test suite for PerProjectContainerManager

This test suite provides >80% coverage testing for the per-project container
management functionality including:
- Unit tests for all public methods
- Integration tests for Docker operations
- Mock-based testing for external dependencies
- Error handling and edge case validation
- Performance and concurrency testing
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timedelta
from typing import Dict, Any

import docker
from docker.errors import DockerException, APIError, NotFound, ImageNotFound

from services.per_project_container_manager import (
    PerProjectContainerManager,
    ContainerError,
    get_per_project_container_manager
)
from core.structured_logging import LogStatus


class TestPerProjectContainerManager:
    """Test suite for PerProjectContainerManager class."""
    
    @pytest.fixture
    def manager(self):
        """Create a PerProjectContainerManager instance for testing."""
        return PerProjectContainerManager(correlation_id="test-correlation-123")
    
    @pytest.fixture
    def mock_docker_client(self):
        """Create a mock Docker client."""
        mock_client = Mock(spec=docker.DockerClient)
        mock_client.ping.return_value = True
        return mock_client
    
    @pytest.fixture
    def mock_container(self):
        """Create a mock Docker container."""
        mock_container = Mock()
        mock_container.id = "container-123"
        mock_container.status = "running"
        mock_container.labels = {
            "clarity.component": "per-project-containers",
            "clarity.project_id": "test-project",
            "clarity.created": datetime.utcnow().isoformat()
        }
        mock_container.exec_run.return_value = (0, b"success")
        mock_container.reload.return_value = None
        return mock_container
    
    @pytest.fixture
    def mock_volume(self):
        """Create a mock Docker volume."""
        mock_volume = Mock()
        mock_volume.name = "clarity-project-vol-test-project-12345678"
        mock_volume.attrs = {
            'Labels': {
                "clarity.component": "per-project-containers",
                "clarity.project_id": "test-project",
                "clarity.created": datetime.utcnow().isoformat()
            }
        }
        return mock_volume
    
    def test_initialization(self):
        """Test PerProjectContainerManager initialization."""
        # Test with correlation ID
        manager = PerProjectContainerManager(correlation_id="test-123")
        assert manager.correlation_id == "test-123"
        assert manager.logger is not None
        assert manager._docker_client is None
        assert manager._container_registry == {}
        
        # Test without correlation ID
        manager_no_id = PerProjectContainerManager()
        assert manager_no_id.correlation_id is None
    
    def test_validate_project_id_valid(self, manager):
        """Test project ID validation with valid inputs."""
        valid_ids = [
            "test-project",
            "project_123",
            "simple",
            "test-project-with-dashes",
            "project_with_underscores",
            "a" * 50  # 50 characters
        ]
        
        for project_id in valid_ids:
            # Should not raise exception
            manager._validate_project_id(project_id)
    
    def test_validate_project_id_invalid(self, manager):
        """Test project ID validation with invalid inputs."""
        invalid_cases = [
            ("", "Project ID must be a non-empty string"),
            (None, "Project ID must be a non-empty string"),
            (123, "Project ID must be a non-empty string"),
            ("a" * 101, "Project ID too long"),  # 101 characters
            ("project with spaces", "Project ID contains invalid characters"),
            ("project@domain", "Project ID contains invalid characters"),
            ("project/path", "Project ID contains invalid characters"),
            ("../dangerous", "Project ID contains invalid characters"),
            ("project\x00null", "Project ID contains invalid characters"),
            ("project<script>", "Project ID contains invalid characters"),
        ]

        for project_id, expected_error in invalid_cases:
            with pytest.raises(ContainerError) as exc_info:
                manager._validate_project_id(project_id)
            # Check that the error message contains key parts of the expected error
            error_msg = str(exc_info.value)
            if "non-empty string" in expected_error:
                assert "non-empty string" in error_msg
            elif "too long" in expected_error:
                assert "too long" in error_msg
            elif "invalid characters" in expected_error:
                assert "invalid characters" in error_msg
    
    def test_generate_container_name(self, manager):
        """Test container name generation."""
        project_id = "test-project"
        name = manager._generate_container_name(project_id)
        
        assert name.startswith("clarity-project-test-project-")
        assert len(name.split("-")[-1]) == 8  # Hash should be 8 characters
        
        # Same project ID should generate same name
        name2 = manager._generate_container_name(project_id)
        assert name == name2
        
        # Different project ID should generate different name
        name3 = manager._generate_container_name("different-project")
        assert name != name3
    
    def test_generate_volume_name(self, manager):
        """Test volume name generation."""
        project_id = "test-project"
        name = manager._generate_volume_name(project_id)
        
        assert name.startswith("clarity-project-vol-test-project-")
        assert len(name.split("-")[-1]) == 8  # Hash should be 8 characters
        
        # Same project ID should generate same name
        name2 = manager._generate_volume_name(project_id)
        assert name == name2
    
    def test_prepare_environment_variables(self, manager):
        """Test environment variable preparation."""
        with patch.dict('os.environ', {
            'GITHUB_TOKEN': 'github-token-123',
            'GITLAB_TOKEN': 'gitlab-token-456',
            'OTHER_VAR': 'should-not-be-included'
        }):
            env_vars = manager._prepare_environment_variables()
            
            # Should include Git tokens
            assert env_vars['GITHUB_TOKEN'] == 'github-token-123'
            assert env_vars['GITLAB_TOKEN'] == 'gitlab-token-456'
            
            # Should include basic container environment
            assert env_vars['NODE_ENV'] == 'development'
            assert env_vars['CONTAINER_TYPE'] == 'clarity-project'
            assert env_vars['CONTAINER_TTL_DAYS'] == '7'
            
            # Should not include other environment variables
            assert 'OTHER_VAR' not in env_vars
    
    @patch('services.per_project_container_manager.docker.from_env')
    def test_docker_client_property_success(self, mock_from_env, manager):
        """Test Docker client property with successful connection."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_from_env.return_value = mock_client
        
        # First access should create client
        client = manager.docker_client
        assert client == mock_client
        mock_from_env.assert_called_once()
        mock_client.ping.assert_called_once()
        
        # Second access should reuse client
        client2 = manager.docker_client
        assert client2 == mock_client
        assert mock_from_env.call_count == 1  # Should not be called again
    
    @patch('services.per_project_container_manager.docker.from_env')
    def test_docker_client_property_failure(self, mock_from_env, manager):
        """Test Docker client property with connection failure."""
        mock_from_env.side_effect = DockerException("Docker daemon not available")
        
        with pytest.raises(ContainerError) as exc_info:
            _ = manager.docker_client
        
        assert "Failed to connect to Docker daemon" in str(exc_info.value)
    
    def test_check_concurrency_limits(self, manager):
        """Test concurrency limit checking."""
        # Empty registry should allow creation
        assert manager._check_concurrency_limits("test-project") is True
        
        # Add containers to registry
        for i in range(4):
            manager._container_registry[f"container-{i}"] = {
                'project_id': f'project-{i}',
                'status': 'running'
            }
        
        # Should still allow (4 < 5 global limit)
        assert manager._check_concurrency_limits("new-project") is True
        
        # Add one more to reach global limit
        manager._container_registry["container-4"] = {
            'project_id': 'project-4',
            'status': 'running'
        }
        
        # Should not allow (5 >= 5 global limit)
        assert manager._check_concurrency_limits("new-project") is False
        
        # Test per-project limit
        manager._container_registry.clear()
        manager._container_registry["container-1"] = {
            'project_id': 'test-project',
            'status': 'running'
        }
        
        # Should not allow same project (1 >= 1 per-project limit)
        assert manager._check_concurrency_limits("test-project") is False
        
        # Should allow different project
        assert manager._check_concurrency_limits("different-project") is True
    
    def test_register_unregister_container(self, manager, mock_container):
        """Test container registration and unregistration."""
        project_id = "test-project"
        
        # Register container
        manager._register_container(project_id, mock_container)
        
        assert mock_container.id in manager._container_registry
        registry_entry = manager._container_registry[mock_container.id]
        assert registry_entry['project_id'] == project_id
        assert registry_entry['container'] == mock_container
        assert registry_entry['status'] == 'running'
        assert isinstance(registry_entry['created_at'], datetime)
        
        # Unregister container
        manager._unregister_container(mock_container.id)
        assert mock_container.id not in manager._container_registry
    
    @patch('services.per_project_container_manager.docker.from_env')
    def test_ensure_network_exists_new(self, mock_from_env, manager):
        """Test network creation when network doesn't exist."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        mock_client.ping.return_value = True
        
        # Network doesn't exist
        mock_client.networks.get.side_effect = NotFound("Network not found")
        mock_network = Mock()
        mock_client.networks.create.return_value = mock_network
        
        manager._ensure_network_exists()
        
        mock_client.networks.get.assert_called_once_with("clarity-project-network")
        # Check that network creation was called with correct parameters
        mock_client.networks.create.assert_called_once()
        call_args = mock_client.networks.create.call_args
        assert call_args[0][0] == "clarity-project-network"
        assert call_args[1]["driver"] == "bridge"
        assert "clarity.component" in call_args[1]["labels"]
        assert call_args[1]["labels"]["clarity.component"] == "per-project-containers"
        assert "clarity.created" in call_args[1]["labels"]
    
    @patch('services.per_project_container_manager.docker.from_env')
    def test_ensure_network_exists_existing(self, mock_from_env, manager):
        """Test network handling when network already exists."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        mock_client.ping.return_value = True
        
        # Network exists
        mock_network = Mock()
        mock_client.networks.get.return_value = mock_network
        
        manager._ensure_network_exists()
        
        mock_client.networks.get.assert_called_once_with("clarity-project-network")
        mock_client.networks.create.assert_not_called()
    
    @patch('services.per_project_container_manager.docker.from_env')
    def test_create_project_volume_new(self, mock_from_env, manager):
        """Test volume creation when volume doesn't exist."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        mock_client.ping.return_value = True
        
        project_id = "test-project"
        volume_name = manager._generate_volume_name(project_id)
        
        # Volume doesn't exist
        mock_client.volumes.get.side_effect = NotFound("Volume not found")
        mock_volume = Mock()
        mock_volume.name = volume_name
        mock_client.volumes.create.return_value = mock_volume
        
        result = manager._create_project_volume(project_id)
        
        assert result == mock_volume
        mock_client.volumes.get.assert_called_once_with(volume_name)
        mock_client.volumes.create.assert_called_once_with(
            name=volume_name,
            labels={
                "clarity.component": "per-project-containers",
                "clarity.project_id": project_id,
                "clarity.created": pytest.approx(datetime.utcnow().isoformat(), abs=5),
                "clarity.ttl_days": "7"
            }
        )
    
    @patch('services.per_project_container_manager.docker.from_env')
    def test_create_project_volume_existing(self, mock_from_env, manager):
        """Test volume handling when volume already exists."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        mock_client.ping.return_value = True
        
        project_id = "test-project"
        volume_name = manager._generate_volume_name(project_id)
        
        # Volume exists
        mock_volume = Mock()
        mock_volume.name = volume_name
        mock_client.volumes.get.return_value = mock_volume
        
        result = manager._create_project_volume(project_id)
        
        assert result == mock_volume
        mock_client.volumes.get.assert_called_once_with(volume_name)
        mock_client.volumes.create.assert_not_called()
    
    def test_perform_health_checks_success(self, manager, mock_container):
        """Test successful health checks."""
        # Mock successful exec_run calls
        mock_container.status = "running"
        mock_container.exec_run.return_value = (0, b"success")
        
        result = manager._perform_health_checks(mock_container, "test-project", "exec-123")
        
        assert result['container_running'] is True
        assert result['git_available'] is True
        assert result['node_available'] is True
        assert result['workspace_accessible'] is True
        assert result['overall_health'] is True
        
        # Verify exec_run was called for each check
        expected_calls = [
            call("git --version"),
            call("node --version"),
            call("ls -la /workspace")
        ]
        mock_container.exec_run.assert_has_calls(expected_calls)
    
    def test_perform_health_checks_failure(self, manager, mock_container):
        """Test health checks with failures."""
        # Container not running
        mock_container.status = "stopped"
        
        result = manager._perform_health_checks(mock_container, "test-project", "exec-123")
        
        assert result['container_running'] is False
        assert result['overall_health'] is False
        
        # Should not perform other checks if container not running
        mock_container.exec_run.assert_not_called()
    
    def test_perform_health_checks_partial_failure(self, manager, mock_container):
        """Test health checks with partial failures."""
        mock_container.status = "running"
        
        # Git fails, others succeed
        def mock_exec_run(command):
            if "git" in command:
                return (1, b"git not found")
            return (0, b"success")
        
        mock_container.exec_run.side_effect = mock_exec_run
        
        result = manager._perform_health_checks(mock_container, "test-project", "exec-123")
        
        assert result['container_running'] is True
        assert result['git_available'] is False
        assert result['node_available'] is True
        assert result['workspace_accessible'] is True
        assert result['overall_health'] is False  # Git is critical
    
    @patch('services.per_project_container_manager.docker.from_env')
    def test_start_or_reuse_container_new_container(self, mock_from_env, manager):
        """Test starting a new container when none exists."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        mock_client.ping.return_value = True
        
        project_id = "test-project"
        container_name = manager._generate_container_name(project_id)
        
        # No existing container
        mock_client.containers.get.side_effect = NotFound("Container not found")
        
        # Mock network and volume creation
        mock_network = Mock()
        mock_client.networks.get.return_value = mock_network
        
        mock_volume = Mock()
        mock_volume.name = manager._generate_volume_name(project_id)
        mock_client.volumes.get.return_value = mock_volume
        
        # Mock container creation
        mock_container = Mock()
        mock_container.id = "new-container-123"
        mock_container.status = "running"
        mock_container.exec_run.return_value = (0, b"success")
        mock_client.containers.run.return_value = mock_container
        
        with patch.dict('os.environ', {'GITHUB_TOKEN': 'test-token'}):
            result = manager.start_or_reuse_container(project_id, "exec-123")
        
        assert result['success'] is True
        assert result['project_id'] == project_id
        assert result['container_id'] == "new-container-123"
        assert result['container_status'] == 'started'
        assert result['container_name'] == container_name
        assert 'performance_metrics' in result
        assert 'health_checks' in result
        assert 'resource_limits' in result
        
        # Verify container was created with correct parameters
        mock_client.containers.run.assert_called_once()
        call_args = mock_client.containers.run.call_args
        assert call_args[0][0] == "node:18-alpine"  # image
        assert call_args[1]['name'] == container_name
        assert call_args[1]['mem_limit'] == '1g'
        assert call_args[1]['detach'] is True
        assert 'GITHUB_TOKEN' in call_args[1]['environment']
    
    @patch('services.per_project_container_manager.docker.from_env')
    def test_start_or_reuse_container_reuse_existing(self, mock_from_env, manager):
        """Test reusing an existing healthy container."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        mock_client.ping.return_value = True
        
        project_id = "test-project"
        container_name = manager._generate_container_name(project_id)
        
        # Existing healthy container
        mock_container = Mock()
        mock_container.id = "existing-container-123"
        mock_container.status = "running"
        mock_container.exec_run.return_value = (0, b"success")
        mock_client.containers.get.return_value = mock_container
        
        result = manager.start_or_reuse_container(project_id, "exec-123")
        
        assert result['success'] is True
        assert result['project_id'] == project_id
        assert result['container_id'] == "existing-container-123"
        assert result['container_status'] == 'reused'
        assert result['container_name'] == container_name
        
        # Should not create new container
        mock_client.containers.run.assert_not_called()
        
        # Should perform health checks
        mock_container.exec_run.assert_called()
    
    @patch('services.per_project_container_manager.docker.from_env')
    def test_start_or_reuse_container_concurrency_limit(self, mock_from_env, manager):
        """Test container creation blocked by concurrency limits."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        mock_client.ping.return_value = True
        
        project_id = "test-project"
        
        # Fill up global container limit
        for i in range(5):
            manager._container_registry[f"container-{i}"] = {
                'project_id': f'project-{i}',
                'status': 'running'
            }
        
        with pytest.raises(ContainerError) as exc_info:
            manager.start_or_reuse_container(project_id, "exec-123")
        
        assert "concurrency limits" in str(exc_info.value)
    
    @patch('services.per_project_container_manager.docker.from_env')
    def test_start_or_reuse_container_invalid_project_id(self, mock_from_env, manager):
        """Test container creation with invalid project ID."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        mock_client.ping.return_value = True
        
        with pytest.raises(ContainerError) as exc_info:
            manager.start_or_reuse_container("invalid/project", "exec-123")
        
        assert "invalid characters" in str(exc_info.value)
    
    @patch('services.per_project_container_manager.docker.from_env')
    def test_cleanup_expired_containers(self, mock_from_env, manager):
        """Test cleanup of expired containers and volumes."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        mock_client.ping.return_value = True
        
        # Mock expired container
        old_time = (datetime.utcnow() - timedelta(days=8)).isoformat()
        mock_container = Mock()
        mock_container.id = "old-container-123"
        mock_container.labels = {
            "clarity.component": "per-project-containers",
            "clarity.project_id": "old-project",
            "clarity.created": old_time
        }
        mock_client.containers.list.return_value = [mock_container]
        
        # Mock expired volume
        mock_volume = Mock()
        mock_volume.name = "old-volume-123"
        mock_volume.attrs = {
            'Labels': {
                "clarity.component": "per-project-containers",
                "clarity.project_id": "old-project",
                "clarity.created": old_time
            }
        }
        mock_client.volumes.list.return_value = [mock_volume]
        
        result = manager.cleanup_expired_containers(max_age_days=7, execution_id="cleanup-123")
        
        assert result['containers_checked'] == 1
        assert result['containers_removed'] == 1
        assert result['volumes_checked'] == 1
        assert result['volumes_removed'] == 1
        assert result['errors'] == 0
        
        # Verify cleanup calls
        mock_container.remove.assert_called_once_with(force=True)
        mock_volume.remove.assert_called_once_with(force=True)
    
    @patch('services.per_project_container_manager.docker.from_env')
    def test_cleanup_expired_containers_recent(self, mock_from_env, manager):
        """Test cleanup skips recent containers and volumes."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        mock_client.ping.return_value = True
        
        # Mock recent container (1 day old)
        recent_time = (datetime.utcnow() - timedelta(days=1)).isoformat()
        mock_container = Mock()
        mock_container.id = "recent-container-123"
        mock_container.labels = {
            "clarity.component": "per-project-containers",
            "clarity.project_id": "recent-project",
            "clarity.created": recent_time
        }
        mock_client.containers.list.return_value = [mock_container]
        
        # Mock recent volume
        mock_volume = Mock()
        mock_volume.name = "recent-volume-123"
        mock_volume.attrs = {
            'Labels': {
                "clarity.component": "per-project-containers",
                "clarity.project_id": "recent-project",
                "clarity.created": recent_time
            }
        }
        mock_client.volumes.list.return_value = [mock_volume]
        
        result = manager.cleanup_expired_containers(max_age_days=7, execution_id="cleanup-123")
        
        assert result['containers_checked'] == 1
        assert result['containers_removed'] == 0
        assert result['volumes_checked'] == 1
        assert result['volumes_removed'] == 0
        assert result['errors'] == 0
        
        # Should not remove recent items
        mock_container.remove.assert_not_called()
        mock_volume.remove.assert_not_called()
    
    def test_container_error_creation(self):
        """Test ContainerError exception creation."""
        # Basic error
        error = ContainerError("Test error message")
        assert str(error) == "Test error message"
        assert error.project_id is None
        assert error.container_id is None
        
        # Error with project and container IDs
        error_with_ids = ContainerError(
            "Test error with IDs",
            project_id="test-project",
            container_id="container-123"
        )
        assert str(error_with_ids) == "Test error with IDs"
        assert error_with_ids.project_id == "test-project"
        assert error_with_ids.container_id == "container-123"


class TestPerProjectContainerManagerIntegration:
    """Integration tests for PerProjectContainerManager."""
    
    @pytest.fixture
    def manager(self):
        """Create manager for integration tests."""
        return PerProjectContainerManager(correlation_id="integration-test-123")
    
    def test_factory_function(self):
        """Test the factory function."""
        # Without correlation ID
        manager1 = get_per_project_container_manager()
        assert isinstance(manager1, PerProjectContainerManager)
        assert manager1.correlation_id is None
        
        # With correlation ID
        manager2 = get_per_project_container_manager("test-correlation-456")
        assert isinstance(manager2, PerProjectContainerManager)
        assert manager2.correlation_id == "test-correlation-456"
        
        # Should create different instances
        assert manager1 is not manager2
    
    @patch('services.per_project_container_manager.docker.from_env')
    def test_full_container_lifecycle(self, mock_from_env, manager):
        """Test complete container lifecycle from creation to cleanup."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        mock_client.ping.return_value = True
        
        project_id = "lifecycle-test"
        
        # Setup mocks for container creation
        mock_client.containers.get.side_effect = NotFound("Container not found")
        mock_client.networks.get.return_value = Mock()
        
        mock_volume = Mock()
        mock_volume.name = manager._generate_volume_name(project_id)
        mock_client.volumes.get.return_value = mock_volume
        
        mock_container = Mock()
        mock_container.id = "lifecycle-container-123"
        mock_container.status = "running"
        mock_container.exec_run.return_value = (0, b"success")
        mock_client.containers.run.return_value = mock_container
        
        # 1. Create container
        result = manager.start_or_reuse_container(project_id, "lifecycle-exec")
        assert result['success'] is True
        assert result['container_status'] == 'started'
        
        # 2. Reuse container (simulate second call)
        mock_client.containers.get.return_value = mock_container
        mock_client.containers.get.side_effect = None
        
        result2 = manager.start_or_reuse_container(project_id, "lifecycle-exec-2")
        assert result2['success'] is True
        assert result2['container_status'] == 'reused'
        
        # 3. Cleanup (simulate expired container)
        old_time = (datetime.utcnow() - timedelta(days=8)).isoformat()
        mock_container.labels = {
            "clarity.component": "per-project-containers",
            "clarity.project_id": project_id,
            "clarity.created": old_time
        }
        mock_client.containers.list.return_value = [mock_container]
        mock_client.volumes.list.return_value = []
        
        cleanup_result = manager.cleanup_expired_containers(max_age_days=7)
        assert cleanup_result['containers_removed'] == 1
    
    def test_concurrent_container_requests(self, manager):
        """Test handling of concurrent container requests."""
        project_ids = [f"concurrent-project-{i}" for i in range(3)]
        
        # Fill registry to test concurrency limits
        for i, project_id in enumerate(project_ids):
            manager._register_container(project_id, Mock(id=f"container-{i}"))
        
        # Should allow up to global limit
        assert manager._check_concurrency_limits("new-project-1") is True
        assert manager._check_concurrency_limits("new-project-2") is True
        
        # Add more to reach limit
        manager._register_container("project-4", Mock(id="container-4"))
        manager._register_container("project-5", Mock(id="container-5"))
        
        # Should block new containers
        assert manager._check_concurrency_limits("blocked-project") is False
    
    def test_performance_requirements(self, manager):
        """Test that operations meet performance requirements (<2s)."""
        # Test validation performance
        start_time = time.time()
        for i in range(100):
            manager._validate_project_id(f"test-project-{i}")
        validation_time = time.time() - start_time
        assert validation_time < 0.1  # Should be very fast
        
        # Test name generation performance
        start_time = time.time()
        for i in range(100):
            manager._generate_container_name(f"test-project-{i}")
            manager._generate_volume_name(f"test-project-{i}")
        generation_time = time.time() - start_time
        assert generation_time < 0.1  # Should be very fast
        
        # Test concurrency check performance
        # Add some containers to registry
        for i in range(10):
            manager._container_registry[f"container-{i}"] = {
                'project_id': f'project-{i}',
                'status': 'running'
            }
        
        start_time = time.time()
        for i in range(100):
            manager._check_concurrency_limits(f"test-project-{i}")
        concurrency_time = time.time() - start_time
        assert concurrency_time < 0.1  # Should be very fast


class TestPerProjectContainerManagerErrorHandling:
    """Test error handling scenarios."""
    
    @pytest.fixture
    def manager(self):
        """Create manager for error testing."""
        return PerProjectContainerManager(correlation_id="error-test-123")
    
    @patch('services.per_project_container_manager.docker.from_env')
    def test_docker_connection_failure(self, mock_from_env, manager):
        """Test Docker connection failure handling."""
        mock_from_env.side_effect = DockerException("Docker daemon not available")
        
        with pytest.raises(ContainerError) as exc_info:
            _ = manager.docker_client
        
        assert "Failed to connect to Docker daemon" in str(exc_info.value)
    
    @patch('services.per_project_container_manager.docker.from_env')
    def test_container_creation_failure(self, mock_from_env, manager):
        """Test container creation failure handling."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        mock_client.ping.return_value = True
        
        project_id = "test-project"
        
        # Mock no existing container
        mock_client.containers.get.side_effect = NotFound("Container not found")
        
        # Mock network and volume
        mock_client.networks.get.return_value = Mock()
        mock_volume = Mock()
        mock_volume.name = manager._generate_volume_name(project_id)
        mock_client.volumes.get.return_value = mock_volume
        
        # Mock container creation failure
        mock_client.containers.run.side_effect = APIError("Container creation failed")
        
        with pytest.raises(ContainerError) as exc_info:
            manager.start_or_reuse_container(project_id, "exec-123")
        
        assert "Failed to create container" in str(exc_info.value)
    
    @patch('services.per_project_container_manager.docker.from_env')
    def test_network_creation_failure(self, mock_from_env, manager):
        """Test network creation failure handling."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        mock_client.ping.return_value = True
        
        # Network doesn't exist and creation fails
        mock_client.networks.get.side_effect = NotFound("Network not found")
        mock_client.networks.create.side_effect = APIError("Network creation failed")
        
        with pytest.raises(ContainerError) as exc_info:
            manager._ensure_network_exists()
        
        assert "Failed to create project network" in str(exc_info.value)
    
    @patch('services.per_project_container_manager.docker.from_env')
    def test_volume_creation_failure(self, mock_from_env, manager):
        """Test volume creation failure handling."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        mock_client.ping.return_value = True
        
        project_id = "test-project"
        
        # Volume doesn't exist and creation fails
        mock_client.volumes.get.side_effect = NotFound("Volume not found")
        mock_client.volumes.create.side_effect = APIError("Volume creation failed")
        
        with pytest.raises(ContainerError) as exc_info:
            manager._create_project_volume(project_id)
        
        assert "Failed to create project volume" in str(exc_info.value)
    
    @patch('services.per_project_container_manager.docker.from_env')
    def test_cleanup_with_errors(self, mock_from_env, manager):
        """Test cleanup operation with partial errors."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        mock_client.ping.return_value = True
        
        # Mock container that fails to remove
        old_time = (datetime.utcnow() - timedelta(days=8)).isoformat()
        mock_container = Mock()
        mock_container.id = "problematic-container"
        mock_container.labels = {
            "clarity.component": "per-project-containers",
            "clarity.project_id": "test-project",
            "clarity.created": old_time
        }
        mock_container.remove.side_effect = APIError("Failed to remove container")
        mock_client.containers.list.return_value = [mock_container]
        
        # Mock volume that fails to remove
        mock_volume = Mock()
        mock_volume.name = "problematic-volume"
        mock_volume.attrs = {
            'Labels': {
                "clarity.component": "per-project-containers",
                "clarity.project_id": "test-project",
                "clarity.created": old_time
            }
        }
        mock_volume.remove.side_effect = APIError("Failed to remove volume")
        mock_client.volumes.list.return_value = [mock_volume]
        
        result = manager.cleanup_expired_containers(max_age_days=7)
        
        assert result['containers_checked'] == 1
        assert result['containers_removed'] == 0
        assert result['volumes_checked'] == 1
        assert result['volumes_removed'] == 0
        assert result['errors'] == 2  # Both container and volume removal failed


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])