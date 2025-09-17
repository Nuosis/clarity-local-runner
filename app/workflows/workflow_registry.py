from enum import Enum

# TODO: Import actual workflow implementations as they are created
from workflows.devteam_automation_workflow import DevTeamAutomationWorkflow
# from workflows.repository_initialization_workflow import RepositoryInitializationWorkflow
# from workflows.task_execution_workflow import TaskExecutionWorkflow
from workflows.placeholder_workflow import PlaceholderWorkflow


class WorkflowRegistry(Enum):
    """Registry of available workflows for the Clarity Local Runner system."""
    
    # DevTeam automation workflow implementation
    DEVTEAM_AUTOMATION = DevTeamAutomationWorkflow
    
    # TODO: Add additional workflow implementations as they are created
    # REPOSITORY_INITIALIZATION = RepositoryInitializationWorkflow
    # TASK_EXECUTION = TaskExecutionWorkflow
    
    # Placeholder workflow from existing system
    PLACEHOLDER = PlaceholderWorkflow
