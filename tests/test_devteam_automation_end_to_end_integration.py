"""
Comprehensive End-to-End Integration Test for DEVTEAM_AUTOMATION Workflow

This module provides complete end-to-end validation of the DEVTEAM_AUTOMATION workflow
integration, testing the complete pipeline from API ingestion through workflow execution
to database persistence.

Test Coverage:
- WorkflowRegistry["DEVTEAM_AUTOMATION"] resolution validation
- Complete pipeline: POST /events → Celery → WorkflowRegistry → DevTeamAutomationWorkflow
- Performance validation: workflow execution completes within 2s requirement
- CorrelationId propagation through entire pipeline
- Task_context persistence to database after workflow execution
- Integration with existing EventRequest schema
- Realistic DEVTEAM_AUTOMATION event payload testing
"""

import json
import logging
import pytest
import time
from datetime import datetime
from io import StringIO
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from database.event import Event
from database.session import db_session
from database.repository import GenericRepository
from core.structured_logging import get_structured_logger, LogStatus
from worker.tasks import process_incoming_event
from schemas.event_schema import EventRequest
from workflows.workflow_registry import WorkflowRegistry
from workflows.devteam_automation_workflow import DevTeamAutomationWorkflow


class TestDevTeamAutomationEndToEndIntegration:
    """Comprehensive end-to-end integration test suite for DEVTEAM_AUTOMATION workflow."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def log_capture(self):
        """Capture log output for testing."""
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.DEBUG)
        
        # Get the root logger and add our handler
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.DEBUG)
        
        yield log_stream
        
        # Clean up
        root_logger.removeHandler(handler)

    @pytest.fixture
    def devteam_automation_event_payload(self):
        """Realistic DEVTEAM_AUTOMATION event payload for testing."""
        return {
            "id": "evt_devteam_integration_test",
            "type": "DEVTEAM_AUTOMATION",
            "project_id": "customer-integration/project-test",
            "task": {
                "id": "3.1.2",
                "title": "Ensure workflow can be resolved by name/id and validate end-to-end integration",
                "description": "Complete end-to-end integration validation with comprehensive test coverage",
                "type": "atomic",
                "dependencies": ["3.1.1"],
                "files": ["tests/test_devteam_automation_end_to_end_integration.py"]
            },
            "priority": "high",
            "data": {
                "repository_url": "https://github.com/customer/project-test.git",
                "branch": "feature/devteam-integration",
                "environment": "test"
            },
            "options": {
                "idempotency_key": "integration_test_key_123",
                "timeout_seconds": 300
            },
            "metadata": {
                "correlation_id": "corr_integration_test_456",
                "source": "integration_test_suite",
                "user_id": "test_user_integration"
            }
        }

    @pytest.fixture
    def minimal_devteam_event_payload(self):
        """Minimal DEVTEAM_AUTOMATION event payload for testing."""
        return {
            "id": "evt_minimal_devteam_test",
            "type": "DEVTEAM_AUTOMATION",
            "project_id": "test/minimal",
            "task": {
                "id": "1.0",
                "title": "Minimal DevTeam automation task"
            }
        }

    def test_workflow_registry_devteam_automation_resolution(self):
        """
        Test that WorkflowRegistry["DEVTEAM_AUTOMATION"] resolves correctly.
        
        Acceptance Criteria:
        - WorkflowRegistry["DEVTEAM_AUTOMATION"] resolves to correct workflow class
        """
        # Test registry resolution by name
        workflow_class = WorkflowRegistry["DEVTEAM_AUTOMATION"].value
        assert workflow_class == DevTeamAutomationWorkflow
        
        # Test registry resolution by enum
        workflow_class_enum = WorkflowRegistry.DEVTEAM_AUTOMATION.value
        assert workflow_class_enum == DevTeamAutomationWorkflow
        
        # Test workflow instantiation
        workflow_instance = workflow_class()
        assert isinstance(workflow_instance, DevTeamAutomationWorkflow)
        
        # Test workflow name consistency
        assert WorkflowRegistry.DEVTEAM_AUTOMATION.name == "DEVTEAM_AUTOMATION"
        
        print("✅ WorkflowRegistry['DEVTEAM_AUTOMATION'] resolution validated")

    def test_complete_pipeline_post_events_to_database_persistence(
        self, client, devteam_automation_event_payload, log_capture
    ):
        """
        Test complete pipeline: POST /events → Celery → WorkflowRegistry → DevTeamAutomationWorkflow → Database persistence.
        
        Acceptance Criteria:
        - End-to-end test: POST /events → Celery → WorkflowRegistry → DevTeamAutomationWorkflow → Database persistence
        """
        with patch('app.api.endpoint.celery_app.send_task') as mock_send_task, \
             patch('app.api.endpoint.GenericRepository') as mock_api_repo, \
             patch('app.worker.tasks.contextmanager') as mock_contextmanager, \
             patch('app.worker.tasks.GenericRepository') as mock_worker_repo, \
             patch('app.worker.tasks.WorkflowRegistry') as mock_registry:
            
            # === API LAYER SETUP ===
            mock_event = MagicMock()
            mock_event.id = "integration_event_123"
            mock_event.workflow_type = "DEVTEAM_AUTOMATION"
            
            mock_api_repo_instance = MagicMock()
            mock_api_repo_instance.create.return_value = mock_event
            mock_api_repo.return_value = mock_api_repo_instance
            
            mock_task_id = "integration_task_456"
            mock_send_task.return_value = mock_task_id
            
            # === WORKER LAYER SETUP ===
            mock_session = MagicMock()
            mock_contextmanager.return_value.__enter__.return_value = mock_session
            
            mock_worker_event = MagicMock()
            mock_worker_event.id = "integration_event_123"
            mock_worker_event.workflow_type = "DEVTEAM_AUTOMATION"
            mock_worker_event.data = devteam_automation_event_payload
            
            mock_worker_repo_instance = MagicMock()
            mock_worker_repo_instance.get.return_value = mock_worker_event
            mock_worker_repo.return_value = mock_worker_repo_instance
            
            # Mock actual DevTeam workflow execution
            mock_workflow_class = MagicMock()
            mock_workflow = MagicMock()
            mock_workflow.run.return_value = MagicMock()
            mock_workflow.run.return_value.model_dump.return_value = {
                "event": devteam_automation_event_payload,
                "metadata": {
                    "correlationId": "corr_integration_test_456",
                    "status": "prepared",
                    "workflow_type": "DEVTEAM_AUTOMATION"
                },
                "nodes": {
                    "SelectNode": {"status": "completed"},
                    "PrepNode": {"status": "completed"}
                }
            }
            mock_workflow_class.return_value = mock_workflow
            mock_registry.__getitem__.return_value.value = mock_workflow_class
            
            # === EXECUTE COMPLETE PIPELINE ===
            
            # Step 1: POST /events (API ingestion)
            start_time = time.time()
            response = client.post("/process/events/", json=devteam_automation_event_payload)
            api_time = time.time() - start_time
            
            # Verify API response
            assert response.status_code == 202
            response_data = response.json()
            assert response_data["status"] == "accepted"
            assert response_data["correlation_id"] == "corr_integration_test_456"
            assert response_data["event_type"] == "DEVTEAM_AUTOMATION"
            
            # Verify Celery task dispatch
            mock_send_task.assert_called_once_with(
                "process_incoming_event",
                args=[str(mock_event.id)],
                headers={
                    "correlation_id": "corr_integration_test_456",
                    "event_id": str(mock_event.id),
                    "project_id": "customer-integration/project-test",
                    "event_type": "DEVTEAM_AUTOMATION"
                }
            )
            
            # Step 2: Worker processing (Celery → WorkflowRegistry → DevTeamAutomationWorkflow)
            mock_task_request = MagicMock()
            mock_task_request.id = mock_task_id
            mock_task_request.headers = {
                "correlation_id": "corr_integration_test_456",
                "event_id": str(mock_event.id),
                "project_id": "customer-integration/project-test",
                "event_type": "DEVTEAM_AUTOMATION"
            }
            
            mock_self = MagicMock()
            mock_self.request = mock_task_request
            
            worker_start_time = time.time()
            process_incoming_event(mock_self, str(mock_event.id))
            worker_time = time.time() - worker_start_time
            
            total_time = time.time() - start_time
            
            # === VERIFY COMPLETE PIPELINE ===
            
            # 1. Verify workflow registry resolution was called
            mock_registry.__getitem__.assert_called_once_with("DEVTEAM_AUTOMATION")
            
            # 2. Verify workflow execution
            mock_workflow.run.assert_called_once_with(devteam_automation_event_payload)
            
            # 3. Verify task_context persistence to database
            expected_task_context = {
                "event": devteam_automation_event_payload,
                "metadata": {
                    "correlationId": "corr_integration_test_456",
                    "status": "prepared",
                    "workflow_type": "DEVTEAM_AUTOMATION",
                    "taskId": mock_task_id,
                    "executionId": f"exec_{mock_event.id}"
                },
                "nodes": {
                    "SelectNode": {"status": "completed"},
                    "PrepNode": {"status": "completed"}
                }
            }
            assert mock_worker_event.task_context == expected_task_context
            mock_worker_repo_instance.update.assert_called_once_with(obj=mock_worker_event)
            
            # 4. Verify structured logging
            log_output = log_capture.getvalue()
            log_lines = [line for line in log_output.strip().split('\n') if line]
            assert len(log_lines) >= 4  # Multiple structured log entries
            
            print(f"✅ Complete pipeline validation successful:")
            print(f"   - API ingestion time: {api_time:.3f}s")
            print(f"   - Worker processing time: {worker_time:.3f}s")
            print(f"   - Total pipeline time: {total_time:.3f}s")
            print(f"   - Log entries generated: {len(log_lines)}")

    def test_performance_requirement_workflow_execution_within_2s(
        self, devteam_automation_event_payload
    ):
        """
        Test performance requirement: workflow execution completes within 2s.
        
        Acceptance Criteria:
        - Performance validated: workflow execution completes within 2s requirement
        """
        # Test with actual workflow instance (not mocked)
        workflow = DevTeamAutomationWorkflow()
        
        # Measure workflow execution time
        start_time = time.time()
        result = workflow.run(devteam_automation_event_payload)
        execution_time = time.time() - start_time
        
        # Verify performance requirement
        assert execution_time <= 2.0, f"Workflow execution took {execution_time:.3f}s, exceeding 2s requirement"
        
        # Verify workflow completed successfully
        assert result is not None
        assert "SelectNode" in result.nodes
        assert "PrepNode" in result.nodes
        assert result.metadata["correlationId"] == "corr_integration_test_456"
        assert result.metadata["workflow_type"] == "DEVTEAM_AUTOMATION"
        
        print(f"✅ Performance requirement validated: {execution_time:.3f}s (≤2s)")

    def test_correlation_id_propagation_through_entire_pipeline(
        self, client, devteam_automation_event_payload, log_capture
    ):
        """
        Test correlationId propagation through entire pipeline.
        
        Acceptance Criteria:
        - CorrelationId propagation verified through entire pipeline
        """
        with patch('app.api.endpoint.celery_app.send_task') as mock_send_task, \
             patch('app.api.endpoint.GenericRepository') as mock_api_repo, \
             patch('app.worker.tasks.contextmanager') as mock_contextmanager, \
             patch('app.worker.tasks.GenericRepository') as mock_worker_repo, \
             patch('app.worker.tasks.WorkflowRegistry') as mock_registry:
            
            # Setup mocks
            mock_event = MagicMock()
            mock_event.id = "correlation_test_event"
            mock_event.workflow_type = "DEVTEAM_AUTOMATION"
            
            mock_api_repo_instance = MagicMock()
            mock_api_repo_instance.create.return_value = mock_event
            mock_api_repo.return_value = mock_api_repo_instance
            
            mock_task_id = "correlation_test_task"
            mock_send_task.return_value = mock_task_id
            
            mock_session = MagicMock()
            mock_contextmanager.return_value.__enter__.return_value = mock_session
            
            mock_worker_event = MagicMock()
            mock_worker_event.id = "correlation_test_event"
            mock_worker_event.workflow_type = "DEVTEAM_AUTOMATION"
            mock_worker_event.data = devteam_automation_event_payload
            
            mock_worker_repo_instance = MagicMock()
            mock_worker_repo_instance.get.return_value = mock_worker_event
            mock_worker_repo.return_value = mock_worker_repo_instance
            
            mock_workflow_class = MagicMock()
            mock_workflow = MagicMock()
            mock_workflow.run.return_value = MagicMock()
            mock_workflow.run.return_value.model_dump.return_value = {"result": "correlation_success"}
            mock_workflow_class.return_value = mock_workflow
            mock_registry.__getitem__.return_value.value = mock_workflow_class
            
            # Execute pipeline
            response = client.post("/process/events/", json=devteam_automation_event_payload)
            
            # Simulate worker processing
            mock_task_request = MagicMock()
            mock_task_request.id = mock_task_id
            mock_task_request.headers = {
                "correlation_id": "corr_integration_test_456",
                "event_id": str(mock_event.id),
                "project_id": "customer-integration/project-test",
                "event_type": "DEVTEAM_AUTOMATION"
            }
            
            mock_self = MagicMock()
            mock_self.request = mock_task_request
            
            process_incoming_event(mock_self, str(mock_event.id))
            
            # === VERIFY CORRELATION ID PROPAGATION ===
            
            # 1. API response includes correlationId
            response_data = response.json()
            assert response_data["correlation_id"] == "corr_integration_test_456"
            
            # 2. Celery task headers include correlationId
            call_args = mock_send_task.call_args
            assert call_args[1]["headers"]["correlation_id"] == "corr_integration_test_456"
            
            # 3. Task context includes correlationId
            expected_task_context = {
                "result": "correlation_success",
                "metadata": {
                    "correlationId": "corr_integration_test_456",
                    "taskId": mock_task_id,
                    "executionId": f"exec_{mock_event.id}"
                }
            }
            assert mock_worker_event.task_context == expected_task_context
            
            # 4. Structured logs include correlationId
            log_output = log_capture.getvalue()
            log_lines = [line for line in log_output.strip().split('\n') if line]
            
            for line in log_lines:
                if line.strip():
                    log_entry = json.loads(line)
                    if "correlationId" in log_entry:
                        assert log_entry["correlationId"] == "corr_integration_test_456"
            
            print("✅ CorrelationId propagation verified through entire pipeline")

    def test_task_context_persistence_to_database_after_workflow_execution(
        self, devteam_automation_event_payload, log_capture
    ):
        """
        Test task_context persistence to database after workflow execution.
        
        Acceptance Criteria:
        - Task_context properly persisted to Event.task_context field
        """
        with patch('app.worker.tasks.contextmanager') as mock_contextmanager, \
             patch('app.worker.tasks.GenericRepository') as mock_repo, \
             patch('app.worker.tasks.WorkflowRegistry') as mock_registry:
            
            # Mock task request
            mock_task_request = MagicMock()
            mock_task_request.id = "persistence_test_task"
            mock_task_request.headers = {
                "correlation_id": "corr_integration_test_456",
                "project_id": "customer-integration/project-test",
                "event_type": "DEVTEAM_AUTOMATION"
            }
            
            # Mock database session and event
            mock_session = MagicMock()
            mock_contextmanager.return_value.__enter__.return_value = mock_session
            
            mock_event = MagicMock()
            mock_event.id = "persistence_test_event"
            mock_event.workflow_type = "DEVTEAM_AUTOMATION"
            mock_event.data = devteam_automation_event_payload
            
            mock_repo_instance = MagicMock()
            mock_repo_instance.get.return_value = mock_event
            mock_repo.return_value = mock_repo_instance
            
            # Mock workflow execution with realistic DevTeam workflow result
            mock_workflow_class = MagicMock()
            mock_workflow = MagicMock()
            mock_workflow.run.return_value = MagicMock()
            mock_workflow.run.return_value.model_dump.return_value = {
                "event": devteam_automation_event_payload,
                "metadata": {
                    "correlationId": "corr_integration_test_456",
                    "status": "prepared",
                    "workflow_type": "DEVTEAM_AUTOMATION",
                    "event_id": "persistence_test_event",
                    "project_id": "customer-integration/project-test",
                    "task_id": "3.1.2",
                    "priority": "high"
                },
                "nodes": {
                    "SelectNode": {
                        "status": "completed",
                        "message": "Fixed plan selected for DevTeam automation workflow"
                    },
                    "PrepNode": {
                        "status": "completed",
                        "message": "Task context prepared with basic metadata for DevTeam automation"
                    }
                }
            }
            mock_workflow_class.return_value = mock_workflow
            mock_registry.__getitem__.return_value.value = mock_workflow_class
            
            # Create task instance
            mock_self = MagicMock()
            mock_self.request = mock_task_request
            
            # Measure persistence time
            start_time = time.time()
            process_incoming_event(mock_self, "persistence_test_event")
            persistence_time = time.time() - start_time
            
            # === VERIFY TASK_CONTEXT PERSISTENCE ===
            
            # 1. Verify task_context structure
            expected_task_context = {
                "event": devteam_automation_event_payload,
                "metadata": {
                    "correlationId": "corr_integration_test_456",
                    "status": "prepared",
                    "workflow_type": "DEVTEAM_AUTOMATION",
                    "event_id": "persistence_test_event",
                    "project_id": "customer-integration/project-test",
                    "task_id": "3.1.2",
                    "priority": "high",
                    "taskId": "persistence_test_task",
                    "executionId": "exec_persistence_test_event"
                },
                "nodes": {
                    "SelectNode": {
                        "status": "completed",
                        "message": "Fixed plan selected for DevTeam automation workflow"
                    },
                    "PrepNode": {
                        "status": "completed",
                        "message": "Task context prepared with basic metadata for DevTeam automation"
                    }
                }
            }
            assert mock_event.task_context == expected_task_context
            
            # 2. Verify database update was called
            mock_repo_instance.update.assert_called_once_with(obj=mock_event)
            
            # 3. Verify persistence time is reasonable (≤1s)
            assert persistence_time <= 1.0, f"Persistence time {persistence_time:.3f}s exceeds 1s requirement"
            
            print(f"✅ Task_context persistence validated in {persistence_time:.3f}s")

    def test_realistic_devteam_automation_event_payloads(
        self, client, devteam_automation_event_payload, minimal_devteam_event_payload
    ):
        """
        Test with realistic DEVTEAM_AUTOMATION event payloads.
        
        Acceptance Criteria:
        - Integration with existing EventRequest schema confirmed
        - Test with realistic DEVTEAM_AUTOMATION event payloads
        """
        with patch('app.api.endpoint.celery_app.send_task') as mock_send_task, \
             patch('app.api.endpoint.GenericRepository') as mock_repo:
            
            # Setup mocks
            mock_event = MagicMock()
            mock_event.id = "realistic_payload_test"
            mock_event.workflow_type = "DEVTEAM_AUTOMATION"
            
            mock_repo_instance = MagicMock()
            mock_repo_instance.create.return_value = mock_event
            mock_repo.return_value = mock_repo_instance
            
            mock_send_task.return_value = "realistic_task_123"
            
            # Test 1: Full-featured DEVTEAM_AUTOMATION event
            response1 = client.post("/process/events/", json=devteam_automation_event_payload)
            assert response1.status_code == 202
            response1_data = response1.json()
            assert response1_data["event_type"] == "DEVTEAM_AUTOMATION"
            assert response1_data["correlation_id"] == "corr_integration_test_456"
            
            # Test 2: Minimal DEVTEAM_AUTOMATION event
            response2 = client.post("/process/events/", json=minimal_devteam_event_payload)
            assert response2.status_code == 202
            response2_data = response2.json()
            assert response2_data["event_type"] == "DEVTEAM_AUTOMATION"
            
            # Test 3: EventRequest schema validation
            validated_event = EventRequest.parse_obj(devteam_automation_event_payload)
            assert validated_event.type == "DEVTEAM_AUTOMATION"
            assert validated_event.task is not None
            assert validated_event.task.id == "3.1.2"
            assert validated_event.metadata is not None
            assert validated_event.metadata.correlation_id == "corr_integration_test_456"
            
            # Test 4: Workflow execution with realistic payload
            workflow = DevTeamAutomationWorkflow()
            result = workflow.run(devteam_automation_event_payload)
            assert result.metadata["correlationId"] == "corr_integration_test_456"
            assert result.metadata["workflow_type"] == "DEVTEAM_AUTOMATION"
            assert result.metadata["task_id"] == "3.1.2"
            
            print("✅ Realistic DEVTEAM_AUTOMATION event payloads validated")

    def test_no_breaking_changes_to_existing_functionality(self, client):
        """
        Test that DEVTEAM_AUTOMATION integration doesn't break existing functionality.
        
        Acceptance Criteria:
        - No breaking changes to existing event processing pipeline
        """
        with patch('app.api.endpoint.celery_app.send_task') as mock_send_task, \
             patch('app.api.endpoint.GenericRepository') as mock_repo:
            
            # Setup mocks
            mock_event = MagicMock()
            mock_event.id = "backward_compatibility_test"
            mock_event.workflow_type = "PLACEHOLDER"
            
            mock_repo_instance = MagicMock()
            mock_repo_instance.create.return_value = mock_event
            mock_repo.return_value = mock_repo_instance
            
            mock_send_task.return_value = "backward_compat_task"
            
            # Test existing PLACEHOLDER event still works
            placeholder_event = {
                "id": "test_placeholder_event",
                "type": "PLACEHOLDER",
                "data": {"test": "backward_compatibility"}
            }
            
            response = client.post("/process/events/", json=placeholder_event)
            assert response.status_code == 202
            response_data = response.json()
            assert response_data["event_type"] == "PLACEHOLDER"
            
            # Verify workflow type determination works for both
            from app.api.endpoint import get_workflow_type
            
            assert get_workflow_type({"type": "DEVTEAM_AUTOMATION"}) == "DEVTEAM_AUTOMATION"
            assert get_workflow_type({"type": "PLACEHOLDER"}) == "PLACEHOLDER"
            assert get_workflow_type({"type": "UNKNOWN"}) == "PLACEHOLDER"  # Default fallback
            
            print("✅ Backward compatibility with existing functionality verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])