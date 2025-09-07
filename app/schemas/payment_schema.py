"""
Payment Processing Workflow Schemas

This module defines Pydantic schemas for the payment processing workflow,
including validation for payment data, subscription information, and workflow results.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, validator


class PaymentMethodType(str, Enum):
    """Supported payment method types"""

    CARD = "card"
    BANK_ACCOUNT = "bank_account"
    DIGITAL_WALLET = "digital_wallet"


class PaymentStatus(str, Enum):
    """Payment processing status"""

    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class SubscriptionStatus(str, Enum):
    """Subscription status"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"
    UNPAID = "unpaid"


class PaymentMethodSchema(BaseModel):
    """Payment method information"""

    type: PaymentMethodType
    card_last_four: Optional[str] = Field(None, description="Last 4 digits of card")
    card_brand: Optional[str] = Field(
        None, description="Card brand (visa, mastercard, etc.)"
    )
    card_exp_month: Optional[int] = Field(
        None, ge=1, le=12, description="Card expiration month"
    )
    card_exp_year: Optional[int] = Field(
        None, ge=2024, description="Card expiration year"
    )
    bank_account_last_four: Optional[str] = Field(
        None, description="Last 4 digits of bank account"
    )
    bank_routing_number: Optional[str] = Field(None, description="Bank routing number")

    @validator("card_last_four")
    def validate_card_last_four(cls, v):
        if v is not None and (len(v) != 4 or not v.isdigit()):
            raise ValueError("Card last four must be exactly 4 digits")
        return v

    @validator("bank_account_last_four")
    def validate_bank_last_four(cls, v):
        if v is not None and (len(v) != 4 or not v.isdigit()):
            raise ValueError("Bank account last four must be exactly 4 digits")
        return v


class SubscriptionPlanSchema(BaseModel):
    """Subscription plan details"""

    plan_id: str = Field(..., description="Unique plan identifier")
    name: str = Field(..., description="Plan name")
    amount: Decimal = Field(..., gt=0, description="Plan amount in dollars")
    currency: str = Field(default="usd", description="Currency code")
    interval: str = Field(..., description="Billing interval (month, year)")
    interval_count: int = Field(
        default=1, ge=1, description="Number of intervals between billings"
    )
    trial_period_days: Optional[int] = Field(
        None, ge=0, description="Trial period in days"
    )

    @validator("currency")
    def validate_currency(cls, v):
        if v.lower() not in ["usd", "cad", "eur", "gbp"]:
            raise ValueError("Currency must be one of: usd, cad, eur, gbp")
        return v.lower()

    @validator("interval")
    def validate_interval(cls, v):
        if v.lower() not in ["day", "week", "month", "year"]:
            raise ValueError("Interval must be one of: day, week, month, year")
        return v.lower()


class PaymentEventSchema(BaseModel):
    """
    Payment processing workflow event schema

    This schema defines the structure for payment processing workflow events,
    including customer information, payment details, and subscription data.
    """

    # Customer Information
    customer_id: Optional[str] = Field(None, description="Existing Stripe customer ID")
    user_id: UUID = Field(..., description="Internal user ID")
    email: EmailStr = Field(..., description="Customer email address")
    name: str = Field(
        ..., min_length=2, max_length=100, description="Customer full name"
    )
    phone: Optional[str] = Field(None, description="Customer phone number")

    # Payment Information
    payment_method_id: Optional[str] = Field(
        None, description="Stripe payment method ID"
    )
    payment_method: Optional[PaymentMethodSchema] = Field(
        None, description="Payment method details"
    )
    amount: Decimal = Field(..., gt=0, description="Payment amount in dollars")
    currency: str = Field(default="usd", description="Payment currency")

    # Subscription Information
    subscription_plan: SubscriptionPlanSchema = Field(
        ..., description="Subscription plan details"
    )
    subscription_id: Optional[str] = Field(None, description="Existing subscription ID")

    # Billing Information
    billing_address: Optional[Dict[str, str]] = Field(
        None, description="Billing address"
    )
    tax_rate: Optional[Decimal] = Field(
        None, ge=0, le=1, description="Tax rate (0.0 to 1.0)"
    )

    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )
    idempotency_key: Optional[str] = Field(
        None, description="Idempotency key for payment"
    )

    # Workflow Context
    workflow_id: Optional[str] = Field(None, description="Workflow execution ID")
    retry_count: int = Field(default=0, ge=0, description="Number of retry attempts")

    @validator("phone")
    def validate_phone(cls, v):
        if v is not None:
            # Remove all non-digit characters
            digits_only = "".join(filter(str.isdigit, v))
            if len(digits_only) < 10 or len(digits_only) > 15:
                raise ValueError("Phone number must contain 10-15 digits")
        return v

    @validator("currency")
    def validate_currency(cls, v):
        if v.lower() not in ["usd", "cad", "eur", "gbp"]:
            raise ValueError("Currency must be one of: usd, cad, eur, gbp")
        return v.lower()

    @validator("amount")
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        if v > Decimal("999999.99"):
            raise ValueError("Amount cannot exceed $999,999.99")
        return v

    @validator("metadata")
    def validate_metadata(cls, v):
        if v is not None and len(v) > 50:
            raise ValueError("Metadata cannot have more than 50 keys")
        return v


class PaymentResultSchema(BaseModel):
    """Payment processing workflow result schema"""

    # Status Information
    status: PaymentStatus = Field(..., description="Payment processing status")
    success: bool = Field(..., description="Whether the payment was successful")

    # Payment Details
    payment_intent_id: Optional[str] = Field(
        None, description="Stripe payment intent ID"
    )
    charge_id: Optional[str] = Field(None, description="Stripe charge ID")
    amount_paid: Optional[Decimal] = Field(None, description="Amount actually paid")
    currency: Optional[str] = Field(None, description="Payment currency")

    # Customer and Subscription
    customer_id: Optional[str] = Field(None, description="Stripe customer ID")
    subscription_id: Optional[str] = Field(None, description="Stripe subscription ID")
    subscription_status: Optional[SubscriptionStatus] = Field(
        None, description="Subscription status"
    )

    # Transaction Details
    transaction_id: Optional[str] = Field(None, description="Internal transaction ID")
    receipt_url: Optional[str] = Field(None, description="Receipt URL")
    invoice_id: Optional[str] = Field(None, description="Invoice ID")

    # Error Information
    error_code: Optional[str] = Field(None, description="Error code if payment failed")
    error_message: Optional[str] = Field(
        None, description="Error message if payment failed"
    )
    decline_code: Optional[str] = Field(None, description="Card decline code")

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    processed_at: Optional[datetime] = Field(
        None, description="Processing completion timestamp"
    )

    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )

    # Workflow Information
    workflow_id: Optional[str] = Field(None, description="Workflow execution ID")
    node_results: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Individual node results"
    )


class StripeWebhookEventSchema(BaseModel):
    """Stripe webhook event schema"""

    id: str = Field(..., description="Stripe event ID")
    type: str = Field(..., description="Event type")
    data: Dict[str, Any] = Field(..., description="Event data")
    created: int = Field(..., description="Event creation timestamp")
    livemode: bool = Field(..., description="Whether event is from live mode")
    pending_webhooks: int = Field(..., description="Number of pending webhooks")
    request: Optional[Dict[str, Any]] = Field(None, description="Request information")

    @validator("type")
    def validate_event_type(cls, v):
        # Common Stripe event types we handle
        valid_types = [
            "payment_intent.succeeded",
            "payment_intent.payment_failed",
            "invoice.payment_succeeded",
            "invoice.payment_failed",
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
            "charge.dispute.created",
            "charge.succeeded",
            "charge.failed",
        ]
        if v not in valid_types:
            raise ValueError(f"Unsupported event type: {v}")
        return v


class AccountingEntrySchema(BaseModel):
    """Accounting entry for payment transactions"""

    transaction_id: str = Field(..., description="Transaction identifier")
    account_code: str = Field(..., description="Account code")
    description: str = Field(..., description="Transaction description")
    debit_amount: Optional[Decimal] = Field(None, ge=0, description="Debit amount")
    credit_amount: Optional[Decimal] = Field(None, ge=0, description="Credit amount")
    currency: str = Field(default="usd", description="Currency code")
    reference_id: Optional[str] = Field(
        None, description="Reference ID (payment intent, etc.)"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Entry timestamp"
    )

    @validator("debit_amount", "credit_amount")
    def validate_amounts(cls, v, values):
        # Ensure exactly one of debit or credit is provided
        debit = values.get("debit_amount")
        credit = values.get("credit_amount")

        if debit is not None and credit is not None:
            raise ValueError("Cannot specify both debit and credit amounts")
        if debit is None and credit is None:
            raise ValueError("Must specify either debit or credit amount")

        return v
