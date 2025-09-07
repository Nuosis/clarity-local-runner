"""
Common Pydantic schemas and response models for Cedar Heights Music Academy API.
"""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union
from uuid import UUID

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard API response format."""

    success: bool
    data: Optional[T] = None
    message: Optional[str] = None
    errors: Optional[List[Dict[str, str]]] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class PaginationMetadata(BaseModel):
    """Pagination metadata for list responses."""

    page: int = Field(..., ge=1, description="Current page number")
    limit: int = Field(..., ge=1, le=100, description="Items per page")
    total: int = Field(..., ge=0, description="Total number of items")
    pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class PaginatedResponse(BaseModel):
    """Base class for paginated responses."""

    pagination: PaginationMetadata


class ErrorDetail(BaseModel):
    """Error detail structure."""

    field: Optional[str] = None
    code: str
    message: str


class RequestMetadata(BaseModel):
    """Request metadata for tracking."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: str
    execution_time_ms: Optional[float] = None


class HealthStatus(BaseModel):
    """Health check response."""

    status: str
    timestamp: datetime
    version: str
    services: Dict[str, str]
    uptime: Optional[int] = None


class DetailedHealthStatus(BaseModel):
    """Detailed health check response."""

    status: str
    timestamp: datetime
    version: str
    services: Dict[str, Dict[str, Any]]
    metrics: Dict[str, Any]
