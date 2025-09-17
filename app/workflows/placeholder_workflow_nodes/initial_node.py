from core.nodes.base import Node
from core.task import TaskContext


class InitialNode(Node):
    """
    Simple initial node for placeholder workflow.
    
    This node serves as a basic starting point for the placeholder workflow,
    processing the incoming event and storing a simple result in the task context.
    """

    async def process(self, task_context: TaskContext) -> TaskContext:
        """
        Process the task context by storing a simple placeholder result.
        
        Args:
            task_context: The shared context object passed through the workflow
            
        Returns:
            Updated TaskContext with this node's processing results
        """
        # Store a simple result indicating the node has processed the event
        task_context.update_node(
            node_name=self.node_name,
            status="completed",
            message="Placeholder workflow initial processing completed",
            event_data=task_context.event
        )
        
        return task_context