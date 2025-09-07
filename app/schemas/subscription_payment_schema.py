"""
Subscription Payment Event Schemas

This module defines Pydantic schemas for subscription payment events
specifically for invoice-based webhook processing in Phase 1.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, validator


class StripeInvoiceObjectSchema(BaseModel):
    """Schema for Stripe invoice object within webhook events."""

    id: str = Field(..., description="Unique identifier for the invoice")
    object: str = Field(
        ..., description="String representing the object's type. Always 'invoice'"
    )
    amount_due: int = Field(
        ..., description="Final amount due at this time for this invoice in cents"
    )
    amount_paid: int = Field(..., description="The amount, in cents, that was paid")
    amount_remaining: int = Field(
        ..., description="The amount remaining, in cents, that is due"
    )
    currency: str = Field(..., description="Three-letter ISO currency code")
    customer: str = Field(..., description="ID of the customer who will be billed")
    subscription: Optional[str] = Field(
        None, description="The subscription that this invoice was prepared for"
    )
    status: str = Field(..., description="The status of the invoice")
    payment_intent: Optional[str] = Field(
        None, description="The PaymentIntent associated with this invoice"
    )
    hosted_invoice_url: Optional[str] = Field(
        None, description="The URL for the hosted invoice page"
    )
    invoice_pdf: Optional[str] = Field(
        None, description="The link to download the PDF for the invoice"
    )
    number: Optional[str] = Field(
        None,
        description="A unique, identifying string that appears on emails sent to the customer",
    )
    created: int = Field(
        ..., description="Time at which the object was created (Unix timestamp)"
    )
    due_date: Optional[int] = Field(
        None,
        description="The date on which payment for this invoice is due (Unix timestamp)",
    )
    period_start: int = Field(
        ...,
        description="Start of the usage period during which invoice items were added to this invoice",
    )
    period_end: int = Field(
        ...,
        description="End of the usage period during which invoice items were added to this invoice",
    )

    @validator("object")
    def validate_object_type(cls, v):
        """Ensure the object type is 'invoice'."""
        if v != "invoice":
            raise ValueError("Object type must be 'invoice' for invoice events")
        return v

    @validator("status")
    def validate_invoice_status(cls, v):
        """Validate invoice status values."""
        valid_statuses = ["draft", "open", "paid", "uncollectible", "void"]
        if v not in valid_statuses:
            raise ValueError(
                f"Invalid invoice status: {v}. Must be one of {valid_statuses}"
            )
        return v

    @validator("currency")
    def validate_currency_code(cls, v):
        """Validate currency is a 3-letter ISO code."""
        if len(v) != 3:
            raise ValueError("Currency must be a 3-letter ISO code")
        return v.upper()


class InvoicePaymentSucceededEventSchema(BaseModel):
    """Schema for invoice.payment_succeeded webhook events."""

    id: str = Field(..., description="Unique identifier for the event")
    object: str = Field(
        ..., description="String representing the object's type. Always 'event'"
    )
    type: str = Field(
        ..., description="Event type. Must be 'invoice.payment_succeeded'"
    )
    created: int = Field(
        ..., description="Time at which the event was created (Unix timestamp)"
    )
    livemode: bool = Field(
        ..., description="Whether the event occurred in live mode or test mode"
    )
    pending_webhooks: int = Field(
        ..., description="Number of webhooks that haven't been successfully delivered"
    )
    api_version: Optional[str] = Field(
        None, description="The Stripe API version used to render data"
    )
    data: Dict[str, Any] = Field(
        ..., description="Object containing data associated with the event"
    )
    request: Optional[Dict[str, Any]] = Field(
        None, description="Information on the API request that triggered the event"
    )

    @validator("object")
    def validate_object_type(cls, v):
        """Ensure the object type is 'event'."""
        if v != "event":
            raise ValueError("Object type must be 'event' for webhook events")
        return v

    @validator("type")
    def validate_event_type(cls, v):
        """Ensure the event type is invoice.payment_succeeded."""
        if v != "invoice.payment_succeeded":
            raise ValueError("Event type must be 'invoice.payment_succeeded'")
        return v

    @validator("data")
    def validate_data_structure(cls, v):
        """Validate data contains invoice object."""
        if not isinstance(v, dict):
            raise ValueError("Data field must be a dictionary")

        if "object" not in v:
            raise ValueError("Data field must contain an 'object' key")

        # Validate the invoice object
        try:
            StripeInvoiceObjectSchema(**v["object"])
        except Exception as e:
            raise ValueError(f"Invalid invoice object in data: {e}")

        return v

    def get_invoice(self) -> StripeInvoiceObjectSchema:
        """Extract and validate the invoice object from event data."""
        return StripeInvoiceObjectSchema(**self.data["object"])

    def get_customer_id(self) -> str:
        """Extract customer ID from the invoice."""
        invoice = self.get_invoice()
        return invoice.customer

    def get_subscription_id(self) -> Optional[str]:
        """Extract subscription ID from the invoice."""
        invoice = self.get_invoice()
        return invoice.subscription

    def get_payment_amount(self) -> Decimal:
        """Get the payment amount in dollars."""
        invoice = self.get_invoice()
        return Decimal(invoice.amount_paid) / 100

    def get_currency(self) -> str:
        """Get the payment currency."""
        invoice = self.get_invoice()
        return invoice.currency


class InvoicePaymentFailedEventSchema(BaseModel):
    """Schema for invoice.payment_failed webhook events."""

    id: str = Field(..., description="Unique identifier for the event")
    object: str = Field(
        ..., description="String representing the object's type. Always 'event'"
    )
    type: str = Field(..., description="Event type. Must be 'invoice.payment_failed'")
    created: int = Field(
        ..., description="Time at which the event was created (Unix timestamp)"
    )
    livemode: bool = Field(
        ..., description="Whether the event occurred in live mode or test mode"
    )
    pending_webhooks: int = Field(
        ..., description="Number of webhooks that haven't been successfully delivered"
    )
    api_version: Optional[str] = Field(
        None, description="The Stripe API version used to render data"
    )
    data: Dict[str, Any] = Field(
        ..., description="Object containing data associated with the event"
    )
    request: Optional[Dict[str, Any]] = Field(
        None, description="Information on the API request that triggered the event"
    )

    @validator("object")
    def validate_object_type(cls, v):
        """Ensure the object type is 'event'."""
        if v != "event":
            raise ValueError("Object type must be 'event' for webhook events")
        return v

    @validator("type")
    def validate_event_type(cls, v):
        """Ensure the event type is invoice.payment_failed."""
        if v != "invoice.payment_failed":
            raise ValueError("Event type must be 'invoice.payment_failed'")
        return v

    @validator("data")
    def validate_data_structure(cls, v):
        """Validate data contains invoice object."""
        if not isinstance(v, dict):
            raise ValueError("Data field must be a dictionary")

        if "object" not in v:
            raise ValueError("Data field must contain an 'object' key")

        # Validate the invoice object
        try:
            StripeInvoiceObjectSchema(**v["object"])
        except Exception as e:
            raise ValueError(f"Invalid invoice object in data: {e}")

        return v

    def get_invoice(self) -> StripeInvoiceObjectSchema:
        """Extract and validate the invoice object from event data."""
        return StripeInvoiceObjectSchema(**self.data["object"])

    def get_customer_id(self) -> str:
        """Extract customer ID from the invoice."""
        invoice = self.get_invoice()
        return invoice.customer

    def get_subscription_id(self) -> Optional[str]:
        """Extract subscription ID from the invoice."""
        invoice = self.get_invoice()
        return invoice.subscription

    def get_failed_amount(self) -> Decimal:
        """Get the failed payment amount in dollars."""
        invoice = self.get_invoice()
        return Decimal(invoice.amount_due) / 100

    def get_currency(self) -> str:
        """Get the payment currency."""
        invoice = self.get_invoice()
        return invoice.currency


class SubscriptionPaymentEventSchema(BaseModel):
    """
    Unified schema for subscription payment events from Stripe webhooks.

    This schema handles both invoice.payment_succeeded and invoice.payment_failed
    events for the SubscriptionPaymentWorkflow.
    """

    # Core event identification
    stripe_event_id: str = Field(..., description="Stripe event ID")
    event_type: str = Field(
        ...,
        description="Type of event (invoice.payment_succeeded or invoice.payment_failed)",
    )
    created_at: datetime = Field(..., description="When the event was created")
    livemode: bool = Field(..., description="Whether this is a live or test event")

    # Invoice and payment details
    invoice_id: str = Field(..., description="Stripe invoice ID")
    customer_id: str = Field(..., description="Stripe customer ID")
    subscription_id: Optional[str] = Field(None, description="Stripe subscription ID")
    payment_intent_id: Optional[str] = Field(
        None, description="Stripe payment intent ID"
    )

    # Financial details
    amount: Decimal = Field(..., description="Payment amount in dollars")
    currency: str = Field(..., description="Payment currency (ISO 3-letter code)")
    invoice_status: str = Field(..., description="Current status of the invoice")

    # Additional metadata
    invoice_number: Optional[str] = Field(
        None, description="Human-readable invoice number"
    )
    hosted_invoice_url: Optional[str] = Field(
        None, description="URL to hosted invoice page"
    )
    invoice_pdf_url: Optional[str] = Field(None, description="URL to invoice PDF")
    period_start: datetime = Field(..., description="Billing period start")
    period_end: datetime = Field(..., description="Billing period end")

    # Raw event data for debugging/audit
    raw_event_data: Dict[str, Any] = Field(
        ..., description="Complete raw Stripe event data"
    )

    @validator("event_type")
    def validate_event_type(cls, v):
        """Ensure event type is supported."""
        supported_types = ["invoice.payment_succeeded", "invoice.payment_failed"]
        if v not in supported_types:
            raise ValueError(f"Event type must be one of {supported_types}")
        return v

    @validator("currency")
    def validate_currency(cls, v):
        """Validate currency format."""
        if len(v) != 3:
            raise ValueError("Currency must be a 3-letter ISO code")
        return v.upper()

    @validator("amount")
    def validate_amount(cls, v):
        """Ensure amount is positive."""
        if v < 0:
            raise ValueError("Amount must be positive")
        return v

    def is_payment_successful(self) -> bool:
        """Check if this represents a successful payment."""
        return self.event_type == "invoice.payment_succeeded"

    def is_payment_failed(self) -> bool:
        """Check if this represents a failed payment."""
        return self.event_type == "invoice.payment_failed"

    @classmethod
    def from_stripe_event(
        cls, stripe_event: Dict[str, Any]
    ) -> "SubscriptionPaymentEventSchema":
        """
        Create SubscriptionPaymentEventSchema from raw Stripe webhook event.

        Args:
            stripe_event: Raw Stripe webhook event data

        Returns:
            SubscriptionPaymentEventSchema instance

        Raises:
            ValueError: If event data is invalid or unsupported
        """
        # Validate event type
        event_type = stripe_event.get("type")
        if event_type not in ["invoice.payment_succeeded", "invoice.payment_failed"]:
            raise ValueError(f"Unsupported event type: {event_type}")

        # Extract invoice data
        invoice_data = stripe_event.get("data", {}).get("object", {})
        if not invoice_data:
            raise ValueError("Missing invoice data in event")

        # Determine amount based on event type
        if event_type == "invoice.payment_succeeded":
            amount_cents = invoice_data.get("amount_paid", 0)
        else:  # invoice.payment_failed
            amount_cents = invoice_data.get("amount_due", 0)

        return cls(
            stripe_event_id=stripe_event["id"],
            event_type=event_type,
            created_at=datetime.fromtimestamp(stripe_event["created"]),
            livemode=stripe_event.get("livemode", False),
            invoice_id=invoice_data["id"],
            customer_id=invoice_data["customer"],
            subscription_id=invoice_data.get("subscription"),
            payment_intent_id=invoice_data.get("payment_intent"),
            amount=Decimal(amount_cents) / 100,
            currency=invoice_data["currency"].upper(),
            invoice_status=invoice_data["status"],
            invoice_number=invoice_data.get("number"),
            hosted_invoice_url=invoice_data.get("hosted_invoice_url"),
            invoice_pdf_url=invoice_data.get("invoice_pdf"),
            period_start=datetime.fromtimestamp(invoice_data["period_start"]),
            period_end=datetime.fromtimestamp(invoice_data["period_end"]),
            raw_event_data=stripe_event,
        )
