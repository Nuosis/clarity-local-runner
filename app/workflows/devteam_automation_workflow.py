from core.schema import WorkflowSchema, NodeConfig
from core.workflow import Workflow
from schemas.event_schema import EventRequest
from workflows.devteam_automation_workflow_nodes.select_node import SelectNode
from workflows.devteam_automation_workflow_nodes.prep_node import PrepNode


class DevTeamAutomationWorkflow(Workflow):
    """
    DevTeam Automation Workflow Implementation
    
    This workflow implements the DevTeam automation processing pipeline following
    the established SELECT→PREP pattern. It processes DEVTEAM_AUTOMATION events
    through a structured workflow that selects an execution plan and prepares
    the task context for downstream processing.
    
    Primary Responsibility:
    - Process DEVTEAM_AUTOMATION events through a structured workflow
    - Follow the SELECT→PREP pattern for task execution planning
    - Maintain compatibility with existing EventRequest schema
    - Provide foundation for future DevTeam automation capabilities
    
    Workflow Flow:
    1. SelectNode: Generates a fixed plan object for task execution
    2. PrepNode: Sets basic task_context metadata and prepares for execution
    
    Performance Requirements:
    - Workflow execution must complete within 2s requirement
    - Leverages existing EventRequest schema for DEVTEAM_AUTOMATION events
    - Follows established patterns from PlaceholderWorkflow
    """
    
    workflow_schema = WorkflowSchema(
        description="DevTeam automation workflow for processing development tasks",
        event_schema=EventRequest,
        start=SelectNode,
        nodes=[
            NodeConfig(
                node=SelectNode,
                connections=[PrepNode],
                description="Selects execution plan for DevTeam automation task",
            ),
            NodeConfig(
                node=PrepNode,
                connections=[],
                description="Prepares task context with basic metadata for execution",
            ),
        ],
    )