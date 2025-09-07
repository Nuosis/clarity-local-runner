import hashlib
import hmac
import logging
import os
import time
from typing import Optional

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class StripeWebhookService:
    """
    Stripe Webhook Signature Verification Service

    This service handles Stripe webhook signature verification to ensure
    webhook events are authentic and haven't been tampered with.

    Reference: https://stripe.com/docs/webhooks/signatures
    """

    def __init__(self):
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        if not self.webhook_secret:
            logger.warning(
                "STRIPE_WEBHOOK_SECRET not set - webhook signature verification disabled"
            )

    def verify_signature(
        self, payload: bytes, signature_header: str, tolerance: int = 300
    ) -> bool:
        """
        Verify the Stripe webhook signature with enhanced logging for invoice events.

        Args:
            payload: Raw request body as bytes
            signature_header: Stripe-Signature header value
            tolerance: Maximum age of webhook in seconds (default: 5 minutes)

        Returns:
            bool: True if signature is valid, False otherwise

        Raises:
            HTTPException: If signature verification fails
        """
        if not self.webhook_secret:
            logger.warning(
                "Webhook signature verification skipped - no secret configured"
            )
            return True

        try:
            # Parse the signature header
            elements = signature_header.split(",")
            signature_data = {}

            for element in elements:
                key, value = element.split("=", 1)
                if key == "t":
                    signature_data["timestamp"] = int(value)
                elif key.startswith("v"):
                    signature_data[key] = value

            if "timestamp" not in signature_data:
                logger.error("Missing timestamp in Stripe webhook signature header")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing timestamp in signature header",
                )

            # Check timestamp tolerance with enhanced logging
            current_time = int(time.time())
            timestamp_diff = abs(current_time - signature_data["timestamp"])

            if timestamp_diff > tolerance:
                logger.error(
                    f"Stripe webhook timestamp too old: {timestamp_diff}s > {tolerance}s tolerance"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Webhook timestamp too old",
                )

            # Log timestamp validation success for invoice events
            logger.debug(f"Webhook timestamp validated: age={timestamp_diff}s")

            # Construct the signed payload
            signed_payload = f"{signature_data['timestamp']}.{payload.decode('utf-8')}"

            # Compute expected signature
            expected_signature = hmac.new(
                self.webhook_secret.encode("utf-8"),
                signed_payload.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            # Compare signatures (use constant-time comparison)
            signature_versions_checked = []
            for version_key in signature_data:
                if version_key.startswith("v") and version_key in signature_data:
                    signature_versions_checked.append(version_key)
                    if hmac.compare_digest(
                        expected_signature, signature_data[version_key]
                    ):
                        logger.info(
                            f"Stripe webhook signature verified successfully using {version_key}"
                        )
                        return True

            logger.error(
                f"Stripe webhook signature verification failed for all versions: {signature_versions_checked}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook signature",
            )

        except ValueError as e:
            logger.error(f"Error parsing webhook signature header: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid signature header format",
            )
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected error during webhook signature verification: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Webhook signature verification failed",
            )

    def is_duplicate_event(
        self, event_id: str, idempotency_key: Optional[str] = None
    ) -> bool:
        """
        Check if this webhook event has already been processed.

        This implementation uses database-based deduplication to prevent
        duplicate processing of Stripe webhook events, particularly important
        for invoice events in Phase 1.

        Args:
            event_id: Stripe event ID
            idempotency_key: Optional idempotency key

        Returns:
            bool: True if event is a duplicate, False otherwise
        """
        try:
            from database.event import Event
            from database.session import db_session
            from sqlalchemy import and_

            # Check if event with this Stripe event ID already exists
            with db_session() as session:
                existing_event = (
                    session.query(Event)
                    .filter(Event.data.op("->>")("id") == event_id)
                    .first()
                )

                if existing_event:
                    logger.info(
                        f"Duplicate Stripe event detected: {event_id} "
                        f"(existing event ID: {existing_event.id})"
                    )
                    return True

                # Additional check with idempotency key if provided
                if idempotency_key:
                    existing_by_key = (
                        session.query(Event)
                        .filter(
                            Event.data.op("->>")("idempotency_key") == idempotency_key
                        )
                        .first()
                    )

                    if existing_by_key:
                        logger.info(
                            f"Duplicate event detected by idempotency key: {idempotency_key} "
                            f"(existing event ID: {existing_by_key.id})"
                        )
                        return True

                logger.debug(f"Event {event_id} is not a duplicate")
                return False

        except Exception as e:
            logger.error(f"Error checking for duplicate event {event_id}: {e}")
            # In case of error, assume it's not a duplicate to avoid blocking valid events
            # This is a fail-safe approach - better to process a duplicate than miss an event
            return False

    def extract_event_metadata(self, stripe_event: dict) -> dict:
        """
        Extract useful metadata from Stripe event for logging and monitoring.
        Enhanced for invoice events with additional subscription payment details.

        Args:
            stripe_event: Parsed Stripe event data

        Returns:
            dict: Event metadata
        """
        metadata = {
            "event_id": stripe_event.get("id"),
            "event_type": stripe_event.get("type"),
            "created": stripe_event.get("created"),
            "livemode": stripe_event.get("livemode"),
            "api_version": stripe_event.get("api_version"),
            "pending_webhooks": stripe_event.get("pending_webhooks"),
            "object_id": stripe_event.get("data", {}).get("object", {}).get("id"),
            "object_type": stripe_event.get("data", {}).get("object", {}).get("object"),
        }

        # Add invoice-specific metadata for Phase 1 events
        event_type = stripe_event.get("type", "")
        if event_type.startswith("invoice."):
            invoice_data = stripe_event.get("data", {}).get("object", {})
            metadata.update(
                {
                    "invoice_id": invoice_data.get("id"),
                    "customer_id": invoice_data.get("customer"),
                    "subscription_id": invoice_data.get("subscription"),
                    "invoice_status": invoice_data.get("status"),
                    "amount_due": invoice_data.get("amount_due"),
                    "amount_paid": invoice_data.get("amount_paid"),
                    "currency": invoice_data.get("currency"),
                    "payment_intent": invoice_data.get("payment_intent"),
                }
            )

        return metadata

    def generate_idempotency_key(self, stripe_event: dict) -> str:
        """
        Generate a consistent idempotency key for Stripe events.

        This creates a deterministic key based on event content to ensure
        the same event always generates the same key, enabling proper
        duplicate detection even if Stripe sends the same event multiple times.

        Args:
            stripe_event: Parsed Stripe event data

        Returns:
            str: Idempotency key for the event
        """
        import hashlib
        import json

        # Create a consistent representation of the event for hashing
        key_data = {
            "id": stripe_event.get("id"),
            "type": stripe_event.get("type"),
            "created": stripe_event.get("created"),
            "livemode": stripe_event.get("livemode"),
        }

        # Add object-specific data for more precise deduplication
        event_object = stripe_event.get("data", {}).get("object", {})
        if event_object:
            key_data["object_id"] = event_object.get("id")
            key_data["object_type"] = event_object.get("object")

            # For invoice events, include amount and status for precision
            if stripe_event.get("type", "").startswith("invoice."):
                key_data.update(
                    {
                        "amount_due": event_object.get("amount_due"),
                        "amount_paid": event_object.get("amount_paid"),
                        "status": event_object.get("status"),
                    }
                )

        # Create deterministic hash
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()[:32]


# Global service instance
stripe_webhook_service = StripeWebhookService()
