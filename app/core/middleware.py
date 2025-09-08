"""
Middleware for Cedar Heights Music Academy API.
"""

import logging
import time
import uuid
from typing import Callable, Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from schemas.common import APIResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware

from .exceptions import (
    # AuthenticationError,
    # AuthorizationError,
    # BusinessRuleError,
    CedarHeightsException,
    # ConflictError,
    # DatabaseError,
    # ExternalServiceError,
    # NotFoundError,
    # PaymentError,
    # RateLimitError,
    # SchedulingError,
    # WorkflowError,
)

# from .exceptions import (
#     ValidationError as CustomValidationError,
# )

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for handling exceptions and returning standardized error responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            return await self._handle_exception(request, exc)

    async def _handle_exception(self, request: Request, exc: Exception) -> JSONResponse:
        """Handle different types of exceptions and return appropriate responses."""

        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

        # Log the exception
        logger.error(
            f"Exception in request {request_id}: {type(exc).__name__}: {str(exc)}",
            exc_info=True,
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "exception_type": type(exc).__name__,
            },
        )

        # Handle custom exceptions
        if isinstance(exc, CedarHeightsException):
            return self._create_error_response(
                message=exc.message,
                error_code=exc.error_code,
                status_code=exc.status_code,
                request_id=request_id,
                details=exc.details,
            )

        # Handle Pydantic validation errors
        if isinstance(exc, ValidationError):
            field_errors = []
            for error in exc.errors():
                field_errors.append(
                    {
                        "field": ".".join(str(loc) for loc in error["loc"]),
                        "code": error["type"],
                        "message": error["msg"],
                    }
                )

            return self._create_error_response(
                message="Validation failed",
                error_code="VALIDATION_ERROR",
                status_code=422,
                request_id=request_id,
                field_errors=field_errors,
            )

        # Handle SQLAlchemy database errors
        if isinstance(exc, SQLAlchemyError):
            return self._create_error_response(
                message="Database operation failed",
                error_code="DATABASE_ERROR",
                status_code=500,
                request_id=request_id,
            )

        # Handle generic exceptions
        return self._create_error_response(
            message="Internal server error",
            error_code="INTERNAL_ERROR",
            status_code=500,
            request_id=request_id,
        )

    def _create_error_response(
        self,
        message: str,
        error_code: str,
        status_code: int,
        request_id: str,
        details: Optional[dict] = None,
        field_errors: Optional[list] = None,
    ) -> JSONResponse:
        """Create a standardized error response."""

        errors = []

        # Add field errors if present
        if field_errors:
            errors.extend(field_errors)
        else:
            errors.append({"field": None, "code": error_code, "message": message})

        response_data = APIResponse(
            success=False,
            data=None,
            message=message,
            errors=errors,
            metadata={
                "timestamp": time.time(),
                "request_id": request_id,
                "error_details": details or {},
            },
        )

        return JSONResponse(status_code=status_code, content=response_data.dict())


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Log request
        start_time = time.time()

        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            },
        )

        # Process request
        response = await call_next(request)

        # Calculate execution time
        execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds

        # Log response
        logger.info(
            f"Request completed: {request.method} {request.url.path} - {response.status_code}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "execution_time_ms": execution_time,
            },
        )

        # Add request metadata to response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Execution-Time"] = str(execution_time)

        return response


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for monitoring API performance."""

    def __init__(self, app, slow_request_threshold: float = 200.0):
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold  # milliseconds

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate execution time
        execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds

        # Log slow requests
        if execution_time > self.slow_request_threshold:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.warning(
                f"Slow request detected: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "execution_time_ms": execution_time,
                    "threshold_ms": self.slow_request_threshold,
                    "status_code": response.status_code,
                },
            )

        # Add performance headers
        response.headers["X-Response-Time"] = f"{execution_time:.2f}ms"

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy - Allow Swagger UI resources
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "connect-src 'self'"
        )
        response.headers["Content-Security-Policy"] = csp_policy

        return response


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware."""

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}  # In production, use Redis or similar
        self.window_start = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        # Reset window if needed
        if (
            client_ip not in self.window_start
            or current_time - self.window_start[client_ip] >= 60
        ):
            self.window_start[client_ip] = current_time
            self.request_counts[client_ip] = 0

        # Check rate limit
        self.request_counts[client_ip] += 1
        if self.request_counts[client_ip] > self.requests_per_minute:
            logger.warning(
                f"Rate limit exceeded for IP: {client_ip}",
                extra={
                    "client_ip": client_ip,
                    "requests_count": self.request_counts[client_ip],
                    "limit": self.requests_per_minute,
                },
            )

            return JSONResponse(
                status_code=429,
                content=APIResponse(
                    success=False,
                    data=None,
                    message="Rate limit exceeded",
                    errors=[
                        {
                            "field": None,
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": f"Too many requests. Limit: {self.requests_per_minute} per minute",
                        }
                    ],
                ).dict(),
            )

        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, self.requests_per_minute - self.request_counts[client_ip])
        )
        response.headers["X-RateLimit-Reset"] = str(
            int(self.window_start[client_ip] + 60)
        )

        return response


class CORSMiddleware(BaseHTTPMiddleware):
    """Custom CORS middleware with enhanced logging."""

    def __init__(
        self,
        app,
        allow_origins: list = None,
        allow_methods: list = None,
        allow_headers: list = None,
        allow_credentials: bool = True,
    ):
        super().__init__(app)
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or [
            "GET",
            "POST",
            "PUT",
            "DELETE",
            "OPTIONS",
        ]
        self.allow_headers = allow_headers or ["*"]
        self.allow_credentials = allow_credentials

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        origin = request.headers.get("origin")

        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response()
            self._add_cors_headers(response, origin)
            return response

        # Process request
        response = await call_next(request)

        # Add CORS headers to response
        self._add_cors_headers(response, origin)

        return response

    def _add_cors_headers(self, response: Response, origin: Optional[str] = None):
        """Add CORS headers to response."""
        if origin and (self.allow_origins == ["*"] or origin in self.allow_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
        elif self.allow_origins == ["*"]:
            response.headers["Access-Control-Allow-Origin"] = "*"

        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)

        if self.allow_credentials:
            response.headers["Access-Control-Allow-Credentials"] = "true"
