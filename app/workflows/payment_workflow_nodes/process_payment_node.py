"""
Process Payment Node

This module implements the ProcessPaymentNode workflow node that handles
payment processing for both one-time payments and subscription payments.
"""

import logging
import os
from decimal import Decimal
from typing import Any, Dict, Optional

import stripe
from core.nodes.base import Node
from core.task import TaskContext
from database.session import db_session
from models.user import User
from schemas.payment_schema import PaymentEventSchema, PaymentStatus
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ProcessPaymentNode(Node):
    """
    Workflow node that processes payments through Stripe.

    This node handles:
    - Creating payment intents for one-time payments
    - Processing subscription payments
    - Handling payment method confirmation
    - Managing payment failures and retries
    - Recording payment transactions

    Input: PaymentEventSchema with payment information
    Output: Updated context with payment results
    """

    def __init__(self):
        super().__init__()
        self.name = "ProcessPaymentNode"
        self.description = "Processes payments through Stripe payment intents"

        # Initialize Stripe with API key
        stripe_secret_key = os.getenv("STRIPE_SECRET_KEY")
        if stripe_secret_key:
            stripe.api_key = stripe_secret_key
        else:
            logger.warning(
                "STRIPE_SECRET_KEY not configured - Stripe operations will fail"
            )

    async def process(self, context: TaskContext) -> TaskContext:
        """
        Process the payment workflow step.

        Args:
            context: Task context containing payment event data

        Returns:
            Updated task context with payment results
        """
        logger.info(f"Starting {self.name} processing")

        try:
            # Extract payment event data
            payment_event = PaymentEventSchema(**context.data)
            logger.info(
                f"Processing payment for customer {context.data.get('stripe_customer_id')}"
            )

            # Validate required data
            if not context.data.get("stripe_customer_id"):
                raise ValueError(
                    "stripe_customer_id is required for payment processing"
                )

            # Determine payment type and process accordingly
            if context.data.get("subscription_id"):
                # Handle subscription payment
                payment_result = await self._process_subscription_payment(
                    context, payment_event
                )
            else:
                # Handle one-time payment
                payment_result = await self._process_one_time_payment(
                    context, payment_event
                )

            # Update context with payment results
            context.data.update(payment_result)

            # Store node result
            context.results[self.name] = {
                "success": payment_result.get("payment_status")
                == PaymentStatus.SUCCEEDED,
                "payment_intent_id": payment_result.get("payment_intent_id"),
                "payment_status": payment_result.get("payment_status"),
                "amount_paid": payment_result.get("amount_paid"),
                "message": "Payment processed successfully"
                if payment_result.get("payment_status") == PaymentStatus.SUCCEEDED
                else "Payment processing failed",
            }

            logger.info(
                f"Payment processing completed with status: {payment_result.get('payment_status')}"
            )
            return context

        except stripe.error.StripeError as e:
            error_msg = f"Stripe API error in {self.name}: {str(e)}"
            logger.error(error_msg)
            return self._handle_error(context, error_msg, "stripe_api_error")

        except Exception as e:
            error_msg = f"Unexpected error in {self.name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return self._handle_error(context, error_msg, "unexpected_error")

    async def _process_one_time_payment(
        self, context: TaskContext, payment_event: PaymentEventSchema
    ) -> Dict[str, Any]:
        """
        Process a one-time payment using payment intents.

        Args:
            context: Task context
            payment_event: Payment event data

        Returns:
            Dictionary with payment results
        """
        try:
            # Create payment intent
            payment_intent_data = {
                "amount": int(payment_event.amount * 100),  # Convert to cents
                "currency": payment_event.currency,
                "customer": context.data["stripe_customer_id"],
                "metadata": {
                    "user_id": str(payment_event.user_id),
                    "source": "cedar_heights_music_academy",
                    "payment_type": "one_time",
                },
            }

            # Add payment method if provided
            if payment_event.payment_method_id:
                payment_intent_data["payment_method"] = payment_event.payment_method_id
                payment_intent_data["confirmation_method"] = "manual"
                payment_intent_data["confirm"] = True
            else:
                payment_intent_data["confirmation_method"] = "automatic"

            # Add description
            payment_intent_data["description"] = f"Payment for {payment_event.name}"

            # Add custom metadata if provided
            if payment_event.metadata:
                payment_intent_data["metadata"].update(payment_event.metadata)

            # Set idempotency key if provided
            idempotency_key = (
                payment_event.idempotency_key
                or f"payment_{payment_event.user_id}_{int(payment_event.amount * 100)}"
            )

            # Create payment intent
            payment_intent = stripe.PaymentIntent.create(
                **payment_intent_data, idempotency_key=idempotency_key
            )

            # Process payment result
            return await self._process_payment_intent_result(
                payment_intent, payment_event
            )

        except stripe.error.StripeError as e:
            logger.error(f"Failed to process one-time payment: {str(e)}")
            return {
                "payment_status": PaymentStatus.FAILED,
                "error_code": e.code if hasattr(e, "code") else "stripe_error",
                "error_message": str(e),
            }

    async def _process_subscription_payment(
        self, context: TaskContext, payment_event: PaymentEventSchema
    ) -> Dict[str, Any]:
        """
        Process a subscription payment.

        Args:
            context: Task context
            payment_event: Payment event data

        Returns:
            Dictionary with payment results
        """
        try:
            subscription_id = context.data["subscription_id"]

            # Retrieve subscription to check status
            subscription = stripe.Subscription.retrieve(subscription_id)

            if subscription.status == "incomplete":
                # Handle incomplete subscription
                return await self._handle_incomplete_subscription(
                    subscription, payment_event
                )
            elif subscription.status == "active":
                # Subscription is active, return success
                return {
                    "payment_status": PaymentStatus.SUCCEEDED,
                    "subscription_id": subscription_id,
                    "subscription_status": subscription.status,
                    "amount_paid": Decimal(
                        str(subscription.items.data[0].price.unit_amount / 100)
                    ),
                    "currency": subscription.items.data[0].price.currency,
                }
            else:
                # Handle other subscription statuses
                return {
                    "payment_status": PaymentStatus.FAILED,
                    "subscription_id": subscription_id,
                    "subscription_status": subscription.status,
                    "error_message": f"Subscription status is {subscription.status}",
                }

        except stripe.error.StripeError as e:
            logger.error(f"Failed to process subscription payment: {str(e)}")
            return {
                "payment_status": PaymentStatus.FAILED,
                "error_code": e.code if hasattr(e, "code") else "stripe_error",
                "error_message": str(e),
            }

    async def _handle_incomplete_subscription(
        self, subscription: stripe.Subscription, payment_event: PaymentEventSchema
    ) -> Dict[str, Any]:
        """
        Handle incomplete subscription that requires payment confirmation.

        Args:
            subscription: Stripe subscription object
            payment_event: Payment event data

        Returns:
            Dictionary with payment results
        """
        try:
            # Get the latest invoice
            latest_invoice = subscription.latest_invoice
            if not latest_invoice:
                return {
                    "payment_status": PaymentStatus.FAILED,
                    "error_message": "No invoice found for incomplete subscription",
                }

            # Get payment intent from invoice
            if (
                hasattr(latest_invoice, "payment_intent")
                and latest_invoice.payment_intent
            ):
                payment_intent = latest_invoice.payment_intent

                # If payment method is provided, confirm the payment intent
                if payment_event.payment_method_id:
                    payment_intent = stripe.PaymentIntent.confirm(
                        payment_intent.id,
                        payment_method=payment_event.payment_method_id,
                    )

                return await self._process_payment_intent_result(
                    payment_intent, payment_event
                )
            else:
                return {
                    "payment_status": PaymentStatus.FAILED,
                    "error_message": "No payment intent found for subscription invoice",
                }

        except stripe.error.StripeError as e:
            logger.error(f"Failed to handle incomplete subscription: {str(e)}")
            return {
                "payment_status": PaymentStatus.FAILED,
                "error_code": e.code if hasattr(e, "code") else "stripe_error",
                "error_message": str(e),
            }

    async def _process_payment_intent_result(
        self, payment_intent: stripe.PaymentIntent, payment_event: PaymentEventSchema
    ) -> Dict[str, Any]:
        """
        Process the result of a payment intent.

        Args:
            payment_intent: Stripe payment intent object
            payment_event: Payment event data

        Returns:
            Dictionary with payment results
        """
        result = {
            "payment_intent_id": payment_intent.id,
            "amount_paid": Decimal(str(payment_intent.amount / 100)),
            "currency": payment_intent.currency,
        }

        if payment_intent.status == "succeeded":
            result["payment_status"] = PaymentStatus.SUCCEEDED
            result["charge_id"] = (
                payment_intent.charges.data[0].id
                if payment_intent.charges.data
                else None
            )
            result["receipt_url"] = (
                payment_intent.charges.data[0].receipt_url
                if payment_intent.charges.data
                else None
            )

        elif payment_intent.status == "requires_payment_method":
            result["payment_status"] = PaymentStatus.FAILED
            result["error_message"] = "Payment method required"
            result["client_secret"] = payment_intent.client_secret

        elif payment_intent.status == "requires_confirmation":
            result["payment_status"] = PaymentStatus.PENDING
            result["client_secret"] = payment_intent.client_secret

        elif payment_intent.status == "requires_action":
            result["payment_status"] = PaymentStatus.PENDING
            result["client_secret"] = payment_intent.client_secret
            result["next_action"] = payment_intent.next_action

        elif payment_intent.status == "processing":
            result["payment_status"] = PaymentStatus.PROCESSING

        elif payment_intent.status == "canceled":
            result["payment_status"] = PaymentStatus.CANCELLED

        else:
            result["payment_status"] = PaymentStatus.FAILED
            result["error_message"] = (
                f"Unknown payment intent status: {payment_intent.status}"
            )

        # Add error details if payment failed
        if payment_intent.last_payment_error:
            error = payment_intent.last_payment_error
            result["error_code"] = error.code
            result["error_message"] = error.message
            result["decline_code"] = error.decline_code

        return result

    def _handle_error(
        self, context: TaskContext, error_message: str, error_code: str
    ) -> TaskContext:
        """
        Handle errors and update context with error information.

        Args:
            context: Task context to update
            error_message: Error message
            error_code: Error code for categorization

        Returns:
            Updated context with error information
        """
        context.data["error"] = True
        context.data["error_message"] = error_message
        context.data["error_code"] = error_code
        context.data["payment_status"] = PaymentStatus.FAILED

        context.results[self.name] = {
            "success": False,
            "error_code": error_code,
            "error_message": error_message,
            "payment_status": PaymentStatus.FAILED,
        }

        return context

    def validate_input(self, context: TaskContext) -> bool:
        """
        Validate that the context contains required data for payment processing.

        Args:
            context: Task context to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            # Validate payment event schema
            PaymentEventSchema(**context.data)

            # Check required fields
            required_fields = ["stripe_customer_id", "amount"]
            for field in required_fields:
                if field not in context.data or not context.data[field]:
                    logger.error(
                        f"Missing required field for payment processing: {field}"
                    )
                    return False

            # Validate amount
            if context.data["amount"] <= 0:
                logger.error("Payment amount must be greater than 0")
                return False

            # Validate Stripe configuration
            stripe_secret_key = os.getenv("STRIPE_SECRET_KEY")
            if not stripe_secret_key:
                logger.error("STRIPE_SECRET_KEY not configured")
                return False

            return True

        except Exception as e:
            logger.error(f"Input validation failed: {str(e)}")
            return False

    def get_required_config(self) -> Dict[str, Any]:
        """
        Get required configuration for this node.

        Returns:
            Dictionary of required configuration keys and descriptions
        """
        return {"STRIPE_SECRET_KEY": "Stripe secret API key for payment processing"}

    def get_output_schema(self) -> Dict[str, Any]:
        """
        Get the output schema for this node.

        Returns:
            Dictionary describing the output data structure
        """
        return {
            "payment_intent_id": "str - Stripe payment intent ID",
            "payment_status": "str - Payment status (succeeded, failed, pending, etc.)",
            "charge_id": "str - Stripe charge ID if payment succeeded",
            "amount_paid": "Decimal - Amount actually paid",
            "currency": "str - Payment currency",
            "receipt_url": "str - Receipt URL if available",
            "client_secret": "str - Client secret for frontend confirmation",
            "error": "bool - Whether an error occurred",
            "error_message": "str - Error message if error occurred",
            "error_code": "str - Error code for categorization",
            "decline_code": "str - Card decline code if applicable",
        }
