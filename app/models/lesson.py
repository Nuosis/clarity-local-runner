"""
Lesson scheduling and management models.
"""

from datetime import datetime, time
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Timeslot(Base, TimestampMixin):
    """Available teaching slots with status tracking."""

    __tablename__ = "timeslots"

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("teachers.id", ondelete="CASCADE")
    )
    day_of_week: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="0=Sunday, 6=Saturday"
    )
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[str] = mapped_column(String(20), default="available")
    student_id: Mapped[Optional[int]] = mapped_column(ForeignKey("students.id"))
    semester_id: Mapped[Optional[int]] = mapped_column(ForeignKey("semesters.id"))
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    teacher = relationship("Teacher", back_populates="timeslots")
    student = relationship("Student", back_populates="timeslots")
    semester = relationship("Semester", back_populates="timeslots")
    lessons = relationship("Lesson", back_populates="timeslot")

    __table_args__ = (
        CheckConstraint(
            "day_of_week >= 0 AND day_of_week <= 6", name="valid_day_of_week"
        ),
        CheckConstraint(
            "duration_minutes >= 15 AND duration_minutes <= 120", name="valid_duration"
        ),
        CheckConstraint(
            "status IN ('available', 'pending', 'confirmed', 'blocked')",
            name="valid_status",
        ),
        CheckConstraint("end_time > start_time", name="valid_timeslot_duration"),
    )

    def __repr__(self) -> str:
        return f"<Timeslot(id={self.id}, teacher_id={self.teacher_id}, day={self.day_of_week}, {self.start_time}-{self.end_time})>"


class Lesson(Base, TimestampMixin):
    """Individual lesson instances with attendance and notes."""

    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE")
    )
    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("teachers.id", ondelete="CASCADE")
    )
    timeslot_id: Mapped[Optional[int]] = mapped_column(ForeignKey("timeslots.id"))
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    lesson_type: Mapped[str] = mapped_column(String(20), default="regular")
    status: Mapped[str] = mapped_column(String(20), default="scheduled")
    payment_status: Mapped[str] = mapped_column(String(20), default="pending")
    attendance_marked: Mapped[bool] = mapped_column(Boolean, default=False)
    teacher_notes: Mapped[Optional[str]] = mapped_column(Text)
    student_progress_notes: Mapped[Optional[str]] = mapped_column(Text)
    makeup_lesson_id: Mapped[Optional[int]] = mapped_column(ForeignKey("lessons.id"))
    original_lesson_id: Mapped[Optional[int]] = mapped_column(ForeignKey("lessons.id"))
    semester_id: Mapped[Optional[int]] = mapped_column(ForeignKey("semesters.id"))

    # Relationships
    student = relationship("Student", back_populates="lessons")
    teacher = relationship("Teacher", back_populates="lessons")
    timeslot = relationship("Timeslot", back_populates="lessons")
    semester = relationship("Semester", back_populates="lessons")
    makeup_lesson = relationship(
        "Lesson", remote_side=[id], foreign_keys=[makeup_lesson_id]
    )
    original_lesson = relationship(
        "Lesson", remote_side=[id], foreign_keys=[original_lesson_id]
    )
    payments = relationship("Payment", back_populates="lesson")
    messages = relationship("Message", back_populates="lesson")
    notifications = relationship("Notification", back_populates="lesson")

    __table_args__ = (
        CheckConstraint(
            "duration_minutes >= 15 AND duration_minutes <= 120",
            name="valid_lesson_duration",
        ),
        CheckConstraint(
            "lesson_type IN ('demo', 'regular', 'makeup')", name="valid_lesson_type"
        ),
        CheckConstraint(
            "status IN ('scheduled', 'completed', 'cancelled', 'rescheduled', 'no_show')",
            name="valid_lesson_status",
        ),
        CheckConstraint(
            "payment_status IN ('pending', 'paid', 'failed', 'refunded')",
            name="valid_payment_status",
        ),
    )

    def __repr__(self) -> str:
        return f"<Lesson(id={self.id}, student_id={self.student_id}, scheduled_at={self.scheduled_at}, status='{self.status}')>"


class MakeupLessonTracking(Base, TimestampMixin):
    """Student makeup lesson eligibility and usage per semester."""

    __tablename__ = "makeup_lesson_tracking"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE")
    )
    semester_id: Mapped[int] = mapped_column(
        ForeignKey("semesters.id", ondelete="CASCADE")
    )
    makeup_lessons_used: Mapped[int] = mapped_column(Integer, default=0)
    makeup_lessons_allowed: Mapped[int] = mapped_column(Integer, default=1)

    # Relationships
    student = relationship("Student", back_populates="makeup_tracking")
    semester = relationship("Semester", back_populates="makeup_tracking")

    __table_args__ = (
        CheckConstraint("makeup_lessons_used >= 0", name="valid_makeup_used"),
        CheckConstraint("makeup_lessons_allowed >= 0", name="valid_makeup_allowed"),
    )

    def __repr__(self) -> str:
        return f"<MakeupLessonTracking(student_id={self.student_id}, semester_id={self.semester_id}, used={self.makeup_lessons_used}/{self.makeup_lessons_allowed})>"
