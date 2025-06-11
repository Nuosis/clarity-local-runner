from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor

from core.nodes.base import Node
from core.schema import NodeConfig
from core.task import TaskContext


class ParallelNode(Node, ABC):
    """
    Base class for nodes that execute other nodes in parallel using ThreadPoolExecutor.

    This class provides a method to execute a list of nodes in parallel using threads.
    ThreadPoolExecutor creates real threads, which are more suited to CPU-bound operations,
    but can introduce blocking behavior and thread contention.

    When to use:
    - In most modern Python async applications, you should prefer ConcurrentNode over ParallelNode.
    - ParallelNode is no longer recommended for general use. It may still be useful if you need to run blocking, CPU-heavy
      synchronous code in parallel (e.g. image processing, data compression), where async code would not be efficient.
    - However, in typical async workflows (web apps, Celery tasks, async pipelines), using ConcurrentNode is safer and more predictable.
    - Be aware that using ParallelNode can block other processes if you spawn too many threads or if the tasks
      run long CPU-bound operations.

    Subclasses must implement the `process` method to define the specific logic of the parallel node.
    """

    def execute_nodes_in_parallel(self, task_context: TaskContext):
        node_config: NodeConfig = task_context.metadata["nodes"][self.__class__]
        future_list = []
        with ThreadPoolExecutor() as executor:
            for node in node_config.parallel_nodes:
                future = executor.submit(node().process, task_context)
                future_list.append(future)

            results = [future.result() for future in future_list]
        return results

    @abstractmethod
    async def process(self, task_context: TaskContext) -> TaskContext:
        pass
