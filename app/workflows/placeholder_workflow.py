from core.schema import WorkflowSchema, NodeConfig
from core.workflow import Workflow
from schemas.placeholder_schema import PlaceholderEventSchema
from workflows.placeholder_workflow_nodes.initial_node import InitialNode


class PlaceholderWorkflow(Workflow):
    workflow_schema = WorkflowSchema(
        description="",
        event_schema=PlaceholderEventSchema,
        start=InitialNode,
        nodes=[
            NodeConfig(
                node=InitialNode,
                connections=[],
                description="",
            ),
        ],
    )
