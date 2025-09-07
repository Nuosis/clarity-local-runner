"""
Payment Processing Workflow

This module implements the main PaymentWorkflow that orchestrates the complete
payment processing workflow using the GenAI Launchpad workflow framework.
"""

from core.schema import NodeConfig, WorkflowSchema
from core.workflow import Workflow
from schemas.payment_schema import PaymentEventSchema

# Import all payment workflow nodes
from workflows.payment_workflow_nodes.create_stripe_customer_node import (
    CreateStripeCustomerNode,
)
from workflows.payment_workflow_nodes.create_subscription_node import (
    CreateSubscriptionNode,
)
from workflows.payment_workflow_nodes.payment_failure_handling_node import (
    PaymentFailureHandlingNode,
)
from workflows.payment_workflow_nodes.payment_router_node import PaymentRouterNode
from workflows.payment_workflow_nodes.process_payment_node import ProcessPaymentNode
from workflows.payment_workflow_nodes.update_accounting_node import UpdateAccountingNode


class PaymentWorkflow(Workflow):
    """
    Complete payment processing workflow for Cedar Heights Music Academy.

    This workflow orchestrates the entire payment processing chain:
    1. CreateStripeCustomerNode - Creates or retrieves Stripe customer
    2. CreateSubscriptionNode - Creates subscription if needed
    3. ProcessPaymentNode - Processes the actual payment
    4. PaymentRouterNode - Routes based on payment status
    5. PaymentFailureHandlingNode - Handles failures (conditional)
    6. UpdateAccountingNode - Updates accounting records (conditional)

    The workflow supports both one-time payments and subscription payments,
    with intelligent routing based on payment results and comprehensive
    error handling throughout the process.

    Usage:
        workflow = PaymentWorkflow()
        result = await workflow.run_async(payment_data)

        # Or for synchronous execution:
        result = workflow.run(payment_data)
    """

    workflow_schema = WorkflowSchema(
        description="Complete payment processing workflow with Stripe integration and accounting updates",
        event_schema=PaymentEventSchema,
        start=CreateStripeCustomerNode,
        nodes=[
            NodeConfig(
                node=CreateStripeCustomerNode,
                connections=[CreateSubscriptionNode],
                description="Creates or retrieves Stripe customer and updates database with customer ID",
            ),
            NodeConfig(
                node=CreateSubscriptionNode,
                connections=[ProcessPaymentNode],
                description="Creates Stripe subscription with trial periods and recurring billing setup",
            ),
            NodeConfig(
                node=ProcessPaymentNode,
                connections=[PaymentRouterNode],
                description="Processes both one-time and subscription payments using Stripe payment intents",
            ),
            NodeConfig(
                node=PaymentRouterNode,
                connections=[PaymentFailureHandlingNode, UpdateAccountingNode],
                description="Routes payment processing based on status with intelligent retry logic and failure handling decisions",
            ),
            NodeConfig(
                node=PaymentFailureHandlingNode,
                connections=[],
                description="Handles payment failures with comprehensive notification system and cleanup operations",
            ),
            NodeConfig(
                node=UpdateAccountingNode,
                connections=[],
                description="Creates double-entry accounting records with tax calculations and audit trails",
            ),
        ],
    )
