from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor

from core.nodes.base import Node
from core.schema import NodeConfig
from core.task import TaskContext


class ParallelNode(Node, ABC):
    """
    Base class for nodes that execute other nodes in parallel.

    This class provides a method to execute a list of nodes in parallel using concurrent.futures.ThreadPoolExecutor.
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
