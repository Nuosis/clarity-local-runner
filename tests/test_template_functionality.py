"""
Unit tests for Repository Cache Manager template functionality.

This module tests the template reading and validation functionality added to
RepositoryCacheManager for Branch 4.4.1 implementation.
"""

import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from services.repository_cache_manager import RepositoryCacheManager, get_repository_cache_manager
from core.exceptions import RepositoryError
from core.structured_logging import LogStatus


class TestRepositoryCacheManagerTemplate:
    """Test suite for RepositoryCacheManager template functionality."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.correlation_id = "test_template_123"
        self.project_id = "test_project_456"
        self.execution_id = "test_execution_789"
        
        # Create manager instance with test correlation ID
        self.manager = RepositoryCacheManager(correlation_id=self.correlation_id)
        
        # Mock logger to avoid actual logging during tests
        self.mock_logger = Mock()
        self.manager.logger = self.mock_logger
    
    def test_get_default_task_list_template_success(self):
        """Test successful retrieval of default task list template."""
        # Act
        template_content = self.manager.get_default_task_list_template(
            project_id=self.project_id,
            execution_id=self.execution_id
        )
        
        # Assert
        assert isinstance(template_content, str)
        assert len(template_content) > 0
        assert "# Task List" in template_content
        assert "1.1.1 Add DEVTEAM_ENABLED flag" in template_content
        assert "1.2.1 Initialize project structure" in template_content
        assert "2.1.1 Configure development environment" in template_content
        
        # Verify logging calls
        self.mock_logger.info.assert_any_call(
            "Retrieving default task list template",
            correlation_id=self.correlation_id,
            project_id=self.project_id,
            execution_id=self.execution_id,
            status=LogStatus.STARTED
        )
        
        self.mock_logger.info.assert_any_call(
            "Default task list template retrieved successfully",
            correlation_id=self.correlation_id,
            project_id=self.project_id,
            execution_id=self.execution_id,
            status=LogStatus.COMPLETED,
            template_length=len(template_content),
            template_lines=len(template_content.split('\n')),
            duration_ms=pytest.approx(0, abs=100)  # Allow some tolerance for timing
        )
    
    def test_get_default_task_list_template_without_optional_params(self):
        """Test template retrieval without optional parameters."""
        # Act
        template_content = self.manager.get_default_task_list_template()
        
        # Assert
        assert isinstance(template_content, str)
        assert len(template_content) > 0
        assert "# Task List" in template_content
        
        # Verify logging calls with None values
        self.mock_logger.info.assert_any_call(
            "Retrieving default task list template",
            correlation_id=self.correlation_id,
            project_id=None,
            execution_id=None,
            status=LogStatus.STARTED
        )
    
    @patch.object(RepositoryCacheManager, 'validate_template_format')
    def test_get_default_task_list_template_validation_failure(self, mock_validate):
        """Test template retrieval when validation fails."""
        # Arrange
        mock_validate.return_value = {
            'is_valid': False,
            'errors': ['Template validation failed']
        }
        
        # Act & Assert
        with pytest.raises(RepositoryError) as exc_info:
            self.manager.get_default_task_list_template(
                project_id=self.project_id,
                execution_id=self.execution_id
            )
        
        assert "Default template validation failed" in str(exc_info.value)
        
        # Verify error logging
        self.mock_logger.error.assert_called_once()
        error_call = self.mock_logger.error.call_args
        assert error_call[1]['status'] == LogStatus.FAILED
        assert error_call[1]['correlation_id'] == self.correlation_id
    
    @patch.object(RepositoryCacheManager, 'validate_template_format')
    def test_get_default_task_list_template_unexpected_error(self, mock_validate):
        """Test template retrieval with unexpected error."""
        # Arrange
        mock_validate.side_effect = Exception("Unexpected validation error")
        
        # Act & Assert
        with pytest.raises(RepositoryError) as exc_info:
            self.manager.get_default_task_list_template(
                project_id=self.project_id,
                execution_id=self.execution_id
            )
        
        assert "Failed to get default task list template" in str(exc_info.value)
        
        # Verify error logging
        self.mock_logger.error.assert_called_once()
        error_call = self.mock_logger.error.call_args
        assert error_call[1]['status'] == LogStatus.FAILED
    
    def test_validate_template_format_valid_template(self):
        """Test validation of a valid template."""
        # Arrange
        valid_template = """# Task List

## Project Tasks

### 1. Core Configuration Tasks

#### 1.1.1 Add DEVTEAM_ENABLED flag to src/config.js
- **Description**: Add DEVTEAM_ENABLED flag with default false and JSDoc documentation
- **Type**: atomic
- **Status**: pending
"""
        
        # Act
        result = self.manager.validate_template_format(
            valid_template,
            project_id=self.project_id,
            execution_id=self.execution_id
        )
        
        # Assert
        assert result['is_valid'] is True
        assert result['validation_status'] == 'valid'
        assert result['template_content'] == valid_template
        assert 'validation_checks' in result
        assert 'performance_metrics' in result
        assert 'template_info' in result
        
        # Check specific validation checks
        checks = result['validation_checks']
        assert checks['has_content'] is True
        assert checks['has_markdown_headers'] is True
        assert checks['has_task_ids'] is True
        assert checks['reasonable_length'] is True
        assert checks['no_dangerous_content'] is True
        
        # Check template info
        info = result['template_info']
        assert info['content_length'] == len(valid_template)
        assert info['line_count'] == len(valid_template.split('\n'))
        assert info['task_count'] == 1  # One task ID pattern
        assert info['word_count'] > 0
    
    def test_validate_template_format_empty_template(self):
        """Test validation of empty template."""
        # Act
        result = self.manager.validate_template_format(
            "",
            project_id=self.project_id,
            execution_id=self.execution_id
        )
        
        # Assert
        assert result['is_valid'] is False
        assert result['validation_status'] == 'invalid'
        assert 'Template content is empty' in result['errors']
        
        # Check validation checks
        checks = result['validation_checks']
        assert checks['has_content'] is False
    
    def test_validate_template_format_too_short_template(self):
        """Test validation of template that's too short."""
        # Arrange
        short_template = "# Short"
        
        # Act
        result = self.manager.validate_template_format(
            short_template,
            project_id=self.project_id,
            execution_id=self.execution_id
        )
        
        # Assert
        assert result['is_valid'] is False
        assert result['validation_status'] == 'invalid'
        assert any('too short' in error for error in result['errors'])
        
        # Check validation checks
        checks = result['validation_checks']
        assert checks['reasonable_length'] is False
    
    def test_validate_template_format_dangerous_content(self):
        """Test validation of template with dangerous content."""
        # Arrange
        dangerous_template = """# Task List
        
<script>alert('dangerous')</script>

#### 1.1.1 Test task
- **Description**: Test task
"""
        
        # Act
        result = self.manager.validate_template_format(
            dangerous_template,
            project_id=self.project_id,
            execution_id=self.execution_id
        )
        
        # Assert
        assert result['is_valid'] is False
        assert result['validation_status'] == 'invalid'
        assert any('dangerous content' in error for error in result['errors'])
        
        # Check validation checks
        checks = result['validation_checks']
        assert checks['no_dangerous_content'] is False
    
    def test_validate_template_format_with_warnings(self):
        """Test validation of template that generates warnings."""
        # Arrange
        template_with_warnings = """# Task List
        
This is a basic template without proper task structure.
It has content and headers but missing task IDs and fields.
"""
        
        # Act
        result = self.manager.validate_template_format(
            template_with_warnings,
            project_id=self.project_id,
            execution_id=self.execution_id
        )
        
        # Assert
        assert result['is_valid'] is True  # Valid but with warnings
        assert result['validation_status'] == 'valid_with_warnings'
        assert result['warnings'] is not None
        assert len(result['warnings']) > 0
        
        # Check that warnings include expected issues
        warnings = result['warnings']
        assert any('task ID patterns' in warning for warning in warnings)
        assert any('description field' in warning for warning in warnings)
    
    def test_validate_template_format_non_string_input(self):
        """Test validation with non-string input."""
        # Act & Assert
        with pytest.raises(RepositoryError) as exc_info:
            # Use type: ignore to suppress the intentional type error for testing
            self.manager.validate_template_format(
                123,  # type: ignore # Non-string input for testing error handling
                project_id=self.project_id,
                execution_id=self.execution_id
            )
        
        assert "Template content must be a string" in str(exc_info.value)
    
    def test_validate_template_format_performance_tracking(self):
        """Test that validation tracks performance metrics."""
        # Arrange
        template = "# Test Template\n\n#### 1.1.1 Test task\n- **Description**: Test"
        
        # Act
        result = self.manager.validate_template_format(
            template,
            project_id=self.project_id,
            execution_id=self.execution_id
        )
        
        # Assert
        assert 'performance_metrics' in result
        metrics = result['performance_metrics']
        assert 'total_duration_ms' in metrics
        assert 'validation_duration_ms' in metrics
        assert metrics['total_duration_ms'] >= 0
        assert metrics['validation_duration_ms'] >= 0
    
    def test_validate_template_format_logging(self):
        """Test that validation logs appropriately."""
        # Arrange
        template = "# Test Template\n\n#### 1.1.1 Test task\n- **Description**: Test"
        
        # Act
        result = self.manager.validate_template_format(
            template,
            project_id=self.project_id,
            execution_id=self.execution_id
        )
        
        # Assert logging calls
        self.mock_logger.info.assert_any_call(
            "Starting template format validation",
            correlation_id=self.correlation_id,
            project_id=self.project_id,
            execution_id=self.execution_id,
            status=LogStatus.STARTED,
            template_length=len(template)
        )
        
        if result['is_valid']:
            self.mock_logger.info.assert_any_call(
                "Template format validation completed successfully",
                correlation_id=self.correlation_id,
                project_id=self.project_id,
                execution_id=self.execution_id,
                status=LogStatus.COMPLETED,
                validation_status=result['validation_status'],
                total_duration_ms=pytest.approx(0, abs=100),
                validation_checks_passed=pytest.approx(0, abs=10),
                validation_checks_total=pytest.approx(0, abs=10),
                template_length=len(template),
                task_count=pytest.approx(0, abs=5)
            )
    
    def test_validate_template_format_unexpected_error(self):
        """Test validation with unexpected error during processing."""
        # Arrange - Mock time.time to raise an exception
        with patch('time.time', side_effect=Exception("Time error")):
            # Act & Assert
            with pytest.raises(RepositoryError) as exc_info:
                self.manager.validate_template_format(
                    "# Test Template",
                    project_id=self.project_id,
                    execution_id=self.execution_id
                )
            
            assert "Template format validation failed" in str(exc_info.value)
    
    def test_default_task_list_template_constant_structure(self):
        """Test that the default template constant has expected structure."""
        # Act
        template = RepositoryCacheManager.DEFAULT_TASK_LIST_TEMPLATE
        
        # Assert basic structure
        assert isinstance(template, str)
        assert len(template) > 1000  # Should be substantial
        
        # Check for required sections
        assert "# Task List" in template
        assert "## Project Tasks" in template
        assert "### 1. Core Configuration Tasks" in template
        assert "### 2. Development Setup Tasks" in template
        
        # Check for example tasks from PRD
        assert "1.1.1 Add DEVTEAM_ENABLED flag" in template
        assert "1.2.1 Initialize project structure" in template
        assert "2.1.1 Configure development environment" in template
        
        # Check for required task fields
        assert "**Description**:" in template
        assert "**Type**:" in template
        assert "**Priority**:" in template
        assert "**Status**:" in template
        assert "**Dependencies**:" in template
        assert "**Files**:" in template
        assert "**Criteria**:" in template
        assert "**Estimated Duration**:" in template
        
        # Check for format guidelines
        assert "Task Format Guidelines" in template
        assert "lenient parser" in template
        assert "auto-default" in template
    
    def test_template_integration_with_existing_methods(self):
        """Test that template methods integrate properly with existing functionality."""
        # Test that template methods don't interfere with existing functionality
        
        # Act - Call template method
        template = self.manager.get_default_task_list_template()
        
        # Assert - Should not affect other manager state
        assert self.manager.correlation_id == self.correlation_id
        assert self.manager.CACHE_ROOT == Path("/workspace/repos")
        assert hasattr(self.manager, 'logger')
        
        # Template should be valid when validated
        validation_result = self.manager.validate_template_format(template)
        assert validation_result['is_valid'] is True
    
    def test_factory_function_compatibility(self):
        """Test that factory function works with template functionality."""
        # Act
        manager = get_repository_cache_manager(correlation_id="factory_test_123")
        
        # Assert
        assert isinstance(manager, RepositoryCacheManager)
        assert manager.correlation_id == "factory_test_123"
        
        # Test template functionality works
        template = manager.get_default_task_list_template()
        assert isinstance(template, str)
        assert len(template) > 0
        
        validation_result = manager.validate_template_format(template)
        assert validation_result['is_valid'] is True


class TestTemplatePerformanceRequirements:
    """Test suite for template performance requirements."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = RepositoryCacheManager(correlation_id="perf_test_123")
        # Mock logger to avoid logging overhead in performance tests
        self.manager.logger = Mock()
    
    def test_get_default_task_list_template_performance(self):
        """Test that template retrieval meets ≤2s performance requirement."""
        # Act
        start_time = time.time()
        template = self.manager.get_default_task_list_template()
        duration = time.time() - start_time
        
        # Assert
        assert duration <= 2.0  # Must meet ≤2s requirement
        assert isinstance(template, str)
        assert len(template) > 0
    
    def test_validate_template_format_performance(self):
        """Test that template validation meets ≤2s performance requirement."""
        # Arrange
        template = self.manager.DEFAULT_TASK_LIST_TEMPLATE
        
        # Act
        start_time = time.time()
        result = self.manager.validate_template_format(template)
        duration = time.time() - start_time
        
        # Assert
        assert duration <= 2.0  # Must meet ≤2s requirement
        assert result['is_valid'] is True
        
        # Check that performance metrics are reasonable
        metrics = result['performance_metrics']
        assert metrics['total_duration_ms'] <= 2000  # ≤2s in milliseconds


class TestTemplateEdgeCases:
    """Test suite for template edge cases and error conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = RepositoryCacheManager(correlation_id="edge_test_123")
        self.manager.logger = Mock()
    
    def test_validate_template_format_very_large_template(self):
        """Test validation with very large template (near max limit)."""
        # Arrange - Create large template near the limit
        large_template = "# Large Template\n" + "x" * 49000  # Just under 50k limit
        
        # Act
        result = self.manager.validate_template_format(large_template)
        
        # Assert
        assert result['is_valid'] is True
        assert result['validation_checks']['reasonable_length'] is True
    
    def test_validate_template_format_too_large_template(self):
        """Test validation with template exceeding size limit."""
        # Arrange - Create template over the limit
        too_large_template = "# Too Large Template\n" + "x" * 60000  # Over 50k limit
        
        # Act
        result = self.manager.validate_template_format(too_large_template)
        
        # Assert
        assert result['is_valid'] is False
        assert result['validation_checks']['reasonable_length'] is False
        assert any('too long' in error for error in result['errors'])
    
    def test_validate_template_format_unicode_content(self):
        """Test validation with Unicode content."""
        # Arrange
        unicode_template = """# Task List 📋

## Project Tasks 🚀

#### 1.1.1 Add DEVTEAM_ENABLED flag 🏁
- **Description**: Add DEVTEAM_ENABLED flag with émojis and ünïcödé
- **Type**: atomic
- **Status**: pending
"""
        
        # Act
        result = self.manager.validate_template_format(unicode_template)
        
        # Assert
        assert result['is_valid'] is True
        assert result['template_content'] == unicode_template
    
    def test_validate_template_format_control_characters(self):
        """Test validation with control characters."""
        # Arrange - Template with control characters (should be rejected)
        control_char_template = f"# Task List\n\n#### 1.1.1 Test\x00\x01\x02"
        
        # Act
        result = self.manager.validate_template_format(control_char_template)
        
        # Assert
        assert result['is_valid'] is False
        assert result['validation_checks']['no_dangerous_content'] is False
        assert any('dangerous content' in error for error in result['errors'])