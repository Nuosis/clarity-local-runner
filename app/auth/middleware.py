"""
JWT authentication middleware for FastAPI.
Adapted from clarity-backend patterns for Supabase JWT.
"""

import logging
from typing import Awaitable, Callable, List, Optional

from fastapi import HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware

from .exceptions import AuthenticationError
from .models import UserContext
from .supabase_auth import SupabaseJWTAuth

logger = logging.getLogger(__name__)


class JWTAuthenticationError(HTTPException):
    """HTTP exception for JWT authentication failures."""

    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class SupabaseJWTBearer(HTTPBearer):
    """FastAPI security scheme for Supabase JWT authentication."""

    def __init__(self, auth_handler: SupabaseJWTAuth, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self.auth_handler = auth_handler

    async def __call__(
        self, request: Request
    ) -> Optional[HTTPAuthorizationCredentials]:
        """Validate JWT token from Authorization header."""
        credentials = await super().__call__(request)

        if not credentials:
            if self.auto_error:
                raise JWTAuthenticationError("Missing authorization header")
            return None

        try:
            # Validate token and get user context
            user_context = await self.auth_handler.validate_token(
                credentials.credentials
            )

            # Store user context in request state
            request.state.user = user_context

            return credentials

        except AuthenticationError as e:
            if self.auto_error:
                raise JWTAuthenticationError(str(e))
            return None


class SupabaseJWTMiddleware(BaseHTTPMiddleware):
    """Middleware for Supabase JWT authentication."""

    def __init__(self, app, auth_handler: SupabaseJWTAuth):
        super().__init__(app)
        self.auth_handler = auth_handler

        # Public routes that don't require authentication
        self.public_routes = {
            "/",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/metrics",
        }

        # Public path prefixes
        self.public_prefixes = (
            "/webhook/",
            "/events/",
            "/docs/",
            "/redoc/",
            "/health/",
            "/favicon",
            "/apple-touch-icon",
            "/_next/",
            "/static/",
            "/assets/",
            "/css/",
            "/js/",
            "/img/",
            "/images/",
            "/fonts/",
        )

    def _is_public_route(self, path: str) -> bool:
        """Check if route is public."""
        if path in self.public_routes:
            return True
        return path.startswith(self.public_prefixes)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request and add security headers."""
        is_public = self._is_public_route(request.url.path)

        # Add auth info to request state
        request.state.auth_info = {
            "auth_type": "supabase_jwt",
            "is_public_route": is_public,
            "path": request.url.path,
        }

        # Initialize user context as None
        request.state.user = None

        # Handle CORS preflight requests
        if request.method == "OPTIONS":
            try:
                response = await call_next(request)
            except Exception as e:
                logger.error(f"Error processing CORS preflight: {e}")
                from fastapi import Response

                response = Response(status_code=200)
        else:
            try:
                response = await call_next(request)
            except Exception as e:
                logger.error(f"Request processing error: {e}")
                raise

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY" if not is_public else "SAMEORIGIN"

        if not is_public:
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        # Add CORS headers for development
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = (
            "GET, POST, PUT, DELETE, OPTIONS"
        )
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"

        return response


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Simplified authentication middleware for specific routes."""

    def __init__(
        self,
        app,
        auth_handler: SupabaseJWTAuth,
        protected_prefixes: Optional[List[str]] = None,
    ):
        super().__init__(app)
        self.auth_handler = auth_handler
        self.protected_prefixes = protected_prefixes or ["/api/v1/"]

    def _requires_auth(self, path: str) -> bool:
        """Check if path requires authentication."""
        return any(path.startswith(prefix) for prefix in self.protected_prefixes)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request with authentication check."""
        if self._requires_auth(request.url.path):
            # Extract token from Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                raise JWTAuthenticationError("Missing or invalid authorization header")

            token = auth_header.split(" ")[1]

            try:
                # Validate token and set user context
                user_context = await self.auth_handler.validate_token(token)
                request.state.user = user_context
            except AuthenticationError as e:
                raise JWTAuthenticationError(str(e))

        response = await call_next(request)
        return response
