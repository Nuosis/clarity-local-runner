"""
Custom authentication and authorization exceptions.
"""

from typing import Optional


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    def __init__(
        self, message: str = "Authentication failed", details: Optional[str] = None
    ):
        self.message = message
        self.details = details
        super().__init__(self.message)


class AuthorizationError(Exception):
    """Raised when authorization fails."""

    def __init__(
        self, message: str = "Access denied", required_permission: Optional[str] = None
    ):
        self.message = message
        self.required_permission = required_permission
        super().__init__(self.message)


class TokenExpiredError(AuthenticationError):
    """Raised when JWT token has expired."""

    def __init__(self, message: str = "Token has expired"):
        super().__init__(message)


class InvalidTokenError(AuthenticationError):
    """Raised when JWT token is invalid."""

    def __init__(self, message: str = "Invalid token"):
        super().__init__(message)
