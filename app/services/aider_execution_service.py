"""
Aider Execution Service Module for Clarity Local Runner

This module provides Aider execution capabilities within isolated Docker containers,
integrating with the existing DeterministicPromptService and PerProjectContainerManager
to execute Aider commands and capture execution artifacts.

Primary Responsibility: Execute Aider commands in isolated containers and capture artifacts
"""

import os
import re
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from core.structured_logging import get_structured_logger, LogStatus, log_performance
from core.exceptions import ValidationError, ExternalServiceError
from core.performance_monitoring import record_verification_duration
from services.deterministic_prompt_service import (
    DeterministicPromptService, 
    PromptContext,
    get_deterministic_prompt_service
)
from services.per_project_container_manager import (
    PerProjectContainerManager,
    ContainerError,
    get_per_project_container_manager
)


@dataclass
class AiderExecutionContext:
    """
    Context data structure for Aider execution.
    
    This dataclass encapsulates all the information needed to execute
    Aider commands within isolated containers.
    """
    project_id: str
    execution_id: str
    correlation_id: Optional[str] = None
    
    # Repository context
    repository_url: Optional[str] = None
    repository_path: Optional[str] = None
    repository_branch: str = "main"
    
    # Aider configuration
    model: str = "gpt-4"
    aider_args: Optional[List[str]] = None
    files_to_modify: Optional[List[str]] = None
    
    # Execution settings
    timeout_seconds: int = 1800  # 30 minutes default
    working_directory: str = "/workspace"
    
    # Additional context
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AiderExecutionResult:
    """
    Result data structure for Aider execution.
    
    This dataclass contains all artifacts and metadata from Aider execution,
    including retry-related metadata to support the retry functionality
    implemented in Tasks 7.5.1-7.5.3.
    """
    success: bool
    execution_id: str
    project_id: str
    
    # Execution artifacts
    stdout_output: str
    stderr_output: str
    exit_code: int
    diff_output: Optional[str] = None
    files_modified: Optional[List[str]] = None
    commit_hash: Optional[str] = None
    
    # Performance metrics
    total_duration_ms: float = 0.0
    aider_execution_duration_ms: float = 0.0
    container_setup_duration_ms: float = 0.0
    artifact_capture_duration_ms: float = 0.0
    
    # Error information
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    
    # Retry-related metadata (added for Tasks 7.5.1-7.5.3)
    attempt_count: int = 1
    retry_attempts: Optional[List[Dict[str, Any]]] = None
    final_attempt: bool = True
    
    # Additional metadata
    aider_version: Optional[str] = None
    container_id: Optional[str] = None
    execution_timestamp: Optional[str] = None
    
    def __post_init__(self):
        """Initialize retry_attempts as empty list if None for backward compatibility."""
        if self.retry_attempts is None:
            self.retry_attempts = []


class AiderExecutionError(Exception):
    """Custom exception for Aider execution errors."""
    
    def __init__(
        self, 
        message: str, 
        project_id: Optional[str] = None, 
        execution_id: Optional[str] = None,
        exit_code: Optional[int] = None
    ):
        super().__init__(message)
        self.project_id = project_id
        self.execution_id = execution_id
        self.exit_code = exit_code


class AiderExecutionService:
    """
    Aider execution service for running Aider commands in isolated containers.
    
    This service integrates with the existing DeterministicPromptService and
    PerProjectContainerManager to provide secure, isolated Aider execution
    with comprehensive artifact capture and audit logging.
    
    Key Features:
    - Container-based isolation for secure execution
    - Integration with existing prompt generation service
    - Comprehensive artifact capture (diff, stdout, files modified)
    - Performance monitoring (≤30s requirement)
    - Comprehensive error handling and validation
    - Structured audit logging with correlation IDs
    """
    
    # Aider installation and configuration
    AIDER_INSTALL_COMMAND = "pip install aider-chat"
    AIDER_VERSION_COMMAND = "aider --version"
    
    # File patterns for detecting modifications
    MODIFIED_FILES_PATTERNS = [
        re.compile(r'^\s*Modified\s+(.+)$', re.MULTILINE | re.IGNORECASE),
        re.compile(r'^\s*Created\s+(.+)$', re.MULTILINE | re.IGNORECASE),
        re.compile(r'^\s*Deleted\s+(.+)$', re.MULTILINE | re.IGNORECASE),
    ]
    
    # Git commit hash pattern
    COMMIT_HASH_PATTERN = re.compile(r'commit\s+([a-f0-9]{40})', re.IGNORECASE)
    
    # Git commands
    GIT_CHECKOUT_COMMAND = "git checkout"
    GIT_MERGE_COMMAND = "git merge --no-ff"
    GIT_PUSH_COMMAND = "git push"
    GIT_STATUS_COMMAND = "git status"
    GIT_LOG_COMMAND = "git log -1 --format=%H"
    
    # NPM commands
    NPM_CI_COMMAND = "npm ci"
    NPM_BUILD_COMMAND = "npm run build"
    NPM_VERSION_COMMAND = "npm --version"
    
    # Common build output directories
    BUILD_OUTPUT_DIRECTORIES = [
        "dist",
        "build",
        "out",
        "public",
        ".next",
        "lib",
        "es"
    ]
    
    def __init__(self, correlation_id: Optional[str] = None):
        """
        Initialize the Aider execution service.
        
        Args:
            correlation_id: Optional correlation ID for distributed tracing
        """
        self.logger = get_structured_logger(__name__)
        self.correlation_id = correlation_id
        
        # Initialize dependent services
        self.prompt_service = get_deterministic_prompt_service(correlation_id)
        self.container_manager = get_per_project_container_manager(correlation_id)
        
        # Set persistent context for logging
        if correlation_id:
            self.logger.set_context(correlationId=correlation_id)
    
    @log_performance(get_structured_logger(__name__), "execute_aider")
    def execute_aider(
        self,
        execution_context: AiderExecutionContext,
        prompt_context: Optional[PromptContext] = None,
        use_generated_prompt: bool = True
    ) -> AiderExecutionResult:
        """
        Execute Aider command within an isolated container.
        
        This method orchestrates the complete Aider execution process including
        container setup, prompt generation, Aider execution, and artifact capture.
        
        Args:
            execution_context: Context for Aider execution
            prompt_context: Optional context for prompt generation
            use_generated_prompt: Whether to use generated prompt or direct execution
            
        Returns:
            AiderExecutionResult containing execution artifacts and metadata
            
        Raises:
            ValidationError: If input validation fails
            AiderExecutionError: If Aider execution fails
            ContainerError: If container operations fail
        """
        start_time = time.time()
        
        try:
            # Validate execution context
            self._validate_execution_context(execution_context)
            
            self.logger.info(
                "Starting Aider execution",
                correlation_id=self.correlation_id,
                project_id=execution_context.project_id,
                execution_id=execution_context.execution_id,
                status=LogStatus.STARTED,
                repository_url=execution_context.repository_url,
                model=execution_context.model,
                use_generated_prompt=use_generated_prompt
            )
            
            # Initialize result object
            result = AiderExecutionResult(
                success=False,
                execution_id=execution_context.execution_id,
                project_id=execution_context.project_id,
                stdout_output="",
                stderr_output="",
                exit_code=-1,
                execution_timestamp=datetime.utcnow().isoformat() + "Z"
            )
            
            # Step 1: Setup container
            container_setup_start = time.time()
            container_result = self._setup_container(execution_context)
            container_setup_duration = (time.time() - container_setup_start) * 1000
            
            result.container_id = container_result['container_id']
            result.container_setup_duration_ms = round(container_setup_duration, 2)
            
            # Step 2: Install Aider if needed
            self._ensure_aider_installed(container_result['container'], execution_context)
            
            # Step 3: Setup repository if specified
            if execution_context.repository_url:
                self._setup_repository(container_result['container'], execution_context)
            
            # Step 4: Generate prompt if requested
            aider_prompt = None
            if use_generated_prompt and prompt_context:
                prompt_result = self.prompt_service.generate_prompt(prompt_context)
                if prompt_result['success']:
                    aider_prompt = prompt_result['prompt']
                    self.logger.info(
                        "Generated Aider prompt successfully",
                        correlation_id=self.correlation_id,
                        project_id=execution_context.project_id,
                        execution_id=execution_context.execution_id,
                        prompt_length=len(aider_prompt)
                    )
            
            # Step 5: Execute Aider
            aider_execution_start = time.time()
            execution_result = self._execute_aider_command(
                container_result['container'], 
                execution_context, 
                aider_prompt
            )
            aider_execution_duration = (time.time() - aider_execution_start) * 1000
            
            result.aider_execution_duration_ms = round(aider_execution_duration, 2)
            result.stdout_output = execution_result['stdout']
            result.stderr_output = execution_result['stderr']
            result.exit_code = execution_result['exit_code']
            
            # Step 6: Capture artifacts
            artifact_capture_start = time.time()
            artifacts = self._capture_execution_artifacts(
                container_result['container'], 
                execution_context,
                execution_result
            )
            artifact_capture_duration = (time.time() - artifact_capture_start) * 1000
            
            result.artifact_capture_duration_ms = round(artifact_capture_duration, 2)
            result.diff_output = artifacts.get('diff_output')
            result.files_modified = artifacts.get('files_modified', [])
            result.commit_hash = artifacts.get('commit_hash')
            result.aider_version = artifacts.get('aider_version')
            
            # Determine success
            result.success = execution_result['exit_code'] == 0
            
            # Calculate total duration
            total_duration = (time.time() - start_time) * 1000
            result.total_duration_ms = round(total_duration, 2)
            
            # Log completion
            self.logger.info(
                "Aider execution completed",
                correlation_id=self.correlation_id,
                project_id=execution_context.project_id,
                execution_id=execution_context.execution_id,
                status=LogStatus.COMPLETED if result.success else LogStatus.FAILED,
                exit_code=result.exit_code,
                files_modified_count=len(result.files_modified or []),
                total_duration_ms=result.total_duration_ms,
                success=result.success
            )
            
            return result
            
        except (ValidationError, ContainerError, AiderExecutionError):
            # Re-raise known exceptions with additional context
            total_duration = (time.time() - start_time) * 1000
            self.logger.error(
                "Aider execution failed due to known error",
                correlation_id=self.correlation_id,
                project_id=execution_context.project_id,
                execution_id=execution_context.execution_id,
                status=LogStatus.FAILED,
                total_duration_ms=round(total_duration, 2)
            )
            raise
        except Exception as e:
            total_duration = (time.time() - start_time) * 1000
            self.logger.error(
                "Aider execution failed with unexpected error",
                correlation_id=self.correlation_id,
                project_id=execution_context.project_id,
                execution_id=execution_context.execution_id,
                status=LogStatus.FAILED,
                total_duration_ms=round(total_duration, 2),
                error=e
            )
            raise AiderExecutionError(
                f"Aider execution failed: {str(e)}",
                project_id=execution_context.project_id,
                execution_id=execution_context.execution_id
            )
    
    def _validate_execution_context(self, context: AiderExecutionContext) -> None:
        """
        Validate Aider execution context for required fields and security.
        
        Args:
            context: Execution context to validate
            
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(context, AiderExecutionContext):
            raise ValidationError(
                "execution_context must be an AiderExecutionContext instance",
                field_errors=[{"field": "execution_context", "error": "Invalid type"}]
            )
        
        # Validate required fields
        required_fields = ['project_id', 'execution_id']
        missing_fields = []
        
        for field in required_fields:
            value = getattr(context, field, None)
            if not value or not str(value).strip():
                missing_fields.append(field)
        
        if missing_fields:
            raise ValidationError(
                f"Missing required fields: {', '.join(missing_fields)}",
                field_errors=[
                    {"field": field, "error": "Required field is missing or empty"}
                    for field in missing_fields
                ]
            )
        
        # Validate field formats for security
        import re
        
        # Project ID validation (similar to container manager)
        if not re.match(r'^[a-zA-Z0-9_/-]+$', context.project_id):
            raise ValidationError(
                "project_id contains invalid characters",
                field_errors=[{"field": "project_id", "error": "Must contain only alphanumeric characters, underscores, hyphens, and forward slashes"}]
            )
        
        # Validate timeout
        if context.timeout_seconds <= 0 or context.timeout_seconds > 3600:  # Max 1 hour
            raise ValidationError(
                "timeout_seconds must be between 1 and 3600 seconds",
                field_errors=[{"field": "timeout_seconds", "error": "Invalid timeout value"}]
            )
        
        # Validate model name
        if not re.match(r'^[a-zA-Z0-9_-]+$', context.model):
            raise ValidationError(
                "model contains invalid characters",
                field_errors=[{"field": "model", "error": "Must contain only alphanumeric characters, underscores, and hyphens"}]
            )
    
    def _validate_retry_limit(
        self,
        max_attempts: int,
        operation_name: str,
        context: AiderExecutionContext
    ) -> None:
        """
        Validate retry limit to ensure maximum of 2 attempts per build operation.
        
        This method enforces the PRD requirement (line 81) that specifies maximum 2 retries
        for build verification operations (VerifyNode: build/test checks, ≤2 retries).
        
        Args:
            max_attempts: Number of attempts requested
            operation_name: Name of the operation for error messages
            context: Execution context for logging
            
        Raises:
            ValidationError: If retry limit is exceeded
        """
        # PRD line 81 specifies maximum 2 attempts for build operations
        MAX_ALLOWED_ATTEMPTS = 2
        
        if not isinstance(max_attempts, int):
            raise ValidationError(
                f"max_attempts must be an integer, got {type(max_attempts).__name__}",
                field_errors=[{"field": "max_attempts", "error": "Must be an integer"}]
            )
        
        if max_attempts < 1:
            raise ValidationError(
                f"max_attempts must be at least 1, got {max_attempts}",
                field_errors=[{"field": "max_attempts", "error": "Must be at least 1"}]
            )
        
        if max_attempts > MAX_ALLOWED_ATTEMPTS:
            error_message = (
                f"Retry limit exceeded for {operation_name}: requested {max_attempts} attempts, "
                f"but maximum allowed is {MAX_ALLOWED_ATTEMPTS} as specified in PRD line 81"
            )
            
            self.logger.error(
                "Retry limit validation failed",
                correlation_id=self.correlation_id,
                project_id=context.project_id,
                execution_id=context.execution_id,
                operation_name=operation_name,
                requested_attempts=max_attempts,
                max_allowed_attempts=MAX_ALLOWED_ATTEMPTS,
                error_message=error_message
            )
            
            raise ValidationError(
                error_message,
                field_errors=[{
                    "field": "max_attempts",
                    "error": f"Maximum {MAX_ALLOWED_ATTEMPTS} attempts allowed, got {max_attempts}"
                }]
            )
        
        # Log successful validation
        self.logger.debug(
            "Retry limit validation passed",
            correlation_id=self.correlation_id,
            project_id=context.project_id,
            execution_id=context.execution_id,
            operation_name=operation_name,
            max_attempts=max_attempts,
            max_allowed_attempts=MAX_ALLOWED_ATTEMPTS
        )
    
    def _setup_container(self, context: AiderExecutionContext) -> Dict[str, Any]:
        """
        Setup container for Aider execution.
        
        Args:
            context: Execution context
            
        Returns:
            Dictionary containing container information
            
        Raises:
            ContainerError: If container setup fails
        """
        try:
            container_result = self.container_manager.start_or_reuse_container(
                project_id=context.project_id,
                execution_id=context.execution_id,
                timeout_seconds=30  # Container setup timeout
            )
            
            if not container_result['success']:
                raise ContainerError(
                    "Failed to setup container for Aider execution",
                    project_id=context.project_id
                )
            
            # Get container object
            container = self.container_manager.docker_client.containers.get(
                container_result['container_id']
            )
            
            return {
                'container': container,
                'container_id': container_result['container_id'],
                'container_status': container_result['container_status']
            }
            
        except Exception as e:
            raise ContainerError(
                f"Container setup failed: {str(e)}",
                project_id=context.project_id
            )
    
    def _ensure_aider_installed(self, container, context: AiderExecutionContext) -> None:
        """
        Ensure Aider is installed in the container.
        
        Args:
            container: Docker container instance
            context: Execution context
            
        Raises:
            AiderExecutionError: If Aider installation fails
        """
        try:
            # Check if Aider is already installed
            exit_code, output = container.exec_run(self.AIDER_VERSION_COMMAND)
            
            if exit_code == 0:
                # Aider is already installed
                version_output = output.decode('utf-8').strip() if isinstance(output, bytes) else str(output).strip()
                self.logger.info(
                    "Aider already installed",
                    correlation_id=self.correlation_id,
                    project_id=context.project_id,
                    execution_id=context.execution_id,
                    aider_version=version_output
                )
                return
            
            # Install Aider
            self.logger.info(
                "Installing Aider in container",
                correlation_id=self.correlation_id,
                project_id=context.project_id,
                execution_id=context.execution_id,
                status=LogStatus.IN_PROGRESS
            )
            
            exit_code, output = container.exec_run(self.AIDER_INSTALL_COMMAND)
            
            if exit_code != 0:
                error_output = output.decode('utf-8') if isinstance(output, bytes) else str(output)
                raise AiderExecutionError(
                    f"Failed to install Aider: {error_output}",
                    project_id=context.project_id,
                    execution_id=context.execution_id,
                    exit_code=exit_code
                )
            
            # Verify installation
            exit_code, output = container.exec_run(self.AIDER_VERSION_COMMAND)
            if exit_code != 0:
                raise AiderExecutionError(
                    "Aider installation verification failed",
                    project_id=context.project_id,
                    execution_id=context.execution_id,
                    exit_code=exit_code
                )
            
            version_output = output.decode('utf-8').strip() if isinstance(output, bytes) else str(output).strip()
            self.logger.info(
                "Aider installed successfully",
                correlation_id=self.correlation_id,
                project_id=context.project_id,
                execution_id=context.execution_id,
                status=LogStatus.COMPLETED,
                aider_version=version_output
            )
            
        except Exception as e:
            if isinstance(e, AiderExecutionError):
                raise
            raise AiderExecutionError(
                f"Aider installation failed: {str(e)}",
                project_id=context.project_id,
                execution_id=context.execution_id
            )
    
    def _setup_repository(self, container, context: AiderExecutionContext) -> None:
        """
        Setup repository in the container workspace.
        
        Args:
            container: Docker container instance
            context: Execution context
            
        Raises:
            AiderExecutionError: If repository setup fails
        """
        try:
            if not context.repository_url:
                return
            
            self.logger.info(
                "Setting up repository in container",
                correlation_id=self.correlation_id,
                project_id=context.project_id,
                execution_id=context.execution_id,
                repository_url=context.repository_url,
                repository_branch=context.repository_branch
            )
            
            # Clone repository
            clone_command = f"cd {context.working_directory} && git clone -b {context.repository_branch} {context.repository_url} repo"
            exit_code, output = container.exec_run(clone_command)
            
            if exit_code != 0:
                error_output = output.decode('utf-8') if isinstance(output, bytes) else str(output)
                raise AiderExecutionError(
                    f"Failed to clone repository: {error_output}",
                    project_id=context.project_id,
                    execution_id=context.execution_id,
                    exit_code=exit_code
                )
            
            self.logger.info(
                "Repository setup completed",
                correlation_id=self.correlation_id,
                project_id=context.project_id,
                execution_id=context.execution_id,
                status=LogStatus.COMPLETED
            )
            
        except Exception as e:
            if isinstance(e, AiderExecutionError):
                raise
            raise AiderExecutionError(
                f"Repository setup failed: {str(e)}",
                project_id=context.project_id,
                execution_id=context.execution_id
            )
    
    def _execute_aider_command(
        self, 
        container, 
        context: AiderExecutionContext, 
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute Aider command in the container.
        
        Args:
            container: Docker container instance
            context: Execution context
            prompt: Optional prompt to use with Aider
            
        Returns:
            Dictionary containing execution results
            
        Raises:
            AiderExecutionError: If command execution fails
        """
        try:
            # Build Aider command
            working_dir = f"{context.working_directory}/repo" if context.repository_url else context.working_directory
            
            # Base command
            aider_cmd = f"cd {working_dir} && aider --model {context.model}"
            
            # Add files to modify if specified
            if context.files_to_modify:
                files_str = " ".join(f'"{file}"' for file in context.files_to_modify)
                aider_cmd += f" {files_str}"
            
            # Add additional arguments if specified
            if context.aider_args:
                aider_cmd += " " + " ".join(context.aider_args)
            
            # Add prompt if provided
            if prompt:
                # Write prompt to temporary file and use it
                prompt_file = f"{working_dir}/aider_prompt.txt"
                write_prompt_cmd = f"cd {working_dir} && echo {json.dumps(prompt)} > aider_prompt.txt"
                
                exit_code, output = container.exec_run(write_prompt_cmd)
                if exit_code != 0:
                    raise AiderExecutionError(
                        "Failed to write prompt file",
                        project_id=context.project_id,
                        execution_id=context.execution_id,
                        exit_code=exit_code
                    )
                
                aider_cmd += f" --message-file aider_prompt.txt"
            
            self.logger.info(
                "Executing Aider command",
                correlation_id=self.correlation_id,
                project_id=context.project_id,
                execution_id=context.execution_id,
                status=LogStatus.IN_PROGRESS,
                has_prompt=prompt is not None,
                files_count=len(context.files_to_modify or [])
            )
            
            # Execute Aider command
            exit_code, output = container.exec_run(aider_cmd)
            
            # Process output
            stdout = output.decode('utf-8') if isinstance(output, bytes) else str(output)
            stderr = ""  # Docker exec_run combines stdout and stderr
            
            self.logger.info(
                "Aider command execution completed",
                correlation_id=self.correlation_id,
                project_id=context.project_id,
                execution_id=context.execution_id,
                status=LogStatus.COMPLETED if exit_code == 0 else LogStatus.FAILED,
                exit_code=exit_code,
                output_length=len(stdout)
            )
            
            return {
                'exit_code': exit_code,
                'stdout': stdout,
                'stderr': stderr,
                'command': aider_cmd
            }
            
        except Exception as e:
            if isinstance(e, AiderExecutionError):
                raise
            raise AiderExecutionError(
                f"Aider command execution failed: {str(e)}",
                project_id=context.project_id,
                execution_id=context.execution_id
            )
    
    def _capture_execution_artifacts(
        self, 
        container, 
        context: AiderExecutionContext, 
        execution_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Capture execution artifacts from Aider execution.
        
        Args:
            container: Docker container instance
            context: Execution context
            execution_result: Results from Aider execution
            
        Returns:
            Dictionary containing captured artifacts
        """
        artifacts = {
            'diff_output': None,
            'files_modified': [],
            'commit_hash': None,
            'aider_version': None
        }
        
        try:
            working_dir = f"{context.working_directory}/repo" if context.repository_url else context.working_directory
            
            # Capture Aider version
            try:
                exit_code, output = container.exec_run(self.AIDER_VERSION_COMMAND)
                if exit_code == 0:
                    artifacts['aider_version'] = output.decode('utf-8').strip() if isinstance(output, bytes) else str(output).strip()
            except Exception:
                pass  # Non-critical
            
            # Extract files modified from stdout
            stdout = execution_result.get('stdout', '')
            files_modified = []
            
            for pattern in self.MODIFIED_FILES_PATTERNS:
                matches = pattern.findall(stdout)
                files_modified.extend(matches)
            
            # Clean and deduplicate file paths
            artifacts['files_modified'] = list(set(
                file.strip() for file in files_modified if file.strip()
            ))
            
            # Capture git diff if repository is available
            if context.repository_url:
                try:
                    diff_cmd = f"cd {working_dir} && git diff HEAD~1"
                    exit_code, output = container.exec_run(diff_cmd)
                    if exit_code == 0:
                        artifacts['diff_output'] = output.decode('utf-8') if isinstance(output, bytes) else str(output)
                except Exception:
                    pass  # Non-critical
                
                # Capture commit hash
                try:
                    commit_cmd = f"cd {working_dir} && git log -1 --format=%H"
                    exit_code, output = container.exec_run(commit_cmd)
                    if exit_code == 0:
                        commit_hash = output.decode('utf-8').strip() if isinstance(output, bytes) else str(output).strip()
                        if commit_hash:
                            artifacts['commit_hash'] = commit_hash
                except Exception:
                    pass  # Non-critical
            
            self.logger.info(
                "Execution artifacts captured",
                correlation_id=self.correlation_id,
                project_id=context.project_id,
                execution_id=context.execution_id,
                files_modified_count=len(artifacts['files_modified']),
                has_diff=artifacts['diff_output'] is not None,
                has_commit_hash=artifacts['commit_hash'] is not None
            )
            
        except Exception as e:
            self.logger.warn(
                "Failed to capture some execution artifacts",
                correlation_id=self.correlation_id,
                project_id=context.project_id,
                execution_id=context.execution_id,
                error=str(e)
            )
        
        return artifacts
    
    @log_performance(get_structured_logger(__name__), "execute_npm_ci")
    def execute_npm_ci(
        self,
        execution_context: AiderExecutionContext,
        working_directory: Optional[str] = None
    ) -> AiderExecutionResult:
        """
        Execute npm ci command within an isolated container with retry mechanism.
        
        This method executes npm ci in the target repository to install dependencies
        from package-lock.json with clean, reproducible builds. It includes retry
        logic with maximum 2 attempts as specified in PRD line 81.
        
        Args:
            execution_context: Context for npm execution
            working_directory: Optional working directory override
            
        Returns:
            AiderExecutionResult containing execution artifacts and metadata
            
        Raises:
            ValidationError: If input validation fails
            AiderExecutionError: If npm ci execution fails after all retries
            ContainerError: If container operations fail
        """
        return self._execute_npm_ci_with_retry(execution_context, working_directory)
    
    def _execute_npm_ci_with_retry(
        self,
        execution_context: AiderExecutionContext,
        working_directory: Optional[str] = None,
        max_attempts: int = 2
    ) -> AiderExecutionResult:
        """
        Execute npm ci with retry mechanism (maximum 2 attempts).
        
        Args:
            execution_context: Context for npm execution
            working_directory: Optional working directory override
            max_attempts: Maximum number of attempts (default: 2, maximum allowed: 2)
            
        Returns:
            AiderExecutionResult containing execution artifacts and metadata
            
        Raises:
            ValidationError: If input validation fails or retry limit exceeded
            AiderExecutionError: If npm ci execution fails after all retries
            ContainerError: If container operations fail
        """
        start_time = time.time()
        last_error = None
        retry_attempts = []
        
        try:
            # Validate execution context
            self._validate_execution_context(execution_context)
            
            # Validate retry limit as specified in PRD line 81: maximum 2 attempts
            self._validate_retry_limit(max_attempts, "npm ci", execution_context)
            
            self.logger.info(
                "Starting npm ci execution with retry mechanism",
                correlation_id=self.correlation_id,
                project_id=execution_context.project_id,
                execution_id=execution_context.execution_id,
                status=LogStatus.STARTED,
                repository_url=execution_context.repository_url,
                working_directory=working_directory or execution_context.working_directory,
                max_attempts=max_attempts
            )
            
            for attempt in range(1, max_attempts + 1):
                attempt_start_time = time.time()
                
                # Enhanced retry attempt logging with comprehensive details
                self.logger.info(
                    f"npm ci execution attempt {attempt}/{max_attempts} starting",
                    correlation_id=self.correlation_id,
                    project_id=execution_context.project_id,
                    execution_id=execution_context.execution_id,
                    operation_type="npm_ci",
                    attempt=attempt,
                    max_attempts=max_attempts,
                    retry_strategy="exponential_backoff" if attempt > 1 else "initial_attempt",
                    working_directory=working_directory or execution_context.working_directory,
                    repository_url=execution_context.repository_url,
                    timeout_seconds=execution_context.timeout_seconds,
                    status=LogStatus.IN_PROGRESS,
                    retry_context={
                        "is_retry": attempt > 1,
                        "previous_attempts": attempt - 1,
                        "remaining_attempts": max_attempts - attempt
                    }
                )
                
                try:
                    result = self._execute_npm_ci_single_attempt(
                        execution_context,
                        working_directory,
                        attempt
                    )
                    
                    # Calculate attempt duration for detailed logging
                    attempt_duration = (time.time() - attempt_start_time) * 1000
                    
                    # If successful, return immediately with enhanced success logging
                    if result.success:
                        total_duration = (time.time() - start_time) * 1000
                        
                        # Update result with retry metadata
                        result.attempt_count = attempt
                        result.retry_attempts = retry_attempts
                        result.final_attempt = True
                        
                        self.logger.info(
                            f"npm ci execution succeeded on attempt {attempt}/{max_attempts}",
                            correlation_id=self.correlation_id,
                            project_id=execution_context.project_id,
                            execution_id=execution_context.execution_id,
                            operation_type="npm_ci",
                            attempt=attempt,
                            max_attempts=max_attempts,
                            attempt_duration_ms=round(attempt_duration, 2),
                            total_duration_ms=round(total_duration, 2),
                            exit_code=result.exit_code,
                            files_modified_count=len(result.files_modified or []),
                            container_id=result.container_id,
                            status=LogStatus.COMPLETED,
                            retry_outcome={
                                "success": True,
                                "attempts_used": attempt,
                                "attempts_saved": max_attempts - attempt,
                                "total_retry_duration_ms": round(total_duration, 2)
                            }
                        )
                        return result
                    
                    # If not successful but no exception, treat as failure with detailed logging
                    failure_reason = f"npm ci failed with exit code {result.exit_code}"
                    last_error = AiderExecutionError(
                        failure_reason,
                        project_id=execution_context.project_id,
                        execution_id=execution_context.execution_id,
                        exit_code=result.exit_code
                    )
                    
                    # Record retry attempt details
                    retry_attempt_info = {
                        "attempt": attempt,
                        "start_time": datetime.utcnow().isoformat() + "Z",
                        "duration_ms": round(attempt_duration, 2),
                        "success": False,
                        "error_type": "AiderExecutionError",
                        "error_message": failure_reason,
                        "failure_reason": failure_reason,
                        "exit_code": result.exit_code,
                        "container_id": result.container_id,
                        "stdout_length": len(result.stdout_output or ""),
                        "stderr_length": len(result.stderr_output or "")
                    }
                    retry_attempts.append(retry_attempt_info)
                    
                    # Enhanced failure logging for non-exception failures
                    self.logger.warn(
                        f"npm ci execution attempt {attempt}/{max_attempts} failed with exit code",
                        correlation_id=self.correlation_id,
                        project_id=execution_context.project_id,
                        execution_id=execution_context.execution_id,
                        operation_type="npm_ci",
                        attempt=attempt,
                        max_attempts=max_attempts,
                        attempt_duration_ms=round(attempt_duration, 2),
                        exit_code=result.exit_code,
                        failure_reason=failure_reason,
                        stdout_length=len(result.stdout_output or ""),
                        stderr_length=len(result.stderr_output or ""),
                        container_id=result.container_id,
                        status=LogStatus.FAILED,
                        retry_context={
                            "will_retry": attempt < max_attempts,
                            "remaining_attempts": max_attempts - attempt,
                            "failure_type": "exit_code_failure"
                        }
                    )
                    
                except Exception as e:
                    last_error = e
                    attempt_duration = (time.time() - attempt_start_time) * 1000
                    
                    # Record retry attempt details
                    retry_attempt_info = {
                        "attempt": attempt,
                        "start_time": datetime.utcnow().isoformat() + "Z",
                        "duration_ms": round(attempt_duration, 2),
                        "success": False,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "failure_reason": f"Exception during npm ci execution: {str(e)}",
                        "exit_code": None,
                        "container_id": None
                    }
                    retry_attempts.append(retry_attempt_info)
                    
                    # Enhanced exception failure logging with comprehensive details
                    self.logger.warn(
                        f"npm ci execution attempt {attempt}/{max_attempts} failed with exception",
                        correlation_id=self.correlation_id,
                        project_id=execution_context.project_id,
                        execution_id=execution_context.execution_id,
                        operation_type="npm_ci",
                        attempt=attempt,
                        max_attempts=max_attempts,
                        attempt_duration_ms=round(attempt_duration, 2),
                        error_type=type(e).__name__,
                        error_message=str(e),
                        failure_reason=f"Exception during npm ci execution: {str(e)}",
                        status=LogStatus.FAILED,
                        retry_context={
                            "will_retry": attempt < max_attempts,
                            "remaining_attempts": max_attempts - attempt,
                            "failure_type": "exception_failure",
                            "exception_class": type(e).__name__
                        }
                    )
                
                # Container cleanup after failed attempt (except for last attempt)
                if attempt < max_attempts:
                    try:
                        self._cleanup_container_after_failed_attempt(execution_context, attempt)
                    except Exception as cleanup_error:
                        self.logger.warn(
                            f"Container cleanup failed after npm ci attempt {attempt}",
                            correlation_id=self.correlation_id,
                            project_id=execution_context.project_id,
                            execution_id=execution_context.execution_id,
                            operation_type="npm_ci",
                            attempt=attempt,
                            cleanup_error_type=type(cleanup_error).__name__,
                            cleanup_error_message=str(cleanup_error),
                            status=LogStatus.FAILED,
                            cleanup_context={
                                "operation": "npm_ci",
                                "failed_attempt": attempt,
                                "max_attempts": max_attempts
                            }
                        )
            
            # All attempts failed
            total_duration = (time.time() - start_time) * 1000
            self.logger.error(
                f"npm ci execution failed after {max_attempts} attempts",
                correlation_id=self.correlation_id,
                project_id=execution_context.project_id,
                execution_id=execution_context.execution_id,
                max_attempts=max_attempts,
                total_duration_ms=round(total_duration, 2),
                final_error=str(last_error),
                status=LogStatus.FAILED
            )
            
            # Re-raise the last error
            if isinstance(last_error, (ValidationError, ContainerError, AiderExecutionError)):
                raise last_error
            else:
                raise AiderExecutionError(
                    f"npm ci execution failed after {max_attempts} attempts: {str(last_error)}",
                    project_id=execution_context.project_id,
                    execution_id=execution_context.execution_id
                )
                
        except (ValidationError, ContainerError, AiderExecutionError):
            # Re-raise known exceptions with additional context
            total_duration = (time.time() - start_time) * 1000
            self.logger.error(
                "npm ci execution failed due to known error",
                correlation_id=self.correlation_id,
                project_id=execution_context.project_id,
                execution_id=execution_context.execution_id,
                status=LogStatus.FAILED,
                total_duration_ms=round(total_duration, 2)
            )
            raise
        except Exception as e:
            total_duration = (time.time() - start_time) * 1000
            self.logger.error(
                "npm ci execution failed with unexpected error",
                correlation_id=self.correlation_id,
                project_id=execution_context.project_id,
                execution_id=execution_context.execution_id,
                status=LogStatus.FAILED,
                total_duration_ms=round(total_duration, 2),
                error=e
            )
            raise AiderExecutionError(
                f"npm ci execution failed: {str(e)}",
                project_id=execution_context.project_id,
                execution_id=execution_context.execution_id
            )
    
    def _execute_npm_ci_single_attempt(
        self,
        execution_context: AiderExecutionContext,
        working_directory: Optional[str] = None,
        attempt: int = 1
    ) -> AiderExecutionResult:
        """
        Execute a single npm ci attempt.
        
        Args:
            execution_context: Context for npm execution
            working_directory: Optional working directory override
            attempt: Current attempt number
            
        Returns:
            AiderExecutionResult containing execution artifacts and metadata
        """
        attempt_start_time = time.time()
        
        # Initialize result object
        result = AiderExecutionResult(
            success=False,
            execution_id=execution_context.execution_id,
            project_id=execution_context.project_id,
            stdout_output="",
            stderr_output="",
            exit_code=-1,
            execution_timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
        # Step 1: Setup container
        container_setup_start = time.time()
        container_result = self._setup_container(execution_context)
        container_setup_duration = (time.time() - container_setup_start) * 1000
        
        result.container_id = container_result['container_id']
        result.container_setup_duration_ms = round(container_setup_duration, 2)
        
        # Step 2: Setup repository if specified
        if execution_context.repository_url:
            self._setup_repository(container_result['container'], execution_context)
        
        # Step 3: Verify npm is available
        self._ensure_npm_available(container_result['container'], execution_context)
        
        # Step 4: Execute npm ci
        npm_execution_start = time.time()
        execution_result = self._execute_npm_ci_command(
            container_result['container'],
            execution_context,
            working_directory
        )
        npm_execution_end = time.time()
        npm_execution_duration = (npm_execution_end - npm_execution_start) * 1000
        
        # Record verification duration metric
        record_verification_duration(
            start_time=npm_execution_start,
            end_time=npm_execution_end,
            verification_type="npm_ci",
            success=execution_result['exit_code'] == 0,
            correlation_id=self.correlation_id,
            execution_id=execution_context.execution_id,
            project_id=execution_context.project_id,
            operation_details={
                "attempt": str(attempt),
                "working_directory": working_directory or execution_context.working_directory,
                "skipped": str(execution_result.get('skipped', False))
            }
        )
        
        result.aider_execution_duration_ms = round(npm_execution_duration, 2)  # Reusing field for npm duration
        result.stdout_output = execution_result['stdout']
        result.stderr_output = execution_result['stderr']
        result.exit_code = execution_result['exit_code']
        
        # Step 5: Capture artifacts
        artifact_capture_start = time.time()
        artifacts = self._capture_npm_artifacts(
            container_result['container'],
            execution_context,
            execution_result,
            working_directory
        )
        artifact_capture_duration = (time.time() - artifact_capture_start) * 1000
        
        result.artifact_capture_duration_ms = round(artifact_capture_duration, 2)
        result.files_modified = artifacts.get('files_modified', [])
        
        # Determine success (npm ci should exit with 0 for success)
        result.success = execution_result['exit_code'] == 0
        
        # Calculate total duration for this attempt
        attempt_duration = (time.time() - attempt_start_time) * 1000
        result.total_duration_ms = round(attempt_duration, 2)
        
        # Log attempt completion
        self.logger.info(
            f"npm ci attempt {attempt} completed",
            correlation_id=self.correlation_id,
            project_id=execution_context.project_id,
            execution_id=execution_context.execution_id,
            attempt=attempt,
            status=LogStatus.COMPLETED if result.success else LogStatus.FAILED,
            exit_code=result.exit_code,
            attempt_duration_ms=result.total_duration_ms,
            success=result.success
        )
        
        return result
    
    def _cleanup_container_after_failed_attempt(
        self,
        execution_context: AiderExecutionContext,
        attempt: int
    ) -> None:
        """
        Clean up container resources after a failed attempt.
        
        This method ensures proper cleanup of container resources between retry attempts
        to prevent resource leaks and ensure clean state for subsequent attempts.
        
        Args:
            execution_context: Context for the execution
            attempt: The failed attempt number
        """
        try:
            self.logger.info(
                f"Cleaning up container resources after failed attempt {attempt}",
                correlation_id=self.correlation_id,
                project_id=execution_context.project_id,
                execution_id=execution_context.execution_id,
                attempt=attempt
            )
            
            # Use the container manager to clean up any existing containers for this project
            if hasattr(self, 'container_manager') and self.container_manager:
                # Clean up expired containers - this will handle project-specific cleanup
                try:
                    cleanup_stats = self.container_manager.cleanup_expired_containers(
                        max_age_days=0,  # Force cleanup of all containers for this cleanup
                        execution_id=execution_context.execution_id
                    )
                    self.logger.info(
                        f"Container cleanup stats after failed attempt {attempt}",
                        correlation_id=self.correlation_id,
                        project_id=execution_context.project_id,
                        execution_id=execution_context.execution_id,
                        attempt=attempt,
                        cleanup_stats=cleanup_stats
                    )
                except Exception as cleanup_error:
                    # Log but don't re-raise cleanup errors
                    self.logger.warn(
                        f"Container cleanup method failed after attempt {attempt}",
                        correlation_id=self.correlation_id,
                        project_id=execution_context.project_id,
                        execution_id=execution_context.execution_id,
                        attempt=attempt,
                        cleanup_error=str(cleanup_error)
                    )
            
            self.logger.info(
                f"Container cleanup completed after failed attempt {attempt}",
                correlation_id=self.correlation_id,
                project_id=execution_context.project_id,
                execution_id=execution_context.execution_id,
                attempt=attempt
            )
            
        except Exception as e:
            self.logger.warn(
                f"Container cleanup encountered error after failed attempt {attempt}",
                correlation_id=self.correlation_id,
                project_id=execution_context.project_id,
                execution_id=execution_context.execution_id,
                attempt=attempt,
                cleanup_error=str(e)
            )
            # Don't re-raise cleanup errors as they shouldn't prevent retry attempts
    
    def _ensure_npm_available(self, container, context: AiderExecutionContext) -> None:
        """
        Ensure npm is available in the container.
        
        Args:
            container: Docker container instance
            context: Execution context
            
        Raises:
            AiderExecutionError: If npm is not available
        """
        try:
            # Check if npm is available
            exit_code, output = container.exec_run(self.NPM_VERSION_COMMAND)
            
            if exit_code == 0:
                # npm is available
                version_output = output.decode('utf-8').strip() if isinstance(output, bytes) else str(output).strip()
                self.logger.info(
                    "npm is available",
                    correlation_id=self.correlation_id,
                    project_id=context.project_id,
                    execution_id=context.execution_id,
                    npm_version=version_output
                )
                return
            else:
                error_output = output.decode('utf-8') if isinstance(output, bytes) else str(output)
                raise AiderExecutionError(
                    f"npm is not available in container: {error_output}",
                    project_id=context.project_id,
                    execution_id=context.execution_id,
                    exit_code=exit_code
                )
            
        except Exception as e:
            if isinstance(e, AiderExecutionError):
                raise
            raise AiderExecutionError(
                f"Failed to check npm availability: {str(e)}",
                project_id=context.project_id,
                execution_id=context.execution_id
            )
    
    def _execute_npm_ci_command(
        self,
        container,
        context: AiderExecutionContext,
        working_directory: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute npm ci command in the container.
        
        Args:
            container: Docker container instance
            context: Execution context
            working_directory: Optional working directory override
            
        Returns:
            Dictionary containing execution results
            
        Raises:
            AiderExecutionError: If command execution fails
        """
        try:
            # Determine working directory
            if working_directory:
                work_dir = working_directory
            elif context.repository_url:
                work_dir = f"{context.working_directory}/repo"
            else:
                work_dir = context.working_directory
            
            # Check if package.json exists
            package_json_check = f"cd {work_dir} && test -f package.json"
            exit_code, output = container.exec_run(package_json_check)
            
            if exit_code != 0:
                # No package.json found - this should be handled gracefully
                self.logger.warn(
                    "No package.json found, skipping npm ci",
                    correlation_id=self.correlation_id,
                    project_id=context.project_id,
                    execution_id=context.execution_id,
                    working_directory=work_dir
                )
                return {
                    'exit_code': 0,  # Success but skipped
                    'stdout': "No package.json found, npm ci skipped",
                    'stderr': "",
                    'command': f"cd {work_dir} && {self.NPM_CI_COMMAND}",
                    'skipped': True
                }
            
            # Build npm ci command
            npm_cmd = f"cd {work_dir} && {self.NPM_CI_COMMAND}"
            
            self.logger.info(
                "Executing npm ci command",
                correlation_id=self.correlation_id,
                project_id=context.project_id,
                execution_id=context.execution_id,
                status=LogStatus.IN_PROGRESS,
                working_directory=work_dir
            )
            
            # Execute npm ci command with timeout
            exit_code, output = container.exec_run(npm_cmd)
            
            # Process output
            stdout = output.decode('utf-8') if isinstance(output, bytes) else str(output)
            stderr = ""  # Docker exec_run combines stdout and stderr
            
            self.logger.info(
                "npm ci command execution completed",
                correlation_id=self.correlation_id,
                project_id=context.project_id,
                execution_id=context.execution_id,
                status=LogStatus.COMPLETED if exit_code == 0 else LogStatus.FAILED,
                exit_code=exit_code,
                output_length=len(stdout)
            )
            
            return {
                'exit_code': exit_code,
                'stdout': stdout,
                'stderr': stderr,
                'command': npm_cmd,
                'skipped': False
            }
            
        except Exception as e:
            if isinstance(e, AiderExecutionError):
                raise
            raise AiderExecutionError(
                f"npm ci command execution failed: {str(e)}",
                project_id=context.project_id,
                execution_id=context.execution_id
            )
    
    def _capture_npm_artifacts(
        self,
        container,
        context: AiderExecutionContext,
        execution_result: Dict[str, Any],
        working_directory: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Capture execution artifacts from npm ci execution.
        
        Args:
            container: Docker container instance
            context: Execution context
            execution_result: Results from npm ci execution
            working_directory: Optional working directory override
            
        Returns:
            Dictionary containing captured artifacts
        """
        artifacts = {
            'files_modified': [],
            'npm_version': None,
            'package_lock_exists': False,
            'node_modules_created': False
        }
        
        try:
            # Determine working directory
            if working_directory:
                work_dir = working_directory
            elif context.repository_url:
                work_dir = f"{context.working_directory}/repo"
            else:
                work_dir = context.working_directory
            
            # Capture npm version
            try:
                exit_code, output = container.exec_run(self.NPM_VERSION_COMMAND)
                if exit_code == 0:
                    artifacts['npm_version'] = output.decode('utf-8').strip() if isinstance(output, bytes) else str(output).strip()
            except Exception:
                pass  # Non-critical
            
            # Check if package-lock.json exists
            try:
                exit_code, output = container.exec_run(f"cd {work_dir} && test -f package-lock.json")
                artifacts['package_lock_exists'] = exit_code == 0
            except Exception:
                pass  # Non-critical
            
            # Check if node_modules was created/updated
            try:
                exit_code, output = container.exec_run(f"cd {work_dir} && test -d node_modules")
                artifacts['node_modules_created'] = exit_code == 0
            except Exception:
                pass  # Non-critical
            
            # For npm ci, the main "files modified" are typically node_modules contents
            # We'll indicate this generically rather than listing thousands of files
            if artifacts['node_modules_created'] and not execution_result.get('skipped', False):
                artifacts['files_modified'] = ['node_modules/']
            
            self.logger.info(
                "npm execution artifacts captured",
                correlation_id=self.correlation_id,
                project_id=context.project_id,
                execution_id=context.execution_id,
                npm_version=artifacts['npm_version'],
                package_lock_exists=artifacts['package_lock_exists'],
                node_modules_created=artifacts['node_modules_created']
            )
            
        except Exception as e:
            self.logger.warn(
                "Failed to capture some npm execution artifacts",
                correlation_id=self.correlation_id,
                project_id=context.project_id,
                execution_id=context.execution_id,
                error=str(e)
            )
        
        return artifacts
    
    @log_performance(get_structured_logger(__name__), "execute_npm_build")
    def execute_npm_build(
        self,
        execution_context: AiderExecutionContext,
        working_directory: Optional[str] = None,
        build_script: str = "build"
    ) -> AiderExecutionResult:
        """
        Execute npm run build command within an isolated container with retry mechanism.
        
        This method executes npm run build in the target repository to build the project
        for production. It includes retry logic with maximum 2 attempts as specified in PRD line 81.
        
        Args:
            execution_context: Context for npm build execution
            working_directory: Optional working directory override
            build_script: Build script name (default: "build")
            
        Returns:
            AiderExecutionResult containing execution artifacts and metadata
            
        Raises:
            ValidationError: If input validation fails
            AiderExecutionError: If npm build execution fails after all retries
            ContainerError: If container operations fail
        """
        return self._execute_npm_build_with_retry(execution_context, working_directory, build_script)
    
    def _execute_npm_build_with_retry(
        self,
        execution_context: AiderExecutionContext,
        working_directory: Optional[str] = None,
        build_script: str = "build",
        max_attempts: int = 2
    ) -> AiderExecutionResult:
        """
        Execute npm run build with retry mechanism (maximum 2 attempts).
        
        This method implements retry logic for npm run build operations with proper
        container cleanup between attempts. It follows the established pattern from
        Task 7.5.1 with comprehensive error handling and structured logging.
        
        Enforces PRD line 81 requirement: maximum 2 attempts for build operations.
        
        Args:
            execution_context: Context for npm build execution
            working_directory: Optional working directory override
            build_script: Build script name (default: "build")
            max_attempts: Maximum number of attempts (default: 2, maximum allowed: 2)
            
        Returns:
            AiderExecutionResult containing execution artifacts and metadata
            
        Raises:
            ValidationError: If input validation fails or retry limit exceeded
            AiderExecutionError: If npm build execution fails after all retries
            ContainerError: If container operations fail
        """
        start_time = time.time()
        last_error = None
        retry_attempts = []
        
        try:
            # Validate execution context
            self._validate_execution_context(execution_context)
            
            # Validate retry limit to enforce PRD requirement (line 81)
            self._validate_retry_limit(max_attempts, "npm build", execution_context)
            
            self.logger.info(
                "Starting npm run build execution with retry mechanism",
                correlation_id=self.correlation_id,
                project_id=execution_context.project_id,
                execution_id=execution_context.execution_id,
                status=LogStatus.STARTED,
                repository_url=execution_context.repository_url,
                working_directory=working_directory or execution_context.working_directory,
                build_script=build_script,
                max_attempts=max_attempts
            )
            
            for attempt in range(1, max_attempts + 1):
                attempt_start_time = time.time()
                
                # Enhanced retry attempt logging with comprehensive details for npm build
                self.logger.info(
                    f"npm run build execution attempt {attempt}/{max_attempts} starting",
                    correlation_id=self.correlation_id,
                    project_id=execution_context.project_id,
                    execution_id=execution_context.execution_id,
                    operation_type="npm_build",
                    attempt=attempt,
                    max_attempts=max_attempts,
                    build_script=build_script,
                    retry_strategy="exponential_backoff" if attempt > 1 else "initial_attempt",
                    working_directory=working_directory or execution_context.working_directory,
                    repository_url=execution_context.repository_url,
                    timeout_seconds=execution_context.timeout_seconds,
                    status=LogStatus.IN_PROGRESS,
                    retry_context={
                        "is_retry": attempt > 1,
                        "previous_attempts": attempt - 1,
                        "remaining_attempts": max_attempts - attempt,
                        "build_script": build_script
                    }
                )
                
                try:
                    result = self._execute_npm_build_single_attempt(
                        execution_context,
                        working_directory,
                        build_script,
                        attempt
                    )
                    
                    # Calculate attempt duration for detailed logging
                    attempt_duration = (time.time() - attempt_start_time) * 1000
                    
                    # If successful, return immediately with enhanced success logging
                    if result.success:
                        total_duration = (time.time() - start_time) * 1000
                        
                        # Update result with retry metadata
                        result.attempt_count = attempt
                        result.retry_attempts = retry_attempts
                        result.final_attempt = True
                        
                        self.logger.info(
                            f"npm run build execution succeeded on attempt {attempt}/{max_attempts}",
                            correlation_id=self.correlation_id,
                            project_id=execution_context.project_id,
                            execution_id=execution_context.execution_id,
                            operation_type="npm_build",
                            attempt=attempt,
                            max_attempts=max_attempts,
                            build_script=build_script,
                            attempt_duration_ms=round(attempt_duration, 2),
                            total_duration_ms=round(total_duration, 2),
                            exit_code=result.exit_code,
                            files_modified_count=len(result.files_modified or []),
                            container_id=result.container_id,
                            status=LogStatus.COMPLETED,
                            retry_outcome={
                                "success": True,
                                "attempts_used": attempt,
                                "attempts_saved": max_attempts - attempt,
                                "total_retry_duration_ms": round(total_duration, 2),
                                "build_script": build_script
                            }
                        )
                        return result
                    
                    # If not successful but no exception, treat as failure with detailed logging
                    failure_reason = f"npm run build failed with exit code {result.exit_code}"
                    last_error = AiderExecutionError(
                        failure_reason,
                        project_id=execution_context.project_id,
                        execution_id=execution_context.execution_id,
                        exit_code=result.exit_code
                    )
                    
                    # Record retry attempt details
                    retry_attempt_info = {
                        "attempt": attempt,
                        "start_time": datetime.utcnow().isoformat() + "Z",
                        "duration_ms": round(attempt_duration, 2),
                        "success": False,
                        "error_type": "AiderExecutionError",
                        "error_message": failure_reason,
                        "failure_reason": failure_reason,
                        "exit_code": result.exit_code,
                        "container_id": result.container_id,
                        "stdout_length": len(result.stdout_output or ""),
                        "stderr_length": len(result.stderr_output or ""),
                        "build_script": build_script
                    }
                    retry_attempts.append(retry_attempt_info)
                    
                    # Enhanced failure logging for non-exception failures
                    self.logger.warn(
                        f"npm run build execution attempt {attempt}/{max_attempts} failed with exit code",
                        correlation_id=self.correlation_id,
                        project_id=execution_context.project_id,
                        execution_id=execution_context.execution_id,
                        operation_type="npm_build",
                        attempt=attempt,
                        max_attempts=max_attempts,
                        build_script=build_script,
                        attempt_duration_ms=round(attempt_duration, 2),
                        exit_code=result.exit_code,
                        failure_reason=failure_reason,
                        stdout_length=len(result.stdout_output or ""),
                        stderr_length=len(result.stderr_output or ""),
                        container_id=result.container_id,
                        status=LogStatus.FAILED,
                        retry_context={
                            "will_retry": attempt < max_attempts,
                            "remaining_attempts": max_attempts - attempt,
                            "failure_type": "exit_code_failure",
                            "build_script": build_script
                        }
                    )
                    
                except Exception as e:
                    last_error = e
                    attempt_duration = (time.time() - attempt_start_time) * 1000
                    
                    # Record retry attempt details
                    retry_attempt_info = {
                        "attempt": attempt,
                        "start_time": datetime.utcnow().isoformat() + "Z",
                        "duration_ms": round(attempt_duration, 2),
                        "success": False,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "failure_reason": f"Exception during npm run build execution: {str(e)}",
                        "exit_code": None,
                        "container_id": None,
                        "build_script": build_script
                    }
                    retry_attempts.append(retry_attempt_info)
                    
                    # Enhanced exception failure logging with comprehensive details
                    self.logger.warn(
                        f"npm run build execution attempt {attempt}/{max_attempts} failed with exception",
                        correlation_id=self.correlation_id,
                        project_id=execution_context.project_id,
                        execution_id=execution_context.execution_id,
                        operation_type="npm_build",
                        attempt=attempt,
                        max_attempts=max_attempts,
                        build_script=build_script,
                        attempt_duration_ms=round(attempt_duration, 2),
                        error_type=type(e).__name__,
                        error_message=str(e),
                        failure_reason=f"Exception during npm run build execution: {str(e)}",
                        status=LogStatus.FAILED,
                        retry_context={
                            "will_retry": attempt < max_attempts,
                            "remaining_attempts": max_attempts - attempt,
                            "failure_type": "exception_failure",
                            "exception_class": type(e).__name__,
                            "build_script": build_script
                        }
                    )
                
                # Container cleanup after failed attempt (except for last attempt)
                if attempt < max_attempts:
                    try:
                        self._cleanup_container_after_failed_attempt(execution_context, attempt)
                    except Exception as cleanup_error:
                        self.logger.warn(
                            f"Container cleanup failed after npm build attempt {attempt}",
                            correlation_id=self.correlation_id,
                            project_id=execution_context.project_id,
                            execution_id=execution_context.execution_id,
                            operation_type="npm_build",
                            attempt=attempt,
                            build_script=build_script,
                            cleanup_error_type=type(cleanup_error).__name__,
                            cleanup_error_message=str(cleanup_error),
                            status=LogStatus.FAILED,
                            cleanup_context={
                                "operation": "npm_build",
                                "failed_attempt": attempt,
                                "max_attempts": max_attempts,
                                "build_script": build_script
                            }
                        )
            
            # All attempts failed
            total_duration = (time.time() - start_time) * 1000
            self.logger.error(
                f"npm run build execution failed after {max_attempts} attempts",
                correlation_id=self.correlation_id,
                project_id=execution_context.project_id,
                execution_id=execution_context.execution_id,
                max_attempts=max_attempts,
                build_script=build_script,
                total_duration_ms=round(total_duration, 2),
                final_error=str(last_error),
                status=LogStatus.FAILED
            )
            
            # Re-raise the last error
            if isinstance(last_error, (ValidationError, ContainerError, AiderExecutionError)):
                raise last_error
            else:
                raise AiderExecutionError(
                    f"npm run build execution failed after {max_attempts} attempts: {str(last_error)}",
                    project_id=execution_context.project_id,
                    execution_id=execution_context.execution_id
                )
                
        except (ValidationError, ContainerError, AiderExecutionError):
            # Re-raise known exceptions with additional context
            total_duration = (time.time() - start_time) * 1000
            self.logger.error(
                "npm run build execution failed due to known error",
                correlation_id=self.correlation_id,
                project_id=execution_context.project_id,
                execution_id=execution_context.execution_id,
                status=LogStatus.FAILED,
                build_script=build_script,
                total_duration_ms=round(total_duration, 2)
            )
            raise
        except Exception as e:
            total_duration = (time.time() - start_time) * 1000
            self.logger.error(
                "npm run build execution failed with unexpected error",
                correlation_id=self.correlation_id,
                project_id=execution_context.project_id,
                execution_id=execution_context.execution_id,
                status=LogStatus.FAILED,
                build_script=build_script,
                total_duration_ms=round(total_duration, 2),
                error=e
            )
            raise AiderExecutionError(
                f"npm run build execution failed: {str(e)}",
                project_id=execution_context.project_id,
                execution_id=execution_context.execution_id
            )
    
    def _execute_npm_build_single_attempt(
        self,
        execution_context: AiderExecutionContext,
        working_directory: Optional[str] = None,
        build_script: str = "build",
        attempt: int = 1
    ) -> AiderExecutionResult:
        """
        Execute a single npm run build attempt.
        
        Args:
            execution_context: Context for npm build execution
            working_directory: Optional working directory override
            build_script: Build script name (default: "build")
            attempt: Current attempt number
            
        Returns:
            AiderExecutionResult containing execution artifacts and metadata
        """
        attempt_start_time = time.time()
        
        # Initialize result object
        result = AiderExecutionResult(
            success=False,
            execution_id=execution_context.execution_id,
            project_id=execution_context.project_id,
            stdout_output="",
            stderr_output="",
            exit_code=-1,
            execution_timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
        # Step 1: Setup container
        container_setup_start = time.time()
        container_result = self._setup_container(execution_context)
        container_setup_duration = (time.time() - container_setup_start) * 1000
        
        result.container_id = container_result['container_id']
        result.container_setup_duration_ms = round(container_setup_duration, 2)
        
        # Step 2: Setup repository if specified
        if execution_context.repository_url:
            self._setup_repository(container_result['container'], execution_context)
        
        # Step 3: Verify npm is available
        self._ensure_npm_available(container_result['container'], execution_context)
        
        # Step 4: Execute npm run build
        npm_execution_start = time.time()
        execution_result = self._execute_npm_build_command(
            container_result['container'],
            execution_context,
            working_directory,
            build_script
        )
        npm_execution_end = time.time()
        npm_execution_duration = (npm_execution_end - npm_execution_start) * 1000
        
        # Record verification duration metric
        record_verification_duration(
            start_time=npm_execution_start,
            end_time=npm_execution_end,
            verification_type="npm_build",
            success=execution_result['exit_code'] == 0,
            correlation_id=self.correlation_id,
            execution_id=execution_context.execution_id,
            project_id=execution_context.project_id,
            operation_details={
                "attempt": str(attempt),
                "build_script": build_script,
                "working_directory": working_directory or execution_context.working_directory,
                "skipped": str(execution_result.get('skipped', False))
            }
        )
        
        result.aider_execution_duration_ms = round(npm_execution_duration, 2)  # Reusing field for npm duration
        result.stdout_output = execution_result['stdout']
        result.stderr_output = execution_result['stderr']
        result.exit_code = execution_result['exit_code']
        
        # Step 5: Capture artifacts
        artifact_capture_start = time.time()
        artifacts = self._capture_npm_build_artifacts(
            container_result['container'],
            execution_context,
            execution_result,
            working_directory,
            build_script
        )
        artifact_capture_duration = (time.time() - artifact_capture_start) * 1000
        
        result.artifact_capture_duration_ms = round(artifact_capture_duration, 2)
        result.files_modified = artifacts.get('files_modified', [])
        
        # Determine success (npm run build should exit with 0 for success)
        result.success = execution_result['exit_code'] == 0
        
        # Calculate total duration for this attempt
        attempt_duration = (time.time() - attempt_start_time) * 1000
        result.total_duration_ms = round(attempt_duration, 2)
        
        # Log attempt completion
        self.logger.info(
            f"npm run build attempt {attempt} completed",
            correlation_id=self.correlation_id,
            project_id=execution_context.project_id,
            execution_id=execution_context.execution_id,
            attempt=attempt,
            build_script=build_script,
            status=LogStatus.COMPLETED if result.success else LogStatus.FAILED,
            exit_code=result.exit_code,
            attempt_duration_ms=result.total_duration_ms,
            success=result.success
        )
        
        return result
    
    def _execute_npm_build_command(
        self,
        container,
        context: AiderExecutionContext,
        working_directory: Optional[str] = None,
        build_script: str = "build"
    ) -> Dict[str, Any]:
        """
        Execute npm run build command in the container.
        
        Args:
            container: Docker container instance
            context: Execution context
            working_directory: Optional working directory override
            build_script: Build script name (default: "build")
            
        Returns:
            Dictionary containing execution results
            
        Raises:
            AiderExecutionError: If command execution fails
        """
        try:
            # Determine working directory
            if working_directory:
                work_dir = working_directory
            elif context.repository_url:
                work_dir = f"{context.working_directory}/repo"
            else:
                work_dir = context.working_directory
            
            # Check if package.json exists
            package_json_check = f"cd {work_dir} && test -f package.json"
            exit_code, output = container.exec_run(package_json_check)
            
            if exit_code != 0:
                # No package.json found - this should be handled gracefully
                self.logger.warn(
                    "No package.json found, skipping npm run build",
                    correlation_id=self.correlation_id,
                    project_id=context.project_id,
                    execution_id=context.execution_id,
                    working_directory=work_dir,
                    build_script=build_script
                )
                return {
                    'exit_code': 0,  # Success but skipped
                    'stdout': f"No package.json found, npm run {build_script} skipped",
                    'stderr': "",
                    'command': f"cd {work_dir} && npm run {build_script}",
                    'skipped': True,
                    'skip_reason': 'no_package_json'
                }
            
            # Check if build script exists in package.json
            script_check = f"cd {work_dir} && node -e \"const pkg = require('./package.json'); if (!pkg.scripts || !pkg.scripts['{build_script}']) {{ process.exit(1); }}\""
            exit_code, output = container.exec_run(script_check)
            
            if exit_code != 0:
                # No build script found - this should be handled gracefully per ADD Profile B
                self.logger.warn(
                    f"No '{build_script}' script found in package.json, skipping npm run build",
                    correlation_id=self.correlation_id,
                    project_id=context.project_id,
                    execution_id=context.execution_id,
                    working_directory=work_dir,
                    build_script=build_script
                )
                return {
                    'exit_code': 0,  # Success but skipped
                    'stdout': f"No '{build_script}' script found in package.json, npm run {build_script} skipped",
                    'stderr': "",
                    'command': f"cd {work_dir} && npm run {build_script}",
                    'skipped': True,
                    'skip_reason': 'no_build_script'
                }
            
            # Build npm run build command
            npm_cmd = f"cd {work_dir} && npm run {build_script}"
            
            self.logger.info(
                "Executing npm run build command",
                correlation_id=self.correlation_id,
                project_id=context.project_id,
                execution_id=context.execution_id,
                status=LogStatus.IN_PROGRESS,
                working_directory=work_dir,
                build_script=build_script
            )
            
            # Execute npm run build command with timeout
            exit_code, output = container.exec_run(npm_cmd)
            
            # Process output
            stdout = output.decode('utf-8') if isinstance(output, bytes) else str(output)
            stderr = ""  # Docker exec_run combines stdout and stderr
            
            self.logger.info(
                "npm run build command execution completed",
                correlation_id=self.correlation_id,
                project_id=context.project_id,
                execution_id=context.execution_id,
                status=LogStatus.COMPLETED if exit_code == 0 else LogStatus.FAILED,
                exit_code=exit_code,
                output_length=len(stdout),
                build_script=build_script
            )
            
            return {
                'exit_code': exit_code,
                'stdout': stdout,
                'stderr': stderr,
                'command': npm_cmd,
                'skipped': False,
                'build_script': build_script
            }
            
        except Exception as e:
            if isinstance(e, AiderExecutionError):
                raise
            raise AiderExecutionError(
                f"npm run build command execution failed: {str(e)}",
                project_id=context.project_id,
                execution_id=context.execution_id
            )
    
    def _capture_npm_build_artifacts(
        self,
        container,
        context: AiderExecutionContext,
        execution_result: Dict[str, Any],
        working_directory: Optional[str] = None,
        build_script: str = "build"
    ) -> Dict[str, Any]:
        """
        Capture execution artifacts from npm run build execution.
        
        Args:
            container: Docker container instance
            context: Execution context
            execution_result: Results from npm run build execution
            working_directory: Optional working directory override
            build_script: Build script name used
            
        Returns:
            Dictionary containing captured artifacts
        """
        artifacts = {
            'files_modified': [],
            'npm_version': None,
            'build_script_exists': False,
            'build_output_directories': [],
            'build_script': build_script
        }
        
        try:
            # Determine working directory
            if working_directory:
                work_dir = working_directory
            elif context.repository_url:
                work_dir = f"{context.working_directory}/repo"
            else:
                work_dir = context.working_directory
            
            # Capture npm version
            try:
                exit_code, output = container.exec_run(self.NPM_VERSION_COMMAND)
                if exit_code == 0:
                    artifacts['npm_version'] = output.decode('utf-8').strip() if isinstance(output, bytes) else str(output).strip()
            except Exception:
                pass  # Non-critical
            
            # Check if build script exists (redundant but useful for artifacts)
            try:
                script_check = f"cd {work_dir} && node -e \"const pkg = require('./package.json'); if (!pkg.scripts || !pkg.scripts['{build_script}']) {{ process.exit(1); }}\""
                exit_code, output = container.exec_run(script_check)
                artifacts['build_script_exists'] = exit_code == 0
            except Exception:
                pass  # Non-critical
            
            # Detect build output directories
            build_dirs_found = []
            for build_dir in self.BUILD_OUTPUT_DIRECTORIES:
                try:
                    exit_code, output = container.exec_run(f"cd {work_dir} && test -d {build_dir}")
                    if exit_code == 0:
                        build_dirs_found.append(build_dir)
                except Exception:
                    pass  # Non-critical
            
            artifacts['build_output_directories'] = build_dirs_found
            
            # For npm run build, the main "files modified" are typically build output directories
            # We'll indicate the build directories that were created/updated
            if build_dirs_found and not execution_result.get('skipped', False):
                artifacts['files_modified'] = [f"{build_dir}/" for build_dir in build_dirs_found]
            elif not execution_result.get('skipped', False):
                # If no standard build directories found but build succeeded, indicate generic build output
                artifacts['files_modified'] = ['build_output/']
            
            self.logger.info(
                "npm build execution artifacts captured",
                correlation_id=self.correlation_id,
                project_id=context.project_id,
                execution_id=context.execution_id,
                npm_version=artifacts['npm_version'],
                build_script_exists=artifacts['build_script_exists'],
                build_output_directories=artifacts['build_output_directories'],
                build_script=build_script
            )
            
        except Exception as e:
            self.logger.warn(
                "Failed to capture some npm build execution artifacts",
                correlation_id=self.correlation_id,
                project_id=context.project_id,
                execution_id=context.execution_id,
                error=str(e),
                build_script=build_script
            )
        
        return artifacts
    
    @log_performance(get_structured_logger(__name__), "execute_git_merge")
    def execute_git_merge(
        self,
        execution_context: AiderExecutionContext,
        source_branch: str,
        target_branch: str = "main",
        working_directory: Optional[str] = None
    ) -> AiderExecutionResult:
        """
        Execute git merge command within an isolated container.
        
        This method executes git merge to merge a source branch into a target branch,
        following the Task Execution State Machine: VERIFY → MERGE → PUSH.
        It includes comprehensive conflict detection and error handling.
        
        Args:
            execution_context: Context for git merge execution
            source_branch: Source branch to merge from (e.g., "task/123-feature-branch")
            target_branch: Target branch to merge into (default: "main")
            working_directory: Optional working directory override
            
        Returns:
            AiderExecutionResult containing execution artifacts and metadata
            
        Raises:
            ValidationError: If input validation fails
            AiderExecutionError: If git merge execution fails
            ContainerError: If container operations fail
        """
        start_time = time.time()
        
        try:
            # Validate execution context
            self._validate_execution_context(execution_context)
            
            # Validate branch names
            self._validate_branch_names(source_branch, target_branch, execution_context)
            
            self.logger.info(
                "Starting git merge execution",
                correlation_id=self.correlation_id,
                project_id=execution_context.project_id,
                execution_id=execution_context.execution_id,
                status=LogStatus.STARTED,
                source_branch=source_branch,
                target_branch=target_branch,
                repository_url=execution_context.repository_url,
                working_directory=working_directory or execution_context.working_directory
            )
            
            # Initialize result object
            result = AiderExecutionResult(
                success=False,
                execution_id=execution_context.execution_id,
                project_id=execution_context.project_id,
                stdout_output="",
                stderr_output="",
                exit_code=-1,
                execution_timestamp=datetime.utcnow().isoformat() + "Z"
            )
            
            # Step 1: Setup container
            container_setup_start = time.time()
            container_result = self._setup_container(execution_context)
            container_setup_duration = (time.time() - container_setup_start) * 1000
            
            result.container_id = container_result['container_id']
            result.container_setup_duration_ms = round(container_setup_duration, 2)
            
            # Step 2: Setup repository if specified
            if execution_context.repository_url:
                self._setup_repository(container_result['container'], execution_context)
            
            # Step 3: Execute git merge
            merge_execution_start = time.time()
            execution_result = self._execute_git_merge_command(
                container_result['container'],
                execution_context,
                source_branch,
                target_branch,
                working_directory
            )
            merge_execution_end = time.time()
            merge_execution_duration = (merge_execution_end - merge_execution_start) * 1000
            
            # Record verification duration metric for git merge
            record_verification_duration(
                start_time=merge_execution_start,
                end_time=merge_execution_end,
                verification_type="git_merge",
                success=execution_result['exit_code'] == 0,
                correlation_id=self.correlation_id,
                execution_id=execution_context.execution_id,
                project_id=execution_context.project_id,
                operation_details={
                    "source_branch": source_branch,
                    "target_branch": target_branch,
                    "has_conflicts": str(execution_result.get('has_conflicts', False)),
                    "working_directory": working_directory or execution_context.working_directory
                }
            )
            
            result.aider_execution_duration_ms = round(merge_execution_duration, 2)  # Reusing field for merge duration
            result.stdout_output = execution_result['stdout']
            result.stderr_output = execution_result['stderr']
            result.exit_code = execution_result['exit_code']
            
            # Step 4: Capture artifacts
            artifact_capture_start = time.time()
            artifacts = self._capture_git_merge_artifacts(
                container_result['container'],
                execution_context,
                execution_result,
                working_directory
            )
            artifact_capture_duration = (time.time() - artifact_capture_start) * 1000
            
            result.artifact_capture_duration_ms = round(artifact_capture_duration, 2)
            result.diff_output = artifacts.get('diff_output')
            result.files_modified = artifacts.get('files_modified', [])
            result.commit_hash = artifacts.get('commit_hash')
            
            # Determine success (git merge should exit with 0 for success)
            result.success = execution_result['exit_code'] == 0
            
            # Calculate total duration
            total_duration = (time.time() - start_time) * 1000
            result.total_duration_ms = round(total_duration, 2)
            
            # Log completion
            self.logger.info(
                "Git merge execution completed",
                correlation_id=self.correlation_id,
                project_id=execution_context.project_id,
                execution_id=execution_context.execution_id,
                status=LogStatus.COMPLETED if result.success else LogStatus.FAILED,
                exit_code=result.exit_code,
                source_branch=source_branch,
                target_branch=target_branch,
                files_modified_count=len(result.files_modified or []),
                total_duration_ms=result.total_duration_ms,
                success=result.success,
                has_conflicts=execution_result.get('has_conflicts', False)
            )
            
            return result
            
        except (ValidationError, ContainerError, AiderExecutionError):
            # Re-raise known exceptions with additional context
            total_duration = (time.time() - start_time) * 1000
            self.logger.error(
                "Git merge execution failed due to known error",
                correlation_id=self.correlation_id,
                project_id=execution_context.project_id,
                execution_id=execution_context.execution_id,
                status=LogStatus.FAILED,
                source_branch=source_branch,
                target_branch=target_branch,
                total_duration_ms=round(total_duration, 2)
            )
            raise
        except Exception as e:
            total_duration = (time.time() - start_time) * 1000
            self.logger.error(
                "Git merge execution failed with unexpected error",
                correlation_id=self.correlation_id,
                project_id=execution_context.project_id,
                execution_id=execution_context.execution_id,
                status=LogStatus.FAILED,
                source_branch=source_branch,
                target_branch=target_branch,
                total_duration_ms=round(total_duration, 2),
                error=e
            )
            raise AiderExecutionError(
                f"Git merge execution failed: {str(e)}",
                project_id=execution_context.project_id,
                execution_id=execution_context.execution_id
            )
    
    def _validate_branch_names(
        self,
        source_branch: str,
        target_branch: str,
        context: AiderExecutionContext
    ) -> None:
        """
        Validate git branch names for security and format compliance.
        
        Args:
            source_branch: Source branch name to validate
            target_branch: Target branch name to validate
            context: Execution context for logging
            
        Raises:
            ValidationError: If branch names are invalid
        """
        import re
        
        # Git branch name validation pattern (simplified but secure)
        # Allows alphanumeric, hyphens, underscores, forward slashes, and dots
        branch_pattern = re.compile(r'^[a-zA-Z0-9_/-]+(?:\.[a-zA-Z0-9_/-]+)*$')
        
        validation_errors = []
        
        if not source_branch or not source_branch.strip():
            validation_errors.append({"field": "source_branch", "error": "Source branch name is required"})
        elif not branch_pattern.match(source_branch):
            validation_errors.append({"field": "source_branch", "error": "Source branch name contains invalid characters"})
        
        if not target_branch or not target_branch.strip():
            validation_errors.append({"field": "target_branch", "error": "Target branch name is required"})
        elif not branch_pattern.match(target_branch):
            validation_errors.append({"field": "target_branch", "error": "Target branch name contains invalid characters"})
        
        if source_branch == target_branch:
            validation_errors.append({"field": "branches", "error": "Source and target branches cannot be the same"})
        
        if validation_errors:
            error_message = f"Branch name validation failed: {', '.join([err['error'] for err in validation_errors])}"
            self.logger.error(
                "Branch name validation failed",
                correlation_id=self.correlation_id,
                project_id=context.project_id,
                execution_id=context.execution_id,
                source_branch=source_branch,
                target_branch=target_branch,
                validation_errors=validation_errors
            )
            raise ValidationError(error_message, field_errors=validation_errors)
        
        self.logger.debug(
            "Branch name validation passed",
            correlation_id=self.correlation_id,
            project_id=context.project_id,
            execution_id=context.execution_id,
            source_branch=source_branch,
            target_branch=target_branch
        )
    
    def _execute_git_merge_command(
        self,
        container,
        context: AiderExecutionContext,
        source_branch: str,
        target_branch: str,
        working_directory: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute git merge command in the container.
        
        Args:
            container: Docker container instance
            context: Execution context
            source_branch: Source branch to merge from
            target_branch: Target branch to merge into
            working_directory: Optional working directory override
            
        Returns:
            Dictionary containing execution results
            
        Raises:
            AiderExecutionError: If command execution fails
        """
        try:
            # Determine working directory
            if working_directory:
                work_dir = working_directory
            elif context.repository_url:
                work_dir = f"{context.working_directory}/repo"
            else:
                work_dir = context.working_directory
            
            self.logger.info(
                "Executing git merge command",
                correlation_id=self.correlation_id,
                project_id=context.project_id,
                execution_id=context.execution_id,
                status=LogStatus.IN_PROGRESS,
                source_branch=source_branch,
                target_branch=target_branch,
                working_directory=work_dir
            )
            
            # Step 1: Checkout target branch
            checkout_cmd = f"cd {work_dir} && {self.GIT_CHECKOUT_COMMAND} {target_branch}"
            exit_code, output = container.exec_run(checkout_cmd)
            
            if exit_code != 0:
                error_output = output.decode('utf-8') if isinstance(output, bytes) else str(output)
                raise AiderExecutionError(
                    f"Failed to checkout target branch '{target_branch}': {error_output}",
                    project_id=context.project_id,
                    execution_id=context.execution_id,
                    exit_code=exit_code
                )
            
            # Step 2: Execute merge command
            merge_cmd = f"cd {work_dir} && {self.GIT_MERGE_COMMAND} {source_branch}"
            exit_code, output = container.exec_run(merge_cmd)
            
            # Process output
            stdout = output.decode('utf-8') if isinstance(output, bytes) else str(output)
            stderr = ""  # Docker exec_run combines stdout and stderr
            
            # Detect merge conflicts
            has_conflicts = self._detect_merge_conflicts(stdout, exit_code)
            
            # Log merge result
            if exit_code == 0:
                self.logger.info(
                    "Git merge command completed successfully",
                    correlation_id=self.correlation_id,
                    project_id=context.project_id,
                    execution_id=context.execution_id,
                    status=LogStatus.COMPLETED,
                    exit_code=exit_code,
                    source_branch=source_branch,
                    target_branch=target_branch,
                    output_length=len(stdout)
                )
            elif has_conflicts:
                self.logger.warn(
                    "Git merge completed with conflicts",
                    correlation_id=self.correlation_id,
                    project_id=context.project_id,
                    execution_id=context.execution_id,
                    status=LogStatus.FAILED,
                    exit_code=exit_code,
                    source_branch=source_branch,
                    target_branch=target_branch,
                    conflict_detected=True,
                    output_length=len(stdout)
                )
            else:
                self.logger.error(
                    "Git merge command failed",
                    correlation_id=self.correlation_id,
                    project_id=context.project_id,
                    execution_id=context.execution_id,
                    status=LogStatus.FAILED,
                    exit_code=exit_code,
                    source_branch=source_branch,
                    target_branch=target_branch,
                    output_length=len(stdout)
                )
            
            return {
                'exit_code': exit_code,
                'stdout': stdout,
                'stderr': stderr,
                'command': merge_cmd,
                'has_conflicts': has_conflicts,
                'source_branch': source_branch,
                'target_branch': target_branch
            }
            
        except Exception as e:
            if isinstance(e, AiderExecutionError):
                raise
            raise AiderExecutionError(
                f"Git merge command execution failed: {str(e)}",
                project_id=context.project_id,
                execution_id=context.execution_id
            )
    
    def _detect_merge_conflicts(self, merge_output: str, exit_code: int) -> bool:
        """
        Detect merge conflicts from git merge output and exit code.
        
        Args:
            merge_output: Output from git merge command
            exit_code: Exit code from git merge command
            
        Returns:
            True if merge conflicts detected, False otherwise
        """
        # Git merge exit codes:
        # 0 = success (clean merge or fast-forward)
        # 1 = conflicts detected
        # Other = other errors (invalid branch, etc.)
        
        if exit_code == 1:
            return True
        
        # Also check output for conflict markers
        conflict_indicators = [
            "CONFLICT",
            "Automatic merge failed",
            "fix conflicts and then commit",
            "<<<<<<< HEAD",
            "=======",
            ">>>>>>> "
        ]
        
        merge_output_lower = merge_output.lower()
        for indicator in conflict_indicators:
            if indicator.lower() in merge_output_lower:
                return True
        
        return False
    
    def _capture_git_merge_artifacts(
        self,
        container,
        context: AiderExecutionContext,
        execution_result: Dict[str, Any],
        working_directory: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Capture execution artifacts from git merge execution.
        
        Args:
            container: Docker container instance
            context: Execution context
            execution_result: Results from git merge execution
            working_directory: Optional working directory override
            
        Returns:
            Dictionary containing captured artifacts
        """
        artifacts = {
            'diff_output': None,
            'files_modified': [],
            'commit_hash': None,
            'merge_conflicts': [],
            'source_branch': execution_result.get('source_branch'),
            'target_branch': execution_result.get('target_branch'),
            'has_conflicts': execution_result.get('has_conflicts', False)
        }
        
        try:
            # Determine working directory
            if working_directory:
                work_dir = working_directory
            elif context.repository_url:
                work_dir = f"{context.working_directory}/repo"
            else:
                work_dir = context.working_directory
            
            # Capture merge commit hash if merge was successful
            if execution_result['exit_code'] == 0:
                try:
                    commit_cmd = f"cd {work_dir} && {self.GIT_LOG_COMMAND}"
                    exit_code, output = container.exec_run(commit_cmd)
                    if exit_code == 0:
                        commit_hash = output.decode('utf-8').strip() if isinstance(output, bytes) else str(output).strip()
                        if commit_hash:
                            artifacts['commit_hash'] = commit_hash
                except Exception:
                    pass  # Non-critical
                
                # Capture diff output for successful merge
                try:
                    diff_cmd = f"cd {work_dir} && git show --name-only {artifacts['commit_hash']}"
                    exit_code, output = container.exec_run(diff_cmd)
                    if exit_code == 0:
                        diff_output = output.decode('utf-8') if isinstance(output, bytes) else str(output)
                        artifacts['diff_output'] = diff_output
                        
                        # Extract files modified from diff output
                        lines = diff_output.split('\n')
                        files_modified = []
                        for line in lines:
                            line = line.strip()
                            if line and not line.startswith('commit') and not line.startswith('Author') and not line.startswith('Date'):
                                if '/' in line or '.' in line:  # Likely a file path
                                    files_modified.append(line)
                        artifacts['files_modified'] = files_modified
                except Exception:
                    pass  # Non-critical
            
            # Capture conflict information if conflicts detected
            if artifacts['has_conflicts']:
                try:
                    status_cmd = f"cd {work_dir} && {self.GIT_STATUS_COMMAND} --porcelain"
                    exit_code, output = container.exec_run(status_cmd)
                    if exit_code == 0:
                        status_output = output.decode('utf-8') if isinstance(output, bytes) else str(output)
                        conflict_files = []
                        for line in status_output.split('\n'):
                            if line.startswith('UU ') or line.startswith('AA ') or line.startswith('DD '):
                                conflict_files.append(line[3:].strip())
                        artifacts['merge_conflicts'] = conflict_files
                except Exception:
                    pass  # Non-critical
            
            self.logger.info(
                "Git merge execution artifacts captured",
                correlation_id=self.correlation_id,
                project_id=context.project_id,
                execution_id=context.execution_id,
                files_modified_count=len(artifacts['files_modified']),
                has_diff=artifacts['diff_output'] is not None,
                has_commit_hash=artifacts['commit_hash'] is not None,
                has_conflicts=artifacts['has_conflicts'],
                conflict_files_count=len(artifacts['merge_conflicts'])
            )
            
        except Exception as e:
            self.logger.warn(
                "Failed to capture some git merge execution artifacts",
                correlation_id=self.correlation_id,
                project_id=context.project_id,
                execution_id=context.execution_id,
                error=str(e)
            )
        
        return artifacts
    
    @log_performance(get_structured_logger(__name__), "execute_git_push")
    def execute_git_push(
        self,
        execution_context: AiderExecutionContext,
        branch_name: str = "main",
        remote_name: str = "origin",
        working_directory: Optional[str] = None
    ) -> AiderExecutionResult:
        """
        Execute git push command within an isolated container.
        
        This method executes git push to push changes to a remote repository,
        following the Task Execution State Machine: VERIFY → MERGE → PUSH → UPDATE_TASKLIST.
        It includes comprehensive error handling for network, authentication, and push failures.
        
        Args:
            execution_context: Context for git push execution
            branch_name: Branch to push (default: "main")
            remote_name: Remote repository name (default: "origin")
            working_directory: Optional working directory override
            
        Returns:
            AiderExecutionResult containing execution artifacts and metadata
            
        Raises:
            ValidationError: If input validation fails
            AiderExecutionError: If git push execution fails
            ContainerError: If container operations fail
        """
        start_time = time.time()
        
        try:
            # Validate execution context
            self._validate_execution_context(execution_context)
            
            # Validate branch and remote names
            self._validate_push_parameters(branch_name, remote_name, execution_context)
            
            self.logger.info(
                "Starting git push execution",
                correlation_id=self.correlation_id,
                project_id=execution_context.project_id,
                execution_id=execution_context.execution_id,
                status=LogStatus.STARTED,
                branch_name=branch_name,
                remote_name=remote_name,
                repository_url=execution_context.repository_url,
                working_directory=working_directory or execution_context.working_directory
            )
            
            # Initialize result object
            result = AiderExecutionResult(
                success=False,
                execution_id=execution_context.execution_id,
                project_id=execution_context.project_id,
                stdout_output="",
                stderr_output="",
                exit_code=-1,
                execution_timestamp=datetime.utcnow().isoformat() + "Z"
            )
            
            # Step 1: Setup container
            container_setup_start = time.time()
            container_result = self._setup_container(execution_context)
            container_setup_duration = (time.time() - container_setup_start) * 1000
            
            result.container_id = container_result['container_id']
            result.container_setup_duration_ms = round(container_setup_duration, 2)
            
            # Step 2: Setup repository if specified
            if execution_context.repository_url:
                self._setup_repository(container_result['container'], execution_context)
            
            # Step 3: Execute git push
            push_execution_start = time.time()
            execution_result = self._execute_git_push_command(
                container_result['container'],
                execution_context,
                branch_name,
                remote_name,
                working_directory
            )
            push_execution_duration = (time.time() - push_execution_start) * 1000
            
            result.aider_execution_duration_ms = round(push_execution_duration, 2)  # Reusing field for push duration
            result.stdout_output = execution_result['stdout']
            result.stderr_output = execution_result['stderr']
            result.exit_code = execution_result['exit_code']
            
            # Step 4: Capture artifacts
            artifact_capture_start = time.time()
            artifacts = self._capture_git_push_artifacts(
                container_result['container'],
                execution_context,
                execution_result,
                working_directory
            )
            artifact_capture_duration = (time.time() - artifact_capture_start) * 1000
            
            result.artifact_capture_duration_ms = round(artifact_capture_duration, 2)
            result.commit_hash = artifacts.get('commit_hash')
            result.files_modified = artifacts.get('files_pushed', [])
            
            # Determine success (git push should exit with 0 for success)
            result.success = execution_result['exit_code'] == 0
            
            # Calculate total duration
            total_duration = (time.time() - start_time) * 1000
            result.total_duration_ms = round(total_duration, 2)
            
            # Log completion
            self.logger.info(
                "Git push execution completed",
                correlation_id=self.correlation_id,
                project_id=execution_context.project_id,
                execution_id=execution_context.execution_id,
                status=LogStatus.COMPLETED if result.success else LogStatus.FAILED,
                exit_code=result.exit_code,
                branch_name=branch_name,
                remote_name=remote_name,
                total_duration_ms=result.total_duration_ms,
                success=result.success,
                push_rejected=execution_result.get('push_rejected', False)
            )
            
            # Trigger status projection completion update after successful git push
            if result.success:
                try:
                    self._trigger_status_projection_completion(execution_context)
                except Exception as e:
                    # Log error but don't fail the git push operation
                    self.logger.warn(
                        "Failed to trigger status projection completion update",
                        correlation_id=self.correlation_id,
                        project_id=execution_context.project_id,
                        execution_id=execution_context.execution_id,
                        error=str(e),
                        error_type=type(e).__name__
                    )
            
            return result
            
        except (ValidationError, ContainerError, AiderExecutionError):
            # Re-raise known exceptions with additional context
            total_duration = (time.time() - start_time) * 1000
            self.logger.error(
                "Git push execution failed due to known error",
                correlation_id=self.correlation_id,
                project_id=execution_context.project_id,
                execution_id=execution_context.execution_id,
                status=LogStatus.FAILED,
                branch_name=branch_name,
                remote_name=remote_name,
                total_duration_ms=round(total_duration, 2)
            )
            raise
        except Exception as e:
            total_duration = (time.time() - start_time) * 1000
            self.logger.error(
                "Git push execution failed with unexpected error",
                correlation_id=self.correlation_id,
                project_id=execution_context.project_id,
                execution_id=execution_context.execution_id,
                status=LogStatus.FAILED,
                branch_name=branch_name,
                remote_name=remote_name,
                total_duration_ms=round(total_duration, 2),
                error=e
            )
            raise AiderExecutionError(
                f"Git push execution failed: {str(e)}",
                project_id=execution_context.project_id,
                execution_id=execution_context.execution_id
            )
    
    def _validate_push_parameters(
        self,
        branch_name: str,
        remote_name: str,
        context: AiderExecutionContext
    ) -> None:
        """
        Validate git push parameters for security and format compliance.
        
        Args:
            branch_name: Branch name to validate
            remote_name: Remote name to validate
            context: Execution context for logging
            
        Raises:
            ValidationError: If parameters are invalid
        """
        import re
        
        # Git branch/remote name validation pattern (simplified but secure)
        # Allows alphanumeric, hyphens, underscores, forward slashes, and dots
        name_pattern = re.compile(r'^[a-zA-Z0-9_/-]+(?:\.[a-zA-Z0-9_/-]+)*$')
        
        validation_errors = []
        
        if not branch_name or not branch_name.strip():
            validation_errors.append({"field": "branch_name", "error": "Branch name is required"})
        elif not name_pattern.match(branch_name):
            validation_errors.append({"field": "branch_name", "error": "Branch name contains invalid characters"})
        
        if not remote_name or not remote_name.strip():
            validation_errors.append({"field": "remote_name", "error": "Remote name is required"})
        elif not name_pattern.match(remote_name):
            validation_errors.append({"field": "remote_name", "error": "Remote name contains invalid characters"})
        
        if validation_errors:
            error_message = f"Push parameter validation failed: {', '.join([err['error'] for err in validation_errors])}"
            self.logger.error(
                "Push parameter validation failed",
                correlation_id=self.correlation_id,
                project_id=context.project_id,
                execution_id=context.execution_id,
                branch_name=branch_name,
                remote_name=remote_name,
                validation_errors=validation_errors
            )
            raise ValidationError(error_message, field_errors=validation_errors)
        
        self.logger.debug(
            "Push parameter validation passed",
            correlation_id=self.correlation_id,
            project_id=context.project_id,
            execution_id=context.execution_id,
            branch_name=branch_name,
            remote_name=remote_name
        )
    
    def _execute_git_push_command(
        self,
        container,
        context: AiderExecutionContext,
        branch_name: str,
        remote_name: str,
        working_directory: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute git push command in the container.
        
        Args:
            container: Docker container instance
            context: Execution context
            branch_name: Branch to push
            remote_name: Remote repository name
            working_directory: Optional working directory override
            
        Returns:
            Dictionary containing execution results
            
        Raises:
            AiderExecutionError: If command execution fails
        """
        try:
            # Determine working directory
            if working_directory:
                work_dir = working_directory
            elif context.repository_url:
                work_dir = f"{context.working_directory}/repo"
            else:
                work_dir = context.working_directory
            
            self.logger.info(
                "Executing git push command",
                correlation_id=self.correlation_id,
                project_id=context.project_id,
                execution_id=context.execution_id,
                status=LogStatus.IN_PROGRESS,
                branch_name=branch_name,
                remote_name=remote_name,
                working_directory=work_dir
            )
            
            # Build git push command
            push_cmd = f"cd {work_dir} && {self.GIT_PUSH_COMMAND} {remote_name} {branch_name}"
            
            # Execute push command
            exit_code, output = container.exec_run(push_cmd)
            
            # Process output
            stdout = output.decode('utf-8') if isinstance(output, bytes) else str(output)
            stderr = ""  # Docker exec_run combines stdout and stderr
            
            # Detect push rejection or other issues
            push_rejected = self._detect_push_rejection(stdout, exit_code)
            
            # Log push result
            if exit_code == 0:
                self.logger.info(
                    "Git push command completed successfully",
                    correlation_id=self.correlation_id,
                    project_id=context.project_id,
                    execution_id=context.execution_id,
                    status=LogStatus.COMPLETED,
                    exit_code=exit_code,
                    branch_name=branch_name,
                    remote_name=remote_name,
                    output_length=len(stdout)
                )
            elif push_rejected:
                self.logger.warn(
                    "Git push was rejected by remote",
                    correlation_id=self.correlation_id,
                    project_id=context.project_id,
                    execution_id=context.execution_id,
                    status=LogStatus.FAILED,
                    exit_code=exit_code,
                    branch_name=branch_name,
                    remote_name=remote_name,
                    push_rejected=True,
                    output_length=len(stdout)
                )
            else:
                self.logger.error(
                    "Git push command failed",
                    correlation_id=self.correlation_id,
                    project_id=context.project_id,
                    execution_id=context.execution_id,
                    status=LogStatus.FAILED,
                    exit_code=exit_code,
                    branch_name=branch_name,
                    remote_name=remote_name,
                    output_length=len(stdout)
                )
            
            return {
                'exit_code': exit_code,
                'stdout': stdout,
                'stderr': stderr,
                'command': push_cmd,
                'push_rejected': push_rejected,
                'branch_name': branch_name,
                'remote_name': remote_name
            }
            
        except Exception as e:
            if isinstance(e, AiderExecutionError):
                raise
            raise AiderExecutionError(
                f"Git push command execution failed: {str(e)}",
                project_id=context.project_id,
                execution_id=context.execution_id
            )
    
    def _detect_push_rejection(self, push_output: str, exit_code: int) -> bool:
        """
        Detect push rejection from git push output and exit code.
        
        Args:
            push_output: Output from git push command
            exit_code: Exit code from git push command
            
        Returns:
            True if push was rejected, False otherwise
        """
        # Git push exit codes:
        # 0 = success
        # 1 = generic error (could be rejection, network, auth, etc.)
        # Other = other errors
        
        if exit_code != 0:
            # Check output for rejection indicators
            rejection_indicators = [
                "rejected",
                "non-fast-forward",
                "fetch first",
                "push declined",
                "permission denied",
                "authentication failed",
                "could not read from remote repository"
            ]
            
            push_output_lower = push_output.lower()
            for indicator in rejection_indicators:
                if indicator.lower() in push_output_lower:
                    return True
        
        return False
    
    def _capture_git_push_artifacts(
        self,
        container,
        context: AiderExecutionContext,
        execution_result: Dict[str, Any],
        working_directory: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Capture execution artifacts from git push execution.
        
        Args:
            container: Docker container instance
            context: Execution context
            execution_result: Results from git push execution
            working_directory: Optional working directory override
            
        Returns:
            Dictionary containing captured artifacts
        """
        artifacts = {
            'commit_hash': None,
            'files_pushed': [],
            'branch_name': execution_result.get('branch_name'),
            'remote_name': execution_result.get('remote_name'),
            'push_rejected': execution_result.get('push_rejected', False),
            'push_successful': execution_result['exit_code'] == 0
        }
        
        try:
            # Determine working directory
            if working_directory:
                work_dir = working_directory
            elif context.repository_url:
                work_dir = f"{context.working_directory}/repo"
            else:
                work_dir = context.working_directory
            
            # Capture current commit hash if push was successful
            if execution_result['exit_code'] == 0:
                try:
                    commit_cmd = f"cd {work_dir} && {self.GIT_LOG_COMMAND}"
                    exit_code, output = container.exec_run(commit_cmd)
                    if exit_code == 0:
                        commit_hash = output.decode('utf-8').strip() if isinstance(output, bytes) else str(output).strip()
                        if commit_hash:
                            artifacts['commit_hash'] = commit_hash
                except Exception:
                    pass  # Non-critical
                
                # Capture files that were pushed (from recent commits)
                try:
                    # Get files changed in the last commit
                    files_cmd = f"cd {work_dir} && git show --name-only --format="
                    exit_code, output = container.exec_run(files_cmd)
                    if exit_code == 0:
                        files_output = output.decode('utf-8') if isinstance(output, bytes) else str(output)
                        files_pushed = []
                        for line in files_output.split('\n'):
                            line = line.strip()
                            if line and not line.startswith('commit') and not line.startswith('Author') and not line.startswith('Date'):
                                files_pushed.append(line)
                        artifacts['files_pushed'] = files_pushed
                except Exception:
                    pass  # Non-critical
            
            self.logger.info(
                "Git push execution artifacts captured",
                correlation_id=self.correlation_id,
                project_id=context.project_id,
                execution_id=context.execution_id,
                files_pushed_count=len(artifacts['files_pushed']),
                has_commit_hash=artifacts['commit_hash'] is not None,
                push_successful=artifacts['push_successful'],
                push_rejected=artifacts['push_rejected']
            )
            
        except Exception as e:
            self.logger.warn(
                "Failed to capture some git push execution artifacts",
                correlation_id=self.correlation_id,
                project_id=context.project_id,
                execution_id=context.execution_id,
                error=str(e)
            )
        
        return artifacts
    
    def _trigger_status_projection_completion(self, execution_context: AiderExecutionContext) -> None:
        """
        Trigger status projection completion update after successful git push.
        
        This method integrates with the StatusProjectionService to update the workflow
        status to completed state following the Task Execution State Machine:
        VERIFY → MERGE → PUSH → UPDATE_TASKLIST → DONE
        
        Args:
            execution_context: Context for the execution that completed
        """
        try:
            # Import here to avoid circular imports
            from services.status_projection_service import get_status_projection_service
            from database.session import db_session
            
            # Get status projection service instance with database session
            session_generator = db_session()
            session = next(session_generator)
            
            try:
                status_service = get_status_projection_service(session, self.correlation_id)
                
                # Trigger completion update
                status_service.update_status_projection_to_completed(
                    execution_id=execution_context.execution_id,
                    project_id=execution_context.project_id
                )
                
                # Commit the session
                session.commit()
                
            except Exception as session_error:
                session.rollback()
                raise session_error
            finally:
                session.close()
            
            self.logger.info(
                "Status projection completion update triggered successfully",
                correlation_id=self.correlation_id,
                project_id=execution_context.project_id,
                execution_id=execution_context.execution_id
            )
            
        except Exception as e:
            # Log error but don't re-raise to avoid breaking git push operation
            self.logger.error(
                "Failed to trigger status projection completion update",
                correlation_id=self.correlation_id,
                project_id=execution_context.project_id,
                execution_id=execution_context.execution_id,
                error=e,
                error_type=type(e).__name__
            )
            # Re-raise to be caught by the calling method
            raise


def get_aider_execution_service(correlation_id: Optional[str] = None) -> AiderExecutionService:
    """
    Factory function to get an Aider execution service instance.
    
    Args:
        correlation_id: Optional correlation ID for distributed tracing
        
    Returns:
        AiderExecutionService instance
    """
    return AiderExecutionService(correlation_id=correlation_id)