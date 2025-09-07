from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, validator


class StripeWebhookEventSchema(BaseModel):
    """
    Stripe Webhook Event Schema

    This schema validates incoming Stripe webhook events according to Stripe's
    webhook event structure. It handles the standard Stripe event format with
    id, object, type, data, and other metadata fields.

    Reference: https://stripe.com/docs/api/events/object
    """

    id: str = Field(..., description="Unique identifier for the event")
    object: str = Field(
        ..., description="String representing the object's type. Always 'event'"
    )
    api_version: Optional[str] = Field(
        None, description="The Stripe API version used to render data"
    )
    created: int = Field(
        ..., description="Time at which the object was created (Unix timestamp)"
    )
    data: Dict[str, Any] = Field(
        ..., description="Object containing data associated with the event"
    )
    livemode: bool = Field(
        ..., description="Whether the event was created in live mode or test mode"
    )
    pending_webhooks: int = Field(
        ..., description="Number of webhooks that haven't been successfully delivered"
    )
    request: Optional[Dict[str, Any]] = Field(
        None, description="Information on the API request that triggered the event"
    )
    type: str = Field(
        ..., description="Description of the event (e.g., invoice.payment_succeeded)"
    )

    @validator("object")
    def validate_object_type(cls, v):
        """Ensure the object type is 'event' as expected for Stripe webhooks."""
        if v != "event":
            raise ValueError("Object type must be 'event' for Stripe webhook events")
        return v

    @validator("type")
    def validate_event_type(cls, v):
        """Validate that the event type is one we handle for payment processing."""
        # Phase 1: Focus on invoice events for subscription payments
        invoice_events = [
            "invoice.payment_succeeded",
            "invoice.payment_failed",
        ]

        # Other payment-related events we support
        other_payment_events = [
            "payment_intent.succeeded",
            "payment_intent.payment_failed",
            "payment_intent.processing",
            "payment_intent.canceled",
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
            "customer.created",
            "customer.updated",
            "customer.deleted",
            "charge.succeeded",
            "charge.failed",
            "charge.dispute.created",
        ]

        all_supported_events = invoice_events + other_payment_events

        if v not in all_supported_events:
            # Log warning but don't fail validation - we might want to store unknown events
            import logging

            logging.warning(f"Received unknown Stripe event type: {v}")

        return v

    @validator("data")
    def validate_data_structure(cls, v):
        """Ensure data contains the expected object and previous_attributes fields."""
        if not isinstance(v, dict):
            raise ValueError("Data field must be a dictionary")

        if "object" not in v:
            raise ValueError("Data field must contain an 'object' key")

        return v

    def get_event_object(self) -> Dict[str, Any]:
        """Extract the main object from the event data."""
        return self.data.get("object", {})

    def get_previous_attributes(self) -> Dict[str, Any]:
        """Extract previous attributes for update events."""
        return self.data.get("previous_attributes", {})

    def is_payment_event(self) -> bool:
        """Check if this is a payment-related event."""
        payment_prefixes = [
            "payment_intent.",
            "invoice.",
            "customer.",
            "charge.",
        ]
        return any(self.type.startswith(prefix) for prefix in payment_prefixes)

    def is_invoice_event(self) -> bool:
        """Check if this is an invoice-related event (Phase 1 focus)."""
        return self.type.startswith("invoice.")

    def get_customer_id(self) -> Optional[str]:
        """Extract customer ID from the event object."""
        event_obj = self.get_event_object()

        # Direct customer field
        if "customer" in event_obj:
            return event_obj["customer"]

        # Customer ID in nested objects
        if "subscription" in event_obj and isinstance(event_obj["subscription"], dict):
            return event_obj["subscription"].get("customer")

        # For customer events, the object itself is the customer
        if self.type.startswith("customer."):
            return event_obj.get("id")

        return None

    def get_payment_intent_id(self) -> Optional[str]:
        """Extract payment intent ID from the event object."""
        event_obj = self.get_event_object()

        # Direct payment intent field
        if "payment_intent" in event_obj:
            return event_obj["payment_intent"]

        # For payment_intent events, the object itself is the payment intent
        if self.type.startswith("payment_intent."):
            return event_obj.get("id")

        return None

    def get_subscription_id(self) -> Optional[str]:
        """Extract subscription ID from the event object."""
        event_obj = self.get_event_object()

        # Direct subscription field
        if "subscription" in event_obj:
            return event_obj["subscription"]

        # For subscription events, the object itself is the subscription
        if self.type.startswith("customer.subscription."):
            return event_obj.get("id")

        return None

    class Config:
        """Pydantic configuration."""

        extra = "allow"  # Allow extra fields from Stripe
        json_encoders = {
            # Handle any special encoding needs
        }
