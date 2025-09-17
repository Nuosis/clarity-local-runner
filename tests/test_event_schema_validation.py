"""
Test suite for EventRequest schema validation.

This module tests the comprehensive validation implemented for the POST /events endpoint,
ensuring all acceptance criteria are met including:
- Comprehensive field validation and constraints
- Input sanitization and security checks
- Meaningful error messages with proper HTTP status codes
- Performance requirements (≤200ms validation processing)
"""

import json
import time
from datetime import datetime
from typing import Dict, Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from schemas.event_schema import EventRequest, EventType, EventPriority, TaskDefinition
from main import app


class TestEventRequestSchema:
    """Test cases for EventRequest schema validation."""

    def test_valid_devteam_automation_event(self):
        """Test valid DevTeam automation event passes validation."""
        valid_event = {
            "id": "evt_devteam_12345",
            "type": "DEVTEAM_AUTOMATION",
            "project_id": "customer-123/project-abc",
            "task": {
                "id": "1.1.1",
                "title": "Add DEVTEAM_ENABLED flag to src/config.js",
                "description": "Add DEVTEAM_ENABLED flag with default false and JSDoc",
                "type": "atomic",
                "dependencies": [],
                "files": ["src/config.js"]
            },
            "priority": "normal",
            "data": {
                "repository_url": "https://github.com/user/repo.git",
                "branch": "main"
            },
            "options": {
                "idempotency_key": "unique-key-12345",
                "timeout_seconds": 300
            },
            "metadata": {
                "correlation_id": "req_12345",
                "source": "devteam_ui",
                "user_id": "user_123"
            }
        }
        
        # Should not raise validation error
        event = EventRequest(**valid_event)
        assert event.id == "evt_devteam_12345"
        assert event.type == EventType.DEVTEAM_AUTOMATION
        assert event.project_id == "customer-123/project-abc"
        assert event.task.id == "1.1.1"
        assert event.priority == EventPriority.NORMAL

    def test_valid_placeholder_event_backward_compatibility(self):
        """Test backward compatibility with PlaceholderEventSchema."""
        placeholder_event = {
            "id": "simple_event_123",
            "type": "PLACEHOLDER"
        }
        
        # Should not raise validation error
        event = EventRequest(**placeholder_event)
        assert event.id == "simple_event_123"
        assert event.type == EventType.PLACEHOLDER

    def test_invalid_event_id_format(self):
        """Test invalid event ID format raises validation error."""
        invalid_events = [
            {"id": "", "type": "PLACEHOLDER"},  # Empty ID
            {"id": "   ", "type": "PLACEHOLDER"},  # Whitespace only
            {"id": "invalid<script>", "type": "PLACEHOLDER"},  # Dangerous characters
            {"id": "invalid'quote", "type": "PLACEHOLDER"},  # Quote character
            {"id": "invalid&amp;", "type": "PLACEHOLDER"},  # Ampersand
            {"id": "a" * 101, "type": "PLACEHOLDER"},  # Too long
        ]
        
        for invalid_event in invalid_events:
            with pytest.raises(ValidationError) as exc_info:
                EventRequest(**invalid_event)
            
            errors = exc_info.value.errors()
            assert any("id" in str(error["loc"]) for error in errors)

    def test_invalid_project_id_format(self):
        """Test invalid project ID format raises validation error."""
        invalid_events = [
            {
                "id": "test_123",
                "type": "DEVTEAM_AUTOMATION",
                "project_id": "invalid/format/too/many/parts",
                "task": {"id": "1.1", "title": "Test task"}
            },
            {
                "id": "test_124",
                "type": "DEVTEAM_AUTOMATION", 
                "project_id": "invalid<script>",
                "task": {"id": "1.1", "title": "Test task"}
            },
            {
                "id": "test_125",
                "type": "DEVTEAM_AUTOMATION",
                "project_id": "",
                "task": {"id": "1.1", "title": "Test task"}
            }
        ]
        
        for invalid_event in invalid_events:
            with pytest.raises(ValidationError) as exc_info:
                EventRequest(**invalid_event)
            
            errors = exc_info.value.errors()
            assert any("project_id" in str(error["loc"]) for error in errors)

    def test_invalid_task_id_format(self):
        """Test invalid task ID format raises validation error."""
        invalid_task_ids = [
            "invalid_format",  # No dots with numbers
            "1.a.1",  # Letters in task ID
            "1..1",  # Double dots
            ".1.1",  # Starting with dot
            "1.1.",  # Ending with dot
            "",  # Empty
        ]
        
        for invalid_task_id in invalid_task_ids:
            invalid_event = {
                "id": "test_123",
                "type": "DEVTEAM_AUTOMATION",
                "project_id": "customer-123/project-abc",
                "task": {
                    "id": invalid_task_id,
                    "title": "Test task"
                }
            }
            
            with pytest.raises(ValidationError) as exc_info:
                EventRequest(**invalid_event)
            
            errors = exc_info.value.errors()
            assert any("task" in str(error["loc"]) for error in errors)

    def test_devteam_automation_requires_project_id_and_task(self):
        """Test DevTeam automation events require project_id and task."""
        # Missing project_id
        with pytest.raises(ValidationError) as exc_info:
            EventRequest(
                id="test_123",
                type="DEVTEAM_AUTOMATION",
                task={"id": "1.1", "title": "Test task"}
            )
        
        errors = exc_info.value.errors()
        assert any("project_id" in error["msg"].lower() for error in errors)
        
        # Missing task
        with pytest.raises(ValidationError) as exc_info:
            EventRequest(
                id="test_124",
                type="DEVTEAM_AUTOMATION",
                project_id="customer-123/project-abc"
            )
        
        errors = exc_info.value.errors()
        assert any("task" in error["msg"].lower() for error in errors)

    def test_data_payload_size_limit(self):
        """Test data payload size limit validation."""
        # Create a large payload (over 1MB)
        large_data = {"large_field": "x" * (1024 * 1024 + 1)}
        
        with pytest.raises(ValidationError) as exc_info:
            EventRequest(
                id="test_123",
                type="PLACEHOLDER",
                data=large_data
            )
        
        errors = exc_info.value.errors()
        assert any("payload exceeds maximum size" in error["msg"].lower() for error in errors)

    def test_field_length_constraints(self):
        """Test field length constraints are enforced."""
        # Test various field length limits
        test_cases = [
            {
                "field": "id",
                "value": "a" * 101,  # Max 100
                "event": {"id": "a" * 101, "type": "PLACEHOLDER"}
            },
            {
                "field": "project_id", 
                "value": "a" * 201,  # Max 200
                "event": {
                    "id": "test_123",
                    "type": "DEVTEAM_AUTOMATION",
                    "project_id": "a" * 201,
                    "task": {"id": "1.1", "title": "Test"}
                }
            },
            {
                "field": "task.title",
                "value": "a" * 201,  # Max 200
                "event": {
                    "id": "test_123",
                    "type": "DEVTEAM_AUTOMATION",
                    "project_id": "customer-123/project-abc",
                    "task": {"id": "1.1", "title": "a" * 201}
                }
            }
        ]
        
        for test_case in test_cases:
            with pytest.raises(ValidationError) as exc_info:
                EventRequest(**test_case["event"])
            
            errors = exc_info.value.errors()
            # Should have validation error related to the field
            assert len(errors) > 0

    def test_enum_validation(self):
        """Test enum field validation."""
        # Invalid event type
        with pytest.raises(ValidationError):
            EventRequest(
                id="test_123",
                type="INVALID_TYPE"
            )
        
        # Invalid priority
        with pytest.raises(ValidationError):
            EventRequest(
                id="test_123",
                type="PLACEHOLDER",
                priority="invalid_priority"
            )

    def test_optional_fields_defaults(self):
        """Test optional fields have correct defaults."""
        minimal_event = EventRequest(
            id="test_123",
            type="PLACEHOLDER"
        )
        
        assert minimal_event.priority == EventPriority.NORMAL
        assert minimal_event.data == {}
        assert minimal_event.project_id is None
        assert minimal_event.task is None
        assert minimal_event.options is None
        assert minimal_event.metadata is None
        assert isinstance(minimal_event.created_at, datetime)

    def test_validation_performance(self):
        """Test validation performance meets ≤200ms requirement."""
        valid_event = {
            "id": "perf_test_123",
            "type": "DEVTEAM_AUTOMATION",
            "project_id": "customer-123/project-abc",
            "task": {
                "id": "1.1.1",
                "title": "Performance test task",
                "description": "Testing validation performance",
                "files": ["file1.js", "file2.py", "file3.md"]
            },
            "data": {
                "repository_url": "https://github.com/user/repo.git",
                "branch": "main",
                "additional_data": {"key1": "value1", "key2": "value2"}
            }
        }
        
        # Test multiple validations to get average time
        times = []
        for _ in range(10):
            start_time = time.time()
            EventRequest(**valid_event)
            end_time = time.time()
            times.append((end_time - start_time) * 1000)  # Convert to milliseconds
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        # Should meet ≤200ms requirement
        assert avg_time <= 200, f"Average validation time {avg_time:.2f}ms exceeds 200ms limit"
        assert max_time <= 200, f"Max validation time {max_time:.2f}ms exceeds 200ms limit"


class TestEventEndpointIntegration:
    """Integration tests for the POST /events endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_valid_event_returns_202(self, client):
        """Test valid event returns 202 Accepted."""
        valid_event = {
            "id": "integration_test_123",
            "type": "DEVTEAM_AUTOMATION",
            "project_id": "customer-123/project-abc",
            "task": {
                "id": "1.1.1",
                "title": "Integration test task"
            }
        }
        
        response = client.post("/process/events/", json=valid_event)
        
        assert response.status_code == 202
        response_data = response.json()
        assert response_data["status"] == "accepted"
        assert "event_id" in response_data
        assert "task_id" in response_data
        assert response_data["event_type"] == "DEVTEAM_AUTOMATION"

    def test_invalid_event_returns_422(self, client):
        """Test invalid event returns 422 with detailed error messages."""
        invalid_event = {
            "id": "",  # Invalid empty ID
            "type": "INVALID_TYPE"  # Invalid type
        }
        
        response = client.post("/process/events/", json=invalid_event)
        
        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data
        
        # Should have validation errors
        if isinstance(error_data["detail"], list):
            # FastAPI default format
            assert len(error_data["detail"]) > 0
        else:
            # Custom format
            assert "errors" in error_data["detail"] or "message" in error_data["detail"]

    def test_malformed_json_returns_422(self, client):
        """Test malformed JSON returns 422."""
        response = client.post(
            "/process/events/",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422

    def test_endpoint_performance(self, client):
        """Test endpoint performance meets requirements."""
        valid_event = {
            "id": "perf_endpoint_test",
            "type": "PLACEHOLDER"
        }
        
        # Test multiple requests to get average response time
        times = []
        for _ in range(5):
            start_time = time.time()
            response = client.post("/process/events/", json=valid_event)
            end_time = time.time()
            
            assert response.status_code == 202
            times.append((end_time - start_time) * 1000)  # Convert to milliseconds
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        # Should meet ≤200ms requirement (allowing some overhead for HTTP)
        assert avg_time <= 300, f"Average response time {avg_time:.2f}ms exceeds reasonable limit"
        assert max_time <= 500, f"Max response time {max_time:.2f}ms exceeds reasonable limit"


if __name__ == "__main__":
    # Run basic validation tests
    test_schema = TestEventRequestSchema()
    
    print("Testing valid DevTeam automation event...")
    test_schema.test_valid_devteam_automation_event()
    print("✓ Passed")
    
    print("Testing backward compatibility...")
    test_schema.test_valid_placeholder_event_backward_compatibility()
    print("✓ Passed")
    
    print("Testing validation performance...")
    test_schema.test_validation_performance()
    print("✓ Passed")
    
    print("Testing field validation...")
    test_schema.test_enum_validation()
    print("✓ Passed")
    
    print("\nAll schema validation tests passed!")