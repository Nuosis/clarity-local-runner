import logging
import os
import time
from typing import Callable

from api.router import router as process_router
from api.v1.api import api_router
from auth.dependencies import initialize_auth_handler
from auth.middleware import SupabaseJWTMiddleware
from auth.routes import router as auth_router
from auth.supabase_auth import SupabaseJWTAuth
from core.middleware import (
    ErrorHandlingMiddleware,
    LoggingMiddleware,
    PerformanceMonitoringMiddleware,
    SecurityHeadersMiddleware,
)
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log environment variables for debugging
logger.info("=== ENVIRONMENT VARIABLES DEBUG ===")
logger.info(f"SUPABASE_URL: {os.getenv('SUPABASE_URL', 'NOT_SET')}")
logger.info(f"SUPABASE_ANON_KEY: {os.getenv('SUPABASE_ANON_KEY', 'NOT_SET')}")
logger.info(f"SUPABASE_KEY: {os.getenv('SUPABASE_KEY', 'NOT_SET')}")
logger.info(f"SUPABASE_JWT_SECRET: {os.getenv('SUPABASE_JWT_SECRET', 'NOT_SET')}")
logger.info(f"SERVICE_ROLE_KEY: {os.getenv('SERVICE_ROLE_KEY', 'NOT_SET')}")
logger.info(f"JWT_SECRET: {os.getenv('JWT_SECRET', 'NOT_SET')}")
logger.info(f"DATABASE_URL: {os.getenv('DATABASE_URL', 'NOT_SET')}")
logger.info("=== END ENVIRONMENT VARIABLES DEBUG ===")

# Create FastAPI application with enhanced OpenAPI configuration
app = FastAPI(
    title="Cedar Heights Music Academy API",
    description="""
    ## Cedar Heights Music Academy Management System API

    This API provides comprehensive management capabilities for a music academy including:

    ### Core Features
    * **Student Management** - Complete student lifecycle management with enrollment, profiles, and progress tracking
    * **Teacher Management** - Teacher profiles, availability, and student assignments
    * **Lesson Scheduling** - Advanced lesson scheduling with conflict detection and availability management
    * **Payment Processing** - Integrated payment processing with Stripe, subscription management, and billing
    * **Health Monitoring** - System health checks and performance monitoring

    ### Authentication & Security
    * JWT-based authentication via Supabase
    * Role-based access control (Admin, Teacher, Parent)
    * Comprehensive audit logging
    * Security headers and CORS protection

    ### Performance & Reliability
    * Response time monitoring (target <200ms)
    * Comprehensive error handling
    * Request/response logging
    * Database connection pooling

    ### API Standards
    * RESTful design principles
    * Consistent response formats
    * Comprehensive input validation
    * Detailed error messages
    * OpenAPI 3.0 specification
    """,
    version="1.0.0",
    contact={
        "name": "Cedar Heights Music Academy",
        "email": "support@cedarheights.academy",
    },
    license_info={
        "name": "Private License",
        "url": "https://cedarheights.academy/license",
    },
    openapi_tags=[
        {
            "name": "health",
            "description": "System health and monitoring endpoints",
        },
        {
            "name": "auth",
            "description": "Authentication and authorization endpoints",
        },
        {
            "name": "students",
            "description": "Student management operations including enrollment, profiles, and progress tracking",
        },
        {
            "name": "teachers",
            "description": "Teacher management operations including profiles, availability, and assignments",
        },
        {
            "name": "lessons",
            "description": "Lesson scheduling and management with conflict detection and status tracking",
        },
        {
            "name": "payments",
            "description": "Payment processing, subscription management, and billing operations",
        },
        {
            "name": "public",
            "description": "Public endpoints for frontend integration (no authentication required)",
        },
    ],
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Development server",
        },
        {
            "url": "https://api.cedarheights.academy",
            "description": "Production server",
        },
    ],
)

# Add comprehensive middleware stack
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(PerformanceMonitoringMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8080",
        "https://cedarheights.academy",
        "https://admin.cedarheights.academy",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Initialize auth handler and add JWT authentication middleware
auth_handler = SupabaseJWTAuth(
    supabase_url=os.getenv("SUPABASE_URL", "http://localhost:54321"),
    supabase_key=os.getenv("SUPABASE_ANON_KEY", ""),
    jwt_secret=os.getenv("SUPABASE_JWT_SECRET", ""),
)

# Initialize the auth handler for dependencies
initialize_auth_handler(auth_handler)

app.add_middleware(SupabaseJWTMiddleware, auth_handler=auth_handler)

# Include routers with proper prefixes
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(api_router, prefix="/api/v1")
app.include_router(process_router, prefix="/process")  # Legacy workflow router


@app.get("/", tags=["health"])
async def root():
    """
    Root endpoint providing API information and health status.

    Returns basic API information and confirms the service is running.
    """
    return {
        "message": "Cedar Heights Music Academy API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "api_v1": "/api/v1",
    }


@app.get("/health", tags=["health"])
async def health_check():
    """
    Basic health check endpoint.

    Returns the current health status of the API service.
    Use `/api/v1/health/detailed` for comprehensive health information.
    """
    return {
        "status": "healthy",
        "service": "cedar-heights-api",
        "version": "1.0.0",
        "timestamp": time.time(),
    }


# Global exception handler for unhandled exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "error": "An unexpected error occurred. Please try again later.",
        },
    )


# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup event handler."""
    logger.info("Cedar Heights Music Academy API starting up...")
    logger.info("✅ Authentication system initialized")
    logger.info("✅ Middleware stack configured")
    logger.info("✅ API routes registered")
    logger.info("🚀 Cedar Heights Music Academy API is ready!")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event handler."""
    logger.info("Cedar Heights Music Academy API shutting down...")
    logger.info("👋 Cedar Heights Music Academy API stopped")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
