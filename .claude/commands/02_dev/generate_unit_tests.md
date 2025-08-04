# Generate Unit Tests

ANALYZE the code structure and key behaviors that need testing.
CREATE focused pytest unit tests for critical functionality.

Generate unit tests for:

$ARGUMENTS

## Process

1. **Identify Key Behaviors**
   - Core functionality that must work correctly
   - Critical error conditions
   - Important edge cases
   - State changes and side effects

2. **Generate Focused Tests**

   ```python
   import pytest
   from unittest.mock import Mock, patch
   
   def test_<function>_<behavior>():
       # Given: Setup
       # When: Action
       # Then: Assert
   ```

3. **Test Naming**
   - `test_<what>_<condition>_<expected>`
   - Be specific: `test_process_invalid_event_raises_validation_error`

## Workflow Node Example

```python
@pytest.mark.asyncio
async def test_analyze_node_extracts_key_info():
    # Given
    context = TaskContext(
        event={"text": "urgent: customer complaint"},
        nodes={},
        metadata={}
    )
    
    # When
    node = AnalyzeNode()
    result = await node.process(context)
    
    # Then
    assert result.nodes["AnalyzeNode"]["priority"] == "high"
```

## Mock External Dependencies

```python
@patch('openai.ChatCompletion.create')
def test_agent_node_handles_api_error(mock_api):
    mock_api.side_effect = Exception("API Error")
    # Test error handling behavior
```

## Focus Areas

- **Core Logic**: The main purpose of the code
- **Error Handling**: What happens when things go wrong
- **Integration Points**: Mocking external services
- **Data Validation**: Input/output contracts

Skip:

- Trivial getters/setters
- Simple data classes
- One-line functions
- Excessive permutations

Remember: Write tests that verify behavior, not implementation details.
