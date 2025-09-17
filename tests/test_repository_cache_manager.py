"""
Unit tests for Repository Cache Manager

This test suite provides comprehensive coverage for the RepositoryCacheManager
including directory operations, security validation, cleanup policies, and
integration with structured logging and error handling.
"""

import os
import shutil
import stat
import subprocess
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from services.repository_cache_manager import RepositoryCacheManager, get_repository_cache_manager
from core.exceptions import RepositoryError
from core.structured_logging import LogStatus


class TestRepositoryCacheManager:
    """Test suite for RepositoryCacheManager functionality."""
    
    @pytest.fixture
    def temp_cache_root(self):
        """Create a temporary directory for cache testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        # Cleanup
        if Path(temp_dir).exists():
            shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def cache_manager(self, temp_cache_root):
        """Create a cache manager with temporary cache root."""
        with patch.object(RepositoryCacheManager, 'CACHE_ROOT', temp_cache_root):
            return RepositoryCacheManager(correlation_id="test_correlation_123")
    
    @pytest.fixture
    def mock_logger(self):
        """Mock structured logger for testing."""
        return Mock()
    
    def test_initialization(self):
        """Test RepositoryCacheManager initialization."""
        correlation_id = "test_init_123"
        manager = RepositoryCacheManager(correlation_id=correlation_id)
        
        assert manager.correlation_id == correlation_id
        assert manager.logger is not None
        assert manager.CACHE_ROOT == Path("/workspace/repos")
        assert manager.CLEANUP_AGE_HOURS == 24
        assert manager.DEFAULT_DIR_PERMISSIONS == 0o755
    
    def test_initialization_without_correlation_id(self):
        """Test initialization without correlation ID."""
        manager = RepositoryCacheManager()
        
        assert manager.correlation_id is None
        assert manager.logger is not None
    
    def test_factory_function(self):
        """Test get_repository_cache_manager factory function."""
        correlation_id = "factory_test_456"
        manager = get_repository_cache_manager(correlation_id=correlation_id)
        
        assert isinstance(manager, RepositoryCacheManager)
        assert manager.correlation_id == correlation_id
    
    def test_validate_repository_url_valid_urls(self, cache_manager):
        """Test URL validation with valid repository URLs."""
        valid_urls = [
            "https://github.com/user/repo.git",
            "http://gitlab.com/user/repo",
            "git@github.com:user/repo.git",
            "ssh://git@bitbucket.org/user/repo.git"
        ]
        
        for url in valid_urls:
            # Should not raise any exception
            cache_manager._validate_repository_url(url)
    
    def test_validate_repository_url_invalid_urls(self, cache_manager):
        """Test URL validation with invalid repository URLs."""
        invalid_urls = [
            "",  # Empty string
            None,  # None value
            "ftp://example.com/repo",  # Invalid scheme
            "https://github.com/../../../etc/passwd",  # Path traversal
            "https://github.com/user/repo?token=secret",  # Query params are OK
            "https://github.com/user/repo\x00",  # Control character
        ]
        
        for url in invalid_urls:
            with pytest.raises(RepositoryError):
                cache_manager._validate_repository_url(url)
    
    def test_generate_cache_key(self, cache_manager):
        """Test cache key generation."""
        test_cases = [
            ("https://github.com/user/repo.git", "repo"),
            ("https://gitlab.com/group/project", "project"),
            ("git@github.com:user/my-awesome-repo.git", "my-awesome-repo"),
            ("https://github.com/user/repo-with-special-chars!@#.git", "repo-with-special-chars___"),
        ]
        
        for url, expected_prefix in test_cases:
            cache_key = cache_manager._generate_cache_key(url)
            
            # Should start with sanitized repo name
            assert cache_key.startswith(expected_prefix)
            # Should end with hash
            assert "_" in cache_key
            # Should be filesystem safe
            assert all(c.isalnum() or c in "_-" for c in cache_key)
            # Should be reasonable length
            assert len(cache_key) <= 62  # 50 + 1 + 12 - 1
    
    def test_generate_cache_key_consistency(self, cache_manager):
        """Test that cache key generation is consistent."""
        url = "https://github.com/user/repo.git"
        
        key1 = cache_manager._generate_cache_key(url)
        key2 = cache_manager._generate_cache_key(url)
        
        assert key1 == key2
    
    def test_generate_cache_key_uniqueness(self, cache_manager):
        """Test that different URLs generate different cache keys."""
        url1 = "https://github.com/user/repo1.git"
        url2 = "https://github.com/user/repo2.git"
        
        key1 = cache_manager._generate_cache_key(url1)
        key2 = cache_manager._generate_cache_key(url2)
        
        assert key1 != key2
    
    @patch('services.repository_cache_manager.os.chmod')
    def test_create_cache_directory_success(self, mock_chmod, cache_manager, temp_cache_root):
        """Test successful cache directory creation."""
        repository_url = "https://github.com/user/repo.git"
        project_id = "test_project_123"
        execution_id = "test_execution_456"
        
        with patch.object(cache_manager.logger, 'info') as mock_log_info:
            cache_path = cache_manager.create_cache_directory(
                repository_url=repository_url,
                project_id=project_id,
                execution_id=execution_id
            )
            
            # Verify directory was created
            assert cache_path.exists()
            assert cache_path.is_dir()
            assert cache_path.parent == temp_cache_root
            
            # Verify permissions were set
            mock_chmod.assert_called_with(cache_path, cache_manager.DEFAULT_DIR_PERMISSIONS)
            
            # Verify logging
            assert mock_log_info.call_count >= 2  # Started and completed logs
            
            # Check log calls contain expected information
            log_calls = mock_log_info.call_args_list
            start_call = log_calls[0]
            assert "Creating repository cache directory" in start_call[0][0]
            assert start_call[1]['status'] == LogStatus.STARTED
            assert start_call[1]['repository_url'] == repository_url
            assert start_call[1]['project_id'] == project_id
            assert start_call[1]['execution_id'] == execution_id
    
    def test_create_cache_directory_already_exists(self, cache_manager, temp_cache_root):
        """Test cache directory creation when directory already exists."""
        repository_url = "https://github.com/user/repo.git"
        
        # Create directory first time
        cache_path1 = cache_manager.create_cache_directory(repository_url)
        
        with patch.object(cache_manager.logger, 'info') as mock_log_info:
            # Create same directory again
            cache_path2 = cache_manager.create_cache_directory(repository_url)
            
            assert cache_path1 == cache_path2
            assert cache_path2.exists()
            
            # Should log that directory already exists
            log_calls = mock_log_info.call_args_list
            skipped_call = next((call for call in log_calls 
                               if call[1].get('status') == LogStatus.SKIPPED), None)
            assert skipped_call is not None
            assert "already exists" in skipped_call[0][0]
    
    def test_create_cache_directory_invalid_url(self, cache_manager):
        """Test cache directory creation with invalid URL."""
        invalid_url = "ftp://invalid.com/repo"
        
        with pytest.raises(RepositoryError) as exc_info:
            cache_manager.create_cache_directory(invalid_url)
        
        assert "Unsupported URL scheme" in str(exc_info.value)
        assert exc_info.value.repository_url == invalid_url
    
    @patch('services.repository_cache_manager.os.chmod')
    def test_create_cache_directory_permission_error(self, mock_chmod, cache_manager):
        """Test cache directory creation with permission error."""
        mock_chmod.side_effect = PermissionError("Permission denied")
        repository_url = "https://github.com/user/repo.git"
        
        with patch.object(cache_manager.logger, 'error') as mock_log_error:
            with pytest.raises(RepositoryError) as exc_info:
                cache_manager.create_cache_directory(repository_url)
            
            assert "Failed to create cache directory" in str(exc_info.value)
            assert exc_info.value.repository_url == repository_url
            
            # Verify error logging
            mock_log_error.assert_called_once()
            error_call = mock_log_error.call_args
            assert error_call[1]['status'] == LogStatus.FAILED
            assert error_call[1]['repository_url'] == repository_url
    
    def test_get_cache_directory_exists(self, cache_manager):
        """Test getting cache directory that exists."""
        repository_url = "https://github.com/user/repo.git"
        
        # Create directory first
        created_path = cache_manager.create_cache_directory(repository_url)
        
        # Get directory
        retrieved_path = cache_manager.get_cache_directory(repository_url)
        
        assert retrieved_path == created_path
        assert retrieved_path.exists()
    
    def test_get_cache_directory_not_exists(self, cache_manager):
        """Test getting cache directory that doesn't exist."""
        repository_url = "https://github.com/user/nonexistent.git"
        
        retrieved_path = cache_manager.get_cache_directory(repository_url)
        
        assert retrieved_path is None
    
    def test_get_cache_directory_invalid_url(self, cache_manager):
        """Test getting cache directory with invalid URL."""
        invalid_url = "ftp://invalid.com/repo"
        
        with pytest.raises(RepositoryError):
            cache_manager.get_cache_directory(invalid_url)
    
    def test_directory_exists_true(self, cache_manager):
        """Test directory_exists returns True for existing directory."""
        repository_url = "https://github.com/user/repo.git"
        
        # Create directory
        cache_manager.create_cache_directory(repository_url)
        
        # Check existence
        assert cache_manager.directory_exists(repository_url) is True
    
    def test_directory_exists_false(self, cache_manager):
        """Test directory_exists returns False for non-existing directory."""
        repository_url = "https://github.com/user/nonexistent.git"
        
        assert cache_manager.directory_exists(repository_url) is False
    
    def test_directory_exists_invalid_url(self, cache_manager):
        """Test directory_exists returns False for invalid URL."""
        invalid_url = "ftp://invalid.com/repo"
        
        assert cache_manager.directory_exists(invalid_url) is False
    
    def test_get_directory_size(self, cache_manager, temp_cache_root):
        """Test directory size calculation."""
        # Create test directory with files
        test_dir = temp_cache_root / "test_size"
        test_dir.mkdir()
        
        # Create files with known sizes
        (test_dir / "file1.txt").write_text("Hello World")  # 11 bytes
        (test_dir / "file2.txt").write_text("Test")  # 4 bytes
        
        # Create subdirectory with file
        sub_dir = test_dir / "subdir"
        sub_dir.mkdir()
        (sub_dir / "file3.txt").write_text("Sub")  # 3 bytes
        
        size = cache_manager._get_directory_size(test_dir)
        
        assert size == 18  # 11 + 4 + 3
    
    def test_get_directory_size_empty(self, cache_manager, temp_cache_root):
        """Test directory size calculation for empty directory."""
        test_dir = temp_cache_root / "empty"
        test_dir.mkdir()
        
        size = cache_manager._get_directory_size(test_dir)
        
        assert size == 0
    
    def test_get_directory_size_nonexistent(self, cache_manager, temp_cache_root):
        """Test directory size calculation for non-existent directory."""
        nonexistent_dir = temp_cache_root / "nonexistent"
        
        size = cache_manager._get_directory_size(nonexistent_dir)
        
        assert size == 0
    
    def test_cleanup_old_directories_no_cache_root(self, cache_manager, temp_cache_root):
        """Test cleanup when cache root doesn't exist."""
        # Remove cache root
        shutil.rmtree(temp_cache_root)
        
        with patch.object(cache_manager.logger, 'info') as mock_log_info:
            stats = cache_manager.cleanup_old_directories()
            
            expected_stats = {
                'directories_checked': 0,
                'directories_removed': 0,
                'bytes_freed': 0,
                'errors': 0
            }
            assert stats == expected_stats
            
            # Should log that cache root doesn't exist
            log_calls = mock_log_info.call_args_list
            skipped_call = next((call for call in log_calls 
                               if call[1].get('status') == LogStatus.SKIPPED), None)
            assert skipped_call is not None
    
    def test_cleanup_old_directories_success(self, cache_manager, temp_cache_root):
        """Test successful cleanup of old directories."""
        # Create old directory (>24 hours)
        old_dir = temp_cache_root / "old_repo_abc123"
        old_dir.mkdir()
        (old_dir / "file.txt").write_text("old content")
        
        # Set old modification time
        old_time = time.time() - (25 * 3600)  # 25 hours ago
        os.utime(old_dir, (old_time, old_time))
        
        # Create new directory (<24 hours)
        new_dir = temp_cache_root / "new_repo_def456"
        new_dir.mkdir()
        (new_dir / "file.txt").write_text("new content")
        
        with patch.object(cache_manager.logger, 'info') as mock_log_info:
            stats = cache_manager.cleanup_old_directories(max_age_hours=24)
            
            # Old directory should be removed
            assert not old_dir.exists()
            # New directory should remain
            assert new_dir.exists()
            
            # Check stats
            assert stats['directories_checked'] == 2
            assert stats['directories_removed'] == 1
            assert stats['bytes_freed'] > 0
            assert stats['errors'] == 0
            
            # Verify logging
            log_calls = mock_log_info.call_args_list
            completed_call = next((call for call in log_calls 
                                 if call[1].get('status') == LogStatus.COMPLETED), None)
            assert completed_call is not None
    
    def test_cleanup_old_directories_custom_age(self, cache_manager, temp_cache_root):
        """Test cleanup with custom age threshold."""
        # Create directory that's 2 hours old
        test_dir = temp_cache_root / "test_repo_ghi789"
        test_dir.mkdir()
        
        # Set modification time to 2 hours ago
        old_time = time.time() - (2 * 3600)
        os.utime(test_dir, (old_time, old_time))
        
        # Cleanup with 1 hour threshold - should remove directory
        stats = cache_manager.cleanup_old_directories(max_age_hours=1)
        
        assert not test_dir.exists()
        assert stats['directories_removed'] == 1
    
    def test_cleanup_old_directories_with_errors(self, cache_manager, temp_cache_root):
        """Test cleanup handling of errors during removal."""
        # Create directory
        test_dir = temp_cache_root / "error_repo_jkl012"
        test_dir.mkdir()
        
        # Set old modification time
        old_time = time.time() - (25 * 3600)
        os.utime(test_dir, (old_time, old_time))
        
        with patch('shutil.rmtree', side_effect=PermissionError("Permission denied")):
            with patch.object(cache_manager.logger, 'error') as mock_log_error:
                stats = cache_manager.cleanup_old_directories()
                
                # Directory should still exist due to error
                assert test_dir.exists()
                assert stats['directories_checked'] == 1
                assert stats['directories_removed'] == 0
                assert stats['errors'] == 1
                
                # Should log error
                mock_log_error.assert_called_once()
    
    def test_cleanup_old_directories_exception(self, cache_manager, temp_cache_root):
        """Test cleanup with general exception."""
        with patch('pathlib.Path.iterdir', side_effect=OSError("Access denied")):
            with patch.object(cache_manager.logger, 'error') as mock_log_error:
                with pytest.raises(RepositoryError) as exc_info:
                    cache_manager.cleanup_old_directories()
                
                assert "Cache cleanup failed" in str(exc_info.value)
                mock_log_error.assert_called_once()
    
    def test_get_cache_statistics_empty_cache(self, cache_manager, temp_cache_root):
        """Test cache statistics for empty cache."""
        stats = cache_manager.get_cache_statistics()
        
        expected_stats = {
            'total_directories': 0,
            'total_size_bytes': 0,
            'oldest_directory': None,
            'newest_directory': None,
            'cache_root_exists': True
        }
        assert stats == expected_stats
    
    def test_get_cache_statistics_no_cache_root(self, cache_manager, temp_cache_root):
        """Test cache statistics when cache root doesn't exist."""
        # Remove cache root
        shutil.rmtree(temp_cache_root)
        
        stats = cache_manager.get_cache_statistics()
        
        expected_stats = {
            'total_directories': 0,
            'total_size_bytes': 0,
            'oldest_directory': None,
            'newest_directory': None,
            'cache_root_exists': False
        }
        assert stats == expected_stats
    
    def test_get_cache_statistics_with_directories(self, cache_manager, temp_cache_root):
        """Test cache statistics with multiple directories."""
        # Create directories with different ages
        old_dir = temp_cache_root / "old_repo"
        old_dir.mkdir()
        (old_dir / "file.txt").write_text("old")
        
        new_dir = temp_cache_root / "new_repo"
        new_dir.mkdir()
        (new_dir / "file.txt").write_text("new content")
        
        # Set different modification times
        old_time = time.time() - 3600  # 1 hour ago
        new_time = time.time() - 1800  # 30 minutes ago
        os.utime(old_dir, (old_time, old_time))
        os.utime(new_dir, (new_time, new_time))
        
        stats = cache_manager.get_cache_statistics()
        
        assert stats['total_directories'] == 2
        assert stats['total_size_bytes'] > 0
        assert stats['oldest_directory'] is not None
        assert stats['newest_directory'] is not None
        assert stats['cache_root_exists'] is True
        
        # Verify oldest/newest tracking
        assert Path(stats['oldest_directory']['path']).name == "old_repo"
        assert Path(stats['newest_directory']['path']).name == "new_repo"
    
    def test_remove_cache_directory_success(self, cache_manager):
        """Test successful cache directory removal."""
        repository_url = "https://github.com/user/repo.git"
        
        # Create directory first
        cache_path = cache_manager.create_cache_directory(repository_url)
        assert cache_path.exists()
        
        with patch.object(cache_manager.logger, 'info') as mock_log_info:
            result = cache_manager.remove_cache_directory(repository_url)
            
            assert result is True
            assert not cache_path.exists()
            
            # Verify logging
            log_calls = mock_log_info.call_args_list
            completed_call = next((call for call in log_calls 
                                 if call[1].get('status') == LogStatus.COMPLETED), None)
            assert completed_call is not None
            assert completed_call[1]['repository_url'] == repository_url
    
    def test_remove_cache_directory_not_exists(self, cache_manager):
        """Test removing cache directory that doesn't exist."""
        repository_url = "https://github.com/user/nonexistent.git"
        
        with patch.object(cache_manager.logger, 'info') as mock_log_info:
            result = cache_manager.remove_cache_directory(repository_url)
            
            assert result is False
            
            # Should log that directory doesn't exist
            log_calls = mock_log_info.call_args_list
            skipped_call = next((call for call in log_calls 
                               if call[1].get('status') == LogStatus.SKIPPED), None)
            assert skipped_call is not None
    
    def test_remove_cache_directory_error(self, cache_manager):
        """Test cache directory removal with error."""
        repository_url = "https://github.com/user/repo.git"
        
        # Create directory
        cache_path = cache_manager.create_cache_directory(repository_url)
        
        with patch('shutil.rmtree', side_effect=PermissionError("Permission denied")):
            with patch.object(cache_manager.logger, 'error') as mock_log_error:
                with pytest.raises(RepositoryError) as exc_info:
                    cache_manager.remove_cache_directory(repository_url)
                
                assert "Failed to remove cache directory" in str(exc_info.value)
                assert exc_info.value.repository_url == repository_url
                
                # Verify error logging
                mock_log_error.assert_called_once()
                error_call = mock_log_error.call_args
                assert error_call[1]['status'] == LogStatus.FAILED
    
    def test_performance_decorator_success(self, cache_manager):
        """Test that performance logging decorator works correctly."""
        repository_url = "https://github.com/user/repo.git"
        
        with patch.object(cache_manager.logger, 'debug') as mock_log_debug:
            cache_path = cache_manager.create_cache_directory(repository_url)
            
            # Performance decorator should log completion
            debug_calls = mock_log_debug.call_args_list
            perf_call = next((call for call in debug_calls 
                            if "completed" in call[0][0] and 'duration_ms' in call[1]), None)
            assert perf_call is not None
            assert perf_call[1]['status'] == LogStatus.COMPLETED
            assert 'duration_ms' in perf_call[1]
    
    def test_performance_decorator_failure(self, cache_manager):
        """Test that performance logging decorator handles failures."""
        invalid_url = "ftp://invalid.com/repo"
        
        with patch.object(cache_manager.logger, 'error') as mock_log_error:
            with pytest.raises(RepositoryError):
                cache_manager.create_cache_directory(invalid_url)
            
            # Performance decorator should log failure
            error_calls = mock_log_error.call_args_list
            perf_call = next((call for call in error_calls 
                            if "failed" in call[0][0] and 'duration_ms' in call[1]), None)
            assert perf_call is not None
            assert perf_call[1]['status'] == LogStatus.FAILED
            assert 'duration_ms' in perf_call[1]
    
    def test_security_path_traversal_prevention(self, cache_manager):
        """Test that path traversal attacks are prevented."""
        malicious_urls = [
            "https://github.com/../../../etc/passwd",
            "https://github.com/user/../../sensitive",
            "file:///etc/passwd",
        ]
        
        for url in malicious_urls:
            with pytest.raises(RepositoryError):
                cache_manager.create_cache_directory(url)
    
    def test_concurrent_directory_creation(self, cache_manager):
        """Test concurrent creation of the same cache directory."""
        repository_url = "https://github.com/user/repo.git"
        
        # Create directory twice (simulating concurrent access)
        path1 = cache_manager.create_cache_directory(repository_url)
        path2 = cache_manager.create_cache_directory(repository_url)
        
        assert path1 == path2
        assert path1.exists()
    
    def test_integration_with_structured_logging(self, cache_manager):
        """Test integration with structured logging system."""
        repository_url = "https://github.com/user/repo.git"
        project_id = "integration_test_project"
        execution_id = "integration_test_execution"
        
        with patch.object(cache_manager.logger, 'info') as mock_log_info:
            cache_manager.create_cache_directory(
                repository_url=repository_url,
                project_id=project_id,
                execution_id=execution_id
            )
            
            # Verify structured logging fields are present
            log_calls = mock_log_info.call_args_list
            for call in log_calls:
                kwargs = call[1]
                assert 'correlation_id' in kwargs or kwargs.get('correlationId') == "test_correlation_123"
                if 'project_id' in kwargs:
                    assert kwargs['project_id'] == project_id
                if 'execution_id' in kwargs:
                    assert kwargs['execution_id'] == execution_id
                if 'status' in kwargs:
                    assert isinstance(kwargs['status'], LogStatus)


class TestRepositoryCacheManagerIntegration:
    """Integration tests for RepositoryCacheManager with real filesystem operations."""
    
    @pytest.fixture
    def real_temp_cache(self):
        """Create a real temporary cache directory."""
        temp_dir = tempfile.mkdtemp(prefix="repo_cache_test_")
        yield Path(temp_dir)
        # Cleanup
        if Path(temp_dir).exists():
            shutil.rmtree(temp_dir)
    
    def test_end_to_end_cache_lifecycle(self, real_temp_cache):
        """Test complete cache lifecycle: create, use, cleanup."""
        with patch.object(RepositoryCacheManager, 'CACHE_ROOT', real_temp_cache):
            manager = RepositoryCacheManager(correlation_id="e2e_test_789")
            
            repository_url = "https://github.com/user/test-repo.git"
            
            # 1. Create cache directory
            cache_path = manager.create_cache_directory(repository_url)
            assert cache_path.exists()
            assert cache_path.is_dir()
            
            # 2. Verify directory exists
            assert manager.directory_exists(repository_url)
            retrieved_path = manager.get_cache_directory(repository_url)
            assert retrieved_path == cache_path
            
            # 3. Add some content to simulate usage
            test_file = cache_path / "test_content.txt"
            test_file.write_text("Test repository content")
            
            # 4. Get statistics
            stats = manager.get_cache_statistics()
            assert stats['total_directories'] == 1
            assert stats['total_size_bytes'] > 0
            
            # 5. Remove cache directory
            removed = manager.remove_cache_directory(repository_url)
            assert removed is True
            assert not cache_path.exists()
            
            # 6. Verify removal
            assert not manager.directory_exists(repository_url)
            final_stats = manager.get_cache_statistics()
            assert final_stats['total_directories'] == 0
    
    def test_performance_requirements(self, real_temp_cache):
        """Test that directory operations meet performance requirements (≤2s)."""
        with patch.object(RepositoryCacheManager, 'CACHE_ROOT', real_temp_cache):
            manager = RepositoryCacheManager()
            
            repository_url = "https://github.com/user/perf-test.git"
            
            # Test create operation performance
            start_time = time.time()
            cache_path = manager.create_cache_directory(repository_url)
            create_duration = time.time() - start_time
            
            assert create_duration < 2.0, f"Create operation took {create_duration}s, exceeds 2s requirement"
            
            # Test get operation performance
            start_time = time.time()
            retrieved_path = manager.get_cache_directory(repository_url)
            get_duration = time.time() - start_time
            
            assert get_duration < 2.0, f"Get operation took {get_duration}s, exceeds 2s requirement"
            assert retrieved_path == cache_path
            
            # Test cleanup operation performance
            start_time = time.time()
            stats = manager.cleanup_old_directories()
            cleanup_duration = time.time() - start_time
            
            assert cleanup_duration < 2.0, f"Cleanup operation took {cleanup_duration}s, exceeds 2s requirement"
    
    def test_file_permissions_security(self, real_temp_cache):
        """Test that proper file permissions are set for security."""
        with patch.object(RepositoryCacheManager, 'CACHE_ROOT', real_temp_cache):
            manager = RepositoryCacheManager()
            
            repository_url = "https://github.com/user/security-test.git"
            cache_path = manager.create_cache_directory(repository_url)
            
            # Check directory permissions
            dir_stat = cache_path.stat()
            dir_mode = stat.S_IMODE(dir_stat.st_mode)
            
            # Should have read, write, execute for owner and group, read/execute for others
            expected_mode = manager.DEFAULT_DIR_PERMISSIONS
            assert dir_mode == expected_mode, f"Directory permissions {oct(dir_mode)} != expected {oct(expected_mode)}"


class TestRepositoryExistenceCheck:
    """Test suite for enhanced repository existence check functionality (Task 4.1.2)."""
    
    @pytest.fixture
    def temp_cache_root(self):
        """Create a temporary directory for cache testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        # Cleanup
        if Path(temp_dir).exists():
            shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def cache_manager(self, temp_cache_root):
        """Create a cache manager with temporary cache root."""
        with patch.object(RepositoryCacheManager, 'CACHE_ROOT', temp_cache_root):
            return RepositoryCacheManager(correlation_id="test_existence_check_123")
    
    def test_check_repository_existence_cache_hit(self, cache_manager):
        """Test repository existence check with cache hit."""
        repository_url = "https://github.com/user/test-repo.git"
        project_id = "test_project_456"
        execution_id = "test_execution_789"
        
        # Create cache directory first
        cache_path = cache_manager.create_cache_directory(repository_url)
        
        # Add some content to the cache
        test_file = cache_path / "test_file.txt"
        test_file.write_text("test content")
        
        with patch.object(cache_manager.logger, 'info') as mock_log_info:
            result = cache_manager.check_repository_existence(
                repository_url=repository_url,
                project_id=project_id,
                execution_id=execution_id
            )
            
            # Verify result structure
            assert isinstance(result, dict)
            assert result['exists_in_cache'] is True
            assert result['cache_path'] == str(cache_path)
            assert result['repository_url'] == repository_url
            assert result['validation_status'] == "cache_hit"
            assert 'cache_key' in result
            assert 'performance_metrics' in result
            assert 'cache_size_bytes' in result
            assert 'last_accessed' in result
            assert 'last_modified' in result
            
            # Verify performance metrics
            perf_metrics = result['performance_metrics']
            assert 'check_duration_ms' in perf_metrics
            assert 'url_validation_time_ms' in perf_metrics
            assert 'cache_lookup_time_ms' in perf_metrics
            assert perf_metrics['check_duration_ms'] > 0
            
            # Verify cache metadata
            assert result['cache_size_bytes'] > 0  # Should have content
            assert result['last_accessed'] is not None
            assert result['last_modified'] is not None
            
            # Verify logging
            log_calls = mock_log_info.call_args_list
            start_call = next((call for call in log_calls
                             if "Starting repository existence check" in call[0][0]), None)
            assert start_call is not None
            assert start_call[1]['project_id'] == project_id
            assert start_call[1]['execution_id'] == execution_id
            
            completed_call = next((call for call in log_calls
                                 if "completed successfully" in call[0][0]), None)
            assert completed_call is not None
            assert completed_call[1]['exists_in_cache'] is True
            assert completed_call[1]['validation_status'] == "cache_hit"
    
    def test_check_repository_existence_cache_miss(self, cache_manager):
        """Test repository existence check with cache miss."""
        repository_url = "https://github.com/user/nonexistent-repo.git"
        project_id = "test_project_456"
        execution_id = "test_execution_789"
        
        with patch.object(cache_manager.logger, 'info') as mock_log_info:
            result = cache_manager.check_repository_existence(
                repository_url=repository_url,
                project_id=project_id,
                execution_id=execution_id
            )
            
            # Verify result structure
            assert isinstance(result, dict)
            assert result['exists_in_cache'] is False
            assert result['cache_path'] is None
            assert result['repository_url'] == repository_url
            assert result['validation_status'] == "cache_miss"
            assert 'cache_key' in result
            assert 'performance_metrics' in result
            
            # Should not have cache metadata for non-existent cache
            assert 'cache_size_bytes' not in result
            assert 'last_accessed' not in result
            assert 'last_modified' not in result
            
            # Verify performance metrics
            perf_metrics = result['performance_metrics']
            assert perf_metrics['check_duration_ms'] > 0
            
            # Verify logging
            log_calls = mock_log_info.call_args_list
            completed_call = next((call for call in log_calls
                                 if "completed successfully" in call[0][0]), None)
            assert completed_call is not None
            assert completed_call[1]['exists_in_cache'] is False
            assert completed_call[1]['validation_status'] == "cache_miss"
    
    def test_check_repository_existence_invalid_url(self, cache_manager):
        """Test repository existence check with invalid URL."""
        invalid_url = "ftp://invalid.com/repo"
        
        with patch.object(cache_manager.logger, 'error') as mock_log_error:
            with pytest.raises(RepositoryError) as exc_info:
                cache_manager.check_repository_existence(invalid_url)
            
            assert "Unsupported URL scheme" in str(exc_info.value)
            assert exc_info.value.repository_url == invalid_url
            
            # Verify error logging
            mock_log_error.assert_called_once()
            error_call = mock_log_error.call_args
            assert error_call[1]['status'] == LogStatus.FAILED
            assert error_call[1]['repository_url'] == invalid_url
    
    def test_check_repository_existence_performance(self, cache_manager):
        """Test that repository existence check meets performance requirements (≤2s)."""
        repository_url = "https://github.com/user/performance-test.git"
        
        # Test with cache miss (should be fastest)
        start_time = time.time()
        result = cache_manager.check_repository_existence(repository_url)
        duration = time.time() - start_time
        
        assert duration < 2.0, f"Cache miss check took {duration}s, exceeds 2s requirement"
        assert result['performance_metrics']['check_duration_ms'] < 2000
        
        # Create cache and test with cache hit
        cache_manager.create_cache_directory(repository_url)
        
        start_time = time.time()
        result = cache_manager.check_repository_existence(repository_url)
        duration = time.time() - start_time
        
        assert duration < 2.0, f"Cache hit check took {duration}s, exceeds 2s requirement"
        assert result['performance_metrics']['check_duration_ms'] < 2000
    
    def test_check_repository_existence_with_correlation_id(self, cache_manager):
        """Test that correlationId is properly propagated in existence check."""
        repository_url = "https://github.com/user/correlation-test.git"
        correlation_id = "test_correlation_456"
        
        # Create manager with specific correlation ID
        manager = RepositoryCacheManager(correlation_id=correlation_id)
        
        with patch.object(RepositoryCacheManager, 'CACHE_ROOT', cache_manager.CACHE_ROOT):
            with patch.object(manager.logger, 'info') as mock_log_info:
                result = manager.check_repository_existence(repository_url)
                
                # Verify correlationId in all log calls
                log_calls = mock_log_info.call_args_list
                for call in log_calls:
                    assert call[1]['correlation_id'] == correlation_id
    
    def test_get_repository_cache_info_exists(self, cache_manager):
        """Test getting cache info for existing repository."""
        repository_url = "https://github.com/user/cache-info-test.git"
        project_id = "test_project_789"
        execution_id = "test_execution_012"
        
        # Create cache directory with content
        cache_path = cache_manager.create_cache_directory(repository_url)
        test_file1 = cache_path / "file1.txt"
        test_file1.write_text("content1")
        test_file2 = cache_path / "subdir" / "file2.txt"
        test_file2.parent.mkdir(parents=True)
        test_file2.write_text("content2")
        
        with patch.object(cache_manager.logger, 'debug') as mock_log_debug:
            cache_info = cache_manager.get_repository_cache_info(
                repository_url=repository_url,
                project_id=project_id,
                execution_id=execution_id
            )
            
            # Verify cache info structure
            assert cache_info is not None
            assert isinstance(cache_info, dict)
            assert cache_info['cache_path'] == str(cache_path)
            assert 'cache_key' in cache_info
            assert cache_info['size_bytes'] > 0
            assert cache_info['file_count'] == 2  # Two files created
            assert cache_info['is_valid'] is True
            assert 'created_at' in cache_info
            assert 'last_accessed' in cache_info
            assert 'last_modified' in cache_info
            
            # Verify logging
            log_calls = mock_log_debug.call_args_list
            collecting_call = next((call for call in log_calls
                                  if "Collecting repository cache information" in call[0][0]), None)
            assert collecting_call is not None
            assert collecting_call[1]['project_id'] == project_id
            assert collecting_call[1]['execution_id'] == execution_id
            
            collected_call = next((call for call in log_calls
                                 if "information collected" in call[0][0]), None)
            assert collected_call is not None
            assert collected_call[1]['cache_info'] == cache_info
    
    def test_get_repository_cache_info_not_exists(self, cache_manager):
        """Test getting cache info for non-existent repository."""
        repository_url = "https://github.com/user/nonexistent-cache.git"
        
        cache_info = cache_manager.get_repository_cache_info(repository_url)
        
        assert cache_info is None
    
    def test_get_repository_cache_info_invalid_url(self, cache_manager):
        """Test getting cache info with invalid URL."""
        invalid_url = "ftp://invalid.com/repo"
        
        with pytest.raises(RepositoryError) as exc_info:
            cache_manager.get_repository_cache_info(invalid_url)
        
        assert "Unsupported URL scheme" in str(exc_info.value)
        assert exc_info.value.repository_url == invalid_url
    
    def test_get_repository_cache_info_error_handling(self, cache_manager):
        """Test cache info error handling."""
        repository_url = "https://github.com/user/error-test.git"
        
        # Create cache directory
        cache_path = cache_manager.create_cache_directory(repository_url)
        
        # Mock stat to raise an exception
        with patch.object(cache_path, 'stat', side_effect=OSError("Permission denied")):
            with patch.object(cache_manager.logger, 'error') as mock_log_error:
                with pytest.raises(RepositoryError) as exc_info:
                    cache_manager.get_repository_cache_info(repository_url)
                
                assert "Failed to get repository cache info" in str(exc_info.value)
                mock_log_error.assert_called_once()
    
    def test_repository_existence_check_integration_with_workflow(self, cache_manager):
        """Test integration of repository existence check with workflow patterns."""
        repository_url = "https://github.com/user/workflow-integration.git"
        project_id = "workflow_project_123"
        execution_id = "workflow_execution_456"
        
        # Simulate workflow integration scenario
        # 1. Check if repository exists in cache (should be cache miss)
        result1 = cache_manager.check_repository_existence(
            repository_url=repository_url,
            project_id=project_id,
            execution_id=execution_id
        )
        
        assert result1['exists_in_cache'] is False
        assert result1['validation_status'] == "cache_miss"
        
        # 2. Create cache directory (simulating repository initialization)
        cache_path = cache_manager.create_cache_directory(
            repository_url=repository_url,
            project_id=project_id,
            execution_id=execution_id
        )
        
        # 3. Check existence again (should be cache hit)
        result2 = cache_manager.check_repository_existence(
            repository_url=repository_url,
            project_id=project_id,
            execution_id=execution_id
        )
        
        assert result2['exists_in_cache'] is True
        assert result2['validation_status'] == "cache_hit"
        assert result2['cache_path'] == str(cache_path)
        
        # 4. Get detailed cache info
        cache_info = cache_manager.get_repository_cache_info(
            repository_url=repository_url,
            project_id=project_id,
            execution_id=execution_id
        )
        
        assert cache_info is not None
        assert cache_info['cache_path'] == str(cache_path)
        assert cache_info['is_valid'] is True
    
    def test_repository_existence_check_concurrent_access(self, cache_manager):
        """Test repository existence check under concurrent access scenarios."""
        repository_url = "https://github.com/user/concurrent-test.git"
        
        # Create cache directory
        cache_path = cache_manager.create_cache_directory(repository_url)
        
        # Simulate concurrent existence checks
        results = []
        for i in range(5):
            result = cache_manager.check_repository_existence(
                repository_url=repository_url,
                project_id=f"concurrent_project_{i}",
                execution_id=f"concurrent_execution_{i}"
            )
            results.append(result)
        
        # All results should be consistent
        for result in results:
            assert result['exists_in_cache'] is True
            assert result['validation_status'] == "cache_hit"
            assert result['cache_path'] == str(cache_path)
            assert result['performance_metrics']['check_duration_ms'] < 2000
    
    def test_repository_existence_check_security_validation(self, cache_manager):
        """Test security validation in repository existence check."""
        malicious_urls = [
            "https://github.com/../../../etc/passwd",
            "https://github.com/user/../../sensitive",
            "file:///etc/passwd",
            "https://github.com/user/repo\x00malicious",
        ]
        
        for malicious_url in malicious_urls:
            with pytest.raises(RepositoryError):
                cache_manager.check_repository_existence(malicious_url)
    
    def test_repository_existence_check_structured_logging(self, cache_manager):
        """Test structured logging in repository existence check."""
        repository_url = "https://github.com/user/logging-test.git"
        project_id = "logging_project_123"
        execution_id = "logging_execution_456"
        
        with patch.object(cache_manager.logger, 'info') as mock_log_info:
            cache_manager.check_repository_existence(
                repository_url=repository_url,
                project_id=project_id,
                execution_id=execution_id
            )
            
            # Verify structured logging fields
            log_calls = mock_log_info.call_args_list
            for call in log_calls:
                kwargs = call[1]
                # Check for required structured logging fields
                assert 'correlation_id' in kwargs
                assert 'project_id' in kwargs
                assert 'execution_id' in kwargs
                assert 'status' in kwargs
                assert 'repository_url' in kwargs
                
                # Verify values
                assert kwargs['correlation_id'] == cache_manager.correlation_id
                assert kwargs['project_id'] == project_id
                assert kwargs['execution_id'] == execution_id
                assert kwargs['repository_url'] == repository_url


class TestRepositoryClone:
    """Test suite for repository clone functionality (Task 4.2.1)."""
    
    @pytest.fixture
    def temp_cache_root(self):
        """Create a temporary directory for cache testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        # Cleanup
        if Path(temp_dir).exists():
            shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def cache_manager(self, temp_cache_root):
        """Create a cache manager with temporary cache root."""
        manager = RepositoryCacheManager(correlation_id="test_clone_123")
        # Override the CACHE_ROOT instance variable to use temp directory for testing
        manager.CACHE_ROOT = temp_cache_root
        return manager
    
    @pytest.fixture
    def mock_successful_git_clone(self):
        """Mock successful git clone subprocess."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Cloning into 'repo'..."
        mock_result.stderr = ""
        return mock_result
    
    @pytest.fixture
    def mock_failed_git_clone(self):
        """Mock failed git clone subprocess."""
        mock_result = Mock()
        mock_result.returncode = 128
        mock_result.stdout = ""
        mock_result.stderr = "fatal: repository 'https://github.com/user/nonexistent.git' not found"
        return mock_result
    
    def test_clone_repository_success(self, cache_manager, mock_successful_git_clone):
        """Test successful repository clone operation."""
        repository_url = "https://github.com/user/test-repo.git"
        project_id = "test_project_123"
        execution_id = "test_execution_456"
        
        with patch('subprocess.run', return_value=mock_successful_git_clone) as mock_subprocess:
            with patch.object(cache_manager.logger, 'info') as mock_log_info:
                # Create some test files to simulate cloned content
                def create_test_files(*args, **kwargs):
                    cache_key = cache_manager._generate_cache_key(repository_url)
                    cache_path = cache_manager.CACHE_ROOT / cache_key
                    if cache_path.exists():
                        (cache_path / "README.md").write_text("# Test Repository")
                        (cache_path / "src" / "main.py").parent.mkdir(parents=True)
                        (cache_path / "src" / "main.py").write_text("print('Hello World')")
                    return mock_successful_git_clone
                
                mock_subprocess.side_effect = create_test_files
                
                result = cache_manager.clone_repository(
                    repository_url=repository_url,
                    project_id=project_id,
                    execution_id=execution_id
                )
                
                # Verify result structure
                assert isinstance(result, dict)
                assert result['success'] is True
                assert result['repository_url'] == repository_url
                assert result['clone_status'] == 'cloned'
                assert 'cache_path' in result
                assert 'performance_metrics' in result
                assert 'repository_size_bytes' in result
                assert 'files_cloned' in result
                
                # Verify performance metrics
                perf_metrics = result['performance_metrics']
                assert 'total_duration_ms' in perf_metrics
                assert 'git_clone_duration_ms' in perf_metrics
                assert 'validation_duration_ms' in perf_metrics
                assert perf_metrics['total_duration_ms'] > 0
                assert perf_metrics['git_clone_duration_ms'] >= 0
                
                # Verify repository metrics
                assert result['repository_size_bytes'] > 0
                assert result['files_cloned'] == 2  # README.md and main.py
                
                # Verify git command was called correctly
                mock_subprocess.assert_called_once()
                call_args = mock_subprocess.call_args
                assert call_args[0][0][0] == "git"
                assert call_args[0][0][1] == "clone"
                assert call_args[0][0][2] == repository_url
                assert call_args[1]['capture_output'] is True
                assert call_args[1]['text'] is True
                assert call_args[1]['timeout'] == 30
                
                # Verify logging
                log_calls = mock_log_info.call_args_list
                start_call = next((call for call in log_calls
                                 if "Starting repository clone operation" in call[0][0]), None)
                assert start_call is not None
                assert start_call[1]['project_id'] == project_id
                assert start_call[1]['execution_id'] == execution_id
                
                completed_call = next((call for call in log_calls
                                     if "completed successfully" in call[0][0]), None)
                assert completed_call is not None
                assert completed_call[1]['repository_url'] == repository_url
    
    def test_clone_repository_already_exists(self, cache_manager):
        """Test clone operation when repository already exists in cache."""
        repository_url = "https://github.com/user/existing-repo.git"
        project_id = "test_project_789"
        execution_id = "test_execution_012"
        
        # Create cache directory first
        cache_path = cache_manager.create_cache_directory(repository_url)
        (cache_path / "existing_file.txt").write_text("existing content")
        
        with patch('subprocess.run') as mock_subprocess:
            with patch.object(cache_manager.logger, 'info') as mock_log_info:
                result = cache_manager.clone_repository(
                    repository_url=repository_url,
                    project_id=project_id,
                    execution_id=execution_id
                )
                
                # Verify result indicates repository already exists
                assert result['success'] is True
                assert result['clone_status'] == 'already_exists'
                assert result['cache_path'] == str(cache_path)
                assert result['repository_size_bytes'] > 0
                assert result['files_cloned'] == 1
                
                # Verify git clone was not called
                mock_subprocess.assert_not_called()
                
                # Verify logging indicates skip
                log_calls = mock_log_info.call_args_list
                skipped_call = next((call for call in log_calls
                                   if "already exists in cache" in call[0][0]), None)
                assert skipped_call is not None
                assert skipped_call[1]['status'] == LogStatus.SKIPPED
    
    def test_clone_repository_git_failure(self, cache_manager, mock_failed_git_clone):
        """Test clone operation with git command failure."""
        repository_url = "https://github.com/user/nonexistent.git"
        
        with patch('subprocess.run', return_value=mock_failed_git_clone):
            with patch.object(cache_manager.logger, 'error') as mock_log_error:
                with pytest.raises(RepositoryError) as exc_info:
                    cache_manager.clone_repository(repository_url)
                
                assert "Git clone failed" in str(exc_info.value)
                assert exc_info.value.repository_url == repository_url
                
                # Verify error logging
                mock_log_error.assert_called()
                error_calls = mock_log_error.call_args_list
                git_error_call = next((call for call in error_calls
                                     if "Git clone operation failed" in call[0][0]), None)
                assert git_error_call is not None
                assert git_error_call[1]['status'] == LogStatus.FAILED
                assert git_error_call[1]['git_return_code'] == 128
    
    def test_clone_repository_timeout(self, cache_manager):
        """Test clone operation with timeout."""
        repository_url = "https://github.com/user/slow-repo.git"
        timeout_seconds = 5
        
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired("git", timeout_seconds)):
            with patch.object(cache_manager.logger, 'error') as mock_log_error:
                with pytest.raises(RepositoryError) as exc_info:
                    cache_manager.clone_repository(
                        repository_url=repository_url,
                        timeout_seconds=timeout_seconds
                    )
                
                assert "timed out" in str(exc_info.value)
                assert f"{timeout_seconds} seconds" in str(exc_info.value)
                
                # Verify error logging
                mock_log_error.assert_called()
                error_calls = mock_log_error.call_args_list
                timeout_call = next((call for call in error_calls
                                   if "timed out" in call[0][0]), None)
                assert timeout_call is not None
                assert timeout_call[1]['timeout_seconds'] == timeout_seconds
    
    def test_clone_repository_invalid_url(self, cache_manager):
        """Test clone operation with invalid repository URL."""
        invalid_url = "ftp://invalid.com/repo"
        
        with pytest.raises(RepositoryError) as exc_info:
            cache_manager.clone_repository(invalid_url)
        
        assert "Unsupported URL scheme" in str(exc_info.value)
        assert exc_info.value.repository_url == invalid_url
    
    def test_clone_repository_with_auth_token(self, cache_manager, mock_successful_git_clone):
        """Test clone operation with authentication token."""
        repository_url = "https://github.com/user/private-repo.git"
        auth_token = "ghp_test_token_123"
        
        with patch('subprocess.run', return_value=mock_successful_git_clone) as mock_subprocess:
            def create_test_files(*args, **kwargs):
                cache_key = cache_manager._generate_cache_key(repository_url)
                cache_path = cache_manager.CACHE_ROOT / cache_key
                if cache_path.exists():
                    (cache_path / "private_file.txt").write_text("private content")
                return mock_successful_git_clone
            
            mock_subprocess.side_effect = create_test_files
            
            result = cache_manager.clone_repository(
                repository_url=repository_url,
                auth_token=auth_token
            )
            
            assert result['success'] is True
            assert result['clone_status'] == 'cloned'
            
            # Verify git command used authenticated URL
            mock_subprocess.assert_called_once()
            call_args = mock_subprocess.call_args
            clone_url = call_args[0][0][2]
            assert auth_token in clone_url
            assert clone_url.startswith("https://")
    
    def test_clone_repository_custom_timeout(self, cache_manager, mock_successful_git_clone):
        """Test clone operation with custom timeout."""
        repository_url = "https://github.com/user/large-repo.git"
        custom_timeout = 60
        
        with patch('subprocess.run', return_value=mock_successful_git_clone) as mock_subprocess:
            def create_test_files(*args, **kwargs):
                cache_key = cache_manager._generate_cache_key(repository_url)
                cache_path = cache_manager.CACHE_ROOT / cache_key
                if cache_path.exists():
                    (cache_path / "large_file.txt").write_text("large content")
                return mock_successful_git_clone
            
            mock_subprocess.side_effect = create_test_files
            
            result = cache_manager.clone_repository(
                repository_url=repository_url,
                timeout_seconds=custom_timeout
            )
            
            assert result['success'] is True
            
            # Verify custom timeout was used
            call_args = mock_subprocess.call_args
            assert call_args[1]['timeout'] == custom_timeout
    
    def test_clone_repository_empty_result(self, cache_manager, mock_successful_git_clone):
        """Test clone operation that results in empty directory."""
        repository_url = "https://github.com/user/empty-repo.git"
        
        with patch('subprocess.run', return_value=mock_successful_git_clone):
            with pytest.raises(RepositoryError) as exc_info:
                cache_manager.clone_repository(repository_url)
            
            assert "cache directory is empty" in str(exc_info.value)
    
    def test_prepare_clone_url_without_token(self, cache_manager):
        """Test URL preparation without authentication token."""
        repository_url = "https://github.com/user/public-repo.git"
        
        prepared_url = cache_manager._prepare_clone_url(repository_url)
        
        assert prepared_url == repository_url
    
    def test_prepare_clone_url_with_token(self, cache_manager):
        """Test URL preparation with authentication token."""
        repository_url = "https://github.com/user/private-repo.git"
        auth_token = "ghp_test_token_456"
        
        prepared_url = cache_manager._prepare_clone_url(repository_url, auth_token)
        
        assert auth_token in prepared_url
        assert prepared_url.startswith("https://")
        assert "github.com" in prepared_url
        assert prepared_url != repository_url
    
    def test_prepare_clone_url_non_https(self, cache_manager):
        """Test URL preparation with non-HTTPS URL."""
        repository_url = "git@github.com:user/repo.git"
        auth_token = "token_123"
        
        prepared_url = cache_manager._prepare_clone_url(repository_url, auth_token)
        
        # Should return original URL for non-HTTPS (MVP approach)
        assert prepared_url == repository_url
    
    def test_count_files_in_directory(self, cache_manager, temp_cache_root):
        """Test file counting utility method."""
        test_dir = temp_cache_root / "test_count"
        test_dir.mkdir()
        
        # Create test files
        (test_dir / "file1.txt").write_text("content1")
        (test_dir / "file2.txt").write_text("content2")
        (test_dir / "subdir").mkdir()
        (test_dir / "subdir" / "file3.txt").write_text("content3")
        
        file_count = cache_manager._count_files_in_directory(test_dir)
        
        assert file_count == 3
    
    def test_count_files_empty_directory(self, cache_manager, temp_cache_root):
        """Test file counting in empty directory."""
        empty_dir = temp_cache_root / "empty"
        empty_dir.mkdir()
        
        file_count = cache_manager._count_files_in_directory(empty_dir)
        
        assert file_count == 0
    
    def test_count_files_nonexistent_directory(self, cache_manager, temp_cache_root):
        """Test file counting in non-existent directory."""
        nonexistent_dir = temp_cache_root / "nonexistent"
        
        file_count = cache_manager._count_files_in_directory(nonexistent_dir)
        
        assert file_count == 0
    
    def test_clone_repository_performance_logging(self, cache_manager, mock_successful_git_clone):
        """Test that clone operation completes successfully and includes performance metrics in result."""
        repository_url = "https://github.com/user/perf-test.git"

        with patch('subprocess.run', return_value=mock_successful_git_clone):
            def create_test_files(*args, **kwargs):
                cache_key = cache_manager._generate_cache_key(repository_url)
                cache_path = cache_manager.CACHE_ROOT / cache_key
                if cache_path.exists():
                    (cache_path / "test.txt").write_text("test")
                return mock_successful_git_clone

            with patch('subprocess.run', side_effect=create_test_files):
                result = cache_manager.clone_repository(repository_url)

            # Verify that the operation completed successfully and includes performance metrics
            assert result['success'] is True
            assert 'performance_metrics' in result
            assert 'total_duration_ms' in result['performance_metrics']
            assert 'git_clone_duration_ms' in result['performance_metrics']
            assert 'validation_duration_ms' in result['performance_metrics']
            
            # Verify performance metrics are reasonable
            assert result['performance_metrics']['total_duration_ms'] >= 0
            assert result['performance_metrics']['git_clone_duration_ms'] >= 0
            assert result['performance_metrics']['validation_duration_ms'] >= 0
    
    def test_clone_repository_structured_logging_fields(self, cache_manager, mock_successful_git_clone):
        """Test that clone operation includes all required structured logging fields."""
        repository_url = "https://github.com/user/logging-test.git"
        project_id = "logging_project_456"
        execution_id = "logging_execution_789"

        with patch('subprocess.run', return_value=mock_successful_git_clone):
            with patch.object(cache_manager.logger, 'info') as mock_log_info:
                def create_test_files(*args, **kwargs):
                    cache_key = cache_manager._generate_cache_key(repository_url)
                    cache_path = cache_manager.CACHE_ROOT / cache_key
                    if cache_path.exists():
                        (cache_path / "test.txt").write_text("test")
                    return mock_successful_git_clone

                with patch('subprocess.run', side_effect=create_test_files):
                    cache_manager.clone_repository(
                        repository_url=repository_url,
                        project_id=project_id,
                        execution_id=execution_id
                    )

                # Verify structured logging fields - look for clone-specific log calls
                log_calls = mock_log_info.call_args_list
                clone_related_calls = []
                for call in log_calls:
                    kwargs = call[1]
                    # Look for calls that include repository_url or are clone-related
                    if 'repository_url' in kwargs and kwargs['repository_url'] == repository_url:
                        clone_related_calls.append(call)
                    elif any(keyword in call[0][0].lower() for keyword in ['clone', 'starting repository']):
                        clone_related_calls.append(call)

                # Should have at least one clone-related call
                assert len(clone_related_calls) > 0, f"Expected clone-related log calls, got: {[call[0] for call in log_calls]}"
                
                # Check that at least one call has the required fields
                found_required_fields = False
                for call in clone_related_calls:
                    kwargs = call[1]
                    if ('correlation_id' in kwargs and 'project_id' in kwargs and
                        'execution_id' in kwargs and 'status' in kwargs):
                        found_required_fields = True
                        break
                
                assert found_required_fields, "Expected at least one log call with required structured logging fields"
    
    def test_clone_repository_cleanup_on_failure(self, cache_manager, mock_failed_git_clone):
        """Test that failed clone operations clean up created directories."""
        repository_url = "https://github.com/user/cleanup-test.git"
        
        with patch('subprocess.run', return_value=mock_failed_git_clone):
            # Get the cache path that would be created
            cache_key = cache_manager._generate_cache_key(repository_url)
            expected_cache_path = cache_manager.CACHE_ROOT / cache_key
            
            with pytest.raises(RepositoryError):
                cache_manager.clone_repository(repository_url)
            
            # Verify cache directory was cleaned up
            assert not expected_cache_path.exists()
    
    def test_clone_repository_concurrent_safety(self, cache_manager, mock_successful_git_clone):
        """Test clone operation safety under concurrent access scenarios."""
        repository_url = "https://github.com/user/concurrent-clone.git"
        
        def create_test_files(*args, **kwargs):
            cache_key = cache_manager._generate_cache_key(repository_url)
            cache_path = cache_manager.CACHE_ROOT / cache_key
            if cache_path.exists():
                (cache_path / "concurrent.txt").write_text("concurrent test")
            return mock_successful_git_clone
        
        with patch('subprocess.run', side_effect=create_test_files):
            # First clone should succeed
            result1 = cache_manager.clone_repository(repository_url)
            assert result1['clone_status'] == 'cloned'
            
            # Second clone should detect existing repository
            result2 = cache_manager.clone_repository(repository_url)
            assert result2['clone_status'] == 'already_exists'
            
            # Both should point to same cache path
            assert result1['cache_path'] == result2['cache_path']


class TestRepositoryCloneValidation:
    """Test suite for repository clone validation functionality (Task 4.2.2)."""
    
    @pytest.fixture
    def temp_cache_root(self):
        """Create a temporary directory for cache testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        # Cleanup
        if Path(temp_dir).exists():
            shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def cache_manager(self, temp_cache_root):
        """Create a cache manager with temporary cache root."""
        manager = RepositoryCacheManager(correlation_id="test_validate_clone_123")
        # Override the CACHE_ROOT instance variable to use temp directory for testing
        manager.CACHE_ROOT = temp_cache_root
        return manager
    
    @pytest.fixture
    def mock_git_commands(self):
        """Mock successful git command responses."""
        def mock_subprocess_run(*args, **kwargs):
            command = args[0]
            if command[0] == "git":
                if command[1] == "status":
                    mock_result = Mock()
                    mock_result.returncode = 0
                    mock_result.stdout = ""
                    mock_result.stderr = ""
                    return mock_result
                elif command[1] == "remote" and command[2] == "get-url":
                    mock_result = Mock()
                    mock_result.returncode = 0
                    mock_result.stdout = "https://github.com/user/test-repo.git\n"
                    mock_result.stderr = ""
                    return mock_result
                elif command[1] == "fsck":
                    mock_result = Mock()
                    mock_result.returncode = 0
                    mock_result.stdout = ""
                    mock_result.stderr = ""
                    return mock_result
                elif command[1] == "log":
                    mock_result = Mock()
                    mock_result.returncode = 0
                    mock_result.stdout = "abc123|Initial commit|Test Author|2023-01-01 12:00:00 +0000\n"
                    mock_result.stderr = ""
                    return mock_result
            
            # Default mock for other commands
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            return mock_result
        
        return mock_subprocess_run
    
    def test_validate_clone_success(self, cache_manager, mock_git_commands):
        """Test successful clone validation with all checks passing."""
        repository_url = "https://github.com/user/test-repo.git"
        project_id = "test_project_123"
        execution_id = "test_execution_456"
        
        # Create cache directory with .git directory
        cache_path = cache_manager.create_cache_directory(repository_url)
        git_dir = cache_path / '.git'
        git_dir.mkdir()
        (git_dir / 'config').write_text('[core]\n\trepositoryformatversion = 0')
        
        # Add some test files
        (cache_path / 'README.md').write_text('# Test Repository')
        (cache_path / 'src').mkdir()
        (cache_path / 'src' / 'main.py').write_text('print("Hello World")')
        
        with patch('subprocess.run', side_effect=mock_git_commands):
            with patch.object(cache_manager.logger, 'info') as mock_log_info:
                result = cache_manager.validate_clone(
                    repository_url=repository_url,
                    project_id=project_id,
                    execution_id=execution_id
                )
                
                # Verify result structure
                assert isinstance(result, dict)
                assert result['is_valid'] is True
                assert result['repository_url'] == repository_url
                assert result['cache_path'] == str(cache_path)
                assert result['validation_status'] == 'valid'
                assert 'validation_checks' in result
                assert 'performance_metrics' in result
                assert 'repository_info' in result
                assert result['error_details'] is None
                
                # Verify validation checks
                checks = result['validation_checks']
                assert checks['git_directory_exists'] is True
                assert checks['git_status_works'] is True
                assert checks['remote_origin_configured'] is True
                assert checks['repository_not_corrupted'] is True
                assert checks['proper_permissions'] is True
                assert checks['directory_structure_valid'] is True
                
                # Verify performance metrics
                perf_metrics = result['performance_metrics']
                assert 'total_duration_ms' in perf_metrics
                assert 'git_validation_duration_ms' in perf_metrics
                assert 'structure_validation_duration_ms' in perf_metrics
                assert perf_metrics['total_duration_ms'] > 0
                
                # Verify repository info
                repo_info = result['repository_info']
                assert repo_info['cache_path'] == str(cache_path)
                assert repo_info['repository_size_bytes'] > 0
                assert repo_info['file_count'] == 2  # README.md and main.py
                assert repo_info['remote_url'] == "https://github.com/user/test-repo.git"
                assert 'last_commit' in repo_info
                
                # Verify logging
                log_calls = mock_log_info.call_args_list
                start_call = next((call for call in log_calls
                                 if "Starting repository clone validation" in call[0][0]), None)
                assert start_call is not None
                assert start_call[1]['project_id'] == project_id
                assert start_call[1]['execution_id'] == execution_id
                
                completed_call = next((call for call in log_calls
                                     if "completed successfully" in call[0][0]), None)
                assert completed_call is not None
                assert completed_call[1]['validation_status'] == 'valid'
    
    def test_validate_clone_repository_not_found(self, cache_manager):
        """Test validation when repository is not found in cache."""
        repository_url = "https://github.com/user/nonexistent-repo.git"
        project_id = "test_project_789"
        execution_id = "test_execution_012"
        
        with patch.object(cache_manager.logger, 'warn') as mock_log_warn:
            result = cache_manager.validate_clone(
                repository_url=repository_url,
                project_id=project_id,
                execution_id=execution_id
            )
            
            # Verify result indicates repository not found
            assert result['is_valid'] is False
            assert result['repository_url'] == repository_url
            assert result['cache_path'] is None
            assert result['validation_status'] == 'not_found'
            assert result['validation_checks'] == {}
            assert result['repository_info'] == {}
            assert result['error_details'] == ['Repository not found in cache']
            
            # Verify performance metrics are present
            assert 'performance_metrics' in result
            assert result['performance_metrics']['total_duration_ms'] > 0
            assert result['performance_metrics']['git_validation_duration_ms'] == 0.0
            
            # Verify warning logging
            mock_log_warn.assert_called_once()
            warn_call = mock_log_warn.call_args
            assert "not found in cache" in warn_call[0][0]
            assert warn_call[1]['status'] == LogStatus.FAILED
    
    def test_validate_clone_missing_git_directory(self, cache_manager):
        """Test validation when .git directory is missing."""
        repository_url = "https://github.com/user/no-git-repo.git"
        
        # Create cache directory without .git directory
        cache_path = cache_manager.create_cache_directory(repository_url)
        (cache_path / 'README.md').write_text('# Test Repository')
        
        with patch.object(cache_manager.logger, 'warn') as mock_log_warn:
            result = cache_manager.validate_clone(repository_url)
            
            # Verify result indicates invalid repository
            assert result['is_valid'] is False
            assert result['validation_status'] == 'invalid'
            assert result['validation_checks']['git_directory_exists'] is False
            assert '.git directory not found' in result['error_details']
            
            # Verify warning logging
            mock_log_warn.assert_called_once()
            warn_call = mock_log_warn.call_args
            assert "completed with issues" in warn_call[0][0]
    
    def test_validate_clone_git_status_fails(self, cache_manager):
        """Test validation when git status command fails."""
        repository_url = "https://github.com/user/corrupt-repo.git"
        
        # Create cache directory with .git directory
        cache_path = cache_manager.create_cache_directory(repository_url)
        git_dir = cache_path / '.git'
        git_dir.mkdir()
        
        def mock_failing_git_status(*args, **kwargs):
            command = args[0]
            if command[0] == "git" and command[1] == "status":
                mock_result = Mock()
                mock_result.returncode = 128
                mock_result.stdout = ""
                mock_result.stderr = "fatal: not a git repository"
                return mock_result
            return Mock(returncode=0, stdout="", stderr="")
        
        with patch('subprocess.run', side_effect=mock_failing_git_status):
            result = cache_manager.validate_clone(repository_url)
            
            # Verify result indicates invalid repository
            assert result['is_valid'] is False
            assert result['validation_status'] == 'invalid'
            assert result['validation_checks']['git_directory_exists'] is True
            assert result['validation_checks']['git_status_works'] is False
            assert any('git status failed' in error for error in result['error_details'])
    
    def test_validate_clone_remote_origin_mismatch(self, cache_manager):
        """Test validation when remote origin URL doesn't match."""
        repository_url = "https://github.com/user/test-repo.git"
        
        # Create cache directory with .git directory
        cache_path = cache_manager.create_cache_directory(repository_url)
        git_dir = cache_path / '.git'
        git_dir.mkdir()
        
        def mock_mismatched_remote(*args, **kwargs):
            command = args[0]
            if command[0] == "git":
                if command[1] == "status":
                    return Mock(returncode=0, stdout="", stderr="")
                elif command[1] == "remote" and command[2] == "get-url":
                    mock_result = Mock()
                    mock_result.returncode = 0
                    mock_result.stdout = "https://github.com/different/repo.git\n"
                    mock_result.stderr = ""
                    return mock_result
                elif command[1] == "fsck":
                    return Mock(returncode=0, stdout="", stderr="")
            return Mock(returncode=0, stdout="", stderr="")
        
        with patch('subprocess.run', side_effect=mock_mismatched_remote):
            result = cache_manager.validate_clone(repository_url)
            
            # Verify result indicates invalid repository
            assert result['is_valid'] is False
            assert result['validation_status'] == 'invalid'
            assert result['validation_checks']['remote_origin_configured'] is False
            assert any('Remote origin URL mismatch' in error for error in result['error_details'])
    
    def test_validate_clone_git_fsck_fails(self, cache_manager):
        """Test validation when git fsck detects corruption."""
        repository_url = "https://github.com/user/corrupted-repo.git"
        
        # Create cache directory with .git directory
        cache_path = cache_manager.create_cache_directory(repository_url)
        git_dir = cache_path / '.git'
        git_dir.mkdir()
        
        def mock_corrupted_repo(*args, **kwargs):
            command = args[0]
            if command[0] == "git":
                if command[1] == "status":
                    return Mock(returncode=0, stdout="", stderr="")
                elif command[1] == "remote" and command[2] == "get-url":
                    return Mock(returncode=0, stdout=f"{repository_url}\n", stderr="")
                elif command[1] == "fsck":
                    mock_result = Mock()
                    mock_result.returncode = 1
                    mock_result.stdout = ""
                    mock_result.stderr = "error: object file is empty"
                    return mock_result
            return Mock(returncode=0, stdout="", stderr="")
        
        with patch('subprocess.run', side_effect=mock_corrupted_repo):
            result = cache_manager.validate_clone(repository_url)
            
            # Repository should still be considered valid since fsck is not critical
            # (only git_directory_exists, git_status_works, remote_origin_configured, directory_structure_valid are critical)
            assert result['is_valid'] is True
            assert result['validation_checks']['repository_not_corrupted'] is False
            assert any('git fsck failed' in error for error in result['error_details'])
    
    def test_validate_clone_timeout_handling(self, cache_manager):
        """Test validation with git command timeouts."""
        repository_url = "https://github.com/user/slow-repo.git"
        timeout_seconds = 2
        
        # Create cache directory with .git directory
        cache_path = cache_manager.create_cache_directory(repository_url)
        git_dir = cache_path / '.git'
        git_dir.mkdir()
        
        def mock_timeout_git(*args, **kwargs):
            command = args[0]
            if command[0] == "git" and command[1] == "status":
                raise subprocess.TimeoutExpired("git", timeout_seconds)
            return Mock(returncode=0, stdout="", stderr="")
        
        with patch('subprocess.run', side_effect=mock_timeout_git):
            result = cache_manager.validate_clone(
                repository_url=repository_url,
                timeout_seconds=timeout_seconds
            )
            
            # Verify result indicates invalid repository due to timeout
            assert result['is_valid'] is False
            assert result['validation_status'] == 'invalid'
            assert result['validation_checks']['git_status_works'] is False
            assert any(f'timed out after {timeout_seconds} seconds' in error for error in result['error_details'])
    
    def test_validate_clone_invalid_url(self, cache_manager):
        """Test validation with invalid repository URL."""
        invalid_url = "ftp://invalid.com/repo"
        
        with pytest.raises(RepositoryError) as exc_info:
            cache_manager.validate_clone(invalid_url)
        
        assert "Unsupported URL scheme" in str(exc_info.value)
        assert exc_info.value.repository_url == invalid_url
    
    def test_validate_clone_performance_requirements(self, cache_manager, mock_git_commands):
        """Test that clone validation meets performance requirements (≤2s)."""
        repository_url = "https://github.com/user/performance-test.git"
        
        # Create cache directory with .git directory
        cache_path = cache_manager.create_cache_directory(repository_url)
        git_dir = cache_path / '.git'
        git_dir.mkdir()
        (cache_path / 'test_file.txt').write_text('test content')
        
        with patch('subprocess.run', side_effect=mock_git_commands):
            start_time = time.time()
            result = cache_manager.validate_clone(repository_url)
            duration = time.time() - start_time
            
            assert duration < 2.0, f"Validation took {duration}s, exceeds 2s requirement"
            assert result['performance_metrics']['total_duration_ms'] < 2000
            assert result['is_valid'] is True
    
    def test_validate_clone_with_auth_token_url_matching(self, cache_manager):
        """Test URL matching with authentication tokens."""
        repository_url = "https://github.com/user/private-repo.git"
        
        # Create cache directory with .git directory
        cache_path = cache_manager.create_cache_directory(repository_url)
        git_dir = cache_path / '.git'
        git_dir.mkdir()
        
        def mock_auth_token_remote(*args, **kwargs):
            command = args[0]
            if command[0] == "git":
                if command[1] == "status":
                    return Mock(returncode=0, stdout="", stderr="")
                elif command[1] == "remote" and command[2] == "get-url":
                    # Remote URL has auth token
                    mock_result = Mock()
                    mock_result.returncode = 0
                    mock_result.stdout = "https://token123@github.com/user/private-repo.git\n"
                    mock_result.stderr = ""
                    return mock_result
                elif command[1] == "fsck":
                    return Mock(returncode=0, stdout="", stderr="")
            return Mock(returncode=0, stdout="", stderr="")
        
        with patch('subprocess.run', side_effect=mock_auth_token_remote):
            result = cache_manager.validate_clone(repository_url)
            
            # Should match despite auth token difference
            assert result['is_valid'] is True
            assert result['validation_checks']['remote_origin_configured'] is True
    
    def test_validate_remote_url_match_helper(self, cache_manager):
        """Test the _validate_remote_url_match helper method."""
        test_cases = [
            # Basic matching
            ("https://github.com/user/repo.git", "https://github.com/user/repo.git", True),
            # Auth token differences
            ("https://github.com/user/repo.git", "https://token@github.com/user/repo.git", True),
            ("https://token1@github.com/user/repo.git", "https://token2@github.com/user/repo.git", True),
            # Case insensitive
            ("https://GitHub.com/User/Repo.git", "https://github.com/user/repo.git", True),
            # Different repos
            ("https://github.com/user/repo1.git", "https://github.com/user/repo2.git", False),
            # Different hosts
            ("https://github.com/user/repo.git", "https://gitlab.com/user/repo.git", False),
        ]
        
        for expected_url, actual_url, should_match in test_cases:
            result = cache_manager._validate_remote_url_match(expected_url, actual_url)
            assert result == should_match, f"URL matching failed for {expected_url} vs {actual_url}"
    
    def test_validate_file_permissions_helper(self, cache_manager, temp_cache_root):
        """Test the _validate_file_permissions helper method."""
        # Create test directory with files
        test_dir = temp_cache_root / "test_permissions"
        test_dir.mkdir(mode=0o755)
        
        # Create test files with proper permissions
        test_file1 = test_dir / "file1.txt"
        test_file1.write_text("content1")
        test_file1.chmod(0o644)
        
        test_file2 = test_dir / "file2.txt"
        test_file2.write_text("content2")
        test_file2.chmod(0o644)
        
        # Should validate successfully
        result = cache_manager._validate_file_permissions(test_dir)
        assert result is True
    
    def test_validate_file_permissions_invalid(self, cache_manager, temp_cache_root):
        """Test file permissions validation with invalid permissions."""
        # Create test directory without read permissions
        test_dir = temp_cache_root / "test_invalid_permissions"
        test_dir.mkdir(mode=0o000)  # No permissions
        
        try:
            result = cache_manager._validate_file_permissions(test_dir)
            # Should return False due to lack of permissions
            assert result is False
        finally:
            # Restore permissions for cleanup
            test_dir.chmod(0o755)
    
    def test_validate_clone_structured_logging_fields(self, cache_manager, mock_git_commands):
        """Test that validation includes all required structured logging fields."""
        repository_url = "https://github.com/user/logging-test.git"
        project_id = "logging_project_456"
        execution_id = "logging_execution_789"
        
        # Create cache directory with .git directory
        cache_path = cache_manager.create_cache_directory(repository_url)
        git_dir = cache_path / '.git'
        git_dir.mkdir()
        
        with patch('subprocess.run', side_effect=mock_git_commands):
            with patch.object(cache_manager.logger, 'info') as mock_log_info:
                cache_manager.validate_clone(
                    repository_url=repository_url,
                    project_id=project_id,
                    execution_id=execution_id
                )
                
                # Verify structured logging fields
                log_calls = mock_log_info.call_args_list
                validation_related_calls = []
                for call in log_calls:
                    kwargs = call[1]
                    if 'repository_url' in kwargs and kwargs['repository_url'] == repository_url:
                        validation_related_calls.append(call)
                    elif any(keyword in call[0][0].lower() for keyword in ['validation', 'starting repository']):
                        validation_related_calls.append(call)
                
                # Should have at least one validation-related call
                assert len(validation_related_calls) > 0
                
                # Check that at least one call has the required fields
                found_required_fields = False
                for call in validation_related_calls:
                    kwargs = call[1]
                    if ('correlation_id' in kwargs and 'project_id' in kwargs and
                        'execution_id' in kwargs and 'status' in kwargs):
                        found_required_fields = True
                        break
                
                assert found_required_fields, "Expected at least one log call with required structured logging fields"
    
    def test_validate_clone_concurrent_safety(self, cache_manager, mock_git_commands):
        """Test validation safety under concurrent access scenarios."""
        repository_url = "https://github.com/user/concurrent-validation.git"
        
        # Create cache directory with .git directory
        cache_path = cache_manager.create_cache_directory(repository_url)
        git_dir = cache_path / '.git'
        git_dir.mkdir()
        (cache_path / 'concurrent.txt').write_text('concurrent test')
        
        with patch('subprocess.run', side_effect=mock_git_commands):
            # Simulate concurrent validation calls
            results = []
            for i in range(3):
                result = cache_manager.validate_clone(
                    repository_url=repository_url,
                    project_id=f"concurrent_project_{i}",
                    execution_id=f"concurrent_execution_{i}"
                )
                results.append(result)
            
            # All results should be consistent
            for result in results:
                assert result['is_valid'] is True
                assert result['validation_status'] == 'valid'
                assert result['cache_path'] == str(cache_path)
                assert result['performance_metrics']['total_duration_ms'] < 2000
    
    def test_validate_clone_error_handling(self, cache_manager):
        """Test validation error handling with unexpected exceptions."""
        repository_url = "https://github.com/user/error-test.git"
        
        # Create cache directory
        cache_path = cache_manager.create_cache_directory(repository_url)
        git_dir = cache_path / '.git'
        git_dir.mkdir()
        
        # Mock subprocess to raise unexpected exception
        with patch('subprocess.run', side_effect=Exception("Unexpected error")):
            with patch.object(cache_manager.logger, 'error') as mock_log_error:
                with pytest.raises(RepositoryError) as exc_info:
                    cache_manager.validate_clone(repository_url)
                
                assert "Repository clone validation failed" in str(exc_info.value)
                assert exc_info.value.repository_url == repository_url
                
                # Verify error logging
                mock_log_error.assert_called()
                error_calls = mock_log_error.call_args_list
                unexpected_error_call = next((call for call in error_calls
                                            if "unexpected error" in call[0][0]), None)
                assert unexpected_error_call is not None
                assert unexpected_error_call[1]['status'] == LogStatus.FAILED
    
    def test_validate_clone_integration_with_clone_operation(self, cache_manager, mock_git_commands):
        """Test integration between clone and validation operations."""
        repository_url = "https://github.com/user/integration-test.git"
        project_id = "integration_project_123"
        execution_id = "integration_execution_456"
        
        # Mock successful git clone
        mock_clone_result = Mock()
        mock_clone_result.returncode = 0
        mock_clone_result.stdout = "Cloning into 'repo'..."
        mock_clone_result.stderr = ""
        
        def create_test_repo_on_clone(*args, **kwargs):
            command = args[0]
            if command[0] == "git" and command[1] == "clone":
                # Simulate git clone creating repository structure
                cache_key = cache_manager._generate_cache_key(repository_url)
                cache_path = cache_manager.CACHE_ROOT / cache_key
                if cache_path.exists():
                    git_dir = cache_path / '.git'
                    git_dir.mkdir(exist_ok=True)
                    (git_dir / 'config').write_text('[core]\n\trepositoryformatversion = 0')
                    (cache_path / 'README.md').write_text('# Integration Test')
                return mock_clone_result
            else:
                return mock_git_commands(*args, **kwargs)
        
        with patch('subprocess.run', side_effect=create_test_repo_on_clone):
            # 1. Clone repository
            clone_result = cache_manager.clone_repository(
                repository_url=repository_url,
                project_id=project_id,
                execution_id=execution_id
            )
            
            assert clone_result['success'] is True
            assert clone_result['clone_status'] == 'cloned'
            
            # 2. Validate cloned repository
            validation_result = cache_manager.validate_clone(
                repository_url=repository_url,
                project_id=project_id,
                execution_id=execution_id
            )
            
            assert validation_result['is_valid'] is True
            assert validation_result['validation_status'] == 'valid'
            assert validation_result['cache_path'] == clone_result['cache_path']
            
            # 3. Verify all critical validation checks pass
            checks = validation_result['validation_checks']
            critical_checks = [
                'git_directory_exists',
                'git_status_works',
                'remote_origin_configured',
                'directory_structure_valid'
            ]
            
            for check in critical_checks:
                assert checks[check] is True, f"Critical check {check} failed"


class TestRepositoryFetchLatestChanges:
    """Test suite for repository fetch latest changes functionality (Task 4.3.1)."""
    
    @pytest.fixture
    def temp_cache_root(self):
        """Create a temporary directory for cache testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        # Cleanup
        if Path(temp_dir).exists():
            shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def cache_manager(self, temp_cache_root):
        """Create a cache manager with temporary cache root."""
        manager = RepositoryCacheManager(correlation_id="test_fetch_123")
        # Override the CACHE_ROOT instance variable to use temp directory for testing
        manager.CACHE_ROOT = temp_cache_root
        return manager
    
    @pytest.fixture
    def mock_git_repo(self, cache_manager):
        """Create a mock git repository in cache."""
        repository_url = "https://github.com/user/test-repo.git"
        cache_path = cache_manager.create_cache_directory(repository_url)
        
        # Create .git directory to simulate a valid git repository
        git_dir = cache_path / '.git'
        git_dir.mkdir()
        (git_dir / 'config').write_text('[core]\n\trepositoryformatversion = 0')
        
        # Add some test files
        (cache_path / 'README.md').write_text('# Test Repository')
        (cache_path / 'src').mkdir()
        (cache_path / 'src' / 'main.py').write_text('print("Hello World")')
        
        return repository_url, cache_path
    
    @pytest.fixture
    def mock_successful_git_fetch(self):
        """Mock successful git fetch and pull operations."""
        def mock_subprocess_run(*args, **kwargs):
            command = args[0]
            if command[0] == "git":
                if command[1] == "fetch":
                    mock_result = Mock()
                    mock_result.returncode = 0
                    mock_result.stdout = "From https://github.com/user/test-repo\n   abc123..def456  main       -> origin/main"
                    mock_result.stderr = ""
                    return mock_result
                elif command[1] == "status":
                    mock_result = Mock()
                    mock_result.returncode = 0
                    mock_result.stdout = ""
                    mock_result.stderr = ""
                    return mock_result
                elif command[1] == "rev-list":
                    mock_result = Mock()
                    mock_result.returncode = 0
                    mock_result.stdout = "0\t2\n"  # 0 ahead, 2 behind
                    mock_result.stderr = ""
                    return mock_result
                elif command[1] == "pull":
                    mock_result = Mock()
                    mock_result.returncode = 0
                    mock_result.stdout = "Updating abc123..def456\nFast-forward\n 2 files changed, 10 insertions(+), 2 deletions(-)"
                    mock_result.stderr = ""
                    return mock_result
            
            # Default mock for other commands
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            return mock_result
        
        return mock_subprocess_run
    
    @pytest.fixture
    def mock_up_to_date_git_fetch(self):
        """Mock git fetch when repository is up to date."""
        def mock_subprocess_run(*args, **kwargs):
            command = args[0]
            if command[0] == "git":
                if command[1] == "fetch":
                    mock_result = Mock()
                    mock_result.returncode = 0
                    mock_result.stdout = ""
                    mock_result.stderr = ""
                    return mock_result
                elif command[1] == "status":
                    mock_result = Mock()
                    mock_result.returncode = 0
                    mock_result.stdout = ""
                    mock_result.stderr = ""
                    return mock_result
                elif command[1] == "rev-list":
                    mock_result = Mock()
                    mock_result.returncode = 0
                    mock_result.stdout = "0\t0\n"  # 0 ahead, 0 behind
                    mock_result.stderr = ""
                    return mock_result
            
            # Default mock for other commands
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            return mock_result
        
        return mock_subprocess_run
    
    def test_fetch_latest_changes_success_with_updates(self, cache_manager, mock_git_repo, mock_successful_git_fetch):
        """Test successful fetch operation with updates available."""
        repository_url, cache_path = mock_git_repo
        project_id = "test_project_123"
        execution_id = "test_execution_456"
        
        with patch('subprocess.run', side_effect=mock_successful_git_fetch):
            with patch.object(cache_manager.logger, 'info') as mock_log_info:
                result = cache_manager.fetch_latest_changes(
                    repository_url=repository_url,
                    project_id=project_id,
                    execution_id=execution_id
                )
                
                # Verify result structure
                assert isinstance(result, dict)
                assert result['success'] is True
                assert result['repository_url'] == repository_url
                assert result['cache_path'] == str(cache_path)
                assert result['fetch_status'] == 'updated'
                assert result['changes_fetched'] is True
                assert result['commits_ahead'] == 0
                assert result['commits_behind'] == 2
                assert result['files_changed'] == 2
                assert 'performance_metrics' in result
                assert 'repository_size_bytes' in result
                
                # Verify performance metrics
                perf_metrics = result['performance_metrics']
                assert 'total_duration_ms' in perf_metrics
                assert 'git_fetch_duration_ms' in perf_metrics
                assert 'validation_duration_ms' in perf_metrics
                assert perf_metrics['total_duration_ms'] > 0
                assert perf_metrics['git_fetch_duration_ms'] >= 0
                
                # Verify repository size is positive
                assert result['repository_size_bytes'] > 0
                
                # Verify logging
                log_calls = mock_log_info.call_args_list
                start_call = next((call for call in log_calls
                                 if "Starting repository fetch latest changes operation" in call[0][0]), None)
                assert start_call is not None
                assert start_call[1]['project_id'] == project_id
                assert start_call[1]['execution_id'] == execution_id
                
                completed_call = next((call for call in log_calls
                                     if "completed successfully" in call[0][0]), None)
                assert completed_call is not None
                assert completed_call[1]['fetch_status'] == 'updated'
                assert completed_call[1]['changes_fetched'] is True
    
    def test_fetch_latest_changes_up_to_date(self, cache_manager, mock_git_repo, mock_up_to_date_git_fetch):
        """Test fetch operation when repository is already up to date."""
        repository_url, cache_path = mock_git_repo
        project_id = "test_project_789"
        execution_id = "test_execution_012"
        
        with patch('subprocess.run', side_effect=mock_up_to_date_git_fetch):
            with patch.object(cache_manager.logger, 'info') as mock_log_info:
                result = cache_manager.fetch_latest_changes(
                    repository_url=repository_url,
                    project_id=project_id,
                    execution_id=execution_id
                )
                
                # Verify result indicates up to date
                assert result['success'] is True
                assert result['fetch_status'] == 'up_to_date'
                assert result['changes_fetched'] is False
                assert result['commits_ahead'] == 0
                assert result['commits_behind'] == 0
                assert result['files_changed'] == 0
                
                # Verify logging
                log_calls = mock_log_info.call_args_list
                completed_call = next((call for call in log_calls
                                     if "completed successfully" in call[0][0]), None)
                assert completed_call is not None
                assert completed_call[1]['fetch_status'] == 'up_to_date'
                assert completed_call[1]['changes_fetched'] is False
    
    def test_fetch_latest_changes_repository_not_found(self, cache_manager):
        """Test fetch operation when repository is not found in cache."""
        repository_url = "https://github.com/user/nonexistent-repo.git"
        project_id = "test_project_345"
        execution_id = "test_execution_678"
        
        with patch.object(cache_manager.logger, 'warn') as mock_log_warn:
            result = cache_manager.fetch_latest_changes(
                repository_url=repository_url,
                project_id=project_id,
                execution_id=execution_id
            )
            
            # Verify result indicates repository not found
            assert result['success'] is False
            assert result['repository_url'] == repository_url
            assert result['cache_path'] is None
            assert result['fetch_status'] == 'not_found'
            assert result['changes_fetched'] is False
            assert result['commits_ahead'] == 0
            assert result['commits_behind'] == 0
            assert result['files_changed'] == 0
            assert result['repository_size_bytes'] == 0
            
            # Verify performance metrics are present
            assert 'performance_metrics' in result
            assert result['performance_metrics']['total_duration_ms'] > 0
            assert result['performance_metrics']['git_fetch_duration_ms'] == 0.0
            
            # Verify warning logging
            mock_log_warn.assert_called_once()
            warn_call = mock_log_warn.call_args
            assert "not found in cache" in warn_call[0][0]
            assert warn_call[1]['status'] == LogStatus.FAILED
    
    def test_fetch_latest_changes_invalid_git_repository(self, cache_manager):
        """Test fetch operation when cache directory exists but is not a valid git repository."""
        repository_url = "https://github.com/user/invalid-git-repo.git"
        
        # Create cache directory without .git directory
        cache_path = cache_manager.create_cache_directory(repository_url)
        (cache_path / 'README.md').write_text('# Not a git repository')
        
        with pytest.raises(RepositoryError) as exc_info:
            cache_manager.fetch_latest_changes(repository_url)
        
        assert "not a valid git repository" in str(exc_info.value)
        assert exc_info.value.repository_url == repository_url
    
    def test_fetch_latest_changes_git_fetch_failure(self, cache_manager, mock_git_repo):
        """Test fetch operation when git fetch command fails."""
        repository_url, cache_path = mock_git_repo
        
        def mock_failing_git_fetch(*args, **kwargs):
            command = args[0]
            if command[0] == "git" and command[1] == "fetch":
                mock_result = Mock()
                mock_result.returncode = 128
                mock_result.stdout = ""
                mock_result.stderr = "fatal: unable to access 'https://github.com/user/test-repo.git/': Could not resolve host"
                return mock_result
            return Mock(returncode=0, stdout="", stderr="")
        
        with patch('subprocess.run', side_effect=mock_failing_git_fetch):
            with patch.object(cache_manager.logger, 'error') as mock_log_error:
                with pytest.raises(RepositoryError) as exc_info:
                    cache_manager.fetch_latest_changes(repository_url)
                
                assert "Git fetch failed" in str(exc_info.value)
                assert exc_info.value.repository_url == repository_url
                
                # Verify error logging
                mock_log_error.assert_called()
                error_calls = mock_log_error.call_args_list
                git_error_call = next((call for call in error_calls
                                     if "Git fetch operation failed" in call[0][0]), None)
                assert git_error_call is not None
                assert git_error_call[1]['status'] == LogStatus.FAILED
                assert git_error_call[1]['git_return_code'] == 128
    
    def test_fetch_latest_changes_git_pull_failure(self, cache_manager, mock_git_repo):
        """Test fetch operation when git pull command fails."""
        repository_url, cache_path = mock_git_repo
        
        def mock_failing_git_pull(*args, **kwargs):
            command = args[0]
            if command[0] == "git":
                if command[1] == "fetch":
                    return Mock(returncode=0, stdout="", stderr="")
                elif command[1] == "status":
                    return Mock(returncode=0, stdout="", stderr="")
                elif command[1] == "rev-list":
                    return Mock(returncode=0, stdout="0\t1\n", stderr="")  # 1 behind
                elif command[1] == "pull":
                    mock_result = Mock()
                    mock_result.returncode = 1
                    mock_result.stdout = ""
                    mock_result.stderr = "error: Your local changes to the following files would be overwritten by merge"
                    return mock_result
            return Mock(returncode=0, stdout="", stderr="")
        
        with patch('subprocess.run', side_effect=mock_failing_git_pull):
            with patch.object(cache_manager.logger, 'error') as mock_log_error:
                with pytest.raises(RepositoryError) as exc_info:
                    cache_manager.fetch_latest_changes(repository_url)
                
                assert "Git pull failed" in str(exc_info.value)
                
                # Verify error logging
                mock_log_error.assert_called()
                error_calls = mock_log_error.call_args_list
                git_error_call = next((call for call in error_calls
                                     if "Git pull operation failed" in call[0][0]), None)
                assert git_error_call is not None
                assert git_error_call[1]['status'] == LogStatus.FAILED
    
    def test_fetch_latest_changes_timeout(self, cache_manager, mock_git_repo):
        """Test fetch operation with timeout."""
        repository_url, cache_path = mock_git_repo
        timeout_seconds = 5
        
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired("git", timeout_seconds)):
            with patch.object(cache_manager.logger, 'error') as mock_log_error:
                with pytest.raises(RepositoryError) as exc_info:
                    cache_manager.fetch_latest_changes(
                        repository_url=repository_url,
                        timeout_seconds=timeout_seconds
                    )
                
                assert "timed out" in str(exc_info.value)
                assert f"{timeout_seconds} seconds" in str(exc_info.value)
                
                # Verify error logging
                mock_log_error.assert_called()
                error_calls = mock_log_error.call_args_list
                timeout_call = next((call for call in error_calls
                                   if "timed out" in call[0][0]), None)
                assert timeout_call is not None
                assert timeout_call[1]['timeout_seconds'] == timeout_seconds
    
    def test_fetch_latest_changes_invalid_url(self, cache_manager):
        """Test fetch operation with invalid repository URL."""
        invalid_url = "ftp://invalid.com/repo"
        
        with pytest.raises(RepositoryError) as exc_info:
            cache_manager.fetch_latest_changes(invalid_url)
        
        assert "Unsupported URL scheme" in str(exc_info.value)
        assert exc_info.value.repository_url == invalid_url
    
    def test_fetch_latest_changes_with_auth_token(self, cache_manager, mock_git_repo, mock_successful_git_fetch):
        """Test fetch operation with authentication token."""
        repository_url, cache_path = mock_git_repo
        auth_token = "ghp_test_token_123"
        
        with patch('subprocess.run', side_effect=mock_successful_git_fetch):
            result = cache_manager.fetch_latest_changes(
                repository_url=repository_url,
                auth_token=auth_token
            )
            
            assert result['success'] is True
            assert result['fetch_status'] == 'updated'
            # Note: Auth token handling would be implemented in future enhancement
            # For now, we just verify the method accepts the parameter
    
    def test_fetch_latest_changes_custom_timeout(self, cache_manager, mock_git_repo, mock_successful_git_fetch):
        """Test fetch operation with custom timeout."""
        repository_url, cache_path = mock_git_repo
        custom_timeout = 60
        
        with patch('subprocess.run', side_effect=mock_successful_git_fetch) as mock_subprocess:
            result = cache_manager.fetch_latest_changes(
                repository_url=repository_url,
                timeout_seconds=custom_timeout
            )
            
            assert result['success'] is True
            
            # Verify custom timeout was used in subprocess calls
            for call in mock_subprocess.call_args_list:
                if 'timeout' in call[1]:
                    assert call[1]['timeout'] == custom_timeout
    
    def test_fetch_latest_changes_performance_requirements(self, cache_manager, mock_git_repo, mock_successful_git_fetch):
        """Test that fetch operation meets performance requirements (≤2s)."""
        repository_url, cache_path = mock_git_repo
        
        with patch('subprocess.run', side_effect=mock_successful_git_fetch):
            start_time = time.time()
            result = cache_manager.fetch_latest_changes(repository_url)
            duration = time.time() - start_time
            
            assert duration < 2.0, f"Fetch operation took {duration}s, exceeds 2s requirement"
            assert result['performance_metrics']['total_duration_ms'] < 2000
            assert result['success'] is True
    
    def test_fetch_latest_changes_structured_logging_fields(self, cache_manager, mock_git_repo, mock_successful_git_fetch):
        """Test that fetch operation includes all required structured logging fields."""
        repository_url, cache_path = mock_git_repo
        project_id = "logging_project_456"
        execution_id = "logging_execution_789"
        
        with patch('subprocess.run', side_effect=mock_successful_git_fetch):
            with patch.object(cache_manager.logger, 'info') as mock_log_info:
                cache_manager.fetch_latest_changes(
                    repository_url=repository_url,
                    project_id=project_id,
                    execution_id=execution_id
                )
                
                # Verify structured logging fields
                log_calls = mock_log_info.call_args_list
                fetch_related_calls = []
                for call in log_calls:
                    kwargs = call[1]
                    if 'repository_url' in kwargs and kwargs['repository_url'] == repository_url:
                        fetch_related_calls.append(call)
                    elif any(keyword in call[0][0].lower() for keyword in ['fetch', 'starting repository']):
                        fetch_related_calls.append(call)
                
                # Should have at least one fetch-related call
                assert len(fetch_related_calls) > 0
                
                # Check that at least one call has the required fields
                found_required_fields = False
                for call in fetch_related_calls:
                    kwargs = call[1]
                    if ('correlation_id' in kwargs and 'project_id' in kwargs and
                        'execution_id' in kwargs and 'status' in kwargs):
                        found_required_fields = True
                        break
                
                assert found_required_fields, "Expected at least one log call with required structured logging fields"
    
    def test_fetch_latest_changes_concurrent_safety(self, cache_manager, mock_git_repo, mock_successful_git_fetch):
        """Test fetch operation safety under concurrent access scenarios."""
        repository_url, cache_path = mock_git_repo
        
        with patch('subprocess.run', side_effect=mock_successful_git_fetch):
            # Simulate concurrent fetch calls
            results = []
            for i in range(3):
                result = cache_manager.fetch_latest_changes(
                    repository_url=repository_url,
                    project_id=f"concurrent_project_{i}",
                    execution_id=f"concurrent_execution_{i}"
                )
                results.append(result)
            
            # All results should be consistent
            for result in results:
                assert result['success'] is True
                assert result['cache_path'] == str(cache_path)
                assert result['performance_metrics']['total_duration_ms'] < 2000
    
    def test_fetch_latest_changes_error_handling(self, cache_manager, mock_git_repo):
        """Test fetch operation error handling with unexpected exceptions."""
        repository_url, cache_path = mock_git_repo
        
        # Mock subprocess to raise unexpected exception
        with patch('subprocess.run', side_effect=Exception("Unexpected error")):
            with patch.object(cache_manager.logger, 'error') as mock_log_error:
                with pytest.raises(RepositoryError) as exc_info:
                    cache_manager.fetch_latest_changes(repository_url)
                
                assert "Repository fetch latest changes failed" in str(exc_info.value)
                assert exc_info.value.repository_url == repository_url
                
                # Verify error logging
                mock_log_error.assert_called()
                error_calls = mock_log_error.call_args_list
                unexpected_error_call = next((call for call in error_calls
                                            if "unexpected error" in call[0][0]), None)
                assert unexpected_error_call is not None
                assert unexpected_error_call[1]['status'] == LogStatus.FAILED
    
    def test_fetch_latest_changes_integration_with_existing_methods(self, cache_manager, mock_successful_git_fetch):
        """Test integration between fetch and other repository operations."""
        repository_url = "https://github.com/user/integration-test.git"
        project_id = "integration_project_123"
        execution_id = "integration_execution_456"
        
        # Mock successful git clone
        mock_clone_result = Mock()
        mock_clone_result.returncode = 0
        mock_clone_result.stdout = "Cloning into 'repo'..."
        mock_clone_result.stderr = ""
        
        def create_test_repo_on_clone(*args, **kwargs):
            command = args[0]
            if command[0] == "git" and command[1] == "clone":
                # Simulate git clone creating repository structure
                cache_key = cache_manager._generate_cache_key(repository_url)
                cache_path = cache_manager.CACHE_ROOT / cache_key
                if cache_path.exists():
                    git_dir = cache_path / '.git'
                    git_dir.mkdir(exist_ok=True)
                    (git_dir / 'config').write_text('[core]\n\trepositoryformatversion = 0')
                    (cache_path / 'README.md').write_text('# Integration Test')
                return mock_clone_result
            else:
                return mock_successful_git_fetch(*args, **kwargs)
        
        with patch('subprocess.run', side_effect=create_test_repo_on_clone):
            # 1. Clone repository
            clone_result = cache_manager.clone_repository(
                repository_url=repository_url,
                project_id=project_id,
                execution_id=execution_id
            )
            
            assert clone_result['success'] is True
            assert clone_result['clone_status'] == 'cloned'
            
            # 2. Fetch latest changes
            fetch_result = cache_manager.fetch_latest_changes(
                repository_url=repository_url,
                project_id=project_id,
                execution_id=execution_id
            )
            
            assert fetch_result['success'] is True
            assert fetch_result['fetch_status'] == 'updated'
            assert fetch_result['cache_path'] == clone_result['cache_path']
            
            # 3. Verify repository existence check still works
            existence_result = cache_manager.check_repository_existence(
                repository_url=repository_url,
                project_id=project_id,
                execution_id=execution_id
            )
            
            assert existence_result['exists_in_cache'] is True
            assert existence_result['cache_path'] == clone_result['cache_path']


class TestRepositoryFetchValidation:
    """Test suite for repository fetch validation functionality (Task 4.3.2)."""
    
    @pytest.fixture
    def temp_cache_root(self):
        """Create a temporary directory for cache testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        # Cleanup
        if Path(temp_dir).exists():
            shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def cache_manager(self, temp_cache_root):
        """Create a cache manager with temporary cache root."""
        manager = RepositoryCacheManager(correlation_id="test_fetch_validation_123")
        # Override the CACHE_ROOT instance variable to use temp directory for testing
        manager.CACHE_ROOT = temp_cache_root
        return manager
    
    @pytest.fixture
    def mock_git_repo_with_fetch(self, cache_manager):
        """Create a mock git repository in cache with recent fetch."""
        repository_url = "https://github.com/user/test-repo.git"
        cache_path = cache_manager.create_cache_directory(repository_url)
        
        # Create .git directory to simulate a valid git repository
        git_dir = cache_path / '.git'
        git_dir.mkdir()
        (git_dir / 'config').write_text('[core]\n\trepositoryformatversion = 0')
        
        # Create FETCH_HEAD file to simulate recent fetch
        fetch_head = git_dir / 'FETCH_HEAD'
        fetch_head.write_text('abc123def456\t\tbranch \'main\' of https://github.com/user/test-repo.git')
        
        # Add some test files
        (cache_path / 'README.md').write_text('# Test Repository')
        (cache_path / 'src').mkdir()
        (cache_path / 'src' / 'main.py').write_text('print("Hello World")')
        
        return repository_url, cache_path
    
    @pytest.fixture
    def mock_successful_git_commands(self):
        """Mock successful git command responses for fetch validation."""
        def mock_subprocess_run(*args, **kwargs):
            command = args[0]
            if command[0] == "git":
                if command[1] == "status" and "--porcelain" in command:
                    mock_result = Mock()
                    mock_result.returncode = 0
                    mock_result.stdout = ""  # Clean working directory
                    mock_result.stderr = ""
                    return mock_result
                elif command[1] == "remote" and command[2] == "get-url":
                    mock_result = Mock()
                    mock_result.returncode = 0
                    mock_result.stdout = "https://github.com/user/test-repo.git\n"
                    mock_result.stderr = ""
                    return mock_result
                elif command[1] == "rev-list":
                    mock_result = Mock()
                    mock_result.returncode = 0
                    mock_result.stdout = "0\t0\n"  # 0 ahead, 0 behind (synchronized)
                    mock_result.stderr = ""
                    return mock_result
                elif command[1] == "branch" and "--show-current" in command:
                    mock_result = Mock()
                    mock_result.returncode = 0
                    mock_result.stdout = "main\n"
                    mock_result.stderr = ""
                    return mock_result
                elif command[1] == "log":
                    mock_result = Mock()
                    mock_result.returncode = 0
                    mock_result.stdout = "abc123|Initial commit|Test Author|2023-01-01 12:00:00 +0000\n"
                    mock_result.stderr = ""
                    return mock_result
            
            # Default mock for other commands
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            return mock_result
        
        return mock_subprocess_run
    
    def test_validate_fetch_operation_success(self, cache_manager, mock_git_repo_with_fetch, mock_successful_git_commands):
        """Test successful fetch operation validation with all checks passing."""
        repository_url, cache_path = mock_git_repo_with_fetch
        project_id = "test_project_123"
        execution_id = "test_execution_456"
        
        with patch('subprocess.run', side_effect=mock_successful_git_commands):
            with patch.object(cache_manager.logger, 'info') as mock_log_info:
                result = cache_manager.validate_fetch_operation(
                    repository_url=repository_url,
                    project_id=project_id,
                    execution_id=execution_id
                )
                
                # Verify result structure
                assert isinstance(result, dict)
                assert result['is_valid'] is True
                assert result['repository_url'] == repository_url
                assert result['cache_path'] == str(cache_path)
                assert result['validation_status'] == 'valid'
                assert 'validation_checks' in result
                assert 'performance_metrics' in result
                assert 'repository_info' in result
                assert 'fetch_validation' in result
                assert result['error_details'] is None
                
                # Verify validation checks
                checks = result['validation_checks']
                assert checks['git_directory_exists'] is True
                assert checks['git_status_works'] is True
                assert checks['remote_origin_configured'] is True
                assert checks['repository_synchronized'] is True
                assert checks['working_directory_clean'] is True
                assert checks['proper_permissions'] is True
                assert checks['directory_structure_valid'] is True
                
                # Verify performance metrics
                perf_metrics = result['performance_metrics']
                assert 'total_duration_ms' in perf_metrics
                assert 'git_validation_duration_ms' in perf_metrics
                assert 'fetch_validation_duration_ms' in perf_metrics
                assert 'structure_validation_duration_ms' in perf_metrics
                assert perf_metrics['total_duration_ms'] > 0
                
                # Verify repository info
                repo_info = result['repository_info']
                assert repo_info['cache_path'] == str(cache_path)
                assert repo_info['repository_size_bytes'] > 0
                assert repo_info['file_count'] == 2  # README.md and main.py
                assert repo_info['remote_url'] == "https://github.com/user/test-repo.git"
                assert repo_info['commits_ahead'] == 0
                assert repo_info['commits_behind'] == 0
                assert 'current_branch' in repo_info
                assert 'last_commit' in repo_info
                
                # Verify fetch validation
                fetch_validation = result['fetch_validation']
                assert 'last_fetch_time' in fetch_validation
                assert 'minutes_since_fetch' in fetch_validation
                assert 'fetch_recent' in fetch_validation
                
                # Verify logging
                log_calls = mock_log_info.call_args_list
                start_call = next((call for call in log_calls
                                 if "Starting repository fetch operation validation" in call[0][0]), None)
                assert start_call is not None
                assert start_call[1]['project_id'] == project_id
                assert start_call[1]['execution_id'] == execution_id
                
                completed_call = next((call for call in log_calls
                                     if "completed successfully" in call[0][0]), None)
                assert completed_call is not None
                assert completed_call[1]['validation_status'] == 'valid'
    
    def test_validate_fetch_operation_repository_not_found(self, cache_manager):
        """Test validation when repository is not found in cache."""
        repository_url = "https://github.com/user/nonexistent-repo.git"
        project_id = "test_project_789"
        execution_id = "test_execution_012"
        
        with patch.object(cache_manager.logger, 'warn') as mock_log_warn:
            result = cache_manager.validate_fetch_operation(
                repository_url=repository_url,
                project_id=project_id,
                execution_id=execution_id
            )
            
            # Verify result indicates repository not found
            assert result['is_valid'] is False
            assert result['repository_url'] == repository_url
            assert result['cache_path'] is None
            assert result['validation_status'] == 'not_found'
            assert result['validation_checks'] == {}
            assert result['repository_info'] == {}
            assert result['fetch_validation'] == {}
            assert result['error_details'] == ['Repository not found in cache']
            
            # Verify performance metrics are present
            assert 'performance_metrics' in result
            assert result['performance_metrics']['total_duration_ms'] > 0
            assert result['performance_metrics']['git_validation_duration_ms'] == 0.0
            assert result['performance_metrics']['fetch_validation_duration_ms'] == 0.0
            
            # Verify warning logging
            mock_log_warn.assert_called_once()
            warn_call = mock_log_warn.call_args
            assert "not found in cache" in warn_call[0][0]
            assert warn_call[1]['status'] == LogStatus.FAILED
    
    def test_validate_fetch_operation_missing_git_directory(self, cache_manager):
        """Test validation when .git directory is missing."""
        repository_url = "https://github.com/user/no-git-repo.git"
        
        # Create cache directory without .git directory
        cache_path = cache_manager.create_cache_directory(repository_url)
        (cache_path / 'README.md').write_text('# Test Repository')
        
        with patch.object(cache_manager.logger, 'warn') as mock_log_warn:
            result = cache_manager.validate_fetch_operation(repository_url)
            
            # Verify result indicates invalid repository
            assert result['is_valid'] is False
            assert result['validation_status'] == 'invalid'
            assert result['validation_checks']['git_directory_exists'] is False
            assert '.git directory not found' in result['error_details']
            
            # Verify warning logging
            mock_log_warn.assert_called_once()
            warn_call = mock_log_warn.call_args
            assert "completed with issues" in warn_call[0][0]
    
    def test_validate_fetch_operation_repository_behind_remote(self, cache_manager, mock_git_repo_with_fetch):
        """Test validation when repository is behind remote."""
        repository_url, cache_path = mock_git_repo_with_fetch
        
        def mock_behind_remote(*args, **kwargs):
            command = args[0]
            if command[0] == "git":
                if command[1] == "status" and "--porcelain" in command:
                    return Mock(returncode=0, stdout="", stderr="")
                elif command[1] == "remote" and command[2] == "get-url":
                    return Mock(returncode=0, stdout=f"{repository_url}\n", stderr="")
                elif command[1] == "rev-list":
                    return Mock(returncode=0, stdout="0\t2\n", stderr="")  # 0 ahead, 2 behind
            return Mock(returncode=0, stdout="", stderr="")
        
        with patch('subprocess.run', side_effect=mock_behind_remote):
            result = cache_manager.validate_fetch_operation(repository_url)
            
            # Should be invalid due to being behind remote
            assert result['is_valid'] is False
            assert result['validation_status'] == 'invalid'
            assert result['validation_checks']['repository_synchronized'] is False
            assert result['repository_info']['commits_behind'] == 2
            assert any('2 commits behind remote' in error for error in result['error_details'])
    
    def test_validate_fetch_operation_dirty_working_directory(self, cache_manager, mock_git_repo_with_fetch):
        """Test validation when working directory has uncommitted changes."""
        repository_url, cache_path = mock_git_repo_with_fetch
        
        def mock_dirty_working_dir(*args, **kwargs):
            command = args[0]
            if command[0] == "git":
                if command[1] == "status" and "--porcelain" in command:
                    return Mock(returncode=0, stdout=" M README.md\n", stderr="")  # Modified file
                elif command[1] == "remote" and command[2] == "get-url":
                    return Mock(returncode=0, stdout=f"{repository_url}\n", stderr="")
                elif command[1] == "rev-list":
                    return Mock(returncode=0, stdout="0\t0\n", stderr="")
            return Mock(returncode=0, stdout="", stderr="")
        
        with patch('subprocess.run', side_effect=mock_dirty_working_dir):
            result = cache_manager.validate_fetch_operation(repository_url)
            
            # Should be invalid due to dirty working directory
            assert result['is_valid'] is False
            assert result['validation_status'] == 'invalid'
            assert result['validation_checks']['working_directory_clean'] is False
            assert any('uncommitted changes' in error for error in result['error_details'])
    
    def test_validate_fetch_operation_no_fetch_head(self, cache_manager):
        """Test validation when FETCH_HEAD file is missing."""
        repository_url = "https://github.com/user/no-fetch-repo.git"
        
        # Create cache directory with .git but no FETCH_HEAD
        cache_path = cache_manager.create_cache_directory(repository_url)
        git_dir = cache_path / '.git'
        git_dir.mkdir()
        (git_dir / 'config').write_text('[core]\n\trepositoryformatversion = 0')
        
        def mock_no_fetch_head(*args, **kwargs):
            command = args[0]
            if command[0] == "git":
                if command[1] == "status" and "--porcelain" in command:
                    return Mock(returncode=0, stdout="", stderr="")
                elif command[1] == "remote" and command[2] == "get-url":
                    return Mock(returncode=0, stdout=f"{repository_url}\n", stderr="")
                elif command[1] == "rev-list":
                    return Mock(returncode=0, stdout="0\t0\n", stderr="")
            return Mock(returncode=0, stdout="", stderr="")
        
        with patch('subprocess.run', side_effect=mock_no_fetch_head):
            result = cache_manager.validate_fetch_operation(repository_url)
            
            # Should still be valid for critical checks, but fetch validation should indicate no recent fetch
            assert result['is_valid'] is True  # Critical checks pass
            assert result['fetch_validation']['fetch_recent'] is False
            assert any('FETCH_HEAD file not found' in error for error in result['error_details'])
    
    def test_validate_fetch_operation_git_command_timeout(self, cache_manager, mock_git_repo_with_fetch):
        """Test validation with git command timeouts."""
        repository_url, cache_path = mock_git_repo_with_fetch
        timeout_seconds = 2
        
        def mock_timeout_git(*args, **kwargs):
            command = args[0]
            if command[0] == "git" and command[1] == "status":
                raise subprocess.TimeoutExpired("git", timeout_seconds)
            return Mock(returncode=0, stdout="", stderr="")
        
        with patch('subprocess.run', side_effect=mock_timeout_git):
            result = cache_manager.validate_fetch_operation(
                repository_url=repository_url,
                timeout_seconds=timeout_seconds
            )
            
            # Verify result indicates invalid repository due to timeout
            assert result['is_valid'] is False
            assert result['validation_status'] == 'invalid'
            assert result['validation_checks']['git_status_works'] is False
            assert any(f'timed out after {timeout_seconds} seconds' in error for error in result['error_details'])
    
    def test_validate_fetch_operation_invalid_url(self, cache_manager):
        """Test validation with invalid repository URL."""
        invalid_url = "ftp://invalid.com/repo"
        
        with pytest.raises(RepositoryError) as exc_info:
            cache_manager.validate_fetch_operation(invalid_url)
        
        assert "Unsupported URL scheme" in str(exc_info.value)
        assert exc_info.value.repository_url == invalid_url
    
    def test_validate_fetch_operation_performance_requirements(self, cache_manager, mock_git_repo_with_fetch, mock_successful_git_commands):
        """Test that fetch validation meets performance requirements (≤2s)."""
        repository_url, cache_path = mock_git_repo_with_fetch
        
        with patch('subprocess.run', side_effect=mock_successful_git_commands):
            start_time = time.time()
            result = cache_manager.validate_fetch_operation(repository_url)
            duration = time.time() - start_time
            
            assert duration < 2.0, f"Validation took {duration}s, exceeds 2s requirement"
            assert result['performance_metrics']['total_duration_ms'] < 2000
            assert result['is_valid'] is True
    
    def test_validate_fetch_operation_with_warnings(self, cache_manager, mock_git_repo_with_fetch):
        """Test validation that passes critical checks but has warnings."""
        repository_url, cache_path = mock_git_repo_with_fetch
        
        def mock_with_warnings(*args, **kwargs):
            command = args[0]
            if command[0] == "git":
                if command[1] == "status" and "--porcelain" in command:
                    return Mock(returncode=0, stdout="", stderr="")
                elif command[1] == "remote" and command[2] == "get-url":
                    return Mock(returncode=0, stdout=f"{repository_url}\n", stderr="")
                elif command[1] == "rev-list":
                    return Mock(returncode=0, stdout="1\t0\n", stderr="")  # 1 ahead, 0 behind
            return Mock(returncode=0, stdout="", stderr="")
        
        with patch('subprocess.run', side_effect=mock_with_warnings):
            result = cache_manager.validate_fetch_operation(repository_url)
            
            # Should be valid since critical checks pass, but repository is ahead
            assert result['is_valid'] is True
            assert result['validation_status'] == 'valid'
            assert result['validation_checks']['repository_synchronized'] is True  # Ahead is acceptable
            assert result['repository_info']['commits_ahead'] == 1
    
    def test_validate_fetch_operation_structured_logging_fields(self, cache_manager, mock_git_repo_with_fetch, mock_successful_git_commands):
        """Test that validation includes all required structured logging fields."""
        repository_url, cache_path = mock_git_repo_with_fetch
        project_id = "logging_project_456"
        execution_id = "logging_execution_789"
        
        with patch('subprocess.run', side_effect=mock_successful_git_commands):
            with patch.object(cache_manager.logger, 'info') as mock_log_info:
                cache_manager.validate_fetch_operation(
                    repository_url=repository_url,
                    project_id=project_id,
                    execution_id=execution_id
                )
                
                # Verify structured logging fields
                log_calls = mock_log_info.call_args_list
                validation_related_calls = []
                for call in log_calls:
                    kwargs = call[1]
                    if 'repository_url' in kwargs and kwargs['repository_url'] == repository_url:
                        validation_related_calls.append(call)
                    elif any(keyword in call[0][0].lower() for keyword in ['validation', 'starting repository']):
                        validation_related_calls.append(call)
                
                # Should have at least one validation-related call
                assert len(validation_related_calls) > 0
                
                # Check that at least one call has the required fields
                found_required_fields = False
                for call in validation_related_calls:
                    kwargs = call[1]
                    if ('correlation_id' in kwargs and 'project_id' in kwargs and
                        'execution_id' in kwargs and 'status' in kwargs):
                        found_required_fields = True
                        break
                
                assert found_required_fields, "Expected at least one log call with required structured logging fields"
    
    def test_validate_fetch_operation_concurrent_safety(self, cache_manager, mock_git_repo_with_fetch, mock_successful_git_commands):
        """Test validation safety under concurrent access scenarios."""
        repository_url, cache_path = mock_git_repo_with_fetch
        
        with patch('subprocess.run', side_effect=mock_successful_git_commands):
            # Simulate concurrent validation calls
            results = []
            for i in range(3):
                result = cache_manager.validate_fetch_operation(
                    repository_url=repository_url,
                    project_id=f"concurrent_project_{i}",
                    execution_id=f"concurrent_execution_{i}"
                )
                results.append(result)
            
            # All results should be consistent
            for result in results:
                assert result['is_valid'] is True
                assert result['validation_status'] == 'valid'
                assert result['cache_path'] == str(cache_path)
                assert result['performance_metrics']['total_duration_ms'] < 2000
    
    def test_validate_fetch_operation_error_handling(self, cache_manager, mock_git_repo_with_fetch):
        """Test validation error handling with unexpected exceptions."""
        repository_url, cache_path = mock_git_repo_with_fetch
        
        # Mock subprocess to raise unexpected exception
        with patch('subprocess.run', side_effect=Exception("Unexpected error")):
            with patch.object(cache_manager.logger, 'error') as mock_log_error:
                with pytest.raises(RepositoryError) as exc_info:
                    cache_manager.validate_fetch_operation(repository_url)
                
                assert "Repository fetch validation failed" in str(exc_info.value)
                assert exc_info.value.repository_url == repository_url
                
                # Verify error logging
                mock_log_error.assert_called()
                error_calls = mock_log_error.call_args_list
                unexpected_error_call = next((call for call in error_calls
                                            if "unexpected error" in call[0][0]), None)
                assert unexpected_error_call is not None
                assert unexpected_error_call[1]['status'] == LogStatus.FAILED
    
    def test_validate_fetch_operation_integration_with_fetch_method(self, cache_manager, mock_successful_git_commands):
        """Test integration between fetch and validation operations."""
        repository_url = "https://github.com/user/integration-test.git"
        project_id = "integration_project_123"
        execution_id = "integration_execution_456"
        
        # Mock successful git clone and fetch
        mock_clone_result = Mock()
        mock_clone_result.returncode = 0
        mock_clone_result.stdout = "Cloning into 'repo'..."
        mock_clone_result.stderr = ""
        
        mock_fetch_result = Mock()
        mock_fetch_result.returncode = 0
        mock_fetch_result.stdout = "From https://github.com/user/integration-test\n   abc123..def456  main       -> origin/main"
        mock_fetch_result.stderr = ""
        
        def create_test_repo_and_fetch(*args, **kwargs):
            command = args[0]
            if command[0] == "git" and command[1] == "clone":
                # Simulate git clone creating repository structure
                cache_key = cache_manager._generate_cache_key(repository_url)
                cache_path = cache_manager.CACHE_ROOT / cache_key
                if cache_path.exists():
                    git_dir = cache_path / '.git'
                    git_dir.mkdir(exist_ok=True)
                    (git_dir / 'config').write_text('[core]\n\trepositoryformatversion = 0')
                    # Create FETCH_HEAD to simulate fetch
                    (git_dir / 'FETCH_HEAD').write_text('def456\t\tbranch \'main\' of https://github.com/user/integration-test.git')
                    (cache_path / 'README.md').write_text('# Integration Test')
                return mock_clone_result
            elif command[0] == "git" and command[1] == "fetch":
                return mock_fetch_result
            else:
                return mock_successful_git_commands(*args, **kwargs)
        
        with patch('subprocess.run', side_effect=create_test_repo_and_fetch):
            # 1. Clone repository
            clone_result = cache_manager.clone_repository(
                repository_url=repository_url,
                project_id=project_id,
                execution_id=execution_id
            )
            
            assert clone_result['success'] is True
            assert clone_result['clone_status'] == 'cloned'
            
            # 2. Fetch latest changes
            fetch_result = cache_manager.fetch_latest_changes(
                repository_url=repository_url,
                project_id=project_id,
                execution_id=execution_id
            )
            
            assert fetch_result['success'] is True
            
            # 3. Validate fetch operation
            validation_result = cache_manager.validate_fetch_operation(
                repository_url=repository_url,
                project_id=project_id,
                execution_id=execution_id
            )
            
            assert validation_result['is_valid'] is True
            assert validation_result['validation_status'] == 'valid'
            assert validation_result['cache_path'] == clone_result['cache_path']
            
            # 4. Verify all critical validation checks pass
            checks = validation_result['validation_checks']
            critical_checks = [
                'git_directory_exists',
                'git_status_works',
                'remote_origin_configured',
                'directory_structure_valid',
                'working_directory_clean'
            ]
            
            for check in critical_checks:
                assert checks[check] is True, f"Critical check {check} failed"
            
            # 5. Verify fetch validation indicates recent fetch
            fetch_validation = validation_result['fetch_validation']
            assert fetch_validation['fetch_recent'] is True