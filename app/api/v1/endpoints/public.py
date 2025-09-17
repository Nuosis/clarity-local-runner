"""
Public API endpoints for Clarity Local Runner.
These endpoints do not require authentication and provide public information about workflows.
"""

from typing import List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel
from schemas.common import APIResponse

router = APIRouter()


class WorkflowInfo(BaseModel):
    """Public workflow information."""
    
    id: str
    name: str
    description: str
    category: str
    is_available: bool


class SystemStatus(BaseModel):
    """System status information."""
    
    status: str
    version: str
    uptime: str
    active_workflows: int


@router.get("/workflows", response_model=APIResponse[List[WorkflowInfo]])
async def get_public_workflows(
    category: Optional[str] = Query(None, description="Filter by workflow category")
):
    """
    Get available workflows for public display.
    
    Returns basic workflow information without sensitive data.
    """
    try:
        # TODO: Implement actual workflow discovery from registry
        workflows = [
            WorkflowInfo(
                id="placeholder",
                name="Placeholder Workflow",
                description="A placeholder workflow for development",
                category="development",
                is_available=True
            )
        ]
        
        if category:
            workflows = [w for w in workflows if w.category == category]
        
        return APIResponse(
            success=True,
            data=workflows,
            message="Available workflows retrieved successfully"
        )
        
    except Exception as e:
        return APIResponse(
            success=False,
            data=None,
            message=f"Failed to retrieve workflows: {str(e)}"
        )


@router.get("/status", response_model=APIResponse[SystemStatus])
async def get_system_status():
    """
    Get system status information.
    
    Returns current system status and basic metrics.
    """
    try:
        # TODO: Implement actual system status monitoring
        status = SystemStatus(
            status="operational",
            version="1.0.0",
            uptime="0 days, 0 hours",
            active_workflows=0
        )
        
        return APIResponse(
            success=True,
            data=status,
            message="System status retrieved successfully"
        )
        
    except Exception as e:
        return APIResponse(
            success=False,
            data=None,
            message=f"Failed to retrieve system status: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    Simple health check endpoint.
    
    Returns basic health status for monitoring.
    """
    return {"status": "healthy", "service": "clarity-local-runner"}
