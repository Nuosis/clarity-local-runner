"""
Payment Router Node

This module implements the PaymentRouterNode workflow node that routes
payment processing based on payment status and business logic.
"""

import logging
from typing import Any, Dict, Optional

from core.nodes.base import Node
from core.task import TaskContext
from schemas.payment_schema import PaymentEventSchema, PaymentStatus

logger = logging.getLogger(__name__)


class PaymentRouterNode(Node):
    """
    Workflow node that routes payment processing based on status and business logic.

    This node handles:
    - Routing successful payments to accounting updates
    - Routing failed payments to failure handling
    - Routing pending payments to retry logic
    - Making routing decisions based on payment type
    - Setting up next workflow steps

    Input: PaymentEventSchema with payment results
    Output: Updated context with routing decisions
    """

    def __init__(self):
        super().__init__()
        self.name = "PaymentRouterNode"
        self.description = (
            "Routes payment processing based on status and business logic"
        )

    async def process(self, context: TaskContext) -> TaskContext:
        """
        Process the payment routing workflow step.

        Args:
            context: Task context containing payment results

        Returns:
            Updated task context with routing decisions
        """
        logger.info(f"Starting {self.name} processing")

        try:
            # Extract payment event data
            payment_event = PaymentEventSchema(**context.data)
            payment_status = context.data.get("payment_status", PaymentStatus.FAILED)

            logger.info(f"Routing payment with status: {payment_status}")

            # Make routing decisions based on payment status
            routing_decision = await self._make_routing_decision(
                context, payment_event, payment_status
            )

            # Update context with routing information
            context.data.update(routing_decision)

            # Store node result
            context.results[self.name] = {
                "success": True,
                "payment_status": payment_status,
                "next_action": routing_decision.get("next_action"),
                "requires_retry": routing_decision.get("requires_retry", False),
                "requires_failure_handling": routing_decision.get(
                    "requires_failure_handling", False
                ),
                "requires_accounting_update": routing_decision.get(
                    "requires_accounting_update", False
                ),
                "message": f"Payment routed for {routing_decision.get('next_action', 'completion')}",
            }

            logger.info(
                f"Payment routing completed: {routing_decision.get('next_action')}"
            )
            return context

        except Exception as e:
            error_msg = f"Unexpected error in {self.name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return self._handle_error(context, error_msg, "routing_error")

    async def _make_routing_decision(
        self,
        context: TaskContext,
        payment_event: PaymentEventSchema,
        payment_status: str,
    ) -> Dict[str, Any]:
        """
        Make routing decisions based on payment status and context.

        Args:
            context: Task context
            payment_event: Payment event data
            payment_status: Current payment status

        Returns:
            Dictionary with routing decisions
        """
        routing_decision = {
            "payment_status": payment_status,
            "requires_retry": False,
            "requires_failure_handling": False,
            "requires_accounting_update": False,
            "workflow_complete": False,
        }

        if payment_status == PaymentStatus.SUCCEEDED:
            # Payment succeeded - route to accounting update
            routing_decision.update(
                {
                    "next_action": "update_accounting",
                    "requires_accounting_update": True,
                    "workflow_complete": False,
                    "success_type": self._determine_success_type(context),
                }
            )

        elif payment_status == PaymentStatus.FAILED:
            # Payment failed - determine if retry is possible
            retry_decision = await self._should_retry_payment(context, payment_event)

            if retry_decision["should_retry"]:
                routing_decision.update(
                    {
                        "next_action": "retry_payment",
                        "requires_retry": True,
                        "retry_count": retry_decision["retry_count"],
                        "retry_delay": retry_decision["retry_delay"],
                        "workflow_complete": False,
                    }
                )
            else:
                routing_decision.update(
                    {
                        "next_action": "handle_failure",
                        "requires_failure_handling": True,
                        "workflow_complete": True,
                        "failure_reason": context.data.get(
                            "error_message", "Payment failed"
                        ),
                    }
                )

        elif payment_status == PaymentStatus.PENDING:
            # Payment pending - set up monitoring
            routing_decision.update(
                {
                    "next_action": "monitor_payment",
                    "requires_monitoring": True,
                    "workflow_complete": False,
                    "monitoring_timeout": self._calculate_monitoring_timeout(context),
                }
            )

        elif payment_status == PaymentStatus.PROCESSING:
            # Payment processing - wait and monitor
            routing_decision.update(
                {
                    "next_action": "wait_for_processing",
                    "requires_monitoring": True,
                    "workflow_complete": False,
                    "processing_timeout": 300,  # 5 minutes
                }
            )

        elif payment_status == PaymentStatus.CANCELLED:
            # Payment cancelled - handle as failure without retry
            routing_decision.update(
                {
                    "next_action": "handle_cancellation",
                    "requires_failure_handling": True,
                    "workflow_complete": True,
                    "failure_reason": "Payment was cancelled",
                }
            )

        else:
            # Unknown status - treat as failure
            routing_decision.update(
                {
                    "next_action": "handle_unknown_status",
                    "requires_failure_handling": True,
                    "workflow_complete": True,
                    "failure_reason": f"Unknown payment status: {payment_status}",
                }
            )

        return routing_decision

    async def _should_retry_payment(
        self, context: TaskContext, payment_event: PaymentEventSchema
    ) -> Dict[str, Any]:
        """
        Determine if payment should be retried based on error type and retry count.

        Args:
            context: Task context
            payment_event: Payment event data

        Returns:
            Dictionary with retry decision
        """
        current_retry_count = context.data.get("retry_count", 0)
        max_retries = 3  # Maximum number of retry attempts

        # Check if we've exceeded max retries
        if current_retry_count >= max_retries:
            return {
                "should_retry": False,
                "reason": "Maximum retry attempts exceeded",
                "retry_count": current_retry_count,
            }

        # Check error type to determine if retry is appropriate
        error_code = context.data.get("error_code", "")
        decline_code = context.data.get("decline_code", "")

        # Retryable error codes
        retryable_errors = [
            "card_declined",
            "processing_error",
            "temporary_failure",
            "rate_limit",
            "api_connection_error",
            "api_error",
        ]

        # Non-retryable decline codes
        non_retryable_declines = [
            "insufficient_funds",
            "stolen_card",
            "lost_card",
            "pickup_card",
            "restricted_card",
            "security_violation",
            "invalid_account",
            "card_not_supported",
        ]

        # Don't retry if decline code indicates permanent failure
        if decline_code in non_retryable_declines:
            return {
                "should_retry": False,
                "reason": f"Non-retryable decline code: {decline_code}",
                "retry_count": current_retry_count,
            }

        # Retry if error code is retryable or if it's a generic failure
        should_retry = error_code in retryable_errors or not error_code

        if should_retry:
            # Calculate retry delay (exponential backoff)
            retry_delay = min(60 * (2**current_retry_count), 300)  # Max 5 minutes

            return {
                "should_retry": True,
                "retry_count": current_retry_count + 1,
                "retry_delay": retry_delay,
                "reason": f"Retryable error: {error_code or 'generic_failure'}",
            }
        else:
            return {
                "should_retry": False,
                "reason": f"Non-retryable error: {error_code}",
                "retry_count": current_retry_count,
            }

    def _determine_success_type(self, context: TaskContext) -> str:
        """
        Determine the type of successful payment for routing purposes.

        Args:
            context: Task context

        Returns:
            Success type string
        """
        if context.data.get("subscription_id"):
            return "subscription_payment"
        else:
            return "one_time_payment"

    def _calculate_monitoring_timeout(self, context: TaskContext) -> int:
        """
        Calculate how long to monitor a pending payment.

        Args:
            context: Task context

        Returns:
            Timeout in seconds
        """
        # Different timeouts based on payment method
        payment_method_type = context.data.get("payment_method", {}).get("type", "card")

        if payment_method_type == "bank_account":
            return 3600  # 1 hour for bank transfers
        elif payment_method_type == "digital_wallet":
            return 600  # 10 minutes for digital wallets
        else:
            return 300  # 5 minutes for cards

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

        # Route to failure handling
        context.data["next_action"] = "handle_failure"
        context.data["requires_failure_handling"] = True
        context.data["workflow_complete"] = True

        context.results[self.name] = {
            "success": False,
            "error_code": error_code,
            "error_message": error_message,
            "next_action": "handle_failure",
        }

        return context

    def validate_input(self, context: TaskContext) -> bool:
        """
        Validate that the context contains required data for routing.

        Args:
            context: Task context to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            # Validate payment event schema
            PaymentEventSchema(**context.data)

            # Check that payment processing has been attempted
            if "payment_status" not in context.data:
                logger.error("Missing payment_status for routing")
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
        return {}  # No external configuration required

    def get_output_schema(self) -> Dict[str, Any]:
        """
        Get the output schema for this node.

        Returns:
            Dictionary describing the output data structure
        """
        return {
            "next_action": "str - Next action to take (update_accounting, retry_payment, handle_failure, etc.)",
            "requires_retry": "bool - Whether payment should be retried",
            "requires_failure_handling": "bool - Whether failure handling is needed",
            "requires_accounting_update": "bool - Whether accounting update is needed",
            "requires_monitoring": "bool - Whether payment monitoring is needed",
            "workflow_complete": "bool - Whether the workflow is complete",
            "retry_count": "int - Number of retry attempts",
            "retry_delay": "int - Delay before retry in seconds",
            "success_type": "str - Type of successful payment",
            "failure_reason": "str - Reason for failure if applicable",
            "monitoring_timeout": "int - Timeout for monitoring in seconds",
        }
