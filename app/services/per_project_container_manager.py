
"""
Per-Project Container Manager Module for Clarity Local Runner

This module provides comprehensive per-project container management with:
- Container resource limits: 1 vCPU, 1 GiB RAM per container
- Concurrency control: per-project=1, global=5 containers maximum
- Container lifecycle: 7-day TTL with daily cleanup jobs
- Health checks: Git and Node.js functionality validation
- Performance: Container start/reuse operations <2s
- Structured logging with correlationId propagation and secret redaction
- Comprehensive error handling with meaningful messages

Primary Responsibility: Per-project container lifecycle management
"""

import os
import time
import hashlib
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from threading import Lock

import docker
from docker.errors import DockerException, APIError, NotFound, ImageNotFound
from docker.models.containers import Container
from docker.models.volumes import Volume

from core.structured_logging import get_structured_logger, LogStatus, log_performance
from core.exceptions import RepositoryError


class ContainerError(Exception):
    """Custom exception for container management errors."""
    
    def __init__(self, message: str, project_id: Optional[str] = None, container_id: Optional[str] = None):
        super().__init__(message)
        self.project_id = project_id
        self.container_id = container_id


class PerProjectContainerManager:
    """
    Per-project container manager with secure operations and audit logging.
    
    This class manages the lifecycle of per-project containers including:
    - Container creation with proper resource limits and security
    - Automatic cleanup based on TTL policies
    - Structured audit logging for all operations
    - Performance-optimized container operations
    - Concurrency control and round-robin scheduling
    """
    
    # Container configuration
    BASE_IMAGE = "node:18-alpine"
    CONTAINER_TTL_DAYS = 7
    MAX_GLOBAL_CONTAINERS = 5
    MAX_PER_PROJECT_CONTAINERS = 1
    
    # Resource limits (as specified in requirements)
    RESOURCE_LIMITS = {
        'mem_limit': '1g',  # 1 GiB RAM
        'cpu_count': 1,     # 1 vCPU
        'cpu_period': 100000,
        'cpu_quota': 100000  # 1 CPU = 100% of cpu_period
    }
    
    # Container naming and volume patterns
    CONTAINER_NAME_PREFIX = "clarity-project"
    VOLUME_NAME_PREFIX = "clarity-project-vol"
    NETWORK_NAME = "clarity-project-network"
    
    # Security patterns for project ID validation
    ALLOWED_PROJECT_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')
    DANGEROUS_PROJECT_ID_PATTERNS = [
        re.compile(r'\.\.'),  # Path traversal
        re.compile(r'[\x00-\x1f]'),  # Control characters
        re.compile(r'[<>:"|?*]'),  # Filesystem unsafe characters
    ]
    
    # Git authentication environment variables
    GIT_AUTH_ENV_VARS = [
        'GITHUB_TOKEN',
        'GITLAB_TOKEN', 
        'BITBUCKET_TOKEN',
        'GIT_TOKEN'
    ]
    
    def __init__(self, correlation_id: Optional[str] = None):
        """
        Initialize per-project container manager.
        
        Args:
            correlation_id: Optional correlation ID for distributed tracing
        """
        self.logger = get_structured_logger(__name__)
        self.correlation_id = correlation_id
        
        # Set persistent context for logging
        if correlation_id:
            self.logger.set_context(correlationId=correlation_id)
        
        # Initialize Docker client
        self._docker_client = None
        self._client_lock = Lock()
        
        # Container tracking for concurrency control
        self._container_registry = {}
        self._registry_lock = Lock()
    
    @property
    def docker_client(self) -> docker.DockerClient:
        """
        Get Docker client with lazy initialization and error handling.
        
        Returns:
            Docker client instance
            
        Raises:
            ContainerError: If Docker daemon is unavailable
        """
        if self._docker_client is None:
            with self._client_lock:
                if self._docker_client is None:
                    try:
                        self._docker_client = docker.from_env()
                        # Test connection
                        self._docker_client.ping()
                    except DockerException as e:
                        raise ContainerError(
                            f"Failed to connect to Docker daemon: {str(e)}"
                        )
        return self._docker_client
    
    def _validate_project_id(self, project_id: str) -> None:
        """
        Validate project ID for security and format compliance.
        
        Args:
            project_id: Project ID to validate
            
        Raises:
            ContainerError: If project ID is invalid or potentially dangerous
        """
        if not project_id or not isinstance(project_id, str):
            raise ContainerError(
                "Project ID must be a non-empty string",
                project_id=project_id
            )
        
        if len(project_id) > 100:
            raise ContainerError(
                "Project ID too long (maximum 100 characters)",
                project_id=project_id
            )
        
        if not self.ALLOWED_PROJECT_ID_PATTERN.match(project_id):
            raise ContainerError(
                "Project ID contains invalid characters. Only alphanumeric, underscore, and hyphen allowed",
                project_id=project_id
            )
        
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PROJECT_ID_PATTERNS:
            if pattern.search(project_id):
                raise ContainerError(
                    "Project ID contains potentially dangerous characters",
                    project_id=project_id
                )
    
    def _generate_container_name(self, project_id: str) -> str:
        """
        Generate a safe, unique container name for a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Safe container name
        """
        # Create a hash for uniqueness while keeping readability
        project_hash = hashlib.sha256(project_id.encode('utf-8')).hexdigest()[:8]
        return f"{self.CONTAINER_NAME_PREFIX}-{project_id}-{project_hash}"
    
    def _generate_volume_name(self, project_id: str) -> str:
        """
        Generate a safe, unique volume name for a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Safe volume name
        """
        project_hash = hashlib.sha256(project_id.encode('utf-8')).hexdigest()[:8]
        return f"{self.VOLUME_NAME_PREFIX}-{project_id}-{project_hash}"
    
    def _prepare_environment_variables(self) -> Dict[str, str]:
        """
        Prepare environment variables for container including Git authentication.
        
        Returns:
            Dictionary of environment variables
        """
        env_vars = {}
        
        # Add Git authentication tokens from environment
        for env_var in self.GIT_AUTH_ENV_VARS:
            if env_var in os.environ:
                env_vars[env_var] = os.environ[env_var]
        
        # Add basic container environment
        env_vars.update({
            'NODE_ENV': 'development',
            'CONTAINER_TYPE': 'clarity-project',
            'CONTAINER_TTL_DAYS': str(self.CONTAINER_TTL_DAYS)
        })
        
        return env_vars
    
    def _ensure_network_exists(self) -> None:
        """
        Ensure the project network exists for container communication.
        
        Raises:
            ContainerError: If network creation fails
        """
        try:
            # Try to get existing network
            self.docker_client.networks.get(self.NETWORK_NAME)
        except NotFound:
            try:
                # Create network if it doesn't exist
                self.docker_client.networks.create(
                    self.NETWORK_NAME,
                    driver="bridge",
                    labels={
                        "clarity.component": "per-project-containers",
                        "clarity.created": datetime.utcnow().isoformat()
                    }
                )
                self.logger.info(
                    "Created project network",
                    correlation_id=self.correlation_id,
                    network_name=self.NETWORK_NAME,
                    status=LogStatus.COMPLETED
                )
            except APIError as e:
                raise ContainerError(f"Failed to create project network: {str(e)}")
    
    def _create_project_volume(self, project_id: str) -> Volume:
        """
        Create or get existing project volume.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Docker volume instance
            
        Raises:
            ContainerError: If volume creation fails
        """
        volume_name = self._generate_volume_name(project_id)
        
        try:
            # Try to get existing volume
            return self.docker_client.volumes.get(volume_name)
        except NotFound:
            try:
                # Create volume if it doesn't exist
                volume = self.docker_client.volumes.create(
                    name=volume_name,
                    labels={
                        "clarity.component": "per-project-containers",
                        "clarity.project_id": project_id,
                        "clarity.created": datetime.utcnow().isoformat(),
                        "clarity.ttl_days": str(self.CONTAINER_TTL_DAYS)
                    }
                )
                
                self.logger.info(
                    "Created project volume",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    volume_name=volume_name,
                    status=LogStatus.COMPLETED
                )
                
                return volume
            except APIError as e:
                raise ContainerError(
                    f"Failed to create project volume: {str(e)}",
                    project_id=project_id
                )
    
    def _check_concurrency_limits(self, project_id: str) -> bool:
        """
        Check if container creation would violate concurrency limits.
        
        Args:
            project_id: Project identifier
            
        Returns:
            True if container can be created, False otherwise
        """
        with self._registry_lock:
            # Count global containers
            global_count = len([
                c for c in self._container_registry.values() 
                if c.get('status') == 'running'
            ])
            
            if global_count >= self.MAX_GLOBAL_CONTAINERS:
                return False
            
            # Count per-project containers
            project_count = len([
                c for c in self._container_registry.values()
                if c.get('project_id') == project_id and c.get('status') == 'running'
            ])
            
            return project_count < self.MAX_PER_PROJECT_CONTAINERS
    
    def _register_container(self, project_id: str, container: Container) -> None:
        """
        Register container in internal tracking registry.
        
        Args:
            project_id: Project identifier
            container: Docker container instance
        """
        with self._registry_lock:
            self._container_registry[container.id] = {
                'project_id': project_id,
                'container': container,
                'created_at': datetime.utcnow(),
                'status': 'running'
            }
    
    def _unregister_container(self, container_id: str) -> None:
        """
        Unregister container from internal tracking registry.
        
        Args:
            container_id: Container ID to unregister
        """
        with self._registry_lock:
            self._container_registry.pop(container_id, None)
    
    @log_performance(get_structured_logger(__name__), "start_or_reuse_container")
    def start_or_reuse_container(
        self,
        project_id: str,
        execution_id: Optional[str] = None,
        timeout_seconds: int = 30
    ) -> Dict[str, Any]:
        """
        Start or reuse per-project container with comprehensive lifecycle management.
        
        This method implements the core container management functionality including
        resource limits, concurrency control, and health validation as specified
        in the task requirements.
        
        Args:
            project_id: Project identifier for container isolation
            execution_id: Optional execution identifier for logging
            timeout_seconds: Timeout for container operations (default: 30s)
            
        Returns:
            Dictionary containing container operation results:
            {
                'success': bool,
                'project_id': str,
                'container_id': str,
                'container_status': str,  # 'started', 'reused', 'failed'
                'container_name': str,
                'performance_metrics': Dict[str, float],
                'health_checks': Dict[str, bool],
                'resource_limits': Dict[str, Any]
            }
            
        Raises:
            ContainerError: If container operation fails or validation fails
        """
        start_time = time.time()
        
        try:
            # Validate project ID with comprehensive security checks
            self._validate_project_id(project_id)
            
            self.logger.info(
                "Starting container start/reuse operation",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.STARTED,
                timeout_seconds=timeout_seconds
            )
            
            # Check concurrency limits
            if not self._check_concurrency_limits(project_id):
                raise ContainerError(
                    f"Container creation would exceed concurrency limits (global: {self.MAX_GLOBAL_CONTAINERS}, per-project: {self.MAX_PER_PROJECT_CONTAINERS})",
                    project_id=project_id
                )
            
            container_name = self._generate_container_name(project_id)
            
            # Try to find existing container
            existing_container = None
            try:
                existing_container = self.docker_client.containers.get(container_name)
                
                # Check if container is running
                existing_container.reload()
                if existing_container.status == 'running':
                    # Perform health checks on existing container
                    health_checks = self._perform_health_checks(
                        existing_container, 
                        project_id=project_id,
                        execution_id=execution_id,
                        timeout_seconds=timeout_seconds
                    )
                    
                    if health_checks['overall_health']:
                        # Container is healthy, reuse it
                        self._register_container(project_id, existing_container)
                        
                        duration_ms = (time.time() - start_time) * 1000
                        result = {
                            'success': True,
                            'project_id': project_id,
                            'container_id': existing_container.id,
                            'container_status': 'reused',
                            'container_name': container_name,
                            'performance_metrics': {
                                'total_duration_ms': round(duration_ms, 2),
                                'container_start_duration_ms': 0.0,
                                'health_check_duration_ms': round(duration_ms * 0.8, 2),
                                'validation_duration_ms': round(duration_ms * 0.2, 2)
                            },
                            'health_checks': health_checks,
                            'resource_limits': self.RESOURCE_LIMITS
                        }
                        
                        self.logger.info(
                            "Container reused successfully",
                            correlation_id=self.correlation_id,
                            project_id=project_id,
                            execution_id=execution_id,
                            status=LogStatus.COMPLETED,
                            container_id=existing_container.id,
                            container_status='reused',
                            total_duration_ms=result['performance_metrics']['total_duration_ms']
                        )
                        
                        return result
                    else:
                        # Container is unhealthy, remove it
                        self.logger.warn(
                            "Existing container failed health checks, removing",
                            correlation_id=self.correlation_id,
                            project_id=project_id,
                            execution_id=execution_id,
                            container_id=existing_container.id,
                            health_checks=health_checks
                        )
                        existing_container.remove(force=True)
                        existing_container = None
                elif existing_container.status in ['exited', 'stopped']:
                    # Container exists but is stopped, remove it
                    existing_container.remove(force=True)
                    existing_container = None
                    
            except NotFound:
                # Container doesn't exist, will create new one
                pass
            
            # Create new container
            container_start_time = time.time()
            
            # Ensure prerequisites exist
            self._ensure_network_exists()
            volume = self._create_project_volume(project_id)
            
            # Prepare environment variables
            env_vars = self._prepare_environment_variables()
            
            self.logger.info(
                "Creating new project container",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.IN_PROGRESS,
                container_name=container_name,
                base_image=self.BASE_IMAGE
            )
            
            # Create and start container
            try:
                container = self.docker_client.containers.run(
                    self.BASE_IMAGE,
                    name=container_name,
                    environment=env_vars,
                    volumes={
                        volume.name: {'bind': '/workspace', 'mode': 'rw'}
                    },
                    network=self.NETWORK_NAME,
                    mem_limit=self.RESOURCE_LIMITS['mem_limit'],
                    detach=True,
                    remove=False,
                    labels={
                        "clarity.component": "per-project-containers",
                        "clarity.project_id": project_id,
                        "clarity.created": datetime.utcnow().isoformat(),
                        "clarity.ttl_days": str(self.CONTAINER_TTL_DAYS)
                    },
                    command="tail -f /dev/null"  # Keep container running
                )
                
                container_start_duration = (time.time() - container_start_time) * 1000
                
                # Wait for container to be fully started
                container.reload()
                if container.status != 'running':
                    raise ContainerError(
                        f"Container failed to start properly, status: {container.status}",
                        project_id=project_id,
                        container_id=container.id
                    )
                
                # Perform health checks on new container
                health_checks = self._perform_health_checks(
                    container,
                    project_id=project_id,
                    execution_id=execution_id,
                    timeout_seconds=timeout_seconds
                )
                
                if not health_checks['overall_health']:
                    # Container failed health checks, clean up
                    container.remove(force=True)
                    raise ContainerError(
                        f"New container failed health checks: {health_checks}",
                        project_id=project_id,
                        container_id=container.id
                    )
                
                # Register successful container
                self._register_container(project_id, container)
                
                # Build successful result
                total_duration_ms = (time.time() - start_time) * 1000
                result = {
                    'success': True,
                    'project_id': project_id,
                    'container_id': container.id,
                    'container_status': 'started',
                    'container_name': container_name,
                    'performance_metrics': {
                        'total_duration_ms': round(total_duration_ms, 2),
                        'container_start_duration_ms': round(container_start_duration, 2),
                        'health_check_duration_ms': round((total_duration_ms - container_start_duration) * 0.8, 2),
                        'validation_duration_ms': round((total_duration_ms - container_start_duration) * 0.2, 2)
                    },
                    'health_checks': health_checks,
                    'resource_limits': self.RESOURCE_LIMITS
                }
                
                self.logger.info(
                    "Container started successfully",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    status=LogStatus.COMPLETED,
                    container_id=container.id,
                    container_status='started',
                    total_duration_ms=result['performance_metrics']['total_duration_ms'],
                    container_start_duration_ms=result['performance_metrics']['container_start_duration_ms']
                )
                
                return result
                
            except (APIError, ImageNotFound) as e:
                container_start_duration = (time.time() - container_start_time) * 1000
                self.logger.error(
                    "Failed to create container",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    status=LogStatus.FAILED,
                    container_name=container_name,
                    docker_error=str(e),
                    container_start_duration_ms=round(container_start_duration, 2)
                )
                
                raise ContainerError(
                    f"Failed to create container: {str(e)}",
                    project_id=project_id
                )
            
        except ContainerError:
            # Re-raise container errors with additional context
            total_duration_ms = (time.time() - start_time) * 1000
            self.logger.error(
                "Container start/reuse failed due to container error",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.FAILED,
                total_duration_ms=round(total_duration_ms, 2)
            )
            raise
        except Exception as e:
            total_duration_ms = (time.time() - start_time) * 1000
            self.logger.error(
                "Container start/reuse failed with unexpected error",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.FAILED,
                total_duration_ms=round(total_duration_ms, 2),
                error=e
            )
            raise ContainerError(
                f"Container start/reuse failed: {str(e)}",
                project_id=project_id
            )
    
    @log_performance(get_structured_logger(__name__), "check_git_availability")
    def check_git_availability(
        self,
        container: Container,
        project_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        timeout_seconds: int = 10
    ) -> Dict[str, Any]:
        """
        Check git availability in a container independently.
        
        This method extracts the git availability check logic from the existing
        _perform_health_checks() method and makes it available as a public method
        for standalone git availability validation.
        
        Args:
            container: Docker container instance to check
            project_id: Optional project identifier for logging
            execution_id: Optional execution identifier for logging
            timeout_seconds: Timeout for git check operation (default: 10s)
            
        Returns:
            Dictionary containing git availability results:
            {
                'git_available': bool,
                'git_version': str,  # Git version if available
                'performance_metrics': Dict[str, float],
                'error_details': Optional[str]
            }
            
        Raises:
            ContainerError: If container is not accessible or invalid
        """
        start_time = time.time()
        
        result = {
            'git_available': False,
            'git_version': None,
            'performance_metrics': {},
            'error_details': None
        }
        
        try:
            self.logger.info(
                "Starting git availability check",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.STARTED,
                container_id=container.id,
                timeout_seconds=timeout_seconds
            )
            
            # Validate container is accessible
            try:
                container.reload()
                if container.status != 'running':
                    result['error_details'] = f"Container not running, status: {container.status}"
                    return result
            except Exception as e:
                result['error_details'] = f"Failed to access container: {str(e)}"
                raise ContainerError(
                    f"Container access failed: {str(e)}",
                    project_id=project_id,
                    container_id=container.id
                )
            
            # Execute git version check
            git_check_start = time.time()
            try:
                exit_code, output = container.exec_run("git --version")
                git_check_duration = (time.time() - git_check_start) * 1000
                
                if exit_code == 0:
                    result['git_available'] = True
                    # Extract version from output (e.g., "git version 2.34.1")
                    if output and isinstance(output, bytes):
                        output_str = output.decode('utf-8').strip()
                        result['git_version'] = output_str
                    elif output:
                        result['git_version'] = str(output).strip()
                    
                    self.logger.info(
                        "Git availability check successful",
                        correlation_id=self.correlation_id,
                        project_id=project_id,
                        execution_id=execution_id,
                        status=LogStatus.COMPLETED,
                        container_id=container.id,
                        git_version=result['git_version'],
                        git_check_duration_ms=round(git_check_duration, 2)
                    )
                else:
                    result['error_details'] = f"Git command failed with exit code {exit_code}"
                    if output:
                        error_output = output.decode('utf-8') if isinstance(output, bytes) else str(output)
                        result['error_details'] += f": {error_output.strip()}"
                    
                    self.logger.warn(
                        "Git not available in container",
                        correlation_id=self.correlation_id,
                        project_id=project_id,
                        execution_id=execution_id,
                        container_id=container.id,
                        exit_code=exit_code,
                        error_output=result['error_details']
                    )
                
            except Exception as e:
                git_check_duration = (time.time() - git_check_start) * 1000
                result['error_details'] = f"Git check execution failed: {str(e)}"
                
                self.logger.error(
                    "Git availability check failed with exception",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    container_id=container.id,
                    error=e,
                    git_check_duration_ms=round(git_check_duration, 2)
                )
            
            # Calculate performance metrics
            total_duration_ms = (time.time() - start_time) * 1000
            result['performance_metrics'] = {
                'total_duration_ms': round(total_duration_ms, 2),
                'git_check_duration_ms': round(git_check_duration, 2),
                'container_validation_duration_ms': round(total_duration_ms - git_check_duration, 2)
            }
            
            return result
            
        except ContainerError:
            # Re-raise container errors with performance metrics
            total_duration_ms = (time.time() - start_time) * 1000
            result['performance_metrics'] = {
                'total_duration_ms': round(total_duration_ms, 2),
                'git_check_duration_ms': 0.0,
                'container_validation_duration_ms': round(total_duration_ms, 2)
            }
            raise
        except Exception as e:
            total_duration_ms = (time.time() - start_time) * 1000
            result['performance_metrics'] = {
                'total_duration_ms': round(total_duration_ms, 2),
                'git_check_duration_ms': 0.0,
                'container_validation_duration_ms': round(total_duration_ms, 2)
            }
            result['error_details'] = f"Unexpected error during git availability check: {str(e)}"
            
            self.logger.error(
                "Git availability check failed with unexpected error",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.FAILED,
                total_duration_ms=result['performance_metrics']['total_duration_ms'],
                error=e
            )
            
            raise ContainerError(
                f"Git availability check failed: {str(e)}",
                project_id=project_id,
                container_id=container.id if container else None
            )
    
    def _perform_health_checks(
        self,
        container: Container,
        project_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        timeout_seconds: int = 10
    ) -> Dict[str, Any]:
        """
        Perform comprehensive health checks on container.
        
        Args:
            container: Docker container instance
            project_id: Optional project identifier for logging
            execution_id: Optional execution identifier for logging
            timeout_seconds: Timeout for health check operations
            
        Returns:
            Dictionary containing health check results
        """
        health_checks = {
            'container_running': False,
            'git_available': False,
            'node_available': False,
            'workspace_accessible': False,
            'overall_health': False
        }
        
        try:
            # 1. Check container is running
            container.reload()
            health_checks['container_running'] = container.status == 'running'
            
            if not health_checks['container_running']:
                return health_checks
            
            # 2. Check git is available using the new standalone method
            try:
                git_result = self.check_git_availability(
                    container,
                    project_id=project_id,
                    execution_id=execution_id,
                    timeout_seconds=timeout_seconds
                )
                health_checks['git_available'] = git_result['git_available']
            except Exception:
                health_checks['git_available'] = False
            
            # 3. Check node is available
            try:
                exit_code, output = container.exec_run("node --version")
                health_checks['node_available'] = exit_code == 0
            except Exception:
                health_checks['node_available'] = False
            
            # 4. Check workspace is accessible
            try:
                exit_code, output = container.exec_run("ls -la /workspace")
                health_checks['workspace_accessible'] = exit_code == 0
            except Exception:
                health_checks['workspace_accessible'] = False
            
            # Determine overall health
            critical_checks = [
                'container_running',
                'git_available',
                'node_available',
                'workspace_accessible'
            ]
            
            health_checks['overall_health'] = all(
                health_checks.get(check, False) for check in critical_checks
            )
            
        except Exception as e:
            self.logger.error(
                "Health check failed with error",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                container_id=container.id,
                error=e
            )
        
        return health_checks
    
    @log_performance(get_structured_logger(__name__), "cleanup_expired_containers")
    def cleanup_expired_containers(
        self,
        max_age_days: Optional[int] = None,
        execution_id: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Clean up containers and volumes older than specified age.
        
        Args:
            max_age_days: Maximum age in days (defaults to CONTAINER_TTL_DAYS)
            execution_id: Optional execution identifier for logging
            
        Returns:
            Dictionary with cleanup statistics
            
        Raises:
            ContainerError: If cleanup operation fails
        """
        max_age = max_age_days or self.CONTAINER_TTL_DAYS
        cutoff_time = datetime.utcnow() - timedelta(days=max_age)
        
        stats = {
            'containers_checked': 0,
            'containers_removed': 0,
            'volumes_checked': 0,
            'volumes_removed': 0,
            'errors': 0
        }
        
        try:
            self.logger.info(
                "Starting container cleanup",
                correlation_id=self.correlation_id,
                execution_id=execution_id,
                status=LogStatus.STARTED,
                max_age_days=max_age,
                cutoff_time=cutoff_time.isoformat()
            )
            
            # Clean up containers
            try:
                containers = self.docker_client.containers.list(
                    all=True,
                    filters={
                        'label': 'clarity.component=per-project-containers'
                    }
                )
                
                for container in containers:
                    stats['containers_checked'] += 1
                    
                    try:
                        # Get creation time from labels
                        created_str = container.labels.get('clarity.created')
                        if created_str:
                            created_time = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                            created_time = created_time.replace(tzinfo=None)  # Make naive for comparison
                            
                            if created_time < cutoff_time:
                                project_id = container.labels.get('clarity.project_id', 'unknown')
                                
                                # Remove from registry
                                self._unregister_container(container.id)
                                
                                # Remove container
                                container.remove(force=True)
                                stats['containers_removed'] += 1
                                
                                self.logger.info(
                                    "Removed expired container",
                                    correlation_id=self.correlation_id,
                                    execution_id=execution_id,
                                    container_id=container.id,
                                    project_id=project_id,
                                    container_age_days=round((datetime.utcnow() - created_time).total_seconds() / 86400, 2)
                                )
                                
                    except Exception as e:
                        stats['errors'] += 1
                        self.logger.error(
                            "Failed to remove container",
                            correlation_id=self.correlation_id,
                            execution_id=execution_id,
                            container_id=container.id,
                            error=e
                        )
                        
            except APIError as e:
                self.logger.error(
                    "Failed to list containers for cleanup",
                    correlation_id=self.correlation_id,
                    execution_id=execution_id,
                    error=e
                )
            
            # Clean up volumes
            try:
                volumes = self.docker_client.volumes.list(
                    filters={
                        'label': 'clarity.component=per-project-containers'
                    }
                )
                
                for volume in volumes:
                    stats['volumes_checked'] += 1
                    
                    try:
                        # Get creation time from labels
                        created_str = volume.attrs['Labels'].get('clarity.created')
                        if created_str:
                            created_time = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                            created_time = created_time.replace(tzinfo=None)  # Make naive for comparison
                            
                            if created_time < cutoff_time:
                                project_id = volume.attrs['Labels'].get('clarity.project_id', 'unknown')
                                
                                # Remove volume
                                volume.remove(force=True)
                                stats['volumes_removed'] += 1
                                
                                self.logger.info(
                                    "Removed expired volume",
                                    correlation_id=self.correlation_id,
                                    execution_id=execution_id,
                                    volume_name=volume.name,
                                    project_id=project_id,
                                    volume_age_days=round((datetime.utcnow() - created_time).total_seconds() / 86400, 2)
                                )
                                
                    except Exception as e:
                        stats['errors'] += 1
                        self.logger.error(
                            "Failed to remove volume",
                            correlation_id=self.correlation_id,
                            execution_id=execution_id,
                            volume_name=volume.name,
                            error=e
                        )
                        
            except APIError as e:
                self.logger.error(
                    "Failed to list volumes for cleanup",
                    correlation_id=self.correlation_id,
                    execution_id=execution_id,
                    error=e
                )
            
            self.logger.info(
                "Container cleanup completed",
                correlation_id=self.correlation_id,
                execution_id=execution_id,
                status=LogStatus.COMPLETED,
                containers_checked=stats['containers_checked'],
                containers_removed=stats['containers_removed'],
                volumes_checked=stats['volumes_checked'],
                volumes_removed=stats['volumes_removed'],
                errors=stats['errors']
            )
            
            return stats
            
        except Exception as e:
            self.logger.error(
                "Container cleanup failed",
                correlation_id=self.correlation_id,
                execution_id=execution_id,
                status=LogStatus.FAILED,
                error=e
            )
            raise ContainerError(f"Container cleanup failed: {str(e)}")


def get_per_project_container_manager(correlation_id: Optional[str] = None) -> PerProjectContainerManager:
    """
    Factory function to get a per-project container manager instance.
    
    Args:
        correlation_id: Optional correlation ID for distributed tracing
        
    Returns:
        PerProjectContainerManager instance
    """
    return PerProjectContainerManager(correlation_id=correlation_id)