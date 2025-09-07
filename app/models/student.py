"""
Student model for student management and enrollment.
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    DECIMAL,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Student(Base, TimestampMixin):
    """Student profiles linked to parent accounts with teacher assignments."""

    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[Optional[str]] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    parent_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    teacher_id: Mapped[Optional[int]] = mapped_column(ForeignKey("teachers.id"))
    instrument: Mapped[str] = mapped_column(String(50), nullable=False)
    skill_level: Mapped[str] = mapped_column(String(20), default="beginner")
    lesson_rate: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    enrollment_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    parent = relationship("User", back_populates="students_as_parent")
    teacher = relationship("Teacher", back_populates="students")
    timeslots = relationship("Timeslot", back_populates="student")
    lessons = relationship("Lesson", back_populates="student")
    payments = relationship("Payment", back_populates="student")
    subscriptions = relationship("Subscription", back_populates="student")
    billing_records = relationship("BillingRecord", back_populates="student")
    makeup_tracking = relationship("MakeupLessonTracking", back_populates="student")
    messages = relationship("Message", back_populates="student")
    notifications = relationship("Notification", back_populates="student")

    __table_args__ = (
        CheckConstraint(
            "instrument IN ('piano', 'guitar', 'bass')",
            name="valid_instrument",
        ),
        CheckConstraint(
            "skill_level IN ('beginner', 'intermediate', 'advanced')",
            name="valid_skill_level",
        ),
        CheckConstraint(
            "lesson_rate >= 30 AND lesson_rate <= 200", name="valid_lesson_rate"
        ),
    )

    @property
    def full_name(self) -> str:
        """Return the student's full name."""
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self) -> int:
        """Calculate student's current age."""
        today = date.today()
        return (
            today.year
            - self.date_of_birth.year
            - (
                (today.month, today.day)
                < (self.date_of_birth.month, self.date_of_birth.day)
            )
        )

    def __repr__(self) -> str:
        return f"<Student(id={self.id}, name='{self.full_name}', instrument='{self.instrument}')>"
