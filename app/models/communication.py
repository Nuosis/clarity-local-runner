"""
Communication and notification models.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Message(Base, TimestampMixin):
    """Internal messaging between users."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    recipient_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    subject: Mapped[Optional[str]] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(String(20), default="message")
    priority: Mapped[str] = mapped_column(String(10), default="normal")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    parent_message_id: Mapped[Optional[int]] = mapped_column(ForeignKey("messages.id"))
    student_id: Mapped[Optional[int]] = mapped_column(ForeignKey("students.id"))
    lesson_id: Mapped[Optional[int]] = mapped_column(ForeignKey("lessons.id"))
    message_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Relationships
    sender = relationship(
        "User", foreign_keys=[sender_id], back_populates="sent_messages"
    )
    recipient = relationship(
        "User", foreign_keys=[recipient_id], back_populates="received_messages"
    )
    parent_message = relationship("Message", remote_side=[id])
    student = relationship("Student", back_populates="messages")
    lesson = relationship("Lesson", back_populates="messages")
    email_tracking = relationship("EmailTracking", back_populates="message")

    __table_args__ = (
        CheckConstraint(
            "message_type IN ('message', 'notification', 'alert', 'reminder')",
            name="valid_message_type",
        ),
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="valid_message_priority",
        ),
    )

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, sender_id={self.sender_id}, recipient_id={self.recipient_id}, read={self.is_read})>"


class EmailTracking(Base, TimestampMixin):
    """Track email delivery and status."""

    __tablename__ = "email_tracking"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[Optional[int]] = mapped_column(ForeignKey("messages.id"))
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    sender_email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(200))
    email_service_id: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    delivery_attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    email_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Relationships
    message = relationship("Message", back_populates="email_tracking")

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'sent', 'delivered', 'bounced', 'failed', 'opened', 'clicked')",
            name="valid_email_status",
        ),
    )

    def __repr__(self) -> str:
        return f"<EmailTracking(id={self.id}, recipient='{self.recipient_email}', status='{self.status}')>"


class Notification(Base, TimestampMixin):
    """System-generated notifications."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[str] = mapped_column(String(30), nullable=False)
    priority: Mapped[str] = mapped_column(String(10), default="normal")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    action_url: Mapped[Optional[str]] = mapped_column(String(500))
    student_id: Mapped[Optional[int]] = mapped_column(ForeignKey("students.id"))
    lesson_id: Mapped[Optional[int]] = mapped_column(ForeignKey("lessons.id"))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    notification_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Relationships
    user = relationship("User", back_populates="notifications")
    student = relationship("Student", back_populates="notifications")
    lesson = relationship("Lesson", back_populates="notifications")

    __table_args__ = (
        CheckConstraint(
            """notification_type IN (
            'enrollment_confirmation', 'payment_success', 'payment_failed', 'lesson_reminder', 
            'lesson_cancelled', 'lesson_rescheduled', 'semester_renewal', 'makeup_lesson_available'
        )""",
            name="valid_notification_type",
        ),
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="valid_notification_priority",
        ),
    )

    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, user_id={self.user_id}, type='{self.notification_type}', read={self.is_read})>"
