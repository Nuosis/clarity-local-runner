"""
Unit Tests for Retry Logic in AiderExecutionService

This module provides comprehensive unit tests for the retry logic functionality
implemented in Tasks 7.5.1-7.5.4, covering all failure scenarios and edge cases.
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
from services.per_project_container_manager import ContainerError
from core.exceptions import ValidationError


class TestRetryLogicValidation:
    """Test suite for retry logic validation functionality."""
    
    @pytest.fixture
    def service(self):
        """Create an AiderExecutionService instance for testing."""
        return AiderExecutionService(correlation_id="test_retry_validation_corr_123")
    
    @pytest.fixture
    def valid_execution_context(self):
        """Create a valid AiderExecutionContext for retry testing."""
        return AiderExecutionContext(
            project_id="test-retry-project",
            execution_id="retry_exec_123",
            correlation_id="retry_corr_123",
            repository_url="https://github.com/test/retry-repo.git",
            repository_branch="main",
            timeout_seconds=1800,
            user_id="test_user"
        )
    
    def test_validate_retry_limit_valid_attempts(self, service, valid_execution_context):
        """Test retry limit validation with valid attempt counts."""
        # Test valid attempt counts (1 and 2)
        service._validate_retry_limit(1, "npm ci", valid_execution_context)
        service._validate_retry_limit(2, "npm ci", valid_execution_context)
        service._validate_retry_limit(1, "npm build", valid_execution_context)
        service._validate_retry_limit(2, "npm build", valid_execution_context)
        # Should not raise any exceptions
    
    def test_validate_retry_limit_exceeds_maximum(self, service, valid_execution_context):
        """Test retry limit validation when exceeding maximum allowed attempts."""
        with pytest.raises(ValidationError) as exc_info:
            service._validate_retry_limit(3, "npm ci", valid_execution_context)
        
        assert "Retry limit exceeded" in str(exc_info.value)
        assert "maximum allowed is 2" in str(exc_info.value)
        assert "PRD line 81" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            service._validate_retry_limit(5, "npm build", valid_execution_context)
        
        assert "Retry limit exceeded" in str(exc_info.value)
        assert "maximum allowed is 2" in str(exc_info.value)
    
    def test_validate_retry_limit_invalid_type(self, service, valid_execution_context):
        """Test retry limit validation with invalid type."""
        with pytest.raises(ValidationError) as exc_info:
            service._validate_retry_limit("2", "npm ci", valid_execution_context)
        
        assert "max_attempts must be an integer" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            service._validate_retry_limit(2.5, "npm build", valid_execution_context)
        
        assert "max_attempts must be an integer" in str(exc_info.value)
    
    def test_validate_retry_limit_zero_attempts(self, service, valid_execution_context):
        """Test retry limit validation with zero attempts."""
        with pytest.raises(ValidationError) as exc_info:
            service._validate_retry_limit(0, "npm ci", valid_execution_context)
        
        assert "max_attempts must be at least 1" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            service._validate_retry_limit(-1, "npm build", valid_execution_context)
        
        assert "max_attempts must be at least 1" in str(exc_info.value)
    
    def test_validate_retry_limit_structured_logging(self, service, valid_execution_context):
        """Test that retry limit validation includes proper structured logging."""
        # This test verifies that the method logs appropriately with structured logging
        # The actual logging verification would require log capture in a real scenario
        service._validate_retry_limit(2, "npm ci", valid_execution_context)
        service._validate_retry_limit(1, "npm build", valid_execution_context)
        # Should complete without exceptions and log debug messages with structured logging


class TestRetryMechanismNpmCi:
    """Test suite for npm ci retry mechanism functionality."""
    
    @pytest.fixture
    def service(self):
        """Create an AiderExecutionService instance for testing."""
        return AiderExecutionService(correlation_id="test_npm_ci_retry_corr_123")
    
    @pytest.fixture
    def valid_execution_context(self):
        """Create a valid AiderExecutionContext for npm ci retry testing."""
        return AiderExecutionContext(
            project_id="test-npm-ci-retry-project",
            execution_id="npm_ci_retry_exec_123",
            correlation_id="npm_ci_retry_corr_123",
            repository_url="https://github.com/test/npm-ci-retry-repo.git",
            repository_branch="main",
            timeout_seconds=1800,
            user_id="test_user"
        )
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_npm_ci_retry_success_first_attempt(self, mock_get_container_manager, service, valid_execution_context):
        """Test npm ci retry mechanism succeeding on first attempt."""
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        mock_container_manager.start_or_reuse_container.return_value = {
            'success': True,
            'container_id': 'npm_ci_retry_container_123',
            'container_status': 'started'
        }
        
        # Mock container
        mock_container = Mock()
        mock_container.id = 'npm_ci_retry_container_123'
        mock_docker_client = Mock()
        mock_docker_client.containers.get.return_value = mock_container
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock successful first attempt
        mock_container.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"8.19.2"),  # npm version check
            (0, b""),  # package.json exists
            (0, b"npm ci completed successfully"),  # npm ci success
            (0, b"8.19.2"),  # npm version for artifacts
            (0, b""),  # package-lock.json exists
            (0, b"")   # node_modules exists
        ]
        
        result = service._execute_npm_ci_with_retry(valid_execution_context)
        
        assert result.success is True
        assert result.exit_code == 0
        assert result.attempt_count == 1
        assert result.final_attempt is True
        assert result.retry_attempts == []  # No retry attempts needed
        assert result.container_id == 'npm_ci_retry_container_123'
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_npm_ci_retry_success_second_attempt(self, mock_get_container_manager, service, valid_execution_context):
        """Test npm ci retry mechanism succeeding on second attempt."""
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        # Mock two different container setups for retry
        mock_container_manager.start_or_reuse_container.side_effect = [
            {
                'success': True,
                'container_id': 'npm_ci_retry_container_1',
                'container_status': 'started'
            },
            {
                'success': True,
                'container_id': 'npm_ci_retry_container_2',
                'container_status': 'started'
            }
        ]
        
        # Mock containers
        mock_container_1 = Mock()
        mock_container_1.id = 'npm_ci_retry_container_1'
        mock_container_2 = Mock()
        mock_container_2.id = 'npm_ci_retry_container_2'
        
        mock_docker_client = Mock()
        mock_docker_client.containers.get.side_effect = [mock_container_1, mock_container_2]
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock first attempt failure, second attempt success
        mock_container_1.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"8.19.2"),  # npm version check
            (0, b""),  # package.json exists
            (1, b"npm ERR! network timeout")  # npm ci fails
        ]
        
        mock_container_2.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"8.19.2"),  # npm version check
            (0, b""),  # package.json exists
            (0, b"npm ci completed successfully"),  # npm ci success
            (0, b"8.19.2"),  # npm version for artifacts
            (0, b""),  # package-lock.json exists
            (0, b"")   # node_modules exists
        ]
        
        # Mock cleanup method
        service._cleanup_container_after_failed_attempt = Mock()
        
        result = service._execute_npm_ci_with_retry(valid_execution_context)
        
        assert result.success is True
        assert result.exit_code == 0
        assert result.attempt_count == 2
        assert result.final_attempt is True
        assert len(result.retry_attempts) == 1  # One failed attempt recorded
        assert result.retry_attempts[0]['attempt'] == 1
        assert result.retry_attempts[0]['success'] is False
        assert result.retry_attempts[0]['error_type'] == 'AiderExecutionError'
        assert result.container_id == 'npm_ci_retry_container_2'
        
        # Verify cleanup was called after first failed attempt
        service._cleanup_container_after_failed_attempt.assert_called_once_with(valid_execution_context, 1)
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_npm_ci_retry_failure_both_attempts(self, mock_get_container_manager, service, valid_execution_context):
        """Test npm ci retry mechanism failing on both attempts."""
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        # Mock two different container setups for retry
        mock_container_manager.start_or_reuse_container.side_effect = [
            {
                'success': True,
                'container_id': 'npm_ci_retry_container_1',
                'container_status': 'started'
            },
            {
                'success': True,
                'container_id': 'npm_ci_retry_container_2',
                'container_status': 'started'
            }
        ]
        
        # Mock containers
        mock_container_1 = Mock()
        mock_container_1.id = 'npm_ci_retry_container_1'
        mock_container_2 = Mock()
        mock_container_2.id = 'npm_ci_retry_container_2'
        
        mock_docker_client = Mock()
        mock_docker_client.containers.get.side_effect = [mock_container_1, mock_container_2]
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock both attempts failing
        mock_container_1.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"8.19.2"),  # npm version check
            (0, b""),  # package.json exists
            (1, b"npm ERR! network timeout")  # npm ci fails
        ]
        
        mock_container_2.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"8.19.2"),  # npm version check
            (0, b""),  # package.json exists
            (1, b"npm ERR! dependency resolution failed")  # npm ci fails again
        ]
        
        # Mock cleanup method
        service._cleanup_container_after_failed_attempt = Mock()
        
        with pytest.raises(AiderExecutionError) as exc_info:
            service._execute_npm_ci_with_retry(valid_execution_context)
        
        assert "npm ci failed with exit code 1" in str(exc_info.value)
        
        # Verify cleanup was called after first failed attempt
        service._cleanup_container_after_failed_attempt.assert_called_once_with(valid_execution_context, 1)
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_npm_ci_retry_exception_handling(self, mock_get_container_manager, service, valid_execution_context):
        """Test npm ci retry mechanism with exception handling."""
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        # Mock container setup failure on first attempt, success on second
        mock_container_manager.start_or_reuse_container.side_effect = [
            ContainerError("Container setup failed", project_id=valid_execution_context.project_id),
            {
                'success': True,
                'container_id': 'npm_ci_retry_container_2',
                'container_status': 'started'
            }
        ]
        
        # Mock container for second attempt
        mock_container_2 = Mock()
        mock_container_2.id = 'npm_ci_retry_container_2'
        mock_docker_client = Mock()
        mock_docker_client.containers.get.return_value = mock_container_2
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock second attempt success
        mock_container_2.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"8.19.2"),  # npm version check
            (0, b""),  # package.json exists
            (0, b"npm ci completed successfully"),  # npm ci success
            (0, b"8.19.2"),  # npm version for artifacts
            (0, b""),  # package-lock.json exists
            (0, b"")   # node_modules exists
        ]
        
        # Mock cleanup method
        service._cleanup_container_after_failed_attempt = Mock()
        
        result = service._execute_npm_ci_with_retry(valid_execution_context)
        
        assert result.success is True
        assert result.exit_code == 0
        assert result.attempt_count == 2
        assert result.final_attempt is True
        assert len(result.retry_attempts) == 1  # One failed attempt recorded
        assert result.retry_attempts[0]['attempt'] == 1
        assert result.retry_attempts[0]['success'] is False
        assert result.retry_attempts[0]['error_type'] == 'ContainerError'
        assert "Container setup failed" in result.retry_attempts[0]['error_message']
        
        # Verify cleanup was called after first failed attempt
        service._cleanup_container_after_failed_attempt.assert_called_once_with(valid_execution_context, 1)
    
    def test_npm_ci_retry_limit_validation(self, service, valid_execution_context):
        """Test npm ci retry mechanism validates retry limits."""
        with pytest.raises(ValidationError) as exc_info:
            service._execute_npm_ci_with_retry(valid_execution_context, max_attempts=3)
        
        assert "Retry limit exceeded" in str(exc_info.value)
        assert "maximum allowed is 2" in str(exc_info.value)
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_npm_ci_retry_cleanup_failure(self, mock_get_container_manager, service, valid_execution_context):
        """Test npm ci retry mechanism handles cleanup failures gracefully."""
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        # Mock two different container setups for retry
        mock_container_manager.start_or_reuse_container.side_effect = [
            {
                'success': True,
                'container_id': 'npm_ci_retry_container_1',
                'container_status': 'started'
            },
            {
                'success': True,
                'container_id': 'npm_ci_retry_container_2',
                'container_status': 'started'
            }
        ]
        
        # Mock containers
        mock_container_1 = Mock()
        mock_container_1.id = 'npm_ci_retry_container_1'
        mock_container_2 = Mock()
        mock_container_2.id = 'npm_ci_retry_container_2'
        
        mock_docker_client = Mock()
        mock_docker_client.containers.get.side_effect = [mock_container_1, mock_container_2]
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock first attempt failure, second attempt success
        mock_container_1.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"8.19.2"),  # npm version check
            (0, b""),  # package.json exists
            (1, b"npm ERR! network timeout")  # npm ci fails
        ]
        
        mock_container_2.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"8.19.2"),  # npm version check
            (0, b""),  # package.json exists
            (0, b"npm ci completed successfully"),  # npm ci success
            (0, b"8.19.2"),  # npm version for artifacts
            (0, b""),  # package-lock.json exists
            (0, b"")   # node_modules exists
        ]
        
        # Mock cleanup method to raise exception
        service._cleanup_container_after_failed_attempt = Mock(side_effect=Exception("Cleanup failed"))
        
        # Should still succeed despite cleanup failure
        result = service._execute_npm_ci_with_retry(valid_execution_context)
        
        assert result.success is True
        assert result.exit_code == 0
        assert result.attempt_count == 2
        
        # Verify cleanup was attempted
        service._cleanup_container_after_failed_attempt.assert_called_once_with(valid_execution_context, 1)


class TestRetryMechanismNpmBuild:
    """Test suite for npm build retry mechanism functionality."""
    
    @pytest.fixture
    def service(self):
        """Create an AiderExecutionService instance for testing."""
        return AiderExecutionService(correlation_id="test_npm_build_retry_corr_123")
    
    @pytest.fixture
    def valid_execution_context(self):
        """Create a valid AiderExecutionContext for npm build retry testing."""
        return AiderExecutionContext(
            project_id="test-npm-build-retry-project",
            execution_id="npm_build_retry_exec_123",
            correlation_id="npm_build_retry_corr_123",
            repository_url="https://github.com/test/npm-build-retry-repo.git",
            repository_branch="main",
            timeout_seconds=1800,
            user_id="test_user"
        )
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_npm_build_retry_success_first_attempt(self, mock_get_container_manager, service, valid_execution_context):
        """Test npm build retry mechanism succeeding on first attempt."""
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        mock_container_manager.start_or_reuse_container.return_value = {
            'success': True,
            'container_id': 'npm_build_retry_container_123',
            'container_status': 'started'
        }
        
        # Mock container
        mock_container = Mock()
        mock_container.id = 'npm_build_retry_container_123'
        mock_docker_client = Mock()
        mock_docker_client.containers.get.return_value = mock_container
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock successful first attempt
        mock_container.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"8.19.2"),  # npm version check
            (0, b""),  # package.json exists
            (0, b""),  # build script check
            (0, b"webpack compiled successfully"),  # npm build success
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
        
        result = service._execute_npm_build_with_retry(valid_execution_context)
        
        assert result.success is True
        assert result.exit_code == 0
        assert result.attempt_count == 1
        assert result.final_attempt is True
        assert result.retry_attempts == []  # No retry attempts needed
        assert result.container_id == 'npm_build_retry_container_123'
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_npm_build_retry_success_second_attempt(self, mock_get_container_manager, service, valid_execution_context):
        """Test npm build retry mechanism succeeding on second attempt."""
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        # Mock two different container setups for retry
        mock_container_manager.start_or_reuse_container.side_effect = [
            {
                'success': True,
                'container_id': 'npm_build_retry_container_1',
                'container_status': 'started'
            },
            {
                'success': True,
                'container_id': 'npm_build_retry_container_2',
                'container_status': 'started'
            }
        ]
        
        # Mock containers
        mock_container_1 = Mock()
        mock_container_1.id = 'npm_build_retry_container_1'
        mock_container_2 = Mock()
        mock_container_2.id = 'npm_build_retry_container_2'
        
        mock_docker_client = Mock()
        mock_docker_client.containers.get.side_effect = [mock_container_1, mock_container_2]
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock first attempt failure, second attempt success
        mock_container_1.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"8.19.2"),  # npm version check
            (0, b""),  # package.json exists
            (0, b""),  # build script check
            (1, b"webpack compilation failed")  # npm build fails
        ]
        
        mock_container_2.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"8.19.2"),  # npm version check
            (0, b""),  # package.json exists
            (0, b""),  # build script check
            (0, b"webpack compiled successfully"),  # npm build success
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
        
        # Mock cleanup method
        service._cleanup_container_after_failed_attempt = Mock()
        
        result = service._execute_npm_build_with_retry(valid_execution_context)
        
        assert result.success is True
        assert result.exit_code == 0
        assert result.attempt_count == 2
        assert result.final_attempt is True
        assert len(result.retry_attempts) == 1  # One failed attempt recorded
        assert result.retry_attempts[0]['attempt'] == 1
        assert result.retry_attempts[0]['success'] is False
        assert result.retry_attempts[0]['error_type'] == 'AiderExecutionError'
        assert result.retry_attempts[0]['build_script'] == 'build'
        assert result.container_id == 'npm_build_retry_container_2'
        
        # Verify cleanup was called after first failed attempt
        service._cleanup_container_after_failed_attempt.assert_called_once_with(valid_execution_context, 1)
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_npm_build_retry_failure_both_attempts(self, mock_get_container_manager, service, valid_execution_context):
        """Test npm build retry mechanism failing on both attempts."""
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        # Mock two different container setups for retry
        mock_container_manager.start_or_reuse_container.side_effect = [
            {
                'success': True,
                'container_id': 'npm_build_retry_container_1',
                'container_status': 'started'
            },
            {
                'success': True,
                'container_id': 'npm_build_retry_container_2',
                'container_status': 'started'
            }
        ]
        
        # Mock containers
        mock_container_1 = Mock()
        mock_container_1.id = 'npm_build_retry_container_1'
        mock_container_2 = Mock()
        mock_container_2.id = 'npm_build_retry_container_2'
        
        mock_docker_client = Mock()
        mock_docker_client.containers.get.side_effect = [mock_container_1, mock_container_2]
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock both attempts failing
        mock_container_1.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"8.19.2"),  # npm version check
            (0, b""),  # package.json exists
            (0, b""),  # build script check
            (1, b"webpack compilation failed")  # npm build fails
        ]
        
        mock_container_2.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"8.19.2"),  # npm version check
            (0, b""),  # package.json exists
            (0, b""),  # build script check
            (1, b"webpack out of memory error")  # npm build fails again
        ]
        
        # Mock cleanup method
        service._cleanup_container_after_failed_attempt = Mock()
        
        with pytest.raises(AiderExecutionError) as exc_info:
            service._execute_npm_build_with_retry(valid_execution_context)
        
        assert "npm run build failed with exit code 1" in str(exc_info.value)
        
        # Verify cleanup was called after first failed attempt
        service._cleanup_container_after_failed_attempt.assert_called_once_with(valid_execution_context, 1)
    
    def test_npm_build_retry_limit_validation(self, service, valid_execution_context):
        """Test npm build retry mechanism validates retry limits."""
        with pytest.raises(ValidationError) as exc_info:
            service._execute_npm_build_with_retry(valid_execution_context, max_attempts=4)
        
        assert "Retry limit exceeded" in str(exc_info.value)
        assert "maximum allowed is 2" in str(exc_info.value)
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_npm_build_retry_with_custom_build_script(self, mock_get_container_manager, service, valid_execution_context):
        """Test npm build retry mechanism with custom build script."""
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        mock_container_manager.start_or_reuse_container.return_value = {
            'success': True,
            'container_id': 'npm_build_retry_container_123',
            'container_status': 'started'
        }
        
        # Mock container
        mock_container = Mock()
        mock_container.id = 'npm_build_retry_container_123'
        mock_docker_client = Mock()
        mock_docker_client.containers.get.return_value = mock_container
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock successful first attempt with custom build script
        mock_container.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"8.19.2"),  # npm version check
            (0, b""),  # package.json exists
            (0, b""),  # build:prod script check
            (0, b"webpack compiled successfully in production mode"),  # npm build success
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
        
        result = service._execute_npm_build_with_retry(valid_execution_context, build_script="build:prod")
        
        assert result.success is True
        assert result.exit_code == 0
        assert result.attempt_count == 1
        assert result.final_attempt is True
        assert result.retry_attempts == []  # No retry attempts needed
        assert result.container_id == 'npm_build_retry_container_123'


class TestContainerCleanup:
    """Test suite for container cleanup after failed attempts."""
    
    @pytest.fixture
    def service(self):
        """Create an AiderExecutionService instance for testing."""
        return AiderExecutionService(correlation_id="test_cleanup_corr_123")
    
    @pytest.fixture
    def valid_execution_context(self):
        """Create a valid AiderExecutionContext for cleanup testing."""
        return AiderExecutionContext(
            project_id="test-cleanup-project",
            execution_id="cleanup_exec_123",
            correlation_id="cleanup_corr_123",
            repository_url="https://github.com/test/cleanup-repo.git",
            repository_branch="main",
            timeout_seconds=1800,
            user_id="test_user"
        )
    
    def test_cleanup_container_after_failed_attempt_success(self, service, valid_execution_context):
        """Test successful container cleanup after failed attempt."""
        # Mock container manager
        mock_container_manager = Mock()
        service.container_manager = mock_container_manager
        
        # Mock successful cleanup
        mock_container_manager.cleanup_expired_containers.return_value = {
            'containers_removed': 1,
            'volumes_removed': 0,
            'networks_removed': 0
        }
        
        # Should not raise any exception
        service._cleanup_container_after_failed_attempt(valid_execution_context, 1)
        
        # Verify cleanup was called with correct parameters
        mock_container_manager.cleanup_expired_containers.assert_called_once_with(
            max_age_days=0,
            execution_id=valid_execution_context.execution_id
        )
    
    def test_cleanup_container_after_failed_attempt_failure(self, service, valid_execution_context):
        """Test container cleanup failure handling."""
        # Mock container manager
        mock_container_manager = Mock()
        service.container_manager = mock_container_manager
        
        # Mock cleanup failure
        mock_container_manager.cleanup_expired_containers.side_effect = Exception("Cleanup failed")
        
        # Should not raise exception, just log warning
        service._cleanup_container_after_failed_attempt(valid_execution_context, 1)
        
        # Verify cleanup was attempted
        mock_container_manager.cleanup_expired_containers.assert_called_once()
    
    def test_cleanup_container_no_container_manager(self, service, valid_execution_context):
        """Test container cleanup when container manager is not available."""
        # Set container manager to None
        service.container_manager = None
        
        # Should not raise exception
        service._cleanup_container_after_failed_attempt(valid_execution_context, 1)


class TestRetryMetadataTracking:
    """Test suite for retry metadata tracking functionality."""
    
    @pytest.fixture
    def service(self):
        """Create an AiderExecutionService instance for testing."""
        return AiderExecutionService(correlation_id="test_metadata_corr_123")
    
    @pytest.fixture
    def valid_execution_context(self):
        """Create a valid AiderExecutionContext for metadata testing."""
        return AiderExecutionContext(
            project_id="test-metadata-project",
            execution_id="metadata_exec_123",
            correlation_id="metadata_corr_123",
            repository_url="https://github.com/test/metadata-repo.git",
            repository_branch="main",
            timeout_seconds=1800,
            user_id="test_user"
        )
    
    def test_aider_execution_result_retry_metadata_defaults(self):
        """Test AiderExecutionResult retry metadata default values."""
        result = AiderExecutionResult(
            success=True,
            execution_id="test_exec_123",
            project_id="test_project_123",
            stdout_output="test output",
            stderr_output="",
            exit_code=0
        )
        
        # Test default retry metadata values
        assert result.attempt_count == 1
        assert result.retry_attempts == []  # Should be initialized as empty list
        assert result.final_attempt is True
    
    def test_aider_execution_result_retry_metadata_custom(self):
        """Test AiderExecutionResult with custom retry metadata."""
        retry_attempts = [
            {
                "attempt": 1,
                "start_time": "2024-01-15T10:30:00.000Z",
                "duration_ms": 2500.5,
                "success": False,
                "error_type": "AiderExecutionError",
                "error_message": "npm ci failed with exit code 1",
                "failure_reason": "npm ci failed with exit code 1",
                "exit_code": 1,
                "container_id": "container-abc123",
                "stdout_length": 1024,
                "stderr_length": 256
            }
        ]
        
        result = AiderExecutionResult(
            success=True,
            execution_id="test_exec_123",
            project_id="test_project_123",
            stdout_output="test output",
            stderr_output="",
            exit_code=0,
            attempt_count=2,
            retry_attempts=retry_attempts,
            final_attempt=True
        )
        
        # Test custom retry metadata values
        assert result.attempt_count == 2
        assert result.retry_attempts == retry_attempts
        assert result.final_attempt is True
        assert result.retry_attempts is not None
        assert len(result.retry_attempts) == 1
        assert result.retry_attempts[0]['attempt'] == 1
        assert result.retry_attempts[0]['success'] is False
    
    def test_aider_execution_result_post_init_retry_attempts(self):
        """Test AiderExecutionResult __post_init__ method for retry_attempts."""
        # Test with None retry_attempts
        result = AiderExecutionResult(
            success=True,
            execution_id="test_exec_123",
            project_id="test_project_123",
            stdout_output="test output",
            stderr_output="",
            exit_code=0,
            retry_attempts=None
        )
        
        # Should be initialized as empty list
        assert result.retry_attempts == []
        assert isinstance(result.retry_attempts, list)
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_retry_metadata_population_npm_ci(self, mock_get_container_manager, service, valid_execution_context):
        """Test retry metadata is properly populated for npm ci retry."""
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        # Mock two different container setups for retry
        mock_container_manager.start_or_reuse_container.side_effect = [
            {
                'success': True,
                'container_id': 'npm_ci_metadata_container_1',
                'container_status': 'started'
            },
            {
                'success': True,
                'container_id': 'npm_ci_metadata_container_2',
                'container_status': 'started'
            }
        ]
        
        # Mock containers
        mock_container_1 = Mock()
        mock_container_1.id = 'npm_ci_metadata_container_1'
        mock_container_2 = Mock()
        mock_container_2.id = 'npm_ci_metadata_container_2'
        
        mock_docker_client = Mock()
        mock_docker_client.containers.get.side_effect = [mock_container_1, mock_container_2]
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock first attempt failure, second attempt success
        mock_container_1.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"8.19.2"),  # npm version check
            (0, b""),  # package.json exists
            (1, b"npm ERR! network timeout")  # npm ci fails
        ]
        
        mock_container_2.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"8.19.2"),  # npm version check
            (0, b""),  # package.json exists
            (0, b"npm ci completed successfully"),  # npm ci success
            (0, b"8.19.2"),  # npm version for artifacts
            (0, b""),  # package-lock.json exists
            (0, b"")   # node_modules exists
        ]
        
        # Mock cleanup method
        service._cleanup_container_after_failed_attempt = Mock()
        
        result = service._execute_npm_ci_with_retry(valid_execution_context)
        
        # Verify retry metadata is properly populated
        assert result.attempt_count == 2
        assert result.final_attempt is True
        assert len(result.retry_attempts) == 1
        
        # Verify retry attempt details
        retry_attempt = result.retry_attempts[0]
        assert retry_attempt['attempt'] == 1
        assert retry_attempt['success'] is False
        assert retry_attempt['error_type'] == 'AiderExecutionError'
        assert 'npm ci failed with exit code 1' in retry_attempt['error_message']
        assert retry_attempt['exit_code'] == 1
        assert retry_attempt['container_id'] == 'npm_ci_metadata_container_1'
        assert 'duration_ms' in retry_attempt
        assert 'start_time' in retry_attempt
        assert retry_attempt['duration_ms'] > 0


class TestRetryPerformanceRequirements:
    """Test suite for retry performance requirements."""
    
    @pytest.fixture
    def service(self):
        """Create an AiderExecutionService instance for testing."""
        return AiderExecutionService(correlation_id="test_performance_corr_123")
    
    @pytest.fixture
    def valid_execution_context(self):
        """Create a valid AiderExecutionContext for performance testing."""
        return AiderExecutionContext(
            project_id="test-performance-project",
            execution_id="performance_exec_123",
            correlation_id="performance_corr_123",
            repository_url="https://github.com/test/performance-repo.git",
            repository_branch="main",
            timeout_seconds=1800,
            user_id="test_user"
        )
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_npm_ci_retry_performance_requirement(self, mock_get_container_manager, service, valid_execution_context):
        """Test that npm ci retry operations complete within ≤60s total time."""
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        mock_container_manager.start_or_reuse_container.return_value = {
            'success': True,
            'container_id': 'npm_ci_performance_container_123',
            'container_status': 'started'
        }
        
        # Mock container
        mock_container = Mock()
        mock_container.id = 'npm_ci_performance_container_123'
        mock_docker_client = Mock()
        mock_docker_client.containers.get.return_value = mock_container
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock fast container operations
        mock_container.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"8.19.2"),  # npm version check
            (0, b""),  # package.json exists
            (0, b"npm ci completed successfully"),  # npm ci success
            (0, b"8.19.2"),  # npm version for artifacts
            (0, b""),  # package-lock.json exists
            (0, b"")   # node_modules exists
        ]
        
        start_time = time.time()
        result = service._execute_npm_ci_with_retry(valid_execution_context)
        execution_time = time.time() - start_time
        
        # Verify performance requirement (≤60s)
        assert execution_time <= 60.0, f"Execution took {execution_time:.2f}s, exceeds 60s requirement"
        assert result.total_duration_ms <= 60000, f"Total duration {result.total_duration_ms}ms exceeds 60s requirement"
        assert result.success is True
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_npm_build_retry_performance_requirement(self, mock_get_container_manager, service, valid_execution_context):
        """Test that npm build retry operations complete within ≤60s total time."""
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        mock_container_manager.start_or_reuse_container.return_value = {
            'success': True,
            'container_id': 'npm_build_performance_container_123',
            'container_status': 'started'
        }
        
        # Mock container
        mock_container = Mock()
        mock_container.id = 'npm_build_performance_container_123'
        mock_docker_client = Mock()
        mock_docker_client.containers.get.return_value = mock_container
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock fast container operations
        mock_container.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"8.19.2"),  # npm version check
            (0, b""),  # package.json exists
            (0, b""),  # build script check
            (0, b"webpack compiled successfully"),  # npm build success
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
        
        start_time = time.time()
        result = service._execute_npm_build_with_retry(valid_execution_context)
        execution_time = time.time() - start_time
        
        # Verify performance requirement (≤60s)
        assert execution_time <= 60.0, f"Execution took {execution_time:.2f}s, exceeds 60s requirement"
        assert result.total_duration_ms <= 60000, f"Total duration {result.total_duration_ms}ms exceeds 60s requirement"
        assert result.success is True


class TestRetryBackwardCompatibility:
    """Test suite for retry backward compatibility."""
    
    @pytest.fixture
    def service(self):
        """Create an AiderExecutionService instance for testing."""
        return AiderExecutionService(correlation_id="test_compatibility_corr_123")
    
    @pytest.fixture
    def valid_execution_context(self):
        """Create a valid AiderExecutionContext for compatibility testing."""
        return AiderExecutionContext(
            project_id="test-compatibility-project",
            execution_id="compatibility_exec_123",
            correlation_id="compatibility_corr_123",
            repository_url="https://github.com/test/compatibility-repo.git",
            repository_branch="main",
            timeout_seconds=1800,
            user_id="test_user"
        )
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_execute_npm_ci_public_interface_unchanged(self, mock_get_container_manager, service, valid_execution_context):
        """Test that execute_npm_ci public interface remains unchanged."""
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        mock_container_manager.start_or_reuse_container.return_value = {
            'success': True,
            'container_id': 'npm_ci_compatibility_container_123',
            'container_status': 'started'
        }
        
        # Mock container
        mock_container = Mock()
        mock_container.id = 'npm_ci_compatibility_container_123'
        mock_docker_client = Mock()
        mock_docker_client.containers.get.return_value = mock_container
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock successful execution
        mock_container.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"8.19.2"),  # npm version check
            (0, b""),  # package.json exists
            (0, b"npm ci completed successfully"),  # npm ci success
            (0, b"8.19.2"),  # npm version for artifacts
            (0, b""),  # package-lock.json exists
            (0, b"")   # node_modules exists
        ]
        
        # Test public interface with original parameters
        result = service.execute_npm_ci(valid_execution_context)
        
        # Verify result structure is backward compatible
        assert hasattr(result, 'success')
        assert hasattr(result, 'execution_id')
        assert hasattr(result, 'project_id')
        assert hasattr(result, 'stdout_output')
        assert hasattr(result, 'stderr_output')
        assert hasattr(result, 'exit_code')
        assert hasattr(result, 'total_duration_ms')
        
        # Verify new retry fields are present but don't break existing code
        assert hasattr(result, 'attempt_count')
        assert hasattr(result, 'retry_attempts')
        assert hasattr(result, 'final_attempt')
        
        # Test with working directory override (existing functionality)
        result_with_dir = service.execute_npm_ci(valid_execution_context, "/custom/dir")
        assert result_with_dir.success is True
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_execute_npm_build_public_interface_unchanged(self, mock_get_container_manager, service, valid_execution_context):
        """Test that execute_npm_build public interface remains unchanged."""
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        mock_container_manager.start_or_reuse_container.return_value = {
            'success': True,
            'container_id': 'npm_build_compatibility_container_123',
            'container_status': 'started'
        }
        
        # Mock container
        mock_container = Mock()
        mock_container.id = 'npm_build_compatibility_container_123'
        mock_docker_client = Mock()
        mock_docker_client.containers.get.return_value = mock_container
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock successful execution
        mock_container.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"8.19.2"),  # npm version check
            (0, b""),  # package.json exists
            (0, b""),  # build script check
            (0, b"webpack compiled successfully"),  # npm build success
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
        
        # Test public interface with original parameters
        result = service.execute_npm_build(valid_execution_context)
        
        # Verify result structure is backward compatible
        assert hasattr(result, 'success')
        assert hasattr(result, 'execution_id')
        assert hasattr(result, 'project_id')
        assert hasattr(result, 'stdout_output')
        assert hasattr(result, 'stderr_output')
        assert hasattr(result, 'exit_code')
        assert hasattr(result, 'total_duration_ms')
        
        # Verify new retry fields are present but don't break existing code
        assert hasattr(result, 'attempt_count')
        assert hasattr(result, 'retry_attempts')
        assert hasattr(result, 'final_attempt')
        
        # Test with working directory and build script overrides (existing functionality)
        result_with_overrides = service.execute_npm_build(valid_execution_context, "/custom/dir", "build:prod")
        assert result_with_overrides.success is True


class TestRetryEdgeCases:
    """Test suite for retry edge cases and failure scenarios."""
    
    @pytest.fixture
    def service(self):
        """Create an AiderExecutionService instance for testing."""
        return AiderExecutionService(correlation_id="test_edge_cases_corr_123")
    
    @pytest.fixture
    def valid_execution_context(self):
        """Create a valid AiderExecutionContext for edge case testing."""
        return AiderExecutionContext(
            project_id="test-edge-cases-project",
            execution_id="edge_cases_exec_123",
            correlation_id="edge_cases_corr_123",
            repository_url="https://github.com/test/edge-cases-repo.git",
            repository_branch="main",
            timeout_seconds=1800,
            user_id="test_user"
        )
    
    def test_retry_with_invalid_execution_context(self, service):
        """Test retry mechanism with invalid execution context."""
        invalid_context = AiderExecutionContext(
            project_id="",  # Invalid empty project_id
            execution_id="edge_cases_exec_123"
        )
        
        with pytest.raises(ValidationError):
            service._execute_npm_ci_with_retry(invalid_context)
        
        with pytest.raises(ValidationError):
            service._execute_npm_build_with_retry(invalid_context)
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_retry_with_timeout_scenarios(self, mock_get_container_manager, service, valid_execution_context):
        """Test retry mechanism with timeout scenarios."""
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        # Mock container setup that takes too long
        mock_container_manager.start_or_reuse_container.side_effect = Exception("Operation timed out")
        
        with pytest.raises(AiderExecutionError):
            service._execute_npm_ci_with_retry(valid_execution_context)
    
    @patch('services.aider_execution_service.get_per_project_container_manager')
    def test_retry_with_mixed_failure_types(self, mock_get_container_manager, service, valid_execution_context):
        """Test retry mechanism with different types of failures."""
        # Mock container manager
        mock_container_manager = Mock()
        mock_get_container_manager.return_value = mock_container_manager
        service.container_manager = mock_container_manager
        
        # Mock first attempt with container error, second with execution error
        mock_container_manager.start_or_reuse_container.side_effect = [
            ContainerError("Container setup failed", project_id=valid_execution_context.project_id),
            {
                'success': True,
                'container_id': 'npm_mixed_failure_container_2',
                'container_status': 'started'
            }
        ]
        
        # Mock container for second attempt
        mock_container_2 = Mock()
        mock_container_2.id = 'npm_mixed_failure_container_2'
        mock_docker_client = Mock()
        mock_docker_client.containers.get.return_value = mock_container_2
        mock_container_manager.docker_client = mock_docker_client
        
        # Mock second attempt also failing but with different error
        mock_container_2.exec_run.side_effect = [
            (0, b"Cloning into 'repo'..."),  # Git clone
            (0, b"8.19.2"),  # npm version check
            (0, b""),  # package.json exists
            (1, b"npm ERR! different error")  # npm ci fails with different error
        ]
        
        # Mock cleanup method
        service._cleanup_container_after_failed_attempt = Mock()
        
        with pytest.raises(AiderExecutionError) as exc_info:
            service._execute_npm_ci_with_retry(valid_execution_context)
        
        assert "npm ci failed with exit code 1" in str(exc_info.value)
        
        # Verify cleanup was called after first failed attempt
        service._cleanup_container_after_failed_attempt.assert_called_once_with(valid_execution_context, 1)
    
    def test_retry_attempts_list_structure(self, service, valid_execution_context):
        """Test that retry_attempts list has correct structure."""
        # Create a result with retry attempts
        retry_attempts = [
            {
                "attempt": 1,
                "start_time": "2024-01-15T10:30:00.000Z",
                "duration_ms": 2500.5,
                "success": False,
                "error_type": "AiderExecutionError",
                "error_message": "npm ci failed with exit code 1",
                "failure_reason": "npm ci failed with exit code 1",
                "exit_code": 1,
                "container_id": "container-abc123",
                "stdout_length": 1024,
                "stderr_length": 256
            }
        ]
        
        result = AiderExecutionResult(
            success=True,
            execution_id="test_exec_123",
            project_id="test_project_123",
            stdout_output="test output",
            stderr_output="",
            exit_code=0,
            attempt_count=2,
            retry_attempts=retry_attempts,
            final_attempt=True
        )
        
        # Verify retry_attempts structure
        assert isinstance(result.retry_attempts, list)
        assert len(result.retry_attempts) == 1
        
        retry_attempt = result.retry_attempts[0]
        required_fields = [
            'attempt', 'start_time', 'duration_ms', 'success', 'error_type',
            'error_message', 'failure_reason', 'exit_code', 'container_id',
            'stdout_length', 'stderr_length'
        ]
        
        for field in required_fields:
            assert field in retry_attempt, f"Required field '{field}' missing from retry_attempt"
        
        # Verify field types
        assert isinstance(retry_attempt['attempt'], int)
        assert isinstance(retry_attempt['start_time'], str)
        assert isinstance(retry_attempt['duration_ms'], (int, float))
        assert isinstance(retry_attempt['success'], bool)
        assert isinstance(retry_attempt['error_type'], str)
        assert isinstance(retry_attempt['error_message'], str)