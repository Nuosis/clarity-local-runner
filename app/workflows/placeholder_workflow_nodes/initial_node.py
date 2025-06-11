from core.nodes.base import Node
from core.task import TaskContext


class InitialNode(Node):
    async def process(self, task_context: TaskContext) -> TaskContext:
        return task_context
