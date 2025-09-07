"""
System configuration and audit models.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    DECIMAL,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class SystemSetting(Base, TimestampMixin):
    """Application configuration."""

    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    setting_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    setting_value: Mapped[Optional[str]] = mapped_column(Text)
    setting_type: Mapped[str] = mapped_column(String(20), default="string")
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    category: Mapped[str] = mapped_column(String(50), default="general")

    __table_args__ = (
        CheckConstraint(
            "setting_type IN ('string', 'number', 'boolean', 'json')",
            name="valid_setting_type",
        ),
    )

    def __repr__(self) -> str:
        return f"<SystemSetting(key='{self.setting_key}', type='{self.setting_type}', public={self.is_public})>"


class PricingConfig(Base, TimestampMixin):
    """Lesson rates and billing settings."""

    __tablename__ = "pricing_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    instrument: Mapped[str] = mapped_column(String(50), nullable=False)
    skill_level: Mapped[str] = mapped_column(String(20), default="all")
    lesson_duration: Mapped[int] = mapped_column(Integer, default=30)
    rate_per_lesson: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="CAD")
    billing_frequency: Mapped[str] = mapped_column(String(20), default="monthly")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    effective_date: Mapped[date] = mapped_column(Date, default=date.today)

    __table_args__ = (
        CheckConstraint(
            "skill_level IN ('all', 'beginner', 'intermediate', 'advanced')",
            name="valid_skill_level",
        ),
        CheckConstraint(
            "lesson_duration >= 15 AND lesson_duration <= 120",
            name="valid_lesson_duration",
        ),
        CheckConstraint("rate_per_lesson >= 0", name="valid_rate"),
        CheckConstraint(
            "billing_frequency IN ('weekly', 'monthly', 'semester', 'annual')",
            name="valid_billing_frequency",
        ),
    )

    def __repr__(self) -> str:
        return f"<PricingConfig(instrument='{self.instrument}', rate={self.rate_per_lesson}, active={self.is_active})>"


class AuditLog(Base, TimestampMixin):
    """Track all data changes for compliance."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    table_name: Mapped[str] = mapped_column(String(100), nullable=False)
    record_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(10), nullable=False)
    old_values: Mapped[Optional[dict]] = mapped_column(JSONB)
    new_values: Mapped[Optional[dict]] = mapped_column(JSONB)
    changed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now
    )
    ip_address: Mapped[Optional[str]] = mapped_column(INET)
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    audit_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Relationships
    changed_by_user = relationship("User", back_populates="audit_entries")

    __table_args__ = (
        CheckConstraint(
            "action IN ('INSERT', 'UPDATE', 'DELETE')", name="valid_audit_action"
        ),
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, table='{self.table_name}', record_id={self.record_id}, action='{self.action}')>"
