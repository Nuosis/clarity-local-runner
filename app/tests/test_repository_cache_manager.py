"""
Unit tests for Repository Cache Manager

This test suite provides comprehensive coverage for the RepositoryCacheManager
including directory operations, security validation, cleanup policies, and
integration with structured logging and error handling.
"""

import os
import shutil
import stat
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
    
    @patch('app.services.repository_cache_manager.os.chmod')
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
    
    @patch('app.services.repository_cache_manager.os.chmod')
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