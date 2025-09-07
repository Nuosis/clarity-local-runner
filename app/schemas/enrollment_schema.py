"""
Enrollment workflow event schemas for student registration.
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, validator


class EnrollmentEventSchema(BaseModel):
    """Schema for student enrollment workflow events."""

    # Student Information
    student_first_name: str = Field(..., min_length=1, max_length=100)
    student_last_name: str = Field(..., min_length=1, max_length=100)
    student_date_of_birth: date
    student_email: Optional[str] = Field(None, max_length=255)

    # Parent Information
    parent_first_name: str = Field(..., min_length=1, max_length=100)
    parent_last_name: str = Field(..., min_length=1, max_length=100)
    parent_email: str = Field(..., max_length=255)
    parent_phone: Optional[str] = Field(None, max_length=20)

    # Lesson Information
    instrument: str = Field(..., description="Instrument to learn")
    skill_level: str = Field(default="beginner", description="Student skill level")
    lesson_rate: Decimal = Field(
        ..., ge=30, le=200, description="Lesson rate per session"
    )
    preferred_schedule: Optional[str] = Field(
        None, description="Preferred lesson schedule"
    )

    # Payment Information
    payment_method_id: Optional[str] = Field(
        None, description="Stripe payment method ID"
    )
    billing_address: Optional[dict] = Field(
        None, description="Billing address information"
    )

    # Additional Information
    notes: Optional[str] = Field(None, description="Additional notes or requirements")
    referral_source: Optional[str] = Field(None, description="How they heard about us")

    @validator("instrument")
    def validate_instrument(cls, v):
        """Validate instrument is supported."""
        allowed_instruments = ["piano", "guitar", "bass"]
        if v.lower() not in allowed_instruments:
            raise ValueError(
                f"Instrument must be one of: {', '.join(allowed_instruments)}"
            )
        return v.lower()

    @validator("skill_level")
    def validate_skill_level(cls, v):
        """Validate skill level is supported."""
        allowed_levels = ["beginner", "intermediate", "advanced"]
        if v.lower() not in allowed_levels:
            raise ValueError(f"Skill level must be one of: {', '.join(allowed_levels)}")
        return v.lower()

    @validator("student_date_of_birth")
    def validate_student_age(cls, v):
        """Validate student is at least 5 years old."""
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 5:
            raise ValueError("Student must be at least 5 years old")
        return v

    @validator("parent_email")
    def validate_parent_email(cls, v):
        """Validate parent email format."""
        if "@" not in v or "." not in v:
            raise ValueError("Invalid email format")
        return v.lower()


class EnrollmentResultSchema(BaseModel):
    """Schema for enrollment workflow results."""

    success: bool
    student_id: Optional[int] = None
    parent_user_id: Optional[int] = None
    teacher_id: Optional[int] = None
    demo_lesson_id: Optional[int] = None
    stripe_customer_id: Optional[str] = None
    error_message: Optional[str] = None
    enrollment_date: Optional[date] = None
    next_steps: Optional[list] = None
