"""
Create Subscription Node

This node handles creating Stripe subscriptions with trial periods
and recurring billing setup.
"""

import logging
import os
from typing import Any, Dict

import stripe
from core.nodes.base import Node
from core.task import TaskContext
from database.session import db_session
from models.user import User
from schemas.payment_schema import PaymentEventSchema

logger = logging.getLogger(__name__)


class CreateSubscriptionNode(Node):
    """
    Node for creating Stripe subscriptions.

    This node:
    1. Validates subscription plan data
    2. Creates Stripe subscription with trial period
    3. Sets up recurring billing
    4. Updates database with subscription information
    5. Handles errors gracefully
    """

    name = "CreateSubscriptionNode"
    description = (
        "Creates Stripe subscription with trial periods and recurring billing setup"
    )

    def get_required_config(self) -> Dict[str, Any]:
        """Return required configuration for this node."""
        return {"STRIPE_SECRET_KEY": "Stripe secret API key for payment processing"}

    def get_output_schema(self) -> Dict[str, Any]:
        """Return the output schema for this node."""
        return {
            "subscription_id": "string",
            "subscription_status": "string",
            "trial_end": "string",
            "current_period_end": "string",
            "error": "boolean",
            "error_message": "string",
        }

    async def process(self, context: TaskContext) -> TaskContext:
        """
        Process the subscription creation workflow step.

        Args:
            context: Task context containing payment event data

        Returns:
            Updated task context with subscription information
        """
        logger.info("Starting subscription creation process")

        try:
            # Validate input data
            payment_event = PaymentEventSchema(**context.event)

            # Check if subscription plan is provided
            if not payment_event.subscription_plan:
                logger.info(
                    "No subscription plan provided, skipping subscription creation"
                )
                context.nodes[self.name] = {
                    "success": True,
                    "skipped": True,
                    "message": "No subscription plan provided",
                }
                return context

            # Initialize Stripe
            stripe_secret_key = os.getenv("STRIPE_SECRET_KEY")
            if not stripe_secret_key:
                raise ValueError("STRIPE_SECRET_KEY environment variable not set")

            stripe.api_key = stripe_secret_key

            # Get Stripe customer ID from previous node
            create_customer_result = context.nodes.get("CreateStripeCustomerNode", {})
            stripe_customer_id = create_customer_result.get("stripe_customer_id")

            if not stripe_customer_id:
                raise ValueError("Stripe customer ID not found from previous step")

            subscription_plan = payment_event.subscription_plan
            logger.info(
                f"Creating subscription for customer {stripe_customer_id}, plan: {subscription_plan.plan_id}"
            )

            # Create or retrieve Stripe price
            price_data = {
                "unit_amount": int(subscription_plan.amount * 100),  # Convert to cents
                "currency": subscription_plan.currency.lower(),
                "recurring": {
                    "interval": subscription_plan.interval,
                    "interval_count": subscription_plan.interval_count,
                },
                "product_data": {
                    "name": subscription_plan.name,
                    "metadata": {
                        "plan_id": subscription_plan.plan_id,
                        "source": "cedar_heights_music_academy",
                    },
                },
            }

            # Create subscription
            subscription_data = {
                "customer": stripe_customer_id,
                "items": [{"price_data": price_data}],
                "metadata": {
                    "user_id": str(payment_event.user_id),
                    "plan_id": subscription_plan.plan_id,
                    "source": "cedar_heights_music_academy",
                },
            }

            # Add trial period if specified
            if (
                subscription_plan.trial_period_days
                and subscription_plan.trial_period_days > 0
            ):
                subscription_data["trial_period_days"] = (
                    subscription_plan.trial_period_days
                )
                logger.info(
                    f"Adding trial period: {subscription_plan.trial_period_days} days"
                )

            # Create the subscription
            subscription = stripe.Subscription.create(**subscription_data)

            logger.info(f"Successfully created subscription: {subscription.id}")

            # Update context with subscription info
            context.nodes[self.name] = {
                "success": True,
                "subscription_id": subscription.id,
                "subscription_status": subscription.status,
                "trial_end": subscription.trial_end,
                "current_period_end": subscription.current_period_end,
                "message": "Successfully created subscription",
            }

            return context

        except stripe.error.StripeError as e:
            error_msg = f"Stripe API error during subscription creation: {str(e)}"
            logger.error(error_msg)

            context.nodes[self.name] = {
                "success": False,
                "error": True,
                "error_message": error_msg,
                "error_code": "stripe_subscription_error",
            }

            return context

        except Exception as e:
            error_msg = f"Subscription creation failed: {str(e)}"
            logger.error(error_msg, exc_info=True)

            context.nodes[self.name] = {
                "success": False,
                "error": True,
                "error_message": error_msg,
                "error_code": "subscription_creation_error",
            }

            return context


# Example usage for testing
async def example_create_subscription():
    """Example of how to use the CreateSubscriptionNode."""
    from core.task import TaskContext

    # Mock payment event data with subscription
    payment_data = {
        "user_id": "123e4567-e89b-12d3-a456-426614174000",
        "email": "john.doe@example.com",
        "name": "John Doe",
        "amount": 99.99,
        "currency": "usd",
        "subscription_plan": {
            "plan_id": "music_lessons_monthly",
            "name": "Monthly Music Lessons",
            "amount": 99.99,
            "currency": "usd",
            "interval": "month",
            "interval_count": 1,
            "trial_period_days": 7,
        },
        "payment_method_id": "pm_1234567890",
    }

    # Create task context with mock customer creation result
    context = TaskContext(event=payment_data, nodes={}, metadata={})
    context.nodes["CreateStripeCustomerNode"] = {
        "success": True,
        "stripe_customer_id": "cus_test123",
        "customer_created": True,
    }

    # Process node
    node = CreateSubscriptionNode()
    result_context = await node.process(context)

    print("=== Create Subscription Node Result ===")
    print(f"Node Results: {result_context.nodes}")

    return result_context


if __name__ == "__main__":
    import asyncio

    asyncio.run(example_create_subscription())
