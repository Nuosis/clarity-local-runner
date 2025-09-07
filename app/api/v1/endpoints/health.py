"""
Health check endpoints for Cedar Heights Music Academy API.
"""

import os
import time
from datetime import datetime
from typing import Any, Dict

from database.session import db_session
from fastapi import APIRouter, Depends
from schemas.common import APIResponse, DetailedHealthStatus, HealthStatus
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/", response_model=APIResponse[HealthStatus])
async def health_check(db: Session = Depends(db_session)) -> APIResponse[HealthStatus]:
    """
    Basic health check endpoint.

    Returns:
        APIResponse containing health status information
    """
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"

    health_data = HealthStatus(
        status="healthy" if db_status == "healthy" else "unhealthy",
        timestamp=datetime.utcnow(),
        version="1.0.0",
        services={"database": db_status, "api": "healthy"},
    )

    return APIResponse(success=True, data=health_data, message="Health check completed")


@router.get("/detailed", response_model=APIResponse[DetailedHealthStatus])
async def detailed_health_check(
    db: Session = Depends(db_session),
) -> APIResponse[DetailedHealthStatus]:
    """
    Detailed health check with system information.

    Returns:
        APIResponse containing detailed health and system information
    """
    try:
        import psutil
    except ImportError:
        # Fallback if psutil is not available
        psutil = None

    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        db_status = "healthy"
        db_response_time = time.time()
        db.execute(text("SELECT COUNT(*) FROM users"))
        db_response_time = (time.time() - db_response_time) * 1000  # Convert to ms
    except Exception:
        db_status = "unhealthy"
        db_response_time = None

    # System metrics (with fallback)
    metrics: Dict[str, Any] = {"environment": os.getenv("ENVIRONMENT", "development")}

    if psutil:
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            metrics["cpu_percent"] = cpu_percent
            metrics["memory"] = {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
            }
            metrics["disk"] = {
                "total": disk.total,
                "free": disk.free,
                "percent": (disk.used / disk.total) * 100,
            }
        except Exception:
            metrics["system_metrics"] = "unavailable"
    else:
        metrics["system_metrics"] = "psutil_not_available"

    detailed_data = DetailedHealthStatus(
        status="healthy" if db_status == "healthy" else "unhealthy",
        timestamp=datetime.utcnow(),
        version="1.0.0",
        services={
            "database": {"status": db_status, "response_time_ms": db_response_time},
            "api": {
                "status": "healthy",
                "uptime": time.time(),  # Simplified uptime
            },
        },
        metrics=metrics,
    )

    return APIResponse(
        success=True, data=detailed_data, message="Detailed health check completed"
    )


@router.get("/ready", response_model=APIResponse[Dict[str, str]])
async def readiness_check(
    db: Session = Depends(db_session),
) -> APIResponse[Dict[str, str]]:
    """
    Kubernetes readiness probe endpoint.

    Returns:
        APIResponse indicating if the service is ready to accept traffic
    """
    try:
        # Test database connection
        db.execute(text("SELECT 1"))

        return APIResponse(
            success=True, data={"status": "ready"}, message="Service is ready"
        )
    except Exception:
        return APIResponse(
            success=False, data={"status": "not_ready"}, message="Service is not ready"
        )


@router.get("/live", response_model=APIResponse[Dict[str, str]])
async def liveness_check() -> APIResponse[Dict[str, str]]:
    """
    Kubernetes liveness probe endpoint.

    Returns:
        APIResponse indicating if the service is alive
    """
    return APIResponse(
        success=True, data={"status": "alive"}, message="Service is alive"
    )
