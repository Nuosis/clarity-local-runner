# Generate End-to-End Tests

READ the workflow or feature specification provided.
UNDERSTAND the complete user journey and system interactions.
ANALYZE the full data flow from API input to final output.

Generate comprehensive end-to-end tests for:

$ARGUMENTS

## Process

1. **Map the Complete Flow**
   - Entry point (API endpoint, event trigger)
   - Processing steps (workflow nodes, services)
   - External integrations (databases, AI providers)
   - Final output/side effects

2. **Identify Test Scenarios**
   - **Primary Use Cases**: Main success paths
   - **Alternative Flows**: Different routing decisions
   - **Error Scenarios**: Invalid inputs, service failures
   - **Concurrent Operations**: Race conditions, parallel processing
   - **State Persistence**: Database consistency

3. **Design Test Environment**
   - Docker services required
   - Test database setup/teardown
   - Mock external services vs real integrations
   - Test data preparation

4. **Plan Test Execution**
   - API request construction
   - Async workflow completion waiting
   - Result verification across all systems
   - Cleanup procedures

## E2E Test Structure

### For GenAI Launchpad Workflows

```python
@pytest.mark.e2e
async def test_workflow_complete_flow():
    # 1. Setup test data
    test_event = {
        "user_input": "Analyze this text",
        "metadata": {"priority": "high"}
    }
    
    # 2. Submit to API
    response = await client.post("/events/", json=test_event)
    assert response.status_code == 202
    
    # 3. Wait for Celery task completion
    task_id = response.json()["task_id"]
    result = await wait_for_task_completion(task_id)
    
    # 4. Verify database state
    event = await get_event_from_db(event_id)
    assert event.task_context is not None
    assert event.task_context["nodes"]["AnalyzeNode"]["status"] == "completed"
    
    # 5. Verify workflow routing
    assert "RouterNode" in event.task_context["nodes"]
    assert event.task_context["nodes"]["RouterNode"]["selected"] == "HighPriorityHandler"
    
    # 6. Verify final output
    final_result = event.task_context["nodes"]["ResponseNode"]
    assert final_result["message"] == expected_message
```

## Key Testing Patterns

### 1. API to Database Flow

```python
# Test complete persistence
response = await client.post("/endpoint/", json=data)
db_record = await fetch_from_db(response.json()["id"])
assert db_record.data == data
```

### 2. Workflow Execution Verification

```python
# Test node execution order
context = result.task_context
executed_nodes = list(context["nodes"].keys())
assert executed_nodes == ["Node1", "Node2", "RouterNode", "Node3"]
```

### 3. External Service Integration

```python
# Test with real or mocked AI providers
with mock_ai_response({"analysis": "positive"}):
    result = await run_workflow(test_event)
    assert result.nodes["AgentNode"]["sentiment"] == "positive"
```

### 4. Error Propagation

```python
# Test error handling through the stack
with simulate_service_failure("database"):
    response = await client.post("/events/", json=data)
    assert response.status_code == 503
```

## Test Data Management

1. **Fixtures for Complex Scenarios**

   ```python
   @pytest.fixture
   async def high_priority_event():
       return {
           "user_input": "URGENT: System failure",
           "metadata": {"priority": "critical"}
       }
   ```

2. **Database State Setup**

   ```python
   @pytest.fixture
   async def populated_database():
       await create_test_events()
       yield
       await cleanup_test_data()
   ```

## Verification Points

1. **API Response**: Status codes, response format
2. **Task Execution**: Celery task completion
3. **Database State**: Event storage and updates
4. **Workflow Path**: Correct node execution
5. **Business Logic**: Expected transformations
6. **Side Effects**: Emails, notifications, logs

## Docker Integration

For tests requiring full stack:

```python
@pytest.mark.requires_docker
class TestFullWorkflow:
    def setup_class(cls):
        # Ensure Docker services running
        check_docker_services(["db", "redis", "api"])
```

## Output Requirements

Generate test files that:

1. Cover complete user journeys
2. Test integration points thoroughly
3. Verify data consistency across systems
4. Include both success and failure paths
5. Are runnable in CI/CD pipeline

## Save Location

- Default: `tests/e2e/test_<feature>_e2e.py`
- Or as specified by the user

Remember: E2E tests validate that the entire system works together correctly, not just individual components.
