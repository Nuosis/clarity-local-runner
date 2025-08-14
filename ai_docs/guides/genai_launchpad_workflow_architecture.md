# GenAI Launchpad Workflow Architecture

## Overview

GenAI Launchpad is a **DAG-based workflow orchestration framework** designed for building AI-powered processing pipelines. It implements the **Chain of Responsibility pattern** with type-safe, schema-driven workflows that can integrate multiple AI providers and execute nodes both sequentially and concurrently.

## Core Architecture Components

### 1. TaskContext (`app/core/task.py`)

The **central state container** that flows through all workflow nodes:

```python
class TaskContext(BaseModel):
    event: Any                    # Original trigger event data
    nodes: Dict[str, Any]        # Results from each node's execution
    metadata: Dict[str, Any]     # Workflow-level metadata and configuration
    should_stop: bool            # Flag to halt workflow execution
```

**Key features:**

- `update_node(node_name, **kwargs)`: Updates node-specific results
- `stop_workflow()`: Halts workflow execution after current node
- Preserves complete execution history for debugging and auditing

### 2. WorkflowSchema (`app/core/schema.py`)

**Defines workflow structure** using Pydantic models for type safety:

```python
class WorkflowSchema(BaseModel):
    description: Optional[str]           # Workflow purpose
    event_schema: Type[BaseModel]       # Input validation schema
    start: Type[Node]                   # Entry point node
    nodes: List[NodeConfig]             # Node configurations and connections
```

### 3. NodeConfig (`app/core/schema.py`)

**Configures individual nodes** and their relationships:

```python
class NodeConfig(BaseModel):
    node: Type[Node]                        # Node class to instantiate
    connections: List[Type[Node]]           # Next nodes in the flow
    is_router: bool                         # Whether node performs routing
    description: Optional[str]              # Node purpose
    concurrent_nodes: List[Type[Node]]      # Nodes to run concurrently
```

### 4. Workflow Engine (`app/core/workflow.py`)

**Orchestrates workflow execution**:

- **Validation**: Uses `WorkflowValidator` to ensure DAG structure
- **Initialization**: Creates node instances and connection mappings
- **Execution**: Processes nodes sequentially with routing and concurrency support
- **Context Management**: Logs execution and handles errors via `node_context()`

**Execution methods:**

- `run(event)`: Synchronous execution (creates new event loop)
- `run_async(event)`: Asynchronous execution (uses existing event loop)

## Node Architecture

### Base Node (`app/core/nodes/base.py`)

**Abstract base class** implementing Chain of Responsibility:

```python
class Node(ABC):
    @property
    def node_name(self) -> str:
        return self.__class__.__name__
    
    @abstractmethod
    async def process(self, task_context: TaskContext) -> TaskContext:
        pass
```

**Implementation pattern:**

1. Receive TaskContext from previous node
2. Process according to node's responsibility
3. Store results in `task_context.nodes[self.node_name]`
4. Return updated context for next node

### Node Types

#### 1. AgentNode (`app/core/nodes/agent.py`)

**AI-powered processing node** using pydantic-ai:

```python
class AgentNode(Node, ABC):
    class DepsType(BaseModel): pass      # Input dependencies
    class OutputType(BaseModel): pass    # Structured AI output
    
    @abstractmethod
    def get_agent_config(self) -> AgentConfig:
        pass
```

**Supports multiple providers:**

- OpenAI / Azure OpenAI
- Anthropic (Claude)
- Google Gemini
- AWS Bedrock
- Ollama (local models)

**AgentConfig** defines:

- `model_provider`: Provider selection
- `model_name`: Specific model
- `output_type`: Response structure
- `system_prompt`: Agent instructions
- Tools, MCP servers, retries, etc.

#### 2. ConcurrentNode (`app/core/nodes/concurrent.py`)

**Executes multiple nodes concurrently** using asyncio:

```python
class ConcurrentNode(Node, ABC):
    async def execute_nodes_concurrently(self, task_context: TaskContext):
        node_config = task_context.metadata["nodes"][self.__class__]
        coroutines = [node().process(task_context) 
                     for node in node_config.concurrent_nodes]
        return await asyncio.gather(*coroutines)
```

**Use cases:**

- Parallel API calls
- Independent processing tasks
- Multiple AI model queries

#### 3. BaseRouter (`app/core/nodes/router.py`)

**Decision-making node** for conditional flow:

```python
class BaseRouter(Node):
    def route(self, task_context: TaskContext) -> Node:
        for route_node in self.routes:
            next_node = route_node.determine_next_node(task_context)
            if next_node:
                return next_node
        return self.fallback
```

**RouterNode** interface:

```python
class RouterNode(ABC):
    @abstractmethod
    def determine_next_node(self, task_context: TaskContext) -> Optional[Node]:
        pass
```

## Workflow Validation (`app/core/validate.py`)

**WorkflowValidator** ensures workflow integrity:

1. **DAG Validation**:
   - Detects cycles using Depth-First Search (DFS)
   - Ensures acyclic directed graph structure

2. **Reachability Check**:
   - Uses Breadth-First Search (BFS) from start node
   - Identifies unreachable nodes

3. **Connection Rules**:
   - Non-router nodes can only have single connection
   - Only router nodes can have multiple connections

## Execution Flow

### 1. Workflow Initialization

```python
class MyWorkflow(Workflow):
    workflow_schema = WorkflowSchema(...)
    
workflow = MyWorkflow()  # Validates and initializes nodes
```

### 2. Event Processing

```python
# Synchronous execution
result = workflow.run({"user_input": "Hello"})

# Asynchronous execution  
result = await workflow.run_async({"user_input": "Hello"})
```

### 3. Execution Steps

1. **Event Validation**: Input validated against `event_schema`
2. **Context Creation**: TaskContext initialized with validated event
3. **Node Execution Loop**:
   - Current node processes context
   - Router nodes determine next path
   - Concurrent nodes spawn parallel execution
   - Process continues until no connections remain or `should_stop` is True
4. **Result Return**: Final TaskContext with all node results

### 4. Node Processing Pattern

```python
class MyNode(Node):
    async def process(self, task_context: TaskContext) -> TaskContext:
        # Access previous results
        previous_result = task_context.nodes.get("PreviousNode", {})
        
        # Process data
        result = await self.do_processing(task_context.event)
        
        # Store results
        task_context.update_node(self.node_name, 
                                result=result,
                                timestamp=datetime.now())
        
        return task_context
```

## Implementation Guide

### Creating a New Workflow

1. **Define Event Schema** (`app/schemas/`):

```python
class MyEventSchema(BaseModel):
    user_input: str
    metadata: Dict[str, Any]
```

2. **Create Nodes** (`app/workflows/my_workflow_nodes/`):

```python
class AnalyzeNode(AgentNode):
    class OutputType(AgentNode.OutputType):
        sentiment: str
        score: float
    
    def get_agent_config(self) -> AgentConfig:
        return AgentConfig(
            model_provider=ModelProvider.OPENAI,
            model_name="gpt-4",
            output_type=self.OutputType,
            system_prompt="Analyze sentiment..."
        )
    
    async def process(self, task_context: TaskContext) -> TaskContext:
        result = await self.agent.run(task_context.event.user_input)
        task_context.update_node(self.node_name, **result.dict())
        return task_context
```

3. **Define Workflow** (`app/workflows/`):

```python
class MyWorkflow(Workflow):
    workflow_schema = WorkflowSchema(
        description="Sentiment analysis workflow",
        event_schema=MyEventSchema,
        start=AnalyzeNode,
        nodes=[
            NodeConfig(
                node=AnalyzeNode,
                connections=[RouterNode],
                description="Analyzes input sentiment"
            ),
            NodeConfig(
                node=RouterNode,
                connections=[PositiveNode, NegativeNode],
                is_router=True,
                description="Routes based on sentiment"
            )
        ]
    )
```

### Using the Workflow Init Command

The framework includes a helper command to scaffold new workflows:

```bash
python -m app.core.commands.init_workflow
```

This creates:

- Workflow file with basic structure
- Node folder with initial node
- Schema file for event validation

## Advanced Patterns

### Concurrent Processing

Configure concurrent nodes for parallel operations:

```python
NodeConfig(
    node=ProcessNode,
    connections=[NextNode],
    concurrent_nodes=[
        EmailNotificationNode,
        DatabaseLogNode,
        MetricsNode
    ]
)
```

### Complex Routing

Implement sophisticated routing logic:

```python
class SmartRouter(BaseRouter):
    def __init__(self):
        self.routes = [
            HighPriorityRoute(),
            ContentTypeRoute(),
            DefaultRoute()
        ]
        self.fallback = ErrorHandlerNode()
```

### Error Handling

The framework provides context managers for error handling:

```python
with self.node_context(node_name):
    # Node execution with automatic logging
    # Errors are logged and re-raised
```

### Workflow Termination

Nodes can stop workflow execution:

```python
if error_condition:
    task_context.stop_workflow()
    return task_context
```

## Best Practices

1. **Type Safety**: Always define Pydantic models for inputs/outputs
2. **Single Responsibility**: Each node should have one clear purpose
3. **Error Handling**: Use try/except blocks and log errors appropriately
4. **Testing**: Test nodes independently with mock TaskContext
5. **Documentation**: Use descriptive node names and descriptions
6. **Performance**: Use ConcurrentNode for I/O-bound parallel operations

## Key Benefits

- **Type-Safe**: Pydantic validation throughout
- **Modular**: Nodes are independent and reusable
- **Testable**: Each component can be tested in isolation
- **Scalable**: Async execution and concurrent processing
- **Flexible**: Multiple AI providers and custom routing logic
- **Debuggable**: Complete execution history in TaskContext

This architecture enables building sophisticated AI workflows with clear separation of concerns, comprehensive validation, and flexible execution patterns suitable for production environments.

## Example Implmentation 
`/ai_docs/context/guides/workflow_example/`