import logging
import sys
from pathlib import Path


sys.path.append(str(Path(__file__).parent.parent / "app"))
sys.path.append(str(Path(__file__).parent.parent))

import nest_asyncio
from workflows.workflow_registry import WorkflowRegistry

from playground.utils.event_loader import EventLoader

logging.basicConfig(level=logging.INFO)
nest_asyncio.apply()

"""
This playground is used to test the WorkflowRegistry and the workflows themselves.
"""

event = EventLoader.load_event(event_key="placeholder_event")
workflow = WorkflowRegistry.PLACEHOLDER.value()
output = workflow.run(event)
output.model_dump()
