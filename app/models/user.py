"""
User model for authentication and user management.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """
    Core user model for authentication and profile management.
    Integrates with Supabase Auth for authentication.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    supabase_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        unique=True,
        nullable=False,
        comment="Reference to Supabase auth.users.id",
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Role: admin, teacher, parent"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    user_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Relationships
    teacher_profile = relationship("Teacher", back_populates="user", uselist=False)
    students_as_parent = relationship("Student", back_populates="parent")
    sent_messages = relationship(
        "Message", foreign_keys="Message.sender_id", back_populates="sender"
    )
    received_messages = relationship(
        "Message", foreign_keys="Message.recipient_id", back_populates="recipient"
    )
    notifications = relationship("Notification", back_populates="user")
    audit_entries = relationship("AuditLog", back_populates="changed_by_user")

    @property
    def full_name(self) -> str:
        """Return the user's full name."""
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"
