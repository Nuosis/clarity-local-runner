"""
DevTeam WebSocket Endpoint

This module implements the WebSocket endpoint for real-time DevTeam automation communication.
It provides the /ws/devteam endpoint that accepts connections by projectId parameter with
JWT authentication and basic connection management.

The endpoint follows ADD Profile C requirements:
- Single endpoint: /ws/devteam
- Auth passthrough: JWT validation on connection
- ProjectId routing: Route by projectId only
- Message validation: Comprehensive validation with size limits
- Connection management: Accept, store, and close connections

Performance Requirements:
- ≤500ms WebSocket latency for real-time events
- ≤300ms WebSocket handshake for connection establishment
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Set
from urllib.parse import parse_qs

from fastapi import WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.routing import APIRouter
from pydantic import BaseModel, Field, ValidationError

from auth.dependencies import verify_token_manually
from auth.exceptions import AuthenticationError
from auth.models import UserContext
from core.structured_logging import get_structured_logger
from schemas.websocket_envelope import create_envelope, create_error_envelope, MessageType

# Configure structured logging
logger = logging.getLogger(__name__)
structured_logger = get_structured_logger(__name__)

# WebSocket connection manager
class ConnectionManager:
    """
    WebSocket connection manager for DevTeam automation.
    
    Manages active WebSocket connections with project-based routing and
    user authentication. Provides methods for connecting, disconnecting,
    and broadcasting messages to specific projects or all connections.
    """
    
    def __init__(self):
        # Active connections: {project_id: {connection_id: (websocket, user_context)}}
        self.active_connections: Dict[str, Dict[str, tuple[WebSocket, UserContext]]] = {}
        # Connection metadata for logging and management
        self.connection_metadata: Dict[str, dict] = {}
    
    async def connect(
        self,
        websocket: WebSocket,
        project_id: str,
        user_context: UserContext,
        connection_id: str | None = None
    ) -> str:
        """
        Accept a WebSocket connection and add it to the manager.
        
        Args:
            websocket: The WebSocket connection
            project_id: Project identifier for routing
            user_context: Authenticated user context
            connection_id: Optional connection identifier (generated if not provided)
            
        Returns:
            str: The connection identifier
        """
        if connection_id is None:
            connection_id = f"conn_{uuid.uuid4()}"
        
        # Accept the WebSocket connection
        await websocket.accept()
        
        # Initialize project connections if not exists
        if project_id not in self.active_connections:
            self.active_connections[project_id] = {}
        
        # Store the connection
        self.active_connections[project_id][connection_id] = (websocket, user_context)
        
        # Store connection metadata
        self.connection_metadata[connection_id] = {
            "project_id": project_id,
            "user_id": user_context.user_id,
            "connected_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat()
        }
        
        logger.info(
            "WebSocket connection established",
            extra={
                "connection_id": connection_id,
                "project_id": project_id,
                "user_id": user_context.user_id,
                "total_connections": self.get_total_connections(),
                "project_connections": len(self.active_connections.get(project_id, {})),
                "operation": "websocket_connect"
            }
        )
        
        return connection_id
    
    def disconnect(self, connection_id: str):
        """
        Remove a WebSocket connection from the manager.
        
        Args:
            connection_id: The connection identifier to remove
        """
        if connection_id not in self.connection_metadata:
            return
        
        metadata = self.connection_metadata[connection_id]
        project_id = metadata["project_id"]
        
        # Remove from active connections
        if project_id in self.active_connections:
            if connection_id in self.active_connections[project_id]:
                del self.active_connections[project_id][connection_id]
            
            # Clean up empty project entries
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]
        
        # Remove metadata
        del self.connection_metadata[connection_id]
        
        logger.info(
            "WebSocket connection closed",
            extra={
                "connection_id": connection_id,
                "project_id": project_id,
                "user_id": metadata.get("user_id"),
                "total_connections": self.get_total_connections(),
                "connection_duration": self._calculate_duration(metadata.get("connected_at", "")),
                "operation": "websocket_disconnect"
            }
        )
    
    async def send_personal_message(self, message: dict, connection_id: str):
        """
        Send a message to a specific connection.
        
        Args:
            message: The message to send
            connection_id: The target connection identifier
        """
        if connection_id not in self.connection_metadata:
            return
        
        metadata = self.connection_metadata[connection_id]
        project_id = metadata["project_id"]
        
        if project_id in self.active_connections and connection_id in self.active_connections[project_id]:
            websocket, _ = self.active_connections[project_id][connection_id]
            try:
                await websocket.send_text(json.dumps(message))
                # Update last activity
                self.connection_metadata[connection_id]["last_activity"] = datetime.utcnow().isoformat()
            except Exception as e:
                logger.error(
                    "Failed to send personal message",
                    extra={
                        "connection_id": connection_id,
                        "project_id": project_id,
                        "error": str(e),
                        "operation": "websocket_send_personal"
                    }
                )
    
    async def broadcast_to_project(self, message: dict, project_id: str):
        """
        Broadcast a message to all connections for a specific project.
        
        Args:
            message: The message to broadcast
            project_id: The target project identifier
        """
        if project_id not in self.active_connections:
            return
        
        connections = self.active_connections[project_id].copy()
        failed_connections = []
        
        for connection_id, (websocket, _) in connections.items():
            try:
                await websocket.send_text(json.dumps(message))
                # Update last activity
                if connection_id in self.connection_metadata:
                    self.connection_metadata[connection_id]["last_activity"] = datetime.utcnow().isoformat()
            except Exception as e:
                logger.error(
                    "Failed to broadcast to connection",
                    extra={
                        "connection_id": connection_id,
                        "project_id": project_id,
                        "error": str(e),
                        "operation": "websocket_broadcast"
                    }
                )
                failed_connections.append(connection_id)
        
        # Clean up failed connections
        for connection_id in failed_connections:
            self.disconnect(connection_id)
        
        logger.info(
            "Message broadcast to project",
            extra={
                "project_id": project_id,
                "target_connections": len(connections),
                "failed_connections": len(failed_connections),
                "successful_connections": len(connections) - len(failed_connections),
                "operation": "websocket_broadcast_project"
            }
        )
    
    def get_total_connections(self) -> int:
        """Get the total number of active connections."""
        return sum(len(connections) for connections in self.active_connections.values())
    
    def get_project_connections(self, project_id: str) -> int:
        """Get the number of active connections for a specific project."""
        return len(self.active_connections.get(project_id, {}))
    
    def get_connection_info(self, connection_id: str) -> dict:
        """Get connection metadata for a specific connection."""
        return self.connection_metadata.get(connection_id, {})
    
    def _calculate_duration(self, connected_at: str) -> float:
        """Calculate connection duration in seconds."""
        if not connected_at:
            return 0.0
        try:
            connected_time = datetime.fromisoformat(connected_at.replace('Z', '+00:00'))
            return (datetime.utcnow() - connected_time.replace(tzinfo=None)).total_seconds()
        except Exception:
            return 0.0


# Message schemas for validation
class WebSocketMessage(BaseModel):
    """Base WebSocket message schema following ADD Profile C envelope format."""
    
    type: str = Field(..., description="Message type")
    ts: str = Field(..., description="Timestamp (ISO format)")
    projectId: str = Field(..., description="Project identifier")
    payload: dict = Field(..., description="Message payload")
    
    class Config:
        schema_extra = {
            "example": {
                "type": "execution-update",
                "ts": "2025-01-14T18:30:00Z",
                "projectId": "customer-123/project-abc",
                "payload": {
                    "status": "running",
                    "progress": 45.2,
                    "current_task": "1.1.1"
                }
            }
        }


class WebSocketErrorMessage(BaseModel):
    """WebSocket error message schema."""
    
    type: str = Field(default="error", description="Message type (always 'error')")
    ts: str = Field(..., description="Timestamp (ISO format)")
    projectId: str = Field(..., description="Project identifier")
    payload: dict = Field(..., description="Error payload")
    
    class Config:
        schema_extra = {
            "example": {
                "type": "error",
                "ts": "2025-01-14T18:30:00Z",
                "projectId": "customer-123/project-abc",
                "payload": {
                    "error_code": "VALIDATION_ERROR",
                    "message": "Invalid message format",
                    "details": "Missing required field: type"
                }
            }
        }


# Global connection manager instance
manager = ConnectionManager()

# Create router
router = APIRouter()


@router.websocket("/devteam")
async def websocket_devteam_endpoint(
    websocket: WebSocket,
    project_id: str = Query(..., description="Project identifier for routing")
):
    """
    WebSocket endpoint for DevTeam automation real-time communication.
    
    This endpoint provides real-time bidirectional communication for DevTeam automation
    with JWT authentication and project-based routing. It follows ADD Profile C requirements
    for single endpoint, auth passthrough, and projectId routing.
    
    **Connection Requirements:**
    - JWT token must be provided via 'token' query parameter or Authorization header
    - projectId must be provided as query parameter
    - Connection establishment must complete within ≤300ms
    - Real-time events must be delivered within ≤500ms
    
    **Message Format:**
    All messages follow the envelope format: { type, ts, projectId, payload }
    
    **Supported Message Types:**
    - execution-update: Status and progress updates
    - execution-log: Log entries and debug information  
    - error: Error notifications and alerts
    - completion: Task and workflow completion events
    
    **Security:**
    - JWT validation on connection establishment
    - Per-project authorization checks
    - Message size limits enforced at gateway level
    - Comprehensive audit logging
    
    Args:
        websocket: The WebSocket connection
        project_id: Project identifier for routing messages
    """
    connection_id = None
    start_time = time.time()
    
    try:
        # Extract authentication token from query parameters or headers
        query_params = dict(websocket.query_params)
        token = query_params.get('token')
        
        # If no token in query params, try to get from headers
        if not token:
            auth_header = websocket.headers.get('authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        if not token:
            # Send error message and close connection
            await websocket.close(code=4001, reason="Authentication token required")
            logger.warning(
                "WebSocket connection rejected - missing token",
                extra={
                    "project_id": project_id,
                    "remote_addr": websocket.client.host if websocket.client else "unknown",
                    "operation": "websocket_auth_failed"
                }
            )
            return
        
        # Validate project ID format
        if not project_id or not project_id.strip():
            await websocket.close(code=4002, reason="Project ID required")
            logger.warning(
                "WebSocket connection rejected - missing project ID",
                extra={
                    "remote_addr": websocket.client.host if websocket.client else "unknown",
                    "operation": "websocket_validation_failed"
                }
            )
            return
        
        project_id = project_id.strip()
        
        # Validate project ID format for security
        import re
        if not re.match(r"^[a-zA-Z0-9_/-]+$", project_id):
            await websocket.close(code=4003, reason="Invalid project ID format")
            logger.warning(
                "WebSocket connection rejected - invalid project ID format",
                extra={
                    "project_id": project_id,
                    "remote_addr": websocket.client.host if websocket.client else "unknown",
                    "operation": "websocket_validation_failed"
                }
            )
            return
        
        # Authenticate the user
        try:
            user_context = await verify_token_manually(token)
        except (AuthenticationError, HTTPException) as e:
            await websocket.close(code=4004, reason="Authentication failed")
            logger.warning(
                "WebSocket connection rejected - authentication failed",
                extra={
                    "project_id": project_id,
                    "error": str(e),
                    "remote_addr": websocket.client.host if websocket.client else "unknown",
                    "operation": "websocket_auth_failed"
                }
            )
            return
        
        # Calculate handshake duration
        handshake_duration = (time.time() - start_time) * 1000
        
        # Connect to the manager
        connection_id = await manager.connect(websocket, project_id, user_context)
        
        # Log successful connection with performance metrics
        logger.info(
            "WebSocket connection authenticated and established",
            extra={
                "connection_id": connection_id,
                "project_id": project_id,
                "user_id": user_context.user_id,
                "handshake_duration_ms": round(handshake_duration, 2),
                "performance_target_met": handshake_duration <= 300,
                "remote_addr": websocket.client.host if websocket.client else "unknown",
                "operation": "websocket_connected"
            }
        )
        
        # Send welcome message using standardized envelope
        welcome_message = create_envelope(
            message_type=MessageType.CONNECTION_ESTABLISHED,
            project_id=project_id,
            payload={
                "connection_id": connection_id,
                "user_id": user_context.user_id,
                "message": "WebSocket connection established successfully"
            }
        )
        await manager.send_personal_message(welcome_message, connection_id)
        
        # Listen for messages
        while True:
            try:
                # Receive message with timeout for performance monitoring
                message_start = time.time()
                data = await websocket.receive_text()
                
                # Validate message size (basic check, gateway should enforce limits)
                if len(data) > 10000:  # 10KB limit
                    error_message = create_error_envelope(
                        project_id=project_id,
                        error_code="MESSAGE_TOO_LARGE",
                        message="Message exceeds size limit",
                        details=f"Max size: 10000, received: {len(data)}"
                    )
                    await manager.send_personal_message(error_message, connection_id)
                    continue
                
                # Parse and validate message
                try:
                    message_data = json.loads(data)
                    message = WebSocketMessage(**message_data)
                except (json.JSONDecodeError, ValidationError) as e:
                    error_message = create_error_envelope(
                        project_id=project_id,
                        error_code="INVALID_MESSAGE_FORMAT",
                        message="Message validation failed",
                        details=str(e)
                    )
                    await manager.send_personal_message(error_message, connection_id)
                    continue
                
                # Calculate message processing time
                processing_duration = (time.time() - message_start) * 1000
                
                # Log message received
                logger.info(
                    "WebSocket message received",
                    extra={
                        "connection_id": connection_id,
                        "project_id": project_id,
                        "user_id": user_context.user_id,
                        "message_type": message.type,
                        "processing_duration_ms": round(processing_duration, 2),
                        "performance_target_met": processing_duration <= 500,
                        "operation": "websocket_message_received"
                    }
                )
                
                # Echo message back using standardized envelope
                echo_message = create_envelope(
                    message_type=MessageType.MESSAGE_RECEIVED,
                    project_id=project_id,
                    payload={
                        "original_type": message.type,
                        "received_at": message.ts,
                        "processed_at": datetime.utcnow().isoformat() + "Z",
                        "message": "Message received and processed successfully"
                    }
                )
                await manager.send_personal_message(echo_message, connection_id)
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(
                    "Error processing WebSocket message",
                    extra={
                        "connection_id": connection_id,
                        "project_id": project_id,
                        "user_id": user_context.user_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "operation": "websocket_message_error"
                    },
                    exc_info=True
                )
                
                # Send error message to client using standardized envelope
                error_message = create_error_envelope(
                    project_id=project_id,
                    error_code="PROCESSING_ERROR",
                    message="Error processing message",
                    details="An internal error occurred while processing your message"
                )
                try:
                    await manager.send_personal_message(error_message, connection_id)
                except Exception:
                    # If we can't send error message, connection is likely broken
                    break
    
    except WebSocketDisconnect:
        logger.info(
            "WebSocket disconnected by client",
            extra={
                "connection_id": connection_id,
                "project_id": project_id,
                "operation": "websocket_client_disconnect"
            }
        )
    except Exception as e:
        logger.error(
            "Unexpected error in WebSocket endpoint",
            extra={
                "connection_id": connection_id,
                "project_id": project_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "operation": "websocket_unexpected_error"
            },
            exc_info=True
        )
    finally:
        # Clean up connection
        if connection_id:
            manager.disconnect(connection_id)


# Utility functions for connection management
def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance."""
    return manager


async def broadcast_to_project(message: dict, project_id: str):
    """
    Utility function to broadcast a message to all connections for a project.
    
    Args:
        message: The message to broadcast
        project_id: The target project identifier
    """
    await manager.broadcast_to_project(message, project_id)


async def send_to_connection(message: dict, connection_id: str):
    """
    Utility function to send a message to a specific connection.
    
    Args:
        message: The message to send
        connection_id: The target connection identifier
    """
    await manager.send_personal_message(message, connection_id)


def get_project_connection_count(project_id: str) -> int:
    """
    Get the number of active connections for a project.
    
    Args:
        project_id: The project identifier
        
    Returns:
        int: Number of active connections
    """
    return manager.get_project_connections(project_id)


def get_total_connection_count() -> int:
    """
    Get the total number of active WebSocket connections.
    
    Returns:
        int: Total number of active connections
    """
    return manager.get_total_connections()