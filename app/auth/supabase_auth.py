"""
Supabase JWT authentication integration.
Handles token validation and user context extraction.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import jwt
from supabase import Client, create_client

from .exceptions import AuthenticationError, InvalidTokenError, TokenExpiredError
from .models import UserContext, UserRole

logger = logging.getLogger(__name__)


class SupabaseJWTAuth:
    """Supabase JWT authentication handler."""

    def __init__(self, supabase_url: str, supabase_key: str, jwt_secret: str):
        """Initialize Supabase JWT authentication.

        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase anon key
            jwt_secret: JWT secret for token validation
        """
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.jwt_secret = jwt_secret

        # Cache for user permissions to reduce database queries
        self._permission_cache: Dict[str, Dict[str, Any]] = {}

    async def validate_token(self, token: str) -> UserContext:
        """Validate JWT token and return user context.

        Args:
            token: JWT token to validate

        Returns:
            UserContext: Validated user context

        Raises:
            AuthenticationError: If token validation fails
            TokenExpiredError: If token has expired
            InvalidTokenError: If token is malformed
        """
        try:
            # Decode JWT token
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])

            # Extract user information
            user_id = payload.get("sub")
            email = payload.get("email")
            role = payload.get("role", "parent")  # Default to parent

            if not user_id or not email:
                raise InvalidTokenError("Token missing required claims")

            # Verify token expiration
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(
                timezone.utc
            ):
                raise TokenExpiredError("Token has expired")

            # Get user details from Supabase
            user_data = await self._get_user_details(user_id)

            # Get role from user data if available, otherwise use token role
            if user_data and "role" in user_data:
                role = user_data["role"]

            # Validate role
            try:
                user_role = UserRole(role)
            except ValueError:
                logger.warning(
                    f"Invalid role '{role}' for user {user_id}, defaulting to parent"
                )
                user_role = UserRole.PARENT

            return UserContext(
                user_id=user_id,
                email=email,
                role=user_role,
                permissions=self._get_role_permissions(user_role.value),
                user_data=user_data,
                authenticated=True,
                auth_type="supabase_jwt",
            )

        except jwt.ExpiredSignatureError:
            raise TokenExpiredError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            raise AuthenticationError("Authentication failed")

    async def _get_user_details(self, user_id: str) -> Dict[str, Any]:
        """Get user details from Supabase users table.

        Args:
            user_id: User ID to fetch details for

        Returns:
            Dict containing user details
        """
        try:
            response = (
                self.supabase.table("users").select("*").eq("id", user_id).execute()
            )
            if response.data:
                return response.data[0]
            else:
                logger.warning(f"No user data found for user_id: {user_id}")
                return {}
        except Exception as e:
            logger.warning(f"Could not fetch user details for {user_id}: {str(e)}")
            return {}

    def _get_role_permissions(self, role: str) -> list[str]:
        """Get permissions for a given role.

        Args:
            role: User role

        Returns:
            List of permissions for the role
        """
        # Check cache first
        if role in self._permission_cache:
            return self._permission_cache[role]["permissions"]

        role_permissions = {
            "admin": [
                "users:read",
                "users:write",
                "users:delete",
                "students:read",
                "students:write",
                "students:delete",
                "teachers:read",
                "teachers:write",
                "teachers:delete",
                "lessons:read",
                "lessons:write",
                "lessons:delete",
                "payments:read",
                "payments:write",
                "payments:delete",
                "reports:read",
                "reports:write",
                "system:admin",
                "system:config",
            ],
            "teacher": [
                "students:read",
                "lessons:read",
                "lessons:write",
                "payments:read",
                "profile:write",
                "schedule:read",
                "schedule:write",
            ],
            "parent": [
                "students:read",
                "lessons:read",
                "payments:read",
                "profile:write",
                "enrollment:write",
            ],
        }

        permissions = role_permissions.get(role, [])

        # Cache the permissions
        self._permission_cache[role] = {
            "permissions": permissions,
            "cached_at": datetime.now(timezone.utc),
        }

        return permissions

    def has_permission(self, user_context: UserContext, permission: str) -> bool:
        """Check if user has a specific permission.

        Args:
            user_context: User context
            permission: Permission to check

        Returns:
            True if user has permission, False otherwise
        """
        return permission in user_context.permissions

    def clear_permission_cache(self):
        """Clear the permission cache."""
        self._permission_cache.clear()
        logger.info("Permission cache cleared")
