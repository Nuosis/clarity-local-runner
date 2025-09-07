"""
Payment and billing models for financial management.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Payment(Base, TimestampMixin):
    """Payment records and billing history."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE")
    )
    lesson_id: Mapped[Optional[int]] = mapped_column(ForeignKey("lessons.id"))
    stripe_payment_intent_id: Mapped[str] = mapped_column(String(255), nullable=False)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255))
    amount: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="CAD")
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(20), nullable=False)
    payment_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    failure_reason: Mapped[Optional[str]] = mapped_column(Text)
    billing_cycle: Mapped[str] = mapped_column(String(20), default="monthly")
    description: Mapped[Optional[str]] = mapped_column(Text)
    payment_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Relationships
    student = relationship("Student", back_populates="payments")
    lesson = relationship("Lesson", back_populates="payments")
    billing_records = relationship("BillingRecord", back_populates="payment")

    __table_args__ = (
        CheckConstraint("amount >= 0", name="valid_payment_amount"),
        CheckConstraint(
            "status IN ('pending', 'succeeded', 'failed', 'cancelled', 'refunded')",
            name="valid_payment_status",
        ),
        CheckConstraint(
            "payment_method IN ('card', 'bank_transfer', 'cash', 'other')",
            name="valid_payment_method",
        ),
        CheckConstraint(
            "billing_cycle IN ('weekly', 'monthly', 'semester', 'annual')",
            name="valid_billing_cycle",
        ),
    )

    def __repr__(self) -> str:
        return f"<Payment(id={self.id}, student_id={self.student_id}, amount={self.amount}, status='{self.status}')>"


class Subscription(Base, TimestampMixin):
    """Stripe subscription management."""

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE")
    )
    stripe_subscription_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    stripe_customer_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    current_period_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    current_period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    billing_cycle: Mapped[str] = mapped_column(String(20), default="monthly")
    amount: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="CAD")
    subscription_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Relationships
    student = relationship("Student", back_populates="subscriptions")
    billing_records = relationship("BillingRecord", back_populates="subscription")

    __table_args__ = (
        CheckConstraint("amount >= 0", name="valid_subscription_amount"),
        CheckConstraint(
            "status IN ('active', 'past_due', 'cancelled', 'unpaid', 'incomplete')",
            name="valid_subscription_status",
        ),
        CheckConstraint(
            "billing_cycle IN ('weekly', 'monthly', 'semester', 'annual')",
            name="valid_subscription_billing_cycle",
        ),
    )

    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, student_id={self.student_id}, status='{self.status}', amount={self.amount})>"


class BillingRecord(Base, TimestampMixin):
    """Internal accounting and financial tracking."""

    __tablename__ = "billing_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE")
    )
    payment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("payments.id"))
    subscription_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("subscriptions.id")
    )
    amount: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="CAD")
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    billing_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    billing_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Relationships
    student = relationship("Student", back_populates="billing_records")
    payment = relationship("Payment", back_populates="billing_records")
    subscription = relationship("Subscription", back_populates="billing_records")

    __table_args__ = (
        CheckConstraint(
            "transaction_type IN ('charge', 'refund', 'adjustment', 'credit')",
            name="valid_transaction_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'paid', 'overdue', 'cancelled')",
            name="valid_billing_status",
        ),
    )

    def __repr__(self) -> str:
        return f"<BillingRecord(id={self.id}, student_id={self.student_id}, type='{self.transaction_type}', amount={self.amount})>"
