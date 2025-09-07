"""
Authentication-related Pydantic models.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class UserRole(str, Enum):
    """User roles in the Cedar Heights Music Academy system."""

    ADMIN = "admin"
    TEACHER = "teacher"
    PARENT = "parent"


class UserContext(BaseModel):
    """User authentication context."""

    user_id: str = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User email address")
    role: UserRole = Field(..., description="User role")
    permissions: List[str] = Field(default_factory=list, description="User permissions")
    user_data: Dict[str, Any] = Field(
        default_factory=dict, description="Additional user data"
    )
    authenticated: bool = Field(default=True, description="Authentication status")
    auth_type: str = Field(default="supabase_jwt", description="Authentication type")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class AuthResponse(BaseModel):
    """Authentication response model."""

    success: bool = Field(..., description="Authentication success status")
    user: Optional[UserContext] = Field(None, description="User context if successful")
    error: Optional[str] = Field(None, description="Error message if failed")
    token: Optional[str] = Field(None, description="JWT token if successful")


class LoginRequest(BaseModel):
    """Login request model."""

    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class TokenRefreshRequest(BaseModel):
    """Token refresh request model."""

    refresh_token: str = Field(..., description="Refresh token")


class PasswordResetRequest(BaseModel):
    """Password reset request model."""

    email: str = Field(..., description="User email address")


class PasswordUpdateRequest(BaseModel):
    """Password update request model."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., description="New password")


class UserProfileUpdate(BaseModel):
    """User profile update model."""

    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    phone: Optional[str] = Field(None, description="Phone number")
