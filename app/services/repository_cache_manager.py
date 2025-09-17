"""
Repository Cache Manager Module for Clarity Local Runner

This module provides comprehensive repository cache directory management with:
- Secure directory structure creation at /workspace/repos
- Automatic cleanup policies for directories >24 hours old
- Integration with structured logging and RepositoryError handling
- Performance-optimized operations (≤2s requirement)
- Proper file permissions and access controls
- Audit logging for all directory operations

Primary Responsibility: Repository cache directory lifecycle management
"""

import os
import shutil
import stat
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse
import hashlib
import re

from core.structured_logging import get_structured_logger, LogStatus, log_performance
from core.exceptions import RepositoryError


class RepositoryCacheManager:
    """
    Repository cache directory manager with secure operations and audit logging.
    
    This class manages the lifecycle of repository cache directories including:
    - Creation with proper permissions and security
    - Automatic cleanup based on age policies
    - Structured audit logging for all operations
    - Performance-optimized directory operations
    - Default task list template management
    """
    
    # Cache configuration
    CACHE_ROOT = Path("/workspace/repos")
    CLEANUP_AGE_HOURS = 24
    DEFAULT_DIR_PERMISSIONS = 0o755
    DEFAULT_FILE_PERMISSIONS = 0o644
    
    # Security patterns for repository URL validation
    ALLOWED_URL_SCHEMES = {'http', 'https', 'git', 'ssh'}
    DANGEROUS_PATH_PATTERNS = [
        re.compile(r'\.\.'),  # Path traversal
        re.compile(r'[\x00-\x1f]'),  # Control characters
    ]
    
    # Default task list template following PRD format (sections 190-207)
    DEFAULT_TASK_LIST_TEMPLATE = """# Task List

## Project Tasks

### 1. Core Configuration Tasks

#### 1.1.1 Add DEVTEAM_ENABLED flag to src/config.js
- **Description**: Add DEVTEAM_ENABLED flag with default false and JSDoc documentation
- **Type**: atomic
- **Priority**: medium
- **Status**: pending
- **Dependencies**: []
- **Files**: ["src/config.js"]
- **Criteria**:
  - test.coverage: ≥80%
  - type.strict: 0 errors
  - doc.updated: task_outcomes.md
- **Estimated Duration**: unknown

#### 1.2.1 Initialize project structure
- **Description**: Set up basic project directory structure and configuration files
- **Type**: atomic
- **Priority**: medium
- **Status**: pending
- **Dependencies**: []
- **Files**: ["package.json", "src/", "tests/"]
- **Criteria**:
  - test.coverage: ≥80%
  - type.strict: 0 errors
  - doc.updated: task_outcomes.md
- **Estimated Duration**: unknown

### 2. Development Setup Tasks

#### 2.1.1 Configure development environment
- **Description**: Set up development tools and environment configuration
- **Type**: atomic
- **Priority**: medium
- **Status**: pending
- **Dependencies**: ["1.2.1"]
- **Files**: [".env.example", "docker-compose.yml"]
- **Criteria**:
  - test.coverage: ≥80%
  - type.strict: 0 errors
  - doc.updated: task_outcomes.md
- **Estimated Duration**: unknown

## Task Format Guidelines

Each task should follow this structure:
- **ID**: Hierarchical numbering (e.g., 1.1.1, 1.2.1, 2.1.1)
- **Title**: Clear, actionable description
- **Description**: Detailed explanation of what needs to be done
- **Type**: atomic (for individual tasks) or composite (for task groups)
- **Priority**: low, medium, high
- **Status**: pending, in_progress, completed, blocked, cancelled
- **Dependencies**: Array of task IDs that must be completed first
- **Files**: Array of files that will be modified
- **Criteria**: Quality gates that must be met
- **Estimated Duration**: Time estimate or "unknown"

## Notes

This template provides a starting structure for project tasks. Tasks can be added, modified, or removed as needed. The lenient parser will auto-default missing fields:
- Priority defaults to "medium"
- Status defaults to "pending"
- Estimated Duration defaults to "unknown"
"""
    
    def __init__(self, correlation_id: Optional[str] = None):
        """
        Initialize repository cache manager.
        
        Args:
            correlation_id: Optional correlation ID for distributed tracing
        """
        self.logger = get_structured_logger(__name__)
        self.correlation_id = correlation_id
        
        # Set persistent context for logging
        if correlation_id:
            self.logger.set_context(correlationId=correlation_id)
    
    def _validate_repository_url(self, repository_url: str) -> None:
        """
        Validate repository URL for security and format compliance.
        
        Args:
            repository_url: Repository URL to validate
            
        Raises:
            RepositoryError: If URL is invalid or potentially dangerous
        """
        if not repository_url or not isinstance(repository_url, str):
            raise RepositoryError(
                "Repository URL must be a non-empty string",
                repository_url=repository_url
            )
        
        try:
            parsed = urlparse(repository_url)
            
            # Check scheme
            if parsed.scheme.lower() not in self.ALLOWED_URL_SCHEMES:
                raise RepositoryError(
                    f"Unsupported URL scheme: {parsed.scheme}. Allowed: {self.ALLOWED_URL_SCHEMES}",
                    repository_url=repository_url
                )
            
            # Check for dangerous patterns in the full URL
            for pattern in self.DANGEROUS_PATH_PATTERNS:
                if pattern.search(repository_url):
                    raise RepositoryError(
                        f"Repository URL contains potentially dangerous characters",
                        repository_url=repository_url
                    )
                    
        except Exception as e:
            if isinstance(e, RepositoryError):
                raise
            raise RepositoryError(
                f"Invalid repository URL format: {str(e)}",
                repository_url=repository_url
            )
    
    def _generate_cache_key(self, repository_url: str) -> str:
        """
        Generate a safe, unique cache key for a repository URL.
        
        Args:
            repository_url: Repository URL
            
        Returns:
            Safe cache key for directory naming
        """
        # Create a hash of the URL for uniqueness
        url_hash = hashlib.sha256(repository_url.encode('utf-8')).hexdigest()[:12]
        
        # Extract a safe name from the URL
        parsed = urlparse(repository_url)
        path_parts = [part for part in parsed.path.split('/') if part]
        
        if path_parts:
            # Use the last part (typically repo name) and sanitize it
            repo_name = path_parts[-1]
            # Remove .git suffix if present
            if repo_name.endswith('.git'):
                repo_name = repo_name[:-4]
            # Sanitize for filesystem safety
            safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', repo_name)[:50]
        else:
            safe_name = "repo"
        
        return f"{safe_name}_{url_hash}"
    
    @log_performance(get_structured_logger(__name__), "create_cache_directory")
    def create_cache_directory(
        self,
        repository_url: str,
        project_id: Optional[str] = None,
        execution_id: Optional[str] = None
    ) -> Path:
        """
        Create a cache directory for a repository with proper permissions.
        
        Args:
            repository_url: Repository URL to cache
            project_id: Optional project identifier for logging
            execution_id: Optional execution identifier for logging
            
        Returns:
            Path to the created cache directory
            
        Raises:
            RepositoryError: If directory creation fails or URL is invalid
        """
        try:
            # Validate repository URL
            self._validate_repository_url(repository_url)
            
            # Generate cache key and path
            cache_key = self._generate_cache_key(repository_url)
            cache_path = self.CACHE_ROOT / cache_key
            
            self.logger.info(
                "Creating repository cache directory",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.STARTED,
                repository_url=repository_url,
                cache_key=cache_key,
                cache_path=str(cache_path)
            )
            
            # Ensure root cache directory exists
            self.CACHE_ROOT.mkdir(parents=True, exist_ok=True, mode=self.DEFAULT_DIR_PERMISSIONS)
            
            # Create the specific cache directory
            if cache_path.exists():
                self.logger.info(
                    "Cache directory already exists",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    status=LogStatus.SKIPPED,
                    cache_path=str(cache_path)
                )
            else:
                cache_path.mkdir(parents=True, exist_ok=True, mode=self.DEFAULT_DIR_PERMISSIONS)
                
                # Set proper permissions
                os.chmod(cache_path, self.DEFAULT_DIR_PERMISSIONS)
                
                self.logger.info(
                    "Repository cache directory created successfully",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    status=LogStatus.COMPLETED,
                    cache_path=str(cache_path),
                    permissions=oct(self.DEFAULT_DIR_PERMISSIONS)
                )
            
            return cache_path
            
        except RepositoryError:
            raise
        except Exception as e:
            self.logger.error(
                "Failed to create repository cache directory",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.FAILED,
                repository_url=repository_url,
                error=e
            )
            raise RepositoryError(
                f"Failed to create cache directory: {str(e)}",
                repository_url=repository_url
            )
    
    def get_cache_directory(self, repository_url: str) -> Optional[Path]:
        """
        Get the cache directory path for a repository if it exists.
        
        Args:
            repository_url: Repository URL
            
        Returns:
            Path to cache directory if it exists, None otherwise
            
        Raises:
            RepositoryError: If URL validation fails
        """
        try:
            self._validate_repository_url(repository_url)
            cache_key = self._generate_cache_key(repository_url)
            cache_path = self.CACHE_ROOT / cache_key
            
            if cache_path.exists() and cache_path.is_dir():
                return cache_path
            return None
            
        except RepositoryError:
            raise
        except Exception as e:
            raise RepositoryError(
                f"Failed to get cache directory: {str(e)}",
                repository_url=repository_url
            )
    
    def directory_exists(self, repository_url: str) -> bool:
        """
        Check if a cache directory exists for a repository.
        
        Args:
            repository_url: Repository URL to check
            
        Returns:
            True if cache directory exists, False otherwise
        """
        try:
            cache_path = self.get_cache_directory(repository_url)
            return cache_path is not None
        except RepositoryError:
            return False
    
    @log_performance(get_structured_logger(__name__), "repository_existence_check")
    def check_repository_existence(
        self,
        repository_url: str,
        project_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        validate_remote: bool = False
    ) -> Dict[str, Any]:
        """
        Comprehensive repository existence check with cache lookup functionality.
        
        This method provides enhanced repository existence validation that integrates
        with the ADD repository initialization workflow requirements. It performs
        both local cache validation and optional remote repository validation.
        
        Args:
            repository_url: Repository URL to validate and check
            project_id: Optional project identifier for logging
            execution_id: Optional execution identifier for logging
            validate_remote: Whether to perform remote repository validation (future enhancement)
            
        Returns:
            Dictionary containing existence check results:
            {
                'exists_in_cache': bool,
                'cache_path': Optional[str],
                'cache_key': str,
                'repository_url': str,
                'validation_status': str,
                'last_accessed': Optional[str],
                'cache_size_bytes': Optional[int],
                'performance_metrics': Dict[str, float]
            }
            
        Raises:
            RepositoryError: If URL validation fails or check operation encounters errors
        """
        start_time = time.time()
        
        try:
            # Validate repository URL with comprehensive security checks
            self._validate_repository_url(repository_url)
            
            self.logger.info(
                "Starting repository existence check",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.STARTED,
                repository_url=repository_url,
                validate_remote=validate_remote
            )
            
            # Generate cache key for consistent lookup
            cache_key = self._generate_cache_key(repository_url)
            
            # Perform cache directory lookup
            cache_path = self.get_cache_directory(repository_url)
            exists_in_cache = cache_path is not None
            
            # Collect cache metadata if directory exists
            cache_metadata = {}
            if exists_in_cache and cache_path:
                try:
                    # Get cache directory size
                    cache_size = self._get_directory_size(cache_path)
                    cache_metadata['cache_size_bytes'] = cache_size
                    
                    # Get last accessed time
                    dir_stat = cache_path.stat()
                    cache_metadata['last_accessed'] = datetime.fromtimestamp(dir_stat.st_atime).isoformat()
                    cache_metadata['last_modified'] = datetime.fromtimestamp(dir_stat.st_mtime).isoformat()
                    
                except (OSError, IOError) as e:
                    self.logger.warn(
                        "Failed to collect cache metadata",
                        correlation_id=self.correlation_id,
                        project_id=project_id,
                        execution_id=execution_id,
                        repository_url=repository_url,
                        cache_path=str(cache_path),
                        error=str(e)
                    )
                    cache_metadata['cache_size_bytes'] = 0
                    cache_metadata['last_accessed'] = None
                    cache_metadata['last_modified'] = None
            
            # Determine validation status
            if exists_in_cache:
                validation_status = "cache_hit"
            else:
                validation_status = "cache_miss"
            
            # Calculate performance metrics
            check_duration = time.time() - start_time
            performance_metrics = {
                'check_duration_ms': round(check_duration * 1000, 2),
                'url_validation_time_ms': round(0.001 * 1000, 2),  # Estimated based on validation complexity
                'cache_lookup_time_ms': round((check_duration - 0.001) * 1000, 2)
            }
            
            # Build comprehensive result
            result = {
                'exists_in_cache': exists_in_cache,
                'cache_path': str(cache_path) if cache_path else None,
                'cache_key': cache_key,
                'repository_url': repository_url,
                'validation_status': validation_status,
                'performance_metrics': performance_metrics,
                **cache_metadata
            }
            
            # Log successful completion
            self.logger.info(
                "Repository existence check completed successfully",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.COMPLETED,
                repository_url=repository_url,
                exists_in_cache=exists_in_cache,
                validation_status=validation_status,
                check_duration_ms=performance_metrics['check_duration_ms'],
                cache_key=cache_key
            )
            
            return result
            
        except RepositoryError:
            # Re-raise repository errors with additional context
            check_duration = time.time() - start_time
            self.logger.error(
                "Repository existence check failed due to validation error",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.FAILED,
                repository_url=repository_url,
                check_duration_ms=round(check_duration * 1000, 2)
            )
            raise
        except Exception as e:
            check_duration = time.time() - start_time
            self.logger.error(
                "Repository existence check failed with unexpected error",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.FAILED,
                repository_url=repository_url,
                check_duration_ms=round(check_duration * 1000, 2),
                error=e
            )
            raise RepositoryError(
                f"Repository existence check failed: {str(e)}",
                repository_url=repository_url
            )
    
    def get_repository_cache_info(
        self,
        repository_url: str,
        project_id: Optional[str] = None,
        execution_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed cache information for a repository if it exists.
        
        This method provides comprehensive cache information for integration
        with the ADD repository initialization workflow.
        
        Args:
            repository_url: Repository URL to get cache info for
            project_id: Optional project identifier for logging
            execution_id: Optional execution identifier for logging
            
        Returns:
            Dictionary with cache information if exists, None otherwise:
            {
                'cache_path': str,
                'cache_key': str,
                'size_bytes': int,
                'created_at': str,
                'last_accessed': str,
                'last_modified': str,
                'file_count': int,
                'is_valid': bool
            }
            
        Raises:
            RepositoryError: If URL validation fails
        """
        try:
            # Validate repository URL
            self._validate_repository_url(repository_url)
            
            # Get cache directory
            cache_path = self.get_cache_directory(repository_url)
            if not cache_path:
                return None
            
            self.logger.debug(
                "Collecting repository cache information",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                repository_url=repository_url,
                cache_path=str(cache_path)
            )
            
            # Collect comprehensive cache information
            cache_key = self._generate_cache_key(repository_url)
            size_bytes = self._get_directory_size(cache_path)
            
            # Get directory statistics
            dir_stat = cache_path.stat()
            created_at = datetime.fromtimestamp(dir_stat.st_ctime).isoformat()
            last_accessed = datetime.fromtimestamp(dir_stat.st_atime).isoformat()
            last_modified = datetime.fromtimestamp(dir_stat.st_mtime).isoformat()
            
            # Count files in cache directory
            file_count = 0
            try:
                for item in cache_path.rglob('*'):
                    if item.is_file():
                        file_count += 1
            except (OSError, IOError):
                file_count = 0
            
            # Validate cache integrity (basic check)
            is_valid = cache_path.exists() and cache_path.is_dir() and size_bytes >= 0
            
            cache_info = {
                'cache_path': str(cache_path),
                'cache_key': cache_key,
                'size_bytes': size_bytes,
                'created_at': created_at,
                'last_accessed': last_accessed,
                'last_modified': last_modified,
                'file_count': file_count,
                'is_valid': is_valid
            }
            
            self.logger.debug(
                "Repository cache information collected",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                repository_url=repository_url,
                cache_info=cache_info
            )
            
            return cache_info
            
        except RepositoryError:
            raise
        except Exception as e:
            self.logger.error(
                "Failed to collect repository cache information",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                repository_url=repository_url,
                error=e
            )
            raise RepositoryError(
                f"Failed to get repository cache info: {str(e)}",
                repository_url=repository_url
            )
    
    @log_performance(get_structured_logger(__name__), "cleanup_old_directories")
    def cleanup_old_directories(
        self,
        max_age_hours: Optional[int] = None,
        project_id: Optional[str] = None,
        execution_id: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Clean up cache directories older than specified age.
        
        Args:
            max_age_hours: Maximum age in hours (defaults to CLEANUP_AGE_HOURS)
            project_id: Optional project identifier for logging
            execution_id: Optional execution identifier for logging
            
        Returns:
            Dictionary with cleanup statistics
            
        Raises:
            RepositoryError: If cleanup operation fails
        """
        max_age = max_age_hours or self.CLEANUP_AGE_HOURS
        cutoff_time = datetime.now() - timedelta(hours=max_age)
        
        stats = {
            'directories_checked': 0,
            'directories_removed': 0,
            'bytes_freed': 0,
            'errors': 0
        }
        
        try:
            self.logger.info(
                "Starting repository cache cleanup",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.STARTED,
                max_age_hours=max_age,
                cutoff_time=cutoff_time.isoformat()
            )
            
            if not self.CACHE_ROOT.exists():
                self.logger.info(
                    "Cache root directory does not exist, skipping cleanup",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    status=LogStatus.SKIPPED
                )
                return stats
            
            # Iterate through cache directories
            for cache_dir in self.CACHE_ROOT.iterdir():
                if not cache_dir.is_dir():
                    continue
                
                stats['directories_checked'] += 1
                
                try:
                    # Get directory modification time
                    dir_mtime = datetime.fromtimestamp(cache_dir.stat().st_mtime)
                    
                    if dir_mtime < cutoff_time:
                        # Calculate directory size before removal
                        dir_size = self._get_directory_size(cache_dir)
                        
                        # Remove the directory
                        shutil.rmtree(cache_dir)
                        
                        stats['directories_removed'] += 1
                        stats['bytes_freed'] += dir_size
                        
                        self.logger.info(
                            "Removed old cache directory",
                            correlation_id=self.correlation_id,
                            project_id=project_id,
                            execution_id=execution_id,
                            cache_directory=str(cache_dir),
                            directory_age_hours=round((datetime.now() - dir_mtime).total_seconds() / 3600, 2),
                            size_bytes=dir_size
                        )
                        
                except Exception as e:
                    stats['errors'] += 1
                    self.logger.error(
                        "Failed to remove cache directory",
                        correlation_id=self.correlation_id,
                        project_id=project_id,
                        execution_id=execution_id,
                        cache_directory=str(cache_dir),
                        error=e
                    )
            
            self.logger.info(
                "Repository cache cleanup completed",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.COMPLETED,
                directories_checked=stats['directories_checked'],
                directories_removed=stats['directories_removed'],
                bytes_freed=stats['bytes_freed'],
                errors=stats['errors']
            )
            
            return stats
            
        except Exception as e:
            self.logger.error(
                "Repository cache cleanup failed",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.FAILED,
                error=e
            )
            raise RepositoryError(f"Cache cleanup failed: {str(e)}")
    
    def _get_directory_size(self, directory: Path) -> int:
        """
        Calculate the total size of a directory in bytes.
        
        Args:
            directory: Directory path
            
        Returns:
            Total size in bytes
        """
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except (OSError, IOError):
                        # Skip files that can't be accessed
                        continue
        except (OSError, IOError):
            # Return 0 if directory can't be accessed
            pass
        return total_size
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the repository cache.
        
        Returns:
            Dictionary with cache statistics
        """
        stats = {
            'total_directories': 0,
            'total_size_bytes': 0,
            'oldest_directory': None,
            'newest_directory': None,
            'cache_root_exists': self.CACHE_ROOT.exists()
        }
        
        if not self.CACHE_ROOT.exists():
            return stats
        
        oldest_time = None
        newest_time = None
        
        try:
            for cache_dir in self.CACHE_ROOT.iterdir():
                if not cache_dir.is_dir():
                    continue
                
                stats['total_directories'] += 1
                
                # Calculate directory size
                dir_size = self._get_directory_size(cache_dir)
                stats['total_size_bytes'] += dir_size
                
                # Track oldest and newest
                dir_mtime = datetime.fromtimestamp(cache_dir.stat().st_mtime)
                
                if oldest_time is None or dir_mtime < oldest_time:
                    oldest_time = dir_mtime
                    stats['oldest_directory'] = {
                        'path': str(cache_dir),
                        'modified_time': dir_mtime.isoformat(),
                        'age_hours': round((datetime.now() - dir_mtime).total_seconds() / 3600, 2)
                    }
                
                if newest_time is None or dir_mtime > newest_time:
                    newest_time = dir_mtime
                    stats['newest_directory'] = {
                        'path': str(cache_dir),
                        'modified_time': dir_mtime.isoformat(),
                        'age_hours': round((datetime.now() - dir_mtime).total_seconds() / 3600, 2)
                    }
                    
        except Exception as e:
            self.logger.error(
                "Failed to collect cache statistics",
                correlation_id=self.correlation_id,
                error=e
            )
        
        return stats
    
    def remove_cache_directory(
        self,
        repository_url: str,
        project_id: Optional[str] = None,
        execution_id: Optional[str] = None
    ) -> bool:
        """
        Remove a specific cache directory.
        
        Args:
            repository_url: Repository URL whose cache to remove
            project_id: Optional project identifier for logging
            execution_id: Optional execution identifier for logging
            
        Returns:
            True if directory was removed, False if it didn't exist
            
        Raises:
            RepositoryError: If removal fails
        """
        try:
            cache_path = self.get_cache_directory(repository_url)
            
            if cache_path is None:
                self.logger.info(
                    "Cache directory does not exist, nothing to remove",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    repository_url=repository_url,
                    status=LogStatus.SKIPPED
                )
                return False
            
            # Calculate size before removal for logging
            dir_size = self._get_directory_size(cache_path)
            
            # Remove the directory
            shutil.rmtree(cache_path)
            
            self.logger.info(
                "Cache directory removed successfully",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.COMPLETED,
                repository_url=repository_url,
                cache_path=str(cache_path),
                size_bytes=dir_size
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to remove cache directory",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.FAILED,
                repository_url=repository_url,
                error=e
            )
            raise RepositoryError(
                f"Failed to remove cache directory: {str(e)}",
                repository_url=repository_url
            )
    
    @log_performance(get_structured_logger(__name__), "clone_repository")
    def clone_repository(
        self,
        repository_url: str,
        project_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        auth_token: Optional[str] = None,
        timeout_seconds: int = 30
    ) -> Dict[str, Any]:
        """
        Clone repository if absent from cache using git clone operations.
        
        This method performs git clone operations when repositories are not present
        in the cache directory. It follows MVP implementation approach with HTTPS
        authentication only and full clones.
        
        Args:
            repository_url: Repository URL to clone
            project_id: Optional project identifier for logging
            execution_id: Optional execution identifier for logging
            auth_token: Optional authentication token for private repositories
            timeout_seconds: Timeout for git clone operation (default: 30s)
            
        Returns:
            Dictionary containing clone operation results:
            {
                'success': bool,
                'cache_path': str,
                'repository_url': str,
                'clone_status': str,  # 'cloned', 'already_exists', 'failed'
                'performance_metrics': Dict[str, float],
                'repository_size_bytes': int,
                'files_cloned': int
            }
            
        Raises:
            RepositoryError: If clone operation fails or URL validation fails
        """
        start_time = time.time()
        
        try:
            # Validate repository URL with comprehensive security checks
            self._validate_repository_url(repository_url)
            
            self.logger.info(
                "Starting repository clone operation",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.STARTED,
                repository_url=repository_url,
                timeout_seconds=timeout_seconds
            )
            
            # Check if repository already exists in cache
            cache_path = self.get_cache_directory(repository_url)
            if cache_path and cache_path.exists():
                # Repository already exists, return early
                repo_size = self._get_directory_size(cache_path)
                file_count = self._count_files_in_directory(cache_path)
                
                duration_ms = (time.time() - start_time) * 1000
                result = {
                    'success': True,
                    'cache_path': str(cache_path),
                    'repository_url': repository_url,
                    'clone_status': 'already_exists',
                    'performance_metrics': {
                        'total_duration_ms': round(duration_ms, 2),
                        'git_clone_duration_ms': 0.0,
                        'validation_duration_ms': round(duration_ms, 2)
                    },
                    'repository_size_bytes': repo_size,
                    'files_cloned': file_count
                }
                
                self.logger.info(
                    "Repository already exists in cache, skipping clone",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    status=LogStatus.SKIPPED,
                    repository_url=repository_url,
                    cache_path=str(cache_path),
                    repository_size_bytes=repo_size
                )
                
                return result
            
            # Create cache directory for the repository
            cache_path = self.create_cache_directory(
                repository_url=repository_url,
                project_id=project_id,
                execution_id=execution_id
            )
            
            # Prepare git clone command
            clone_url = self._prepare_clone_url(repository_url, auth_token)
            git_command = ["git", "clone", clone_url, str(cache_path)]
            
            self.logger.info(
                "Executing git clone command",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.IN_PROGRESS,
                repository_url=repository_url,
                cache_path=str(cache_path),
                timeout_seconds=timeout_seconds
            )
            
            # Execute git clone with timeout and error handling
            clone_start_time = time.time()
            try:
                result_process = subprocess.run(
                    git_command,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                    cwd=cache_path.parent  # Run from parent directory
                )
                clone_duration_ms = (time.time() - clone_start_time) * 1000
                
                if result_process.returncode != 0:
                    # Git clone failed
                    error_output = result_process.stderr or result_process.stdout or "Unknown git error"
                    
                    # Clean up failed clone directory
                    if cache_path.exists():
                        shutil.rmtree(cache_path)
                    
                    self.logger.error(
                        "Git clone operation failed",
                        correlation_id=self.correlation_id,
                        project_id=project_id,
                        execution_id=execution_id,
                        status=LogStatus.FAILED,
                        repository_url=repository_url,
                        git_error=error_output,
                        git_return_code=result_process.returncode,
                        clone_duration_ms=round(clone_duration_ms, 2)
                    )
                    
                    raise RepositoryError(
                        f"Git clone failed: {error_output}",
                        repository_url=repository_url
                    )
                
            except subprocess.TimeoutExpired:
                # Handle timeout
                clone_duration_ms = (time.time() - clone_start_time) * 1000
                
                # Clean up timed out clone directory
                if cache_path.exists():
                    shutil.rmtree(cache_path)
                
                self.logger.error(
                    "Git clone operation timed out",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    status=LogStatus.FAILED,
                    repository_url=repository_url,
                    timeout_seconds=timeout_seconds,
                    clone_duration_ms=round(clone_duration_ms, 2)
                )
                
                raise RepositoryError(
                    f"Git clone timed out after {timeout_seconds} seconds",
                    repository_url=repository_url
                )
            
            # Verify clone success and collect metrics
            if not cache_path.exists() or not any(cache_path.iterdir()):
                raise RepositoryError(
                    "Git clone completed but cache directory is empty",
                    repository_url=repository_url
                )
            
            # Collect post-clone metrics
            repo_size = self._get_directory_size(cache_path)
            file_count = self._count_files_in_directory(cache_path)
            total_duration_ms = (time.time() - start_time) * 1000
            
            # Build successful result
            result = {
                'success': True,
                'cache_path': str(cache_path),
                'repository_url': repository_url,
                'clone_status': 'cloned',
                'performance_metrics': {
                    'total_duration_ms': round(total_duration_ms, 2),
                    'git_clone_duration_ms': round(clone_duration_ms, 2),
                    'validation_duration_ms': round(total_duration_ms - clone_duration_ms, 2)
                },
                'repository_size_bytes': repo_size,
                'files_cloned': file_count
            }
            
            self.logger.info(
                "Repository clone completed successfully",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.COMPLETED,
                repository_url=repository_url,
                cache_path=str(cache_path),
                repository_size_bytes=repo_size,
                files_cloned=file_count,
                total_duration_ms=result['performance_metrics']['total_duration_ms'],
                git_clone_duration_ms=result['performance_metrics']['git_clone_duration_ms']
            )
            
            return result
            
        except RepositoryError:
            # Re-raise repository errors with additional context
            total_duration_ms = (time.time() - start_time) * 1000
            self.logger.error(
                "Repository clone failed due to repository error",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.FAILED,
                repository_url=repository_url,
                total_duration_ms=round(total_duration_ms, 2)
            )
            raise
        except Exception as e:
            total_duration_ms = (time.time() - start_time) * 1000
            self.logger.error(
                "Repository clone failed with unexpected error",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.FAILED,
                repository_url=repository_url,
                total_duration_ms=round(total_duration_ms, 2),
                error=e
            )
            raise RepositoryError(
                f"Repository clone failed: {str(e)}",
                repository_url=repository_url
            )
    
    def _prepare_clone_url(self, repository_url: str, auth_token: Optional[str] = None) -> str:
        """
        Prepare repository URL for git clone with authentication if provided.
        
        Args:
            repository_url: Original repository URL
            auth_token: Optional authentication token
            
        Returns:
            Prepared URL for git clone operation
        """
        if not auth_token:
            return repository_url
        
        # For HTTPS URLs, inject token authentication
        parsed = urlparse(repository_url)
        if parsed.scheme.lower() in ('http', 'https'):
            # Format: https://token@hostname/path
            auth_url = f"{parsed.scheme}://{auth_token}@{parsed.netloc}{parsed.path}"
            if parsed.query:
                auth_url += f"?{parsed.query}"
            return auth_url
        
        # For other schemes, return original URL (MVP approach)
        return repository_url
    
    def _count_files_in_directory(self, directory: Path) -> int:
        """
        Count the total number of files in a directory recursively.
        
        Args:
            directory: Directory path to count files in
            
        Returns:
            Total number of files
        """
        file_count = 0
        try:
            for item in directory.rglob('*'):
                if item.is_file():
                    file_count += 1
        except (OSError, IOError):
            # Return 0 if directory can't be accessed
            pass
        return file_count
    
    @log_performance(get_structured_logger(__name__), "validate_clone")
    def validate_clone(
        self,
        repository_url: str,
        project_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        timeout_seconds: int = 10
    ) -> Dict[str, Any]:
        """
        Validate successful clone operation with comprehensive repository health checks.
        
        This method performs comprehensive validation of cloned repositories to ensure
        they are properly initialized and functional. It validates git repository
        structure, remote configuration, and basic repository health.
        
        Args:
            repository_url: Repository URL to validate
            project_id: Optional project identifier for logging
            execution_id: Optional execution identifier for logging
            timeout_seconds: Timeout for git operations (default: 10s)
            
        Returns:
            Dictionary containing validation results:
            {
                'is_valid': bool,
                'repository_url': str,
                'cache_path': str,
                'validation_status': str,  # 'valid', 'invalid', 'not_found'
                'validation_checks': Dict[str, bool],
                'performance_metrics': Dict[str, float],
                'repository_info': Dict[str, Any],
                'error_details': Optional[List[str]]
            }
            
        Raises:
            RepositoryError: If URL validation fails or validation encounters critical errors
        """
        start_time = time.time()
        
        try:
            # Validate repository URL with comprehensive security checks
            self._validate_repository_url(repository_url)
            
            self.logger.info(
                "Starting repository clone validation",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.STARTED,
                repository_url=repository_url,
                timeout_seconds=timeout_seconds
            )
            
            # Get cache directory for the repository
            cache_path = self.get_cache_directory(repository_url)
            if not cache_path:
                # Repository not found in cache
                validation_duration = (time.time() - start_time) * 1000
                result = {
                    'is_valid': False,
                    'repository_url': repository_url,
                    'cache_path': None,
                    'validation_status': 'not_found',
                    'validation_checks': {},
                    'performance_metrics': {
                        'total_duration_ms': round(validation_duration, 2),
                        'git_validation_duration_ms': 0.0,
                        'structure_validation_duration_ms': round(validation_duration, 2)
                    },
                    'repository_info': {},
                    'error_details': ['Repository not found in cache']
                }
                
                self.logger.warn(
                    "Repository clone validation failed - not found in cache",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    status=LogStatus.FAILED,
                    repository_url=repository_url,
                    validation_duration_ms=round(validation_duration, 2)
                )
                
                return result
            
            # Initialize validation tracking
            validation_checks = {}
            error_details = []
            git_validation_start = time.time()
            
            # 1. Verify .git directory exists
            git_dir = cache_path / '.git'
            validation_checks['git_directory_exists'] = git_dir.exists() and git_dir.is_dir()
            if not validation_checks['git_directory_exists']:
                error_details.append('.git directory not found or not a directory')
            
            # 2. Check git status command works (repository is properly initialized)
            validation_checks['git_status_works'] = False
            try:
                if validation_checks['git_directory_exists']:
                    result_process = subprocess.run(
                        ["git", "status", "--porcelain"],
                        cwd=cache_path,
                        capture_output=True,
                        text=True,
                        timeout=timeout_seconds
                    )
                    validation_checks['git_status_works'] = result_process.returncode == 0
                    if not validation_checks['git_status_works']:
                        error_details.append(f'git status failed: {result_process.stderr}')
            except subprocess.TimeoutExpired:
                error_details.append(f'git status timed out after {timeout_seconds} seconds')
            except Exception as e:
                error_details.append(f'git status error: {str(e)}')
            
            # 3. Validate remote origin is correctly configured
            validation_checks['remote_origin_configured'] = False
            remote_url = None
            try:
                if validation_checks['git_status_works']:
                    result_process = subprocess.run(
                        ["git", "remote", "get-url", "origin"],
                        cwd=cache_path,
                        capture_output=True,
                        text=True,
                        timeout=timeout_seconds
                    )
                    if result_process.returncode == 0:
                        remote_url = result_process.stdout.strip()
                        # Verify remote URL matches expected repository URL (allowing for auth token differences)
                        validation_checks['remote_origin_configured'] = self._validate_remote_url_match(
                            repository_url, remote_url
                        )
                        if not validation_checks['remote_origin_configured']:
                            error_details.append(f'Remote origin URL mismatch: expected {repository_url}, got {remote_url}')
                    else:
                        error_details.append(f'git remote get-url failed: {result_process.stderr}')
            except subprocess.TimeoutExpired:
                error_details.append(f'git remote get-url timed out after {timeout_seconds} seconds')
            except Exception as e:
                error_details.append(f'git remote get-url error: {str(e)}')
            
            # 4. Verify repository is not corrupted (basic health check)
            validation_checks['repository_not_corrupted'] = False
            try:
                if validation_checks['git_status_works']:
                    result_process = subprocess.run(
                        ["git", "fsck", "--no-progress"],
                        cwd=cache_path,
                        capture_output=True,
                        text=True,
                        timeout=timeout_seconds
                    )
                    validation_checks['repository_not_corrupted'] = result_process.returncode == 0
                    if not validation_checks['repository_not_corrupted']:
                        error_details.append(f'git fsck failed: {result_process.stderr}')
            except subprocess.TimeoutExpired:
                error_details.append(f'git fsck timed out after {timeout_seconds} seconds')
            except Exception as e:
                error_details.append(f'git fsck error: {str(e)}')
            
            git_validation_duration = (time.time() - git_validation_start) * 1000
            
            # 5. Ensure proper file permissions and directory structure
            structure_validation_start = time.time()
            validation_checks['proper_permissions'] = self._validate_file_permissions(cache_path)
            if not validation_checks['proper_permissions']:
                error_details.append('Invalid file permissions detected')
            
            # 6. Basic directory structure validation
            validation_checks['directory_structure_valid'] = cache_path.exists() and cache_path.is_dir()
            if not validation_checks['directory_structure_valid']:
                error_details.append('Cache directory structure is invalid')
            
            structure_validation_duration = (time.time() - structure_validation_start) * 1000
            
            # Collect repository information
            repository_info = {}
            try:
                repository_info['cache_path'] = str(cache_path)
                repository_info['repository_size_bytes'] = self._get_directory_size(cache_path)
                repository_info['file_count'] = self._count_files_in_directory(cache_path)
                repository_info['remote_url'] = remote_url
                
                # Get last commit info if possible
                if validation_checks['git_status_works']:
                    try:
                        result_process = subprocess.run(
                            ["git", "log", "-1", "--format=%H|%s|%an|%ad", "--date=iso"],
                            cwd=cache_path,
                            capture_output=True,
                            text=True,
                            timeout=timeout_seconds
                        )
                        if result_process.returncode == 0:
                            commit_parts = result_process.stdout.strip().split('|', 3)
                            if len(commit_parts) >= 4:
                                repository_info['last_commit'] = {
                                    'hash': commit_parts[0],
                                    'message': commit_parts[1],
                                    'author': commit_parts[2],
                                    'date': commit_parts[3]
                                }
                    except Exception:
                        # Non-critical, continue without commit info
                        pass
                        
            except Exception as e:
                self.logger.warn(
                    "Failed to collect repository information",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    repository_url=repository_url,
                    error=str(e)
                )
            
            # Determine overall validation status
            critical_checks = [
                'git_directory_exists',
                'git_status_works',
                'remote_origin_configured',
                'directory_structure_valid'
            ]
            
            is_valid = all(validation_checks.get(check, False) for check in critical_checks)
            validation_status = 'valid' if is_valid else 'invalid'
            
            # Calculate total duration
            total_duration = (time.time() - start_time) * 1000
            
            # Build result
            result = {
                'is_valid': is_valid,
                'repository_url': repository_url,
                'cache_path': str(cache_path),
                'validation_status': validation_status,
                'validation_checks': validation_checks,
                'performance_metrics': {
                    'total_duration_ms': round(total_duration, 2),
                    'git_validation_duration_ms': round(git_validation_duration, 2),
                    'structure_validation_duration_ms': round(structure_validation_duration, 2)
                },
                'repository_info': repository_info,
                'error_details': error_details if error_details else None
            }
            
            # Log completion
            if is_valid:
                self.logger.info(
                    "Repository clone validation completed successfully",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    status=LogStatus.COMPLETED,
                    repository_url=repository_url,
                    cache_path=str(cache_path),
                    validation_status=validation_status,
                    total_duration_ms=result['performance_metrics']['total_duration_ms'],
                    validation_checks_passed=sum(1 for v in validation_checks.values() if v),
                    validation_checks_total=len(validation_checks)
                )
            else:
                self.logger.warn(
                    "Repository clone validation completed with issues",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    status=LogStatus.COMPLETED,
                    repository_url=repository_url,
                    cache_path=str(cache_path),
                    validation_status=validation_status,
                    total_duration_ms=result['performance_metrics']['total_duration_ms'],
                    validation_checks_passed=sum(1 for v in validation_checks.values() if v),
                    validation_checks_total=len(validation_checks),
                    error_details=error_details
                )
            
            return result
            
        except RepositoryError:
            # Re-raise repository errors with additional context
            total_duration = (time.time() - start_time) * 1000
            self.logger.error(
                "Repository clone validation failed due to repository error",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.FAILED,
                repository_url=repository_url,
                total_duration_ms=round(total_duration, 2)
            )
            raise
        except Exception as e:
            total_duration = (time.time() - start_time) * 1000
            self.logger.error(
                "Repository clone validation failed with unexpected error",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.FAILED,
                repository_url=repository_url,
                total_duration_ms=round(total_duration, 2),
                error=e
            )
            raise RepositoryError(
                f"Repository clone validation failed: {str(e)}",
                repository_url=repository_url
            )
    
    def _validate_remote_url_match(self, expected_url: str, actual_url: str) -> bool:
        """
        Validate that remote URL matches expected repository URL.
        
        This handles cases where authentication tokens may be present in URLs
        and normalizes URLs for comparison.
        
        Args:
            expected_url: Expected repository URL
            actual_url: Actual remote URL from git
            
        Returns:
            True if URLs match (accounting for auth differences)
        """
        try:
            from urllib.parse import urlparse
            
            # Parse both URLs
            expected_parsed = urlparse(expected_url)
            actual_parsed = urlparse(actual_url)
            
            # Compare scheme, netloc (without auth), and path
            expected_netloc = expected_parsed.netloc.split('@')[-1] if '@' in expected_parsed.netloc else expected_parsed.netloc
            actual_netloc = actual_parsed.netloc.split('@')[-1] if '@' in actual_parsed.netloc else actual_parsed.netloc
            
            return (
                expected_parsed.scheme.lower() == actual_parsed.scheme.lower() and
                expected_netloc.lower() == actual_netloc.lower() and
                expected_parsed.path.lower() == actual_parsed.path.lower()
            )
            
        except Exception:
            # If parsing fails, do simple string comparison
            return expected_url.lower() == actual_url.lower()
    
    def _validate_file_permissions(self, directory: Path) -> bool:
        """
        Validate that file permissions are appropriate for the cache directory.
        
        Args:
            directory: Directory to validate permissions for
            
        Returns:
            True if permissions are valid
        """
        try:
            # Check directory permissions
            dir_stat = directory.stat()
            dir_mode = stat.S_IMODE(dir_stat.st_mode)
            
            # Directory should be readable and writable by owner
            if not (dir_mode & stat.S_IRUSR and dir_mode & stat.S_IWUSR):
                return False
            
            # Check a few files for basic permissions
            file_count = 0
            for item in directory.rglob('*'):
                if item.is_file() and file_count < 5:  # Check first 5 files only
                    try:
                        file_stat = item.stat()
                        file_mode = stat.S_IMODE(file_stat.st_mode)
                        
                        # File should be readable by owner
                        if not (file_mode & stat.S_IRUSR):
                            return False
                        
                        file_count += 1
                    except (OSError, IOError):
                        # Skip files that can't be accessed
                        continue
            
            return True
            
        except (OSError, IOError):
            return False
    
    @log_performance(get_structured_logger(__name__), "fetch_latest_changes")
    def fetch_latest_changes(
        self,
        repository_url: str,
        project_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        auth_token: Optional[str] = None,
        timeout_seconds: int = 30
    ) -> Dict[str, Any]:
        """
        Fetch latest changes from remote repository if repository exists in cache.
        
        This method performs git pull operations to update an existing cached repository
        with the latest changes from the remote. It follows the established patterns
        for security, logging, and error handling.
        
        Args:
            repository_url: Repository URL to fetch changes from
            project_id: Optional project identifier for logging
            execution_id: Optional execution identifier for logging
            auth_token: Optional authentication token for private repositories
            timeout_seconds: Timeout for git operations (default: 30s)
            
        Returns:
            Dictionary containing fetch operation results:
            {
                'success': bool,
                'repository_url': str,
                'cache_path': str,
                'fetch_status': str,  # 'updated', 'up_to_date', 'not_found', 'failed'
                'changes_fetched': bool,
                'commits_ahead': int,
                'commits_behind': int,
                'performance_metrics': Dict[str, float],
                'repository_size_bytes': int,
                'files_changed': int
            }
            
        Raises:
            RepositoryError: If fetch operation fails or URL validation fails
        """
        start_time = time.time()
        
        try:
            # Validate repository URL with comprehensive security checks
            self._validate_repository_url(repository_url)
            
            self.logger.info(
                "Starting repository fetch latest changes operation",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.STARTED,
                repository_url=repository_url,
                timeout_seconds=timeout_seconds
            )
            
            # Check if repository exists in cache
            cache_path = self.get_cache_directory(repository_url)
            if not cache_path or not cache_path.exists():
                # Repository not found in cache
                duration_ms = (time.time() - start_time) * 1000
                result = {
                    'success': False,
                    'repository_url': repository_url,
                    'cache_path': None,
                    'fetch_status': 'not_found',
                    'changes_fetched': False,
                    'commits_ahead': 0,
                    'commits_behind': 0,
                    'performance_metrics': {
                        'total_duration_ms': round(duration_ms, 2),
                        'git_fetch_duration_ms': 0.0,
                        'validation_duration_ms': round(duration_ms, 2)
                    },
                    'repository_size_bytes': 0,
                    'files_changed': 0
                }
                
                self.logger.warn(
                    "Repository not found in cache, cannot fetch changes",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    status=LogStatus.FAILED,
                    repository_url=repository_url,
                    fetch_duration_ms=round(duration_ms, 2)
                )
                
                return result
            
            # Verify this is a valid git repository
            git_dir = cache_path / '.git'
            if not git_dir.exists() or not git_dir.is_dir():
                raise RepositoryError(
                    "Cache directory exists but is not a valid git repository",
                    repository_url=repository_url
                )
            
            self.logger.info(
                "Executing git fetch operation",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.IN_PROGRESS,
                repository_url=repository_url,
                cache_path=str(cache_path),
                timeout_seconds=timeout_seconds
            )
            
            # Get repository size before fetch for comparison
            repo_size_before = self._get_directory_size(cache_path)
            
            # Execute git fetch with timeout and error handling
            fetch_start_time = time.time()
            try:
                # First, fetch the latest changes from remote
                fetch_result = subprocess.run(
                    ["git", "fetch", "origin"],
                    cwd=cache_path,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds
                )
                
                if fetch_result.returncode != 0:
                    error_output = fetch_result.stderr or fetch_result.stdout or "Unknown git fetch error"
                    self.logger.error(
                        "Git fetch operation failed",
                        correlation_id=self.correlation_id,
                        project_id=project_id,
                        execution_id=execution_id,
                        status=LogStatus.FAILED,
                        repository_url=repository_url,
                        git_error=error_output,
                        git_return_code=fetch_result.returncode
                    )
                    
                    raise RepositoryError(
                        f"Git fetch failed: {error_output}",
                        repository_url=repository_url
                    )
                
                # Check if there are changes to pull
                status_result = subprocess.run(
                    ["git", "status", "-uno", "--porcelain"],
                    cwd=cache_path,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds
                )
                
                if status_result.returncode != 0:
                    raise RepositoryError(
                        f"Git status check failed: {status_result.stderr}",
                        repository_url=repository_url
                    )
                
                # Check commits ahead/behind
                rev_list_result = subprocess.run(
                    ["git", "rev-list", "--count", "--left-right", "HEAD...origin/HEAD"],
                    cwd=cache_path,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds
                )
                
                commits_ahead = 0
                commits_behind = 0
                if rev_list_result.returncode == 0 and rev_list_result.stdout.strip():
                    try:
                        ahead_behind = rev_list_result.stdout.strip().split('\t')
                        if len(ahead_behind) >= 2:
                            commits_ahead = int(ahead_behind[0])
                            commits_behind = int(ahead_behind[1])
                    except (ValueError, IndexError):
                        # If parsing fails, assume no changes
                        pass
                
                changes_fetched = False
                files_changed = 0
                
                # If there are commits behind, pull them
                if commits_behind > 0:
                    pull_result = subprocess.run(
                        ["git", "pull", "origin", "HEAD"],
                        cwd=cache_path,
                        capture_output=True,
                        text=True,
                        timeout=timeout_seconds
                    )
                    
                    if pull_result.returncode != 0:
                        error_output = pull_result.stderr or pull_result.stdout or "Unknown git pull error"
                        self.logger.error(
                            "Git pull operation failed",
                            correlation_id=self.correlation_id,
                            project_id=project_id,
                            execution_id=execution_id,
                            status=LogStatus.FAILED,
                            repository_url=repository_url,
                            git_error=error_output,
                            git_return_code=pull_result.returncode
                        )
                        
                        raise RepositoryError(
                            f"Git pull failed: {error_output}",
                            repository_url=repository_url
                        )
                    
                    changes_fetched = True
                    
                    # Count changed files from the pull output
                    if pull_result.stdout:
                        # Parse git pull output to count changed files
                        lines = pull_result.stdout.split('\n')
                        for line in lines:
                            if 'file' in line and ('changed' in line or 'insertion' in line or 'deletion' in line):
                                try:
                                    # Extract number from lines like "5 files changed, 10 insertions(+), 2 deletions(-)"
                                    parts = line.split()
                                    if len(parts) > 0 and parts[0].isdigit():
                                        files_changed = int(parts[0])
                                        break
                                except (ValueError, IndexError):
                                    pass
                
                fetch_duration_ms = (time.time() - fetch_start_time) * 1000
                
            except subprocess.TimeoutExpired:
                # Handle timeout
                fetch_duration_ms = (time.time() - fetch_start_time) * 1000
                
                self.logger.error(
                    "Git fetch operation timed out",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    status=LogStatus.FAILED,
                    repository_url=repository_url,
                    timeout_seconds=timeout_seconds,
                    fetch_duration_ms=round(fetch_duration_ms, 2)
                )
                
                raise RepositoryError(
                    f"Git fetch timed out after {timeout_seconds} seconds",
                    repository_url=repository_url
                )
            
            # Get repository size after fetch
            repo_size_after = self._get_directory_size(cache_path)
            total_duration_ms = (time.time() - start_time) * 1000
            
            # Determine fetch status
            if changes_fetched:
                fetch_status = 'updated'
            elif commits_behind == 0:
                fetch_status = 'up_to_date'
            else:
                fetch_status = 'no_changes'
            
            # Build successful result
            result = {
                'success': True,
                'repository_url': repository_url,
                'cache_path': str(cache_path),
                'fetch_status': fetch_status,
                'changes_fetched': changes_fetched,
                'commits_ahead': commits_ahead,
                'commits_behind': commits_behind,
                'performance_metrics': {
                    'total_duration_ms': round(total_duration_ms, 2),
                    'git_fetch_duration_ms': round(fetch_duration_ms, 2),
                    'validation_duration_ms': round(total_duration_ms - fetch_duration_ms, 2)
                },
                'repository_size_bytes': repo_size_after,
                'files_changed': files_changed
            }
            
            self.logger.info(
                "Repository fetch latest changes completed successfully",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.COMPLETED,
                repository_url=repository_url,
                cache_path=str(cache_path),
                fetch_status=fetch_status,
                changes_fetched=changes_fetched,
                commits_behind=commits_behind,
                files_changed=files_changed,
                total_duration_ms=result['performance_metrics']['total_duration_ms'],
                git_fetch_duration_ms=result['performance_metrics']['git_fetch_duration_ms']
            )
            
            return result
            
        except RepositoryError:
            # Re-raise repository errors with additional context
            total_duration_ms = (time.time() - start_time) * 1000
            self.logger.error(
                "Repository fetch latest changes failed due to repository error",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.FAILED,
                repository_url=repository_url,
                total_duration_ms=round(total_duration_ms, 2)
            )
            raise
        except Exception as e:
            total_duration_ms = (time.time() - start_time) * 1000
            self.logger.error(
                "Repository fetch latest changes failed with unexpected error",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.FAILED,
                repository_url=repository_url,
                total_duration_ms=round(total_duration_ms, 2),
                error=e
            )
            raise RepositoryError(
                f"Repository fetch latest changes failed: {str(e)}",
                repository_url=repository_url
            )
    
    @log_performance(get_structured_logger(__name__), "validate_fetch_operation")
    def validate_fetch_operation(
        self,
        repository_url: str,
        project_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        timeout_seconds: int = 10
    ) -> Dict[str, Any]:
        """
        Validate successful fetch operation with comprehensive repository state checks.
        
        This method performs comprehensive validation of fetch operations to ensure
        the repository is in a consistent state after fetching latest changes. It validates
        git repository structure, remote synchronization, and repository health.
        
        Args:
            repository_url: Repository URL to validate fetch operation for
            project_id: Optional project identifier for logging
            execution_id: Optional execution identifier for logging
            timeout_seconds: Timeout for git operations (default: 10s)
            
        Returns:
            Dictionary containing validation results:
            {
                'is_valid': bool,
                'repository_url': str,
                'cache_path': str,
                'validation_status': str,  # 'valid', 'invalid', 'not_found'
                'validation_checks': Dict[str, bool],
                'performance_metrics': Dict[str, float],
                'repository_info': Dict[str, Any],
                'fetch_validation': Dict[str, Any],
                'error_details': Optional[List[str]]
            }
            
        Raises:
            RepositoryError: If URL validation fails or validation encounters critical errors
        """
        start_time = time.time()
        
        try:
            # Validate repository URL with comprehensive security checks
            self._validate_repository_url(repository_url)
            
            self.logger.info(
                "Starting repository fetch operation validation",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.STARTED,
                repository_url=repository_url,
                timeout_seconds=timeout_seconds
            )
            
            # Get cache directory for the repository
            cache_path = self.get_cache_directory(repository_url)
            if not cache_path:
                # Repository not found in cache
                validation_duration = (time.time() - start_time) * 1000
                result = {
                    'is_valid': False,
                    'repository_url': repository_url,
                    'cache_path': None,
                    'validation_status': 'not_found',
                    'validation_checks': {},
                    'performance_metrics': {
                        'total_duration_ms': round(validation_duration, 2),
                        'git_validation_duration_ms': 0.0,
                        'fetch_validation_duration_ms': 0.0,
                        'structure_validation_duration_ms': round(validation_duration, 2)
                    },
                    'repository_info': {},
                    'fetch_validation': {},
                    'error_details': ['Repository not found in cache']
                }
                
                self.logger.warn(
                    "Repository fetch validation failed - not found in cache",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    status=LogStatus.FAILED,
                    repository_url=repository_url,
                    validation_duration_ms=round(validation_duration, 2)
                )
                
                return result
            
            # Initialize validation tracking
            validation_checks = {}
            error_details = []
            git_validation_start = time.time()
            
            # 1. Verify .git directory exists
            git_dir = cache_path / '.git'
            validation_checks['git_directory_exists'] = git_dir.exists() and git_dir.is_dir()
            if not validation_checks['git_directory_exists']:
                error_details.append('.git directory not found or not a directory')
            
            # 2. Check git status command works (repository is properly initialized)
            validation_checks['git_status_works'] = False
            try:
                if validation_checks['git_directory_exists']:
                    result_process = subprocess.run(
                        ["git", "status", "--porcelain"],
                        cwd=cache_path,
                        capture_output=True,
                        text=True,
                        timeout=timeout_seconds
                    )
                    validation_checks['git_status_works'] = result_process.returncode == 0
                    if not validation_checks['git_status_works']:
                        error_details.append(f'git status failed: {result_process.stderr}')
            except subprocess.TimeoutExpired:
                error_details.append(f'git status timed out after {timeout_seconds} seconds')
            except Exception as e:
                error_details.append(f'git status error: {str(e)}')
            
            # 3. Validate remote origin is correctly configured
            validation_checks['remote_origin_configured'] = False
            remote_url = None
            try:
                if validation_checks['git_status_works']:
                    result_process = subprocess.run(
                        ["git", "remote", "get-url", "origin"],
                        cwd=cache_path,
                        capture_output=True,
                        text=True,
                        timeout=timeout_seconds
                    )
                    if result_process.returncode == 0:
                        remote_url = result_process.stdout.strip()
                        # Verify remote URL matches expected repository URL
                        validation_checks['remote_origin_configured'] = self._validate_remote_url_match(
                            repository_url, remote_url
                        )
                        if not validation_checks['remote_origin_configured']:
                            error_details.append(f'Remote origin URL mismatch: expected {repository_url}, got {remote_url}')
                    else:
                        error_details.append(f'git remote get-url failed: {result_process.stderr}')
            except subprocess.TimeoutExpired:
                error_details.append(f'git remote get-url timed out after {timeout_seconds} seconds')
            except Exception as e:
                error_details.append(f'git remote get-url error: {str(e)}')
            
            # 4. Check repository synchronization with remote
            validation_checks['repository_synchronized'] = False
            commits_ahead = 0
            commits_behind = 0
            try:
                if validation_checks['git_status_works']:
                    # Check if repository is synchronized with remote
                    result_process = subprocess.run(
                        ["git", "rev-list", "--count", "--left-right", "HEAD...origin/HEAD"],
                        cwd=cache_path,
                        capture_output=True,
                        text=True,
                        timeout=timeout_seconds
                    )
                    if result_process.returncode == 0 and result_process.stdout.strip():
                        try:
                            ahead_behind = result_process.stdout.strip().split('\t')
                            if len(ahead_behind) >= 2:
                                commits_ahead = int(ahead_behind[0])
                                commits_behind = int(ahead_behind[1])
                                # Repository is synchronized if not behind (ahead is acceptable)
                                validation_checks['repository_synchronized'] = commits_behind == 0
                                if commits_behind > 0:
                                    error_details.append(f'Repository is {commits_behind} commits behind remote')
                        except (ValueError, IndexError):
                            error_details.append('Failed to parse git rev-list output')
                    else:
                        error_details.append(f'git rev-list failed: {result_process.stderr}')
            except subprocess.TimeoutExpired:
                error_details.append(f'git rev-list timed out after {timeout_seconds} seconds')
            except Exception as e:
                error_details.append(f'git rev-list error: {str(e)}')
            
            # 5. Verify working directory is clean (no uncommitted changes)
            validation_checks['working_directory_clean'] = False
            try:
                if validation_checks['git_status_works']:
                    result_process = subprocess.run(
                        ["git", "status", "--porcelain"],
                        cwd=cache_path,
                        capture_output=True,
                        text=True,
                        timeout=timeout_seconds
                    )
                    if result_process.returncode == 0:
                        # Working directory is clean if no output from git status --porcelain
                        validation_checks['working_directory_clean'] = len(result_process.stdout.strip()) == 0
                        if not validation_checks['working_directory_clean']:
                            error_details.append('Working directory has uncommitted changes')
                    else:
                        error_details.append(f'git status --porcelain failed: {result_process.stderr}')
            except subprocess.TimeoutExpired:
                error_details.append(f'git status --porcelain timed out after {timeout_seconds} seconds')
            except Exception as e:
                error_details.append(f'git status --porcelain error: {str(e)}')
            
            git_validation_duration = (time.time() - git_validation_start) * 1000
            
            # 6. Fetch-specific validation
            fetch_validation_start = time.time()
            fetch_validation = {}
            
            # Verify last fetch was recent (within reasonable time)
            try:
                if validation_checks['git_directory_exists']:
                    fetch_head_file = git_dir / 'FETCH_HEAD'
                    if fetch_head_file.exists():
                        fetch_stat = fetch_head_file.stat()
                        fetch_time = datetime.fromtimestamp(fetch_stat.st_mtime)
                        time_since_fetch = datetime.now() - fetch_time
                        fetch_validation['last_fetch_time'] = fetch_time.isoformat()
                        fetch_validation['minutes_since_fetch'] = round(time_since_fetch.total_seconds() / 60, 2)
                        # Consider fetch recent if within last 24 hours
                        fetch_validation['fetch_recent'] = time_since_fetch.total_seconds() < 86400
                    else:
                        fetch_validation['last_fetch_time'] = None
                        fetch_validation['minutes_since_fetch'] = None
                        fetch_validation['fetch_recent'] = False
                        error_details.append('FETCH_HEAD file not found - repository may not have been fetched')
            except Exception as e:
                fetch_validation['last_fetch_time'] = None
                fetch_validation['minutes_since_fetch'] = None
                fetch_validation['fetch_recent'] = False
                error_details.append(f'Failed to check fetch timestamp: {str(e)}')
            
            # 7. Ensure proper file permissions and directory structure
            structure_validation_start = time.time()
            validation_checks['proper_permissions'] = self._validate_file_permissions(cache_path)
            if not validation_checks['proper_permissions']:
                error_details.append('Invalid file permissions detected')
            
            # 8. Basic directory structure validation
            validation_checks['directory_structure_valid'] = cache_path.exists() and cache_path.is_dir()
            if not validation_checks['directory_structure_valid']:
                error_details.append('Cache directory structure is invalid')
            
            structure_validation_duration = (time.time() - structure_validation_start) * 1000
            fetch_validation_duration = (time.time() - fetch_validation_start) * 1000
            
            # Collect repository information
            repository_info = {}
            try:
                repository_info['cache_path'] = str(cache_path)
                repository_info['repository_size_bytes'] = self._get_directory_size(cache_path)
                repository_info['file_count'] = self._count_files_in_directory(cache_path)
                repository_info['remote_url'] = remote_url
                repository_info['commits_ahead'] = commits_ahead
                repository_info['commits_behind'] = commits_behind
                
                # Get current branch info if possible
                if validation_checks['git_status_works']:
                    try:
                        result_process = subprocess.run(
                            ["git", "branch", "--show-current"],
                            cwd=cache_path,
                            capture_output=True,
                            text=True,
                            timeout=timeout_seconds
                        )
                        if result_process.returncode == 0:
                            repository_info['current_branch'] = result_process.stdout.strip()
                    except Exception:
                        # Non-critical, continue without branch info
                        pass
                        
                # Get last commit info if possible
                if validation_checks['git_status_works']:
                    try:
                        result_process = subprocess.run(
                            ["git", "log", "-1", "--format=%H|%s|%an|%ad", "--date=iso"],
                            cwd=cache_path,
                            capture_output=True,
                            text=True,
                            timeout=timeout_seconds
                        )
                        if result_process.returncode == 0:
                            commit_parts = result_process.stdout.strip().split('|', 3)
                            if len(commit_parts) >= 4:
                                repository_info['last_commit'] = {
                                    'hash': commit_parts[0],
                                    'message': commit_parts[1],
                                    'author': commit_parts[2],
                                    'date': commit_parts[3]
                                }
                    except Exception:
                        # Non-critical, continue without commit info
                        pass
                        
            except Exception as e:
                self.logger.warn(
                    "Failed to collect repository information",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    repository_url=repository_url,
                    error=str(e)
                )
            
            # Determine overall validation status
            critical_checks = [
                'git_directory_exists',
                'git_status_works',
                'remote_origin_configured',
                'directory_structure_valid',
                'working_directory_clean'
            ]
            
            # Repository synchronization is important but not critical for basic validation
            important_checks = [
                'repository_synchronized'
            ]
            
            critical_valid = all(validation_checks.get(check, False) for check in critical_checks)
            important_valid = all(validation_checks.get(check, False) for check in important_checks)
            
            is_valid = critical_valid and important_valid
            if critical_valid and not important_valid:
                validation_status = 'valid_with_warnings'
            elif critical_valid:
                validation_status = 'valid'
            else:
                validation_status = 'invalid'
            
            # Calculate total duration
            total_duration = (time.time() - start_time) * 1000
            
            # Build result
            result = {
                'is_valid': is_valid,
                'repository_url': repository_url,
                'cache_path': str(cache_path),
                'validation_status': validation_status,
                'validation_checks': validation_checks,
                'performance_metrics': {
                    'total_duration_ms': round(total_duration, 2),
                    'git_validation_duration_ms': round(git_validation_duration, 2),
                    'fetch_validation_duration_ms': round(fetch_validation_duration, 2),
                    'structure_validation_duration_ms': round(structure_validation_duration, 2)
                },
                'repository_info': repository_info,
                'fetch_validation': fetch_validation,
                'error_details': error_details if error_details else None
            }
            
            # Log completion
            if is_valid:
                self.logger.info(
                    "Repository fetch validation completed successfully",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    status=LogStatus.COMPLETED,
                    repository_url=repository_url,
                    cache_path=str(cache_path),
                    validation_status=validation_status,
                    total_duration_ms=result['performance_metrics']['total_duration_ms'],
                    validation_checks_passed=sum(1 for v in validation_checks.values() if v),
                    validation_checks_total=len(validation_checks),
                    commits_behind=commits_behind,
                    fetch_recent=fetch_validation.get('fetch_recent', False)
                )
            else:
                self.logger.warn(
                    "Repository fetch validation completed with issues",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    status=LogStatus.COMPLETED,
                    repository_url=repository_url,
                    cache_path=str(cache_path),
                    validation_status=validation_status,
                    total_duration_ms=result['performance_metrics']['total_duration_ms'],
                    validation_checks_passed=sum(1 for v in validation_checks.values() if v),
                    validation_checks_total=len(validation_checks),
                    error_details=error_details
                )
            
            return result
            
        except RepositoryError:
            # Re-raise repository errors with additional context
            total_duration = (time.time() - start_time) * 1000
            self.logger.error(
                "Repository fetch validation failed due to repository error",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.FAILED,
                repository_url=repository_url,
                total_duration_ms=round(total_duration, 2)
            )
            raise
        except Exception as e:
            total_duration = (time.time() - start_time) * 1000
            self.logger.error(
                "Repository fetch validation failed with unexpected error",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.FAILED,
                repository_url=repository_url,
                total_duration_ms=round(total_duration, 2),
                error=e
            )
            raise RepositoryError(
                f"Repository fetch validation failed: {str(e)}",
                repository_url=repository_url
            )
    
    @log_performance(get_structured_logger(__name__), "get_default_task_list_template")
    def get_default_task_list_template(
        self,
        project_id: Optional[str] = None,
        execution_id: Optional[str] = None
    ) -> str:
        """
        Get the default task list template content for repository initialization.
        
        This method provides the default task_lists.md template content that follows
        the PRD format requirements (sections 190-207) and supports ADD lenient parsing
        with auto-defaults for missing fields.
        
        Args:
            project_id: Optional project identifier for logging
            execution_id: Optional execution identifier for logging
            
        Returns:
            String containing the default task list template in Markdown format
            
        Raises:
            RepositoryError: If template retrieval encounters critical errors
        """
        start_time = time.time()
        
        try:
            self.logger.info(
                "Retrieving default task list template",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.STARTED
            )
            
            # Return the static template content
            template_content = self.DEFAULT_TASK_LIST_TEMPLATE
            
            # Validate template format before returning
            validation_result = self.validate_template_format(
                template_content,
                project_id=project_id,
                execution_id=execution_id
            )
            
            if not validation_result['is_valid']:
                self.logger.error(
                    "Default template validation failed",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    status=LogStatus.FAILED,
                    validation_errors=validation_result.get('errors', [])
                )
                raise RepositoryError(
                    f"Default template validation failed: {validation_result.get('errors', ['Unknown validation error'])}"
                )
            
            duration_ms = (time.time() - start_time) * 1000
            
            self.logger.info(
                "Default task list template retrieved successfully",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.COMPLETED,
                template_length=len(template_content),
                template_lines=len(template_content.split('\n')),
                duration_ms=round(duration_ms, 2)
            )
            
            return template_content
            
        except RepositoryError:
            raise
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(
                "Failed to retrieve default task list template",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.FAILED,
                duration_ms=round(duration_ms, 2),
                error=e
            )
            raise RepositoryError(f"Failed to get default task list template: {str(e)}")
    
    @log_performance(get_structured_logger(__name__), "validate_template_format")
    def validate_template_format(
        self,
        template_content: str,
        project_id: Optional[str] = None,
        execution_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate task list template format and structure.
        
        This method performs comprehensive validation of task list template content
        to ensure it follows the expected format and contains valid task definitions.
        It supports lenient parsing as specified in ADD requirements.
        
        Args:
            template_content: Template content to validate
            project_id: Optional project identifier for logging
            execution_id: Optional execution identifier for logging
            
        Returns:
            Dictionary containing validation results:
            {
                'is_valid': bool,
                'template_content': str,
                'validation_status': str,  # 'valid', 'valid_with_warnings', 'invalid'
                'validation_checks': Dict[str, bool],
                'performance_metrics': Dict[str, float],
                'template_info': Dict[str, Any],
                'errors': Optional[List[str]],
                'warnings': Optional[List[str]]
            }
            
        Raises:
            RepositoryError: If validation encounters critical errors
        """
        start_time = time.time()
        
        try:
            if not isinstance(template_content, str):
                raise RepositoryError(
                    "Template content must be a string",
                    template_content=type(template_content).__name__
                )
            
            self.logger.info(
                "Starting template format validation",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.STARTED,
                template_length=len(template_content)
            )
            
            # Initialize validation tracking
            validation_checks = {}
            errors = []
            warnings = []
            
            # 1. Basic content validation
            validation_checks['has_content'] = len(template_content.strip()) > 0
            if not validation_checks['has_content']:
                errors.append('Template content is empty')
            
            # 2. Check for markdown structure
            validation_checks['has_markdown_headers'] = '# ' in template_content or '## ' in template_content
            if not validation_checks['has_markdown_headers']:
                warnings.append('Template does not contain markdown headers')
            
            # 3. Check for task structure patterns
            task_id_pattern = re.compile(r'####?\s+\d+\.\d+\.\d+')
            task_matches = task_id_pattern.findall(template_content)
            validation_checks['has_task_ids'] = len(task_matches) > 0
            if not validation_checks['has_task_ids']:
                warnings.append('Template does not contain task ID patterns (e.g., 1.1.1)')
            
            # 4. Check for required task fields (lenient approach)
            required_patterns = {
                'description': re.compile(r'[Dd]escription.*:', re.IGNORECASE),
                'type': re.compile(r'[Tt]ype.*:', re.IGNORECASE),
                'status': re.compile(r'[Ss]tatus.*:', re.IGNORECASE)
            }
            
            for field, pattern in required_patterns.items():
                field_key = f'has_{field}_field'
                validation_checks[field_key] = bool(pattern.search(template_content))
                if not validation_checks[field_key]:
                    warnings.append(f'Template does not contain {field} field patterns')
            
            # 5. Check for reasonable length (not too short, not too long)
            min_length = 100  # Minimum reasonable template length
            max_length = 50000  # Maximum reasonable template length
            validation_checks['reasonable_length'] = min_length <= len(template_content) <= max_length
            if not validation_checks['reasonable_length']:
                if len(template_content) < min_length:
                    errors.append(f'Template content too short (minimum {min_length} characters)')
                else:
                    errors.append(f'Template content too long (maximum {max_length} characters)')
            
            # 6. Check for dangerous content patterns
            dangerous_patterns = [
                re.compile(r'<script', re.IGNORECASE),
                re.compile(r'javascript:', re.IGNORECASE),
                re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F]'),  # Control characters except \t, \n, \r
            ]
            
            validation_checks['no_dangerous_content'] = True
            for pattern in dangerous_patterns:
                if pattern.search(template_content):
                    validation_checks['no_dangerous_content'] = False
                    errors.append('Template contains potentially dangerous content')
                    break
            
            # Collect template information
            template_info = {
                'content_length': len(template_content),
                'line_count': len(template_content.split('\n')),
                'task_count': len(task_matches),
                'header_count': len(re.findall(r'^#+\s', template_content, re.MULTILINE)),
                'word_count': len(template_content.split())
            }
            
            # Determine overall validation status
            critical_checks = [
                'has_content',
                'reasonable_length',
                'no_dangerous_content'
            ]
            
            important_checks = [
                'has_markdown_headers',
                'has_task_ids'
            ]
            
            critical_valid = all(validation_checks.get(check, False) for check in critical_checks)
            important_valid = all(validation_checks.get(check, False) for check in important_checks)
            
            is_valid = critical_valid and len(errors) == 0
            if critical_valid and important_valid and len(warnings) == 0:
                validation_status = 'valid'
            elif critical_valid and len(warnings) > 0:
                validation_status = 'valid_with_warnings'
            else:
                validation_status = 'invalid'
            
            # Calculate performance metrics
            duration_ms = (time.time() - start_time) * 1000
            performance_metrics = {
                'total_duration_ms': round(duration_ms, 2),
                'validation_duration_ms': round(duration_ms, 2)
            }
            
            # Build result
            result = {
                'is_valid': is_valid,
                'template_content': template_content,
                'validation_status': validation_status,
                'validation_checks': validation_checks,
                'performance_metrics': performance_metrics,
                'template_info': template_info,
                'errors': errors if errors else None,
                'warnings': warnings if warnings else None
            }
            
            # Log completion
            if is_valid:
                self.logger.info(
                    "Template format validation completed successfully",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    status=LogStatus.COMPLETED,
                    validation_status=validation_status,
                    total_duration_ms=performance_metrics['total_duration_ms'],
                    validation_checks_passed=sum(1 for v in validation_checks.values() if v),
                    validation_checks_total=len(validation_checks),
                    template_length=template_info['content_length'],
                    task_count=template_info['task_count']
                )
            else:
                self.logger.warn(
                    "Template format validation completed with issues",
                    correlation_id=self.correlation_id,
                    project_id=project_id,
                    execution_id=execution_id,
                    status=LogStatus.COMPLETED,
                    validation_status=validation_status,
                    total_duration_ms=performance_metrics['total_duration_ms'],
                    validation_checks_passed=sum(1 for v in validation_checks.values() if v),
                    validation_checks_total=len(validation_checks),
                    errors=errors,
                    warnings=warnings
                )
            
            return result
            
        except RepositoryError:
            raise
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(
                "Template format validation failed with unexpected error",
                correlation_id=self.correlation_id,
                project_id=project_id,
                execution_id=execution_id,
                status=LogStatus.FAILED,
                duration_ms=round(duration_ms, 2),
                error=e
            )
            raise RepositoryError(f"Template format validation failed: {str(e)}")


def get_repository_cache_manager(correlation_id: Optional[str] = None) -> RepositoryCacheManager:
    """
    Factory function to get a repository cache manager instance.
    
    Args:
        correlation_id: Optional correlation ID for distributed tracing
        
    Returns:
        RepositoryCacheManager instance
    """
    return RepositoryCacheManager(correlation_id=correlation_id)