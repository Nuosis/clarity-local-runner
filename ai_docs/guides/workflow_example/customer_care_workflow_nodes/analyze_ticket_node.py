from core.nodes.concurrent import ConcurrentNode
from core.task import TaskContext


class AnalyzeTicketNode(ConcurrentNode):
    async def process(self, task_context: TaskContext) -> TaskContext:
        await self.execute_nodes_concurrently(task_context)
        return task_context
