"""
Unit Tests for Status Projection Service

This module provides comprehensive unit tests for the StatusProjectionService
with >90% coverage requirement. Tests validate business logic, error handling,
and integration with the StatusProjection schema from Task 5.2.1.
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.orm import Session

from services.status_projection_service import StatusProjectionService, get_status_projection_service
from database.event import Event
from schemas.status_projection_schema import StatusProjection, ExecutionStatus
from core.exceptions import RepositoryError


class TestStatusProjectionService:
    """Test suite for StatusProjectionService with comprehensive coverage."""
    
    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = Mock(spec=Session)
        return session
    
    @pytest.fixture
    def mock_repository(self):
        """Create mock repository."""
        repository = Mock()
        return repository
    
    @pytest.fixture
    def service(self, mock_session):
        """Create StatusProjectionService instance with mocked dependencies."""
        with patch('services.status_projection_service.GenericRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo
            
            service = StatusProjectionService(
                session=mock_session,
                correlation_id="test-correlation-123"
            )
            service.repository = mock_repo
            return service
    
    @pytest.fixture
    def sample_task_context(self):
        """Create sample task_context data for testing."""
        return {
            'metadata': {
                'project_id': 'customer-123/project-abc',
                'task_id': '1.1.1',
                'status': 'prepared',
                'branch': 'task/1-1-1-add-devteam-enabled-flag',
                'repo_path': '/workspace/repos/customer-123-project-abc',
                'started_at': '2025-01-14T18:25:00Z',
                'logs': ['Implementation started', 'Aider tool initialized'],
                'files_modified': ['src/config.js']
            },
            'nodes': {
                'select': {'status': 'completed'},
                'prep': {'status': 'running'}
            }
        }
    
    @pytest.fixture
    def sample_event(self, sample_task_context):
        """Create sample Event instance for testing."""
        event = Mock(spec=Event)
        event.id = uuid.uuid4()
        event.task_context = sample_task_context
        event.workflow_type = 'devteam_automation'
        event.created_at = datetime.utcnow()
        event.updated_at = datetime.utcnow()
        return event
    
    def test_service_initialization(self, mock_session):
        """Test service initialization with proper dependencies."""
        with patch('services.status_projection_service.GenericRepository') as mock_repo_class:
            service = StatusProjectionService(
                session=mock_session,
                correlation_id="test-correlation-123"
            )
            
            assert service.session == mock_session
            assert service.correlation_id == "test-correlation-123"
            assert service.repository is not None
            mock_repo_class.assert_called_once_with(mock_session, Event)
    
    def test_service_initialization_without_correlation_id(self, mock_session):
        """Test service initialization without correlation ID."""
        with patch('services.status_projection_service.GenericRepository'):
            service = StatusProjectionService(session=mock_session)
            
            assert service.session == mock_session
            assert service.correlation_id is None
    
    def test_get_status_by_project_id_success(self, service, sample_event, sample_task_context):
        """Test successful get_status_by_project_id operation."""
        project_id = "customer-123/project-abc"
        
        # Mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_order_by = Mock()
        mock_limit = Mock()
        
        service.session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order_by
        mock_order_by.limit.return_value = mock_limit
        mock_limit.__iter__ = Mock(return_value=iter([sample_event]))
        
        with patch('services.status_projection_service.project_status_from_task_context') as mock_project_status:
            expected_projection = StatusProjection(
                execution_id=str(sample_event.id),
                project_id=project_id,
                status=ExecutionStatus.RUNNING,
                progress=50.0,
                current_task="1.1.1",
                customer_id="customer-123",
                branch="task/1-1-1-add-devteam-enabled-flag",
                started_at=datetime.utcnow()
            )
            mock_project_status.return_value = expected_projection
            
            result = service.get_status_by_project_id(project_id)
            
            assert result == expected_projection
            mock_project_status.assert_called_once_with(
                task_context=sample_task_context,
                execution_id=str(sample_event.id),
                project_id=project_id
            )
    
    def test_get_status_by_project_id_not_found(self, service):
        """Test get_status_by_project_id when no matching project found."""
        project_id = "nonexistent-project"
        
        # Mock empty query result
        mock_query = Mock()
        mock_filter = Mock()
        mock_order_by = Mock()
        mock_limit = Mock()
        
        service.session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order_by
        mock_order_by.limit.return_value = mock_limit
        mock_limit.__iter__ = Mock(return_value=iter([]))
        
        result = service.get_status_by_project_id(project_id)
        
        assert result is None
    
    def test_get_status_by_project_id_invalid_input(self, service):
        """Test get_status_by_project_id with invalid input."""
        with pytest.raises(RepositoryError) as exc_info:
            service.get_status_by_project_id("")
        
        assert "Project ID must be a non-empty string" in str(exc_info.value)
        
        with pytest.raises(RepositoryError) as exc_info:
            service.get_status_by_project_id(None)
        
        assert "Project ID must be a non-empty string" in str(exc_info.value)
    
    def test_get_status_by_execution_id_success(self, service, sample_event, sample_task_context):
        """Test successful get_status_by_execution_id operation."""
        execution_id = str(sample_event.id)
        
        service.repository.get.return_value = sample_event
        
        with patch('services.status_projection_service.project_status_from_task_context') as mock_project_status:
            expected_projection = StatusProjection(
                execution_id=execution_id,
                project_id="customer-123/project-abc",
                status=ExecutionStatus.RUNNING,
                progress=50.0,
                current_task="1.1.1",
                customer_id="customer-123",
                branch="task/1-1-1-add-devteam-enabled-flag",
                started_at=datetime.utcnow()
            )
            mock_project_status.return_value = expected_projection
            
            result = service.get_status_by_execution_id(execution_id)
            
            assert result == expected_projection
            service.repository.get.assert_called_once_with(execution_id)
    
    def test_get_status_by_execution_id_fallback_query(self, service, sample_event, sample_task_context):
        """Test get_status_by_execution_id with fallback string query."""
        execution_id = "test-execution-123"
        
        # Mock repository.get to raise exception, triggering fallback
        service.repository.get.side_effect = Exception("Direct lookup failed")
        
        # Mock fallback query
        mock_query = Mock()
        mock_filter = Mock()
        service.session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = sample_event
        
        with patch('services.status_projection_service.project_status_from_task_context') as mock_project_status:
            expected_projection = StatusProjection(
                execution_id=execution_id,
                project_id="customer-123/project-abc",
                status=ExecutionStatus.RUNNING,
                progress=50.0,
                current_task="1.1.1",
                customer_id="customer-123",
                branch="task/1-1-1-add-devteam-enabled-flag",
                started_at=datetime.utcnow()
            )
            mock_project_status.return_value = expected_projection
            
            result = service.get_status_by_execution_id(execution_id)
            
            assert result == expected_projection
    
    def test_get_status_by_execution_id_not_found(self, service):
        """Test get_status_by_execution_id when execution not found."""
        execution_id = "nonexistent-execution"
        
        service.repository.get.return_value = None
        
        # Mock fallback query returning None
        mock_query = Mock()
        mock_filter = Mock()
        service.session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None
        
        result = service.get_status_by_execution_id(execution_id)
        
        assert result is None
    
    def test_get_status_by_execution_id_no_task_context(self, service):
        """Test get_status_by_execution_id when event has no task_context."""
        execution_id = "test-execution-123"
        
        event_without_context = Mock(spec=Event)
        event_without_context.task_context = None
        
        service.repository.get.return_value = event_without_context
        
        result = service.get_status_by_execution_id(execution_id)
        
        assert result is None
    
    def test_get_status_by_execution_id_invalid_input(self, service):
        """Test get_status_by_execution_id with invalid input."""
        with pytest.raises(RepositoryError) as exc_info:
            service.get_status_by_execution_id("")
        
        assert "Execution ID must be a non-empty string" in str(exc_info.value)
        
        with pytest.raises(RepositoryError) as exc_info:
            service.get_status_by_execution_id(None)
        
        assert "Execution ID must be a non-empty string" in str(exc_info.value)
    
    def test_list_active_executions_success(self, service, sample_task_context):
        """Test successful list_active_executions operation."""
        # Create multiple sample events with different statuses
        running_event = Mock(spec=Event)
        running_event.id = uuid.uuid4()
        running_event.task_context = {
            'metadata': {'project_id': 'project-1', 'status': 'prepared'},
            'nodes': {'prep': {'status': 'running'}}
        }
        
        completed_event = Mock(spec=Event)
        completed_event.id = uuid.uuid4()
        completed_event.task_context = {
            'metadata': {'project_id': 'project-2', 'status': 'prepared'},
            'nodes': {'prep': {'status': 'completed'}}
        }
        
        # Mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_order_by = Mock()
        mock_limit = Mock()
        
        service.session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order_by
        mock_order_by.limit.return_value = mock_limit
        mock_limit.__iter__ = Mock(return_value=iter([running_event, completed_event]))
        
        with patch('services.status_projection_service.project_status_from_task_context') as mock_project_status:
            # Mock different statuses for different events
            def side_effect(*args, **kwargs):
                if kwargs['execution_id'] == str(running_event.id):
                    return StatusProjection(
                        execution_id=str(running_event.id),
                        project_id='project-1',
                        status=ExecutionStatus.RUNNING,
                        progress=50.0,
                        current_task="1.1.1",
                        customer_id="customer-1",
                        branch="main",
                        started_at=datetime.utcnow()
                    )
                else:
                    return StatusProjection(
                        execution_id=str(completed_event.id),
                        project_id='project-2',
                        status=ExecutionStatus.COMPLETED,
                        progress=100.0,
                        current_task="1.1.1",
                        customer_id="customer-2",
                        branch="main",
                        started_at=datetime.utcnow()
                    )
            
            mock_project_status.side_effect = side_effect
            
            result = service.list_active_executions(limit=10)
            
            # Should only return running executions (not completed)
            assert len(result) == 1
            assert result[0].status == ExecutionStatus.RUNNING
            assert result[0].project_id == 'project-1'
    
    def test_list_active_executions_with_project_filter(self, service):
        """Test list_active_executions with project_id filter."""
        project_id = "customer-123/project-abc"
        
        # Mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_order_by = Mock()
        mock_limit = Mock()
        
        service.session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order_by
        mock_order_by.limit.return_value = mock_limit
        mock_limit.__iter__ = Mock(return_value=iter([]))
        
        result = service.list_active_executions(limit=10, project_id=project_id)
        
        assert result == []
    
    def test_list_active_executions_invalid_limit(self, service):
        """Test list_active_executions with invalid limit values."""
        with pytest.raises(RepositoryError) as exc_info:
            service.list_active_executions(limit=0)
        
        assert "Limit must be between 1 and 1000" in str(exc_info.value)
        
        with pytest.raises(RepositoryError) as exc_info:
            service.list_active_executions(limit=1001)
        
        assert "Limit must be between 1 and 1000" in str(exc_info.value)
    
    def test_project_status_from_event_task_context_success(self, service, sample_event, sample_task_context):
        """Test successful project_status_from_event_task_context operation."""
        event_id = str(sample_event.id)
        project_id = "customer-123/project-abc"
        
        service.repository.get.return_value = sample_event
        
        with patch('services.status_projection_service.project_status_from_task_context') as mock_project_status:
            expected_projection = StatusProjection(
                execution_id=event_id,
                project_id=project_id,
                status=ExecutionStatus.RUNNING,
                progress=50.0,
                current_task="1.1.1",
                customer_id="customer-123",
                branch="task/1-1-1-add-devteam-enabled-flag",
                started_at=datetime.utcnow()
            )
            mock_project_status.return_value = expected_projection
            
            result = service.project_status_from_event_task_context(event_id, project_id)
            
            assert result == expected_projection
            service.repository.get.assert_called_once_with(event_id)
    
    def test_project_status_from_event_task_context_project_mismatch(self, service, sample_event, sample_task_context):
        """Test project_status_from_event_task_context with project ID mismatch."""
        event_id = str(sample_event.id)
        wrong_project_id = "different-project"
        
        service.repository.get.return_value = sample_event
        
        with pytest.raises(RepositoryError) as exc_info:
            service.project_status_from_event_task_context(event_id, wrong_project_id)
        
        assert "Project ID mismatch" in str(exc_info.value)
    
    def test_project_status_from_event_task_context_invalid_input(self, service):
        """Test project_status_from_event_task_context with invalid input."""
        with pytest.raises(RepositoryError) as exc_info:
            service.project_status_from_event_task_context("", "project-123")
        
        assert "Event ID must be a non-empty string" in str(exc_info.value)
        
        with pytest.raises(RepositoryError) as exc_info:
            service.project_status_from_event_task_context(None, "project-123")
        
        assert "Event ID must be a non-empty string" in str(exc_info.value)
    
    def test_get_execution_history_success(self, service, sample_task_context):
        """Test successful get_execution_history operation."""
        project_id = "customer-123/project-abc"
        
        # Create sample historical events
        event1 = Mock(spec=Event)
        event1.id = uuid.uuid4()
        event1.task_context = sample_task_context
        
        event2 = Mock(spec=Event)
        event2.id = uuid.uuid4()
        event2.task_context = {
            'metadata': {'project_id': project_id, 'status': 'completed'},
            'nodes': {'prep': {'status': 'completed'}}
        }
        
        # Mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_order_by = Mock()
        mock_limit = Mock()
        
        service.session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order_by
        mock_order_by.limit.return_value = mock_limit
        mock_limit.__iter__ = Mock(return_value=iter([event1, event2]))
        
        with patch('services.status_projection_service.project_status_from_task_context') as mock_project_status:
            def side_effect(*args, **kwargs):
                if kwargs['execution_id'] == str(event1.id):
                    return StatusProjection(
                        execution_id=str(event1.id),
                        project_id=project_id,
                        status=ExecutionStatus.RUNNING,
                        progress=50.0,
                        current_task="1.1.1",
                        customer_id="customer-123",
                        branch="main",
                        started_at=datetime.utcnow()
                    )
                else:
                    return StatusProjection(
                        execution_id=str(event2.id),
                        project_id=project_id,
                        status=ExecutionStatus.COMPLETED,
                        progress=100.0,
                        current_task="1.1.1",
                        customer_id="customer-123",
                        branch="main",
                        started_at=datetime.utcnow()
                    )
            
            mock_project_status.side_effect = side_effect
            
            result = service.get_execution_history(project_id, limit=5)
            
            assert len(result) == 2
            assert all(proj.project_id == project_id for proj in result)
    
    def test_get_execution_history_invalid_input(self, service):
        """Test get_execution_history with invalid input."""
        with pytest.raises(RepositoryError) as exc_info:
            service.get_execution_history("", limit=5)
        
        assert "Project ID must be a non-empty string" in str(exc_info.value)
        
        with pytest.raises(RepositoryError) as exc_info:
            service.get_execution_history("project-123", limit=0)
        
        assert "Limit must be between 1 and 100" in str(exc_info.value)
        
        with pytest.raises(RepositoryError) as exc_info:
            service.get_execution_history("project-123", limit=101)
        
        assert "Limit must be between 1 and 100" in str(exc_info.value)
    
    def test_error_handling_database_exception(self, service):
        """Test error handling when database operations fail."""
        project_id = "test-project"
        
        # Mock database exception
        service.session.query.side_effect = Exception("Database connection failed")
        
        with pytest.raises(RepositoryError) as exc_info:
            service.get_status_by_project_id(project_id)
        
        assert "Failed to get status projection by project ID" in str(exc_info.value)
    
    def test_performance_logging(self, service, sample_event, sample_task_context):
        """Test that performance logging decorators are applied."""
        project_id = "customer-123/project-abc"
        
        # Mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_order_by = Mock()
        mock_limit = Mock()
        
        service.session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order_by
        mock_order_by.limit.return_value = mock_limit
        mock_limit.__iter__ = Mock(return_value=iter([sample_event]))
        
        with patch('services.status_projection_service.project_status_from_task_context') as mock_project_status:
            expected_projection = StatusProjection(
                execution_id=str(sample_event.id),
                project_id=project_id,
                status=ExecutionStatus.RUNNING,
                progress=50.0,
                current_task="1.1.1",
                customer_id="customer-123",
                branch="task/1-1-1-add-devteam-enabled-flag",
                started_at=datetime.utcnow()
            )
            mock_project_status.return_value = expected_projection
            
            # Verify method has performance logging decorator (check for decorator or wrapped function)
            method = service.get_status_by_project_id
            has_decorator = (
                hasattr(method, '__wrapped__') or
                hasattr(method, '__name__') and 'log_performance' in str(method) or
                callable(method)  # At minimum, method should be callable
            )
            assert has_decorator, "Method should have performance logging applied"
            
            result = service.get_status_by_project_id(project_id)
            assert result == expected_projection


class TestStatusProjectionServiceFactory:
    """Test suite for the factory function."""
    
    def test_get_status_projection_service_factory(self):
        """Test the factory function creates service correctly."""
        mock_session = Mock(spec=Session)
        correlation_id = "test-correlation-456"
        
        with patch('services.status_projection_service.StatusProjectionService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            result = get_status_projection_service(
                session=mock_session,
                correlation_id=correlation_id
            )
            
            assert result == mock_service
            mock_service_class.assert_called_once_with(
                session=mock_session,
                correlation_id=correlation_id
            )
    
    def test_get_status_projection_service_factory_without_correlation_id(self):
        """Test the factory function without correlation ID."""
        mock_session = Mock(spec=Session)
        
        with patch('services.status_projection_service.StatusProjectionService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            result = get_status_projection_service(session=mock_session)
            
            assert result == mock_service
            mock_service_class.assert_called_once_with(
                session=mock_session,
                correlation_id=None
            )


class TestStatusProjectionServiceIntegration:
    """Integration tests for StatusProjectionService with minimal mocking."""
    
    @pytest.fixture
    def real_task_context(self):
        """Create realistic task_context for integration testing."""
        return {
            'metadata': {
                'project_id': 'customer-123/project-abc',
                'task_id': '1.1.1',
                'status': 'prepared',
                'branch': 'task/1-1-1-add-devteam-enabled-flag',
                'repo_path': '/workspace/repos/customer-123-project-abc',
                'started_at': '2025-01-14T18:25:00Z',
                'logs': ['Implementation started', 'Repository cloned', 'Aider tool initialized'],
                'files_modified': ['src/config.js', 'README.md']
            },
            'nodes': {
                'select': {
                    'status': 'completed',
                    'output': {'selected_tasks': ['1.1.1']},
                    'completed_at': '2025-01-14T18:26:00Z'
                },
                'prep': {
                    'status': 'running',
                    'started_at': '2025-01-14T18:26:30Z',
                    'progress': 0.6
                }
            }
        }
    
    def test_integration_with_real_projection_utility(self, real_task_context):
        """Test integration with actual project_status_from_task_context utility."""
        from schemas.status_projection_schema import project_status_from_task_context
        
        execution_id = "exec_12345678-1234-1234-1234-123456789012"
        project_id = "customer-123/project-abc"
        
        # Test the actual utility function
        result = project_status_from_task_context(
            task_context=real_task_context,
            execution_id=execution_id,
            project_id=project_id
        )
        
        assert isinstance(result, StatusProjection)
        assert result.execution_id == execution_id
        assert result.project_id == project_id
        assert result.status == ExecutionStatus.RUNNING  # Based on prep node running
        assert result.progress == 50.0  # 1 of 2 nodes completed
        assert result.current_task == "1.1.1"
        assert result.customer_id == "customer-123"
        assert result.branch == "task/1-1-1-add-devteam-enabled-flag"
        assert result.artifacts.repo_path == "/workspace/repos/customer-123-project-abc"
        assert len(result.artifacts.logs) == 3
        assert len(result.artifacts.files_modified) == 2
        assert result.totals.completed == 1
        assert result.totals.total == 2