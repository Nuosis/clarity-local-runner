"""
User-related Pydantic schemas with validation.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, validator


class UserRole(str, Enum):
    """Valid user roles."""

    ADMIN = "admin"
    TEACHER = "teacher"
    PARENT = "parent"


class UserBase(BaseModel):
    """Base user schema with common fields."""

    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, pattern=r"^\+?1?[0-9]{10}$")
    role: UserRole
    is_active: bool = True


class UserCreate(UserBase):
    """Schema for creating a new user."""

    supabase_user_id: UUID
    user_metadata: dict = Field(default_factory=dict)

    @validator("phone")
    def validate_phone(cls, v):
        if v and not v.replace("+", "").replace("-", "").replace(" ", "").isdigit():
            raise ValueError(
                "Phone number must contain only digits, spaces, hyphens, and plus sign"
            )
        return v


class UserUpdate(BaseModel):
    """Schema for updating user information."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, pattern=r"^\+?1?[0-9]{10}$")
    is_active: Optional[bool] = None
    user_metadata: Optional[dict] = None


class UserResponse(UserBase):
    """Schema for user responses."""

    id: int
    supabase_user_id: UUID
    user_metadata: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str = Field(..., min_length=8)


class UserProfile(BaseModel):
    """Simplified user profile for public display."""

    id: int
    first_name: str
    last_name: str
    role: UserRole
    is_active: bool

    class Config:
        from_attributes = True
