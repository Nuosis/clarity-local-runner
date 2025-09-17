import asyncio
from core.nodes.base import Node
from core.task import TaskContext
from services.execution_update_service import send_execution_update


class SelectNode(Node):
    """
    SelectNode for DevTeam Automation workflow.
    
    This node serves as the selection phase of the DevTeam automation workflow,
    returning a fixed plan object that defines the execution strategy for the task.
    Following the established pattern from PlaceholderWorkflow, this is a stub
    implementation that provides the minimal structure needed for workflow execution.
    
    Primary Responsibility:
    - Generate and return a fixed plan object for task execution
    - Set initial workflow state in task_context
    - Prepare the workflow for the subsequent PrepNode processing
    """

    async def process(self, task_context: TaskContext) -> TaskContext:
        """
        Process the task context by generating a fixed plan object.
        
        This method implements the selection logic for DevTeam automation tasks.
        It creates a minimal but complete plan structure that can be used by
        downstream nodes for task execution.
        
        Args:
            task_context: The shared context object passed through the workflow
            
        Returns:
            Updated TaskContext with the selected plan and node processing results
        """
        # Create a fixed plan object with minimal structure
        fixed_plan = {
            "plan_id": f"plan_{task_context.event.id}",
            "strategy": "devteam_automation",
            "phases": [
                {
                    "phase": "preparation",
                    "description": "Prepare task context and validate requirements"
                },
                {
                    "phase": "execution", 
                    "description": "Execute DevTeam automation task"
                }
            ],
            "estimated_duration": "2s",
            "priority": getattr(task_context.event, 'priority', 'normal')
        }
        
        # Store the plan in task_context for downstream processing
        task_context.metadata["selected_plan"] = fixed_plan
        
        # Update node processing status following established patterns
        task_context.update_node(
            node_name=self.node_name,
            status="completed",
            message="Fixed plan selected for DevTeam automation workflow",
            event_data={
                "plan_id": fixed_plan["plan_id"],
                "strategy": fixed_plan["strategy"],
                "phases_count": len(fixed_plan["phases"])
            }
        )
        
        # Send execution update for node completion
        project_id = getattr(task_context.event, 'project_id', None)
        if project_id:
            try:
                # Create execution ID from event ID
                execution_id = f"exec_{task_context.event.id}"
                
                # Get correlation ID from metadata if available
                correlation_id = task_context.metadata.get('correlationId')
                
                # Send node completion update
                asyncio.run(send_execution_update(
                    project_id=project_id,
                    task_context=task_context.model_dump(mode="json"),
                    execution_id=execution_id,
                    event_type="node_completed",
                    correlation_id=correlation_id
                ))
            except Exception as update_error:
                # Log but don't fail the node processing
                pass
        
        return task_context