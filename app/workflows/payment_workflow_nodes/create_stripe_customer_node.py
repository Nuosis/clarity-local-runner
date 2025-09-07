"""
Create Stripe Customer Node

This node handles creating or retrieving Stripe customers and updating
the database with the Stripe customer ID.
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


class CreateStripeCustomerNode(Node):
    """
    Node for creating or retrieving Stripe customers.

    This node:
    1. Initializes Stripe with the API key
    2. Checks if customer already exists in Stripe
    3. Creates new customer if needed
    4. Updates database with Stripe customer ID
    5. Handles errors gracefully with rollback
    """

    name = "CreateStripeCustomerNode"
    description = (
        "Creates or retrieves Stripe customer and updates database with customer ID"
    )

    def get_required_config(self) -> Dict[str, Any]:
        """Return required configuration for this node."""
        return {"STRIPE_SECRET_KEY": "Stripe secret API key for payment processing"}

    def get_output_schema(self) -> Dict[str, Any]:
        """Return the output schema for this node."""
        return {
            "stripe_customer_id": "string",
            "customer_created": "boolean",
            "customer_email": "string",
            "error": "boolean",
            "error_message": "string",
        }

    async def process(self, context: TaskContext) -> TaskContext:
        """
        Process the Stripe customer creation workflow step.

        Args:
            context: Task context containing payment event data

        Returns:
            Updated task context with Stripe customer information
        """
        logger.info("Starting Stripe customer creation process")

        try:
            # Validate input data
            payment_event = PaymentEventSchema(**context.event)

            # Initialize Stripe
            stripe_secret_key = os.getenv("STRIPE_SECRET_KEY")
            if not stripe_secret_key:
                raise ValueError("STRIPE_SECRET_KEY environment variable not set")

            stripe.api_key = stripe_secret_key

            # Extract customer information
            user_id = payment_event.user_id
            email = payment_event.email
            name = payment_event.name
            phone = getattr(payment_event, "phone", None)

            logger.info(
                f"Processing Stripe customer for user {user_id}, email: {email}"
            )

            # Check if user already has a Stripe customer ID
            with db_session() as db:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    raise ValueError(f"User with ID {user_id} not found")

                existing_stripe_customer_id = getattr(user, "stripe_customer_id", None)

                if existing_stripe_customer_id:
                    # Verify customer exists in Stripe
                    try:
                        customer = stripe.Customer.retrieve(existing_stripe_customer_id)
                        logger.info(
                            f"Found existing Stripe customer: {existing_stripe_customer_id}"
                        )

                        # Update context with existing customer info
                        context.nodes[self.name] = {
                            "success": True,
                            "stripe_customer_id": existing_stripe_customer_id,
                            "customer_created": False,
                            "customer_email": customer.email,
                            "message": "Using existing Stripe customer",
                        }

                        return context

                    except stripe.error.InvalidRequestError:
                        logger.warning(
                            f"Stripe customer {existing_stripe_customer_id} not found, creating new one"
                        )
                        # Continue to create new customer

                # Create new Stripe customer
                customer_data = {
                    "email": email,
                    "name": name,
                    "metadata": {
                        "user_id": str(user_id),
                        "source": "cedar_heights_music_academy",
                    },
                }

                if phone:
                    customer_data["phone"] = phone

                logger.info("Creating new Stripe customer")
                customer = stripe.Customer.create(**customer_data)

                # Update user with Stripe customer ID
                user.stripe_customer_id = customer.id
                db.commit()

                logger.info(f"Successfully created Stripe customer: {customer.id}")

                # Update context with success info
                context.nodes[self.name] = {
                    "success": True,
                    "stripe_customer_id": customer.id,
                    "customer_created": True,
                    "customer_email": customer.email,
                    "message": "Successfully created new Stripe customer",
                }

                return context

        except stripe.error.StripeError as e:
            error_msg = f"Stripe API error: {str(e)}"
            logger.error(error_msg)

            context.nodes[self.name] = {
                "success": False,
                "error": True,
                "error_message": error_msg,
                "error_code": "stripe_api_error",
            }

            return context

        except Exception as e:
            error_msg = f"Customer creation failed: {str(e)}"
            logger.error(error_msg, exc_info=True)

            context.nodes[self.name] = {
                "success": False,
                "error": True,
                "error_message": error_msg,
                "error_code": "customer_creation_error",
            }

            return context


# Example usage for testing
async def example_create_stripe_customer():
    """Example of how to use the CreateStripeCustomerNode."""
    from core.task import TaskContext

    # Mock payment event data
    payment_data = {
        "user_id": "123e4567-e89b-12d3-a456-426614174000",
        "email": "john.doe@example.com",
        "name": "John Doe",
        "phone": "+1-555-123-4567",
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

    # Create task context
    context = TaskContext(event=payment_data, nodes={}, metadata={})

    # Process node
    node = CreateStripeCustomerNode()
    result_context = await node.process(context)

    print("=== Create Stripe Customer Node Result ===")
    print(f"Node Results: {result_context.nodes}")

    return result_context


if __name__ == "__main__":
    import asyncio

    asyncio.run(example_create_stripe_customer())
