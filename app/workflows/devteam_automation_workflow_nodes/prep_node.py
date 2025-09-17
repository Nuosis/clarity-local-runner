import asyncio
from datetime import datetime
from core.nodes.base import Node
from core.task import TaskContext
from services.execution_update_service import send_execution_update


class PrepNode(Node):
    """
    PrepNode for DevTeam Automation workflow.
    
    This node serves as the preparation phase of the DevTeam automation workflow,
    setting basic task_context metadata required for downstream processing.
    Following the established pattern from PlaceholderWorkflow, this is a stub
    implementation that provides the essential metadata structure.
    
    Primary Responsibility:
    - Set basic task_context metadata (correlationId, status, timestamps)
    - Prepare workflow state for execution phases
    - Validate and enrich task context with required fields
    """

    async def process(self, task_context: TaskContext) -> TaskContext:
        """
        Process the task context by setting basic metadata for task execution.
        
        This method implements the preparation logic for DevTeam automation tasks.
        It enriches the task_context with essential metadata fields required
        for proper workflow execution and audit trail maintenance.
        
        Args:
            task_context: The shared context object passed through the workflow
            
        Returns:
            Updated TaskContext with basic metadata and node processing results
        """
        # Extract correlationId from event metadata if available
        correlation_id = None
        if hasattr(task_context.event, 'metadata') and task_context.event.metadata:
            correlation_id = task_context.event.metadata.correlation_id
        
        # Set basic task_context metadata following established patterns
        task_context.metadata.update({
            "correlationId": correlation_id or f"corr_{task_context.event.id}",
            "status": "prepared",
            "prepared_at": datetime.utcnow().isoformat(),
            "workflow_type": "DEVTEAM_AUTOMATION",
            "event_id": task_context.event.id,
            "project_id": getattr(task_context.event, 'project_id', None),
            "task_id": getattr(task_context.event.task, 'id', None) if hasattr(task_context.event, 'task') else None,
            "priority": getattr(task_context.event, 'priority', 'normal')
        })
        
        # Retrieve the selected plan from SelectNode if available
        selected_plan = task_context.metadata.get("selected_plan", {})
        
        # Update node processing status following established patterns
        task_context.update_node(
            node_name=self.node_name,
            status="completed",
            message="Task context prepared with basic metadata for DevTeam automation",
            event_data={
                "correlationId": task_context.metadata["correlationId"],
                "workflow_type": task_context.metadata["workflow_type"],
                "prepared_at": task_context.metadata["prepared_at"],
                "plan_id": selected_plan.get("plan_id", "unknown")
            }
        )
        
        # Send execution update for node completion
        project_id = getattr(task_context.event, 'project_id', None)
        if project_id:
            try:
                # Create execution ID from event ID
                execution_id = f"exec_{task_context.event.id}"
                
                # Get correlation ID from metadata
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