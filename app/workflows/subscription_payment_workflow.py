"""
Subscription Payment Processing Workflow

This module implements the SubscriptionPaymentWorkflow that orchestrates the processing
of Stripe invoice webhook events for subscription payments in Phase 1.
"""

from core.schema import NodeConfig, WorkflowSchema
from core.workflow import Workflow
from schemas.subscription_payment_schema import SubscriptionPaymentEventSchema

from workflows.payment_workflow_nodes.payment_failure_handling_node import (
    PaymentFailureHandlingNode,
)

# Import existing nodes that will be reused
from workflows.payment_workflow_nodes.update_accounting_node import UpdateAccountingNode

# Import workflow nodes (will be created in subsequent tasks)
from workflows.subscription_payment_workflow_nodes.record_subscription_payment_node import (
    RecordSubscriptionPaymentNode,
)
from workflows.subscription_payment_workflow_nodes.subscription_payment_router_node import (
    SubscriptionPaymentRouterNode,
)


class SubscriptionPaymentWorkflow(Workflow):
    """
    Subscription payment processing workflow for Cedar Heights Music Academy.

    This workflow handles Stripe invoice webhook events (invoice.payment_succeeded
    and invoice.payment_failed) for subscription payments. It provides a simplified
    approach focused solely on subscription payment processing.

    Workflow Flow:
    1. RecordSubscriptionPaymentNode - Records payment in DB with unique paymentId
    2. SubscriptionPaymentRouterNode - Routes based on payment success/failure
    3. UpdateAccountingNode - Updates accounting records (for successful payments)
    4. PaymentFailureHandlingNode - Handles failed payments (for failed payments)

    The workflow supports both successful and failed subscription payments with
    intelligent routing and comprehensive error handling.

    Usage:
        workflow = SubscriptionPaymentWorkflow()
        result = await workflow.run_async(subscription_payment_data)

        # Or for synchronous execution:
        result = workflow.run(subscription_payment_data)
    """

    workflow_schema = WorkflowSchema(
        description="Subscription payment processing workflow for Stripe invoice events",
        event_schema=SubscriptionPaymentEventSchema,
        start=RecordSubscriptionPaymentNode,
        nodes=[
            NodeConfig(
                node=RecordSubscriptionPaymentNode,
                connections=[SubscriptionPaymentRouterNode],
                description="Records subscription payment in database with unique paymentId to prevent duplicates",
            ),
            NodeConfig(
                node=SubscriptionPaymentRouterNode,
                connections=[UpdateAccountingNode, PaymentFailureHandlingNode],
                description="Routes subscription payment processing based on success/failure status",
            ),
            NodeConfig(
                node=UpdateAccountingNode,
                connections=[],
                description="Creates double-entry accounting records for successful subscription payments",
            ),
            NodeConfig(
                node=PaymentFailureHandlingNode,
                connections=[],
                description="Handles failed subscription payments with notifications and cleanup operations",
            ),
        ],
    )
