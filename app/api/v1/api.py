"""
Main API router for Clarity Local Runner workflow orchestration system v1.
"""

from fastapi import APIRouter

from .endpoints import (
    health,
    public,
    devteam_automation,
    websocket,
)

api_router = APIRouter()

# Health check endpoints
api_router.include_router(health.router, prefix="/health", tags=["health"])

# Public endpoints (no authentication required)
api_router.include_router(public.router, prefix="/public", tags=["public"])

# DevTeam automation endpoints
api_router.include_router(
    devteam_automation.router,
    prefix="/devteam/automation",
    tags=["devteam-automation"]
)

# WebSocket endpoints
api_router.include_router(
    websocket.router,
    prefix="/ws",
    tags=["websocket"]
)

# TODO: Add additional workflow orchestration endpoints as they are implemented
# - Workflow execution endpoints
# - Task management endpoints
# - Container orchestration endpoints
# - Repository management endpoints
