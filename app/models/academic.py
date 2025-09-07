"""
Academic year and semester management models.
"""

from datetime import date, time
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class AcademicYear(Base, TimestampMixin):
    """Academic year definitions (September start)."""

    __tablename__ = "academic_years"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="e.g., '2024-2025'"
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    semesters = relationship(
        "Semester", back_populates="academic_year", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<AcademicYear(id={self.id}, name='{self.name}', current={self.is_current})>"


class Semester(Base, TimestampMixin):
    """Academic periods within school years."""

    __tablename__ = "semesters"

    id: Mapped[int] = mapped_column(primary_key=True)
    academic_year_id: Mapped[int] = mapped_column(
        ForeignKey("academic_years.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="e.g., 'Fall 2024', 'Winter 2025'"
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    academic_year = relationship("AcademicYear", back_populates="semesters")
    makeup_weeks = relationship(
        "MakeupWeek", back_populates="semester", cascade="all, delete-orphan"
    )
    timeslots = relationship("Timeslot", back_populates="semester")
    lessons = relationship("Lesson", back_populates="semester")
    makeup_tracking = relationship("MakeupLessonTracking", back_populates="semester")

    def __repr__(self) -> str:
        return (
            f"<Semester(id={self.id}, name='{self.name}', current={self.is_current})>"
        )


class MakeupWeek(Base, TimestampMixin):
    """REQUIRED semester-specific makeup week definitions (Sun-Sat dates)."""

    __tablename__ = "makeup_weeks"

    id: Mapped[int] = mapped_column(primary_key=True)
    semester_id: Mapped[int] = mapped_column(
        ForeignKey("semesters.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="e.g., 'Fall 2024 Makeup Week'"
    )
    start_date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="Sunday of makeup week"
    )
    end_date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="Saturday of makeup week"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    semester = relationship("Semester", back_populates="makeup_weeks")

    def __repr__(self) -> str:
        return (
            f"<MakeupWeek(id={self.id}, name='{self.name}', active={self.is_active})>"
        )


class SchoolHours(Base, TimestampMixin):
    """Operational hours settings."""

    __tablename__ = "school_hours"

    id: Mapped[int] = mapped_column(primary_key=True)
    day_of_week: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="0=Sunday, 6=Saturday"
    )
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        CheckConstraint(
            "day_of_week >= 0 AND day_of_week <= 6", name="valid_day_of_week"
        ),
        CheckConstraint("end_time > start_time", name="valid_time_range"),
    )

    def __repr__(self) -> str:
        return (
            f"<SchoolHours(day={self.day_of_week}, {self.start_time}-{self.end_time})>"
        )
