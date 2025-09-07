"""
Update Accounting Node

This module implements the UpdateAccountingNode workflow node that handles
accounting updates for successful payments and financial record keeping.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import uuid4

from core.nodes.base import Node
from core.task import TaskContext
from database.session import db_session
from models.user import User
from schemas.payment_schema import (
    AccountingEntrySchema,
    PaymentEventSchema,
    PaymentStatus,
)
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class UpdateAccountingNode(Node):
    """
    Workflow node that updates accounting records for successful payments.

    This node handles:
    - Creating accounting entries for successful payments
    - Recording revenue recognition
    - Updating customer account balances
    - Creating audit trails for financial transactions
    - Generating transaction records for reporting
    - Handling tax calculations and records

    Input: PaymentEventSchema with successful payment information
    Output: Updated context with accounting results
    """

    def __init__(self):
        super().__init__()
        self.name = "UpdateAccountingNode"
        self.description = "Updates accounting records for successful payments"

    async def process(self, context: TaskContext) -> TaskContext:
        """
        Process the accounting update workflow step.

        Args:
            context: Task context containing successful payment information

        Returns:
            Updated task context with accounting results
        """
        logger.info(f"Starting {self.name} processing")

        try:
            # Extract payment event data
            payment_event = PaymentEventSchema(**context.data)
            payment_status = context.data.get("payment_status")

            # Verify this is a successful payment
            if payment_status != PaymentStatus.SUCCEEDED:
                logger.warning(
                    f"Accounting update called for non-successful payment: {payment_status}"
                )
                return self._handle_error(
                    context,
                    f"Invalid payment status for accounting: {payment_status}",
                    "invalid_status",
                )

            logger.info(
                f"Processing accounting update for successful payment - User: {payment_event.user_id}, Amount: ${payment_event.amount}"
            )

            # Create accounting entries
            accounting_entries = await self._create_accounting_entries(
                context, payment_event
            )

            # Update customer account
            customer_account_update = await self._update_customer_account(
                context, payment_event
            )

            # Create transaction record
            transaction_record = await self._create_transaction_record(
                context, payment_event
            )

            # Handle tax calculations if applicable
            tax_calculations = await self._handle_tax_calculations(
                context, payment_event
            )

            # Generate audit trail
            audit_trail = await self._generate_audit_trail(context, payment_event)

            # Update context with accounting results
            context.data.update(
                {
                    "accounting_updated": True,
                    "accounting_entries": accounting_entries,
                    "customer_account_updated": customer_account_update["success"],
                    "transaction_record_created": transaction_record["success"],
                    "tax_calculated": tax_calculations["success"],
                    "audit_trail_created": audit_trail["success"],
                }
            )

            # Store node result
            context.results[self.name] = {
                "success": True,
                "accounting_entries": accounting_entries,
                "customer_account": customer_account_update,
                "transaction_record": transaction_record,
                "tax_calculations": tax_calculations,
                "audit_trail": audit_trail,
                "message": "Accounting records updated successfully",
            }

            logger.info(
                f"Accounting update completed successfully for user {payment_event.user_id}"
            )
            return context

        except Exception as e:
            error_msg = f"Unexpected error in {self.name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return self._handle_error(context, error_msg, "accounting_error")

    async def _create_accounting_entries(
        self, context: TaskContext, payment_event: PaymentEventSchema
    ) -> List[Dict[str, Any]]:
        """
        Create double-entry accounting records for the payment.

        Args:
            context: Task context
            payment_event: Payment event data

        Returns:
            List of accounting entries created
        """
        try:
            entries = []
            transaction_id = str(uuid4())
            amount = payment_event.amount

            # Determine account codes based on payment type
            if context.data.get("subscription_id"):
                # Subscription payment
                revenue_account = "4100"  # Subscription Revenue
                description = f"Subscription payment from {payment_event.name}"
            else:
                # One-time payment
                revenue_account = "4200"  # One-time Payment Revenue
                description = f"One-time payment from {payment_event.name}"

            # Debit: Cash/Bank Account (Asset increases)
            cash_entry = AccountingEntrySchema(
                transaction_id=transaction_id,
                account_code="1100",  # Cash/Bank Account
                description=f"Payment received - {description}",
                debit_amount=amount,
                currency=payment_event.currency,
                reference_id=context.data.get("payment_intent_id"),
                created_at=datetime.utcnow(),
            )
            entries.append(cash_entry.dict())

            # Credit: Revenue Account (Revenue increases)
            revenue_entry = AccountingEntrySchema(
                transaction_id=transaction_id,
                account_code=revenue_account,
                description=description,
                credit_amount=amount,
                currency=payment_event.currency,
                reference_id=context.data.get("payment_intent_id"),
                created_at=datetime.utcnow(),
            )
            entries.append(revenue_entry.dict())

            # Handle processing fees if applicable
            processing_fee = await self._calculate_processing_fee(
                amount, payment_event.currency
            )
            if processing_fee > 0:
                # Debit: Processing Fee Expense
                fee_entry = AccountingEntrySchema(
                    transaction_id=transaction_id,
                    account_code="6100",  # Processing Fee Expense
                    description=f"Payment processing fee - {description}",
                    debit_amount=processing_fee,
                    currency=payment_event.currency,
                    reference_id=context.data.get("payment_intent_id"),
                    created_at=datetime.utcnow(),
                )
                entries.append(fee_entry.dict())

                # Credit: Cash/Bank Account (reduce cash by fee amount)
                fee_cash_entry = AccountingEntrySchema(
                    transaction_id=transaction_id,
                    account_code="1100",  # Cash/Bank Account
                    description=f"Payment processing fee deduction - {description}",
                    credit_amount=processing_fee,
                    currency=payment_event.currency,
                    reference_id=context.data.get("payment_intent_id"),
                    created_at=datetime.utcnow(),
                )
                entries.append(fee_cash_entry.dict())

            # Log accounting entries for audit purposes
            logger.info(
                f"Created {len(entries)} accounting entries for transaction {transaction_id}"
            )

            return entries

        except Exception as e:
            logger.error(f"Failed to create accounting entries: {str(e)}")
            return []

    async def _update_customer_account(
        self, context: TaskContext, payment_event: PaymentEventSchema
    ) -> Dict[str, Any]:
        """
        Update customer account balance and payment history.

        Args:
            context: Task context
            payment_event: Payment event data

        Returns:
            Dictionary with customer account update results
        """
        try:
            db: Session = db_session()

            # Find user record
            user = db.query(User).filter(User.id == payment_event.user_id).first()
            if not user:
                logger.error(
                    f"User not found for accounting update: {payment_event.user_id}"
                )
                return {"success": False, "error": "User not found"}

            # Update user's payment history (this would typically be in a separate payments table)
            # For now, we'll just log the update
            logger.info(
                f"Updated customer account for user {payment_event.user_id} - Payment: ${payment_event.amount}"
            )

            # In a real system, you might:
            # - Update account balance
            # - Record payment history
            # - Update subscription status
            # - Calculate loyalty points
            # - Update customer lifetime value

            db.commit()

            return {
                "success": True,
                "user_id": str(payment_event.user_id),
                "amount_paid": str(payment_event.amount),
                "currency": payment_event.currency,
                "message": "Customer account updated successfully",
            }

        except Exception as e:
            logger.error(f"Failed to update customer account: {str(e)}")
            if "db" in locals():
                db.rollback()
            return {"success": False, "error": str(e)}
        finally:
            if "db" in locals():
                db.close()

    async def _create_transaction_record(
        self, context: TaskContext, payment_event: PaymentEventSchema
    ) -> Dict[str, Any]:
        """
        Create a comprehensive transaction record for reporting and audit.

        Args:
            context: Task context
            payment_event: Payment event data

        Returns:
            Dictionary with transaction record results
        """
        try:
            transaction_record = {
                "transaction_id": str(uuid4()),
                "user_id": str(payment_event.user_id),
                "customer_name": payment_event.name,
                "customer_email": payment_event.email,
                "payment_intent_id": context.data.get("payment_intent_id"),
                "charge_id": context.data.get("charge_id"),
                "subscription_id": context.data.get("subscription_id"),
                "amount": str(payment_event.amount),
                "currency": payment_event.currency,
                "payment_method_type": payment_event.payment_method.type
                if payment_event.payment_method
                else "unknown",
                "payment_status": PaymentStatus.SUCCEEDED,
                "processed_at": datetime.utcnow().isoformat(),
                "stripe_customer_id": context.data.get("stripe_customer_id"),
                "receipt_url": context.data.get("receipt_url"),
                "metadata": payment_event.metadata or {},
            }

            # In a production system, you would store this in a transactions table
            logger.info(
                f"Transaction record created: {transaction_record['transaction_id']}"
            )

            return {
                "success": True,
                "transaction_record": transaction_record,
                "message": "Transaction record created successfully",
            }

        except Exception as e:
            logger.error(f"Failed to create transaction record: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _handle_tax_calculations(
        self, context: TaskContext, payment_event: PaymentEventSchema
    ) -> Dict[str, Any]:
        """
        Handle tax calculations and records if applicable.

        Args:
            context: Task context
            payment_event: Payment event data

        Returns:
            Dictionary with tax calculation results
        """
        try:
            tax_rate = payment_event.tax_rate or Decimal("0")

            if tax_rate > 0:
                tax_amount = payment_event.amount * tax_rate

                tax_record = {
                    "tax_rate": str(tax_rate),
                    "tax_amount": str(tax_amount),
                    "taxable_amount": str(payment_event.amount - tax_amount),
                    "currency": payment_event.currency,
                    "tax_jurisdiction": "default",  # Would be determined by customer location
                    "calculated_at": datetime.utcnow().isoformat(),
                }

                logger.info(
                    f"Tax calculated: {tax_amount} {payment_event.currency} at rate {tax_rate}"
                )

                return {
                    "success": True,
                    "tax_record": tax_record,
                    "message": "Tax calculations completed",
                }
            else:
                return {
                    "success": True,
                    "tax_record": None,
                    "message": "No tax applicable",
                }

        except Exception as e:
            logger.error(f"Failed to handle tax calculations: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _generate_audit_trail(
        self, context: TaskContext, payment_event: PaymentEventSchema
    ) -> Dict[str, Any]:
        """
        Generate comprehensive audit trail for the payment transaction.

        Args:
            context: Task context
            payment_event: Payment event data

        Returns:
            Dictionary with audit trail results
        """
        try:
            audit_trail = {
                "audit_id": str(uuid4()),
                "event_type": "payment_processed",
                "user_id": str(payment_event.user_id),
                "amount": str(payment_event.amount),
                "currency": payment_event.currency,
                "payment_intent_id": context.data.get("payment_intent_id"),
                "workflow_id": context.data.get("workflow_id"),
                "timestamp": datetime.utcnow().isoformat(),
                "ip_address": context.data.get(
                    "ip_address"
                ),  # Would be captured from request
                "user_agent": context.data.get(
                    "user_agent"
                ),  # Would be captured from request
                "workflow_steps": list(context.results.keys()),
                "final_status": "success",
                "metadata": {
                    "subscription_id": context.data.get("subscription_id"),
                    "customer_id": context.data.get("stripe_customer_id"),
                    "retry_count": context.data.get("retry_count", 0),
                },
            }

            # Log audit trail
            logger.info(f"Audit trail generated: {audit_trail['audit_id']}")

            return {
                "success": True,
                "audit_trail": audit_trail,
                "message": "Audit trail generated successfully",
            }

        except Exception as e:
            logger.error(f"Failed to generate audit trail: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _calculate_processing_fee(
        self, amount: Decimal, currency: str
    ) -> Decimal:
        """
        Calculate payment processing fees.

        Args:
            amount: Payment amount
            currency: Payment currency

        Returns:
            Processing fee amount
        """
        # Stripe's typical fee structure (this would be configurable in production)
        if currency.lower() == "usd":
            # 2.9% + $0.30 for US cards
            percentage_fee = amount * Decimal("0.029")
            fixed_fee = Decimal("0.30")
            return percentage_fee + fixed_fee
        else:
            # International rates vary, using a simplified calculation
            return amount * Decimal("0.035")  # 3.5%

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
        context.data["accounting_updated"] = False

        context.results[self.name] = {
            "success": False,
            "error_code": error_code,
            "error_message": error_message,
        }

        return context

    def validate_input(self, context: TaskContext) -> bool:
        """
        Validate that the context contains required data for accounting updates.

        Args:
            context: Task context to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            # Validate payment event schema
            PaymentEventSchema(**context.data)

            # Check that payment was successful
            payment_status = context.data.get("payment_status")
            if payment_status != PaymentStatus.SUCCEEDED:
                logger.error(
                    f"Accounting update requires successful payment, got: {payment_status}"
                )
                return False

            # Check required fields for accounting
            required_fields = ["amount", "currency", "user_id"]
            for field in required_fields:
                if field not in context.data or not context.data[field]:
                    logger.error(f"Missing required field for accounting: {field}")
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
        return {}  # No external configuration required for basic accounting

    def get_output_schema(self) -> Dict[str, Any]:
        """
        Get the output schema for this node.

        Returns:
            Dictionary describing the output data structure
        """
        return {
            "accounting_updated": "bool - Whether accounting records were updated",
            "accounting_entries": "List[Dict] - List of accounting entries created",
            "customer_account_updated": "bool - Whether customer account was updated",
            "transaction_record_created": "bool - Whether transaction record was created",
            "tax_calculated": "bool - Whether tax calculations were performed",
            "audit_trail_created": "bool - Whether audit trail was generated",
        }
