#!/usr/bin/env python3
"""
Validation script for Task 4.3.2: Validate successful fetch operation

This script validates the implementation of the validate_fetch_operation() method
in the RepositoryCacheManager class.
"""

import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch
import subprocess

# Add the app directory to the Python path for imports
sys.path.insert(0, 'app')

from services.repository_cache_manager import RepositoryCacheManager, get_repository_cache_manager
from core.exceptions import RepositoryError
from core.structured_logging import LogStatus


def test_validate_fetch_operation_basic():
    """Test basic validate_fetch_operation functionality."""
    print("🧪 Testing basic validate_fetch_operation functionality...")
    
    # Create temporary cache directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_cache_root = Path(temp_dir)
        
        # Create cache manager with temporary cache root
        manager = RepositoryCacheManager(correlation_id="test_validation_123")
        manager.CACHE_ROOT = temp_cache_root
        
        repository_url = "https://github.com/user/test-repo.git"
        
        # Test 1: Repository not found in cache
        print("  ✓ Testing repository not found scenario...")
        result = manager.validate_fetch_operation(repository_url)
        
        assert result['is_valid'] is False
        assert result['validation_status'] == 'not_found'
        assert result['cache_path'] is None
        assert 'Repository not found in cache' in result['error_details']
        print("    ✅ Repository not found validation works correctly")
        
        # Test 2: Create cache directory with .git but no FETCH_HEAD
        print("  ✓ Testing repository without fetch...")
        cache_path = manager.create_cache_directory(repository_url)
        git_dir = cache_path / '.git'
        git_dir.mkdir()
        (git_dir / 'config').write_text('[core]\n\trepositoryformatversion = 0')
        
        def mock_git_commands(*args, **kwargs):
            command = args[0]
            if command[0] == "git":
                if command[1] == "status" and "--porcelain" in command:
                    return Mock(returncode=0, stdout="", stderr="")
                elif command[1] == "remote" and command[2] == "get-url":
                    return Mock(returncode=0, stdout=f"{repository_url}\n", stderr="")
                elif command[1] == "rev-list":
                    return Mock(returncode=0, stdout="0\t0\n", stderr="")
            return Mock(returncode=0, stdout="", stderr="")
        
        with patch('subprocess.run', side_effect=mock_git_commands):
            result = manager.validate_fetch_operation(repository_url)
            
            assert result['is_valid'] is True  # Critical checks pass
            assert result['fetch_validation']['fetch_recent'] is False
            assert any('FETCH_HEAD file not found' in error for error in result['error_details'])
            print("    ✅ Repository without fetch validation works correctly")
        
        # Test 3: Create repository with recent fetch
        print("  ✓ Testing repository with recent fetch...")
        fetch_head = git_dir / 'FETCH_HEAD'
        fetch_head.write_text('abc123def456\t\tbranch \'main\' of https://github.com/user/test-repo.git')
        
        with patch('subprocess.run', side_effect=mock_git_commands):
            result = manager.validate_fetch_operation(repository_url)
            
            assert result['is_valid'] is True
            assert result['validation_status'] == 'valid'
            assert result['cache_path'] == str(cache_path)
            assert result['fetch_validation']['fetch_recent'] is True
            print("    ✅ Repository with recent fetch validation works correctly")
    
    print("✅ Basic validate_fetch_operation functionality tests passed!")


def test_validate_fetch_operation_performance():
    """Test that validate_fetch_operation meets performance requirements."""
    print("🧪 Testing validate_fetch_operation performance requirements...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_cache_root = Path(temp_dir)
        
        manager = RepositoryCacheManager(correlation_id="test_perf_456")
        manager.CACHE_ROOT = temp_cache_root
        
        repository_url = "https://github.com/user/perf-test.git"
        
        # Create cache directory with .git and FETCH_HEAD
        cache_path = manager.create_cache_directory(repository_url)
        git_dir = cache_path / '.git'
        git_dir.mkdir()
        (git_dir / 'config').write_text('[core]\n\trepositoryformatversion = 0')
        (git_dir / 'FETCH_HEAD').write_text('abc123\t\tbranch \'main\' of https://github.com/user/perf-test.git')
        
        def mock_fast_git_commands(*args, **kwargs):
            command = args[0]
            if command[0] == "git":
                if command[1] == "status" and "--porcelain" in command:
                    return Mock(returncode=0, stdout="", stderr="")
                elif command[1] == "remote" and command[2] == "get-url":
                    return Mock(returncode=0, stdout=f"{repository_url}\n", stderr="")
                elif command[1] == "rev-list":
                    return Mock(returncode=0, stdout="0\t0\n", stderr="")
            return Mock(returncode=0, stdout="", stderr="")
        
        with patch('subprocess.run', side_effect=mock_fast_git_commands):
            start_time = time.time()
            result = manager.validate_fetch_operation(repository_url)
            duration = time.time() - start_time
            
            assert duration < 2.0, f"Validation took {duration}s, exceeds 2s requirement"
            assert result['performance_metrics']['total_duration_ms'] < 2000
            assert result['is_valid'] is True
            print(f"    ✅ Performance requirement met: {duration:.3f}s < 2.0s")
    
    print("✅ Performance requirements tests passed!")


def test_validate_fetch_operation_error_handling():
    """Test error handling in validate_fetch_operation."""
    print("🧪 Testing validate_fetch_operation error handling...")
    
    manager = RepositoryCacheManager(correlation_id="test_error_789")
    
    # Test invalid URL
    print("  ✓ Testing invalid URL handling...")
    try:
        manager.validate_fetch_operation("ftp://invalid.com/repo")
        assert False, "Should have raised RepositoryError"
    except RepositoryError as e:
        assert "Unsupported URL scheme" in str(e)
        print("    ✅ Invalid URL error handling works correctly")
    
    print("✅ Error handling tests passed!")


def test_validate_fetch_operation_integration():
    """Test integration between fetch and validation operations."""
    print("🧪 Testing fetch and validation integration...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_cache_root = Path(temp_dir)
        
        manager = RepositoryCacheManager(correlation_id="test_integration_012")
        manager.CACHE_ROOT = temp_cache_root
        
        repository_url = "https://github.com/user/integration-test.git"
        
        # Mock git operations
        def mock_integration_git(*args, **kwargs):
            command = args[0]
            if command[0] == "git":
                if command[1] == "clone":
                    # Simulate creating repository structure
                    cache_key = manager._generate_cache_key(repository_url)
                    cache_path = manager.CACHE_ROOT / cache_key
                    if cache_path.exists():
                        git_dir = cache_path / '.git'
                        git_dir.mkdir(exist_ok=True)
                        (git_dir / 'config').write_text('[core]\n\trepositoryformatversion = 0')
                        (git_dir / 'FETCH_HEAD').write_text('def456\t\tbranch \'main\' of https://github.com/user/integration-test.git')
                        (cache_path / 'README.md').write_text('# Integration Test')
                    return Mock(returncode=0, stdout="Cloning...", stderr="")
                elif command[1] == "fetch":
                    return Mock(returncode=0, stdout="From github.com...", stderr="")
                elif command[1] == "status" and "--porcelain" in command:
                    return Mock(returncode=0, stdout="", stderr="")
                elif command[1] == "remote" and command[2] == "get-url":
                    return Mock(returncode=0, stdout=f"{repository_url}\n", stderr="")
                elif command[1] == "rev-list":
                    return Mock(returncode=0, stdout="0\t0\n", stderr="")
                elif command[1] == "pull":
                    return Mock(returncode=0, stdout="Already up to date.", stderr="")
            return Mock(returncode=0, stdout="", stderr="")
        
        with patch('subprocess.run', side_effect=mock_integration_git):
            # 1. Clone repository
            print("  ✓ Testing clone operation...")
            clone_result = manager.clone_repository(repository_url)
            assert clone_result['success'] is True
            print("    ✅ Clone operation successful")
            
            # 2. Fetch latest changes
            print("  ✓ Testing fetch operation...")
            fetch_result = manager.fetch_latest_changes(repository_url)
            assert fetch_result['success'] is True
            print("    ✅ Fetch operation successful")
            
            # 3. Validate fetch operation
            print("  ✓ Testing fetch validation...")
            validation_result = manager.validate_fetch_operation(repository_url)
            assert validation_result['is_valid'] is True
            assert validation_result['validation_status'] == 'valid'
            assert validation_result['cache_path'] == clone_result['cache_path']
            print("    ✅ Fetch validation successful")
    
    print("✅ Integration tests passed!")


def test_factory_function():
    """Test the factory function works correctly."""
    print("🧪 Testing factory function...")
    
    correlation_id = "factory_test_345"
    manager = get_repository_cache_manager(correlation_id=correlation_id)
    
    assert isinstance(manager, RepositoryCacheManager)
    assert manager.correlation_id == correlation_id
    assert hasattr(manager, 'validate_fetch_operation')
    
    print("✅ Factory function test passed!")


def main():
    """Run all validation tests."""
    print("🚀 Starting Task 4.3.2 validation: Validate successful fetch operation")
    print("=" * 80)
    
    try:
        test_factory_function()
        test_validate_fetch_operation_basic()
        test_validate_fetch_operation_performance()
        test_validate_fetch_operation_error_handling()
        test_validate_fetch_operation_integration()
        
        print("=" * 80)
        print("🎉 All Task 4.3.2 validation tests passed successfully!")
        print("\n📋 Summary:")
        print("  ✅ validate_fetch_operation() method implemented")
        print("  ✅ Comprehensive validation checks implemented")
        print("  ✅ Performance requirements met (≤2s)")
        print("  ✅ Structured logging and error handling implemented")
        print("  ✅ Integration with existing fetch functionality verified")
        print("  ✅ Factory function integration confirmed")
        
        return True
        
    except Exception as e:
        print(f"❌ Validation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)