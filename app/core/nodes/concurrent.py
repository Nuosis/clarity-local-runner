import asyncio
from abc import ABC, abstractmethod

from core.nodes.base import Node
from core.schema import NodeConfig
from core.task import TaskContext


class ConcurrentNode(Node, ABC):
    """
    Base class for nodes that execute other nodes concurrently using asyncio.

    This class provides a method to execute a list of nodes concurrently on a single thread,
    using asyncio.gather. This ensures that I/O-bound operations can proceed in parallel
    without blocking the main thread or event loop.

    When to use:
    - Use ConcurrentNode when running the workflow in the main application, where the event loop is active
      (for example, in a FastAPI app or a CLI tool).
    - It is also perfectly fine to use ConcurrentNode within Celery tasks — Celery runs the task in a worker process,
      and asyncio code will execute efficiently in that context.
    - It is especially suited for workflows that consist mostly of async I/O operations (e.g. network calls, database access).
    - It will not block other processes.

    Subclasses must implement the `process` method to define the specific logic of the concurrent node.
    """

    async def execute_nodes_concurrently(self, task_context: TaskContext):
        node_config: NodeConfig = task_context.metadata["nodes"][self.__class__]
        coroutines = [
            node().process(task_context) for node in node_config.parallel_nodes
        ]
        return await asyncio.gather(*coroutines)

    @abstractmethod
    async def process(self, task_context: TaskContext) -> TaskContext:
        pass
