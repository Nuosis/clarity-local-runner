"""
Main API router for Cedar Heights Music Academy v1.
"""

from fastapi import APIRouter

from .endpoints import (
    academic,
    health,
    lessons,
    payments,
    public,
    settings,
    students,
    teachers,
)

api_router = APIRouter()

# Health check endpoints
api_router.include_router(health.router, prefix="/health", tags=["health"])

# Public endpoints (no authentication required)
api_router.include_router(public.router, prefix="/public", tags=["public"])

# Student management endpoints
api_router.include_router(students.router, prefix="/students", tags=["students"])

# Teacher management endpoints
api_router.include_router(teachers.router, prefix="/teachers", tags=["teachers"])

# Lesson management endpoints
api_router.include_router(lessons.router, prefix="/lessons", tags=["lessons"])

# Payment management endpoints
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])

# Academic calendar management endpoints
api_router.include_router(academic.router, prefix="/academic", tags=["academic"])

# System settings management endpoints
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
