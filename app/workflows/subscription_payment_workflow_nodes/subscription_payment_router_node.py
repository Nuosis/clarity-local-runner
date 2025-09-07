"""
Subscription Payment Router Node

This node routes subscription payment processing based on payment success/failure
status from Stripe invoice webhook events.
"""

import logging
from typing import Any, Dict

from core.nodes.base import Node
from core.task import TaskContext
from schemas.subscription_payment_schema import SubscriptionPaymentEventSchema


class SubscriptionPaymentRouterNode(Node):
    """
    Routes subscription payment processing based on success/failure status.

    This node handles routing decisions for subscription payment events:
    - Routes successful payments to accounting updates
    - Routes failed payments to failure handling
    - Provides routing metadata for workflow orchestration

    Key Features:
    - Simple binary routing (success/failure)
    - No retry logic (handled by Stripe)
    - Comprehensive logging and error handling
    - Routing decision metadata for downstream nodes
    """

    async def process(self, task_context: TaskContext) -> TaskContext:
        """
        Process subscription payment routing based on event type.

        Args:
            task_context: Contains SubscriptionPaymentEventSchema and RecordSubscriptionPaymentNode results

        Returns:
            Updated TaskContext with routing decisions
        """
        try:
            logging.info(f"Starting {self.node_name} routing")

            # Extract payment event from context
            payment_event: SubscriptionPaymentEventSchema = task_context.event

            # Get results from previous node (RecordSubscriptionPaymentNode)
            record_results = task_context.nodes.get("RecordSubscriptionPaymentNode", {})

            # Initialize routing results
            routing_results = {
                "success": False,
                "routing_decision": None,
                "next_action": None,
                "workflow_complete": False,
                "error": None,
            }

            # Check if payment recording was successful
            if not record_results.get("success", False):
                # If payment recording failed, route to failure handling
                routing_decision = await self._route_to_failure_handling(
                    payment_event,
                    "Payment recording failed",
                    record_results.get("error", "Unknown recording error"),
                )
                routing_results.update(routing_decision)
                routing_results["success"] = True  # Routing itself succeeded

            elif record_results.get("duplicate_detected", False):
                # Duplicate payment detected - complete workflow successfully
                routing_decision = await self._route_to_completion(
                    payment_event,
                    "Duplicate payment detected - no further processing needed",
                )
                routing_results.update(routing_decision)
                routing_results["success"] = True

            else:
                # Payment was recorded successfully, route based on payment status
                if payment_event.is_payment_successful():
                    routing_decision = await self._route_successful_payment(
                        payment_event
                    )
                    routing_results.update(routing_decision)
                    routing_results["success"] = True

                elif payment_event.is_payment_failed():
                    routing_decision = await self._route_failed_payment(payment_event)
                    routing_results.update(routing_decision)
                    routing_results["success"] = True

                else:
                    # Unknown payment status
                    routing_decision = await self._route_to_failure_handling(
                        payment_event,
                        f"Unknown payment event type: {payment_event.event_type}",
                        f"Unsupported event type in subscription payment workflow",
                    )
                    routing_results.update(routing_decision)
                    routing_results["success"] = True

            # Store routing results in task context
            task_context.update_node(self.node_name, **routing_results)

            # Add routing metadata to task context for workflow engine
            task_context.metadata.update(
                {
                    "routing_decision": routing_results["routing_decision"],
                    "next_action": routing_results["next_action"],
                    "workflow_complete": routing_results["workflow_complete"],
                }
            )

            logging.info(
                f"Subscription payment routing completed. "
                f"Decision: {routing_results['routing_decision']}, "
                f"Next action: {routing_results['next_action']}"
            )

            return task_context

        except Exception as e:
            error_msg = f"Error in {self.node_name}: {str(e)}"
            logging.error(error_msg)

            # Route to failure handling on error
            task_context.update_node(
                self.node_name,
                success=False,
                error=error_msg,
                routing_decision="failure_handling",
                next_action="handle_failure",
                workflow_complete=True,
            )

            task_context.metadata.update(
                {
                    "routing_decision": "failure_handling",
                    "next_action": "handle_failure",
                    "workflow_complete": True,
                }
            )

            return task_context

    async def _route_successful_payment(
        self, payment_event: SubscriptionPaymentEventSchema
    ) -> Dict[str, Any]:
        """
        Route successful subscription payment to accounting update.

        Args:
            payment_event: Successful payment event

        Returns:
            Routing decision dictionary
        """
        logging.info(
            f"Routing successful subscription payment. "
            f"Amount: {payment_event.amount} {payment_event.currency}, "
            f"Invoice: {payment_event.invoice_id}"
        )

        return {
            "routing_decision": "accounting_update",
            "next_action": "update_accounting",
            "workflow_complete": False,
            "payment_status": "succeeded",
            "routing_reason": "Subscription payment succeeded - proceeding to accounting update",
            "routing_metadata": {
                "payment_amount": float(payment_event.amount),
                "payment_currency": payment_event.currency,
                "invoice_id": payment_event.invoice_id,
                "subscription_id": payment_event.subscription_id,
                "customer_id": payment_event.customer_id,
                "period_start": payment_event.period_start.isoformat(),
                "period_end": payment_event.period_end.isoformat(),
            },
        }

    async def _route_failed_payment(
        self, payment_event: SubscriptionPaymentEventSchema
    ) -> Dict[str, Any]:
        """
        Route failed subscription payment to failure handling.

        Args:
            payment_event: Failed payment event

        Returns:
            Routing decision dictionary
        """
        logging.info(
            f"Routing failed subscription payment. "
            f"Amount: {payment_event.amount} {payment_event.currency}, "
            f"Invoice: {payment_event.invoice_id}"
        )

        return {
            "routing_decision": "failure_handling",
            "next_action": "handle_failure",
            "workflow_complete": True,
            "payment_status": "failed",
            "routing_reason": "Subscription payment failed - proceeding to failure handling",
            "routing_metadata": {
                "failed_amount": float(payment_event.amount),
                "payment_currency": payment_event.currency,
                "invoice_id": payment_event.invoice_id,
                "subscription_id": payment_event.subscription_id,
                "customer_id": payment_event.customer_id,
                "invoice_status": payment_event.invoice_status,
                "failure_context": "subscription_payment_failed",
            },
        }

    async def _route_to_failure_handling(
        self,
        payment_event: SubscriptionPaymentEventSchema,
        reason: str,
        error_details: str,
    ) -> Dict[str, Any]:
        """
        Route to failure handling for errors or unknown states.

        Args:
            payment_event: Payment event
            reason: High-level reason for failure routing
            error_details: Detailed error information

        Returns:
            Routing decision dictionary
        """
        logging.warning(
            f"Routing to failure handling. Reason: {reason}, Details: {error_details}"
        )

        return {
            "routing_decision": "failure_handling",
            "next_action": "handle_failure",
            "workflow_complete": True,
            "payment_status": "error",
            "routing_reason": reason,
            "routing_metadata": {
                "error_details": error_details,
                "invoice_id": payment_event.invoice_id,
                "subscription_id": payment_event.subscription_id,
                "customer_id": payment_event.customer_id,
                "event_type": payment_event.event_type,
                "failure_context": "routing_error",
            },
        }

    async def _route_to_completion(
        self, payment_event: SubscriptionPaymentEventSchema, reason: str
    ) -> Dict[str, Any]:
        """
        Route to workflow completion (no further processing needed).

        Args:
            payment_event: Payment event
            reason: Reason for completion

        Returns:
            Routing decision dictionary
        """
        logging.info(f"Routing to completion. Reason: {reason}")

        return {
            "routing_decision": "completion",
            "next_action": "complete_workflow",
            "workflow_complete": True,
            "payment_status": "completed",
            "routing_reason": reason,
            "routing_metadata": {
                "completion_reason": reason,
                "invoice_id": payment_event.invoice_id,
                "subscription_id": payment_event.subscription_id,
                "customer_id": payment_event.customer_id,
                "event_type": payment_event.event_type,
            },
        }
