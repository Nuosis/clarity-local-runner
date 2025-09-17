"""
DevTeam Automation Workflow Nodes Package

This package contains the node implementations for the DevTeam Automation workflow.
The workflow follows a SELECT→PREP pattern for processing DevTeam automation events.

Nodes:
- SelectNode: Selects and returns a fixed plan object for task execution
- PrepNode: Prepares task context with basic metadata for downstream processing
"""