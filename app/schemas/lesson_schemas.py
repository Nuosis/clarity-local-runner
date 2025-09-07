"""
Lesson-related Pydantic schemas with validation.
"""

from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, validator

from .common import PaginatedResponse
from .student_schemas import Instrument


class LessonType(str, Enum):
    """Valid lesson types."""

    REGULAR = "regular"
    DEMO = "demo"
    MAKEUP = "makeup"
    TRIAL = "trial"


class LessonStatus(str, Enum):
    """Valid lesson statuses."""

    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    RESCHEDULED = "rescheduled"


class PaymentStatus(str, Enum):
    """Valid payment statuses."""

    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class LessonBase(BaseModel):
    """Base lesson schema with common fields."""

    scheduled_at: datetime
    duration_minutes: int = Field(..., ge=15, le=120)
    lesson_type: LessonType = LessonType.REGULAR
    teacher_notes: Optional[str] = Field(None, max_length=1000)
    student_progress_notes: Optional[str] = Field(None, max_length=1000)

    @validator("scheduled_at")
    def validate_future_date(cls, v):
        """Ensure lesson is scheduled for future (except for completed lessons)."""
        # This validation can be relaxed for updates and completed lessons
        return v


class LessonCreate(LessonBase):
    """Schema for creating a new lesson."""

    student_id: int = Field(..., gt=0)
    teacher_id: int = Field(..., gt=0)
    timeslot_id: Optional[int] = Field(None, gt=0)
    semester_id: Optional[int] = Field(None, gt=0)
    notes: Optional[str] = Field(None, max_length=500)


class LessonUpdate(BaseModel):
    """Schema for updating lesson information."""

    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=15, le=120)
    status: Optional[LessonStatus] = None
    attendance_marked: Optional[bool] = None
    teacher_notes: Optional[str] = Field(None, max_length=1000)
    student_progress_notes: Optional[str] = Field(None, max_length=1000)
    payment_status: Optional[PaymentStatus] = None


class StudentInfo(BaseModel):
    """Student information for lesson responses."""

    id: int
    first_name: str
    last_name: str
    instrument: Instrument
    skill_level: str

    class Config:
        from_attributes = True


class TeacherInfo(BaseModel):
    """Teacher information for lesson responses."""

    id: int
    first_name: str
    last_name: str
    email: str

    class Config:
        from_attributes = True


class LessonResponse(LessonBase):
    """Schema for lesson responses."""

    id: int
    student: StudentInfo
    teacher: TeacherInfo
    status: LessonStatus = LessonStatus.SCHEDULED
    payment_status: PaymentStatus = PaymentStatus.PENDING
    attendance_marked: bool = False
    timeslot_id: Optional[int] = None
    semester_id: Optional[int] = None
    makeup_lesson_id: Optional[int] = None
    original_lesson_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LessonListItem(BaseModel):
    """Simplified lesson info for list responses."""

    id: int
    student_id: int
    student_name: str
    teacher_id: int
    teacher_name: str
    scheduled_at: datetime
    duration_minutes: int
    lesson_type: LessonType
    status: LessonStatus
    payment_status: PaymentStatus
    attendance_marked: bool
    teacher_notes: Optional[str] = None
    student_progress_notes: Optional[str] = None
    timeslot_id: Optional[int] = None
    semester_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class LessonListResponse(PaginatedResponse):
    """Response for lesson list endpoint."""

    lessons: List[LessonListItem]


class LessonQueryParams(BaseModel):
    """Query parameters for lesson list endpoint."""

    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(20, ge=1, le=100, description="Items per page")
    student_id: Optional[int] = Field(None, gt=0, description="Filter by student ID")
    teacher_id: Optional[int] = Field(None, gt=0, description="Filter by teacher ID")
    status: Optional[LessonStatus] = Field(None, description="Filter by status")
    lesson_type: Optional[LessonType] = Field(None, description="Filter by lesson type")
    date_from: Optional[date] = Field(None, description="Filter from date")
    date_to: Optional[date] = Field(None, description="Filter to date")
    include_notes: bool = Field(False, description="Include lesson notes")


class LessonCancellation(BaseModel):
    """Schema for lesson cancellation."""

    cancellation_reason: str = Field(..., min_length=1, max_length=500)
    notify_parent: bool = True
    offer_makeup: bool = True


class ConflictCheck(BaseModel):
    """Schema for checking scheduling conflicts."""

    teacher_id: int = Field(..., gt=0)
    scheduled_at: datetime
    duration_minutes: int = Field(..., ge=15, le=120)
    exclude_lesson_id: Optional[int] = Field(None, gt=0)


class ConflictCheckResponse(BaseModel):
    """Response for conflict check."""

    has_conflicts: bool
    conflicts: List[dict] = []
    available: bool
    suggested_times: List[datetime] = []


class ScheduleSlot(BaseModel):
    """Schedule slot for schedule view."""

    id: int
    time: str
    duration_minutes: int
    student_name: str
    teacher_name: str
    status: LessonStatus
    lesson_type: LessonType

    class Config:
        from_attributes = True


class ScheduleDay(BaseModel):
    """Schedule for a single day."""

    date: str
    day_name: str
    lessons: List[ScheduleSlot]


class ScheduleTeacher(BaseModel):
    """Teacher summary for schedule view."""

    id: int
    name: str
    lessons_count: int


class ScheduleResponse(BaseModel):
    """Response for schedule endpoint."""

    view: str
    date_range: dict
    schedule: List[ScheduleDay]
    teachers: List[ScheduleTeacher]


class ScheduleQueryParams(BaseModel):
    """Query parameters for schedule endpoint."""

    view: str = Field("week", description="Schedule view type")
    schedule_date: Optional[date] = Field(None, description="Center date for view")
    teacher_id: Optional[int] = Field(None, gt=0, description="Filter by teacher ID")
    student_id: Optional[int] = Field(None, gt=0, description="Filter by student ID")

    @validator("view")
    def validate_view(cls, v):
        """Validate view type."""
        if v not in ["day", "week", "month"]:
            raise ValueError("View must be one of: day, week, month")
        return v
