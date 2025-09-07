"""
Student-related Pydantic schemas with validation.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, validator

from .common import PaginatedResponse


class SkillLevel(str, Enum):
    """Valid skill levels."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class Instrument(str, Enum):
    """Valid instruments."""

    PIANO = "piano"
    GUITAR = "guitar"
    BASS = "bass"


class StudentBase(BaseModel):
    """Base student schema with common fields."""

    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    date_of_birth: date
    instrument: Instrument
    skill_level: SkillLevel = SkillLevel.BEGINNER
    lesson_rate: Decimal = Field(..., ge=0, decimal_places=2)
    enrollment_date: date
    is_active: bool = True
    notes: Optional[str] = Field(None, max_length=1000)

    @validator("date_of_birth")
    def validate_age(cls, v):
        """Validate student is at least 5 years old."""
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 5:
            raise ValueError("Student must be at least 5 years old")
        return v

    @property
    def age(self) -> int:
        """Calculate current age."""
        today = date.today()
        return (
            today.year
            - self.date_of_birth.year
            - (
                (today.month, today.day)
                < (self.date_of_birth.month, self.date_of_birth.day)
            )
        )


class StudentCreate(StudentBase):
    """Schema for creating a new student."""

    parent_id: int = Field(..., gt=0)
    teacher_id: Optional[int] = Field(None, gt=0)


class StudentUpdate(BaseModel):
    """Schema for updating student information."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    skill_level: Optional[SkillLevel] = None
    lesson_rate: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    is_active: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=1000)
    teacher_id: Optional[int] = Field(None, gt=0)


class ParentInfo(BaseModel):
    """Parent information for student responses."""

    id: int
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None

    class Config:
        from_attributes = True


class TeacherInfo(BaseModel):
    """Teacher information for student responses."""

    id: int
    first_name: str
    last_name: str
    email: EmailStr
    instruments: List[Instrument]

    class Config:
        from_attributes = True


class StudentResponse(StudentBase):
    """Schema for student responses."""

    id: int
    parent: Optional[ParentInfo] = None
    teacher: Optional[TeacherInfo] = None
    stripe_customer_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class StudentListItem(BaseModel):
    """Simplified student info for list responses."""

    id: int
    first_name: str
    last_name: str
    email: Optional[EmailStr] = None
    age: int
    instrument: Instrument
    skill_level: SkillLevel
    lesson_rate: Decimal
    enrollment_date: date
    is_active: bool
    parent: Optional[ParentInfo] = None
    teacher: Optional[TeacherInfo] = None
    stripe_customer_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class StudentListResponse(PaginatedResponse):
    """Response for student list endpoint."""

    students: List[StudentListItem]


class StudentQueryParams(BaseModel):
    """Query parameters for student list endpoint."""

    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(20, ge=1, le=100, description="Items per page")
    teacher_id: Optional[int] = Field(None, gt=0, description="Filter by teacher ID")
    instrument: Optional[Instrument] = Field(None, description="Filter by instrument")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    search: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Search by name"
    )


class StudentProfile(BaseModel):
    """Simplified student profile for public display."""

    id: int
    first_name: str
    last_name: str
    instrument: Instrument
    skill_level: SkillLevel
    is_active: bool

    class Config:
        from_attributes = True
