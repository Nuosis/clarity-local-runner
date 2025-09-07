"""
Teacher models for instructor management and availability.
"""

from datetime import time
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    DECIMAL,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Teacher(Base, TimestampMixin):
    """Teacher profiles with instrument specializations."""

    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    instruments: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False)
    hourly_rate: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    max_students: Mapped[int] = mapped_column(Integer, default=30)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    bio: Mapped[Optional[str]] = mapped_column(Text)
    photo_url: Mapped[Optional[str]] = mapped_column(String(500))

    # Relationships
    user = relationship("User", back_populates="teacher_profile")
    availability = relationship(
        "TeacherAvailability", back_populates="teacher", cascade="all, delete-orphan"
    )
    students = relationship("Student", back_populates="teacher")
    timeslots = relationship("Timeslot", back_populates="teacher")
    lessons = relationship("Lesson", back_populates="teacher")

    __table_args__ = (
        CheckConstraint(
            "hourly_rate >= 30 AND hourly_rate <= 200", name="valid_hourly_rate"
        ),
        CheckConstraint(
            "max_students >= 1 AND max_students <= 50", name="valid_max_students"
        ),
    )

    def __repr__(self) -> str:
        return f"<Teacher(id={self.id}, user_id={self.user_id}, instruments={self.instruments})>"


class TeacherAvailability(Base, TimestampMixin):
    """Day-based availability definitions with lesson slots."""

    __tablename__ = "teacher_availability"

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("teachers.id", ondelete="CASCADE")
    )
    day_of_week: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="0=Sunday, 6=Saturday"
    )
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    teacher = relationship("Teacher", back_populates="availability")

    __table_args__ = (
        CheckConstraint(
            "day_of_week >= 0 AND day_of_week <= 6", name="valid_day_of_week"
        ),
        CheckConstraint("end_time > start_time", name="valid_availability_time"),
    )

    def __repr__(self) -> str:
        return f"<TeacherAvailability(teacher_id={self.teacher_id}, day={self.day_of_week}, {self.start_time}-{self.end_time})>"
