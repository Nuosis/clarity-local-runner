"""
Payment-related Pydantic schemas with validation.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, validator

from .common import PaginatedResponse


class PaymentStatus(str, Enum):
    """Valid payment statuses."""

    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    """Valid payment methods."""

    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"
    CHECK = "check"


class BillingCycle(str, Enum):
    """Valid billing cycles."""

    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"


class Currency(str, Enum):
    """Valid currencies."""

    CAD = "CAD"
    USD = "USD"


class PaymentBase(BaseModel):
    """Base payment schema with common fields."""

    amount: Decimal = Field(..., ge=0, decimal_places=2)
    currency: Currency = Currency.CAD
    payment_method: PaymentMethod = PaymentMethod.CARD
    description: Optional[str] = Field(None, max_length=500)
    billing_cycle: Optional[BillingCycle] = None

    @validator("amount")
    def validate_amount(cls, v):
        """Ensure amount is positive."""
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v


class PaymentCreate(PaymentBase):
    """Schema for creating a new payment."""

    student_id: int = Field(..., gt=0)
    lesson_id: Optional[int] = Field(None, gt=0)
    stripe_payment_intent_id: Optional[str] = Field(None, max_length=255)
    payment_date: Optional[datetime] = None


class PaymentUpdate(BaseModel):
    """Schema for updating payment information."""

    status: Optional[PaymentStatus] = None
    payment_date: Optional[datetime] = None
    failure_reason: Optional[str] = Field(None, max_length=500)
    metadata: Optional[dict] = None


class StudentInfo(BaseModel):
    """Student information for payment responses."""

    id: int
    first_name: str
    last_name: str

    class Config:
        from_attributes = True


class LessonInfo(BaseModel):
    """Lesson information for payment responses."""

    id: int
    scheduled_at: datetime
    teacher_name: str

    class Config:
        from_attributes = True


class PaymentResponse(PaymentBase):
    """Schema for payment responses."""

    id: int
    student: StudentInfo
    lesson: Optional[LessonInfo] = None
    stripe_payment_intent_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    status: PaymentStatus = PaymentStatus.PENDING
    payment_date: Optional[datetime] = None
    failure_reason: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaymentListItem(BaseModel):
    """Simplified payment info for list responses."""

    id: int
    student_id: int
    student_name: str
    lesson_id: Optional[int] = None
    stripe_payment_intent_id: Optional[str] = None
    amount: Decimal
    currency: Currency
    status: PaymentStatus
    payment_method: PaymentMethod
    payment_date: Optional[datetime] = None
    billing_cycle: Optional[BillingCycle] = None
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentListResponse(PaginatedResponse):
    """Response for payment list endpoint."""

    payments: List[PaymentListItem]
    summary: Optional[dict] = None


class PaymentQueryParams(BaseModel):
    """Query parameters for payment list endpoint."""

    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(20, ge=1, le=100, description="Items per page")
    student_id: Optional[int] = Field(None, gt=0, description="Filter by student ID")
    status: Optional[PaymentStatus] = Field(None, description="Filter by status")
    date_from: Optional[date] = Field(None, description="Filter from date")
    date_to: Optional[date] = Field(None, description="Filter to date")


class PaymentSummary(BaseModel):
    """Payment summary statistics."""

    total_amount: Decimal
    successful_payments: int
    failed_payments: int
    pending_payments: int
    refunded_amount: Optional[Decimal] = None


# Subscription-related schemas
class SubscriptionStatus(str, Enum):
    """Valid subscription statuses."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"
    UNPAID = "unpaid"


class SubscriptionBase(BaseModel):
    """Base subscription schema."""

    billing_cycle: BillingCycle = BillingCycle.MONTHLY
    amount: Decimal = Field(..., ge=0, decimal_places=2)
    currency: Currency = Currency.CAD


class SubscriptionCreate(SubscriptionBase):
    """Schema for creating a subscription."""

    student_id: int = Field(..., gt=0)
    stripe_customer_id: str = Field(..., min_length=1, max_length=255)


class SubscriptionUpdate(BaseModel):
    """Schema for updating subscription."""

    status: Optional[SubscriptionStatus] = None
    amount: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    billing_cycle: Optional[BillingCycle] = None


class SubscriptionResponse(SubscriptionBase):
    """Schema for subscription responses."""

    id: int
    student_id: int
    student_name: str
    stripe_subscription_id: str
    stripe_customer_id: str
    status: SubscriptionStatus
    current_period_start: datetime
    current_period_end: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SubscriptionListResponse(PaginatedResponse):
    """Response for subscription list endpoint."""

    subscriptions: List[SubscriptionResponse]


class SubscriptionQueryParams(BaseModel):
    """Query parameters for subscription list endpoint."""

    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(20, ge=1, le=100, description="Items per page")
    student_id: Optional[int] = Field(None, gt=0, description="Filter by student ID")
    status: Optional[SubscriptionStatus] = Field(None, description="Filter by status")


class SubscriptionCancellation(BaseModel):
    """Schema for subscription cancellation."""

    cancellation_reason: str = Field(..., min_length=1, max_length=500)
    cancel_at_period_end: bool = True


# Billing record schemas
class TransactionType(str, Enum):
    """Valid transaction types."""

    CHARGE = "charge"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"


class BillingRecordBase(BaseModel):
    """Base billing record schema."""

    amount: Decimal = Field(..., decimal_places=2)
    currency: Currency = Currency.CAD
    transaction_type: TransactionType = TransactionType.CHARGE
    description: str = Field(..., min_length=1, max_length=500)
    billing_date: date
    due_date: Optional[date] = None


class BillingRecordCreate(BillingRecordBase):
    """Schema for creating billing record."""

    student_id: int = Field(..., gt=0)
    payment_id: Optional[int] = Field(None, gt=0)
    subscription_id: Optional[int] = Field(None, gt=0)


class BillingRecordResponse(BillingRecordBase):
    """Schema for billing record responses."""

    id: int
    student_id: int
    student_name: str
    payment_id: Optional[int] = None
    subscription_id: Optional[int] = None
    status: PaymentStatus
    created_at: datetime

    class Config:
        from_attributes = True


class BillingRecordListResponse(PaginatedResponse):
    """Response for billing record list endpoint."""

    billing_records: List[BillingRecordResponse]


class BillingQueryParams(BaseModel):
    """Query parameters for billing list endpoint."""

    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(20, ge=1, le=100, description="Items per page")
    student_id: Optional[int] = Field(None, gt=0, description="Filter by student ID")
    status: Optional[PaymentStatus] = Field(None, description="Filter by status")
    date_from: Optional[date] = Field(None, description="Filter from date")
    date_to: Optional[date] = Field(None, description="Filter to date")


# Workflow-related schemas
class PaymentWorkflowRequest(BaseModel):
    """Schema for payment workflow requests."""

    student_id: int = Field(..., gt=0)
    lesson_id: Optional[int] = Field(None, gt=0)
    amount: Decimal = Field(..., ge=0, decimal_places=2)
    payment_method_id: str = Field(..., min_length=1, max_length=255)
    currency: Currency = Currency.CAD
    description: str = Field(..., min_length=1, max_length=500)
    automatic_payment: bool = True


class PaymentWorkflowResponse(BaseModel):
    """Schema for payment workflow responses."""

    workflow_id: str
    status: str
    execution_time: float
    results: dict


class PaymentWorkflowStatus(BaseModel):
    """Schema for payment workflow status."""

    workflow_id: str
    status: str
    progress: int = Field(..., ge=0, le=100)
    current_node: Optional[str] = None
    nodes_executed: List[str] = []
    execution_time: Optional[float] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
