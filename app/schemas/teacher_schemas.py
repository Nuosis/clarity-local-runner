"""
Teacher-related Pydantic schemas with validation.
"""

from datetime import datetime, time
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, validator

from .common import PaginatedResponse
from .student_schemas import Instrument


class DayOfWeek(int, Enum):
    """Days of the week."""

    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    SUNDAY = 0


class TeacherBase(BaseModel):
    """Base teacher schema with common fields."""

    instruments: List[Instrument] = Field(..., min_length=1)
    hourly_rate: Decimal = Field(..., ge=0, decimal_places=2)
    max_students: int = Field(..., ge=1, le=100)
    is_available: bool = True
    bio: Optional[str] = Field(None, max_length=1000)
    photo_url: Optional[str] = Field(None, max_length=500)

    @validator("instruments")
    def validate_instruments(cls, v):
        """Ensure no duplicate instruments."""
        if len(v) != len(set(v)):
            raise ValueError("Duplicate instruments not allowed")
        return v


class TeacherCreate(TeacherBase):
    """Schema for creating a new teacher."""

    user_id: int = Field(..., gt=0)


class TeacherUpdate(BaseModel):
    """Schema for updating teacher information."""

    instruments: Optional[List[Instrument]] = Field(None, min_length=1)
    hourly_rate: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    max_students: Optional[int] = Field(None, ge=1, le=100)
    is_available: Optional[bool] = None
    bio: Optional[str] = Field(None, max_length=1000)
    photo_url: Optional[str] = Field(None, max_length=500)

    @validator("instruments")
    def validate_instruments(cls, v):
        """Ensure no duplicate instruments."""
        if v and len(v) != len(set(v)):
            raise ValueError("Duplicate instruments not allowed")
        return v


class StudentInfo(BaseModel):
    """Student information for teacher responses."""

    id: int
    first_name: str
    last_name: str
    instrument: Instrument
    skill_level: str

    class Config:
        from_attributes = True


class AvailabilitySlot(BaseModel):
    """Teacher availability slot."""

    id: int
    day_of_week: DayOfWeek
    day_name: str
    start_time: time
    end_time: time
    duration_minutes: int
    is_recurring: bool
    is_active: bool
    student_id: Optional[int] = None
    student_name: Optional[str] = None
    is_available: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TeacherResponse(TeacherBase):
    """Schema for teacher responses."""

    id: int
    user_id: int
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    current_students: int = 0
    students: Optional[List[StudentInfo]] = None
    availability: Optional[List[AvailabilitySlot]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class TeacherListItem(BaseModel):
    """Simplified teacher info for list responses."""

    id: int
    user_id: int
    first_name: str
    last_name: str
    email: EmailStr
    instruments: List[Instrument]
    hourly_rate: Decimal
    max_students: int
    current_students: int
    is_available: bool
    bio: Optional[str] = None
    photo_url: Optional[str] = None
    availability: Optional[List[AvailabilitySlot]] = None
    created_at: datetime

    class Config:
        from_attributes = True

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class TeacherListResponse(PaginatedResponse):
    """Response for teacher list endpoint."""

    teachers: List[TeacherListItem]


class TeacherQueryParams(BaseModel):
    """Query parameters for teacher list endpoint."""

    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(20, ge=1, le=100, description="Items per page")
    instrument: Optional[Instrument] = Field(None, description="Filter by instrument")
    is_available: Optional[bool] = Field(None, description="Filter by availability")
    include_availability: bool = Field(False, description="Include availability slots")


class AvailabilitySlotCreate(BaseModel):
    """Schema for creating availability slot."""

    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    is_recurring: bool = True
    is_active: bool = True

    @validator("end_time")
    def validate_time_range(cls, v, values):
        """Ensure end time is after start time."""
        if "start_time" in values and v <= values["start_time"]:
            raise ValueError("End time must be after start time")
        return v


class AvailabilitySlotUpdate(BaseModel):
    """Schema for updating availability slot."""

    start_time: Optional[time] = None
    end_time: Optional[time] = None
    is_active: Optional[bool] = None
    student_id: Optional[int] = Field(None, gt=0)

    @validator("end_time")
    def validate_time_range(cls, v, values):
        """Ensure end time is after start time."""
        if (
            v
            and "start_time" in values
            and values["start_time"]
            and v <= values["start_time"]
        ):
            raise ValueError("End time must be after start time")
        return v


class AvailabilityQueryParams(BaseModel):
    """Query parameters for availability endpoints."""

    day_of_week: Optional[DayOfWeek] = Field(None, description="Filter by day of week")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    include_bookings: bool = Field(False, description="Include current bookings")


class WeeklyScheduleSlot(BaseModel):
    """Weekly schedule slot."""

    id: int
    start_time: time
    end_time: time
    is_available: bool
    student_id: Optional[int] = None
    student_name: Optional[str] = None

    class Config:
        from_attributes = True


class WeeklyScheduleDay(BaseModel):
    """Weekly schedule for a single day."""

    date: str
    day_name: str
    day_of_week: DayOfWeek
    slots: List[WeeklyScheduleSlot]


class WeeklyScheduleSummary(BaseModel):
    """Weekly schedule summary."""

    total_slots: int
    available_slots: int
    booked_slots: int
    availability_percentage: float


class WeeklyScheduleResponse(BaseModel):
    """Response for weekly schedule endpoint."""

    teacher_id: int
    teacher_name: str
    week_start: str
    week_end: str
    schedule: List[WeeklyScheduleDay]
    summary: WeeklyScheduleSummary


class WeeklyScheduleQueryParams(BaseModel):
    """Query parameters for weekly schedule endpoint."""

    week_start: Optional[str] = Field(None, description="Start of week (YYYY-MM-DD)")
    include_booked: bool = Field(False, description="Include booked slots")


class TeacherProfile(BaseModel):
    """Simplified teacher profile for public display."""

    id: int
    first_name: str
    last_name: str
    instruments: List[Instrument]
    bio: Optional[str] = None
    photo_url: Optional[str] = None
    is_available: bool

    class Config:
        from_attributes = True
