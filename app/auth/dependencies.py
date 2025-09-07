"""
FastAPI dependencies for authentication and authorization.
"""

from typing import List, Optional

from fastapi import Depends, HTTPException, Request, status

from .exceptions import AuthenticationError, AuthorizationError
from .middleware import SupabaseJWTBearer
from .models import UserContext, UserRole
from .supabase_auth import SupabaseJWTAuth

# Global auth handler (initialized in main.py)
_auth_handler: Optional[SupabaseJWTAuth] = None


def initialize_auth_handler(auth_handler: SupabaseJWTAuth):
    """Initialize the global auth handler."""
    global _auth_handler
    _auth_handler = auth_handler


def get_auth_handler() -> SupabaseJWTAuth:
    """Get the initialized auth handler."""
    if _auth_handler is None:
        raise RuntimeError("Auth handler not initialized")
    return _auth_handler


# Security scheme
def get_jwt_bearer() -> SupabaseJWTBearer:
    """Get JWT bearer security scheme."""
    return SupabaseJWTBearer(get_auth_handler())


# Authentication dependencies
async def get_current_user(request: Request) -> UserContext:
    """Get current authenticated user."""
    if not hasattr(request.state, "user") or request.state.user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return request.state.user


async def get_optional_user(request: Request) -> Optional[UserContext]:
    """Get current user if authenticated, None otherwise."""
    return getattr(request.state, "user", None)


# Role-based dependencies
def require_role(required_role: UserRole):
    """Dependency factory for role-based access control."""

    async def role_checker(
        user: UserContext = Depends(get_current_user),
    ) -> UserContext:
        if user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role.value}",
            )
        return user

    return role_checker


def require_permission(required_permission: str):
    """Dependency factory for permission-based access control."""

    async def permission_checker(
        user: UserContext = Depends(get_current_user),
    ) -> UserContext:
        if required_permission not in user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required permission: {required_permission}",
            )
        return user

    return permission_checker


def require_any_permission(required_permissions: List[str]):
    """Dependency factory for checking if user has any of the required permissions."""

    async def permission_checker(
        user: UserContext = Depends(get_current_user),
    ) -> UserContext:
        if not any(perm in user.permissions for perm in required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required one of: {', '.join(required_permissions)}",
            )
        return user

    return permission_checker


def require_all_permissions(required_permissions: List[str]):
    """Dependency factory for checking if user has all required permissions."""

    async def permission_checker(
        user: UserContext = Depends(get_current_user),
    ) -> UserContext:
        missing_permissions = [
            perm for perm in required_permissions if perm not in user.permissions
        ]
        if missing_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Missing permissions: {', '.join(missing_permissions)}",
            )
        return user

    return permission_checker


# Convenience dependencies
require_admin = require_role(UserRole.ADMIN)
require_teacher = require_role(UserRole.TEACHER)
require_parent = require_role(UserRole.PARENT)


def require_admin_or_teacher():
    """Require admin or teacher role."""

    async def checker(user: UserContext = Depends(get_current_user)) -> UserContext:
        if user.role not in [UserRole.ADMIN, UserRole.TEACHER]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Admin or teacher role required",
            )
        return user

    return checker


def require_admin_or_owner(user_id_field: str = "user_id"):
    """Require admin role or ownership of the resource."""

    async def checker(
        request: Request, user: UserContext = Depends(get_current_user)
    ) -> UserContext:
        # Admin can access anything
        if user.role == UserRole.ADMIN:
            return user

        # Check if user owns the resource
        path_params = request.path_params
        query_params = request.query_params

        # Try to get user_id from path params first, then query params
        resource_user_id = path_params.get(user_id_field) or query_params.get(
            user_id_field
        )

        if resource_user_id and resource_user_id == user.user_id:
            return user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role or resource ownership required",
        )

    return checker


def require_student_access():
    """Require access to student data (admin, teacher, or parent of the student)."""

    async def checker(
        request: Request, user: UserContext = Depends(get_current_user)
    ) -> UserContext:
        # Admin can access all students
        if user.role == UserRole.ADMIN:
            return user

        # Teachers can access their assigned students (would need additional logic)
        if user.role == UserRole.TEACHER:
            # TODO: Add logic to check if teacher is assigned to the student
            return user

        # Parents can access their own children
        if user.role == UserRole.PARENT:
            # TODO: Add logic to check if parent owns the student
            return user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Insufficient permissions for student data",
        )

    return checker


# Utility functions
async def verify_token_manually(token: str) -> UserContext:
    """Manually verify a JWT token (useful for websockets or custom auth flows)."""
    try:
        auth_handler = get_auth_handler()
        return await auth_handler.validate_token(token)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


def check_permission(user: UserContext, permission: str) -> bool:
    """Check if user has a specific permission."""
    return permission in user.permissions


def check_role(user: UserContext, role: UserRole) -> bool:
    """Check if user has a specific role."""
    return user.role == role


def is_admin(user: UserContext) -> bool:
    """Check if user is an admin."""
    return user.role == UserRole.ADMIN


def is_teacher(user: UserContext) -> bool:
    """Check if user is a teacher."""
    return user.role == UserRole.TEACHER


def is_parent(user: UserContext) -> bool:
    """Check if user is a parent."""
    return user.role == UserRole.PARENT
