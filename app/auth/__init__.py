"""
Authentication module for Clarity Local Runner.

This module provides Supabase JWT authentication with role-based authorization
for the workflow orchestration system.
"""

from .dependencies import (
    get_current_user,
    get_optional_user,
    initialize_auth_handler,
    require_admin,
    require_admin_or_teacher,
    require_parent,
    require_permission,
    require_role,
    require_teacher,
)
from .exceptions import AuthenticationError, AuthorizationError
from .middleware import SupabaseJWTBearer, SupabaseJWTMiddleware
from .models import AuthResponse, UserContext, UserRole
from .supabase_auth import SupabaseJWTAuth

__all__ = [
    # Models
    "UserContext",
    "UserRole",
    "AuthResponse",
    # Core auth
    "SupabaseJWTAuth",
    "SupabaseJWTMiddleware",
    "SupabaseJWTBearer",
    # Dependencies
    "get_current_user",
    "get_optional_user",
    "require_admin",
    "require_teacher",
    "require_parent",
    "require_admin_or_teacher",
    "require_role",
    "require_permission",
    "initialize_auth_handler",
    # Exceptions
    "AuthenticationError",
    "AuthorizationError",
]
